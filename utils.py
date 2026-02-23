"""Utilities for Behavioural Forecasting Engine pipeline."""
import pandas as pd
from pathlib import Path


def load_history_df(path: str | Path | None = None) -> pd.DataFrame:
    """Load historical feature DataFrame from disk or return empty."""
    if path is None:
        path = Path(__file__).parent / "data" / "history.parquet"
    path = Path(path)
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()
