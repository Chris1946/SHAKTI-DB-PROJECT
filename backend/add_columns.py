import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://pulsetrace:changeme@localhost:5432/shakthidb")
    try:
        await conn.execute("ALTER TABLE system_metrics ADD COLUMN IF NOT EXISTS cpu_temp_current DOUBLE PRECISION")
        await conn.execute("ALTER TABLE system_metrics ADD COLUMN IF NOT EXISTS cpu_temp_high DOUBLE PRECISION")
        await conn.execute("ALTER TABLE system_metrics ADD COLUMN IF NOT EXISTS cpu_temp_critical DOUBLE PRECISION")
        await conn.execute("ALTER TABLE system_metrics ADD COLUMN IF NOT EXISTS cpu_throttled BOOLEAN")
        print("Columns added successfully")
    except Exception as e:
        print("Error:", e)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
