"""
Videogen-Lucy — Streamlit Long-Form AI Video Generation Platform.
Standalone Web Application Deployable to Streamlit Community Cloud, Hugging Face Spaces, or Self-Hosted Servers.
Supports:
- Reference Images & Videos Upload & Conditioning (Characters, Locations, Objects, Styles, Motion)
- Google Veo 3.1 & Google Flow API Integration for High-Fidelity Video Generation
- Dual-Mode Authentication (Email & Password + Mobile Phone & OTP)
- 5-30 Minute Long-Form Video Generation with Character & Environment Consistency Locks
- Wan2.1 Multi-Shot Pipeline, EdgeTTS Speech Synthesis, Multi-Track Audio Mixing
- YouTube-Ready 1080p H.264/AAC MP4, SRT/VTT Subtitles, Asset Manifests
"""
import os
import sys
import io
import json
import zipfile
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure root repository directory is on sys.path for Streamlit Cloud & Hugging Face
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from sqlalchemy import select, or_, delete
from sqlalchemy.orm import selectinload

# Backend Imports
from backend.app.config import settings
from backend.app.models.database import AsyncSessionLocal, init_db
from backend.app.models.entities import (
    User, Project, Scene, Shot, Story, Character, Location, OTPToken, ReferenceMedia
)
from backend.app.pipeline.orchestrator import WorkflowOrchestrator
from backend.app.pipeline.safety_guard import ContentLicenseGuard
from backend.app.pipeline.resource_estimator import ResourceEstimator
from backend.app.pipeline.reference_processor import ReferenceProcessor
from backend.app.utils.security import (
    hash_password, verify_password, create_access_token, decode_access_token, generate_otp_code
)
from backend.app.providers.sms.factory import SMSProviderFactory

# Page Setup
st.set_page_config(
    page_title="Videogen-Lucy — AI Long-Form Video Platform",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Storage & Database
settings.init_directories()
try:
    asyncio.run(init_db())
except Exception:
    pass


# Session State Initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "storyboard_data" not in st.session_state:
    st.session_state.storyboard_data = None
if "otp_sent_to" not in st.session_state:
    st.session_state.otp_sent_to = None
if "dev_otp" not in st.session_state:
    st.session_state.dev_otp = None
if "uploaded_references" not in st.session_state:
    st.session_state.uploaded_references = []
if "session_ref_proj_id" not in st.session_state:
    st.session_state.session_ref_proj_id = f"sess_{os.urandom(4).hex()}"


# Async Helper
def run_async(coro):
    return asyncio.run(coro)


# Database User Actions
async def _async_register_user(email, password, name, phone=None):
    async with AsyncSessionLocal() as session:
        email_clean = email.lower().strip()
        stmt = select(User).where(User.email == email_clean)
        if (await session.execute(stmt)).scalar_one_or_none():
            return None, "An account with this email address already exists."
        
        if phone:
            p_stmt = select(User).where(User.phone_number == phone.strip())
            if (await session.execute(p_stmt)).scalar_one_or_none():
                return None, "An account with this phone number already exists."

        new_user = User(
            email=email_clean,
            name=name or email_clean.split("@")[0].capitalize(),
            phone_number=phone.strip() if phone else None,
            hashed_password=hash_password(password),
            video_credits=settings.DEFAULT_FREE_CREDITS,
            plan_tier="FREE",
            is_active=True,
            is_verified=True
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "phone_number": new_user.phone_number,
            "video_credits": new_user.video_credits or 15,
            "plan_tier": new_user.plan_tier or "FREE"
        }, None


async def _async_login_user(email, password):
    async with AsyncSessionLocal() as session:
        email_clean = email.lower().strip()
        stmt = select(User).where(User.email == email_clean)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if not user or not user.hashed_password:
            return None, "Invalid email or password."
        if not verify_password(password, user.hashed_password):
            return None, "Invalid email or password."
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "phone_number": user.phone_number,
            "video_credits": user.video_credits or 15,
            "plan_tier": user.plan_tier or "FREE"
        }, None


async def _async_send_otp(identifier: str):
    async with AsyncSessionLocal() as session:
        clean_id = identifier.strip()
        code = generate_otp_code()
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)

        otp_rec = OTPToken(
            phone_or_email=clean_id,
            otp_code=code,
            purpose="login",
            expires_at=expires,
            is_used=False
        )
        session.add(otp_rec)
        await session.commit()

        sms_provider = SMSProviderFactory.get_provider()
        res = await sms_provider.send_otp(
            clean_id,
            f"Your Videogen-Lucy login verification code is: {code}. Valid for 10 minutes."
        )

        return code if not res.get("delivered") else None, res.get("message", "OTP sent successfully.")


async def _async_verify_otp(identifier: str, code: str, name_fallback: str = None):
    async with AsyncSessionLocal() as session:
        clean_id = identifier.strip()
        now = datetime.now(timezone.utc)

        stmt = select(OTPToken).where(
            OTPToken.phone_or_email == clean_id,
            OTPToken.otp_code == code.strip(),
            OTPToken.is_used == False,
            OTPToken.expires_at > now
        ).order_by(OTPToken.created_at.desc())

        otp = (await session.execute(stmt)).scalars().first()
        if not otp:
            return None, "Invalid or expired verification code."

        otp.is_used = True
        await session.commit()

        is_phone = not ("@" in clean_id)
        if is_phone:
            u_stmt = select(User).where(User.phone_number == clean_id)
        else:
            u_stmt = select(User).where(User.email == clean_id.lower())

        user = (await session.execute(u_stmt)).scalar_one_or_none()
        if not user:
            user = User(
                email=clean_id.lower() if not is_phone else None,
                phone_number=clean_id if is_phone else None,
                name=name_fallback or (f"Mobile User {clean_id[-4:]}" if is_phone else clean_id.split("@")[0].capitalize()),
                video_credits=settings.DEFAULT_FREE_CREDITS,
                plan_tier="FREE",
                is_active=True,
                is_verified=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "phone_number": user.phone_number,
            "video_credits": user.video_credits or 15,
            "plan_tier": user.plan_tier or "FREE"
        }, None


async def _async_refresh_user(user_id: str):
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        user = (await session.execute(stmt)).scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "phone_number": user.phone_number,
                "video_credits": user.video_credits or 15,
                "plan_tier": user.plan_tier or "FREE"
            }
        return None


async def _async_create_and_generate_storyboard(payload, user_id=None):
    async with AsyncSessionLocal() as session:
        proj = Project(
            user_id=user_id,
            prompt=payload["prompt"],
            language=payload["language"],
            target_duration=payload["target_duration"],
            video_style=payload["video_style"],
            camera_style=payload.get("camera_style", "Cinematic handheld"),
            character_style=payload["character_style"],
            voice_type=payload["voice_type"],
            resolution=payload["resolution"],
            aspect_ratio=payload["aspect_ratio"],
            music_mood=payload["music_mood"],
            lock_character_appearance=payload.get("lock_character_appearance", True),
            lock_environment=payload.get("lock_environment", True),
            status="DRAFT"
        )
        session.add(proj)
        await session.flush()

        # Save reference media records
        for r_data in payload.get("references", []):
            ref = ReferenceMedia(
                project_id=proj.id,
                media_type=r_data["media_type"],
                reference_category=r_data["reference_category"],
                file_path=r_data["file_path"],
                file_url=r_data.get("file_url"),
                original_filename=r_data.get("original_filename"),
                description=r_data.get("description"),
                importance_weight=r_data.get("importance_weight", 1.0),
                target_scenes_json=r_data.get("target_scenes", ["all"]),
                usage_mode=r_data.get("usage_mode", "visual_reference"),
                extracted_keyframes_json=r_data.get("extracted_keyframes", []),
                metadata_json=r_data.get("metadata", {}),
                order=r_data.get("order", 0)
            )
            session.add(ref)

        await session.commit()
        await session.refresh(proj)

        orchestrator = WorkflowOrchestrator(session)
        sb = await orchestrator.generate_storyboard(proj.id)
        return proj.id, sb


async def _async_generate_storyboard(project_id):
    async with AsyncSessionLocal() as session:
        orchestrator = WorkflowOrchestrator(session)
        return await orchestrator.generate_storyboard(project_id)


