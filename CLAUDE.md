# Plant Tracker — Claude Code

The repository guidance is shared with other agent harnesses and lives in `AGENTS.md`.
It is imported here so Claude Code loads it automatically:

@AGENTS.md

## Claude Code specifics

- The tracker workflow is exposed as the `plant-tracker` skill. Invoke it with
  `/plant-tracker`, or just describe the task — the skill description covers photo
  imports, care updates, and "what does this plant need" questions.
- `.claude/skills/plant-tracker/SKILL.md` is a thin entry point. The canonical workflow is
  `.agents/skills/plant-tracker/SKILL.md` and the binding rules are
  `.agents/skills/plant-tracker/references/tracker-contract.md`. Read both before editing
  the tracker.
- Use `Edit`, never `Write`, on `plants.html`. A full-file rewrite can silently drop rows.
- Keep each personal `<tr>` on one line with no whitespace between tags; the validator's
  regex depends on it.
- `.agents/` and `.claude/` must stay in sync. After changing either skill entry point,
  run `python3 .agents/skills/plant-tracker/scripts/check_skill_sync.py .`.
