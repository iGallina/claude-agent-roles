#!/usr/bin/env python3
"""Generate both agent formats from the one source per role in roles/.

    python3 scripts/build.py           write .claude/agents/<role>.md and paseo/<role>.md
    python3 scripts/build.py --check   exit 1 when a committed file differs from the generator output

Standard library only. Python 3.9 or newer.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ("name", "title", "description", "model", "thinking", "order")
MODELS = {"claude-fable-5-2", "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"}
THINKING = {"low", "medium", "high", "xhigh", "max"}


def parse(text, where="source"):
    """Flat `key: value` front matter, then the body. Rejects what the readers of the outputs would reject."""
    if not text.startswith("---\n"):
        raise ValueError(f"{where}: front matter must open on line 1")
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise ValueError(f"{where}: front matter never closes")
    fm = {}
    for line in head.split("\n"):
        if not line.strip():
            continue
        key, colon, value = line.partition(":")
        if not colon:
            raise ValueError(f"{where}: line without key: value -> {line!r}")
        fm[key.strip()] = value.strip()
    return fm, body.strip("\n")


def validate(fm, where):
    missing = [k for k in REQUIRED if not fm.get(k)]
    if missing:
        raise ValueError(f"{where}: missing {', '.join(missing)}")
    if fm["model"] not in MODELS:
        raise ValueError(f"{where}: model {fm['model']!r} is not one of {sorted(MODELS)}")
    if fm["thinking"] not in THINKING:
        raise ValueError(f"{where}: thinking {fm['thinking']!r} is not one of {sorted(THINKING)}")
    if not fm["order"].isdigit():
        raise ValueError(f"{where}: order must be a number")


def claude_code(fm, body, role):
    head = [f"name: {fm['name']}", f"description: {fm['description']}"]
    if fm.get("tools"):
        head.append(f"tools: {fm['tools']}")
    head += [f"model: {fm['model']}", f"effort: {fm['thinking']}"]
    return _join(head, body, role)


def paseo(fm, body, role):
    head = [
        f"name: {fm['title']}",
        "provider: claude",
        f"model: {fm['model']}",
        "modeId: auto",
        f"thinkingOptionId: {fm['thinking']}",
        f"notes: {fm['description']}",
    ]
    return _join(head, body, role)


def _join(head, body, role):
    note = f"<!-- Generated from roles/{role}.md by scripts/build.py. Edit the source, then run the script. -->"
    return "---\n" + "\n".join(head) + "\n---\n" + note + "\n\n" + body + "\n"


def render_all(roles_dir):
    """{relative output path: text} for every role in roles_dir."""
    out = {}
    for fname in sorted(os.listdir(roles_dir)):
        if not fname.endswith(".md"):
            continue
        role = fname[:-3]
        with open(os.path.join(roles_dir, fname), encoding="utf-8") as f:
            fm, body = parse(f.read(), f"roles/{fname}")
        validate(fm, f"roles/{fname}")
        if fm["name"] != role:
            raise ValueError(f"roles/{fname}: name {fm['name']!r} must equal the file name")
        out[os.path.join(".claude", "agents", fname)] = claude_code(fm, body, role)
        out[os.path.join("paseo", fname)] = paseo(fm, body, role)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    rendered = render_all(os.path.join(ROOT, "roles"))
    stale = []
    for rel, text in rendered.items():
        target = os.path.join(ROOT, rel)
        current = None
        if os.path.exists(target):
            with open(target, encoding="utf-8") as f:
                current = f.read()
        if current == text:
            continue
        stale.append(rel)
        if not check:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(text)
    if check:
        for rel in stale:
            print(f"stale: {rel}", file=sys.stderr)
        return 1 if stale else 0
    print(f"wrote {len(stale)} file(s), {len(rendered) - len(stale)} unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
