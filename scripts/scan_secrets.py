#!/usr/bin/env python3
"""Fail if a run folder contains anything that looks like a secret.

Usage: python3 scripts/scan_secrets.py runs/PXQ-101
"""
import os, re, sys

PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "Anthropic key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    "AWS key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "password assignment": re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"]?(?!\*{3}|<|\$\{)[^\s'\"]{6,}"),
}
TEXT_EXT = {".md", ".json", ".log", ".txt", ".yaml", ".yml", ".har", ".csv", ".html"}

def main(root):
    hits = []
    for dirpath, _, files in os.walk(root):
        for name in files:
            if os.path.splitext(name)[1].lower() not in TEXT_EXT:
                continue
            path = os.path.join(dirpath, name)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for label, rx in PATTERNS.items():
                for m in rx.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append(f"{path}:{line} looks like a {label}")
    for h in hits:
        print(h)
    print(f"{len(hits)} possible secrets found" if hits else "No secrets found")
    return 1 if hits else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "runs"))
