from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .poller import Poller
from .providers.open_meteo import OpenMeteoProvider
from .viewpoints import VIEWPOINTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def build_poller(settings: Settings, client: httpx.AsyncClient) -> Poller:
    provider = OpenMeteoProvider([(v.lat, v.lon) for v in VIEWPOINTS], client, models=settings.open_meteo_models)
    features = {"drive": settings.ors_api_key is not None}
    return Poller(provider, settings.poll_minutes, settings.app_version, settings.commit, features=features)


def create_app(settings: Settings | None = None, poller: Poller | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = httpx.AsyncClient()
        app.state.poller = poller or build_poller(settings, client)
        task = asyncio.create_task(app.state.poller.run_forever())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await client.aclose()

    app = FastAPI(title="Good Fog", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    @app.get("/api/snapshot")
    async def snapshot():
        snap = app.state.poller.snapshot
        if snap is None:
            return JSONResponse({"status": "warming_up"}, status_code=503, headers={"Cache-Control": "no-cache"})
        return JSONResponse(snap, headers={"Cache-Control": "no-cache"})

    @app.get("/api/health")
    async def health():
        return app.state.poller.health()

    return app


app = create_app()
