from __future__ import annotations

import hashlib
import json

from ztare.leanmill.axiom_pack import (
    lint_axiom_pack_blueprint,
    screen_axiom_pack_blueprint,
)
from ztare.leanmill.axiom_pack_band import (
    BAND_CARRIER_SIZE,
    BAND_MAX_INTERPRETATIONS,
    build_band_heldout_manifest,
    build_band_preregistration,
    finite_band_pilot_design,
    rank_band_heldout_tasks,
)
from ztare.leanmill.axiom_yield import verify_shadow_task_manifest
from ztare.leanmill.contracts.axiom_pack_transport import AxiomPackTransportContract
from ztare.leanmill.finite_model import (
    SAT,
    FiniteModel,
    certify_joint_satisfiability,
    evaluate_axiom,
)
from ztare.leanmill.formal_verification_provider import generate_keypair


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_band_pilot_is_typed_deterministic_and_quarantined() -> None:
    first = finite_band_pilot_design()
    second = finite_band_pilot_design()

    assert first.to_json() == second.to_json()
    assert first.to_json()["status"] == "quarantined_design"
    assert first.to_json()["experiment_executed"] is False
    assert first.to_json()["benchmark_result"] is False
    assert first.to_json()["novelty_result"] is False
    manifest_requirement = first.to_json()["heldout_manifest_requirement"]
    assert manifest_requirement["required_before_candidate_generation"] is True
    assert manifest_requirement["signed_manifest_present"] is False
    retained = first.to_json()["retained_model_requirement"]
    assert retained["status"] == "required_not_run"
    assert retained["constraint_role"] == "stress_only_conjunction"
    assert retained["part_of_base_theory"] is False
    assert retained["part_of_candidate_pack"] is False
    assert [sort.name for sort in first.signature.sorts] == ["B"]
    assert [(op.name, op.arg_sorts, op.result_sort) for op in first.signature.operations] == [
        ("mul", ("B", "B"), "B")
    ]
    assert [axiom.name for axiom in first.base_axioms] == [
        "mul_assoc",
        "mul_idempotent",
    ]
    assert [axiom.name for axiom in first.candidate_axioms] == [
        "endpoint_repeat_delete",
        "interior_swap_same_endpoints",
        "opposite_endpoint_repeat_delete",
    ]
    assert len(first.blueprints) == 3
    for blueprint in first.blueprints:
        lint = lint_axiom_pack_blueprint(blueprint)
        assert lint["ok"] is True, lint
        assert len(blueprint.candidate_axiom_templates) == 1
        assert blueprint.cheap_filter_policy["semantic_min_carrier_size"] == 3
        assert blueprint.cheap_filter_policy["semantic_max_carrier_size"] == 3
        assert blueprint.cheap_filter_policy["semantic_max_interpretations"] == 100_000


def test_each_band_family_passes_the_shared_quarantined_screen() -> None:
    design = finite_band_pilot_design()
    for blueprint in design.blueprints:
        report = screen_axiom_pack_blueprint(blueprint)
        assert report["status"] == "screened_quarantined", blueprint.name
        assert report["promotion_ready"] is False


def test_band_proposer_brief_excludes_every_operator_only_surface() -> None:
    design = finite_band_pilot_design()
    brief = design.proposer_brief()
    serialized = json.dumps(brief, sort_keys=True, separators=(",", ":"))

    assert brief["purpose"] == "candidate_generation_only"
    assert brief["operator_only_surfaces_exposed"] is False
    assert brief["base_theory"]["digest"] == design.base_theory_digest
    assert brief["base_theory"]["signature"] == design.signature.to_json()
    assert brief["base_theory"]["axioms"] == [
        axiom.to_json() for axiom in design.base_axioms
    ]

    forbidden: set[str] = set()
    operator_axioms = (
        *design.candidate_axioms,
        *design.collapse_controls,
        *design.retained_model_constraints,
        *(task.formula for task in design.heldout_tasks),
    )
    for axiom in operator_axioms:
        forbidden.update(
            {
                axiom.name,
                axiom.content_hash,
                axiom.semantic_hash,
                json.dumps(axiom.to_json(), sort_keys=True, separators=(",", ":")),
                json.dumps(axiom.formula.to_json(), sort_keys=True, separators=(",", ":")),
            }
        )
    for task in design.heldout_tasks:
        forbidden.update({task.task_id, task.family, task.input_digest})
    for blueprint in design.blueprints:
        for template in blueprint.candidate_axiom_templates:
            forbidden.update(
                str(template.get(key) or "")
                for key in ("name", "family", "statement")
            )

    assert all(value and value not in serialized for value in forbidden)


