-- ============================================================
-- PulseTrace — PostgreSQL Docker Init Script
-- ============================================================
-- This script runs automatically when the PostgreSQL container
-- starts for the first time. It creates the ShakthiDB schema.
-- ============================================================

-- The database is already created by POSTGRES_DB env var.
-- We just need to create the tables.

\i /docker-entrypoint-initdb.d/schema.sql
