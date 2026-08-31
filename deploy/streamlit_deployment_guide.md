# 🎈 Streamlit Cloud & Open-Source Deployment Guide for Videogen-Lucy

Videogen-Lucy comes with a complete, standalone **Streamlit Web Application** ([`streamlit_app.py`](file:///f:/github/videogen-lucy/streamlit_app.py)) that can be deployed for free to **Streamlit Community Cloud**, **Hugging Face Spaces**, or self-hosted on any cloud server.

---

## 1. Run Streamlit Locally

To start the Streamlit application on your local machine:

```powershell
streamlit run streamlit_app.py
```

The application will open at: **`http://localhost:8501`**

---

## 2. Deploy to Streamlit Community Cloud (100% Free 1-Click)

[Streamlit Community Cloud](https://share.streamlit.io) provides free hosting directly from your GitHub repository.

### Step-by-Step Deployment:
1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Add Streamlit Long-Form Video Platform"
   git push origin main
   ```
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with your GitHub account.
3. Click **"New app"**.
4. Configure your repository details:
   - **Repository**: `Rupesh4113/videogen-lucy` (or your fork)
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **App URL**: `https://videogen-lucy.streamlit.app` (customize if available)
5. Under **Advanced settings**, set any optional environment variables:
   - `SECRET_KEY` = `your_super_secret_jwt_key`
   - `SMS_PROVIDER` = `ntfy`
6. Click **Deploy!**
   - Streamlit Cloud will automatically install dependencies from [`requirements.txt`](file:///f:/github/videogen-lucy/requirements.txt) and OS packages from [`packages.txt`](file:///f:/github/videogen-lucy/packages.txt) (FFmpeg).

---

## 3. Deploy to Hugging Face Spaces (Streamlit SDK)

Hugging Face Spaces offers free CPU & GPU hosting for Streamlit apps.

### Step-by-Step Deployment:
1. Go to **[huggingface.co/spaces](https://huggingface.co/spaces)** and click **"Create new Space"**.
2. Select **Space SDK**: `Streamlit`.
3. Choose Space Hardware (Free CPU or GPU tier).
4. Set Space Name: `videogen-lucy`.
5. Link your GitHub repository or push directly:
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/videogen-lucy
   git push space main
   ```
6. Hugging Face Spaces will automatically launch your Streamlit video studio!

---

## 4. Deploy with Docker / Open-Source Cloud VPS

To deploy the Streamlit app in Docker or on any Linux server:

### Docker Command:
```bash
docker run -d \
  -p 8501:8501 \
  -v videogen_storage:/app/storage \
  --name videogen-streamlit \
  python:3.11-slim \
  bash -c "pip install -r requirements.txt && streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0"
```

---

## 5. Features Included in `streamlit_app.py`

- 🔐 **Dual-Mode Authentication**: Email & Password and Mobile Phone & OTP (ntfy open-source mobile push).
- 🎬 **Story Creation**: 5–30 minute story planning, duration scaling, style controls, and cost estimators.
- 📖 **Storyboard Preview**: 3-Act narrative, Character & Environment Bibles, dialogue & screenplay inspection.
- 📽️ **Master Video Theater**: Native video playback, synchronized subtitles, and 1-click download of MP4, SRT, VTT, Manifest JSON, and ZIP packages.
- 🎞️ **Scene Studio**: Inspect individual scene videos and trigger single-scene prompt regenerations.
- 🛡️ **YouTube Compliance Audit**: Automated legal, trademark, and AI synthetic content disclosure checklist.
