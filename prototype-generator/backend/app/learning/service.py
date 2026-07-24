"""
service.py
----------
All the "business logic" for the AZ-900 adaptive loop lives here — the
routers/az900.py endpoints are intentionally thin and just call straight
into these functions. Three responsibilities:

  1. Run the diagnostic assessment (start_assessment / submit_assessment),
     sampling from the hand-authored QUESTION_BANK in knowledge_base.py —
     never LLM-generated, see that file's docstring for why.
  2. Generate personalized content for whichever of the 7 template games the
     learner picked (generate_practice_content), grounded in one AZ-900
     domain, and launch it through the *existing* game engine — this does
     NOT build a new way to render a game. It calls session_store.upsert_game(),
     the exact same function the chat orchestrator and the "instant launch a
     template" button use, so an AZ-900 practice game is a completely normal
     library game as far as the rest of the app is concerned.
  3. Turn real game results into one "progress" number the frontend can put
     in a bar (record_practice_result / get_progress_summary). Practice
     results are NOT a participation click — they're the actual score the
     game reported via postMessage (see games/bundle.py's reportGameResult
     and PlayView.tsx's message listener), fed into the exact same
     domain_mastery accumulator the diagnostic uses.
"""

import json
import random

from openai import OpenAI

from .. import config as app_config
from .. import session_store
from ..games import registry
from . import store
from .knowledge_base import (
    DOMAIN_ICON_THEMES,
    DOMAINS,
    FALLBACK_CROSSWORD,
    FALLBACK_MATCHING,
    FALLBACK_PHRASE,
    QUESTION_BANK,
    SNIPPETS,
    get_random_snippet,
    get_snippet_for_topic,
)

client = OpenAI(api_key=app_config.GROQ_API_KEY, base_url=app_config.GROQ_BASE_URL)

# How many questions a diagnostic assessment contains. Spread as evenly as
# possible across the 3 DOMAINS by start_assessment() below.
ASSESSMENT_SIZE = 10

QUIZ_GEN_SYSTEM_PROMPT = """You write multiple choice quiz questions for an AZ-900 (Microsoft \
Azure Fundamentals) study game. You MUST base every question strictly on the provided facts — \
do not introduce any Azure detail that isn't directly supported by them. Return ONLY a JSON \
object of the exact shape {"questions": [{"question": string, "choices": [4 strings], \
"answerIndex": 0-3}, ...]} with no other text, no markdown fences."""

CROSSWORD_GEN_SYSTEM_PROMPT = """You write short crossword-style word+clue entries for an \
AZ-900 (Microsoft Azure Fundamentals) study game. You MUST base every word and clue strictly on \
the provided facts. Return ONLY a JSON object of the exact shape {"words": [{"word": string, \
"clue": string}, ...]} with 3 to 5 entries, no other text, no markdown fences. Each "word" must \
be a single UPPERCASE term with NO spaces (use the closest single-word or acronym form of the \
concept), 3 to 15 letters."""

MATCHING_GEN_SYSTEM_PROMPT = """You write short term-to-definition matching pairs for an AZ-900 \
(Microsoft Azure Fundamentals) study game. You MUST base every pair strictly on the provided \
facts. Return ONLY a JSON object of the exact shape {"pairs": [{"left": string, "right": string}, \
...]} with exactly 4 entries, no other text, no markdown fences. "left" is a short term or \
service name, "right" is a short (under 12 words) definition of it."""

WHEEL_GEN_SYSTEM_PROMPT = """You pick ONE short AZ-900 (Microsoft Azure Fundamentals) vocabulary \
term or phrase for a guess-the-phrase word game, based strictly on the provided facts. Return \
ONLY a JSON object of the exact shape {"phrase": string, "category": string} with no other text, \
no markdown fences. "phrase" must be 2 to 4 words, UPPERCASE letters and spaces only — no \
punctuation, digits, or numbers. "category" is a short label for the topic."""


# ===========================================================================
# Diagnostic assessment
# ===========================================================================

