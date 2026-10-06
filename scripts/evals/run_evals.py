#!/usr/bin/env python3
"""Run PXQ agent evals with headless Claude Code and score the results.

Each case is a JSON file in evals/<agent>/cases/. A case has an input folder
or text, the prompt to send, and checks to run on the agent's output.

Usage:
  python3 scripts/evals/run_evals.py --all
  python3 scripts/evals/run_evals.py --agent reviewer
  python3 scripts/evals/run_evals.py --all --dry-run     # validate cases only
"""
import argparse, glob, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_claude(prompt, max_turns):
    tools = open(os.path.join(ROOT, "runner", "allowed-tools.txt"), encoding="utf-8").read().strip()
    cmd = ["claude", "-p", prompt, "--allowedTools", tools, "--mcp-config", ".mcp.json",
           "--output-format", "json", "--max-turns", str(max_turns)]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:500])
    data = json.loads(out.stdout)
    return data.get("result", "")

def read_json(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return json.load(fh)

def check(case, result_text):
    failures = []
    for c in case["checks"]:
        kind = c["type"]
        if kind == "file_json_equals":
            try:
                val = read_json(c["file"])
                for k in filter(None, c["path"].split(".")):
                    val = val[int(k)] if isinstance(val, list) else val[k]
            except Exception as e:
                failures.append(f"{c['file']} {c['path']} unreadable ({e})")
                continue
            if val != c["equals"]:
                failures.append(f"{c['path']} was {val!r}, expected {c['equals']!r}")
        elif kind == "file_json_count":
            try:
                val = read_json(c["file"])
                for k in filter(None, c["path"].split(".")):
                    val = val[k]
                n = len(val)
            except Exception as e:
                failures.append(f"{c['file']} {c['path']} unreadable ({e})")
                continue
            if not (c.get("min", 0) <= n <= c.get("max", 10**9)):
                failures.append(f"{c['path']} had {n} items, expected {c.get('min', 0)} to {c.get('max', 'any')}")
        elif kind == "text_contains":
            if c["value"].lower() not in result_text.lower():
                failures.append(f"output didn't mention {c['value']!r}")
        elif kind == "text_excludes":
            if c["value"].lower() in result_text.lower():
                failures.append(f"output mentioned {c['value']!r}")
        else:
            failures.append(f"unknown check type {kind}")
    return failures

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["planner", "tester", "reviewer"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    agents = ["planner", "tester", "reviewer"] if a.all or not a.agent else [a.agent]
    total = passed = 0
    for agent in agents:
        for path in sorted(glob.glob(os.path.join(ROOT, "evals", agent, "cases", "*.json"))):
            case = json.load(open(path, encoding="utf-8"))
            total += 1
            name = f"{agent}/{os.path.basename(path)}"
            if a.dry_run:
                missing = [k for k in ("prompt", "checks") if k not in case]
                print(f"{'ok ' if not missing else 'BAD'} {name}" + (f" missing {missing}" if missing else ""))
                passed += 0 if missing else 1
                continue
            try:
                text = run_claude(case["prompt"], case.get("max_turns", 40))
                fails = check(case, text)
            except Exception as e:
                fails = [f"run failed: {e}"]
            if fails:
                print(f"FAIL {name}")
                for f in fails:
                    print(f"     {f}")
            else:
                passed += 1
                print(f"pass {name}")
    print(f"{passed}/{total} passed")
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
