#!/usr/bin/env python3
"""Clear the personal plant rows, keeping the UI and the species reference.

Each run writes its own timestamped backup. The previous version used one fixed
filename and refused to continue when it already existed, advising `--no-backup`
instead — which, run months later against a real collection, destroyed the whole
inventory with no backup at all.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

START_MARKER = '<section id="my-plants"'
END_MARKER = '<section id="reference"'
# The opening tag carries attributes, such as lang="ru" on the demo records.
TBODY_OPEN = re.compile(r"<tbody\b[^>]*>")
TBODY_CLOSE = "</tbody>"
EMPTY_BODY = "\n            "
# Soil recipes are keyed by species name, so they enumerate the collection too.
SOIL_MAP = re.compile(r"(const soilMixes = new Map\(\[)(.*?)(\n\s*\]\);)", re.DOTALL)


def find_tbody_span(text, start, end):
    """Return (content_start, content_end) of the first <tbody> in the range."""
    opening = TBODY_OPEN.search(text, start, end)
    if opening is None:
        return None
    try:
        return opening.end(), text.index(TBODY_CLOSE, opening.end(), end)
    except ValueError:
        return None


def next_backup_path(root, stamp):
    """A backup path that does not already exist."""
    candidate = root / f"plants.backup.{stamp}.html"
    suffix = 2
    while candidate.exists():
        candidate = root / f"plants.backup.{stamp}-{suffix}.html"
        suffix += 1
    return candidate


def write_atomically(path, text):
    """Replace `path` in one step, so an interrupted run cannot truncate it."""
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".start-fresh-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        shutil.copystat(path, temp_name)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument(
        "--no-backup", action="store_true",
        help="do not write a backup copy before clearing",
    )
    parser.add_argument(
        "--clear-reference", action="store_true",
        help="also clear the species care reference and its soil recipes, so the "
             "tracker keeps none of the previous owner's plants or photos",
    )
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    tracker = root / "plants.html"
    if not tracker.is_file():
        parser.error(f"tracker not found: {tracker}")

    text = tracker.read_text(encoding="utf-8")
    try:
        section_start = text.index(START_MARKER)
        section_end = text.index(END_MARKER)
    except ValueError as exc:
        parser.error(f"unexpected tracker structure, nothing was changed: {exc}")

    personal = find_tbody_span(text, section_start, section_end)
    if personal is None:
        parser.error("could not find the personal <tbody>, nothing was changed")

    spans = [personal]
    if args.clear_reference:
        reference = find_tbody_span(text, section_end, len(text))
        if reference is None:
            parser.error("could not find the reference <tbody>, nothing was changed")
        spans.append(reference)

    # Rewrite from the end so earlier offsets stay valid.
    cleared = text
    for start, end in sorted(spans, reverse=True):
        cleared = cleared[:start] + EMPTY_BODY + cleared[end:]

    if args.clear_reference:
        cleared, replaced = SOIL_MAP.subn(r"\1\3", cleared)
        if not replaced:
            parser.error("could not find the soil recipe map, nothing was changed")

    if cleared == text:
        print(f"Nothing to clear: {tracker}")
        return 0

    if not args.no_backup:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        backup = next_backup_path(root, stamp)
        shutil.copy2(tracker, backup)
        print(f"Backup: {backup}")

    write_atomically(tracker, cleared)
    if args.clear_reference:
        print(f"Cleared personal inventory and species reference: {tracker}")
        print(
            "No plants, photos, or soil recipes from the previous inventory remain in "
            "the tracker. The photo files in images/ are untouched; delete them "
            "separately if you do not want them."
        )
    else:
        print(f"Cleared personal inventory: {tracker}")
        print(
            "The species reference and its photos are kept for reuse, so the tracker "
            "still shows the previous inventory's species. Pass --clear-reference to "
            "remove those too."
        )
    print(
        "Until you add a plant, validate with:\n"
        "  python3 .agents/skills/plant-tracker/scripts/validate_tracker.py . --allow-empty"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
