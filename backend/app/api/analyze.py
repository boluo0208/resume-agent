from fastapi import APIRouter

from app.agents.resume_analysis_agent import ResumeAnalysisAgent
from app.schemas.analysis import AnalysisRequest, AnalysisResponse

router = APIRouter(prefix="/api", tags=["analysis"])
agent = ResumeAnalysisAgent()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(payload: AnalysisRequest):
    return await agent.run(payload)
