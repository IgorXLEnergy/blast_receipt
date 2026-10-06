import sys
import json
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
        self.assertEqual(result["decision"], "accepted")
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


    def fixture(self, name):
        path = Path(__file__).parent / "fixtures" / (name + ".json")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_carrefour_generic_blast_is_not_rejected_or_given_a_flavor(self):
        fixture = self.fixture("first")
        result = analyze_lines(fixture["ocr_lines"])
        self.assertEqual(result["decision"], "manual_review")
        self.assertTrue(result["blast"]["found"])
        self.assertEqual(result["blast"]["quantity"], 1)
        self.assertEqual(result["blast"]["spend"], 1.99)
        self.assertIsNone(result["blast"]["products"][0]["sku"])
        self.assertIn("variant_unresolved", result["review_reasons"])
        self.assertEqual(result["basket_candidates"], [])

    def test_lewiatan_preserves_two_unknown_items_and_their_own_prices(self):
        result = analyze_lines(self.fixture("second")["ocr_lines"])
        self.assertEqual(result["retailer"]["code"], "LEWIATAN")
        self.assertEqual(result["purchase_date"], "2026-10-06")
        self.assertEqual(result["decision"], "manual_review")
        self.assertEqual(result["blast"]["quantity"], 2)
        self.assertEqual(result["blast"]["spend"], 5.98)
        self.assertEqual(len(result["blast"]["products"]), 2)
        for product in result["blast"]["products"]:
            self.assertIsNone(product["sku"])
            self.assertEqual(product["unit_price"], 2.99)
            self.assertEqual(product["reported_family"], "BOOST")
        self.assertEqual(len(result["basket_candidates"]), 2)
        self.assertTrue(all("BATON" in x["raw_name"] for x in result["basket_candidates"]))
        self.assertTrue(all(x["unit_price"] == 2.49 for x in result["basket_candidates"]))

    def test_unpriced_product_does_not_borrow_next_product_price(self):
        result = analyze_lines(rows("BLAST KAKTUS", "BLAST ARBUZ 4,99"))
        self.assertIsNone(result["blast"]["products"][0]["line_total"])
        self.assertIsNone(result["blast"]["spend"])
        self.assertEqual(result["decision"], "manual_review")
        self.assertIn("price_missing", result["review_reasons"])

    def test_multiplication_sign_and_printed_arithmetic_conflict(self):
        result = analyze_lines(rows("BLAST KAKTUS", "3szt. ×3,99 10,00A"))
        product = result["blast"]["products"][0]
        self.assertEqual(product["quantity"], 3)
        self.assertEqual(product["unit_price"], 3.99)
        self.assertEqual(product["line_total"], 10.0)
        self.assertFalse(product["arithmetic_ok"])
        self.assertEqual(result["decision"], "manual_review")

    def test_split_flavor_line(self):
        result = analyze_lines(rows("BLAST BOOST", "CLEMENTINE", "1szt x2,99 2,99A"))
        self.assertEqual(result["blast"]["products"][0]["sku"], "BLAST-BOOST-CLEMENTINE")
        self.assertEqual(result["blast"]["spend"], 2.99)

    def test_tax_payment_and_totals_are_not_products(self):
        result = analyze_lines(rows("PARAGON FISKALNY", "BLAST KAKTUS 1,99", "Kwota C 05,00%", "Podatek PTU", "0,09", "SUMA PLN 1,99", "KARTA 1,99"))
        self.assertEqual(result["blast"]["spend"], 1.99)
        self.assertEqual(result["basket_candidates"], [])

    def test_retailer_boundaries_and_specific_chain_names(self):
        self.assertEqual(analyze_lines(rows("Carrefour Market", "PARAGON FISKALNY"))["retailer"]["name"], "Carrefour Market")
        self.assertEqual(analyze_lines(rows("EUROSPAR", "PARAGON FISKALNY"))["retailer"]["name"], "EUROSPAR")
        self.assertIsNone(analyze_lines(rows("DINOZAUR", "PARAGON FISKALNY"))["retailer"])

    def test_aggregate_does_not_hide_later_arithmetic_conflict(self):
        result = analyze_lines(rows("BLAST KAKTUS 1 x 3,99 3,99", "BLAST KAKTUS 2 x 3,99 7,00"))
        self.assertEqual(result["blast"]["quantity"], 3)
        self.assertEqual(result["decision"], "manual_review")
        self.assertIn("arithmetic_conflict", result["review_reasons"])

    def test_unrelated_brand_is_rejected(self):
        result = analyze_lines(rows("BLASTOFF 2,99"))
        self.assertFalse(result["blast"]["found"])
        self.assertEqual(result["decision"], "reject_no_blast")


if __name__ == "__main__":
    unittest.main()
