#!/usr/bin/env python3
"""Copy owner feedback from approved tickets into learning/feedback/.

Owners approve with scripts/owner/pxq.sh, which leaves the feedback JSON as a
comment on the ticket. This pulls those comments into
learning/feedback/<yyyy-mm>/PXQ-<n>.json so the weekly learning run can read
them. Only tags and reasons travel. Draft evidence never leaves the owner.

Usage: export_feedback.py [--days 7] [--repo owner/name]
"""
import argparse, datetime as dt, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLOCK = re.compile(r"<!-- pxq-feedback -->\s*```json\s*(\{.*?\})\s*```", re.S)

def gh(*args):
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "SamsonIdowu/PXQ-Autopilot"))
    a = ap.parse_args()
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)).date().isoformat()
    issues = gh("issue", "list", "--repo", a.repo, "--label", "stage:approved", "--state", "all",
                "--search", f"updated:>={since}", "--limit", "500", "--json", "number,comments")
    wrote = 0
    for it in issues:
        for c in reversed(it["comments"]):
            m = BLOCK.search(c.get("body", ""))
            if not m:
                continue
            fb = json.loads(m.group(1))
            month = c["createdAt"][:7]
            out = os.path.join(ROOT, "learning", "feedback", month, f'PXQ-{it["number"]}.json')
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(fb, fh, indent=2)
            wrote += 1
            break
    print(f"Exported feedback for {wrote} ticket(s) since {since}.")

if __name__ == "__main__":
    sys.exit(main())
