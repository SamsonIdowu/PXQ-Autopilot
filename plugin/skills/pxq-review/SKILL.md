---
name: pxq-review
description: Lets a ticket owner review their private draft report, tag each finding for agent learning, then approve and share the final report. Use when the owner says "review PXQ-###".
---

# Review my report

1. Confirm the person asking owns the ticket. Drafts are private to their owner.
2. Read `report.final.md`, `findings.json` and `review.json` from the owner's private drafts repo.
3. Show the report and ask the owner to tag every finding with one of these.
   - **confirmed** when it's real and correctly rated.
   - **false-positive** when it isn't a real problem. Ask for a one-line reason.
   - **wrong-severity**, along with the right severity.
   - **duplicate**, along with the existing issue link.
   - **unclear** when it's real but badly explained.
4. Ask whether the agents missed anything they noticed themselves. Each answer becomes a missed-issue record.
5. Write `feedback.json` against `schemas/feedback.schema.json` next to the draft in the owner's drafts folder. Include finding types, tags and reasons. Don't include draft evidence. The owner's approve command attaches it to the ticket, and the weekly learning run collects it from there.
6. Act on the owner's decision.
   - **Approve.** Remove findings tagged false-positive. Fix tagged severities. Publish the final report as a Claude artifact named per `pxq-report`. Show the owner the link and ask before posting. After a yes, post the link to the reports channel through the owner's Slack connection. Then give the owner this command to run as themselves.
     `scripts/owner/pxq.sh approve <issue> <path to feedback.json> <artifact link>`
     It saves the feedback on the ticket, sets `stage:approved` and closes it.
   - **Request changes.** Give the owner this command to run.
     `scripts/owner/pxq.sh changes <issue> "<their note>"`
     It records the note, sets `stage:changes` and sends the ticket back to the Tester.

You can't change labels, comment on issues or close them yourself. The guard hook blocks it so the owner's sign-off is always a person's action.
