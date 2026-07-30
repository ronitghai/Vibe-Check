/**
 * GameCard.tsx
 * -------------
 * Presentational card for curated and AI-generated learning activities.
 */

import type { LibraryItem } from "../types";

const ICONS: Record<string, string> = {
  rapid_quiz: "✅",
  scenario_challenge: "🏗️",
  matching_game: "🔗",
  crossword: "📝",
  jeopardy: "🏆",
};

interface Props {
  item: LibraryItem;
  busy: boolean;
  onPlay: () => void;
}

export default function GameCard({
  item,
  busy,
  onPlay,
}: Props) {
  const icon = ICONS[item.gameId] || "✨";

  return (
    <button
      className="game-card"
      onClick={onPlay}
      disabled={busy}
    >
      <div className="game-card-icon">
        {icon}
      </div>

      <div className="game-card-title">
        {item.title}
      </div>

      <div className="game-card-desc">
        {item.description}
      </div>

      <div
        className={`game-card-badge ${item.gameType}`}
      >
        {busy
          ? "Launching…"
          : item.gameType === "template"
            ? "Template"
            : "AI-Generated"}
      </div>
    </button>
  );
}