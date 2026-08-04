from __future__ import annotations

import pytest

from ztare.worldmodel.observation_object_catalog import (
    compile_catalog_presentation,
    compile_grid_object_catalog,
    decode_grid_rle_rows,
)


def _grid():
    return (
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 0, 3, 3, 9, 12, 3, 3),
        (3, 1, 0, 3, 9, 12, 3, 3),
        (3, 0, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
    )


def test_catalog_separates_field_and_content_addressed_occurrences() -> None:
    catalog = compile_grid_object_catalog(
        _grid(),
        observation_sha256="observation-a",
    )

    assert catalog.field_values == (3,)
    assert len(catalog.objects) == 2
    marker = catalog.resolve_selector({
        "bbox": [1, 1, 3, 2],
        "palette": [0, 1],
        "cell_count": 4,
    })
    mover = catalog.resolve_selector({
        "bbox": [1, 4, 2, 5],
        "palette": [9, 12],
        "cell_count": 4,
    })
    assert marker.object_ref != mover.object_ref
    assert set(catalog.object_refs) == {
        marker.object_ref,
        mover.object_ref,
    }


def test_type_identity_survives_translation_while_occurrence_does_not() -> None:
    left = (
        (3, 3, 3, 3, 3, 3),
        (3, 9, 12, 3, 3, 3),
        (3, 9, 12, 3, 3, 3),
        (3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3),
    )
    right = (
        (3, 3, 3, 3, 3, 3),
        (3, 3, 3, 9, 12, 3),
        (3, 3, 3, 9, 12, 3),
        (3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3),
    )

    first = compile_grid_object_catalog(
        left,
        observation_sha256="observation-a",
    ).objects[0]
    second = compile_grid_object_catalog(
        right,
        observation_sha256="observation-b",
    ).objects[0]

    assert first.type_sha256 == second.type_sha256
    assert first.object_ref != second.object_ref


def test_selector_ambiguity_and_bad_rle_fail_closed() -> None:
    catalog = compile_grid_object_catalog(
        _grid(),
        observation_sha256="observation",
    )

    with pytest.raises(ValueError, match="resolve exactly once"):
        catalog.resolve_selector({"cell_count": 4})
    with pytest.raises(ValueError, match="invalid RLE token"):
        decode_grid_rle_rows(("3x2,bad",))


def test_catalog_presentation_round_trips_without_exposing_refs() -> None:
    catalog = compile_grid_object_catalog(
        _grid(),
        observation_sha256="observation",
    )
    presentation = compile_catalog_presentation(catalog)

    assert tuple(
        handle
        for handle, _object_ref in presentation.handle_to_object_ref
    ) == ("o00", "o01")
    for handle, object_ref in presentation.handle_to_object_ref:
        assert presentation.resolve_handle(handle) == object_ref
        assert presentation.handle_for_ref(object_ref) == handle
    prompt = presentation.prompt_receipt()
    assert prompt["presentation_sha256"] == presentation.sha256
    assert all("object_ref" not in row for row in prompt["objects"])
    assert [
        row["handle"] for row in prompt["objects"]
    ] == ["o00", "o01"]

    with pytest.raises(ValueError, match="unknown catalog-scoped"):
        presentation.resolve_handle("o99")
