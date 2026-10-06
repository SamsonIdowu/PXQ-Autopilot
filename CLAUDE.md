# PXQ Autopilot

This repo holds the agents, skills, guardrails and workflows for Wazuh's Product Experience and Quality team (PXQ). Claude Code reads this file at the start of every session in this folder.

## Who you're working for

You run inside one teammate's own Claude account, on their cloud agent or their own machine. The rough work stays with them. Only a final report the owner approves is ever shared with the team.

Samson Idowu is the admin. Everyone else joins when the admin invites them from the dashboard's Team page. Seats, lanes and GitHub logins are in `config/team.yaml`.

## The agents

| Agent | When to use it |
|---|---|
| `pxq-planner` | Someone pastes a directive or says "plan this" |
| `pxq-tester` | Running one ticket from `runs/<ticket>/ticket.json` |
| `pxq-reviewer` | Checking a Tester draft before the owner sees it |

Skills live in `.claude/skills/`. The Tester picks one by test type. `install` uses `test-install`. `detection` and `fp-audit` use `test-detection`. `web-journey` uses `test-web-journey`. `api-security` uses `test-api-security`. `docs` uses `test-docs`.

## Rules that don't bend

- Never create, edit, comment on, label or close GitHub issues or pull requests. Never push. Never call `gh api`. People do those with `scripts/owner/pxq.sh`, so a person is behind every ticket and every approval. The guard hook blocks these anyway.
- Never post to Slack from a test run. The owner shares the final report after they approve it.
- Only reach hosts in `config/networks.yaml`, plus the public Wazuh and package hosts the guard allows. Ask the person if you need another one.
- Use test accounts only. Never use real customer data, real payment cards or anyone's personal account.
- Reproduce every finding twice before you report it. One run is a note, not a finding.
- Don't edit `.claude/hooks/`, `.claude/settings.json`, `.mcp.json`, `runner/`, `config/networks.yaml` or `.github/`. Changes there go through a reviewed pull request.

## Where things are

| Path | What's in it |
|---|---|
| `config/` | Team seats, allowed networks, Wazuh service names, environment templates |
| `schemas/` | Plan, finding, review and feedback formats. Validate against them. |
| `learning/lessons/` | Lessons per agent. Read yours at the start of every run. |
| `evals/` | Cases that keep agents from repeating past mistakes |
| `plans/` | Approved plans waiting to become issues |
| `runs/` | One folder per ticket run. Ignored by git. |
| `runner/run-ticket.sh` | What the GitHub runner calls for each ticket |
| `docs/FIRST_RUN.md` | Setup and first ticket, step by step |

## Handy commands

```bash
scripts/setup/doctor.sh local                       # is this machine ready?
python3 tests/test_guard.py                         # guard hook still blocks what it should
python3 scripts/evals/run_evals.py --all --dry-run  # eval cases are well formed
python3 scripts/learn/aggregate_feedback.py --dir tests/fixtures/feedback --out /tmp/metrics.json
```
