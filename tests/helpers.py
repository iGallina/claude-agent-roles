"""Shared test helpers. The front matter parser is independent of scripts/build.py on purpose:
it reads flat `key: value` front matter only, so a build bug cannot hide itself."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = ("chief-of-staff", "account-manager", "project-manager", "personal-assistant", "task-worker", "researcher")
ALLOWED_MODELS = {"claude-fable-5-2", "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"}
THINKING = {"low", "medium", "high", "xhigh", "max"}
CLAUDE_TOOLS = {"Read", "Write", "Edit", "Grep", "Glob", "Bash", "WebFetch", "WebSearch"}


def path(*parts):
    return os.path.join(ROOT, *parts)


def read(*parts):
    with open(path(*parts), encoding="utf-8") as f:
        return f.read()


def split(text):
    """(front matter dict, body). Raises ValueError on anything that is not flat `key: value` front matter."""
    if not text.startswith("---\n"):
        raise ValueError("front matter must open on line 1")
    rest = text[4:]
    head, sep, body = rest.partition("\n---\n")
    if not sep:
        raise ValueError("front matter never closes")
    fm = {}
    for line in head.split("\n"):
        if not line.strip():
            continue
        key, colon, value = line.partition(":")
        if not colon:
            raise ValueError(f"line without key: value -> {line!r}")
        fm[key.strip()] = value.strip()
    return fm, body


KEBAB = re.compile(r"^[a-z][a-z0-9-]*$")
