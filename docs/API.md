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
- `manual_review`: BLAST is plausible but confidence / pricing consistency is insufficient for automatic use.
- `reject_no_blast`: no BLAST product was detected.

Do not use the lab decision directly for prizes or competition eligibility until validation targets are reached on a labelled receipt set.
