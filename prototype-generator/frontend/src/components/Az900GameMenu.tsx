/**
 * Az900GameMenu.tsx
 * --------------------
 * The Game Menu shown after a diagnostic exists (see App.tsx's gating) — a
 * grid of all 7 games, reusing GameCard for the exact same look as the
 * regular library grid. Every card behaves the same way here: clicking it
 * does NOT launch immediately. It opens Az900DomainPicker ("which domain
 * should this round focus on?", weakest pre-flagged) — only once a domain
 * is chosen does generatePracticeContent() actually run and the game
 * launch.
 *
 * ALL 7 games get AZ-900-grounded content now (not just the quiz-shaped
 * ones) — see learning/service.py's per-game generator dispatch
 * (_build_config_overrides) for how each game's content is produced.
 */

import { useEffect, useState } from "react";
import { fetchLibrary, generatePracticeContent } from "../api/client";
import GameCard from "./GameCard";
import Az900DomainPicker from "./Az900DomainPicker";
import type { DomainMastery, LibraryItem, PlayingGame } from "../types";

interface Props {
  sessionId: string;
  refreshKey: number;
  domains: DomainMastery[];
  weakestDomain: string;
  /** `az900Domain` is what PlayView reports back against when the game ends. */
  onPlay: (game: PlayingGame, az900GameId: string, az900Domain: string) => void;
}

export default function Az900GameMenu({ sessionId, refreshKey, domains, weakestDomain, onPlay }: Props) {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState<string | null>(null);
  // Which game card is currently showing its domain picker, if any.
  const [pickerFor, setPickerFor] = useState<LibraryItem | null>(null);

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

  async function handleChooseDomain(domain: string) {
    const item = pickerFor;
    if (!item) return;
    setPickerFor(null);
    setLaunching(item.gameId);
    try {
      const res = await generatePracticeContent(sessionId, item.gameId, domain);
      onPlay({ gameId: res.game_id, gameType: res.game_type as "template" | "generated" }, res.game_id, res.domain);
    } finally {
      setLaunching(null);
    }
  }

  return (
    <div className="az900-menu">
      <div className="game-meta">Game Menu</div>
      {loading ? (
        <div className="status-text">Loading games…</div>
      ) : (
        <div className="game-grid">
          {items.map((item) => (
            <GameCard
              key={item.gameId}
              item={item}
              busy={launching === item.gameId}
              onPlay={() => setPickerFor(item)}
            />
          ))}
        </div>
      )}

      {pickerFor && (
        <Az900DomainPicker
          gameTitle={pickerFor.title}
          domains={domains}
          weakestDomain={weakestDomain}
          onChoose={handleChooseDomain}
          onCancel={() => setPickerFor(null)}
        />
      )}
    </div>
  );
}
