import asyncio
from app.services.llm_narrator import LLMNarrator
async def main():
    n = LLMNarrator()
    print("API KEY:", n.api_key)
    res = await n.generate_narration({"alert_id": 192, "message": "High memory usage", "top_processes": [{"pid": 1234, "name": "Chrome", "memory": 40.5}]})
    print("RESULT:")
    print(res)
asyncio.run(main())
