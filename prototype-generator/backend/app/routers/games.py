from fastapi import APIRouter, HTTPException

from .. import session_store
from ..games import bundle, registry
from ..models import GameBundleResponse, LaunchGameRequest, LibraryItem, LibraryResponse

router = APIRouter()


@router.get("/api/library/{session_id}", response_model=LibraryResponse)
def get_library(session_id: str) -> LibraryResponse:
    """The 7 built-in templates (always available) plus any games generated in this session."""
    items = [LibraryItem(**item) for item in registry.list_templates()]
    items += [LibraryItem(**item) for item in session_store.list_generated_games(session_id)]
    return LibraryResponse(items=items)


@router.get("/api/games/{session_id}/{game_id}", response_model=GameBundleResponse)
def get_game(session_id: str, game_id: str) -> GameBundleResponse:
    stored = session_store.get_game(session_id, game_id)

    if stored:
        if stored["game_type"] == "template":
            html = registry.load_template_html(game_id)
            html = bundle.inject(html, stored["config"])
        else:
            html = bundle.inject(stored["html"])
        return GameBundleResponse(
            game_id=game_id, game_type=stored["game_type"], title=stored["title"], html=html
        )

    if game_id in registry.GAMES:
        info = registry.GAMES[game_id]
        html = registry.load_template_html(game_id)
        html = bundle.inject(html, registry.merge_config(game_id, {}))
        return GameBundleResponse(game_id=game_id, game_type="template", title=info["title"], html=html)

    raise HTTPException(status_code=404, detail="Unknown game for this session")


@router.post("/api/games/launch", response_model=GameBundleResponse)
def launch_game(req: LaunchGameRequest) -> GameBundleResponse:
    """Instant-launch a template with default content — no LLM round-trip."""
    if req.game_id not in registry.GAMES:
        raise HTTPException(status_code=404, detail=f"Unknown template game_id '{req.game_id}'")

    info = registry.GAMES[req.game_id]
    config = registry.merge_config(req.game_id, {})
    session_store.upsert_game(req.session_id, req.game_id, "template", info["title"], {"config": config})

    html = bundle.inject(registry.load_template_html(req.game_id), config)
    return GameBundleResponse(game_id=req.game_id, game_type="template", title=info["title"], html=html)
