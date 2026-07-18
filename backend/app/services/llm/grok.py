import logging
from typing import Optional
from openai import AsyncOpenAI
import httpx

from app.config import settings
from .provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class GrokProvider(BaseLLMProvider):
    """
    LLM Provider using Groq's API with the OpenAI SDK.
    Provides fast LPU inference.
    """

    def __init__(self):
        # Fallback to GROQ_API_KEY environment variable if llm_api_key isn't explicitly set
        import os
        api_key = settings.llm_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("No API key found for GrokProvider. Narration will fail.")
            self.client = None
            return

        # Initialize AsyncOpenAI client configured for Groq
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=httpx.Timeout(settings.llm_timeout),
        )

    async def generate_narration(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self.client:
            return None

        try:
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
                max_tokens=settings.llm_max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Grok API call failed: {type(e).__name__} - {e}")
            return None
