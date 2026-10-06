#!/usr/bin/env bash
# The few GitHub actions a person takes themselves. Agents are blocked from these on purpose,
# so every ticket that gets opened and every report that gets approved has a person behind it.
#
# Run it in your own terminal, or in Claude Code with a leading "!" so it runs as you.
#
#   scripts/owner/pxq.sh open-issues plans/DIR-2026-10-06-eq-focus.json
#   scripts/owner/pxq.sh approve  <issue> <feedback.json> <report-artifact-url>
#   scripts/owner/pxq.sh changes  <issue> "<what to change>"
#   scripts/owner/pxq.sh rerun    <issue> [cloud|local]
set -euo pipefail
REPO="${PXQ_REPO:-SamsonIdowu/PXQ-Autopilot}"
cmd="${1:-}"; shift || true

stage() {  # swap the stage:* label
  local issue="$1" new="$2" old
  old=$(gh issue view "$issue" --repo "$REPO" --json labels -q '[.labels[].name|select(startswith("stage:"))]|join(",")')
  [[ -n "$old" ]] && gh issue edit "$issue" --repo "$REPO" --remove-label "$old" >/dev/null
  gh issue edit "$issue" --repo "$REPO" --add-label "stage:$new" >/dev/null
}

case "$cmd" in
  open-issues)
    plan="${1:?path to plans/<directive>.json}"
    python3 - "$plan" "$REPO" <<'PY'
import json, subprocess, sys
plan, repo = json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]
existing = "\n".join(i["body"] for i in json.loads(subprocess.run(
    ["gh", "issue", "list", "--repo", repo, "--label", "pxq:ticket", "--state", "all", "--limit", "1000", "--json", "body"],
    capture_output=True, text=True, check=True).stdout))
made = 0
for t in plan["tickets"]:
    marker = f'"key": "{t["key"]}"'
    if marker in existing:
        print(f'skip {t["key"]} (already open)'); continue
    svc = ", ".join(t["services"])
    title = f'{svc} · {t["title"]}'
    body = ("```json\n" + json.dumps(t, indent=2) + "\n```\n\n"
            f'**Directive** {plan.get("directive_id", "")}  \n**Deliverable** {t["deliverable"]}  \n'
            f'**Services** {svc}  \n**Test type** {t["test_type"]}  \n**Lane** {t["lane"]}  \n'
            f'**Needs cloud agent** {"yes" if t["needs_cloud"] else "no"}\n\n'
            "**Acceptance**\n" + "\n".join(f"- {a}" for a in t["acceptance"]) + "\n")
    labels = ["pxq:ticket", f'type:{t["test_type"]}', f'lane:{t["lane"]}'] + (["needs:cloud"] if t["needs_cloud"] else [])
    args = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for l in labels: args += ["--label", l]
    url = subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()
    print(f'{t["key"]} -> {url}'); made += 1
print(f"Opened {made} issue(s). The assign workflow picks owners within a minute or two.")
PY
    ;;
  approve)
    issue="${1:?issue number}"; fb="${2:?feedback.json}"; url="${3:?final report artifact URL}"
    python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$fb"
    { echo "Approved by @$(gh api user -q .login). Final report: $url"; echo; echo "<!-- pxq-feedback -->"
      echo '```json'; cat "$fb"; echo; echo '```'; } | gh issue comment "$issue" --repo "$REPO" --body-file -
    stage "$issue" approved
    gh issue close "$issue" --repo "$REPO" --reason completed >/dev/null
    echo "PXQ-$issue approved and closed. Feedback saved on the ticket for the weekly learning run."
    ;;
  changes)
    issue="${1:?issue number}"; note="${2:?what to change}"
    gh issue comment "$issue" --repo "$REPO" --body "Changes requested by the owner. $note"
    stage "$issue" changes
    "$0" rerun "$issue"
    ;;
  rerun)
    issue="${1:?issue number}"; agent="${2:-cloud}"
    owner=$(gh issue view "$issue" --repo "$REPO" --json assignees -q '.assignees[0].login')
    gh workflow run dispatch.yml --repo "$REPO" -f issue="$issue" -f owner="$owner" -f agent="$agent"
    echo "PXQ-$issue sent to $owner's $agent agent."
    ;;
  *)
    sed -n '2,12p' "$0"; exit 1 ;;
esac
