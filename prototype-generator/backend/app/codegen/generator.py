"""
generator.py
------------
Generates a complete, self-contained educational browser game from a title and
game specification, then validates the result.

The generator prioritizes:

- complete gameplay rather than prototypes
- meaningful AZ-900 learning interactions
- scoring and progression
- immediate feedback and explanations
- a clear completion state
- reliable result reporting to the parent application

If validation fails, the model receives the failure reason and regenerates the
entire document. Up to three total attempts are allowed.
"""

import re

from openai import OpenAI

from .. import config
from . import validator


client = OpenAI(
    api_key=config.GROQ_API_KEY,
    base_url=config.GROQ_BASE_URL,
)


SYSTEM_PROMPT = """
You are a senior educational game developer creating polished, complete,
single-player browser games for an AZ-900 Study Companion.

Your output is loaded directly into an iframe and shown to a real learner.
Never create a mockup, wireframe, placeholder, proof of concept, or minimal
demo. The result must be a complete playable learning activity.

The game must reinforce genuine Microsoft Azure Fundamentals AZ-900 knowledge.

OUTPUT RULES

1. Output exactly one complete HTML document:

   <!DOCTYPE html>
   <html>
     <head>...</head>
     <body>...</body>
   </html>

   Output nothing before or after the HTML.
   Do not use Markdown code fences.

2. Put all CSS inside one inline <style> tag in <head>.

3. Put all JavaScript inside one inline <script> tag immediately before
   </body>.

4. Never load external resources.

   Do not use:

   - external scripts
   - external stylesheets
   - images
   - fonts
   - fetch
   - XMLHttpRequest
   - WebSocket
   - localStorage
   - sessionStorage
   - indexedDB
   - document.cookie

5. The page must work completely offline inside its iframe.

6. Use only:

   - HTML
   - CSS
   - vanilla JavaScript
   - inline SVG
   - CSS shapes and gradients
   - canvas
   - emoji
   - text

DESIGN SYSTEM

A shared dark design system is injected before your <style> tag.

Use these CSS variables:

- var(--bg)
- var(--surface)
- var(--surface-2)
- var(--border)
- var(--text)
- var(--text-muted)
- var(--accent)
- var(--accent-strong)
- var(--success)
- var(--success-bg)
- var(--danger)
- var(--danger-bg)
- var(--warning)
- var(--radius)
- var(--font)

Use the existing utility classes when useful:

- .btn
- .game-title
- .game-meta
- .game-status

The body is already styled with the dark background, font, padding, and base
text color.

Do not invent unrelated color palettes or hard-code arbitrary hex colors.

For JavaScript colors, use:

- GameTheme.bg
- GameTheme.surface
- GameTheme.surface2
- GameTheme.border
- GameTheme.text
- GameTheme.textMuted
- GameTheme.accent
- GameTheme.accentStrong
- GameTheme.success
- GameTheme.successBg
- GameTheme.danger
- GameTheme.dangerBg
- GameTheme.warning

Do not use CSS var(...) expressions inside JavaScript.

QUALITY REQUIREMENTS

Every generated game must include all of the following:

1. A clear title and short instructions.

2. A complete game state with:

   - score
   - progress
   - current question, challenge, or level
   - completed items
   - final results

3. At least 8 meaningful learning interactions.

   For quiz-board or category games, use at least 12 questions unless the
   supplied specification explicitly requires more.

4. Immediate feedback after every answer or decision.

5. A short educational explanation after every answer.

6. A visible progress indicator, such as:

   - questions completed
   - board tiles completed
   - level number
   - progress bar
   - correct answers out of total

7. A final completion screen containing:

   - final score
   - correct answers
   - total questions
   - percentage
   - a restart button

8. Real event listeners and working controls.

9. No dead buttons.

10. No placeholder content such as:

   - "Question 1"
   - "Option A"
   - "Insert answer here"
   - "Coming soon"
   - lorem ipsum

11. No single-question games.

12. No purely decorative interfaces.

13. No free-text grading unless the game normalizes:

   - capitalization
   - whitespace
   - punctuation
   - accepted answer variants

   Prefer multiple-choice answers when reliable automatic grading is needed.

14. Already-completed questions, tiles, or challenges must become disabled or
   visibly completed.

15. The learner must always understand:

   - what to do
   - whether the answer was correct
   - why the answer was correct or incorrect
   - what remains
   - when the game is complete

AZ-900 CONTENT REQUIREMENTS

All learning content must be relevant to the requested AZ-900 topic or domain.

Use accurate concepts such as:

- cloud computing
- public, private, and hybrid cloud
- shared responsibility
- consumption-based pricing
- CapEx and OpEx
- scalability
- elasticity
- high availability
- reliability
- predictability
- security
- governance
- manageability
- IaaS
- PaaS
- SaaS
- Azure regions
- availability zones
- resource groups
- subscriptions
- management groups
- Azure Policy
- role-based access control
- Azure Monitor
- Azure Service Health
- Microsoft Defender for Cloud
- Azure Cost Management

Do not invent Azure products, definitions, or exam facts.

RESULT REPORTING

When the game is completed, send the learner's result to the parent
application exactly once:

window.parent.postMessage(
  {
    source: "game-engine",
    type: "game-result",
    correct: correctCount,
    total: totalCount
  },
  "*"
);

The values must be numbers.

Do not send the result before the activity is complete.

RESTART REQUIREMENTS

The restart button must:

- reset the score
- reset progress
- reset all completed questions or tiles
- reset feedback
- allow the whole activity to be played again
- allow a new result to be reported after the new run is completed

JEOPARDY-STYLE GAME REQUIREMENTS

When the request asks for a Jeopardy-style game, the game must include:

- a visible category board
- at least 4 categories
- at least 4 questions per category
- values of 100, 200, 300, and 400
- at least 16 total questions
- one selectable tile per question
- four multiple-choice answers per question
- immediate correct or incorrect feedback
- a short explanation after every answer
- a running dollar score
- answered tiles disabled and visibly completed
- a clear board-completion condition
- a final score screen
- correct and total result reporting

Do not reduce Jeopardy to four buttons or a single question per category.

SCENARIO GAME REQUIREMENTS

When the request asks for a scenario or decision game:

- include at least 8 realistic Azure decisions
- provide 3 or 4 choices per scenario
- explain the consequence of each selected answer
- track correct decisions and progress
- include a final performance summary

ARCADE GAME REQUIREMENTS

When the request uses an arcade mechanic:

- the educational questions must be part of the main progression
- use a reliable pause state during questions
- show questions as DOM overlays
- do not stop requestAnimationFrame permanently
- gate state updates with a boolean such as paused
- resume play only after the learner answers

TECHNICAL REQUIREMENTS

- Keep the implementation understandable and maintainable.
- The game may exceed 200 lines when necessary.
- Prefer completeness and reliability over extreme brevity.
- Ensure every queried element exists.
- Ensure every function referenced by an event listener exists.
- Avoid duplicate element IDs.
- Avoid syntax errors.
- Avoid unfinished branches.
- Do not leave console errors.
""".strip()


