"""Behaviour tests for validate_tracker.py.

The validator is the project's only automated guard on tracker correctness, so the
cases that matter most are the ones where it could report success without having
checked anything.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tracker_fixture import Plant, build_project, render_tracker, validate


class ValidatorTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def assertPasses(self, result):
        self.assertEqual(
            result.returncode, 0,
            f"expected success, got exit {result.returncode}\n{result.stderr}",
        )

    def assertFailsWith(self, result, needle):
        self.assertEqual(
            result.returncode, 1,
            f"expected failure, got exit {result.returncode}\nstdout: {result.stdout}",
        )
        self.assertIn(needle.lower(), result.stderr.lower())


class TestAcceptsValidTrackers(ValidatorTestCase):
    def test_minimal_valid_tracker_passes(self):
        build_project(self.root)
        self.assertPasses(validate(self.root))

    def test_repository_tracker_passes(self):
        # The tracker ships empty: photos and records are private and stay local.
        repo = Path(__file__).resolve().parent.parent
        self.assertPasses(validate(repo, "--allow-empty"))

    def test_legacy_russian_priority_labels_are_accepted(self):
        build_project(self.root, [Plant("Алоэ", priority="Высокий")])
        self.assertPasses(validate(self.root))

    def test_legacy_display_date_format_is_accepted(self):
        build_project(self.root, [Plant("Aloe", date="2026-08-11", display="11.08.2026")])
        self.assertPasses(validate(self.root))


class TestCatchesContractViolations(ValidatorTestCase):
    def test_duplicate_plant_names_fail(self):
        build_project(self.root, [Plant("Aloe"), Plant("Aloe")])
        self.assertFailsWith(validate(self.root), "duplicate")

    def test_low_priority_row_with_an_action_fails(self):
        build_project(self.root, [Plant("Aloe", priority="Low", action="Repot it")])
        self.assertFailsWith(validate(self.root), "low-priority")

    def test_priority_label_without_matching_class_fails(self):
        plant = Plant("Aloe", priority="High")
        tracker = render_tracker([plant]).replace('class="priority high"', 'class="priority"')
        build_project(self.root, [plant], tracker=tracker)
        self.assertFailsWith(validate(self.root), "class mismatch")

    def test_unknown_priority_label_fails(self):
        build_project(self.root, [Plant("Aloe", priority="Urgent")])
        self.assertFailsWith(validate(self.root), "priority")

    def test_rows_out_of_order_fail(self):
        build_project(self.root, [Plant("Basil"), Plant("Aloe")])
        self.assertFailsWith(validate(self.root), "sorted")

    def test_high_priority_must_sort_before_low(self):
        build_project(self.root, [Plant("Zebra", priority="Low"), Plant("Aloe", priority="High")])
        self.assertFailsWith(validate(self.root), "sorted")

    def test_impossible_date_fails(self):
        build_project(self.root, [Plant("Aloe", date="2026-13-99")])
        self.assertFailsWith(validate(self.root), "date")

    def test_display_date_not_matching_iso_fails(self):
        build_project(self.root, [Plant("Aloe", date="2026-08-11", display="2020-01-01")])
        self.assertFailsWith(validate(self.root), "date")

    def test_missing_image_file_fails(self):
        build_project(self.root)
        (self.root / "images" / "aloe-2026-08-11-1.jpg").unlink()
        self.assertFailsWith(validate(self.root), "missing image")

    def test_referenced_image_absent_from_inventory_fails(self):
        build_project(self.root, inventory=["basil-2026-08-11-1.jpg"])
        self.assertFailsWith(validate(self.root), "images/readme.md")


class TestSilentSuccessHoles(ValidatorTestCase):
    """The validator must never report success without having checked the rows.

    Each of these describes a way the row parser can come up empty or short while
    the exit code stays 0, which makes CI green on an unvalidated tracker.
    """

    def test_tracker_with_no_rows_fails(self):
        build_project(self.root, [])
        result = validate(self.root)
        self.assertNotEqual(
            result.returncode, 0,
            "an empty personal table must not report success by default; "
            f"got: {result.stdout.strip()}",
        )

    def test_empty_tracker_passes_when_explicitly_allowed(self):
        build_project(self.root, [])
        self.assertPasses(validate(self.root, "--allow-empty"))

    def test_whitespace_between_cells_does_not_hide_rows(self):
        plants = [Plant("Aloe"), Plant("Basil")]
        tracker = render_tracker(plants).replace("<td", "\n              <td")
        build_project(self.root, plants, tracker=tracker)
        result = validate(self.root)
        self.assertPasses(result)
        self.assertIn("2 plants", result.stdout)

    def test_reformatting_cannot_disable_the_content_checks(self):
        # Same duplicate-name violation as above, but pretty-printed.
        plants = [Plant("Aloe"), Plant("Aloe")]
        tracker = render_tracker(plants).replace("<td", "\n              <td")
        build_project(self.root, plants, tracker=tracker)
        self.assertFailsWith(validate(self.root), "duplicate")

    def test_extra_class_on_photo_cell_does_not_drop_the_row(self):
        plants = [Plant("Aloe"), Plant("Basil", photo_cell_class="photo-cell photo-cell--hero")]
        build_project(self.root, plants)
        result = validate(self.root)
        self.assertPasses(result)
        self.assertIn("2 plants", result.stdout)

    def test_violation_in_a_row_with_an_extra_class_is_still_caught(self):
        plants = [
            Plant("Aloe"),
            Plant("Aloe", photo_cell_class="photo-cell photo-cell--hero"),
        ]
        build_project(self.root, plants)
        self.assertFailsWith(validate(self.root), "duplicate")

    def test_row_name_cell_as_table_header_is_still_parsed(self):
        # Accessibility fix: plant names should be able to become <th scope="row">.
        plants = [Plant("Aloe", name_cell='<th scope="row" class="plant-name">')]
        tracker = render_tracker(plants).replace(
            '<th scope="row" class="plant-name">Aloe</td>',
            '<th scope="row" class="plant-name">Aloe</th>',
        )
        build_project(self.root, plants, tracker=tracker)
        result = validate(self.root)
        self.assertPasses(result)
        self.assertIn("1 plant", result.stdout)


class TestStrictness(ValidatorTestCase):
    def test_non_padded_iso_date_fails(self):
        build_project(self.root, [Plant("Aloe", date="2026-8-7", display="2026-08-07")])
        self.assertFailsWith(validate(self.root), "date")

    def test_numeric_name_order_matches_the_pages_own_sort(self):
        # plants.html sorts with Intl.Collator({numeric: true}), so Ficus 2
        # precedes Ficus 10. The validator must agree.
        build_project(self.root, [Plant("Ficus 2"), Plant("Ficus 10")])
        self.assertPasses(validate(self.root))

    def test_malformed_row_error_identifies_the_row(self):
        plants = [Plant("Aloe"), Plant("Basil")]
        tracker = render_tracker(plants).replace(
            '<td class="last-inspection"><time datetime="2026-08-11">2026-08-11</time></td></tr>'
            "\n            <tr>",
            "<td>2026-08-11</td></tr>\n            <tr>",
            1,
        )
        build_project(self.root, plants, tracker=tracker)
        result = validate(self.root)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("aloe", result.stderr.lower())

    def test_unbalanced_html_fails(self):
        plants = [Plant("Aloe")]
        tracker = render_tracker(plants).replace("</tbody>", "", 1)
        build_project(self.root, plants, tracker=tracker)
        self.assertFailsWith(validate(self.root), "html")


class TestRepositoryWithoutImages(ValidatorTestCase):
    """A tracker whose photos are kept private and out of the repository.

    With no photos committed there is nothing for the inventory to reconcile, so
    requiring images/README.md would fail every fresh clone. When photos *are*
    present the inventory is still mandatory.
    """

    def test_empty_tracker_with_no_images_at_all_validates(self):
        build_project(self.root, [])
        (self.root / "images" / "README.md").unlink()
        result = validate(self.root, "--allow-empty")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_inventory_still_fails_when_images_are_present(self):
        build_project(self.root)
        (self.root / "images" / "README.md").unlink()
        self.assertFailsWith(validate(self.root), "inventory")

    def test_missing_images_directory_is_still_an_error(self):
        build_project(self.root, [])
        for path in (self.root / "images").iterdir():
            path.unlink()
        (self.root / "images").rmdir()
        result = validate(self.root, "--allow-empty")
        self.assertEqual(result.returncode, 1)
        self.assertIn("images directory", result.stderr.lower())

    def test_referenced_image_still_required_even_without_an_inventory(self):
        build_project(self.root)
        (self.root / "images" / "README.md").unlink()
        (self.root / "images" / "aloe-2026-08-11-1.jpg").unlink()
        self.assertFailsWith(validate(self.root), "missing image")


class TestImageInventory(ValidatorTestCase):
    def test_inventory_listing_a_missing_file_fails(self):
        build_project(self.root, inventory=["aloe-2026-08-11-1.jpg", "basil-2026-08-11-1.jpg", "ghost.jpg"])
        self.assertFailsWith(validate(self.root), "ghost.jpg")

    def test_image_on_disk_but_not_in_inventory_fails(self):
        build_project(self.root)
        (self.root / "images" / "stray-2026-08-11-1.jpg").write_bytes(b"\xff\xd8\xff\xd9")
        self.assertFailsWith(validate(self.root), "stray-2026-08-11-1.jpg")

    def test_historical_image_kept_on_disk_and_listed_is_allowed(self):
        # Old photos stay in images/ and in the inventory after the tracker stops
        # referencing them. That is required by the contract, not an error.
        build_project(self.root, extra_images=["aloe-2026-01-01-1.jpg"])
        self.assertPasses(validate(self.root))

    def test_inventory_prose_template_is_not_mistaken_for_a_listing(self):
        build_project(self.root)
        readme = self.root / "images" / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\nNames follow `<plant-slug>-YYYY-MM-DD-<n>.jpg`.\n",
            encoding="utf-8",
        )
        self.assertPasses(validate(self.root))


if __name__ == "__main__":
    unittest.main()
