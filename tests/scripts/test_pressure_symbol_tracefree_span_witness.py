from fractions import Fraction

from projects.ns_millennium_hunt.scripts.pressure_symbol_tracefree_span_witness import (
    build_witness,
    q_axis,
)


def test_pressure_axial_symbols_span_diagonal_tracefree_packet() -> None:
    witness = build_witness(max_prefix=8)

    assert witness["unit_identity"]["passes"] is True
    assert witness["unit_identity"]["coords"] == {
        "a": "1",
        "d": "0",
        "b": "0",
        "c": "0",
        "e": "0",
    }
    assert witness["unit_identity"]["matrix"] == [
        ["1", "0", "0"],
        ["0", "0", "0"],
        ["0", "0", "-1"],
    ]

    for row in witness["rows"]:
        assert row["matches_diagonal_packet"] is True
        assert row["pressure_symbol_representation"] == "alpha * (Q(e1) - Q(e3))"
        assert row["five_frame_event_pay"] == str(2 * abs(Fraction(row["alpha"])))


def test_q_axis_rejects_unknown_axis() -> None:
    try:
        q_axis("bad")
    except ValueError as exc:
        assert "unknown axis" in str(exc)
    else:
        raise AssertionError("expected axis failure")


def test_pressure_symbol_witness_rejects_bad_prefix() -> None:
    try:
        build_witness(max_prefix=0)
    except ValueError as exc:
        assert "max_prefix" in str(exc)
    else:
        raise AssertionError("expected max_prefix failure")
