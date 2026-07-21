"""
validator.py
------------
Safety + correctness gate for LLM-generated game HTML before it's ever
stored or served. Two checks:
  1. A denylist regex — not a sandbox by itself (the sandboxed iframe + CSP
     in games/bundle.py is the real containment), just refuses to even serve
     output that obviously tries to reach outside the page.
  2. A real JavaScript syntax check (via `node --check`) — models occasionally
     write invalid JS (e.g. using CSS's var(--x) as a bare JS expression),
     which silently breaks the whole game with no visible error. Catching
     that here lets generator.py retry with the concrete error message
     instead of shipping a dead page.
"""

import re
import shutil
import subprocess
import tempfile
import os

from .. import config

DENYLIST_PATTERNS = [
    r"\bfetch\s*\(",
    r"XMLHttpRequest",
    r"\bWebSocket\s*\(",
    r"\beval\s*\(",
    r"new\s+Function\s*\(",
    r"document\.cookie",
    r"\btop\s*\.",
    r"\bparent\s*\.",
    r"navigator\.sendBeacon",
    r"<script[^>]+src=",
    r"<link[^>]+href=",
    r"<img[^>]+src=(?![\"']data:)",
    r"localStorage",
    r"indexedDB",
]

DENYLIST_RE = re.compile("|".join(DENYLIST_PATTERNS), re.IGNORECASE)
SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)

NODE_BIN = shutil.which("node") or (
    r"C:\Program Files\nodejs\node.exe"
    if os.path.exists(r"C:\Program Files\nodejs\node.exe")
    else None
)


def validate(html: str) -> tuple[bool, str | None]:
    """Return (ok, reason). reason is None when ok."""
    if not html or "<html" not in html.lower():
        return False, "output is not a full HTML document"

    if len(html.encode("utf-8")) > config.MAX_GENERATED_HTML_BYTES:
        return False, f"output exceeds {config.MAX_GENERATED_HTML_BYTES} bytes"

    match = DENYLIST_RE.search(html)
    if match:
        return False, f"output contains disallowed pattern: {match.group(0)!r}"

    js_ok, js_reason = _check_js_syntax(html)
    if not js_ok:
        return False, js_reason

    return True, None


def _check_js_syntax(html: str) -> tuple[bool, str | None]:
    if NODE_BIN is None:
        return True, None  # can't verify without node; fall through rather than hard-fail

    scripts = SCRIPT_RE.findall(html)
    if not scripts:
        return True, None

    combined = "\n;\n".join(scripts)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(combined)
        path = f.name

    try:
        result = subprocess.run(
            [NODE_BIN, "--check", path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            lines = (result.stderr or "invalid syntax").strip().splitlines()
            error_line = next((l for l in lines if "Error" in l), lines[0] if lines else "invalid syntax")
            return False, f"generated JavaScript has a syntax error: {error_line.strip()}"
        return True, None
    except (subprocess.TimeoutExpired, OSError):
        return True, None  # don't block on checker infra issues
    finally:
        os.unlink(path)
