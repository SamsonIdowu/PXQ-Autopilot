# PXQ Autopilot

Agents, skills, hooks and workflows for Wazuh's Product Experience and Quality team.

**New here?** Start with [docs/FIRST_RUN.md](docs/FIRST_RUN.md). It walks through setup and the first ticket.

## How a ticket moves

1. A person pastes a directive into Claude Code and says "plan this". The Planner writes `plans/<directive>.json`.
2. The person approves it and runs `scripts/owner/pxq.sh open-issues plans/<directive>.json`.
3. The `assign` workflow picks an owner by lane and load and starts the ticket on their cloud agent.
4. If no cloud agent picks it up in 10 minutes, `fallback` moves it to the owner's local agent. Tickets marked `needs:cloud` wait instead.
5. On the owner's runner, the Tester runs it in their Claude account, then the Reviewer checks it. Only progress lines reach the shared job log. Drafts go to the owner's private `pxq-drafts` repo.
6. The owner says "review PXQ-###" in Claude Code, tags each finding and approves. The final report goes to the channel. The owner's approve command saves the tags on the ticket.
7. Every Monday, `learn` turns those tags into proposed lessons and eval cases as a pull request for a person to merge.

## The three agents

| Agent | File | Job | Runs in |
|---|---|---|---|
| Planner | `.claude/agents/pxq-planner.md` | Turns a CEO directive into deliverables and tickets | The submitter's Claude chat or Claude Code |
| Tester | `.claude/agents/pxq-tester.md` | Runs one ticket in a fresh environment, reproduces findings twice, writes a draft | The owner's cloud agent, or their local agent as a fallback |
| Reviewer | `.claude/agents/pxq-reviewer.md` | Checks the draft in a fresh session, fixes presentation, sends weak findings back | The owner's agent, right after the Tester |

The Tester picks a skill by test type.

| Test type | Skill |
|---|---|
| install | `test-install` |
| detection, fp-audit | `test-detection` |
| web-journey | `test-web-journey` |
| api-security | `test-api-security` |
| docs | `test-docs` |

## Shared skills

- `pxq-findings` holds the finding format, types and severity matrix.
- `pxq-report` holds the report template and naming rule, `PXQ-### · <Wazuh services> · <what was tested>`.
- `pxq-plan` plans a directive and opens issues after approval.
- `pxq-review` lets the owner review, tag findings and share.
- `pxq-learn` is the weekly learning run.

## Folders

| Path | What's in it |
|---|---|
| `.claude/` | Agents, skills, the guard hook and permission rules |
| `config/` | Team seats, allowed networks, Wazuh service names, environment templates |
| `schemas/` | Contracts for plans, findings, reviews and feedback |
| `learning/` | Lessons per agent, owner feedback, metrics |
| `evals/` | Test cases that keep agents from repeating past mistakes |
| `runner/` | The script each person's agent runs for a ticket |
| `.github/workflows/` | `assign` (pick owner), `dispatch` (run tickets), `fallback` (cloud to local), `learn` (weekly), `validate` (checks on every pull request) |
| `scripts/owner/pxq.sh` | The GitHub actions only a person takes. Open issues, approve, request changes, rerun. |
| `scripts/setup/` | `labels.sh` for the admin, `doctor.sh` for every agent machine |
| `docs/FIRST_RUN.md` | Setup and the first ticket, step by step |

## Two ways to install

1. **From the repo (the source).** Clone it on your agent machine. Claude Code picks up `.claude/` automatically when you run it in the repo folder.
2. **As a plugin.** Run `scripts/plugin/build.sh` to build `plugin/`. Then, in Claude Code, run `/plugin marketplace add SamsonIdowu/PXQ-Autopilot` and `/plugin install pxq-agents@wazuh-pxq`. The plugin is a packaged copy. Changes always start in the repo.

## Try it

```bash
python3 scripts/learn/aggregate_feedback.py --dir learning/feedback/examples   # metrics from sample feedback
python3 scripts/evals/run_evals.py --all --dry-run                            # check eval cases
python3 tests/test_guard.py                                                   # guard hook blocks and allows the right commands
scripts/setup/doctor.sh local                                                 # is this machine ready to run tickets?
```

## Admin runner

The weekly learning run needs one runner with the extra label `pxq-admin`. This is normally the admin's cloud agent.
