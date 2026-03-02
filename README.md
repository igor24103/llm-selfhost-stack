# LLM Self-Hosting Stack

> 🤖 Production-ready self-hosted LLM infrastructure with Ollama, Open WebUI, and automated monitoring.

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-LLM%20Server-000000?logo=data:image/svg+xml;base64,PHN2Zy8+)
![Nginx](https://img.shields.io/badge/Nginx-Reverse%20Proxy-009639?logo=nginx&logoColor=white)
![NVIDIA](https://img.shields.io/badge/NVIDIA-GPU%20Accelerated-76B900?logo=nvidia&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ What is this?

A complete, production-ready stack for self-hosting Large Language Models on your own GPU server. Run models like Llama 3, Mistral, and CodeLlama locally with a beautiful web UI — no API costs, full data privacy.

### Key Features

- **🐳 One-command deployment** via Docker Compose
- **🤖 Ollama** — Run any open-source LLM (Llama 3, Mistral, Gemma, etc.)
- **🌐 Open WebUI** — ChatGPT-like interface for your models
- **🔒 Nginx reverse proxy** with SSL, security headers, and rate limiting
- **📊 Health monitoring** — Python script checks GPU, API, disk, containers
- **🔔 Webhook alerts** — Slack/Discord notifications when something goes down
- **🔄 Auto-updates** via Watchtower
- **📦 One-click setup** script for Ubuntu servers

---

## 🏗 Architecture

```
                    ┌─────────────────────────────────────┐
  Internet ───────▶ │         Nginx (SSL + Proxy)         │
                    │  ┌────────────┐  ┌───────────────┐  │
                    │  │ /api/* ──▶ │  │    /* ──▶      │  │
                    │  │ Ollama API │  │  Open WebUI    │  │
                    │  │ :11434     │  │  :8080         │  │
                    │  └────────────┘  └───────────────┘  │
                    └───────────────┬──────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────┐
                    │       Docker Compose Network         │
                    │  ┌─────────┐  ┌──────────┐  ┌─────┐ │
                    │  │ Ollama  │  │ Open     │  │Watch│ │
                    │  │ Server  │  │ WebUI    │  │tower│ │
                    │  │ (GPU)   │  │          │  │     │ │
                    │  └─────────┘  └──────────┘  └─────┘ │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────┐
                    │          NVIDIA GPU (CUDA)           │
                    │     RTX 3090 / 4090 / A100 etc.     │
                    └─────────────────────────────────────┘
```

### Project Structure

```
llm-selfhost-stack/
├── docker-compose.yml       # Ollama + Open WebUI + Watchtower
├── setup.sh                 # One-command Ubuntu setup
├── nginx/
│   └── ollama.conf          # Reverse proxy + SSL + security headers
├── scripts/
│   └── health_check.py      # GPU/API/Container monitoring + alerts
├── docs/
│   └── setup_guide.md       # Detailed setup instructions
├── .env.example             # Environment variables template
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Ubuntu 22.04+ server
- NVIDIA GPU with 16GB+ VRAM
- Docker & Docker Compose
- Domain name (for SSL)

### Option 1: Automated Setup

```bash
git clone https://github.com/yourusername/llm-selfhost-stack.git
cd llm-selfhost-stack
sudo ./setup.sh
```

### Option 2: Manual Setup

```bash
# 1. Clone and configure
git clone https://github.com/yourusername/llm-selfhost-stack.git
cd llm-selfhost-stack
cp .env.example .env
nano .env  # Set your domain and secret key

# 2. Start services
docker compose up -d

# 3. Pull your first model
docker exec ollama-server ollama pull llama3

# 4. Configure Nginx + SSL
sudo cp nginx/ollama.conf /etc/nginx/sites-available/ollama
sudo ln -s /etc/nginx/sites-available/ollama /etc/nginx/sites-enabled/
sudo certbot --nginx -d ai.yourdomain.com
sudo nginx -t && sudo systemctl reload nginx
```

### Pull Models

```bash
# Lightweight & fast
docker exec ollama-server ollama pull llama3        # 8B params, ~5GB
docker exec ollama-server ollama pull mistral       # 7B params, ~4GB

# Code specialist
docker exec ollama-server ollama pull codellama     # 7B params, ~4GB

# High quality (needs 48GB+ VRAM)
docker exec ollama-server ollama pull llama3:70b    # 70B params, ~40GB
```

---

## 📊 Monitoring

The health check script monitors 5 components:

```bash
python3 scripts/health_check.py
```

```
==================================================
  LLM Server Health Check — 2024-03-15 14:30:00
==================================================

🤖 Ollama API...
  ✅ Online — 3 models: llama3, mistral, codellama
🌐 Open WebUI...
  ✅ Online — HTTP 200
🎮 GPU Status...
  🟢 NVIDIA RTX 4090: 42°C | GPU 15% | VRAM 8192/24576MB (33.3%)
🐳 Docker Containers...
  ✅ ollama-server: Up 3 days (healthy)
  ✅ open-webui: Up 3 days
  ✅ watchtower: Up 3 days
💾 Disk Usage...
  📊 45G / 200G (23% used, 155G free)

==================================================
  ✅ All systems operational
==================================================
```

### Automated Monitoring

Add to crontab for continuous monitoring:

```bash
# Run every 5 minutes
*/5 * * * * /usr/bin/python3 /opt/llm-stack/scripts/health_check.py >> /var/log/llm-health.log 2>&1
```

Set `WEBHOOK_URL` in `.env` for Slack/Discord alerts when services go down.

---

## 🔒 Security

| Feature | Implementation |
|---------|---------------|
| **HTTPS** | Let's Encrypt via Certbot, auto-renewal |
| **HSTS** | 1-year strict transport security |
| **Headers** | X-Frame-Options, X-Content-Type-Options, CSP |
| **Firewall** | UFW: only 22, 80, 443 open; Ollama port blocked |
| **Auth** | Open WebUI built-in authentication |
| **Internal only** | Ollama binds to 127.0.0.1 — not exposed to internet |
| **Rate limiting** | Configurable Nginx rate limiting on API endpoints |

---

## 🔧 Configuration

### Supported Models

| Model | Size | VRAM | Best For |
|-------|------|------|----------|
| Llama 3 (8B) | ~5GB | 8GB | General chat, fast responses |
| Mistral (7B) | ~4GB | 8GB | Code generation, analysis |
| CodeLlama (7B) | ~4GB | 8GB | Programming assistance |
| Gemma (7B) | ~5GB | 8GB | Balanced performance |
| Llama 3 (70B) | ~40GB | 48GB | Maximum quality |

### GPU Requirements

| GPU | VRAM | Recommended Models |
|-----|------|--------------------|
| RTX 3060 | 12GB | 7B models |
| RTX 3090 | 24GB | 7B-13B models |
| RTX 4090 | 24GB | 7B-13B models (faster) |
| A100 | 80GB | Up to 70B models |

---

## 📄 License

MIT License — free to use, modify, and distribute.
