"""Tolerant JSON extraction for LLM outputs (handles code fences / surrounding prose)."""
from __future__ import annotations

import json
from typing import Any


def loads_tolerant(text: str) -> dict[str, Any]:
    """Best-effort parse of a JSON object from an LLM response. Returns {} on failure."""
    if not text:
        return {}
    t = text.strip()
    if t.startswith("```"):
        # strip a leading ```json / ``` fence and its closer
        t = t.lstrip("`")
        if t[:4].lower() == "json":
            t = t[4:]
        if "```" in t:
            t = t.split("```", 1)[0]
        t = t.strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start : end + 1]
    try:
        obj = json.loads(t)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}
