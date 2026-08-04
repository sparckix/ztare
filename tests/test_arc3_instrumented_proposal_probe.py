from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ztare.common.decision_use_gate import DecisionUseContract
from ztare.common.object_linked_judgment import (
    ObjectReferenceAuthority,
    ObjectRolePathContract,
)
from ztare.common.wake_sleep_credit_router import MemoryScope
from ztare.worldmodel.observation_object_catalog import (
    compile_catalog_presentation,
    compile_catalog_from_observation,
    compile_grid_object_catalog,
)


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/public/control/arc3_instrumented_proposal_probe.py"
    )
    spec = importlib.util.spec_from_file_location(
        "arc3_instrumented_proposal_probe_under_test",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _adapter():
    return {
        "schema": "ztare-regex-proposal-feature-adapter-v1",
        "text_fields": ["prediction", "plan_summary"],
        "rules": [
            {
                "feature_id": "precondition_first",
                "include_any_regex": [r"\bmarker\b"],
                "exclude_any_regex": [],
            },
            {
                "feature_id": "terminal_first",
                "include_any_regex": [r"\btarget\b"],
                "exclude_any_regex": [r"\bmarker\b"],
            },
        ],
    }


def _scope():
    return MemoryScope(
        task_sha256="task",
        controller_sha256="controller",
        context_sha256="observation",
        choice_set_sha256="choices",
        action_vocabulary_sha256="actions",
    )


class _Actor:
    def __init__(self, *, offered: bool):
        self.offered = offered
        self.queued = None
        self.calls = 0

    def propose(self, observation):
        self.calls += 1
        return {
            "schema": "proposal",
            "phase": "blind_pre_proposal",
            "session_id": "session",
            "session_tick_count": 1,
            "action": 0,
            "prediction": "move toward target",
            "plan_summary": "test target",
            "uncertainty": "gate",
            "observation_sha256": observation["sha256"],
        }

    def queue_recall_digest(self, digest, *, consumption_receipt=None):
        self.queued = (digest, consumption_receipt)

    def revise(self, observation, *, pre_proposal):
        self.calls += 1
        assert self.queued is not None
        if self.offered:
            prediction = "move toward marker"
            plan = "visit marker before target"
            action = 1
        else:
            prediction = "move toward target"
            plan = "test target"
            action = 0
        return {
            "schema": "decision",
            "phase": "post_proposal_commitment",
            "session_id": "session",
            "session_tick_count": 2,
            "action": action,
            "prediction": prediction,
            "plan_summary": plan,
            "uncertainty": "gate",
            "recall_injection": {
                "digest_sha256": "digest",
                "consumption_receipt_sha256": "consumption",
                "direct_injection_count": 1,
            },
            "extra_inference_tick_count": 1,
        }

    def decide(self, observation):
        raise AssertionError("not used in this test")


def test_feature_adapter_distinguishes_precondition_and_terminal() -> None:
    module = _load()

    assert module.extract_proposal_features(
        {
            "prediction": "move toward target",
            "plan_summary": "test upper target",
        },
        _adapter(),
    ) == ("terminal_first",)
    assert module.extract_proposal_features(
        {
            "prediction": "move toward marker",
            "plan_summary": "marker before target",
        },
        _adapter(),
    ) == ("precondition_first",)


def test_instrumented_thread_compiles_supported_target_transport() -> None:
    module = _load()
    scope = _scope()
    contract = DecisionUseContract(
        scope=scope,
        intervention_revision_sha256="target-intervention",
        required_features=("precondition_first",),
        forbidden_features=("terminal_first",),
        evidence_refs=("episode",),
    )
    thread = module.InstrumentedFirstDecisionThread(
        actor=_Actor(offered=True),
        assignment="offer",
        digest={"schema": "memory"},
        consumption_receipt={
            "status": "consumed",
            "sha256": "consumption",
            "observation_sha256": "observation",
        },
        target_contract=contract,
        controller_instance_sha256="instance",
        stratum_sha256="stratum",
        feature_adapter=_adapter(),
    )

    decision = thread.decide({
        "sha256": "observation",
        "action_count": 0,
    })

    assert decision["action"] == 1
    assert thread.transition is not None
    assert thread.transition.relation == "offered_supported_transport"
    assert thread.transition.supported_transport is True


def test_invalid_feature_regex_fails_before_classification() -> None:
    module = _load()
    adapter = _adapter()
    adapter["rules"][0]["include_any_regex"] = ["["]

    with pytest.raises(ValueError, match="invalid regex"):
        module.extract_proposal_features(
            {"prediction": "marker", "plan_summary": ""},
            adapter,
        )


class _ObjectActor:
    def __init__(self, *, mover_ref: str, marker_ref: str):
        self.mover_ref = mover_ref
        self.marker_ref = marker_ref
        self.queued = None
        self.calls = 0

    def propose(self, observation, *, object_catalog):
        self.calls += 1
        return {
            "schema": "proposal",
            "phase": "blind_pre_proposal",
            "session_id": "session",
            "session_tick_count": 1,
            "action": 0,
            "prediction": "probe the small object",
            "plan_summary": "move the small object",
            "uncertainty": "control identity",
            "observation_sha256": observation["sha256"],
            "catalog_sha256": object_catalog["catalog_sha256"],
            "controlled_object_ref": self.marker_ref,
            "ordered_waypoint_refs": [],
        }

    def queue_recall_digest(self, digest, *, consumption_receipt=None):
        self.queued = (digest, consumption_receipt)

    def revise(self, observation, *, pre_proposal, object_catalog):
        self.calls += 1
        assert self.queued is not None
        return {
            "schema": "decision",
            "phase": "post_proposal_commitment",
            "session_id": "session",
            "session_tick_count": 2,
            "action": 1,
            "prediction": "move the larger object to the small object",
            "plan_summary": "control mover then visit marker",
            "uncertainty": "action mapping",
            "catalog_sha256": object_catalog["catalog_sha256"],
            "controlled_object_ref": self.mover_ref,
            "ordered_waypoint_refs": [self.marker_ref],
            "recall_injection": {
                "digest_sha256": "digest",
                "consumption_receipt_sha256": "consumption",
                "direct_injection_count": 1,
            },
            "extra_inference_tick_count": 1,
        }

    def decide(self, observation):
        raise AssertionError("not used in this test")


def test_object_linked_thread_uses_catalog_refs_not_words() -> None:
    module = _load()
    grid = (
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 0, 3, 3, 9, 12, 3, 3),
        (3, 1, 0, 3, 9, 12, 3, 3),
        (3, 0, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
    )
    catalog = compile_grid_object_catalog(
        grid,
        observation_sha256="observation",
    )
    marker = catalog.resolve_selector({
        "bbox": [1, 1, 3, 2],
        "palette": [0, 1],
        "cell_count": 4,
    })
    mover = catalog.resolve_selector({
        "bbox": [1, 4, 2, 5],
        "palette": [9, 12],
        "cell_count": 4,
    })
    scope = _scope()
    authority = ObjectReferenceAuthority(
        observation_sha256="observation",
        catalog_sha256=catalog.sha256,
        object_refs=catalog.object_refs,
    )
    contract = ObjectRolePathContract(
        scope=scope,
        catalog_sha256=catalog.sha256,
        intervention_revision_sha256="target-intervention",
        required_controlled_object_ref=mover.object_ref,
        required_waypoint_refs=(marker.object_ref,),
        forbidden_controlled_object_refs=(marker.object_ref,),
        evidence_refs=("episode",),
    )
    thread = module.ObjectLinkedFirstDecisionThread(
        actor=_ObjectActor(
            mover_ref=mover.object_ref,
            marker_ref=marker.object_ref,
        ),
        assignment="offer",
        digest={"schema": "memory"},
        consumption_receipt={
            "status": "consumed",
            "sha256": "consumption",
            "observation_sha256": "observation",
        },
        target_contract=contract,
        object_catalog=catalog,
        object_authority=authority,
        controller_instance_sha256="instance",
        stratum_sha256="stratum",
    )

    decision = thread.decide({
        "sha256": "observation",
        "action_count": 0,
    })

    assert decision["action"] == 1
    assert thread.transition is not None
    assert thread.transition.relation == "offered_supported_transport"
    assert thread.transition.supported_transport is True


def test_h92_selectors_resolve_on_the_recorded_h91_observation() -> None:
    base = (
        Path(__file__).resolve().parents[1]
        / "research_areas/pre_registrations"
        / "arc3_consumer_indexed_exception_frontier_20260723"
    )
    arm = json.loads(
        (
            base
            / "h91_instrumented_proposal_plasticity/arms/"
            "pair_01_offer_causal_mechanics.json"
        ).read_text(encoding="utf-8")
    )
    spec = json.loads(
        (
            base / "h92_object_linked_judgment_quotient_spec.json"
        ).read_text(encoding="utf-8")
    )
    catalog = compile_catalog_from_observation(
        arm["probe"]["observations"][0]
    )
    contract = spec["object_role_contract"]

    controlled = catalog.resolve_selector(
        contract["controlled_object_selector"]
    )
    waypoint = catalog.resolve_selector(
        contract["required_waypoint_selectors"][0]
    )

    assert catalog.field_values == (3, 4, 5)
    assert len(catalog.objects) == 10
    assert controlled.bbox == (45, 34, 49, 38)
    assert waypoint.bbox == (31, 20, 33, 22)
    assert controlled.object_ref != waypoint.object_ref


class _HandleActor:
    def __init__(self, *, mover_handle: str, marker_handle: str):
        self.mover_handle = mover_handle
        self.marker_handle = marker_handle
        self.queued = None

    def propose(self, observation, *, object_catalog):
        return {
            "schema": "proposal",
            "phase": "blind_pre_proposal",
            "session_id": "session",
            "session_tick_count": 1,
            "action": 0,
            "prediction": "probe the small object",
            "plan_summary": "move the small object",
            "uncertainty": "control identity",
            "observation_sha256": observation["sha256"],
            "catalog_sha256": object_catalog["catalog_sha256"],
            "presentation_sha256": (
                object_catalog["presentation_sha256"]
            ),
            "controlled_object_handle": self.marker_handle,
            "ordered_waypoint_handles": [],
        }

    def queue_recall_digest(self, digest, *, consumption_receipt=None):
        self.queued = (digest, consumption_receipt)

    def revise(self, observation, *, pre_proposal, object_catalog):
        assert self.queued is not None
        return {
            "schema": "decision",
            "phase": "post_proposal_commitment",
            "session_id": "session",
            "session_tick_count": 2,
            "action": 1,
            "prediction": "move large object to small object",
            "plan_summary": "control mover then visit marker",
            "uncertainty": "action mapping",
            "catalog_sha256": object_catalog["catalog_sha256"],
            "presentation_sha256": (
                object_catalog["presentation_sha256"]
            ),
            "controlled_object_handle": self.mover_handle,
            "ordered_waypoint_handles": [self.marker_handle],
            "recall_injection": {
                "digest_sha256": "digest",
                "consumption_receipt_sha256": "consumption",
                "direct_injection_count": 1,
            },
            "extra_inference_tick_count": 1,
        }

    def decide(self, observation):
        raise AssertionError("not used")


def test_catalog_scoped_thread_checkpoints_then_resolves_handles() -> None:
    module = _load()
    grid = (
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 0, 3, 3, 9, 12, 3, 3),
        (3, 1, 0, 3, 9, 12, 3, 3),
        (3, 0, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
        (3, 3, 3, 3, 3, 3, 3, 3),
    )
    catalog = compile_grid_object_catalog(
        grid,
        observation_sha256="observation",
    )
    presentation = compile_catalog_presentation(catalog)
    marker = catalog.resolve_selector({
        "bbox": [1, 1, 3, 2],
        "palette": [0, 1],
        "cell_count": 4,
    })
    mover = catalog.resolve_selector({
        "bbox": [1, 4, 2, 5],
        "palette": [9, 12],
        "cell_count": 4,
    })
    scope = _scope()
    authority = ObjectReferenceAuthority(
        observation_sha256="observation",
        catalog_sha256=catalog.sha256,
        object_refs=catalog.object_refs,
    )
    contract = ObjectRolePathContract(
        scope=scope,
        catalog_sha256=catalog.sha256,
        intervention_revision_sha256="target-intervention",
        required_controlled_object_ref=mover.object_ref,
        required_waypoint_refs=(marker.object_ref,),
        forbidden_controlled_object_refs=(marker.object_ref,),
        evidence_refs=("episode",),
    )
    checkpoints = []
    admission_checkpoints = []
    actor = _HandleActor(
        mover_handle=presentation.handle_for_ref(mover.object_ref),
        marker_handle=presentation.handle_for_ref(marker.object_ref),
    )

    def select_before_delivery(pre):
        assert actor.queued is None
        return {
            "schema": "test-admission",
            "action": "offer",
            "proposal_sha256": pre.sha256,
        }

    thread = module.ObjectLinkedFirstDecisionThread(
        actor=actor,
        assignment="offer",
        digest={"schema": "memory"},
        consumption_receipt={
            "status": "consumed",
            "sha256": "consumption",
            "observation_sha256": "observation",
        },
        target_contract=contract,
        object_catalog=catalog,
        object_authority=authority,
        object_presentation=presentation,
        proposal_observer=lambda phase, row: checkpoints.append(
            (phase, dict(row))
        ),
        admission_selector=select_before_delivery,
        admission_observer=lambda row: admission_checkpoints.append(
            dict(row)
        ),
        controller_instance_sha256="instance",
        stratum_sha256="stratum",
    )

    decision = thread.decide({
        "sha256": "observation",
        "action_count": 0,
    })

    assert decision["action"] == 1
    assert [phase for phase, _row in checkpoints] == [
        "blind_pre_proposal",
        "post_proposal_commitment",
    ]
    assert checkpoints[0][1]["controlled_object_handle"] == (
        presentation.handle_for_ref(marker.object_ref)
    )
    assert len(admission_checkpoints) == 1
    assert admission_checkpoints[0]["proposal_sha256"] == (
        decision["instrumented_proposal"]["pre_proposal"]["sha256"]
    )
    assert decision["instrumented_proposal"][
        "admission_decision"
    ]["action"] == "offer"
    assert thread.transition is not None
    assert thread.transition.supported_transport is True
