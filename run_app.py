"""Launch the Lidar 3D workbench locally (needs the local GPU for live reconstruction).

    .venv/Scripts/python.exe run_app.py        # -> http://127.0.0.1:8120
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("LIDAR3D_PORT", "8120"))
    print(f"Lidar 3D workbench -> http://127.0.0.1:{port}")
    uvicorn.run("app.server:app", host="127.0.0.1", port=port, reload=False, log_level="info")
