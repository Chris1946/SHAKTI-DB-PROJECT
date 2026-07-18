import json
import logging
import re
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.memory import UserMemory, SystemMemory, IncidentMemory, KnowledgeMemory
from .provider import BaseLLMProvider
from .grok import GrokProvider

logger = logging.getLogger(__name__)


class AdaptiveContextBuilder:
    """
    Builds RAG context using pgvector from Memory modules.
    """
    def __init__(self, db: AsyncSession, hostname: str):
        self.db = db
        self.hostname = hostname

    async def build_context(self) -> str:
        # 1. Fetch System Profile
        system_profile = ""
        result = await self.db.execute(select(SystemMemory).where(SystemMemory.hostname == self.hostname))
        sys_mem = result.scalar_one_or_none()
        if sys_mem:
            system_profile = f"System Architecture: {sys_mem.architecture}\n"
            system_profile += f"OS: {sys_mem.os_name} {sys_mem.os_version} (Kernel: {sys_mem.kernel_version})\n"
            system_profile += f"Hardware: {sys_mem.cpu_model} ({sys_mem.cpu_cores} Cores), {sys_mem.total_memory} bytes RAM\n"
            if sys_mem.profile:
                system_profile += f"Additional Profile: {json.dumps(sys_mem.profile)}\n"

        # 2. Fetch User Prefs (Mocking user 'default' for now)
        user_prefs = ""
        result = await self.db.execute(select(UserMemory).where(UserMemory.user_id == "default"))
        user_mem = result.scalar_one_or_none()
        if user_mem and user_mem.preferences:
            user_prefs = f"User Preferences: {json.dumps(user_mem.preferences)}\n"

        # 3. RAG: Fetch Top 3 Knowledge Docs (Without embeddings for now, just fetch all or top 3 recent)
        # In a full pgvector implementation, we would embed the alert facts and query:
        # select(KnowledgeMemory).order_by(KnowledgeMemory.embedding.cosine_distance(alert_emb)).limit(3)
        knowledge_context = ""
        result = await self.db.execute(select(KnowledgeMemory).limit(3))
        for k in result.scalars().all():
            knowledge_context += f"Knowledge [{k.topic}]: {k.content}\n"

        # 4. RAG: Fetch Top 3 Similar Incidents
        incident_context = ""
        result = await self.db.execute(
            select(IncidentMemory).where(IncidentMemory.hostname == self.hostname).order_by(IncidentMemory.created_at.desc()).limit(3)
        )
        for inc in result.scalars().all():
            incident_context += f"Past Incident: {inc.explanation}\n"

        context = "=== SYSTEM INTELLIGENCE PROFILE ===\n"
        context += system_profile + "\n"
        context += "=== USER PREFERENCES ===\n"
        context += user_prefs + "\n"
        context += "=== KNOWLEDGE BASE ===\n"
        context += knowledge_context + "\n"
        context += "=== PAST INCIDENTS ===\n"
        context += incident_context + "\n"

        return context


class LLMNarrator:
    """
    Orchestrates RAG context gathering, LLM generation, and validation.
    """

    def __init__(self, db: AsyncSession, hostname: str):
        self.db = db
        self.hostname = hostname
        self.provider = self._init_provider()

    def _init_provider(self) -> BaseLLMProvider:
        if settings.llm_provider.lower() == "grok":
            return GrokProvider()
        # Fallback to Grok
        return GrokProvider()

    async def generate_narration(self, facts: dict) -> Optional[str]:
        """
        Generate a natural language explanation grounded in facts and RAG context.
        """
        if not self.provider:
            return None

        context_builder = AdaptiveContextBuilder(self.db, self.hostname)
        rag_context = await context_builder.build_context()

        system_prompt = (
            "You are an AI-powered Operating System Digital Twin assistant.\n"
            "Your job is to explain WHY anomalies occurred and HOW work flowed through the OS.\n"
            "Always reference the execution path and adapt your recommendations to the hardware characteristics provided.\n"
            "State your limitations if you do not have enough telemetry.\n"
            "DO NOT hallucinate metrics, PIDs, temperatures, or latency numbers. Use ONLY the data provided in the Facts.\n\n"
            f"{rag_context}"
        )

        user_prompt = f"Diagnostic Facts:\n{json.dumps(facts, indent=2)}\n\nGenerate your explanation:"

        narration = await self.provider.generate_narration(system_prompt, user_prompt)
        
        if narration and self.validate_narration(narration, facts):
            # Save the successful incident to memory asynchronously
            await self._save_incident_memory(facts, narration)
            return narration
            
        logger.warning("LLM hallucination detected or API failed. Rejecting output.")
        return None

    def validate_narration(self, narration: str, facts: dict) -> bool:
        """
        Validates that the LLM didn't hallucinate numbers or quoted process names.
        """
        if not narration:
            return False

        facts_str = json.dumps(facts).lower()

        # Validate all numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', narration)
        for num in numbers:
            if num not in facts_str:
                logger.warning(f"Hallucinated number detected: {num}")
                return False

        # Validate quoted strings
        quoted_strings = re.findall(r'["\']([^"\']+)["\']', narration)
        for q_str in quoted_strings:
            if q_str.lower() not in facts_str:
                logger.warning(f"Hallucinated process name detected: {q_str}")
                return False

        return True

    async def _save_incident_memory(self, facts: dict, narration: str):
        """Save this incident to memory for future RAG."""
        try:
            incident = IncidentMemory(
                hostname=self.hostname,
                facts_json=facts,
                explanation=narration,
            )
            self.db.add(incident)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save incident memory: {e}")
            await self.db.rollback()
