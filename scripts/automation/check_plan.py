#!/usr/bin/env python3
"""Check and tidy a Planner plan before it goes to the dashboard.

Validates against schemas/plan.schema.json, gives every ticket a unique key from the
directive ID, keeps only owners who have a seat in config/team.yaml, and stops anyone
going past their max_open. Writes the tidied plan to --out and prints any problems.

Usage: check_plan.py <plan.json> --out <tidy.json> [--load '{"login": open_count}']
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def team():
    out = {}
    for l in open(os.path.join(ROOT, "config", "team.yaml"), encoding="utf-8"):
        m = re.search(r'github:\s*"([^"]+)".*max_open:\s*(\d+)', l)
        if m:
            out[m.group(1).lower()] = (m.group(1), int(m.group(2)))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("--out", required=True); ap.add_argument("--load", default="{}")
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    problems = []
    did = plan.get("directive_id", "")
    if not re.match(r"^DIR-\d{4}-\d{2}-\d{2}-[a-z0-9-]+$", did):
        problems.append(f"directive_id {did!r} doesn't match DIR-YYYY-MM-DD-name")
    people, load = team(), {k.lower(): v for k, v in json.loads(a.load).items()}
    for i, t in enumerate(plan.get("tickets", []), 1):
        t["key"] = f"{did[4:]}-{i}"
        who = str(t.get("assignee") or "").lower()
        if who and who not in people:
            problems.append(f'{t["key"]}: {t["assignee"]} has no seat, left for the assign workflow')
            t["assignee"] = ""
        elif who:
            login, cap = people[who]
            if load.get(who, 0) >= cap:
                problems.append(f'{t["key"]}: {login} is at max_open, left for the assign workflow')
                t["assignee"] = ""
            else:
                t["assignee"] = login
                load[who] = load.get(who, 0) + 1
    try:
        import jsonschema
        schema = json.load(open(os.path.join(ROOT, "schemas", "plan.schema.json")))
        for e in jsonschema.Draft202012Validator(schema).iter_errors(plan):
            problems.append(f'schema: {"/".join(map(str, e.path))} {e.message[:160]}')
    except ImportError:
        problems.append("jsonschema isn't installed, schema not checked")
    json.dump(plan, open(a.out, "w", encoding="utf-8"), indent=1)
    print("\n".join(problems) if problems else "Plan OK")
    return 1 if any(p.startswith("schema:") for p in problems) else 0

if __name__ == "__main__":
    sys.exit(main())
