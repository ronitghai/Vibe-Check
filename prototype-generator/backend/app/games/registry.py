"""
registry.py
------------
Maps a game_id (what the frontend/backend pass around everywhere — Game
Menu cards, launch requests, practice results) to its template HTML file
and default config. Two callers depend on this file:

  - learning/service.py's generate_practice_content() looks up a game_id's
    template file and merges its own AZ-900-grounded config on top of
    `defaults` via merge_config() below — so a template's `defaults` are
    what renders if the LLM generation ever fails/times out, same safety
    net every content generator in service.py already has.
  - learning/service.py's record_practice_result() reads `mastery_weight`
    to decide how strongly one game's real score should move the domain
    mastery accumulator (see that function's own docstring for why retrieval/
    application activities count more than quick vocabulary review).

Only mechanics that directly retrieve, apply, or reinforce certification
knowledge are exposed — entertainment-first templates (tic-tac-toe, wheel of
fortune, memory match) were intentionally removed after prototype validation
in favor of these 5.

EACH ENTRY IN GAMES:
  title          — shown on the Game Menu card and in the launched game's title bar.
  file           — the HTML filename under games/library/, loaded by load_template_html().
  description    — shown on the Game Menu card, under the title.
  learning_mode  — a free-text label describing the pedagogical style (retrieval_practice,
                   application_practice, relationship_learning, recall_practice,
                   retrieval_and_application). Purely descriptive right now — nothing reads
                   it programmatically — but keep it accurate if you add a game, since it's
                   the fastest way for a future contributor to understand *why* a game exists
                   without reading its whole template.
  mastery_weight — how strongly this game's real score moves domain_mastery relative to a
                   1.0 baseline (rapid_quiz/scenario_challenge/jeopardy are full-weight
                   "did you actually know this"; matching_game is 0.6 and crossword is 0.35,
                   since correctly matching or filling in a word is a weaker signal of real
                   understanding than answering a cold quiz question). See
                   service.record_practice_result for exactly how this gets applied.
  defaults       — the config a template renders with if nothing else is supplied — either
                   because the LLM-generation path failed (see merge_config below) or because
                   a caller launched the template directly with no content of its own.
"""

import os

LIBRARY_DIR = os.path.join(os.path.dirname(__file__), "library")

