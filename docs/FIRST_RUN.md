# First run

This gets PXQ Autopilot from an empty setup to one ticket tested, reviewed and approved. Do the admin part once. Each teammate does the person part on every machine that will run tickets.

Plan for about an hour for the admin part and 30 minutes per person.

## 0. Make the repo private first

This repo drives self-hosted runners on teammates' machines and holds the lab network ranges. Issue bodies describe unreleased 5.0 testing. GitHub advises against self-hosted runners on public repos, because anyone who can get a workflow to run could reach a teammate's machine.

Settings → General → Danger Zone → Change visibility → Private.

If it has to stay public, at minimum turn on Settings → Actions → General → "Require approval for all outside collaborators". Never add `pull_request` triggers to the workflows that use self-hosted runners.

## 1. Admin setup (Samson, once)

### Repo settings

1. **Collaborators.** Settings → Collaborators. Add Mario and Mauricio with the Write role.
2. **Team file.** Put their GitHub logins in `config/team.yaml` and add them to `.github/CODEOWNERS`. The dispatch workflow won't run a ticket for anyone who isn't in the team file.
3. **Branch protection on `main`.** Settings → Branches → Add rule.
   - Require a pull request before merging.
   - Require review from Code Owners.
   - Require the `validate / checks` status check.
4. **Actions.** Settings → Actions → General.
   - Workflow permissions can stay "Read repository contents". Each workflow asks for only what it needs.
   - Tick "Allow GitHub Actions to create and approve pull requests". The weekly learning run opens a pull request and needs this.
5. **Fallback timer (optional).** Settings → Secrets and variables → Actions → Variables. Add `PXQ_FALLBACK_MINUTES`. The default is 10. It's how long a ticket waits for a cloud agent before it moves to the owner's local agent.

### Labels

From any machine where `gh` is signed in as you, run this.

```bash
scripts/setup/labels.sh
```

It creates the `pxq:ticket`, `stage:*`, `needs:cloud`, `type:*`, `lane:*` and `learning` labels. It's safe to run again.

### Dashboard

The team dashboard is a Claude artifact owned by the admin. It reads a snapshot of GitHub, so nothing on it is sample data.

1. The `dashboard-data` workflow builds `snapshot.json` on every ticket change and once an hour, and publishes it to the `dashboard-data` branch. Run it once by hand after your first push: Actions → dashboard-data → Run workflow.
2. A Claude scheduled task in the admin's account, "PXQ dashboard sync", copies the snapshot into the dashboard once an hour. Press **Sync now** on the dashboard for a fresh copy. It works through the Claude Code Remote connector in the admin's claude.ai account.
3. Share the dashboard with the team from its Share menu. Then link each seat to its Claude profile on the Team page.

If the repo goes private, the scheduled task's cloud session needs read access to it, because it fetches the snapshot with git.

### Organization-wide Claude settings (recommended)

Ask the Claude org owner to push managed settings that lock Claude Code sign-ins to the Wazuh Claude organization. That stops anyone from running tickets on a personal account by mistake. The plan doc, section 3, has the exact keys.

## 2. Person setup (everyone, on each agent machine)

A machine is either your **cloud agent** (a VM with lab access that stays on) or your **local agent** (your own computer, used when the cloud agent is down). You can set up one or both.

### Windows

Use WSL2 with Ubuntu 24.04. The runner script needs bash.

```powershell
wsl --install -d Ubuntu-24.04
```

Then do everything below inside Ubuntu. Turn on systemd so the runner can run as a service. Add this to `/etc/wsl.conf`, then run `wsl --shutdown` from PowerShell and reopen Ubuntu.

```ini
[boot]
systemd=true
```

### Tools

```bash
sudo apt update && sudo apt install -y git jq python3 python3-yaml shellcheck
# Node 20 or later, then Claude Code
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash - && sudo apt install -y nodejs
sudo npm install -g @anthropic-ai/claude-code
# GitHub CLI: https://github.com/cli/cli/blob/trunk/docs/install_linux.md
# Local agents only: VMs for install tests
sudo snap install multipass
```

### Sign in

1. **Claude.** Run `claude`, then `/login`, and pick your Wazuh Claude account. Don't use `claude setup-token`, and don't set `ANTHROPIC_API_KEY`. Tickets must run on your own seat.
2. **GitHub.** Run `gh auth login` and choose HTTPS and the browser.

### Your private drafts repo

Drafts never go to the team repo. Create a private repo called `pxq-drafts` on your own GitHub account, then clone it.

```bash
gh repo create pxq-drafts --private --clone && mv pxq-drafts ~/pxq-drafts
```

### Clone and check

```bash
git clone https://github.com/SamsonIdowu/PXQ-Autopilot.git ~/PXQ-Autopilot
cd ~/PXQ-Autopilot
scripts/setup/doctor.sh local     # or: cloud
```

Fix every FAIL line before you go on. Warnings are fine for a first run.

### Register your runner

1. In GitHub, open Settings → Actions → Runners → New self-hosted runner. Choose Linux x64. Leave the page open, because the token on it expires in an hour.
2. Run the download lines from that page in `~/actions-runner`.
3. Register with your labels. Swap in your GitHub login and `cloud` or `local`.

