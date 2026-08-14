"""Behaviour tests for prepare_photo.sh.

This script is where private metadata is supposed to be destroyed, so the tests
that matter most are the ones asserting it cannot leave a half-processed file
behind, and that what it writes is actually the image it claims.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from image_fixture import (
    IMAGEMAGICK,
    SCRIPTS,
    all_tag_groups,
    dimensions,
    make_image,
    read_tags,
    requires_exiftool,
    requires_imagemagick,
    set_tags,
    supports_format,
)

STUB_FAILING_EXIFTOOL = "#!/bin/sh\nexit 1\n"

# Everything prepare_photo.sh needs from PATH, so an isolated PATH can still run it.
# "bash" is required because the shebang resolves it through `env`.
SHELL_UTILITIES = (
    "bash", "awk", "chmod", "cut", "grep", "mktemp", "mv", "od", "rm", "tail", "tr",
)


@requires_imagemagick
@requires_exiftool
class PreparePhotoTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "images").mkdir()
        (self.root / "images" / "README.md").write_text(
            "# Plant photos\n\nCurrent image inventory:\n\n", encoding="utf-8"
        )
        self.source_dir = self.root / "src"
        self.source_dir.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def prepare(self, source, slug="aloe", date="2026-08-12", index=1, path=None):
        env = dict(os.environ)
        if path is not None:
            env["PATH"] = path
        return subprocess.run(
            [str(SCRIPTS / "prepare_photo.sh"), str(source), slug, date, str(index), str(self.root)],
            capture_output=True, text=True, env=env,
        )

    def isolated_path(self, *image_tools):
        """A PATH holding only the script's shell utilities plus the named image tools.

        The directory is the entire PATH. Adding system directories instead would
        not isolate anything: on Linux ImageMagick lives in /usr/bin, so a test
        for "no converter available" would silently find one and prove nothing.
        """
        bindir = self.root / f"bin-{'-'.join(image_tools) or 'none'}"
        bindir.mkdir(exist_ok=True)
        for name in SHELL_UTILITIES + image_tools:
            found = shutil.which(name)
            if not found:
                self.skipTest(f"{name} is not available")
            link = bindir / name
            if not link.exists():
                link.symlink_to(found)

        # Fail loudly rather than passing vacuously if isolation did not hold.
        for absent in {"magick", "convert"} - set(image_tools):
            self.assertIsNone(
                shutil.which(absent, path=str(bindir)),
                f"{absent} leaked into the isolated PATH, so this test proves nothing",
            )
        return str(bindir)

    def destination(self, slug="aloe", date="2026-08-12", index=1):
        return self.root / "images" / f"{slug}-{date}-{index}.jpg"


class TestArgumentValidation(PreparePhotoTestCase):
    def test_missing_source_fails(self):
        result = self.prepare(self.source_dir / "nope.jpg")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stderr)

    def test_uppercase_slug_is_rejected(self):
        source = make_image(self.source_dir / "a.jpg")
        result = self.prepare(source, slug="Aloe")
        self.assertEqual(result.returncode, 1)
        self.assertIn("slug", result.stderr.lower())

    def test_non_iso_date_is_rejected(self):
        source = make_image(self.source_dir / "a.jpg")
        result = self.prepare(source, date="12-08-2026")
        self.assertEqual(result.returncode, 1)
        self.assertIn("date", result.stderr.lower())

    def test_zero_index_is_rejected(self):
        source = make_image(self.source_dir / "a.jpg")
        result = self.prepare(source, index=0)
        self.assertEqual(result.returncode, 1)

    def test_refuses_to_overwrite_an_existing_image(self):
        source = make_image(self.source_dir / "a.jpg")
        self.assertEqual(self.prepare(source).returncode, 0)
        second = self.prepare(source)
        self.assertEqual(second.returncode, 1)
        self.assertIn("overwrite", second.stderr.lower())


class TestProducesAUsableImage(PreparePhotoTestCase):
    def test_writes_a_real_non_empty_jpeg(self):
        source = make_image(self.source_dir / "a.jpg", 800, 600)
        result = self.prepare(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.destination()
        self.assertTrue(dest.is_file(), "destination file was not created")
        self.assertGreater(dest.stat().st_size, 0)
        self.assertEqual(read_tags(dest, "FileType").get("FileType"), "JPEG")

    def test_prints_the_path_it_actually_wrote(self):
        source = make_image(self.source_dir / "a.jpg")
        result = self.prepare(source)
        printed = Path(result.stdout.strip())
        self.assertTrue(printed.is_file(), f"printed path does not exist: {printed}")

    def test_large_image_is_downscaled_to_the_long_edge(self):
        source = make_image(self.source_dir / "a.jpg", 4000, 3000)
        self.assertEqual(self.prepare(source).returncode, 0)
        self.assertEqual(max(dimensions(self.destination())), 2200)

    def test_small_image_is_not_upscaled(self):
        source = make_image(self.source_dir / "a.jpg", 600, 400)
        self.assertEqual(self.prepare(source).returncode, 0)
        self.assertEqual(dimensions(self.destination()), (600, 400))

    def test_multi_frame_source_does_not_silently_write_split_files(self):
        if not supports_format(".gif"):
            self.skipTest("ImageMagick cannot write GIF here")
        burst = self.source_dir / "burst.gif"
        subprocess.run(
            [IMAGEMAGICK, "-delay", "10", "-size", "40x30",
             "xc:green", "xc:yellow", str(burst)],
            check=True, capture_output=True,
        )
        result = self.prepare(burst)
        images = sorted(p.name for p in (self.root / "images").glob("*.jpg"))
        if result.returncode == 0:
            self.assertEqual(
                images, ["aloe-2026-08-12-1.jpg"],
                "a multi-frame source must yield exactly the one named file",
            )
            self.assertTrue(self.destination().is_file())
        else:
            self.assertEqual(images, [], f"failed run left files behind: {images}")


class TestStripsPrivateMetadata(PreparePhotoTestCase):
    def _leaky_source(self):
        source = make_image(self.source_dir / "leaky.jpg", 800, 600)
        set_tags(
            source,
            GPSLatitude=52.2, GPSLatitudeRef="N", GPSLongitude=21.0, GPSLongitudeRef="E",
            Make="TestCam", Model="X100", SerialNumber="SN12345",
            Artist="Jane Doe", DateTimeOriginal="2026:08:11 07:31:02",
        )
        return source

    def test_output_has_no_identifying_metadata(self):
        source = self._leaky_source()
        self.assertEqual(self.prepare(source).returncode, 0)
        leaked = read_tags(
            self.destination(),
            "GPSLatitude", "GPSLongitude", "Make", "Model",
            "SerialNumber", "Artist", "DateTimeOriginal",
        )
        self.assertEqual(leaked, {}, f"metadata survived: {leaked}")

    def test_output_passes_the_repository_metadata_check(self):
        source = self._leaky_source()
        self.assertEqual(self.prepare(source).returncode, 0)
        result = subprocess.run(
            [str(SCRIPTS / "check_photo_metadata.sh"), str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_no_makernotes_group_survives(self):
        source = self._leaky_source()
        self.assertEqual(self.prepare(source).returncode, 0)
        self.assertNotIn("MakerNotes", all_tag_groups(self.destination()))

    def test_rotation_is_baked_in_rather_than_left_as_a_tag(self):
        # A viewer that ignores EXIF must still show the image the right way up.
        source = make_image(self.source_dir / "sideways.jpg", 1200, 800)
        set_tags(source, numeric=True, Orientation=6)  # 6 = rotate 90 CW
        self.assertEqual(self.prepare(source).returncode, 0)
        dest = self.destination()
        width, height = dimensions(dest)
        self.assertGreater(height, width, "expected the rotation to be applied to the pixels")
        orientation = read_tags(dest, "Orientation").get("Orientation")
        self.assertIn(
            orientation, (None, "Horizontal (normal)", "1"),
            f"a baked-in rotation must not also leave a rotate tag, got {orientation!r}",
        )


class TestLeavesNoPartialOutput(PreparePhotoTestCase):
    def test_failure_leaves_no_file_at_the_destination(self):
        source = make_image(self.source_dir / "a.jpg")
        stub_dir = self.root / "stub-bin"
        stub_dir.mkdir()
        stub = stub_dir / "exiftool"
        stub.write_text(STUB_FAILING_EXIFTOOL, encoding="utf-8")
        stub.chmod(0o755)
        path = f"{stub_dir}:{os.environ['PATH']}"

        result = self.prepare(source, path=path)
        leftovers = sorted(p.name for p in (self.root / "images").glob("*.jpg"))
        if result.returncode != 0:
            self.assertEqual(
                leftovers, [],
                "a failed run must not leave an unstripped file in images/",
            )

    def test_unconvertible_source_fails_and_leaves_nothing(self):
        broken = self.source_dir / "broken.jpg"
        broken.write_text("this is not an image", encoding="utf-8")
        result = self.prepare(broken)
        self.assertNotEqual(result.returncode, 0, "a non-image source must fail")
        self.assertFalse(
            self.destination().exists(),
            "a failed conversion must not leave a destination file",
        )


class TestConverterDiscovery(PreparePhotoTestCase):
    def test_works_with_imagemagick_6_convert_only(self):
        # Debian/Ubuntu ship ImageMagick 6, which has `convert` but no `magick`.
        path = self.isolated_path("convert", "exiftool")
        source = make_image(self.source_dir / "a.jpg", 800, 600)
        result = self.prepare(source, path=path)
        self.assertEqual(
            result.returncode, 0,
            f"ImageMagick 6 should be supported\nstderr: {result.stderr}",
        )
        self.assertTrue(self.destination().is_file())

    def test_missing_converter_reports_what_to_install(self):
        path = self.isolated_path()
        source = make_image(self.source_dir / "a.jpg")
        result = self.prepare(source, path=path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("imagemagick", result.stderr.lower())


class TestInventoryStaysInSync(PreparePhotoTestCase):
    def test_creates_the_inventory_if_it_does_not_exist(self):
        # Photos are kept out of git, so the inventory is not committed either and
        # a fresh clone starts without one. The first photo must create it.
        (self.root / "images" / "README.md").unlink()
        source = make_image(self.source_dir / "a.jpg")
        result = self.prepare(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        inventory = self.root / "images" / "README.md"
        self.assertTrue(inventory.is_file(), "inventory was not created")
        self.assertIn("`aloe-2026-08-12-1.jpg`", inventory.read_text(encoding="utf-8"))

    def test_new_image_is_recorded_in_the_inventory(self):
        # The validator treats an unlisted file in images/ as an error, so
        # preparing a photo must not leave the tracker in a failing state.
        source = make_image(self.source_dir / "a.jpg")
        self.assertEqual(self.prepare(source).returncode, 0)
        inventory = (self.root / "images" / "README.md").read_text(encoding="utf-8")
        self.assertIn("`aloe-2026-08-12-1.jpg`", inventory)


if __name__ == "__main__":
    unittest.main()
