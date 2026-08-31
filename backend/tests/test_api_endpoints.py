"""
Tests for FastAPI REST Endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "providers" in data


@pytest.mark.asyncio
async def test_safety_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test clean prompt
        res = await client.post("/api/v1/safety/check", json={"prompt": "A mother caring for a child in a village"})
        assert res.status_code == 200
        assert res.json()["is_safe"] is True

        # Test infringing prompt
        res2 = await client.post("/api/v1/safety/check", json={"prompt": "Spider-Man fighting Superman in Gotham"})
        assert res2.status_code == 200
        assert res2.json()["is_safe"] is False


@pytest.mark.asyncio
async def test_project_crud_and_storyboard_endpoints(db_session: AsyncSession):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Project
        payload = {
            "prompt": "Create a 5-minute story about a monsoon night in an Indian village.",
            "language": "en",
            "target_duration": 300,
            "video_style": "Cinematic animation",
            "character_style": "Semi-realistic",
            "voice_type": "Narrator + characters",
            "resolution": "1080p",
            "aspect_ratio": "16:9",
            "music_mood": "Indian"
        }
        create_res = await client.post("/api/v1/projects", json=payload)
        assert create_res.status_code == 201
        proj_data = create_res.json()
        project_id = proj_data["id"]

        # Get Project
        get_res = await client.get(f"/api/v1/projects/{project_id}")
        assert get_res.status_code == 200
        assert get_res.json()["status"] == "DRAFT"

        # Generate Storyboard
        sb_res = await client.post(f"/api/v1/projects/{project_id}/storyboard")
        if sb_res.status_code != 200:
            print("ERROR IN STORYBOARD:", sb_res.text)
        assert sb_res.status_code == 200
        sb_data = sb_res.json()
        assert "story" in sb_data
        assert len(sb_data["characters"]) >= 1
        assert len(sb_data["scenes"]) >= 5

        # Inspect Status
        status_res = await client.get(f"/api/v1/projects/{project_id}/status")
        assert status_res.status_code == 200
        assert status_res.json()["current_stage"] == "STORYBOARD_READY"
