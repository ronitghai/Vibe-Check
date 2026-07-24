/**
 * api/client.ts
 * --------------
 * Every backend call the frontend makes, as thin typed fetch wrappers — one
 * function per endpoint, grouped by feature. The top section (chat/library/
 * games) is generic game-serving infra used by every launch path; the AZ-900
 * section below is specific to the diagnostic/progress/practice loop (see
 * that section's own header comment).
 */

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface ChatApiResponse {
  reply: string;
  game_ready: boolean;
  game_id: string | null;
  game_type: "template" | "generated" | null;
  /** Which AZ-900 domain the launched game targets (see orchestrator.py) —
   * null when no game was launched this turn. Lets a chat-generated game
   * report a real score the same way a Game Menu practice game does. */
  domain: string | null;
}

export interface GameBundle {
  game_id: string;
  game_type: string;
  title: string;
  html: string;
}

export interface LibraryItemApi {
  game_id: string;
  game_type: string;
  title: string;
  description: string;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export async function sendChatMessage(sessionId: string, message: string): Promise<ChatApiResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}

export async function fetchLibrary(sessionId: string): Promise<LibraryItemApi[]> {
  const res = await fetch(`${API_BASE}/api/library/${sessionId}`);
  if (!res.ok) throw new Error(`Library fetch failed: ${res.status}`);
  const data = await res.json();
  return data.items;
}

export async function fetchGameById(sessionId: string, gameId: string): Promise<GameBundle> {
  const res = await fetch(`${API_BASE}/api/games/${sessionId}/${gameId}`);
  if (!res.ok) throw new Error(`Game fetch failed: ${res.status}`);
  return res.json();
}

export async function launchTemplateGame(sessionId: string, gameId: string): Promise<GameBundle> {
  const res = await fetch(`${API_BASE}/api/games/launch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, game_id: gameId }),
  });
  if (!res.ok) throw new Error(`Launch failed: ${res.status}`);
  return res.json();
}

export async function fetchHistory(sessionId: string): Promise<HistoryMessage[]> {
  const res = await fetch(`${API_BASE}/api/history/${sessionId}`);
  if (!res.ok) throw new Error(`History fetch failed: ${res.status}`);
  const data = await res.json();
  return data.messages;
}

// ===========================================================================
// AZ-900 learning companion
// ---------------------------------------------------------------------------
// Every function below is a thin wrapper around one backend/app/routers/az900.py
// endpoint. The TypeScript interfaces here are hand-kept in sync with the
// Pydantic models in backend/app/learning/models.py — if you add/rename a
// field on one side, update the other side too (there's no code generation
// tying them together, it's just "make sure the shapes match").
// ===========================================================================

/** One diagnostic question as shown to the learner — no correct answer
 * included, the server never sends that until after grading. */
export interface AssessmentQuestion {
  question_id: number;
  domain: string;
  question: string;
  choices: string[];
}

export interface AssessmentStartResponse {
  assessment_id: string;
  questions: AssessmentQuestion[];
}

/** One answer the learner picked, sent back on submit. */
export interface AssessmentAnswer {
  question_id: number;
  choice_index: number;
}

/** Shown in the results modal for each question the learner missed. The
 * `explanation` text always comes from the backend's hand-authored
 * knowledge base, never generated on the fly. */
export interface MissedExplanation {
  question: string;
  yourAnswer: string | null;
  correctAnswer: string;
  domain: string;
  explanation: string;
}

/** One row of the progress table for one AZ-900 domain. `practiceCount` is
 * how many practice games have actually been PLAYED (and scored) for this
 * domain — see PlayView's postMessage listener, not a manual click. */
export interface DomainMasteryApi {
  domain: string;
  correct: number;
  total: number;
  masteryPct: number;
  practiceCount: number;
}

export interface AssessmentSubmitResponse {
  results: { question_id: number; domain: string; correct: boolean }[];
  explanations: MissedExplanation[];
  score: { correct: number; total: number };
  mastery: DomainMasteryApi[];
  weakestDomain: string;
}

/** Returned by both GET /dashboard and POST /practice/result — same shape
 * either way, so the caller can treat them interchangeably: whichever one
 * just responded becomes the new progress state.
 * `overallProgress` (0-100) is the single number the top progress bar shows
 * — see backend/app/learning/service.py's get_progress_summary: it's a
 * plain average of real accuracy (masteryPct) across the 3 domains, where
 * "real accuracy" blends diagnostic answers AND actual practice-game
 * results (both flow into the same domain_mastery accumulator). */
export interface DashboardResponse {
  domains: DomainMasteryApi[];
  weakestDomain: string;
  overallProgress: number;
}

export interface GeneratePracticeGameResponse {
  game_id: string;
  game_type: string;
  domain: string;
}

/** One real scored result reported by a game via postMessage — see
 * PlayView.tsx's message listener and games/bundle.py's reportGameResult. */
export interface GameResult {
  gameId: string;
  domain: string;
  correct: number;
  total: number;
}

/** Kick off a new 10-question diagnostic for this session. */
export async function startAssessment(sessionId: string): Promise<AssessmentStartResponse> {
  const res = await fetch(`${API_BASE}/api/az900/assessment/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Assessment start failed: ${res.status}`);
  return res.json();
}

/** Submit answers for grading. Throws if the assessment_id is unknown or was
 * already submitted once (the backend enforces single-use). */
export async function submitAssessment(
  sessionId: string,
  assessmentId: string,
  answers: AssessmentAnswer[]
): Promise<AssessmentSubmitResponse> {
  const res = await fetch(`${API_BASE}/api/az900/assessment/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, assessment_id: assessmentId, answers }),
  });
  if (!res.ok) throw new Error(`Assessment submit failed: ${res.status}`);
  return res.json();
}

/** Generate + launch AZ-900-grounded content for `gameId` (any of the 7
 * template games) targeting `domain` (omit to target whichever domain is
 * currently weakest). This is what Az900DomainPicker calls once a learner
 * has picked both a game card and a domain. */
export async function generatePracticeContent(
  sessionId: string,
  gameId: string,
  domain?: string
): Promise<GeneratePracticeGameResponse> {
  const res = await fetch(`${API_BASE}/api/az900/game/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, game_id: gameId, domain: domain ?? null }),
  });
  if (!res.ok) throw new Error(`Practice content generation failed: ${res.status}`);
  return res.json();
}

/** Fetch the current progress summary (mastery + practice + overall %) for
 * the progress bar and weak-areas panel. */
export async function fetchDashboard(sessionId: string): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE}/api/az900/dashboard/${sessionId}`);
  if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
  return res.json();
}

/** Report a practice game's REAL score (received via postMessage — see
 * PlayView.tsx). Feeds domain_mastery directly, same accumulator the
 * diagnostic uses. Returns the freshly recomputed progress summary (same
 * shape as fetchDashboard) so the caller can update state immediately. */
export async function reportPracticeResult(sessionId: string, result: GameResult): Promise<DashboardResponse> {
  const res = await fetch(`${API_BASE}/api/az900/practice/result`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      game_id: result.gameId,
      domain: result.domain,
      correct: result.correct,
      total: result.total,
    }),
  });
  if (!res.ok) throw new Error(`Reporting practice result failed: ${res.status}`);
  return res.json();
}
