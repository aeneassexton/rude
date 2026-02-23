"""Node D: Environmental Context (Weather).

Light node — no Lovable credits consumed.

Fetches current-day weather from Open-Meteo (free, no API key).
Accepts latitude/longitude from the client (browser geolocation API).

Features returned:
  temperature_c       Current temperature in Celsius
  precipitation_mm    Precipitation in mm
  cloud_cover_pct     Cloud cover 0–100
  uv_index            UV index 0–11+
  daylight_hours      Computed from sunrise/sunset
  is_sunny            Binary: cloud_cover < 30 and precipitation == 0

Research basis:
  Seasonal Affective Disorder (SAD) literature links low light, low temperature
  and high precipitation to depressed mood and reduced HRV.
  UV index correlates with serotonin synthesis rates.
"""
import logging
from datetime import date

import requests

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT = 8


def fetch_weather(lat: float, lon: float, log_date: date | None = None) -> dict[str, float]:
    """Fetch weather features for a given location.

    Args:
        lat:      Latitude from browser geolocation.
        lon:      Longitude from browser geolocation.
        log_date: Date to fetch for (defaults to today).

    Returns:
        Dict of weather features ready to merge into the feature matrix.
        Falls back to neutral values on API failure — never crashes pipeline.
    """
    log_date = log_date or date.today()

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "uv_index_max",
            "sunshine_duration",    # seconds of sunshine
            "sunrise",
            "sunset",
        ],
        "current": ["cloud_cover"],
        "timezone": "auto",
        "start_date": str(log_date),
        "end_date": str(log_date),
    }

    try:
        resp = requests.get(_OPEN_METEO_URL, params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("node_environmental fetch failed lat=%.3f lon=%.3f: %s — using neutral values", lat, lon, exc)
        return _neutral_weather()

    try:
        daily = data["daily"]
        current = data.get("current", {})

        temp_max = float(daily["temperature_2m_max"][0] or 15.0)
        temp_min = float(daily["temperature_2m_min"][0] or 10.0)
        temperature_c = (temp_max + temp_min) / 2

        precipitation_mm = float(daily["precipitation_sum"][0] or 0.0)
        uv_index = float(daily["uv_index_max"][0] or 3.0)
        sunshine_seconds = float(daily["sunshine_duration"][0] or 21600)
        daylight_hours = round(sunshine_seconds / 3600, 1)

        cloud_cover_pct = float(current.get("cloud_cover") or 50.0)
        is_sunny = float(cloud_cover_pct < 30 and precipitation_mm == 0)

        features = {
            "temperature_c": round(temperature_c, 1),
            "precipitation_mm": round(precipitation_mm, 1),
            "cloud_cover_pct": round(cloud_cover_pct, 1),
            "uv_index": round(uv_index, 1),
            "daylight_hours": daylight_hours,
            "is_sunny": is_sunny,
        }
        logger.info(
            "node_environmental status=end temp=%.1f precip=%.1f uv=%.1f sunny=%s",
            temperature_c, precipitation_mm, uv_index, bool(is_sunny),
        )
        return features

    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("node_environmental parse error: %s — using neutral values", exc)
        return _neutral_weather()


def _neutral_weather() -> dict[str, float]:
    """Safe fallback when weather fetch fails."""
    return {
        "temperature_c": 15.0,
        "precipitation_mm": 0.0,
        "cloud_cover_pct": 50.0,
        "uv_index": 3.0,
        "daylight_hours": 12.0,
        "is_sunny": 0.0,
    }


def run(lat: float, lon: float, log_date: date | None = None) -> dict[str, float]:
    """Return weather feature dict for the given coordinates."""
    logger.info("node_environmental status=start lat=%.3f lon=%.3f", lat, lon)
    return fetch_weather(lat, lon, log_date)
