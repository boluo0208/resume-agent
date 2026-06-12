from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.api.analyze import router as analyze_router
from app.api.parse import router as parse_router
from app.services.llm_service import LLMService

app = FastAPI(
    title="Resume Agent API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(parse_router)


@app.get("/")
def root():
    return {
        "name": "Resume Agent API",
        "frontend": "http://localhost:5173",
        "docs": "http://localhost:8000/docs",
        "health": "/api/health",
        "analyze": "POST /api/analyze",
        "parse": "POST /api/resume/parse",
        "parse_image": "POST /api/resume/parse-image",
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/llm/status")
def llm_status():
    llm = LLMService()
    return {
        "enabled": llm.available,
        "mode": "llm" if llm.available else "mock",
        "base_url": llm.base_url if llm.available else None,
        "model": llm.model if llm.available else None,
    }
