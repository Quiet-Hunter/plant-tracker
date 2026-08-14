"""Behaviour tests for check_photo_metadata.sh.

This script is the gate the documentation tells people to trust before publishing
photos, so the cases that matter most are the ones where it could report "OK"
without having actually inspected a file.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from image_fixture import (
    REPO_ROOT,
    make_image,
    requires_exiftool,
    requires_imagemagick,
    requires_non_root,
    run_script,
    set_tags,
    supports_format,
)


@requires_exiftool
@requires_imagemagick
class MetadataCheckTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.images = self.root / "images"
        self.images.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def check(self):
        return run_script("check_photo_metadata.sh", self.root)

    def assertClean(self, result):
        self.assertEqual(
            result.returncode, 0,
            f"expected a clean report, got exit {result.returncode}\n{result.stderr}",
        )

    def assertFlagged(self, result, needle=None):
        self.assertNotEqual(
            result.returncode, 0,
            f"expected a non-zero exit, got:\n{result.stdout}",
        )
        if needle:
            combined = (result.stdout + result.stderr).lower()
            self.assertIn(needle.lower(), combined)


class TestCleanImagesPass(MetadataCheckTestCase):
    def test_freshly_generated_images_pass(self):
        make_image(self.images / "aloe-2026-08-11-1.jpg")
        self.assertClean(self.check())

    def test_orientation_tag_alone_is_allowed(self):
        path = make_image(self.images / "aloe-2026-08-11-1.jpg")
        set_tags(path, Orientation=1)
        self.assertClean(self.check())

    def test_icc_profile_alone_is_allowed(self):
        # The pipeline should preserve colour profiles, so their presence must not
        # be treated as a metadata leak.
        make_image(self.images / "aloe-2026-08-11-1.jpg", extra_args=["-colorspace", "sRGB"])
        self.assertClean(self.check())

    def test_repository_images_pass(self):
        self.assertClean(run_script("check_photo_metadata.sh", REPO_ROOT))


class TestDetectsLeaks(MetadataCheckTestCase):
    def test_gps_coordinates_are_flagged(self):
        path = make_image(self.images / "aloe-2026-08-11-1.jpg")
        set_tags(path, GPSLatitude=52.2, GPSLatitudeRef="N",
                 GPSLongitude=21.0, GPSLongitudeRef="E")
        self.assertFlagged(self.check(), "aloe-2026-08-11-1.jpg")

    def test_camera_make_and_model_are_flagged(self):
        path = make_image(self.images / "aloe-2026-08-11-1.jpg")
        set_tags(path, Make="TestCam", Model="X100")
        self.assertFlagged(self.check())

    def test_camera_serial_number_is_flagged(self):
        path = make_image(self.images / "aloe-2026-08-11-1.jpg")
        set_tags(path, SerialNumber="SN12345")
        self.assertFlagged(self.check())

    def test_owner_and_artist_are_flagged(self):
        path = make_image(self.images / "aloe-2026-08-11-1.jpg")
        set_tags(path, Artist="Jane Doe", Copyright="Jane Doe")
        self.assertFlagged(self.check())

    def test_capture_timestamp_is_flagged(self):
        path = make_image(self.images / "aloe-2026-08-11-1.jpg")
        set_tags(path, DateTimeOriginal="2026:08:11 07:31:02")
        self.assertFlagged(self.check())

    def test_gps_in_a_tiff_is_flagged(self):
        if not supports_format(".tif"):
            self.skipTest("ImageMagick cannot write TIFF here")
        path = make_image(self.images / "stray.tif")
        set_tags(path, GPSLatitude=52.2, GPSLatitudeRef="N",
                 GPSLongitude=21.0, GPSLongitudeRef="E")
        self.assertFlagged(self.check(), "stray.tif")

    def test_gps_in_a_heic_is_flagged(self):
        if not supports_format(".heic"):
            self.skipTest("ImageMagick cannot write HEIC here")
        path = make_image(self.images / "stray.heic")
        set_tags(path, GPSLatitude=52.2, GPSLatitudeRef="N",
                 GPSLongitude=21.0, GPSLongitudeRef="E")
        self.assertFlagged(self.check(), "stray.heic")

    def test_leak_in_a_subdirectory_is_flagged(self):
        path = make_image(self.images / "archive" / "old.jpg")
        set_tags(path, GPSLatitude=52.2, GPSLatitudeRef="N",
                 GPSLongitude=21.0, GPSLongitudeRef="E")
        self.assertFlagged(self.check())


class TestDoesNotReportSuccessWithoutLooking(MetadataCheckTestCase):
    @requires_non_root
    def test_unreadable_image_is_not_reported_as_clean(self):
        path = make_image(self.images / "aloe-2026-08-11-1.jpg")
        set_tags(path, GPSLatitude=52.2, GPSLatitudeRef="N",
                 GPSLongitude=21.0, GPSLongitudeRef="E")
        path.chmod(0o000)
        self.addCleanup(path.chmod, 0o644)
        self.assertFlagged(self.check())

    def test_missing_images_directory_is_an_error(self):
        result = run_script("check_photo_metadata.sh", self.root / "nowhere")
        self.assertNotEqual(result.returncode, 0)

    def test_empty_images_directory_passes(self):
        self.assertClean(self.check())


if __name__ == "__main__":
    unittest.main()
