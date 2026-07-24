"""
store.py
--------
All SQLite reads/writes for the AZ-900 learning loop live here. Nothing in
this file talks to Groq/OpenAI or does any scoring logic — that's
service.py's job. This file is *only* "save this" / "read that back".

It reuses the exact same connection helper (`_conn()`) and the exact same
SQLite database file as the rest of the app (see session_store.py) — we're
just adding three more tables to it, not standing up a second database.

THE THREE TABLES:
  1. domain_mastery      — running correct/total answer counts, per session,
                            per AZ-900 domain. This is "how good is this
                            learner at each domain" and is the main input to
                            the progress bar and the weak-areas sidebar.
  2. pending_assessments — the server-side answer key for a diagnostic that
                            has been started but not yet submitted. The
                            client only ever sees questions + choices, never
                            the correct answerIndex — grading always happens
                            against what's stored here, never against
                            anything the client claims is correct. Rows are
                            deleted the moment they're graded (single-use).
  3. practice_log         — one row per practice game actually PLAYED TO THE
                            END, with its real score (correct/total), reported
                            by the game itself via postMessage (see
                            games/bundle.py's reportGameResult helper and
                            PlayView.tsx's message listener) — not a manual
                            "mark complete" click. The score also gets folded
                            into domain_mastery via record_result() (the same
                            function the diagnostic uses), so practice_log
                            itself is really just an attempt history for
                            display ("you've practiced Quiz Flyer 3 times") —
                            it doesn't independently drive the progress bar.
"""

import datetime
import json
import uuid

from ..session_store import _conn
from .knowledge_base import DOMAINS


