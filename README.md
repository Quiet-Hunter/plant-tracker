# Plant Tracker

A local-first, photo-based tracker for houseplants. Send your coding agent one plant or a whole batch of photos; the included `plant-tracker` skill organizes the images, updates the inventory, records care history, and highlights what needs attention.

**Works with both [Codex](https://openai.com/codex/) and [Claude Code](https://claude.com/claude-code).** Both harnesses run the same workflow from the same files, so a tracker maintained with one can be picked up by the other.

The repository is a single static HTML page. There is no database, account, build step, or hosted service. Your photos and notes stay in files you control.

> The tracker ships empty. Your plant records live in `plants.html` and your photos in
> `images/`, which is gitignored — so your collection stays on your machine and is never
> committed, even if you publish your fork.

## What it does

- Keeps one row per physical plant, with multiple photos when useful.
- Maintains a reusable care reference with watering, light, soil, feeding, and notes.
- Sorts work by high, medium, and low priority.
- Accepts single-plant updates or bulk photo imports.
- Records repotting, feeding, treatment, pruning, and other owner-confirmed actions.
- Validates broken image links, duplicate names, priorities, dates, and row order.
- Runs locally in VS Code or any browser and can be published with GitHub Pages.

## Quick start

### 1. Clone and open

```bash
git clone https://github.com/YOUR-USERNAME/plant-tracker.git
cd plant-tracker
code .
```

Open `plants.html` in a browser. A VS Code extension such as Live Server is convenient but not required.

### 2. Reset the inventory (optional)

The tracker already ships empty, so you can skip this. If you ever want to clear an
inventory you have built, this removes your plant rows while keeping the care reference:

```bash
python3 .agents/skills/plant-tracker/scripts/start_fresh.py .
```

Every run writes its own timestamped backup, such as `plants.backup.2026-08-12T104500Z.html`,
so an earlier one is never overwritten. Backups are gitignored.

Add `--clear-reference` to also empty the species care reference and its soil recipes,
leaving nothing of a previous inventory behind:

```bash
python3 .agents/skills/plant-tracker/scripts/start_fresh.py . --clear-reference
```

While the inventory is empty, validation needs `--allow-empty`; without it an empty table
is an error, so a bad edit that drops every row cannot pass silently.

### 3. Add plants with your agent

Open the repository with Codex or Claude Code. Both discover the skill automatically — no
installation step. Invoke it explicitly to make the workflow unambiguous:

| Harness | Invocation |
| --- | --- |
| Codex | `Use $plant-tracker. …` |
| Claude Code | `/plant-tracker`, or `Use the plant-tracker skill. …` |

```text
Use the plant-tracker skill. These 8 photos show a monstera (2 photos), a pothos,
two separate ficus plants (2 photos each), and an unknown succulent.
Build my initial inventory and tell me what needs attention.
```

Or send an ongoing update:

```text
Use the plant-tracker skill. I repotted Ficus 1 today. The first photo is the full
plant and the second shows the roots. Update the tracker and assess the pot.
```

The skill also activates implicitly for requests that clearly involve this repository, but
naming it makes the intended workflow unambiguous.

## Bulk import

You do not need a second skill for adding new plants. `plant-tracker` supports three modes:

1. **Start fresh** — clear an inventory safely, with a timestamped backup.
2. **Bulk import** — map many photos, group multiple views of the same plant, create personal rows, and add missing species references.
3. **Ongoing updates** — update photos, health notes, treatment history, tasks, and priorities.

For the best bulk result, send files in the same order as a list of names and include photo counts. If identification is uncertain, the skill uses a temporary descriptive name and marks the uncertainty instead of guessing silently.

See [Getting Started](docs/GETTING_STARTED.md) and [Photo Workflow](docs/PHOTO_WORKFLOW.md) for detailed examples.

## Repository layout

```text
.
├── .agents/skills/plant-tracker/  # Canonical workflow, contract, and utilities
├── .claude/skills/plant-tracker/  # Claude Code entry point; delegates to .agents/
├── .github/workflows/             # Validation on pushes and pull requests
├── docs/                          # User and maintainer documentation
├── images/                        # Your photos and inventory — gitignored, local only
├── tests/                         # Standard-library test suite for the scripts
├── AGENTS.md                      # Shared repository guidance for every harness
├── CLAUDE.md                      # Claude Code guidance; imports AGENTS.md
├── index.html                     # GitHub Pages entry point
├── plants.html                    # Source of truth and standalone application
└── plants.xlsx                    # Local legacy file; intentionally ignored
```

The workflow and the rules live once, under `.agents/`. Each harness gets a thin entry
point that points back at them, so Codex and Claude Code cannot drift apart. See
[Skill Design](docs/SKILL.md) for the details and for how to add another harness.

## Validate changes

```bash
python3 .agents/skills/plant-tracker/scripts/validate_tracker.py .
python3 .agents/skills/plant-tracker/scripts/sync_image_inventory.py . --check
# add --allow-empty to the validator while your inventory is still empty
python3 .agents/skills/plant-tracker/scripts/check_skill_sync.py .
python3 -m unittest discover -s tests -t tests
```

The validator parses the page and finds rows by their CSS classes, so reformatting the HTML cannot hide them. It checks tag balance, unique names, priority labels against their classes, empty low-priority actions, sort order matching the page's own numeric-aware sort, zero-padded ISO dates, and that `images/` and `images/README.md` agree in both directions.

If the inventory and the folder ever disagree, repair it:

```bash
python3 .agents/skills/plant-tracker/scripts/sync_image_inventory.py .
```

The tests need no packages — they use the standard library. All of these run in GitHub Actions, along with `shellcheck`.

## Image conversion

**[ImageMagick](https://imagemagick.org/) is required** (version 6 or 7; for HEIC sources it must be built with libheif). Install it with `brew install imagemagick` or `apt install imagemagick`.

```bash
.agents/skills/plant-tracker/scripts/prepare_photo.sh \
  /path/to/photo.HEIC monstera 2026-08-12 1 .
```

The utility resizes without ever upscaling, bakes in EXIF rotation, strips every metadata profile while keeping the colour profile, confirms the result is really a JPEG, and only then moves it into `images/` — so a failed run cannot leave an un-stripped photo behind. It also records the new filename in `images/README.md`, creating that inventory if this is your first photo.

Always use it rather than copying a file into `images/` yourself; a hand-copied photo keeps its metadata and will fail validation.

Check every photo for identifying metadata before publishing:

```bash
.agents/skills/plant-tracker/scripts/check_photo_metadata.sh .
```

This needs [ExifTool](https://exiftool.org/) (`brew install exiftool` / `apt install libimage-exiftool-perl`). It covers every format ExifTool recognises, flags GPS, camera model, serial numbers, owner and artist names, capture timestamps and embedded thumbnails, and fails on any file it cannot read rather than calling it clean.

## Publish with GitHub Pages

`images/` is gitignored, so **your photos are never committed and a published copy will show
empty photo frames.** That is deliberate: the default is that your collection stays private.

If you do want a published tracker with visible photos, you are choosing to publish those
photos. Review [Privacy](docs/PRIVACY.md) first, run the metadata check, then force-add only
the images you are happy to make public:

```bash
.agents/skills/plant-tracker/scripts/check_photo_metadata.sh .
git add -f images/some-plant-2026-08-12-1.jpg
```

Prefer a private repository if the photos reveal your home, location, or anything else
personal. Remember that a photo committed once stays in git history even if you delete it
later.

To publish, push to GitHub, open **Settings → Pages**, choose **Deploy from a branch**, and
select the repository root on `main`. `index.html` forwards visitors to the tracker.

## Customize and contribute

- [Customization](docs/CUSTOMIZATION.md) explains labels, languages, fields, and care references.
- [Skill Design](docs/SKILL.md) explains how the shared agent workflow operates and how to support another harness.
- [Privacy](docs/PRIVACY.md) covers photo and metadata checks before publishing.
- [Sharing](docs/SHARING.md) includes ready-to-use launch copy and repository topics.
- [Contributing](CONTRIBUTING.md) covers safe changes and validation.

## License

MIT — see [LICENSE](LICENSE).
