"""The LIVE local-GPU API (ADR-0057 Lane C, ACTIVE) + read-only artifact serving.

Run it next to your GPU:  uvicorn app.main:app --port 8000
- GET  /api/live/health           which engines can run here (CUDA detection)
- POST /api/live/reconstruct      real-time reconstruction of YOUR footage (Estela / rgbd-sensor / depth-icp / lingbot)
- GET  /api/cases ...             the committed artifacts, read-only
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import Settings, origins
from .routers import content, live


def create_app() -> FastAPI:
    s = Settings()
    app = FastAPI(title="Lidar 3D local-GPU API", version="0.13.006")
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins(s) or ["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(content.router)
    app.include_router(live.router)

    @app.get("/health")
    @app.get("/healthz")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
