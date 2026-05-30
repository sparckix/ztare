from projects.ns_millennium_hunt.scripts.selected_c7_geometry_sign_blind_no_sheath_witness import (
    build_witness,
)


def test_sign_blind_geometry_does_not_imply_strict_no_sheath() -> None:
    witness = build_witness(epsilon=0.1)
    assert witness.sign_blind_geometry_cannot_select_orientation is True
    assert "ofSelectedGeometry" in witness.killed_route
    for row in witness.rows:
        assert row.c7_geometry_fields_unchanged_under_sign_flip is True
        assert row.pressure_symbol_membership_unchanged is True
        assert row.core_positive_cone_mass == row.opposite_sheath_cone_mass
        assert row.strict_no_sheath_dominance_holds is False


def test_epsilon_zero_is_not_the_strict_target() -> None:
    witness = build_witness(epsilon=0.0)
    assert witness.sign_blind_geometry_cannot_select_orientation is False
    assert all(row.strict_no_sheath_dominance_holds for row in witness.rows)
