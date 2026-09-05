"""
Vercel Serverless Function entry point for Videogen-Lucy FastAPI backend.
"""
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
from backend.app.main import app
