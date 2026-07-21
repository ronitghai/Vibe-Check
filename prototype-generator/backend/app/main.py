from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import session_store
from .routers import chat, games

app = FastAPI(title="AI Game Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_store.init_db()

app.include_router(chat.router)
app.include_router(games.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
