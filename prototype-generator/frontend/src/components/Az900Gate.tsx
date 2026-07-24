/**
 * Az900Gate.tsx
 * --------------
 * The very first thing a brand-new session sees (see App.tsx's mount-time
 * dashboard check) — a plain prompt, not the quiz itself and not the Game
 * Menu. Nothing is playable from here; the ONLY action is starting the
 * diagnostic. This is what makes "you cannot play any games before the
 * diagnostic" literally true: there is no menu, no library, nothing to
 * click except "Start Diagnostic" until App.tsx switches to
 * "az900-diagnostic".
 */

interface Props {
  onStart: () => void;
}

export default function Az900Gate({ onStart }: Props) {
  return (
    <div className="az900-gate">
      <div className="az900-gate-card">
        <h1>AZ-900 Study Companion</h1>
        <p>
          Before anything else, a quick 10-question diagnostic finds out where you already stand
          across all 3 AZ-900 exam domains. Once it's graded, your Game Menu unlocks with
          practice games built around whatever you got wrong.
        </p>
        <button className="btn" onClick={onStart}>
          Start Diagnostic
        </button>
      </div>
    </div>
  );
}
