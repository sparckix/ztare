from fractions import Fraction

from projects.ns_millennium_hunt.scripts.psd_preimage_of_diagonal_five_frame_packet import (
    build_witness,
)


def test_psd_preimage_has_diagonal_packet_as_tracefree_part() -> None:
    witness = build_witness(max_prefix=8)

    for row in witness["rows"]:
        assert row["psd_nonnegative_eigenvalues"] is True
        assert row["tracefree_part_matches_packet"] is True
        assert row["tracefree_diag"] == row["target_diag"]
        assert Fraction(row["trace"]) == Fraction(3, 2) * Fraction(row["five_frame_event_pay"])

    assert Fraction(witness["final_trace_prefix"]) == Fraction(3, 2) * Fraction(
        witness["final_five_frame_event_prefix"]
    )


def test_psd_preimage_rejects_bad_prefix() -> None:
    try:
        build_witness(max_prefix=0)
    except ValueError as exc:
        assert "max_prefix" in str(exc)
    else:
        raise AssertionError("expected max_prefix failure")
