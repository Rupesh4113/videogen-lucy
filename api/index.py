"""
Vercel Serverless Function entry point for Videogen-Lucy FastAPI backend.
"""
import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from backend.app.main import app

# Top-level ASGI instance for Vercel serverless runtime
app: FastAPI = app
