from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Iterable

from .catalog import products as product_catalog
from .catalog import retailers as retailer_catalog

MONEY_RE = re.compile(r"(?<!\d)(-?\d{1,4}[,.]\d{2})(?!\d|\s*%)")
QTY_X_PRICE_RE = re.compile(r"(?<!\d)(\d{1,3})\s*(?:SZT\.?)?\s*(?:X|\*)\s*(\d{1,4}[,.]\d{2})(?!\d)")
QTY_SZT_RE = re.compile(r"(?<!\d)(\d{1,3})\s*(?:SZT|SZT\.)\b")
QTY_ILOSC_RE = re.compile(r"\bILOSC\s*[:=\-]?\s*(\d{1,3})\b")
DATE_PATTERNS = [
    re.compile(r"\b(\d{2})[.\-/](\d{2})[.\-/](\d{4})\b"),
    re.compile(r"\b(\d{4})[.\-/](\d{2})[.\-/](\d{2})\b"),
]
DISCOUNT_MARKERS = ("RABAT", "PROMOC", "OBNIZ", "UPUST", "RAB.")
NON_ITEM_MARKERS = (
    "SUMA", "RAZEM", "PLN", "VAT", "PTU", "KARTA", "GOTOWKA", "RESZTA", "PARAGON",
    "SPRZED", "KWOTA", "ROZLICZENIE", "NIP", "KASA", "KASJER", "TRANSAKC", "DO ZAPLATY", "ZAPLACONO",
)


def normalize(value: str) -> str:
    value = value.upper().replace("Ł", "L").replace("×", "X")
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
    if re.search(r"\b(?:BLAST|BLST|BLA5T)\b", n):
        return True
    # Keep this conservative. Flavor-only lines are handled only when directly next to a BLAST line.
    return False


def _is_control(text: str) -> bool:
    return any(marker in text for marker in NON_ITEM_MARKERS) or "%" in text


def _is_price_line(text: str) -> bool:
    return bool(QTY_X_PRICE_RE.match(text) or QTY_SZT_RE.match(text) or
                re.fullmatch(r"[\d.,=+*X A-D-]+", text))


def _is_continuation(text: str) -> bool:
    # Packaging and explicit flavor fragments can be split off by OCR.
    return bool(re.fullmatch(
        r"(?:PUSZ|BUT|PET|ML|A|B|C|D|KAKTUS|MANGO|ANANAS|KLASYK|ARBUZ|"
        r"TRIPLE|BERRY|CLEMENTINE|KIWI|[0-9]+|[0-9]+ML)(?:[ .-]+(?:"
        r"PUSZ|BUT|PET|ML|A|B|C|D|KAKTUS|MANGO|ANANAS|KLASYK|ARBUZ|"
        r"TRIPLE|BERRY|CLEMENTINE|KIWI|[0-9]+|[0-9]+ML))*", text))


def _item_context(lines: list[str], index: int) -> list[int]:
    indices = [index]
    for i in range(index + 1, min(len(lines), index + 6)):
        text = normalize(lines[i])
        if _is_control(text):
            break
        discount = any(marker in text for marker in DISCOUNT_MARKERS)
        if not (discount or _is_price_line(text) or _is_continuation(text)):
            break  # Never take a price from the next product or previous product.
        indices.append(i)
    return indices


