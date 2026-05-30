from projects.ns_millennium_hunt.scripts.five_frame_nonadaptive_currency_mismatch_witness import (
    build_witness,
)


def test_nonadaptive_route_tail_budget_does_not_pay_five_frame_event_pay() -> None:
    witness = build_witness(max_prefix=64, owner_budget=2.0)

    assert witness["route_tail_prefix_stays_within_budget"] is True
    assert witness["five_frame_prefix_exceeds_budget"] is True
    assert witness["first_route_exceeds_budget"] is None
    assert witness["first_five_frame_exceeds_budget"] is not None
    assert (
        witness["final_five_frame_prefix"]
        > witness["final_route_tail_prefix"]
    )



def test_witness_events_satisfy_pointwise_five_frame_tomography() -> None:
    witness = build_witness(max_prefix=8, owner_budget=2.0)

    for row in witness["rows"]:
        event = row["tensor_event"]
        coeffs = event["tensor_coefficients"]
        recovered = event["recovered_coefficients"]
        assert event["pointwise_tomography_passes"] is True
        assert recovered == coeffs
        assert abs(event["tracefree_total_variation_proxy"] - row["five_frame_event_pay"]) < 1e-12

    assert witness["tomography_side_conditions"]["sample_stream_is_pointwise_recoverable"] is True


def test_witness_rejects_bad_inputs() -> None:
    try:
        build_witness(max_prefix=0)
    except ValueError as exc:
        assert "max_prefix" in str(exc)
    else:
        raise AssertionError("expected max_prefix failure")

    try:
        build_witness(owner_budget=-1.0)
    except ValueError as exc:
        assert "owner_budget" in str(exc)
    else:
        raise AssertionError("expected owner_budget failure")
