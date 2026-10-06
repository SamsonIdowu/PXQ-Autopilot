#!/usr/bin/env python3
"""Turn owner feedback files into agent metrics.

Usage:
  python3 scripts/learn/aggregate_feedback.py [--dir learning/feedback] [--since 7d] [--out learning/metrics/latest.json]
"""
import argparse, collections, datetime as dt, glob, json, os, sys

def parse_since(s):
    if not s:
        return None
    n, unit = int(s[:-1]), s[-1]
    days = {"d": 1, "w": 7}[unit] * n
    return dt.date.today() - dt.timedelta(days=days)

def load(dir_, since):
    out = []
    for path in sorted(glob.glob(os.path.join(dir_, "**", "*.json"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            fb = json.load(fh)
        d = fb.get("date")
        if since and d and dt.date.fromisoformat(d) < since:
            continue
        fb["_path"] = path
        out.append(fb)
    return out

def ratio(a, b):
    return round(a / b, 3) if b else None

def aggregate(items):
    groups = collections.defaultdict(lambda: {"tickets": 0, "findings": 0, "tags": collections.Counter(),
                                              "sev_checked": 0, "sev_agree": 0, "missed": 0,
                                              "fp_reasons": collections.Counter(), "reviewer_pass": 0, "reviewer_pass_kept": 0})
    for fb in items:
        key = (fb.get("test_type", "unknown"), (fb.get("agent_versions") or {}).get("skill", "unknown"))
        g = groups[key]
        g["tickets"] += 1
        g["missed"] += len(fb.get("missed", []))
        passed = fb.get("reviewer_verdict") in ("pass", "fix-presentation")
        for f in fb.get("findings", []):
            g["findings"] += 1
            g["tags"][f["tag"]] += 1
            if f["tag"] in ("confirmed", "wrong-severity"):
                g["sev_checked"] += 1
                if f["tag"] == "confirmed":
                    g["sev_agree"] += 1
            if f["tag"] == "false-positive":
                g["fp_reasons"][(f.get("reason") or "no reason given").strip()] += 1
            if passed:
                g["reviewer_pass"] += 1
                if f["tag"] != "false-positive":
                    g["reviewer_pass_kept"] += 1
    rows = []
    for (test_type, skill), g in sorted(groups.items()):
        real = g["tags"]["confirmed"] + g["tags"]["wrong-severity"] + g["tags"]["unclear"]
        rows.append({
            "test_type": test_type, "skill": skill, "tickets": g["tickets"], "findings": g["findings"],
            "tags": dict(g["tags"]),
            "precision": ratio(real, g["findings"]),
            "false_positive_rate": ratio(g["tags"]["false-positive"], g["findings"]),
            "severity_agreement": ratio(g["sev_agree"], g["sev_checked"]),
            "recall_estimate": ratio(real, real + g["missed"]),
            "reviewer_agreement": ratio(g["reviewer_pass_kept"], g["reviewer_pass"]),
            "missed": g["missed"],
            "top_false_positive_reasons": g["fp_reasons"].most_common(5),
        })
    total_f = sum(r["findings"] for r in rows)
    total_real = sum(r["tags"].get("confirmed", 0) + r["tags"].get("wrong-severity", 0) + r["tags"].get("unclear", 0) for r in rows)
    total_missed = sum(r["missed"] for r in rows)
    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "tickets": len(items),
        "overall": {"findings": total_f, "precision": ratio(total_real, total_f),
                    "recall_estimate": ratio(total_real, total_real + total_missed)},
        "by_test_type": rows,
        "patterns": [
            {"test_type": r["test_type"], "reason": reason, "count": n}
            for r in rows for reason, n in r["top_false_positive_reasons"] if n >= 2
        ],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="learning/feedback")
    ap.add_argument("--since", default=None)
    ap.add_argument("--out", default="learning/metrics/latest.json")
    a = ap.parse_args()
    items = load(a.dir, parse_since(a.since))
    result = aggregate(items)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    o = result["overall"]
    print(f"{result['tickets']} tickets, {o['findings']} findings, precision {o['precision']}, recall estimate {o['recall_estimate']}")
    for p in result["patterns"]:
        print(f"pattern: {p['test_type']} · {p['reason']} · {p['count']} times")
    return 0

if __name__ == "__main__":
    sys.exit(main())
