#!/bin/bash
set -e

echo "========================================"
echo "      🚀 Starting PulseTrace Stack       "
echo "========================================"

# 1. Setup Environment
if [ ! -f .env ]; then
    echo "[+] Creating .env file from .env.example"
    cp .env.example .env
fi

# 2. Start Backend & Database
echo "[+] Starting PostgreSQL and FastAPI Backend via Docker..."
docker compose up -d

echo "[+] Waiting 15 seconds for backend to initialize..."
sleep 15

# 3. Setup and Run Agent
echo "[+] Setting up Python Virtual Environment for the Agent..."
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "[+] Starting Agent in the background..."
# Stop any existing agent
pkill -f "python main.py" || true
nohup python main.py > agent.log 2>&1 &

echo "========================================"
echo "✅ Success! The PulseTrace Stack is running."
echo "   - Backend is at http://localhost:8000"
echo "   - Agent is collecting metrics in the background (see agent/agent.log)"
echo ""
echo "👉 You can now download and open the Native Desktop App!"
echo "========================================"
