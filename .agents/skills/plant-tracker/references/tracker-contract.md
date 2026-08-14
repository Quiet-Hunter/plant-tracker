# Plant tracker contract

## Source of truth

- Project file: `plants.html`.
- Final images: `images/` — **gitignored.** The owner's photos are private and must never
  be committed. Only `images/.gitkeep` is tracked. Never `git add -f` a photo unless the
  owner explicitly asks to publish that specific file.
- Image inventory: `images/README.md` — also gitignored, created on demand by
  `prepare_photo.sh` or `sync_image_inventory.py`.
- `plants.xls` and `plants.xlsx` are not authoritative unless the user explicitly asks to synchronize them.

## Personal table schema

The first table, inside `<section id="my-plants">`, contains seven columns:

1. Photo
2. My plant
3. Species
4. Condition
5. What to do
6. Priority
7. Last inspection

Keep one `<tr>...</tr>` per physical plant. Number plants with the same common name so every displayed personal name remains unique.

Use an existing row as the markup template. Preserve `photo-cell`, `photo-frame`, optional `photo-gallery`, `plant-name`, `last-inspection`, links, lazy loading, and hidden filename fallbacks.

## Bootstrap and bulk import

- `scripts/start_fresh.py` clears only personal inventory rows. It keeps the reference table, UI, and image files, and every run writes its own timestamped backup (`plants.backup.<timestamp>.html`), so an earlier backup is never overwritten.
- Starting fresh keeps the species reference and its photos by default. Say so, and offer
  `--clear-reference`, which also empties the reference table and the soil recipe map so
  nothing of a previous inventory remains.
- Between starting fresh and adding the first plant, the personal table is legitimately empty. Validate with `--allow-empty` during that window; without the flag an empty table is an error, because an empty table is otherwise indistinguishable from an edit that dropped every row.
- Map the entire batch before editing. An ordered list of names and photo counts is authoritative.
- Without a list, group photos conservatively. A changed pot, background, or angle alone does not prove a new plant.
- Create one personal row per physical plant and one reference row per species.
- Temporary names are acceptable for uncertain identifications. Mark uncertainty in the species or condition text instead of inventing certainty.
- Default new record content to English. Match another language when the user's request or the existing inventory establishes it.

## Observation rules

- Write the condition as a dated factual update followed by a concise comparison with the previous state.
- Record owner-confirmed actions as facts.
- Do not infer root health from foliage alone.
- Treat old leaf damage as persistent historical damage; do not report it as active progression without new evidence.
- For suspected pests, record visible signs and a confirmation method. Active treatment remains pending until the user reports completion and follow-up is reassuring.
- Keep care recommendations specific to the plant's current state, not a generic care encyclopedia.

## Priority rules

Assign exactly one semantic priority using the matching CSS class:

- `High` / class `priority high`: active or suspected pest/disease treatment, urgent rescue, or another problem needing prompt intervention.
- `Medium` / class `priority medium`: a concrete, safe, currently pending task such as feeding, repotting a stable plant, pruning, weeding, loosening soil, support, or rejuvenation.
- `Low` / class `priority`: no action is currently required or feasible work has been completed.

Legacy Russian labels `Высокий`, `Средний`, and `Низкий` remain valid and must not be translated unless requested.

For every low-priority row, the action cell must be empty: `<td></td>`.

When the user gives explicit priority instructions, those override the general rubric.

Sort personal rows by priority rank (high, medium, low) and then displayed plant name using case-insensitive Unicode order.

## Fertilizer guardrails

Recommend feeding only when the plant is established, hydrated, not actively infested, not severely weakened, and showing active growth or flowering.

Do not recommend feeding when any of the following apply:

- repotted within roughly 3–6 weeks;
- active pest treatment or quarantine;
- severe wilt, root concern, prolonged wet soil, or recent drought collapse;
- unrooted or newly rooting cutting;
- dormant or clearly stalled plant.

Prefer fertilizer on already moist substrate. Use a conservative fraction of the label dose when product strength is unknown. Feeding already reported for the current date is completed work, not a pending medium-priority task.

## Photo policy

- Always produce final images with `scripts/prepare_photo.sh`. It requires ImageMagick 6 or 7, resizes without upscaling, bakes in any EXIF rotation, removes every metadata profile while keeping the colour profile, verifies the result really is a JPEG, and only then moves it into `images/`. A failed run leaves nothing behind.
- Never hand-copy a photo into `images/`. Doing so bypasses metadata stripping, and the validator will fail because the file is not in the inventory.
- Store final display images as JPEG, maximum dimension about 2200 px, quality about 82%.
- Name files `<slug>-YYYY-MM-DD-<n>.jpg`.
- Use one current photo when it represents the update; use a gallery only when multiple views add distinct evidence.
- Update the reference table with a representative full-plant image when useful.
- Never delete historical photos without explicit authorization. Resolve exact files first and prefer a recoverable trash operation.
- Do not use image generation or diagnostic-altering edits on plant photos.

## Soil resources

Read the existing species recipe before proposing a mix. Use the owner's available materials and do not silently invent unavailable amendments. Ask which materials they have before generating recipes for a new inventory; common ones are universal indoor-plant soil, perlite, expanded clay, and orchid bark.

## Validation requirements

Run `scripts/validate_tracker.py` and fix every error before finishing. It checks:

- the HTML tags balance;
- at least one personal row exists, unless `--allow-empty` is passed;
- every row exposes a `plant-name` cell, a `priority` span, and a `last-inspection` time;
- personal plant names are unique;
- every priority label has the matching CSS class;
- all low-priority action cells are empty;
- personal rows are sorted by priority, then by name using the same numeric-aware order as the page (so `Ficus 2` precedes `Ficus 10`);
- inspection dates use zero-padded ISO `datetime="YYYY-MM-DD"` and display either `YYYY-MM-DD` or the legacy `DD.MM.YYYY` format;
- every referenced image exists on disk, with exact case;
- `images/README.md` and the files in `images/` agree in both directions.

Rows are located by parsing the document and matching cells by class, so reformatting the file no longer hides them. Even so, keep rows on one line to match the surrounding markup and keep diffs readable.

`scripts/sync_image_inventory.py` repairs the inventory when the two sides disagree; `--check` reports drift without editing.

Run `scripts/check_photo_metadata.sh` before publishing. It inspects every format ExifTool recognises, fails on any file it cannot read rather than skipping it, and flags GPS, camera make and model, serial numbers, owner and artist names, capture timestamps, embedded thumbnails, and IPTC/XMP blocks. Colour profiles are allowed.
