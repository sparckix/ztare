from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from ztare.common.causal_response_derivative import (
    compile_causal_response_derivative,
    compile_causal_response_program,
    compile_residual_proposal_transition,
    compile_residual_response_family,
    compile_response_reproduction_estimate,
    response_derivative_event_family_binding_receipt,
)
from ztare.common.instrumented_proposal_plasticity import (
    InstrumentedProposalOutcome,
)
from ztare.common.object_basin_response import (
    object_contract_from_receipt,
    object_proposal_from_receipt,
    object_response_family_from_receipt,
    object_transition_from_receipt,
)
from ztare.common.object_lineage_transport import (
    CausalObjectLineageTransport,
    causal_object_lineage_transport_from_receipt,
)
from ztare.common.object_linked_judgment import ObjectReferenceAuthority
from ztare.common.wake_sleep_credit_router import MemoryScope


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = (
    ROOT
    / "research_areas/pre_registrations"
    / "arc3_consumer_indexed_exception_frontier_20260723"
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _objects():
    manifest = _load(
        FIXTURES / "h96_causal_object_lineage/manifest.json"
    )
    family = object_response_family_from_receipt(
        manifest["source_response_family"]
    )
    response = next(
        row for row in family.responses
        if row.sha256 == manifest["source_response"]["sha256"]
    )
    contract = object_contract_from_receipt(
        manifest["source_contract"]
    )
    witnesses = []
    for name in (
        "pair_01_offer_causal_mechanics.json",
        "pair_02_offer_causal_mechanics.json",
    ):
        arm = _load(
            FIXTURES
            / "h95_response_transport_square/arms"
            / name
        )
        row = arm["probe"]["turns"][0]["instrumented_proposal"]
        witnesses.append((
            object_transition_from_receipt(row["transition"]),
            object_proposal_from_receipt(row["pre_proposal"]),
            object_proposal_from_receipt(row["post_proposal"]),
        ))
    program = compile_causal_response_program(
        family,
        response,
        contract,
        tuple(witnesses),
        evidence_refs=("fixture:h95",),
    )
    lineage = causal_object_lineage_transport_from_receipt(
        manifest["lineage_transport"]
    )
    scope = MemoryScope(**manifest["target_scope"])
    binding = response_derivative_event_family_binding_receipt(
        program,
        lineage,
    )
    derivative = compile_causal_response_derivative(
        program,
        lineage,
        target_scope=scope,
        target_intervention_revision_sha256=(
            manifest["target_contract"][
                "intervention_revision_sha256"
            ]
        ),
        source_forbidden_controlled_object_refs=(
            contract.forbidden_controlled_object_refs
        ),
        event_family_binding_receipt=binding,
        event_selection_phase="pre_outcome",
        evidence_refs=("fixture:h96-prefix",),
    )
    authority = ObjectReferenceAuthority(
        observation_sha256=lineage.target_observation_sha256,
        catalog_sha256=lineage.target_catalog_sha256,
        object_refs=tuple(
            row["object_ref"]
            for row in manifest["target_catalog"]["objects"]
        ),
    )
    return manifest, program, lineage, derivative, authority


def test_h95_program_derives_expected_h96_residual() -> None:
    _manifest, program, _lineage, derivative, _authority = _objects()

    assert program.status == "compiled"
    assert program.support_count == 2
    assert program.controlled_object_ref == (
        "object:28bb088c2e48d4142d75c7ac2b409841"
        "58e3ce353c2b7f8090b3b5ae62620a21"
    )
    assert program.ordered_waypoint_refs == (
        "object:d439addc7224e3e25a64da7fb371ea591"
        "702e6badbe718c0c785e7330301702a",
        "object:d4585d1fc35c3033cd74977e855fac711"
        "644aa3347227e5e48c0ce83c5a272d7",
    )
    assert derivative.status == "derived"
    assert len(derivative.discharges) == 1
    residual = derivative.residual_contract
    assert residual is not None
    assert residual.required_controlled_object_ref == (
        "object:0dd38c622efa2070f589dcff588f08ff"
        "977ecba6c66339a7ad389b66e703f910"
    )
    assert residual.pending_waypoint_refs == (
        "object:dae43c2313554cae80b2067609f97b9ba"
        "8ea89fbe6f8c0c027d0b3a0033af6be",
    )
    assert residual.discharged_waypoint_refs == (
        "object:4a1f362bcd28e0c40f519570cc7c8c006"
        "81171761d6ee69837246f984105b1f7",
    )


def test_h96_pair_reclassifies_under_preoutcome_residual() -> None:
    _manifest, _program, _lineage, derivative, authority = _objects()
    rows = {}
    for assignment, name in (
        ("offer", "pair_01_offer_causal_mechanics.json"),
        (
            "withhold",
            "pair_01_withhold_redundant_true_memory.json",
        ),
    ):
        arm = _load(
            FIXTURES / "h96_causal_object_lineage/arms" / name
        )
        row = arm["probe"]["turns"][0]["instrumented_proposal"]
        rows[assignment] = compile_residual_proposal_transition(
            trial_ref=f"h96:{assignment}",
            stratum_sha256="h96-construction-stratum",
            assignment=assignment,
            pre_proposal=object_proposal_from_receipt(
                row["pre_proposal"]
            ),
            post_proposal=object_proposal_from_receipt(
                row["post_proposal"]
            ),
            derivative=derivative,
            authority=authority,
        )

    assert rows["offer"].relation == "offered_supported_derivative"
    assert rows["offer"].supported_transport is True
    assert rows["withhold"].relation == "withheld_already_satisfied"
    assert rows["withhold"].supported_transport is False


def test_derivative_refuses_postoutcome_proxy_and_missing_coevent() -> None:
    manifest, program, lineage, _derivative, _authority = _objects()
    scope = MemoryScope(**manifest["target_scope"])
    binding = response_derivative_event_family_binding_receipt(
        program,
        lineage,
    )
    kwargs = {
        "target_scope": scope,
        "target_intervention_revision_sha256": (
            manifest["target_contract"][
                "intervention_revision_sha256"
            ]
        ),
        "source_forbidden_controlled_object_refs": (
            manifest["source_contract"][
                "forbidden_controlled_object_refs"
            ]
        ),
        "evidence_refs": ("fixture:negative",),
    }
    post = compile_causal_response_derivative(
        program,
        lineage,
        event_family_binding_receipt=binding,
        event_selection_phase="post_outcome",
        **kwargs,
    )
    proxy_binding = {
        **binding,
        "known_proxy_family_confuser": "outcome-matched endpoint",
    }
    proxy = compile_causal_response_derivative(
        program,
        lineage,
        event_family_binding_receipt=proxy_binding,
        event_selection_phase="pre_outcome",
        **kwargs,
    )
    program_roots = {
        program.controlled_object_ref,
        *program.ordered_waypoint_refs,
        *manifest["source_contract"][
            "forbidden_controlled_object_refs"
        ],
    }
    no_coevent_lineage = CausalObjectLineageTransport(
        source_observation_sha256=(
            lineage.source_observation_sha256
        ),
        source_catalog_sha256=lineage.source_catalog_sha256,
        target_observation_sha256=(
            lineage.target_observation_sha256
        ),
        target_catalog_sha256=lineage.target_catalog_sha256,
        required_source_object_refs=tuple(program_roots),
        traces=tuple(
            row for row in lineage.traces
            if row.source_object_ref in program_roots
        ),
        status="transportable",
        reason="test_projection_without_revision_coevent",
        evidence_refs=("fixture:negative-projection",),
    )
    no_coevent_binding = (
        response_derivative_event_family_binding_receipt(
            program,
            no_coevent_lineage,
        )
    )
    no_coevent = compile_causal_response_derivative(
        program,
        no_coevent_lineage,
        event_family_binding_receipt=no_coevent_binding,
        event_selection_phase="pre_outcome",
        **kwargs,
    )

    assert post.reason == "event_selection_not_pre_outcome"
    assert proxy.reason == "event_family_binding_refused"
    assert no_coevent.reason == "joint_discharge_coevent_missing"
    assert {post.status, proxy.status, no_coevent.status} == {"refused"}


def test_response_reproduction_boundary_is_mechanical() -> None:
    subcritical = compile_response_reproduction_estimate(
        response_schema_sha256="schema",
        parent_family_sha256s=("parent",),
        promoted_child_family_sha256s=(),
        false_edge_count=0,
        primitive_action_cost=40,
        evidence_refs=("h96",),
    )
    critical = compile_response_reproduction_estimate(
        response_schema_sha256="schema",
        parent_family_sha256s=("parent",),
        promoted_child_family_sha256s=("child",),
        false_edge_count=0,
        primitive_action_cost=80,
        evidence_refs=("h97",),
    )
    supercritical = compile_response_reproduction_estimate(
        response_schema_sha256="schema",
        parent_family_sha256s=("parent",),
        promoted_child_family_sha256s=("child-a", "child-b"),
        false_edge_count=0,
        primitive_action_cost=160,
        evidence_refs=("future-sibling-test",),
    )

    assert subcritical.response_reproduction_number == 0.0
    assert subcritical.regime == "subcritical"
    assert critical.response_reproduction_number == 1.0
    assert critical.regime == "critical"
    assert supercritical.response_reproduction_number == 2.0
    assert supercritical.regime == "supercritical"


def test_residual_settlements_promote_one_typed_child_family() -> None:
    _manifest, program, _lineage, derivative, authority = _objects()
    source = _load(
        FIXTURES
        / "h96_causal_object_lineage/arms"
        / "pair_01_offer_causal_mechanics.json"
    )
    row = source["probe"]["turns"][0]["instrumented_proposal"]
    pre = object_proposal_from_receipt(row["pre_proposal"])
    offered_post = object_proposal_from_receipt(row["post_proposal"])
    withheld_post = replace(
        pre,
        proposal_ref="fixture:withheld-post",
        predicted_consequence_ref="fixture:withheld-prediction",
        parent_proposal_sha256=pre.sha256,
        consumed_intervention_revision_sha256="",
    )
    outcomes = []
    for pair_index in (1, 2):
        offer = compile_residual_proposal_transition(
            trial_ref=f"fixture:{pair_index}:offer",
            stratum_sha256=f"fixture-stratum:{pair_index}",
            assignment="offer",
            pre_proposal=pre,
            post_proposal=offered_post,
            derivative=derivative,
            authority=authority,
        )
        withhold = compile_residual_proposal_transition(
            trial_ref=f"fixture:{pair_index}:withhold",
            stratum_sha256=f"fixture-stratum:{pair_index}",
            assignment="withhold",
            pre_proposal=pre,
            post_proposal=withheld_post,
            derivative=derivative,
            authority=authority,
        )
        outcomes.extend((
            InstrumentedProposalOutcome(
                transition=offer,
                external_outcome_ref=f"fixture:{pair_index}:offer",
                external_value=1.0,
                offer_cost=0.0,
                primitive_action_cost=20.0,
            ),
            InstrumentedProposalOutcome(
                transition=withhold,
                external_outcome_ref=f"fixture:{pair_index}:withhold",
                external_value=0.0,
                offer_cost=0.0,
                primitive_action_cost=20.0,
            ),
        ))

    child = compile_residual_response_family(
        tuple(outcomes),
        derivative=derivative,
        source_settlement_ref="fixture:h97",
        source_settlement_sha256="fixture-h97-settlement",
    )
    reproduction = compile_response_reproduction_estimate(
        response_schema_sha256=program.sha256,
        parent_family_sha256s=("parent-family",),
        promoted_child_family_sha256s=(child.sha256,),
        false_edge_count=0,
        primitive_action_cost=80.0,
        evidence_refs=("fixture:h97",),
    )

    assert child.promoted is True
    assert child.admissible_response_count == 1
    assert child.responses[0].offer_count == 2
    assert child.responses[0].withhold_count == 2
    assert child.responses[0].first_stage_transport_delta == 1.0
    assert reproduction.response_reproduction_number == 1.0
    assert reproduction.regime == "critical"
