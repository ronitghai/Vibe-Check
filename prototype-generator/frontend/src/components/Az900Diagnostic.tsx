/**
 * Az900Diagnostic.tsx
 * ---------------------
 * The full-screen diagnostic quiz. Shown by App.tsx whenever a session has
 * never completed a diagnostic before (see App.tsx's gating check against
 * GET /api/az900/dashboard/{session}) — entering "AZ-900 Prep" goes STRAIGHT
 * here, no dashboard/landing screen first, per the "you must start out with
 * the diagnostic" requirement. Also reachable any time afterward via the
 * "Retake Diagnostic" button in Az900WeakAreas.
 *
 * Layout note: this is a full-height flex column with exactly ONE scrolling
 * region (`.az900-body`, see App.css) — the progress bar strip at the top
 * stays fixed while the question list scrolls underneath it. An earlier
 * version nested a scrollable `.az900` inside a wider flex row with an
 * unrelated max-width, which produced a stray/duplicate scrollbar and a lot
 * of dead space on wide screens — that's why this structure looks the way
 * it does; don't reintroduce a max-width on the outer container.
 */

import { useEffect, useState } from "react";
import { startAssessment, submitAssessment } from "../api/client";
import type { AssessmentQuestion, AssessmentSubmitResponse } from "../api/client";
import Az900ProgressBar from "./Az900ProgressBar";

interface Props {
  sessionId: string;
  onSubmitted: (result: AssessmentSubmitResponse) => void;
  onBack: () => void;
}

export default function Az900Diagnostic({ sessionId, onSubmitted, onBack }: Props) {
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  // answers: {question_id -> the choice index the learner clicked}. A plain
  // object keyed by question_id (not an array) so we can cheaply check "is
  // question N answered yet" with `answers[id] !== undefined`.
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // Fetch a fresh 10-question assessment every time this component mounts —
  // including when the learner clicks "Retake Diagnostic", since that
  // unmounts/remounts this component with a new key in App.tsx.
  useEffect(() => {
    setLoading(true);
    startAssessment(sessionId)
      .then((res) => {
        setAssessmentId(res.assessment_id);
        setQuestions(res.questions);
        setAnswers({});
      })
      .finally(() => setLoading(false));
  }, [sessionId]);

  const answeredCount = questions.filter((q) => answers[q.question_id] !== undefined).length;
  const allAnswered = questions.length > 0 && answeredCount === questions.length;
  // Drives the top progress bar — literal "how far through the diagnostic
  // are you", independent of the Game Window's mastery/engagement formula.
  const progressPct = questions.length > 0 ? (answeredCount / questions.length) * 100 : 0;

  async function handleSubmit() {
    if (!assessmentId || !allAnswered) return;
    setSubmitting(true);
    try {
      const payload = questions.map((q) => ({
        question_id: q.question_id,
        choice_index: answers[q.question_id],
      }));
      const result = await submitAssessment(sessionId, assessmentId, payload);
      onSubmitted(result);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="az900">
      <Az900ProgressBar
        value={progressPct}
        label="Diagnostic — complete it to unlock your Game Menu"
      />

      <div className="az900-body">
        <div className="az900-header">
          <button className="back-btn" onClick={onBack}>
            ← Back
          </button>
          <h2>Diagnostic Assessment</h2>
          <p>{questions.length || 10} quick questions across all 3 AZ-900 domains.</p>
        </div>

        {loading ? (
          <div className="status-text">Preparing your assessment…</div>
        ) : (
          <>
            <div className="az900-questions">
              {questions.map((q, i) => (
                <div className="az900-question" key={q.question_id}>
                  <div className="az900-question-meta">
                    Question {i + 1} of {questions.length} · {q.domain}
                  </div>
                  <div className="az900-question-text">{q.question}</div>
                  <div className="az900-choices">
                    {q.choices.map((choice, idx) => (
                      <button
                        key={idx}
                        className={`az900-choice ${answers[q.question_id] === idx ? "selected" : ""}`}
                        onClick={() => setAnswers((a) => ({ ...a, [q.question_id]: idx }))}
                      >
                        {choice}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <button className="btn" onClick={handleSubmit} disabled={!allAnswered || submitting}>
              {submitting ? "Grading…" : "Submit Assessment"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
