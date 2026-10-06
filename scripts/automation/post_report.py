#!/usr/bin/env python3
"""Post the Reviewer's final report to the ticket so the team sees it on the dashboard.

Called by runner/run-ticket.sh after the secret scan. Only report.final.md and a short
findings summary leave the agent machine. Evidence, logs and transcripts stay there.

Usage: post_report.py <run-dir> <issue> <owner/repo>
"""
import json, os, subprocess, sys, tempfile

MAX = 60000

def main(run, issue, repo):
    report_path = os.path.join(run, "report.final.md")
    if not os.path.exists(report_path):
        print("No report.final.md, nothing to post", file=sys.stderr)
        return 1
    report = open(report_path, encoding="utf-8").read()
    findings = []
    try:
        findings = json.load(open(os.path.join(run, "findings.json"), encoding="utf-8"))
    except Exception:
        pass
    removed = set()
    try:
        removed = {r if isinstance(r, str) else r.get("id") for r in json.load(open(os.path.join(run, "review.json"))).get("removed", [])}
    except Exception:
        pass
    summary = [{k: f.get(k) for k in ("id", "title", "severity", "service", "type")}
               for f in (findings if isinstance(findings, list) else []) if f.get("id") not in removed]
    if len(report) > MAX:
        report = report[:MAX] + "\n\n_Report cut short here. The full report stays on the owner's agent._\n"
    body = ("<!-- pxq-report v1 -->\n"
            f"<!-- pxq-findings {json.dumps(summary, separators=(',', ':')).replace('--', '- -')} -->\n"
            "**Report from the agents. Pending the owner's review.**\n"
            "The owner approves it on the dashboard, or comments `/approve` or `/changes <what to change>` here.\n\n---\n\n"
            + report)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(body)
    subprocess.run(["gh", "issue", "comment", str(issue), "--repo", repo, "--body-file", fh.name], check=True)
    os.unlink(fh.name)
    return 0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
