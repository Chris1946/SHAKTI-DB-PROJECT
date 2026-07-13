#!/usr/bin/env bash
# ============================================================
# PulseTrace — Start Development Stack
# ============================================================
# Starts PostgreSQL, Backend, and optionally the Agent.
# Usage:
#   ./scripts/start-dev.sh          # Start DB + Backend
#   ./scripts/start-dev.sh --agent  # Start DB + Backend + Agent
#   ./scripts/start-dev.sh --stop   # Stop everything
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# ---- Stop mode ----
if [[ "${1:-}" == "--stop" ]]; then
    echo "Stopping PulseTrace stack..."
    docker compose down
    echo "✓ Stack stopped"
    exit 0
fi

# ---- Check .env ----
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Run ./scripts/setup.sh first."
    exit 1
fi

# ---- Start PostgreSQL ----
echo "============================================================"
echo "  Starting PulseTrace Development Stack"
echo "============================================================"
echo ""
echo "[1/3] Starting PostgreSQL (ShakthiDB)..."
docker compose up -d postgres
echo "  ✓ PostgreSQL starting on port ${POSTGRES_PORT:-5432}"

# Wait for PostgreSQL to be healthy
echo "  Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-pulsetrace}" -d "${POSTGRES_DB:-shakthidb}" &> /dev/null; then
        echo "  ✓ PostgreSQL is ready"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ✗ PostgreSQL failed to start in 30 seconds"
        exit 1
    fi
    sleep 1
done

# ---- Start Backend ----
echo ""
echo "[2/3] Starting FastAPI Backend..."

# Check if running via Docker or locally
if [[ "${USE_DOCKER_BACKEND:-false}" == "true" ]]; then
    docker compose up -d backend
    echo "  ✓ Backend starting in Docker on port ${BACKEND_PORT:-8000}"
else
    # Run locally for hot-reload development
    cd "$PROJECT_ROOT/backend"
    if [ ! -d ".venv" ]; then
        echo "  ✗ Backend venv not found. Run ./scripts/setup.sh first."
        exit 1
    fi

    # Source .env for local development
    set -a
    source "$PROJECT_ROOT/.env"
    # Override DB host for local development (Docker network → localhost)
    export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT:-5432}/${POSTGRES_DB}"
    set +a

    echo "  Starting uvicorn with hot-reload..."
    source .venv/bin/activate
    uvicorn app.main:app --reload --host 0.0.0.0 --port "${BACKEND_PORT:-8000}" &
    BACKEND_PID=$!
    echo "  ✓ Backend started (PID: $BACKEND_PID) on port ${BACKEND_PORT:-8000}"
    cd "$PROJECT_ROOT"
fi

# Wait for backend health check
echo "  Waiting for backend to be ready..."
sleep 3
for i in $(seq 1 20); do
    if curl -s "http://localhost:${BACKEND_PORT:-8000}/api/v1/health" > /dev/null 2>&1; then
        echo "  ✓ Backend is healthy"
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "  ⚠ Backend health check failed — check logs"
    fi
    sleep 1
done

# ---- Optionally start Agent ----
if [[ "${1:-}" == "--agent" ]]; then
    echo ""
    echo "[3/3] Starting Monitoring Agent..."
    cd "$PROJECT_ROOT/agent"
    if [ ! -d ".venv" ]; then
        echo "  ✗ Agent venv not found. Run ./scripts/setup.sh first."
        exit 1
    fi

    source .venv/bin/activate
    python main.py &
    AGENT_PID=$!
    echo "  ✓ Agent started (PID: $AGENT_PID)"
    cd "$PROJECT_ROOT"
else
    echo ""
    echo "[3/3] Agent not started (use --agent flag to auto-start)"
fi

# ---- Summary ----
echo ""
echo "============================================================"
echo "  PulseTrace is running!"
echo "============================================================"
echo ""
echo "  Services:"
echo "    PostgreSQL:  localhost:${POSTGRES_PORT:-5432} (ShakthiDB)"
echo "    Backend:     http://localhost:${BACKEND_PORT:-8000}"
echo "    API Docs:    http://localhost:${BACKEND_PORT:-8000}/docs"
echo "    Health:      http://localhost:${BACKEND_PORT:-8000}/api/v1/health"
echo ""
echo "  Quick test:"
echo "    curl http://localhost:${BACKEND_PORT:-8000}/api/v1/health"
echo ""
echo "  To stop:"
echo "    ./scripts/start-dev.sh --stop"
echo ""
