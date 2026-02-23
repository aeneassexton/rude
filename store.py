"""Mood history store with automatic Supabase / parquet backend selection.

Backend is chosen at import time:
  - If SUPABASE_URL and SUPABASE_SERVICE_KEY are set → Supabase (production)
  - Otherwise → local parquet files under data/ (local dev / testing)

Required Supabase tables (run once in SQL Editor):

    CREATE TABLE IF NOT EXISTS mood_logs (
      id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
      user_id text NOT NULL,
      date date NOT NULL,
      mood_label text NOT NULL,
      mood_score float NOT NULL,
      created_at timestamptz DEFAULT now(),
      UNIQUE(user_id, date)
    );

    CREATE TABLE IF NOT EXISTS feature_history (
      id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
      user_id text NOT NULL,
      date date NOT NULL,
      sleep_hours float, hrv float, resting_hr float,
      steps float, workouts float, vo2_max float,
      mindfulness_minutes float,
      created_at timestamptz DEFAULT now(),
      UNIQUE(user_id, date)
    );
"""
import logging
import os
from datetime import date
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mood label ↔ score mappings (shared by both backends)
# ---------------------------------------------------------------------------
MOOD_LABEL_TO_SCORE: dict[str, float] = {
    "radiant": 9.0,
    "energised": 8.0,
    "steady": 7.0,
    "calm": 6.5,
    "quiet": 5.5,
    "tired": 4.0,
    "heavy": 2.5,
    "low": 1.5,
}

MOOD_SCORE_COLOURS: list[tuple[float, str]] = [
    (8.0, "green"),
    (6.0, "blue"),
    (4.0, "gray"),
    (0.0, "red"),
]


def mood_label_to_score(label: str) -> float:
    return MOOD_LABEL_TO_SCORE.get(label.lower(), 5.0)


def score_to_colour(score: float) -> str:
    for threshold, colour in MOOD_SCORE_COLOURS:
        if score >= threshold:
            return colour
    return "red"


def score_to_label(score: float) -> str:
    closest = min(MOOD_LABEL_TO_SCORE, key=lambda k: abs(MOOD_LABEL_TO_SCORE[k] - score))
    return closest.capitalize()


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------
_SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
_USE_SUPABASE = bool(_SUPABASE_URL and _SUPABASE_KEY)

if _USE_SUPABASE:
    from supabase import create_client, Client as SupabaseClient
    _sb: SupabaseClient = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    logger.info("store backend=supabase url=%s", _SUPABASE_URL)
else:
    _sb = None  # type: ignore[assignment]
    logger.info("store backend=parquet (set SUPABASE_URL + SUPABASE_SERVICE_KEY for production)")

# ---------------------------------------------------------------------------
# Parquet fallback paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# MoodStore
# ---------------------------------------------------------------------------
class MoodStore:
    """Per-user mood log. Automatically uses Supabase or local parquet."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._mood_path = DATA_DIR / f"mood_{user_id}.parquet"
        self._feat_path = DATA_DIR / f"history_{user_id}.parquet"

    # ------------------------------------------------------------------
    # Mood log
    # ------------------------------------------------------------------
    def load_mood_log(self) -> pd.DataFrame:
        if _USE_SUPABASE:
            return self._sb_load_mood_log()
        return self._parquet_load_mood_log()

    def append_mood(self, mood_label: str, log_date: date | None = None) -> None:
        log_date = log_date or date.today()
        score = mood_label_to_score(mood_label)
        if _USE_SUPABASE:
            self._sb_append_mood(mood_label, log_date, score)
        else:
            self._parquet_append_mood(mood_label, log_date, score)
        logger.info(
            "store backend=%s user=%s date=%s mood=%s score=%.1f",
            "supabase" if _USE_SUPABASE else "parquet",
            self.user_id, log_date, mood_label, score,
        )

    # ------------------------------------------------------------------
    # Feature history
    # ------------------------------------------------------------------
    def load_feature_history(self) -> pd.DataFrame:
        if _USE_SUPABASE:
            return self._sb_load_features()
        return self._parquet_load_features()

    def append_features(self, features: dict) -> None:
        if _USE_SUPABASE:
            self._sb_append_features(features)
        else:
            self._parquet_append_features(features)

    # ------------------------------------------------------------------
    # Supabase implementations
    # ------------------------------------------------------------------
    def _sb_load_mood_log(self) -> pd.DataFrame:
        try:
            resp = (
                _sb.table("mood_logs")
                .select("date, mood_label, mood_score")
                .eq("user_id", self.user_id)
                .order("date")
                .execute()
            )
            if resp.data:
                return pd.DataFrame(resp.data)
            return pd.DataFrame(columns=["date", "mood_label", "mood_score"])
        except Exception as exc:
            logger.error("supabase load_mood_log failed user=%s: %s", self.user_id, exc)
            return pd.DataFrame(columns=["date", "mood_label", "mood_score"])

    def _sb_append_mood(self, mood_label: str, log_date: date, score: float) -> None:
        try:
            _sb.table("mood_logs").upsert(
                {
                    "user_id": self.user_id,
                    "date": str(log_date),
                    "mood_label": mood_label.lower(),
                    "mood_score": score,
                },
                on_conflict="user_id,date",
            ).execute()
        except Exception as exc:
            logger.error("supabase append_mood failed user=%s: %s", self.user_id, exc)
            raise

    def _sb_load_features(self) -> pd.DataFrame:
        _FEAT_COLS = [
            "date", "sleep_hours", "hrv", "resting_hr",
            "steps", "workouts", "vo2_max", "mindfulness_minutes",
        ]
        try:
            resp = (
                _sb.table("feature_history")
                .select(", ".join(_FEAT_COLS))
                .eq("user_id", self.user_id)
                .order("date")
                .execute()
            )
            if resp.data:
                return pd.DataFrame(resp.data).drop(columns=["date"], errors="ignore")
            return pd.DataFrame()
        except Exception as exc:
            logger.error("supabase load_features failed user=%s: %s", self.user_id, exc)
            return pd.DataFrame()

    def _sb_append_features(self, features: dict) -> None:
        try:
            payload = {"user_id": self.user_id, "date": str(date.today()), **features}
            _sb.table("feature_history").upsert(
                payload, on_conflict="user_id,date"
            ).execute()
        except Exception as exc:
            logger.error("supabase append_features failed user=%s: %s", self.user_id, exc)

    # ------------------------------------------------------------------
    # Parquet implementations (local dev fallback)
    # ------------------------------------------------------------------
    def _parquet_load_mood_log(self) -> pd.DataFrame:
        if self._mood_path.exists():
            return pd.read_parquet(self._mood_path)
        return pd.DataFrame(columns=["date", "mood_label", "mood_score"])

    def _parquet_append_mood(self, mood_label: str, log_date: date, score: float) -> None:
        new_row = pd.DataFrame(
            [{"date": str(log_date), "mood_label": mood_label.lower(), "mood_score": score}]
        )
        df = pd.concat([self._parquet_load_mood_log(), new_row], ignore_index=True)
        df = df.drop_duplicates(subset=["date"], keep="last")
        df.to_parquet(self._mood_path, index=False)

    def _parquet_load_features(self) -> pd.DataFrame:
        if self._feat_path.exists():
            return pd.read_parquet(self._feat_path)
        return pd.DataFrame()

    def _parquet_append_features(self, features: dict) -> None:
        new_row = pd.DataFrame([features])
        df = pd.concat([self._parquet_load_features(), new_row], ignore_index=True)
        df.to_parquet(self._feat_path, index=False)