GAMES = {
    "rapid_quiz": {
        "title": "Knowledge Check",
        "file": "rapid_quiz.html",
        "description": "Answer targeted AZ-900 questions and receive immediate explanations.",
        "learning_mode": "retrieval_practice",
        "mastery_weight": 1.0,
        "defaults": {"questions": [], "timePerQuestion": 20},
    },
    "scenario_challenge": {
        "title": "Azure Scenario Challenge",
        "file": "scenario_challenge.html",
        "description": "Apply Azure concepts to realistic business and architecture situations.",
        "learning_mode": "application_practice",
        "mastery_weight": 1.0,
        "defaults": {"questions": []},
    },
    "matching_game": {
        "title": "Concept Connections",
        "file": "matching_game.html",
        "description": "Connect Azure services and concepts with the purpose they serve.",
        "learning_mode": "relationship_learning",
        "mastery_weight": 0.6,
        "defaults": {"title": "Match each Azure concept to its purpose", "pairs": []},
    },
    "crossword": {
        "title": "Vocabulary Review",
        "file": "crossword.html",
        "description": "Reinforce important AZ-900 terminology through clue-based recall.",
        "learning_mode": "recall_practice",
        "mastery_weight": 0.35,
        "defaults": {"words": []},
    },
    "jeopardy": {
        "title": "Azure Jeopardy",
        "file": "jeopardy.html",
        "description": (
            "Choose Azure categories and point values, answer questions, "
            "and build your score."
        ),
        "learning_mode": "retrieval_and_application",
        "mastery_weight": 1.0,
        "defaults": {
            "title": "AZ-900 Jeopardy",
            "categories": [
                {
                    "name": "Cloud Models",
                    "questions": [
                        {
                            "value": 100,
                            "question": (
                                "Which cloud model combines public and private "
                                "cloud environments?"
                            ),
                            "choices": [
                                "Public cloud",
                                "Private cloud",
                                "Hybrid cloud",
                                "Community cloud",
                            ],
                            "answerIndex": 2,
                            "explanation": (
                                "Hybrid cloud combines public and private "
                                "cloud environments."
                            ),
                        },
                        {
                            "value": 200,
                            "question": (
                                "Which cloud model is dedicated to one organization?"
                            ),
                            "choices": [
                                "Public cloud",
                                "Private cloud",
                                "Hybrid cloud",
                                "SaaS",
                            ],
                            "answerIndex": 1,
                            "explanation": (
                                "A private cloud is dedicated to a single organization."
                            ),
                        },
                        {
                            "value": 300,
                            "question": (
                                "Which cloud model normally delivers resources "
                                "over the public internet?"
                            ),
                            "choices": [
                                "Public cloud",
                                "Private cloud",
                                "Hybrid cloud",
                                "On-premises only",
                            ],
                            "answerIndex": 0,
                            "explanation": (
                                "Public cloud resources are delivered over the "
                                "internet by a cloud provider."
                            ),
                        },
                        {
                            "value": 400,
                            "question": (
                                "A company combines its datacenter with Azure. "
                                "Which model is this?"
                            ),
                            "choices": [
                                "Public cloud",
                                "Private cloud",
                                "Hybrid cloud",
                                "SaaS",
                            ],
                            "answerIndex": 2,
                            "explanation": (
                                "Combining on-premises infrastructure with public "
                                "cloud services is hybrid cloud."
                            ),
                        },
                    ],
                },
                {
                    "name": "Service Models",
                    "questions": [
                        {
                            "value": 100,
                            "question": (
                                "Which model provides virtual machines, networking, "
                                "and storage?"
                            ),
                            "choices": ["IaaS", "PaaS", "SaaS", "Hybrid cloud"],
                            "answerIndex": 0,
                            "explanation": (
                                "Infrastructure as a Service provides foundational "
                                "compute, storage, and networking."
                            ),
                        },
                        {
                            "value": 200,
                            "question": (
                                "Which model lets developers focus on applications "
                                "while the provider manages the platform?"
                            ),
                            "choices": ["IaaS", "PaaS", "SaaS", "Private cloud"],
                            "answerIndex": 1,
                            "explanation": (
                                "Platform as a Service manages the platform and "
                                "underlying infrastructure."
                            ),
                        },
                        {
                            "value": 300,
                            "question": (
                                "Which model delivers complete applications?"
                            ),
                            "choices": ["IaaS", "PaaS", "SaaS", "CapEx"],
                            "answerIndex": 2,
                            "explanation": (
                                "Software as a Service provides complete applications."
                            ),
                        },
                        {
                            "value": 400,
                            "question": (
                                "Which service model gives customers the most "
                                "operating-system responsibility?"
                            ),
                            "choices": ["SaaS", "PaaS", "IaaS", "Consumption pricing"],
                            "answerIndex": 2,
                            "explanation": (
                                "IaaS customers manage operating systems, applications, "
                                "and data."
                            ),
                        },
                    ],
                },
                {
                    "name": "Cloud Benefits",
                    "questions": [
                        {
                            "value": 100,
                            "question": (
                                "Which benefit helps a service remain accessible "
                                "despite failures?"
                            ),
                            "choices": [
                                "Elasticity",
                                "High availability",
                                "CapEx",
                                "Governance",
                            ],
                            "answerIndex": 1,
                            "explanation": (
                                "High availability helps services remain accessible."
                            ),
                        },
                        {
                            "value": 200,
                            "question": (
                                "Which benefit allows capacity to change as demand changes?"
                            ),
                            "choices": [
                                "Scalability",
                                "Compliance",
                                "CapEx",
                                "Private cloud",
                            ],
                            "answerIndex": 0,
                            "explanation": (
                                "Scalability allows resources to increase or decrease "
                                "with demand."
                            ),
                        },
                        {
                            "value": 300,
                            "question": (
                                "Which term describes rapidly and dynamically "
                                "adjusting resources?"
                            ),
                            "choices": [
                                "Reliability",
                                "Elasticity",
                                "Governance",
                                "SaaS",
                            ],
                            "answerIndex": 1,
                            "explanation": (
                                "Elasticity dynamically expands and reduces resources."
                            ),
                        },
                        {
                            "value": 400,
                            "question": (
                                "Which benefit helps forecast expected performance "
                                "and costs?"
                            ),
                            "choices": [
                                "Predictability",
                                "Availability zone",
                                "IaaS",
                                "Private DNS",
                            ],
                            "answerIndex": 0,
                            "explanation": (
                                "Predictability helps organizations forecast "
                                "performance and costs."
                            ),
                        },
                    ],
                },
                {
                    "name": "Cloud Economics",
                    "questions": [
                        {
                            "value": 100,
                            "question": (
                                "Which term means upfront spending on physical assets?"
                            ),
                            "choices": ["OpEx", "CapEx", "Elasticity", "PaaS"],
                            "answerIndex": 1,
                            "explanation": (
                                "Capital expenditure is upfront investment in "
                                "physical assets."
                            ),
                        },
                        {
                            "value": 200,
                            "question": (
                                "Which term means ongoing spending for operations "
                                "and services?"
                            ),
                            "choices": ["CapEx", "OpEx", "IaaS", "Governance"],
                            "answerIndex": 1,
                            "explanation": (
                                "Operational expenditure is ongoing spending."
                            ),
                        },
                        {
                            "value": 300,
                            "question": (
                                "Which model charges customers according to usage?"
                            ),
                            "choices": [
                                "Capital model",
                                "Consumption-based model",
                                "Private model",
                                "Fixed hardware model",
                            ],
                            "answerIndex": 1,
                            "explanation": (
                                "Consumption-based pricing charges for resources used."
                            ),
                        },
                        {
                            "value": 400,
                            "question": (
                                "Which cloud benefit reduces the need to purchase "
                                "physical datacenter equipment?"
                            ),
                            "choices": [
                                "Increased CapEx",
                                "Reduced infrastructure management",
                                "Manual scaling",
                                "Private networking",
                            ],
                            "answerIndex": 1,
                            "explanation": (
                                "Cloud providers manage physical infrastructure, "
                                "reducing customer maintenance."
                            ),
                        },
                    ],
                },
            ],
        },
    },
}


