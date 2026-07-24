/**
 * Az900WeakAreas.tsx
 * --------------------
 * The sidebar shown next to the Game Menu (see Az900GameWindow.tsx).
 * DISPLAY ONLY — lists all 3 AZ-900 domains, weakest (lowest mastery %)
 * first, each with a mastery bar and how many practice rounds have been
 * scored for it. It does NOT choose what launches next — that job moved to
 * Az900DomainPicker, which appears at the moment a game card is clicked
 * (see Az900GameMenu.tsx). This panel is purely "here's where you stand",
 * plus the one action that's always available: retaking the diagnostic.
 */

import type { DomainMastery } from "../types";

interface Props {
  domains: DomainMastery[];
  onRetakeDiagnostic: () => void;
}

export default function Az900WeakAreas({ domains, onRetakeDiagnostic }: Props) {
  // Sort a COPY (never mutate the array a parent passed down as a prop) —
  // weakest domain first, so it's the first thing the learner sees.
  const sortedWeakestFirst = [...domains].sort((a, b) => a.masteryPct - b.masteryPct);

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
              {d.practiceCount} practice round{d.practiceCount === 1 ? "" : "s"} played
            </div>
          </div>
        ))}
      </div>

      <button className="btn btn-secondary az900-retake-btn" onClick={onRetakeDiagnostic}>
        Retake Diagnostic
      </button>
    </div>
  );
}
