from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None


def _as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _jsonish(result: Any) -> dict[str, Any]:
    value = getattr(result, "json", None)
    if callable(value):
        value = value()
    if isinstance(value, dict):
        return value
    if isinstance(result, dict):
        return result
    return {}


@lru_cache(maxsize=1)
def get_engine():
    if PaddleOCR is None:
        raise RuntimeError("PaddleOCR is not installed")
    return PaddleOCR(
        lang=os.getenv("OCR_LANG", "pl"),
        ocr_version=os.getenv("OCR_VERSION", "PP-OCRv6"),
        device=os.getenv("OCR_DEVICE", "cpu"),
        use_doc_orientation_classify=_as_bool("OCR_ENABLE_ORIENTATION", True),
        use_doc_unwarping=_as_bool("OCR_ENABLE_UNWARPING", True),
        use_textline_orientation=_as_bool("OCR_ENABLE_ORIENTATION", True),
        text_rec_score_thresh=float(os.getenv("OCR_TEXT_SCORE_THRESHOLD", "0.20")),
    )


def extract_lines(prediction: list[Any]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for page in prediction:
        payload = _jsonish(page)
        data = payload.get("res", payload)
        texts = data.get("rec_texts", []) or []
        scores = data.get("rec_scores", []) or []
        boxes = data.get("rec_boxes", []) or data.get("dt_polys", []) or []
        for i, text in enumerate(texts):
            box = boxes[i] if i < len(boxes) else None
            if hasattr(box, "tolist"):
                box = box.tolist()
            lines.append({
                "text": str(text),
                "confidence": float(scores[i]) if i < len(scores) else None,
                "box": box,
            })
    return lines


def run_ocr(image_path: str | Path) -> list[dict[str, Any]]:
    engine = get_engine()
    prediction = list(engine.predict(str(image_path)))
    return extract_lines(prediction)
