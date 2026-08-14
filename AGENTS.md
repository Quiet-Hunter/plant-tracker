# Repository guidance

This file is shared by every supported agent harness. Codex reads it directly; Claude Code
imports it from `CLAUDE.md`. Put harness-neutral rules here and harness-specific notes in
the entry points.

- Use the `plant-tracker` skill for inventory creation, bulk photo imports, and ongoing
  plant updates. Invoke it as `$plant-tracker` in Codex or `/plant-tracker` in Claude Code.
- The workflow lives at `.agents/skills/plant-tracker/SKILL.md` and the binding rules at
  `.agents/skills/plant-tracker/references/tracker-contract.md`. Read both before editing
  the tracker.
- Treat `plants.html` as the source of truth; `plants.xlsx` is legacy and intentionally ignored.
- `images/` and `images/README.md` are gitignored: the owner's photos are private and
  must never be committed. Only `images/.gitkeep` is tracked. Never `git add -f` a photo.
- Edit `plants.html` surgically. Never regenerate the whole file, and keep each personal
  `<tr>` on one line with no whitespace between tags.
- Preserve the language of existing plant records unless translation is explicitly requested.
- Keep one personal row per physical plant and one reference row per species.
- Do not delete historical photos without explicit authorization.
- Produce every tracker image with `prepare_photo.sh`; never copy one into `images/` by
  hand, because that skips metadata stripping and fails validation.
- Run `python3 .agents/skills/plant-tracker/scripts/validate_tracker.py .` after tracker
  changes. Add `--allow-empty` only while the inventory is intentionally empty.
- Run `.agents/skills/plant-tracker/scripts/check_photo_metadata.sh .` before publishing photos.
- Run `python3 .agents/skills/plant-tracker/scripts/check_skill_sync.py .` after changing
  either skill entry point.
- Run `python3 -m unittest discover -s tests -t tests` after changing any bundled script.
