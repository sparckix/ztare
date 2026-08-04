from ztare.worldmodel.persistent_component_reservoir import (
    ReservoirWitness,
    discover_component_reservoir_coordinate,
    translation_component_counts,
)


def _frame(count, *, active=8, exhausted=3, row_shift=0, col_shift=0):
    grid = [[0 for _ in range(14)] for _ in range(10)]
    origins = [(2 + row_shift, 2 + col_shift + 4 * index) for index in range(3)]
    for index, (row, col) in enumerate(origins):
        value = active if index < count else exhausted
        for dy in range(2):
            for dx in range(2):
                grid[row + dy][col + dx] = value
    return tuple(tuple(row) for row in grid)


def test_discovers_palette_equivariant_translation_invariant_reservoir():
    witnesses = (
        ReservoirWitness(_frame(3), "safe", "trace#21"),
        ReservoirWitness(_frame(2), "safe", "trace#43"),
        ReservoirWitness(_frame(1), "terminal", "trace#65"),
    )
    background = tuple(
        _frame(count)
        for count in (3, 3, 2, 2, 1, 1)
    )
    coordinate = discover_component_reservoir_coordinate(
        witnesses,
        exceptional_outcome="terminal",
        background_observations=background,
    )

    assert coordinate is not None
    assert coordinate.witness_counts == (3, 2, 1)
    assert coordinate.project(_frame(2, row_shift=2)) == 2
    assert coordinate.predicts_exception(_frame(1))
    assert not coordinate.predicts_exception(_frame(2))

    renamed_witnesses = tuple(
        ReservoirWitness(
            tuple(tuple(value + 20 for value in row) for row in witness.observation),
            witness.outcome,
            witness.evidence_ref,
        )
        for witness in witnesses
    )
    renamed_background = tuple(
        tuple(tuple(value + 20 for value in row) for row in observation)
        for observation in background
    )
    renamed = discover_component_reservoir_coordinate(
        renamed_witnesses,
        exceptional_outcome="terminal",
        background_observations=renamed_background,
    )

    assert renamed is not None
    assert renamed.witness_counts == coordinate.witness_counts
    assert renamed.structural_sha256 == coordinate.structural_sha256


def test_rejects_text_as_a_grid_presentation():
    try:
        translation_component_counts("not-a-grid")
    except TypeError as exc:
        assert "two-dimensional" in str(exc)
    else:
        raise AssertionError("text must not be interpreted as a grid")


def test_interleaved_trajectories_keep_their_own_temporal_order():
    witnesses = (
        ReservoirWitness(
            _frame(1),
            "terminal",
            "first#2",
            sequence_id="first",
            sequence_index=2,
        ),
        ReservoirWitness(
            _frame(3),
            "safe",
            "second#0",
            sequence_id="second",
            sequence_index=0,
        ),
        ReservoirWitness(
            _frame(3),
            "safe",
            "first#0",
            sequence_id="first",
            sequence_index=0,
        ),
        ReservoirWitness(
            _frame(2),
            "safe",
            "second#1",
            sequence_id="second",
            sequence_index=1,
        ),
        ReservoirWitness(
            _frame(2),
            "safe",
            "first#1",
            sequence_id="first",
            sequence_index=1,
        ),
        ReservoirWitness(
            _frame(1),
            "terminal",
            "second#2",
            sequence_id="second",
            sequence_index=2,
        ),
    )
    coordinate = discover_component_reservoir_coordinate(
        witnesses,
        exceptional_outcome="terminal",
        background_observations=tuple(
            _frame(count) for count in (3, 2, 1, 3, 2, 1)
        ),
    )
    ordered = discover_component_reservoir_coordinate(
        (
            ReservoirWitness(_frame(3), "safe", "ordered#0"),
            ReservoirWitness(_frame(2), "safe", "ordered#1"),
            ReservoirWitness(_frame(1), "terminal", "ordered#2"),
        ),
        exceptional_outcome="terminal",
        background_observations=tuple(
            _frame(count) for count in (3, 3, 2, 2, 1, 1)
        ),
    )

    assert coordinate is not None
    assert ordered is not None
    assert coordinate.structural_sha256 == ordered.structural_sha256
    assert coordinate.project(_frame(3)) == 3
    assert coordinate.project(_frame(1)) == 1