def list_templates() -> list:
    """Every game_id in GAMES, as the shape the frontend's Game Menu / library
    list expects — title + description only, no config or file path (those
    are internal, only load_template_html/merge_config need them)."""
    return [
        {
            "game_id": game_id,
            "game_type": "template",
            "title": info["title"],
            "description": info["description"],
        }
        for game_id, info in GAMES.items()
    ]


def load_template_html(game_id: str) -> str:
    """Read one game's raw HTML file off disk. Raw — no design-system CSS/JS
    injected yet and no config baked in; that's games/bundle.py's job
    (called separately, after this), which every launch path goes through
    regardless of where the game_id/config came from."""
    path = os.path.join(LIBRARY_DIR, GAMES[game_id]["file"])
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def merge_config(game_id: str, config: dict) -> dict:
    """Overlay `config` on top of this game_id's `defaults`, key by key —
    NOT a shallow dict merge that would silently keep an empty/falsy value
    from `config` and hide the default underneath it. Any key in `config`
    that's None/""/[]/{} is treated as "didn't actually supply this" and the
    default shows through instead — this is what makes a partial or failed
    LLM generation degrade gracefully to real, curated content instead of a
    game rendering half-empty (see every content generator in
    learning/service.py, which all funnel through this one function)."""
    defaults = GAMES[game_id]["defaults"]
    config = config or {}
    merged = dict(defaults)
    for key, value in config.items():
        if value not in (None, "", [], {}):
            merged[key] = value
    return merged
