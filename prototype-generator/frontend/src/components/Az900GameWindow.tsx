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
 *   3. Az900GameMenu (right) — all 7 games; clicking one opens a domain
 *      picker (Az900DomainPicker) rather than launching directly.
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
import type { DomainMastery, PlayingGame } from "../types";

interface Props {
  sessionId: string;
  /** Bump this from the parent (e.g. after a game reports a real result) to
   * force a fresh fetch of progress. */
  refreshKey: number;
  onRetakeDiagnostic: () => void;
  onPlay: (game: PlayingGame, az900GameId: string, az900Domain: string) => void;
}

export default function Az900GameWindow({ sessionId, refreshKey, onRetakeDiagnostic, onPlay }: Props) {
  const [domains, setDomains] = useState<DomainMastery[]>([]);
  const [weakestDomain, setWeakestDomain] = useState("");
  const [overallProgress, setOverallProgress] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchDashboard(sessionId)
      .then((d) => {
        setDomains(d.domains);
        setWeakestDomain(d.weakestDomain);
        setOverallProgress(d.overallProgress);
      })
      .finally(() => setLoading(false));
  }, [sessionId, refreshKey]);

  if (loading && domains.length === 0) {
    return (
      <div className="az900">
        <div className="status-text">Loading your progress…</div>
      </div>
    );
  }

  return (
    <div className="az900">
      <Az900ProgressBar value={overallProgress} label="Program Progress" />
      <div className="az900-window">
        <Az900WeakAreas domains={domains} onRetakeDiagnostic={onRetakeDiagnostic} />
        <Az900GameMenu
          sessionId={sessionId}
          refreshKey={refreshKey}
          domains={domains}
          weakestDomain={weakestDomain}
          onPlay={onPlay}
        />
      </div>
    </div>
  );
}
