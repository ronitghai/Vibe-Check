"""
routers/az900.py
-----------------
Thin HTTP layer for the AZ-900 learning companion. Every handler here is
just: unpack the request, call one function in learning/service.py, wrap the
result in a response model. All the actual logic (grading, the progress
formula, calling the LLM, launching a game) lives in service.py — if you're
looking for "how does X work", this file is the wrong place to look, go to
service.py instead.

Mounted onto the app in main.py via app.include_router(az900.router).
"""

from fastapi import APIRouter, HTTPException

from ..learning import service
from ..learning.models import (
    AssessmentStartRequest,
    AssessmentStartResponse,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    DashboardResponse,
    GeneratePracticeGameRequest,
    GeneratePracticeGameResponse,
    PracticeResultRequest,
)

router = APIRouter(prefix="/api/az900")


@router.post("/assessment/start", response_model=AssessmentStartResponse)
def assessment_start(req: AssessmentStartRequest) -> AssessmentStartResponse:
    """Start a new 10-question diagnostic for this session. See
    service.start_assessment for how questions are sampled."""
    return AssessmentStartResponse(**service.start_assessment(req.session_id))


@router.post("/assessment/submit", response_model=AssessmentSubmitResponse)
def assessment_submit(req: AssessmentSubmitRequest) -> AssessmentSubmitResponse:
    """Grade a completed diagnostic. 400s if assessment_id is unknown or was
    already submitted once (service.submit_assessment raises ValueError for
    both — see store.pop_pending_assessment's single-use behavior)."""
    try:
        result = service.submit_assessment(
            req.session_id, req.assessment_id, [a.model_dump() for a in req.answers]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AssessmentSubmitResponse(**result)


@router.post("/game/generate", response_model=GeneratePracticeGameResponse)
def game_generate(req: GeneratePracticeGameRequest) -> GeneratePracticeGameResponse:
    """Generate + launch AZ-900-grounded content for `game_id` (any of the 7
    template games), targeting `domain` (or the current weakest domain if
    omitted). 400s for a game_id that isn't a real template game. See
    service.generate_practice_content."""
    try:
        result = service.generate_practice_content(req.session_id, req.game_id, req.domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return GeneratePracticeGameResponse(**result)


@router.get("/dashboard/{session_id}", response_model=DashboardResponse)
def dashboard(session_id: str) -> DashboardResponse:
    """Everything the post-diagnostic screen needs in one call: per-domain
    mastery + practice counts, the weakest domain, and the combined
    overallProgress number for the top progress bar."""
    return DashboardResponse(**service.get_progress_summary(session_id))


@router.post("/practice/result", response_model=DashboardResponse)
def practice_result(req: PracticeResultRequest) -> DashboardResponse:
    """Called when a practice game reports its REAL score via postMessage
    (see PlayView.tsx). Feeds the score into domain_mastery (the same
    accumulator the diagnostic uses) and the attempt-history log, then
    returns the freshly recomputed progress summary — same shape as
    GET /dashboard, so the frontend can just overwrite its progress state
    with the response."""
    return DashboardResponse(
        **service.record_practice_result(req.session_id, req.game_id, req.domain, req.correct, req.total)
    )
