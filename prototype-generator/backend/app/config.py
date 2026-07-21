"""
config.py
---------
Central place for environment-derived settings. Load a Groq API key the same
way chatbot.py loads OPENAI_API_KEY, just from a .env file in backend/.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", "llama-3.3-70b-versatile")
CODEGEN_MODEL = os.environ.get("CODEGEN_MODEL", "llama-3.3-70b-versatile")

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "sessions.db"),
)

MAX_GENERATED_HTML_BYTES = 60_000
