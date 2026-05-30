from fractions import Fraction

from projects.ns_millennium_hunt.scripts.tracefree_measure_valuation_tomography import (
    FRAME,
    build_certificate,
    inverse_l1_constant,
)
from projects.ns_millennium_hunt.scripts.tracefree_tensor_frame_tomography import determinant


def test_measure_valuation_frame_is_invertible() -> None:
    assert determinant(FRAME) == Fraction(1)


def test_measure_valuation_inverse_l1_constant_is_two() -> None:
    assert inverse_l1_constant() == Fraction(2)


def test_measure_valuation_survives_final_cancellation() -> None:
    cert = build_certificate()
    packet = cert["same_window_cancellation_test"]
    assert packet["final_shadow_l1"] == "0"
    assert packet["final_samples_fail"] is True
    assert packet["bound_holds_presummed"] is True
    assert "same-source signed shadow measures" in cert["interpretation"]
