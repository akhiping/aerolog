from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

session_router = APIRouter(prefix="/api/session")


@session_router.post("/start")
async def start_session(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json() if await request.body() else {}
    technician_id = body.get("technician_id", "")
    language = body.get("language", "en")
    session_id = body.get("session_id", str(uuid.uuid4()))

    pipeline = request.app.state.pipeline_manager
    pipeline.set_db(db)
    greeting = await pipeline.start_session(session_id, technician_id, language)

    return {
        "session_id": session_id,
        "greeting": greeting.content,
        "state": greeting.state.value if greeting.state else "LISTENING",
    }


@session_router.post("/{session_id}/input")
async def session_input(session_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text input required")

    pipeline = request.app.state.pipeline_manager
    pipeline.set_db(db)
    responses = await pipeline.process_input(session_id, text)

    return {
        "session_id": session_id,
        "responses": [r.model_dump() for r in responses],
    }


@session_router.post("/{session_id}/end")
async def end_session(session_id: str, request: Request):
    pipeline = request.app.state.pipeline_manager
    session = pipeline.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "finalized": session.finalized,
        "record": session.record.model_dump() if session.record else None,
    }


@session_router.get("/{session_id}/state")
async def get_session_state(session_id: str, request: Request):
    pipeline = request.app.state.pipeline_manager
    session = pipeline.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "state": session.state.value,
        "record": session.record.model_dump(),
        "finalized": session.finalized,
        "language": session.language,
    }
