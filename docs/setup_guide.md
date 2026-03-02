# Ollama AI Server — Setup Guide

## Server Requirements
- OS: Ubuntu 22.04 LTS
- GPU: NVIDIA RTX 3090 / 4090 (or similar with 24GB+ VRAM)
- RAM: 32GB+
- Storage: 100GB+ SSD

---

## 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install NVIDIA drivers
sudo apt install -y nvidia-driver-535
sudo reboot

# Verify GPU
nvidia-smi
```

## 2. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

## 3. Download and Configure Models

```bash
# Download Llama 3 (8B) — lightweight, fast responses
ollama pull llama3

# Download Mistral (7B) — good for code and analysis
ollama pull mistral

# Download Llama 3 (70B) — high quality, requires more VRAM
ollama pull llama3:70b
```

## 4. Configure Remote Access

Edit environment:
```bash
sudo systemctl edit ollama.service
```

Add:
```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

Restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## 5. Nginx Reverse Proxy + SSL

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Config: `/etc/nginx/sites-available/ollama`
```nginx
server {
    listen 80;
    server_name ai.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:11434;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long AI responses
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

Enable & SSL:
```bash
sudo ln -s /etc/nginx/sites-available/ollama /etc/nginx/sites-enabled/
sudo certbot --nginx -d ai.yourdomain.com
sudo systemctl restart nginx
```

## 6. Firewall Configuration

```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 11434/tcp    # Block direct Ollama port (use Nginx only)
sudo ufw enable
```

## 7. Install Open WebUI

```bash
docker run -d \
  --name open-webui \
  --network=host \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

Access: `https://ai.yourdomain.com:8080`

## 8. Testing

```bash
# Test API
curl http://localhost:11434/api/generate -d '{
  "model": "llama3",
  "prompt": "Hello, how are you?"
}'

# Check loaded models
ollama list

# Monitor GPU usage
watch -n 1 nvidia-smi
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start Ollama | `sudo systemctl start ollama` |
| Stop Ollama | `sudo systemctl stop ollama` |
| View logs | `journalctl -u ollama -f` |
| List models | `ollama list` |
| Remove model | `ollama rm <model_name>` |
| Update Ollama | `curl -fsSL https://ollama.com/install.sh \| sh` |

---

*If you have any issues, check logs first: `journalctl -u ollama --no-pager -n 50`*
