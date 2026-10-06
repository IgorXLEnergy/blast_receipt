from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .ocr_engine import run_ocr
from .parser import analyze_lines

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR.parent / "static"

app = FastAPI(title="BLAST Receipt Intelligence Lab", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = int(float(os.getenv("OCR_MAX_FILE_MB", "12")) * 1024 * 1024)
AUTO_THRESHOLD = float(os.getenv("BLAST_AUTO_ACCEPT_THRESHOLD", "0.94"))
REVIEW_THRESHOLD = float(os.getenv("BLAST_MANUAL_REVIEW_THRESHOLD", "0.72"))


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "blast-receipt-intelligence",
        "version": "0.2.0",
        "ocr_lang": os.getenv("OCR_LANG", "pl"),
        "ocr_version": os.getenv("OCR_VERSION", "PP-OCRv6"),
    }


async def _store_temp(file: UploadFile) -> tuple[str, str, int]:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Supported formats: JPG, PNG, WEBP")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large")
    suffix = Path(file.filename or "receipt.jpg").suffix.lower() or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(raw)
    tmp.close()
    return tmp.name, hashlib.sha256(raw).hexdigest(), len(raw)


@app.post("/v1/ocr")
async def ocr(file: UploadFile = File(...)):
    path, sha256, size = await _store_temp(file)
    try:
        lines = run_ocr(path)
        return {
            "sha256": sha256,
            "bytes": size,
            "lines": lines,
            "raw_text": "\n".join(x["text"] for x in lines),
        }
    finally:
        Path(path).unlink(missing_ok=True)


@app.post("/v1/analyze")
async def analyze(file: UploadFile = File(...)):
    path, sha256, size = await _store_temp(file)
    try:
        lines = run_ocr(path)
        result = analyze_lines(lines, AUTO_THRESHOLD, REVIEW_THRESHOLD)
        result["receipt_image"] = {"sha256": sha256, "bytes": size, "filename": file.filename}
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        Path(path).unlink(missing_ok=True)