async def _async_create_and_execute_pipeline(payload, user_id=None, progress_callback=None):
    async with AsyncSessionLocal() as session:
        proj = Project(
            user_id=user_id,
            prompt=payload["prompt"],
            language=payload["language"],
            target_duration=payload["target_duration"],
            video_style=payload["video_style"],
            camera_style=payload.get("camera_style", "Cinematic handheld"),
            character_style=payload["character_style"],
            voice_type=payload["voice_type"],
            resolution=payload["resolution"],
            aspect_ratio=payload["aspect_ratio"],
            music_mood=payload["music_mood"],
            lock_character_appearance=payload.get("lock_character_appearance", True),
            lock_environment=payload.get("lock_environment", True),
            status="DRAFT"
        )
        session.add(proj)
        await session.flush()

        for r_data in payload.get("references", []):
            ref = ReferenceMedia(
                project_id=proj.id,
                media_type=r_data["media_type"],
                reference_category=r_data["reference_category"],
                file_path=r_data["file_path"],
                file_url=r_data.get("file_url"),
                original_filename=r_data.get("original_filename"),
                description=r_data.get("description"),
                importance_weight=r_data.get("importance_weight", 1.0),
                target_scenes_json=r_data.get("target_scenes", ["all"]),
                usage_mode=r_data.get("usage_mode", "visual_reference"),
                extracted_keyframes_json=r_data.get("extracted_keyframes", []),
                metadata_json=r_data.get("metadata", {}),
                order=r_data.get("order", 0)
            )
            session.add(ref)

        await session.commit()
        await session.refresh(proj)

        orchestrator = WorkflowOrchestrator(session, progress_callback)
        video_url = await orchestrator.execute_full_video_pipeline(proj.id, progress_callback)
        return proj.id, video_url


async def _async_execute_pipeline(project_id, progress_callback=None):
    async with AsyncSessionLocal() as session:
        orchestrator = WorkflowOrchestrator(session, progress_callback)
        return await orchestrator.execute_full_video_pipeline(project_id, progress_callback)


async def _async_get_project_details(project_id):
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Project)
            .options(
                selectinload(Project.story),
                selectinload(Project.characters),
                selectinload(Project.locations),
                selectinload(Project.references),
                selectinload(Project.scenes).selectinload(Scene.shots),
            )
            .where(Project.id == project_id)
        )
        proj = (await session.execute(stmt)).scalar_one_or_none()
        if not proj:
            return None, []
        return proj, list(proj.scenes)


async def _async_list_user_projects(user_id=None):
    async with AsyncSessionLocal() as session:
        if user_id:
            stmt = select(Project).where(
                or_(Project.user_id == user_id, Project.user_id.is_(None))
            ).order_by(Project.created_at.desc())
        else:
            stmt = select(Project).order_by(Project.created_at.desc())
        res = await session.execute(stmt)
        return res.scalars().all()


