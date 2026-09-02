import json
from pathlib import Path

import httpx
import pytest
import respx

from goodfog.providers import ProviderError
from goodfog.providers.open_meteo import URL, OpenMeteoProvider, parse_open_meteo
from goodfog.viewpoints import VIEWPOINTS

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())


def test_parse_maps_by_index_and_exposes_daily():
    fcs = parse_open_meteo(FIXTURE, expected_points=8)
    assert len(fcs) == 8
    f = fcs[0]
    assert len(f.hourly_time) == 72
    assert len(f.sunrise) == 3 and len(f.sunset) == 3
    assert f.sunset[0].startswith(f.hourly_time[0][:10])  # same local day


def test_hour_at_returns_hour_or_none():
    f = parse_open_meteo(FIXTURE, expected_points=8)[7]
    key = f.hourly_time[20]
    h = f.hour_at(key)
    assert h is not None
    assert 0 <= h.low_cloud <= 100
    assert f.hour_at("1999-01-01T00:00") is None


def test_hour_at_handles_null_dewpoint():
    payload = json.loads(json.dumps(FIXTURE[:1]))
    payload[0]["hourly"]["dewpoint_2m"][5] = None
    payload[0]["hourly"]["cloudcover_low"][5] = None
    f = parse_open_meteo(payload, expected_points=1)[0]
    h = f.hour_at(f.hourly_time[5])
    assert h.lcl_ft is None and h.dewpoint_f is None and h.low_cloud == 0


def test_parse_rejects_wrong_count_and_malformed():
    with pytest.raises(ProviderError):
        parse_open_meteo(FIXTURE[:3], expected_points=8)
    with pytest.raises(ProviderError):
        parse_open_meteo([{"hourly": {}}], expected_points=1)


@respx.mock
async def test_fetch_builds_multi_point_query():
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=FIXTURE))
    async with httpx.AsyncClient() as client:
        p = OpenMeteoProvider([(v.lat, v.lon) for v in VIEWPOINTS], client, models="best_match")
        fcs = await p.fetch()
    assert len(fcs) == 8
    q = route.calls.last.request.url.params
    assert q["latitude"] == ",".join(str(v.lat) for v in VIEWPOINTS)
    assert q["timezone"] == "America/Los_Angeles"
    assert q["forecast_days"] == "3"
    assert q["models"] == "best_match"
    assert "dewpoint_2m" in q["hourly"]


@respx.mock
async def test_fetch_http_error_is_provider_error():
    respx.get(URL).mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as client:
        p = OpenMeteoProvider([(1.0, 2.0)], client, models="best_match")
        with pytest.raises(ProviderError):
            await p.fetch()
