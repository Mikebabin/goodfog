from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..fog import Hour, hour_from_values
from . import ProviderError

URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = (
    "cloudcover_low,cloudcover_mid,cloudcover_high,windspeed_10m,"
    "precipitation_probability,temperature_2m,dewpoint_2m"
)
FORECAST_DAYS = 4  # day-3 sunset needs an hourly row on the fourth calendar day


@dataclass(frozen=True)
class Forecast:
    hourly_time: tuple[str, ...]
    hourly: dict[str, tuple]
    sunrise: tuple[str, ...]
    sunset: tuple[str, ...]

    def hour_at(self, iso_hour: str) -> Hour | None:
        try:
            i = self.hourly_time.index(iso_hour)
        except ValueError:
            return None
        h = self.hourly
        return hour_from_values(
            h["temperature_2m"][i], h["dewpoint_2m"][i],
            low=h["cloudcover_low"][i], mid=h["cloudcover_mid"][i], high=h["cloudcover_high"][i],
            wind_kmh=float(h["windspeed_10m"][i] or 0.0), rain=h["precipitation_probability"][i],
        )


def _parse_one(obj: dict) -> Forecast:
    try:
        hourly = obj["hourly"]
        daily = obj["daily"]
        return Forecast(
            hourly_time=tuple(hourly["time"]),
            hourly={k: tuple(hourly[k]) for k in HOURLY_VARS.split(",")},
            sunrise=tuple(daily["sunrise"]),
            sunset=tuple(daily["sunset"]),
        )
    except (KeyError, TypeError) as e:
        raise ProviderError(f"malformed Open-Meteo payload: {e!r}") from e


def parse_open_meteo(payload, expected_points: int) -> list[Forecast]:
    objs = [payload] if isinstance(payload, dict) else list(payload)
    if len(objs) != expected_points:
        raise ProviderError(f"expected {expected_points} points, got {len(objs)}")
    return [_parse_one(o) for o in objs]


def request_params(points: list[tuple[float, float]], models: str) -> dict[str, str]:
    """The exact query the provider sends; scripts/fetch_fixture.py reuses it so the fixture cannot drift."""
    return {
        "latitude": ",".join(str(lat) for lat, _ in points),
        "longitude": ",".join(str(lon) for _, lon in points),
        "hourly": HOURLY_VARS,
        "daily": "sunrise,sunset",
        "timezone": "America/Los_Angeles",
        "forecast_days": str(FORECAST_DAYS),
        "models": models,
    }


class OpenMeteoProvider:
    name = "open_meteo"

    def __init__(self, points: list[tuple[float, float]], client: httpx.AsyncClient, models: str) -> None:
        self.points = points
        self.client = client
        self.models = models

    async def fetch(self) -> list[Forecast]:
        params = request_params(self.points, self.models)
        try:
            r = await self.client.get(URL, params=params, timeout=15.0)
            r.raise_for_status()
            return parse_open_meteo(r.json(), len(self.points))
        except httpx.HTTPError as e:
            raise ProviderError(f"Open-Meteo request failed: {e!r}") from e
