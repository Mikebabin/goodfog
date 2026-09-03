import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from goodfog import poller as poller_module
from goodfog.poller import Poller
from goodfog.providers import ProviderError
from goodfog.providers.open_meteo import parse_open_meteo

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "open_meteo.json").read_text())
T0 = datetime(2026, 9, 2, 23, 0, tzinfo=timezone.utc)


class FakeProvider:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    async def fetch(self):
        self.calls += 1
        if self.fail:
            raise ProviderError("boom")
        return parse_open_meteo(FIXTURE, 8)


async def test_poll_once_builds_snapshot():
    p = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    assert p.snapshot is None
    await p.poll_once(now=T0)
    assert p.snapshot["app_version"] == "0.1.0"
    assert p.generated_at == T0
    assert p.last_error is None


async def test_failure_keeps_previous_snapshot_and_records_error():
    prov = FakeProvider()
    p = Poller(prov, poll_minutes=15, app_version="0.1.0", commit="dev")
    await p.poll_once(now=T0)
    prov.fail = True
    await p.poll_once(now=T0 + timedelta(minutes=15))
    assert p.snapshot is not None and p.generated_at == T0
    assert "boom" in p.last_error


async def test_short_daily_block_surfaces_as_provider_error_and_keeps_snapshot():
    class ShortDailyProvider:
        async def fetch(self):
            payload = json.loads(json.dumps(FIXTURE))
            payload[0]["daily"]["sunset"] = payload[0]["daily"]["sunset"][:3]
            return parse_open_meteo(payload, 8)

    p = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    await p.poll_once(now=T0)
    prev_snapshot = p.snapshot

    p.provider = ShortDailyProvider()
    await p.poll_once(now=T0 + timedelta(minutes=15))

    assert p.snapshot is prev_snapshot
    assert p.generated_at == T0
    assert p.last_error is not None and p.last_error.startswith("ProviderError")


async def test_poll_once_records_non_provider_exception():
    class BadProvider:
        async def fetch(self):
            raise RuntimeError("bad")

    p = Poller(BadProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    p.snapshot = {"prev": True}
    p.generated_at = T0
    await p.poll_once(now=T0 + timedelta(minutes=15))
    assert p.snapshot == {"prev": True}
    assert p.generated_at == T0
    assert p.last_error is not None and "RuntimeError" in p.last_error
    assert p.health(now=T0)["last_error"] == p.last_error


async def test_run_forever_survives_failing_poll_once(monkeypatch):
    class FlakyProvider:
        def __init__(self):
            self.calls = 0

        async def fetch(self):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom")
            return parse_open_meteo(FIXTURE, 8)

    provider = FlakyProvider()
    p = Poller(provider, poll_minutes=15, app_version="0.1.0", commit="dev")

    sleep_calls = 0

    async def fake_sleep(seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(poller_module.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await p.run_forever()

    assert provider.calls == 2
    assert p.snapshot is not None


async def test_health_stale_after_three_missed_polls():
    p = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    h = p.health(now=T0)
    assert h["status"] == "warming_up" and h["stale"] is True
    await p.poll_once(now=T0)
    assert p.health(now=T0 + timedelta(minutes=44))["stale"] is False
    assert p.health(now=T0 + timedelta(minutes=46))["stale"] is True
    h = p.health(now=T0)
    assert h["status"] == "ok" and h["app_version"] == "0.1.0" and h["generated_at"] == T0.isoformat(timespec="seconds")


async def test_poller_passes_features_to_snapshot_and_health():
    p = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev", features={"drive": True})
    await p.poll_once(now=T0)
    assert p.snapshot["features"] == {"drive": True}
    assert p.health(now=T0)["drive"] is True
    plain = Poller(FakeProvider(), poll_minutes=15, app_version="0.1.0", commit="dev")
    assert plain.health(now=T0)["drive"] is False
