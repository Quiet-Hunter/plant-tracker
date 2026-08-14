"""Build minimal tracker projects on disk for tests.

Tests need a `plants.html` that the real validator accepts, small enough that a
single mutation isolates a single rule. `build_project` writes one, plus the
`images/` files and `images/README.md` inventory the validator cross-checks.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".agents" / "skills" / "plant-tracker" / "scripts"

PRIORITY_CLASS = {
    "High": "high", "Medium": "medium", "Low": "",
    "Высокий": "high", "Средний": "medium", "Низкий": "",
}

# A 1x1 JPEG. Tests only need the file to exist and be a real image.
TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300ffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    "ffffffffffffffffffffffffffffffffffc00011080001000101011100ffc40014"
    "0001000000000000000000000000000000ffda0008010100003f0037ffd9"
)


class Plant:
    """One personal row."""

    def __init__(self, name, species="Species", condition="Fine", action=None,
                 priority="Low", date="2026-08-11", display=None, images=None,
                 photo_cell_class="photo-cell", name_cell='<td class="plant-name">'):
        self.name = name
        self.species = species
        self.condition = condition
        self.priority = priority
        self.date = date
        self.display = display if display is not None else date
        self.photo_cell_class = photo_cell_class
        self.name_cell = name_cell
        self.images = images if images is not None else [f"{slugify(name)}-{date}-1.jpg"]
        # Low priority requires an empty action cell, so default accordingly.
        if action is None:
            action = "" if priority in ("Low", "Низкий") else "Water it"
        self.action = action

    def render(self):
        frames = "".join(
            f'<div class="photo-frame"><a href="images/{f}" target="_blank" rel="noopener">'
            f'<img src="images/{f}" alt="{self.name}" loading="lazy"></a>'
            f'<span class="photo-placeholder" hidden>{f}</span></div>'
            for f in self.images
        )
        if len(self.images) > 1:
            photo = f'<td class="{self.photo_cell_class} multiple"><div class="photo-gallery">{frames}</div></td>'
        else:
            photo = f'<td class="{self.photo_cell_class}">{frames}</td>'
        css = PRIORITY_CLASS.get(self.priority, "")
        span_class = f"priority {css}".strip()
        return (
            f"<tr>{photo}{self.name_cell}{self.name}</td>"
            f"<td>{self.species}</td><td>{self.condition}</td><td>{self.action}</td>"
            f'<td><span class="{span_class}">{self.priority}</span></td>'
            f'<td class="last-inspection"><time datetime="{self.date}">{self.display}</time></td></tr>'
        )


def slugify(name):
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")


HEAD = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Plant Tracker</title></head>
<body>
"""

MY_PLANTS_OPEN = """    <section id="my-plants" role="tabpanel" aria-labelledby="tab-my-plants">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Photo</th>
              <th scope="col">My plant</th>
              <th scope="col">Species</th>
              <th scope="col">Condition</th>
              <th scope="col">What to do</th>
              <th scope="col">Priority</th>
              <th scope="col">Last inspection</th>
            </tr>
          </thead>
          <tbody>
"""

MY_PLANTS_CLOSE = """          </tbody>
        </table>
        <p class="empty-state" hidden>Nothing found.</p>
      </div>
    </section>

"""

REFERENCE = """    <section id="reference" role="tabpanel" aria-labelledby="tab-reference" hidden>
      <div class="table-wrap">
        <table>
          <thead><tr><th scope="col">Photo</th><th scope="col">Species</th></tr></thead>
          <tbody>
          </tbody>
        </table>
        <p class="empty-state" hidden>Nothing found.</p>
      </div>
    </section>
  </body>
</html>
"""


def render_tracker(plants):
    rows = "".join(f"            {p.render()}\n" for p in plants)
    return HEAD + MY_PLANTS_OPEN + rows + MY_PLANTS_CLOSE + REFERENCE


def build_project(root, plants=None, extra_images=(), inventory=None, tracker=None):
    """Write a complete, valid tracker project into `root` and return the path."""
    root = Path(root)
    if plants is None:
        plants = [Plant("Aloe"), Plant("Basil")]
    (root / "images").mkdir(parents=True, exist_ok=True)

    text = tracker if tracker is not None else render_tracker(plants)
    (root / "plants.html").write_text(text, encoding="utf-8")

    referenced = [img for p in plants for img in p.images]
    for name in list(referenced) + list(extra_images):
        (root / "images" / name).write_bytes(TINY_JPEG)

    listed = inventory if inventory is not None else list(referenced) + list(extra_images)
    lines = ["# Plant photos", "", "Current image inventory:", ""]
    lines += [f"- `{name}`" for name in listed]
    (root / "images" / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def run_script(name, *args):
    """Run a bundled script and return the CompletedProcess."""
    path = SCRIPTS / name
    cmd = [sys.executable, str(path)] if path.suffix == ".py" else [str(path)]
    return subprocess.run(
        cmd + [str(a) for a in args], capture_output=True, text=True
    )


def validate(root, *args):
    return run_script("validate_tracker.py", root, *args)
