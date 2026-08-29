"""
api.py — the control surface behind the dashboard.

Small on purpose: the dashboard needs to read incidents, approve or reject a
patch, and kick off a demo run. Nothing here holds state — the incidents on
disk are the state, and this only reads and writes them.

Built on the standard library so the project adds no server dependency.

    GET  /api/feed                     every incident plus the fleet summary
    GET  /api/scenarios                the break scenarios the demo can apply
    GET  /api/status                   whether a run is in flight
    POST /api/run                      {"bot_id": ..., "scenario": ...}
    POST /api/incidents/<id>/approve   apply a verified patch and re-run
    POST /api/incidents/<id>/reject    discard a proposed patch
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import engine
from registry import load_bots
from serve import ensure_server

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_HOST = "127.0.0.1"
API_PORT = 8100

# One run at a time: the browser automation is the bottleneck and two
# concurrent heals would fight over the same script files.
_job_lock = threading.Lock()
_job_state = {"running": False, "label": None, "log": [], "error": None}


def _run_job(label: str, work) -> None:
    """Run one engine job in the background, recording its outcome."""
    def target():
        try:
            work()
        except Exception as error:  # noqa: BLE001 - surfaced to the dashboard
            _job_state["error"] = str(error)
        finally:
            _job_state["running"] = False
            _job_state["label"] = None
            _job_lock.release()

    if not _job_lock.acquire(blocking=False):
        raise RuntimeError("A run is already in progress.")

    _job_state.update({"running": True, "label": label, "error": None})
    threading.Thread(target=target, daemon=True).start()


class BotMedicAPI(BaseHTTPRequestHandler):
    """Request handler for the dashboard's control calls."""

    server_version = "BotMedic/1.0"

    def log_message(self, fmt, *args):  # noqa: A003 - stdlib signature
        """Keep the console readable; the engine prints its own progress."""

    # ── plumbing ──────────────────────────────────────────────────

    def _send(self, status: int, payload: dict) -> None:
        """Write a JSON response with permissive CORS for the dev server."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        """Parse a JSON request body, tolerating an empty one."""
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):  # noqa: N802 - stdlib naming
        """Answer the browser's CORS preflight."""
        self._send(204, {})

    # ── routes ────────────────────────────────────────────────────

    def do_GET(self):  # noqa: N802 - stdlib naming
        """Read-only endpoints."""
        if self.path.startswith("/api/feed"):
            engine.publish_feed()
            self._send(200, json.loads(
                (PROJECT_ROOT / "dashboard/public/incidents.json").read_text(encoding="utf-8")
            ))
        elif self.path.startswith("/api/scenarios"):
            self._send(200, {
                "scenarios": [
                    {"id": key, "description": value["description"], "breaks": value["breaks"]}
                    for key, value in engine.BREAK_SCENARIOS.items()
                ],
                "bots": [
                    {"bot_id": bot_id, **{k: bot[k] for k in
                                          ("bot_name", "risk_tier", "description")}}
                    for bot_id, bot in load_bots().items()
                ],
            })
        elif self.path.startswith("/api/status"):
            self._send(200, dict(_job_state))
        else:
            self._send(404, {"error": f"No route for {self.path}"})

    def do_POST(self):  # noqa: N802 - stdlib naming
        """Actions that change state."""
        parts = [part for part in self.path.split("?")[0].split("/") if part]

        try:
            if parts[:2] == ["api", "run"]:
                payload = self._body()
                bot_id = payload.get("bot_id")
                scenario_id = payload.get("scenario")
                scenario = engine.BREAK_SCENARIOS.get(scenario_id or "")
                breaks = scenario["breaks"] if scenario else None
                label = f"{bot_id} / {scenario_id or 'as-is'}"
                _run_job(label, lambda: engine.heal(bot_id, breaks=breaks))
                self._send(202, {"accepted": True, "label": label})

            elif len(parts) == 4 and parts[:2] == ["api", "incidents"] and parts[3] == "approve":
                run_id = parts[2]
                payload = self._body()
                scenario = engine.BREAK_SCENARIOS.get(payload.get("scenario") or "")
                breaks = scenario["breaks"] if scenario else None
                # Checked here, not inside the worker: a risk-tier refusal has to
                # come back on the request the operator made, as a 403 they see.
                engine.assert_approvable(run_id)
                _run_job(
                    f"approve {run_id}",
                    lambda: engine.approve(run_id, breaks=breaks),
                )
                self._send(202, {"accepted": True, "run_id": run_id})

            elif len(parts) == 4 and parts[:2] == ["api", "incidents"] and parts[3] == "reject":
                run_id = parts[2]
                reason = self._body().get("reason", "Rejected by operator")
                self._send(200, engine.reject(run_id, reason))

            else:
                self._send(404, {"error": f"No route for {self.path}"})

        except PermissionError as error:
            # The risk tier refusing an approval is a legitimate answer, not a crash.
            self._send(403, {"error": str(error)})
        except (KeyError, ValueError) as error:
            self._send(400, {"error": str(error)})
        except RuntimeError as error:
            self._send(409, {"error": str(error)})


def main() -> None:
    """Start the target site and the control API together."""
    site_url = ensure_server()
    engine.publish_feed()
    server = ThreadingHTTPServer((API_HOST, API_PORT), BotMedicAPI)
    print(f"Target site   {site_url}")
    print(f"Control API   http://{API_HOST}:{API_PORT}/api/feed")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()


