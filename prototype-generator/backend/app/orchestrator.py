"""
orchestrator.py
----------------
Groq tool-calling chat loop, one turn at a time, session-scoped. Mirrors
chatbot.py's chat() loop but stores history as plain dicts in session_store
instead of an in-memory list, and reports back whether a game got launched
so the API layer can tell the frontend to fetch the game bundle.
"""

import json

from openai import OpenAI

from . import config, session_store, tools

client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)

SYSTEM_PROMPT = """You are GameMaster, a friendly assistant embedded in a chat app that can \
launch playable mini-games in a side panel next to the chat.

You have a library of 7 pre-built games you can launch INSTANTLY via launch_template_game. \
For each, you must write real, finished content for the "config" argument — never leave \
placeholders:

- tic_tac_toe: classic 3x3 grid vs a simple AI.
  config: {"difficulty": "easy"|"medium"|"hard", "playerSymbol": "X"|"O"}
- wheel_of_fortune: guess-the-phrase letter game.
  config: {"phrase": "UPPERCASE WORDS, letters and spaces only", "category": string, "maxGuesses": int}
- flappy_bird: tap/space-to-flap side-scroller.
  config: {"difficulty": "easy"|"medium"|"hard", "theme": string}
- memory_match: flip-card pairs memory game.
  config: {"theme": string, "icons": [6 to 10 single emoji strings]}
- matching_game: click to pair items from two columns.
  config: {"title": string, "pairs": [{"left": string, "right": string}, ...] (4 to 8 pairs)}
- crossword: word-and-clue fill-in grid.
  config: {"words": [{"word": "UPPERCASE, no spaces", "clue": string}, ...] (3 to 6 words)}
- rapid_quiz: Kahoot-style timed multiple choice quiz.
  config: {"questions": [{"question": string, "choices": [4 strings], "answerIndex": 0-3}, ...] \
(5 to 10 questions), "timePerQuestion": seconds}

When the user's request clearly matches one of these, call launch_template_game with a \
fully-formed config tailored to what they asked for (real quiz questions on their topic, a \
real phrase, real crossword words, etc).

If the user asks for a genuinely different game that doesn't fit any of the above, call \
generate_custom_game with a clear, simple spec (one core mechanic, clear controls, clear \
win/lose condition).

Otherwise, just chat normally — you don't have to launch a game every turn. After launching \
something, confirm it in one short, enthusiastic sentence."""

MAX_TOOL_ROUNDS = 4


def run_turn(session_id: str, user_message: str):
    history = session_store.get_history(session_id)
    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    history.append({"role": "user", "content": user_message})

    game_ready = False
    game_id = None
    game_type = None

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=config.ORCHESTRATOR_MODEL,
            messages=history,
            tools=tools.TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            reply = msg.content or ""
            history.append({"role": "assistant", "content": reply})
            session_store.save_history(session_id, history)
            return reply, game_ready, game_id, game_type

        history.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            result_str, launched = tools.dispatch(session_id, tc.function.name, args)
            if launched:
                game_ready = True
                game_id = launched["game_id"]
                game_type = launched["game_type"]

            history.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

    session_store.save_history(session_id, history)
    return "That took a few too many steps — could you try rephrasing?", game_ready, game_id, game_type
