#!/usr/bin/env python3
"""Add or remove a seat in config/team.yaml, keeping the file's one-line-per-person format.

Used by scripts/owner/pxq.sh add-member and remove-member. Validates every value so a
name or login can never inject anything into the file.

Usage:
  team_yaml.py add <key> --name "Full Name" --github <login> --primary <lane> --backup <lane> --max <n>
  team_yaml.py remove <key>
  team_yaml.py github <key>          # prints the seat's GitHub login
"""
import argparse, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.environ.get("PXQ_TEAM_FILE", os.path.join(ROOT, "config", "team.yaml"))
LANES = {"learn-discover", "buy-onboard", "use-operate"}
KEY = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
NAME = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{0,60}$")
LINE = re.compile(r"^\s+([a-z0-9_-]+):\s*\{.*\}\s*$")

def seats(lines):
    return {m.group(1): i for i, l in enumerate(lines) if (m := LINE.match(l))}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["add", "remove", "github"])
    ap.add_argument("key")
    ap.add_argument("--name"); ap.add_argument("--github"); ap.add_argument("--primary")
    ap.add_argument("--backup"); ap.add_argument("--max", type=int, default=6)
    a = ap.parse_args()
    if not KEY.match(a.key):
        sys.exit(f"Seat key '{a.key}' must be lowercase letters, digits or hyphens.")
    lines = open(PATH, encoding="utf-8").read().splitlines()
    have = seats(lines)
    admin = next((l.split(":", 1)[1].strip() for l in lines if l.startswith("admin:")), "")

    if a.action == "github":
        if a.key not in have:
            sys.exit(f"No seat '{a.key}' in team.yaml.")
        m = re.search(r'github:\s*"([^"]*)"', lines[have[a.key]])
        print(m.group(1) if m else "")
        return

    if a.action == "remove":
        if a.key == admin:
            sys.exit("The admin seat can't be removed.")
        if a.key not in have:
            sys.exit(f"No seat '{a.key}' in team.yaml.")
        del lines[have[a.key]]
    else:
        errs = []
        if a.key in have: errs.append(f"Seat '{a.key}' already exists.")
        if not a.name or not NAME.match(a.name): errs.append("Name may only use letters, spaces, dots, apostrophes and hyphens.")
        if not a.github or not LOGIN.match(a.github): errs.append("That isn't a valid GitHub login.")
        if a.primary not in LANES: errs.append(f"Primary lane must be one of {', '.join(sorted(LANES))}.")
        if a.backup not in LANES or a.backup == a.primary: errs.append("Backup lane must be a different lane.")
        if not 1 <= a.max <= 20: errs.append("Max open tickets must be between 1 and 20.")
        taken = {m.group(1).lower() for l in lines if (m := re.search(r'github:\s*"([^"]*)"', l))}
        if a.github and a.github.lower() in taken: errs.append(f"GitHub login {a.github} already has a seat.")
        if errs:
            sys.exit("\n".join(errs))
        lines.append(f'  {a.key}: {{ name: {a.name}, github: "{a.github}", primary: {a.primary}, backup: {a.backup}, max_open: {a.max} }}')
    open(PATH, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{a.action}ed seat {a.key}" if a.action == "add" else f"removed seat {a.key}")

if __name__ == "__main__":
    main()
