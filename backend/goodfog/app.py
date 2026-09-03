from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Settings
from .drive import DriveCache, build_drive_response, round_origin, validate_origin
from .poller import Poller
from .providers.open_meteo import OpenMeteoProvider
from .providers.ors import OrsProvider, RoutingError
from .viewpoints import VIEWPOINTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO line prints full request URLs (keys, addresses)
log = logging.getLogger(__name__)

DEST_POINTS = [(v.lat, v.lon) for v in VIEWPOINTS]


class DriveRequest(BaseModel):
    lat: float
    lon: float


def build_poller(settings: Settings, client: httpx.AsyncClient) -> Poller:
    provider = OpenMeteoProvider(DEST_POINTS, client, models=settings.open_meteo_models)
    features = {"drive": settings.ors_api_key is not None}
    return Poller(provider, settings.poll_minutes, settings.app_version, settings.commit, features=features)


def _unavailable() -> JSONResponse:
    return JSONResponse({"detail": "routing_unavailable"}, status_code=503)


def create_app(
    settings: Settings | None = None,
    poller: Poller | None = None,
    ors: OrsProvider | None = None,
    drive_cache: DriveCache | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = httpx.AsyncClient()
        app.state.poller = poller or build_poller(settings, client)
        if app.state.ors is None and settings.ors_api_key:
            app.state.ors = OrsProvider(client, settings.ors_api_key)
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
    app.state.ors = ors  # tests inject a fake; production builds one in lifespan when a key is set
    app.state.drive_cache = drive_cache or DriveCache()

    @app.get("/api/snapshot")
    async def snapshot():
        snap = app.state.poller.snapshot
        if snap is None:
            return JSONResponse({"status": "warming_up"}, status_code=503, headers={"Cache-Control": "no-cache"})
        return JSONResponse(snap, headers={"Cache-Control": "no-cache"})

    @app.get("/api/health")
    async def health():
        return app.state.poller.health()

    @app.get("/api/geocode")
    async def geocode(q: str = Query(..., min_length=1, max_length=200)):
        text = q.strip()
        if not text:
            return JSONResponse({"detail": "q must not be blank"}, status_code=422)
        provider = app.state.ors
        if provider is None:
            return _unavailable()
        try:
            place = await provider.geocode(text)
        except RoutingError as e:
            log.warning("geocode failed: %s", e)  # message carries status/type only, never the query
            return _unavailable()
        if place is None:
            return JSONResponse({"detail": "no_match"}, status_code=404)
        return {"label": place.label, "lat": place.lat, "lon": place.lon}

    @app.post("/api/drive")
    async def drive(req: DriveRequest):
        try:
            lat, lon = validate_origin(req.lat, req.lon)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=422)
        provider = app.state.ors
        if provider is None:
            return _unavailable()
        key = round_origin(lat, lon)
        now = time.monotonic()
        cached = app.state.drive_cache.get(key, now)
        if cached is not None:
            return cached
        try:
            legs = await provider.matrix(key, DEST_POINTS)
        except RoutingError as e:
            log.warning("drive lookup failed: %s", e)  # never log coordinates
            return _unavailable()
        body = build_drive_response(VIEWPOINTS, legs, key)
        app.state.drive_cache.put(key, body, now)
        return body

    return app


app = create_app()
