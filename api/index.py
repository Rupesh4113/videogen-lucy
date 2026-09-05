"""
Vercel Serverless Function entry point for Videogen-Lucy FastAPI backend.
"""
import os
import sys

# Ensure repository root is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app.main import app as _app

# Top-level ASGI application instance for Vercel Serverless
app = _app
