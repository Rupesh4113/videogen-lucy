"""
API v1 Router aggregation.
"""
from fastapi import APIRouter
from backend.app.api.v1.endpoints import auth, projects, safety, estimates, health, ws

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Users"])
api_v1_router.include_router(projects.router, tags=["Projects"])
api_v1_router.include_router(safety.router, tags=["Safety & Compliance"])
api_v1_router.include_router(estimates.router, tags=["Estimates"])
api_v1_router.include_router(health.router, tags=["System Health"])
api_v1_router.include_router(ws.router, tags=["WebSockets"])
