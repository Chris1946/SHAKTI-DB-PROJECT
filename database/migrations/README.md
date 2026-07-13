# Database Migrations

PulseTrace uses the `database/schema.sql` file for initial schema creation.

For future schema changes, we will use **Alembic** (SQLAlchemy's migration tool).

## Setup (Phase 2+)

```bash
cd backend
alembic init alembic
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Convention

- Migration files go in this directory
- Each migration should be reversible (include downgrade)
- Use descriptive names: `001_add_latency_histograms.sql`
