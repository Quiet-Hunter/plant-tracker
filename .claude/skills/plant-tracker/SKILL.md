---
name: plant-tracker
description: Create, bootstrap, and maintain this repository's photo-based household plant tracker. Use when the user wants to start a personal inventory, import one or many plant photos, identify or group plants, report watering, feeding, treatment, pruning, repotting, or ask what a tracked plant needs. Inspect the evidence, update plants.html and images consistently, recalculate priorities, validate the tracker, and summarize recommended care. Do not use for generic plant questions that do not involve this repository's tracker.
---

# Plant Tracker

This is the Claude Code entry point for the tracker workflow. The workflow itself is
harness-neutral and lives in one canonical place, so Claude Code and Codex behave
identically.

## Read these first, in order

1. `.agents/skills/plant-tracker/SKILL.md` — the complete workflow: how to map a photo
   batch, inspect and assess evidence, prepare images, update the tracker, and verify.
2. `.agents/skills/plant-tracker/references/tracker-contract.md` — the binding rules:
   table schema, priority rubric, fertilizer guardrails, photo policy, and validation
   requirements.

Read both fully before editing `plants.html`. Do not work from this file alone; it
contains no workflow rules of its own.

## Claude Code specifics

- **Editing:** use `Edit` for surgical changes to `plants.html`. Never rewrite the whole
  file with `Write` — the file holds the entire inventory, and a full rewrite risks
  silently dropping rows. Where the canonical workflow says `apply_patch` (a Codex tool),
  use `Edit`.
- **Row formatting:** each personal `<tr>` is one long single line with no whitespace
  between tags. The validator's regex depends on this. Match the surrounding rows exactly
  and never reflow or pretty-print the table.
- **Images:** read supplied photos with `Read` so you actually see them. Never assess a
  plant from its filename.
- **Scripts:** run via `Bash` from the repository root, using the paths in the canonical
  workflow (for example `python3 .agents/skills/plant-tracker/scripts/validate_tracker.py .`).
- **Parallel work:** when preparing several photos, batch the independent
  `prepare_photo.sh` calls into one message.

## Finish every session by verifying

```bash
python3 .agents/skills/plant-tracker/scripts/validate_tracker.py .
```

Fix every reported error before reporting success. Claiming the tracker is updated
without a passing validator run is a failure, not a shortcut.
