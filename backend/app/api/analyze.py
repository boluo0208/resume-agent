from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.resume_analysis_agent import ResumeAnalysisAgent
from app.schemas.analysis import AnalysisRequest, AnalysisResponse

router = APIRouter(prefix="/api", tags=["analysis"])
agent = ResumeAnalysisAgent()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(payload: AnalysisRequest):
    return await agent.run(payload)


@router.post("/analyze/stream")
async def analyze_resume_stream(payload: AnalysisRequest):
    """SSE streaming endpoint — emits agent progress events in real time."""
    async def event_stream():
        async for chunk in agent.run_stream(payload):
            yield chunk.encode("utf-8") if isinstance(chunk, str) else chunk
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
