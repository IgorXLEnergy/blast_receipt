from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Iterable

from .catalog import products as product_catalog
from .catalog import retailers as retailer_catalog

MONEY_RE = re.compile(r"(?<!\d)(-?\d{1,4}[,.]\d{2})(?!\d)")
QTY_X_PRICE_RE = re.compile(r"(?<!\d)(\d{1,3})\s*(?:X|\*)\s*(\d{1,4}[,.]\d{2})(?!\d)")
QTY_SZT_RE = re.compile(r"(?<!\d)(\d{1,3})\s*(?:SZT|SZT\.)\b")
QTY_ILOSC_RE = re.compile(r"\bILOSC\s*[:=\-]?\s*(\d{1,3})\b")
DATE_PATTERNS = [
    re.compile(r"\b(\d{2})[.\-/](\d{2})[.\-/](\d{4})\b"),
    re.compile(r"\b(\d{4})[.\-/](\d{2})[.\-/](\d{2})\b"),
]
DISCOUNT_MARKERS = ("RABAT", "PROMOC", "OBNIZ", "UPUST", "RAB.")
NON_ITEM_MARKERS = (
    "SUMA", "RAZEM", "PLN", "VAT", "PTU", "KARTA", "GOTOWKA", "RESZTA", "PARAGON",
    "SPRZEDAZ", "NIP", "KASA", "KASJER", "TRANSAKC", "DO ZAPLATY", "ZAPLACONO",
)


def normalize(value: str) -> str:
    value = value.upper().replace("Ł", "L")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^A-Z0-9.,/%+*X -]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def money(value: str) -> float:
    return round(float(value.replace(",", ".")), 2)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def token_overlap(a: str, b: str) -> float:
    aa = {x for x in normalize(a).split() if len(x) > 1}
    bb = {x for x in normalize(b).split() if len(x) > 1}
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(bb)


def is_blastish(line: str) -> bool:
    n = normalize(line)
    if any(token in n for token in ("BLAST", "BLST", "BLA5T")):
        return True
    # Keep this conservative. Flavor-only lines are handled only when directly next to a BLAST line.
    return False


def extract_quantity_and_price(lines: list[str], index: int) -> dict[str, Any]:
    context_indices = [index, index + 1, index - 1, index + 2]
    context = [normalize(lines[i]) for i in context_indices if 0 <= i < len(lines)]

    quantity = 1
    unit_price = None
    line_total = None
    source = "single_line"

    for text in context:
        m = QTY_X_PRICE_RE.search(text)
        if m:
            quantity = max(1, min(200, int(m.group(1))))
            unit_price = money(m.group(2))
            source = "qty_x_unit"
            break

    if quantity == 1:
        for text in context:
            m = QTY_SZT_RE.search(text) or QTY_ILOSC_RE.search(text)
            if m:
                quantity = max(1, min(200, int(m.group(1))))
                source = "explicit_qty"
                break

    current_amounts = [money(x) for x in MONEY_RE.findall(normalize(lines[index]))]
    nearby_amounts: list[float] = []
    for text in context:
        nearby_amounts.extend(money(x) for x in MONEY_RE.findall(text))

    if quantity > 1 and unit_price is not None:
        expected = round(quantity * unit_price, 2)
        plausible = [v for v in nearby_amounts if abs(v - expected) <= 0.03]
        line_total = plausible[0] if plausible else expected
    elif current_amounts:
        line_total = current_amounts[-1]
        unit_price = line_total
    elif nearby_amounts:
        # Conservative fallback used only for the matched product line context.
        candidate = next((v for v in nearby_amounts if v > 0), None)
        if candidate is not None:
            line_total = candidate
            unit_price = round(candidate / quantity, 2) if quantity else candidate

    if quantity > 1 and unit_price is None and line_total is not None:
        unit_price = round(line_total / quantity, 2)

    discount_total = 0.0
    for i in (index + 1, index + 2):
        if 0 <= i < len(lines):
            text = normalize(lines[i])
            if any(marker in text for marker in DISCOUNT_MARKERS):
                vals = [money(x) for x in MONEY_RE.findall(text)]
                if vals:
                    val = vals[-1]
                    discount_total += val if val < 0 else -abs(val)

    effective_total = None
    effective_unit_price = None
    if line_total is not None:
        effective_total = round(max(0.0, line_total + discount_total), 2)
        effective_unit_price = round(effective_total / max(1, quantity), 2)

    arithmetic_ok = None
    if unit_price is not None and line_total is not None:
        arithmetic_ok = abs(quantity * unit_price - line_total) <= 0.05

    return {
        "quantity": quantity,
        "unit_price": unit_price,
        "line_total": line_total,
        "discount_total": round(discount_total, 2),
        "effective_unit_price": effective_unit_price,
        "effective_total": effective_total,
        "price_source": source,
        "arithmetic_ok": arithmetic_ok,
    }


