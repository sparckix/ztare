from __future__ import annotations

from ztare.common.object_lineage_transport import (
    compile_causal_object_lineage_transport,
)
from ztare.worldmodel.observation_object_catalog import (
    compile_grid_object_catalog,
)


def _grid(
    *,
    revised: bool,
    marker: bool,
) -> tuple[tuple[int, ...], ...]:
    rows = [[3 for _x in range(12)] for _y in range(12)]
    glyph = (
        ((1, 3), (2, 3), (3, 1), (3, 2), (3, 3))
        if revised
        else ((1, 1), (2, 1), (3, 1), (3, 2), (3, 3))
    )
    for y, x in glyph:
        rows[y][x] = 9
    if marker:
        for y in (7, 8):
            for x in (8, 9):
                rows[y][x] = 1
    return tuple(tuple(row) for row in rows)


def _transition(source: str, target: str, action: int) -> dict:
    return {
        "source_observation_sha256": source,
        "successor_observation_sha256": target,
        "action": action,
    }


def test_lineage_preserves_revision_and_bracketed_occlusion() -> None:
    source = compile_grid_object_catalog(
        _grid(revised=False, marker=True),
        observation_sha256="source",
    )
    middle = compile_grid_object_catalog(
        _grid(revised=True, marker=False),
        observation_sha256="middle",
    )
    target = compile_grid_object_catalog(
        _grid(revised=True, marker=True),
        observation_sha256="target",
    )
    source_glyph = source.resolve_selector({
        "bbox": [1, 1, 3, 3],
        "palette": [9],
        "cell_count": 5,
    })
    source_marker = source.resolve_selector({
        "bbox": [7, 8, 8, 9],
        "palette": [1],
        "cell_count": 4,
    })
    target_glyph = target.resolve_selector({
        "bbox": [1, 1, 3, 3],
        "palette": [9],
        "cell_count": 5,
    })
    target_marker = target.resolve_selector({
        "bbox": [7, 8, 8, 9],
        "palette": [1],
        "cell_count": 4,
    })

    lineage = compile_causal_object_lineage_transport(
        (source, middle, target),
        (
            _transition("source", "middle", 0),
            _transition("middle", "target", 1),
        ),
        required_source_object_refs=(
            source_glyph.object_ref,
            source_marker.object_ref,
        ),
        evidence_refs=("synthetic-path",),
    )

    assert lineage.status == "transportable"
    assert lineage.appearance_revision_count == 1
    assert lineage.bracketed_occlusion_count == 1
    assert lineage.map_ref(source_glyph.object_ref) == (
        target_glyph.object_ref
    )
    assert lineage.map_ref(source_marker.object_ref) == (
        target_marker.object_ref
    )


def test_lineage_refuses_unbracketed_absence() -> None:
    source = compile_grid_object_catalog(
        _grid(revised=False, marker=True),
        observation_sha256="source",
    )
    target = compile_grid_object_catalog(
        _grid(revised=True, marker=False),
        observation_sha256="target",
    )
    source_marker = source.resolve_selector({
        "bbox": [7, 8, 8, 9],
        "palette": [1],
        "cell_count": 4,
    })

    lineage = compile_causal_object_lineage_transport(
        (source, target),
        (_transition("source", "target", 0),),
        required_source_object_refs=(source_marker.object_ref,),
        evidence_refs=("unbracketed-path",),
    )

    assert lineage.status == "refused"
    assert lineage.reason == "lineage_absence_is_not_uniquely_bracketed"
