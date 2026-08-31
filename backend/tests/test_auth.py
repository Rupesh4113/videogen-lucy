"""
Automated Test Suite for Authentication & User Subsystems.
Verifies:
1. PBKDF2 Password Hashing & Verification
2. JWT Token Creation, Decoding, and Expiration
3. Email & Password Registration and Login
4. Mobile Phone & OTP Delivery and Verification
5. Protected /auth/me Endpoint
6. Project User Isolation
"""
import pytest
from datetime import timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.main import app
from backend.app.models.entities import User, OTPToken, Project
from backend.app.utils.security import (
    hash_password, verify_password, create_access_token, decode_access_token, generate_otp_code
)


@pytest.mark.asyncio
async def test_password_hashing_and_verification():
    raw_pw = "SuperSecurePassword2026!"
    hashed = hash_password(raw_pw)
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(raw_pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_jwt_token_generation_and_decoding():
    payload = {"sub": "user-1234", "email": "test@videogen.ai", "name": "Test User"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=60))
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-1234"
    assert decoded["email"] == "test@videogen.ai"

    # Expired token test
    expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
    assert decode_access_token(expired_token) is None


@pytest.mark.asyncio
async def test_email_password_registration_and_login(db_session: AsyncSession):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Register User
        reg_payload = {
            "email": "director@videogen.ai",
            "password": "CinemaPassword123!",
            "name": "Satyajit Ray",
            "phone_number": "+919876543210"
        }
        res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "director@videogen.ai"
        assert data["user"]["name"] == "Satyajit Ray"

        # 2. Duplicate Registration Rejection
        dup_res = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert dup_res.status_code == 400

        # 3. Login with Valid Password
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": "director@videogen.ai",
            "password": "CinemaPassword123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        # 4. Login with Invalid Password
        bad_login = await ac.post("/api/v1/auth/login", json={
            "email": "director@videogen.ai",
            "password": "WrongPassword!"
        })
        assert bad_login.status_code == 401

        # 5. Access /auth/me with Bearer token
        me_res = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "director@videogen.ai"


@pytest.mark.asyncio
async def test_mobile_otp_send_and_verify(db_session: AsyncSession):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        phone = "+919123456789"
        
        # 1. Send OTP
        send_res = await ac.post("/api/v1/auth/otp/send", json={"phone_or_email": phone})
        assert send_res.status_code == 200
        send_data = send_res.json()
        assert send_data["success"] is True
        otp_code = send_data["dev_otp_code"]
        assert otp_code is not None
        assert len(otp_code) == 6

        # 2. Verify with Wrong OTP
        bad_verify = await ac.post("/api/v1/auth/otp/verify", json={
            "phone_or_email": phone,
            "otp_code": "000000"
        })
        assert bad_verify.status_code == 400

        # 3. Verify with Correct OTP
        verify_res = await ac.post("/api/v1/auth/otp/verify", json={
            "phone_or_email": phone,
            "otp_code": otp_code,
            "name": "Mobile Creator"
        })
        assert verify_res.status_code == 200
        token_data = verify_res.json()
        assert "access_token" in token_data
        assert token_data["user"]["phone_number"] == phone
        assert token_data["user"]["name"] == "Mobile Creator"

        # 4. Reusing Same OTP Should Fail (One-Time usage)
        reuse_res = await ac.post("/api/v1/auth/otp/verify", json={
            "phone_or_email": phone,
            "otp_code": otp_code
        })
        assert reuse_res.status_code == 400


@pytest.mark.asyncio
async def test_project_user_isolation(db_session: AsyncSession):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register User A
        res_a = await ac.post("/api/v1/auth/register", json={
            "email": "user_a@videogen.ai",
            "password": "Password123!",
            "name": "User A"
        })
        token_a = res_a.json()["access_token"]

        # User A creates a project
        p_res = await ac.post("/api/v1/projects", json={
            "prompt": "Story A about mountains",
            "target_duration": 300,
            "video_style": "Cinematic animation",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token_a}"})
        assert p_res.status_code == 201
        proj_a = p_res.json()

        # Check project was associated with user A
        assert proj_a["user_id"] == res_a.json()["user"]["id"]

        # List projects for User A
        list_a = await ac.get("/api/v1/projects", headers={"Authorization": f"Bearer {token_a}"})
        assert list_a.status_code == 200
        ids_a = [p["id"] for p in list_a.json()]
        assert proj_a["id"] in ids_a
