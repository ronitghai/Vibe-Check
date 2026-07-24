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
    payload and in the dashboard/game-menu response below."""
    domain: str
    correct: int
    total: int
    masteryPct: int
    practiceCount: int = 0  # how many practice games have been PLAYED (and scored) for this domain


class AssessmentScore(BaseModel):
    correct: int
    total: int


class AssessmentSubmitResponse(BaseModel):
    results: List[AssessmentResult]
    explanations: List[MissedExplanation]
    score: AssessmentScore
    mastery: List[DomainMastery]
    weakestDomain: str


# --- POST /api/az900/game/generate ---

class GeneratePracticeGameRequest(BaseModel):
    session_id: str
    game_id: str  # which of the 7 template games to generate content for — required
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
