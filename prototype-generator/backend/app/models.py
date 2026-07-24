"""
models.py
---------
Pydantic request/response shapes for the chat + library/games endpoints
(routers/chat.py, routers/games.py). The AZ-900-specific equivalents live in
learning/models.py instead — this file is only the general chat/game-bundle
plumbing shared by every launch path (chat, instant-launch, AZ-900 practice).
"""

from typing import List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    game_ready: bool = False
    game_id: Optional[str] = None
    game_type: Optional[str] = None  # "template" | "generated"
    # Which AZ-900 domain the launched game targets (see orchestrator.py) —
    # None when no game was launched this turn. The frontend uses this to
    # wire up real score reporting for chat-generated games, same as a
    # Game Menu practice game (see App.tsx's handleGameLaunchedFromChat).
    domain: Optional[str] = None


class GameBundleResponse(BaseModel):
    game_id: str
    game_type: str
    title: str
    html: str


class LibraryItem(BaseModel):
    game_id: str
    game_type: str  # "template" | "generated"
    title: str
    description: str


class LibraryResponse(BaseModel):
    items: List[LibraryItem]


class LaunchGameRequest(BaseModel):
    session_id: str
    game_id: str


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    messages: List[HistoryMessage]
