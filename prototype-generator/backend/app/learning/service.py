"""
service.py
----------
All the "business logic" for the AZ-900 adaptive loop lives here — the
routers/az900.py endpoints are intentionally thin and just call straight
into these functions. Three responsibilities:

  1. Run the diagnostic assessment (start_assessment / submit_assessment),
     sampling from the hand-authored QUESTION_BANK in knowledge_base.py —
     never LLM-generated, see that file's docstring for why.
  2. Generate personalized content for whichever curated learning activity the
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
    DOMAINS,
    DOMAIN_WEIGHTS,
    FALLBACK_CROSSWORD,
    FALLBACK_MATCHING,
    QUESTION_BANK,
    SNIPPETS,
    TOPICS_BY_DOMAIN,
    get_snippet_for_topic,
)

client = OpenAI(api_key=app_config.GROQ_API_KEY, base_url=app_config.GROQ_BASE_URL)

# How many questions a diagnostic assessment contains. Spread as evenly as
# possible across the 3 DOMAINS by start_assessment() below.
ASSESSMENT_SIZE = 10

QUIZ_GEN_SYSTEM_PROMPT = """You write multiple choice quiz questions for an AZ-900 (Microsoft \
Azure Fundamentals) study game. You MUST base every question strictly on the provided facts — \
do not introduce any Azure detail that isn't directly supported by them. Return ONLY a JSON object of the exact shape {"questions": [{"question": string, "choices": [4 strings], "answerIndex": 0-3, "explanation": string}, ...]} with no other text, no markdown fences. Order the questions \
from easiest to hardest, so the first question is the most foundational and the last question \
is the most challenging. Keep the difficulty ramping as the learner progresses."""

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

JEOPARDY_GEN_SYSTEM_PROMPT = """
You create structured Jeopardy-style question boards for Microsoft AZ-900
certification practice.

Use only the AZ-900 facts supplied by the user.

Return only a JSON object with this exact structure:

{
  "title": string,
  "categories": [
    {
      "name": string,
      "questions": [
        {
          "value": 100,
          "question": string,
          "choices": [string, string, string, string],
          "answerIndex": 0,
          "explanation": string
        },
        {
          "value": 200,
          "question": string,
          "choices": [string, string, string, string],
          "answerIndex": 0,
          "explanation": string
        },
        {
          "value": 300,
          "question": string,
          "choices": [string, string, string, string],
          "answerIndex": 0,
          "explanation": string
        },
        {
          "value": 400,
          "question": string,
          "choices": [string, string, string, string],
          "answerIndex": 0,
          "explanation": string
        }
      ]
    }
  ]
}

Requirements:

- Exactly 4 categories.
- Exactly 4 questions per category.
- Values must be 100, 200, 300, and 400 in that order.
- Exactly 16 total questions.
- Exactly 4 answer choices for every question.
- Questions must increase in difficulty from 100 to 400.
- Do not duplicate questions.
- Do not duplicate category names.
- Every explanation must teach the relevant concept.
- Do not use free-text answers.
- Return no Markdown and no text outside the JSON object.
"""



# ===========================================================================
# Diagnostic assessment
# ===========================================================================

def _weighted_question_counts(total: int) -> dict[str, int]:
    """
    Split `total` questions across DOMAINS proportional to DOMAIN_WEIGHTS
    (the real 25-30/35-40/30-35 AZ-900 exam weighting), using the largest-
    remainder method so the counts always sum to exactly `total` — e.g. for
    ASSESSMENT_SIZE=10 this comes out to Cloud Concepts=3, Azure
    Architecture & Services=4, Azure Management & Governance=3.
    """
    weight_sum = sum(DOMAIN_WEIGHTS[d] for d in DOMAINS)
    raw = {d: total * DOMAIN_WEIGHTS[d] / weight_sum for d in DOMAINS}
    counts = {d: int(raw[d]) for d in DOMAINS}  # floor
    remaining = total - sum(counts.values())
    # Give the leftover questions to whichever domains had the largest
    # fractional remainder, so the total always lands exactly on `total`.
    by_remainder = sorted(DOMAINS, key=lambda d: raw[d] - counts[d], reverse=True)
    for d in by_remainder[:remaining]:
        counts[d] += 1
    return counts


