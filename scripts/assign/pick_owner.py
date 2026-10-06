#!/usr/bin/env python3
"""Pick the owner for a PXQ ticket by lane, then load.

Order of preference:
  1. People whose primary lane is the ticket's lane.
  2. People whose backup lane is the ticket's lane.
  3. Anyone else on the team.
Within each group the person with the fewest open tickets wins. People already
at max_open are skipped. Prints the chosen GitHub login, or nothing if nobody
has room.

Usage:
  pick_owner.py --ticket ticket.json --team config/team.yaml --load '{"SamsonIdowu": 2}'
"""
import argparse, json, sys
import yaml

def pick(ticket, team, load):
    lane = ticket.get("lane")
    best = None
    for key, p in (team.get("people") or {}).items():
        login = (p.get("github") or "").strip()
        if not login:
            continue
        open_now = int(load.get(login, 0))
        if open_now >= int(p.get("max_open", 6)):
            continue
        rank = 0 if p.get("primary") == lane else 1 if p.get("backup") == lane else 2
        cand = (rank, open_now, login.lower(), login)
        if best is None or cand < best:
            best = cand
    return best[3] if best else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket", required=True)
    ap.add_argument("--team", default="config/team.yaml")
    ap.add_argument("--load", default="{}", help="JSON map of login to open ticket count")
    a = ap.parse_args()
    ticket = json.load(open(a.ticket, encoding="utf-8"))
    team = yaml.safe_load(open(a.team, encoding="utf-8"))
    print(pick(ticket, team, json.loads(a.load)))

if __name__ == "__main__":
    sys.exit(main())
