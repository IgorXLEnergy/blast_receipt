# Laravel adapter

This folder is a drop-in reference module for the existing BLAST Laravel backend. It is intentionally not a full Laravel application because the production project already exists.

Copy/adapt:

- `app/Services/ReceiptOcrClient.php`
- `app/Services/ReceiptInterpreter.php`
- migration / seeders
- config
- route snippet

Production recommendation:

1. Laravel receives/stores the image and creates a receipt record.
2. Queue worker calls `/v1/ocr`, not `/v1/analyze`.
3. Laravel applies DB-backed product aliases and retailer profiles.
4. Laravel persists OCR + interpreted fields.
5. Competition eligibility only uses accepted/reviewed receipts.

The Python `/v1/analyze` route is for rapid lab testing and rule prototyping.
