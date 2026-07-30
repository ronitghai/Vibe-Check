/**
 * Az900GameMenu.tsx
 * --------------------
 * Displays curated AZ-900 learning activities and AI-generated custom games.
 *
 * Curated template activities:
 * - Open the domain picker.
 * - Generate personalized content for the selected domain.
 *
 * AI-generated custom games:
 * - Have already been generated and stored by the backend.
 * - Launch directly without calling generatePracticeContent() again.
 */

import { useEffect, useState } from "react";
import { fetchLibrary, generatePracticeContent } from "../api/client";
import GameCard from "./GameCard";
import Az900DomainPicker from "./Az900DomainPicker";
import type {
  DomainMastery,
  LibraryItem,
  PlayingGame,
} from "../types";

interface Props {
  sessionId: string;
  refreshKey: number;
  domains: DomainMastery[];
  weakestDomain: string;

  /**
   * az900GameId identifies the game whose result is being reported.
   * az900Domain determines which domain receives the practice result.
   */
  onPlay: (
    game: PlayingGame,
    az900GameId: string,
    az900Domain: string
  ) => void;
}

type MenuItem = LibraryItem & {
  domain?: string;
};

export default function Az900GameMenu({
  sessionId,
  refreshKey,
  domains,
  weakestDomain,
  onPlay,
}: Props) {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState<string | null>(null);

  // Only template activities need a domain picker.
  const [pickerFor, setPickerFor] = useState<MenuItem | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    fetchLibrary(sessionId)
      .then((raw) => {
        if (cancelled) {
          return;
        }

        setItems(
          raw.map((item) => {
            const itemWithOptionalDomain = item as typeof item & {
              domain?: string;
            };

            return {
              gameId: item.game_id,
              gameType: item.game_type as "template" | "generated",
              title: item.title,
              description: item.description,
              domain: itemWithOptionalDomain.domain,
            };
          })
        );
      })
      .catch((fetchError) => {
        console.error("Could not load game library:", fetchError);

        if (!cancelled) {
          setItems([]);
          setError("Could not load the learning activities.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, refreshKey]);

  /**
   * Launch an AI-generated game directly.
   *
   * The generated game already has a saved HTML bundle, so it must not be sent
   * through the curated practice-generation endpoint again.
   */
  function launchGeneratedGame(item: MenuItem) {
    setError(null);
    setLaunching(item.gameId);

    try {
      const domain = item.domain ?? weakestDomain;

      onPlay(
        {
          gameId: item.gameId,
          gameType: "generated",
        },
        item.gameId,
        domain
      );
    } catch (launchError) {
      console.error("Could not launch generated game:", launchError);
      setError("Could not launch this generated game. Please try again.");
    } finally {
      setLaunching(null);
    }
  }

  /**
   * Handle a card click.
   *
   * Templates need a selected domain before personalized content is generated.
   * Generated games already exist and can launch immediately.
   */
  function handleCardPlay(item: MenuItem) {
    if (item.gameType === "generated") {
      launchGeneratedGame(item);
      return;
    }

    setPickerFor(item);
  }

  /**
   * Generate personalized content for a curated template after the learner
   * chooses an AZ-900 domain.
   */
  async function handleChooseDomain(domain: string) {
    const item = pickerFor;

    if (!item) {
      return;
    }

    setPickerFor(null);
    setLaunching(item.gameId);
    setError(null);

    try {
      // Safety check in case a generated item somehow reaches the picker.
      if (item.gameType === "generated") {
        onPlay(
          {
            gameId: item.gameId,
            gameType: "generated",
          },
          item.gameId,
          item.domain ?? domain
        );

        return;
      }

      const result = await generatePracticeContent(
        sessionId,
        item.gameId,
        domain
      );

      onPlay(
        {
          gameId: result.game_id,
          gameType: result.game_type as "template" | "generated",
        },
        result.game_id,
        result.domain
      );
    } catch (generationError) {
      console.error(
        "Could not prepare learning activity:",
        generationError
      );

      setError(
        "Could not prepare this learning activity. Please try again."
      );
    } finally {
      setLaunching(null);
    }
  }

  return (
    <div className="az900-menu">
      <div className="game-meta">
        Personalized Learning Activities
      </div>

      {error && (
        <div className="status-text error">
          {error}
        </div>
      )}

      {loading ? (
        <div className="status-text">
          Loading games…
        </div>
      ) : (
        <div className="game-grid">
          {items.map((item) => (
            <GameCard
              key={item.gameId}
              item={item}
              busy={launching === item.gameId}
              onPlay={() => handleCardPlay(item)}
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