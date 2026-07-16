from __future__ import annotations

import pytest

from ztare.common.equivariance import (
    CanonicalOrder,
    EquivarianceObservation,
    FiniteGroupPresentation,
    TransformationAction,
    UNDEFINED,
    authorize_quotient,
    certify_equivariance,
    certify_group_action,
    orbit_coordinates,
    stable_sha256,
    validate_group_presentation,
)


Z2 = FiniteGroupPresentation(
    group_id="z2_flip",
    elements=("e", "flip"),
    identity="e",
    multiplication=(
        ("e", "e", "e"),
        ("e", "flip", "flip"),
        ("flip", "e", "flip"),
        ("flip", "flip", "e"),
    ),
)


def _identity(value):
    return value


def _flip(value):
    return 1 - value


def _actions(*, domain=lambda _row: True):
    return {
        "e": TransformationAction(
            element_id="e",
            implementation_sha256=stable_sha256("identity-v1"),
            source_map=_identity,
            target_map=_identity,
            intervention_map=_identity,
            time_map=_identity,
            in_domain=domain,
            declared_domain="binary within-epoch states",
        ),
        "flip": TransformationAction(
            element_id="flip",
            implementation_sha256=stable_sha256("binary-flip-v1"),
            source_map=_flip,
            target_map=_flip,
            intervention_map=_identity,
            time_map=_identity,
            in_domain=domain,
            declared_domain="binary within-epoch states",
        ),
    }


def _bank():
    return [
        EquivarianceObservation(0, 0, 0, 1, "row:0"),
        EquivarianceObservation(1, 0, 1, 0, "row:1"),
        EquivarianceObservation(
            0,
            0,
            2,
            0,
            "row:boundary",
            transition_kind="epoch_boundary",
            classification_authority="environment_adapter",
        ),
    ]


def test_z2_presentation_action_and_carrier_authorize_orbit_quotient():
    assert validate_group_presentation(Z2) == ()
    actions = _actions()
    bank = _bank()
    carrier = lambda state, _action, _time: 1 - state
    group_certificate = certify_group_action(
        group=Z2,
        actions=actions,
        observations=bank,
        trusted_boundary_authorities=frozenset({"environment_adapter"}),
    )
    assert group_certificate.passed, group_certificate.failures
    flip_certificate = certify_equivariance(
        carrier=carrier,
        carrier_sha256=stable_sha256("toggle-carrier-v1"),
        action=actions["flip"],
        observations=bank,
        trusted_boundary_authorities=frozenset({"environment_adapter"}),
    )
    assert flip_certificate.passed, flip_certificate.counterexamples
    assert flip_certificate.tested == 2
    assert flip_certificate.boundary_excluded == 1
    authority = authorize_quotient(
        group=Z2,
        group_action=group_certificate,
        equivariance={"flip": flip_certificate},
    )
    coordinates = orbit_coordinates(
        0,
        group=Z2,
        actions=actions,
        authority=authority,
        canonical_order=CanonicalOrder(
            state_schema_id="binary-state-v1",
            canonicalizer_id="numeric-order-v1",
            implementation_sha256=stable_sha256("numeric-order-v1"),
            key=lambda value: value,
        ),
    )
    assert len(coordinates.orbit_member_sha256s) == 2
    assert coordinates.stabilizer == ("e",)
    assert len(coordinates.transporters_to_representative) == 1


def test_absolute_property_carrier_cannot_borrow_flip_identity():
    actions = _actions()
    bank = [
        EquivarianceObservation(0, 0, 0, 0, "row:0"),
        EquivarianceObservation(1, 0, 1, 0, "row:1"),
    ]
    certificate = certify_equivariance(
        carrier=lambda _state, _action, _time: 0,
        carrier_sha256=stable_sha256("absolute-zero-carrier"),
        action=actions["flip"],
        observations=bank,
    )
    assert not certificate.passed
    assert certificate.commute_mismatches == 2
    assert {
        row["kind"] for row in certificate.counterexamples
    } == {"commuting_square_mismatch"}