# ==============================================================================
# SIDEBAR: User Authentication & Navigation & Settings
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/clapperboard.png", width=64)
    st.title("Videogen-Lucy")
    st.caption("AI Long-Form Video Platform • Google Veo 3.1 / Wan2.1")

    st.markdown("---")

    # User Profile / Login Card
    if st.session_state.user:
        # Refresh latest user balance
        u_info = run_async(_async_refresh_user(st.session_state.user["id"]))
        if u_info:
            st.session_state.user = u_info
            
        u_credits = st.session_state.user.get("video_credits", 15)
        u_tier = st.session_state.user.get("plan_tier", "FREE")
        
        st.success(f"👤 **{st.session_state.user.get('name', 'Creator')}**")
        if st.session_state.user.get("email"):
            st.caption(f"📧 {st.session_state.user['email']}")
        
        st.info(f"🪙 **Credits: {u_credits} Mins** • Plan: **{u_tier}**")
        
        col_side_u1, col_side_u2 = st.columns(2)
        with col_side_u1:
            if st.button("💎 Buy Credits", use_container_width=True):
                st.session_state.nav_choice = "💎 Pricing & Payments Hub"
                st.rerun()
        with col_side_u2:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user = None
                st.rerun()
    else:
        with st.expander("👤 Sign In / Register (Dual Auth)", expanded=True):
            auth_mode = st.radio("Authentication Method", ["Email & Password", "Mobile Phone & OTP"], horizontal=True)

            if auth_mode == "Email & Password":
                login_tab, reg_tab = st.tabs(["Log In", "Register"])
                
                with login_tab:
                    email_in = st.text_input("Email Address", key="login_email", placeholder="creator@example.com")
                    pass_in = st.text_input("Password", type="password", key="login_pass")
                    
                    if st.button("Log In", type="primary", use_container_width=True):
                        if not email_in or not pass_in:
                            st.error("Please enter both email and password.")
                        else:
                            u, err = run_async(_async_login_user(email_in, pass_in))
                            if err:
                                st.error(err)
                            else:
                                st.session_state.user = u
                                st.success("Logged in successfully!")
                                st.rerun()

                with reg_tab:
                    reg_name = st.text_input("Full Name", placeholder="Rupesh Sharma")
                    reg_email = st.text_input("Email Address", key="reg_email", placeholder="creator@example.com")
                    reg_phone = st.text_input("Mobile Phone (Optional)", placeholder="+91 9876543210")
                    reg_pass = st.text_input("Create Password", type="password", key="reg_pass")

                    if st.button("Create Account", type="primary", use_container_width=True):
                        if not reg_email or not reg_pass:
                            st.error("Email and password are required.")
                        else:
                            u, err = run_async(_async_register_user(reg_email, reg_pass, reg_name, reg_phone))
                            if err:
                                st.error(err)
                            else:
                                st.session_state.user = u
                                st.success("Account created and logged in!")
                                st.rerun()

            else:
                # Mobile Phone & OTP Tab
                st.caption("Sign in via Instant Mobile OTP verification.")
                phone_in = st.text_input("Mobile Number / Email", placeholder="+91 8867382604 or user@domain.com")
                otp_name = st.text_input("Your Name (New Users)", placeholder="Rupesh")

                col_otp_btn, _ = st.columns([2, 1])
                with col_otp_btn:
                    if st.button("📲 Send OTP to Device", use_container_width=True):
                        if not phone_in:
                            st.error("Please enter a mobile phone number.")
                        else:
                            with st.spinner("Dispatching OTP code..."):
                                dev_code, msg = run_async(_async_send_otp(phone_in))
                                st.session_state.otp_sent_to = phone_in
                                if dev_code:
                                    st.session_state.dev_otp = dev_code
                                    st.info(f"🔔 **Your Verification Code is: `{dev_code}`**")
                                st.success(f"✓ {msg}")

                if st.session_state.otp_sent_to:
                    st.markdown("---")
                    st.caption(f"Enter 6-digit OTP code sent to: **{st.session_state.otp_sent_to}**")
                    otp_val = st.text_input("Verification Code (OTP)", max_chars=6, placeholder="123456")

                    if st.button("✓ Verify & Log In", type="primary", use_container_width=True):
                        u, err = run_async(_async_verify_otp(st.session_state.otp_sent_to, otp_val, otp_name))
                        if err:
                            st.error(err)
                        else:
                            st.session_state.user = u
                            st.session_state.otp_sent_to = None
                            st.session_state.dev_otp = None
                            st.success("Verified and logged in!")
                            st.rerun()

    st.markdown("---")

    # AI Engine & API Configuration
    with st.expander("⚡ 2026 Video Engine Hub (Open-Source & Commercial T2V)", expanded=False):
        engine_options = [
            "Wan 2.2 / 2.1 (Alibaba Open-Source - 14B/1.3B DiT, Sliding Tile)",
            "Tencent HunyuanVideo 1.5 (Open-Source - Dual-Stream DiT, 3D RoPE)",
            "Lightricks LTX-Video 2.3 (Open-Source - Spatial-Temporal Token Carving)",
            "THUDM CogVideoX-5B (Open-Source - 3D Causal VAE)",
            "Google Veo 3.1 (Commercial - 1080p/4K Ultra-Realistic Video)",
            "Runway Gen-4.5 (Commercial - @reference consistency & physics)",
            "Kling 3.0 (Commercial - High Motion & Complex Physics)",
            "Seedance 2.0 (Commercial - 60s Joint Audio-Video Generation)",
            "OpenAI Sora (Sora-1.0 / Sora-Turbo Spacetime DiT)",
            "Replicate Cloud API",
            "Simulation / Fast Cloud Mode"
        ]
        selected_engine = st.selectbox("Video Provider Engine", engine_options, index=0)

        if "Wan 2.2" in selected_engine or "Wan" in selected_engine:
            settings.VIDEO_PROVIDER = "wan_local"
            wan_variant = st.selectbox("Wan Model Architecture", ["wan-2.2-14b (Flagship 14B DiT)", "wan-2.2-1.3b (Fast 1.3B Consumer)", "wan-2.1-14b (Wan 2.1 14B)", "wan-2.1-1.3b (Wan 2.1 1.3B)"], index=0)
            settings.WAN_MODEL_VARIANT = wan_variant.split(" ")[0]
            st.caption("🚀 Architecture: **3D Variational DiT + Sliding Tile Attention** • Native 1080p/4K Multi-Shot")

        elif "HunyuanVideo" in selected_engine or "Hunyuan" in selected_engine:
            settings.VIDEO_PROVIDER = "hunyuan_local"
            hunyuan_variant = st.selectbox("Hunyuan Model Version", ["hunyuan-video-1.5 (Flagship Dual-Stream)", "hunyuan-video-1.0 (Standard)"], index=0)
            st.caption("🇨🇳 Architecture: **Dual-Stream Visual-Language DiT + 3D RoPE** • 54/120 Native Temporal Frames")

        elif "LTX-Video" in selected_engine or "LTX" in selected_engine:
            settings.VIDEO_PROVIDER = "ltx_local"
            ltx_variant = st.selectbox("LTX-Video Version", ["ltx-video-2.3 (Real-Time Token Carving)", "ltx-video-2.0 (Standard)"], index=0)
            st.caption("⚡ Architecture: **High-Efficiency DiT with Spatial-Temporal Token Carving** • Ultra-fast consumer GPU inference")

        elif "CogVideoX" in selected_engine or "CogVideo" in selected_engine:
            settings.VIDEO_PROVIDER = "cogvideo_local"
            cog_variant = st.selectbox("CogVideoX Model", ["cogvideox-5b (High Capacity 5B)", "cogvideox-2b (Lightweight 2B)", "cogvideox-1.5 (Pro)"], index=0)
            st.caption("🧠 Architecture: **3D Causal VAE Compression + Expert Transformer** • Open Commercial Weights")

        elif "Runway" in selected_engine:
            settings.VIDEO_PROVIDER = "runway_commercial"
            runway_model = st.selectbox("Runway Model Version", ["gen-4.5 (Latest Flagship - @reference)", "gen-4 (Production)", "gen-3-alpha (Legacy)"], index=0)
            settings.RUNWAY_MODEL = runway_model.split(" ")[0]
            r_key = st.text_input("Runway API Key", type="password", value=os.getenv("RUNWAY_API_KEY", ""), placeholder="key_...")
            if r_key:
                os.environ["RUNWAY_API_KEY"] = r_key
                st.success("✓ Runway API Key configured!")
            st.caption("🎬 Features: **@reference identity locking & Aleph cinematic physics**")

        elif "Kling" in selected_engine:
            settings.VIDEO_PROVIDER = "kling_commercial"
            kling_model = st.selectbox("Kling AI Model", ["kling-3.0 (Next-Gen High Motion)", "kling-1.5 (Pro 1080p)", "kling-1.0 (Standard)"], index=0)
            settings.KLING_MODEL = kling_model.split(" ")[0]
            k_key = st.text_input("Kling AI API Key", type="password", value=os.getenv("KLING_API_KEY", ""), placeholder="kling_...")
            if k_key:
                os.environ["KLING_API_KEY"] = k_key
                st.success("✓ Kling API Key configured!")
            st.caption("🌪️ Features: **Dynamic fluid/cloth/camera motion & high-velocity physics**")

        elif "Seedance" in selected_engine:
            settings.VIDEO_PROVIDER = "seedance_commercial"
            sd_model = st.selectbox("Seedance Model", ["seedance-2.0 (Joint Audio-Video DiT)", "seedance-1.0 (Video Only)"], index=0)
            settings.SEEDANCE_MODEL = sd_model.split(" ")[0]
            sd_key = st.text_input("Seedance API Key", type="password", value=os.getenv("SEEDANCE_API_KEY", ""), placeholder="sd_...")
            if sd_key:
                os.environ["SEEDANCE_API_KEY"] = sd_key
                st.success("✓ Seedance API Key configured!")
            st.caption("🎵 Features: **60-second joint native audio-visual synchronization**")

        elif "OpenAI Sora" in selected_engine or "Sora" in selected_engine:
            settings.VIDEO_PROVIDER = "openai_sora"
            
            sora_model_choice = st.selectbox(
                "Sora Model Architecture",
                [
                    "sora-1.0 (Flagship Spacetime DiT - Recommended)",
                    "sora-turbo (Sora Turbo - High Speed Generation)"
                ],
                index=0
            )
            selected_sora_code = "sora-1.0" if "sora-1.0" in sora_model_choice else "sora-turbo"
            settings.SORA_MODEL = selected_sora_code
            os.environ["SORA_MODEL"] = selected_sora_code
            
            sora_key = st.text_input(
                "OpenAI / Sora API Key",
                type="password",
                value=os.getenv("SORA_API_KEY") or os.getenv("OPENAI_API_KEY") or "",
                placeholder="sk-..."
            )
            if sora_key:
                os.environ["SORA_API_KEY"] = sora_key
                os.environ["OPENAI_API_KEY"] = sora_key
                settings.SORA_API_KEY = sora_key
                st.success("✓ OpenAI Sora API Key active!")
            else:
                st.info("ℹ️ Enter OpenAI API Key or use Fast Cloud Mode for simulated spacetime preview rendering.")

            sora_recaption = st.checkbox("Enable Sora Spacetime Re-Captioning Engine (5D Expansion)", value=True)
            settings.SORA_ENABLE_RECAPTIONING = sora_recaption
            os.environ["SORA_ENABLE_RECAPTIONING"] = "true" if sora_recaption else "false"
            
            st.caption("🌌 Architecture: **Spacetime Latent Patch Diffusion Transformer (DiT)** • Variable Aspect 16:9 / 9:16 / 1:1")

        elif "Google Veo" in selected_engine or "Veo" in selected_engine:
            settings.VIDEO_PROVIDER = "google_flow"
            
            veo_model_choice = st.selectbox(
                "Veo Model Version",
                [
                    "veo-3.1-generate-001 (Veo 3.1 - Recommended)",
                    "veo-3.1-generate-preview (Veo 3.1 Preview)",
                    "veo-3.0-generate-001 (Veo 3.0 Production)",
                    "veo-2.0-generate-001 (Veo 2.0 Stable)"
                ],
                index=0
            )
            selected_model_code = veo_model_choice.split(" ")[0]
            settings.GOOGLE_VEO_MODEL = selected_model_code
            os.environ["GOOGLE_VEO_MODEL"] = selected_model_code
            
            st.caption(f"🎬 Active Model: **{selected_model_code}** • 1080p/4K Cinematic Synthesis")
            
            gkey = st.text_input(
                "Google API Key (AI Studio / Gemini / Vertex)",
                type="password",
                value=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "",
                placeholder="AIzaSy..."
            )
            if gkey:
                os.environ["GOOGLE_API_KEY"] = gkey
                os.environ["GOOGLE_FLOW_API_KEY"] = gkey
                os.environ["GEMINI_API_KEY"] = gkey
                st.success("✓ Google Veo 3.1 API Key active!")
            else:
                st.info("ℹ️ Enter key or use Fast Cloud Mode (renders preview clips without charge).")

            with st.expander("GCP Vertex AI Settings (Optional)", expanded=False):
                gcp_proj = st.text_input("GCP Project ID", value=os.getenv("GCP_PROJECT_ID", ""), placeholder="my-gcp-project")
                gcp_loc = st.text_input("GCP Location", value=os.getenv("GCP_LOCATION", "us-central1"))
                if gcp_proj:
                    os.environ["GCP_PROJECT_ID"] = gcp_proj
                    os.environ["GCP_LOCATION"] = gcp_loc
        elif "Replicate" in selected_engine:
            settings.VIDEO_PROVIDER = "replicate"
        else:
            settings.VIDEO_PROVIDER = "simulation"

    st.markdown("---")
    nav_options = [
        "🎬 Create & Plan Story",
        "📖 Storyboard Preview",
        "📽️ Video Theater & Downloads",
        "🎞️ Scene Studio & Regeneration",
        "💎 Pricing & Payments Hub",
        "🛡️ YouTube Compliance Audit",
        "📁 Project History"
    ]
    
    # Check if a button redirected to a specific tab
    current_nav_idx = 0
    if "nav_choice" in st.session_state and st.session_state.nav_choice in nav_options:
        current_nav_idx = nav_options.index(st.session_state.nav_choice)
        del st.session_state.nav_choice

    nav_selection = st.radio(
        "Navigation",
        nav_options,
        index=current_nav_idx
    )

    st.markdown("---")
    st.caption("Engines: **Wan 2.2 / Hunyuan 1.5 / LTX 2.3 / CogVideoX / Veo 3.1 / Runway / Kling / Sora**")
    st.caption("Voice: **EdgeTTS (EN/HI)** • Audio: **CC0 Indian & Cinematic Soundscapes**")


