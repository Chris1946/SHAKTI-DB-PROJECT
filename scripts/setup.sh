#!/usr/bin/env bash
# ============================================================
# PulseTrace — Development Setup Script
# ============================================================
# Run once to set up the development environment:
#   chmod +x scripts/setup.sh && ./scripts/setup.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================================"
echo "  PulseTrace — Development Setup"
echo "============================================================"
echo ""

# ---- .env file ----
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "[1/4] Creating .env from template..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"

    # Generate secure random values
    RANDOM_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
    RANDOM_API_KEY=$(python3 -c "import uuid; print(str(uuid.uuid4()))")

    # Replace placeholder values (macOS-compatible sed)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/changeme_use_strong_password/$RANDOM_PASSWORD/g" "$PROJECT_ROOT/.env"
        sed -i '' "s/changeme_generate_a_uuid/$RANDOM_API_KEY/g" "$PROJECT_ROOT/.env"
    else
        sed -i "s/changeme_use_strong_password/$RANDOM_PASSWORD/g" "$PROJECT_ROOT/.env"
        sed -i "s/changeme_generate_a_uuid/$RANDOM_API_KEY/g" "$PROJECT_ROOT/.env"
    fi

    echo "  ✓ .env created with secure random credentials"
    echo "  ⚠ Review and customize: $PROJECT_ROOT/.env"
else
    echo "[1/4] .env already exists — skipping"
fi

# ---- Backend virtual environment ----
echo ""
echo "[2/4] Setting up backend Python environment..."
cd "$PROJECT_ROOT/backend"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  ✓ Virtual environment created"
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "  ✓ Backend dependencies installed"
deactivate

# ---- Agent virtual environment ----
echo ""
echo "[3/4] Setting up agent Python environment..."
cd "$PROJECT_ROOT/agent"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  ✓ Virtual environment created"
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "  ✓ Agent dependencies installed"
deactivate

# ---- Docker check ----
echo ""
echo "[4/4] Checking Docker..."
if command -v docker &> /dev/null; then
    echo "  ✓ Docker: $(docker --version)"
    if command -v docker compose &> /dev/null 2>&1 || docker compose version &> /dev/null 2>&1; then
        echo "  ✓ Docker Compose available"
    else
        echo "  ⚠ Docker Compose not found — install it for full stack"
    fi
else
    echo "  ⚠ Docker not found — install Docker for database and deployment"
fi

# ---- Done ----
echo ""
echo "============================================================"
echo "  Setup complete!"
echo "============================================================"
echo ""
echo "  Next steps:"
echo "    1. Review .env:          cat .env"
echo "    2. Start the stack:      ./scripts/start-dev.sh"
echo "    3. Or manually:"
echo "       docker compose up -d          # Start PostgreSQL + Backend"
echo "       cd agent && source .venv/bin/activate && python main.py"
echo ""
echo "  API docs:  http://localhost:8000/docs"
echo "  Health:    http://localhost:8000/api/v1/health"
echo ""
