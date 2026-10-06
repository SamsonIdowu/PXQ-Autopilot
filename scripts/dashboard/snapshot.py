#!/usr/bin/env python3
"""Build the dashboard snapshot from GitHub.

Reads tickets, stages, owners, runs, plans and learning metrics, and writes one
JSON file the dashboard shows. The dashboard-data workflow runs this with the
workflow's own token and publishes the file to the dashboard-data branch. A
Claude scheduled task copies it into the dashboard.

Only things already visible to anyone who can read the repo go into the
snapshot. Drafts and evidence never do.

Usage:
  GITHUB_TOKEN=... python3 scripts/dashboard/snapshot.py --repo owner/name --out snapshot.json
"""
import argparse, datetime as dt, glob, hashlib, json, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API = os.environ.get("GH_API", "https://api.github.com")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

STAGES = ["new", "assigned", "testing", "review", "rework", "owner", "changes", "approved",
          "blocked", "paused-usage", "unassigned", "closed"]
LABELS_NEEDED = ["pxq:ticket", "needs:cloud", "learning"] + [f"stage:{s}" for s in STAGES if s not in ("new", "closed")]
WORKFLOWS = {"assign.yml", "dispatch.yml", "fallback.yml", "learn.yml", "validate.yml", "dashboard-data.yml"}
DISPATCH_TITLE = re.compile(r"^ticket (\d+) for ([A-Za-z0-9-]+) on (cloud|local)$")
TICKET_JSON = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
FEEDBACK = re.compile(r"<!-- pxq-feedback -->\s*```json\s*(\{.*?\})\s*```", re.S)
REPORT_URL = re.compile(r"Final report: (https://\S+)")
REPORT_MARK = "<!-- pxq-report v1 -->"
FINDINGS = re.compile(r"<!-- pxq-findings (.*?) -->", re.S)
REPORTS = {}  # issue number -> report markdown, written next to the snapshot
DIRECTIVE = re.compile(r"\*\*Directive\*\*\s+(\S+)")


def get(path, params=None):
    url = path if path.startswith("http") else f"{API}/{path.lstrip('/')}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "X-GitHub-Api-Version": "2022-11-28",
                                               "User-Agent": "pxq-dashboard"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get_all(path, params=None, key=None, limit=500):
    out, page = [], 1
    while len(out) < limit:
        data = get(path, dict(params or {}, per_page=100, page=page))
        items = data[key] if key else data
        out += items
        if len(items) < 100:
            break
        page += 1
    return out[:limit]


def iso(s):
    return s or None


def read_yaml_team(path):
    """Read config/team.yaml without PyYAML (flow mappings, one person per line)."""
    team, admin = [], None
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].rstrip()
        m = re.match(r"^admin:\s*(\S+)", line)
        if m:
            admin = m.group(1)
            continue
        m = re.match(r"^\s+([a-z0-9_-]+):\s*\{(.*)\}\s*$", line)
        if not m:
            continue
        fields = {}
        for part in re.findall(r'(\w+):\s*("[^"]*"|[^,]+)', m.group(2)):
            k, v = part[0], part[1].strip().strip('"')
            fields[k] = None if v == "null" else v
        team.append({"key": m.group(1), "name": fields.get("name", m.group(1)), "github": fields.get("github") or "",
                     "primary": fields.get("primary"), "backup": fields.get("backup"),
                     "max_open": int(fields.get("max_open") or 6)})
    return team, admin


def parse_ticket(body):
    m = TICKET_JSON.search(body or "")
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def summarize_feedback(fb):
    tags = {"confirmed": 0, "false-positive": 0, "wrong-severity": 0, "duplicate": 0, "unclear": 0}
    sev = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
    for f in fb.get("findings", []):
        tags[f.get("tag", "confirmed")] = tags.get(f.get("tag", "confirmed"), 0) + 1
        if f.get("tag") in ("false-positive", "duplicate"):
            continue
        s = f.get("owner_severity") or f.get("agent_severity")
        if s in sev:
            sev[s] += 1
    return {"decision": fb.get("decision"), "tags": tags, "severity": sev, "missed": len(fb.get("missed", [])),
            "reviewer_verdict": fb.get("reviewer_verdict"), "agent": fb.get("agent")}