def extract_quantity_and_price(lines: list[str], index: int) -> dict[str, Any]:
    context = [normalize(lines[i]) for i in _item_context(lines, index)]
    quantity = 1
    unit_price = line_total = None
    source = "missing"
    price_texts = [t for t in context if not any(m in t for m in DISCOUNT_MARKERS)]
    for text in price_texts:
        m = QTY_X_PRICE_RE.search(text)
        if m:
            quantity = max(1, min(200, int(m.group(1))))
            unit_price = money(m.group(2))
            amounts = [money(v) for v in MONEY_RE.findall(text)]
            line_total = amounts[-1] if len(amounts) > 1 else round(quantity * unit_price, 2)
            source = "qty_x_unit"
            # A standalone following amount is the printed total, including conflicts.
            position = price_texts.index(text)
            if len(amounts) == 1 and position + 1 < len(price_texts):
                following = price_texts[position + 1]
                if re.fullmatch(r"-?\d{1,4}[,.]\d{2}(?: [A-D])?", following):
                    line_total = money(MONEY_RE.search(following).group(1))
            break
    if unit_price is None:
        for text in price_texts:
            m = QTY_SZT_RE.search(text) or QTY_ILOSC_RE.search(text)
            if m:
                quantity = max(1, min(200, int(m.group(1))))
                source = "explicit_qty"
                break
        for text in price_texts:
            amounts = [money(v) for v in MONEY_RE.findall(text)]
            if amounts:
                line_total = amounts[-1]
                unit_price = round(line_total / quantity, 2)
                if source == "missing":
                    source = "single_line" if text == context[0] else "following_line"
                break
    discount_total = 0.0
    for text in context:
        if any(marker in text for marker in DISCOUNT_MARKERS):
            vals = [money(v) for v in MONEY_RE.findall(text)]
            if vals:
                discount_total -= abs(vals[-1])
    effective_total = round(max(0.0, line_total + discount_total), 2) if line_total is not None else None
    return {
        "quantity": quantity,
        "unit_price": unit_price,
        "line_total": line_total,
        "discount_total": round(discount_total, 2),
        "effective_unit_price": round(effective_total / quantity, 2) if effective_total is not None else None,
        "effective_total": effective_total,
        "price_source": source,
        "arithmetic_ok": abs(quantity * unit_price - line_total) <= 0.05 if unit_price is not None and line_total is not None else None,
    }


def detect_retailer(lines: list[str]) -> dict[str, Any] | None:
    header = []
    for line in lines[:20]:
        if "PARAGON" in normalize(line):
            break
        header.append(normalize(line))
    head = " ".join(header)
    exact = []
    for retailer in retailer_catalog():
        for marker in retailer.get("markers", []):
            n = normalize(marker)
            if n and re.search(r"(?<![A-Z0-9])" + re.escape(n) + r"(?![A-Z0-9])", head):
                exact.append((len(n), retailer))
    if not exact:
        return None
    _, best = max(exact, key=lambda entry: entry[0])
    return {"code": best["code"], "name": best["name"], "confidence": 0.995}


def detect_date(lines: list[str]) -> str | None:
    for raw in lines:
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
    scored = sorted(
        [(product_score(line, p), p) for p in product_catalog()],
        key=lambda entry: entry[0][0], reverse=True,
    )
    n = normalize(line)
    best_score, method = scored[0][0] if scored else (0.0, "none")
    best = scored[0][1] if scored else None
    second_score = scored[1][0][0] if len(scored) > 1 else 0.0
    # Brand/family words alone do not establish a flavor or SKU.
    flavor_words = [normalize(k) for k in best.get("keywords", []) if k not in ("BLAST", "BOOST", "ENERGY")] if best else []
    has_flavor = bool(flavor_words) and all(
        re.search(r"(?<![A-Z0-9])" + re.escape(k) + r"(?![A-Z0-9])", n) for k in flavor_words
    )
    if best and has_flavor and best_score >= 0.72 and best_score - second_score >= 0.08:
        return {**best, "match_score": round(best_score, 4), "match_method": method}
    return {
        "sku": None,
        "canonical_name": "BLAST — wariant nieustalony",
        "match_score": 0.0,
        "match_method": "brand_only",
    }


def _aggregate(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str | tuple[str, int], dict[str, Any]] = {}
    for item in matches:
        sku = item["sku"] or ("unresolved", item["line_index"])
        if sku not in grouped:
            grouped[sku] = dict(item)
            continue
        g = grouped[sku]
        new_qty = item["quantity"]
        g["quantity"] += new_qty
        if g.get("effective_total") is not None and item.get("effective_total") is not None:
            g["effective_total"] = round(g["effective_total"] + item["effective_total"], 2)
            g["effective_unit_price"] = round(g["effective_total"] / g["quantity"], 2)
        else:
            g["effective_total"] = g["effective_unit_price"] = None
        if g.get("line_total") is not None and item.get("line_total") is not None:
            g["line_total"] = round(g["line_total"] + item["line_total"], 2)
            g["unit_price"] = round(g["line_total"] / g["quantity"], 2)
        else:
            g["line_total"] = g["unit_price"] = None
        g["discount_total"] = round(g.get("discount_total", 0) + item.get("discount_total", 0), 2)
        for field in ("match_score", "confidence", "brand_confidence", "variant_confidence"):
            g[field] = min(g[field], item[field])
        if item["arithmetic_ok"] is False:
            g["arithmetic_ok"] = False
        g["source_lines"] = g.get("source_lines", []) + item.get("source_lines", [])
    return list(grouped.values())


