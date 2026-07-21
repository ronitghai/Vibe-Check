import { useState } from "react";
import LibraryView from "./components/LibraryView";
import PlayView from "./components/PlayView";
import ChatDrawer from "./components/ChatDrawer";
import { getSessionId } from "./session";
import type { PlayingGame } from "./types";
import "./App.css";

export default function App() {
  const [sessionId] = useState(getSessionId);
  const [view, setView] = useState<"library" | "play">("library");
  const [playingGame, setPlayingGame] = useState<PlayingGame | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [libraryVersion, setLibraryVersion] = useState(0);

  function handlePlay(game: PlayingGame) {
    setPlayingGame(game);
    setView("play");
  }

  function handleGameLaunchedFromChat(game: PlayingGame) {
    setChatOpen(false);
    setLibraryVersion((v) => v + 1);
    handlePlay(game);
  }

  return (
    <div className="app">
      <header className="app-header">🎮 AI Game Chat</header>

      <main className="app-main">
        {view === "library" || !playingGame ? (
          <LibraryView sessionId={sessionId} refreshKey={libraryVersion} onPlay={handlePlay} />
        ) : (
          <PlayView sessionId={sessionId} game={playingGame} onBack={() => setView("library")} />
        )}
      </main>

      <button className="fab" onClick={() => setChatOpen(true)}>
        ✨ Generate a game
      </button>

      <ChatDrawer
        sessionId={sessionId}
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        onGameLaunched={handleGameLaunchedFromChat}
      />
    </div>
  );
}
