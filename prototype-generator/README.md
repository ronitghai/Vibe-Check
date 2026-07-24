# AZ-900 Study Companion

An adaptive study app for the Microsoft AZ-900 (Azure Fundamentals) certification. A learner
can't play any games until they finish a 10-question diagnostic; after that, a Game Menu of 7
mini-games unlocks, each one generating fresh AZ-900 content grounded in a specific exam domain.
Every game reports its real score back (win/loss, correct/total) via `postMessage`, which is what
actually moves the progress bar — there's no manual "mark complete" button anywhere. A chat-based
"✨ Generate a game" feature is also available from the Game Menu for anything the 7 templates
don't cover, but it's constrained to AZ-900 material too — see "AI game generator" below.

## Setup

**Backend**

```
cd backend
```

Windows:
```
python -m venv venv
venv\Scripts\activate
copy .env.example .env
```

Mac/Linux:
```
python3 -m venv venv
source venv/bin/activate
cp .env.example .env
```

Then, on either OS, edit `.env` and set `GROQ_API_KEY`, and start the server:

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Runs at http://localhost:8000. Requires `node` on PATH (used by
`backend/app/codegen/validator.py` to syntax-check chat-generated JavaScript before serving it —
falls back to a few common install locations per OS if `node` isn't on PATH, see that file).

**Frontend**

```
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173.

## The learning loop

- `POST /api/az900/assessment/start` / `.../submit` — the diagnostic. Sampled from a hand-authored
  question bank (`backend/app/learning/knowledge_base.py`) — never LLM-generated, since these are
  the highest-stakes questions in the app (they score the learner). Every domain a submitted
  assessment covers writes into `domain_mastery`, an accumulating correct/total per domain that
  never resets, even across retakes.
- `GET /api/az900/dashboard/{session_id}` — per-domain mastery %, the weakest domain, and one
  `overallProgress` number (a plain average of real accuracy across the 3 domains) for the top
  progress bar. `frontend/src/App.tsx` calls this once on mount to decide whether a session lands
  on the diagnostic gate or straight on the Game Menu.
- `POST /api/az900/game/generate` — generates AZ-900-grounded content for one of the 7 template
  games, targeting a chosen (or the current weakest) domain, and launches it exactly like any
  other game in the app.
- `POST /api/az900/practice/result` — called when a game reports its real score via
  `postMessage` (see `games/bundle.py`'s `window.reportGameResult` and `PlayView.tsx`'s message
  listener). Feeds the SAME `domain_mastery` accumulator the diagnostic uses, so practice and
  diagnostic accuracy blend into one number per domain — the progress bar moves because the
  learner is actually answering things correctly, not because they opened a game.

## AI game generator ("✨ Generate a game")

Only reachable from inside the unlocked Game Menu. Runs a Groq tool-calling loop
(`backend/app/orchestrator.py`) that can launch any of the 7 templates or, for anything that
doesn't fit, generate a brand-new simple game from scratch
(`backend/app/codegen/generator.py`). Both paths are constrained to AZ-900 material: the system
prompt is handed the full hand-authored fact base from `knowledge_base.py` and the session's
current weakest domain as a default focus, every tool call must declare which of the 3 AZ-900
domains its content targets, and an off-topic request ("make me a game about dinosaurs") gets
reinterpreted as AZ-900 content in that spirit rather than refused outright. A chat-launched game
gets real score reporting wired up exactly like a Game Menu card.

- The frontend mounts every game in a sandboxed `<iframe sandbox="allow-scripts" srcDoc=...>` —
  no `allow-same-origin`, no network access, isolated from the rest of the page.
- Session id is a UUID stored in `localStorage`; the diagnostic, practice history, and chat
  history all persist server-side in `backend/sessions.db` (SQLite) per session — reloading the
  page returns to wherever that session left off (gate, diagnostic, or Game Menu).

## Design system

`backend/app/games/bundle.py` injects a shared `<style>` block (CSS custom properties for the
palette + `.btn`/`.game-title`/`.game-meta`/`.game-status` utility classes), `window.GameTheme`
(the same palette as JS values), and `window.reportGameResult(correct, total)` (the real-scoring
hook every game calls at its own "game over" moment) into every game bundle, template or
chat-generated, right after a strict CSP meta tag. The 7 templates in
`backend/app/games/library/*.html` are built on these tokens instead of hardcoded colors, and the
codegen system prompt (`backend/app/codegen/generator.py`) instructs the model to do the same.
`frontend/src/index.css` defines the identical palette for the outer app chrome.

## Codegen safety

`backend/app/codegen/validator.py` runs generated HTML through a denylist (no network calls, no
external resources, no `document.cookie`/`localStorage`/`top`/`parent`) and a real JavaScript
syntax check (`node --check`) before it's ever stored or served. On failure the generator retries
once with the concrete error fed back to the model; if that also fails, the chat falls back to
suggesting a template game instead.

## Template game library

Tic-Tac-Toe, Wheel of Fortune, Quiz Flyer, Memory Match, Vocabulary Match, Crossword, Rapid Quiz —
`backend/app/games/library/`. Each is a single self-contained HTML file that reads
`window.__CONFIG__` for its content and calls `window.reportGameResult(correct, total)` at its own
game-over moment.
