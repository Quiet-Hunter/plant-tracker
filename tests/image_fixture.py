"""Helpers for building real image files with known metadata in tests."""
from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".agents" / "skills" / "plant-tracker" / "scripts"

EXIFTOOL = shutil.which("exiftool")
IMAGEMAGICK = shutil.which("magick") or shutil.which("convert")

requires_exiftool = unittest.skipUnless(EXIFTOOL, "ExifTool is not installed")
requires_imagemagick = unittest.skipUnless(IMAGEMAGICK, "ImageMagick is not installed")
requires_non_root = unittest.skipIf(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    "permission tests are meaningless as root",
)


def make_image(path, width=40, height=30, extra_args=()):
    """Create a real image at `path` using ImageMagick. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [IMAGEMAGICK, "-size", f"{width}x{height}", "gradient:green-yellow"]
    cmd += list(extra_args)
    cmd += [str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def supports_format(suffix):
    """Whether ImageMagick on this machine can write the given container."""
    if not IMAGEMAGICK:
        return False
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        probe = Path(d) / f"probe{suffix}"
        try:
            make_image(probe)
        except subprocess.CalledProcessError:
            return False
        return probe.is_file() and probe.stat().st_size > 0


def set_tags(path, numeric=False, **tags):
    """Write metadata tags onto an existing image.

    Pass numeric=True for tags whose raw value is an enum, such as Orientation,
    which ExifTool otherwise expects as a description like "Rotate 90 CW".
    """
    args = [EXIFTOOL, "-q", "-overwrite_original"]
    if numeric:
        args.append("-n")
    args += [f"-{name.replace('_', ':')}={value}" for name, value in tags.items()]
    args.append(str(path))
    subprocess.run(args, check=True, capture_output=True)


def read_tags(path, *names):
    """Return {tag: value} for the requested tags that are actually present."""
    args = [EXIFTOOL, "-q", "-q", "-s", "-s"] + [f"-{n}" for n in names] + [str(path)]
    result = subprocess.run(args, capture_output=True, text=True)
    found = {}
    for line in result.stdout.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            found[key.strip()] = value.strip()
    return found


def all_tag_groups(path):
    """Return the set of metadata group names present in the file."""
    result = subprocess.run(
        [EXIFTOOL, "-q", "-q", "-G1", "-s", "-a", str(path)],
        capture_output=True, text=True,
    )
    groups = set()
    for line in result.stdout.splitlines():
        if line.startswith("["):
            groups.add(line[1:line.index("]")])
    return groups


def dimensions(path):
    tags = read_tags(path, "ImageWidth", "ImageHeight")
    return int(tags["ImageWidth"]), int(tags["ImageHeight"])


def run_script(name, *args, env=None):
    merged = dict(os.environ)
    if env:
        merged.update(env)
    return subprocess.run(
        [str(SCRIPTS / name)] + [str(a) for a in args],
        capture_output=True, text=True, env=merged,
    )
