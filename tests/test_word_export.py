"""Tests voor getagde Cue Print-TXT naar een opgemaakt Word-document."""
from io import BytesIO
import unittest

from docx import Document

from app import (InvalidTaggedAgenda, build_word_copy_formats,
                 parse_tagged_agenda, transform_txt_to_docx)


SAMPLE_TXT = '''<body>
<l_region>
Bunde<EP>
</l_region>
<EP>
<l_info><bold>
Het Landschap verbeeld door Arjen van Prooijen
</bold>
<SU>De Agnespoort, Agnesplein 14, 6241 CA Bunde * do 15-10 * 20.00-22.00 uur
<EP></l_info>
<l_region>Eijsden<EP></l_region>
<l_info><bold>Rommelmarkt </bold>
Cultureel Centrum Eijsden, Breusterstraat 23, 6245 EG Eijsden * zo 18-10 *
9.00-17.00 uur<EP></l_info>
</body>'''


def read_docx(source):
    return Document(BytesIO(transform_txt_to_docx(source)))


class WordExportTests(unittest.TestCase):
    def test_example_text_matches_user_word_example(self):
        doc = read_docx(SAMPLE_TXT)
        self.assertEqual([p.text for p in doc.paragraphs], [
            "BUNDE",
            "Het Landschap verbeeld door Arjen van Prooijen De Agnespoort, Agnesplein 14, 6241 CA Bunde * do 15-10 * 20.00-22.00 uur",
            "EIJSDEN",
            "Rommelmarkt Cultureel Centrum Eijsden, Breusterstraat 23, 6245 EG Eijsden * zo 18-10 * 9.00-17.00 uur",
        ])

    def test_bold_is_real_word_formatting_not_visible_tags(self):
        doc = read_docx(SAMPLE_TXT)
        self.assertTrue(doc.paragraphs[0].runs[0].bold)
        self.assertTrue(doc.paragraphs[1].runs[0].bold)
        self.assertFalse(bool(doc.paragraphs[1].runs[-1].bold))
        self.assertTrue(doc.paragraphs[2].runs[0].bold)
        self.assertTrue(doc.paragraphs[3].runs[0].bold)
        self.assertFalse(bool(doc.paragraphs[3].runs[-1].bold))
        combined = " ".join(p.text for p in doc.paragraphs)
        for tag in ('<body>', '<l_region>', '<l_info>', '<bold>', '<SU>', '<EP>'):
            self.assertNotIn(tag, combined)

    def test_handles_numbered_info_empty_sections_and_extra_leading(self):
        src = '''<body><l_region>Vaals<EP></l_region>
        <l_info><EP></l_info><l_info(1)><bold>Nieuws</bold><SU>De zaal<extra_leading><EP></l_info(1)>
        <l_region><EP></l_region><l_info><EP></l_info>
        </body>'''
        self.assertEqual([p.text for p in read_docx(src).paragraphs], ["VAALS", "Nieuws De zaal"])

    def test_merges_repeated_places_and_removes_exact_duplicate_events(self):
        src = '''<body>
        <l_region>Zutendaal</l_region><l_info><bold>A</bold><SU>Een</l_info>
        <l_region>Arcen</l_region><l_info><bold>B</bold><SU>Twee</l_info>
        <l_region>Zutendaal</l_region><l_info><bold>A</bold><SU>Een</l_info>
        <l_info><bold>C</bold><SU>Drie</l_info>
        </body>'''
        self.assertEqual([p.text for p in read_docx(src).paragraphs], [
            "ARCEN", "B Twee", "ZUTENDAAL", "A Een", "C Drie"
        ])

    def test_same_title_but_different_full_text_is_not_removed(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info><bold>Concert</bold><SU>Locatie 1 * 20.00 uur</l_info>
        <l_info><bold>Concert</bold><SU>Locatie 2 * 20.00 uur</l_info>
        <l_info><bold>Andere titel</bold><SU>Locatie 1 * 20.00 uur</l_info>
        </body>'''
        doc = read_docx(src)
        self.assertEqual([p.text for p in doc.paragraphs], [
            "VENLO", "Concert Locatie 1 * 20.00 uur",
            "Concert Locatie 2 * 20.00 uur",
            "Andere titel Locatie 1 * 20.00 uur",
        ])

    def test_same_title_and_body_in_different_place_is_not_removed(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info><bold>Concert</bold><SU>Hal A</l_info>
        <l_region>Roermond</l_region><l_info><bold>Concert</bold><SU>Hal A</l_info>
        </body>'''
        self.assertEqual([p.text for p in read_docx(src).paragraphs], [
            "ROERMOND", "Concert Hal A", "VENLO", "Concert Hal A",
        ])

    def test_numbered_bold_duplicate_of_plain_bold(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info(1)><bold(1)>Optreden</bold(1)><SU>Locatie 10</l_info(1)>
        <l_region>Venlo</l_region>
        <l_info><bold>Optreden</bold><SU>Locatie 10</l_info>
        </body>'''
        doc = read_docx(src)
        self.assertEqual([p.text for p in doc.paragraphs], ["VENLO", "Optreden Locatie 10"])
        self.assertTrue(doc.paragraphs[1].runs[0].bold)

    def test_duplicate_is_removed_from_word_and_copy_formats(self):
        src = '''<body><l_region>Baarlo</l_region>
        <l_info><bold>Wandeling</bold><SU>Park * 10.00 uur</l_info>
        <l_region>Baarlo</l_region>
        <l_info><bold>Wandeling</bold><SU>Park * 10.00 uur</l_info>
        </body>'''
        sections = parse_tagged_agenda(src)
        plain, html = build_word_copy_formats(sections)
        self.assertEqual(plain.count("Wandeling Park * 10.00 uur"), 1)
        self.assertEqual(html.count("Wandeling"), 1)
        self.assertEqual([p.text for p in read_docx(src).paragraphs], [
            "BAARLO", "Wandeling Park * 10.00 uur",
        ])

    def test_duplicate_inside_same_info_block_is_removed(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info><bold>Concert</bold><SU>Locatie * 20.00 uur<EP>
        <bold>Concert</bold><SU>Locatie * 20.00 uur<EP>
        <bold>Ander</bold><SU>Locatie * 21.00 uur</l_info>
        </body>'''
        self.assertEqual([p.text for p in read_docx(src).paragraphs], [
            "VENLO", "Concert Locatie * 20.00 uur", "Ander Locatie * 21.00 uur",
        ])

    def test_keeps_content_without_su_or_without_bold(self):
        src = '''<body><l_region>Arcen</l_region>
        <l_info><bold>Titel</bold>Locatie * 20.00 uur<EP></l_info>
        <l_info>Bericht zonder vetopmaak<EP></l_info>
        </body>'''
        doc = read_docx(src)
        self.assertEqual([p.text for p in doc.paragraphs], [
            "ARCEN", "Titel Locatie * 20.00 uur", "Bericht zonder vetopmaak"
        ])
        self.assertFalse(bool(doc.paragraphs[-1].runs[-1].bold))

    def test_date_and_punctuation_not_normalized_again(self):
        src = '''<body><l_region>Arcen</l_region><l_info>
        <bold>Start</bold><SU>9 uur * € 7,– & details
        </l_info></body>'''
        self.assertEqual(read_docx(src).paragraphs[1].text, "Start 9 uur * € 7,– & details")

    def test_copy_format_html_is_escaped(self):
        src = '''<body><l_region>Arcen</l_region>
        <l_info><bold>Concert & Muziek</bold><SU>Firma A & Co</l_info></body>'''
        plain, html = build_word_copy_formats(parse_tagged_agenda(src))
        self.assertIn('Concert & Muziek Firma A & Co', plain)
        self.assertIn('<strong>Concert &amp; Muziek</strong>', html)
        self.assertIn('Firma A &amp; Co', html)

    def test_numbered_bold_is_recognized_and_formatted(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info><bold(1)>Greatest hits 1 and more - Queen Must Go On</bold(1)>
        <SU>Maaspoort * wo 14-10 * 20.15 uur</l_info></body>'''
        doc = read_docx(src)
        self.assertEqual([p.text for p in doc.paragraphs], [
            "VENLO", "Greatest hits 1 and more - Queen Must Go On Maaspoort * wo 14-10 * 20.15 uur"
        ])
        self.assertTrue(doc.paragraphs[1].runs[0].bold)
        self.assertFalse(bool(doc.paragraphs[1].runs[2].bold))

    def test_two_titles_in_one_info_block_create_separate_events(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info><bold>Over de Liefde</bold>
        <SU>Maaspoort * za 17-10 * 20.15 uur<EP>
        <bold>Voorlichtingsavond over borstvoeding</bold>
        Viecuri * wo 21-10 * 19.00 uur<EP></l_info></body>'''
        self.assertEqual([p.text for p in read_docx(src).paragraphs], [
            "VENLO", "Over de Liefde Maaspoort * za 17-10 * 20.15 uur",
            "Voorlichtingsavond over borstvoeding Viecuri * wo 21-10 * 19.00 uur"
        ])

    def test_extra_inline_tags_are_ignored_without_losing_text(self):
        src = ("<body><l_region>Vaals</l_region>"
               "<l_info><tracking><bold>Titel</bold></tracking>"
               "<SU>De <small_caps>zaal</small_caps> * 19.00 uur"
               "<extra_leading(2)><EP></l_info></body>")
        doc = read_docx(src)
        self.assertEqual([p.text for p in doc.paragraphs], [
            'VAALS', 'Titel De zaal * 19.00 uur'])
        self.assertTrue(doc.paragraphs[1].runs[0].bold)

    def test_tag_with_attributes_is_not_silently_discarded(self):
        src = ("<body><l_region>Vaals</l_region>"
               "<l_info><bold>Titel</bold><SU>Locatie <span class=x>"
               "andere tekst</l_info></body>")
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda(src)

    def test_numbered_bold_closing_tag_must_match(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info><bold(1)>Titel</bold(2)>Beschrijving</l_info></body>'''
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda(src)

    def test_numbered_bold_missing_closing_tag_is_rejected(self):
        src = '''<body><l_region>Venlo</l_region>
        <l_info><bold(1)>Titel</bold>Beschrijving</l_info></body>'''
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda(src)

    def test_plain_text_instead_of_tagged_agenda_is_rejected(self):
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda('Gewone tekst zonder agenda-tags')

    def test_unclosed_region_is_rejected(self):
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda('<body><l_region>Arcen<l_info><bold>Foo</bold>x</l_info></body>')

    def test_unclosed_bold_is_rejected(self):
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda('<body><l_region>Arcen</l_region><l_info><bold>Foo</l_info></body>')

    def test_event_without_place_is_rejected(self):
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda('<body><l_info><bold>Foo</bold>Text</l_info></body>')

    def test_empty_sections_only_are_rejected(self):
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda('<body><l_region>Arcen</l_region><l_info><EP></l_info></body>')

    def test_wrong_numbered_info_is_rejected(self):
        with self.assertRaises(InvalidTaggedAgenda):
            parse_tagged_agenda('<body><l_region>Arcen</l_region><l_info(1)><bold>Foo</bold>x</l_info(2)></body>')


if __name__ == "__main__":
    unittest.main()
