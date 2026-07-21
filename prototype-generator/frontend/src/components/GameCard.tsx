import type { LibraryItem } from "../types";

const ICONS: Record<string, string> = {
  tic_tac_toe: "⭕",
  wheel_of_fortune: "🎡",
  flappy_bird: "🐦",
  memory_match: "🧠",
  matching_game: "🔗",
  crossword: "📝",
  rapid_quiz: "⚡",
};

interface Props {
  item: LibraryItem;
  busy: boolean;
  onPlay: () => void;
}

export default function GameCard({ item, busy, onPlay }: Props) {
  const icon = ICONS[item.gameId] || "✨";
  return (
    <button className="game-card" onClick={onPlay} disabled={busy}>
      <div className="game-card-icon">{icon}</div>
      <div className="game-card-title">{item.title}</div>
      <div className="game-card-desc">{item.description}</div>
      <div className={`game-card-badge ${item.gameType}`}>
        {busy ? "Launching…" : item.gameType === "template" ? "Template" : "AI-Generated"}
      </div>
    </button>
  );
}
