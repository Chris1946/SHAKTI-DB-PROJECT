#!/bin/bash
set -e

echo "========================================"
echo "      🚀 Starting PulseTrace Stack       "
echo "========================================"

# --- Dependency Checks ---

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 is not installed."
    read -p "Would you like to try installing Python 3 now? (y/n): " install_py
    if [[ "$install_py" == "y" || "$install_py" == "Y" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "[+] Installing via Homebrew..."
            brew install python
        elif command -v apt-get &> /dev/null; then
            echo "[+] Installing via apt..."
            sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
        else
            echo "[-] Unsupported OS for auto-install. Please install Python 3 manually."
            exit 1
        fi
    else
        echo "[-] Python 3 is required. Exiting."
        exit 1
    fi
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[!] Docker is not installed."
    read -p "Would you like to try installing Docker now? (y/n): " install_docker
    if [[ "$install_docker" == "y" || "$install_docker" == "Y" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "[+] Installing Docker Desktop via Homebrew..."
            brew install --cask docker
            echo "[!] Please open Docker from your Applications folder, complete the setup, and run this script again."
            exit 0
        elif command -v apt-get &> /dev/null; then
            echo "[+] Installing Docker via apt..."
            sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
            sudo systemctl enable --now docker
        else
            echo "[-] Unsupported OS for auto-install. Please install Docker manually."
            exit 1
        fi
    else
        echo "[-] Docker is required. Exiting."
        exit 1
    fi
fi

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
