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
        "description": "Classic strategy game that sharpens critical thinking against an AI opponent.",
        "defaults": {
            "difficulty": "medium",
            "playerSymbol": "X",
            "theme": "classic",
        },
    },
    "wheel_of_fortune": {
        "title": "Wheel of Fortune",
        "file": "wheel_of_fortune.html",
        "description": "Build vocabulary by guessing a hidden word or phrase, letter by letter.",
        "defaults": {
            "phrase": "SOLAR SYSTEM",
            "category": "Science",
            "maxGuesses": 8,
        },
    },
    "quiz_flyer": {
        "title": "Quiz Flyer",
        "file": "quiz_flyer.html",
        "description": "Fly through pipes and answer quick questions to keep your streak going.",
        "defaults": {
            "difficulty": "medium",
            "checkpointEvery": 4,
            "questions": [
                {"question": "How many continents are on Earth?", "choices": ["5", "6", "7", "8"], "answerIndex": 2},
                {"question": "What planet is known as the Red Planet?", "choices": ["Venus", "Mars", "Jupiter", "Saturn"], "answerIndex": 1},
                {"question": "5 + 7 = ?", "choices": ["10", "11", "12", "13"], "answerIndex": 2},
                {"question": "What gas do plants absorb from the air?", "choices": ["Oxygen", "Carbon Dioxide", "Nitrogen", "Helium"], "answerIndex": 1},
                {"question": "Which ocean is the largest?", "choices": ["Atlantic", "Indian", "Arctic", "Pacific"], "answerIndex": 3},
            ],
        },
    },
    "memory_match": {
        "title": "Memory Match",
        "file": "memory_match.html",
        "description": "Strengthen recall by matching pairs from a science-lab set of icons.",
        "defaults": {
            "theme": "Science Lab",
            "icons": ["🔬", "🧪", "🧬", "⚗️", "🌡️", "🔭", "🦠", "💡"],
        },
    },
    "matching_game": {
        "title": "Vocabulary Match",
        "file": "matching_game.html",
        "description": "Study key terms by pairing each one with its definition.",
        "defaults": {
            "title": "Match the term to its definition",
            "pairs": [
                {"left": "Photosynthesis", "right": "How plants make food from sunlight"},
                {"left": "Mammal", "right": "Warm-blooded animal that nurses its young"},
                {"left": "Equator", "right": "Imaginary line dividing Earth into two hemispheres"},
                {"left": "Democracy", "right": "Government run by the people"},
            ],
        },
    },
    "crossword": {
        "title": "Crossword",
        "file": "crossword.html",
        "description": "Build vocabulary and spelling by filling in words from their clues.",
        "defaults": {
            "words": [
                {"word": "GRAVITY", "clue": "The force that pulls objects toward Earth"},
                {"word": "FRACTION", "clue": "A part of a whole number"},
                {"word": "CAPITAL", "clue": "The city where a government is based"},
            ],
        },
    },
    "rapid_quiz": {
        "title": "Rapid Quiz",
        "file": "rapid_quiz.html",
        "description": "Test your knowledge across school subjects in a fast-paced quiz.",
        "defaults": {
            "questions": [
                {"question": "2 + 2 = ?", "choices": ["3", "4", "5", "6"], "answerIndex": 1},
                {"question": "Capital of France?", "choices": ["Rome", "Paris", "Berlin", "Madrid"], "answerIndex": 1},
                {"question": "Which planet do we live on?", "choices": ["Mars", "Venus", "Earth", "Mercury"], "answerIndex": 2},
                {"question": "7 x 6 = ?", "choices": ["42", "36", "48", "40"], "answerIndex": 0},
                {"question": "Who wrote Romeo and Juliet?", "choices": ["Dickens", "Shakespeare", "Austen", "Twain"], "answerIndex": 1},
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
