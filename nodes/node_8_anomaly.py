"""Node 8: Anomaly Detection Alert.

Light node — no Lovable credits consumed.

IMPORTANT — scale contract:
  Both `baseline_df` and `features_df` MUST be in the same (raw) scale.
  Pass `history_df` (raw features) as `features_df`, NOT `normalized_features`.
  `baseline_df` is the rolling mean returned by node_2 in the original scale.

  Comparing normalized [0,1] features against a raw-scale baseline would yield
  deviations near 1.0 for every feature, triggering constant false alerts.
"""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def detect_anomaly(
    baseline_df: pd.DataFrame,
    features_df: pd.DataFrame,
    threshold: float = 0.2,
) -> tuple[bool, pd.Series]:
    """Detect anomalies and return (alert_flag, per-feature deviations).

    Args:
        baseline_df: Rolling baseline DataFrame in RAW feature scale (from node_2).
        features_df: Raw feature DataFrame in the same scale as baseline_df.
                     The LAST row is used as today's observation.
        threshold:   Fractional deviation threshold (0.2 = 20% from baseline).

    Returns:
        alert_flag: True if any feature deviates beyond `threshold`.
        deviations: Per-feature fractional deviation Series.
    """
    if baseline_df.empty:
        logger.warning("node=node_8_anomaly status=skipped reason=empty_baseline")
        empty = pd.Series(dtype=float)
        return False, empty

    today = features_df.iloc[-1]
    baseline_last = baseline_df.iloc[-1]

    if baseline_last.isna().all():
        logger.warning(
            "node=node_8_anomaly status=skipped reason=baseline_all_nan "
            "(history < min_periods=14 rows) fallback=no_alert"
        )
        return False, pd.Series(np.zeros(len(today)), index=today.index)

    baseline_safe = baseline_last.replace(0, np.nan)
    deviations = (today - baseline_safe).abs() / baseline_safe.abs()
    deviations = deviations.fillna(0.0)

    alert = bool((deviations > threshold).any())
    logger.info(
        "node=node_8_anomaly status=end alert=%s max_deviation=%.4f",
        alert,
        float(deviations.max()),
    )
    return alert, deviations


def run(
    baseline_stats: pd.DataFrame,
    history_df: pd.DataFrame,
) -> tuple[bool, pd.Series]:
    """Return (alert_flag, deviations).

    Args:
        baseline_stats: Raw-scale rolling baseline from node_2.
        history_df:     Raw feature history (NOT normalized_features).
                        Pass the same `history_df` used before normalization.
    """
    logger.info("node=node_8_anomaly status=start history_rows=%d", len(history_df))
    return detect_anomaly(baseline_stats, history_df)
