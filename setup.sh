#!/bin/bash
# ============================================================
#  LLM Self-Hosting Stack — Quick Setup Script
#  Tested on Ubuntu 22.04 LTS with NVIDIA GPU
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# --- Pre-flight checks ---
echo "============================================"
echo "  LLM Self-Hosting Stack — Setup"
echo "============================================"
echo ""

[[ $EUID -ne 0 ]] && error "Run as root: sudo ./setup.sh"

# --- 1. System Update ---
log "Updating system packages..."
apt update && apt upgrade -y -q

# --- 2. Docker ---
if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable --now docker
    log "Docker installed"
else
    log "Docker already installed: $(docker --version)"
fi

# --- 3. NVIDIA Drivers ---
if ! command -v nvidia-smi &>/dev/null; then
    warn "NVIDIA drivers not found. Installing..."
    apt install -y nvidia-driver-535
    warn "REBOOT REQUIRED after driver install. Run this script again after reboot."
    read -p "Reboot now? [y/N]: " -n 1 -r
    [[ $REPLY =~ ^[Yy]$ ]] && reboot
else
    log "NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
fi

# --- 4. NVIDIA Container Toolkit ---
if ! dpkg -l | grep -q nvidia-container-toolkit; then
    log "Installing NVIDIA Container Toolkit..."
    distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L "https://nvidia.github.io/libnvidia-container/${distribution}/libnvidia-container.list" | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt update && apt install -y nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
    log "NVIDIA Container Toolkit installed"
else
    log "NVIDIA Container Toolkit already installed"
fi

# --- 5. Create project directory ---
PROJECT_DIR="/opt/llm-stack"
mkdir -p "$PROJECT_DIR"
cp docker-compose.yml "$PROJECT_DIR/" 2>/dev/null || warn "docker-compose.yml not found in current dir"
cp .env.example "$PROJECT_DIR/.env" 2>/dev/null || true
log "Project directory: $PROJECT_DIR"

# --- 6. Nginx ---
if ! command -v nginx &>/dev/null; then
    log "Installing Nginx..."
    apt install -y nginx
fi
cp nginx/ollama.conf /etc/nginx/sites-available/ollama 2>/dev/null || warn "Nginx config not found"
ln -sf /etc/nginx/sites-available/ollama /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
log "Nginx configured"

# --- 7. SSL Certificate ---
if ! command -v certbot &>/dev/null; then
    log "Installing Certbot..."
    apt install -y certbot python3-certbot-nginx
fi
warn "Run manually: certbot --nginx -d your-domain.com"

# --- 8. Firewall ---
log "Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 11434/tcp  # Block direct Ollama access
ufw --force enable
log "Firewall configured"

# --- 9. Cron for health checks ---
CRON_LINE="*/5 * * * * /usr/bin/python3 $PROJECT_DIR/scripts/health_check.py >> /var/log/llm-health.log 2>&1"
(crontab -l 2>/dev/null | grep -v "health_check" ; echo "$CRON_LINE") | crontab -
log "Health check cron added (every 5 min)"

# --- 10. Start Stack ---
cd "$PROJECT_DIR"
log "Starting LLM stack..."
docker compose up -d

echo ""
echo "============================================"
echo "  ✅ Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit /opt/llm-stack/.env"
echo "  2. Run: certbot --nginx -d your-domain.com"
echo "  3. Pull models: docker exec ollama-server ollama pull llama3"
echo "  4. Access WebUI: https://your-domain.com"
echo "============================================"
