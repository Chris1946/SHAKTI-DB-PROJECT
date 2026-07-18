import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect('postgresql://postgres@localhost:5432/shakthidb')
        print("Connected!")
        await conn.close()
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
