/**
 * App.tsx
 * -------
 * Top-level view router + state owner for the whole frontend. There's no
 * routing library here on purpose (this is a small app) — `view` is just a
 * string union and renderMain() below is a big if-chain picking which
 * screen to show. If you're trying to trace "how did I get to screen X",
 * start by searching this file for `setView(`.
 *
 * This app is a single-purpose AZ-900 study companion — there is no general
 * game library and no way to reach a game without going through the
 * diagnostic first. FOUR SCREENS:
 *   "az900-gate"          — the landing prompt, first thing ANY session
 *                            sees (Az900Gate.tsx) — nothing playable here,
 *                            just "Start Diagnostic".
 *   "az900-diagnostic"    — the AZ-900 10-question diagnostic (Az900Diagnostic.tsx)
 *   "az900-game-window"   — AZ-900 progress bar + weak areas + game menu,
 *                            unlocked only once a diagnostic exists
 *                            (Az900GameWindow.tsx). The "✨ Generate a game"
 *                            chat drawer also only mounts on this screen.
 *   "play"                — one game, fullscreen (PlayView.tsx) — used by
 *                            every launch path (Game Menu cards, chat).
 *
 * THE GATE (see the mount-time effect below): on first render, this checks
 * whether the session has ever completed a diagnostic (any domain with
 * total > 0 in GET /api/az900/dashboard) and picks the starting view from
 * that — "az900-gate" if not, straight to "az900-game-window" if so. There
 * used to be a header button that ran this same check on click; it's gone
 * now because there's nowhere else in the app to navigate away to.
 * `hasDiagnostic` is kept in state (not re-derived) so Az900Diagnostic's
 * "← Back" button knows whether to return to the gate (first attempt) or
 * the Game Window (a retake) — see its onBack below.
 *
 * REAL SCORING: a game launched from either the Game Menu OR the chat
 * generator is tagged with (az900GameId, az900Domain). PlayView listens for
 * that specific game's own postMessage score report and calls
 * handleGameResult below, which feeds the real correct/total into the
 * backend (reportPracticeResult) — see PlayView.tsx and games/bundle.py's
 * reportGameResult for the other end of this pipe.
 */

import { useEffect, useState } from "react";
import PlayView from "./components/PlayView";
import ChatDrawer from "./components/ChatDrawer";
import Az900Gate from "./components/Az900Gate";
import Az900GameWindow from "./components/Az900GameWindow";
import Az900Diagnostic from "./components/Az900Diagnostic";
import Az900Summary from "./components/Az900Summary";
import { fetchDashboard, reportPracticeResult } from "./api/client";
import { getSessionId } from "./session";
import type { PlayingGame } from "./types";
import type { AssessmentSubmitResponse, GameResult } from "./api/client";
import "./App.css";

type View = "az900-gate" | "az900-diagnostic" | "az900-game-window" | "play";

