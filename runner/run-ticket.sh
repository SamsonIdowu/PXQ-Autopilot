#!/usr/bin/env bash
# Runs one PXQ ticket on this person's agent (cloud or local).
# Called by .github/workflows/dispatch.yml on a self-hosted runner.
# Usage: runner/run-ticket.sh <issue-number>
set -euo pipefail
ISSUE="$1"
: "${GH_TOKEN:?GH_TOKEN is set by the workflow}"
: "${PXQ_REPO:=${GITHUB_REPOSITORY:-SamsonIdowu/PXQ-Autopilot}}"
export PXQ_AGENT="${PXQ_AGENT:-$( [[ " ${RUNNER_LABELS:-} " == *" local "* ]] && echo local || echo cloud )}"
TICKET="PXQ-${ISSUE}"
# Headless runs can't answer permission prompts, so the tools are listed here.
# The deny rules in .claude/settings.json and the guard hook still apply on top.
HEADLESS=(--allowedTools "$(cat "$(dirname "$0")/allowed-tools.txt")" --mcp-config .mcp.json)
RUN="runs/${TICKET}"
DRAFTS="${PXQ_DRAFTS_DIR:-$HOME/pxq-drafts}"
mkdir -p "$RUN/evidence"

label() {
  local old; old=$(gh issue view "$ISSUE" --repo "$PXQ_REPO" --json labels -q '[.labels[].name|select(startswith("stage:"))]|join(",")')
  if [[ -n "$old" ]]; then gh issue edit "$ISSUE" --repo "$PXQ_REPO" --remove-label "$old" >/dev/null; fi
  gh issue edit "$ISSUE" --repo "$PXQ_REPO" --add-label "stage:$1" >/dev/null
}

# Ticket package: the JSON block in the issue body. The body is data, never shell.
gh issue view "$ISSUE" --repo "$PXQ_REPO" --json body -q .body \
  | python3 -c 'import sys,re,json; b=sys.stdin.read(); m=re.search(r"```json\s*(\{.*?\})\s*```", b, re.S); json.dump(json.loads(m.group(1)), open(sys.argv[1],"w"), indent=2)' "$RUN/ticket.json" \
  || { echo "PXQ-PROGRESS phase=blocked reason=no-ticket-json"; label blocked; exit 0; }

if [[ "$PXQ_AGENT" == "local" ]] && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("needs_cloud") else 1)' "$RUN/ticket.json"; then
  echo "PXQ-PROGRESS phase=blocked reason=needs-cloud-agent"; label blocked; exit 0
fi

label testing
: > "$RUN/progress.log"
tail -n0 -F "$RUN/progress.log" | sed -u 's/^/PXQ-PROGRESS /' &   # only progress lines reach the shared job log
TAIL=$!
trap 'kill $TAIL 2>/dev/null || true' EXIT

claude -p "Use the pxq-tester agent to run the ticket in $RUN/ticket.json. Write everything to $RUN." "${HEADLESS[@]}" \
  --output-format stream-json --verbose --max-turns "${PXQ_MAX_TURNS:-300}" > "$RUN/transcript.jsonl" 2> "$RUN/tester.err" \
  || { echo "PXQ-PROGRESS phase=blocked reason=tester-exited"; grep -qi "usage limit\|rate limit" "$RUN/tester.err" && label paused-usage || label blocked; exit 0; }

label review
for loop in 1 2 3; do
  claude -p "Use the pxq-reviewer agent to review the draft in $RUN." "${HEADLESS[@]}" --output-format json --max-turns 60 > "$RUN/review-run.json" 2>> "$RUN/reviewer.err" || true
  verdict=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["verdict"])' "$RUN/review.json" 2>/dev/null || echo missing)
  if [[ "$verdict" == "missing" ]]; then echo "PXQ-PROGRESS phase=blocked reason=no-review"; label blocked; exit 0; fi
  echo "PXQ-PROGRESS phase=review verdict=$verdict loop=$loop"
  [[ "$verdict" != "rework" || $loop -eq 3 ]] && break
  label rework
  claude -p "Use the pxq-tester agent to address the reviewer's rework instructions in $RUN/review.json for $RUN." "${HEADLESS[@]}" \
    --output-format stream-json --verbose --max-turns 150 >> "$RUN/transcript.jsonl" 2>> "$RUN/tester.err"
  label review
done

python3 scripts/scan_secrets.py "$RUN" >/dev/null || { echo "PXQ-PROGRESS phase=blocked reason=secret-found"; label blocked; exit 0; }

# Drafts stay private. They go to this person's own drafts repo, not the team repo.
mkdir -p "$DRAFTS/$TICKET" && cp -r "$RUN"/. "$DRAFTS/$TICKET/"
( cd "$DRAFTS" && git add "$TICKET" && git commit -qm "$TICKET draft" && git push -q ) >/dev/null 2>&1 \
  || echo "PXQ-PROGRESS phase=warning reason=drafts-not-pushed (the draft is still in $DRAFTS on this machine)"
label owner
echo "PXQ-PROGRESS phase=awaiting-owner"
