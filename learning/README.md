# How the agents learn

The agents use Claude models as they are. Nobody retrains a model. The agents get better because what they read before every run gets better, and every improvement is checked and approved by a person.

## What the agents read

| Layer | Where | Who changes it |
|---|---|---|
| Role and rules | `.claude/agents/*.md` | People, through a reviewed pull request |
| How to test | `.claude/skills/*/SKILL.md` | People, or the learning run proposes it |
| Lessons | `learning/lessons/<agent>.md` | The learning run proposes them, and a teammate approves |
| Known issues | GitHub search at run time | Updated as issues are filed |
| Examples and evals | `evals/<agent>/cases/` | The learning run adds a case for every real mistake |

## Where the signals come from

1. **Owner feedback.** When owners review a report, they tag every finding as confirmed, false positive, wrong severity, duplicate or unclear, and they note anything the agents missed. The owner's approve command saves it on the ticket, and the weekly learning run copies it to `learning/feedback/<month>/<ticket>.json`. It holds tags and short reasons only, never draft evidence. Sample feedback for tests lives in `tests/fixtures/feedback/`, so it never counts toward real metrics.
2. **Reviewer decisions.** These are rework requests and removed findings.
3. **Outcomes upstream.** These are accepted, won't fix, and fixed and verified.
4. **Canaries.** Known-good installs should pass. Any finding on them is probably a false positive.

## The weekly loop

```
owner feedback ─┐
reviewer data  ─┼─> measure ─> find patterns ─> propose lessons, skill edits, eval cases ─> run evals ─> pull request ─> teammate approves ─> agents use it next run
upstream data  ─┘
```

1. **Measure.** `aggregate_feedback.py` works out precision, false-positive rate, severity agreement, missed issues and reviewer agreement. It splits them by test type and skill version.
2. **Find patterns.** The same mistake twice or more in a week becomes a candidate lesson.
3. **Propose.** The smallest change that would have prevented it, plus an eval case built from the real ticket.
4. **Check.** Evals run before and after. A change that breaks a passing case is dropped.
5. **Approve.** A teammate reviews the pull request. Changes to hooks, permissions or workflows aren't allowed in learning pull requests at all.

## Guardrails

- Lessons can't weaken safety rules, hooks, permissions or the two-reproduction rule.
- Every lesson cites the tickets behind it, so anyone can check why it exists.
- Lessons that haven't mattered for 60 days are retired, so the files stay short.
- Agent precision and recall go into the monthly KPI scorecard (handbook K04 and K05).
