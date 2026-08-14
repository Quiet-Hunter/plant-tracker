# Contributing

Contributions are welcome. Keep the project local-first, dependency-light, and usable as a standalone HTML file.

## Before opening a pull request

1. Do not commit private plant photos or personal care notes without permission.
2. Preserve the existing demo data language unless the change explicitly targets content translation.
3. Keep one row per physical plant and one reference row per species.
4. Run:

   ```bash
   python3 -m unittest discover -s tests -t tests
   python3 .agents/skills/plant-tracker/scripts/validate_tracker.py .
   python3 .agents/skills/plant-tracker/scripts/sync_image_inventory.py . --check
   python3 .agents/skills/plant-tracker/scripts/check_skill_sync.py .
   .agents/skills/plant-tracker/scripts/check_photo_metadata.sh .
   shellcheck .agents/skills/plant-tracker/scripts/*.sh
   ```

5. Open `plants.html` and test both tabs, search, photo links, keyboard navigation, print preview, and narrow-screen layout.

Changes to the table schema must also update the tracker contract, validator, reset utility, and documentation.

## Tests

The suite is in `tests/` and uses only the standard library, so there is nothing to install:

```bash
python3 -m unittest discover -s tests -t tests
```

`tests/tracker_fixture.py` builds a minimal valid tracker on disk, and `tests/image_fixture.py` builds real images with known metadata. Tests requiring ImageMagick or ExifTool skip themselves when the tool is missing, so a partial toolchain still gives a useful run.

Please add a failing test before fixing a bug in any bundled script. Several of the defects these tests cover were cases where a script reported success without having checked anything, which is exactly the class of bug that reappears silently.

## Changing the agent skill

The workflow is canonical in `.agents/skills/plant-tracker/` and each harness has a thin
entry point that delegates to it. Put shared rules in the canonical skill or the contract,
never in a harness entry point, and keep the frontmatter `description` identical across
entry points. `check_skill_sync.py` enforces this. See
[Skill Design](docs/SKILL.md) for the full rationale and for how to add a harness.
