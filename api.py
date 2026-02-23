"""FastAPI HTTP wrapper for the Behavioural Forecasting Engine.

Exposes three endpoints that map directly to the three screens in the Lovable app:

  POST /mood/{user_id}          ← mood check-in screen (log today's mood)
  GET  /forecast/{user_id}      ← "The Week Ahead" forecast screen
  GET  /rhythm/{user_id}        ← "Your Rhythm" calendar screen

CORS is open (*) by default so Lovable's preview and production domains can call it.
Restrict CORS_ORIGINS via environment variable before going to production.

Usage:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
import os
from datetime import date, timedelta
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pipeline import run_pipeline, setup_logging
from store import MoodStore, WeatherStore, CycleStore, score_to_colour, score_to_label, mood_label_to_score
from nodes.node_environmental import run as run_environmental
from nodes.node_hormonal import run as run_hormonal

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Behavioural Forecasting Engine",
    version="1.0.0",
    description="Mood forecasting API for the BFE consumer app.",
)

# CORS — allow the Lovable preview + your custom domain.
# Set CORS_ORIGINS=https://yourapp.lovable.app in production.
_raw_origins = os.getenv("CORS_ORIGINS", "*")
_origins = [o.strip() for o in _raw_origins.split(",")] if _raw_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class MoodLogRequest(BaseModel):
    mood_label: str = Field(..., examples=["Radiant"], description="Mood label from UI wheel")
    log_date: Optional[str] = Field(
        None, examples=["2026-02-23"], description="ISO date string; defaults to today"
    )
    features: Optional[dict] = Field(
        None,
        description="Optional physiological features dict for this day. "
        "If omitted, mock values are used.",
    )


class DayForecast(BaseModel):
    day: str
    date: str
    mood_score: float
    mood_label: str
    colour: str
    ci_lower: float
    ci_upper: float


class ForecastResponse(BaseModel):
    user_id: str
    week: list[DayForecast]
    pattern: str
    trend: str
    alert: bool
    credits_remaining: int


class RhythmDay(BaseModel):
    date: str
    mood_label: str
    mood_score: float
    colour: str
    is_today: bool


class RhythmResponse(BaseModel):
    user_id: str
    month: str
    history: list[RhythmDay]


class MoodLogResponse(BaseModel):
    success: bool
    date: str
    mood_label: str
    mood_score: float


class WeatherLogRequest(BaseModel):
    lat: float = Field(..., description="Latitude from device location")
    lon: float = Field(..., description="Longitude from device location")
    log_date: Optional[str] = None


class WeatherLogResponse(BaseModel):
    success: bool
    date: str
    temperature_c: float
    is_sunny: bool
    uv_index: float
    daylight_hours: float


class CycleLogRequest(BaseModel):
    period_start: str = Field(..., examples=["2026-02-10"], description="ISO date of period start")
    cycle_length: int = Field(default=28, ge=21, le=45)


class CycleLogResponse(BaseModel):
    success: bool
    period_start: str
    cycle_length: int
    current_phase: str
    cycle_day: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_week_forecasts(
    user_id: str,
    store: MoodStore,
    bayesian_method: str = "map",
) -> tuple[list[DayForecast], bool, int]:
    """Run the BFE pipeline and build 7 DayForecast objects.

    Returns (week, alert_flag, credits_remaining).
    """
    import lovable as lv

    mood_log = store.load_mood_log()
    target_mood: np.ndarray | None = None
    if not mood_log.empty:
        target_mood = mood_log["mood_score"].values

    result = run_pipeline(
        user_id=user_id,
        target_mood=target_mood,
        use_mock_ingestion=True,  # swap to False when live Apple Health is ready
        bayesian_method=bayesian_method,
    )

    weights = result["weights"]
    intercept = result["intercept"]
    norm_features = result["normalized_features"]

    # Generate one forecast per day for the next 7 days.
    # We use today's normalised features as a proxy for each future day
    # (real multi-day lookahead requires multi-step forecasting — future work).
    today_row = norm_features.iloc[[-1]]
    week: list[DayForecast] = []
    base_date = date.today()

    for i in range(7):
        day_date = base_date + timedelta(days=i)
        day_name = day_date.strftime("%a")  # Mon, Tue, …

        # Add small synthetic perturbation per day so the week isn't flat.
        rng = np.random.default_rng(seed=42 + i)
        perturbed = today_row.copy()
        perturbed += rng.normal(0, 0.05, size=perturbed.shape)
        perturbed = perturbed.clip(0, 1)

        from nodes.node_5_forecast import generate_forecast
        try:
            fc = generate_forecast(weights, intercept, perturbed)
            pred = float(np.clip(fc["pred"].iloc[0], 1.0, 10.0))
            ci_lower = float(np.clip(fc["ci_lower"].iloc[0], 1.0, 10.0))
            ci_upper = float(np.clip(fc["ci_upper"].iloc[0], 1.0, 10.0))
        except Exception:
            pred, ci_lower, ci_upper = 5.0, 3.5, 6.5

        week.append(
            DayForecast(
                day=day_name,
                date=str(day_date),
                mood_score=round(pred, 2),
                mood_label=score_to_label(pred),
                colour=score_to_colour(pred),
                ci_lower=round(ci_lower, 2),
                ci_upper=round(ci_upper, 2),
            )
        )

    return week, bool(result["alert_flag"]), lv.context.credits


def _derive_pattern(mood_log: "import pandas as pd; pd.DataFrame") -> str:  # type: ignore
    """Very simple pattern insight from mood history."""
    import pandas as pd

    if mood_log.empty or len(mood_log) < 5:
        return "Keep logging to unlock your first pattern insight."

    scores = mood_log["mood_score"].values
    if scores[-3:].mean() > scores[:-3].mean():
        return "Your mood has been trending upward recently."
    if scores[-3:].mean() < scores[:-3].mean():
        return "Your energy has been lower than usual lately — rest may help."
    return "Your mood has been steady and consistent."


def _derive_trend(mood_log: "import pandas as pd; pd.DataFrame") -> str:  # type: ignore
    if mood_log.empty or len(mood_log) < 3:
        return "Not enough data yet — keep logging daily."
    top = mood_log.nlargest(3, "mood_score")["mood_label"].mode()
    label = top.iloc[0].capitalize() if not top.empty else "positive"
    return f"You've been most {label} on recent high-energy days."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/mood/{user_id}", response_model=MoodLogResponse)
def log_mood(user_id: str, body: MoodLogRequest):
    """Log today's mood from the check-in wheel.

    Called by the 'How are you feeling?' screen after the user selects a mood.
    """
    store = MoodStore(user_id)
    log_date: date = date.today()
    if body.log_date:
        try:
            log_date = date.fromisoformat(body.log_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="log_date must be ISO format YYYY-MM-DD")

    store.append_mood(body.mood_label, log_date=log_date)

    if body.features:
        store.append_features(body.features)

    score = mood_label_to_score(body.mood_label)
    return MoodLogResponse(
        success=True,
        date=str(log_date),
        mood_label=body.mood_label.lower(),
        mood_score=score,
    )


@app.get("/forecast/{user_id}", response_model=ForecastResponse)
def get_forecast(user_id: str, method: str = "map"):
    """Return the week-ahead forecast.

    Called by the 'The Week Ahead' screen.
    `method` can be 'map' (fast) or 'mcmc' (accurate, slower).
    """
    store = MoodStore(user_id)
    mood_log = store.load_mood_log()

    try:
        week, alert, credits = _build_week_forecasts(user_id, store, bayesian_method=method)
    except Exception as exc:
        logger.error("forecast error user=%s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    pattern = _derive_pattern(mood_log)
    trend = _derive_trend(mood_log)

    return ForecastResponse(
        user_id=user_id,
        week=week,
        pattern=pattern,
        trend=trend,
        alert=alert,
        credits_remaining=credits,
    )


@app.get("/rhythm/{user_id}", response_model=RhythmResponse)
def get_rhythm(user_id: str, year: int = 0, month: int = 0):
    """Return the full mood history for the calendar view.

    Called by the 'Your Rhythm' screen.
    year/month default to the current month if not provided.
    """
    store = MoodStore(user_id)
    mood_log = store.load_mood_log()

    today = date.today()
    year = year or today.year
    month = month or today.month
    month_str = date(year, month, 1).strftime("%B %Y").upper()

    history: list[RhythmDay] = []
    if not mood_log.empty:
        for _, row in mood_log.iterrows():
            try:
                d = date.fromisoformat(str(row["date"]))
            except ValueError:
                continue
            if d.year != year or d.month != month:
                continue
            history.append(
                RhythmDay(
                    date=str(d),
                    mood_label=str(row["mood_label"]).capitalize(),
                    mood_score=float(row["mood_score"]),
                    colour=score_to_colour(float(row["mood_score"])),
                    is_today=(d == today),
                )
            )

    return RhythmResponse(user_id=user_id, month=month_str, history=history)


@app.post("/weather/{user_id}", response_model=WeatherLogResponse)
def log_weather(user_id: str, body: WeatherLogRequest):
    """Fetch and store weather for the user's location.

    Called by the iOS app on launch with CoreLocation lat/lng.
    Automatically fetches from Open-Meteo — no user input needed.
    """
    log_date = date.today()
    if body.log_date:
        try:
            log_date = date.fromisoformat(body.log_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="log_date must be YYYY-MM-DD")

    features = run_environmental(lat=body.lat, lon=body.lon, log_date=log_date)
    WeatherStore(user_id).append_weather(features, lat=body.lat, lon=body.lon, log_date=log_date)

    return WeatherLogResponse(
        success=True,
        date=str(log_date),
        temperature_c=features["temperature_c"],
        is_sunny=bool(features["is_sunny"]),
        uv_index=features["uv_index"],
        daylight_hours=features["daylight_hours"],
    )


@app.post("/cycle/{user_id}", response_model=CycleLogResponse)
def log_cycle(user_id: str, body: CycleLogRequest):
    """Log a period start date (Flo-style cycle tracking).

    Called when the user marks a period start in the app.
    System auto-calculates current phase and injects it into the forecast.
    """
    try:
        period_start = date.fromisoformat(body.period_start)
    except ValueError:
        raise HTTPException(status_code=422, detail="period_start must be YYYY-MM-DD")

    CycleStore(user_id).log_period(period_start, cycle_length=body.cycle_length)
    phase_features = run_hormonal(period_start=period_start, cycle_length=body.cycle_length)

    phase = next(
        (k.replace("phase_", "") for k in phase_features
         if k.startswith("phase_") and phase_features[k] == 1.0),
        "luteal",
    )

    return CycleLogResponse(
        success=True,
        period_start=str(period_start),
        cycle_length=body.cycle_length,
        current_phase=phase,
        cycle_day=int(phase_features["cycle_day"]),
    )


@app.get("/", include_in_schema=False)
def root():
    """Redirect root to interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    """Liveness probe — used by Render/Railway/Fly.io."""
    return {"status": "ok"}


@app.get("/status")
def status():
    """Shows which storage backend is active. Safe to call — no secrets exposed."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    backend = "supabase" if (supabase_url and supabase_key) else "parquet (no Supabase env vars)"
    return {
        "backend": backend,
        "supabase_url_set": bool(supabase_url),
        "supabase_key_set": bool(supabase_key),
    }
