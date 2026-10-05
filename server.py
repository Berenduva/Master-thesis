#!/usr/bin/env python3
"""
Local study server for the confidence-score thesis study
=========================================================

What it does
------------
1. Serves the study app (index.html, study-config.js) at http://localhost:8000
2. Gives every new participant an ID (P001, P002, ...)
3. Saves everything the app sends into CSV files, one set per participant:

     data/participants.csv      one row per status change (started / finished / withdrew)
     data/P001_events.csv       every logged event: hovers, details, fact-check, decisions, ...
     data/P001_trials.csv       one row per question (the decision plus summary measures)
     data/P001_responses.csv    the consent statements the participant ticked

(The questionnaires are run separately in Qualtrics; link them via the participant ID.)

Only the Python standard library is used, so there is nothing to install.

How to run
----------
    python server.py                 # http://localhost:8000, only reachable from this computer
    python server.py --port 8080     # different port
    python server.py --lan           # also reachable from other devices on the same network
    python server.py --open          # open the study in your default browser

Useful URL parameters for the researcher (add to the address):
    ?pid=P012        use a fixed participant ID instead of the next free one
    ?debug=1         show the live event log next to the participant screen

The data/ folder is listed in .gitignore so participant data never ends up on GitHub.
"""

import argparse
import csv
import json
import re
import threading
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent          # the repository folder
DATA_DIR = ROOT / "data"                        # all CSV output goes here
PARTICIPANTS_CSV = DATA_DIR / "participants.csv"

# Files the browser is allowed to request. Everything else (data/, .git/,
# this script) is refused, so participants can never download other people's data.
STATIC_ALLOWED = re.compile(r"^/(index\.html|study-config\.js|favicon\.ico|assets/[\w\-./]+)?$")

# Which questions are shown with / without the confidence score is randomised
# per participant in the browser (index.html, planTrials) and saved per trial.

# --------------------------------------------------------------------------
# CSV column definitions (fixed order, so every file is easy to merge in R/pandas)
# --------------------------------------------------------------------------
PARTICIPANT_FIELDS = [
    "pid", "session_id", "status", "server_time", "user_agent", "screen",
]
EVENT_FIELDS = [
    "pid", "session_id", "server_time", "client_time", "t_session_ms",
    "phase", "condition", "trial", "question_id", "ai_correct",
    "t_trial_ms", "event", "target", "value", "duration_ms",
]
TRIAL_FIELDS = [
    "pid", "session_id", "condition", "trial", "question_id", "ai_correct", "overall_confidence",
    "decision", "appropriate", "rt_ms",
    "details_opened", "details_toggles",
    "hover_count", "hovered_models", "hover_total_ms",
    "factcheck_opened", "factcheck_rt_ms", "time_after_factcheck_ms",
    "server_time",
]
RESPONSE_FIELDS = [
    "pid", "session_id", "instrument",
    "item_id", "item_text", "position", "value", "reverse_scored", "server_time",
]

# One lock for all file writes: the server is multi-threaded and two requests
# must never write to the same CSV at the same moment.
WRITE_LOCK = threading.RLock()  # re-entrant: start_session holds it while appending

PID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def now_iso() -> str:
    """Current time as an ISO-8601 string in UTC, millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def append_rows(path: Path, fields: list, rows: list) -> None:
    """Append dict rows to a CSV file, writing the header first if the file is new.
    Unknown keys are ignored and missing keys are left empty."""
    DATA_DIR.mkdir(exist_ok=True)
    with WRITE_LOCK:
        new_file = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if new_file:
                writer.writeheader()
            for row in rows:
                writer.writerow({k: clean(row.get(k, "")) for k in fields})


def clean(value):
    """Make a value safe for one CSV cell (lists -> 'a; b', no line breaks)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (list, tuple)):
        value = "; ".join(str(v) for v in value)
    if isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("\r", " ").replace("\n", " ")


def next_participant_number() -> int:
    """Highest number used so far in participants.csv (P007 -> 7), plus one."""
    highest = 0
    if PARTICIPANTS_CSV.exists():
        with PARTICIPANTS_CSV.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                m = re.fullmatch(r"P(\d+)", row.get("pid", ""))
                if m:
                    highest = max(highest, int(m.group(1)))
    return highest + 1


