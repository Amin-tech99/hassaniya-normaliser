"""Local web UI server for Hassaniya text normalization."""

from __future__ import annotations

import argparse
import difflib
import json
import logging
import re
import webbrowser
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Tuple

from .. import normalize_text

_LOG = logging.getLogger(__name__)
_TOKEN_PATTERN = re.compile(r"\b\w+\b|[^\w\s]|\s+", re.UNICODE)

_PAGE = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>مطبع النص الحساني</title>
  <style>
    :root {
      --bg-1: #f6f8f7;
      --bg-2: #e6efe9;
      --surface: #ffffff;
      --text: #15221d;
      --muted: #4c5f57;
      --accent: #1d765a;
      --accent-soft: #d8ede5;
      --mark: #ffe28b;
      --border: #d3e0d9;
      --error: #8f1f1f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Noto Naskh Arabic", "Amiri", "Scheherazade New", "Segoe UI", Tahoma, sans-serif;
      background: linear-gradient(160deg, var(--bg-1) 0%, var(--bg-2) 100%);
      color: var(--text);
      min-height: 100vh;
      padding: 20px;
    }
    .wrap {
      max-width: 1100px;
      margin: 0 auto;
      display: grid;
      gap: 16px;
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(17, 54, 39, 0.08);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 1.7rem;
    }
    p.meta {
      margin: 0;
      color: var(--muted);
      font-size: 0.96rem;
    }
    .label {
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 0.92rem;
    }
    textarea {
      width: 100%;
      min-height: 180px;
      border-radius: 10px;
      border: 1px solid var(--border);
      padding: 12px;
      font-size: 1.06rem;
      line-height: 1.8;
      resize: vertical;
      direction: rtl;
      background: #fcfdfc;
    }
    .row {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    button {
      border: none;
      background: var(--accent);
      color: white;
      border-radius: 999px;
      padding: 10px 18px;
      font-size: 0.95rem;
      cursor: pointer;
      transition: transform 120ms ease, opacity 120ms ease;
      font-family: inherit;
    }
    button:hover { transform: translateY(-1px); }
    button:disabled { opacity: 0.6; cursor: wait; }
    .stat {
      background: var(--accent-soft);
      color: #184b3a;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.88rem;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .panel {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      min-height: 130px;
      background: #fcfdfc;
      white-space: pre-wrap;
      direction: rtl;
      line-height: 1.9;
      font-size: 1.06rem;
    }
    mark.change {
      background: var(--mark);
      padding: 0 2px;
      border-radius: 3px;
      cursor: pointer;
      outline: none;
      transition: box-shadow 120ms ease;
    }
    mark.change:focus {
      box-shadow: 0 0 0 2px rgba(29, 118, 90, 0.35);
    }
    mark.change.selected {
      box-shadow: 0 0 0 2px rgba(29, 118, 90, 0.35);
    }
    .word-ghost {
      position: fixed;
      left: 0;
      top: 0;
      transform: translate(-50%, -100%);
      z-index: 40;
      opacity: 0;
      pointer-events: none;
      background: rgba(255, 255, 255, 0.28);
      border: 1px solid rgba(255, 255, 255, 0.52);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      color: #1f7a5d;
      font-weight: 700;
      padding: 8px 12px;
      border-radius: 999px;
      box-shadow: 0 10px 24px rgba(17, 54, 39, 0.16);
      transition: opacity 140ms ease;
      max-width: min(90vw, 360px);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 1rem;
    }
    .word-ghost.below {
      transform: translate(-50%, 0);
    }
    .word-ghost.show {
      opacity: 1;
    }
    .err {
      color: var(--error);
      font-size: 0.9rem;
      margin-top: 8px;
    }
    @media (max-width: 860px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="card">
      <h1>مطبع النص الحساني</h1>
      <p class="meta">الصق النص ثم اضغط "تطبيع". الكلمات المبدلة تصبح قابلة للنقر لمعرفة شكلها قبل التطبيع.</p>
    </section>

    <section class="card">
      <div class="label">النص الأصلي</div>
      <textarea id="input" placeholder="الصق النص هنا..."></textarea>
      <div class="row">
        <button id="runBtn" type="button">تطبيع</button>
        <span id="changed" class="stat">الكلمات المبدلة: 0</span>
        <span id="total" class="stat">إجمالي الكلمات: 0</span>
        <span id="pct" class="stat">نسبة التغيير: 0%</span>
      </div>
      <div id="err" class="err" role="alert"></div>
    </section>

    <section class="card grid">
      <div>
        <div class="label">النص بعد التطبيع</div>
        <div id="normalized" class="panel"></div>
      </div>
      <div>
        <div class="label">الكلمات المبدلة (انقر على الكلمة لرؤية شكلها قبل التطبيع)</div>
        <div id="highlighted" class="panel"></div>
      </div>
    </section>
  </div>
  <div id="wordGhost" class="word-ghost" aria-hidden="true"></div>

  <script>
    const runBtn = document.getElementById("runBtn");
    const input = document.getElementById("input");
    const normalized = document.getElementById("normalized");
    const highlighted = document.getElementById("highlighted");
    const changed = document.getElementById("changed");
    const total = document.getElementById("total");
    const pct = document.getElementById("pct");
    const err = document.getElementById("err");
    const wordGhost = document.getElementById("wordGhost");

    function clearSelectedWord() {
      highlighted.querySelectorAll("mark.change.selected").forEach((el) => {
        el.classList.remove("selected");
      });
    }

    function hideWordGhost() {
      clearSelectedWord();
      wordGhost.classList.remove("show", "below");
      wordGhost.textContent = "";
    }

    function showOldWord(node) {
      const before = node.dataset.before || "-";
      const rect = node.getBoundingClientRect();
      const aboveTop = rect.top - 10;

      clearSelectedWord();
      node.classList.add("selected");

      wordGhost.textContent = `قبل: ${before}`;
      wordGhost.style.left = `${rect.left + rect.width / 2}px`;

      if (aboveTop < 48) {
        wordGhost.classList.add("below");
        wordGhost.style.top = `${rect.bottom + 10}px`;
      } else {
        wordGhost.classList.remove("below");
        wordGhost.style.top = `${aboveTop}px`;
      }

      wordGhost.classList.add("show");
    }

    async function runNormalize() {
      err.textContent = "";
      runBtn.disabled = true;
      hideWordGhost();

      try {
        const res = await fetch("/api/normalize", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({ text: input.value || "" })
        });

        if (!res.ok) {
          const msg = await res.text();
          throw new Error(msg || "فشل التطبيع");
        }

        const data = await res.json();
        normalized.textContent = data.normalized_text;
        highlighted.innerHTML = data.highlighted_html;
        changed.textContent = `الكلمات المبدلة: ${data.stats.changed_words}`;
        total.textContent = `إجمالي الكلمات: ${data.stats.total_words}`;
        pct.textContent = `نسبة التغيير: ${data.stats.change_percentage}%`;
      } catch (e) {
        err.textContent = String(e.message || e);
      } finally {
        runBtn.disabled = false;
      }
    }

    runBtn.addEventListener("click", runNormalize);

    input.addEventListener("keydown", (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") {
        runNormalize();
      }
    });

    highlighted.addEventListener("click", (ev) => {
      const node = ev.target.closest("mark.change");
      if (!node) return;
      showOldWord(node);
    });

    highlighted.addEventListener("keydown", (ev) => {
      if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches("mark.change")) {
        ev.preventDefault();
        showOldWord(ev.target);
      }
    });

    document.addEventListener("click", (ev) => {
      if (!ev.target.closest("mark.change")) {
        hideWordGhost();
      }
    });
  </script>
