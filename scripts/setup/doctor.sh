#!/usr/bin/env bash
# Checks that this machine is ready to run PXQ tickets as a cloud or local agent.
# Run it from the repo folder:  scripts/setup/doctor.sh [cloud|local]
# It only reads. It changes nothing.
AGENT="${1:-local}"
ok=0; warn=0; fail=0
pass() { echo "  ok    $1"; ok=$((ok+1)); }
note() { echo "  warn  $1"; warn=$((warn+1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail+1)); }
have() { command -v "$1" >/dev/null 2>&1; }
cd "$(dirname "$0")/../.." || exit 1

echo "PXQ doctor for a $AGENT agent"
case "$(uname -s)" in
  Linux*)  grep -qi microsoft /proc/version 2>/dev/null && pass "Running in WSL. Good for Windows machines." || pass "Linux" ;;
  Darwin*) pass "macOS" ;;
  *)       bad "Run this in WSL2 (Ubuntu) on Windows. The runner script needs bash." ;;
esac

for t in git python3 jq gh node npx; do have "$t" && pass "$t found" || bad "$t is missing"; done
python3 -c 'import yaml' 2>/dev/null && pass "PyYAML found" || note "PyYAML missing. Run: python3 -m pip install --user pyyaml"

if have claude; then
  pass "Claude Code $(claude --version 2>/dev/null | head -1)"
  if [[ -f "$HOME/.claude/.credentials.json" ]]; then
    perms=$(stat -c %a "$HOME/.claude/.credentials.json" 2>/dev/null || stat -f %Lp "$HOME/.claude/.credentials.json")
    [[ "$perms" == "600" ]] && pass "Claude sign-in stored with 600 permissions" || note "Run: chmod 600 ~/.claude/.credentials.json"
  elif [[ "$(uname -s)" == Darwin* ]]; then
    note "On macOS the sign-in lives in the Keychain. Make sure you ran claude and chose your Wazuh Claude account."
  else
    bad "Not signed in. Run claude, then /login, and pick your Wazuh Claude account. Don't use claude setup-token."
  fi
  [[ -n "${ANTHROPIC_API_KEY:-}" ]] && bad "ANTHROPIC_API_KEY is set. Unset it so runs use your Claude account, not an API key."
else
  bad "Claude Code is missing. Install it with: npm install -g @anthropic-ai/claude-code"
fi

if have gh; then
  gh auth status >/dev/null 2>&1 && pass "GitHub CLI signed in as $(gh api user -q .login 2>/dev/null)" || bad "Run: gh auth login"
  login=$(gh api user -q .login 2>/dev/null)
  if [[ -n "$login" ]]; then
    grep -q "github: \"$login\"" config/team.yaml && pass "$login is in config/team.yaml" || bad "$login isn't in config/team.yaml yet. Ask the admin to add you."
  fi
fi

[[ -n "$(git config --global user.email)" ]] && pass "git identity set" || bad "Run: git config --global user.name \"Your Name\" && git config --global user.email you@wazuh.com"

if [[ -d "${PXQ_DRAFTS_DIR:-$HOME/pxq-drafts}/.git" ]]; then
  pass "Private drafts repo at ${PXQ_DRAFTS_DIR:-$HOME/pxq-drafts}"
else
  bad "No drafts repo. Create a PRIVATE repo named pxq-drafts on your GitHub account and clone it to ~/pxq-drafts"
fi

if [[ "$AGENT" == "local" ]]; then
  have multipass && pass "Multipass found for local test VMs" || note "Multipass missing. Local install tests need it (snap install multipass, or the macOS installer)."
fi

have npx && (timeout 60 npx -y @playwright/mcp@latest --help >/dev/null 2>&1 && pass "Playwright MCP starts" || note "Playwright MCP didn't start. Web journey tests need it.")

for f in .claude/hooks/guard_bash.py .claude/settings.json .mcp.json runner/run-ticket.sh runner/allowed-tools.txt; do
  [[ -f "$f" ]] || bad "$f is missing"
done
echo '{"tool_input":{"command":"gh issue create -t x"}}' | python3 .claude/hooks/guard_bash.py 2>/dev/null; [[ $? -eq 2 ]] && pass "Guard hook blocks GitHub writes" || bad "Guard hook isn't blocking"

if [[ -f "$HOME/actions-runner/.runner" ]]; then pass "GitHub runner registered in ~/actions-runner"
else note "No runner in ~/actions-runner yet. See "Register your runner" in docs/FIRST_RUN.md."; fi

echo
echo "$ok ok, $warn warnings, $fail failures"
[[ $fail -eq 0 ]]
