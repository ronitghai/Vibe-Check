"""
orchestrator.py
----------------
Groq tool-calling chat loop, one turn at a time, session-scoped. This is the
"✨ Generate a game" chat entry point in the AZ-900 Game Menu — everything it
produces must be genuine AZ-900 (Microsoft Azure Fundamentals) exam-prep
content tied to one of the 3 domains in learning/knowledge_base.py's DOMAINS,
not a general-purpose "make me any game" tool. Mirrors chatbot.py's chat()
loop but stores history as plain dicts in session_store instead of an
in-memory list, and reports back whether a game got launched — including
which AZ-900 domain it targets — so the API layer can tell the frontend to
fetch the bundle and wire up real score reporting the same way a Game Menu
practice game does (see PlayView.tsx's postMessage listener and
learning/service.py's record_practice_result).
"""

import json

from openai import OpenAI

from . import config, session_store, tools
from .learning import store as learning_store
from .learning.knowledge_base import DOMAINS, SNIPPETS

client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)


def _facts_block() -> str:
    """One bullet list of every hand-authored SNIPPETS fact, grouped by
    domain — handed to the model as reference material for the WHOLE
    conversation (not just one domain) since a chat conversation can freely
    move between game types and topics, unlike the Game Menu's per-request
    generators in learning/service.py, which already know the domain before
    they ever call the LLM."""
    lines = []
    for domain in DOMAINS:
        lines.append(f"{domain}:")
        for entry in SNIPPETS[domain]:
            lines.append(f"  - {entry['snippet']}")
    return "\n".join(lines)


FACTS_BLOCK = _facts_block()


def _build_system_prompt(weakest_domain: str) -> str:
    """Built fresh per new conversation (not a module-level constant) so it
    can bake in this session's current weakest domain as the default focus —
    see run_turn, which only calls this once, when history is empty."""
    return f"""You are the AZ-900 Study Companion's game generator, embedded in an app whose \
whole purpose is helping someone pass the Microsoft AZ-900 (Azure Fundamentals) certification \
exam by turning study into short, playable games. EVERY game you launch must be genuine AZ-900 \
exam-prep content from one of these 3 domains, no exceptions: {", ".join(DOMAINS)}.

Real facts to ground content in — use these, don't invent Azure details that aren't here or in \
well-established AZ-900 material:
{FACTS_BLOCK}

This learner's current weakest domain is "{weakest_domain}" — default to it whenever they don't \
name a specific domain or topic themselves. If someone asks for something that has nothing to do \
with Azure (e.g. "make me a game about dinosaurs"), don't refuse and don't just ignore the \
request either — keep the spirit of what they asked for (the game type, the playful tone) but \
swap the actual content for real AZ-900 material, and say so briefly in your reply.

You have a library of 7 pre-built games you can launch INSTANTLY via launch_template_game. Every \
call to launch_template_game or generate_custom_game MUST include a "domain" argument (one of \
the 3 domains above) — the app uses it to credit the learner's progress for that domain once \
they finish playing, so pick whichever domain the content actually tests, not just a guess.

For each template game, write real, finished content for "config" — never leave placeholders:

- tic_tac_toe: classic 3x3 grid vs a simple AI. config: {{"difficulty": "easy"|"medium"|"hard", \
"playerSymbol": "X"|"O"}}. Optionally add "factCard": one true AZ-900 sentence from the chosen \
domain, shown to the learner before the match.
- wheel_of_fortune: guess-the-phrase letter game. config: {{"phrase": "UPPERCASE WORDS, letters \
and spaces only, 2-4 words", "category": string, "maxGuesses": int}} — phrase must be a real \
AZ-900 term or short concept name.
- quiz_flyer: tap/space-to-flap side-scroller that pauses every few pipes for a quick multiple \
choice question, then resumes. config: {{"difficulty": "easy"|"medium"|"hard", "checkpointEvery": \
int (3-5), "questions": [{{"question": string, "choices": [4 strings], "answerIndex": 0-3}}, \
...] (5 to 10 questions)}}.
- memory_match: flip-card pairs memory game. config: {{"theme": string naming the AZ-900 \
domain/topic, "icons": [6 to 10 single emoji strings]}} — icons can be generic/fun, the theme \
name is what ties it to the domain.
- matching_game: click to pair items from two columns. config: {{"title": string, "pairs": \
[{{"left": string, "right": string}}, ...] (4 to 8 pairs)}} — real AZ-900 term↔definition pairs.
- crossword: word-and-clue fill-in grid. config: {{"words": [{{"word": "UPPERCASE, no spaces", \
"clue": string}}, ...] (3 to 6 words)}} — real AZ-900 vocabulary (service names, acronyms).
- rapid_quiz: Kahoot-style timed multiple choice quiz. config: {{"questions": [{{"question": \
string, "choices": [4 strings], "answerIndex": 0-3}}, ...] (5 to 10 questions), \
"timePerQuestion": seconds}}.

When the user's request clearly matches one of these, call launch_template_game with a \
fully-formed config tailored to what they asked for, grounded in the facts above.

If the user asks for something that doesn't fit any of the 7 templates, call generate_custom_game \
with a clear, simple spec (one core mechanic, clear controls, clear win/lose condition) that \
still tests real AZ-900 knowledge from the chosen domain.

Otherwise, just chat normally — you don't have to launch a game every turn, and you can answer \
AZ-900 study questions directly in text too. After launching something, confirm it in one short, \
enthusiastic sentence."""


MAX_TOOL_ROUNDS = 4


def run_turn(session_id: str, user_message: str):
    history = session_store.get_history(session_id)
    if not history:
        weakest_domain = learning_store.get_weakest_domain(session_id)
        history = [{"role": "system", "content": _build_system_prompt(weakest_domain)}]
    history.append({"role": "user", "content": user_message})

    game_ready = False
    game_id = None
    game_type = None
    game_domain = None

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
            return reply, game_ready, game_id, game_type, game_domain

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
                game_domain = launched.get("domain")

            history.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

    session_store.save_history(session_id, history)
    return (
        "That took a few too many steps — could you try rephrasing?",
        game_ready,
        game_id,
        game_type,
        game_domain,
    )
