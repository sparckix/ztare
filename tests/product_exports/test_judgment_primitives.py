from __future__ import annotations

import json

from src.ztare.product_exports.judgment_primitives import (
    JUDGMENT_PRIMITIVES_V1,
    NON_PRIMITIVE_RUNTIME_CONCEPTS_V1,
    export_judgment_primitives_payload,
    render_typescript_module,
)


def test_judgment_primitive_keys_are_unique() -> None:
    keys = [p.key for p in JUDGMENT_PRIMITIVES_V1]
    assert len(keys) == len(set(keys))
    assert len(keys) == 6


def test_runtime_concepts_are_not_exported_as_primitives() -> None:
    primitive_keys = {p.key for p in JUDGMENT_PRIMITIVES_V1}
    runtime_keys = {c.key for c in NON_PRIMITIVE_RUNTIME_CONCEPTS_V1}
    assert "topological_pivot" not in primitive_keys
    assert primitive_keys.isdisjoint(runtime_keys)


def test_public_payload_does_not_leak_private_paths_or_seam_ids() -> None:
    payload = export_judgment_primitives_payload()
    blob = json.dumps(payload, sort_keys=True)
    forbidden_fragments = [
        "research_areas/private",
        "GP-",
        "seam:",
        ".md",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in blob


def test_typescript_render_contains_public_export_only() -> None:
    ts_blob = render_typescript_module()
    assert "JUDGMENT_PRIMITIVES_EXPORT" in ts_blob
    assert "topological_pivot" in ts_blob
    assert "research_areas/private" not in ts_blob