def start_assessment(session_id: str) -> dict:
    """
    Build one diagnostic assessment: sample ASSESSMENT_SIZE questions from
    QUESTION_BANK, spread as evenly as possible across the 3 domains (so a
    10-question assessment is roughly 3-3-4, never e.g. all 10 from one
    domain), shuffle the overall order, and stash the answer key server-side.

    Returns {assessment_id, questions} where `questions` has NO answerIndex
    in it — only save_pending_assessment()'s copy (server-side) has that.
    The frontend renders `questions` as-is as the quiz form.
    """
    picked: list[dict] = []

    per_domain = ASSESSMENT_SIZE // len(DOMAINS)
    remainder = ASSESSMENT_SIZE - per_domain * len(DOMAINS)

    for i, domain in enumerate(DOMAINS):
        count = per_domain + (1 if i < remainder else 0)
        pool = QUESTION_BANK[domain][:]  # copy — shuffle() mutates in place
        random.shuffle(pool)
        for q in pool[:count]:
            picked.append({"domain": domain, **q})

    random.shuffle(picked)  # interleave domains instead of 4 Cloud Q's in a row, etc.

    assessment_id = store.save_pending_assessment(session_id, picked)

    questions = [
        {
            "question_id": i,
            "domain": q["domain"],
            "question": q["question"],
            "choices": q["choices"],
        }
        for i, q in enumerate(picked)
    ]
    return {"assessment_id": assessment_id, "questions": questions}


def submit_assessment(session_id: str, assessment_id: str, answers: list[dict]) -> dict:
    """
    Grade a completed diagnostic. `answers` is [{question_id, choice_index}]
    from the client — correctness is always computed against the server-side
    key (store.pop_pending_assessment, single-use), never trusted from the
    client directly.

    Side effect: writes to domain_mastery for every domain in this
    assessment via store.record_result — the SAME accumulator practice
    results write to (see record_practice_result below), so diagnostic and
    practice accuracy blend into one number per domain.
    """
    key = store.pop_pending_assessment(session_id, assessment_id)
    if key is None:
        raise ValueError("Unknown or already-submitted assessment_id")

    answer_by_id = {a["question_id"]: a["choice_index"] for a in answers}

    per_domain_correct: dict[str, int] = {d: 0 for d in DOMAINS}
    per_domain_total: dict[str, int] = {d: 0 for d in DOMAINS}
    results = []
    explanations = []

    for i, q in enumerate(key):
        domain = q["domain"]
        chosen = answer_by_id.get(i)
        is_correct = chosen == q["answerIndex"]

        per_domain_total[domain] += 1
        if is_correct:
            per_domain_correct[domain] += 1
        else:
            explanations.append(
                {
                    "question": q["question"],
                    "yourAnswer": q["choices"][chosen] if chosen is not None else None,
                    "correctAnswer": q["choices"][q["answerIndex"]],
                    "domain": domain,
                    "explanation": get_snippet_for_topic(domain, q["topic"]) or "",
                }
            )

        results.append({"question_id": i, "domain": domain, "correct": is_correct})

    for domain in DOMAINS:
        if per_domain_total[domain] > 0:
            store.record_result(session_id, domain, per_domain_correct[domain], per_domain_total[domain])

    total_correct = sum(per_domain_correct.values())
    total_questions = sum(per_domain_total.values())

    progress = get_progress_summary(session_id)  # re-read AFTER the writes above

    return {
        "results": results,
        "explanations": explanations,
        "score": {"correct": total_correct, "total": total_questions},
        "mastery": progress["domains"],
        "weakestDomain": progress["weakestDomain"],
    }


# ===========================================================================
# Progress
# ===========================================================================

def get_progress_summary(session_id: str) -> dict:
    """
    The single source of truth for "how is this learner doing overall" —
    used by the Game Menu/weak-areas screen and by submit_assessment() and
    record_practice_result() to return fresh numbers after a write.

    overallProgress is simply the average masteryPct across the 3 domains.
    domain_mastery's correct/total already blends diagnostic answers AND
    real practice-game answers (both go through store.record_result) into
    one accuracy figure per domain, so a plain average is an honest "how
    well is this learner actually doing" number — no separate "did they
    bother to practice" weighting on top of it. The progress bar moves
    because the learner is answering things correctly, full stop.

    Returns per-domain rows (domain, correct, total, masteryPct,
    practiceCount), the weakest domain, and overallProgress.
    """
    mastery = store.get_mastery(session_id)
    practice_counts = store.get_practice_counts(session_id)

    domains = [{**m, "practiceCount": practice_counts.get(m["domain"], 0)} for m in mastery]

    avg_mastery_pct = sum(d["masteryPct"] for d in domains) / len(domains)

    return {
        "domains": domains,
        "weakestDomain": store.get_weakest_domain(session_id),
        "overallProgress": round(avg_mastery_pct),
    }