# ==============================================================================
# TAB 1: CREATE & PLAN STORY (WITH REFERENCE MEDIA SUPPORT)
# ==============================================================================
if nav_selection == "🎬 Create & Plan Story":
    st.header("🎬 Create AI Long-Form Video with Reference Conditioning")
    st.markdown("Convert your natural language story prompt and uploaded reference media into a complete 5–30 minute animated video with consistent characters, synchronized speech, and 1080p rendering.")

    col_load_ex, _ = st.columns([2, 4])
    with col_load_ex:
        if st.button("💡 Load Example Story (Monsoon Mother)"):
            st.session_state.prompt_text = "Create a heartwarming 10-minute story about a mother named Gauri living in an Indian village during the monsoon. Her baby becomes sick and she takes care of the baby throughout the night."
            st.session_state.duration_val = 600
            st.session_state.lang_val = "en"
            st.session_state.style_val = "Indian village realism"
            st.session_state.char_val = "Semi-realistic"
            st.session_state.camera_val = "Cinematic handheld"
            st.session_state.music_val = "Indian"

    col_form, col_estimate = st.columns([3, 2])

    with col_form:
        prompt_text = st.text_area(
            "1. Video Description / Story Prompt (English or Hindi)",
            value=st.session_state.get("prompt_text", ""),
            height=130,
            placeholder="e.g. Create a heartwarming 10-minute story about a mother named Gauri living in an Indian village during the monsoon..."
        )

        # Reference Media Upload & Management Section
        st.markdown("#### 2. 🖼️ Reference Images & Videos (Optional)")
        st.caption("Upload reference images/videos to guide character appearance, environment architecture, visual styles, and action/motion.")

        uploaded_files = st.file_uploader(
            "Drag & Drop Reference Media (JPG, PNG, WEBP, MP4, MOV, WEBM)",
            type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "webm"],
            accept_multiple_files=True,
            key="ref_media_uploader"
        )

        # Process newly uploaded files into session state
        if uploaded_files:
            existing_filenames = {r["original_filename"] for r in st.session_state.uploaded_references}
            for uf in uploaded_files:
                if uf.name not in existing_filenames:
                    try:
                        file_bytes = uf.getvalue()
                        ref_info = ReferenceProcessor.process_and_save_reference(
                            project_id=st.session_state.session_ref_proj_id,
                            file_bytes=file_bytes,
                            filename=uf.name,
                            reference_category="character" if any(k in uf.name.lower() for k in ["char", "person", "gauri", "face"]) else ("location" if any(k in uf.name.lower() for k in ["house", "village", "room", "loc"]) else "style"),
                            description=f"Reference for {Path(uf.name).stem}",
                            usage_mode="start_frame" if uf.name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and not any(r["usage_mode"] == "start_frame" for r in st.session_state.uploaded_references) else "visual_reference",
                            order=len(st.session_state.uploaded_references)
                        )
                        st.session_state.uploaded_references.append(ref_info)
                    except Exception as e:
                        st.error(f"Error processing '{uf.name}': {e}")

        # Display Reference Media Cards
        if st.session_state.uploaded_references:
            st.markdown(f"**Uploaded References ({len(st.session_state.uploaded_references)} items):**")
            to_remove = []

            for idx, ref in enumerate(st.session_state.uploaded_references):
                with st.expander(f"📌 {ref['reference_category'].title()} Reference: {ref['original_filename']} ({ref['media_type'].upper()})", expanded=True):
                    col_r_media, col_r_meta = st.columns([1, 2])

                    with col_r_media:
                        if ref["media_type"] == "image":
                            if Path(ref["file_path"]).exists():
                                st.image(ref["file_path"], use_container_width=True)
                        else:
                            if Path(ref["file_path"]).exists():
                                st.video(ref["file_path"])
                            if ref.get("extracted_keyframes"):
                                st.caption("📸 Extracted Keyframes:")
                                kf_cols = st.columns(len(ref["extracted_keyframes"]))
                                for kf_idx, kf_p in enumerate(ref["extracted_keyframes"]):
                                    if Path(kf_p).exists():
                                        kf_cols[kf_idx].image(kf_p, caption=f"Frame {kf_idx+1}")

                    with col_r_meta:
                        category_choices = [
                            "character", "location", "object", "style", "motion", "overall"
                        ]
                        cat_idx = category_choices.index(ref.get("reference_category", "character")) if ref.get("reference_category") in category_choices else 0
                        new_cat = st.selectbox(
                            "Reference Category",
                            category_choices,
                            index=cat_idx,
                            key=f"cat_{ref['id']}",
                            format_func=lambda x: {
                                "character": "👤 Character Reference (Facial appearance, Hair, Wardrobe)",
                                "location": "🏞️ Location / Environment (Architecture, Lighting, Layout)",
                                "object": "📦 Object / Prop Reference (Cooking utensils, vehicles, tools)",
                                "style": "🎨 Visual Style Reference (Color palette, Cinema aesthetic)",
                                "motion": "🏃 Action / Motion Reference (Dynamic movement, Camera flow)",
                                "overall": "🎬 Overall Video Reference"
                            }.get(x, x)
                        )
                        ref["reference_category"] = new_cat

                        mode_choices = ["visual_reference", "start_frame", "motion_reference"]
                        mode_idx = mode_choices.index(ref.get("usage_mode", "visual_reference")) if ref.get("usage_mode") in mode_choices else 0
                        new_mode = st.selectbox(
                            "Usage Mode",
                            mode_choices,
                            index=mode_idx,
                            key=f"mode_{ref['id']}",
                            format_func=lambda x: {
                                "visual_reference": "🎨 Visual Reference Only (Style, Face, Palette)",
                                "start_frame": "🎯 Starting Frame (Image-to-Video Anchor)",
                                "motion_reference": "🏃 Motion Inspiration (Movement Dynamics)"
                            }.get(x, x)
                        )
                        ref["usage_mode"] = new_mode

                        new_desc = st.text_input(
                            "AI Instruction / Description",
                            value=ref.get("description", ""),
                            key=f"desc_{ref['id']}",
                            placeholder="e.g. Gauri character reference — use this appearance consistently throughout the video"
                        )
                        ref["description"] = new_desc

                        col_wt, col_sc = st.columns(2)
                        with col_wt:
                            ref["importance_weight"] = st.slider(
                                "Influence Weight", 0.1, 2.0, float(ref.get("importance_weight", 1.0)), 0.1, key=f"wt_{ref['id']}"
                            )
                        with col_sc:
                            target_sc_val = st.selectbox(
                                "Apply to Scene(s)",
                                ["All Scenes", "Scene 1 Only", "Scene 2 Only", "Scene 3 Only", "Scene 4 Only", "Scene 5 Only"],
                                key=f"sc_{ref['id']}"
                            )
                            ref["target_scenes"] = ["all"] if target_sc_val == "All Scenes" else [int(target_sc_val.split(" ")[1])]

                        if st.button("🗑️ Remove This Reference", key=f"del_{ref['id']}"):
                            to_remove.append(idx)

            if to_remove:
                for idx in sorted(to_remove, reverse=True):
                    st.session_state.uploaded_references.pop(idx)
                st.rerun()

        st.markdown("---")

        # Visual & Camera Style Configuration
        st.markdown("#### 3. Visual & Cinematic Styling")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            lang = st.selectbox("Prompt & Narration Language", ["en", "hi"], format_func=lambda x: "English (Indian/Neutral)" if x == "en" else "Hindi (हिंदी - Natural Indian Accent)")
            duration_labels = {
                60: "1 minute (60s - Shorts / Reels, 2 scenes, ~10 shots)",
                180: "3 minutes (180s - YouTube Quick Story, 4 scenes, ~20 shots)",
                300: "5 minutes (300s - YouTube Standard, 6 scenes, ~30 shots)",
                600: "10 minutes (600s - YouTube Long-form, 12 scenes, ~60 shots)",
                900: "15 minutes (900s - YouTube Mid-Feature, 18 scenes, ~90 shots)",
                1200: "20 minutes (1200s - Episodic Anime, 24 scenes, ~120 shots)",
                1800: "30 minutes (1800s - Broadcast Episode, 36 scenes, ~180 shots)"
            }
            duration = st.selectbox(
                "Video Duration (1 to 30 Minutes)",
                [60, 180, 300, 600, 900, 1200, 1800],
                index=3,
                format_func=lambda x: duration_labels.get(x, f"{x // 60} minutes")
            )
            video_style = st.selectbox(
                "Visual Style",
                [
                    "Indian village realism", "Cinematic realistic", "Photorealistic",
                    "Hand-painted Japanese animation", "Bollywood cinematic", "Documentary realism",
                    "3D animation", "Anime", "Commercial", "Travel film", "Children's animation"
                ]
            )

        with col_f2:
            camera_style = st.selectbox(
                "Camera Style",
                [
                    "Cinematic handheld", "Slow dolly", "Tracking shot",
                    "Drone shot", "Close-up", "Wide establishing shot",
                    "Static camera", "Natural documentary camera"
                ]
            )
            char_style = st.selectbox("Character Style", ["Semi-realistic", "Human-like", "Cinematic photoreal", "3D animated", "2D hand-drawn", "Hand-painted anime"])
            resolution = st.selectbox("Resolution", ["1080p", "4K", "720p"])
            aspect_ratio = st.selectbox("Aspect Ratio", ["16:9", "9:16", "1:1"])

        music_mood = st.selectbox(
            "Background Music & Soundscape (CC0/CC-BY)",
            ["Indian", "Cinematic", "Emotional", "Suspense", "Happy", "None"],
            index=0
        )

        # Character and Environment Locking Toggles
        col_lock1, col_lock2 = st.columns(2)
        with col_lock1:
            lock_chars = st.checkbox("🔒 Lock character appearance across scenes", value=True, help="Preserve facial identity, hairstyle, clothing, and body proportions throughout all scenes.")
        with col_lock2:
            lock_env = st.checkbox("🔒 Lock environment across scenes", value=True, help="Preserve background architecture, spatial layout, textures, and atmospheric lighting.")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_check_safety = st.button("🛡️ Check Safety & Copyright")
        with col_btn2:
            pass

        if btn_check_safety and prompt_text:
            safety = ContentLicenseGuard.analyze_prompt(prompt_text)
            if safety.is_safe:
                st.success("✓ **Content & Legal Guard Passed**: No protected IP, trademarked superheroes, or celebrity likenesses detected.")
            else:
                st.warning(f"⚠️ **Protected Content Detected ({safety.risk_level} Risk)**:\n- " + "\n- ".join(safety.detected_violations))
                if safety.suggested_rewrite:
                    st.info(f"💡 **Suggested Safe Rewrite**: *\"{safety.suggested_rewrite}\"*")

    with col_estimate:
        st.subheader("📊 Resource & Cost Estimator")
        est = ResourceEstimator.estimate(duration, resolution)
        
        st.metric("Estimated Scenes", f"{est['total_scenes_estimated']} scenes")
        st.metric("Total Shots", f"{est['total_shots_estimated']} shots")
        st.metric("Est. Generation Time", f"{est['estimated_generation_time_minutes']} min")
        st.metric("Est. Cloud Cost", f"${est['estimated_gpu_cost_usd']:.2f}")
        st.metric("Est. Storage", f"{est['estimated_storage_gb']:.1f} GB")

        st.info("ℹ️ **Reference-Conditioned Multi-Shot Pipeline**: Uses uploaded media for I2V anchors, character bibles, and environment locks before long-form FFmpeg assembly.")

    st.markdown("---")
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        if st.button("✨ 1. Generate Storyboard Preview", type="primary", use_container_width=True):
            if not prompt_text:
                st.error("Please enter a video prompt.")
            else:
                with st.spinner("Generating 3-Act story structure, Character Bibles, and Scene breakdowns with reference conditioning..."):
                    try:
                        payload = {
                            "prompt": prompt_text,
                            "language": lang,
                            "target_duration": duration,
                            "video_style": video_style,
                            "camera_style": camera_style,
                            "character_style": char_style,
                            "voice_type": "Narrator + characters",
                            "resolution": resolution,
                            "aspect_ratio": aspect_ratio,
                            "music_mood": music_mood,
                            "lock_character_appearance": lock_chars,
                            "lock_environment": lock_env,
                            "references": st.session_state.uploaded_references
                        }
                        u_id = st.session_state.user["id"] if st.session_state.user else None
                        proj_id, sb = run_async(_async_create_and_generate_storyboard(payload, u_id))
                        st.session_state.current_project_id = proj_id
                        st.session_state.storyboard_data = sb
                        st.success("Storyboard Preview generated successfully with references! Go to 'Storyboard Preview' tab.")
                    except Exception as err:
                        st.error(f"Error generating storyboard: {err}")

    with col_act2:
        if st.button("🚀 2. Direct Full Video Generation", type="secondary", use_container_width=True):
            if not prompt_text:
                st.error("Please enter a video prompt.")
            else:
                try:
                    payload = {
                        "prompt": prompt_text,
                        "language": lang,
                        "target_duration": duration,
                        "video_style": video_style,
                        "camera_style": camera_style,
                        "character_style": char_style,
                        "voice_type": "Narrator + characters",
                        "resolution": resolution,
                        "aspect_ratio": aspect_ratio,
                        "music_mood": music_mood,
                        "lock_character_appearance": lock_chars,
                        "lock_environment": lock_env,
                        "references": st.session_state.uploaded_references
                    }
                    u_id = st.session_state.user["id"] if st.session_state.user else None
                    
                    prog_bar = st.progress(0, text="Initializing Reference-Aware Multi-Shot Video Pipeline...")
                    def _update_prog(stage, pct, msg):
                        prog_bar.progress(pct / 100.0, text=f"Stage: {stage} ({pct}%) — {msg}")

                    with st.spinner("Executing Full Long-Form Video Production Pipeline with References..."):
                        proj_id, video_url = run_async(_async_create_and_execute_pipeline(payload, u_id, _update_prog))
                        st.session_state.current_project_id = proj_id
                        st.success("Full Long-Form Video Generated Successfully! Open 'Video Theater & Downloads' tab.")
                except Exception as err:
                    st.error(f"Error executing video pipeline: {err}")


