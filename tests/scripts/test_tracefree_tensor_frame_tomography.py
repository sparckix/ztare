from fractions import Fraction

from projects.ns_millennium_hunt.scripts.tracefree_tensor_frame_tomography import (
    MEASUREMENT_MATRIX,
    build_certificate,
    determinant,
    l1_reconstruction_constant,
)


def test_five_direction_tracefree_frame_is_invertible() -> None:
    assert determinant(MEASUREMENT_MATRIX) == Fraction(1)


def test_l1_reconstruction_constant_is_two() -> None:
    assert l1_reconstruction_constant() == Fraction(2)


def test_certificate_names_remaining_ns_fields() -> None:
    cert = build_certificate()
    assert cert["invertible"] is True
    assert cert["l1_reconstruction_constant"] == "2"
    assert "single-scalar cancellation" in cert["scientific_readout"]
    assert "owner_fibers_bounded_by_invoice_fibers" in cert["required_ns_fields_after_algebra"]
