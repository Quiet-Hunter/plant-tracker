#!/usr/bin/env python3
"""Bring images/README.md back in line with the files actually in images/.

The validator treats the inventory as authoritative in both directions: an image
on disk that is not listed, or a listing with no file behind it, is an error. That
catches photos which arrived without going through prepare_photo.sh, but it also
means the list has to be maintained. This repairs it.

Existing entries keep their order so the diff stays small; new files are appended.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".heic", ".heif", ".tif", ".tiff"}
ENTRY = re.compile(r"^\s*[-*]\s+`([^`]+)`\s*$")
HEADING_HINT = re.compile(r"inventory\s*:", re.IGNORECASE)

INVENTORY_TEMPLATE = """# Plant photos

Final tracker photos live in this folder. `plants.html` displays the files its image
paths reference. Add photos with `prepare_photo.sh`, which strips metadata and records
them below; never copy a file here by hand.

This file and the photos beside it are ignored by Git, so your images stay private.

Current image inventory:

"""


def read_entries(lines):
    """Return (entry_names, first_index, last_index) for the bullet list."""
    names = []
    first = last = None
    for index, line in enumerate(lines):
        match = ENTRY.match(line)
        if match:
            names.append(match.group(1))
            if first is None:
                first = index
            last = index
    return names, first, last


def write_atomically(path, text):
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".sync-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument(
        "--check", action="store_true",
        help="report drift and exit non-zero without editing the inventory",
    )
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    images_dir = root / "images"
    readme = images_dir / "README.md"

    if not images_dir.is_dir():
        print(f"ERROR: images directory not found: {images_dir}", file=sys.stderr)
        return 1

    on_disk = sorted(
        p.name for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )

    if not readme.is_file():
        if not on_disk:
            print("OK: no photos and no inventory, nothing to reconcile")
            return 0
        if args.check:
            print(f"ERROR: image inventory not found: {readme}", file=sys.stderr)
            print(
                "Run sync_image_inventory.py without --check to create it.",
                file=sys.stderr,
            )
            return 1
        # Photos are not committed, so a fresh clone starts without an inventory.
        # Create it rather than refusing.
        write_atomically(readme, INVENTORY_TEMPLATE)
        print(f"created: {readme}")

    text = readme.read_text(encoding="utf-8")
    lines = text.splitlines()
    listed, first, last = read_entries(lines)

    present = set(on_disk)
    kept = [name for name in listed if name in present]
    added = [name for name in on_disk if name not in set(listed)]
    removed = [name for name in listed if name not in present]
    final = kept + added

    if not added and not removed:
        print(f"OK: images/README.md lists all {len(on_disk)} images")
        return 0

    if args.check:
        for name in added:
            print(f"ERROR: image on disk but not listed: {name}", file=sys.stderr)
        for name in removed:
            print(f"ERROR: listed but no such file: {name}", file=sys.stderr)
        print(
            "Run sync_image_inventory.py without --check to fix the inventory.",
            file=sys.stderr,
        )
        return 1

    bullets = [f"- `{name}`" for name in final]
    if first is not None:
        rebuilt = lines[:first] + bullets + lines[last + 1:]
    else:
        anchor = next(
            (i for i, line in enumerate(lines) if HEADING_HINT.search(line)),
            len(lines) - 1,
        )
        rebuilt = lines[:anchor + 1] + [""] + bullets + lines[anchor + 1:]

    write_atomically(readme, "\n".join(rebuilt).rstrip("\n") + "\n")

    for name in added:
        print(f"added: {name}")
    for name in removed:
        print(f"removed: {name}")
    print(f"OK: images/README.md now lists {len(final)} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
