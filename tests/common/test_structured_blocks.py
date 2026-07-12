from __future__ import annotations

import json

from ztare.common.structured_blocks import (
    balanced_object_after_marker,
    json_objects_after_marker,
)


def test_balanced_object_after_marker_handles_multiline_json_and_trailing_prose() -> None:
    text = """
before
MARKER: {
  "name": "alpha",
  "nested": {"brace": "literal } inside string"},
  "items": [1, 2]
}
after {not json for this marker}
"""

    blocks = balanced_object_after_marker(text, "MARKER")

    assert len(blocks) == 1
    assert json.loads(blocks[0])["nested"]["brace"] == "literal } inside string"


def test_json_objects_after_marker_extracts_multiple_marker_bound_objects() -> None:
    text = 'X: {"a": 1}\nignored {"z": 0}\nX: {"b": {"c": 2}}\n'

    assert json_objects_after_marker(text, "X") == [{"a": 1}, {"b": {"c": 2}}]


def test_json_objects_after_marker_accepts_colon_equals_or_whitespace_separator() -> None:
    text = (
        'RECEIPT: {"a": 1}\n'
        'RECEIPT = {"b": 2}\n'
        'RECEIPT {"c": 3}\n'
    )

    assert json_objects_after_marker(text, "RECEIPT") == [
        {"a": 1},
        {"b": 2},
        {"c": 3},
    ]
