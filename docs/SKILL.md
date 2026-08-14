# How the agent skill works

The repository includes one focused skill: `plant-tracker`. A separate "add plants" skill is unnecessary because creation and maintenance share the same evidence mapping, photo processing, HTML contract, and validation.

The skill runs on both Codex and Claude Code.

## Supported harnesses

| Harness | Discovers | Invoke with |
| --- | --- | --- |
| Codex | `.agents/skills/plant-tracker/SKILL.md` | `$plant-tracker` |
| Claude Code | `.claude/skills/plant-tracker/SKILL.md` | `/plant-tracker` |

Neither requires an install step. Open the repository and the skill is available.

Repository-wide guidance follows the same pattern: `AGENTS.md` holds the shared rules, and `CLAUDE.md` imports it with `@AGENTS.md` so Claude Code loads the same text rather than a copy of it.

## One workflow, two doors

Each harness looks for skills in its own directory, so the repository needs a file in each. Duplicating the workflow into both would guarantee drift — one copy gets a fix, the other silently keeps the old rule. Instead:

- `.agents/skills/plant-tracker/SKILL.md` is **canonical**. It holds the entire workflow and is written to be harness-neutral.
- `.agents/skills/plant-tracker/references/tracker-contract.md` holds the binding rules: table schema, priority rubric, fertilizer guardrails, photo policy, and validation requirements.
- `.claude/skills/plant-tracker/SKILL.md` is a **thin entry point**. It carries only Claude-Code-specific mechanics (use `Edit` rather than `apply_patch`, read photos with `Read`) and directs the agent to read the two canonical files.

The frontmatter `description` is the one thing that must be duplicated, because it is what each harness matches a request against. A drift guard enforces that:

```bash
python3 .agents/skills/plant-tracker/scripts/check_skill_sync.py .
```

It fails if an entry point is missing, if a `name` or `description` is absent, if the two descriptions differ, or if the Claude entry point stops pointing at the canonical files. It runs in CI.

## Adding another harness

1. Create that harness's skill file in the directory it scans.
2. Copy the frontmatter `name` and `description` verbatim from the canonical skill.
3. In the body, record only what is specific to that harness and point at `.agents/skills/plant-tracker/SKILL.md` and the contract.
4. Add the new path to `ENTRY_POINTS` in `check_skill_sync.py`.
5. If the harness reads its own root guidance file, have it import `AGENTS.md` rather than restate it.

Never move workflow rules into a harness entry point. If a rule applies to every agent, it belongs in the canonical skill or the contract.

## Modes

### Start fresh

Clears personal rows with a recoverable backup and leaves the care reference intact.

### Bulk import

Maps all supplied files before editing, groups multiple photos of one plant, creates one row per physical plant, adds only missing species references, and reports uncertain identifications.

### Ongoing update

Compares new evidence with existing photos and history, records confirmed owner actions, updates actionable care, recalculates all priorities, and optionally replaces a species reference photo with a better full-plant image.

## Repository contract

The skill treats `plants.html` as the source of truth. It preserves old images unless deletion is explicitly authorized, keeps low-priority action cells empty, uses cautious language for photo-only diagnoses, and runs the bundled validator before completion.

It also edits surgically. `plants.html` holds the whole inventory, so a full-file rewrite can silently drop rows, and each personal `<tr>` must stay on one line with no whitespace between tags because the validator's row regex depends on that formatting.

The full operational contract lives at `.agents/skills/plant-tracker/references/tracker-contract.md`.

## Invocation examples

```text
Use the plant-tracker skill to start fresh and import these 12 plant photos.
```

```text
Use the plant-tracker skill. I watered and fed the orchids today. Update their history.
```

```text
Use the plant-tracker skill. What does this tracked plant need, and should I repot it?
```

Both harnesses can discover the skill automatically when a request clearly matches its description. Explicit invocation is recommended in public instructions because it makes the workflow predictable.
