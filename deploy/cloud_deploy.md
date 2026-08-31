# Cloud Deployment & Infrastructure Guide

This document provides step-by-step instructions for deploying **Videogen-Lucy** in production cloud environments.

---

## 1. Architecture Summary

```
                ┌──────────────────────────────┐
                │        Browser / UI          │
                └──────────────┬───────────────┘
                               │ (HTTPS)
                ┌──────────────▼───────────────┐
                │    Cloud Load Balancer       │
                └──────────────┬───────────────┘
                               │
                ┌──────────────▼───────────────┐
                │   FastAPI Backend (CPU)      │
                └──────┬───────────────┬───────┘
                       │               │
       ┌───────────────▼──────┐ ┌──────▼────────────────┐
       │ Managed PostgreSQL   │ │ Managed Redis Cluster │
       └──────────────────────┘ └──────┬────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
             ┌─────────────────┐               ┌─────────────────┐
             │ GPU Worker #1   │               │ GPU Worker #2   │
             │ (Wan2.1 / CUDA) │               │ (Wan2.1 / CUDA) │
             └────────┬────────┘               └────────┬────────┘
                      │                                 │
                      └────────────────┬────────────────┘
                                       │
                               ┌───────▼────────┐
                               │  S3 / GCS / R2 │
                               │ Object Storage │
                               └────────────────┘
```

---

## 2. Docker Compose (Single Host / Dev Server)

To deploy on a single GPU instance (e.g. AWS `g5.4xlarge` or GCP `g2-standard-16` with NVIDIA L4/A10G):

```bash
# 1. Clone repository
git clone https://github.com/Rupesh4113/videogen-lucy.git
cd videogen-lucy

# 2. Copy environment file
cp .env.example .env

# 3. Launch full stack
docker-compose up -d --build

# 4. View logs
docker-compose logs -f
```

The Web UI will be accessible at `http://<YOUR_SERVER_IP>:8000`.

---

## 3. AWS Production Deployment (ECS / EKS + S3 + RDS)

1. **Storage (S3)**:
   Create an S3 bucket with private ACL and configure CORS for video streaming. Set:
   ```env
   STORAGE_PROVIDER=s3
   AWS_S3_BUCKET=videogen-production-assets
   AWS_REGION=us-east-1
   ```

2. **Database (RDS PostgreSQL)**:
   Provision an `db.t4g.medium` instance running PostgreSQL 16.

3. **Backend Container (ECS Fargate - CPU)**:
   Deploy `docker/Dockerfile.backend` on ECS Fargate (2 vCPU, 4GB RAM) with ALB listener.

4. **GPU Workers (ECS EC2 / EKS with Auto-Scaling)**:
   Deploy `docker/Dockerfile.gpu` with GPU instances (`g5.4xlarge` with 24GB VRAM or `p4d.24xlarge` for 80GB A100s).
   Configure target-tracking scaling based on Celery/Redis queue depth.

---

## 4. Google Cloud Platform (GKE + Cloud Storage + Cloud SQL)

1. **GKE Autopilot with GPU Node Pool**:
   ```bash
   gcloud container clusters create videogen-cluster \
     --region us-central1 \
     --accelerator type=nvidia-l4,count=1
   ```
2. **Cloud Storage**:
   Mount GCS buckets or configure S3-compatible interoperability keys.

---

## 5. Local GPU Setup for Wan2.1

To run Wan2.1 on a local workstation with NVIDIA RTX 3090/4090 (24GB VRAM):

1. Ensure CUDA 12.1+ and PyTorch are installed:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   pip install diffusers transformers accelerate
   ```
2. Set `.env`:
   ```env
   VIDEO_PROVIDER=wan_local
   USE_CUDA=true
   ```
3. Launch:
   ```bash
   python main.py
   ```
