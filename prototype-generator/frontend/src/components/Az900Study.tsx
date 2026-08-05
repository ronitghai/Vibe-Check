/**
 * Az900Study.tsx
 * ---------------
 * The "review concepts before you're tested" section — plain text, no
 * games, no scoring, no LLM involved. Deliberately outside the gaming
 * loop entirely: this just reads back GET /api/az900/study, which is the
 * exact same facts (knowledge_base.SNIPPETS) and real Microsoft Learn
 * citations (TOPIC_SOURCES) the rest of the app is grounded in — nothing
 * generated fresh for this screen, so there's nothing here to hallucinate.
 *
 * Reachable from two places (see App.tsx): the gate, before a diagnostic
 * even exists — "review before being tested" only makes sense if it's
 * available pre-diagnostic — and the Game Menu, to look something up after
 * seeing a weak area. Same content either way; `backLabel`/`onBack` just
 * point back to wherever the learner came from.
 *
 * One domain visible at a time (tabs) rather than one long scroll — with
 * ~500 concept sentences across 62 topics, a single unbroken page would be
 * unreadable.
 */

import { useEffect, useState } from "react";
import { fetchStudyContent } from "../api/client";
import type { StudyDomain } from "../api/client";

interface Props {
  backLabel: string;
  onBack: () => void;
}

export default function Az900Study({ backLabel, onBack }: Props) {
  const [domains, setDomains] = useState<StudyDomain[]>([]);
  const [activeDomain, setActiveDomain] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchStudyContent()
      .then((res) => {
        setDomains(res.domains);
        setActiveDomain((current) => current ?? res.domains[0]?.domain ?? null);
      })
      .catch(() => setError("Couldn't load study content."))
      .finally(() => setLoading(false));
  }, []);

  const current = domains.find((d) => d.domain === activeDomain);

  return (
    <div className="az900">
      <div className="az900-body">
        <div className="az900-header">
          <button className="back-btn" onClick={onBack}>
            {backLabel}
          </button>
          <h2>Study Concepts</h2>
          <p>Every fact this app is built on, with the real source it came from, read at your own pace.</p>
        </div>

        {loading && <div className="status-text">Loading study content…</div>}
        {error && <div className="status-text error">{error}</div>}

        {!loading && !error && (
          <>
            <div className="az900-study-tabs">
              {domains.map((d) => (
                <button
                  key={d.domain}
                  className={`az900-study-tab ${d.domain === activeDomain ? "active" : ""}`}
                  onClick={() => setActiveDomain(d.domain)}
                >
                  {d.domain}
                </button>
              ))}
            </div>

            {current && (
              <div className="az900-study-topics">
                {current.topics.map((t) => (
                  <div className="az900-study-topic" key={t.topic}>
                    <h3>{t.label}</h3>
                    <ul>
                      {t.concepts.map((c, i) => (
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
            )}
          </>
        )}
      </div>
    </div>
  );
}