def _build_user_prompt(title: str, spec: str) -> str:
    """
    Build a detailed generation request while preserving the game specification
    supplied by the orchestrator.
    """
    return f"""
Create the complete educational browser game described below.

TITLE
{title}

GAME SPECIFICATION
{spec}

FINAL QUALITY CHECK BEFORE RESPONDING

Confirm internally that the generated HTML includes:

- complete gameplay
- at least 8 meaningful interactions
- accurate AZ-900 content
- visible score
- visible progress
- immediate answer feedback
- educational explanations
- a completion state
- a restart control
- result reporting through window.parent.postMessage
- no placeholders
- no dead controls

Return only the complete HTML document.
""".strip()


def generate_game(
    title: str,
    spec: str,
) -> tuple[str | None, str | None]:
    """
    Return (html, None) when generation and validation succeed.

    Return (None, reason) when all generation attempts fail.
    """
    user_prompt = _build_user_prompt(title, spec)

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    reason = "Unknown validation failure."

    for attempt in range(3):
        response = client.chat.completions.create(
            model=config.CODEGEN_MODEL,
            messages=messages,
            temperature=0.25,
        )

        raw = response.choices[0].message.content or ""
        html = _extract_html(raw)

        ok, reason = validator.validate(html)

        if ok:
            return html, None

        messages.append(
            {
                "role": "assistant",
                "content": raw,
            }
        )

        messages.append(
            {
                "role": "user",
                "content": (
                    "The generated game failed validation.\n\n"
                    f"VALIDATION FAILURE:\n{reason}\n\n"
                    "Regenerate the entire HTML document from scratch.\n"
                    "Do not provide a patch or partial correction.\n"
                    "Preserve the requested game mechanic, but fix the failure "
                    "and ensure the result is a complete, polished, playable "
                    "AZ-900 learning activity that follows every requirement in "
                    "the system prompt."
                ),
            }
        )

    return None, reason


def _extract_html(raw: str) -> str:
    """
    Extract the HTML document when the model adds Markdown fences despite the
    output instructions.
    """
    fenced = re.search(
        r"```(?:html)?\s*(.*?)```",
        raw,
        re.DOTALL | re.IGNORECASE,
    )

    if fenced:
        return fenced.group(1).strip()

    doctype_index = raw.lower().find("<!doctype html>")

    if doctype_index >= 0:
        return raw[doctype_index:].strip()

    html_index = raw.lower().find("<html")

    if html_index >= 0:
        return raw[html_index:].strip()

    return raw.strip()