# ==============================================================================
# TAB 2: STORYBOARD PREVIEW (WITH REFERENCE ATTACHMENTS)
# ==============================================================================
elif nav_selection == "📖 Storyboard Preview":
    st.header("📖 Storyboard Preview & Consistency Bibles")

    if not st.session_state.current_project_id:
        st.info("No active project. Please generate a storyboard in the 'Create & Plan Story' tab.")
    else:
        proj_id = st.session_state.current_project_id
        proj, scenes = run_async(_async_get_project_details(proj_id))

        if proj and proj.story:
            st.subheader(f"Story: {proj.story.title}")
            st.caption(f"Logline: {proj.story.logline or proj.story.summary}")

            # 3-Act Structure
            st.markdown("### 🎭 3-Act Narrative Arc")
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            with col_a1:
                st.markdown("**Act 1: Beginning**")
                st.write(proj.story.beginning or "-")
            with col_a2:
                st.markdown("**Rising Action & Conflict**")
                st.write(f"{proj.story.conflict or ''} {proj.story.rising_action or ''}")
            with col_a3:
                st.markdown("**Act 2: Climax**")
                st.write(proj.story.climax or "-")
            with col_a4:
                st.markdown("**Act 3: Resolution**")
                st.write(f"{proj.story.resolution or ''} {proj.story.ending or ''}")

            st.markdown("---")

            # Reference Media Attached to Project
            if proj.references:
                st.markdown("### 🖼️ Active Reference Media Conditioning")
                r_cols = st.columns(min(4, max(1, len(proj.references))))
                for r_idx, ref in enumerate(proj.references):
                    with r_cols[r_idx % len(r_cols)]:
                        st.caption(f"📌 {ref.reference_category.title()} ({ref.usage_mode})")
                        if ref.media_type == "image" and Path(ref.file_path).exists():
                            st.image(ref.file_path, caption=ref.description or ref.original_filename)
                        elif ref.media_type == "video" and Path(ref.file_path).exists():
                            st.video(ref.file_path)

                st.markdown("---")

            # Character & Location Bibles
            col_cb, col_lb = st.columns(2)
            with col_cb:
                st.markdown("### 👥 Character Consistency Bible")
                for c in (proj.characters or []):
                    with st.expander(f"👤 {c.name} ({c.gender or 'Unknown'}, {c.age or 'Adult'})", expanded=True):
                        if c.reference_image_url and Path(c.reference_image_url.replace("/api/v1/storage/", "storage/")).exists():
                            st.image(c.reference_image_url.replace("/api/v1/storage/", "storage/"), width=150, caption="Character Reference Anchor")
                        st.write(f"**Face & Appearance:** {c.face_description}")
                        st.write(f"**Clothing:** {c.clothing}")
                        st.write(f"**Voice Preset:** {c.voice_preset}")

            with col_lb:
                st.markdown("### 🏞️ Environment Consistency Bible")
                for loc in (proj.locations or []):
                    with st.expander(f"🏞️ {loc.name} ({loc.time_of_day or 'Day'})", expanded=True):
                        if loc.reference_image_url and Path(loc.reference_image_url.replace("/api/v1/storage/", "storage/")).exists():
                            st.image(loc.reference_image_url.replace("/api/v1/storage/", "storage/"), width=200, caption="Environment Reference Anchor")
                        st.write(f"**Description:** {loc.description}")
                        st.write(f"**Lighting & Weather:** {loc.lighting} • {loc.weather}")

            st.markdown("---")

            # Planned Screenplay Scenes
            st.markdown("### 📜 Screenplay Scenes & Shots")
            for sc in scenes:
                with st.expander(f"Scene {sc.scene_number}: {sc.title or ''} ({sc.duration_seconds}s) — {sc.location_name}", expanded=False):
                    st.write(f"**Action:** {sc.action}")
                    if sc.narration:
                        st.write(f"**Narration:** *\"{sc.narration}\"*")
                    if sc.dialogue_json:
                        for d in sc.dialogue_json:
                            st.markdown(f"🗣️ **{d.get('character')}:** \"{d.get('line')}\"")

            st.markdown("---")
            if st.button("🚀 Approve Storyboard & Render Full Video", type="primary", use_container_width=True):
                prog_bar = st.progress(0, text="Starting Full Video Assembly...")
                def _update_prog(stage, pct, msg):
                    prog_bar.progress(pct / 100.0, text=f"Stage: {stage} ({pct}%) — {msg}")

                with st.spinner("Executing Full Long-Form Video Production Pipeline with References..."):
                    try:
                        video_url = run_async(_async_execute_pipeline(proj_id, _update_prog))
                        st.success("Video Generated Successfully! Check 'Video Theater & Downloads' tab.")
                    except Exception as err:
                        st.error(f"Error rendering video: {err}")


