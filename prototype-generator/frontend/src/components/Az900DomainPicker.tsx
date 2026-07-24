/**
 * Az900DomainPicker.tsx
 * -----------------------
 * A small modal shown the moment a learner clicks ANY game card in
 * Az900GameMenu.tsx — "quick option to select which content you want to
 * focus on when you select it" was the exact ask. Three buttons, one per
 * AZ-900 domain, current mastery % on each, weakest domain visually
 * flagged as the recommended pick. Choosing one is the only action here —
 * there's no separate "confirm" step, picking a domain immediately hands
 * control back to the caller (Az900GameMenu), which generates the content
 * and launches the game.
 */

import type { DomainMastery } from "../types";

interface Props {
  gameTitle: string;
  domains: DomainMastery[];
  weakestDomain: string;
  onChoose: (domain: string) => void;
  onCancel: () => void;
}

export default function Az900DomainPicker({ gameTitle, domains, weakestDomain, onChoose, onCancel }: Props) {
  return (
    <>
      <div className="drawer-backdrop open" onClick={onCancel} />
      <div className="az900-modal az900-picker-modal">
        <div className="drawer-header">
          <span>Choose a focus area</span>
          <button className="drawer-close" onClick={onCancel} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="az900-modal-body">
          <p className="az900-picker-subtitle">Which domain should this round of {gameTitle} focus on?</p>
          <div className="az900-picker-options">
            {domains.map((d) => (
              <button key={d.domain} className="az900-picker-option" onClick={() => onChoose(d.domain)}>
                <div className="az900-picker-option-top">
                  <span>{d.domain}</span>
                  {d.domain === weakestDomain && <span className="az900-picker-badge">Recommended</span>}
                </div>
                <div className="az900-bar az900-bar-small">
                  <div className="az900-bar-fill" style={{ width: `${d.masteryPct}%` }} />
                </div>
                <div className="az900-sidebar-item-meta">{d.total > 0 ? `${d.masteryPct}% mastery` : "Not started yet"}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
