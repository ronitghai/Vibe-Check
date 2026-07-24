/**
 * Az900Summary.tsx
 * ------------------
 * Results modal shown once, right after a diagnostic is submitted (see
 * App.tsx's handleAssessmentSubmitted). Floats on top of whatever's behind
 * it (the Game Window, freshly showing the just-updated mastery bars) —
 * closing it just dismisses the modal, it doesn't navigate anywhere.
 *
 * The one action here — "Practice: <weakest domain>" — is a one-click
 * shortcut straight into a Rapid Quiz for the domain the diagnostic just
 * revealed as weakest, so a learner doesn't have to go find it in the Game
 * Menu themselves right after finding out about it. (Rapid Quiz specifically
 * because it's the fastest "test me right now" format — the full Game Menu,
 * with its game-type + domain picker, is still there for anything else.)
 */

import { useState } from "react";
import { generatePracticeContent } from "../api/client";
import type { AssessmentSubmitResponse } from "../api/client";
import type { PlayingGame } from "../types";

const QUICK_PRACTICE_GAME_ID = "rapid_quiz";

interface Props {
  result: AssessmentSubmitResponse;
  sessionId: string;
  onClose: () => void;
  /** `az900GameId`/`az900Domain` tell the caller (App.tsx) what to tag the
   * launched game with, so PlayView knows what to report a real score against. */
  onPlay: (game: PlayingGame, az900GameId: string, az900Domain: string) => void;
}

export default function Az900Summary({ result, sessionId, onClose, onPlay }: Props) {
  const [generating, setGenerating] = useState(false);

  async function handlePractice() {
    setGenerating(true);
    try {
      const res = await generatePracticeContent(sessionId, QUICK_PRACTICE_GAME_ID, result.weakestDomain);
      onPlay({ gameId: res.game_id, gameType: res.game_type as "template" | "generated" }, res.game_id, res.domain);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <>
      {/* Reuses the same dim-backdrop class the chat drawer uses. */}
      <div className="drawer-backdrop open" onClick={onClose} />
      <div className="az900-modal">
        <div className="drawer-header">
          <span>Assessment Results</span>
          <button className="drawer-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="az900-modal-body">
          <div className="az900-score">
            {result.score.correct} / {result.score.total} correct
          </div>
          <div className="az900-weakest">
            Weakest domain: <strong>{result.weakestDomain}</strong>
          </div>

          {result.explanations.length > 0 && (
            <div className="az900-explanations">
              <div className="game-meta">Where you can improve</div>
              {result.explanations.map((e, i) => (
                <div className="az900-explanation" key={i}>
                  <div className="az900-explanation-q">{e.question}</div>
                  <div className="az900-explanation-detail">
                    You answered <em>{e.yourAnswer ?? "nothing"}</em> — correct answer:{" "}
                    <em>{e.correctAnswer}</em>
                  </div>
                  {/* This text is always the hand-authored knowledge_base.py
                      snippet the missed question was based on — never a
                      fresh LLM explanation, see service.submit_assessment. */}
                  <div className="az900-explanation-text">{e.explanation}</div>
                </div>
              ))}
            </div>
          )}

          <button className="btn" onClick={handlePractice} disabled={generating}>
            {generating ? "Generating…" : `Practice: ${result.weakestDomain}`}
          </button>
        </div>
      </div>
    </>
  );
}