def build(repo):
    info = get(f"repos/{repo}")
    team, admin = read_yaml_team(os.path.join(ROOT, "config", "team.yaml"))
    by_login = {p["github"].lower(): p["key"] for p in team if p["github"]}

    labels = {l["name"] for l in get_all(f"repos/{repo}/labels")}
    issues = [i for i in get_all(f"repos/{repo}/issues", {"state": "all", "labels": "pxq:ticket"}) if "pull_request" not in i]

    runs = get_all(f"repos/{repo}/actions/runs", key="workflow_runs", limit=100)
    runs = [r for r in runs if os.path.basename(r.get("path", "")) in WORKFLOWS]

    run_rows, last_run_by_issue, agents = [], {}, {}
    for r in runs:
        wf = os.path.basename(r["path"]).replace(".yml", "")
        row = {"id": r["id"], "workflow": wf, "title": r.get("display_title"), "status": r["status"],
               "conclusion": r.get("conclusion"), "url": r["html_url"], "event": r.get("event"),
               "created": r["created_at"], "updated": r["updated_at"], "branch": r.get("head_branch")}
        m = DISPATCH_TITLE.match(r.get("display_title") or "") if wf == "dispatch" else None
        if m:
            row.update(issue=int(m.group(1)), owner=m.group(2), agent=m.group(3))
            last_run_by_issue.setdefault(row["issue"], row)
        run_rows.append(row)

    # Runner names for recent ticket runs tell us which machine actually picked them up.
    for row in [x for x in run_rows if x.get("issue")][:20]:
        try:
            jobs = get(f"repos/{repo}/actions/runs/{row['id']}/jobs").get("jobs", [])
        except Exception:
            jobs = []
        if jobs:
            row["runner"] = jobs[0].get("runner_name")
            row["started"] = jobs[0].get("started_at")
        if row["status"] == "queued" or not row.get("runner"):
            continue
        a = agents.setdefault(row["owner"].lower(), {})
        if row["agent"] not in a:
            a[row["agent"]] = {"last_seen": row.get("started") or row["created"], "runner": row["runner"],
                               "conclusion": row["conclusion"], "status": row["status"]}

    waiting = {}
    for row in run_rows:
        if row.get("issue") and row["status"] in ("queued", "waiting", "pending"):
            waiting.setdefault(row["owner"].lower(), []).append({"issue": row["issue"], "agent": row["agent"], "since": row["created"]})

    tickets = []
    for i in issues:
        t = parse_ticket(i.get("body"))
        names = [l["name"] for l in i["labels"]]
        stage = next((n.split(":", 1)[1] for n in names if n.startswith("stage:")), None)
        if not stage:
            stage = "closed" if i["state"] == "closed" else ("assigned" if i["assignees"] else "new")
        login = i["assignees"][0]["login"] if i["assignees"] else None
        row = {"n": i["number"], "key": t.get("key"), "title": t.get("title") or i["title"], "issue_title": i["title"],
               "url": i["html_url"], "state": i["state"], "stage": stage,
               "owner": login, "owner_key": by_login.get((login or "").lower(), login),
               "services": t.get("services", []), "test_type": t.get("test_type"), "lane": t.get("lane"),
               "needs_cloud": bool(t.get("needs_cloud")) or "needs:cloud" in names, "deliverable": t.get("deliverable"),
               "directive": (DIRECTIVE.search(i.get("body") or "") or [None, None])[1],
               "created": i["created_at"], "updated": i["updated_at"], "closed": iso(i.get("closed_at")),
               "comments": i.get("comments", 0), "valid_ticket": bool(t), "last_run": last_run_by_issue.get(i["number"])}
        if i.get("comments") and (stage in ("owner", "changes", "approved", "rework", "review") or i["state"] == "closed"):
            try:
                comments = get_all(f"repos/{repo}/issues/{i['number']}/comments", limit=100)
            except Exception:
                comments = []
            for c in reversed(comments):
                body = c.get("body") or ""
                if "report" not in row and body.startswith(REPORT_MARK):
                    fm = FINDINGS.search(body)
                    try:
                        found = json.loads(fm.group(1)) if fm else []
                    except json.JSONDecodeError:
                        found = []
                    sev = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
                    for f in found:
                        if f.get("severity") in sev:
                            sev[f["severity"]] += 1
                    text = body.split("---", 1)[1].strip() if "\n---\n" in body else body
                    REPORTS[i["number"]] = text
                    row["report"] = {"url": c.get("html_url"), "at": c.get("created_at"), "findings": found[:30],
                                     "severity": sev, "hash": hashlib.sha256(text.encode()).hexdigest()[:12]}
                if "report_url" not in row:
                    m = REPORT_URL.search(body)
                    if m:
                        row["report_url"] = m.group(1).rstrip(".)")
                m = FEEDBACK.search(body)
                if m and "feedback" not in row:
                    try:
                        row["feedback"] = summarize_feedback(json.loads(m.group(1)))
                    except json.JSONDecodeError:
                        pass
        tickets.append(row)
    tickets.sort(key=lambda x: x["n"])

    plans = []
    keys_open = {t["key"] for t in tickets if t["key"]}
    for f in sorted(glob.glob(os.path.join(ROOT, "plans", "*.json"))):
        try:
            p = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        ks = [t.get("key") for t in p.get("tickets", [])]
        plans.append({"id": p.get("directive_id") or os.path.basename(f)[:-5], "file": os.path.relpath(f, ROOT),
                      "summary": p.get("summary"), "workstreams": [w.get("title") for w in p.get("workstreams", [])],
                      "tickets": len(ks), "opened": sum(1 for k in ks if k in keys_open)})

    metrics = None
    mpath = os.path.join(ROOT, "learning", "metrics", "latest.json")
    if os.path.exists(mpath):
        try:
            metrics = json.load(open(mpath, encoding="utf-8"))
        except Exception:
            metrics = None

    services = []
    spath = os.path.join(ROOT, "config", "services.yaml")
    if os.path.exists(spath):
        services = [l.strip()[2:].strip() for l in open(spath, encoding="utf-8")
                    if l.strip().startswith("- ") and not l.strip().startswith("#")]
    planner_lessons = []
    lpath = os.path.join(ROOT, "learning", "lessons", "planner.md")
    if os.path.exists(lpath):
        planner_lessons = [l[2:].strip() for l in open(lpath, encoding="utf-8") if l.startswith("- ")][:40]

    lessons = {}
    for a in ("planner", "tester", "reviewer"):
        path = os.path.join(ROOT, "learning", "lessons", f"{a}.md")
        lessons[a] = sum(1 for l in open(path, encoding="utf-8") if l.startswith("- ")) if os.path.exists(path) else 0

    def latest(wf):
        r = next((x for x in run_rows if x["workflow"] == wf and (wf != "validate" or x.get("branch") == info["default_branch"])), None)
        return {k: r[k] for k in ("status", "conclusion", "url", "updated")} if r else None

    snap = {
        "version": 1,
        "repo": {"name": info["full_name"], "url": info["html_url"], "private": info["private"],
                 "default_branch": info["default_branch"]},
        "team": team, "admin": admin,
        "labels": {"missing": [l for l in LABELS_NEEDED if l not in labels]},
        "tickets": tickets,
        "runs": run_rows[:40],
        "agents": agents, "waiting": waiting,
        "plans": plans, "metrics": metrics, "lessons": lessons,
        "services": services, "planner_lessons": planner_lessons,
        "workflows": {wf: latest(wf) for wf in ("validate", "assign", "dispatch", "fallback", "learn", "dashboard-data")},
    }
    # The dashboard stores the snapshot as one document, capped at 256 KiB. Trim the oldest
    # history first if a busy month ever pushes it near the cap.
    while len(json.dumps(snap, separators=(",", ":"))) > 230_000:
        if len(snap["runs"]) > 10:
            snap["runs"] = snap["runs"][:len(snap["runs"]) // 2]
            continue
        closed = [t for t in snap["tickets"] if t["state"] == "closed"]
        if not closed:
            break
        snap["tickets"].remove(min(closed, key=lambda t: t["closed"] or ""))
        snap["trimmed"] = snap.get("trimmed", 0) + 1
    body = json.dumps(snap, sort_keys=True, separators=(",", ":"))
    snap["hash"] = hashlib.sha256(body.encode()).hexdigest()[:16]
    snap["generated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return snap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "SamsonIdowu/PXQ-Autopilot"))
    ap.add_argument("--out", default="snapshot.json")
    ap.add_argument("--reports-dir", help="also write each ticket's report as <issue>.md here")
    a = ap.parse_args()
    snap = build(a.repo)
    if a.reports_dir:
        os.makedirs(a.reports_dir, exist_ok=True)
        for n, text in REPORTS.items():
            with open(os.path.join(a.reports_dir, f"{n}.md"), "w", encoding="utf-8") as fh:
                fh.write(text)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=1, sort_keys=True)
    print(f"{len(snap['tickets'])} tickets, {len(snap['runs'])} runs, hash {snap['hash']} -> {a.out}")


if __name__ == "__main__":
    sys.exit(main())
