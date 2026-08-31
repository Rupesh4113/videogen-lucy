"""
Cost and Resource Estimation API Endpoints.
"""
from fastapi import APIRouter
from backend.app.schemas.project import CostEstimateRequest, CostEstimateResponse
from backend.app.pipeline.resource_estimator import ResourceEstimator

router = APIRouter()


@router.post("/estimates/cost", response_model=CostEstimateResponse)
async def estimate_generation_cost(req: CostEstimateRequest):
    """
    Estimates GPU generation time, cloud/electricity cost, storage footprint, and VRAM requirements.
    """
    res = ResourceEstimator.estimate(req.target_duration, req.resolution)
    return CostEstimateResponse(
        target_duration_minutes=res["target_duration_minutes"],
        total_scenes_estimated=res["total_scenes_estimated"],
        total_shots_estimated=res["total_shots_estimated"],
        estimated_generation_time_minutes=res["estimated_generation_time_minutes"],
        estimated_gpu_cost_usd=res["estimated_gpu_cost_usd"],
        estimated_storage_gb=res["estimated_storage_gb"],
        estimated_vram_requirement_gb=res["estimated_vram_requirement_gb"],
        recommended_model=res["recommended_model"]
    )
