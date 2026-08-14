# Getting started

## Requirements

- Git and a modern browser.
- Python 3 for the reset, validation, and inventory scripts, and for the tests. No Python packages are needed.
- Codex or Claude Code for the photo-driven workflow.
- [ImageMagick](https://imagemagick.org/) 6 or 7 for photo conversion — `brew install imagemagick` or `apt install imagemagick`. For HEIC sources it must be built with libheif.
- [ExifTool](https://exiftool.org/) for the metadata check before publishing — `brew install exiftool` or `apt install libimage-exiftool-perl`.

No JavaScript package installation or web server is required.

## Set up your agent

Open the cloned repository with Codex or Claude Code. Each one finds the skill on its own —
Codex reads `.agents/skills/plant-tracker/`, Claude Code reads `.claude/skills/plant-tracker/`,
and both run the same workflow. There is nothing to install or configure.

Invoke it as `$plant-tracker` in Codex or `/plant-tracker` in Claude Code. "Use the
plant-tracker skill" works in both. The examples below use the neutral phrasing.

## Choose your starting point

### Start adding plants

The tracker ships empty, so there is nothing to clear. Send your agent some photos and it
builds the first rows. Your photos go in `images/`, which is gitignored and stays local.

### Start fresh

Run:

```bash
python3 .agents/skills/plant-tracker/scripts/start_fresh.py .
```

This clears only rows in **My Plants**, preserving the species care reference so its
recipes stay reusable. Add `--clear-reference` to empty that too, leaving nothing of the
previous inventory:

```bash
python3 .agents/skills/plant-tracker/scripts/start_fresh.py . --clear-reference
```

Each run writes its own timestamped backup, such as `plants.backup.2026-08-12T104500Z.html`, and never overwrites an earlier one. Backups are ignored by Git.

To start fresh without a backup:

```bash
python3 .agents/skills/plant-tracker/scripts/start_fresh.py . --no-backup
```

Until you add your first plant, the personal table is empty, and validation needs to be told that is expected:

```bash
python3 .agents/skills/plant-tracker/scripts/validate_tracker.py . --allow-empty
```

Without the flag an empty table is an error. That is deliberate: it means an edit that accidentally drops every row cannot pass validation silently.

## Create an initial inventory

Attach a batch of photos to an agent task. A clear ordered caption produces the most reliable mapping:

```text
Use the plant-tracker skill to build my initial inventory.

1. Monstera — IMG_001 and IMG_002
2. Spider plant — IMG_003
3. Ficus 1 — IMG_004 and IMG_005
4. Ficus 2 — IMG_006
5. Unknown succulent — IMG_007

Create the rows, add missing species to the reference, and list any urgent care.
```

You may also provide a folder or an ordered sequence with counts:

```text
Monstera 2 photos, spider plant, ficus 2 photos, unknown succulent.
```

The skill maps the entire batch before writing. When it cannot identify a plant confidently, it records a temporary descriptive name and asks for confirmation without discarding the rest of the import.

## Send later updates

One message should clearly identify the plant and the event. Multiple images in that message may show the same plant from different angles.

Useful observations include:

- watered or fed;
- repotted, divided, or supported;
- pruned or dead growth removed;
- washed or treated for pests;
- new growth, flowers, yellowing, wilt, or visible insects;
- root and pot photos when assessing repotting.

Example:

```text
Use the plant-tracker skill. This is Ficus 2. I removed all visible scale insects and
washed the leaves today. Update its photos and treatment status. Do not delete
the previous images.
```

## Review the result

Open `plants.html`, switch between **My Plants** and **Plant Reference**, and search by any visible text. Click a photo to open its full-size file.

Run validation after manual edits:

```bash
python3 .agents/skills/plant-tracker/scripts/validate_tracker.py .
```
