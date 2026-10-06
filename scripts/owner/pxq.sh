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
#
# Admin only. The dashboard's Team page gives you these with the values filled in.
#   scripts/owner/pxq.sh add-member <seat> --name "Full Name" --github <login> --primary <lane> --backup <lane> --max <n>
#   scripts/owner/pxq.sh remove-member <seat>
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
    root="$(cd "$(dirname "$0")/../.." && pwd)"
    python3 - "$plan" "$REPO" "$root/config/team.yaml" <<'PY'
import json, re, subprocess, sys
plan, repo = json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]
seated = {m.group(1).lower(): m.group(1) for l in open(sys.argv[3], encoding="utf-8") if (m := re.search(r'github:\s*"([^"]+)"', l))}
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
            "**Acceptance**\n" + "\n".join(f"- {a}" for a in t["acceptance"]) + "\n"
            + (f'\n**Why this owner** {t["assign_reason"]}\n' if t.get("assign_reason") else ""))
    labels = ["pxq:ticket", f'type:{t["test_type"]}', f'lane:{t["lane"]}'] + (["needs:cloud"] if t["needs_cloud"] else [])
    args = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for l in labels: args += ["--label", l]
    who = seated.get(str(t.get("assignee") or "").lower())
    if who:
        args += ["--assignee", who]   # the assigned event starts it on their agent
    elif t.get("assignee"):
        print(f'{t["key"]}: {t["assignee"]} has no seat in team.yaml, so the assign workflow will pick an owner')
    url = subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()
    print(f'{t["key"]} -> {url}'); made += 1
print(f"Opened {made} issue(s). Tickets with an owner start on their agent now. The assign workflow picks owners for the rest.")
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
  add-member|remove-member)
    seat="${1:?seat key}"; shift
    root="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$root"
    [[ -z "$(git status --porcelain)" ]] || { echo "Commit or stash your local changes first."; exit 1; }
    me=$(gh api user -q .login)
    git fetch -q origin
    branch="team/${cmd%%-member}-$seat"
    git switch -q -c "$branch" origin/main
    if [[ "$cmd" == "add-member" ]]; then
      python3 scripts/owner/team_yaml.py add "$seat" "$@" || { git switch -q -; git branch -q -D "$branch"; exit 1; }
      login=$(python3 scripts/owner/team_yaml.py github "$seat")
      title="Add $seat to the PXQ team"
      body="Invited by @$me from the dashboard Team page. Adds the seat to config/team.yaml so tickets can be assigned to @$login."
    else
      login=$(python3 scripts/owner/team_yaml.py github "$seat")
      python3 scripts/owner/team_yaml.py remove "$seat" || { git switch -q -; git branch -q -D "$branch"; exit 1; }
      title="Remove $seat from the PXQ team"
      body="Removed by @$me from the dashboard Team page. Open tickets assigned to @$login need a new owner."
    fi
    git add config/team.yaml
    git -c user.name="$(git config user.name || echo "$me")" commit -qm "$title"
    git push -q -u origin "$branch"
    gh pr create --repo "$REPO" --base main --head "$branch" --title "$title" --body "$body"
    git switch -q -
    if [[ "$cmd" == "add-member" ]]; then
      gh api -X PUT "repos/$REPO/collaborators/$login" -f permission=push >/dev/null \
        && echo "Invited @$login as a collaborator. They accept the invitation from GitHub." \
        || echo "Couldn't invite @$login as a collaborator. Do it in Settings > Collaborators."
      echo "Merge the pull request, then share the dashboard with them and send them docs/FIRST_RUN.md."
    else
      gh api -X DELETE "repos/$REPO/collaborators/$login" >/dev/null 2>&1 \
        && echo "Removed @$login as a collaborator." || echo "Check Settings > Collaborators for @$login."
      echo "Merge the pull request. Remove their runner in Settings > Actions > Runners and stop sharing the dashboard with them."
    fi
    ;;
  *)
    sed -n '2,16p' "$0"; exit 1 ;;
esac
