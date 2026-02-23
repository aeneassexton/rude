"""Node 4: Gradient Boosted Feature Refinement.

Heavy node — consumes 1 Lovable credit per call.

Fallback when credits are insufficient:
  Returns uniform feature importances (1/n_features for each feature).
  Downstream forecast remains valid; importances are only advisory.
"""
import logging

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from lovable import InsufficientCreditsError, use_credits

logger = logging.getLogger(__name__)

_CREDITS_COST = 1
_MIN_SAMPLES = 2  # XGBoost requires at least 2 samples


def gradient_boost_refinement(
    normalized_features: pd.DataFrame,
    target_mood: "np.ndarray | list",
    *,
    n_estimators: int = 100,
    max_depth: int = 3,
) -> np.ndarray:
    """Return feature importances aligned with normalized_features columns.

    Args:
        normalized_features: Min-max scaled feature DataFrame (N x F).
        target_mood:         Observed mood labels aligned with rows (length N).
        n_estimators:        Number of boosting rounds.
        max_depth:           Maximum tree depth.

    Returns:
        importances: 1-D array of shape (F,) summing to 1.0.
    """
    X = np.asarray(normalized_features, dtype=np.float64)
    y = np.asarray(target_mood, dtype=np.float64).ravel()

    if len(X) != len(y):
        raise ValueError(
            f"normalized_features rows ({len(X)}) must match target_mood length ({len(y)})"
        )
    if len(X) < _MIN_SAMPLES:
        raise ValueError(
            f"gradient_boost_refinement requires at least {_MIN_SAMPLES} samples; got {len(X)}"
        )
    if np.isnan(X).any():
        raise ValueError("normalized_features contains NaN")

    model = XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    model.fit(X, y)
    return model.feature_importances_


def run(
    normalized_features: pd.DataFrame,
    target_mood: "np.ndarray | list",
) -> np.ndarray:
    """Return refined_importance array.

    Skips and returns uniform importances when Lovable credits are insufficient
    or when the history window is too short for XGBoost.
    """
    n_features = normalized_features.shape[1]
    logger.info("node=node_4_gradient_boost status=start n_features=%d", n_features)

    try:
        use_credits(_CREDITS_COST, reason="node_4_gradient_boost")
    except InsufficientCreditsError:
        logger.warning(
            "node=node_4_gradient_boost status=skipped reason=insufficient_credits "
            "fallback=uniform_importance"
        )
        return np.ones(n_features) / n_features

    n_samples = len(normalized_features)
    if n_samples < _MIN_SAMPLES:
        logger.warning(
            "node=node_4_gradient_boost status=skipped reason=insufficient_samples "
            "n_samples=%d fallback=uniform_importance",
            n_samples,
        )
        return np.ones(n_features) / n_features

    importances = gradient_boost_refinement(normalized_features, target_mood)
    logger.info(
        "node=node_4_gradient_boost status=end importances=%s",
        np.round(importances, 4).tolist(),
    )
    return importances
