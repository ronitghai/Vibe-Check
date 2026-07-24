/**
 * Az900ProgressBar.tsx
 * ---------------------
 * One reusable progress bar, used in two places with different numbers fed
 * in by the caller:
 *   - Az900Diagnostic.tsx: value = (questions answered / total) * 100,
 *     label = "Diagnostic — complete it to unlock your Game Menu".
 *   - Az900GameWindow.tsx: value = overallProgress from the backend
 *     (see learning/service.py's get_progress_summary for the formula),
 *     label = "Program Progress".
 *
 * This component itself doesn't know or care which of those it's showing —
 * it just renders whatever `value`/`label` it's given. Keeping the "what do
 * these numbers mean" logic in the caller (not here) is what makes this
 * safely reusable in both places.
 */

interface Props {
  value: number; // 0-100
  label: string;
}

export default function Az900ProgressBar({ value, label }: Props) {
  // Clamp defensively — a caller bug that sends e.g. 130% shouldn't blow the
  // bar past the edge of its container.
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div className="az900-progress-wrap">
      <div className="az900-progress-label">
        <span>{label}</span>
        <span>{Math.round(clamped)}%</span>
      </div>
      <div className="az900-bar">
        <div className="az900-bar-fill" style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}