def _topics_uncovered_first(session_id: str, domain: str) -> list[str]:
    """
    Every topic in `domain` (from knowledge_base.TOPICS_BY_DOMAIN), with
    topics this session hasn't been quizzed on yet shuffled to the front.
    Shared by the diagnostic (_pick_questions_for_domain) and practice
    content generation (_pick_target_topics) — both need the same "haven't
    seen this yet beats already-covered" priority so that using either path
    actually advances the learner toward full coverage instead of
    re-covering the same handful of topics forever.
    """
    covered = store.get_covered_topics(session_id, domain)
    all_topics = list(TOPICS_BY_DOMAIN[domain])
    uncovered = [t for t in all_topics if t not in covered]
    seen = [t for t in all_topics if t in covered]
    random.shuffle(uncovered)
    random.shuffle(seen)
    return uncovered + seen


def _pick_questions_for_domain(session_id: str, domain: str, count: int) -> list[dict]:
    """
    Pick `count` questions from QUESTION_BANK[domain] for one diagnostic,
    prioritizing DISTINCT topics the session hasn't been quizzed on yet —
    not just random questions, which could easily pick 2 questions from the
    same already-covered topic while ignoring an untouched one (each topic
    has ~7 questions, so pure random sampling wastes a lot of a diagnostic's
    limited question budget). This is what makes "retake the diagnostic"
    an effective way to raise topic coverage (see get_progress_summary),
    not just a way to re-roll the same handful of topics.

    Within a chosen topic, the specific question is picked at random from
    that topic's pool (~7 questions), so repeats stay varied even after
    every topic is covered.
    """
    by_topic: dict[str, list[dict]] = {}
    for q in QUESTION_BANK[domain]:
        by_topic.setdefault(q["topic"], []).append(q)

    topic_order = [t for t in _topics_uncovered_first(session_id, domain) if t in by_topic]
    return [random.choice(by_topic[topic]) for topic in topic_order[:count]]


def start_assessment(session_id: str) -> dict:
    """
    Build one diagnostic assessment: sample ASSESSMENT_SIZE questions from
    QUESTION_BANK, spread across the 3 domains proportional to their REAL
    AZ-900 exam weight (see DOMAIN_WEIGHTS in knowledge_base.py — 25-30% /
    35-40% / 30-35%, not a flat 1/3 each) and, within each domain,
    prioritizing topics this session hasn't covered yet (see
    _pick_questions_for_domain) — shuffle the overall order, and stash the
    answer key server-side.

    Returns {assessment_id, questions} where `questions` has NO answerIndex
    in it — only save_pending_assessment()'s copy (server-side) has that.
    The frontend renders `questions` as-is as the quiz form.
    """
    picked: list[dict] = []

    for domain, count in _weighted_question_counts(ASSESSMENT_SIZE).items():
        for q in _pick_questions_for_domain(session_id, domain, count):
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
    per_domain_topics: dict[str, list[str]] = {d: [] for d in DOMAINS}
    results = []
    explanations = []

    for i, q in enumerate(key):
        domain = q["domain"]
        chosen = answer_by_id.get(i)
        is_correct = chosen == q["answerIndex"]

        per_domain_total[domain] += 1
        per_domain_topics[domain].append(q["topic"])
        if is_correct:
            per_domain_correct[domain] += 1
        else:
            explanations.append(
                {
                    "question": q["question"],
                    "yourAnswer": q["choices"][chosen] if chosen is not None else None,
                    "correctAnswer": q["choices"][q["answerIndex"]],
                    "domain": domain,
                    # Every question in the current bank carries its own
                    # explanation now (specific to what was actually asked);
                    # fall back to the older topic-level snippet lookup only
                    # for a question that doesn't have one.
                    "explanation": q.get("explanation") or get_snippet_for_topic(domain, q["topic"]) or "",
                }
            )

        results.append({"question_id": i, "domain": domain, "correct": is_correct})

    for domain in DOMAINS:
        if per_domain_total[domain] > 0:
            store.record_result(session_id, domain, per_domain_correct[domain], per_domain_total[domain])
            # Coverage is exposure-based, not correctness-based — every
            # topic actually asked this round counts as "covered" whether
            # the learner got it right or wrong.
            store.mark_topics_covered(session_id, domain, per_domain_topics[domain])

    total_correct = sum(per_domain_correct.values())
    total_questions = sum(per_domain_total.values())

    progress = get_progress_summary(session_id)  # re-read AFTER the writes above

    return {
        "results": results,
        "explanations": explanations,
        "score": {"correct": total_correct, "total": total_questions},
        "mastery": progress["domains"],
        "weakestDomain": progress["weakestDomain"],
        "recommendedActivity": progress.get("recommendedActivity"),
    }


