# Privacy before publishing

`images/` is gitignored, so **photos are private by default and are never committed.**
Only `images/.gitkeep` is tracked. You have to force-add a photo with `git add -f` to
publish it, which makes that a deliberate act rather than an accident.

Your plant records in `plants.html` *are* committed, so review them for anything personal
before publishing.

If you do choose to publish photos, review each one for:

- faces and reflections;
- mail, labels, screens, documents, and QR codes;
- views through windows or recognizable locations;
- family names or sensitive notes;
- photo metadata you do not want to share.

The bundled photo preparation utility strips metadata with ImageMagick, keeping only the colour profile. It writes to a temporary file and moves it into `images/` only on success, so a failed conversion cannot leave an un-stripped photo in the repository.

Run the repository check before publishing:

```bash
.agents/skills/plant-tracker/scripts/check_photo_metadata.sh .
```

It inspects every format ExifTool recognises — including HEIC and TIFF, not just JPEG and PNG — and reports:

- GPS coordinates;
- camera make, model, and serial numbers;
- owner, artist, and copyright names;
- capture timestamps, which reveal your daily routine;
- embedded thumbnails and previews, which can retain a pre-crop version of the image;
- IPTC and XMP blocks, including location fields.

If it cannot read a file, it fails rather than reporting a clean result. A check that says "OK" without having looked is worse than no check, because it gets trusted.

Deleting a file in a later commit does not remove it from Git history, and on a public
repository anyone can still fetch it from an older commit. Removing an already-pushed
photo needs a history rewrite and a force push, and even then existing clones and forks
keep their copies. Prevention is much cheaper: leave `images/` ignored, or use a private
repository until you are sure.
