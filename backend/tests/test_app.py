import asyncio
import json
from pathlib import Path

import httpx
import pytest

from goodfog.app import build_poller, create_app
from goodfog.config import Settings
from goodfog.drive import DailyBudget, DriveCache
from goodfog.poller import Poller
from goodfog.providers.open_meteo import parse_open_meteo
from goodfog.providers.ors import Leg, OrsProvider, Place, RoutingError
from goodfog.viewpoints import VIEWPOINTS

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())


class FakeProvider:
    async def fetch(self):
        return parse_open_meteo(FIXTURE, 8)


def _settings():
    return Settings(poll_minutes=15, open_meteo_models="best_match", app_version="0.1.0", commit="abc1234")


def _client(poller):
    app = create_app(_settings(), poller=poller)
    app.state.poller = poller  # lifespan does not run under ASGITransport
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


class FakePoller:
    def __init__(self):
        self.snapshot = None

    async def run_forever(self):
        await asyncio.Event().wait()

    def health(self):
        return {"status": "warming_up"}


async def test_lifespan_starts_and_stops_poller():
    fake = FakePoller()
    app = create_app(_settings(), poller=fake)

    async def run():
        async with app.router.lifespan_context(app):
            assert app.state.poller is fake

    await asyncio.wait_for(run(), timeout=5)


async def test_build_poller_configures_provider():
    settings = _settings()
    async with httpx.AsyncClient() as client:
        poller = build_poller(settings, client)
    assert isinstance(poller, Poller)
    assert len(poller.provider.points) == 8
    assert poller.provider.models == settings.open_meteo_models


async def test_snapshot_503_while_warming_up():
    poller = Poller(FakeProvider(), 15, "0.1.0", "abc1234")
    async with _client(poller) as c:
        r = await c.get("/api/snapshot")
    assert r.status_code == 503 and r.json() == {"status": "warming_up"}


async def test_snapshot_and_health_after_poll():
    poller = Poller(FakeProvider(), 15, "0.1.0", "abc1234")
    await poller.poll_once()
    async with _client(poller) as c:
        s = await c.get("/api/snapshot")
        h = await c.get("/api/health")
    assert s.status_code == 200
    assert s.headers["cache-control"] == "no-cache"
    assert len(s.json()["viewpoints"]) == 8
    assert h.status_code == 200
    body = h.json()
    assert body["status"] == "ok" and body["app_version"] == "0.1.0" and body["commit"] == "abc1234"
    assert body["stale"] is False


async def test_build_poller_sets_drive_feature_from_key():
    async with httpx.AsyncClient() as client:
        without = build_poller(_settings(), client)
        with_key = build_poller(
            Settings(poll_minutes=15, open_meteo_models="best_match", app_version="0.1.0", commit="abc1234", ors_api_key="k"),
            client,
        )
    assert without.features == {"drive": False}
    assert with_key.features == {"drive": True}


class FakeOrs:
    def __init__(self, legs=None, place="default", fail=False):
        self.legs = legs
        self.place = place
        self.fail = fail
        self.matrix_calls = 0
        self.geocode_calls = []

    async def geocode(self, text):
        self.geocode_calls.append(text)
        if self.fail:
            raise RoutingError("HTTP 500")
        if self.place == "default":
            return Place(label="Somewhere, CA, USA", lat=37.7, lon=-122.4)
        return self.place

    async def matrix(self, origin, dests):
        self.matrix_calls += 1
        if self.fail:
            raise RoutingError("HTTP 500")
        if self.legs is not None:
            return self.legs
        return [Leg(seconds=600 + 60 * i, meters=10000 + 1000 * i) for i in range(len(dests))]


def _drive_client(ors, cache=None, budget=None):
    poller = Poller(FakeProvider(), 15, "0.1.0", "abc1234")
    app = create_app(_settings(), poller=poller, ors=ors, drive_cache=cache, drive_budget=budget)
    app.state.poller = poller
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_drive_and_geocode_503_without_provider():
    async with _drive_client(None) as c:
        d = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
        g = await c.get("/api/geocode", params={"q": "sf"})
    assert d.status_code == 503 and d.json() == {"detail": "routing_unavailable"}
    assert g.status_code == 503 and g.json() == {"detail": "routing_unavailable"}


