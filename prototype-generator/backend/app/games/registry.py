"""
registry.py
-----------
Maps a game_id to its template file and default config. The LLM supplies the
*content* (questions, phrases, pairs, difficulty); the template supplies the
*code*. merge_config() fills in anything the LLM left out with a sane default
so a template never renders empty.
"""

import os

LIBRARY_DIR = os.path.join(os.path.dirname(__file__), "library")

GAMES = {
    "tic_tac_toe": {
        "title": "Tic-Tac-Toe",
        "file": "tic_tac_toe.html",
        "description": "Classic 3x3 grid against a simple AI opponent.",
        "defaults": {
            "difficulty": "medium",
            "playerSymbol": "X",
            "theme": "classic",
        },
    },
    "wheel_of_fortune": {
        "title": "Wheel of Fortune",
        "file": "wheel_of_fortune.html",
        "description": "Guess the hidden phrase, letter by letter.",
        "defaults": {
            "phrase": "PYTHON PROGRAMMING",
            "category": "Technology",
            "maxGuesses": 8,
        },
    },
    "flappy_bird": {
        "title": "Flappy Bird",
        "file": "flappy_bird.html",
        "description": "Tap to flap through a gauntlet of pipes.",
        "defaults": {
            "difficulty": "medium",
            "theme": "sky",
        },
    },
    "memory_match": {
        "title": "Memory Match",
        "file": "memory_match.html",
        "description": "Flip cards to find every matching pair.",
        "defaults": {
            "theme": "Animals",
            "icons": ["🐶", "🐱", "🦊", "🐼", "🐸", "🐵", "🦁", "🐷"],
        },
    },
    "matching_game": {
        "title": "Matching Game",
        "file": "matching_game.html",
        "description": "Pair up related items from two columns.",
        "defaults": {
            "title": "Match the pairs",
            "pairs": [
                {"left": "Sun", "right": "Star"},
                {"left": "Dog", "right": "Bark"},
                {"left": "Cat", "right": "Meow"},
                {"left": "Cow", "right": "Moo"},
            ],
        },
    },
    "crossword": {
        "title": "Crossword",
        "file": "crossword.html",
        "description": "Fill in words from a list of clues.",
        "defaults": {
            "words": [
                {"word": "PYTHON", "clue": "A popular programming language"},
                {"word": "CODE", "clue": "What developers write"},
                {"word": "BUG", "clue": "An error in a program"},
            ],
        },
    },
    "rapid_quiz": {
        "title": "Rapid Quiz",
        "file": "rapid_quiz.html",
        "description": "Kahoot-style timed multiple choice quiz.",
        "defaults": {
            "questions": [
                {"question": "2 + 2 = ?", "choices": ["3", "4", "5", "6"], "answerIndex": 1},
                {"question": "Capital of France?", "choices": ["Rome", "Paris", "Berlin", "Madrid"], "answerIndex": 1},
                {"question": "Color of the sky?", "choices": ["Green", "Red", "Blue", "Purple"], "answerIndex": 2},
                {"question": "7 x 6 = ?", "choices": ["42", "36", "48", "40"], "answerIndex": 0},
                {"question": "Largest planet?", "choices": ["Earth", "Mars", "Jupiter", "Venus"], "answerIndex": 2},
            ],
            "timePerQuestion": 15,
        },
    },
}


def list_templates() -> list:
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
    path = os.path.join(LIBRARY_DIR, GAMES[game_id]["file"])
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def merge_config(game_id: str, config: dict) -> dict:
    defaults = GAMES[game_id]["defaults"]
    config = config or {}
    merged = dict(defaults)
    for key, value in config.items():
        if value not in (None, "", [], {}):
            merged[key] = value
    return merged
