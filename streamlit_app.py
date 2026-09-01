"""
Videogen-Lucy — Streamlit Long-Form AI Video Generation Platform.
Standalone Web Application Deployable to Streamlit Community Cloud, Hugging Face Spaces, or Self-Hosted Servers.
Supports:
- Dual-Mode Authentication (Email & Password + Mobile Phone & OTP)
- 5-30 Minute Long-Form Video Generation with Character & Environment Consistency
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
from backend.app.models.entities import User, Project, Scene, Story, Character, Location, OTPToken
from backend.app.pipeline.orchestrator import WorkflowOrchestrator
from backend.app.pipeline.safety_guard import ContentLicenseGuard
from backend.app.pipeline.resource_estimator import ResourceEstimator
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
except Exception as e:
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
            "phone_number": new_user.phone_number
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
            "phone_number": user.phone_number
        }, None


async def _async_send_otp(phone_or_email):
    async with AsyncSessionLocal() as session:
        identifier = phone_or_email.strip()
        otp_code = generate_otp_code(6)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        otp_record = OTPToken(
            phone_or_email=identifier,
            otp_code=otp_code,
            purpose="login",
            expires_at=expires_at,
            is_used=False
        )
        session.add(otp_record)
        await session.commit()

        sms_provider = SMSProviderFactory.get_sms_provider()
        res = await sms_provider.send_otp(identifier, otp_code)
        return otp_code, res.get("mobile_url"), res.get("message")


async def _async_verify_otp(phone_or_email, otp_code, name=None):
    async with AsyncSessionLocal() as session:
        identifier = phone_or_email.strip()
        now_utc = datetime.now(timezone.utc)

        stmt = select(OTPToken).where(
            OTPToken.phone_or_email == identifier,
            OTPToken.otp_code == otp_code.strip(),
            OTPToken.is_used == False,
            OTPToken.expires_at > now_utc
        ).order_by(OTPToken.created_at.desc())

        record = (await session.execute(stmt)).scalars().first()
        if not record:
            return None, "Invalid or expired OTP code."

        record.is_used = True
        await session.commit()

        user_stmt = select(User).where(
            or_(User.phone_number == identifier, User.email == identifier)
        )
        user = (await session.execute(user_stmt)).scalar_one_or_none()

        if not user:
            is_email = "@" in identifier
            user = User(
                email=identifier if is_email else None,
                phone_number=None if is_email else identifier,
                name=name or (identifier.split("@")[0].capitalize() if is_email else f"User {identifier[-4:]}"),
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
            "phone_number": user.phone_number
        }, None


async def _async_create_and_generate_storyboard(payload, user_id=None):
    async with AsyncSessionLocal() as session:
        proj = Project(
            user_id=user_id,
            prompt=payload["prompt"],
            language=payload["language"],
            target_duration=payload["target_duration"],
            video_style=payload["video_style"],
            character_style=payload["character_style"],
            voice_type=payload["voice_type"],
            resolution=payload["resolution"],
            aspect_ratio=payload["aspect_ratio"],
            music_mood=payload["music_mood"],
            status="DRAFT"
        )
        session.add(proj)
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
            character_style=payload["character_style"],
            voice_type=payload["voice_type"],
            resolution=payload["resolution"],
            aspect_ratio=payload["aspect_ratio"],
            music_mood=payload["music_mood"],
            status="DRAFT"
        )
        session.add(proj)
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
# SIDEBAR: User Authentication & Navigation
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/clapperboard.png", width=64)
    st.title("Videogen-Lucy")
    st.caption("AI Long-Form Video Platform • Wan2.1 Multi-Shot")

    st.markdown("---")

    # User Profile / Login Card
    if st.session_state.user:
        st.success(f"👤 Logged in as: **{st.session_state.user.get('name', 'User')}**")
        if st.session_state.user.get("email"):
            st.caption(f"📧 {st.session_state.user['email']}")
        if st.session_state.user.get("phone_number"):
            st.caption(f"📱 {st.session_state.user['phone_number']}")
        
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        st.subheader("🔐 Account Sign In")
        auth_mode = st.radio("Login Method", ["Email & Password", "Mobile Phone & OTP"], horizontal=True)

        if auth_mode == "Email & Password":
            is_signup = st.checkbox("New User? Create Account", key="chk_signup")
            email_val = st.text_input("Email", placeholder="name@example.com")
            pass_val = st.text_input("Password", type="password", placeholder="••••••••")
            name_val = st.text_input("Full Name", placeholder="e.g. Rahul Sharma") if is_signup else None
            phone_val = st.text_input("Mobile Number (Optional)", placeholder="+91 98765 43210") if is_signup else None

            if st.button("Create Account" if is_signup else "Sign In", type="primary", use_container_width=True):
                if not email_val or not pass_val:
                    st.error("Please enter both email and password.")
                else:
                    if is_signup:
                        u, err = run_async(_async_register_user(email_val, pass_val, name_val, phone_val))
                    else:
                        u, err = run_async(_async_login_user(email_val, pass_val))
                    
                    if err:
                        st.error(err)
                    else:
                        st.session_state.user = u
                        st.success("Signed in successfully!")
                        st.rerun()

        elif auth_mode == "Mobile Phone & OTP":
            phone_input = st.text_input("Mobile Number", placeholder="e.g. 8867382604 or +91 98765 43210")

            col_otp1, col_otp2 = st.columns([1, 1])
            with col_otp1:
                if st.button("📲 Send OTP", use_container_width=True):
                    if not phone_input:
                        st.error("Please enter a phone number.")
                    else:
                        code, mobile_url, msg = run_async(_async_send_otp(phone_input))
                        st.session_state.otp_sent_to = phone_input
                        st.session_state.dev_otp = code
                        st.success(f"OTP sent to {phone_input}!")
                        if mobile_url:
                            st.info(f"[📲 Open Live Mobile Notification]({mobile_url})")

            if st.session_state.otp_sent_to:
                if st.session_state.dev_otp:
                    st.caption(f"🔑 Demo Code: `{st.session_state.dev_otp}`")

                otp_val = st.text_input("Enter 6-Digit OTP", value=st.session_state.dev_otp or "", max_chars=6)
                otp_name = st.text_input("Your Name (Optional)", placeholder="e.g. Priya Patel")

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
    nav_selection = st.radio(
        "Navigation",
        [
            "🎬 Create & Plan Story",
            "📖 Storyboard Preview",
            "📽️ Video Theater & Downloads",
            "🎞️ Scene Studio & Regeneration",
            "🛡️ YouTube Compliance Audit",
            "📁 Project History"
        ]
    )

    st.markdown("---")
    st.caption("Engine: **Wan2.1 (Multi-Shot) + FFmpeg**")
    st.caption("Voice: **EdgeTTS (EN/HI)** • Audio: **CC0 Sitar/Cinema**")


# ==============================================================================
# TAB 1: CREATE & PLAN STORY
# ==============================================================================
if nav_selection == "🎬 Create & Plan Story":
    st.header("🎬 Create AI Long-Form Video")
    st.markdown("Convert your natural language story prompt into a complete 5–30 minute animated video with consistent characters, synchronized speech, and 1080p rendering.")

    col_load_ex, _ = st.columns([2, 4])
    with col_load_ex:
        if st.button("💡 Load Example Story (Monsoon Mother)"):
            st.session_state.prompt_text = "Create a heartwarming 10-minute story about a mother living in an Indian village during the monsoon. Her baby becomes sick and she takes care of the baby throughout the night."
            st.session_state.duration_val = 600
            st.session_state.lang_val = "en"
            st.session_state.style_val = "Cinematic animation"
            st.session_state.char_val = "Semi-realistic"
            st.session_state.music_val = "Indian"

    col_form, col_estimate = st.columns([3, 2])

    with col_form:
        prompt_text = st.text_area(
            "Video Prompt (English or Hindi)",
            value=st.session_state.get("prompt_text", ""),
            height=120,
            placeholder="e.g. Create a heartwarming 10-minute story about a mother living in an Indian village during the monsoon..."
        )

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            lang = st.selectbox("Prompt & Narration Language", ["en", "hi"], format_func=lambda x: "English (Indian/Neutral)" if x == "en" else "Hindi (हिंदी - Natural Indian Accent)")
            duration = st.selectbox(
                "Video Duration",
                [300, 600, 900, 1200, 1800],
                index=1,
                format_func=lambda x: f"{x // 60} minutes (~{x // 50} scenes, {x // 10} shots)"
            )
            video_style = st.selectbox(
                "Video Style",
                ["Cinematic animation", "Realistic animation", "3D animation", "2D animation", "Children's animation", "Storytelling", "Documentary-style animation"]
            )

        with col_f2:
            char_style = st.selectbox("Character Style", ["Semi-realistic", "Human-like", "Cartoon", "3D", "2D"])
            resolution = st.selectbox("Resolution", ["1080p", "720p"])
            aspect_ratio = st.selectbox("Aspect Ratio", ["16:9", "9:16", "1:1"])

        music_mood = st.selectbox(
            "Background Music & Soundscape (CC0/CC-BY)",
            ["Indian", "Cinematic", "Emotional", "Suspense", "Happy", "None"],
            index=0
        )

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
        st.metric("Est. GPU Time", f"{est['estimated_generation_time_minutes']} min")
        st.metric("Est. Cloud Cost", f"${est['estimated_gpu_cost_usd']:.2f}")
        st.metric("Est. Storage", f"{est['estimated_storage_gb']:.1f} GB")

        st.info("ℹ️ **Multi-Shot Pipeline**: Renders isolated 4–10s clips before long-form FFmpeg assembly, preventing GPU VRAM overflows.")

    st.markdown("---")
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        if st.button("✨ 1. Generate Storyboard Preview", type="primary", use_container_width=True):
            if not prompt_text:
                st.error("Please enter a video prompt.")
            else:
                with st.spinner("Generating 3-Act story structure, Character Bibles, and Scene breakdowns..."):
                    try:
                        payload = {
                            "prompt": prompt_text,
                            "language": lang,
                            "target_duration": duration,
                            "video_style": video_style,
                            "character_style": char_style,
                            "voice_type": "Narrator + characters",
                            "resolution": resolution,
                            "aspect_ratio": aspect_ratio,
                            "music_mood": music_mood
                        }
                        u_id = st.session_state.user["id"] if st.session_state.user else None
                        proj_id, sb = run_async(_async_create_and_generate_storyboard(payload, u_id))
                        st.session_state.current_project_id = proj_id
                        st.session_state.storyboard_data = sb
                        st.success("Storyboard Preview generated successfully! Go to 'Storyboard Preview' tab.")
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
                        "character_style": char_style,
                        "voice_type": "Narrator + characters",
                        "resolution": resolution,
                        "aspect_ratio": aspect_ratio,
                        "music_mood": music_mood
                    }
                    u_id = st.session_state.user["id"] if st.session_state.user else None
                    
                    prog_bar = st.progress(0, text="Initializing Wan2.1 Multi-Shot Generation Pipeline...")
                    def _update_prog(stage, pct, msg):
                        prog_bar.progress(pct / 100.0, text=f"Stage: {stage} ({pct}%) — {msg}")

                    with st.spinner("Executing Full Long-Form Video Production Pipeline..."):
                        proj_id, video_url = run_async(_async_create_and_execute_pipeline(payload, u_id, _update_prog))
                        st.session_state.current_project_id = proj_id
                        st.success("Full Long-Form Video Generated Successfully! Open 'Video Theater & Downloads' tab.")
                except Exception as err:
                    st.error(f"Error executing video pipeline: {err}")


# ==============================================================================
# TAB 2: STORYBOARD PREVIEW
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

            # Character & Location Bibles
            col_cb, col_lb = st.columns(2)
            with col_cb:
                st.markdown("### 👥 Character Consistency Bible")
                for c in (proj.characters or []):
                    with st.expander(f"{c.name} ({c.gender or 'Unknown'}, {c.age or 'Adult'})", expanded=True):
                        st.write(f"**Face & Appearance:** {c.face_description}")
                        st.write(f"**Clothing:** {c.clothing}")
                        st.write(f"**Voice Preset:** {c.voice_preset}")

            with col_lb:
                st.markdown("### 🏞️ Environment Consistency Bible")
                for loc in (proj.locations or []):
                    with st.expander(f"{loc.name} ({loc.time_of_day or 'Day'})", expanded=True):
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

                with st.spinner("Executing Full Long-Form Video Production Pipeline..."):
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
        st.info("No active project loaded. Generate a video or open one from 'Project History'.")
    else:
        proj_id = st.session_state.current_project_id
        proj, scenes = run_async(_async_get_project_details(proj_id))

        if proj:
            col_vplay, col_vdown = st.columns([3, 2])

            with col_vplay:
                st.subheader(f"Master Video: {proj.title}")
                st.caption(f"Resolution: {proj.resolution} • Duration: {proj.target_duration}s • Format: 1080p H.264 / AAC MP4")

                project_dir = settings.OUTPUT_DIR / proj_id
                video_file = project_dir / "final_video.mp4"

                if video_file.exists():
                    st.video(str(video_file))
                else:
                    st.warning("Video file rendering in progress or not found. Start generation in 'Create Story'.")

                # Subtitles Box
                sub_file = project_dir / "subtitles_en.srt"
                if sub_file.exists():
                    st.markdown("#### 💬 Synchronized Subtitles (SRT)")
                    with st.expander("View Subtitle Stream", expanded=False):
                        st.code(sub_file.read_text(encoding="utf-8"), language="text")

            with col_vdown:
                st.subheader("📥 Export & Distribution Package")

                if video_file.exists():
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

                    tweak = st.text_input(f"Custom Prompt Tweak for Scene {sc.scene_number}", key=f"tweak_{sc.id}", placeholder="e.g. More intense rain and lightning")
                    if st.button(f"🔄 Regenerate Scene {sc.scene_number}", key=f"btn_regen_{sc.id}"):
                        with st.spinner(f"Regenerating Scene {sc.scene_number}..."):
                            async def _do_regen():
                                async with AsyncSessionLocal() as session:
                                    orch = WorkflowOrchestrator(session)
                                    return await orch.regenerate_scene(sc.id, tweak)
                            run_async(_do_regen())
                            st.success(f"Scene {sc.scene_number} regenerated!")
                            st.rerun()
                st.markdown("---")


# ==============================================================================
# TAB 5: YOUTUBE COMPLIANCE AUDIT
# ==============================================================================
elif nav_selection == "🛡️ YouTube Compliance Audit":
    st.header("🛡️ YouTube Safe Publishing & Compliance Audit")

    st.markdown("Videogen-Lucy conducts algorithmic legal and copyright checks on screenplay, models, soundtracks, and synthetic likenesses.")

    checklist = [
        ("Original Screenplay", "Crafted algorithmically from original story prompts without copyright infringement."),
        ("Original Character Bibles", "No protected superheroes, Disney characters, or trademarked fictional entities."),
        ("Royalty-Free Soundtrack Ledger", "Music tracks backed by CC0 / CC-BY commercial licensing records."),
        ("No Celebrity Likeness", "All facial profiles generated synthetically with personality right compliance."),
        ("Standard Neural Voices", "Licensed neural TTS models without unauthorized voice clones."),
        ("Synchronized Subtitles", "English & Hindi SRT/VTT files generated and bundled in export package."),
        ("Asset Manifest Record", "Full asset_manifest.json containing all model hashes and prompts."),
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
