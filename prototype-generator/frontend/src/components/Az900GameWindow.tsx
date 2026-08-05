/**
 * Az900GameWindow.tsx
 * ---------------------
 * The main AZ-900 screen once a learner has completed at least one
 * diagnostic — App.tsx decides Diagnostic-first vs. this screen based on
 * whether any domain has total > 0 (see App.tsx's `openAz900Prep`).
 * Composes three pieces:
 *
 *   1. Az900ProgressBar (top) — overallProgress, a plain average of real
 *      accuracy across all 3 domains (diagnostic + practice combined —
 *      see learning/service.py's get_progress_summary).
 *   2. Az900WeakAreas (left) — display-only mastery/practice per domain,
 *      plus "Retake Diagnostic".
 *   3. Az900GameMenu (right) — curated learning activities; clicking one opens a domain
 *      picker (Az900DomainPicker) rather than launching directly.
 *   4. Az900WeakConcepts (full width, below the first two) — the actual
 *      TOPIC-level struggling spots, with their explanations shown inline,
 *      not just a domain percentage. Re-fetches on the same refreshKey as
 *      everything else here, so a topic drops off this list the instant
 *      it's mastered.
 *
 * Domain selection no longer lives here — each game launch asks "which
 * domain?" at the moment it's picked (see Az900GameMenu/Az900DomainPicker),
 * so this component just fetches and passes down the current progress data.
 */

import { useEffect, useState } from "react";
import { fetchDashboard } from "../api/client";
import Az900ProgressBar from "./Az900ProgressBar";
import Az900WeakAreas from "./Az900WeakAreas";
import Az900GameMenu from "./Az900GameMenu";
import Az900WeakConcepts from "./Az900WeakConcepts";
import Az900RecommendationCard from "./Az900RecommendationCard";
import type { RecommendedActivityApi } from "../api/client";
import type { DomainMastery, PlayingGame } from "../types";

interface Props {
  sessionId: string;
  /** Bump this from the parent (e.g. after a game reports a real result) to
   * force a fresh fetch of progress. */
  refreshKey: number;
  onRetakeDiagnostic: () => void;
  /** Wipes this session's AZ-900 progress (see session.ts's resetSession)
   * and sends the learner back to the gate — wired all the way up through
   * App.tsx since resetting also has to blow away App's own view state. */
  onResetProgress: () => void;
  onStudy: () => void;
  onPlay: (game: PlayingGame, az900GameId: string, az900Domain: string) => void;
}

export default function Az900GameWindow({
  sessionId,
  refreshKey,
  onRetakeDiagnostic,
  onResetProgress,
  onStudy,
  onPlay,
}: Props) {
  const [domains, setDomains] = useState<DomainMastery[]>([]);
  const [weakestDomain, setWeakestDomain] = useState("");
  const [overallProgress, setOverallProgress] = useState(0);
  const [loading, setLoading] = useState(true);
  const [recommendation, setRecommendation] = useState<RecommendedActivityApi | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchDashboard(sessionId)
      .then((d) => {
        setDomains(d.domains);
        setWeakestDomain(d.weakestDomain);
        setOverallProgress(d.overallProgress);
        setRecommendation(d.recommendedActivity ?? null);
      })
      .catch(() => setError("Could not load your dashboard."))
      .finally(() => setLoading(false));
  }, [sessionId, refreshKey]);

  if (loading && domains.length === 0) {
    return (
      <div className="az900">
        <div className="status-text">Loading your progress…</div>
      </div>
    );
  }

  const topicsCovered = domains.reduce((sum, d) => sum + d.topicsCovered, 0);
  const topicsMastered = domains.reduce((sum, d) => sum + d.topicsMastered, 0);
  const topicsTotal = domains.reduce((sum, d) => sum + d.topicsTotal, 0);

  return (
    <div className="az900">
      <Az900ProgressBar value={overallProgress} label="Program Progress" />
      {topicsTotal > 0 && (
        <div className="az900-coverage-line">
          {topicsMastered}/{topicsTotal} concepts mastered ({topicsCovered} touched), a concept needs 2 correct
          answers in a row to count, and a miss resets it
          <button className="az900-study-link" onClick={onStudy}>
            Study Concepts →
          </button>
        </div>
      )}
      {error && <div className="status-text error">{error}</div>}
      {recommendation && <Az900RecommendationCard sessionId={sessionId} recommendation={recommendation} onPlay={onPlay} />}
      <div className="az900-window">
        <Az900WeakAreas domains={domains} onRetakeDiagnostic={onRetakeDiagnostic} onResetProgress={onResetProgress} />
        <Az900GameMenu
          sessionId={sessionId}
          refreshKey={refreshKey}
          domains={domains}
          weakestDomain={weakestDomain}
          onPlay={onPlay}
        />
        <Az900WeakConcepts sessionId={sessionId} refreshKey={refreshKey} />
      </div>
    </div>
  );
}