def detect_retailer(lines: list[str]) -> dict[str, Any] | None:
    head = " ".join(normalize(x) for x in lines[:20])
    best = None
    best_score = 0.0
    for retailer in retailer_catalog():
        for marker in retailer.get("markers", []):
            n = normalize(marker)
            score = 0.995 if n and n in head else similarity(head, n)
            if score > best_score:
                best = retailer
                best_score = score
    if best is None or best_score < 0.62:
        return None
    return {"code": best["code"], "name": best["name"], "confidence": round(best_score, 4)}


def detect_date(lines: list[str]) -> str | None:
    for raw in lines[:30]:
        text = normalize(raw)
        for idx, pattern in enumerate(DATE_PATTERNS):
            m = pattern.search(text)
            if not m:
                continue
            try:
                if idx == 0:
                    dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                else:
                    dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                return dt.date().isoformat()
            except ValueError:
                pass
    return None


def product_score(line: str, product: dict[str, Any]) -> tuple[float, str]:
    n = normalize(line)
    best_score = 0.0
    best_method = "none"
    for alias in product.get("aliases", []):
        a = normalize(alias)
        if a and (a in n or n in a) and min(len(a), len(n)) >= 7:
            score = 0.99
            method = "contains"
        else:
            score = max(similarity(n, a), token_overlap(n, a))
            method = "fuzzy"
        if score > best_score:
            best_score, best_method = score, method

    keyword_hits = sum(1 for kw in product.get("keywords", []) if normalize(kw) in n)
    if keyword_hits >= 2:
        best_score = max(best_score, min(0.98, 0.76 + keyword_hits * 0.06))
        best_method = "keywords"
    return best_score, best_method


def match_product(line: str) -> dict[str, Any] | None:
    if not is_blastish(line):
        return None
    best = None
    best_score = 0.0
    best_method = "none"
    for product in product_catalog():
        score, method = product_score(line, product)
        if score > best_score:
            best, best_score, best_method = product, score, method
    if best is None or best_score < 0.55:
        return None
    return {**best, "match_score": round(best_score, 4), "match_method": best_method}


