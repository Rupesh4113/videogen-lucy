#!/usr/bin/env bash
# ==============================================================================
# Videogen-Lucy: 1-Click Open-Source Cloud Deployment Script
# Supports: Ubuntu, Debian, Rocky Linux, AlmaLinux, Arch Linux
# Deploys on: Hetzner, DigitalOcean, Linode, OVH, AWS, GCP, Azure, or On-Prem
# ==============================================================================

set -e

echo "======================================================================"
echo "🎬 VIDEOGEN-LUCY: AUTOMATED CLOUD DEPLOYMENT INITIALIZER"
echo "======================================================================"

# 1. Detect OS and Root Permissions
if [ "$EUID" -ne 0 ]; then
  echo "[-] Please run as root or with sudo: sudo bash deploy/setup_cloud.sh"
  exit 1
fi

echo "[+] Updating system packages..."
if command -v apt-get &> /dev/null; then
    apt-get update -y && apt-get upgrade -y
    apt-get install -y curl git python3 python3-pip python3-venv ffmpeg ufw
elif command -v dnf &> /dev/null; then
    dnf update -y
    dnf install -y curl git python3 python3-pip ffmpeg
fi

# 2. Check for NVIDIA GPU & Container Toolkit
echo "[+] Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU Detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)"
    echo "[+] Installing NVIDIA Container Toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg || true
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
      tee /etc/apt/sources.list.d/nvidia-container-toolkit.list || true
    apt-get update && apt-get install -y nvidia-container-toolkit || true
else
    echo "ℹ️ No NVIDIA GPU detected. Running in high-performance CPU orchestration mode."
fi

# 3. Install Docker and Docker Compose
echo "[+] Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "[+] Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# 4. Configure Firewall (UFW)
if command -v ufw &> /dev/null; then
    echo "[+] Configuring firewall ports (80, 443, 8000, 22)..."
    ufw allow 22/tcp || true
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
    ufw allow 8000/tcp || true
    ufw --force enable || true
fi

# 5. Build and Launch Application
echo "[+] Launching Videogen-Lucy via Docker Compose..."
docker compose -f deploy/docker-compose.prod.yml up -d --build

# 6. Final Status
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

echo ""
echo "======================================================================"
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "======================================================================"
echo "Access Videogen-Lucy Web UI at: http://${SERVER_IP}:8000"
echo "API Health check:               http://${SERVER_IP}:8000/api/v1/health"
echo "API Documentation:              http://${SERVER_IP}:8000/docs"
echo "======================================================================"
