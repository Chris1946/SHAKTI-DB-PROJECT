@echo off
setlocal enabledelayedexpansion

echo ========================================
echo       🚀 Starting PulseTrace Stack       
echo ========================================

:: 1. Setup Environment
if not exist ".env" (
    echo [+] Creating .env file from .env.example
    copy .env.example .env
)

:: 2. Start Backend & Database
echo [+] Starting PostgreSQL and FastAPI Backend via Docker...
docker compose up -d

echo [+] Waiting 15 seconds for backend to initialize...
timeout /t 15 /nobreak >nul

:: 3. Setup and Run Agent
echo [+] Setting up Python Virtual Environment for the Agent...
cd agent

if not exist ".venv" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo [+] Starting Agent in the background...
:: This starts the python process without a blocking console window
start /B python main.py > agent.log 2>&1

echo ========================================
echo ✅ Success! The PulseTrace Stack is running.
echo    - Backend is at http://localhost:8000
echo    - Agent is collecting metrics in the background (see agent\agent.log)
echo.
echo 👉 You can now download and open the Native Desktop App!
echo ========================================
