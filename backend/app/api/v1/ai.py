"""
PulseTrace Backend — AI Analysis API
======================================

POST /api/v1/ai/alerts/{alert_id}/analyze
  → Runs the real DiagnosticEngine against system metrics and
    process snapshots to produce a root cause analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.connection import get_db
from app.models.metrics import Alert
from app.services.diagnostics import DiagnosticEngine
from app.services.llm import LLMNarrator

router = APIRouter(prefix="/ai", tags=["ai"])

# Singleton engine
_engine = DiagnosticEngine()


@router.post("/alerts/{alert_id}/analyze")
async def analyze_alert(
    alert_id: int = Path(..., description="The ID of the alert to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Run real root cause analysis for a specific alert.

    Examines actual system metrics and process snapshots around
    the alert timestamp to identify WHY the system was slow.
    """
    # Fetch the alert
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Run the diagnostic engine
    report = await _engine.analyze(alert, db)
    report_dict = report.to_dict()

    # Attempt to generate LLM narration
    narrator = LLMNarrator(db=db, hostname=alert.hostname)
    llm_explanation = await narrator.generate_narration(report_dict)

    if llm_explanation:
        # Override the template recommendation with the LLM narration
        report_dict["recommendation"] = llm_explanation

    return report_dict

from pydantic import BaseModel
from typing import Dict, Any

class JourneyExplanationRequest(BaseModel):
    packet_type: str
    metadata: Dict[str, Any]
    path: list[str]

@router.post("/explain_journey")
async def explain_journey(
    request: JourneyExplanationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an AI narration for why a packet traversed the OS graph.
    """
    from app.services.llm.grok import GrokProvider
    
    prompt = f"""
    The user is watching a live execution digital twin of their operating system.
    They clicked on a {request.packet_type} packet to ask why it traveled this path.
    
    Packet Path: {' -> '.join(request.path)}
    Packet Metadata: {request.metadata}
    
    Explain what this packet represents, why the kernel routed it through these subsystems, 
    what bottlenecks it might face, and any potential optimizations.
    Keep it concise, accurate, and in an educational tone.
    """
    
    try:
        provider = GrokProvider()
        response = await provider.generate(prompt, max_tokens=300)
        return {"explanation": response}
    except Exception as e:
        return {"explanation": f"Failed to generate explanation: {str(e)}"}

