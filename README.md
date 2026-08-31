# 🎬 Videogen-Lucy: Open-Source AI Long-Form Video Generation Platform

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Video Engine: Wan2.1](https://img.shields.io/badge/Video%20Engine-Wan2.1%20T2V%2FI2V-orange.svg)](https://github.com/Wan-Video/Wan2.1)

**Videogen-Lucy** is a production-grade, cloud-deployable AI video generation platform that converts natural-language prompts in **English** and **Hindi** into complete **5–30 minute animated and human-like videos**.

Rather than attempting to generate long videos in a single inference, Videogen-Lucy orchestrates an intelligent multi-stage pipeline: breaking narratives into scenes and 4–10 second shots, enforcing character and environment continuity, synthesizing natural multilingual voices, ducking background music, syncing subtitles, and assembling final 1080p master videos with FFmpeg.

---

## 🌟 Core Features

- **Multilingual Support**: English & natural Indian Hindi prompts and narration (`hi-IN-SwaraNeural`, `hi-IN-MadhurNeural`, `en-IN-NeerjaNeural`, `en-US-ChristopherNeural`).
- **5–30 Minute Long-Form Scaler**:
  - 5 minutes (~6 scenes, 30 shots)
  - 10 minutes (~12 scenes, 60 shots)
  - 20 minutes (~24 scenes, 120 shots)
  - 30 minutes (~36 scenes, 180 shots)
- **Character & Environment Consistency Bibles**: Persistent facial, clothing, palette, and location tracking across scenes.
- **Continuity Engine**: Tracks props, clothing, camera directions, and previous shot actions to prevent visual jump cuts.
- **Pluggable Provider Layer**:
  - **Video**: Wan2.1 (T2V & I2V), HunyuanVideo, CogVideoX, ComfyUI, Replicate.
  - **Voice**: EdgeTTS (zero-cost neural voices), XTTS-v2 (local GPU), ElevenLabs.
  - **Lip Sync**: Wav2Lip / SadTalker.
  - **Storage**: Local filesystem & AWS S3 / MinIO / Cloudflare R2.
- **Multi-Track Audio Engine**: Automated background music ducking (-14dB under speech), environmental SFX (rain, wind, footsteps), and EBU R128 loudness normalization.
- **Storyboard Preview & Scene Regeneration**: Review and edit screenplay before rendering; regenerate individual scenes without rebuilding the entire 30-minute video.
- **Content & License Guard**: Scans prompts for protected characters, real-person likenesses, and trademarks; produces safe constructive rewrites.
- **YouTube Safe Publishing & Asset Manifest**: Generates YouTube compliance checklists, AI disclosure guidance, and complete `asset_manifest.json` tracking model hashes and CC0/CC-BY music licenses.

---

## 🏗️ System Architecture

```
                               ┌─────────────────────────────┐
                               │   Browser / Web UI          │
                               │  (Next.js / HTML5 Player)   │
                               └──────────────┬──────────────┘
                                              │ REST + WebSocket
                               ┌──────────────▼──────────────┐
                               │       FastAPI Backend       │
                               │     (REST API & Security)   │
                               └──────────────┬──────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │  SQLite / PostgreSQL    │                       │  Job Queue & Orchestrator│
        │  (Relational Database)  │                       │  (Redis + Celery/Async) │
        └─────────────────────────┘                       └────────────┬────────────┘
                                                                       │
           ┌───────────────────────────────────────────────────────────┴────────────────────────────────────────┐
           ▼                                                           ▼                                        ▼
┌───────────────────────┐                                   ┌───────────────────────┐               ┌───────────────────────┐
│ Core AI Story Engine  │                                   │ Asset Generation Engines│              │ Assembly & Compliance │
│ • Language Detector   │                                   │ • Character Bible     │               │ • Multi-track Audio   │
│ • Content Safety Guard│                                   │ • Environment Bible   │               │ • FFmpeg Video Mixer  │
│ • Story Generator     │                                   │ • Prompt Compiler     │               │ • Subtitle Engine     │
│ • Script/Screenplay   │                                   │ • VideoProvider (Wan) │               │ • YouTube Compliance  │
│ • Shot Planner        │                                   │ • VoiceProvider (TTS) │               │ • License Manifest    │
│ • Continuity Engine   │                                   │ • LipSync Provider    │               │ • Quality Control     │
└───────────────────────┘                                   └───────────────────────┘               └───────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/Rupesh4113/videogen-lucy.git
cd videogen-lucy

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 3. Launch Platform

```bash
python main.py
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

## 🐳 Docker Deployment

To launch with PostgreSQL, Redis, CPU Backend, and Web UI:

```bash
docker-compose up -d --build
```

---

## 🧪 Running Automated Tests

Run the comprehensive unit, provider, API, and end-to-end integration test suite:

```bash
python -m pytest backend/tests -v
```

---

## 📖 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/projects` | `POST` | Create a new video project |
| `/api/v1/projects` | `GET` | List all projects |
| `/api/v1/projects/{id}` | `GET` | Get project details |
| `/api/v1/projects/{id}/storyboard` | `POST` | Generate 3-act story, bibles, and scenes |
| `/api/v1/projects/{id}/generate` | `POST` | Start asynchronous full video generation |
| `/api/v1/projects/{id}/status` | `GET` | Poll real-time progress percentage and stage |
| `/api/v1/projects/{id}/scenes` | `GET` | Get scene and shot breakdowns |
| `/api/v1/projects/{id}/scenes/{scene_id}/regenerate` | `POST` | Regenerate specific scene |
| `/api/v1/projects/{id}/download` | `GET` | Download YouTube production bundle (.ZIP) |
| `/api/v1/projects/{id}/subtitles` | `GET` | Download synchronized SRT / VTT |
| `/api/v1/projects/{id}/assets` | `GET` | Inspect `asset_manifest.json` |
| `/api/v1/safety/check` | `POST` | Pre-flight prompt copyright & IP check |
| `/api/v1/estimates/cost` | `POST` | Calculate GPU time, VRAM, and cloud cost |
| `/api/v1/health` | `GET` | System health and storage diagnostics |
| `/api/v1/ws/{project_id}` | `WebSocket` | Real-time progress event streaming |

---

## ⚖️ License & Attribution

- **Videogen-Lucy Engine**: Released under the **Apache 2.0 License**.
- **Wan2.1 Video Model**: Open-source under Apache 2.0 license.
- **Audio Soundscapes**: Sourced under Creative Commons CC0 / CC-BY 4.0 permissive commercial terms.
- **Notice**: AI-generated content can create legal, licensing, personality-rights, trademark, or platform-policy considerations. Review the generated `asset_manifest.json` before publishing.