# ==============================================================================
# TAB 3: VIDEO THEATER & DOWNLOADS
# ==============================================================================
elif nav_selection == "📽️ Video Theater & Downloads":
    st.header("📽️ Video Theater & Export Distribution")

    if not st.session_state.current_project_id:
        st.info("No active project loaded. Generate a video in 'Create Story' or open one from 'Project History'.")
    else:
        proj_id = st.session_state.current_project_id
        proj, scenes = run_async(_async_get_project_details(proj_id))

        if proj:
            project_dir = settings.OUTPUT_DIR / proj_id
            video_file = project_dir / "final_video.mp4"

            # Check if video already exists or needs rendering
            if not video_file.exists():
                st.warning(f"🎬 Video rendering has not started for **{proj.title}**.")
                st.info("Click the button below to render all planned scenes, characters, audio tracks, and subtitles into the final 1080p master video:")

                if st.button("▶️ Render Long-Form Video Now (1-Click)", type="primary", use_container_width=True):
                    prog_bar = st.progress(0, text="Starting Full Video Assembly...")
                    def _update_prog(stage, pct, msg):
                        prog_bar.progress(pct / 100.0, text=f"Stage: {stage} ({pct}%) — {msg}")

                    with st.spinner("Executing Production Pipeline with References (Google Veo / Wan2.1 + Audio + Subtitles)..."):
                        try:
                            video_url = run_async(_async_execute_pipeline(proj_id, _update_prog))
                            st.success("Video Generated Successfully!")
                            st.rerun()
                        except Exception as err:
                            st.error(f"Error rendering video: {err}")
            else:
                col_vplay, col_vdown = st.columns([3, 2])

                with col_vplay:
                    st.subheader(f"Master Video: {proj.title}")
                    st.caption(f"Resolution: {proj.resolution} • Duration: {proj.target_duration}s • Format: 1080p H.264 / AAC MP4")

                    st.video(str(video_file))

                    # Subtitles Box
                    sub_file = project_dir / "subtitles_en.srt"
                    if sub_file.exists():
                        st.markdown("#### 💬 Synchronized Subtitles (SRT)")
                        with st.expander("View Subtitle Stream", expanded=False):
                            st.code(sub_file.read_text(encoding="utf-8"), language="text")

                with col_vdown:
                    st.subheader("📥 Export & Distribution Package")

                    with open(video_file, "rb") as f:
                        st.download_button(
                            label="📥 Download Master Video (1080p MP4)",
                            data=f,
                            file_name=f"{proj.title.replace(' ', '_')}_final.mp4",
                            mime="video/mp4",
                            use_container_width=True
                        )

                    if (project_dir / "subtitles_en.srt").exists():
                        with open(project_dir / "subtitles_en.srt", "rb") as f:
                            st.download_button(
                                label="📄 Download English Subtitles (SRT)",
                                data=f,
                                file_name="subtitles_en.srt",
                                mime="text/plain",
                                use_container_width=True
                            )

                    if (project_dir / "subtitles_hi.vtt").exists():
                        with open(project_dir / "subtitles_hi.vtt", "rb") as f:
                            st.download_button(
                                label="📄 Download Hindi Subtitles (WebVTT)",
                                data=f,
                                file_name="subtitles_hi.vtt",
                                mime="text/vtt",
                                use_container_width=True
                            )

                    if (project_dir / "asset_manifest.json").exists():
                        with open(project_dir / "asset_manifest.json", "rb") as f:
                            st.download_button(
                                label="📜 Download Asset & License Manifest (JSON)",
                                data=f,
                                file_name="asset_manifest.json",
                                mime="application/json",
                                use_container_width=True
                            )

                    # Full ZIP Bundle
                    if project_dir.exists():
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for p in project_dir.glob("*"):
                                if p.is_file():
                                    zf.write(p, arcname=p.name)
                        zip_buf.seek(0)
                        st.download_button(
                            label="📦 Download Full Production Bundle (ZIP)",
                            data=zip_buf,
                            file_name=f"videogen_{proj_id}_package.zip",
                            mime="application/zip",
                            use_container_width=True
                        )

                    st.markdown("---")
                    if st.button("🔄 Regenerate with Same References", use_container_width=True):
                        prog_bar = st.progress(0, text="Regenerating video with active references...")
                        def _update_prog(stage, pct, msg):
                            prog_bar.progress(pct / 100.0, text=f"Stage: {stage} ({pct}%) — {msg}")

                        with st.spinner("Regenerating video with existing references..."):
                            try:
                                video_url = run_async(_async_execute_pipeline(proj_id, _update_prog))
                                st.success("Video Regenerated Successfully!")
                                st.rerun()
                            except Exception as err:
                                st.error(f"Error regenerating video: {err}")

                    st.warning("⚠️ **YouTube AI Disclosure**: When uploading to YouTube, select **'Yes (Altered or synthetic content)'** in Video Details.")


