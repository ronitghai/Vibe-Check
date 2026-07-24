"""
generator.py
------------
Free-form path: ask the LLM for a single self-contained HTML game bundle,
then run it through validator.validate(). Up to two retries with the failure
reason fed back to the model; if all attempts fail, give up and let the
caller fall back to suggesting a template game. Temperature is kept low —
correctness matters more than creative variety here, since the validator
(and the player) has no tolerance for broken output.
"""

import re

from openai import OpenAI

from .. import config
from . import validator

client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)

SYSTEM_PROMPT = """You write tiny, self-contained single-player browser games for an EDUCATIONAL \
game library, so they must look like they belong there (not like a random page) and, where the \
requested topic allows it, leave the player having practiced or recalled something real — a \
fact, a vocabulary word, a formula. Never force a quiz onto a request that's clearly meant to be \
pure arcade fun; a light, natural learning hook beats a bolted-on one.

Rules — follow ALL of them exactly:
1. Output ONE complete HTML document: <!DOCTYPE html><html>...<head>...</head><body>...</body></html>. Nothing before or after it, no markdown code fences.
2. All CSS goes in a single inline <style> tag in <head>. All JS goes in a single inline <script> tag before </body>.
3. NEVER reference anything external: no external <script src>, <link>, images, fonts, or network calls of any kind (no fetch, XMLHttpRequest, WebSocket). No document.cookie, localStorage, indexedDB, or references to `top`/`parent`. The page must work completely offline and stay inside its own iframe.
4. Use only inline SVG, CSS shapes/gradients, canvas drawing, emoji, and text for visuals — no external images.
5. Keep it to ONE simple core mechanic (click/tap/keyboard), a visible score or win/lose state, and a "Play again" / restart control. Target under 200 lines of code total.
6. Make it genuinely playable: bind real event listeners, update real game state, and render feedback (no dead buttons). Every id you reference with getElementById/querySelector in your script MUST exist in your HTML — double check spelling before finishing.
7. DESIGN SYSTEM — a shared dark theme is already injected into <head>, before your <style> tag, as CSS custom properties, utility classes, AND a ready-to-use JS object. Use it for everything instead of inventing your own palette or hex colors:
   - CSS: var(--bg), var(--surface), var(--surface-2), var(--border), var(--text), var(--text-muted), var(--accent), var(--accent-strong), var(--success), var(--success-bg), var(--danger), var(--danger-bg), var(--warning), var(--radius), var(--font) — use these inside your <style> block and in style="..." attributes.
   - JavaScript: `window.GameTheme` is already defined with the SAME colors as plain strings — GameTheme.bg, .surface, .surface2, .border, .text, .textMuted, .accent, .accentStrong, .success, .successBg, .danger, .dangerBg, .warning. This is the ONLY way to get a color in JavaScript (canvas fillStyle, el.style.background = GameTheme.accent, etc.) — never call getComputedStyle yourself, and never write `var(--x)` inside your <script> tag. `var(--x)` is CSS-only syntax; used as a bare JS expression it is a syntax error that crashes the entire game.
   - Utility classes already defined — reuse them, don't redefine: .btn (primary action button), .game-title (h1-style heading), .game-meta (small muted subtitle line), .game-status (status/score line).
   - `body` is already styled (dark background, centered flex layout, padding) — your own <style> only needs to add layout specific to your game (grid sizes, canvas dimensions, card layout), not re-declare background/color/font-family.
8. If your game combines a live loop (canvas animation, a timer) with a pause-for-a-question or pause-for-a-dialog moment, the safe pattern is: keep a single boolean flag (e.g. `paused`) that your loop's update step checks and returns early on; show the question/dialog as a normal DOM element positioned `absolute` over the canvas (parent needs `position: relative`) so it visually blocks input naturally; when the DOM dialog is answered/closed, set the flag back to false. Don't try to pause `requestAnimationFrame` itself — just gate the state-changing logic inside it."""


def generate_game(title: str, spec: str) -> tuple[str | None, str | None]:
    """Return (html, None) on success, or (None, reason) on failure."""
    user_prompt = f'Title: "{title}"\nGame spec: {spec}'
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(3):
        response = client.chat.completions.create(
            model=config.CODEGEN_MODEL,
            messages=messages,
            temperature=0.4,
        )
        raw = response.choices[0].message.content or ""
        html = _extract_html(raw)

        ok, reason = validator.validate(html)
        if ok:
            return html, None

        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {
                "role": "user",
                "content": (
                    f"That output failed validation: {reason}. "
                    "Regenerate the ENTIRE document, fixing that issue, following every rule above."
                ),
            }
        )

    return None, reason


def _extract_html(raw: str) -> str:
    """Strip markdown fences if the model added them despite instructions."""
    fenced = re.search(r"```(?:html)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return raw.strip()
