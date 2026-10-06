#!/usr/bin/env python3
"""Checks the dashboard snapshot against a fake GitHub API. No network needed."""
import http.server, json, os, sys, threading, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKET = {"key": "T-1", "title": "AIO install", "services": ["Wazuh server"], "test_type": "install",
          "lane": "use-operate", "needs_cloud": False, "deliverable": "D1.1"}
FB = {"ticket": "PXQ-2", "owner": "samson", "decision": "approved", "test_type": "install", "agent_versions": {},
      "findings": [{"id": "F1", "type": "docs", "agent_severity": "S2", "tag": "confirmed"},
                   {"id": "F2", "type": "docs", "agent_severity": "S3", "tag": "false-positive"}], "missed": []}
body = lambda t: "### Ticket\n\n```json\n" + json.dumps(t) + "\n```\n\n**Directive** DIR-x  \n"
ROUTES = {
    "/repos/o/r": {"full_name": "o/r", "html_url": "https://github.com/o/r", "private": True, "default_branch": "main"},
    "/repos/o/r/labels": [{"name": "pxq:ticket"}, {"name": "stage:testing"}],
    "/repos/o/r/issues": [
        {"number": 1, "title": "Wazuh server · AIO install", "body": body(TICKET), "labels": [{"name": "pxq:ticket"}, {"name": "stage:testing"}],
         "assignees": [{"login": "SamsonIdowu"}], "state": "open", "html_url": "u1", "created_at": "2026-10-07T08:00:00Z",
         "updated_at": "2026-10-07T08:05:00Z", "closed_at": None, "comments": 0},
        {"number": 2, "title": "Wazuh server · Docs", "body": body(dict(TICKET, key="T-2")), "labels": [{"name": "pxq:ticket"}, {"name": "stage:approved"}],
         "assignees": [{"login": "SamsonIdowu"}], "state": "closed", "html_url": "u2", "created_at": "2026-10-06T08:00:00Z",
         "updated_at": "2026-10-07T07:00:00Z", "closed_at": "2026-10-07T07:00:00Z", "comments": 1},
        {"number": 3, "title": "a PR", "pull_request": {}, "labels": [], "assignees": [], "state": "open"}],
    "/repos/o/r/issues/2/comments": [{"body": "Approved by @SamsonIdowu. Final report: https://claude.ai/artifact/abc\n\n<!-- pxq-feedback -->\n```json\n" + json.dumps(FB) + "\n```"}],
    "/repos/o/r/actions/runs": {"workflow_runs": [
        {"id": 11, "path": ".github/workflows/dispatch.yml", "display_title": "ticket 1 for SamsonIdowu on local", "status": "in_progress",
         "conclusion": None, "html_url": "r11", "event": "workflow_dispatch", "created_at": "2026-10-07T08:01:00Z", "updated_at": "2026-10-07T08:02:00Z", "head_branch": "main"},
        {"id": 10, "path": ".github/workflows/validate.yml", "display_title": "x", "status": "completed", "conclusion": "success",
         "html_url": "r10", "event": "push", "created_at": "2026-10-07T07:00:00Z", "updated_at": "2026-10-07T07:01:00Z", "head_branch": "main"},
        {"id": 9, "path": ".github/workflows/other.yml", "display_title": "x", "status": "completed", "conclusion": "success",
         "html_url": "r9", "event": "push", "created_at": "2026-10-07T07:00:00Z", "updated_at": "2026-10-07T07:01:00Z", "head_branch": "main"}]},
    "/repos/o/r/actions/runs/11/jobs": {"jobs": [{"runner_name": "SamsonIdowu-local", "started_at": "2026-10-07T08:01:30Z"}]},
}

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        data = ROUTES.get(path)
        self.send_response(200 if data is not None else 404)
        self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(data if data is not None else {"message": "Not Found"}).encode())
    def log_message(self, *a): pass

srv = http.server.HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["GH_API"] = f"http://127.0.0.1:{srv.server_port}"
os.environ.pop("GITHUB_TOKEN", None); os.environ.pop("GH_TOKEN", None)
sys.path.insert(0, os.path.join(ROOT, "scripts", "dashboard"))
import snapshot  # noqa: E402

s = snapshot.build("o/r")
if os.environ.get("SNAPSHOT_OUT"):  # lets UI tests reuse a realistic snapshot
    json.dump(s, open(os.environ["SNAPSHOT_OUT"], "w"), indent=1)
checks = [
    ("two tickets, PR skipped", len(s["tickets"]) == 2),
    ("stage from label", s["tickets"][0]["stage"] == "testing"),
    ("owner mapped to team key", s["tickets"][0]["owner_key"] == "samson"),
    ("services from ticket JSON", s["tickets"][0]["services"] == ["Wazuh server"]),
    ("last run linked", (s["tickets"][0]["last_run"] or {}).get("agent") == "local"),
    ("runner seen", s["agents"].get("samsonidowu", {}).get("local", {}).get("runner") == "SamsonIdowu-local"),
    ("report link", s["tickets"][1].get("report_url") == "https://claude.ai/artifact/abc"),
    ("feedback summary", s["tickets"][1].get("feedback", {}).get("severity", {}).get("S2") == 1),
    ("false positives excluded from severity", s["tickets"][1]["feedback"]["severity"]["S3"] == 0),
    ("directive parsed", s["tickets"][0]["directive"] == "DIR-x"),
    ("unrelated workflows dropped", all(r["workflow"] != "other" for r in s["runs"])),
    ("validate status", (s["workflows"]["validate"] or {}).get("conclusion") == "success"),
    ("missing labels listed", "stage:approved" in s["labels"]["missing"]),
    ("hash present", len(s["hash"]) == 16),
]
fails = 0
for name, ok in checks:
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name)
print(f"{len(checks) - fails}/{len(checks)} passed")
sys.exit(1 if fails else 0)
