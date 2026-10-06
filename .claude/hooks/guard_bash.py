#!/usr/bin/env python3
"""PreToolUse guard for PXQ agents.

Blocks shell commands that reach hosts outside the allowed networks, post to
GitHub or Slack, or damage the machine. Exit code 2 blocks the command and
shows the reason to the agent.
"""
import ipaddress, json, os, re, sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

def load_allowed():
    """Read config/networks.yaml without needing PyYAML."""
    nets, hosts = [], []
    path = os.path.join(ROOT, "config", "networks.yaml")
    try:
        section = None
        for raw in open(path, encoding="utf-8"):
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if not line.startswith(" ") and line.endswith(":"):
                section = line[:-1].strip()
                continue
            item = line.strip().lstrip("-").strip().strip('"')
            if section == "cidrs" and item:
                nets.append(ipaddress.ip_network(item, strict=False))
            elif section == "hosts" and item:
                hosts.append(item.lower())
    except FileNotFoundError:
        pass
    return nets, hosts

DENY_PATTERNS = [
    (r"\bgh\s+(issue|pr)\s+(create|comment|edit|close|merge|review)\b", "Agents can't write to GitHub. Only people and the workflows do."),
    (r"\bgh\s+api\b", "Agents can't call the GitHub API directly."),
    (r"hooks\.slack\.com|slack\.com/api", "Agents can't post to Slack."),
    (r"\bgit\s+push\b", "Agents can't push code."),
    (r"\brm\s+-[a-z]*r[a-z]*f?\s+/(\s|$)", "Refusing to delete the root filesystem."),
    (r"\b(mkfs|fdisk|parted)\b", "Refusing to change disks."),
    (r"\bdd\s+[^|]*of=/dev/", "Refusing to write to a raw device."),
    (r"\b(shutdown|reboot|halt|poweroff)\b(?!.*--vm)", "Refusing to power off the agent machine."),
]

PIPE_TO_SHELL = re.compile(r"\b(curl|wget)\b([^|;&]*)\|\s*(sudo\s+(-\S+\s+)*)?(ba|z|da)?sh\b")
TRUSTED_SCRIPT_HOSTS = {"packages.wazuh.com"}

def pipe_to_shell_blocked(cmd):
    """A download piped into a shell is allowed only when every URL in it is on a trusted host."""
    for m in PIPE_TO_SHELL.finditer(cmd):
        hosts = re.findall(r"https?://([A-Za-z0-9.\-]+)", m.group(2))
        if not hosts or any(h.lower() not in TRUSTED_SCRIPT_HOSTS for h in hosts):
            return True
    return False

HOST_RE = re.compile(r"(?:ssh|scp|rsync|sftp)\s+(?:-\S+\s+)*(?:\S+@)?([A-Za-z0-9.\-]+)|https?://([A-Za-z0-9.\-]+)")
PUBLIC_OK = {"packages.wazuh.com", "documentation.wazuh.com", "github.com", "raw.githubusercontent.com",
             "objects.githubusercontent.com", "api.github.com", "registry.npmjs.org", "pypi.org", "files.pythonhosted.org",
             "localhost", "127.0.0.1"}

def host_allowed(host, nets, hosts):
    host = host.lower().rstrip(".")
    if host in PUBLIC_OK or host in hosts or any(host.endswith("." + h) for h in hosts):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return any(ip in n for n in nets)
    except ValueError:
        return False

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not cmd:
        return 0
    for pattern, reason in DENY_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            print(f"Blocked by PXQ guard. {reason}", file=sys.stderr)
            return 2
    if pipe_to_shell_blocked(cmd):
        print("Blocked by PXQ guard. Refusing to pipe a download into a shell unless it comes from packages.wazuh.com.", file=sys.stderr)
        return 2
    nets, hosts = load_allowed()
    for m in HOST_RE.finditer(cmd):
        host = m.group(1) or m.group(2)
        if host and not host_allowed(host, nets, hosts):
            print(f"Blocked by PXQ guard. {host} isn't in config/networks.yaml, so agents can't reach it.", file=sys.stderr)
            return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
