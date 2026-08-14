#!/usr/bin/env python3
"""Verify the Codex and Claude Code skill entry points still agree.

The workflow and contract live once, under .agents/. Each harness gets a thin entry
point that must advertise the same name and description, otherwise one harness
discovers the skill for a request the other ignores.
"""
from __future__ import annotations

import sys
from pathlib import Path

ENTRY_POINTS = (
    Path(".agents/skills/plant-tracker/SKILL.md"),
    Path(".claude/skills/plant-tracker/SKILL.md"),
)

CANONICAL = Path(".agents/skills/plant-tracker/SKILL.md")
CONTRACT = Path(".agents/skills/plant-tracker/references/tracker-contract.md")


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Read the leading YAML frontmatter as flat single-line key/value pairs."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing opening '---' frontmatter delimiter")

    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    raise ValueError(f"{path}: missing closing '---' frontmatter delimiter")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors: list[str] = []

    parsed: dict[Path, dict[str, str]] = {}
    for relative in ENTRY_POINTS:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing skill entry point: {relative}")
            continue
        try:
            parsed[relative] = parse_frontmatter(path)
        except ValueError as exc:
            errors.append(str(exc))

    for relative, fields in parsed.items():
        for key in ("name", "description"):
            if not fields.get(key):
                errors.append(f"{relative}: frontmatter is missing '{key}'")
        if fields.get("name") not in (None, "plant-tracker"):
            errors.append(f"{relative}: name must be 'plant-tracker', got {fields['name']!r}")

    if len(parsed) == len(ENTRY_POINTS):
        descriptions = {relative: fields.get("description") for relative, fields in parsed.items()}
        if len(set(descriptions.values())) > 1:
            errors.append(
                "skill descriptions differ between harnesses; both entry points must "
                "advertise the same description so each harness triggers on the same "
                "requests:\n"
                + "\n".join(f"  {relative}: {value}" for relative, value in descriptions.items())
            )

    claude_entry = root / ENTRY_POINTS[1]
    if claude_entry.is_file():
        body = claude_entry.read_text(encoding="utf-8")
        for target in (CANONICAL, CONTRACT):
            if target.as_posix() not in body:
                errors.append(
                    f"{ENTRY_POINTS[1]}: must point readers at {target.as_posix()}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: {len(ENTRY_POINTS)} skill entry points agree on name and description")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
