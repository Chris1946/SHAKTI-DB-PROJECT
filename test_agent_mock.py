import asyncio
import httpx
from datetime import datetime, timezone
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("API_KEY")

async def main():
    batch = {
        "hostname": "test-mock-agent",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "system_metrics": {
            "cpu_percent": 10.5,
            "memory_percent": 45.2,
            "disk_percent": 50.0
        },
        "process_metrics": []
    }
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
        
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:8000/api/v1/metrics", json=batch, headers=headers)
        print("Status:", r.status_code)
        print("Response:", r.text)

asyncio.run(main())
