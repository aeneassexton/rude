"""Node 2: Feature Normalization + Rolling Baseline.

Light node — no Lovable credits consumed.

Min-max normalization is computed over the full history window passed in.
The rolling baseline (30-day mean, min 14 days) is returned in the original
feature scale so that node_8_anomaly can compare raw observations against it.
"""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def normalize_and_baseline(
    df_features: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize features to [0, 1] and compute 30-day rolling baseline.

    Args:
        df_features: DataFrame of raw physiological features (N rows).

    Returns:
        normalized:     Min-max scaled copy of df_features in [0, 1].
        baseline_stats: Rolling 30-day mean in the ORIGINAL (raw) scale.
                        Used by node_8_anomaly — do NOT pass normalized here.
    """
    if df_features.empty:
        raise ValueError("node_2_normalization received an empty DataFrame")

    col_min = df_features.min()
    col_max = df_features.max()
    denom = (col_max - col_min).replace(0, np.nan)

    normalized = (df_features - col_min) / denom
    normalized = normalized.fillna(0.0)

    # Baseline in raw scale — intentionally NOT normalized.
    baseline_stats = df_features.rolling(window=30, min_periods=14).mean()

    nan_cols = normalized.columns[normalized.isna().any()].tolist()
    if nan_cols:
        logger.warning(
            "node=node_2_normalization NaN_after_fillna cols=%s", nan_cols
        )

    logger.info(
        "node=node_2_normalization status=end shape=%s baseline_null_rows=%d",
        normalized.shape,
        int(baseline_stats.isna().all(axis=1).sum()),
    )
    return normalized, baseline_stats


def run(df_features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (normalized_features, baseline_stats)."""
    logger.info("node=node_2_normalization status=start shape=%s", df_features.shape)
    return normalize_and_baseline(df_features)
