"""
Videogen-Lucy Application Entry Point.
Exports top-level FastAPI instance 'app' for Vercel, Render, Fly.io, Hugging Face, and ASGI servers,
and provides local command-line execution via Uvicorn.
"""
import os
import sys

# Ensure backend package can be imported from root directory
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Top-level FastAPI application instance for Vercel & ASGI web servers
from backend.app.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🎬 Starting Videogen-Lucy AI Video Generation Platform at http://localhost:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)
