from __future__ import annotations

import json
from typing import Any


def balanced_object_after_marker(text: str, marker: str) -> list[str]:
    """Return JSON-object substrings following a literal marker.

    This is for typed LLM/control surfaces such as
    ``MARKER: { ... }`` where the JSON object may be pretty-printed and
    followed by prose. It is deliberately marker-bound; callers still own
    schema validation.
    """
    out: list[str] = []
    source = text or ""
    start = 0
    while True:
        idx = source.find(marker, start)
        if idx < 0:
            return out
        span = json_object_span(source, _after_marker_prefix(source, idx + len(marker)))
        if span is None:
            start = idx + len(marker)
            continue
        out.append(source[span[0] : span[1]])
        start = span[1]


def json_objects_after_marker(text: str, marker: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in balanced_object_after_marker(text, marker):
        payload = json.loads(raw)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _after_marker_prefix(text: str, start: int) -> int:
    """Skip the conventional marker separator before a JSON object.

    Typed control surfaces in this repo use both ``MARKER: {...}`` and
    ``MARKER = {...}``. The marker finder remains literal; this helper only
    accepts a small separator grammar before the balanced JSON object.
    """
    i = start
    while i < len(text) and text[i].isspace():
        i += 1
    if i < len(text) and text[i] in (":", "="):
        i += 1
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def json_object_span(text: str, start: int = 0) -> tuple[int, int] | None:
    i = start
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text) or text[i] != "{":
        return None
    try:
        obj, end = json.JSONDecoder(strict=False).raw_decode(text, idx=i)
        if isinstance(obj, dict):
            return i, end
    except json.JSONDecodeError:
        pass

    object_depth = 0
    array_depth = 0
    in_string = False
    quote = ""
    escape = False
    for pos in range(i, len(text)):
        ch = text[pos]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            continue
        if ch in ("'", '"'):
            in_string = True
            quote = ch
        elif ch == "{":
            object_depth += 1
        elif ch == "}":
            object_depth -= 1
            if object_depth == 0 and array_depth == 0:
                return i, pos + 1
        elif ch == "[":
            array_depth += 1
        elif ch == "]":
            array_depth -= 1
    return None