def test_band_transport_prompt_does_not_seed_frozen_candidate_surfaces() -> None:
    design = finite_band_pilot_design()
    proposer_view = design.proposer_brief()
    encoded_view = json.dumps(
        proposer_view, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    transport = AxiomPackTransportContract(
        proposer_view_digest="sha256:" + hashlib.sha256(encoded_view).hexdigest(),
        source_catalog={
            source_ref: {
                "schema": "leanmill.axiom_pack_structural_conjecture.v1",
                "name": source_ref,
            }
            for source_ref in proposer_view["proposal_source_refs"]
        },
    )
    prompt = transport.render_prompt(proposer_view)

    def term_word(term: dict) -> str:
        if term["kind"] == "var":
            return str(term["name"])
        assert term["kind"] == "app"
        return "".join(term_word(arg) for arg in term["args"])

    forbidden_surfaces: set[str] = set()
    for candidate in design.candidate_axioms:
        body = candidate.formula.to_json()["body"]
        forbidden_surfaces.update(
            {candidate.name, term_word(body["left"]), term_word(body["right"])}
        )
    forbidden_surfaces.update(task.task_id for task in design.heldout_tasks)

    assert all(surface not in prompt for surface in forbidden_surfaces)


def test_band_pilot_requires_a_size_three_model_outside_collapse_controls() -> None:
    design = finite_band_pilot_design()
    assert design.retained_model_bounds.min_carrier_size == BAND_CARRIER_SIZE
    assert design.retained_model_bounds.max_carrier_size == BAND_CARRIER_SIZE
    assert design.retained_model_bounds.max_interpretations == BAND_MAX_INTERPRETATIONS
    for candidate in design.candidate_axioms:
        probe = design.retained_model_probe_axiom(candidate)
        assert probe.name not in {axiom.name for axiom in design.base_axioms}
        assert probe.name not in {axiom.name for axiom in design.candidate_axioms}
        receipt = certify_joint_satisfiability(
            design.signature,
            (probe,),
            design.retained_model_bounds,
            base_axioms=design.base_axioms,
        )
        assert receipt.status == SAT, candidate.name
        assert receipt.witness is not None
        model = FiniteModel.from_json(receipt.witness["model"])
        assert model.sort_size_map == {"B": 3}
        assert all(
            evaluate_axiom(design.signature, control, model) is False
            for control in design.collapse_controls
        )


def test_band_heldout_manifest_is_separate_frozen_and_signed() -> None:
    design = finite_band_pilot_design()
    private_key, public_key = generate_keypair()
    admissions = {
        task.task_id: _sha(f"admission:{task.task_id}")
        for task in design.heldout_tasks
    }
    manifest = build_band_heldout_manifest(
        design=design,
        admission_digests=admissions,
        private_key_pem=private_key,
        verifier_ref="test-band-manifest",
        manifest_evidence_ref=_sha("band-manifest-evidence"),
    )

    core = manifest["metadata"]["manifest"]
    assert core["frozen"] is True
    assert core["base_theory_digest"] == design.base_theory_digest
    assert "pack_digest" not in core
    assert {row["split"] for row in core["tasks"]} == {"eval"}
    assert len(design.heldout_tasks) == 9
    assert len({task.family for task in design.heldout_tasks}) == 8
    assert len({row["input_digest"] for row in core["tasks"]}) == len(
        design.heldout_tasks
    )
    candidate_semantics = {axiom.semantic_hash for axiom in design.candidate_axioms}
    heldout_semantics = {task.formula.semantic_hash for task in design.heldout_tasks}
    assert candidate_semantics.isdisjoint(heldout_semantics)
    assert verify_shadow_task_manifest(
        manifest,
        base_theory_digest=design.base_theory_digest,
        trusted_public_key_pem=public_key,
    ) == (True, [])


def test_band_preregistration_separates_signed_operator_packet_and_proposer_view() -> None:
    design = finite_band_pilot_design()
    private_key, public_key = generate_keypair()
    admissions = {
        task.task_id: _sha(f"admission:{task.task_id}")
        for task in design.heldout_tasks
    }
    prereg = build_band_preregistration(
        design=design,
        admission_digests=admissions,
        private_key_pem=private_key,
        verifier_ref="test-band-manifest",
        manifest_evidence_ref=_sha("band-manifest-evidence"),
    )
    assert prereg["schema"] == "leanmill.axiom_pack_band_preregistration.v1"
    assert prereg["experiment_executed"] is False
    assert prereg["task_count"] == 9
    assert prereg["task_family_count"] == 8
    assert prereg["manifest"]["metadata"]["manifest_digest"]
    assert prereg["proposer_view"]["operator_only_surfaces_exposed"] is False
    assert "heldout_tasks" not in prereg["proposer_view"]
    assert verify_shadow_task_manifest(
        prereg["manifest"],
        base_theory_digest=design.base_theory_digest,
        trusted_public_key_pem=public_key,
    ) == (True, [])


def test_band_task_ranking_reuses_information_yield_pricer() -> None:
    design = finite_band_pilot_design()
    committee = [{"id": 0}, {"id": 1}]
    report = rank_band_heldout_tasks(
        design=design,
        committee=committee,
        predict=lambda member, task: (
            member["id"] if "orientation" in task.task_id else task.task_id
        ),
        size_fn=lambda _member: 1,
        previously_observed_task_ids=(task.task_id for task in design.heldout_tasks),
    )

    assert report["canonical_engine"].endswith("price_experiment")
    assert {row["task_id"] for row in report["ranked_tasks"]} == {
        task.task_id for task in design.heldout_tasks
    }
