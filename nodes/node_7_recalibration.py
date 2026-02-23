"""Node 7: Monthly Recalibration.

Heavy node — consumes 1 Lovable credit per call.

Recalibrates Bayesian weights using recent user feedback.
user_feedback values:  0 = not accurate, 1 = somewhat accurate, 2 = accurate.

Bug fixes vs original:
  - Empty feedback array no longer produces NaN weights (raises ValueError).
  - accuracy_factor is floored at 0.1 to prevent full weight collapse
    (original code would zero all weights when accuracy_factor == 0).

Fallback when credits are insufficient:
  Returns original weights unchanged.
"""
import logging

import numpy as np

from lovable import InsufficientCreditsError, use_credits

logger = logging.getLogger(__name__)

_CREDITS_COST = 1
_MIN_ACCURACY_FACTOR = 0.1  # Floor: never zero out all weights.


def recalibrate_model(
    weights: np.ndarray,
    user_feedback: "list | np.ndarray",
) -> np.ndarray:
    """Recalibrate weights using user feedback.

    Args:
        weights:       Current weight array from the Bayesian node.
        user_feedback: Array-like of integers in {0, 1, 2}.

    Returns:
        Recalibrated weight array of the same shape.
    """
    feedback = np.asarray(user_feedback, dtype=np.float64).ravel()

    if len(feedback) == 0:
        raise ValueError("user_feedback is empty — cannot recalibrate")
    if not np.all((feedback >= 0) & (feedback <= 2)):
        raise ValueError("user_feedback values must be in {0, 1, 2}")

    raw = float(np.mean(feedback))
    # Map [0, 2] → [_MIN_ACCURACY_FACTOR, 1.0] to prevent weight collapse.
    accuracy_factor = np.clip(raw / 2.0, _MIN_ACCURACY_FACTOR, 1.0)

    recalibrated = np.asarray(weights, dtype=np.float64) * accuracy_factor
    logger.debug(
        "node=node_7_recalibration accuracy_factor=%.4f feedback_mean=%.4f",
        accuracy_factor,
        raw,
    )
    return recalibrated


def run(
    weights: np.ndarray,
    user_feedback: "list | np.ndarray",
) -> np.ndarray:
    """Return recalibrated weights.

    Skips and returns original weights when Lovable credits are insufficient.
    """
    logger.info("node=node_7_recalibration status=start n_feedback=%d", len(user_feedback))

    try:
        use_credits(_CREDITS_COST, reason="node_7_recalibration")
    except InsufficientCreditsError:
        logger.warning(
            "node=node_7_recalibration status=skipped reason=insufficient_credits "
            "fallback=original_weights"
        )
        return np.asarray(weights, dtype=np.float64)

    recalibrated = recalibrate_model(weights, user_feedback)
    logger.info("node=node_7_recalibration status=end weights_shape=%s", recalibrated.shape)
    return recalibrated
