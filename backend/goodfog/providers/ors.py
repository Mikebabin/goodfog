"""OpenRouteService client: Pelias geocoding and a driving-car duration/distance matrix.

Coordinates are (lat, lon) everywhere in goodfog; ORS speaks [lon, lat], so the flip happens
only inside this module. Error messages carry status codes / exception names only — never the
key, the query text, or coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from . import ProviderError

BASE = "https://api.openrouteservice.org"
GEOCODE_URL = f"{BASE}/geocode/search"
MATRIX_URL = f"{BASE}/v2/matrix/driving-car"
FOCUS_LAT = 37.83   # Golden Gate: biases ambiguous addresses toward SF/Marin
FOCUS_LON = -122.48
TIMEOUT_S = 10.0


class RoutingError(ProviderError):
    """ORS request failed or returned an unexpected shape."""


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Leg:
    seconds: int
    meters: int


class OrsProvider:
    def __init__(self, client: httpx.AsyncClient, api_key: str) -> None:
        self.client = client
        self.api_key = api_key

    async def geocode(self, text: str) -> Place | None:
        params = {
            "api_key": self.api_key,
            "text": text,
            "size": 1,
            "focus.point.lat": FOCUS_LAT,
            "focus.point.lon": FOCUS_LON,
            "boundary.country": "US",
        }
        body = await self._request("GET", GEOCODE_URL, params=params)
        try:
            features = body["features"]
            if not features:
                return None
            f = features[0]
            lon, lat = f["geometry"]["coordinates"][:2]
            return Place(label=str(f["properties"]["label"]), lat=float(lat), lon=float(lon))
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise RoutingError(f"malformed geocode response: {type(e).__name__}") from e

    async def matrix(self, origin: tuple[float, float], dests: list[tuple[float, float]]) -> list[Leg | None]:
        locations = [[origin[1], origin[0]]] + [[lon, lat] for lat, lon in dests]
        payload = {
            "locations": locations,
            "sources": [0],
            "destinations": list(range(1, len(locations))),
            "metrics": ["duration", "distance"],
        }
        body = await self._request("POST", MATRIX_URL, json=payload, headers={"Authorization": self.api_key})
        try:
            durations = body["durations"][0]
            distances = body["distances"][0]
        except (KeyError, IndexError, TypeError) as e:
            raise RoutingError(f"malformed matrix response: {type(e).__name__}") from e
        if len(durations) != len(dests) or len(distances) != len(dests):
            raise RoutingError("matrix returned wrong number of legs")
        try:
            return [
                None if d is None or m is None else Leg(seconds=int(round(d)), meters=int(round(m)))
                for d, m in zip(durations, distances, strict=True)
            ]
        except (TypeError, ValueError) as e:
            raise RoutingError(f"malformed matrix cell: {type(e).__name__}") from e

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            r = await self.client.request(method, url, timeout=TIMEOUT_S, **kwargs)
        except httpx.HTTPError as e:
            raise RoutingError(type(e).__name__) from e
        if r.status_code != 200:
            raise RoutingError(f"HTTP {r.status_code}")
        try:
            body = r.json()
        except ValueError as e:
            raise RoutingError("non-JSON response") from e
        if not isinstance(body, dict):
            raise RoutingError("unexpected response shape")
        return body
