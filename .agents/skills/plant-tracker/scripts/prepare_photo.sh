#!/usr/bin/env bash
# Convert a source photo into a final tracker image: resized, metadata stripped,
# and named to the project convention.
#
# Three things here are deliberate:
#
#   * ImageMagick is required. The previous macOS `sips` fallback produced
#     materially different output (rotation left as a tag rather than applied,
#     small images upscaled, EXIF retained) and it needed ExifTool anyway, which
#     macOS does not ship — so it never actually saved anyone an install.
#   * Conversion writes to a temporary file and only moves it into place on
#     success, so a failure can never leave an un-stripped photo in images/.
#   * `+profile '!icc,*'` removes every metadata profile but keeps the colour
#     profile. Plain `-strip` drops it too, which silently reinterprets a
#     wide-gamut photo as sRGB and shifts the leaf colours a diagnosis relies on.
set -euo pipefail

usage() {
  echo "Usage: $0 SOURCE_IMAGE PLANT_SLUG YYYY-MM-DD INDEX [PROJECT_ROOT]" >&2
  exit 2
}

[[ $# -ge 4 && $# -le 5 ]] || usage

source_image=$1
plant_slug=$2
photo_date=$3
photo_index=$4
project_root=${5:-$(pwd)}

MAX_EDGE=2200
QUALITY=82

[[ -f "$source_image" ]] || { echo "Source image not found: $source_image" >&2; exit 1; }
[[ "$plant_slug" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "Plant slug must be lowercase ASCII hyphen-case" >&2; exit 1; }
[[ "$photo_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "Date must use YYYY-MM-DD" >&2; exit 1; }
[[ "$photo_index" =~ ^[1-9][0-9]*$ ]] || { echo "Index must be a positive integer" >&2; exit 1; }

images_dir="$project_root/images"
[[ -d "$images_dir" ]] || { echo "Images directory not found: $images_dir" >&2; exit 1; }

filename="${plant_slug}-${photo_date}-${photo_index}.jpg"
destination="$images_dir/$filename"
[[ ! -e "$destination" ]] || { echo "Refusing to overwrite existing image: $destination" >&2; exit 1; }

# ImageMagick 7 provides `magick`; ImageMagick 6, still standard on Debian and
# Ubuntu, provides only `convert` and `identify`.
if command -v magick >/dev/null 2>&1; then
  convert_cmd=(magick)
elif command -v convert >/dev/null 2>&1; then
  convert_cmd=(convert)
else
  echo "ImageMagick is required. Install it with 'brew install imagemagick'," >&2
  echo "'apt install imagemagick', or from https://imagemagick.org/." >&2
  echo "For HEIC sources it must be built with libheif support." >&2
  exit 1
fi

work_file=$(mktemp "$images_dir/.prepare-XXXXXX")
trap 'rm -f "$work_file"' EXIT

# [0] takes the first frame, so a multi-page or animated source cannot fan out
# into several numbered files while the script reports the single name it printed.
if ! "${convert_cmd[@]}" "${source_image}[0]" \
      -auto-orient \
      -resize "${MAX_EDGE}x${MAX_EDGE}>" \
      -quality "$QUALITY" \
      +profile '!icc,*' \
      "jpg:$work_file" 2>/dev/null; then
  echo "Could not convert $source_image." >&2
  echo "If it is a HEIC file, ImageMagick needs libheif support." >&2
  exit 1
fi

[[ -s "$work_file" ]] || { echo "Conversion produced an empty file for $source_image" >&2; exit 1; }

# Confirm the result really is a JPEG by its signature, rather than trusting the
# converter's exit status. This needs no extra tool, so it works wherever
# ImageMagick 6's `convert` exists without a matching `identify`.
magic=$(od -An -N3 -tx1 < "$work_file" | tr -d ' \n')
[[ "$magic" == "ffd8ff" ]] || {
  echo "Conversion did not produce a JPEG for $source_image" >&2
  exit 1
}

mv "$work_file" "$destination"
trap - EXIT
chmod 644 "$destination"

# The validator treats an image in images/ that is absent from the inventory as an
# error, so record it here rather than leaving the tracker in a failing state.
# The inventory is not committed (photos are private), so a fresh clone has none.
inventory="$images_dir/README.md"
if [[ ! -f "$inventory" ]]; then
  cat > "$inventory" <<'INVENTORY_HEADER'
# Plant photos

Final tracker photos live in this folder. `plants.html` displays the files its image
paths reference. Add photos with `prepare_photo.sh`, which strips metadata and records
them below; never copy a file here by hand.

This file and the photos beside it are ignored by Git, so your images stay private.

Current image inventory:

INVENTORY_HEADER
fi

if [[ -f "$inventory" ]] && ! grep -qF -- "\`$filename\`" "$inventory"; then
  last_entry=$(grep -n '^- `' "$inventory" | tail -1 | cut -d: -f1 || true)
  if [[ -n "$last_entry" ]]; then
    inventory_tmp=$(mktemp "$images_dir/.inventory-XXXXXX")
    awk -v line="$last_entry" -v entry="- \`$filename\`" \
      'NR == line { print; print entry; next } { print }' "$inventory" > "$inventory_tmp"
    mv "$inventory_tmp" "$inventory"
    chmod 644 "$inventory"
  else
    # shellcheck disable=SC2016  # the backticks are literal Markdown, not a subshell
    printf -- '- `%s`\n' "$filename" >> "$inventory"
  fi
fi

echo "$destination"
