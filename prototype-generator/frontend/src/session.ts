const KEY = "game_chat_session_id";

export function getSessionId(): string {
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(KEY, id);
  }
  return id;
}

/** "Reset Progress" (see Az900WeakAreas.tsx): every AZ-900 table on the
 * backend — domain_mastery, topic_coverage, practice_log, chat history,
 * launched games — is keyed entirely by session_id, and there's no
 * cross-session listing anywhere in the app. So a full reset doesn't need
 * any backend deletion call at all: swapping in a brand-new session_id
 * makes every future request land on a session the backend has never seen,
 * which is indistinguishable from a first-time visitor. The old session's
 * rows are simply orphaned (harmless for a per-learner local dev database).
 * Caller is responsible for reloading afterward so all React state
 * re-initializes against the new id. */
export function resetSession(): string {
  const id = crypto.randomUUID();
  localStorage.setItem(KEY, id);
  return id;
}
