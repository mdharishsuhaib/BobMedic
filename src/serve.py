"""
serve.py — static file server for the demo target site.

Break state is stored server-side in target-site/break-state.json so that
every browser — including the isolated Chrome instance IBM RPA Studio opens —
sees the same DOM mutations without needing shared localStorage.

The server intercepts requests for index.html and invoices.html, reads the
current break flags, and injects a small inline script that sets localStorage
before the page's own script runs. The page JS reads localStorage as before,
so no page code needed to change.
"""

import json
import socket
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR     = PROJECT_ROOT / "target-site"
STATE_FILE   = SITE_DIR / "break-state.json"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

_server = None

BREAK_KEYS = (
    "break_login_id",
    "break_login_move",
    "break_login_text",
    "break_export_id",
)


def read_break_state() -> dict:
    """Return the current break flags from disk (all False when file absent)."""
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {k: False for k in BREAK_KEYS}


def write_break_state(flags: dict) -> None:
    """Persist break flags to disk."""
    STATE_FILE.write_text(
        json.dumps({k: bool(flags.get(k, False)) for k in BREAK_KEYS}, indent=2),
        encoding="utf-8",
    )


def _inject_script(html: str, flags: dict) -> bytes:
    """
    Prepend a localStorage-init script to the page so every browser session
    starts with the correct break state, regardless of its own storage.
    """
    sets = "".join(
        f"localStorage.setItem({json.dumps(k)},{json.dumps('true' if flags.get(k) else 'false')});"
        for k in BREAK_KEYS
    )
    snippet = f"<script>try{{{sets}}}catch(e){{}}</script>"
    # inject right after <head> (or at the top if no <head>)
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + snippet, 1)
    else:
        html = snippet + html
    return html.encode("utf-8")


class _SiteHandler(BaseHTTPRequestHandler):
    """
    Serves static files from SITE_DIR.
    For index.html and invoices.html, injects the break-state script.
    For POST /api/break, updates the server-side state and returns 200.
    """

    def log_message(self, fmt, *args):  # noqa: A003
        pass  # silence per-request noise

    def log_error(self, fmt, *args):  # noqa: A003
        pass  # suppress ConnectionAbortedError tracebacks (normal on Windows)

    def _send(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError):
            pass  # client closed the connection before we finished — harmless

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0].lstrip("/") or "index.html"

        # serve break-state as JSON for the break panel
        if path == "api/break-state":
            body = json.dumps(read_break_state()).encode()
            self._send(200, "application/json", body)
            return

        file_path = SITE_DIR / path
        if not file_path.exists() or not file_path.is_file():
            self._send(404, "text/plain", b"Not found")
            return

        content = file_path.read_bytes()

        # inject break state into HTML pages
        if path in ("index.html", "invoices.html", "payment.html"):
            flags = read_break_state()
            content = _inject_script(content.decode("utf-8", errors="replace"), flags)
            self._send(200, "text/html; charset=utf-8", content)
            return

        # guess content type
        ext = file_path.suffix.lower()
        ct = {
            ".html": "text/html; charset=utf-8",
            ".js":   "application/javascript",
            ".css":  "text/css",
            ".json": "application/json",
            ".png":  "image/png",
            ".ico":  "image/x-icon",
        }.get(ext, "application/octet-stream")
        self._send(200, ct, content)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]

        if path == "/api/break":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                flags = json.loads(body)
                write_break_state(flags)
                self._send(200, "application/json", b'{"ok":true}')
            except Exception as exc:
                self._send(400, "application/json",
                           json.dumps({"error": str(exc)}).encode())
            return

        self._send(404, "text/plain", b"Not found")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def is_running(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    """Return True when something already listens on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        return probe.connect_ex((host, port)) == 0


def ensure_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    """
    Start the target-site server in a background thread if it is not up yet.

    Returns:
        The base URL, e.g. ``http://127.0.0.1:8000``.
    """
    global _server
    base_url = f"http://{host}:{port}"

    if is_running(host, port):
        return base_url

    # Break state is deliberately left alone here. It lives on disk precisely so
    # it survives a restart, and clearing it on start meant that toggling a
    # fault and then starting the server silently undid the fault. `engine.py
    # baseline` clears it explicitly, which is where that belongs.
    _server = ThreadingHTTPServer((host, port), _SiteHandler)
    thread  = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()
    return base_url


def stop_server() -> None:
    """Shut the background server down, if this process started one."""
    global _server
    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None


if __name__ == "__main__":
    url = ensure_server()
    print(f"Target site: {url}")
    print(f"  login      {url}/index.html")
    print(f"  invoices   {url}/invoices.html")
    print(f"  break      {url}/break.html")
    print(f"  state API  {url}/api/break-state")
    print("Ctrl+C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        stop_server()