async def test_drive_returns_legs_and_caches_by_rounded_origin():
    ors = FakeOrs()
    async with _drive_client(ors, DriveCache()) as c:
        r1 = await c.post("/api/drive", json={"lat": 37.77491, "lon": -122.41942})
        r2 = await c.post("/api/drive", json={"lat": 37.77499, "lon": -122.41939})
    assert r1.status_code == 200
    body = r1.json()
    assert body["origin"] == {"lat": 37.775, "lon": -122.419}
    assert set(body["drives"]) == {v.id for v in VIEWPOINTS}
    assert body["drives"][VIEWPOINTS[0].id] == {"seconds": 600, "meters": 10000}
    assert r2.json() == body
    assert ors.matrix_calls == 1


async def test_drive_null_leg_and_upstream_failure():
    legs = [None] + [Leg(seconds=1, meters=1)] * 7
    async with _drive_client(FakeOrs(legs=legs)) as c:
        r = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
    assert r.status_code == 200 and r.json()["drives"][VIEWPOINTS[0].id] is None
    async with _drive_client(FakeOrs(fail=True)) as c:
        r = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
    assert r.status_code == 503 and r.json() == {"detail": "routing_unavailable"}


@pytest.mark.parametrize("body", [{"lat": 91, "lon": 0}, {"lat": 0, "lon": -181}, {"lat": "x", "lon": 0}, {"lon": 0}])
async def test_drive_rejects_bad_coordinates(body):
    ors = FakeOrs()
    async with _drive_client(ors) as c:
        r = await c.post("/api/drive", json=body)
    assert r.status_code == 422
    assert ors.matrix_calls == 0


async def test_geocode_ok_no_match_blank_long_and_failure():
    ors = FakeOrs()
    async with _drive_client(ors) as c:
        ok = await c.get("/api/geocode", params={"q": "  24th st  "})
        blank = await c.get("/api/geocode", params={"q": "   "})
        long = await c.get("/api/geocode", params={"q": "x" * 201})
    assert ok.status_code == 200 and ok.json() == {"label": "Somewhere, CA, USA", "lat": 37.7, "lon": -122.4}
    assert ors.geocode_calls == ["24th st"]
    assert blank.status_code == 422 and long.status_code == 422
    async with _drive_client(FakeOrs(place=None)) as c:
        r = await c.get("/api/geocode", params={"q": "zzz"})
    assert r.status_code == 404 and r.json() == {"detail": "no_match"}
    async with _drive_client(FakeOrs(fail=True)) as c:
        r = await c.get("/api/geocode", params={"q": "zzz"})
    assert r.status_code == 503


async def test_lifespan_builds_ors_only_when_key_set():
    fake = FakePoller()
    keyed = Settings(poll_minutes=15, open_meteo_models="best_match", app_version="0.1.0", commit="abc1234", ors_api_key="k")

    async def run(settings, expect_provider):
        app = create_app(settings, poller=fake)
        async with app.router.lifespan_context(app):
            if expect_provider:
                assert isinstance(app.state.ors, OrsProvider) and app.state.ors.api_key == "k"
            else:
                assert app.state.ors is None

    await asyncio.wait_for(run(keyed, True), timeout=5)
    await asyncio.wait_for(run(_settings(), False), timeout=5)


async def test_drive_503_when_daily_budget_exhausted_and_cache_still_serves():
    ors = FakeOrs()
    async with _drive_client(ors, DriveCache(), budget=DailyBudget(limit=1)) as c:
        ok = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
        cached = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
        blocked = await c.post("/api/drive", json={"lat": 37.8, "lon": -122.5})
    assert ok.status_code == 200 and cached.status_code == 200
    assert blocked.status_code == 503 and blocked.json() == {"detail": "routing_unavailable"}
    assert ors.matrix_calls == 1


async def test_drive_backs_off_after_upstream_failure():
    ors = FakeOrs(fail=True)
    async with _drive_client(ors) as c:
        r1 = await c.post("/api/drive", json={"lat": 37.7, "lon": -122.4})
        r2 = await c.post("/api/drive", json={"lat": 37.71, "lon": -122.41})
    assert r1.status_code == 503 and r2.status_code == 503
    assert ors.matrix_calls == 1  # second request short-circuited by the 30 s backoff
