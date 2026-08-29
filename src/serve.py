"""
serve.py — static file server for the NovaCorp target site.

The target site is served over HTTP rather than opened from disk because the
break control panel stores its flags in localStorage, and Chromium denies
localStorage to file:// origins. Serving the site also makes the demo behave
like a real target application.
"""

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = PROJECT_ROOT / "target-site"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

_server = None


class _QuietHandler(SimpleHTTPRequestHandler):
    """Static handler that does not log every bot request to stdout."""

    def log_message(self, fmt, *args):  # noqa: A003 - stdlib signature
        """Silence per-request logging."""


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

    handler = partial(_QuietHandler, directory=str(SITE_DIR))
    _server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
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
    print(f"NovaCorp target site served at {url}")
    print(f"  login   {url}/index.html")
    print(f"  break   {url}/break.html")
    print("Ctrl+C to stop.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        stop_server()
