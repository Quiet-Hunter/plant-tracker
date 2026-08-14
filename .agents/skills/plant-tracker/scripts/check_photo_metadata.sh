#!/usr/bin/env bash
# Check tracker photos for metadata that would identify a person, device, place,
# or time if the repository were published.
#
# Two properties matter more than speed here. Unreadable files are reported as
# failures rather than skipped: the previous version passed the whole directory to
# one exiftool call with `|| true`, which could not tell "no matches" from "could
# not open the file", so an unreadable photo was reported as clean. And every
# format exiftool recognises is inspected, not just four extensions, because a
# stray HEIC dropped in before conversion is exactly the leak this guards against.
set -euo pipefail

usage() {
  echo "Usage: $0 [PROJECT_ROOT]" >&2
  exit 2
}

[[ $# -le 1 ]] || usage

project_root=${1:-$(pwd)}
images_dir="$project_root/images"

[[ -d "$images_dir" ]] || { echo "Images directory not found: $images_dir" >&2; exit 1; }
command -v exiftool >/dev/null 2>&1 || { echo "ExifTool is required for the metadata check" >&2; exit 1; }

# Whole metadata groups that should never survive the photo pipeline. ICC_Profile
# is deliberately absent: colour profiles are worth keeping and identify nobody.
# Everything requested below counts as a finding, so only add tags that are leaks.
sensitive_args=(
  -GPS:all -MakerNotes:all -IPTC:all -XMP:all -Photoshop:all
  -Make -Model -HostComputer -Software
  -SerialNumber -InternalSerialNumber -LensSerialNumber -BodySerialNumber
  -CameraSerialNumber -LensMake -LensModel
  -OwnerName -CameraOwnerName -Artist -Copyright
  -DateTimeOriginal -CreateDate
  -UserComment -ImageDescription
  -ThumbnailImage -PreviewImage -OtherImage
)

# Bookkeeping tags requested alongside the sensitive ones. Directory comes first so
# it delimits each file's block; any line that is not one of these three is a leak.
bookkeeping_args=(-Directory -FileName -MIMEType)

unreadable=""
while IFS= read -r file; do
  [[ -r "$file" ]] || unreadable="${unreadable}  ${file#"$project_root"/}"$'\n'
done < <(find "$images_dir" -type f | LC_ALL=C sort)

stderr_file=$(mktemp)
trap 'rm -f "$stderr_file"' EXIT

set +e
report=$(exiftool -q -q -m -a -s -s -r \
  "${bookkeeping_args[@]}" "${sensitive_args[@]}" \
  "$images_dir" 2>"$stderr_file")
exiftool_status=$?
set -e

# ExifTool exits 1 on a real error and 2 when nothing matched; only 0 and 2 are
# acceptable here, and any stderr output is treated as a failure to inspect.
if [[ $exiftool_status -ne 0 && $exiftool_status -ne 2 ]]; then
  echo "ExifTool failed with exit $exiftool_status; the images were not fully inspected." >&2
  cat "$stderr_file" >&2
  exit 1
fi

scanned=0
skipped=0
leaks=""
current=""
current_mime=""
current_findings=""

flush_current() {
  [[ -n "$current" ]] || return 0
  case "$current_mime" in
    image/*)
      scanned=$((scanned + 1))
      if [[ -n "$current_findings" ]]; then
        leaks="${leaks}  ${current}"$'\n'"${current_findings}"
      fi
      ;;
    *) skipped=$((skipped + 1)) ;;
  esac
  current=""
  current_mime=""
  current_findings=""
}

while IFS= read -r line; do
  case "$line" in
    "Directory: "*)
      flush_current
      current="${line#Directory: }"
      ;;
    "FileName: "*)
      current="${current}/${line#FileName: }"
      current="${current#"$project_root"/}"
      ;;
    "MIMEType: "*)
      current_mime="${line#MIMEType: }"
      ;;
    *)
      [[ -z "$line" ]] || current_findings="${current_findings}      ${line}"$'\n'
      ;;
  esac
done <<EOF
$report
EOF
flush_current

status=0

if [[ -n "$unreadable" ]]; then
  {
    echo "Could not read every image, so this check cannot report a clean result:"
    printf '%s' "$unreadable"
  } >&2
  status=1
fi

if [[ -s "$stderr_file" ]]; then
  {
    echo "ExifTool reported problems while reading images:"
    sed 's/^/  /' "$stderr_file"
  } >&2
  status=1
fi

if [[ -n "$leaks" ]]; then
  {
    echo "Identifying metadata found:"
    printf '%s' "$leaks"
    echo "Re-run these photos through prepare_photo.sh, which strips metadata."
  } >&2
  status=1
fi

[[ $status -eq 0 ]] || exit "$status"

plural="s"
[[ $scanned -ne 1 ]] || plural=""
summary="OK: no identifying metadata in ${scanned} image${plural}"
[[ $skipped -eq 0 ]] || summary="${summary} (${skipped} non-image file(s) ignored)"
echo "$summary"
