export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface LibraryItem {
  gameId: string;
  gameType: "template" | "generated";
  title: string;
  description: string;
}

export interface PlayingGame {
  gameId: string;
  gameType: "template" | "generated";
}