def init_db() -> None:
    """
    Create all three learning-related tables if they don't already exist.
    Safe to call every time the app starts (CREATE TABLE IF NOT EXISTS).
    Called once from main.py alongside session_store.init_db().
    """
    conn = _conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS domain_mastery (
            session_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            correct INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (session_id, domain)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_assessments (
            assessment_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            questions_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_log (
            session_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            correct INTEGER NOT NULL,
            total INTEGER NOT NULL,
            completed_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# domain_mastery — diagnostic accuracy per domain
# ---------------------------------------------------------------------------

def record_result(session_id: str, domain: str, correct: int, total: int) -> None:
    """
    Add `correct` right answers out of `total` questions to this session's
    running total for `domain`. This is additive/cumulative on purpose — if
    a learner retakes the diagnostic, their history isn't wiped, it
    accumulates (so mastery reflects everything they've ever answered, not
    just the most recent attempt).

    Called once per domain that appeared in a submitted assessment — see
    service.submit_assessment().
    """
    conn = _conn()
    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO domain_mastery (session_id, domain, correct, total, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id, domain) DO UPDATE SET
            correct = correct + excluded.correct,
            total = total + excluded.total,
            updated_at = excluded.updated_at
        """,
        (session_id, domain, correct, total, now),
    )
    conn.commit()
    conn.close()


def get_mastery(session_id: str) -> list[dict]:
    """
    Return one entry per AZ-900 domain (always all 3, in DOMAINS order, even
    if a domain has never been attempted — total/correct come back as 0 and
    masteryPct as 0 rather than the entry being missing). This "always all 3"
    guarantee is relied on by the frontend, which renders exactly 3 progress
    bars without checking for missing entries.
    """
    conn = _conn()
    rows = {
        row["domain"]: row
        for row in conn.execute(
            "SELECT domain, correct, total FROM domain_mastery WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    }
    conn.close()

    result = []
    for domain in DOMAINS:
        row = rows.get(domain)
        correct = row["correct"] if row else 0
        total = row["total"] if row else 0
        mastery_pct = round((correct / total) * 100) if total else 0
        result.append({"domain": domain, "correct": correct, "total": total, "masteryPct": mastery_pct})
    return result


def get_weakest_domain(session_id: str) -> str:
    """
    Pick the single domain to recommend practicing next.

    Domains with zero attempts (total == 0) always sort as "weakest" ahead of
    any domain with a real (even low) score — the logic being: we have *no*
    data on an untouched domain, so a fresh learner should be pointed at a
    full diagnostic covering everything, not nudged toward whichever domain
    happens to be listed first.
    """
    mastery = get_mastery(session_id)
    weakest = min(mastery, key=lambda m: (m["total"] > 0, m["masteryPct"]))
    return weakest["domain"]


# ---------------------------------------------------------------------------
# pending_assessments — server-held answer key for an in-flight diagnostic
# ---------------------------------------------------------------------------

def save_pending_assessment(session_id: str, questions: list[dict]) -> str:
    """
    Stash the full question list — INCLUDING each question's correct
    answerIndex — under a brand-new random assessment_id, and return that id.
    The caller (service.start_assessment) sends the id to the client along
    with a *stripped* version of `questions` that has no answerIndex in it.
    """
    assessment_id = uuid.uuid4().hex
    conn = _conn()
    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO pending_assessments (assessment_id, session_id, questions_json, created_at) "
        "VALUES (?, ?, ?, ?)",
        (assessment_id, session_id, json.dumps(questions), now),
    )
    conn.commit()
    conn.close()
    return assessment_id


def pop_pending_assessment(session_id: str, assessment_id: str) -> list[dict] | None:
    """
    Fetch the answer key for `assessment_id` AND delete it in the same call
    (hence "pop", like a stack) — this makes every assessment_id single-use,
    so replaying the same submit request twice (or a client trying to submit
    twice for extra mastery credit) fails the second time with None.

    Returns None if the id doesn't exist, doesn't belong to this session_id,
    or was already submitted once before.
    """
    conn = _conn()
    row = conn.execute(
        "SELECT questions_json FROM pending_assessments WHERE assessment_id = ? AND session_id = ?",
        (assessment_id, session_id),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM pending_assessments WHERE assessment_id = ?", (assessment_id,))
        conn.commit()
    conn.close()
    return json.loads(row["questions_json"]) if row else None


# ---------------------------------------------------------------------------
# practice_log — real, scored practice attempts (append-only history)
# ---------------------------------------------------------------------------

def log_attempt(session_id: str, game_id: str, domain: str, correct: int, total: int) -> None:
    """
    Record one practice game's real result, as reported by the game itself
    (see games/bundle.py's window.reportGameResult and PlayView.tsx's
    message listener). Purely an append-only history for display purposes
    ("you've practiced this domain 3 times") — the score itself is ALSO
    written to domain_mastery via record_result() by the caller
    (service.record_practice_result), which is what actually moves the
    progress bar. This table never drives scoring on its own.
    """
    conn = _conn()
    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO practice_log (session_id, game_id, domain, correct, total, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, game_id, domain, correct, total, now),
    )
    conn.commit()
    conn.close()


def get_practice_counts(session_id: str) -> dict[str, int]:
    """
    Return {domain: number_of_practice_attempts} for this session — how many
    times a practice game has actually been played to completion for each
    domain. Domains with zero attempts are simply absent from the dict —
    callers should use .get(domain, 0). Purely a display stat (see
    Az900WeakAreas.tsx) — does not feed the progress-bar formula.
    """
    conn = _conn()
    rows = conn.execute(
        "SELECT domain, COUNT(*) AS cnt FROM practice_log WHERE session_id = ? GROUP BY domain",
        (session_id,),
    ).fetchall()
    conn.close()
    return {row["domain"]: row["cnt"] for row in rows}


def get_recent_attempts(session_id: str, limit: int = 5) -> list[dict]:
    """
    Most recent practice attempts (any domain/game), newest first — powers a
    small "recent activity" list in the weak-areas sidebar so a learner can
    see what they actually just played and how they scored.
    """
    conn = _conn()
    rows = conn.execute(
        "SELECT game_id, domain, correct, total, completed_at FROM practice_log "
        "WHERE session_id = ? ORDER BY completed_at DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