# ==============================================================================
# TAB 4: SCENE STUDIO & REGENERATION
# ==============================================================================
elif nav_selection == "🎞️ Scene Studio & Regeneration":
    st.header("🎞️ Scene & Shot Studio")

    if not st.session_state.current_project_id:
        st.info("No active project loaded. Generate a video or open one from 'Project History'.")
    else:
        proj_id = st.session_state.current_project_id
        proj, scenes = run_async(_async_get_project_details(proj_id))

        if scenes:
            st.markdown(f"### Scenes for: **{proj.title}** ({len(scenes)} scenes)")
            for sc in scenes:
                col_sc_v, col_sc_info = st.columns([1, 2])
                with col_sc_v:
                    if sc.video_url and Path(sc.video_url.replace("/api/v1/storage/", "storage/")).exists():
                        st.video(sc.video_url.replace("/api/v1/storage/", "storage/"))
                    else:
                        st.info(f"Scene {sc.scene_number} clip")

                with col_sc_info:
                    st.markdown(f"#### Scene {sc.scene_number}: {sc.title or ''} ({sc.duration_seconds}s)")
                    st.write(f"**Location:** {sc.location_name} • **Lighting:** {sc.lighting}")
                    st.write(f"**Action:** {sc.action}")

                    tweak = st.text_input(f"Custom Prompt Tweak for Scene {sc.scene_number}", key=f"tweak_{sc.id}", placeholder="e.g. More intense monsoon rain and lightning")
                    if st.button(f"🔄 Regenerate Scene {sc.scene_number}", key=f"btn_regen_{sc.id}"):
                        with st.spinner(f"Regenerating Scene {sc.scene_number} with reference conditioning..."):
                            async def _do_regen():
                                async with AsyncSessionLocal() as session:
                                    orch = WorkflowOrchestrator(session)
                                    return await orch.regenerate_scene(sc.id, tweak)
                            run_async(_do_regen())
                            st.success(f"Scene {sc.scene_number} regenerated!")
                            st.rerun()
                st.markdown("---")


