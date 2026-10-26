"""Reader-specific order and link invariants, independent of the full corpus."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reading_text import folio_sort_key, read_folios, viewer_link


class ReaderTests(unittest.TestCase):
    def test_folio_order_handles_recto_verso_and_foldout_panels(self):
        names = ["f10r", "f2v", "f2r2", "f2r1", "f1v"]
        self.assertEqual(
            sorted(names, key=folio_sort_key), ["f1v", "f2r1", "f2r2", "f2v", "f10r"]
        )

    def test_word_link_uses_exact_spelling_not_an_occurrence_number(self):
        self.assertEqual(
            viewer_link("f1r", "fachys"), "https://www.voynichese.com/#/f1r/exa:fachys"
        )
        self.assertEqual(viewer_link("f68v3"), "https://www.voynichese.com/#/f68v3")

    def test_xml_order_and_word_indices_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "f1r.xml"
            path.write_text(
                """<!-- Apache License, Version 2.0 -->
<folio name="f1r" wordCount="2"><word index="3">daiin</word><word index="0">shol</word></folio>"""
            )
            folios, fingerprints = read_folios(Path(directory))
            self.assertEqual(
                folios[0]["words"],
                [{"index": 3, "eva": "daiin"}, {"index": 0, "eva": "shol"}],
            )
            self.assertEqual(len(fingerprints["f1r.xml"]), 64)

    def test_duplicate_word_indices_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "f1r.xml"
            path.write_text(
                """<!-- Apache License, Version 2.0 -->
<folio name="f1r" wordCount="2"><word index="0">daiin</word><word index="0">shol</word></folio>"""
            )
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                read_folios(Path(directory))


if __name__ == "__main__":
    unittest.main()
