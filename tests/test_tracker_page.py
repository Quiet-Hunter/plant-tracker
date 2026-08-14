"""Structural tests for plants.html itself.

These pin the accessibility and usability fixes so a later edit cannot quietly
undo them. They assert on markup and stylesheet content rather than rendering,
because the project deliberately has no browser or JavaScript test dependencies.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKER = REPO_ROOT / "plants.html"

NODE = shutil.which("node")


def relative_luminance(hex_colour):
    value = hex_colour.lstrip("#")
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground, background):
    first, second = relative_luminance(foreground), relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


class TrackerPageTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = TRACKER.read_text(encoding="utf-8")

    def css_variable(self, name):
        match = re.search(rf"{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})", self.text)
        self.assertIsNotNone(match, f"{name} is not defined")
        return match.group(1)


class TestLanguageDeclaration(TrackerPageTestCase):
    def test_document_language_is_declared(self):
        self.assertIn('<html lang="en">', self.text)

    def test_record_bodies_declare_their_own_language(self):
        # The interface is English but the demo records are Russian. Without a
        # lang hook a screen reader reads Cyrillic with an English voice.
        self.assertEqual(
            self.text.count('<tbody lang="'), 2,
            "both table bodies should declare the language of their records",
        )


class TestKeyboardAndScreenReaderSupport(TrackerPageTestCase):
    def test_scroll_regions_are_focusable_and_named(self):
        regions = re.findall(r'<div class="table-wrap"[^>]*>', self.text)
        self.assertEqual(len(regions), 2)
        for region in regions:
            self.assertIn('tabindex="0"', region)
            self.assertIn("aria-label=", region)

    def test_tabs_support_arrow_key_navigation(self):
        self.assertIn("ArrowRight", self.text)
        self.assertIn("ArrowLeft", self.text)

    def test_tabs_use_a_roving_tabindex(self):
        self.assertIn("tabIndex", self.text)

    def test_focus_visible_styles_exist(self):
        self.assertIn(":focus-visible", self.text)

    def test_clipped_photo_links_get_an_inset_focus_ring(self):
        # .photo-frame sets overflow: hidden, so an outset ring is invisible.
        self.assertRegex(self.text, r"\.photo-frame a:focus-visible\s*\{[^}]*outline-offset:\s*-")


class TestColourContrast(TrackerPageTestCase):
    def test_medium_priority_badge_meets_wcag_aa(self):
        ratio = contrast_ratio(self.css_variable("--medium"), "#fff3d7")
        self.assertGreaterEqual(
            round(ratio, 2), 4.5,
            f"medium priority badge contrast is {ratio:.2f}:1, below WCAG AA 4.5:1",
        )

    def test_high_and_low_priority_badges_meet_wcag_aa(self):
        # .priority.high hardcodes its background; the low variant uses a token.
        pairs = (
            ("--high", "#fae5e1"),
            ("--low", self.css_variable("--accent-soft")),
        )
        for token, background in pairs:
            ratio = contrast_ratio(self.css_variable(token), background)
            self.assertGreaterEqual(
                round(ratio, 2), 4.5,
                f"{token} contrast is {ratio:.2f}:1 on {background}",
            )


class TestFilteringBehaviour(TrackerPageTestCase):
    def test_striping_is_not_positional(self):
        # nth-child counts filtered-out rows, producing arbitrary colour runs.
        self.assertNotIn("tbody tr:nth-child(even)", self.text)

    def test_search_ignores_the_photo_column(self):
        # The photo cells hold hidden filename fallbacks; including them made a
        # search for "jpg" match every row.
        self.assertIn("photo-cell", self.text.split("function rowSearchText")[1][:400])

    def test_search_folds_diacritics(self):
        self.assertIn("u0300", self.text)

    def test_hover_highlight_is_gated_on_hover_capable_devices(self):
        self.assertRegex(self.text, r"@media \(hover: hover\)")

    @unittest.skipUnless(NODE, "node is not installed")
    def test_search_normalisation_matches_e_with_and_without_diaeresis(self):
        source = self.text[self.text.index("<script>") + len("<script>"):self.text.rindex("</script>")]
        helper = source[source.index("function searchable"):]
        helper = helper[:helper.index("\n    }") + len("\n    }")]
        script = helper + """
const a = searchable('\\u043f\\u0440\\u043e\\u0442\\u0451\\u0440\\u0442\\u044b');
const b = searchable('\\u043f\\u0440\\u043e\\u0442\\u0435\\u0440\\u0442\\u044b');
if (a !== b) { console.error('mismatch', JSON.stringify([a, b])); process.exit(1); }
"""
        result = subprocess.run([NODE, "--input-type=module", "-e", script],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class TestEmptyStates(TrackerPageTestCase):
    def test_both_sections_distinguish_no_entries_from_no_matches(self):
        self.assertEqual(self.text.count("data-no-entries="), 2)
        self.assertEqual(self.text.count("data-no-matches="), 2)

    def test_a_fresh_tracker_does_not_show_search_failure_copy(self):
        # "Nothing found." is search-result wording; a brand new tracker needs
        # onboarding wording instead.
        match = re.search(r'data-no-entries="([^"]+)"', self.text)
        self.assertIsNotNone(match)
        self.assertNotIn("nothing found", match.group(1).lower())


class TestPrintAndResponsive(TrackerPageTestCase):
    def test_a_print_stylesheet_exists(self):
        self.assertIn("@media print", self.text)

    def test_print_releases_the_scroll_container(self):
        print_block = self.text.split("@media print")[1]
        self.assertIn("max-height: none", print_block)

    def test_print_repeats_table_headers_across_pages(self):
        print_block = self.text.split("@media print")[1]
        self.assertIn("table-header-group", print_block)

    def test_print_shows_both_sections(self):
        print_block = self.text.split("@media print")[1]
        self.assertIn('section[role="tabpanel"][hidden]', print_block)

    def test_narrow_screens_pin_the_plant_name_column(self):
        narrow = self.text.split("@media (max-width: 700px)")[1].split("@media print")[0]
        self.assertIn("position: sticky", narrow)
        self.assertIn(".plant-name", narrow)

    def test_narrow_screens_do_not_nest_a_fixed_height_scroller(self):
        narrow = self.text.split("@media (max-width: 700px)")[1].split("@media print")[0]
        self.assertIn("max-height: none", narrow)

    def test_photo_gallery_wraps_rather_than_squeezing(self):
        self.assertRegex(self.text, r"\.photo-gallery\s*\{[^}]*flex-wrap:\s*wrap")


if __name__ == "__main__":
    unittest.main()
