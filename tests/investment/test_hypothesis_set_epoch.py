import json
from datetime import datetime, timezone

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment.hypothesis_set_epoch import (
    HYPOTHESIS_SET_EPOCH_JOB_KIND,
    compile_hypothesis_set_evidence_request,
    compile_hypothesis_set_evidence_result,
    compile_hypothesis_set_epoch_request,
    compile_hypothesis_set_epoch_result,
    enqueue_hypothesis_set_epoch_request,
    validate_hypothesis_set_evidence_request,
    validate_hypothesis_set_evidence_result,
    validate_hypothesis_set_epoch_result,
)
from ztare.investment.learning_scheduler import compile_learning_schedule
from ztare.investment.prospective_response_matrix import (
    RESPONSE_ALPHABET,
    SCHEMA,
    SETTLEMENT_SCHEMA,
    compile_prospective_response_continuation,
    compile_prospective_response_matrix,
    settle_prospective_response_matrix,
)
from ztare.leanmill import work_queue


SOURCE_REF = "https://www.sec.gov/Archives/filing"


def _matrix(frontier, hypotheses, *, at, successor=None):
    allowed_refs = sorted({
        ref for row in hypotheses for ref in row.get("source_refs") or ()
    })
    responses = [{
        "hypothesis_id": row["hypothesis_id"], "program_id": "earnings",
        "predicted_response": "supports_thesis",
        "predicted_distribution": {
            "supports_thesis": 1.0, "supports_rival": 0.0,
            "mixed": 0.0, "unresolved": 0.0,
        },
        "rationale": "Frozen prediction.", "rationale_source_refs": allowed_refs[:1],
    } for row in hypotheses]
    matrix = compile_prospective_response_matrix(
        frontier, candidate_leaf_sha256="a" * 64,
        evidence_cutoff=at, predicted_at=at, hypotheses=hypotheses,
        responses=responses, allowed_source_refs=allowed_refs,
    )
    if successor is None:
        return matrix
    body = dict(matrix)
    body.pop("matrix_sha256")
    body.update({
        "hypothesis_set_epoch_result_sha256": successor["result_sha256"],
        "epoch_depth": successor["epoch_depth"],
    })
    return {**body, "matrix_sha256": stable_sha256(body)}


def _settle(matrix, response="mixed", at="2026-08-23T00:00:00Z"):
    return settle_prospective_response_matrix(
        matrix, program_id="earnings", observed_response=response,
        observed_at=at, evidence_refs=[SOURCE_REF],
    )


def test_skeletal_matrix_cannot_fabricate_zero_mass_refutation():
    hypotheses = [
        {"hypothesis_id": kind, "kind": kind, "mechanism_sha256": char * 64}
        for kind, char in (("thesis", "1"), ("rival", "2"), ("null", "3"))
    ]
    matrix_body = {
        "schema": SCHEMA, "candidate_leaf_sha256": "a" * 64,
        "committee_epoch_id": "b" * 64, "question_frontier_sha256": "c" * 64,
        "structure_belief_sha256": "d" * 64, "hypotheses": hypotheses,
    }
    matrix = {**matrix_body, "matrix_sha256": stable_sha256(matrix_body)}
    observation = {
        "predictive_evidence_mass": 0.0, "evidence_refs": [SOURCE_REF],
        "question_id": "earnings", "observed_outcome": "mixed",
        "observed_at": "2026-08-23T00:00:00Z",
    }
    update = {
        "belief_sha256": "e" * 64, "parent_belief_sha256": "d" * 64,
        "status": "committee_refuted", "observation_history": [observation],
    }
    settlement_body = {
        "schema": SETTLEMENT_SCHEMA, "matrix_sha256": matrix["matrix_sha256"],
        "program_id": "earnings", "observed_response": "mixed",
        "observed_at": "2026-08-23T00:00:00Z", "evidence_refs": [SOURCE_REF],
        "posterior_cell_size": 3, "status": "committee_refuted",
        "structure_belief_update_receipt": update,
    }
    settlement = {
        **settlement_body, "settlement_sha256": stable_sha256(settlement_body),
    }
    with pytest.raises(ValueError):
        compile_hypothesis_set_epoch_request(matrix, settlement, entity_id="ABC")


