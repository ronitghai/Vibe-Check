# Handoff — AZ-900 Study Companion

Written 2026-08-06 for whoever picks this project up next. This is a
project-history/orientation doc, not user-facing documentation — see
`README.md` for setup/run instructions.

## What this app is

A Groq-LLM-powered adaptive exam-prep tool for Microsoft's AZ-900 (Azure
Fundamentals) certification. It is **not** a general game-generator anymore —
an earlier prototype let you chat with an AI to generate any topic's trivia
game; that was deliberately narrowed to AZ-900-only content, grounded in the
real exam outline, because generic content doesn't actually help someone pass
a specific certification.

### The learner-facing flow

1. **Gate** (`Az900Gate.tsx`) — first thing a new session sees. No menu, no
   games reachable — just "take the diagnostic" or nothing.
2. **Diagnostic** (`Az900Diagnostic.tsx`) — a quiz sampled to maximize
   coverage across the official 57-bullet AZ-900 skills outline (not random;
   see `service.py`'s coverage-maximizing sampler).
3. **Game Menu** (`Az900GameWindow.tsx` + `Az900GameMenu.tsx`) — unlocked
   only after a diagnostic exists. Shows:
   - A recommended-next-activity banner (`Az900RecommendationCard.tsx`)
   - 5 practice games (rapid_quiz, scenario_challenge, matching_game,
     crossword, jeopardy) as HTML templates, rendered in a sandboxed iframe
   - A domain-level progress bar (`Az900ProgressBar.tsx`) and weak-area
     summary (`Az900WeakAreas.tsx`)
   - A **Weak Concepts** panel (`Az900WeakConcepts.tsx`) that explains,
     inline, exactly which topics the learner is struggling with and why —
     with real cited source content, not just a percentage
   - A **Study** section (`Az900Study.tsx`) with sourced reference content
     for all 62 topics
   - A **Reset Progress** button
   - A chat drawer (`ChatDrawer.tsx`/`ChatWindow.tsx`) that can still
     generate a custom game on request, but it's constrained server-side to
     stay on-topic and target the learner's weakest domain — see
     `orchestrator.py`'s system prompt and `tools.py`.

## Architecture

- **Backend**: FastAPI + SQLite (`backend/app/`). Two SQLite access points
  share the same `_conn()` pattern: `session_store.py` (chat sessions) and
  `learning/store.py` (diagnostic results, practice logs, topic mastery
  streaks). Groq is called via the OpenAI-compatible SDK in JSON mode for
  structured content generation.
- **Frontend**: React + TypeScript + Vite (`frontend/src/`). No router —
  `App.tsx` holds a string-union `View` type and a big if-chain
  `renderMain()`. Games render inside a sandboxed
  `<iframe sandbox="allow-scripts" srcDoc={html}>`; a `postMessage` bridge
  (`window.reportGameResult`, injected by `games/bundle.py`) is how a game
  reports its real score back up to the app — this is what actually moves
  the mastery bars, not just opening a game.

## The two things that make the content trustworthy

1. **Grounding pipeline**: the official Microsoft AZ-900 Skills Measured
   outline (57 bullets across 3 domains, real exam weights 25-30% /
   35-40% / 30-35%) plus real Microsoft Learn unit pages, fetched and cited
   per-concept. The audit trail lives in
   `backend/app/learning/content_bank/*.json`; it's merged into
   `knowledge_base.py`'s `SNIPPETS`/`QUESTION_BANK`/`TOPIC_LABELS`/
   `TOPIC_SOURCES`. If you need to add or fix a topic, that's where to look
   — `TOPIC_SOURCES` is what makes the citation links in the Study/Weak
   Concepts panels real, not made up.
2. **Streak-based mastery**: a topic only counts as "mastered" after 2
   correct answers *in a row* (`MASTERY_STREAK_THRESHOLD` in
   `learning/service.py`); any miss resets the streak to 0. This was a
   deliberate choice over a simple "seen it once, correct" model, since
   one lucky guess shouldn't count as mastery. `DOMAIN_WEIGHTS` (the real
   exam weight midpoints) drives both diagnostic question distribution and
   the weighted overall progress score — so the progress bar reflects the
   actual exam's emphasis, not an even split across domains.

## Known non-obvious decisions worth knowing before you change things

- `registry.py`'s `merge_config()` does a **key-by-key falsy-skip merge**,
  not a shallow merge — an empty/None value from the LLM is treated as "LLM
  didn't actually supply this" and the curated default shows through
  instead. This is what makes a partial/failed LLM generation degrade
  gracefully instead of rendering a half-empty game. Don't "simplify" this
  to `{**defaults, **config}` — that would let a failed generation blank out
  a game.
- `mastery_weight` per game (in `registry.py`) is not decorative — quiz-style
  games (rapid_quiz/scenario_challenge/jeopardy) are full-weight signals of
  real knowledge; matching_game (0.6) and crossword (0.35) are weaker
  signals and intentionally move the mastery needle less.
- The chat-based custom-game generator still exists (`orchestrator.py`,
  `tools.py`, `codegen/generator.py` + `codegen/validator.py`'s denylist +
  `node --check` safety net) but is now hard-constrained to AZ-900 topics
  and wired to real scoring exactly like the template games — see
  `tools.dispatch`'s `domain` field threading through to
  `PlayView.tsx`'s `postMessage` listener.
- Cross-platform: `codegen/validator.py`'s Node.js binary lookup tries
  `shutil.which("node")` first (works on any OS if `node` is on PATH), then
  falls back through both Windows and Mac/Linux common install paths.

## Comment coverage

Every backend module and frontend component has a file-level docblock
explaining its purpose and callers; inline comments are deliberately sparse
and reserved for non-obvious behavior (the project's established
convention — no comments that just restate the code). The game template
HTML files under `backend/app/games/library/` are lightly commented,
enough to explain the CONFIG shape and any state-machine-like logic
(e.g. jeopardy.html's open/submit/close-question flow).

## Verified working state as of this handoff

- Backend imports cleanly (`python -c "import app.main"`).
- Frontend typechecks cleanly (`npx tsc -b`).
- Full learner loop (gate → diagnostic → game menu → play a game → real
  score moves mastery bar → weak concepts/study sections reflect it →
  reset progress works) was verified end-to-end in-browser during
  development.

No open bugs or partially-finished work are known at this point.
