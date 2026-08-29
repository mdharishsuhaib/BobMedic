"""
start.py — one command to bring the whole demo up.

Starts three things and leaves them running until Ctrl+C:

    target site     http://127.0.0.1:8000   the NovaCorp portal the bots drive
    control API     http://127.0.0.1:8100   incidents, approvals, demo runs
    dashboard       http://127.0.0.1:3000   the control centre

The dashboard is optional: if npm is missing, the first two still come up and
the dashboard can be opened later, or read from its built files.
"""

import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import engine  # noqa: E402 - after sys.path setup
from api import API_HOST, API_PORT, BobMadakAPI  # noqa: E402
from http.server import ThreadingHTTPServer  # noqa: E402
from serve import ensure_server  # noqa: E402


def start_dashboard() -> subprocess.Popen | None:
    """Launch the Vite dev server, if npm and its packages are available."""
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    dashboard_dir = PROJECT_ROOT / "dashboard"

    if not npm:
        print("[skip] npm not found — start the dashboard yourself with 'npm run dev'.")
        return None
    if not (dashboard_dir / "node_modules").exists():
        print("[npm ] installing dashboard packages (first run only)...")
        subprocess.run([npm, "install"], cwd=dashboard_dir, check=False)

    return subprocess.Popen(
        [npm, "run", "dev"],
        cwd=dashboard_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    """Bring the demo up and hold it there."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    site_url = ensure_server()
    engine.publish_feed()

    api_server = ThreadingHTTPServer((API_HOST, API_PORT), BobMadakAPI)
    threading.Thread(target=api_server.serve_forever, daemon=True).start()

    dashboard = start_dashboard()
    time.sleep(1.5)

    print()
    print("  Target site   " + site_url)
    print("  Break panel   " + site_url + "/break.html")
    print(f"  Control API   http://{API_HOST}:{API_PORT}/api/feed")
    print("  Dashboard     http://127.0.0.1:3000" if dashboard else
          "  Dashboard     not started")
    print()
    print("  Break a bot from the dashboard, or from the command line:")
    print("    python src/engine.py demo invoice-extract rename-login-id")
    print()
    print("  Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        api_server.shutdown()
        if dashboard:
            dashboard.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
