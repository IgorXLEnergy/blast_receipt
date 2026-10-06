# Architecture

## Test / data-collection mode

`browser -> FastAPI /v1/analyze -> PaddleOCR PP-OCRv6 -> parser -> JSON -> browser`

The included UI is intentionally a lab tool. It lets the BLAST team upload real receipts, inspect raw OCR, verify SKU / quantity / price extraction and build the first labelled dataset before production integration.

## Production target

`BLAST app -> Laravel -> queue -> OCR service /v1/ocr -> Laravel receipt interpreter -> DB -> challenge/competition engine`

Laravel remains the system of record. The OCR service is replaceable and stateless. In production, product aliases, retailer-specific patterns, review history, duplicate detection and competition eligibility should live in Laravel.

## Why both /v1/ocr and /v1/analyze?

- `/v1/ocr` is the production-friendly primitive: image -> text, boxes, confidence.
- `/v1/analyze` is the test harness: image -> OCR + starter BLAST interpretation.

The lab parser is not meant to become a second source of truth. Once real receipt profiles are known, port proven rules into the Laravel interpreter and DB-backed alias tables.
