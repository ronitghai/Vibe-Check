"""
tools.py
--------
Tool schema exposed to the LLM (Groq function-calling, OpenAI-compatible
shape — same style as chatbot.py's TOOLS) plus the dispatcher that executes
whichever tool the model calls. Both tools require a "domain" argument (one
of the 3 AZ-900 domains) — orchestrator.py's system prompt instructs the
model to pick whichever domain the content it's writing actually tests, and
this file falls back to the session's weakest domain if the model ever omits
it or returns something outside the enum. `dispatch()`'s returned "launched"
dict carries that domain back up to orchestrator.run_turn -> routers/chat.py
-> the frontend, so a chat-launched game can report a real score against a
domain exactly like a Game Menu practice game does (see PlayView.tsx).
"""

import json

from . import session_store
from .codegen import generator
from .games import registry
from .learning import store as learning_store
from .learning.knowledge_base import DOMAINS

GAME_IDS = list(registry.GAMES.keys())

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_template_game",
            "description": (
                "Launch one of the 7 pre-built template games in the game panel, "
                "fully populated with real AZ-900 exam-prep content for the given domain."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "enum": GAME_IDS},
                    "domain": {
                        "type": "string",
                        "enum": DOMAINS,
                        "description": "Which AZ-900 domain this game's content tests.",
                    },
                    "config": {
                        "type": "object",
                        "description": (
                            "Game-specific content, as described for this game_id in the "
                            "system prompt (e.g. quiz questions, crossword words/clues, a "
                            "phrase, matching pairs). Always write real, AZ-900-grounded "
                            "content, never leave placeholders."
                        ),
                    },
                },
                "required": ["game_id", "domain", "config"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_custom_game",
            "description": (
                "Generate a brand-new simple browser game from scratch, for requests that "
                "don't fit any of the 7 template games — still testing real AZ-900 knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short game title."},
                    "domain": {
                        "type": "string",
                        "enum": DOMAINS,
                        "description": "Which AZ-900 domain this game's content tests.",
                    },
                    "spec": {
                        "type": "string",
                        "description": (
                            "Clear natural-language description: core mechanic, controls, "
                            "win/lose condition, AND the specific AZ-900 facts/terms from this "
                            "domain the game should quiz the player on. Keep it to ONE simple "
                            "mechanic."
                        ),
                    },
                },
                "required": ["title", "domain", "spec"],
            },
        },
    },
]


def dispatch(session_id: str, name: str, args: dict) -> tuple[str, dict | None]:
    if name == "launch_template_game":
        return _launch_template_game(session_id, args)
    if name == "generate_custom_game":
        return _generate_custom_game(session_id, args)
    return json.dumps({"error": f"unknown tool '{name}'"}), None


def _resolve_domain(session_id: str, args: dict) -> str:
    """The tool schema's enum should keep the model honest, but a session's
    weakest domain is a safe, always-valid fallback for a missing/garbled
    value rather than letting scoring silently go to the wrong domain."""
    domain = args.get("domain")
    return domain if domain in DOMAINS else learning_store.get_weakest_domain(session_id)


def _launch_template_game(session_id: str, args: dict) -> tuple[str, dict | None]:
    game_id = args.get("game_id")
    if game_id not in registry.GAMES:
        return json.dumps({"error": f"unknown game_id '{game_id}'"}), None

    domain = _resolve_domain(session_id, args)
    merged_config = registry.merge_config(game_id, args.get("config") or {})
    title = registry.GAMES[game_id]["title"]
    session_store.upsert_game(session_id, game_id, "template", title, {"config": merged_config})
    return (
        json.dumps({"status": "launched", "game_id": game_id, "domain": domain}),
        {"game_id": game_id, "game_type": "template", "domain": domain},
    )


def _generate_custom_game(session_id: str, args: dict) -> tuple[str, dict | None]:
    title = (args.get("title") or "Custom Game").strip()
    domain = _resolve_domain(session_id, args)
    spec = args.get("spec", "")

    html, error = generator.generate_game(title, spec)
    if html is None:
        return (
            json.dumps({"status": "failed", "reason": error}),
            None,
        )

    slug = "custom_" + "".join(c.lower() if c.isalnum() else "_" for c in title)[:40].strip("_")
    game_id = slug or "custom_game"
    description = (spec[:100] + "…") if len(spec) > 100 else spec
    session_store.upsert_game(
        session_id, game_id, "generated", title, {"html": html, "description": description}
    )
    return (
        json.dumps({"status": "launched", "game_id": game_id, "domain": domain}),
        {"game_id": game_id, "game_type": "generated", "domain": domain},
    )