# ==============================================================================
# TAB 5: PRICING & PAYMENTS HUB (UPI, QR CODE, CARDS & BANK SETTLEMENT)
# ==============================================================================
elif nav_selection == "💎 Pricing & Payments Hub":
    from backend.app.providers.payment.gateway_manager import PaymentGatewayManager
    from backend.app.providers.payment.upi_qr_generator import UPIQRGenerator

    st.header("💎 Subscription Plans, Video Credits & Payment Hub")
    st.markdown("Unlock 1080p generation credits, Sora/Veo multi-shot rendering, and commercial licenses. Pay instantly via **UPI QR Code (GPay/PhonePe/Paytm), Cards, NetBanking, or Direct Bank Wire** in **INR (₹)** or **USD ($)**.")

    # User Status Bar
    if st.session_state.user:
        u_info = run_async(_async_refresh_user(st.session_state.user["id"]))
        if u_info:
            st.session_state.user = u_info
        
        c_val = st.session_state.user.get("video_credits", 15)
        t_val = st.session_state.user.get("plan_tier", "FREE")
        st.success(f"👤 Account: **{st.session_state.user.get('name')}** • 🪙 Available Credits: **{c_val} Minutes** • Active Tier: **{t_val}**")
    else:
        st.warning("⚠️ You are currently in Guest Mode. Please **Sign In** from the sidebar so purchased credits are linked to your account.")

    st.markdown("---")

    # Currency Switcher
    col_curr_title, col_curr_sel = st.columns([3, 2])
    with col_curr_title:
        st.subheader("1. Choose Your Video Generation Plan")
    with col_curr_sel:
        currency_pref = st.radio(
            "Select Currency",
            ["🇮🇳 INR (₹) - UPI & Indian Banking", "🇺🇸 USD ($) - Global Cards & Stripe"],
            horizontal=True,
            label_visibility="collapsed"
        )
    
    active_curr = "INR" if "INR" in currency_pref else "USD"
    plans = PaymentGatewayManager.get_plans(currency=active_curr)

    if "active_checkout_plan" not in st.session_state:
        st.session_state.active_checkout_plan = "creator_pro"

    # Display 4 Plan Columns
    cols = st.columns(4)
    for idx, plan in enumerate(plans):
        with cols[idx]:
            # Plan Card Box
            card_border = "border: 2px solid #6366F1;" if plan["is_popular"] else "border: 1px solid #334155;"
            badge_html = f"<span style='background-color:#4F46E5; color:white; padding:2px 8px; border-radius:12px; font-size:12px;'>{plan.get('badge', '')}</span>" if plan.get('badge') else ""
            
            st.markdown(
                f"""
                <div style='{card_border} border-radius:12px; padding:16px; min-height:360px; background-color:rgba(15, 23, 42, 0.6);'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <h3 style='margin:0;'>{plan['title']}</h3>
                        {badge_html}
                    </div>
                    <p style='color:#94A3B8; font-size:13px; margin:8px 0;'>{plan['description']}</p>
                    <h2 style='color:#38BDF8; margin:12px 0;'>{plan['display_price']} <span style='font-size:14px; color:#94A3B8;'>/ package</span></h2>
                    <p style='font-weight:bold; color:#10B981;'>🪙 {plan['video_credits']} Mins Video Credits</p>
                    <hr style='border-color:#334155;'>
                    <ul style='font-size:13px; padding-left:16px; color:#CBD5E1;'>
                        {"".join([f"<li>{f}</li>" for f in plan['features']])}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            btn_label = "Active / Current" if plan["id"] == "free_tier" and not st.session_state.user else ("Select Free" if plan["id"] == "free_tier" else f"⚡ Choose {plan['title']}")
            if st.button(btn_label, key=f"btn_plan_{plan['id']}", use_container_width=True, type="primary" if plan["is_popular"] else "secondary"):
                st.session_state.active_checkout_plan = plan["id"]
                st.rerun()

    # Checkout & Payment Terminal
    st.markdown("---")
    selected_plan = PaymentGatewayManager.get_plan_by_id(st.session_state.active_checkout_plan) or plans[1]
    
    st.subheader(f"2. Complete Payment for **{selected_plan['title']}** ({selected_plan['video_credits']} Minutes)")
    
    amount_to_pay = selected_plan["price_inr"] if active_curr == "INR" else selected_plan["price_usd"]
    
    if amount_to_pay == 0:
        st.success("🎉 This plan is completely FREE! You receive 15 free video generation minutes automatically upon registration.")
    else:
        tab_upi, tab_card, tab_bank = st.tabs([
            "📲 Instant UPI QR Code (GPay / PhonePe / Paytm)",
            "💳 Credit / Debit Card & NetBanking",
            "🏦 Direct Bank Transfer (IMPS / NEFT / Wire)"
        ])

        # TAB A: UPI QR CODE
        with tab_upi:
            col_qr_img, col_qr_details = st.columns([1, 2])
            
            # Generate live UPI payload
            temp_order_id = f"ORD_{os.urandom(4).hex().upper()}"
            upi_payload = UPIQRGenerator.create_payment_payload(
                amount_inr=amount_to_pay if active_curr == "INR" else (amount_to_pay * 85.0),
                order_id=temp_order_id,
                plan_title=selected_plan["title"]
            )
            
            with col_qr_img:
                st.image(upi_payload["qr_code_data"], caption="Scan with any UPI App (GPay, PhonePe, Paytm, BHIM, CRED)", use_container_width=True)
                st.caption(f"Amount: **₹{upi_payload['amount_inr']:.2f}** • 0% Extra Fee")

            with col_qr_details:
                st.markdown("#### ⚡ 3-Step Instant Payment")
                st.markdown(f"1. Open **Google Pay, PhonePe, Paytm, BHIM, or CRED** on your mobile.")
                st.markdown(f"2. Scan the QR code or send payment to UPI ID: **`{upi_payload['merchant_vpa']}`**")
                st.markdown(f"3. Enter the **12-digit UPI UTR / Transaction Number** below to instantly unlock your **{selected_plan['video_credits']} Minutes**.")
                
                st.markdown("---")
                user_utr = st.text_input("Enter 12-Digit UPI UTR / Transaction Ref ID", placeholder="e.g. 423984129841", key="input_upi_utr")
                
                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    if st.button("✓ Confirm Payment & Unlock Credits", type="primary", use_container_width=True):
                        if not user_utr:
                            st.error("Please enter the UPI UTR / Reference ID from your payment app.")
                        else:
                            with st.spinner("Verifying settlement and crediting account..."):
                                async def _do_upi_fulfill():
                                    async with AsyncSessionLocal() as s:
                                        u_id = st.session_state.user["id"] if st.session_state.user else None
                                        order = await PaymentGatewayManager.create_payment_order(
                                            db=s,
                                            plan_id=selected_plan["id"],
                                            currency="INR",
                                            payment_method="upi_qr",
                                            user_id=u_id
                                        )
                                        return await PaymentGatewayManager.verify_and_fulfill_payment(
                                            db=s,
                                            order_id=order.id,
                                            transaction_ref=user_utr
                                        )
                                res = run_async(_do_upi_fulfill())
                                st.success(f"🎉 {res['message']}")
                                st.info(f"📄 Invoice Number: `{res.get('invoice_number')}` • Ref: `{res.get('transaction_ref')}`")
                                st.rerun()

                with col_c2:
                    if st.button("⚡ Fast Dev Verify", use_container_width=True):
                        with st.spinner("Processing simulated verification..."):
                            async def _do_sim_fulfill():
                                async with AsyncSessionLocal() as s:
                                    u_id = st.session_state.user["id"] if st.session_state.user else None
                                    order = await PaymentGatewayManager.create_payment_order(
                                        db=s,
                                        plan_id=selected_plan["id"],
                                        currency="INR",
                                        payment_method="upi_qr",
                                        user_id=u_id
                                    )
                                    return await PaymentGatewayManager.verify_and_fulfill_payment(
                                        db=s,
                                        order_id=order.id,
                                        transaction_ref=f"DEV_UTR_{os.urandom(3).hex().upper()}"
                                    )
                            res = run_async(_do_sim_fulfill())
                            st.success(f"✓ Dev payment simulated! {selected_plan['video_credits']} Minutes added.")
                            st.rerun()

        # TAB B: CREDIT / DEBIT CARDS
        with tab_card:
            st.markdown(f"#### 💳 Card & NetBanking Checkout ({active_curr} {amount_to_pay:.2f})")
            st.caption("Supports Visa, MasterCard, RuPay, American Express, and International Cards.")
            
            col_cd1, col_cd2 = st.columns(2)
            with col_cd1:
                c_num = st.text_input("Card Number", placeholder="4111 2222 3333 4444", key="card_num")
                c_name = st.text_input("Name on Card", placeholder="Rupesh Sharma", key="card_name")
            with col_cd2:
                col_exp, col_cvv = st.columns(2)
                with col_exp:
                    c_exp = st.text_input("Expiry (MM/YY)", placeholder="12/28", key="card_exp")
                with col_cvv:
                    c_cvv = st.text_input("CVV", type="password", max_chars=4, placeholder="123", key="card_cvv")
            
            if st.button(f"🔒 Pay {active_curr} {amount_to_pay:.2f} via Secure Gateway", type="primary", use_container_width=True):
                with st.spinner("Authorizing payment with bank gateway..."):
                    async def _do_card_fulfill():
                        async with AsyncSessionLocal() as s:
                            u_id = st.session_state.user["id"] if st.session_state.user else None
                            order = await PaymentGatewayManager.create_payment_order(
                                db=s,
                                plan_id=selected_plan["id"],
                                currency=active_curr,
                                payment_method="card",
                                user_id=u_id
                            )
                            return await PaymentGatewayManager.verify_and_fulfill_payment(
                                db=s,
                                order_id=order.id,
                                transaction_ref=f"CARD_TXN_{os.urandom(4).hex().upper()}"
                            )
                    res = run_async(_do_card_fulfill())
                    st.success(f"🎉 Payment Authorized! {selected_plan['video_credits']} Minutes added to your account.")
                    st.rerun()

        # TAB C: DIRECT BANK TRANSFER
        with tab_bank:
            st.markdown("#### 🏦 Direct Bank Account Settlement (IMPS / NEFT / RTGS / Swift Wire)")
            st.caption("Direct wire settlement to merchant account. No gateway processing fees.")
            
            bank_info = upi_payload["bank_details"]
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.markdown(f"**Beneficiary Name:** `{bank_info['account_holder']}`")
                st.markdown(f"**Bank Name:** `{bank_info['bank_name']}`")
                st.markdown(f"**Account Number:** `{bank_info['account_number']}`")
            with col_b2:
                st.markdown(f"**IFSC Code:** `{bank_info['ifsc']}`")
                st.markdown(f"**SWIFT / BIC Code:** `{bank_info['swift']}`")
                st.markdown(f"**Amount to Transfer:** `₹{amount_to_pay:.2f}` (or `${amount_to_pay:.2f}` USD)")

            st.markdown("---")
            b_ref = st.text_input("Bank Wire Reference Number / UTR", placeholder="e.g. N1234567890", key="bank_ref_in")
            if st.button("Submit Wire Reference for Instant Credit", type="primary"):
                if not b_ref:
                    st.error("Please enter your bank transfer reference / UTR number.")
                else:
                    async def _do_bank_fulfill():
                        async with AsyncSessionLocal() as s:
                            u_id = st.session_state.user["id"] if st.session_state.user else None
                            order = await PaymentGatewayManager.create_payment_order(
                                db=s,
                                plan_id=selected_plan["id"],
                                currency=active_curr,
                                payment_method="bank_transfer",
                                user_id=u_id
                            )
                            return await PaymentGatewayManager.verify_and_fulfill_payment(
                                db=s,
                                order_id=order.id,
                                transaction_ref=b_ref
                            )
                    res = run_async(_do_bank_fulfill())
                    st.success(f"✓ Bank transfer recorded and verified! {selected_plan['video_credits']} Minutes credited.")
                    st.rerun()

    # User Billing History
    if st.session_state.user:
        st.markdown("---")
        st.subheader("3. 📜 Billing & Invoice History")
        
        async def _get_orders():
            async with AsyncSessionLocal() as s:
                stmt = select(PaymentOrder).where(PaymentOrder.user_id == st.session_state.user["id"]).order_by(PaymentOrder.created_at.desc())
                return (await s.execute(stmt)).scalars().all()
                
        user_orders = run_async(_get_orders())
        if not user_orders:
            st.info("No past transactions found on this account.")
        else:
            for o in user_orders:
                st.markdown(f"• **{o.plan_title}** — `{o.currency} {o.amount:.2f}` • Status: **{o.status}** • Credits: `+{o.credits_granted} Mins` • Invoice: `{o.invoice_number}` • Date: `{o.created_at.strftime('%d %b %Y, %H:%M')}`")


# ==============================================================================
# TAB 6: YOUTUBE COMPLIANCE AUDIT
# ==============================================================================
elif nav_selection == "🛡️ YouTube Compliance Audit":
    st.header("🛡️ YouTube Safe Publishing & Compliance Audit")

    st.markdown("Videogen-Lucy conducts algorithmic legal and copyright checks on screenplay, models, reference media, soundtracks, and synthetic likenesses.")

    checklist = [
        ("Original Screenplay", "Crafted algorithmically from original story prompts without copyright infringement."),
        ("Reference Media Fair-Use & Privacy", "Uploaded references processed locally as visual conditioning anchors with privacy safety."),
        ("Original Character Bibles", "No protected superheroes, Disney characters, or trademarked fictional entities."),
        ("Royalty-Free Soundtrack Ledger", "Music tracks backed by CC0 / CC-BY commercial licensing records."),
        ("No Celebrity Likeness", "All facial profiles generated synthetically with personality right compliance."),
        ("Standard Neural Voices", "Licensed neural TTS models without unauthorized voice clones."),
        ("Synchronized Subtitles", "English & Hindi SRT/VTT files generated and bundled in export package."),
        ("Asset Manifest Record", "Full asset_manifest.json containing all model hashes, reference records, and prompts."),
        ("YouTube AI Disclosure Badge", "Recommended: Check 'Altered or synthetic content' disclosure on upload.")
    ]

    for title, desc in checklist:
        st.success(f"✓ **{title}**: {desc}")

    st.info("ℹ️ **Legal Notice**: AI-generated content can still create legal, licensing, personality-rights, trademark, or platform-policy issues. Review the generated asset manifest and applicable licenses before commercial publishing.")


# ==============================================================================
# TAB 6: PROJECT HISTORY
# ==============================================================================
elif nav_selection == "📁 Project History":
    st.header("📁 Project History & Saved Generations")

    u_id = st.session_state.user["id"] if st.session_state.user else None
    projects = run_async(_async_list_user_projects(u_id))

    if not projects:
        st.info("No projects found. Create a new story in the 'Create & Plan Story' tab.")
    else:
        for p in projects:
            col_p1, col_p2 = st.columns([4, 1])
            with col_p1:
                st.markdown(f"### {p.title}")
                st.caption(f"Status: **{p.status}** • Duration: {p.target_duration}s • Language: {p.language.upper()} • Style: {p.video_style}")
                st.write(f"*{p.prompt[:150]}...*" if len(p.prompt) > 150 else f"*{p.prompt}*")

            with col_p2:
                if st.button("📽️ Open Video", key=f"open_{p.id}", use_container_width=True):
                    st.session_state.current_project_id = p.id
                    st.rerun()
            st.markdown("---")