export default function App() {
  const [sessionId] = useState(getSessionId);
  // Starts null ("still checking") rather than defaulting to the gate, so a
  // returning learner doesn't flash the gate screen for a frame before the
  // dashboard check redirects them to the Game Window.
  const [view, setView] = useState<View | null>(null);
  // Whether THIS session has ever completed a diagnostic — set by the
  // mount-time check below and flipped true the moment one is submitted.
  // Drives Az900Diagnostic's "← Back" destination (see renderMain).
  const [hasDiagnostic, setHasDiagnostic] = useState(false);

  // --- "play" screen state ---
  const [playingGame, setPlayingGame] = useState<PlayingGame | null>(null);
  // Set only when a game was launched from the AZ-900 flow (Game Menu or
  // chat) — this is what makes PlayView listen for a real score report at
  // all (see PlayView's own doc comment: az900GameId, az900Domain, AND
  // onGameResult must all be present).
  const [playAz900GameId, setPlayAz900GameId] = useState<string | null>(null);
  const [playAz900Domain, setPlayAz900Domain] = useState<string | null>(null);

  // --- chat drawer state ---
  const [chatOpen, setChatOpen] = useState(false);

  // --- AZ-900 state ---
  // Bumping this forces Az900GameWindow to re-fetch progress — done after a
  // real game result comes in and after a diagnostic submit, so the
  // progress bar/sidebar never show stale numbers.
  const [az900Version, setAz900Version] = useState(0);
  // Non-null right after submitting a diagnostic -> shows the results modal
  // on top of whatever screen is behind it. Set back to null to dismiss.
  const [az900Summary, setAz900Summary] = useState<AssessmentSubmitResponse | null>(null);

  // The gate check described in this file's top comment — runs once, on
  // mount, for every session.
  useEffect(() => {
    fetchDashboard(sessionId)
      .then((dash) => {
        const completed = dash.domains.some((d) => d.total > 0);
        setHasDiagnostic(completed);
        setView(completed ? "az900-game-window" : "az900-gate");
      })
      .catch(() => setView("az900-gate")); // backend unreachable — fail open to the gate, not a crash
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Launch a game and remember how to get back afterward. `az900GameId`/
   * `az900Domain` are both optional — omit them for a launch that isn't
   * scored (there currently isn't one, but PlayView treats them as opt-in). */
  function handlePlay(game: PlayingGame, az900GameId?: string, az900Domain?: string) {
    setPlayingGame(game);
    setPlayAz900GameId(az900GameId ?? null);
    setPlayAz900Domain(az900Domain ?? null);
    setView("play");
  }

  /** Wired to ChatDrawer's onGameLaunched. Unlike the old general-library
   * chat flow, the backend now always tags a chat-launched game with an
   * AZ-900 domain (see orchestrator.py's tool schema), so this can reuse
   * the exact same scored-launch path as a Game Menu card. */
  function handleGameLaunchedFromChat(game: PlayingGame, domain: string) {
    setChatOpen(false);
    handlePlay(game, game.gameId, domain);
  }

  function handleAssessmentSubmitted(result: AssessmentSubmitResponse) {
    setAz900Summary(result);
    setHasDiagnostic(true);
    setAz900Version((v) => v + 1); // so the Game Window behind the modal shows fresh mastery
    setView("az900-game-window");
  }

  /** Wired to PlayView's onGameResult — a game's REAL score just arrived via
   * postMessage. Feeds it into domain_mastery on the backend, then bumps
   * az900Version so the Game Window's progress bar/sidebar refresh next
   * time it's shown (it isn't visible right now, PlayView is on screen). */
  async function handleGameResult(result: GameResult) {
    await reportPracticeResult(sessionId, result);
    setAz900Version((v) => v + 1);
  }

  function renderMain() {
    if (view === "az900-game-window") {
      return (
        <Az900GameWindow
          sessionId={sessionId}
          refreshKey={az900Version}
          onRetakeDiagnostic={() => setView("az900-diagnostic")}
          onPlay={(game, gameId, domain) => handlePlay(game, gameId, domain)}
        />
      );
    }
    if (view === "az900-diagnostic") {
      return (
        <Az900Diagnostic
          sessionId={sessionId}
          onSubmitted={handleAssessmentSubmitted}
          onBack={() => setView(hasDiagnostic ? "az900-game-window" : "az900-gate")}
        />
      );
    }
    if (view === "play" && playingGame) {
      return (
        <PlayView
          sessionId={sessionId}
          game={playingGame}
          onBack={() => setView("az900-game-window")}
          az900GameId={playAz900GameId ?? undefined}
          az900Domain={playAz900Domain ?? undefined}
          onGameResult={handleGameResult}
        />
      );
    }
    if (view === "az900-gate") {
      return <Az900Gate onStart={() => setView("az900-diagnostic")} />;
    }
    return null; // still resolving the mount-time gate check — render nothing rather than flash a screen
  }

  return (
    <div className="app">
      <main className="app-main">{renderMain()}</main>

      {/* The AI generator is only reachable from inside the unlocked Game
          Menu — it's a shortcut to a scored practice game, not a separate
          general-purpose feature, so it has no reason to exist anywhere
          else in the flow. */}
      {view === "az900-game-window" && (
        <>
          <button className="fab" onClick={() => setChatOpen(true)}>
            ✨ Generate a game
          </button>
          <ChatDrawer
            sessionId={sessionId}
            open={chatOpen}
            onClose={() => setChatOpen(false)}
            onGameLaunched={handleGameLaunchedFromChat}
          />
        </>
      )}

      {az900Summary && (
        <Az900Summary
          result={az900Summary}
          sessionId={sessionId}
          onClose={() => setAz900Summary(null)}
          onPlay={(game, gameId, domain) => {
            setAz900Summary(null);
            handlePlay(game, gameId, domain);
          }}
        />
      )}
    </div>
  );
}
