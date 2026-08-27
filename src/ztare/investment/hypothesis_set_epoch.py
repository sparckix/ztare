"""Open an immutable hypothesis-set successor request after committee refutation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .contracts import canonical_timestamp, require_text, timestamp_key
from .prospective_response_matrix import (
    SCHEMA as RESPONSE_MATRIX_SCHEMA,
    SETTLEMENT_SCHEMA as RESPONSE_SETTLEMENT_SCHEMA,
    compile_prospective_response_continuation,
    settle_prospective_response_matrix,
    validate_prospective_response_matrix,
    validate_prospective_response_settlement,
)


HYPOTHESIS_SET_EPOCH_REQUEST_SCHEMA = "jaggedthoughts-hypothesis-set-epoch-request-v1"
HYPOTHESIS_SET_EPOCH_JOB_SCHEMA = "jaggedthoughts-hypothesis-set-epoch-job-v1"
HYPOTHESIS_SET_EPOCH_RESULT_SCHEMA = "jaggedthoughts-hypothesis-set-epoch-result-v1"
HYPOTHESIS_SET_EPOCH_JOB_KIND = "jaggedthoughts_hypothesis_set_epoch_research"
HYPOTHESIS_SET_EVIDENCE_REQUEST_SCHEMA = "jaggedthoughts-hypothesis-set-evidence-request-v1"
HYPOTHESIS_SET_EVIDENCE_JOB_SCHEMA = "jaggedthoughts-hypothesis-set-evidence-job-v1"
HYPOTHESIS_SET_EVIDENCE_RESULT_SCHEMA = "jaggedthoughts-hypothesis-set-evidence-result-v1"
HYPOTHESIS_SET_EVIDENCE_JOB_KIND = "jaggedthoughts_hypothesis_set_evidence_research"
MAX_HYPOTHESIS_SET_EPOCH_DEPTH = 3
_V2_MATRIX_FIELDS = {
    "candidate_leaf_sha256", "question_frontier_sha256", "evidence_cutoff",
    "predicted_at", "committee_epoch_id", "hypotheses", "protocol_ids",
    "program_declared_source_call_units", "responses", "selection",
    "deterministic_control_selection", "structure_belief_sha256", "mass_semantics",
    "score_semantics", "status", "selected_program_id",
}
_V2_SETTLEMENT_FIELDS = {
    "matrix_sha256", "program_id", "observed_response", "observed_at",
    "evidence_refs", "posterior_cell_size", "realized_information_yield",
    "realized_information_bits", "executed_declared_source_call_units",
    "realized_information_bits_per_declared_source_call_unit", "status",
    "structure_belief_update_receipt", "predictive_scores",
    "matrix_policy_choice_observed",
}


def _validated_refutation(
    matrix: Mapping[str, Any], settlement: Mapping[str, Any],
    prior_settlements: Sequence[Mapping[str, Any]] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    frozen = validate_prospective_response_matrix(matrix)
    result = validate_prospective_response_settlement(settlement)
    if (
        frozen.get("schema") != RESPONSE_MATRIX_SCHEMA
        or result.get("schema") != RESPONSE_SETTLEMENT_SCHEMA
        or not _V2_MATRIX_FIELDS.issubset(frozen)
        or not _V2_SETTLEMENT_FIELDS.issubset(result)
    ):
        raise ValueError("hypothesis epoch requires complete v2 matrix and settlement")
    prior = [validate_prospective_response_settlement(row) for row in prior_settlements]
    if [row["settlement_sha256"] for row in prior] != list(
        result.get("prior_settlement_sha256s") or ()
    ):
        raise ValueError("hypothesis epoch settlement crossed its continuation lineage")
    recomputed = settle_prospective_response_matrix(
        frozen,
        program_id=str(result.get("program_id") or ""),
        observed_response=str(result.get("observed_response") or ""),
        observed_at=str(result.get("observed_at") or ""),
        evidence_refs=list(result.get("evidence_refs") or ()),
        execution_contract=(
            result.get("response_matrix_execution")
            if isinstance(result.get("response_matrix_execution"), Mapping) else None
        ),
        prior_settlements=prior,
    )
    if recomputed != result:
        raise ValueError("hypothesis epoch settlement differs from deterministic replay")
    return frozen, result


def _derived_epoch_depth(matrix: Mapping[str, Any]) -> tuple[int, str | None]:
    result_sha = matrix.get("hypothesis_set_epoch_result_sha256")
    parent_depth = matrix.get("epoch_depth")
    if (result_sha is None) != (parent_depth is None):
        raise ValueError("hypothesis epoch matrix has partial successor lineage")
    if result_sha is None:
        return 1, None
    lineage_sha = require_text(result_sha, "hypothesis epoch lineage result hash")
    if (
        len(lineage_sha) != 64
        or lineage_sha != lineage_sha.lower()
        or any(char not in "0123456789abcdef" for char in lineage_sha)
    ):
        raise ValueError("hypothesis epoch lineage result hash is invalid")
    if isinstance(parent_depth, bool) or not isinstance(parent_depth, int):
        raise ValueError("hypothesis epoch lineage depth is invalid")
    depth = int(parent_depth) + 1
    if depth < 2 or depth > MAX_HYPOTHESIS_SET_EPOCH_DEPTH:
        raise ValueError("hypothesis set epoch depth is outside the bounded recursion")
    return depth, lineage_sha


def _validated_frontier(value: Mapping[str, Any], expected_sha256: str) -> dict[str, Any]:
    body = dict(value)
    declared = require_text(
        body.pop("question_frontier_sha256", ""), "question frontier hash",
    )
    if declared != expected_sha256 or stable_sha256(body) != declared:
        raise ValueError("hypothesis set question frontier identity is invalid")
    if not body.get("frontier_programs"):
        raise ValueError("hypothesis set question frontier is empty")
    return {**body, "question_frontier_sha256": declared}


def hypothesis_set_epoch_output_schema(request_sha256: str) -> dict[str, Any]:
    """Strict subscription output; deterministic code owns epoch identity."""
    text = {"type": "string", "minLength": 1}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "schema": {
                "type": "string",
                "const": "jaggedthoughts-hypothesis-set-epoch-proposal-v1",
            },
            "request_sha256": {
                "type": "string", "const": require_text(request_sha256, "request hash"),
            },
            "hypotheses": {
                "type": "array", "minItems": 3, "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "hypothesis_id": text,
                        "kind": {"type": "string", "enum": ["thesis", "rival", "null"]},
                        "mechanism": text,
                        "falsifier": text,
                        "source_refs": {"type": "array", "minItems": 1, "items": text},
                    },
                    "required": [
                        "hypothesis_id", "kind", "mechanism", "falsifier", "source_refs",
                    ],
                    "additionalProperties": False,
                },
            },
            "expansion_rationale": text,
        },
        "required": ["schema", "request_sha256", "hypotheses", "expansion_rationale"],
        "additionalProperties": False,
    }


def render_hypothesis_set_epoch_prompt(
    request: Mapping[str, Any], matrix: Mapping[str, Any], settlement: Mapping[str, Any],
    prior_settlements: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Render the bounded M-open research assignment."""
    frozen = validate_hypothesis_set_epoch_request(request)
    parent, result = _validated_refutation(matrix, settlement, prior_settlements)
    parent_rows = [
        {
            "kind": row.get("kind"), "hypothesis_id": row.get("hypothesis_id"),
            "mechanism": row.get("mechanism"),
            "mechanism_sha256": row.get("mechanism_sha256"),
            "source_refs": row.get("source_refs") or [],
        }
        for row in parent.get("hypotheses") or ()
    ]
    context = {
        "entity_id": frozen["entity_id"],
        "request_sha256": frozen["request_sha256"],
        "refuted_parent_committee": parent_rows,
        "observed_response": result["observed_response"],
        "observed_at": result["observed_at"],
        "trigger_evidence_refs": result.get("evidence_refs") or [],
        "question_frontier_sha256": frozen["question_frontier_sha256"],
    }
    return (
        "You are the JaggedThoughts hypothesis-expansion researcher. The frozen "
        "thesis/rival/null committee assigned zero probability to a later public "
        "observation and is refuted. Propose exactly one new thesis, rival, and null "
        "mechanism for the same entity. At least one mechanism must be substantively "
        "different from every parent mechanism; relabeling is insufficient. Give each "
        "mechanism a discriminating falsifier and public primary-source URLs. Do not "
        "rank securities, set weights, or make a capital decision. Return only the "
        "strict JSON object requested by the output schema.\n\nBOUND CONTEXT:\n"
        + json.dumps(context, indent=2, sort_keys=True)
    )


