import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parser import analyze_lines  # noqa: E402


def rows(*lines):
    return [{"text": x, "confidence": 0.99, "box": None} for x in lines]


class ParserTests(unittest.TestCase):
    def test_qty_unit_and_total(self):
        result = analyze_lines(rows(
            "CARREFOUR POLSKA",
            "06.10.2026",
            "BLAST KAKTUS 3 x 3,99",
            "11,97",
        ))
        self.assertEqual(result["retailer"]["code"], "CARREFOUR")
        self.assertEqual(result["blast"]["quantity"], 3)
        product = result["blast"]["products"][0]
        self.assertEqual(product["unit_price"], 3.99)
        self.assertEqual(product["line_total"], 11.97)

    def test_repeated_lines_are_aggregated(self):
        result = analyze_lines(rows(
            "DINO POLSKA",
            "BLAST BOOST KIWI 3,99",
            "BLAST BOOST KIWI 3,99",
            "BLAST BOOST KIWI 3,99",
        ))
        self.assertEqual(result["blast"]["quantity"], 3)
        self.assertEqual(result["blast"]["spend"], 11.97)

    def test_discount(self):
        result = analyze_lines(rows(
            "LIDL",
            "BLAST ARBUZ 4,99",
            "RABAT -1,00",
        ))
        p = result["blast"]["products"][0]
        self.assertEqual(p["unit_price"], 4.99)
        self.assertEqual(p["effective_unit_price"], 3.99)

    def test_basket_candidate(self):
        result = analyze_lines(rows(
            "ZABKA",
            "BLAST BOOST CLEMENTINE 4,49",
            "LAYS PAPRYKA 140G 6,99",
            "SUMA 11,48",
        ))
        self.assertEqual(len(result["basket_candidates"]), 1)
        self.assertIn("LAYS", result["basket_candidates"][0]["normalized_name"])


if __name__ == "__main__":
    unittest.main()
