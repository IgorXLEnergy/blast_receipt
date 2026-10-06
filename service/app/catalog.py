from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SHARED_DIR = Path("/shared")
LOCAL_SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"


def _load_json(name: str) -> list[dict[str, Any]]:
    path = SHARED_DIR / name
    if not path.exists():
        path = LOCAL_SHARED_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def products() -> list[dict[str, Any]]:
    return _load_json("products.json")


@lru_cache(maxsize=1)
def retailers() -> list[dict[str, Any]]:
    return _load_json("retailers.json")
