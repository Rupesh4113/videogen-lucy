"""
Videogen-Lucy Application Entry Point.
Launches the FastAPI backend and Web UI on port 8000.
"""
import uvicorn
import os
import sys

# Ensure backend package can be imported from root directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🎬 Starting Videogen-Lucy AI Video Generation Platform at http://localhost:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)
