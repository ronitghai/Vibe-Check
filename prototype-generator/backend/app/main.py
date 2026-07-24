"""
main.py
-------
FastAPI app entrypoint: CORS, DB init, and router mounting. No business
logic lives here — chat.py/games.py/az900.py own their own endpoints, this
file just wires them together. Run with `uvicorn app.main:app --reload`
from backend/ (see README.md for full setup on Windows/Mac/Linux).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import session_store
from .learning import store as learning_store
from .routers import az900, chat, games

app = FastAPI(title="AZ-900 Study Companion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_store.init_db()
learning_store.init_db()

app.include_router(chat.router)
app.include_router(games.router)
app.include_router(az900.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
