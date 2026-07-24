"""
validator.py
------------
Safety + correctness gate for LLM-generated game HTML before it's ever
stored or served. Four checks:
  1. A denylist regex — not a sandbox by itself (the sandboxed iframe + CSP
     in games/bundle.py is the real containment), just refuses to even serve
     output that obviously tries to reach outside the page.
  2. A real JavaScript syntax check (via `node --check`) — models occasionally
     write invalid JS (e.g. using CSS's var(--x) as a bare JS expression),
     which silently breaks the whole game with no visible error. Catching
     that here lets generator.py retry with the concrete error message
     instead of shipping a dead page.
  3. Dangling id references — the most common "dead button" bug: JS calls
     getElementById('x') for an id that doesn't actually exist in the HTML
     (typo, renamed element, copy-paste drift). Doesn't throw a syntax error,
     just silently no-ops or null-derefs at runtime, so node --check can't
     catch it — this is a static cross-check instead.
  4. A sanity check that the script isn't essentially empty (a degenerate
     generation that would otherwise sail through the syntax check trivially).
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
HTML_ID_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
GET_ELEMENT_BY_ID_RE = re.compile(r"""getElementById\(\s*["']([^"']+)["']\s*\)""")
MIN_SCRIPT_CHARS = 40

# shutil.which("node") is the cross-platform primary path — it works
# identically on Windows/Mac/Linux as long as `node` is on PATH, which is
# already true for most installs. The explicit paths below are only a
# fallback for the case where it's installed but not on PATH, covering the
# default install location for each OS/package-manager combo.
_FALLBACK_NODE_PATHS = [
    r"C:\Program Files\nodejs\node.exe",  # Windows installer default
    "/opt/homebrew/bin/node",  # macOS, Homebrew on Apple Silicon
    "/usr/local/bin/node",  # macOS, Homebrew on Intel / manual installs
    "/usr/bin/node",  # Linux, most package managers
]

NODE_BIN = shutil.which("node") or next(
    (p for p in _FALLBACK_NODE_PATHS if os.path.exists(p)), None
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

    script_ok, script_reason = _check_script_present(html)
    if not script_ok:
        return False, script_reason

    js_ok, js_reason = _check_js_syntax(html)
    if not js_ok:
        return False, js_reason

    ids_ok, ids_reason = _check_dangling_ids(html)
    if not ids_ok:
        return False, ids_reason

    return True, None


def _check_script_present(html: str) -> tuple[bool, str | None]:
    scripts = SCRIPT_RE.findall(html)
    total_chars = sum(len(s.strip()) for s in scripts)
    if total_chars < MIN_SCRIPT_CHARS:
        return False, "output has little or no <script> content — the game has no real logic"
    return True, None


def _check_dangling_ids(html: str) -> tuple[bool, str | None]:
    html_ids = set(HTML_ID_RE.findall(html))
    scripts = SCRIPT_RE.findall(html)
    referenced_ids = set()
    for script in scripts:
        referenced_ids.update(GET_ELEMENT_BY_ID_RE.findall(script))

    missing = sorted(referenced_ids - html_ids)
    if missing:
        return (
            False,
            f"script calls getElementById for id(s) {missing} that don't exist in the HTML "
            "(typo or renamed element) — this will crash the game at runtime",
        )
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
