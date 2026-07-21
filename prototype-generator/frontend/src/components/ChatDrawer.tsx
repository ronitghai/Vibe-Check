import ChatWindow from "./ChatWindow";
import type { PlayingGame } from "../types";

interface Props {
  sessionId: string;
  open: boolean;
  onClose: () => void;
  onGameLaunched: (game: PlayingGame) => void;
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
          onGameLaunched={(gameId, gameType) => onGameLaunched({ gameId, gameType })}
        />
      </div>
    </>
  );
}
