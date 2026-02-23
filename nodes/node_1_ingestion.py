"""Node 1: Physiological Data Ingestion.

Light node — no Lovable credits consumed.

Ingestion is performed via an IngestionAdapter.  Two adapters are provided:
  - AppleHealthAdapter  real HTTP call; auth key injected at construction time.
  - MockAdapter         returns synthetic data; safe for testing.

No credentials are hard-coded.  Pass api_key=None to force resolution from the
HEALTH_API_KEY environment variable, or inject any adapter conforming to the
protocol directly via the `adapter` parameter of run().
"""
import logging
import os
from typing import Protocol, runtime_checkable

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column schema — all nodes rely on these names being present.
# ---------------------------------------------------------------------------
FEATURE_COLUMNS: list[str] = [
    "sleep_hours",
    "hrv",
    "resting_hr",
    "steps",
    "workouts",
    "vo2_max",
    "mindfulness_minutes",
]

_MOCK_DEFAULTS: dict[str, float] = {
    "sleep_hours": 7.2,
    "hrv": 45.0,
    "resting_hr": 62.0,
    "steps": 8500.0,
    "workouts": 1.0,
    "vo2_max": 42.0,
    "mindfulness_minutes": 10.0,
}


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------
@runtime_checkable
class IngestionAdapter(Protocol):
    def fetch(self, user_id: str) -> dict[str, float | None]:
        """Return a dict keyed by FEATURE_COLUMNS.  Values may be None."""
        ...


class AppleHealthAdapter:
    """Fetches daily physiological data from the Apple Health bridge API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.applehealth.example.com",
        timeout: int = 10,
    ) -> None:
        if not api_key:
            raise ValueError("AppleHealthAdapter requires a non-empty api_key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fetch(self, user_id: str) -> dict[str, float | None]:
        url = f"{self._base_url}/users/{user_id}/daily"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            response = requests.get(url, headers=headers, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.error("node=node_1_ingestion status=fetch_error error=%r", exc)
            raise RuntimeError(f"Apple Health fetch failed for user {user_id!r}: {exc}") from exc

        return {
            "sleep_hours": data.get("sleep"),
            "hrv": data.get("hrv"),
            "resting_hr": data.get("rhr"),
            "steps": data.get("steps"),
            "workouts": data.get("workouts"),
            "vo2_max": data.get("vo2_max"),
            "mindfulness_minutes": data.get("mindfulness"),
        }


class MockAdapter:
    """Returns synthetic physiological data.  Safe for testing and demos."""

    def __init__(self, data: dict[str, float] | None = None) -> None:
        self._data = data if data is not None else dict(_MOCK_DEFAULTS)

    def fetch(self, user_id: str) -> dict[str, float | None]:
        logger.debug("node=node_1_ingestion status=mock_fetch user_id=%s", user_id)
        return dict(self._data)


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------
def fetch_apple_health(user_id: str, api_key: str) -> dict[str, float | None]:
    """Convenience wrapper around AppleHealthAdapter for backwards compatibility."""
    return AppleHealthAdapter(api_key=api_key).fetch(user_id)


def _validate_features(features: dict) -> dict[str, float]:
    """Fill missing keys with NaN and coerce values to float."""
    validated: dict[str, float] = {}
    for col in FEATURE_COLUMNS:
        val = features.get(col)
        validated[col] = float(val) if val is not None else float("nan")
    missing = [k for k, v in validated.items() if v != v]  # NaN check
    if missing:
        logger.warning("node=node_1_ingestion missing_fields=%s", missing)
    return validated


# ---------------------------------------------------------------------------
# Node entry point
# ---------------------------------------------------------------------------
def run(
    user_id: str,
    api_key: str | None = None,
    adapter: IngestionAdapter | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Ingest physiological data and return (df_features, daily_features_dict).

    Args:
        user_id:  User identifier passed to the adapter.
        api_key:  API key for AppleHealthAdapter.  Falls back to the
                  HEALTH_API_KEY environment variable when not supplied.
                  Ignored when `adapter` is provided.
        adapter:  Any object implementing IngestionAdapter.  When provided,
                  api_key is ignored.

    Returns:
        df_features:    Single-row DataFrame with FEATURE_COLUMNS.
        daily_features: Same data as a plain dict.
    """
    logger.info("node=node_1_ingestion status=start user_id=%s", user_id)

    if adapter is None:
        resolved_key = api_key or os.getenv("HEALTH_API_KEY", "")
        adapter = AppleHealthAdapter(api_key=resolved_key)

    raw = adapter.fetch(user_id)
    daily_features = _validate_features(raw)
    df_features = pd.DataFrame([daily_features])

    logger.info("node=node_1_ingestion status=end shape=%s", df_features.shape)
    return df_features, daily_features
