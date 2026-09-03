import asyncio
import json
from pathlib import Path

import httpx

from goodfog.app import build_poller, create_app
from goodfog.config import Settings
from goodfog.poller import Poller
from goodfog.providers.open_meteo import parse_open_meteo

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
