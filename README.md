<div align="center">

# 🔍 PulseTrace

### AI-Powered eBPF Latency Analyzer & Root Cause Detection Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev)

*A modular, scalable Linux observability platform for real-time system monitoring, anomaly detection, and root cause analysis.*

</div>

---

## Architecture

```
                    Linux Machine
                          │
                          ▼
               Monitoring Agent (psutil → eBPF)
                          │
                    POST /api/v1/metrics
                          │
                          ▼
                   FastAPI Backend
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
   PostgreSQL (ShakthiDB)          AI Engine
            │                           │
            └─────────────┬─────────────┘
                          ▼
                   React Dashboard
```

**Design principle**: The monitoring agent is a pluggable data source. Replace `psutil` with `eBPF` — zero backend changes.

## Features

- **System Metrics Collection** — CPU, memory, disk, network, processes
- **Real-time Dashboard** — Live graphs with historical playback
- **AI Anomaly Detection** — Rule-based alerts → ML-powered insights
- **Modular Agent** — psutil today, eBPF tomorrow
- **Production Architecture** — Async FastAPI, connection pooling, API versioning
- **Docker-Ready** — Single `docker compose up` deployment

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent | Python + psutil (→ eBPF) |
| Backend | FastAPI + SQLAlchemy (async) |
| Database | PostgreSQL 16 (ShakthiDB) |
| Frontend | React + Vite + Recharts |
| AI | scikit-learn (→ PyTorch) |
| Infra | Docker Compose |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)

### 1. Clone & Configure

```bash
git clone https://github.com/Chris1946/SHAKTI-DB-PROJECT.git
cd SHAKTI-DB-PROJECT
cp .env.example .env
# Edit .env with secure passwords
```

### 2. Start the Stack

```bash
# Start PostgreSQL + Backend
docker compose up -d

# Verify
curl http://localhost:8000/api/v1/health
```

### 3. Run the Agent

```bash
cd agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 4. View Metrics (Native Desktop App)

You don't need to build the UI yourself! We provide pre-compiled executables for Windows, macOS, and Linux.

1. Go to the **Releases** page of this repository.
2. Download the artifact for your OS:
   - **Windows**: `PulseTrace-Windows.zip` (Extract and run `PulseTrace.exe`)
   - **macOS**: `PulseTrace-macOS.dmg` (Mount and drag to Applications)
   - **Linux**: `PulseTrace-Linux.tar.gz` (Extract and run the binary)
3. The Desktop App will automatically connect to your local backend (`http://localhost:8000`) and visualize the live hardware metrics collected by your agent!

## Project Structure

```
PulseTrace/
├── backend/          # FastAPI application
│   └── app/
│       ├── api/      # Versioned REST endpoints
│       ├── database/  # Connection & session management
│       ├── models/   # SQLAlchemy ORM models
│       ├── schemas/  # Pydantic validation schemas
│       ├── services/ # Business logic
│       ├── config.py # Centralized configuration
│       └── main.py   # Application factory
├── agent/            # System monitoring agent
│   ├── collectors/   # Modular metric collectors
│   ├── sender/       # HTTP transport layer
│   └── main.py       # Agent entry point
├── database/         # SQL schemas & migrations
├── frontend/         # React dashboard (Phase 2)
├── ai/               # Anomaly detection (Phase 3)
├── ebpf/             # eBPF programs (Phase 5)
├── docker/           # Dockerfiles & init scripts
├── scripts/          # Dev & deployment scripts
├── tests/            # Test suites
└── docs/             # Documentation
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check + DB status |
| `POST` | `/api/v1/metrics` | Ingest metrics batch |
| `GET` | `/api/v1/metrics` | Query metrics (with filters) |
| `GET` | `/api/v1/metrics/latest` | Latest snapshot per host |
| `GET` | `/api/v1/alerts` | List alerts |
| `PATCH` | `/api/v1/alerts/{id}/resolve` | Resolve an alert |

Full OpenAPI docs available at `http://localhost:8000/docs` when running.

## Roadmap

- [x] **Phase 1**: Data pipeline (Agent → Backend → PostgreSQL)
- [x] **Phase 2**: Native Desktop Dashboard (PySide6) with live visualization
- [x] **Phase 3**: AI anomaly detection & root cause analysis (Integrated in backend)
- [x] **Phase 4**: Docker Compose production deployment & GitHub Actions cross-platform build
- [x] **Phase 5**: Agent deployment (Using `psutil` on macOS due to SIP, eBPF codebase built)
- [ ] **Phase 6**: Developer Intelligence Platform (Interactive OS Sandbox)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**PulseTrace** — Built for engineers who care about what's happening inside their systems.

</div>
