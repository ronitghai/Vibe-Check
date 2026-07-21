import { useEffect, useState } from "react";
import { fetchGameById } from "../api/client";
import type { PlayingGame } from "../types";

interface Props {
  sessionId: string;
  game: PlayingGame;
  onBack: () => void;
}

export default function PlayView({ sessionId, game, onBack }: Props) {
  const [html, setHtml] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setHtml(null);

    fetchGameById(sessionId, game.gameId)
      .then((bundle) => {
        if (cancelled) return;
        setHtml(bundle.html);
        setTitle(bundle.title);
      })
      .catch(() => {
        if (!cancelled) setError("Couldn't load this game.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, game.gameId]);

  return (
    <div className="play-view">
      <div className="play-header">
        <button className="back-btn" onClick={onBack}>
          ← Back to Library
        </button>
        <div className="play-title">{title || "Loading…"}</div>
      </div>
      {loading && <div className="play-status">Loading game…</div>}
      {error && <div className="play-status error">{error}</div>}
      {html && <iframe className="game-frame" sandbox="allow-scripts" srcDoc={html} title={title} />}
    </div>
  );
}