# ===========================================================================
# Progress
# ===========================================================================

def get_progress_summary(session_id: str) -> dict:
    """
    The single source of truth for "how is this learner doing overall" —
    used by the Game Menu/weak-areas screen and by submit_assessment() and
    record_practice_result() to return fresh numbers after a write.

    Each domain's masteryPct is GATED by concept coverage, not raw accuracy
    alone:

        masteryPct = round(accuracy_pct * coverage_fraction)

    where accuracy_pct is correct/total from domain_mastery (can go up OR
    down as the learner answers more things — see record_practice_result;
    this is what makes it possible to LOSE progress, not just gain it) and
    coverage_fraction is (topics quizzed at least once) / (topics that
    exist in that domain — see knowledge_base.TOPICS_BY_DOMAIN). Coverage
    only ever grows (store.mark_topics_covered never un-marks a topic), so
    a domain's mastery CEILING rises monotonically as more of the knowledge
    base gets covered, but the actual number under that ceiling still moves
    with real performance. A domain can only ever show 100% once every one
    of its topics has been quizzed AND every answer given was correct —
    100% accuracy on 3 of 16 topics caps out far below 100%.

    overallProgress is that gated masteryPct averaged across the 3 domains,
    weighted by DOMAIN_WEIGHTS (the real 25-30/35-40/30-35 AZ-900 exam
    weighting, not a flat 1/3 each).

    Returns per-domain rows (domain, correct, total, masteryPct,
    practiceCount, topicsCovered, topicsTotal), the weakest domain, and
    overallProgress.
    """
    mastery = store.get_mastery(session_id)
    practice_counts = store.get_practice_counts(session_id)

    domains = []
    for m in mastery:
        domain = m["domain"]
        topics_total = len(TOPICS_BY_DOMAIN[domain])
        topics_covered = len(store.get_covered_topics(session_id, domain))
        coverage_fraction = (topics_covered / topics_total) if topics_total else 0
        gated_pct = round(m["masteryPct"] * coverage_fraction)
        domains.append({
            **m,
            "masteryPct": gated_pct,
            "practiceCount": practice_counts.get(domain, 0),
            "topicsCovered": topics_covered,
            "topicsTotal": topics_total,
        })

    weight_sum = sum(DOMAIN_WEIGHTS[d["domain"]] for d in domains)
    avg_mastery_pct = sum(d["masteryPct"] * DOMAIN_WEIGHTS[d["domain"]] for d in domains) / weight_sum
    # Weakest domain is picked from the GATED numbers (not raw accuracy), so
    # a domain that's "100% right on the 2 questions I've seen" but barely
    # covered still reads as needing attention — same untouched-first
    # tie-break store.get_weakest_domain uses, just applied post-gating.
    weakest_domain = min(domains, key=lambda d: (d["total"] > 0, d["masteryPct"]))["domain"]

    return {
        "domains": domains,
        "weakestDomain": weakest_domain,
        "overallProgress": round(avg_mastery_pct),
        "recommendedActivity": _recommend_next_activity(weakest_domain, domains),
    }


