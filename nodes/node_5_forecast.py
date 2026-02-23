"""Node 5: Predictive Output + Confidence Intervals.

Heavy node — consumes 1 Lovable credit per call.

Fallback when credits are insufficient:
  Returns a neutral forecast (pred=5.0, ci_lower=3.5, ci_upper=6.5) for each
  input row.  Callers can detect a skipped run by checking for this sentinel
  or by inspecting logs.
"""
import logging

import numpy as np
import pandas as pd
import scipy.stats as st

from lovable import InsufficientCreditsError, use_credits

logger = logging.getLogger(__name__)

_CREDITS_COST = 1
_NEUTRAL_PRED = 5.0
_NEUTRAL_CI_HALF = 1.5


def generate_forecast(
    weights: np.ndarray,
    intercept: float,
    features_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate forecasts with 95% per-point confidence intervals.

    Args:
        weights:     1-D weight array of shape (F,).
        intercept:   Scalar bias term.
        features_df: Feature DataFrame (N x F) — typically today's single row.

    Returns:
        DataFrame with columns ["pred", "ci_lower", "ci_upper"].
    """
    if np.isnan(weights).any():
        raise ValueError(
            "weights contain NaN — Bayesian node may have failed. "
            "Check node_3 logs for details."
        )
    if np.isnan(intercept):
        raise ValueError("intercept is NaN")
    if features_df.empty:
        raise ValueError("features_df is empty")

    X = features_df.values
    preds = X.dot(weights) + intercept

    # Sigma from the spread of predictions; fall back to 1.0 for single-point forecasts.
    sigma = float(np.std(preds)) if len(preds) > 1 else 1.0
    if sigma == 0.0:
        sigma = 1.0

    ci_lower, ci_upper = st.norm.interval(0.95, loc=preds, scale=sigma)
    return pd.DataFrame({"pred": preds, "ci_lower": ci_lower, "ci_upper": ci_upper})


def _neutral_forecast(n_rows: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pred": np.full(n_rows, _NEUTRAL_PRED),
            "ci_lower": np.full(n_rows, _NEUTRAL_PRED - _NEUTRAL_CI_HALF),
            "ci_upper": np.full(n_rows, _NEUTRAL_PRED + _NEUTRAL_CI_HALF),
        }
    )


def run(
    weights: np.ndarray,
    intercept: float,
    normalized_features: pd.DataFrame,
) -> pd.DataFrame:
    """Return forecast_df.

    Use today_features = normalized_features.iloc[[-1]] for a daily forecast.
    Skips and returns neutral forecast when Lovable credits are insufficient.
    """
    n_rows = len(normalized_features)
    logger.info("node=node_5_forecast status=start n_rows=%d", n_rows)

    try:
        use_credits(_CREDITS_COST, reason="node_5_forecast")
    except InsufficientCreditsError:
        logger.warning(
            "node=node_5_forecast status=skipped reason=insufficient_credits "
            "fallback=neutral_forecast"
        )
        return _neutral_forecast(n_rows)

    forecast_df = generate_forecast(weights, intercept, normalized_features)
    logger.info(
        "node=node_5_forecast status=end pred_mean=%.4f",
        float(forecast_df["pred"].mean()),
    )
    return forecast_df
