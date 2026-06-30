"""FastAPI server for the Lidar 3D workbench.

REST: list sources / config. WebSocket /ws/stream: client sends {source_id, params}; server
runs the real engine on the local GPU in a background thread and pushes one JSON message per
frame as it is computed (live). One GPU run at a time (8 GB) via an async lock.
"""
from __future__ import annotations
import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.engines import registry

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(title="Lidar 3D — streaming reconstruction workbench")
_gpu_lock = asyncio.Lock()


@app.get("/api/health")
async def health():
    import torch
    return {
        "ok": True,
        "cuda": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "checkpoint": str(config.checkpoint_path()),
        "checkpoint_present": config.checkpoint_path().exists(),
    }


@app.get("/api/sources")
async def sources():
    return {"sources": registry.list_sources()}


@app.get("/api/config")
async def get_config():
    d = config.DEFAULTS
    return {
        "defaults": {
            "max_frames": d.max_frames, "decimation": d.point_decimation,
            "conf_quantile": d.conf_quantile, "kv_window": d.kv_cache_sliding_window,
            "image_size": d.image_size, "scale_frames": d.num_scale_frames,
        }
    }


@app.websocket("/ws/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    try:
        req = await ws.receive_json()
    except Exception:
        await ws.close(); return

    source_id = req.get("source_id", "oxford")
    params = req.get("params", {})
    try:
        paths = registry.source_paths(source_id)
        engine = registry.get_engine(req.get("engine", "lingbot-map"))
    except KeyError as e:
        await ws.send_json({"type": "error", "message": str(e)}); await ws.close(); return

    if _gpu_lock.locked():
        await ws.send_json({"type": "error", "message": "GPU busy with another run; try again shortly."})
        await ws.close(); return

    async with _gpu_lock:
        await ws.send_json({"type": "start", "source_id": source_id,
                            "n_frames": min(len(paths), int(params.get("max_frames", config.DEFAULTS.max_frames))),
                            "engine": engine.name})
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=4)
        stop = threading.Event()
        DONE = object()

        def worker():
            try:
                for fp in engine.stream(paths, params):
                    if stop.is_set():
                        break
                    asyncio.run_coroutine_threadsafe(queue.put(fp.to_msg()), loop).result()
            except Exception as ex:  # surface engine errors to the client
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "message": f"{type(ex).__name__}: {ex}"}), loop).result()
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(DONE), loop).result()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        try:
            while True:
                msg = await queue.get()
                if msg is DONE:
                    break
                await ws.send_json(msg)
            await ws.send_json({"type": "done"})
        except WebSocketDisconnect:
            stop.set()
        finally:
            stop.set()


# Static frontend (mounted last so /api and /ws take precedence)
@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
