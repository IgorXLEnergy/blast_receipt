# API

## `GET /health`
Returns service and OCR configuration.

## `POST /v1/ocr`
Multipart field: `file` (`image/jpeg`, `image/png`, `image/webp`).

Returns SHA-256, OCR lines, bounding boxes and confidence.

## `POST /v1/analyze`
Same upload contract. Adds:

- retailer detection,
- purchase date,
- BLAST SKU matching,
- quantity,
- unit price,
- discount,
- effective unit price,
- BLAST spend,
- candidate non-BLAST basket lines,
- decision/confidence.

### Decision semantics

- `accepted`: all detected BLAST matches are above the automatic threshold and no arithmetic conflict was found.
- `manual_review`: BLAST is present but its variant is unresolved, price is missing, arithmetic conflicts, or matching confidence is insufficient.
- `reject_no_blast`: no BLAST product was detected.

Do not use the lab decision directly for prizes or competition eligibility until validation targets are reached on a labelled receipt set.

### Brand detection and unresolved variants

A generic BLAST receipt description is retained with `sku: null` and
`variant_status: "unresolved"`. Separate unknown receipt items are not merged:
two identical descriptions can represent different products. `brand_confidence`
reports OCR confidence for the source description; `variant_confidence` and the
legacy `confidence` are matching scores, not calibrated probabilities. A zero
variant score means the variant is unresolved, not that BLAST is absent.

`reported_family` preserves a BOOST hint from the receipt only; retailers can
mislabel Very Nice as BOOST. It is not a confirmed product family. User-confirmed
labels are validation evidence and do not automatically create receipt aliases.

`review_reasons` contains `variant_unresolved`, `price_missing`,
`arithmetic_conflict`, or `low_variant_confidence`. BLAST totals are null if any
BLAST item lacks a price, rather than silently reporting a partial total.

Prices are associated with the item and following quantity/packaging lines,
stopping at the next product or fiscal footer. Percentages, taxes and payments
are excluded from basket items. Dates are searched throughout the OCR output.
Retailer display names include the user-provided distribution list; these names
are not a purchase eligibility allowlist or proof of a particular franchise.

These semantics describe the Python browser lab. The Laravel adapter remains
an integration reference and requires equivalent validation before production use.
