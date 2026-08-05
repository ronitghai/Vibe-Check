/**
 * Az900WeakConcepts.tsx
 * -----------------------
 * "Explain my weak spots right here" — sits below the game menu in
 * Az900GameWindow.tsx. Unlike Az900WeakAreas (domain-level mastery bars)
 * this is TOPIC-level and shows the actual concept text, not just a
 * percentage: for each of the learner's worst-performing topics (attempted
 * at least once, not yet mastered — see backend service.py's
 * get_weak_concepts), it shows the official skill label, every fact
 * written for it, the real source, and how this session has actually done
 * on it so far (e.g. "0/1 correct" or "1/2 correct, streak reset by a
 * miss"). Same content as Az900Study.tsx, just pre-filtered to what
 * actually needs attention instead of all 62 topics.
 *
 * Deliberately re-fetches whenever `refreshKey` changes (passed down from
 * Az900GameWindow, which bumps it after every real score) so a topic drops
 * out of this list the moment it's mastered, and a newly-missed one can
 * appear.
 */

import { useEffect, useState } from "react";
import { fetchWeakConcepts } from "../api/client";
import type { WeakConceptTopic } from "../api/client";

interface Props {
  sessionId: string;
  refreshKey: number;
}

export default function Az900WeakConcepts({ sessionId, refreshKey }: Props) {
  const [topics, setTopics] = useState<WeakConceptTopic[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchWeakConcepts(sessionId)
      .then((res) => setTopics(res.topics))
      .catch(() => setTopics([]))
      .finally(() => setLoading(false));
  }, [sessionId, refreshKey]);

  if (loading) {
    return (
      <div className="az900-weak-concepts">
        <div className="game-meta">Focus on your weak concepts</div>
        <div className="status-text">Loading…</div>
      </div>
    );
  }

  if (topics.length === 0) {
    return (
      <div className="az900-weak-concepts">
        <div className="game-meta">Focus on your weak concepts</div>
        <p className="az900-weak-concepts-empty">
          Nothing struggling right now, either you haven't attempted anything yet, or everything
          you've tried is already on its way to mastered. Play a practice activity or the
          diagnostic to see explanations for anything you miss show up here.
        </p>
      </div>
    );
  }

  return (
    <div className="az900-weak-concepts">
      <div className="game-meta">Focus on your weak concepts</div>
      <p className="az900-weak-concepts-sub">
        Topics you've been quizzed on but haven't mastered yet, worst first, with the actual
        facts, so you can fix the gap without leaving this screen.
      </p>
      <div className="az900-study-topics">
        {topics.map((t) => (
          <div className="az900-study-topic" key={`${t.domain}-${t.topic}`}>
            <div className="az900-weak-concept-header">
              <h3>{t.label}</h3>
              <span className="az900-weak-concept-stat">
                {t.totalCorrect}/{t.totalAttempts} correct
                {t.correctStreak > 0 ? ` · streak ${t.correctStreak}` : ""}
              </span>
            </div>
            <div className="az900-weak-concept-domain">{t.domain}</div>
            <ul>
              {t.concepts.slice(0, 3).map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
            {t.sources.length > 0 && (
              <div className="az900-study-sources">
                Source{t.sources.length > 1 ? "s" : ""}:{" "}
                {t.sources.map((url, i) => (
                  <span key={url}>
                    {i > 0 && ", "}
                    <a href={url} target="_blank" rel="noreferrer">
                      {new URL(url).pathname.split("/").filter(Boolean).pop()}
                    </a>
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
