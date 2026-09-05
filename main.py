"""
Videogen-Lucy Application Entry Point.
Exports FastAPI application instance for Vercel deployment and local execution.
"""
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI
from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🎬 Starting Videogen-Lucy AI Video Generation Platform at http://localhost:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)
