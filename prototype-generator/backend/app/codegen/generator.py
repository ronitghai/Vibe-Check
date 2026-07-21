"""
generator.py
------------
Free-form path: ask the LLM for a single self-contained HTML game bundle,
then run it through validator.validate(). One retry with the failure reason
fed back to the model; if that also fails, give up and let the caller fall
back to suggesting a template game.
"""

import re

from openai import OpenAI

from .. import config
from . import validator

client = OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)

SYSTEM_PROMPT = """You write tiny, self-contained single-player browser games that fit into an \
existing game library, so they must look like they belong there — not like a random page.

Rules — follow ALL of them exactly:
1. Output ONE complete HTML document: <!DOCTYPE html><html>...<head>...</head><body>...</body></html>. Nothing before or after it, no markdown code fences.
2. All CSS goes in a single inline <style> tag in <head>. All JS goes in a single inline <script> tag before </body>.
3. NEVER reference anything external: no external <script src>, <link>, images, fonts, or network calls of any kind (no fetch, XMLHttpRequest, WebSocket). No document.cookie, localStorage, indexedDB, or references to `top`/`parent`. The page must work completely offline and stay inside its own iframe.
4. Use only inline SVG, CSS shapes/gradients, canvas drawing, emoji, and text for visuals — no external images.
5. Keep it to ONE simple core mechanic (click/tap/keyboard), a visible score or win/lose state, and a "Play again" / restart control. Target under 200 lines of code total.
6. Make it genuinely playable: bind real event listeners, update real game state, and render feedback (no dead buttons).
7. DESIGN SYSTEM — a shared dark theme is already injected into <head> before your <style> tag, as CSS custom properties and utility classes. Use them for everything instead of inventing your own palette or hex colors:
   - Colors: var(--bg), var(--surface), var(--surface-2), var(--border), var(--text), var(--text-muted), var(--accent), var(--accent-strong), var(--success), var(--success-bg), var(--danger), var(--danger-bg), var(--warning)
   - Sizing: var(--radius) for corner radius, var(--font) for font-family
   - Utility classes already defined — reuse them, don't redefine: .btn (primary action button), .game-title (h1-style heading), .game-meta (small muted subtitle line), .game-status (status/score line)
   - `body` is already styled (dark background, centered flex layout, padding) — your own <style> only needs to add layout specific to your game (grid sizes, canvas dimensions, card layout), not re-declare background/color/font-family.
   - If you draw on a <canvas>, read the actual colors at runtime with getComputedStyle(document.documentElement).getPropertyValue('--accent') etc. instead of hardcoding hex in fillStyle, so canvas art matches the theme too.
   - IMPORTANT: `var(--x)` is CSS-only syntax. It is valid inside a <style> block or an inline style="..." string, but it is NOT a JavaScript expression — writing `var(--accent)` directly in your <script> tag is a syntax error and will crash the entire game. In JavaScript, either set styles as strings (e.g. el.style.background = "var(--accent)") or read the resolved value via getComputedStyle as described above."""


def generate_game(title: str, spec: str) -> tuple[str | None, str | None]:
    """Return (html, None) on success, or (None, reason) on failure."""
    user_prompt = f'Title: "{title}"\nGame spec: {spec}'
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(2):
        response = client.chat.completions.create(
            model=config.CODEGEN_MODEL,
            messages=messages,
            temperature=0.7,
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