def record_practice_result(session_id: str, game_id: str, domain: str, correct: int, total: int) -> dict:
    """
    Called when a practice game reports its real result (see PlayView.tsx's
    postMessage listener, which calls POST /api/az900/practice/result).
    Writes the score into BOTH:
      - domain_mastery (store.record_result) — the same accumulator the
        diagnostic uses, so this is what actually moves the progress bar.
      - practice_log (store.log_attempt) — a pure attempt-history record for
        display ("you've practiced this domain N times").
    Returns the freshly recomputed progress summary.
    """
    store.record_result(session_id, domain, correct, total)
    store.log_attempt(session_id, game_id, domain, correct, total)
    return get_progress_summary(session_id)


# ===========================================================================
# Practice content generation — one function per template game, dispatched
# by generate_practice_content(). Every generator follows the same shape:
# ask the LLM for JSON grounded in this domain's SNIPPETS, validate it
# strictly, and on any failure fall back to hand-authored content instead of
# ever shipping something broken or hallucinated.
# ===========================================================================

def generate_practice_content(session_id: str, game_id: str, domain: str | None = None) -> dict:
    """
    Generate AZ-900-grounded content for `game_id` (any of the 7 template
    games) targeting `domain` (or the current weakest domain if omitted/
    invalid), and launch it through the existing game engine — the exact
    same session_store.upsert_game() call every other launch path in the
    app uses, so this is a completely normal library game afterward.

    Raises ValueError for a game_id that isn't a real template game.
    """
    if game_id not in registry.GAMES:
        raise ValueError(f"Unknown game_id: {game_id}")

    target_domain = domain if domain in DOMAINS else store.get_weakest_domain(session_id)
    snippets = SNIPPETS[target_domain]
    facts_text = "\n".join(f"- {s['snippet']}" for s in snippets)

    overrides = _build_config_overrides(game_id, target_domain, facts_text)
    config = registry.merge_config(game_id, overrides)
    title = f"{registry.GAMES[game_id]['title']} — {target_domain}"

    session_store.upsert_game(session_id, game_id, "template", title, {"config": config})

    return {"game_id": game_id, "game_type": "template", "domain": target_domain}


def _build_config_overrides(game_id: str, domain: str, facts_text: str) -> dict:
    """Dispatch table: which content generator each game_id needs."""
    if game_id in ("quiz_flyer", "rapid_quiz"):
        return {"questions": _generate_questions_from_snippets(domain, facts_text)}
    if game_id == "crossword":
        return {"words": _generate_crossword_words(domain, facts_text)}
    if game_id == "matching_game":
        pairs = _generate_matching_pairs(domain, facts_text)
        return {"title": f"Match the {domain} terms", "pairs": pairs}
    if game_id == "wheel_of_fortune":
        return _generate_wheel_phrase(domain, facts_text)  # already {"phrase", "category"}
    if game_id == "memory_match":
        # No LLM call — memory_match's mechanic is flip-and-match IDENTICAL
        # icons, so there's no fact to test, only a theme to apply.
        return {"theme": domain, "icons": DOMAIN_ICON_THEMES[domain]}
    if game_id == "tic_tac_toe":
        # No LLM call, no content slot to test knowledge with — just show a
        # true, grounded fact before the match (tic_tac_toe.html renders
        # config.factCard if present).
        return {"factCard": get_random_snippet(domain)}
    # Should be unreachable — generate_practice_content() already validated
    # game_id against registry.GAMES before calling this dispatcher.
    return {}


