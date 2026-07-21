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
