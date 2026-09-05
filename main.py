"""
Videogen-Lucy Application Entry Point.
Exports top-level FastAPI instance 'app' for Vercel, Render, Fly.io, Hugging Face, and ASGI servers,
and provides local command-line execution via Uvicorn.
"""
import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from backend.app.main import app

# Top-level ASGI / FastAPI instance for Vercel and production ASGI servers
app: FastAPI = app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🎬 Starting Videogen-Lucy AI Video Generation Platform at http://localhost:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)