def _call_llm_json(system_prompt: str, domain: str, facts_text: str) -> dict:
    """Shared plumbing for every LLM-backed generator below: one Groq call,
    JSON mode, grounded in `facts_text`. Returns {} on any failure so each
    caller's own validator+fallback decides what happens next."""
    user_prompt = f'AZ-900 domain: "{domain}"\nFacts to base this on:\n{facts_text}'
    try:
        response = client.chat.completions.create(
            model=app_config.CODEGEN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception:
        return {}


def _generate_questions_from_snippets(domain: str, facts_text: str) -> list[dict]:
    """Used by quiz_flyer and rapid_quiz. Falls back to shuffling real
    QUESTION_BANK entries for this domain if the LLM call fails/is malformed."""
    parsed = _call_llm_json(QUIZ_GEN_SYSTEM_PROMPT, domain, facts_text)
    questions = parsed.get("questions", [])
    if _valid_questions(questions):
        return questions

    pool = QUESTION_BANK[domain][:]
    random.shuffle(pool)
    return [{"question": q["question"], "choices": q["choices"], "answerIndex": q["answerIndex"]} for q in pool]


def _generate_crossword_words(domain: str, facts_text: str) -> list[dict]:
    """Used by crossword. Falls back to FALLBACK_CROSSWORD[domain]."""
    parsed = _call_llm_json(CROSSWORD_GEN_SYSTEM_PROMPT, domain, facts_text)
    words = parsed.get("words", [])
    if _valid_word_clue_list(words):
        return words
    return FALLBACK_CROSSWORD[domain]


def _generate_matching_pairs(domain: str, facts_text: str) -> list[dict]:
    """Used by matching_game. Falls back to FALLBACK_MATCHING[domain]."""
    parsed = _call_llm_json(MATCHING_GEN_SYSTEM_PROMPT, domain, facts_text)
    pairs = parsed.get("pairs", [])
    if _valid_pairs(pairs):
        return pairs
    return FALLBACK_MATCHING[domain]


def _generate_wheel_phrase(domain: str, facts_text: str) -> dict:
    """Used by wheel_of_fortune. Falls back to FALLBACK_PHRASE[domain]."""
    parsed = _call_llm_json(WHEEL_GEN_SYSTEM_PROMPT, domain, facts_text)
    if _valid_phrase(parsed):
        return {"phrase": parsed["phrase"].upper(), "category": parsed["category"]}
    return FALLBACK_PHRASE[domain]


# ---------------------------------------------------------------------------
# Validators — defensive shape checks on LLM JSON output. Each mirrors the
# exact fields the matching game HTML template expects (see
# games/library/*.html), so anything that passes is guaranteed renderable.
# ---------------------------------------------------------------------------

def _valid_questions(questions) -> bool:
    if not isinstance(questions, list) or not questions:
        return False
    for q in questions:
        if not isinstance(q, dict):
            return False
        if not isinstance(q.get("question"), str) or not q["question"].strip():
            return False
        choices = q.get("choices")
        if not isinstance(choices, list) or len(choices) != 4:
            return False
        if not isinstance(q.get("answerIndex"), int) or not (0 <= q["answerIndex"] < 4):
            return False
    return True


def _valid_word_clue_list(words) -> bool:
    if not isinstance(words, list) or not (2 <= len(words) <= 6):
        return False
    for w in words:
        if not isinstance(w, dict):
            return False
        word = w.get("word")
        clue = w.get("clue")
        if not isinstance(word, str) or not (2 <= len(word.replace(" ", "")) <= 15):
            return False
        if not isinstance(clue, str) or not clue.strip():
            return False
    return True


def _valid_pairs(pairs) -> bool:
    if not isinstance(pairs, list) or not (3 <= len(pairs) <= 6):
        return False
    for p in pairs:
        if not isinstance(p, dict):
            return False
        if not isinstance(p.get("left"), str) or not p["left"].strip():
            return False
        if not isinstance(p.get("right"), str) or not p["right"].strip():
            return False
    return True


def _valid_phrase(data) -> bool:
    if not isinstance(data, dict):
        return False
    phrase = data.get("phrase")
    category = data.get("category")
    if not isinstance(phrase, str) or not isinstance(category, str) or not category.strip():
        return False
    # Must be letters and spaces only once uppercased, and contain at least
    # one letter — wheel_of_fortune.html can only ever reveal A-Z guesses,
    # so any other character would render as a permanently-unsolvable box.
    upper = phrase.upper()
    return bool(upper.strip()) and all(c.isalpha() or c == " " for c in upper)
