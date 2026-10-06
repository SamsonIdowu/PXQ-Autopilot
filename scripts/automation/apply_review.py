#!/usr/bin/env python3
"""Apply an owner's review to a ticket on GitHub.

approve  -> saves the owner's tags on the ticket for the learning run, marks it Done
            (stage:approved) and closes it.
changes  -> records what to change, sets stage:changes and sends it back to the
            owner's agent.

Used by the PXQ automation task (reviews made on the dashboard) and by the
review-commands workflow (/approve and /changes comments on GitHub).

Usage: apply_review.py --issue N --decision approve|changes --by "Name" [--feedback f.json] [--note "..."] [--repo o/r]
"""
import argparse, json, os, subprocess, sys

def gh(*a, check=True):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(r.stderr.strip()[:300])
    return r.stdout

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--decision", choices=["approve", "changes"], required=True)
    ap.add_argument("--by", required=True)
    ap.add_argument("--feedback")
    ap.add_argument("--note", default="")
    ap.add_argument("--note-file", help="read the note from a file, so no text passes through a shell")
    ap.add_argument("--repo", default=os.environ.get("PXQ_REPO") or os.environ.get("GITHUB_REPOSITORY") or "SamsonIdowu/PXQ-Autopilot")
    ap.add_argument("--any-stage", action="store_true")
    a = ap.parse_args()
    info = json.loads(gh("issue", "view", str(a.issue), "--repo", a.repo, "--json", "labels,assignees,state"))
    labels = [l["name"] for l in info["labels"]]
    stages = [l for l in labels if l.startswith("stage:")]
    if "pxq:ticket" not in labels:
        sys.exit("Not a PXQ ticket.")
    if not a.any_stage and "stage:owner" not in stages:
        sys.exit(f"PXQ-{a.issue} isn't pending review (it's {', '.join(stages) or 'unstaged'}).")
    if a.note_file:
        a.note = open(a.note_file, encoding="utf-8").read()
    by = a.by.replace("\n", " ")[:80]
    note = a.note.replace("\r", "")[:2000]
    if a.decision == "approve":
        body = f"Approved by {by}. Done."
        if note:
            body += f"\n\n{note}"
        if a.feedback:
            fb = json.load(open(a.feedback, encoding="utf-8"))
            body += "\n\n<!-- pxq-feedback -->\n```json\n" + json.dumps(fb, indent=1) + "\n```"
        gh("issue", "comment", str(a.issue), "--repo", a.repo, "--body", body)
        for s in stages:
            gh("issue", "edit", str(a.issue), "--repo", a.repo, "--remove-label", s, check=False)
        gh("issue", "edit", str(a.issue), "--repo", a.repo, "--add-label", "stage:approved")
        gh("issue", "close", str(a.issue), "--repo", a.repo, "--reason", "completed")
        print(json.dumps({"issue": a.issue, "result": "done"}))
    else:
        gh("issue", "comment", str(a.issue), "--repo", a.repo, "--body", f"Changes requested by {by}.\n\n{note or 'No note given.'}")
        for s in stages:
            gh("issue", "edit", str(a.issue), "--repo", a.repo, "--remove-label", s, check=False)
        gh("issue", "edit", str(a.issue), "--repo", a.repo, "--add-label", "stage:changes")
        owner = info["assignees"][0]["login"] if info["assignees"] else ""
        if owner:
            gh("workflow", "run", "dispatch.yml", "--repo", a.repo, "-f", f"issue={a.issue}", "-f", f"owner={owner}", "-f", "agent=cloud", check=False)
        print(json.dumps({"issue": a.issue, "result": "changes"}))

if __name__ == "__main__":
    main()
