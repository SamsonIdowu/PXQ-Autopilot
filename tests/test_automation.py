#!/usr/bin/env python3
"""Checks open_plan.py and apply_review.py against a fake gh. No network needed."""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp()
log = os.path.join(tmp, "gh.log")
fake = os.path.join(tmp, "gh")
open(fake, "w").write(f'''#!{sys.executable}
import json, sys
a = sys.argv[1:]
open({log!r}, "a").write(json.dumps(a) + "\\n")
if a[:2] == ["label", "list"]: print(json.dumps([{{"name": "pxq:ticket"}}]))
elif a[:2] == ["issue", "list"]: print(json.dumps([{{"body": "```json\\n{{\\n  \\"key\\": \\"OLD-1\\"\\n}}\\n```"}}]))
elif a[:2] == ["issue", "create"]: print("https://github.com/o/r/issues/41")
elif a[:2] == ["issue", "view"]:
    stage = "stage:owner" if a[2] == "7" else "stage:testing"
    print(json.dumps({{"labels": [{{"name": "pxq:ticket"}}, {{"name": stage}}], "assignees": [{{"login": "SamsonIdowu"}}], "state": "OPEN"}}))
''')
os.chmod(fake, 0o755)
env = dict(os.environ, PATH=tmp + os.pathsep + os.environ["PATH"], PXQ_REPO="o/r")
calls = lambda: [json.loads(l) for l in open(log)] if os.path.exists(log) else []
plan = {"directive_id": "DIR-2026-10-07-x", "tickets": [
    {"key": "OLD-1", "title": "Old", "services": ["Wazuh server"], "test_type": "install", "lane": "use-operate", "acceptance": ["a"]},
    {"key": "NEW-1", "title": "New", "services": ["Wazuh server"], "test_type": "docs", "lane": "learn-discover", "needs_cloud": True, "acceptance": ["a"], "assignee": "samsonidowu", "assign_reason": "Lightest load"},
    {"key": "NEW-2", "title": "Ghost", "services": [], "test_type": "docs", "lane": "learn-discover", "acceptance": ["a"], "assignee": "ghost"}]}
pf = os.path.join(tmp, "plan.json"); json.dump(plan, open(pf, "w"))
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/automation/open_plan.py"), pf, "--project", "3"], env=env, capture_output=True, text=True)
out = json.loads(r.stdout or "[]")
c = calls()
creates = [x for x in c if x[:2] == ["issue", "create"]]
checks = [
    ("existing ticket skipped", len(creates) == 2),
    ("missing labels created", any(x[:3] == ["label", "create", "type:docs"] for x in c) and any(x[:3] == ["label", "create", "needs:cloud"] for x in c)),
    ("seated owner assigned", "--assignee" in creates[0] and creates[0][creates[0].index("--assignee") + 1] == "SamsonIdowu"),
    ("unseated owner left to the assign workflow", "--assignee" not in creates[1]),
    ("reason in body", "Why this owner" in creates[0][creates[0].index("--body") + 1]),
    ("project item added", any(x[:2] == ["project", "item-add"] for x in c)),
    ("result lists opened tickets", [o["key"] for o in out] == ["NEW-1", "NEW-2"] and out[0]["number"] == 41),
]
os.remove(log)
fb = os.path.join(tmp, "fb.json"); json.dump({"ticket": "PXQ-7", "decision": "approved", "findings": [], "missed": []}, open(fb, "w"))
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/automation/apply_review.py"), "--issue", "7", "--decision", "approve", "--by", "Samson Idowu", "--feedback", fb], env=env, capture_output=True, text=True)
c = calls()
checks += [
    ("approve comments with feedback", any(x[:2] == ["issue", "comment"] and "pxq-feedback" in x[-1] for x in c)),
    ("approve marks done and closes", any("stage:approved" in x for x in c) and any(x[:2] == ["issue", "close"] for x in c)),
]
os.remove(log)
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/automation/apply_review.py"), "--issue", "8", "--decision", "approve", "--by", "x"], env=env, capture_output=True, text=True)
checks.append(("refuses a ticket that isn't pending review", r.returncode != 0 and not any(x[:2] == ["issue", "close"] for x in calls())))
if os.path.exists(log): os.remove(log)
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts/automation/apply_review.py"), "--issue", "7", "--decision", "changes", "--by", "x", "--note", "Retest on 5.0.1"], env=env, capture_output=True, text=True)
c = calls()
checks.append(("changes reruns on the owner's agent", any("stage:changes" in x for x in c) and any(x[:2] == ["workflow", "run"] and "owner=SamsonIdowu" in x for x in c)))
fails = 0
for name, ok in checks:
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name)
print(f"{len(checks) - fails}/{len(checks)} passed")
sys.exit(1 if fails else 0)
