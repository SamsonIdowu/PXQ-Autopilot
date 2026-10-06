#!/usr/bin/env python3
"""Work out which dashboard documents a sync needs to write.

Reads the dashboard-data branch checkout (snapshot.json and reports/<issue>.md) and what
the dashboard already holds, then writes small JSON files and prints the ArtifactData
batch entries to send. Report documents are keyed <issue>-<hash>, so a changed report
is a new document and never needs a version pin.

Usage: prepare_sync.py --data /tmp/pxq-data --have-snapshot-hash <hash or ""> --have-reports <dir of existing report docs> --out /tmp/sync
"""
import argparse, datetime as dt, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--have-snapshot-hash", default="")
    ap.add_argument("--have-reports", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    snap_path = os.path.join(a.data, "snapshot.json")
    snap = json.load(open(snap_path, encoding="utf-8"))
    if os.path.getsize(snap_path) > 250_000:
        sys.exit("Snapshot too large for the dashboard")
    have = set()
    if a.have_reports and os.path.isdir(a.have_reports):
        have = {f[:-5] for f in os.listdir(a.have_reports) if f.endswith(".json")}
    writes = []
    changed = snap["hash"] != a.have_snapshot_hash
    if changed:
        writes.append({"op": "set", "collection": "board", "doc_id": "snapshot", "file_path": snap_path, "pin": "snapshot"})
    for t in snap.get("tickets", []):
        r = t.get("report")
        md = os.path.join(a.data, "reports", f'{t["n"]}.md')
        if not r or not os.path.exists(md):
            continue
        doc_id = f'{t["n"]}-{r["hash"]}'
        if doc_id in have:
            continue
        f = os.path.join(a.out, f"report-{doc_id}.json")
        json.dump({"md": open(md, encoding="utf-8").read()[:200_000], "hash": r["hash"], "issue": t["n"]}, open(f, "w", encoding="utf-8"))
        writes.append({"op": "set", "collection": "reports", "doc_id": doc_id, "file_path": f})
    hb = os.path.join(a.out, "heartbeat.json")
    json.dump({"checked_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "hash": snap["hash"],
               "generated_at": snap.get("generated_at"), "changed": changed}, open(hb, "w"))
    writes.append({"op": "set", "collection": "board", "doc_id": "heartbeat", "file_path": hb, "pin": "heartbeat"})
    json.dump(writes, open(os.path.join(a.out, "writes.json"), "w"), indent=1)
    print(json.dumps({"snapshot_changed": changed, "new_reports": sum(1 for w in writes if w["collection"] == "reports"), "writes": len(writes)}))

if __name__ == "__main__":
    main()
