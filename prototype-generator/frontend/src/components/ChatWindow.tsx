import { useEffect, useRef, useState } from "react";
import { fetchHistory, sendChatMessage } from "../api/client";
import type { ChatMessage } from "../types";

const WELCOME: ChatMessage = {
  role: "assistant",
  content:
    'Hi! Ask me to launch a game — try "let\'s play tic tac toe" or "make me a space-themed trivia quiz".',
};

interface Props {
  sessionId: string;
  onGameLaunched: (gameId: string, gameType: "template" | "generated") => void;
}

export default function ChatWindow({ sessionId, onGameLaunched }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHistory(sessionId)
      .then((history) => {
        if (history.length > 0) setMessages([WELCOME, ...history]);
      })
      .catch(() => {
        // No saved history yet (or backend unreachable) — keep just the welcome message.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);

    try {
      const res = await sendChatMessage(sessionId, text);
      setMessages((m) => [...m, { role: "assistant", content: res.reply || "…" }]);
      if (res.game_ready && res.game_id && res.game_type) {
        onGameLaunched(res.game_id, res.game_type);
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Couldn't reach the server — is the backend running?" },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <div className="chat-messages" ref={listRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {busy && <div className="msg assistant typing">…</div>}
      </div>
      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          placeholder="Ask for a game..."
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