def known_pids() -> set:
    if not PARTICIPANTS_CSV.exists():
        return set()
    with PARTICIPANTS_CSV.open(newline="", encoding="utf-8") as f:
        return {row.get("pid", "") for row in csv.DictReader(f)}


class StudyHandler(SimpleHTTPRequestHandler):
    """Serves the static app and handles the small JSON API under /api/."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ---- static files -----------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json({"ok": True, "time": now_iso()})
        if not STATIC_ALLOWED.match(path):
            return self.send_error(HTTPStatus.NOT_FOUND)
        return super().do_GET()

    def end_headers(self):
        # Never cache: after you edit index.html or study-config.js, a reload shows the new version.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        # Keep the console readable: only show API calls and errors, not every file request.
        if "/api/" in self.path or (args and str(args[1])[:1] in "45"):
            super().log_message(fmt, *args)

    # ---- API --------------------------------------------------------------
    def do_POST(self):
        route = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"ok": False, "error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)

        if route == "/api/session":
            return self.start_session(body)

        # Every other route writes data for an existing participant.
        pid = str(body.get("pid", ""))
        if not PID_PATTERN.match(pid):
            return self.send_json({"ok": False, "error": "invalid pid"}, HTTPStatus.BAD_REQUEST)

        if route == "/api/events":
            rows = body.get("events", [])
            append_rows(DATA_DIR / f"{pid}_events.csv", EVENT_FIELDS,
                        [{**r, "pid": pid, "server_time": now_iso()} for r in rows])
            return self.send_json({"ok": True, "saved": len(rows)})

        if route == "/api/trial":
            row = body.get("trial", {})
            append_rows(DATA_DIR / f"{pid}_trials.csv", TRIAL_FIELDS,
                        [{**row, "pid": pid, "server_time": now_iso()}])
            return self.send_json({"ok": True})

        if route == "/api/responses":
            rows = body.get("responses", [])
            append_rows(DATA_DIR / f"{pid}_responses.csv", RESPONSE_FIELDS,
                        [{**r, "pid": pid, "server_time": now_iso()} for r in rows])
            return self.send_json({"ok": True, "saved": len(rows)})

        if route == "/api/status":
            # Called when a participant finishes or withdraws.
            append_rows(PARTICIPANTS_CSV, PARTICIPANT_FIELDS, [{
                **body.get("session", {}), "pid": pid,
                "status": body.get("status", ""), "server_time": now_iso(),
            }])
            return self.send_json({"ok": True})

        return self.send_json({"ok": False, "error": "unknown route"}, HTTPStatus.NOT_FOUND)

    def start_session(self, body: dict):
        """Assign (or accept) a participant ID."""
        with WRITE_LOCK:
            requested = str(body.get("pid") or "").strip()
            if requested and not PID_PATTERN.match(requested):
                return self.send_json({"ok": False, "error": "invalid pid"}, HTTPStatus.BAD_REQUEST)
            # Hold the lock until the 'started' row is written, so two participants
            # starting at the same moment can never receive the same ID.
            pid = requested or f"P{next_participant_number():03d}"
            reused = requested in known_pids() if requested else False

            session = {
                "pid": pid,
                "session_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
                "user_agent": self.headers.get("User-Agent", ""),
                "screen": body.get("screen", ""),
            }
            append_rows(PARTICIPANTS_CSV, PARTICIPANT_FIELDS,
                        [{**session, "status": "started", "server_time": now_iso()}])
        print(f"  -> participant {pid} started"
              + ("  [WARNING: this ID was used before]" if reused else ""))
        return self.send_json({
            "ok": True, **session,
            "pid_reused": reused,
        })

    def send_json(self, data: dict, status=HTTPStatus.OK):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description="Local server for the confidence-score study.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--lan", action="store_true",
                        help="listen on all network interfaces (other devices on the network can connect)")
    parser.add_argument("--open", action="store_true", help="open the study in the default browser")
    args = parser.parse_args()

    host = "0.0.0.0" if args.lan else "127.0.0.1"
    DATA_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((host, args.port), StudyHandler)
    url = f"http://localhost:{args.port}/"
    print(f"Study server running at {url}")
    print(f"Saving data to {DATA_DIR}")
    print("Press Ctrl+C to stop.\n")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
