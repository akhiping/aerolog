from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import init_db
from app.llm.factory import create_llm_provider
from app.rag.engine import RAGEngine
from app.agent.pipeline import AgentPipeline
from app.api.routes import router
from app.api.session import session_router
from app.api.websocket import ws_router, manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AeroLog starting up...")
    await init_db()
    logger.info("Database initialized")

    llm = create_llm_provider(settings)
    logger.info("LLM provider: %s", settings.llm_provider)

    rag = RAGEngine()
    chunk_count = await rag.ingest_directory("manuals")
    logger.info("RAG engine: %d chunks indexed", chunk_count)

    pipeline = AgentPipeline(llm=llm, rag_engine=rag)
    pipeline.set_ws_broadcast(manager.broadcast_to_dashboard)
    app.state.pipeline_manager = pipeline
    app.state.rag_engine = rag
    app.state.llm_provider = llm

    logger.info("AeroLog ready — %s mode", settings.voice_provider)
    yield
    logger.info("AeroLog shutting down")


app = FastAPI(
    title="AeroLog",
    description="Voice Agent for Aircraft Maintenance Logging (MRO)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(session_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "AeroLog",
        "description": "Voice Agent for Aircraft Maintenance Logging",
        "version": "1.0.0",
        "providers": {
            "voice": settings.voice_provider,
            "asr": settings.asr_provider,
            "tts": settings.tts_provider,
            "llm": settings.llm_provider,
        },
        "endpoints": {
            "api_docs": "/docs",
            "session_start": "POST /api/session/start",
            "session_input": "POST /api/session/{id}/input",
            "records": "GET /api/records",
            "metrics": "GET /api/metrics",
            "ws_dashboard": "ws://host/ws/dashboard",
            "ws_session": "ws://host/ws/session/{id}",
            "sse_dashboard": "GET /api/events/dashboard",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
