#!/usr/bin/env bash
# ============================================================
# PulseTrace — ShaktiDB Initialization Script
# ============================================================
# This script runs once via the db-init container to:
#   1. Create the 'shakthidb' database (if it doesn't exist)
#   2. Install required extensions
#   3. Apply the schema
#
# ShaktiDB (IIT Madras PostgreSQL fork) does not support the
# docker-entrypoint-initdb.d convention, so we handle init
# explicitly via this script.
# ============================================================

set -euo pipefail

echo "============================================================"
echo "  PulseTrace — ShaktiDB Schema Initialization"
echo "============================================================"

# Wait for ShaktiDB to accept connections
echo "[1/3] Waiting for ShaktiDB to accept connections..."
for i in $(seq 1 30); do
    if pg_isready -h "$PGHOST" -U "$PGUSER" > /dev/null 2>&1; then
        echo "  ✓ ShaktiDB is accepting connections"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  ✗ ShaktiDB not ready after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Create the database if it doesn't exist
echo "[2/3] Creating database '${PGDATABASE}' if not exists..."
DB_EXISTS=$(psql -h "$PGHOST" -U "$PGUSER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '${PGDATABASE}'" 2>/dev/null || echo "")

if [ "$DB_EXISTS" != "1" ]; then
    psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "CREATE DATABASE ${PGDATABASE};"
    echo "  ✓ Database '${PGDATABASE}' created"
else
    echo "  ✓ Database '${PGDATABASE}' already exists"
fi

# Apply schema
echo "[3/3] Applying schema..."
TABLES_EXIST=$(psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -tAc \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'system_metrics'" 2>/dev/null || echo "0")

if [ "$TABLES_EXIST" = "0" ]; then
    psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -f /schema.sql
    echo "  ✓ Schema applied successfully"
else
    echo "  ✓ Schema already exists (skipping)"
fi

# Verify
echo ""
echo "Tables in ${PGDATABASE}:"
psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -c "\dt"

echo ""
echo "============================================================"
echo "  ShaktiDB initialization complete!"
echo "============================================================"