def test_zero_mass_committee_refutation_queues_one_immutable_successor(tmp_path):
    frontier_body = {
        "schema": "jaggedthoughts-research-question-frontier-v1",
        "frontier_programs": [{
            "program_id": "earnings", "atom_ids": ["margin", "revenue"],
        }],
    }
    frontier = {
        **frontier_body,
        "question_frontier_sha256": stable_sha256(frontier_body),
    }
    hypotheses = [
        {
            "hypothesis_id": kind, "kind": kind,
            "mechanism": f"parent {kind} mechanism", "source_refs": [SOURCE_REF],
        }
        for kind in ("thesis", "rival", "null")
    ]
    matrix = _matrix(frontier, hypotheses, at="2026-08-22T00:00:00Z")
    settlement = _settle(matrix)
    incomplete_body = dict(matrix)
    incomplete_body.pop("matrix_sha256")
    incomplete_body.pop("responses")
    incomplete = {
        **incomplete_body, "matrix_sha256": stable_sha256(incomplete_body),
    }
    with pytest.raises(ValueError, match="complete v2"):
        compile_hypothesis_set_epoch_request(incomplete, settlement, entity_id="ABC")
    forged_body = dict(settlement)
    forged_body.pop("settlement_sha256")
    forged_body["realized_information_bits"] = 1.0
    forged = {**forged_body, "settlement_sha256": stable_sha256(forged_body)}
    with pytest.raises(ValueError, match="deterministic replay"):
        compile_hypothesis_set_epoch_request(matrix, forged, entity_id="ABC")
    matrix_path = tmp_path / "matrix.json"
    settlement_path = tmp_path / "settlement.json"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    settlement_path.write_text(json.dumps(settlement), encoding="utf-8")

    first = enqueue_hypothesis_set_epoch_request(
        tmp_path, matrix=matrix, settlement=settlement, entity_id="abc",
        matrix_path="matrix.json", settlement_path="settlement.json",
        question_frontier=frontier,
    )
    second = enqueue_hypothesis_set_epoch_request(
        tmp_path, matrix=matrix, settlement=settlement, entity_id="abc",
        matrix_path="matrix.json", settlement_path="settlement.json",
        question_frontier=frontier,
    )
    request = json.loads((tmp_path / first["request_path"]).read_text(encoding="utf-8"))
    connection = work_queue.connect(str(tmp_path / "state" / "research_jobs.sqlite3"))
    try:
        jobs = [
            row for row in work_queue.list_items(connection)
            if row["kind"] == HYPOTHESIS_SET_EPOCH_JOB_KIND
        ]
    finally:
        connection.close()
    assert first["work_id"] == second["work_id"] and len(jobs) == 1
    assert request["trigger_witness"]["evidence_refs"] == [SOURCE_REF]
    assert request["question_frontier"] == frontier
    assert request["successor_contract"]["parent_mutation_allowed"] is False
    proposal = {
        "schema": "jaggedthoughts-hypothesis-set-epoch-proposal-v1",
        "request_sha256": request["request_sha256"],
        "hypotheses": [
            {
                "hypothesis_id": f"successor-{kind}", "kind": kind,
                "mechanism": f"new {kind} mechanism {index}",
                "falsifier": f"observe outcome {index}",
                "source_refs": [f"https://www.sec.gov/Archives/example-{index}"],
            }
            for index, kind in enumerate(("thesis", "rival", "null"), 1)
        ],
        "expansion_rationale": "The observed response was outside the parent support.",
    }
    provenance_body = {
        "schema": "jaggedthoughts-subscription-result-provenance-v1",
        "result_path": "runs/000.result.json",
        "call_receipt_path": "runs/000.call.json",
        "dispatch_receipt_path": "runs/000.dispatch.json",
        "result_sha256": "4" * 64, "call_receipt_sha256": "5" * 64,
        "dispatch_receipt_sha256": "6" * 64,
        "accepted_at": "2026-08-24T00:00:00Z",
    }
    duplicate_mechanisms = {
        **proposal,
        "hypotheses": [
            {**row, "mechanism": "same mechanism"}
            for row in proposal["hypotheses"]
        ],
    }
    with pytest.raises(ValueError, match="mechanisms must be distinct"):
        compile_hypothesis_set_epoch_result(
            request, matrix, settlement, duplicate_mechanisms,
            accepted_at="2026-08-24T00:00:00Z",
            provider_result_provenance={
                **provenance_body,
                "provenance_sha256": stable_sha256(provenance_body),
            },
        )
    successor = compile_hypothesis_set_epoch_result(
        request, matrix, settlement, proposal,
        accepted_at="2026-08-24T00:00:00Z",
        provider_result_provenance={
            **provenance_body, "provenance_sha256": stable_sha256(provenance_body),
        },
    )
    assert validate_hypothesis_set_epoch_result(successor) == successor
    assert successor["parent_mutated"] is False
    assert successor["next_transition"] == "freeze_successor_response_matrix"
    assert successor["paper_policy_authority"] is False
    assert successor["capital_authority"] is False

    successor_matrix = _matrix(
        frontier, successor["hypotheses"], at="2026-08-24T00:00:00Z",
        successor=successor,
    )
    evidence_request = compile_hypothesis_set_evidence_request(
        successor_matrix, frontier, successor,
        matrix_path="successor-matrix.json", successor_path="successor.json",
    )
    assert validate_hypothesis_set_evidence_request(evidence_request) == evidence_request
    assert evidence_request["question_frontier"] == frontier
    assert evidence_request["atom_ids"] == ["margin", "revenue"]
    next_settlement = _settle(successor_matrix, at="2026-08-25T00:00:00Z")
    with pytest.raises(ValueError, match="differs from matrix lineage"):
        compile_hypothesis_set_epoch_request(
            successor_matrix, next_settlement, entity_id="ABC",
            question_frontier=frontier, epoch_depth=1,
        )
    next_request = compile_hypothesis_set_epoch_request(
        successor_matrix, next_settlement, entity_id="ABC",
        question_frontier=frontier,
    )
    assert next_request["epoch_depth"] == 2
    assert next_request["parent_hypothesis_set_epoch_result_sha256"] == successor[
        "result_sha256"
    ]
    evidence_proposal = {
        "schema": "jaggedthoughts-hypothesis-set-evidence-proposal-v1",
        "request_sha256": evidence_request["request_sha256"],
        "atom_results": [
            {
                "atom_id": "margin", "status": "supports_thesis",
                "finding": "Margins expanded.",
                "evidence_refs": ["https://www.sec.gov/Archives/margin"],
            },
            {
                "atom_id": "revenue", "status": "supports_rival",
                "finding": "Revenue slowed.",
                "evidence_refs": ["https://www.sec.gov/Archives/revenue"],
            },
        ],
    }
    evidence_result = compile_hypothesis_set_evidence_result(
        evidence_request, evidence_proposal, accepted_at="2026-08-25T00:00:00Z",
        provider_result_provenance={
            **provenance_body, "provenance_sha256": stable_sha256(provenance_body),
        },
    )
    assert validate_hypothesis_set_evidence_result(evidence_result) == evidence_result
    assert evidence_result["observed_response"] == "mixed"
    assert evidence_result["successor_result_sha256"] == successor["result_sha256"]
    assert evidence_result["paper_policy_authority"] is False
    assert evidence_result["capital_authority"] is False
    with pytest.raises(ValueError, match="not atom-complete"):
        compile_hypothesis_set_evidence_result(
            evidence_request,
            {**evidence_proposal, "atom_results": evidence_proposal["atom_results"][:1]},
            accepted_at="2026-08-25T00:00:00Z",
            provider_result_provenance={
                **provenance_body, "provenance_sha256": stable_sha256(provenance_body),
            },
        )
    schedule = compile_learning_schedule(
        jobs, {}, generated_at=datetime.fromtimestamp(
            int(jobs[0]["created_at"]) + 1, tz=timezone.utc,
        ).isoformat(),
    )
    assert schedule["next_action"]["work_id"] == first["work_id"]

    inadequate = _settle(matrix, response="supports_thesis")
    with pytest.raises(ValueError, match="committee-refuted"):
        compile_hypothesis_set_epoch_request(matrix, inadequate, entity_id="ABC")
    with pytest.raises(ValueError, match="frontier identity"):
        compile_hypothesis_set_epoch_request(
            matrix, settlement, entity_id="ABC",
            question_frontier={**frontier, "frontier_programs": []},
        )


