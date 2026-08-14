#!/usr/bin/env python3
"""Validate the tracker in plants.html against the project contract.

Rows are located by parsing the document and identifying cells by class, not by
matching a regex against exact byte formatting. That matters: the previous regex
required every row on one line with no whitespace between tags, so reformatting
the file made every row invisible and the validator reported success having
checked nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

PRIORITIES = {
    "High": (0, "high"),
    "Medium": (1, "medium"),
    "Low": (2, ""),
    "Высокий": (0, "high"),
    "Средний": (1, "medium"),
    "Низкий": (2, ""),
}

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".heic", ".heif", ".tif", ".tiff"}

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INVENTORY_ENTRY = re.compile(r"^\s*[-*]\s+`([^`]+)`", re.MULTILINE)


class Cell:
    """One table cell and the parts of its content the contract cares about."""

    def __init__(self, tag, attrs):
        self.tag = tag
        self.classes = set((dict(attrs).get("class") or "").split())
        self.text_parts = []
        self.priority_label = None
        self.priority_classes = None
        self.time_datetime = None
        self.time_display_parts = None

    @property
    def text(self):
        return "".join(self.text_parts).strip()

    @property
    def time_display(self):
        if self.time_display_parts is None:
            return None
        return "".join(self.time_display_parts).strip()


class TrackerParser(HTMLParser):
    """Collect personal rows, image references, and tag-balance errors."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.image_refs = []
        self.balance_errors = []
        self._stack = []
        self._section = None
        self._in_tbody = False
        self._row = None
        self._cell = None
        self._in_time = False

    # -- structure -------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        for key in ("src", "href"):
            value = attr.get(key)
            if value and value.startswith("images/"):
                self.image_refs.append(value)

        if tag not in VOID_ELEMENTS:
            self._stack.append(tag)

        if tag == "section":
            self._section = attr.get("id")
        elif tag == "tbody" and self._section == "my-plants":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = Cell(tag, attrs)
            self._row.append(self._cell)
        elif self._cell is not None:
            if tag == "span" and "priority" in (attr.get("class") or "").split():
                self._cell.priority_classes = (attr.get("class") or "").split()
                self._cell.priority_label = []
            elif tag == "time":
                self._cell.time_datetime = attr.get("datetime")
                self._cell.time_display_parts = []
                self._in_time = True

    def handle_endtag(self, tag):
        if tag in VOID_ELEMENTS:
            return
        if not self._stack:
            self.balance_errors.append(f"unexpected closing </{tag}>")
        elif self._stack[-1] != tag:
            self.balance_errors.append(
                f"closing </{tag}> where </{self._stack[-1]}> was expected"
            )
            if tag in self._stack:
                while self._stack and self._stack.pop() != tag:
                    pass
        else:
            self._stack.pop()

        if tag == "time":
            self._in_time = False
        elif tag in ("td", "th"):
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag == "tbody":
            self._in_tbody = False
        elif tag == "section":
            self._section = None

    def handle_data(self, data):
        if self._cell is None:
            return
        if self._in_time and self._cell.time_display_parts is not None:
            self._cell.time_display_parts.append(data)
        if self._cell.priority_label is not None and not self._in_time:
            self._cell.priority_label.append(data)
        self._cell.text_parts.append(data)

    def close(self):
        super().close()
        for tag in reversed(self._stack):
            self.balance_errors.append(f"unclosed <{tag}>")


def sort_key(name):
    """Mirror the page's Intl.Collator(undefined, {sensitivity:'base', numeric:true})."""
    folded = unicodedata.normalize("NFKD", name.casefold())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    parts = []
    for chunk in re.split(r"(\d+)", folded):
        if chunk.isdigit():
            parts.append((1, int(chunk), ""))
        elif chunk:
            parts.append((0, 0, chunk))
    return parts


def find_cell(row, css_class):
    for cell in row:
        if css_class in cell.classes:
            return cell
    return None


def find_priority_cell(row):
    for cell in row:
        if cell.priority_classes is not None:
            return cell
    return None


