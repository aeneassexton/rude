"""Node 6: Accuracy Metrics (MAE/RMSE for continuous mood).

Heavy node — consumes 1 Lovable credit per call.

Fallback when credits are insufficient:
  Returns (nan, nan) — pipeline continues without metric logging.
"""
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from lovable import InsufficientCreditsError, use_credits

logger = logging.getLogger(__name__)

_CREDITS_COST = 1

# sklearn >= 1.4 exposes root_mean_squared_error directly.
# Fall back to sqrt(mse) for older versions to avoid the deprecation warning
# that occurs when using mean_squared_error(squared=False).
try:
    from sklearn.metrics import root_mean_squared_error as _rmse_fn

    def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return float(_rmse_fn(y_true, y_pred))

except ImportError:
    from sklearn.metrics import mean_squared_error as _mse_fn  # type: ignore[assignment]

    def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        return float(np.sqrt(_mse_fn(y_true, y_pred)))


def compute_metrics(
    preds_df: pd.DataFrame,
    actuals: "float | np.ndarray | list",
) -> tuple[float, float]:
    """Return (mae, rmse) for continuous mood targets.

    Args:
        preds_df: Forecast DataFrame with a "pred" column.
        actuals:  Scalar or array of ground-truth mood values, aligned with preds_df rows.
    """
    y_pred = np.asarray(preds_df["pred"].values, dtype=np.float64)
    y_true = np.asarray(actuals, dtype=np.float64).ravel()

    if len(y_pred) != len(y_true):
        raise ValueError(
            f"preds length ({len(y_pred)}) != actuals length ({len(y_true)})"
        )

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = _rmse(y_true, y_pred)
    return mae, rmse


def run(
    forecast_df: pd.DataFrame,
    actual_mood: "float | np.ndarray | list",
) -> tuple[float, float]:
    """Return (mae, rmse).

    Skips and returns (nan, nan) when Lovable credits are insufficient.
    """
    logger.info("node=node_6_metrics status=start")

    try:
        use_credits(_CREDITS_COST, reason="node_6_metrics")
    except InsufficientCreditsError:
        logger.warning(
            "node=node_6_metrics status=skipped reason=insufficient_credits fallback=(nan,nan)"
        )
        return float("nan"), float("nan")

    mae, rmse = compute_metrics(forecast_df, actual_mood)
    logger.info("node=node_6_metrics status=end mae=%.4f rmse=%.4f", mae, rmse)
    return mae, rmse
