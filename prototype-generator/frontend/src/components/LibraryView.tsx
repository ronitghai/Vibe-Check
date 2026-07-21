import { useEffect, useState } from "react";
import { fetchLibrary, launchTemplateGame } from "../api/client";
import GameCard from "./GameCard";
import type { LibraryItem, PlayingGame } from "../types";

interface Props {
  sessionId: string;
  refreshKey: number;
  onPlay: (game: PlayingGame) => void;
}

export default function LibraryView({ sessionId, refreshKey, onPlay }: Props) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchLibrary(sessionId)
      .then((raw) =>
        setItems(
          raw.map((i) => ({
            gameId: i.game_id,
            gameType: i.game_type as "template" | "generated",
            title: i.title,
            description: i.description,
          }))
        )
      )
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [sessionId, refreshKey]);

  async function handlePlay(item: LibraryItem) {
    if (item.gameType === "template") {
      setLaunching(item.gameId);
      try {
        await launchTemplateGame(sessionId, item.gameId);
        onPlay({ gameId: item.gameId, gameType: item.gameType });
      } finally {
        setLaunching(null);
      }
    } else {
      onPlay({ gameId: item.gameId, gameType: item.gameType });
    }
  }

  return (
    <div className="library">
      <div className="library-header">
        <h2>Game Library</h2>
        <p>Pick a game to play instantly, or generate a new one.</p>
      </div>
      {loading ? (
        <div className="library-status">Loading library…</div>
      ) : (
        <div className="library-grid">
          {items.map((item) => (
            <GameCard
              key={item.gameId}
              item={item}
              busy={launching === item.gameId}
              onPlay={() => handlePlay(item)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
