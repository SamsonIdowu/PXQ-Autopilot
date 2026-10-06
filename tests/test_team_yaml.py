#!/usr/bin/env python3
"""Checks add-member and remove-member edits to team.yaml, on a temporary copy."""
import os, shutil, subprocess, sys, tempfile
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = os.path.join(tempfile.mkdtemp(), "team.yaml")
shutil.copy(os.path.join(ROOT, "config", "team.yaml"), tmp)
env = dict(os.environ, PXQ_TEAM_FILE=tmp)
run = lambda *a: subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "owner", "team_yaml.py"), *a], env=env, capture_output=True, text=True)
people = lambda: yaml.safe_load(open(tmp))["people"]
checks = []
r = run("add", "ana", "--name", "Ana O'Neil", "--github", "ana-o", "--primary", "buy-onboard", "--backup", "use-operate", "--max", "4")
checks.append(("add works", r.returncode == 0 and people()["ana"]["github"] == "ana-o" and people()["ana"]["max_open"] == 4))
checks.append(("near-duplicate login allowed", run("add", "ana2", "--name", "Ana Two", "--github", "ana", "--primary", "buy-onboard", "--backup", "use-operate").returncode == 0))
checks.append(("exact duplicate login refused", run("add", "ana3", "--name", "Ana Three", "--github", "ANA-O", "--primary", "buy-onboard", "--backup", "use-operate").returncode != 0))
checks.append(("injection refused", run("add", "bad", "--name", 'x"; rm -rf /', "--github", "a;b", "--primary", "buy-onboard", "--backup", "use-operate").returncode != 0))
checks.append(("same lanes refused", run("add", "cara", "--name", "Cara", "--github", "cara", "--primary", "buy-onboard", "--backup", "buy-onboard").returncode != 0))
checks.append(("admin can't be removed", run("remove", yaml.safe_load(open(tmp))["admin"]).returncode != 0))
checks.append(("remove works", run("remove", "ana").returncode == 0 and "ana" not in people()))
checks.append(("file still valid YAML", isinstance(people(), dict)))
fails = 0
for name, ok in checks:
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name)
print(f"{len(checks) - fails}/{len(checks)} passed")
sys.exit(1 if fails else 0)