def test_nonrefuting_committee_runs_the_remaining_question():
    frontier_body = {
        "schema": "jaggedthoughts-research-question-frontier-v1",
        "frontier_programs": [
            {"program_id": key, "atom_ids": [key], "estimated_source_calls": 1}
            for key in ("first", "second")
        ],
    }
    frontier = {**frontier_body, "question_frontier_sha256": stable_sha256(frontier_body)}
    hypotheses = [
        {"hypothesis_id": kind, "kind": kind, "mechanism": kind,
         "source_refs": [SOURCE_REF]}
        for kind in ("thesis", "rival", "null")
    ]
    responses = []
    for program_id in ("first", "second"):
        for hypothesis_id, predicted in (
            ("thesis", "supports_thesis"), ("rival", "supports_rival"),
            ("null", "unresolved"),
        ):
            distribution = {key: 0.05 for key in RESPONSE_ALPHABET}
            distribution[predicted] = 0.85
            distribution["mixed"] = 0.0
            distribution[predicted] += 0.05
            responses.append({
                "hypothesis_id": hypothesis_id, "program_id": program_id,
                "predicted_response": predicted, "predicted_distribution": distribution,
                "rationale": "frozen", "rationale_source_refs": [SOURCE_REF],
            })
    matrix = compile_prospective_response_matrix(
        frontier, candidate_leaf_sha256="a" * 64,
        evidence_cutoff="2026-08-20T00:00:00Z",
        predicted_at="2026-08-21T00:00:00Z", hypotheses=hypotheses,
        responses=responses, allowed_source_refs=[SOURCE_REF],
    )
    first = settle_prospective_response_matrix(
        matrix, program_id=matrix["selected_program_id"],
        observed_response="supports_thesis", observed_at="2026-08-22T00:00:00Z",
        evidence_refs=[SOURCE_REF],
    )
    continuation = compile_prospective_response_continuation(matrix, [first])
    second = settle_prospective_response_matrix(
        matrix, program_id=continuation["next_program_id"],
        observed_response="supports_thesis", observed_at="2026-08-23T00:00:00Z",
        evidence_refs=[SOURCE_REF], prior_settlements=[first],
    )
    assert second["prior_settlement_sha256s"] == [first["settlement_sha256"]]
    assert compile_prospective_response_continuation(
        matrix, [first, second],
    )["frontier_exhaustion_reason"] == "all_programs_observed"
    refuting = settle_prospective_response_matrix(
        matrix, program_id=continuation["next_program_id"],
        observed_response="mixed", observed_at="2026-08-23T00:00:00Z",
        evidence_refs=[SOURCE_REF], prior_settlements=[first],
    )
    request = compile_hypothesis_set_epoch_request(
        matrix, refuting, entity_id="ABC", prior_settlements=[first],
        prior_settlement_paths=["first.json"],
    )
    assert request["prior_settlement_sha256s"] == [first["settlement_sha256"]]
