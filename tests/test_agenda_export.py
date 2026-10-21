"""Regressietests voor ontdubbelen en sorteren van de agenda-export."""

import unittest
import xml.etree.ElementTree as ET

from app import transform_xml


def make_xml(events):
    """Maak een klein XML-testbestand zonder externe gegevens."""
    root = ET.Element("agenda")
    for place, genre, text in events:
        event = ET.SubElement(root, "evenement")
        ET.SubElement(event, "plaats").text = place
        ET.SubElement(event, "genre").text = genre
        ET.SubElement(event, "tekst").text = text
    return ET.tostring(root, encoding="unicode")


class AgendaExportTests(unittest.TestCase):
    def test_identical_events_appear_once(self):
        events = [
            ("Zutendaal", "Muziek", "Concert"),
            ("Zutendaal", "Muziek", "Concert"),
            ("Zutendaal", "Muziek", "Concert"),
        ]
        output = transform_xml(make_xml(events))
        self.assertEqual(output.count("<EP>"), 1)
        self.assertEqual(output.count("<SU>Concert"), 1)

    def test_different_place_genre_or_full_text_remains(self):
        events = [
            ("Zutendaal", "Muziek", "Concert"),
            ("Maastricht", "Muziek", "Concert"),
            ("Zutendaal", "Theater", "Concert"),
            ("Zutendaal", "Muziek", "Concert extra"),
        ]
        output = transform_xml(make_xml(events))
        self.assertEqual(output.count("<EP>"), 4)
        self.assertEqual(output.count("<SU>Concert\n"), 3)
        self.assertEqual(output.count("<SU>Concert extra"), 1)

    def test_uses_existing_normalization_before_deduplication(self):
        events = [
            ("Urmond Gemeente Stein", "Evenement", "Aanvang 9 uur"),
            ("Urmond", "Evenement", "Aanvang 9.00 uur"),
        ]
        output = transform_xml(make_xml(events))
        self.assertEqual(output.count("<EP>"), 1)
        self.assertIn("<l_region>Urmond</l_region>", output)
        self.assertIn("<SU>Aanvang 9.00 uur", output)

    def test_places_are_sorted_alphabetically(self):
        events = [
            ("Zutendaal", "Muziek", "A"),
            ("Maastricht", "Muziek", "B"),
            ("arcen", "Muziek", "C"),
            ("Zutendaal", "Muziek", "A"),
        ]
        output = transform_xml(make_xml(events))
        regions = [line for line in output.splitlines() if line.startswith("<l_region>")]
        self.assertEqual(regions, [
            "<l_region>arcen</l_region>",
            "<l_region>Maastricht</l_region>",
            "<l_region>Zutendaal</l_region>",
        ])
        self.assertEqual(output.count("<EP>"), 3)

    def test_preserves_first_occurrence_order_within_place(self):
        events = [
            ("Arcen", "Evenement", "Eerste"),
            ("Arcen", "Evenement", "Tweede"),
            ("Arcen", "Evenement", "Eerste"),
            ("Arcen", "Evenement", "Derde"),
        ]
        output = transform_xml(make_xml(events))
        self.assertEqual(output.count("<EP>"), 3)
        self.assertLess(output.index("<SU>Eerste"), output.index("<SU>Tweede"))
        self.assertLess(output.index("<SU>Tweede"), output.index("<SU>Derde"))

    def test_no_duplicates_preserves_export_structure(self):
        output = transform_xml(make_xml([("Arcen", "Muziek", "Concert")]))
        self.assertEqual(output, "\n".join([
            "<body>",
            "<l_region>Arcen</l_region>",
            "<EP>",
            "<l_info>",
            "<bold>Muziek</bold>",
            "<SU>Concert",
            "</l_info>",
            "</body>",
        ]))


if __name__ == "__main__":
    unittest.main()
