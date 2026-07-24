"""
routers/chat.py
----------------
HTTP layer for the "✨ Generate a game" chat feature — thin wrapper around
orchestrator.run_turn, same pattern as routers/az900.py's relationship to
learning/service.py.
"""

from fastapi import APIRouter

from .. import orchestrator, session_store
from ..models import ChatRequest, ChatResponse, HistoryMessage, HistoryResponse

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    reply, game_ready, game_id, game_type, domain = orchestrator.run_turn(req.session_id, req.message)
    return ChatResponse(
        reply=reply, game_ready=game_ready, game_id=game_id, game_type=game_type, domain=domain
    )


@router.get("/api/history/{session_id}", response_model=HistoryResponse)
def get_history(session_id: str) -> HistoryResponse:
    """Return just the user/assistant turns, for restoring the chat UI on page load."""
    raw = session_store.get_history(session_id)
    messages = [
        HistoryMessage(role=m["role"], content=m["content"])
        for m in raw
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    return HistoryResponse(messages=messages)
