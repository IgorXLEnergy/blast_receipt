# Roadmap

## v0.2 - current repo
- PP-OCRv6 Polish OCR
- browser upload lab
- 7 initial BLAST products
- retailer-name detection
- quantity and price extraction
- simple discount handling
- raw basket candidate capture
- confidence + manual review state

## v0.3 - real receipt profiles
- add retailer-specific parsers from real samples
- exact transaction/date/receipt-number parsing
- stronger quantity syntax handling
- per-retailer aliases sourced only from validated receipts
- semantic duplicate fingerprint

## v0.4 - review/data flywheel
- Laravel admin review screen
- approve/correct SKU, qty, unit price, retailer
- approved correction -> alias/rule candidate
- export labelled dataset

## v0.5 - basket intelligence
- normalize non-BLAST products
- category taxonomy
- frequently-bought-with-BLAST analysis
- retailer/SKU/price-band comparisons

## v1.0 - production gate
- measured false-accept rate below agreed threshold
- rate limiting / abuse prevention
- retention/privacy policy
- monitoring, queue retries, alerting
- competition engine integration
