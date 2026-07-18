import asyncio
import asyncpg
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def main():
    try:
        conn = await asyncpg.connect('postgresql://postgres@localhost:5432/shakthidb')
        
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public';")
        print(f"\n--- Tables in public schema ---")
        for t in tables:
            print(f"- {t['tablename']}")
        
        for table in tables:
            t_name = table['tablename']
            if t_name == "alembic_version": continue
            print(f"\n--- Top 3 rows from {t_name} ---")
            try:
                rows = await conn.fetch(f"SELECT * FROM {t_name} ORDER BY timestamp DESC LIMIT 3;")
            except asyncpg.exceptions.UndefinedColumnError:
                rows = await conn.fetch(f"SELECT * FROM {t_name} ORDER BY id DESC LIMIT 3;")
                
            for row in rows:
                print(json.dumps(dict(row), cls=DateTimeEncoder, indent=2))

        await conn.close()
    except Exception as e:
        print(f"Error connecting to postgres: {e}")

asyncio.run(main())