def test_partial_map_must_be_undefined_outside_declared_domain_only():
    bank = [
        EquivarianceObservation(0, 0, 0, 1, "inside"),
        EquivarianceObservation(2, 0, 1, 2, "outside"),
    ]
    outside_filtered = TransformationAction(
        element_id="flip",
        implementation_sha256=stable_sha256("partial-flip"),
        source_map=lambda value: 1 - value if value in (0, 1) else UNDEFINED,
        target_map=lambda value: 1 - value if value in (0, 1) else UNDEFINED,
        intervention_map=_identity,
        time_map=_identity,
        in_domain=lambda row: row.state in (0, 1),
        declared_domain="binary states only",
    )
    certificate = certify_equivariance(
        carrier=lambda state, _action, _time: 1 - state if state in (0, 1) else state,
        carrier_sha256=stable_sha256("partial-carrier"),
        action=outside_filtered,
        observations=bank,
        min_coverage_ratio=0.5,
    )
    assert certificate.passed
    assert certificate.tested == 1 and certificate.domain_excluded == 1

    falsely_total = TransformationAction(
        element_id="flip",
        implementation_sha256=stable_sha256("partial-flip"),
        source_map=outside_filtered.source_map,
        target_map=outside_filtered.target_map,
        intervention_map=_identity,
        time_map=_identity,
        declared_domain="all rows",
    )
    failed = certify_equivariance(
        carrier=lambda state, _action, _time: 1 - state if state in (0, 1) else state,
        carrier_sha256=stable_sha256("partial-carrier"),
        action=falsely_total,
        observations=bank,
    )
    assert not failed.passed
    assert any(
        row["kind"] == "undefined_inside_declared_domain"
        for row in failed.counterexamples
    )


def test_nonunital_constant_maps_fail_group_action_certificate():
    annihilate = lambda _value: 0
    actions = {
        element: TransformationAction(
            element_id=element,
            implementation_sha256=stable_sha256(f"annihilate:{element}"),
            source_map=annihilate,
            target_map=annihilate,
            intervention_map=annihilate,
            time_map=annihilate,
            declared_domain="all rows",
        )
        for element in Z2.elements
    }
    certificate = certify_group_action(
        group=Z2,
        actions=actions,
        observations=[EquivarianceObservation(1, 1, 1, 1, "nonzero-row")],
    )
    assert not certificate.passed
    assert any(
        row["kind"] == "identity_action_mismatch"
        for row in certificate.failures
    )


def test_local_partial_certificate_cannot_authorize_global_quotient():
    bank = _bank()[:2]
    actions = _actions(domain=lambda row: row.state == 0)
    group_certificate = certify_group_action(
        group=Z2, actions=actions, observations=bank
    )
    assert group_certificate.passed
    assert group_certificate.coverage_ratio == 0.5
    local = certify_equivariance(
        carrier=lambda state, _action, _time: 1 - state,
        carrier_sha256=stable_sha256("toggle-carrier-v1"),
        action=actions["flip"],
        observations=bank,
        min_coverage_ratio=0.5,
    )
    assert local.passed and local.coverage_ratio == 0.5
    with pytest.raises(ValueError, match="total group action"):
        authorize_quotient(
            group=Z2,
            group_action=group_certificate,
            equivariance={"flip": local},
        )


def test_untrusted_boundary_label_has_no_excusal_authority():
    action = _actions()["flip"]
    row = EquivarianceObservation(
        0,
        0,
        0,
        0,
        "candidate-labelled-boundary",
        transition_kind="epoch_boundary",
        classification_authority="candidate_carrier",
    )
    certificate = certify_equivariance(
        carrier=lambda state, _action, _time: 1 - state,
        carrier_sha256=stable_sha256("toggle-carrier-v1"),
        action=action,
        observations=[row],
        trusted_boundary_authorities=frozenset({"environment_adapter"}),
    )
    assert not certificate.passed
    assert certificate.boundary_excluded == 0
    assert certificate.base_law_mismatches == 1


def test_quotient_refuses_failed_equivariance_even_when_group_action_passes():
    actions = _actions()
    bank = [
        EquivarianceObservation(0, 0, 0, 0, "row:0"),
        EquivarianceObservation(1, 0, 1, 0, "row:1"),
    ]
    group_certificate = certify_group_action(
        group=Z2, actions=actions, observations=bank
    )
    bad = certify_equivariance(
        carrier=lambda _state, _action, _time: 0,
        carrier_sha256=stable_sha256("absolute-zero-carrier"),
        action=actions["flip"],
        observations=bank,
    )
    with pytest.raises(ValueError, match="failed equivariance"):
        authorize_quotient(
            group=Z2,
            group_action=group_certificate,
            equivariance={"flip": bad},
        )
