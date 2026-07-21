const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface ChatApiResponse {
  reply: string;
  game_ready: boolean;
  game_id: string | null;
  game_type: "template" | "generated" | null;
}

export interface GameBundle {
  game_id: string;
  game_type: string;
  title: string;
  html: string;
}

export interface LibraryItemApi {
  game_id: string;
  game_type: string;
  title: string;
  description: string;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export async function sendChatMessage(sessionId: string, message: string): Promise<ChatApiResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}

export async function fetchLibrary(sessionId: string): Promise<LibraryItemApi[]> {
  const res = await fetch(`${API_BASE}/api/library/${sessionId}`);
  if (!res.ok) throw new Error(`Library fetch failed: ${res.status}`);
  const data = await res.json();
  return data.items;
}

export async function fetchGameById(sessionId: string, gameId: string): Promise<GameBundle> {
  const res = await fetch(`${API_BASE}/api/games/${sessionId}/${gameId}`);
  if (!res.ok) throw new Error(`Game fetch failed: ${res.status}`);
  return res.json();
}

export async function launchTemplateGame(sessionId: string, gameId: string): Promise<GameBundle> {
  const res = await fetch(`${API_BASE}/api/games/launch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, game_id: gameId }),
  });
  if (!res.ok) throw new Error(`Launch failed: ${res.status}`);
  return res.json();
}

export async function fetchHistory(sessionId: string): Promise<HistoryMessage[]> {
  const res = await fetch(`${API_BASE}/api/history/${sessionId}`);
  if (!res.ok) throw new Error(`History fetch failed: ${res.status}`);
  const data = await res.json();
  return data.messages;
}
