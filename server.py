#!/usr/bin/env python3
"""
Small local server for the study.

Serves the app on http://localhost:8000 and writes what it sends to data/:
  participants.csv     status per participant (started / resumed / finished / withdrew)
  Pxxx_events.csv      all events (hovers, details, decisions, ...)
  Pxxx_trials.csv      one row per question
  Pxxx_responses.csv   consent (only if consent is shown in the app)

Usage:
  python server.py [--port 8080] [--lan] [--open] [--data test_data]

Only uses the standard library. data/ is in .gitignore.
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

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PARTICIPANTS_CSV = DATA_DIR / "participants.csv"

# only these files can be requested, so nobody can download data/
STATIC_ALLOWED = re.compile(r"^/(index\.html|study-config\.js|questions\.js|favicon\.ico|assets/[\w\-./]+)?$")


# csv columns
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
    "server_time",
]
RESPONSE_FIELDS = [
    "pid", "session_id", "instrument",
    "item_id", "item_text", "position", "value", "reverse_scored", "server_time",
]

# the server is threaded, so lock all writes
WRITE_LOCK = threading.RLock()

PID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def append_rows(path: Path, fields: list, rows: list) -> None:
    """Append rows, write the header if the file is new."""
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
    """One csv cell: lists become "a; b", no newlines."""
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
    """Next free P-number."""
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
    """Group, statuses and answered questions per block for this pid."""
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.send_json({"ok": True, "time": now_iso()})
        if not STATIC_ALLOWED.match(path):
            return self.send_error(HTTPStatus.NOT_FOUND)
        return super().do_GET()

    def end_headers(self):
        # no caching, so edits show up after a reload
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        # only log api calls and errors
        if "/api/" in self.path or (args and str(args[1])[:1] in "45"):
            super().log_message(fmt, *args)

    def do_POST(self):
        route = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"ok": False, "error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)

        if route == "/api/session":
            return self.start_session(body)

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
            append_rows(PARTICIPANTS_CSV, PARTICIPANT_FIELDS, [{
                **body.get("session", {}), "pid": pid,
                "status": body.get("status", ""), "server_time": now_iso(),
            }])
            return self.send_json({"ok": True})

        return self.send_json({"ok": False, "error": "unknown route"}, HTTPStatus.NOT_FOUND)

    def start_session(self, body: dict):
        """New session or resume.
        new: refused if the pid exists, unless force
        resume: pid must exist and the group must match"""
        resume = body.get("mode") == "resume"
        group = str(body.get("group", ""))[:8]
        with WRITE_LOCK:
            requested = str(body.get("pid") or "").strip()
            if requested and not PID_PATTERN.match(requested):
                return self.send_json({"ok": False, "error": "invalid pid"}, HTTPStatus.BAD_REQUEST)
            # keep the lock until the row is written so two people never get the same pid
            pid = requested or f"P{next_participant_number():03d}"
            reused = requested in known_pids() if requested else False
            history = participant_history(pid) if reused else None

            if resume:
                if not reused:
                    print(f"  -> resume refused: participant {pid} not found")
                    return self.send_json({"ok": False, "error": "unknown_pid"})
                if history["group"] and history["group"] != group:
                    print(f"  -> resume refused: {pid} was in Order {history['group']}, not Order {group}")
                    return self.send_json({"ok": False, "error": "group_mismatch",
                                           "previous_group": history["group"]})
            elif reused and not body.get("force"):
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
            print(f"  -> participant {pid} RESUMED at part 2 (Order {group}; answered so far: "
                  f"part 1 {len(history['done']['1'])}, part 2 {len(history['done']['2'])})")
        else:
            print(f"  -> participant {pid} started (Order {group or '?'})"
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

    # print right away, also when not in a terminal
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