def _difficulty_for_mastery(mastery_pct: int) -> str:
    if mastery_pct < 50:
        return "easy"
    if mastery_pct < 75:
        return "medium"
    return "hard"


def _checkpoint_every(difficulty: str) -> int:
    return {"easy": 5, "medium": 4, "hard": 3}.get(difficulty, 4)


def _time_per_question(difficulty: str) -> int:
    return {"easy": 18, "medium": 15, "hard": 12}.get(difficulty, 15)


def _wheel_max_guesses(difficulty: str) -> int:
    return {"easy": 12, "medium": 9, "hard": 7}.get(difficulty, 9)


def _recommend_next_activity(weakest_domain: str, domains: list[dict]) -> dict:
    """Select a pedagogically appropriate next activity, not just a fun game."""
    row = next((d for d in domains if d["domain"] == weakest_domain), None)
    mastery_pct = row["masteryPct"] if row is not None else 0
    practice_count = row.get("practiceCount", 0) if row else 0

    if mastery_pct < 45:
        game_id = "rapid_quiz"
        label = "Knowledge Check"
        reason = "Retrieve foundational concepts and review an explanation after every answer."
    elif mastery_pct < 75:
        game_id = "scenario_challenge"
        label = "Azure Scenario Challenge"
        reason = "Apply the concepts you know to realistic Azure decisions."
    else:
        game_id = "matching_game"
        label = "Concept Connections"
        reason = "Strengthen links between related services before the next assessment."

    return {
        "gameId": game_id,
        "gameLabel": label,
        "domain": weakest_domain,
        "difficulty": _difficulty_for_mastery(mastery_pct),
        "masteryPct": mastery_pct,
        "practiceCount": practice_count,
        "reason": reason,
    }

def record_practice_result(session_id: str, game_id: str, domain: str, correct: int, total: int) -> dict:
    """
    Called when a practice game reports its real result (see PlayView.tsx's
    postMessage listener, which calls POST /api/az900/practice/result).
    Writes the score into:
      - domain_mastery (store.record_result) — the same accumulator the
        diagnostic uses, driving the ACCURACY half of masteryPct.
      - topic_coverage (store.mark_topics_covered) — whichever topics
        generate_practice_content targeted for this specific game (stashed
        in the launched game's own payload at generation time, see
        _pick_target_topics), driving the COVERAGE half. A game not
        launched through generate_practice_content (e.g. one the chat
        generator improvised) simply has no target topics to mark — its
        score still counts toward accuracy, just not toward coverage, since
        there's no reliable way to know which specific topics a freeform
        chat-generated game actually touched.
      - practice_log (store.log_attempt) — a pure attempt-history record for
        display ("you've practiced this domain N times").
    Returns the freshly recomputed progress summary.
    """
    if game_id not in registry.GAMES:
        raise ValueError(f"Unknown learning activity: {game_id}")
    if domain not in DOMAINS:
        raise ValueError(f"Unknown AZ-900 domain: {domain}")
    if total <= 0 or correct < 0 or correct > total:
        raise ValueError("Invalid activity result")

    # Assessment/application activities influence mastery more than lightweight
    # vocabulary review. Scaling both numerator and denominator preserves the
    # activity's accuracy while reducing how strongly it moves mastery.
    weight = float(registry.GAMES[game_id].get("mastery_weight", 1.0))
    weighted_correct = round(correct * weight * 100)
    weighted_total = round(total * weight * 100)
    store.record_result(session_id, domain, weighted_correct, weighted_total)
    store.log_attempt(session_id, game_id, domain, correct, total)

    launched = session_store.get_game(session_id, game_id)
    target_topics = (launched or {}).get("az900_topics") or []
    if target_topics:
        store.mark_topics_covered(session_id, domain, target_topics)

    return get_progress_summary(session_id)