def compile_hypothesis_set_epoch_result(
    request: Mapping[str, Any], matrix: Mapping[str, Any], settlement: Mapping[str, Any],
    proposal: Mapping[str, Any], *, accepted_at: str,
    provider_result_provenance: Mapping[str, Any],
    prior_settlements: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Compile a successor committee without mutating or promoting its parent."""
    frozen_request = validate_hypothesis_set_epoch_request(request)
    parent, trigger = _validated_refutation(matrix, settlement, prior_settlements)
    depth, parent_result_sha = _derived_epoch_depth(parent)
    if (
        parent["matrix_sha256"] != frozen_request["parent_matrix_sha256"]
        or trigger["settlement_sha256"] != frozen_request["trigger_settlement_sha256"]
        or trigger.get("matrix_sha256") != parent["matrix_sha256"]
        or frozen_request.get("epoch_depth") != depth
        or frozen_request.get("parent_hypothesis_set_epoch_result_sha256")
        != parent_result_sha
        or frozen_request.get("prior_settlement_sha256s") != [
            row["settlement_sha256"]
            for row in map(validate_prospective_response_settlement, prior_settlements)
        ]
    ):
        raise ValueError("hypothesis successor crossed its parent artifacts")
    raw = dict(proposal)
    if (
        raw.get("schema") != "jaggedthoughts-hypothesis-set-epoch-proposal-v1"
        or raw.get("request_sha256") != frozen_request["request_sha256"]
    ):
        raise ValueError("hypothesis successor proposal identity is invalid")
    available_at = canonical_timestamp(accepted_at, "hypothesis successor accepted_at")
    if timestamp_key(available_at) < timestamp_key(canonical_timestamp(
        trigger["observed_at"], "hypothesis successor trigger time",
    )):
        raise ValueError("hypothesis successor predates its refuting evidence")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    kinds: set[str] = set()
    for value in raw.get("hypotheses") or ():
        row = dict(value)
        hypothesis_id = require_text(row.get("hypothesis_id"), "successor hypothesis id")
        kind = require_text(row.get("kind"), f"{hypothesis_id} kind")
        mechanism = require_text(row.get("mechanism"), f"{hypothesis_id} mechanism")
        falsifier = require_text(row.get("falsifier"), f"{hypothesis_id} falsifier")
        source_refs = sorted({
            require_text(ref, f"{hypothesis_id} source ref")
            for ref in row.get("source_refs") or ()
        })
        if hypothesis_id in ids or kind in kinds:
            raise ValueError("successor hypothesis ids and kinds must be unique")
        if kind not in {"thesis", "rival", "null"} or not source_refs:
            raise ValueError("successor requires sourced thesis, rival, and null hypotheses")
        if any(not ref.startswith(("https://", "http://")) for ref in source_refs):
            raise ValueError("successor hypothesis sources must be public URLs")
        ids.add(hypothesis_id)
        kinds.add(kind)
        rows.append({
            "hypothesis_id": hypothesis_id, "kind": kind,
            "mechanism": mechanism, "mechanism_sha256": stable_sha256(mechanism),
            "falsifier": falsifier, "source_refs": source_refs,
        })
    if kinds != {"thesis", "rival", "null"} or len(rows) != 3:
        raise ValueError("successor requires exactly one thesis, rival, and null")
    if len({row["mechanism_sha256"] for row in rows}) != len(rows):
        raise ValueError("successor mechanisms must be distinct")
    parent_mechanisms = set(frozen_request["successor_contract"]["parent_mechanism_sha256s"])
    changed = [row for row in rows if row["mechanism_sha256"] not in parent_mechanisms]
    if len(changed) < int(
        frozen_request["successor_contract"]["minimum_changed_mechanism_count"]
    ):
        raise ValueError("successor committee did not change a parent mechanism")
    provenance = dict(provider_result_provenance)
    declared_provenance = require_text(
        provenance.pop("provenance_sha256", ""), "hypothesis successor provenance hash",
    )
    if stable_sha256(provenance) != declared_provenance:
        raise ValueError("hypothesis successor provider provenance is invalid")
    normalized_rows = sorted(rows, key=lambda row: row["kind"])
    body = {
        "schema": HYPOTHESIS_SET_EPOCH_RESULT_SCHEMA,
        "request_sha256": frozen_request["request_sha256"],
        "entity_id": frozen_request["entity_id"],
        "candidate_leaf_sha256": frozen_request["candidate_leaf_sha256"],
        "parent_committee_epoch_id": frozen_request["parent_committee_epoch_id"],
        "parent_matrix_sha256": parent["matrix_sha256"],
        "parent_structure_belief_sha256": frozen_request[
            "parent_structure_belief_sha256"
        ],
        "trigger_settlement_sha256": trigger["settlement_sha256"],
        "question_frontier_sha256": frozen_request["question_frontier_sha256"],
        "epoch_depth": int(frozen_request.get("epoch_depth") or 1),
        "available_at": available_at,
        "hypotheses": normalized_rows,
        "changed_mechanism_count": len(changed),
        "expansion_rationale": require_text(
            raw.get("expansion_rationale"), "hypothesis successor rationale",
        ),
        "provider_result_provenance": {
            **provenance, "provenance_sha256": declared_provenance,
        },
        "parent_mutated": False,
        "next_transition": "freeze_successor_response_matrix",
        "research_queue_authority": True,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    body["committee_epoch_id"] = stable_sha256({
        "parent_committee_epoch_id": body["parent_committee_epoch_id"],
        "trigger_settlement_sha256": body["trigger_settlement_sha256"],
        "available_at": body["available_at"], "hypotheses": normalized_rows,
    })
    return {**body, "result_sha256": stable_sha256(body)}


def validate_hypothesis_set_epoch_result(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = require_text(body.pop("result_sha256", ""), "hypothesis epoch result hash")
    if body.get("schema") != HYPOTHESIS_SET_EPOCH_RESULT_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("hypothesis set epoch result identity is invalid")
    return {**body, "result_sha256": declared}


def compile_hypothesis_set_epoch_request(
    matrix: Mapping[str, Any], settlement: Mapping[str, Any], *, entity_id: str,
    question_frontier: Mapping[str, Any] | None = None,
    epoch_depth: int | None = None,
    prior_settlements: Sequence[Mapping[str, Any]] = (),
    prior_settlement_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """Compile the sole safe M-open trigger: zero predictive committee mass."""
    prior = [validate_prospective_response_settlement(row) for row in prior_settlements]
    paths = [
        require_text(path, "hypothesis epoch prior settlement path")
        for path in prior_settlement_paths
    ]
    if len(prior) != len(paths):
        raise ValueError("hypothesis epoch prior settlement paths are incomplete")
    frozen, result = _validated_refutation(matrix, settlement, prior)
    if result.get("matrix_sha256") != frozen["matrix_sha256"]:
        raise ValueError("hypothesis epoch settlement crossed its frozen matrix")
    update = result.get("structure_belief_update_receipt")
    if (
        result.get("status") != "committee_refuted"
        or not isinstance(update, Mapping)
        or update.get("status") != "committee_refuted"
    ):
        raise ValueError("hypothesis epoch requires a committee-refuted finite belief")
    history = update.get("observation_history") or ()
    if (
        not history
        or float(history[-1].get("predictive_evidence_mass", -1.0)) != 0.0
        or history[-1].get("question_id") != result.get("program_id")
        or history[-1].get("observed_outcome") != result.get("observed_response")
        or history[-1].get("observed_at") != result.get("observed_at")
    ):
        raise ValueError("hypothesis epoch requires a frozen zero-mass predictive witness")
    parent_belief_sha256 = (
        compile_prospective_response_continuation(frozen, prior)[
            "current_structure_belief_sha256"
        ]
        if prior else frozen.get("structure_belief_sha256")
    )
    if update.get("parent_belief_sha256") != parent_belief_sha256:
        raise ValueError("hypothesis epoch belief update crossed its parent belief")
    refs = sorted({
        require_text(value, "hypothesis epoch evidence ref")
        for value in result.get("evidence_refs") or ()
    })
    if not refs or refs != sorted(history[-1].get("evidence_refs") or ()):
        raise ValueError("hypothesis epoch evidence refs differ from the belief witness")
    hypotheses = list(frozen.get("hypotheses") or ())
    if {str(row.get("kind") or "") for row in hypotheses} != {"thesis", "rival", "null"}:
        raise ValueError("hypothesis epoch parent must contain thesis, rival, and null")
    depth, parent_result_sha = _derived_epoch_depth(frozen)
    if epoch_depth is not None and (
        isinstance(epoch_depth, bool) or int(epoch_depth) != depth
    ):
        raise ValueError("hypothesis set epoch depth differs from matrix lineage")
    embedded_frontier = None
    if question_frontier is not None:
        embedded_frontier = _validated_frontier(
            question_frontier, str(frozen["question_frontier_sha256"]),
        )
    body = {
        "schema": HYPOTHESIS_SET_EPOCH_REQUEST_SCHEMA,
        "request_id": f"hypothesis-set-epoch:{result['settlement_sha256'][:24]}",
        "entity_id": require_text(entity_id, "hypothesis epoch entity_id").upper(),
        "candidate_leaf_sha256": frozen["candidate_leaf_sha256"],
        "parent_committee_epoch_id": frozen["committee_epoch_id"],
        "parent_matrix_sha256": frozen["matrix_sha256"],
        "parent_hypothesis_set_epoch_result_sha256": parent_result_sha,
        "parent_structure_belief_sha256": frozen["structure_belief_sha256"],
        "epoch_depth": depth,
        "trigger_settlement_sha256": result["settlement_sha256"],
        "prior_settlement_sha256s": [row["settlement_sha256"] for row in prior],
        "prior_settlement_paths": paths,
        "trigger_rule": "frozen_committee_zero_predictive_evidence_mass",
        "trigger_witness": {
            "program_id": result["program_id"],
            "observed_response": result["observed_response"],
            "observed_at": canonical_timestamp(
                result["observed_at"], "hypothesis epoch observed_at",
            ),
            "evidence_refs": refs,
            "refuted_belief_sha256": update["belief_sha256"],
        },
        "question_frontier_sha256": frozen["question_frontier_sha256"],
        **({"question_frontier": embedded_frontier} if embedded_frontier else {}),
        "successor_contract": {
            "hypothesis_kinds": ["thesis", "rival", "null"],
            "minimum_changed_mechanism_count": 1,
            "parent_mechanism_sha256s": sorted(
                str(row["mechanism_sha256"]) for row in hypotheses
            ),
            "evidence_cutoff": result["observed_at"],
            "parent_mutation_allowed": False,
        },
        "required_capability": "subscription_hypothesis_expansion",
        "expected_exit": "new_hypothesis_set_epoch_or_typed_failure",
        "research_queue_authority": True,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "request_sha256": stable_sha256(body)}


def validate_hypothesis_set_epoch_request(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = require_text(body.pop("request_sha256", ""), "hypothesis epoch request hash")
    if body.get("schema") != HYPOTHESIS_SET_EPOCH_REQUEST_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("hypothesis set epoch request identity is invalid")
    return {**body, "request_sha256": declared}


def enqueue_hypothesis_set_epoch_request(
    workspace: str | Path, *, matrix: Mapping[str, Any], settlement: Mapping[str, Any],
    entity_id: str, matrix_path: str, settlement_path: str,
    question_frontier: Mapping[str, Any] | None = None,
    epoch_depth: int | None = None,
    prior_settlements: Sequence[Mapping[str, Any]] = (),
    prior_settlement_paths: Sequence[str] = (),
    max_attempts: int = 3,
) -> dict[str, Any]:
    """Persist and enqueue one successor request; parent artifacts remain unchanged."""
    root = Path(workspace).expanduser().resolve()
    matrix_file = (root / matrix_path).resolve()
    settlement_file = (root / settlement_path).resolve()
    matrix_file.relative_to(root)
    settlement_file.relative_to(root)
    stored_matrix = validate_prospective_response_matrix(
        json.loads(matrix_file.read_text(encoding="utf-8")),
    )
    stored_settlement = validate_prospective_response_settlement(
        json.loads(settlement_file.read_text(encoding="utf-8")),
    )
    stored_prior = []
    for value in prior_settlement_paths:
        prior_file = (root / value).resolve()
        prior_file.relative_to(root)
        stored_prior.append(validate_prospective_response_settlement(
            json.loads(prior_file.read_text(encoding="utf-8")),
        ))
    if (
        stored_matrix["matrix_sha256"] != matrix.get("matrix_sha256")
        or stored_settlement["settlement_sha256"] != settlement.get("settlement_sha256")
        or [row["settlement_sha256"] for row in stored_prior]
        != [row.get("settlement_sha256") for row in prior_settlements]
    ):
        raise ValueError("hypothesis epoch queue paths differ from supplied artifacts")
    request = compile_hypothesis_set_epoch_request(
        matrix, settlement, entity_id=entity_id,
        question_frontier=question_frontier, epoch_depth=epoch_depth,
        prior_settlements=prior_settlements,
        prior_settlement_paths=prior_settlement_paths,
    )
    request_path = (
        root / "research_jobs" / "activation" / "hypothesis_set_epochs" / "requests"
        / f"{request['request_sha256']}.json"
    )
    request_path.parent.mkdir(parents=True, exist_ok=True)
    if request_path.exists():
        stored_request = validate_hypothesis_set_epoch_request(
            json.loads(request_path.read_text(encoding="utf-8")),
        )
        if stored_request["request_sha256"] != request["request_sha256"]:
            raise ValueError("hypothesis epoch request path has conflicting bytes")
    else:
        temporary = request_path.with_name(f".{request_path.name}.tmp")
        temporary.write_text(
            json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        temporary.replace(request_path)
    work_id = f"investment-hypothesis-set-epoch:{request['request_sha256'][:24]}"
    body = {
        "schema": HYPOTHESIS_SET_EPOCH_JOB_SCHEMA,
        "work_id": work_id,
        "request_sha256": request["request_sha256"],
        "request_path": request_path.relative_to(root).as_posix(),
        "parent_matrix_path": require_text(matrix_path, "hypothesis epoch matrix path"),
        "trigger_settlement_path": require_text(
            settlement_path, "hypothesis epoch settlement path",
        ),
        "entity_id": request["entity_id"],
        "candidate_leaf_sha256": request["candidate_leaf_sha256"],
        "stage": "queued",
        "required_capability": request["required_capability"],
        "expected_exit": request["expected_exit"],
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    job = {**body, "job_sha256": stable_sha256(body)}
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        existing = connection.execute(
            "SELECT 1 FROM work_items WHERE work_id=?", (work_id,),
        ).fetchone()
        work_queue.enqueue(
            connection, kind=HYPOTHESIS_SET_EPOCH_JOB_KIND, priority=925_000,
            max_attempts=max_attempts, payload=job,
        )
        if existing is None:
            work_queue.append_event(
                str(root / "research_jobs" / "agent" / "events.jsonl"),
                {"event_type": "investment_hypothesis_set_epoch_requested", "payload": job},
            )
    finally:
        connection.close()
    return {
        "schema": "jaggedthoughts-hypothesis-set-epoch-enqueue-v1",
        "status": "queued", "work_id": work_id,
        "request_path": request_path.relative_to(root).as_posix(),
        "request_sha256": request["request_sha256"],
        "parent_matrix_sha256": request["parent_matrix_sha256"],
        "trigger_settlement_sha256": request["trigger_settlement_sha256"],
        "capital_authority": False,
    }


def hypothesis_set_evidence_output_schema(
    request_sha256: str, atom_ids: list[str],
) -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "schema": {
                "type": "string",
                "const": "jaggedthoughts-hypothesis-set-evidence-proposal-v1",
            },
            "request_sha256": {"type": "string", "const": request_sha256},
            "atom_results": {
                "type": "array", "minItems": len(atom_ids), "maxItems": len(atom_ids),
                "items": {
                    "type": "object",
                    "properties": {
                        "atom_id": {"type": "string", "enum": atom_ids},
                        "status": {
                            "type": "string",
                            "enum": [
                                "supports_thesis", "supports_rival", "mixed", "unresolved",
                            ],
                        },
                        "finding": text,
                        "evidence_refs": {
                            "type": "array", "minItems": 1, "items": text,
                        },
                    },
                    "required": ["atom_id", "status", "finding", "evidence_refs"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["schema", "request_sha256", "atom_results"],
        "additionalProperties": False,
    }


def compile_hypothesis_set_evidence_request(
    matrix: Mapping[str, Any], question_frontier: Mapping[str, Any],
    successor: Mapping[str, Any], *, matrix_path: str, successor_path: str,
    prior_settlements: Sequence[Mapping[str, Any]] = (),
    prior_settlement_paths: Sequence[str] = (),
) -> dict[str, Any]:
    frozen = validate_prospective_response_matrix(matrix)
    result = validate_hypothesis_set_epoch_result(successor)
    frontier = _validated_frontier(
        question_frontier, str(frozen["question_frontier_sha256"]),
    )
    committee_core = lambda rows: sorted((
        str(row.get("hypothesis_id")), str(row.get("kind")),
        str(row.get("mechanism_sha256")), tuple(sorted(row.get("source_refs") or ())),
    ) for row in rows or ())
    if (
        frozen["candidate_leaf_sha256"] != result["candidate_leaf_sha256"]
        or frozen["question_frontier_sha256"] != result["question_frontier_sha256"]
        or frozen.get("hypothesis_set_epoch_result_sha256") != result["result_sha256"]
        or frozen.get("epoch_depth") != result["epoch_depth"]
        or committee_core(frozen.get("hypotheses"))
        != committee_core(result.get("hypotheses"))
    ):
        raise ValueError("successor evidence request crossed its committee identity")
    settled = [validate_prospective_response_settlement(row) for row in prior_settlements]
    paths = [require_text(path, "successor prior settlement path") for path in prior_settlement_paths]
    if len(settled) != len(paths):
        raise ValueError("successor evidence settlement paths are incomplete")
    continuation = (
        compile_prospective_response_continuation(frozen, settled) if settled else None
    )
    if continuation is not None and continuation.get("next_program_id") is None:
        raise ValueError("successor response frontier is exhausted")
    program_id = require_text(
        continuation.get("next_program_id") if continuation
        else frozen.get("selected_program_id"),
        "successor selected program",
    )
    program = next((
        dict(row) for row in frontier.get("frontier_programs") or ()
        if isinstance(row, Mapping) and row.get("program_id") == program_id
    ), None)
    if program is None:
        raise ValueError("successor selected program is outside its question frontier")
    atom_ids = sorted({
        require_text(value, "successor evidence atom")
        for value in program.get("atom_ids") or ()
    })
    if not atom_ids:
        raise ValueError("successor evidence program has no atoms")
    body = {
        "schema": HYPOTHESIS_SET_EVIDENCE_REQUEST_SCHEMA,
        "request_id": (
            f"hypothesis-set-evidence:{frozen['matrix_sha256'][:16]}:"
            f"{stable_sha256({'program_id': program_id, 'prior': [row['settlement_sha256'] for row in settled]})[:16]}"
        ),
        "entity_id": result["entity_id"],
        "candidate_leaf_sha256": result["candidate_leaf_sha256"],
        "epoch_depth": int(result["epoch_depth"]),
        "successor_result_sha256": result["result_sha256"],
        "successor_result_path": require_text(successor_path, "successor result path"),
        "matrix_sha256": frozen["matrix_sha256"],
        "matrix_path": require_text(matrix_path, "successor matrix path"),
        "question_frontier_sha256": frontier["question_frontier_sha256"],
        "question_frontier": frontier,
        "selected_program": program,
        "selected_program_id": program_id,
        "atom_ids": atom_ids,
        "hypotheses": result["hypotheses"],
        "evidence_cutoff": (
            settled[-1]["observed_at"] if settled else frozen["predicted_at"]
        ),
        "prior_settlement_sha256s": [row["settlement_sha256"] for row in settled],
        "prior_settlement_paths": paths,
        **({"continuation": continuation} if continuation else {}),
        "required_capability": "subscription_hypothesis_evidence",
        "expected_exit": "source_bound_response_settlement",
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "request_sha256": stable_sha256(body)}


def validate_hypothesis_set_evidence_request(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = require_text(body.pop("request_sha256", ""), "hypothesis evidence hash")
    if body.get("schema") != HYPOTHESIS_SET_EVIDENCE_REQUEST_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("hypothesis set evidence request identity is invalid")
    return {**body, "request_sha256": declared}


def render_hypothesis_set_evidence_prompt(request: Mapping[str, Any]) -> str:
    frozen = validate_hypothesis_set_evidence_request(request)
    context = {
        key: frozen[key] for key in (
            "request_sha256", "entity_id", "evidence_cutoff", "selected_program",
            "hypotheses", "atom_ids",
        )
    }
    return (
        "You are the JaggedThoughts bounded public-evidence researcher. Research only "
        "the selected program and return every declared atom exactly once. Use public "
        "primary sources available after the frozen evidence cutoff. For each atom, "
        "classify the evidence as supports_thesis, supports_rival, mixed, or unresolved; "
        "cite opened public URLs and state the finding. Do not revise the hypotheses, "
        "browse another question, rank a security, set a weight, or make a capital "
        "decision. Return only the strict JSON object requested by the output schema.\n\n"
        "FROZEN ASSIGNMENT:\n" + json.dumps(context, indent=2, sort_keys=True)
    )


def compile_hypothesis_set_evidence_result(
    request: Mapping[str, Any], proposal: Mapping[str, Any], *, accepted_at: str,
    provider_result_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = validate_hypothesis_set_evidence_request(request)
    raw = dict(proposal)
    if (
        raw.get("schema") != "jaggedthoughts-hypothesis-set-evidence-proposal-v1"
        or raw.get("request_sha256") != frozen["request_sha256"]
    ):
        raise ValueError("hypothesis evidence proposal identity is invalid")
    observed_at = canonical_timestamp(accepted_at, "hypothesis evidence accepted_at")
    if timestamp_key(observed_at) < timestamp_key(str(frozen["evidence_cutoff"])):
        raise ValueError("hypothesis evidence predates its frozen matrix")
    expected_atoms = set(map(str, frozen["atom_ids"]))
    rows: dict[str, dict[str, Any]] = {}
    for value in raw.get("atom_results") or ():
        row = dict(value)
        atom_id = require_text(row.get("atom_id"), "hypothesis evidence atom")
        status = require_text(row.get("status"), f"{atom_id} evidence status")
        refs = sorted({
            require_text(ref, f"{atom_id} evidence ref")
            for ref in row.get("evidence_refs") or ()
        })
        if atom_id in rows or atom_id not in expected_atoms:
            raise ValueError("hypothesis evidence crossed or duplicated an atom")
        if status not in {"supports_thesis", "supports_rival", "mixed", "unresolved"}:
            raise ValueError("hypothesis evidence status is unsupported")
        if not refs or any(not ref.startswith(("https://", "http://")) for ref in refs):
            raise ValueError("hypothesis evidence requires public source URLs")
        rows[atom_id] = {
            "atom_id": atom_id, "status": status,
            "finding": require_text(row.get("finding"), f"{atom_id} finding"),
            "evidence_refs": refs,
        }
    if set(rows) != expected_atoms:
        raise ValueError("hypothesis evidence result is not atom-complete")
    statuses = {row["status"] for row in rows.values()}
    observed_response = next(iter(statuses)) if len(statuses) == 1 else "mixed"
    provenance = dict(provider_result_provenance)
    declared_provenance = require_text(
        provenance.pop("provenance_sha256", ""), "hypothesis evidence provenance hash",
    )
    if stable_sha256(provenance) != declared_provenance:
        raise ValueError("hypothesis evidence provider provenance is invalid")
    body = {
        "schema": HYPOTHESIS_SET_EVIDENCE_RESULT_SCHEMA,
        "request_sha256": frozen["request_sha256"],
        "entity_id": frozen["entity_id"],
        "candidate_leaf_sha256": frozen["candidate_leaf_sha256"],
        "epoch_depth": frozen["epoch_depth"],
        "successor_result_sha256": frozen["successor_result_sha256"],
        "matrix_sha256": frozen["matrix_sha256"],
        "selected_program_id": frozen["selected_program_id"],
        "observed_response": observed_response,
        "observed_at": observed_at,
        "atom_results": [rows[key] for key in sorted(rows)],
        "evidence_refs": sorted({
            ref for row in rows.values() for ref in row["evidence_refs"]
        }),
        "provider_result_provenance": {
            **provenance, "provenance_sha256": declared_provenance,
        },
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "result_sha256": stable_sha256(body)}


def validate_hypothesis_set_evidence_result(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = require_text(body.pop("result_sha256", ""), "hypothesis evidence result hash")
    if body.get("schema") != HYPOTHESIS_SET_EVIDENCE_RESULT_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("hypothesis set evidence result identity is invalid")
    return {**body, "result_sha256": declared}


def enqueue_hypothesis_set_evidence_request(
    workspace: str | Path, *, matrix: Mapping[str, Any],
    question_frontier: Mapping[str, Any], successor: Mapping[str, Any],
    matrix_path: str, successor_path: str, max_attempts: int = 3,
    prior_settlements: Sequence[Mapping[str, Any]] = (),
    prior_settlement_paths: Sequence[str] = (),
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    request = compile_hypothesis_set_evidence_request(
        matrix, question_frontier, successor,
        matrix_path=matrix_path, successor_path=successor_path,
        prior_settlements=prior_settlements,
        prior_settlement_paths=prior_settlement_paths,
    )
    request_path = (
        root / "research_jobs" / "activation" / "hypothesis_set_evidence" / "requests"
        / f"{request['request_sha256']}.json"
    )
    request_path.parent.mkdir(parents=True, exist_ok=True)
    if request_path.exists():
        stored = validate_hypothesis_set_evidence_request(
            json.loads(request_path.read_text(encoding="utf-8")),
        )
        if stored["request_sha256"] != request["request_sha256"]:
            raise ValueError("hypothesis evidence request path has conflicting bytes")
    else:
        temporary = request_path.with_name(f".{request_path.name}.tmp")
        temporary.write_text(
            json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        temporary.replace(request_path)
    work_id = f"investment-hypothesis-evidence:{request['request_sha256'][:24]}"
    job_body = {
        "schema": HYPOTHESIS_SET_EVIDENCE_JOB_SCHEMA,
        "work_id": work_id,
        "request_sha256": request["request_sha256"],
        "request_path": request_path.relative_to(root).as_posix(),
        "entity_id": request["entity_id"],
        "stage": "queued",
        "required_capability": request["required_capability"],
        "expected_exit": request["expected_exit"],
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    job = {**job_body, "job_sha256": stable_sha256(job_body)}
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        existing = connection.execute(
            "SELECT 1 FROM work_items WHERE work_id=?", (work_id,),
        ).fetchone()
        work_queue.enqueue(
            connection, kind=HYPOTHESIS_SET_EVIDENCE_JOB_KIND, priority=920_000,
            max_attempts=max_attempts, payload=job,
        )
        if existing is None:
            work_queue.append_event(
                str(root / "research_jobs" / "agent" / "events.jsonl"),
                {"event_type": "investment_hypothesis_evidence_requested", "payload": job},
            )
    finally:
        connection.close()
    return {
        "schema": "jaggedthoughts-hypothesis-set-evidence-enqueue-v1",
        "status": "queued", "work_id": work_id,
        "request_path": request_path.relative_to(root).as_posix(),
        "request_sha256": request["request_sha256"],
        "matrix_sha256": request["matrix_sha256"],
        "selected_program_id": request["selected_program_id"],
        "capital_authority": False,
    }


__all__ = [
    "HYPOTHESIS_SET_EVIDENCE_JOB_KIND", "HYPOTHESIS_SET_EVIDENCE_JOB_SCHEMA",
    "HYPOTHESIS_SET_EVIDENCE_REQUEST_SCHEMA", "HYPOTHESIS_SET_EVIDENCE_RESULT_SCHEMA",
    "HYPOTHESIS_SET_EPOCH_JOB_KIND", "HYPOTHESIS_SET_EPOCH_JOB_SCHEMA",
    "HYPOTHESIS_SET_EPOCH_REQUEST_SCHEMA", "HYPOTHESIS_SET_EPOCH_RESULT_SCHEMA",
    "MAX_HYPOTHESIS_SET_EPOCH_DEPTH", "compile_hypothesis_set_evidence_request",
    "compile_hypothesis_set_evidence_result",
    "compile_hypothesis_set_epoch_request", "compile_hypothesis_set_epoch_result",
    "enqueue_hypothesis_set_evidence_request", "enqueue_hypothesis_set_epoch_request",
    "hypothesis_set_epoch_output_schema", "hypothesis_set_evidence_output_schema",
    "render_hypothesis_set_evidence_prompt",
    "render_hypothesis_set_epoch_prompt", "validate_hypothesis_set_epoch_request",
    "validate_hypothesis_set_epoch_result", "validate_hypothesis_set_evidence_request",
    "validate_hypothesis_set_evidence_result",
]
