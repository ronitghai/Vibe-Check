/**
 * ChatDrawer.tsx
 * ---------------
 * Slide-out panel hosting ChatWindow, mounted by App.tsx only while the
 * learner is on the Game Menu (see App.tsx's `view === "az900-game-window"`
 * check around the FAB/drawer) — the chat generator only makes sense once a
 * diagnostic exists and there's a Game Menu to return to.
 */

import ChatWindow from "./ChatWindow";
import type { PlayingGame } from "../types";

interface Props {
  sessionId: string;
  open: boolean;
  onClose: () => void;
  /** `domain` is the AZ-900 domain the backend tagged this game with (see
   * orchestrator.py) — passed straight through to App.tsx so it can wire up
   * real score reporting the same way a Game Menu practice game does. */
  onGameLaunched: (game: PlayingGame, domain: string) => void;
}

export default function ChatDrawer({ sessionId, open, onClose, onGameLaunched }: Props) {
  return (
    <>
      <div className={`drawer-backdrop ${open ? "open" : ""}`} onClick={onClose} />
      <div className={`chat-drawer ${open ? "open" : ""}`}>
        <div className="drawer-header">
          <span>✨ Generate a game</span>
          <button className="drawer-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <ChatWindow
          sessionId={sessionId}
          onGameLaunched={(gameId, gameType, domain) => onGameLaunched({ gameId, gameType }, domain)}
        />
      </div>
    </>
  );
}