# ===========================================================================
# Practice content generation — one function per template game, dispatched
# by generate_practice_content(). Every generator follows the same shape:
# ask the LLM for JSON grounded in this domain's SNIPPETS, validate it
# strictly, and on any failure fall back to hand-authored content instead of
# ever shipping something broken or hallucinated.
# ===========================================================================

# How many distinct topics one practice round's content gets grounded in.
# Tighter than "every snippet in the domain" (which could be 40+ topics) —
# keeps the LLM's grounding focused and, more importantly, means each round
# has a concrete, storable list of topics to credit toward coverage when the
# real score comes back (see _pick_target_topics / record_practice_result).
TOPICS_PER_PRACTICE_ROUND = 8


def _pick_target_topics(session_id: str, domain: str, count: int = TOPICS_PER_PRACTICE_ROUND) -> list[str]:
    """Which topics THIS round of practice content should be grounded in and
    later get coverage credit for — uncovered topics first (see
    _topics_uncovered_first), so playing practice rounds is a real way to
    reach full coverage, not just a way to grind accuracy on a few topics."""
    return _topics_uncovered_first(session_id, domain)[:count]


def generate_practice_content(session_id: str, game_id: str, domain: str | None = None) -> dict:
    """
    Generate AZ-900-grounded content for `game_id` (a curated learning-activity
    games) targeting `domain` (or the current weakest domain if omitted/
    invalid), and launch it through the existing game engine — the exact
    same session_store.upsert_game() call every other launch path in the
    app uses, so this is a completely normal library game afterward.

    Content is grounded in a specific BATCH of that domain's topics (see
    _pick_target_topics), not the whole domain's snippet list — those exact
    topics are stashed in the launched game's own payload as "az900_topics"
    so that when the real score comes back, record_practice_result knows
    precisely which topics to mark covered.

    Raises ValueError for a game_id that isn't a real template game.
    """
    if game_id not in registry.GAMES:
        raise ValueError(f"Unknown game_id: {game_id}")

    target_domain = domain if domain in DOMAINS else store.get_weakest_domain(session_id)
    target_topics = _pick_target_topics(session_id, target_domain)
    relevant_snippets = [s for s in SNIPPETS[target_domain] if s["topic"] in target_topics]
    # Extremely unlikely (would need every topic's snippets to somehow be
    # empty), but fall back to the full domain rather than ground on nothing.
    facts_text = "\n".join(f"- {s['snippet']}" for s in (relevant_snippets or SNIPPETS[target_domain]))
    mastery_pct = _get_domain_mastery_pct(session_id, target_domain)

    overrides = _build_config_overrides(game_id, target_domain, facts_text, mastery_pct)
    config = registry.merge_config(game_id, overrides)
    title = f"{registry.GAMES[game_id]['title']} — {target_domain}"

    session_store.upsert_game(
        session_id, game_id, "template", title, {"config": config, "az900_topics": target_topics}
    )

    return {"game_id": game_id, "game_type": "template", "domain": target_domain}


def _build_config_overrides(game_id: str, domain: str, facts_text: str, mastery_pct: int) -> dict:
    difficulty = _difficulty_for_mastery(mastery_pct)
    if game_id in {"rapid_quiz", "scenario_challenge"}:
        questions = _order_questions_by_complexity(
            _generate_questions_from_snippets(domain, facts_text, scenario=(game_id == "scenario_challenge"))
        )
        result = {"questions": questions}
        if game_id == "rapid_quiz":
            result["timePerQuestion"] = _time_per_question(difficulty)
        return result
    if game_id == "crossword":
        return {"words": _generate_crossword_words(domain, facts_text)}
    if game_id == "matching_game":
        return {"title": f"Connect the {domain} concepts", "pairs": _generate_matching_pairs(domain, facts_text)}
    if game_id == "jeopardy":
        return _generate_jeopardy_config(domain, facts_text)
    return {}

def _get_domain_mastery_pct(session_id: str, domain: str) -> int:
    mastery = store.get_mastery(session_id)
    for row in mastery:
        if row["domain"] == domain:
            return row["masteryPct"]
    return 0


