# ============================================================
# PulseTrace Backend — Multi-stage Dockerfile
# ============================================================
# Stage 1: Install dependencies
# Stage 2: Run the application (slim image)
# ============================================================

# ---- Stage 1: Dependencies ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: Runtime ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime PostgreSQL client library
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code and AI worker
COPY backend/app ./app
COPY backend/ai_worker.py ./ai_worker.py

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/api/v1/health'); r.raise_for_status()"

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
