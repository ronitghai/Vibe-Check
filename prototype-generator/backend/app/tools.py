"""
tools.py
--------
Tool schema exposed to the LLM (Groq function-calling, OpenAI-compatible
shape — same style as chatbot.py's TOOLS) plus the dispatcher that executes
whichever tool the model calls.
"""

import json

from . import session_store
from .codegen import generator
from .games import registry

GAME_IDS = list(registry.GAMES.keys())

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_template_game",
            "description": (
                "Launch one of the 7 pre-built template games in the game panel, "
                "fully populated with content matching the user's request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "enum": GAME_IDS},
                    "config": {
                        "type": "object",
                        "description": (
                            "Game-specific content, as described for this game_id in the "
                            "system prompt (e.g. quiz questions, crossword words/clues, a "
                            "phrase, matching pairs). Always write real content, never leave "
                            "placeholders."
                        ),
                    },
                },
                "required": ["game_id", "config"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_custom_game",
            "description": (
                "Generate a brand-new simple browser game from scratch, for requests that "
                "don't fit any of the 7 template games."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short game title."},
                    "spec": {
                        "type": "string",
                        "description": (
                            "Clear natural-language description: core mechanic, controls, "
                            "and win/lose condition. Keep it to ONE simple mechanic."
                        ),
                    },
                },
                "required": ["title", "spec"],
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


def _launch_template_game(session_id: str, args: dict) -> tuple[str, dict | None]:
    game_id = args.get("game_id")
    if game_id not in registry.GAMES:
        return json.dumps({"error": f"unknown game_id '{game_id}'"}), None

    merged_config = registry.merge_config(game_id, args.get("config") or {})
    title = registry.GAMES[game_id]["title"]
    session_store.upsert_game(session_id, game_id, "template", title, {"config": merged_config})
    return (
        json.dumps({"status": "launched", "game_id": game_id}),
        {"game_id": game_id, "game_type": "template"},
    )


def _generate_custom_game(session_id: str, args: dict) -> tuple[str, dict | None]:
    title = (args.get("title") or "Custom Game").strip()
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
        json.dumps({"status": "launched", "game_id": game_id}),
        {"game_id": game_id, "game_type": "generated"},
    )
