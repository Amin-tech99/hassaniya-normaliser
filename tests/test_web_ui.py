"""Tests for local web UI server."""

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from hassy_normalizer.web_ui.server import _Handler, _normalize_payload

_INPUT = "\u0645\u062f\u0631\u0633\u0629"
_OUTPUT = "\u0645\u062f\u0631\u0633\u0647"


def _start_test_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_normalize_payload():
    payload = _normalize_payload(_INPUT)

    assert "normalized_text" in payload
    assert "highlighted_html" in payload
    assert "stats" in payload
    assert payload["normalized_text"] == _OUTPUT
    assert payload["stats"]["changed_words"] >= 1
    assert "data-before=" in payload["highlighted_html"]
    assert "data-after=" in payload["highlighted_html"]


def test_index_page_is_arabic():
    server, thread = _start_test_server()
    try:
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("GET", "/")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()

        assert response.status == 200
        assert '<html lang="ar" dir="rtl">' in body
        assert "\u0645\u0637\u0628\u0639 \u0627\u0644\u0646\u0635 \u0627\u0644\u062d\u0633\u0627\u0646\u064a" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_health_endpoint():
    server, thread = _start_test_server()
    try:
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request("GET", "/health")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()

        assert response.status == 200
        assert json.loads(body) == {"ok": True}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_normalize_endpoint():
    server, thread = _start_test_server()
    try:
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        req = json.dumps({"text": _INPUT}).encode("utf-8")
        conn.request(
            "POST",
            "/api/normalize",
            body=req,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        conn.close()

        assert response.status == 200
        assert body["normalized_text"] == _OUTPUT
        assert body["stats"]["changed_words"] >= 1
        assert "mark" in body["highlighted_html"]
        assert "data-before=" in body["highlighted_html"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
