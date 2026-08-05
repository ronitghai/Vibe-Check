/**
 * Az900RecommendationCard.tsx
 * -----------------------------
 * The highlighted "do this next" banner at the top of the Game Menu (see
 * Az900GameWindow.tsx) — a shortcut around the normal card-click ->
 * Az900DomainPicker flow. `recommendation` comes straight from the backend
 * (learning/service.py's _recommend_next_activity, part of every dashboard
 * response) and already carries a chosen game_id + domain, so this
 * component only needs to launch it, not ask the learner to pick anything.
 *
 * Not shown at all if there's no recommendation to make (see
 * Az900GameWindow's `{recommendation && ...}` guard) — that only happens if
 * the dashboard fetch is still loading or genuinely returned none.
 */

import { useState } from "react";
import { generatePracticeContent } from "../api/client";
import type { RecommendedActivityApi } from "../api/client";
import type { PlayingGame } from "../types";

interface Props {
  sessionId: string;
  recommendation: RecommendedActivityApi;
  onPlay: (game: PlayingGame, gameId: string, domain: string) => void;
}

export default function Az900RecommendationCard({ sessionId, recommendation, onPlay }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** Generate AZ-900-grounded content for the recommended game_id/domain
   * (same generatePracticeContent call every other launch path in the app
   * uses — see Az900GameMenu.tsx) and hand off to PlayView. */
  async function launch() {
    setBusy(true);
    setError(null);
    try {
      const res = await generatePracticeContent(sessionId, recommendation.gameId, recommendation.domain);
      onPlay(
        { gameId: res.game_id, gameType: res.game_type as "template" | "generated" },
        res.game_id,
        res.domain
      );
    } catch {
      setError("Could not generate the recommended activity. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="recommendation-card">
      <div>
        <div className="game-meta">Recommended next activity</div>
        <h3>{recommendation.gameLabel}</h3>
        <p>
          <strong>{recommendation.domain}</strong> · {recommendation.difficulty} · {recommendation.masteryPct}%
          mastery
        </p>
        <p>{recommendation.reason}</p>
        {error && <p className="error">{error}</p>}
      </div>
      <button className="btn" disabled={busy} onClick={launch}>
        {busy ? "Preparing…" : "Start recommendation"}
      </button>
    </section>
  );
}
