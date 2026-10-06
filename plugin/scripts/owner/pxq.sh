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
    plan="${1:?path to the plan .json}"
    root="$(cd "$(dirname "$0")/../.." && pwd)"
    PXQ_REPO="$REPO" python3 "$root/scripts/automation/open_plan.py" "$plan" >/dev/null
    echo "Done. Tickets with an owner start on their agent now. The assign workflow picks owners for the rest."
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
