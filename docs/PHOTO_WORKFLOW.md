# Photo workflow

## One row means one physical plant

Several photos can belong to one plant. Two separate pots of the same species get separate personal rows, for example `Ficus 1` and `Ficus 2`, while both reuse one `Ficus microcarpa` reference entry.

## Recommended photo set

For a routine update, one full-plant photo is usually enough. Add detail shots only when they provide distinct evidence:

- full plant and pot;
- upper and lower leaf surfaces;
- stem junctions or suspected pests;
- soil surface;
- exposed roots and the proposed pot during repotting.

Avoid including faces, mail, screens, precise views outside windows, or other private details if you plan to publish the repository.

## File processing

Final images are stored in `images/` as JPEG files with a maximum dimension near 2200 pixels and the pattern:

```text
<plant-slug>-YYYY-MM-DD-<sequence>.jpg
```

Example:

```text
ficus-2-2026-08-12-1.jpg
ficus-2-2026-08-12-2.jpg
```

The preparation script refuses to overwrite an existing filename, and it records each new file in `images/README.md` for you.

`images/` and `images/README.md` must agree in both directions: an image on disk that is not listed is an error, and so is a listing with no file behind it. That catches photos which arrived without going through the script — the ones that still carry their metadata. If the two drift apart, repair the list:

```bash
python3 .agents/skills/plant-tracker/scripts/sync_image_inventory.py .
```

Always convert through `prepare_photo.sh` rather than copying a file into `images/` yourself. It requires ImageMagick, and it:

- resizes down to a 2200 px long edge but never scales a small photo up;
- applies EXIF rotation to the pixels, so the image is upright even in viewers that ignore metadata;
- removes every metadata profile while keeping the colour profile, so leaf colours stay accurate;
- verifies the output really is a JPEG, and writes it to a temporary file that is only moved into `images/` on success — a failed run cannot leave an un-stripped photo behind.

## Historical photos

Updating the displayed photo does not automatically authorize deletion. Historical images can be useful for comparing growth and treatment results. Ask explicitly if you want them removed, and review Git history before publishing if they contain private information.

## Diagnostic limits

Photos can support a care assessment but not every diagnosis. The skill distinguishes visible signs from inference and suggests a confirmation check when it would change treatment. Root health cannot be established from foliage alone.