def _candidate_basket_items(lines: list[str], blast_line_indexes: set[int]) -> list[dict[str, Any]]:
    items = []
    fiscal = next((i for i, line in enumerate(lines) if "PARAGON" in normalize(line)), -1)
    for i in range(fiscal + 1, len(lines)):
        if i in blast_line_indexes:
            continue
        raw = lines[i]
        n = normalize(raw)
        if _is_control(n):
            if i > fiscal and any(m in n for m in ("SPRZED", "SUMA", "ROZLICZENIE")):
                break
            continue
        if _is_price_line(n) or _is_continuation(n) or is_blastish(raw):
            continue
        if len(re.sub(r"[^A-Z]", "", n)) < 3:
            continue
        price = extract_quantity_and_price(lines, i)
        if price["line_total"] is None or price["line_total"] <= 0:
            continue
        items.append({"line_index": i, "raw_name": raw, "normalized_name": n,
                      "quantity": price["quantity"], "unit_price": price["unit_price"],
                      "line_total": price["line_total"]})
    return items[:100]


def analyze_lines(ocr_lines: Iterable[dict[str, Any]], auto_threshold: float = 0.94, review_threshold: float = 0.72) -> dict[str, Any]:
    rows = list(ocr_lines)
    raw_lines = [str(row.get("text", "")) for row in rows]
    retailer = detect_retailer(raw_lines)
    purchase_date = detect_date(raw_lines)

    matches: list[dict[str, Any]] = []
    blast_line_indexes: set[int] = set()
    for i, raw in enumerate(raw_lines):
        if i in blast_line_indexes:
            continue
        match = match_product(raw)
        if match and match["sku"] is None:
            indices = _item_context(raw_lines, i)
            match = match_product(" ".join(raw_lines[j] for j in indices))
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
        blast_line_indexes.update(_item_context(raw_lines, i))
        matches.append({
            "sku": match["sku"],
            "canonical_name": match["canonical_name"],
            **price,
            "match_score": match["match_score"],
            "ocr_confidence": round(ocr_conf, 4),
            "confidence": combined,
            "match_method": match["match_method"],
            "variant_status": "identified" if match["sku"] else "unresolved",
            "brand_confidence": round(ocr_conf, 4),
            "variant_confidence": combined,
            "reported_family": "BOOST" if "BOOST" in normalize(raw) else None,
            "source_lines": [raw],
            "line_index": i,
        })

    blast_items = _aggregate(matches)
    total_qty = sum(int(x["quantity"]) for x in blast_items)
    totals = [x.get("effective_total") for x in blast_items if x.get("effective_total") is not None]
    blast_spend = round(sum(totals), 2) if totals and len(totals) == len(blast_items) else None
    weighted_price = round(blast_spend / total_qty, 2) if blast_spend is not None and total_qty else None
    best_conf = max((x["confidence"] for x in blast_items), default=0.0)
    min_conf = min((x["confidence"] for x in blast_items), default=0.0)

    arithmetic_conflict = any(x.get("arithmetic_ok") is False for x in blast_items)
    review_reasons = []
    if any(x["sku"] is None for x in blast_items):
        review_reasons.append("variant_unresolved")
    if any(x["line_total"] is None for x in blast_items):
        review_reasons.append("price_missing")
    if arithmetic_conflict:
        review_reasons.append("arithmetic_conflict")
    if blast_items and min_conf < auto_threshold and not review_reasons:
        review_reasons.append("low_variant_confidence")
    if not blast_items:
        decision = "reject_no_blast"
    elif any(x["sku"] is None or x["line_total"] is None for x in blast_items) or arithmetic_conflict or min_conf < review_threshold:
        decision = "manual_review"
    elif min_conf >= auto_threshold:
        decision = "accepted"
    else:
        decision = "manual_review"

    return {
        "decision": decision,
        "confidence": round(best_conf, 4),
        "review_reasons": review_reasons,
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
