# 🌐 Open-Source Cloud Deployment Guide for Videogen-Lucy

Videogen-Lucy is designed with an **open-source-first architecture**, allowing you to deploy it on any self-hosted cloud platform, private server, or cloud provider with zero vendor lock-in.

---

## Table of Contents
1. [1-Click Script (Any Linux Server / VPS)](#1-1-click-script-any-linux-server--vps)
2. [Coolify (Self-Hosted Cloud PaaS)](#2-coolify-self-hosted-cloud-paas)
3. [CapRover (Self-Hosted Docker PaaS)](#3-caprover-self-hosted-docker-paas)
4. [Kubernetes (K8s, K3s, MicroK8s, OpenShift)](#4-kubernetes-k8s-k3s-microk8s-openshift)
5. [Dokku (Self-Hosted Mini-Heroku)](#5-dokku-self-hosted-mini-heroku)
6. [Hugging Face Spaces / RunPod / Vast.ai (Cloud GPU)](#6-hugging-face-spaces--runpod--vastai-cloud-gpu)
7. [HashiCorp Nomad](#7-hashicorp-nomad)

---

## 1. 1-Click Script (Any Linux Server / VPS)

Deploy on any Ubuntu/Debian/Rocky Linux cloud instance (Hetzner, DigitalOcean, Linode, OVH, AWS, GCP, etc.):

```bash
# 1. Clone the repository
git clone https://github.com/Rupesh4113/videogen-lucy.git
cd videogen-lucy

# 2. Run the automated cloud setup script
sudo bash deploy/setup_cloud.sh
```

The script automatically installs Docker, NVIDIA Container Toolkit (if a GPU is detected), configures firewall ports, builds the application, and starts the platform on port `8000`.

---

## 2. Coolify (Self-Hosted Cloud PaaS)

[Coolify](https://coolify.io) is an open-source, self-hosted alternative to Heroku/Netlify/Vercel.

### Steps:
1. In your Coolify dashboard, select **Create New Resource** -> **Application** -> **Public Repository**.
2. Enter the repository URL: `https://github.com/Rupesh4113/videogen-lucy.git`.
3. Set **Build Pack** to `Docker Compose` or `Dockerfile` (`docker/Dockerfile.backend`).
4. Set **Port** to `8000`.
5. Under **Persistent Storage**, add a volume mapping:
   - Host path: `/data/videogen-storage`
   - Container path: `/app/storage`
6. Click **Deploy**. Coolify will automatically provision SSL, custom domains, and automatic restarts!

---

## 3. CapRover (Self-Hosted Docker PaaS)

[CapRover](https://caprover.com) is an open-source PaaS for deploying Dockerized apps.

### Steps:
1. In your CapRover dashboard, click **Apps** -> **Create New App** named `videogen`.
2. Check **Has Persistent Data** and mount `/app/storage` to `videogen-data`.
3. Under **Deployment**, choose **Deploy via Dockerfile** using `docker/Dockerfile.backend`.
4. Enable **HTTPS (Let's Encrypt)** with one click.
5. Set Container Port to `8000`.

---

## 4. Kubernetes (K8s, K3s, MicroK8s, OpenShift)

Deploy to any Kubernetes cluster with our pre-configured manifests:

```bash
# 1. Apply namespace, persistent volumes, configmaps, and deployments
kubectl apply -f deploy/k8s/kubernetes-manifest.yaml

# 2. Verify pods are running
kubectl get pods -n videogen-system

# 3. Check service and ingress
kubectl get svc,ingress -n videogen-system
```

---

## 5. Dokku (Self-Hosted Mini-Heroku)

```bash
# On your Dokku server:
dokku apps:create videogen
dokku storage:mount videogen /var/lib/videogen/storage:/app/storage
dokku ports:add videogen 80:8000
dokku git:from-image videogen videogen-lucy:latest
```

---

## 6. Hugging Face Spaces / RunPod / Vast.ai (Cloud GPU)

### RunPod / Vast.ai:
1. Choose a PyTorch 2.2+ CUDA 12 template on a 24GB+ VRAM GPU (RTX 3090/4090 or A10G/A100).
2. Open terminal in the pod:
   ```bash
   git clone https://github.com/Rupesh4113/videogen-lucy.git
   cd videogen-lucy
   pip install -r requirements.txt
   VIDEO_PROVIDER=wan_local USE_CUDA=true python main.py
   ```
3. Expose port `8000` via HTTP/TCP proxy.

---

## 7. HashiCorp Nomad

For Nomad clusters, submit the job:

```bash
nomad job run deploy/nomad/videogen.nomad
```