</body>
</html>
"""


def _tokenize_text(text: str) -> List[str]:
    if not text:
        return []
    return _TOKEN_PATTERN.findall(text)


def _is_word_token(token: str) -> bool:
    return bool(re.match(r"\w+", token, re.UNICODE))


def _build_clickable_highlighted_html(original_text: str, normalized_text: str) -> str:
    highlighted_html, _ = _build_highlighted_html_and_stats(original_text, normalized_text)
    return highlighted_html


def _build_highlighted_html_and_stats(original_text: str, normalized_text: str) -> Tuple[str, Dict[str, float]]:
    """Build robust highlighted HTML + stats using word alignment.

    This avoids cascade-highlighting when token counts differ.
    """
    original_tokens = _tokenize_text(original_text)
    normalized_tokens = _tokenize_text(normalized_text)
    original_words = [token for token in original_tokens if _is_word_token(token)]
    normalized_words = [token for token in normalized_tokens if _is_word_token(token)]

    changed_flags: List[bool] = [False] * len(normalized_words)
    before_values: List[str] = [""] * len(normalized_words)

    matcher = difflib.SequenceMatcher(a=original_words, b=normalized_words, autojunk=False)
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            for idx in range(b1, b2):
                changed_flags[idx] = True
                before_values[idx] = ""
            continue
        if tag == "delete":
            continue

        # replace
        before_joined = " ".join(original_words[a1:a2])
        if (a2 - a1) == (b2 - b1):
            for offset, idx in enumerate(range(b1, b2)):
                changed_flags[idx] = True
                before_values[idx] = original_words[a1 + offset]
        else:
            for idx in range(b1, b2):
                changed_flags[idx] = True
                before_values[idx] = before_joined

    html_parts: List[str] = []
    word_index = 0
    for token in normalized_tokens:
        if not _is_word_token(token):
            html_parts.append(escape(token))
            continue

        escaped_display = escape(token)
        changed = changed_flags[word_index]
        if changed:
            before_attr = escape(before_values[word_index], quote=True)
            after_attr = escape(token, quote=True)
            html_parts.append(
                f'<mark class="change" data-before="{before_attr}" data-after="{after_attr}" tabindex="0">{escaped_display}</mark>'
            )
        else:
            html_parts.append(escaped_display)
        word_index += 1

    total_words = len(normalized_words)
    changed_words = sum(1 for flag in changed_flags if flag)
    stats = {
        "total_words": total_words,
        "changed_words": changed_words,
        "unchanged_words": total_words - changed_words,
        "change_percentage": round((changed_words / total_words * 100.0), 1) if total_words else 0.0,
    }
    return "".join(html_parts), stats


def _normalize_payload(text: str) -> Dict[str, object]:
    normalized = normalize_text(text)
    highlighted_html, stats = _build_highlighted_html_and_stats(text, normalized)
    return {
        "normalized_text": normalized,
        "highlighted_html": highlighted_html,
        "stats": stats,
    }


class _Handler(BaseHTTPRequestHandler):
    """HTTP handler for the local UI."""

    server_version = "HassyNormalizerUI/1.0"

    def _write_json(self, status: HTTPStatus, payload: Dict[str, object]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _write_html(self, status: HTTPStatus, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._write_html(HTTPStatus.OK, _PAGE)
            return
        if self.path == "/health":
            self._write_json(HTTPStatus.OK, {"ok": True})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/normalize":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 0 or content_length > 5_000_000:
                raise ValueError("Request body is too large")

            body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(body) if body else {}
            text = payload.get("text", "")
            if not isinstance(text, str):
                raise ValueError("'text' must be a string")

            self._write_json(HTTPStatus.OK, _normalize_payload(text))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive
            _LOG.exception("Unexpected API error")
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:
        _LOG.info("%s - %s", self.address_string(), format % args)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hassy-normalize-ui",
        description="Run local web UI for Hassaniya text normalization.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open a browser tab",
    )
    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    url = f"http://{args.host}:{args.port}"
    _LOG.info("Hassy Normalizer UI running at %s", url)
    _LOG.info("Press Ctrl+C to stop.")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _LOG.info("Stopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
