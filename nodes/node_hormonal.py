"""Node C: Hormonal Phase Modifier (Flo-style cycle tracking).

Light node — no Lovable credits consumed.

Calculates menstrual cycle phase from the user's logged period start date.
Phase is used as a feature modifier in the Bayesian and forecast nodes.

Cycle phases (Flo model):
  menstrual   Day 1–5    Low oestrogen/progesterone. Lower energy, inward focus.
  follicular  Day 6–13   Rising oestrogen. Energy and mood lift, social openness.
  ovulatory   Day 14–16  Oestrogen peak. Highest energy, confidence, verbal fluency.
  luteal      Day 17–28  Progesterone rise then drop. Mood variability, fatigue,
                          sensitivity. PMS window typically day 24–28.

Research basis:
  Gudmundsson et al. (2023): HRV varies significantly across cycle phases.
  Soni et al. (2020): Oestrogen modulates serotonin receptor sensitivity.
  Baker & Driver (2007): Sleep quality degrades in late luteal phase.

Features returned:
  cycle_day           Current day in cycle (1-based)
  phase_menstrual     Binary 0/1
  phase_follicular    Binary 0/1
  phase_ovulatory     Binary 0/1
  phase_luteal        Binary 0/1
  luteal_late         Binary — 1 if day 24+ (PMS window)
  cycle_length        User's cycle length in days
"""
import logging
from datetime import date

logger = logging.getLogger(__name__)

_DEFAULT_CYCLE_LENGTH = 28
_DEFAULT_PERIOD_LENGTH = 5

# Phase boundaries (day of cycle, 1-based)
_PHASE_BOUNDS = {
    "menstrual":  (1, 5),
    "follicular": (6, 13),
    "ovulatory":  (14, 16),
    "luteal":     (17, 999),  # remainder of cycle
}


def calculate_phase(
    period_start: date,
    cycle_length: int = _DEFAULT_CYCLE_LENGTH,
    today: date | None = None,
) -> dict[str, float]:
    """Calculate cycle phase features for a given date.

    Args:
        period_start:  Date of most recent period start (from user log).
        cycle_length:  User's cycle length in days (default 28).
        today:         Date to calculate for (defaults to today).

    Returns:
        Dict of hormonal phase features for the feature matrix.
    """
    today = today or date.today()
    days_since = (today - period_start).days

    # Handle negative (period start in future) or very long gaps gracefully.
    if days_since < 0:
        logger.warning("node_hormonal period_start %s is in the future — using neutral", period_start)
        return _neutral_hormonal()

    # Normalise into current cycle.
    cycle_day = (days_since % cycle_length) + 1  # 1-based

    # Determine phase.
    phase = "luteal"
    for name, (start, end) in _PHASE_BOUNDS.items():
        if start <= cycle_day <= end:
            phase = name
            break

    features = {
        "cycle_day": float(cycle_day),
        "phase_menstrual": float(phase == "menstrual"),
        "phase_follicular": float(phase == "follicular"),
        "phase_ovulatory": float(phase == "ovulatory"),
        "phase_luteal": float(phase == "luteal"),
        "luteal_late": float(phase == "luteal" and cycle_day >= 24),
        "cycle_length": float(cycle_length),
    }

    logger.info(
        "node_hormonal status=end cycle_day=%d phase=%s luteal_late=%s",
        cycle_day, phase, bool(features["luteal_late"]),
    )
    return features


def _neutral_hormonal() -> dict[str, float]:
    """Returned when no cycle data is available (opted out or not logged yet)."""
    return {
        "cycle_day": 0.0,
        "phase_menstrual": 0.0,
        "phase_follicular": 0.0,
        "phase_ovulatory": 0.0,
        "phase_luteal": 0.0,
        "luteal_late": 0.0,
        "cycle_length": float(_DEFAULT_CYCLE_LENGTH),
    }


def run(
    period_start: date | None,
    cycle_length: int = _DEFAULT_CYCLE_LENGTH,
    today: date | None = None,
) -> dict[str, float]:
    """Return hormonal phase features.

    Returns neutral features if period_start is None (user opted out or
    hasn't logged yet — never crashes pipeline).
    """
    logger.info("node_hormonal status=start period_start=%s cycle_length=%d", period_start, cycle_length)

    if period_start is None:
        logger.info("node_hormonal status=skipped reason=no_cycle_data fallback=neutral")
        return _neutral_hormonal()

    return calculate_phase(period_start, cycle_length, today)
