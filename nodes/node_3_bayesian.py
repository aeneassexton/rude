"""Node 3: Bayesian Personal Weight Estimation.

Heavy node — consumes 2 Lovable credits per call.

Two estimation methods are supported:
  "map"  — Maximum A Posteriori (fast, deterministic, default for production).
  "mcmc" — Full MCMC sampling via PyMC (slower, used for research/recalibration).

Fallback when credits are insufficient:
  Returns (np.zeros(n_features), 0.0) — forecast will return pure-intercept output.
"""
import logging

import numpy as np
import pandas as pd

from lovable import InsufficientCreditsError, use_credits

logger = logging.getLogger(__name__)

_CREDITS_COST = 2


def bayesian_personalization(
    normalized_features: pd.DataFrame,
    target_mood: "np.ndarray | list",
    method: str = "map",
    random_seed: int = 42,
) -> tuple[np.ndarray, float]:
    import pymc as pm
    """Estimate personalised weights and intercept for mood prediction.

    Args:
        normalized_features: Min-max scaled feature DataFrame (N x F).
        target_mood:         Observed mood labels aligned with rows (length N).
        method:              "map" (default) or "mcmc".
        random_seed:         Seed for reproducibility.

    Returns:
        weights_est:   1-D array of shape (F,).
        intercept_est: Scalar float.
    """
    X = np.asarray(normalized_features, dtype=np.float64)
    y = np.asarray(target_mood, dtype=np.float64).ravel()

    if len(X) != len(y):
        raise ValueError(
            f"normalized_features rows ({len(X)}) must match target_mood length ({len(y)})"
        )
    if X.ndim != 2:
        raise ValueError(f"normalized_features must be 2-D, got shape {X.shape}")
    if np.isnan(X).any():
        raise ValueError("normalized_features contains NaN — check upstream normalization")
    if np.isnan(y).any():
        raise ValueError("target_mood contains NaN")

    n_features = X.shape[1]

    with pm.Model():
        weights = pm.Normal("weights", mu=0.0, sigma=1.0, shape=n_features)
        intercept = pm.Normal("intercept", mu=0.0, sigma=1.0)
        mu = intercept + pm.math.dot(X, weights)
        pm.Normal("obs", mu=mu, sigma=1.0, observed=y)

        if method == "mcmc":
            trace = pm.sample(
                500,
                tune=500,
                cores=1,
                progressbar=False,
                random_seed=random_seed,
            )
            weights_est = np.mean(trace.posterior["weights"].values, axis=(0, 1))
            intercept_est = float(np.mean(trace.posterior["intercept"].values))
        else:
            # MAP: fast point estimate, deterministic, viable for production.
            map_est = pm.find_MAP(seed=random_seed)
            weights_est = np.asarray(map_est["weights"], dtype=np.float64)
            intercept_est = float(map_est["intercept"])

    return weights_est, intercept_est


def run(
    normalized_features: pd.DataFrame,
    baseline_stats: pd.DataFrame,  # noqa: ARG001 — reserved for future prior construction
    target_mood: "np.ndarray | list",
    method: str = "map",
) -> tuple[np.ndarray, float]:
    """Return (weights, intercept).

    Skips and returns zero weights when Lovable credits are insufficient.
    """
    n_features = normalized_features.shape[1]
    logger.info("node=node_3_bayesian status=start method=%s n_features=%d", method, n_features)

    try:
        use_credits(_CREDITS_COST, reason="node_3_bayesian")
    except InsufficientCreditsError:
        logger.warning(
            "node=node_3_bayesian status=skipped reason=insufficient_credits fallback=zero_weights"
        )
        return np.zeros(n_features), 0.0

    weights, intercept = bayesian_personalization(normalized_features, target_mood, method=method)
    logger.info(
        "node=node_3_bayesian status=end weights_shape=%s intercept=%.4f",
        weights.shape,
        intercept,
    )
    return weights, intercept
