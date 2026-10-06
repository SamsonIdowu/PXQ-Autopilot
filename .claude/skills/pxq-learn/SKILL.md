---
name: pxq-learn
description: The weekly PXQ learning run. Turns owner feedback and outcomes into proposed lesson and playbook changes, adds eval cases, runs evals, and opens a pull request for people to approve. Use only from the learn workflow or when the admin asks.
---

# Weekly learning run

Agents don't retrain a model. They get better because their instructions, lessons, playbooks and examples get better. This run proposes those changes, and people approve them.

## 1. Measure

Run `python3 scripts/learn/aggregate_feedback.py --since 7d`. It writes `learning/metrics/latest.json` with the following, per agent, test type, skill and playbook version.

- Precision, meaning confirmed findings over all findings owners tagged.
- False-positive rate and its top reasons.
- Severity agreement between the agent and the owner.
- Missed issues, meaning things owners found that agents didn't.
- Reviewer agreement, meaning how often the owner kept what the Reviewer passed.

## 2. Find patterns

Look for repeats with two or more cases in the window. Examples.

- The same false-positive reason on the same rule or page.
- The same severity correction on the same finding type.
- The same kind of missed issue on the same journey.

## 3. Propose changes

For each pattern, propose the smallest change that would have prevented it.

- **A lesson** in `learning/lessons/<agent>.md`. One line, with the evidence tickets in brackets.
- **A playbook or skill step** in `.claude/skills/...`, when the fix is procedural.
- **An eval case** in `evals/<agent>/cases/`, built from the real ticket, so the mistake can't come back.

Retire lessons that haven't matched anything in 60 days, or that a newer lesson replaces.

## 4. Check

Run `python3 scripts/evals/run_evals.py --all`. Report pass counts before and after your changes. If anything that passed before now fails, drop the change that caused it.

## 5. Open a pull request

Write the pull request description to `learning/metrics/pr-body.md`. Include the metrics, every proposed change with its evidence tickets, and the eval results before and after. The learn workflow opens the pull request on a branch called `learn/<date>`.

## Never

- Never weaken a safety rule, hook, permission or the two-reproduction rule.
- Never edit `.claude/hooks/`, `.claude/settings.json` or `.github/`.
- Never merge your own pull request.
