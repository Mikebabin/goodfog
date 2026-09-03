import json
from pathlib import Path

import httpx
import pytest
import respx

from goodfog.providers.ors import GEOCODE_URL, MATRIX_URL, Leg, OrsProvider, Place, RoutingError
from goodfog.viewpoints import VIEWPOINTS

FIX = Path(__file__).parent / "fixtures"
GEOCODE = json.loads((FIX / "ors_geocode.json").read_text())
MATRIX = json.loads((FIX / "ors_matrix.json").read_text())
ORIGIN = (37.7749, -122.4194)
DESTS = [(v.lat, v.lon) for v in VIEWPOINTS]


@respx.mock
async def test_geocode_returns_first_place_with_focus_and_country():
    route = respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json=GEOCODE))
    async with httpx.AsyncClient() as client:
        place = await OrsProvider(client, "test-key").geocode("san francisco")
    assert place == Place(label="San Francisco, CA, USA", lat=37.7749, lon=-122.4194)
    q = route.calls.last.request.url.params
    assert q["api_key"] == "test-key" and q["text"] == "san francisco" and q["size"] == "1"
    assert q["focus.point.lat"] == "37.83" and q["focus.point.lon"] == "-122.48"
    assert q["boundary.country"] == "US"


@respx.mock
async def test_geocode_empty_features_is_none():
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": []}))
    async with httpx.AsyncClient() as client:
        assert await OrsProvider(client, "k").geocode("zzzz") is None


@respx.mock
async def test_geocode_http_error_raises():
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(401, json={"error": "bad key"}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError, match="HTTP 401"):
            await OrsProvider(client, "k").geocode("x")


@respx.mock
async def test_geocode_malformed_raises():
    respx.get(GEOCODE_URL).mock(return_value=httpx.Response(200, json={"features": [{"geometry": {}}]}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError):
            await OrsProvider(client, "k").geocode("x")


@respx.mock
async def test_matrix_returns_legs_in_order_with_none_for_null():
    route = respx.post(MATRIX_URL).mock(return_value=httpx.Response(200, json=MATRIX))
    async with httpx.AsyncClient() as client:
        legs = await OrsProvider(client, "test-key").matrix(ORIGIN, DESTS)
    assert len(legs) == 8
    assert legs[0] == Leg(seconds=1540, meters=14830)
    assert legs[5] is None
    assert legs[7] == Leg(seconds=2601, meters=35000)
    req = route.calls.last.request
    assert req.headers["authorization"] == "test-key"
    body = json.loads(req.content)
    assert body["locations"][0] == [-122.4194, 37.7749]  # ORS wants [lon, lat]
    assert body["locations"][1] == [VIEWPOINTS[0].lon, VIEWPOINTS[0].lat]
    assert body["sources"] == [0] and body["destinations"] == list(range(1, 9))
    assert body["metrics"] == ["duration", "distance"]


@respx.mock
async def test_matrix_wrong_leg_count_raises():
    respx.post(MATRIX_URL).mock(return_value=httpx.Response(200, json={"durations": [[1.0]], "distances": [[1.0]]}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError):
            await OrsProvider(client, "k").matrix(ORIGIN, DESTS)


@respx.mock
async def test_matrix_network_error_raises_without_leaking_key():
    respx.post(MATRIX_URL).mock(side_effect=httpx.ConnectTimeout("slow"))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RoutingError) as ei:
            await OrsProvider(client, "secret-key").matrix(ORIGIN, DESTS)
    assert "secret-key" not in str(ei.value)