def check_row(row, index, errors):
    """Validate one personal row. Returns (name, rank) or None if unusable."""
    name_cell = find_cell(row, "plant-name")
    label = f"row {index + 1}"
    if name_cell is None:
        errors.append(f"{label}: no cell with class 'plant-name'")
        return None

    name = name_cell.text
    label = f"{name or label}"

    priority_cell = find_priority_cell(row)
    if priority_cell is None:
        errors.append(f"{label}: no priority cell containing a <span class=\"priority ...\">")
        return None

    priority = "".join(priority_cell.priority_label).strip()
    if priority not in PRIORITIES:
        errors.append(f"Unknown priority for {label}: {priority!r}")
        return None
    rank, expected_class = PRIORITIES[priority]

    actual = [c for c in priority_cell.priority_classes if c != "priority"]
    expected = [expected_class] if expected_class else []
    if actual != expected:
        errors.append(
            f"Priority class mismatch for {label}: "
            f"expected class {' '.join(['priority'] + expected)!r}, "
            f"got {' '.join(['priority'] + actual)!r}"
        )

    # The action cell sits immediately before the priority cell.
    priority_index = row.index(priority_cell)
    if priority_index < 1:
        errors.append(f"{label}: no action cell before the priority cell")
    elif rank == 2 and row[priority_index - 1].text:
        errors.append(f"Low-priority plant with a non-empty action: {label}")

    date_cell = find_cell(row, "last-inspection")
    if date_cell is None:
        errors.append(f"{label}: no cell with class 'last-inspection'")
    elif not date_cell.time_datetime:
        errors.append(f"{label}: inspection cell has no <time datetime=\"...\">")
    else:
        iso = date_cell.time_datetime
        if not ISO_DATE.match(iso):
            errors.append(f"Inspection date for {label} is not zero-padded ISO: {iso!r}")
        else:
            try:
                parsed = datetime.strptime(iso, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Invalid inspection date for {label}: {iso!r}")
            else:
                accepted = {parsed.strftime("%Y-%m-%d"), parsed.strftime("%d.%m.%Y")}
                if date_cell.time_display not in accepted:
                    errors.append(
                        f"Displayed date mismatch for {label}: "
                        f"{date_cell.time_display!r} is not one of {sorted(accepted)}"
                    )

    return name, rank


def check_images(root, parser, errors, notes):
    images_dir = root / "images"
    referenced = sorted({ref.split("?", 1)[0] for ref in parser.image_refs})

    if images_dir.is_dir():
        # Compare against a listing so the check stays correct on case-insensitive
        # filesystems, where Path.is_file() accepts the wrong case.
        on_disk = {p.name for p in images_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES}
    else:
        errors.append(f"Images directory not found: {images_dir}")
        on_disk = set()

    referenced_names = []
    for ref in referenced:
        name = ref[len("images/"):]
        referenced_names.append(name)
        if name not in on_disk:
            errors.append(f"Missing image file: {ref}")

    readme = images_dir / "README.md"
    if not readme.is_file():
        # A repository that keeps its photos out of git has nothing to reconcile.
        # Requiring the inventory anyway would fail every fresh clone.
        if on_disk or referenced:
            errors.append(f"Image inventory not found: {readme}")
        else:
            notes.append("no photos in this checkout, so the image inventory was not checked")
        return len(referenced)

    listed = set(INVENTORY_ENTRY.findall(readme.read_text(encoding="utf-8")))

    unlisted_refs = [n for n in referenced_names if n not in listed]
    if unlisted_refs:
        errors.append("Referenced images absent from images/README.md: " + ", ".join(sorted(unlisted_refs)))

    ghosts = sorted(n for n in listed if n not in on_disk)
    if ghosts:
        errors.append("images/README.md lists files that do not exist: " + ", ".join(ghosts))

    undocumented = sorted(n for n in on_disk if n not in listed)
    if undocumented:
        errors.append(
            "Images on disk but absent from images/README.md: " + ", ".join(undocumented)
        )

    history = sorted(n for n in on_disk if n not in referenced_names and n in listed)
    if history:
        notes.append(f"{len(history)} historical images kept on disk but not displayed")

    return len(referenced)


def main() -> int:
    parser_args = argparse.ArgumentParser(description=__doc__)
    parser_args.add_argument("project_root", nargs="?", default=".")
    parser_args.add_argument(
        "--allow-empty", action="store_true",
        help="permit a personal table with no rows, as left by start_fresh.py",
    )
    args = parser_args.parse_args()

    root = Path(args.project_root).resolve()
    html_path = root / "plants.html"
    if not html_path.is_file():
        print(f"ERROR: tracker not found: {html_path}", file=sys.stderr)
        return 1

    text = html_path.read_text(encoding="utf-8")
    errors: list[str] = []
    notes: list[str] = []

    if '<section id="my-plants"' not in text:
        errors.append('Missing <section id="my-plants">')
    if '<section id="reference"' not in text:
        errors.append('Missing <section id="reference">')

    parser = TrackerParser()
    parser.feed(text)
    parser.close()

    for problem in parser.balance_errors:
        errors.append(f"HTML structure: {problem}")

    if not parser.rows and not args.allow_empty:
        errors.append(
            "No personal plant rows found. If the inventory is intentionally empty "
            "(for example straight after start_fresh.py), pass --allow-empty."
        )

    names: list[str] = []
    ranks: list[int] = []
    sort_keys: list[tuple] = []
    for index, row in enumerate(parser.rows):
        checked = check_row(row, index, errors)
        if checked is None:
            continue
        name, rank = checked
        names.append(name)
        ranks.append(rank)
        sort_keys.append((rank, sort_key(name)))

    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        errors.append("Duplicate personal plant names: " + ", ".join(duplicates))
    if sort_keys != sorted(sort_keys):
        errors.append("Personal rows are not sorted by priority and plant name")

    reference_count = check_images(root, parser, errors, notes)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    plural = "plant" if len(parser.rows) == 1 else "plants"
    print(
        f"OK: {len(parser.rows)} {plural}; "
        f"{ranks.count(0)} high, {ranks.count(1)} medium, {ranks.count(2)} low; "
        f"{reference_count} image references"
    )
    for note in notes:
        print(f"NOTE: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
