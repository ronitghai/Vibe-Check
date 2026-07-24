/**
 * PlayView.tsx
 * ------------
 * Renders one game (template or AI-generated) in a sandboxed iframe. This
 * component is shared by every launch path in the app — Game Menu cards and
 * the chat generator alike — always returning to the Game Menu, so
 * `onBack`'s destination is fixed; the only thing that varies per launch is
 * whether the launch is a scored one:
 *
 *   - `az900GameId` + `az900Domain` + `onGameResult` — when ALL THREE are
 *     provided, this component listens for the game's own REAL score,
 *     reported via postMessage from inside the iframe (see games/bundle.py's
 *     window.reportGameResult, which every one of the 7 template games
 *     calls at its own "game over" moment, and which is also injected into
 *     chat-generated games). There is no manual button here — the score is
 *     whatever the game actually reports, nothing the learner (or this
 *     component) can fake. A small transient banner confirms it was
 *     received.
 */

import { useEffect, useRef, useState } from "react";
import { fetchGameById } from "../api/client";
import type { PlayingGame } from "../types";
import type { GameResult } from "../api/client";

interface Props {
  sessionId: string;
  game: PlayingGame;
  onBack: () => void;
  az900GameId?: string;
  az900Domain?: string;
  onGameResult?: (result: GameResult) => void;
}

export default function PlayView({
  sessionId,
  game,
  onBack,
  az900GameId,
  az900Domain,
  onGameResult,
}: Props) {
  const [html, setHtml] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Transient "✓ Result recorded: 4/5" banner, cleared a few seconds after
  // a result comes in (or when a new game loads).
  const [resultBanner, setResultBanner] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setHtml(null);
    setResultBanner(null);

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

  // Listen for the game's real score. Only wired up when this game was
  // launched from the AZ-900 flow (all three props present) — everywhere
  // else in the app, onGameResult is undefined and this listener no-ops.
  useEffect(() => {
    if (!az900GameId || !az900Domain || !onGameResult) return;
    // Re-bind to new const locals — TypeScript won't carry the narrowing
    // above into the nested closure below for props/params, since it can't
    // prove they aren't reassigned before the closure runs.
    const gameId = az900GameId;
    const domain = az900Domain;
    const reportResult = onGameResult;

    function handleMessage(event: MessageEvent) {
      // Ignore anything that didn't come from THIS game's own iframe —
      // sandboxed iframes have an opaque origin, so we check the message
      // source window reference instead of event.origin.
      if (event.source !== iframeRef.current?.contentWindow) return;
      const data = event.data;
      if (!data || data.source !== "game-engine" || data.type !== "game-result") return;

      const correct = Number(data.correct) || 0;
      const total = Number(data.total) || 0;
      if (total <= 0) return; // nothing meaningful to report

      reportResult({ gameId, domain, correct, total });
      setResultBanner(`✓ Result recorded: ${correct}/${total}`);
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [az900GameId, az900Domain, game.gameId]);

  return (
    <div className="play-view">
      <div className="play-header">
        <button className="back-btn" onClick={onBack}>
          ← Back to AZ-900 Prep
        </button>
        <div className="play-title">{title || "Loading…"}</div>
        {resultBanner && <div className="result-banner">{resultBanner}</div>}
      </div>
      {loading && <div className="play-status">Loading game…</div>}
      {error && <div className="play-status error">{error}</div>}
      {html && (
        <iframe ref={iframeRef} className="game-frame" sandbox="allow-scripts" srcDoc={html} title={title} />
      )}
    </div>
  );
}
