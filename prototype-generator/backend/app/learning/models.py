"""
models.py
---------
Pydantic request/response shapes for every /api/az900/* endpoint (see
routers/az900.py). Kept in their own file, separate from the app-wide
models.py, so the whole AZ-900 feature is self-contained under
backend/app/learning/ — delete this folder and the one `include_router`
line in main.py, and the rest of the app is untouched.

FastAPI validates outgoing responses against these classes automatically
(via `response_model=...` in the router), so if service.py's returned dict
is missing a field or has the wrong type, you'll get a clear error instead
of silently sending bad JSON to the frontend.
"""

from typing import List, Optional

from pydantic import BaseModel


# --- POST /api/az900/assessment/start ---

class AssessmentStartRequest(BaseModel):
    session_id: str


class AssessmentQuestion(BaseModel):
    """One diagnostic question as sent to the client — deliberately has NO
    answerIndex field. The correct answer only ever exists server-side."""
    question_id: int
    domain: str
    question: str
    choices: List[str]


class AssessmentStartResponse(BaseModel):
    assessment_id: str
    questions: List[AssessmentQuestion]


# --- POST /api/az900/assessment/submit ---

class AssessmentAnswer(BaseModel):
    """One answer the client is submitting: which question, which choice."""
    question_id: int
    choice_index: int


class AssessmentSubmitRequest(BaseModel):
    session_id: str
    assessment_id: str
    answers: List[AssessmentAnswer]


class AssessmentResult(BaseModel):
    question_id: int
    domain: str
    correct: bool


class MissedExplanation(BaseModel):
    """Shown in the results modal for every question the learner got wrong."""
    question: str
    yourAnswer: Optional[str] = None  # None if they somehow left it unanswered
    correctAnswer: str
    domain: str
    explanation: str  # pulled straight from knowledge_base.SNIPPETS, never LLM-generated


class DomainMastery(BaseModel):
    """One row of the progress table — used both in an assessment's result
    payload and in the dashboard/game-menu response below. masteryPct is
    literally topicsMastered/topicsTotal (see service.get_progress_summary)
    — a topic only counts once it's been answered correctly
    MASTERY_STREAK_THRESHOLD times IN A ROW, and a single miss resets that
    topic's streak to 0, so masteryPct can go DOWN as well as up."""
    domain: str
    correct: int
    total: int
    masteryPct: int
    practiceCount: int = 0  # how many practice games have been PLAYED (and scored) for this domain
    topicsCovered: int = 0  # distinct topics attempted at least once — informational, doesn't gate masteryPct
    topicsMastered: int = 0  # topics with a correct streak >= MASTERY_STREAK_THRESHOLD — this DOES gate masteryPct
    topicsTotal: int = 0  # total topics that exist for this domain (knowledge_base.TOPICS_BY_DOMAIN)


class AssessmentScore(BaseModel):
    correct: int
    total: int


class RecommendedActivity(BaseModel):
    gameId: str
    gameLabel: str
    domain: str
    difficulty: str
    masteryPct: int
    practiceCount: int
    reason: str


class AssessmentSubmitResponse(BaseModel):
    results: List[AssessmentResult]
    explanations: List[MissedExplanation]
    score: AssessmentScore
    mastery: List[DomainMastery]
    weakestDomain: str
    recommendedActivity: Optional[RecommendedActivity] = None


# --- POST /api/az900/game/generate ---

class GeneratePracticeGameRequest(BaseModel):
    session_id: str
    game_id: str  # curated learning activity id
    domain: Optional[str] = None  # omit to target the current weakest domain


class GeneratePracticeGameResponse(BaseModel):
    game_id: str
    game_type: str
    domain: str  # which domain the generated content ended up targeting


# --- GET /api/az900/dashboard/{session_id}  and  POST /api/az900/practice/result ---
# Both return this same shape (service.get_progress_summary /
# service.record_practice_result both build it) — the frontend re-renders
# from whichever one just responded.

class DashboardResponse(BaseModel):
    domains: List[DomainMastery]
    weakestDomain: str
    overallProgress: int  # 0-100, see service.get_progress_summary for the formula
    recommendedActivity: Optional[RecommendedActivity] = None


# --- GET /api/az900/study ---
# Plain reference content, outside the game/scoring loop entirely — same for
# every session, no session_id needed. See learning/service.py's
# get_study_content.

class StudyTopic(BaseModel):
    topic: str
    label: str  # the official AZ-900 skill-bullet text, e.g. "Describe the shared responsibility model"
    concepts: List[str]  # every fact written for this topic
    sources: List[str]  # real Microsoft Learn URLs these concepts are grounded in


class StudyDomain(BaseModel):
    domain: str
    topics: List[StudyTopic]


class StudyResponse(BaseModel):
    domains: List[StudyDomain]


# --- GET /api/az900/weak-concepts/{session_id} ---
# The learner's actual struggling topics (attempted, not yet mastered),
# explained inline — see learning/service.py's get_weak_concepts.

class WeakConceptTopic(BaseModel):
    domain: str
    topic: str
    label: str
    concepts: List[str]
    sources: List[str]
    correctStreak: int
    totalAttempts: int
    totalCorrect: int


class WeakConceptsResponse(BaseModel):
    topics: List[WeakConceptTopic]


class PracticeResultRequest(BaseModel):
    """Sent by the frontend when a game reports its real score via
    postMessage — see PlayView.tsx's message listener. `correct`/`total`
    are the game's own count, e.g. {correct: 4, total: 5} for a quiz, or
    {correct: 1, total: 1} for a Tic-Tac-Toe win."""
    session_id: str
    game_id: str
    domain: str
    correct: int
    total: int
