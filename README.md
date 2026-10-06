# BLAST Receipt Intelligence

Self-hosted receipt OCR / parsing lab for the BLAST app.

**Current version: v0.2 (test harness, not production competition eligibility).**

The repo is designed for two purposes:

1. let the BLAST team upload the first real receipts through a browser and inspect what OCR actually returns;
2. provide a clean integration path into the existing Laravel backend once the real retailer formats are known.

## What v0.2 detects

- Polish receipt text with PaddleOCR PP-OCRv6;
- major retailer name (starter markers);
- purchase date when present in a common format;
- the 7 initial BLAST products;
- BLAST quantity;
- displayed unit price;
- line total;
- simple adjacent discount lines and effective unit price;
- total BLAST spend / average effective unit price;
- raw non-BLAST candidate item lines for later basket analysis;
- OCR / match confidence and `accepted` vs `manual_review`.

The starting BLAST catalogue is in `shared/products.json`. Do not invent retailer abbreviations. Add them only after they are observed and manually confirmed on real receipts.

## Quick start on Ubuntu / Docker

```bash
cp .env.example .env
docker compose up --build
```

Open:

```text
http://YOUR_SERVER:8088
```

On the first boot PaddleOCR downloads model files, so startup is slower. The named Docker volume keeps the models for later restarts.

### API only

```bash
curl -F "file=@receipt.jpg" http://127.0.0.1:8088/v1/analyze
```

Raw OCR endpoint for Laravel:

```bash
curl -F "file=@receipt.jpg" http://127.0.0.1:8088/v1/ocr
```

## Repository structure

```text
service/             FastAPI + PaddleOCR + browser test UI
shared/              starter BLAST product catalogue + retailer markers
laravel-adapter/     integration reference for the existing Laravel backend
docs/                architecture, API, validation plan and roadmap
.github/workflows/    parser tests + PHP syntax checks
```

## Important boundary

The browser lab currently contains a starter parser so the first receipts can be tested immediately. In production, Laravel should remain the system of record and own:

- product aliases,
- retailer-specific rules,
- manual review,
- duplicate / fraud controls,
- persistent receipt/basket data,
- competition eligibility.

The OCR service should remain stateless and replaceable.

## First data milestone

Collect roughly 30-50 varied receipts per priority chain before optimizing the model. Measure exact SKU / quantity / price accuracy separately from OCR character accuracy. See `docs/TEST_PLAN.md`.

## Security before public exposure

This lab has no authentication and should **not** be exposed to the public internet. Put it behind VPN / Cloudflare Access / basic internal reverse-proxy auth during testing. Production upload endpoints must use app authentication, rate limiting, file validation, retention rules and duplicate detection.

## Running lightweight tests without PaddleOCR

```bash
make test
make lint
```

These validate parser logic and PHP syntax without downloading OCR models.

## GitHub

This directory is ready to initialize as a repository:

```bash
git init
git add .
git commit -m "Initial BLAST receipt intelligence lab"
git branch -M main
git remote add origin git@github.com:YOUR_ORG/blast-receipt-intelligence.git
git push -u origin main
```

Do not commit `.env`, model caches or receipt images.
