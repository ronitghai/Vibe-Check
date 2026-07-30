"""
tools.py
--------
Tool schemas and dispatcher for launching structured template activities or
creating entirely new game mechanics.

Known mechanics such as Jeopardy use reliable HTML templates. The model
generates only their structured educational content.

generate_custom_game remains available for genuinely original mechanics that
do not match an existing template.
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
                "Launch a reliable pre-built AZ-900 learning-game template "
                "populated with personalized educational content. Use this "
                "for quizzes, scenarios, matching, crosswords, and Jeopardy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "enum": GAME_IDS,
                    },
                    "domain": {
                        "type": "string",
                        "enum": DOMAINS,
                        "description": (
                            "The AZ-900 domain tested by the activity."
                        ),
                    },
                    "config": {
                        "type": "object",
                        "description": (
                            "Complete game-specific educational content. "
                            "For jeopardy, provide title and exactly four "
                            "categories with four questions each."
                        ),
                    },
                },
                "required": [
                    "game_id",
                    "domain",
                    "config",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_custom_game",
            "description": (
                "Generate a new browser-game mechanic only when the learner's "
                "request does not match any existing template. Do not use this "
                "for quizzes, scenarios, matching, crosswords, or Jeopardy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "A short game title.",
                    },
                    "domain": {
                        "type": "string",
                        "enum": DOMAINS,
                        "description": (
                            "The AZ-900 domain tested by the game."
                        ),
                    },
                    "spec": {
                        "type": "string",
                        "description": (
                            "A complete description of the original mechanic, "
                            "controls, scoring, progression, completion state, "
                            "feedback, and AZ-900 content."
                        ),
                    },
                },
                "required": [
                    "title",
                    "domain",
                    "spec",
                ],
            },
        },
    },
]


def dispatch(
    session_id: str,
    name: str,
    args: dict,
) -> tuple[str, dict | None]:
    if name == "launch_template_game":
        return _launch_template_game(
            session_id,
            args,
        )

    if name == "generate_custom_game":
        return _generate_custom_game(
            session_id,
            args,
        )

    return (
        json.dumps(
            {
                "error": f"unknown tool '{name}'",
            }
        ),
        None,
    )


def _resolve_domain(
    session_id: str,
    args: dict,
) -> str:
    domain = args.get("domain")

    if domain in DOMAINS:
        return domain

    return learning_store.get_weakest_domain(session_id)


def _launch_template_game(
    session_id: str,
    args: dict,
) -> tuple[str, dict | None]:
    game_id = args.get("game_id")

    if game_id not in registry.GAMES:
        return (
            json.dumps(
                {
                    "error": f"unknown game_id '{game_id}'",
                }
            ),
            None,
        )

    domain = _resolve_domain(
        session_id,
        args,
    )

    supplied_config = args.get("config")

    if not isinstance(supplied_config, dict):
        supplied_config = {}

    merged_config = registry.merge_config(
        game_id,
        supplied_config,
    )

    title = registry.GAMES[game_id]["title"]

    session_store.upsert_game(
        session_id,
        game_id,
        "template",
        title,
        {
            "config": merged_config,
        },
    )

    return (
        json.dumps(
            {
                "status": "launched",
                "game_id": game_id,
                "domain": domain,
            }
        ),
        {
            "game_id": game_id,
            "game_type": "template",
            "domain": domain,
        },
    )


def _generate_custom_game(
    session_id: str,
    args: dict,
) -> tuple[str, dict | None]:
    title = (
        args.get("title")
        or "Custom Game"
    ).strip()

    domain = _resolve_domain(
        session_id,
        args,
    )

    spec = args.get("spec", "")

    html, error = generator.generate_game(
        title,
        spec,
    )

    if html is None:
        return (
            json.dumps(
                {
                    "status": "failed",
                    "reason": error,
                }
            ),
            None,
        )

    slug = (
        "custom_"
        + "".join(
            character.lower()
            if character.isalnum()
            else "_"
            for character in title
        )[:40].strip("_")
    )

    game_id = slug or "custom_game"

    description = (
        spec[:100] + "…"
        if len(spec) > 100
        else spec
    )

    session_store.upsert_game(
        session_id,
        game_id,
        "generated",
        title,
        {
            "html": html,
            "description": description,
        },
    )

    return (
        json.dumps(
            {
                "status": "launched",
                "game_id": game_id,
                "domain": domain,
            }
        ),
        {
            "game_id": game_id,
            "game_type": "generated",
            "domain": domain,
        },
    )