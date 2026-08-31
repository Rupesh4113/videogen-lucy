"""
Resource and Cost Estimator Engine for Long-Form Video Production.
Calculates scene breakdowns, shot counts, GPU compute time, VRAM requirements, and cloud costs.
"""
from typing import Dict, Any


class ResourceEstimator:
    @staticmethod
    def estimate(target_duration_seconds: int, resolution: str = "1080p") -> Dict[str, Any]:
        """
        Calculates estimated scenes, shots, GPU rendering time, storage size, and cloud cost.
        """
        mins = max(1.0, float(target_duration_seconds) / 60.0)
        
        # 5 min -> ~6 scenes, 30 shots
        # 10 min -> ~12 scenes, 60 shots
        # 20 min -> ~24 scenes, 120 shots
        # 30 min -> ~36 scenes, 180 shots
        estimated_scenes = max(4, int(mins * 1.2))
        estimated_shots = estimated_scenes * 5

        # Wan2.1 14B takes ~20-30s per 5s shot on A100 GPU
        estimated_gpu_time_mins = round((estimated_shots * 25) / 60.0, 1)
        
        # Cloud A100 spot instance ~$1.50/hr ($0.025 - $0.035/min)
        estimated_cost = round(estimated_gpu_time_mins * 0.035, 2)
        
        # Estimated storage: ~15MB per shot + raw assets + final master (~2GB per 10 mins)
        estimated_storage = round((estimated_shots * 0.02) + (mins * 0.15), 2)

        # VRAM requirement based on resolution
        vram_req = 24 if resolution == "1080p" else 16

        return {
            "target_duration_minutes": mins,
            "total_scenes_estimated": estimated_scenes,
            "total_shots_estimated": estimated_shots,
            "estimated_generation_time_minutes": estimated_gpu_time_mins,
            "estimated_gpu_cost_usd": estimated_cost,
            "estimated_storage_gb": estimated_storage,
            "estimated_vram_requirement_gb": vram_req,
            "recommended_model": "Wan2.1-T2V-14B (Apache 2.0)"
        }
