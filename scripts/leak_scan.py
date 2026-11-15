#!/usr/bin/env python3
"""Generic leak scan for a public repo.

Emails, IPs, UUIDs, home paths, phone numbers and token prefixes are plain regexes. The repo carries no list of
owner-specific terms: the owner keeps that list outside the repo and scans before a push.

    python3 scripts/leak_scan.py        prints `leak-scan: N hits`, exits 1 when N > 0

Standard library only. Python 3.9 or newer.
"""
import os
import re
import subprocess
import sys
from collections import namedtuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Hit = namedtuple("Hit", "line kind")

GENERIC = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+"),
    "ipv4": re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    "uuid": re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
    # the two path patterns are built from halves so this file does not match itself
    "home path": re.compile("/Us" + "ers/|/ho" + "me/[a-z]|\\bC:\\\\Us" + "ers\\\\"),
    "tilde path": re.compile("(?<![\\w.])~" + "/"),
    "phone": re.compile(r"(?<![\w.-])(?:\+\d[\d\s().-]{8,}\d|\(?\d{2,4}\)?[\s.-]\d{3,5}[\s.-]\d{3,5})(?![\w.-])"),
    "slack token": re.compile(r"\bxox[abprs]-"),
    "api key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|\bgithub_pat_|\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}

_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}


def scan_text(text):
    """Hits as (line, kind), sorted and unique. The matched text is never echoed."""
    hits = set()
    for n, line in enumerate(text.split("\n"), 1):
        for kind, rx in GENERIC.items():
            if rx.search(line):
                hits.add(Hit(n, kind))
    return sorted(hits)


def _in_git_repo(root):
    try:
        r = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    except FileNotFoundError:  # no git binary: walk the folder instead
        return False
    return r.returncode == 0 and os.path.realpath(r.stdout.strip()) == os.path.realpath(root)


def repo_files(root=ROOT):
    """Every file the repo holds. In a git clone: tracked plus untracked, minus ignored. Otherwise (a ZIP download,
    a copy): a walk of the folder that skips .git and caches."""
    if _in_git_repo(root):
        out = subprocess.run(["git", "-C", root, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                             capture_output=True, check=True).stdout.decode("utf-8")
        return sorted(p for p in out.split("\0") if p and os.path.isfile(os.path.join(root, p)))
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        found += [os.path.relpath(os.path.join(base, f), root) for f in files if not f.endswith(".pyc")]
    return sorted(found)


def scan_repo(root=ROOT):
    problems = []
    for rel in repo_files(root):
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            text = f.read()
        problems += [f"{rel}:{h.line} {h.kind}" for h in scan_text(text)]
    return problems


def main():
    problems = scan_repo()
    for p in problems:
        print(p)
    print(f"leak-scan: {len(problems)} hits")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
