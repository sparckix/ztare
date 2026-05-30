from projects.ns_millennium_hunt.scripts.diagonal_packet_no_sheath_dominance_audit import (
    build_audit,
)


def test_diagonal_packet_violates_strict_no_sheath_dominance() -> None:
    audit = build_audit(max_prefix=8, epsilon=0.25)

    assert audit["all_rows_violate_strict_dominance"] is True
    for row in audit["rows"]:
        assert row["opposite_sheath_cone_mass"] == row["core_positive_cone_mass"]
        assert row["strict_no_sheath_dominance_holds"] is False
        assert row["dominance_defect"] > 0


def test_no_sheath_audit_rejects_bad_inputs() -> None:
    for kwargs, message in [
        ({"max_prefix": 0}, "max_prefix"),
        ({"epsilon": 0.0}, "epsilon"),
        ({"epsilon": 1.0}, "epsilon"),
    ]:
        try:
            build_audit(**kwargs)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError(f"expected failure for {kwargs}")
