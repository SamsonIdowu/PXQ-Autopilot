#!/usr/bin/env bash
# Creates or updates every label the PXQ workflows use. Safe to run again.
# Admin runs it once after the repo is set up:  scripts/setup/labels.sh
set -euo pipefail
REPO="${PXQ_REPO:-SamsonIdowu/PXQ-Autopilot}"
mk() { gh label create "$1" --repo "$REPO" --color "$2" --description "$3" --force >/dev/null && echo "  $1"; }
echo "Labels on $REPO"
mk "pxq:ticket"         5319e7 "A PXQ test ticket. Starts auto-assignment."
mk "needs:cloud"        0e8a16 "Needs the cloud agent. Never falls back to a local agent."
mk "learning"           c5def5 "Weekly learning proposal"
mk "stage:assigned"     ededed "Owner picked. Waiting for their agent."
mk "stage:testing"      1d76db "Tester is running"
mk "stage:review"       0052cc "Reviewer is checking the draft"
mk "stage:rework"       fbca04 "Reviewer sent findings back to the Tester"
mk "stage:owner"        d93f0b "Draft ready. Waiting for the owner's review."
mk "stage:changes"      fbca04 "Owner asked for changes"
mk "stage:approved"     0e8a16 "Owner approved. Final report shared."
mk "stage:blocked"      b60205 "Run stopped. See the run log for the reason."
mk "stage:paused-usage" f9d0c4 "Owner's Claude usage limit hit. Resumes later."
mk "stage:unassigned"   b60205 "Nobody had room. Assign by hand."
for t in install detection fp-audit web-journey api-security docs; do mk "type:$t" bfdadc "Test type $t"; done
for l in learn-discover buy-onboard use-operate; do mk "lane:$l" d4c5f9 "Lane $l"; done
