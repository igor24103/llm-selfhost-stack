#!/usr/bin/env python3
"""
LLM Server Health Monitor
Checks Ollama API, GPU status, and Open WebUI availability.
Sends alerts via webhook if any service is down.
"""
import subprocess
import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime


# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
WEBUI_URL = os.environ.get("WEBUI_URL", "http://localhost:8080")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
VRAM_THRESHOLD = 90  # Alert if GPU VRAM usage exceeds this %


def check_ollama() -> dict:
    """Check Ollama API health and list loaded models"""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return {"status": "ok", "models": models, "count": len(models)}
    except urllib.error.URLError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_webui() -> dict:
    """Check Open WebUI availability"""
    try:
        req = urllib.request.Request(WEBUI_URL, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "ok", "code": resp.status}
    except urllib.error.URLError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_gpu() -> dict:
    """Check NVIDIA GPU status via nvidia-smi"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"status": "error", "error": result.stderr.strip()}

        gpus = []
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 5:
                name, temp, util, mem_used, mem_total = parts
                vram_pct = round(float(mem_used) / float(mem_total) * 100, 1) if float(mem_total) > 0 else 0
                gpus.append({
                    "name": name,
                    "temp_c": int(temp),
                    "gpu_util": f"{util}%",
                    "vram_used_mb": int(float(mem_used)),
                    "vram_total_mb": int(float(mem_total)),
                    "vram_pct": vram_pct
                })
        return {"status": "ok", "gpus": gpus}
    except FileNotFoundError:
        return {"status": "skipped", "error": "nvidia-smi not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_docker() -> dict:
    """Check Docker containers status"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=10
        )
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                containers.append({
                    "name": parts[0],
                    "status": parts[1] if len(parts) > 1 else "unknown",
                    "ports": parts[2] if len(parts) > 2 else ""
                })
        return {"status": "ok", "containers": containers}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_disk() -> dict:
    """Check disk usage for model storage"""
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            return {
                "status": "ok",
                "total": parts[1],
                "used": parts[2],
                "available": parts[3],
                "use_pct": parts[4]
            }
        return {"status": "error", "error": "Could not parse df output"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def send_alert(message: str):
    """Send alert via webhook (Slack/Discord compatible)"""
    if not WEBHOOK_URL:
        return
    payload = json.dumps({"text": f"🚨 LLM Server Alert\n{message}"}).encode()
    try:
        req = urllib.request.Request(
            WEBHOOK_URL, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  ⚠ Alert send failed: {e}")


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"  LLM Server Health Check — {timestamp}")
    print(f"{'='*50}\n")

    alerts = []
    all_ok = True

    # 1. Ollama API
    print("🤖 Ollama API...")
    ollama = check_ollama()
    if ollama["status"] == "ok":
        print(f"  ✅ Online — {ollama['count']} models: {', '.join(ollama['models'])}")
    else:
        print(f"  ❌ DOWN — {ollama.get('error', 'Unknown')}")
        alerts.append(f"Ollama API is down: {ollama.get('error')}")
        all_ok = False

    # 2. Open WebUI
    print("🌐 Open WebUI...")
    webui = check_webui()
    if webui["status"] == "ok":
        print(f"  ✅ Online — HTTP {webui['code']}")
    else:
        print(f"  ❌ DOWN — {webui.get('error', 'Unknown')}")
        alerts.append(f"Open WebUI is down: {webui.get('error')}")
        all_ok = False

    # 3. GPU
    print("🎮 GPU Status...")
    gpu = check_gpu()
    if gpu["status"] == "ok":
        for g in gpu["gpus"]:
            status_icon = "🟢" if g["vram_pct"] < VRAM_THRESHOLD else "🟡"
            print(f"  {status_icon} {g['name']}: {g['temp_c']}°C | GPU {g['gpu_util']} | VRAM {g['vram_used_mb']}/{g['vram_total_mb']}MB ({g['vram_pct']}%)")
            if g["vram_pct"] >= VRAM_THRESHOLD:
                alerts.append(f"GPU VRAM at {g['vram_pct']}% ({g['name']})")
    elif gpu["status"] == "skipped":
        print(f"  ⏭ Skipped (no nvidia-smi)")
    else:
        print(f"  ❌ Error — {gpu.get('error')}")

    # 4. Docker
    print("🐳 Docker Containers...")
    docker = check_docker()
    if docker["status"] == "ok":
        for c in docker["containers"]:
            is_healthy = "Up" in c["status"]
            icon = "✅" if is_healthy else "❌"
            print(f"  {icon} {c['name']}: {c['status']}")
            if not is_healthy:
                alerts.append(f"Container '{c['name']}' is not healthy: {c['status']}")
                all_ok = False
    else:
        print(f"  ❌ Error — {docker.get('error')}")

    # 5. Disk
    print("💾 Disk Usage...")
    disk = check_disk()
    if disk["status"] == "ok":
        print(f"  📊 {disk['used']} / {disk['total']} ({disk['use_pct']} used, {disk['available']} free)")
    else:
        print(f"  ⏭ Skipped — {disk.get('error')}")

    # Summary
    print(f"\n{'='*50}")
    if all_ok:
        print("  ✅ All systems operational")
    else:
        print(f"  🚨 {len(alerts)} issue(s) detected")
        for alert in alerts:
            print(f"    • {alert}")
        send_alert("\n".join(f"• {a}" for a in alerts))
    print(f"{'='*50}\n")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
