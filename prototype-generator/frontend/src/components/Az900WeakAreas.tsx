/**
 * Az900WeakAreas.tsx
 * --------------------
 * The sidebar shown next to the Game Menu (see Az900GameWindow.tsx).
 * DISPLAY ONLY — lists all 3 AZ-900 domains, weakest (lowest mastery %)
 * first, each with a mastery bar, its concept-coverage count (see
 * backend service.py's get_progress_summary — masteryPct can't reach 100%
 * until every topic is covered, so this is what explains WHY the bar caps
 * out even at perfect accuracy), and how many practice rounds have been
 * scored for it. It does NOT choose what launches next — that job moved to
 * Az900DomainPicker, which appears at the moment a game card is clicked
 * (see Az900GameMenu.tsx). This panel is purely "here's where you stand",
 * plus the two session-level actions that are always available: retaking
 * the diagnostic, and wiping this session's progress entirely to start
 * fresh (see session.ts's resetSession — a destructive, confirm-gated
 * action, so it's visually separated from "Retake Diagnostic").
 */

import type { DomainMastery } from "../types";

interface Props {
  domains: DomainMastery[];
  onRetakeDiagnostic: () => void;
  onResetProgress: () => void;
}

export default function Az900WeakAreas({ domains, onRetakeDiagnostic, onResetProgress }: Props) {
  // Sort a COPY (never mutate the array a parent passed down as a prop) —
  // weakest domain first, so it's the first thing the learner sees.
  const sortedWeakestFirst = [...domains].sort((a, b) => a.masteryPct - b.masteryPct);

  function handleReset() {
    if (window.confirm("Reset all AZ-900 progress and start fresh? This can't be undone.")) {
      onResetProgress();
    }
  }

  return (
    <div className="az900-sidebar">
      <div className="game-meta">Weak Areas</div>

      <div className="az900-sidebar-list">
        {sortedWeakestFirst.map((d) => (
          <div className="az900-sidebar-item" key={d.domain}>
            <div className="az900-sidebar-item-top">
              <span>{d.domain}</span>
              <span>{d.total > 0 ? `${d.masteryPct}%` : "Not started"}</span>
            </div>
            <div className="az900-bar az900-bar-small">
              <div className="az900-bar-fill" style={{ width: `${d.masteryPct}%` }} />
            </div>
            <div className="az900-sidebar-item-meta">
              {d.topicsMastered}/{d.topicsTotal} mastered ({d.topicsCovered} touched) · {d.practiceCount} practice
              round{d.practiceCount === 1 ? "" : "s"} played
            </div>
          </div>
        ))}
      </div>

      <button className="btn btn-secondary az900-retake-btn" onClick={onRetakeDiagnostic}>
        Retake Diagnostic
      </button>
      <button className="btn btn-danger az900-reset-btn" onClick={handleReset}>
        Reset Progress
      </button>
    </div>
  );
}
