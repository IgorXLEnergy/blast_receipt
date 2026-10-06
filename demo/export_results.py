"""Export anonymized, recorded OCR fixtures through the current parser."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "service"))
from app.parser import analyze_lines
from app.catalog import products

names = {p["sku"]: p["canonical_name"] for p in products()}
descriptions = {
    "first": "Carrefour: ogólny opis BLAST, bez informacji o smaku. 1 sztuka za 1,99 zł.",
    "second": "Lewiatan: dwa opisy BOOST, choć kupiono Classic i Clementine. 2 sztuki za 5,98 zł.",
}
changes = {
    "first": "Przed poprawką: odrzucenie jako brak BLAST. Teraz: wykryta marka, 1 sztuka za 1,99 zł i ręczna weryfikacja wariantu.",
    "second": "Przed poprawką: 5,48 zł i domyślny Triple Berry, bez sklepu i daty. Teraz: 5,98 zł, Lewiatan, poprawna data i dwa nieustalone warianty.",
}
cases = {}
for case in descriptions:
    fixture = json.loads((ROOT / "service/tests/fixtures" / f"{case}.json").read_text(encoding="utf-8"))
    result = analyze_lines(fixture["ocr_lines"])
    result["ocr"]["raw_text"] = "\n".join(row["text"] for row in fixture["ocr_lines"] if row["text"])
    cases[case] = {
        "description": descriptions[case],
        "change": changes[case],
        "confirmed": [f'{p["quantity"]} × {names[p["sku"]]}' for p in fixture["confirmed_products"]],
        "result": result,
    }
(ROOT / "demo/data.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
