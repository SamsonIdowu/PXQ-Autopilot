#!/usr/bin/env python3
"""Open one GitHub issue per ticket in an approved plan.

Used by the PXQ automation task after a directive is approved on the dashboard, and by
scripts/owner/pxq.sh open-issues. Skips tickets that already exist, creates any missing
labels, assigns the Planner's proposed owner when that person has a seat in
config/team.yaml, and can add each issue to a GitHub Project.

Prints a JSON list of what it opened: [{"key", "number", "url", "assignee"}].

Usage: open_plan.py <plan.json> [--repo owner/name] [--project <number>]
"""
import argparse, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LABELS = {"pxq:ticket": ("5319e7", "A PXQ test ticket"), "needs:cloud": ("0e8a16", "Needs the cloud agent")}


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def seated():
    path = os.path.join(ROOT, "config", "team.yaml")
    return {m.group(1).lower(): m.group(1) for l in open(path, encoding="utf-8")
            if (m := re.search(r'github:\s*"([^"]+)"', l))}


def body_for(t, plan):
    svc = ", ".join(t.get("services") or [])
    return ("```json\n" + json.dumps(t, indent=2) + "\n```\n\n"
            f'**Directive** {plan.get("directive_id", "")}  \n**Deliverable** {t.get("deliverable", "")}  \n'
            f'**Services** {svc}  \n**Test type** {t["test_type"]}  \n**Lane** {t["lane"]}  \n'
            f'**Needs cloud agent** {"yes" if t.get("needs_cloud") else "no"}\n\n'
            "**Acceptance**\n" + "\n".join(f"- {a}" for a in t.get("acceptance") or []) + "\n"
            + (f'\n**Why this owner** {t["assign_reason"]}\n' if t.get("assign_reason") else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--repo", default=os.environ.get("PXQ_REPO", "SamsonIdowu/PXQ-Autopilot"))
    ap.add_argument("--project", default=os.environ.get("PXQ_PROJECT", ""))
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    people = seated()

    have = {l["name"] for l in json.loads(gh("label", "list", "--repo", a.repo, "--limit", "200", "--json", "name"))}
    want = dict(LABELS)
    for t in plan["tickets"]:
        want.setdefault(f'type:{t["test_type"]}', ("bfdadc", "Test type"))
        want.setdefault(f'lane:{t["lane"]}', ("d4c5f9", "Lane"))
    for name, (color, desc) in want.items():
        if name not in have:
            gh("label", "create", name, "--repo", a.repo, "--color", color, "--description", desc, "--force", check=False)

    existing = "\n".join(i["body"] for i in json.loads(gh(
        "issue", "list", "--repo", a.repo, "--label", "pxq:ticket", "--state", "all", "--limit", "1000", "--json", "body")))
    out = []
    for t in plan["tickets"]:
        if f'"key": "{t["key"]}"' in existing:
            print(f'skip {t["key"]}, already open', file=sys.stderr)
            continue
        labels = ["pxq:ticket", f'type:{t["test_type"]}', f'lane:{t["lane"]}'] + (["needs:cloud"] if t.get("needs_cloud") else [])
        args = ["issue", "create", "--repo", a.repo, "--title", f'{", ".join(t.get("services") or [])} · {t["title"]}',
                "--body", body_for(t, plan)]
        for l in labels:
            args += ["--label", l]
        who = people.get(str(t.get("assignee") or "").lower())
        if who:
            args += ["--assignee", who]  # the assigned event starts it on their agent
        url = gh(*args).strip()
        num = int(url.rstrip("/").rsplit("/", 1)[1])
        row = {"key": t["key"], "number": num, "url": url, "assignee": who or ""}
        if a.project:
            owner = a.repo.split("/")[0]
            r = subprocess.run(["gh", "project", "item-add", str(a.project), "--owner", owner, "--url", url], capture_output=True, text=True)
            row["project"] = r.returncode == 0
        out.append(row)
        print(f'{t["key"]} -> {url}{" (" + who + ")" if who else ""}', file=sys.stderr)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