def _aggregate(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in matches:
        sku = item["sku"]
        if sku not in grouped:
            grouped[sku] = dict(item)
            continue
        g = grouped[sku]
        old_qty = g["quantity"]
        new_qty = item["quantity"]
        g["quantity"] = old_qty + new_qty
        if g.get("effective_total") is not None and item.get("effective_total") is not None:
            g["effective_total"] = round(g["effective_total"] + item["effective_total"], 2)
            g["effective_unit_price"] = round(g["effective_total"] / g["quantity"], 2)
        if g.get("line_total") is not None and item.get("line_total") is not None:
            g["line_total"] = round(g["line_total"] + item["line_total"], 2)
            g["unit_price"] = round(g["line_total"] / g["quantity"], 2)
        g["discount_total"] = round(g.get("discount_total", 0) + item.get("discount_total", 0), 2)
        g["match_score"] = max(g["match_score"], item["match_score"])
        g["source_lines"] = g.get("source_lines", []) + item.get("source_lines", [])
    return list(grouped.values())


def _candidate_basket_items(lines: list[str], blast_line_indexes: set[int]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, raw in enumerate(lines):
        if i in blast_line_indexes:
            continue
        n = normalize(raw)
        if len(re.sub(r"[^A-Z]", "", n)) < 3:
            continue
        if any(marker in n for marker in NON_ITEM_MARKERS):
            continue
        amounts = MONEY_RE.findall(n)
        if not amounts:
            continue
        price = money(amounts[-1])
        if price <= 0:
            continue
        qty_price = extract_quantity_and_price(lines, i)
        # Use raw text for the first dataset; canonical product/category mapping is a later layer.
        items.append({
            "line_index": i,
            "raw_name": raw,
            "normalized_name": n,
            "quantity": qty_price["quantity"],
            "unit_price": qty_price["unit_price"],
            "line_total": qty_price["line_total"],
        })
    return items[:100]


def analyze_lines(ocr_lines: Iterable[dict[str, Any]], auto_threshold: float = 0.94, review_threshold: float = 0.72) -> dict[str, Any]:
    rows = list(ocr_lines)
    raw_lines = [str(row.get("text", "")) for row in rows]
    retailer = detect_retailer(raw_lines)
    purchase_date = detect_date(raw_lines)

    matches: list[dict[str, Any]] = []
    blast_line_indexes: set[int] = set()
    for i, raw in enumerate(raw_lines):
        match = match_product(raw)
        if not match:
            # A receipt may split a product over two OCR lines. Try the current + next line.
            if i + 1 < len(raw_lines) and is_blastish(raw):
                match = match_product(raw + " " + raw_lines[i + 1])
            if not match:
                continue
        price = extract_quantity_and_price(raw_lines, i)
        ocr_conf = rows[i].get("confidence")
        ocr_conf = float(ocr_conf) if ocr_conf is not None else 0.8
        combined = round(min(match["match_score"], max(0.0, ocr_conf)), 4)
        blast_line_indexes.add(i)
        matches.append({
            "sku": match["sku"],
            "canonical_name": match["canonical_name"],
            **price,
            "match_score": match["match_score"],
            "ocr_confidence": round(ocr_conf, 4),
            "confidence": combined,
            "match_method": match["match_method"],
            "source_lines": [raw],
            "line_index": i,
        })

    blast_items = _aggregate(matches)
    total_qty = sum(int(x["quantity"]) for x in blast_items)
    totals = [x.get("effective_total") for x in blast_items if x.get("effective_total") is not None]
    blast_spend = round(sum(totals), 2) if totals else None
    weighted_price = round(blast_spend / total_qty, 2) if blast_spend is not None and total_qty else None
    best_conf = max((x["confidence"] for x in blast_items), default=0.0)
    min_conf = min((x["confidence"] for x in blast_items), default=0.0)

    arithmetic_conflict = any(x.get("arithmetic_ok") is False for x in blast_items)
    if not blast_items:
        decision = "reject_no_blast"
    elif arithmetic_conflict or min_conf < review_threshold:
        decision = "manual_review"
    elif min_conf >= auto_threshold:
        decision = "accepted"
    else:
        decision = "manual_review"

    return {
        "decision": decision,
        "confidence": round(best_conf, 4),
        "retailer": retailer,
        "purchase_date": purchase_date,
        "blast": {
            "found": bool(blast_items),
            "quantity": total_qty,
            "spend": blast_spend,
            "average_effective_unit_price": weighted_price,
            "products": blast_items,
        },
        "basket_candidates": _candidate_basket_items(raw_lines, blast_line_indexes),
        "ocr": {
            "line_count": len(rows),
            "lines": [
                {
                    "index": i,
                    "text": row.get("text", ""),
                    "confidence": row.get("confidence"),
                    "box": row.get("box"),
                }
                for i, row in enumerate(rows)
            ],
            "raw_text": "\n".join(raw_lines),
        },
    }
