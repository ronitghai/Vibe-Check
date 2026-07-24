"""
bundle.py
---------
Assembles the final HTML string sent to the browser for *any* game (template
or generated). Every bundle gets, in this order:
  1. A strict CSP meta tag (defense-in-depth against generated code).
  2. The shared design system — CSS variables + a few utility classes that
     every game (template or LLM-generated) is expected to build on, so the
     library doesn't look like unrelated pages glued together.
  3. window.GameTheme — the same palette, pre-resolved to real color strings
     in JS. Games that need a color in JS (canvas fillStyle, etc.) read
     GameTheme.accent instead of hand-writing getComputedStyle(...) calls —
     that hand-written boilerplate is exactly where a generated game once
     wrote `var(--accent)` as a bare JS expression (CSS-only syntax) and
     silently crashed the whole script. Removing the need to write it at all
     removes that failure mode.
  4. window.reportGameResult(correct, total) — a one-line helper every game
     can call at its own "game over" moment to report a real score to
     whatever's hosting it (postMessage, since the game runs in a sandboxed
     cross-origin iframe with no other way to talk to the parent page). This
     is what the AZ-900 loop uses to move the progress bar off of real
     performance instead of just "did they open the game" — see
     PlayView.tsx's message listener and learning/service.py's
     record_practice_result. Safe to call from ANY game (template or
     LLM-generated) whether or not anything is listening on the other end.
  5. (for templates) a window.__CONFIG__ script tag carrying the LLM-authored
     content.
"""

import json

CSP = (
    "default-src 'none'; "
    "script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; "
    "img-src data:; "
    "font-src data:; "
    "connect-src 'none'"
)

DESIGN_SYSTEM_CSS = """
<style>
  :root {
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-2: #334155;
    --border: #334155;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #38bdf8;
    --accent-strong: #7dd3fc;
    --success: #22c55e;
    --success-bg: #14532d;
    --danger: #f87171;
    --danger-bg: #7f1d1d;
    --warning: #facc15;
    --radius: 10px;
    --font: system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; padding: 16px;
    display: flex; align-items: center; justify-content: center;
    background: var(--bg); color: var(--text); font-family: var(--font);
  }
  .btn {
    padding: 8px 20px; border-radius: var(--radius); border: none;
    background: var(--accent); color: var(--bg); font-weight: 700;
    cursor: pointer; font-size: 14px;
  }
  .btn:hover { background: var(--accent-strong); }
  .btn:disabled { opacity: 0.5; cursor: default; }
  .game-title { margin: 0 0 4px; font-size: 20px; font-weight: 700; color: var(--text); }
  .game-meta { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
  .game-status { min-height: 20px; font-size: 14px; color: var(--text-muted); margin: 10px 0; }
</style>
""".strip()

DESIGN_SYSTEM_JS = """
<script>
  window.GameTheme = (function () {
    var s = getComputedStyle(document.documentElement);
    function v(name) { return s.getPropertyValue(name).trim(); }
    return {
      bg: v("--bg"),
      surface: v("--surface"),
      surface2: v("--surface-2"),
      border: v("--border"),
      text: v("--text"),
      textMuted: v("--text-muted"),
      accent: v("--accent"),
      accentStrong: v("--accent-strong"),
      success: v("--success"),
      successBg: v("--success-bg"),
      danger: v("--danger"),
      dangerBg: v("--danger-bg"),
      warning: v("--warning")
    };
  })();

  // Call this once, at your game's own "game over" / "round complete"
  // moment, with your real score: reportGameResult(correctCount, totalCount).
  // For a game with no natural "correct/total" (e.g. a win/lose match),
  // report the outcome as 1/1 for a win and 0/1 for a loss — see
  // tic_tac_toe.html for an example. Safe to call even if nothing is
  // listening; wrapped so it can never throw and break your game.
  window.reportGameResult = function (correct, total) {
    try {
      parent.postMessage({ source: "game-engine", type: "game-result", correct: correct, total: total }, "*");
    } catch (e) {
      // no-op — a game should never crash because reporting failed
    }
  };
</script>
""".strip()


def inject(html: str, config: dict | None = None) -> str:
    head_extra = f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
    head_extra += DESIGN_SYSTEM_CSS
    head_extra += DESIGN_SYSTEM_JS
    if config is not None:
        head_extra += f"<script>window.__CONFIG__={json.dumps(config)};</script>"

    if "<head>" in html:
        return html.replace("<head>", "<head>" + head_extra, 1)
    return head_extra + html
