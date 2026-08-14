"""Behaviour tests for start_fresh.py and sync_image_inventory.py.

start_fresh.py is the first thing a new user runs and the only script that
destroys data, so the tests focus on it never doing so unrecoverably.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tracker_fixture import Plant, build_project, run_script, validate


class StartFreshTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        build_project(self.root, [Plant("Aloe"), Plant("Basil")])

    def tracker_text(self):
        return (self.root / "plants.html").read_text(encoding="utf-8")

    def personal_section(self):
        """Just the My Plants section; the reference table also has plant-name cells."""
        text = self.tracker_text()
        return text[text.index('<section id="my-plants"'):text.index('<section id="reference"')]

    def backups(self):
        return sorted(p.name for p in self.root.glob("plants.*backup*.html"))

    def start_fresh(self, *args):
        return run_script("start_fresh.py", self.root, *args)


class TestClearsOnlyThePersonalInventory(StartFreshTestCase):
    def test_personal_rows_are_removed(self):
        result = self.start_fresh()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('class="plant-name"', self.personal_section())

    def test_reference_section_survives(self):
        self.start_fresh()
        self.assertIn('<section id="reference"', self.tracker_text())

    def test_cleared_tracker_is_valid_when_empty_is_allowed(self):
        self.start_fresh()
        result = validate(self.root, "--allow-empty")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_handles_attributes_on_the_tbody_tag(self):
        # plants.html carries <tbody lang="ru"> so screen readers use the right
        # voice for the records. Matching a bare "<tbody>" string missed it.
        tracker = self.root / "plants.html"
        tracker.write_text(
            tracker.read_text(encoding="utf-8").replace("<tbody>", '<tbody lang="ru">'),
            encoding="utf-8",
        )
        result = self.start_fresh()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('class="plant-name"', self.personal_section())
        self.assertIn('<tbody lang="ru">', self.tracker_text())

    def test_clears_the_real_repository_tracker(self):
        # Guards against the markup drifting away from what this script matches.
        repo_tracker = Path(__file__).resolve().parent.parent / "plants.html"
        (self.root / "plants.html").write_text(
            repo_tracker.read_text(encoding="utf-8"), encoding="utf-8"
        )
        result = self.start_fresh()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('class="plant-name"', self.personal_section())
        self.assertIn('<section id="reference"', self.tracker_text())

    def test_unexpected_structure_leaves_the_tracker_untouched(self):
        tracker = self.root / "plants.html"
        tracker.write_text("<html><body>no sections here</body></html>", encoding="utf-8")
        before = tracker.read_text(encoding="utf-8")
        result = self.start_fresh()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(tracker.read_text(encoding="utf-8"), before)


class TestClearingTheSpeciesReference(StartFreshTestCase):
    """--clear-reference removes the previous owner's species rows too.

    Keeping the reference is the default because the care text is reusable, but a
    cleared tracker otherwise still displays someone else's plants and photos.
    """

    def reference_section(self):
        text = self.tracker_text()
        return text[text.index('<section id="reference"'):]

    def test_reference_rows_are_kept_by_default(self):
        repo_tracker = Path(__file__).resolve().parent.parent / "plants.html"
        if 'class="plant-name"' not in repo_tracker.read_text(encoding="utf-8"):
            self.skipTest("repository tracker has no reference rows to keep")
        (self.root / "plants.html").write_text(
            repo_tracker.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.start_fresh()
        self.assertIn('class="plant-name"', self.reference_section())

    def test_clear_reference_empties_the_reference_table(self):
        repo_tracker = Path(__file__).resolve().parent.parent / "plants.html"
        (self.root / "plants.html").write_text(
            repo_tracker.read_text(encoding="utf-8"), encoding="utf-8"
        )
        result = self.start_fresh("--clear-reference")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('class="plant-name"', self.reference_section())

    def test_clear_reference_removes_every_image_reference(self):
        repo_tracker = Path(__file__).resolve().parent.parent / "plants.html"
        (self.root / "plants.html").write_text(
            repo_tracker.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.start_fresh("--clear-reference")
        self.assertNotIn('images/', self.tracker_text())

    def test_clear_reference_empties_the_soil_recipe_map(self):
        # The map is keyed by species name, so leaving it populated would still
        # enumerate the previous owner's collection.
        repo_tracker = Path(__file__).resolve().parent.parent / "plants.html"
        (self.root / "plants.html").write_text(
            repo_tracker.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.start_fresh("--clear-reference")
        text = self.tracker_text()
        self.assertIn("const soilMixes = new Map([", text)
        body = text.split("const soilMixes = new Map([")[1].split("]);")[0]
        self.assertNotIn("'", body, f"soil recipes survived: {body.strip()[:120]}")

    def test_clear_reference_keeps_the_page_usable(self):
        repo_tracker = Path(__file__).resolve().parent.parent / "plants.html"
        (self.root / "plants.html").write_text(
            repo_tracker.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.start_fresh("--clear-reference")
        text = self.tracker_text()
        for needed in ('<section id="my-plants"', '<section id="reference"',
                       "<script>", "empty-state"):
            self.assertIn(needed, text)

    def test_fully_cleared_tracker_validates(self):
        repo_tracker = Path(__file__).resolve().parent.parent / "plants.html"
        (self.root / "plants.html").write_text(
            repo_tracker.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.start_fresh("--clear-reference")
        for path in (self.root / "images").iterdir():
            if path.is_file():
                path.unlink()
        result = validate(self.root, "--allow-empty")
        self.assertEqual(result.returncode, 0, result.stderr)


class TestBackupsAreNeverLost(StartFreshTestCase):
    def test_a_backup_is_created_by_default(self):
        self.start_fresh()
        self.assertTrue(self.backups(), "expected a backup file")

    def test_backup_contains_the_original_rows(self):
        self.start_fresh()
        backup = self.root / self.backups()[0]
        self.assertIn("Aloe", backup.read_text(encoding="utf-8"))

    def test_second_run_does_not_overwrite_the_first_backup(self):
        self.start_fresh()
        first = self.backups()
        self.assertEqual(len(first), 1)
        original = (self.root / first[0]).read_text(encoding="utf-8")

        # Re-populate as a user would, then start fresh again.
        build_project(self.root, [Plant("Cactus")])
        result = self.start_fresh()
        self.assertEqual(result.returncode, 0, result.stderr)

        after = self.backups()
        self.assertEqual(
            len(after), 2,
            f"a second run must keep the earlier backup, found: {after}",
        )
        self.assertEqual(
            (self.root / first[0]).read_text(encoding="utf-8"), original,
            "the first backup's contents must not change",
        )

    def test_no_backup_flag_skips_the_backup(self):
        result = self.start_fresh("--no-backup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.backups(), [])

    def test_running_twice_is_idempotent(self):
        self.start_fresh("--no-backup")
        once = self.tracker_text()
        self.start_fresh("--no-backup")
        self.assertEqual(self.tracker_text(), once)


class TestInventorySync(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def sync(self, *args):
        return run_script("sync_image_inventory.py", self.root, *args)

    def inventory(self):
        return (self.root / "images" / "README.md").read_text(encoding="utf-8")

    def test_adds_an_undocumented_image(self):
        build_project(self.root, [Plant("Aloe")], inventory=[])
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("`aloe-2026-08-11-1.jpg`", self.inventory())

    def test_removes_an_entry_whose_file_is_gone(self):
        build_project(self.root, [Plant("Aloe")], inventory=["aloe-2026-08-11-1.jpg", "ghost.jpg"])
        self.assertEqual(self.sync().returncode, 0)
        self.assertNotIn("ghost.jpg", self.inventory())

    def test_result_satisfies_the_validator(self):
        build_project(self.root, [Plant("Aloe")], inventory=["ghost.jpg"])
        (self.root / "images" / "stray-2026-08-11-1.jpg").write_bytes(b"\xff\xd8\xff\xd9")
        self.assertEqual(self.sync().returncode, 0)
        result = validate(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_mode_reports_drift_without_writing(self):
        build_project(self.root, [Plant("Aloe")], inventory=[])
        before = self.inventory()
        result = self.sync("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.inventory(), before)

    def test_check_mode_passes_when_already_in_sync(self):
        build_project(self.root, [Plant("Aloe")])
        self.assertEqual(self.sync("--check").returncode, 0)

    def test_no_images_and_no_inventory_is_not_an_error(self):
        # A repository that keeps its photos private has nothing to reconcile.
        build_project(self.root, [])
        (self.root / "images" / "README.md").unlink()
        result = self.sync("--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_reports_drift_when_the_inventory_is_missing_but_images_exist(self):
        build_project(self.root, [Plant("Aloe")])
        (self.root / "images" / "README.md").unlink()
        self.assertNotEqual(self.sync("--check").returncode, 0)

    def test_creates_the_inventory_when_it_is_missing(self):
        # The inventory is not committed when photos are kept private, so a fresh
        # clone has none. Repairing must create it rather than refuse.
        build_project(self.root, [Plant("Aloe")])
        (self.root / "images" / "README.md").unlink()
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("`aloe-2026-08-11-1.jpg`", self.inventory())

    def test_created_inventory_satisfies_the_validator(self):
        build_project(self.root, [Plant("Aloe")])
        (self.root / "images" / "README.md").unlink()
        self.assertEqual(self.sync().returncode, 0)
        result = validate(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_preserves_the_surrounding_prose(self):
        build_project(self.root, [Plant("Aloe")], inventory=[])
        readme = self.root / "images" / "README.md"
        readme.write_text(
            "# Plant photos\n\nIntro paragraph.\n\nCurrent image inventory:\n\n"
            "\nClosing note about `<plant-slug>-YYYY-MM-DD-<n>.jpg`.\n",
            encoding="utf-8",
        )
        self.assertEqual(self.sync().returncode, 0)
        text = self.inventory()
        self.assertIn("Intro paragraph.", text)
        self.assertIn("Closing note", text)
        self.assertIn("`aloe-2026-08-11-1.jpg`", text)


if __name__ == "__main__":
    unittest.main()
