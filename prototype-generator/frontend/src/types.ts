/** Shared UI-facing shapes used across multiple components. The API response
 * shapes these are built from live in api/client.ts. */

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

export interface DomainMastery {
  domain: string;
  correct: number;
  total: number;
  masteryPct: number;
  practiceCount: number;
}
