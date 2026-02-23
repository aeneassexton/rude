"""Simple file-backed mood history store.

Persists daily mood logs as a parquet file under data/.
Provides the history_df that the BFE pipeline needs.

In production, swap this for a Supabase / Postgres adapter
by replacing MoodStore.load() and MoodStore.append().
"""
import logging
from datetime import date
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Mood labels from the UI mapped to a numeric score on a 1–10 scale.
# Extend this dict as new mood states are added in Lovable.
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


class MoodStore:
    """Per-user mood log backed by a parquet file."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._path = DATA_DIR / f"mood_{user_id}.parquet"
        self._history_path = DATA_DIR / f"history_{user_id}.parquet"

    # ------------------------------------------------------------------
    # Mood log (user-facing: label + date)
    # ------------------------------------------------------------------
    def load_mood_log(self) -> pd.DataFrame:
        if self._path.exists():
            return pd.read_parquet(self._path)
        return pd.DataFrame(columns=["date", "mood_label", "mood_score"])

    def append_mood(self, mood_label: str, log_date: date | None = None) -> None:
        log_date = log_date or date.today()
        score = mood_label_to_score(mood_label)
        new_row = pd.DataFrame(
            [{"date": str(log_date), "mood_label": mood_label.lower(), "mood_score": score}]
        )
        df = self.load_mood_log()
        df = pd.concat([df, new_row], ignore_index=True)
        df = df.drop_duplicates(subset=["date"], keep="last")
        df.to_parquet(self._path, index=False)
        logger.info("store user=%s date=%s mood=%s score=%.1f", self.user_id, log_date, mood_label, score)

    # ------------------------------------------------------------------
    # Physiological feature history (BFE pipeline input)
    # ------------------------------------------------------------------
    def load_feature_history(self) -> pd.DataFrame:
        if self._history_path.exists():
            return pd.read_parquet(self._history_path)
        return pd.DataFrame()

    def append_features(self, features: dict) -> None:
        new_row = pd.DataFrame([features])
        df = self.load_feature_history()
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_parquet(self._history_path, index=False)
