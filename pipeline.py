"""End-to-end pipeline wiring for the Behavioural Forecasting Engine."""
import logging
import logging.config
import os

import numpy as np
import pandas as pd

from utils import load_history_df
from nodes import (
    run_ingestion,
    run_normalization,
    run_bayesian,
    run_gradient_boost,
    run_forecast,
    run_metrics,
    run_recalibration,
    run_anomaly,
)
from nodes.node_1_ingestion import MockAdapter, AppleHealthAdapter, IngestionAdapter


# ---------------------------------------------------------------------------
# Logging configuration — call setup_logging() once at process startup.
# ---------------------------------------------------------------------------
def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the BFE pipeline."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "bfe": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "bfe",
                }
            },
            "root": {"handlers": ["console"], "level": level},
        }
    )


logger = logging.getLogger(__name__)

_MIN_HISTORY_ROWS = 30


def run_pipeline(
    user_id: str = "USER123",
    target_mood: "np.ndarray | list | None" = None,
    actual_mood_today: "float | np.ndarray | None" = None,
    user_feedback: "list | np.ndarray | None" = None,
    history_path: "str | None" = None,
    use_mock_ingestion: bool = True,
    ingestion_adapter: "IngestionAdapter | None" = None,
    bayesian_method: str = "map",
) -> dict:
    """Run the full behavioural forecasting pipeline.

    Args:
        user_id:            User identifier for ingestion.
        target_mood:        Historical mood values aligned with history rows.
        actual_mood_today:  Today's actual mood for metrics evaluation (optional).
        user_feedback:      Recent feedback [0, 1, 2] for recalibration (optional).
        history_path:       Path to history parquet (optional).
        use_mock_ingestion: If True, use MockAdapter (ignores ingestion_adapter).
        ingestion_adapter:  Custom IngestionAdapter for live ingestion.
                            If None and use_mock_ingestion is False, resolves api_key
                            from the HEALTH_API_KEY environment variable.
        bayesian_method:    "map" (fast, default) or "mcmc" (full sampling).

    Returns:
        Dict containing:
            forecast_df, weights, intercept, refined_importance,
            mae, rmse, alert_flag, deviations,
            normalized_features, baseline_stats.
    """
    logger.info("pipeline=bfe status=start user_id=%s", user_id)

    # ------------------------------------------------------------------
    # 1. Ingestion
    # ------------------------------------------------------------------
    if use_mock_ingestion:
        adapter: IngestionAdapter = MockAdapter()
        logger.info("pipeline=bfe ingestion=mock")
    elif ingestion_adapter is not None:
        adapter = ingestion_adapter
        logger.info("pipeline=bfe ingestion=injected_adapter type=%s", type(adapter).__name__)
    else:
        api_key = os.getenv("HEALTH_API_KEY", "")
        adapter = AppleHealthAdapter(api_key=api_key)
        logger.info("pipeline=bfe ingestion=apple_health")

    df_new, _daily_features = run_ingestion(user_id=user_id, adapter=adapter)

    # ------------------------------------------------------------------
    # 2. Build / pad history
    # ------------------------------------------------------------------
    history_df = load_history_df(history_path)
    history_df = pd.concat([history_df, df_new], ignore_index=True)

    if len(history_df) < _MIN_HISTORY_ROWS:
        logger.warning(
            "pipeline=bfe history_rows=%d < min_rows=%d "
            "— padding with repeated latest row (demo mode only)",
            len(history_df),
            _MIN_HISTORY_ROWS,
        )
        pad_count = _MIN_HISTORY_ROWS - len(history_df)
        pad = pd.concat([df_new] * pad_count, ignore_index=True)
        history_df = pd.concat([pad, history_df], ignore_index=True)

    logger.info("pipeline=bfe history_rows=%d", len(history_df))

    # ------------------------------------------------------------------
    # 3. Normalization + rolling baseline
    # ------------------------------------------------------------------
    normalized_features, baseline_stats = run_normalization(history_df)

    # ------------------------------------------------------------------
    # 4. Target mood alignment
    # ------------------------------------------------------------------
    n_rows = len(normalized_features)
    if target_mood is None:
        np.random.seed(42)
        target_mood = np.random.uniform(3, 8, size=n_rows)

    target_mood = np.asarray(target_mood, dtype=np.float64).ravel()

    if len(target_mood) > n_rows:
        target_mood = target_mood[-n_rows:]
    elif len(target_mood) < n_rows:
        target_mood = np.pad(
            target_mood,
            (n_rows - len(target_mood), 0),
            constant_values=5.0,
        )

    # ------------------------------------------------------------------
    # 5. Bayesian personalization (heavy)
    # ------------------------------------------------------------------
    weights, intercept = run_bayesian(
        normalized_features, baseline_stats, target_mood, method=bayesian_method
    )

    # ------------------------------------------------------------------
    # 6. Gradient boost refinement (heavy)
    # ------------------------------------------------------------------
    refined_importance = run_gradient_boost(normalized_features, target_mood)

    # ------------------------------------------------------------------
    # 7. Forecast for today — last row only (heavy)
    # ------------------------------------------------------------------
    today_features = normalized_features.iloc[[-1]]
    forecast_df = run_forecast(weights, intercept, today_features)

    # ------------------------------------------------------------------
    # 8. Metrics (heavy, optional)
    # ------------------------------------------------------------------
    if actual_mood_today is not None:
        mae, rmse = run_metrics(forecast_df, actual_mood_today)
    else:
        mae, rmse = float("nan"), float("nan")

    # ------------------------------------------------------------------
    # 9. Recalibration (heavy, optional)
    # ------------------------------------------------------------------
    if user_feedback is not None:
        weights = run_recalibration(weights, user_feedback)

    # ------------------------------------------------------------------
    # 10. Anomaly detection — pass RAW history, not normalized (light)
    # ------------------------------------------------------------------
    alert_flag, deviations = run_anomaly(baseline_stats, history_df)

    logger.info(
        "pipeline=bfe status=end forecast=%.4f alert=%s mae=%s rmse=%s",
        float(forecast_df["pred"].iloc[0]),
        alert_flag,
        f"{mae:.4f}" if mae == mae else "nan",  # nan-safe
        f"{rmse:.4f}" if rmse == rmse else "nan",
    )

    return {
        "forecast_df": forecast_df,
        "weights": weights,
        "intercept": intercept,
        "refined_importance": refined_importance,
        "mae": mae,
        "rmse": rmse,
        "alert_flag": alert_flag,
        "deviations": deviations,
        "normalized_features": normalized_features,
        "baseline_stats": baseline_stats,
    }


if __name__ == "__main__":
    setup_logging()
    result = run_pipeline(use_mock_ingestion=True)
    print("Forecast:", result["forecast_df"])
    print("Alert:", result["alert_flag"])
    print("MAE:", result["mae"], "RMSE:", result["rmse"])
