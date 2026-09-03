from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from .snapshot import build_snapshot
from .viewpoints import VIEWPOINTS

log = logging.getLogger(__name__)

STALE_AFTER_POLLS = 3


class Poller:
    def __init__(self, provider, poll_minutes: int, app_version: str, commit: str, features: dict | None = None) -> None:
        self.provider = provider
        self.interval = timedelta(minutes=poll_minutes)
        self.app_version = app_version
        self.commit = commit
        self.features = dict(features or {})
        self.snapshot: dict | None = None
        self.generated_at: datetime | None = None
        self.last_error: str | None = None

    async def poll_once(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        try:
            forecasts = await self.provider.fetch()
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"
            log.exception("poll failed, keeping previous snapshot")
            return
        self.snapshot = build_snapshot(
            VIEWPOINTS, forecasts, now=now, app_version=self.app_version, commit=self.commit, features=self.features
        )
        self.generated_at = now
        self.last_error = None
        log.info("snapshot updated")

    async def run_forever(self) -> None:
        while True:
            try:
                await self.poll_once()
            except Exception:  # never let the loop die
                log.exception("unexpected poll error")
            await asyncio.sleep(self.interval.total_seconds())

    def health(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        stale = self.generated_at is None or now - self.generated_at > STALE_AFTER_POLLS * self.interval
        return {
            "status": "ok" if self.snapshot is not None else "warming_up",
            "app_version": self.app_version,
            "commit": self.commit,
            "generated_at": self.generated_at.isoformat(timespec="seconds") if self.generated_at else None,
            "stale": stale,
            "last_error": self.last_error,
            "drive": bool(self.features.get("drive", False)),
        }