def _question_complexity(question: dict) -> int:
    if not isinstance(question, dict):
        return 0
    text = question.get("question", "")
    choices = question.get("choices", [])
    if not isinstance(choices, list):
        choices = []
    return len(str(text)) + sum(len(str(choice)) for choice in choices)


def _order_questions_by_complexity(questions: list[dict]) -> list[dict]:
    if not isinstance(questions, list):
        return questions
    return sorted(questions, key=_question_complexity)


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


def _generate_questions_from_snippets(domain: str, facts_text: str, scenario: bool = False) -> list[dict]:
    """Create explanation-rich retrieval or scenario questions.

    The hand-authored bank remains the fallback and source of truth. Scenario
    mode prefers questions with applied wording, while regular mode samples a
    balanced set for retrieval practice.
    """
    prompt = QUIZ_GEN_SYSTEM_PROMPT
    if scenario:
        prompt += " Every question must be a short workplace or architecture scenario that asks the learner to choose the best Azure concept or service."
    parsed = _call_llm_json(prompt, domain, facts_text)
    questions = parsed.get("questions", [])
    if _valid_questions(questions):
        return questions[:8]

    pool = QUESTION_BANK[domain][:]
    random.shuffle(pool)
    selected = pool[:8]
    return [
        {
            "question": q["question"],
            "choices": q["choices"],
            "answerIndex": q["answerIndex"],
            "explanation": get_snippet_for_topic(domain, q["topic"]) or "Review this concept in the AZ-900 learning path.",
        }
        for q in selected
    ]

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

def _generate_jeopardy_config(
    domain: str,
    facts_text: str,
) -> dict:
    """
    Generate the structured content consumed by jeopardy.html.

    If the LLM response is incomplete or malformed, registry.merge_config()
    will retain the hand-authored default board from registry.py.
    """
    parsed = _call_llm_json(
        JEOPARDY_GEN_SYSTEM_PROMPT,
        domain,
        facts_text,
    )

    title = parsed.get("title")
    categories = parsed.get("categories")

    if not isinstance(title, str) or not title.strip():
        title = f"{domain} Jeopardy"

    if not _valid_jeopardy_categories(categories):
        return {
            "title": f"{domain} Jeopardy",
        }

    return {
        "title": title.strip(),
        "categories": categories,
    }


def _valid_jeopardy_categories(categories) -> bool:
    """
    Validate the exact structure expected by jeopardy.html.
    """
    if not isinstance(categories, list) or len(categories) != 4:
        return False

    category_names: set[str] = set()
    expected_values = [100, 200, 300, 400]
    seen_questions: set[str] = set()

    for category in categories:
        if not isinstance(category, dict):
            return False

        name = category.get("name")

        if not isinstance(name, str) or not name.strip():
            return False

        normalized_name = name.strip().lower()

        if normalized_name in category_names:
            return False

        category_names.add(normalized_name)

        questions = category.get("questions")

        if not isinstance(questions, list) or len(questions) != 4:
            return False

        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                return False

            if question.get("value") != expected_values[index]:
                return False

            question_text = question.get("question")

            if not isinstance(question_text, str) or not question_text.strip():
                return False

            normalized_question = question_text.strip().lower()

            if normalized_question in seen_questions:
                return False

            seen_questions.add(normalized_question)

            choices = question.get("choices")

            if not isinstance(choices, list) or len(choices) != 4:
                return False

            if not all(
                isinstance(choice, str) and choice.strip()
                for choice in choices
            ):
                return False

            answer_index = question.get("answerIndex")

            if (
                not isinstance(answer_index, int)
                or not 0 <= answer_index < 4
            ):
                return False

            explanation = question.get("explanation")

            if (
                not isinstance(explanation, str)
                or not explanation.strip()
            ):
                return False

    return True



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
        if "explanation" in q and (not isinstance(q["explanation"], str) or not q["explanation"].strip()):
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


