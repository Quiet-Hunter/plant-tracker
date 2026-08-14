---
name: plant-tracker
description: Create, bootstrap, and maintain this repository's photo-based household plant tracker. Use when the user wants to start a personal inventory, import one or many plant photos, identify or group plants, report watering, feeding, treatment, pruning, repotting, or ask what a tracked plant needs. Inspect the evidence, update plants.html and images consistently, recalculate priorities, validate the tracker, and summarize recommended care. Do not use for generic plant questions that do not involve this repository's tracker.
---

# Plant Tracker

Build and maintain the inventory in `plants.html` from photos and owner observations. Treat the HTML tracker as the source of truth and preserve its visual structure.

This file is the canonical, harness-neutral workflow. Codex discovers it directly;
Claude Code reaches it through `.claude/skills/plant-tracker/SKILL.md`. Keep the workflow
here rather than in a harness entry point so both agents behave identically.

## Required context

1. Locate the project root containing `plants.html` and `images/`.
2. Read [references/tracker-contract.md](references/tracker-contract.md) completely before changing the tracker.
3. Inspect the relevant current rows, reference rows, and previous images before assessing changes.
4. Inspect every supplied photo as an image. Never assess a plant from its filename alone.

## Choose the workflow

- **Start fresh:** when the user wants an empty personal inventory, run `scripts/start_fresh.py` and explain that the demo inventory is backed up locally.
- **Bulk import:** when the user supplies many plants or a folder/batch of photos, map all files first, prepare all final images, then add the complete set of personal rows and missing reference rows in one pass.
- **Ongoing update:** when the user supplies observations for already tracked plants, update only the matching rows and any clearly improved reference images.

Use the language the user requests for plant-specific content. When no language is specified, match the existing records. Do not translate existing records unless explicitly asked.

## Workflow

### 1. Map the input

- Treat multiple photos explicitly described as one plant as one observation.
- When the user supplies an ordered list of plant names for a photo batch, map files in that order and respect counts such as “2 photos”.
- For an unnamed batch, group photos using sequence, pot, support, room context, leaf shape, and repeated angles. Give uncertain plants a descriptive temporary name and flag them for confirmation.
- Compare old tracker photos before assigning numbered plants.
- If a mismatch could update the wrong existing plant and cannot be resolved from the files, ask one concise question. For a new bulk import, continue with explicit temporary names rather than blocking the whole batch.

### 2. Inspect and assess

- Inspect every supplied image at useful resolution.
- Separate visible facts from inference. Use cautious wording for pests, diseases, root problems, and uncertain identification.
- Compare with the previous status and record meaningful changes: new growth, yellowing, wilting, pests, flowering, pruning, feeding, repotting, support changes, and soil condition.
- Give only actionable care that follows from the evidence and history. Do not recommend fertilizer to recently repotted, severely weakened, overwatered, drought-stressed, actively infested, or newly rooting plants.
- Do not present a photo-only diagnosis as certain. Recommend a simple confirmation check when it changes treatment.

### 3. Prepare photos

- Use `scripts/prepare_photo.sh` for final tracker images. Pass the source image, plant slug, ISO date, and sequence number. It requires ImageMagick and refuses to leave a half-processed file behind.
- Never copy a photo into `images/` by hand. That skips metadata stripping and fails validation.
- Use lowercase ASCII slugs and the filename format `<slug>-YYYY-MM-DD-<n>.jpg`.
- Keep old image files unless the user explicitly authorizes deletion. Replacing the displayed current photo does not authorize deleting history.
- `prepare_photo.sh` records each new filename in `images/README.md` for you. If the inventory ever drifts, repair it with `scripts/sync_image_inventory.py`.

### 4. Update the tracker

- Apply surgical, targeted edits with your harness's patch or edit tool (`apply_patch` in Codex, `Edit` in Claude Code). Never regenerate `plants.html` wholesale; a full-file rewrite can silently drop rows.
- Keep each personal `<tr>` on a single line with no whitespace between tags, matching the surrounding rows. The validator's row regex depends on this formatting.
- For a new physical plant, add one row to “My Plants”. Number separate plants when names would otherwise collide.
- Add a species to the reference table only when it is missing. Reuse an existing species row for multiple physical plants.
- For ongoing updates, change the current photo, condition, action, priority, and inspection date.
- Use the latest representative full-plant photo in “Plant Reference” when it is clearly better than the current reference photo. Do not overwrite species-level care text with temporary individual symptoms.
- Preserve existing soil recipes and material constraints unless the user changes them.
- Recalculate priorities for all rows and sort by priority, then plant name. Follow the exact contract rules.
- Leave the action cell empty for every low-priority row.

### 5. Verify

Run:

```bash
python3 .agents/skills/plant-tracker/scripts/validate_tracker.py .
```

Add `--allow-empty` only in the window between starting fresh and adding the first plant.

Fix every reported error before finishing. Also visually inspect newly prepared images and confirm that each belongs to the intended plant.

If you changed any bundled script, run the test suite too:

```bash
python3 -m unittest discover -s tests -t tests
```

## Response

- Lead with what was created or updated.
- For bulk imports, report the number of physical plants, species, and unresolved identifications.
- State the observed condition and the immediate action, if any.
- Mention uncertainty when identification or diagnosis is tentative.
- Link to the absolute `plants.html` path.
- Keep routine implementation details out of the response.
