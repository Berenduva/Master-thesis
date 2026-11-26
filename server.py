#!/usr/bin/env python3
"""
Local study server for the confidence-score thesis study
=========================================================

What it does
------------
1. Serves the study app (index.html, study-config.js) at http://localhost:8000
2. Gives every new participant an ID (P001, P002, ...)
3. Saves everything the app sends into CSV files, one set per participant:

     data/participants.csv      one row per status change (started / resumed / finished / withdrew)
     data/P001_events.csv       every logged event: hovers, details, decisions, ...
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
    python server.py --data test_data  # save the CSVs in another folder (e.g. for a test run)

Useful URL parameters for the researcher (add to the address):
    ?pid=P012        pre-fill the participant number on the setup screen
    ?group=2         pre-select Group 2 on the setup screen
    ?debug=1         show the live event log next to the participant screen

Resuming: if the browser window was reloaded or closed during the break or part 2,
choose "Resume at Part 2" on the setup screen with the same participant number and
group. The server looks up which questions were already answered (in Pxxx_trials.csv),
adds a "resumed" row to participants.csv and appends to the same files; nothing is
overwritten.

Reused numbers: starting a NEW session with a participant number that already exists
is refused first (the setup screen asks the researcher to confirm). If the researcher
starts it anyway, the console shows a warning.

The data/ folder is listed in .gitignore so participant data never ends up on GitHub.
"""

import argparse
import csv
import json
import re
import sys
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
DATA_DIR = ROOT / "data"                        # all CSV output goes here (change with --data)
PARTICIPANTS_CSV = DATA_DIR / "participants.csv"

# Files the browser is allowed to request. Everything else (data/, .git/,
# this script) is refused, so participants can never download other people's data.
STATIC_ALLOWED = re.compile(r"^/(index\.html|study-config\.js|questions\.js|favicon\.ico|assets/[\w\-./]+)?$")

# The researcher picks the participant's group (Group 1–4, stored as 1–4) on the setup screen; the group
# fixes which block is shown with / without the confidence score and with which
# question set (GROUPS in study-config.js). Group, block and set are saved per row.

# --------------------------------------------------------------------------
# CSV column definitions (fixed order, so every file is easy to merge in R/pandas)
# --------------------------------------------------------------------------
PARTICIPANT_FIELDS = [
    "pid", "session_id", "group", "status", "server_time", "user_agent", "screen",
]
EVENT_FIELDS = [
    "pid", "session_id", "server_time", "client_time", "t_session_ms",
    "phase", "group", "block", "set", "condition", "trial", "question_id", "ai_correct",
    "t_trial_ms", "event", "target", "value", "duration_ms",
]
TRIAL_FIELDS = [
    "pid", "session_id", "group", "block", "set", "condition", "trial", "question_id", "part",
    "ai_answer", "ai_correct", "overall_confidence",
    "decision", "appropriate", "answer_ready_ms", "rt_ms",
    "details_opened", "details_toggles",
    "hover_count", "hovered_models", "hover_total_ms",
    "viewed_models", "view_total_ms",
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


def participant_history(pid: str) -> dict:
    """What is already stored for this participant: the group of their first session,
    every status so far, and which questions they answered per block (from Pxxx_trials.csv)."""
    group, statuses = "", []
    if PARTICIPANTS_CSV.exists():
        with PARTICIPANTS_CSV.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("pid") == pid:
                    group = group or row.get("group", "")
                    statuses.append(row.get("status", ""))
    done = {"1": [], "2": []}
    trials = DATA_DIR / f"{pid}_trials.csv"
    if trials.exists():
        with trials.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                block, qid = row.get("block", ""), row.get("question_id", "")
                if block in done and qid and qid not in done[block]:
                    done[block].append(qid)
    return {"group": group, "statuses": statuses, "done": done}


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
        """Assign (or accept) a participant ID, or resume an existing participant.

        mode "new"     start at Part 1. A participant number that already exists is
                       refused (error "pid_exists") unless body.force is true.
        mode "resume"  continue an existing participant at Part 2 (after a reload or a
                       closed window). The number must exist and the group must match;
                       the reply lists the questions already answered per block."""
        resume = body.get("mode") == "resume"
        group = str(body.get("group", ""))[:8]
        with WRITE_LOCK:
            requested = str(body.get("pid") or "").strip()
            if requested and not PID_PATTERN.match(requested):
                return self.send_json({"ok": False, "error": "invalid pid"}, HTTPStatus.BAD_REQUEST)
            # Hold the lock until the 'started' row is written, so two participants
            # starting at the same moment can never receive the same ID.
            pid = requested or f"P{next_participant_number():03d}"
            reused = requested in known_pids() if requested else False
            history = participant_history(pid) if reused else None

            if resume:
                if not reused:
                    print(f"  -> resume refused: participant {pid} not found")
                    return self.send_json({"ok": False, "error": "unknown_pid"})
                if history["group"] and history["group"] != group:
                    print(f"  -> resume refused: {pid} was in Group {history['group']}, not Group {group}")
                    return self.send_json({"ok": False, "error": "group_mismatch",
                                           "previous_group": history["group"]})
            elif reused and not body.get("force"):
                # Nothing is written: the setup screen asks the researcher what to do.
                print(f"  -> WARNING: participant number {pid} was used before (not started; "
                      f"the setup screen asks the researcher to resume or use another number)")
                return self.send_json({"ok": False, "error": "pid_exists", "history": history})

            session = {
                "pid": pid,
                "session_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
                "user_agent": self.headers.get("User-Agent", ""),
                "screen": body.get("screen", ""),
                "group": group,
            }
            append_rows(PARTICIPANTS_CSV, PARTICIPANT_FIELDS,
                        [{**session, "status": "resumed" if resume else "started", "server_time": now_iso()}])
        if resume:
            print(f"  -> participant {pid} RESUMED at part 2 (Group {group}; answered so far: "
                  f"part 1 {len(history['done']['1'])}, part 2 {len(history['done']['2'])})")
        else:
            print(f"  -> participant {pid} started (Group {group or '?'})"
                  + ("  [WARNING: this participant number was used before; "
                     "data are appended to the same files]" if reused else ""))
        return self.send_json({
            "ok": True, **session,
            "pid_reused": reused and not resume,
            "resumed": resume,
            "history": history,
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
    parser.add_argument("--data", default="data",
                        help="folder for the CSV files (default: data). Use another folder for test runs.")
    args = parser.parse_args()

    global DATA_DIR, PARTICIPANTS_CSV
    DATA_DIR = (ROOT / args.data).resolve()
    PARTICIPANTS_CSV = DATA_DIR / "participants.csv"

    # Show console messages (e.g. the reused-number warning) immediately, also when the
    # output is not a terminal.
    sys.stdout.reconfigure(line_buffering=True)
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
