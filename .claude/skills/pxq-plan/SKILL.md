---
name: pxq-plan
description: Plan a CEO directive into PXQ tickets and, after the person approves, open them as GitHub issues. Use when someone says "plan this" or pastes a CEO directive.
---

# Plan a directive

1. Ask the `pxq-planner` agent to plan the directive. Give it the full text and the directive ID, `DIR-<date>-<short-name>`.
2. Show the person the plan summary, the ticket table (title, services, test type, lane, needs cloud) and the open questions.
3. Wait for an explicit approval. Apply any edits they ask for, then show the changed tickets again.
4. Only after approval, save the approved plan to `plans/<directive-id>.json`. You can't open issues yourself. The guard hook blocks it so a person is always the one who does.
5. Give the person this exact command to run as themselves, in their terminal or in Claude Code with a leading `!`.
   `scripts/owner/pxq.sh open-issues plans/<directive-id>.json`
   It opens one issue per ticket with the `pxq:ticket` label, skips tickets that already exist, and prints the links.
6. Tell them the assign workflow picks owners within a minute or two and starts each ticket on the owner's cloud agent.

Never open issues before approval, and never assign people yourself.