```bash
cd ~/actions-runner
./config.sh --url https://github.com/SamsonIdowu/PXQ-Autopilot --token <token from the page> \
  --name "$(gh api user -q .login)-local" \
  --labels "pxq-$(gh api user -q .login),local" \
  --unattended
sudo ./svc.sh install "$USER" && sudo ./svc.sh start
```

The service must run as **you**. That's how the runner uses your Claude sign-in without any shared key.

The admin's cloud agent also gets the `pxq-admin` label for the weekly learning run. Add it with `--labels "pxq-SamsonIdowu,cloud,pxq-admin"`.

### Plugin (optional)

The repo is enough when you run Claude Code inside it. Use the plugin only if you want the agents in other folders too.

```text
/plugin marketplace add SamsonIdowu/PXQ-Autopilot
/plugin install pxq-agents@wazuh-pxq
```

A private repo works as long as `git clone` works for you on that machine.

## 3. First run, smallest step first

Each step checks one more piece. Stop at the first one that fails and look at the troubleshooting table.

### Step 1. The agents load

In the repo folder, run `claude` and type `/agents`. You should see `pxq-planner`, `pxq-tester` and `pxq-reviewer`.

### Step 2. The Reviewer catches a weak finding

This needs no VM and costs a few minutes of usage.

```bash
python3 scripts/evals/run_evals.py --agent reviewer
```

It should pass. The Reviewer must send back a finding that was only reproduced once.

### Step 3. The Planner plans the CEO directive

```bash
python3 scripts/evals/run_evals.py --agent planner
```

It writes `evals/planner/out/plan.json`. Open it and check the priorities, services and cloud flags look right to you. This is the best place to catch wrong Wazuh service names before they spread into reports.

### Step 4. One real ticket on a local agent

Use the canary. It's a plain AIO install on a release the team already trusts, so any S1 or S2 finding means the Tester is inventing problems.

1. In GitHub, open Issues → New issue → PXQ test ticket.
2. Paste the JSON from `evals/tester/fixtures/canary-aio.json` into the Ticket box and submit.
3. The `assign` workflow picks an owner and starts the ticket on their cloud agent. If you only have a local agent so far, send it there now rather than waiting for the fallback.

```bash
scripts/owner/pxq.sh rerun <issue number> local
```

4. Watch it in Actions → dispatch. Only `PXQ-PROGRESS` lines show up there. The label moves from `stage:assigned` to `stage:testing`, `stage:review` and then `stage:owner`.

### Step 5. Review, tag and approve

On the owner's machine, in the repo folder, run `claude` and say `review PXQ-<issue number>`.

1. Tag each finding.
2. Approve.
3. Let Claude publish the report artifact and, after you say yes, post the link to the reports channel.
4. Run the approve command Claude gives you, with the leading `!`.

The issue closes with `stage:approved`, and your tags are saved on it for the learning run.

### Step 6. The learning loop

Actions → learn → Run workflow. With one approved ticket it has little to learn from. The point is to see it measure and open a pull request, or say there's nothing to propose.

### Step 7. Plan the real directive

Paste the directive into Claude Code in the repo and say "plan this". Review the plan. Then run the `open-issues` command Claude gives you. Tickets start flowing to owners within a couple of minutes.

## Before you go wide

- [ ] Wazuh service names in `config/services.yaml` checked with Product
- [ ] Lab ranges in `config/networks.yaml` match the real cloud agent network
- [ ] Mario and Mauricio added to `config/team.yaml`, `CODEOWNERS` and as collaborators
- [ ] Every person passes `scripts/setup/doctor.sh`
- [ ] The canary passed with no S1 or S2 findings
- [ ] One full loop done, from issue to approved report to learning run

## Troubleshooting

| What you see | What it usually means |
|---|---|
| dispatch says "isn't in config/team.yaml" | The assignee's GitHub login isn't in the team file, or the case doesn't match |
| Job waits forever in "Queued" | No online runner has the labels `pxq-<login>` and `cloud` or `local`. Check Settings → Actions → Runners. |
| `stage:blocked` with `no-ticket-json` | The issue body has no ```json block, or the JSON is broken |
| `stage:blocked` with `needs-cloud-agent` | The ticket needs a cluster. It never falls back to a laptop. Bring the cloud agent back. |
| `stage:paused-usage` | The owner hit their Claude usage limit. Rerun it later with `scripts/owner/pxq.sh rerun <n>`. |
| `stage:blocked` with `tester-exited` | Look at `runs/PXQ-<n>/tester.err` on the owner's machine. "Not logged in" means the runner service isn't running as the person. |
| `stage:unassigned` | Everyone is at `max_open`. Assign it by hand. The dispatch workflow starts it. |
| Learning run can't open its pull request | Tick "Allow GitHub Actions to create and approve pull requests" in Settings → Actions |
| "Blocked by PXQ guard" in a run | Working as designed. If the host is a real lab host, add it to `config/networks.yaml` in a pull request. |
