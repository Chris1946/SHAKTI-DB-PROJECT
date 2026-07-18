from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM Providers (Grok, OpenAI, Claude, etc).
    """

    @abstractmethod
    async def generate_narration(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Generate a response based on the system and user prompts.
        
        Args:
            system_prompt: High level instructions and constraints.
            user_prompt: The specific context and question.
            
        Returns:
            The generated string, or None if the call failed.
        """
        pass
