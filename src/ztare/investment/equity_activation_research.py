"""Compile source-bound research that can advance blocked equity proposals."""

from __future__ import annotations

import argparse
from functools import lru_cache
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .business_fingerprint_acquisition import (
    BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA,
    compile_workspace_fingerprint_acquisition_plan,
)
from .contracts import canonical_timestamp, require_text, timestamp_key
from .equity_paper import AUDIT_SCHEMA
from .golden_store import GoldenStore, record_agent_research_request
from .learning_credit import learning_credit_allows
from .research_jobs import RESEARCH_REQUEST_SCHEMA, research_rank_priority
from .research_monitor import current_monitor_receipts
from .research_memory import RESEARCH_COVERAGE_SCHEMA
from .research_questions import (
    RESEARCH_QUESTION_FRONTIER_SCHEMA,
    compile_research_question_frontier,
)
from .sources import load_source_manifest


ACTIVATION_RESEARCH_REQUEST_SCHEMA = (
    "jaggedthoughts-equity-activation-research-request-v1"
)
ACTIVATION_RESEARCH_JOB_SCHEMA = (
    "jaggedthoughts-subscription-activation-research-job-v1"
)
ACTIVATION_RESEARCH_JOB_KIND = "jaggedthoughts_subscription_activation_research"
MATRIX_POLICY_ASSIGNMENT_SCHEMA = (
    "jaggedthoughts-activation-matrix-policy-assignment-v2"
)
LEGACY_MATRIX_POLICY_ASSIGNMENT_SCHEMA = (
    "jaggedthoughts-activation-matrix-policy-assignment-v1"
)
MATRIX_POLICY_LEARNING_SCHEMA = "jaggedthoughts-activation-matrix-policy-learning-v2"
LEGACY_MATRIX_POLICY_LEARNING_SCHEMA = "jaggedthoughts-activation-matrix-policy-learning-v1"
MATRIX_POLICY_EXPERIMENT = "activation_stochastic_question_policy_v2"
LEGACY_MATRIX_POLICY_EXPERIMENT = "activation_matrix_question_policy_v1"
MATRIX_POLICY_ARMS = (
    "incumbent_question", "stochastic_matrix_selected_question",
)
LEGACY_MATRIX_POLICY_ARMS = ("incumbent_question", "matrix_selected_question")
ALL_MATRIX_POLICY_ARMS = tuple(dict.fromkeys((*MATRIX_POLICY_ARMS, *LEGACY_MATRIX_POLICY_ARMS)))
MATRIX_POLICY_EFFECTIVE_AT = "2026-08-22T21:42:16Z"


def _immutable_json(path: Path, payload: Mapping[str, Any]) -> None:
    text = json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"immutable activation research artifact changed: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    try:
        int(digest, 16)
    except ValueError as error:
        raise ValueError(f"{label} must be a SHA-256 digest") from error
    return digest


def _verified(
    payload: Mapping[str, Any], *, schema: str, digest_field: str, label: str,
) -> tuple[dict[str, Any], str]:
    body = dict(payload)
    declared = _digest(body.pop(digest_field, ""), f"{label} hash")
    if body.get("schema") != schema or stable_sha256(body) != declared:
        raise ValueError(f"{label} identity is invalid")
    return {**body, digest_field: declared}, declared


def validate_equity_activation_request(request: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the identities a subscription consumer may rely on."""
    normalized, _ = _verified(
        request, schema=ACTIVATION_RESEARCH_REQUEST_SCHEMA,
        digest_field="request_sha256", label="equity activation research request",
    )
    candidate = normalized.get("candidate_identity") or {}
    prior = normalized.get("prior_dossier_identity") or {}
    coverage = normalized.get("coverage_identity") or {}
    for value, label in (
        (candidate.get("candidate_leaf"), "activation candidate leaf"),
        (candidate.get("candidate_sha256"), "activation candidate hash"),
        (prior.get("dossier_leaf"), "activation prior dossier leaf"),
        (prior.get("dossier_sha256"), "activation prior dossier hash"),
        (coverage.get("coverage_sha256"), "activation coverage hash"),
    ):
        _digest(value, label)
    epoch = dict(normalized.get("source_epoch") or {})
    declared_epoch = _digest(epoch.pop("source_epoch_sha256", ""), "activation source epoch")
    if stable_sha256(epoch) != declared_epoch:
        raise ValueError("activation source epoch identity is invalid")
    coordinates = list((normalized.get("acquisition") or {}).get("coordinate_ids") or ())
    if not coordinates or len(coordinates) != len(set(coordinates)):
        raise ValueError("activation research requires unique typed coordinates")
    question_frontier = normalized.get("research_question_frontier")
    if question_frontier is not None:
        question_body = dict(question_frontier)
        question_sha = _digest(
            question_body.pop("question_frontier_sha256", ""),
            "activation research question frontier hash",
        )
        if (
            question_body.get("schema") != RESEARCH_QUESTION_FRONTIER_SCHEMA
            or stable_sha256(question_body) != question_sha
            or question_body.get("entity_id") != candidate.get("entity_id")
            or question_body.get("candidate_sha256") != candidate.get("candidate_sha256")
        ):
            raise ValueError("activation research question frontier identity is invalid")
        strategy_context = question_body.get("strategy_context")
        if isinstance(strategy_context, Mapping) and (
            strategy_context.get("current_candidate_leaf") != candidate.get("candidate_leaf")
            or strategy_context.get("current_candidate_sha256") != candidate.get("candidate_sha256")
            or timestamp_key(str(strategy_context.get("current_candidate_as_of") or ""))
            != timestamp_key(str(candidate.get("as_of") or ""))
        ):
            raise ValueError("activation strategy question crossed candidate identity")
    raw_assignment = normalized.get("matrix_policy_assignment")
    if raw_assignment is not None:
        _validate_matrix_policy_assignment(
            raw_assignment, has_question_frontier=question_frontier is not None,
        )
    return normalized


def _validate_matrix_policy_assignment(
    value: Any, *, has_question_frontier: bool,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("activation matrix policy assignment must be an object")
    assignment = dict(value)
    declared_assignment = _digest(
        assignment.pop("assignment_sha256", ""),
        "activation matrix policy assignment hash",
    )
    experiment_id = assignment.get("experiment_id")
    expected = (
        (MATRIX_POLICY_ASSIGNMENT_SCHEMA, MATRIX_POLICY_ARMS)
        if experiment_id == MATRIX_POLICY_EXPERIMENT else
        (LEGACY_MATRIX_POLICY_ASSIGNMENT_SCHEMA, LEGACY_MATRIX_POLICY_ARMS)
        if experiment_id == LEGACY_MATRIX_POLICY_EXPERIMENT else (None, ())
    )
    if (
        assignment.get("schema") != expected[0]
        or assignment.get("arm_id") not in expected[1]
        or stable_sha256(assignment) != declared_assignment
    ):
        raise ValueError("activation matrix policy assignment identity is invalid")
    if assignment.get("eligible") and not has_question_frontier:
        raise ValueError("matrix policy assignment requires a question frontier")
    return {**assignment, "assignment_sha256": declared_assignment}


def activation_matrix_policy_assignment(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the signed assignment, deriving an ineligible incumbent for old requests."""

    raw = request.get("matrix_policy_assignment")
    has_frontier = isinstance(request.get("research_question_frontier"), Mapping)
    if raw is not None:
        return _validate_matrix_policy_assignment(
            raw, has_question_frontier=has_frontier,
        )
    request_sha = _digest(
        request.get("request_sha256"), "legacy activation request hash",
    )
    seed = stable_sha256({
        "experiment_id": MATRIX_POLICY_EXPERIMENT,
        "legacy_request_sha256": request_sha,
    })
    body = {
        "schema": MATRIX_POLICY_ASSIGNMENT_SCHEMA,
        "experiment_id": MATRIX_POLICY_EXPERIMENT,
        "eligible": False,
        "arm_id": MATRIX_POLICY_ARMS[0],
        "pair_id": f"nonexperimental:{seed[:16]}:legacy",
        "pair_slot": 0,
        "assignment_probability": 1.0,
        "assignment_seed_sha256": seed,
        "common_output_contract": "source_bound_research_question_outcome",
        "research_authority": "assigned_activation_question_only",
        "capital_authority": False,
    }
    return {**body, "assignment_sha256": stable_sha256(body)}


def _matrix_policy_assignments(
    rows: list[dict[str, Any]],
    *,
    audit_sha256: str,
    batch_id: str,
    question_frontiers: Mapping[str, Mapping[str, Any]],
    policy_learning: Mapping[str, Any] | None = None,
    learning_credit_assignment: Mapping[str, Any] | None = None,
    current_eligible_pair_set_sha256: str | None = None,
) -> dict[str, dict[str, Any]]:
    eligible = [
        row for row in rows
        if isinstance(question_frontiers.get(str(row["entity_id"]).upper()), Mapping)
        and question_frontiers[str(row["entity_id"]).upper()].get("frontier_programs")
    ]
    eligible.sort(key=lambda row: (
        int((row.get("candidate_identity") or {}).get("rank"))
        if (row.get("candidate_identity") or {}).get("rank") is not None else 10**9,
        str(row["entity_id"]),
    ))
    seed = stable_sha256({
        "experiment_id": MATRIX_POLICY_EXPERIMENT,
        "equity_audit_sha256": audit_sha256,
        "batch_id": batch_id,
    })
    preferred_arm = None
    policy_sha = None
    if policy_learning is not None:
        policy = dict(policy_learning)
        policy_sha = _digest(
            policy.pop("policy_learning_sha256", ""),
            "activation matrix policy learning hash",
        )
        if stable_sha256(policy) != policy_sha:
            raise ValueError("activation matrix policy learning identity is invalid")
        if policy.get("schema") == MATRIX_POLICY_LEARNING_SCHEMA and policy.get(
            "routing_change_allowed"
        ):
            candidate_arm = str(policy.get("preferred_arm") or "")
            if candidate_arm not in MATRIX_POLICY_ARMS:
                raise ValueError("activation matrix policy preferred arm is unsupported")
            try:
                admitted = learning_credit_allows(
                    learning_credit_assignment or {},
                    component_id="activation_response_question_policy",
                    use="future_activation_question_routing", source_ref=policy_sha,
                ) and learning_credit_allows(
                    learning_credit_assignment or {},
                    component_id="activation_response_question_policy",
                    use="future_activation_question_routing",
                    source_ref=str(policy.get("eligible_pair_set_sha256") or ""),
                )
            except ValueError:
                admitted = False
            preferred_arm = candidate_arm if (
                admitted
                and current_eligible_pair_set_sha256
                == policy.get("eligible_pair_set_sha256")
            ) else None
        elif policy.get("schema") not in {
            MATRIX_POLICY_LEARNING_SCHEMA, LEGACY_MATRIX_POLICY_LEARNING_SCHEMA,
        }:
            raise ValueError("activation matrix policy learning schema is unsupported")
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(eligible):
        complete_pair = index < len(eligible) - (len(eligible) % 2)
        pair_index = index // 2
        pair_randomization_sha256 = stable_sha256({
            "assignment_seed_sha256": seed,
            "pair_index": pair_index,
        })
        pair_offset = int(pair_randomization_sha256[:8], 16) % len(
            MATRIX_POLICY_ARMS
        )
        audit_pair = bool(
            preferred_arm is None
            or ((pair_index + int(seed[8:16], 16)) % 5) < 2
        )
        experimental = complete_pair and audit_pair
        arm_id = (
            MATRIX_POLICY_ARMS[
                ((index % len(MATRIX_POLICY_ARMS)) + pair_offset)
                % len(MATRIX_POLICY_ARMS)
            ]
            if experimental else preferred_arm or MATRIX_POLICY_ARMS[0]
        )
        body = {
            "schema": MATRIX_POLICY_ASSIGNMENT_SCHEMA,
            "experiment_id": MATRIX_POLICY_EXPERIMENT,
            "eligible": experimental,
            "arm_id": arm_id,
            "pair_id": (
                f"{seed[:16]}:{pair_index}" if experimental
                else f"nonexperimental:{seed[:16]}:{index}"
            ),
            "pair_slot": index % 2,
            "assignment_probability": (
                0.5 if experimental else 0.8 if preferred_arm else 1.0
            ),
            "assignment_seed_sha256": seed,
            "pair_randomization_sha256": pair_randomization_sha256,
            "routing_policy_sha256": policy_sha,
            "common_output_contract": "source_bound_research_question_outcome",
            "research_authority": "assigned_activation_question_only",
            "capital_authority": False,
        }
        result[str(row["entity_id"]).upper()] = {
            **body, "assignment_sha256": stable_sha256(body),
        }
    for row in rows:
        entity = str(row["entity_id"]).upper()
        if entity in result:
            continue
        body = {
            "schema": MATRIX_POLICY_ASSIGNMENT_SCHEMA,
            "experiment_id": MATRIX_POLICY_EXPERIMENT,
            "eligible": False,
            "arm_id": MATRIX_POLICY_ARMS[0],
            "pair_id": f"nonexperimental:{seed[:16]}:{entity}",
            "pair_slot": 0,
            "assignment_probability": 1.0,
            "assignment_seed_sha256": seed,
            "routing_policy_sha256": policy_sha,
            "common_output_contract": "source_bound_research_question_outcome",
            "research_authority": "assigned_activation_question_only",
            "capital_authority": False,
        }
        result[entity] = {**body, "assignment_sha256": stable_sha256(body)}
    return result


def _addressable_blockers(
    blockers: Iterable[str], downstream_contracts: Iterable[str], coverage_status: str,
) -> list[str]:
    namespaces = {str(value).partition(".")[0] for value in downstream_contracts}
    selected = []
    for blocker in sorted({str(value) for value in blockers if str(value)}):
        if blocker == "candidate_bound_research_dossier_absent" and "research_dossier" in namespaces:
            selected.append(blocker)
        elif blocker.startswith("research_coverage:") and "research_dossier" in namespaces:
            selected.append(blocker)
        elif blocker.startswith("business_fingerprint_") and "business_fingerprint" in namespaces:
            selected.append(blocker)
        elif blocker.startswith("strategy_frontier_") and "strategy_frontier" in namespaces:
            selected.append(blocker)
    if coverage_status and coverage_status != "covered_by_monitored_dossier":
        selected.append(f"research_coverage:{coverage_status}")
    return sorted(set(selected))


def _material_source_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Drop retrieval-only fields while preserving the evidence identity."""
    material = []
    for raw in rows:
        row = dict(raw)
        body = {
            key: row.get(key)
            for key in (
                "source_id", "adapter", "source_config_sha256", "canonical_url",
            )
            if row.get(key) not in {None, ""}
        }
        if row.get("content_sha256"):
            body["content_sha256"] = row["content_sha256"]
        else:
            for key in ("status", "receipt_sha256"):
                if row.get(key) not in {None, ""}:
                    body[key] = row[key]
        material.append(body)
    return sorted(material, key=lambda row: str(row.get("source_id") or ""))


def _selected_batch(
    rows: list[dict[str, Any]], plans: Mapping[str, Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for row in rows:
        entity = str(row["entity_id"]).upper()
        for batch in plans[entity].get("acquisition_batches") or ():
            if not isinstance(batch, Mapping):
                continue
            batch_id = str(batch.get("batch_id") or "")
            if not batch_id:
                continue
            score = candidates.setdefault(batch_id, {
                "batch_id": batch_id, "entities": set(), "rank_sum": 0,
                "contracts": set(), "coordinates": set(), "yield_classes": set(),
            })
            score["entities"].add(entity)
            score["rank_sum"] += int(batch.get("acquisition_rank") or 10**6)
            score["contracts"].update(str(value) for value in batch.get("downstream_contracts") or ())
            score["coordinates"].update(str(value) for value in batch.get("coordinate_ids") or ())
            score["yield_classes"].add(str(batch.get("information_yield_class") or ""))
    if not candidates:
        raise ValueError("no acquisition batch covers the blocked candidate set")
    winner = min(candidates.values(), key=lambda value: (
        -len(value["entities"]), value["rank_sum"], -len(value["contracts"]),
        value["batch_id"],
    ))
    selected_entities = sorted(winner["entities"])
    return str(winner["batch_id"]), {
        "batch_id": winner["batch_id"],
        "selected_entity_count": len(selected_entities),
        "selected_entities": selected_entities,
        "shared_downstream_contracts": sorted(winner["contracts"]),
        "shared_coordinate_ids": sorted(winner["coordinates"]),
        "information_yield_classes": sorted(winner["yield_classes"] - {""}),
        "selection_order": [
            "candidate_coverage_descending", "acquisition_rank_sum_ascending",
            "downstream_contract_coverage_descending", "batch_id_stable_tiebreak",
        ],
    }


def _active_covering_jobs(
    queue_rows: Iterable[Mapping[str, Any]], *, candidate_leaf: str,
    prior_dossier_leaf: str, batch_id: str, coordinate_ids: set[str],
    source_epoch_sha256: str, question_frontier_sha256: str | None,
    matrix_policy_assignment_sha256: str,
) -> list[Mapping[str, Any]]:
    """Return active work over the same candidate and source material.

    Question and routing-policy hashes are omitted from this basis so a newer
    contract can retire queued legacy work instead of paying for both. Claimed
    work remains the owner until it finishes.
    """
    matches = []
    for row in queue_rows:
        if row.get("status") not in {"queued", "claimed"}:
            continue
        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if (
            payload.get("candidate_leaf") != candidate_leaf
            or payload.get("prior_dossier_leaf") != prior_dossier_leaf
            or payload.get("source_batch_id") != batch_id
            or (
                payload.get("source_material_sha256")
                or payload.get("source_epoch_sha256")
            ) != source_epoch_sha256
            or not coordinate_ids.issubset(set(payload.get("coordinate_ids") or ()))
        ):
            continue
        matches.append(row)
    return sorted(matches, key=lambda row: str(row.get("work_id") or ""))


def compile_equity_activation_research(
    *, equity_audit: Mapping[str, Any], acquisition_plans: Mapping[str, Mapping[str, Any]],
    coverages: Mapping[str, Mapping[str, Any]],
    source_epochs: Mapping[str, Iterable[Mapping[str, Any]]],
    prior_dossiers: Mapping[str, Mapping[str, Any]],
    strategy_question_frontiers: Mapping[str, Mapping[str, Any]] | None = None,
    matrix_policy_learning: Mapping[str, Any] | None = None,
    learning_credit_assignment: Mapping[str, Any] | None = None,
    current_eligible_pair_set_sha256: str | None = None,
    queue_rows: Iterable[Mapping[str, Any]] = (), compiled_at: str,
) -> dict[str, Any]:
    """Select one shared evidence batch and compile one immutable request per candidate."""
    audit, audit_sha = _verified(
        equity_audit, schema=AUDIT_SCHEMA, digest_field="audit_sha256",
        label="equity proposal audit",
    )
    compiled = canonical_timestamp(compiled_at, "activation research compiled_at")
    rows = [
        dict(row) for row in audit.get("rows") or ()
        if isinstance(row, Mapping) and not row.get("activation_eligible")
        and row.get("candidate_leaf")
        and str(row.get("entity_id") or "").upper() in acquisition_plans
        and str(row.get("entity_id") or "").upper() in coverages
        and str(row.get("entity_id") or "").upper() in prior_dossiers
        and str((coverages[str(row.get("entity_id") or "").upper()] or {}).get("status") or "")
        != "research_evidence_quarantined"
    ]
    if not rows:
        raise ValueError("equity audit has no blocked candidate with reusable research lineage")
    normalized_plans: dict[str, dict[str, Any]] = {}
    normalized_coverages: dict[str, dict[str, Any]] = {}
    for row in rows:
        entity = str(row["entity_id"]).upper()
        plan, _ = _verified(
            acquisition_plans[entity], schema=BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA,
            digest_field="source_plan_sha256", label=f"{entity} acquisition plan",
        )
        coverage_projection = dict(coverages[entity])
        coverage_leaf = coverage_projection.pop("coverage_leaf", None)
        coverage, _ = _verified(
            coverage_projection, schema=RESEARCH_COVERAGE_SCHEMA,
            digest_field="coverage_sha256", label=f"{entity} research coverage",
        )
        coverage["coverage_leaf"] = coverage_leaf
        if plan.get("entity_id") != entity or coverage.get("entity_id") != entity:
            raise ValueError("activation research inputs crossed entity identity")
        if coverage.get("candidate_leaf") != row.get("candidate_leaf"):
            raise ValueError("research coverage crossed candidate identity")
        normalized_plans[entity], normalized_coverages[entity] = plan, coverage

    batch_id, selection = _selected_batch(rows, normalized_plans)
    selected = [row for row in rows if str(row["entity_id"]).upper() in selection["selected_entities"]]
    matrix_assignments = _matrix_policy_assignments(
        selected,
        audit_sha256=audit_sha,
        batch_id=batch_id,
        question_frontiers=strategy_question_frontiers or {},
        policy_learning=matrix_policy_learning,
        learning_credit_assignment=learning_credit_assignment,
        current_eligible_pair_set_sha256=current_eligible_pair_set_sha256,
    )
    requests, jobs = [], []
    queue_snapshot = list(queue_rows)
    for row in sorted(selected, key=lambda value: (
        int((value.get("candidate_identity") or {}).get("rank"))
        if (value.get("candidate_identity") or {}).get("rank") is not None else 10**9,
        str(value["entity_id"]),
    )):
        entity = str(row["entity_id"]).upper()
        plan = normalized_plans[entity]
        coverage = normalized_coverages[entity]
        batch = next(
            dict(value) for value in plan.get("acquisition_batches") or ()
            if value.get("batch_id") == batch_id
        )
        coordinates = [
            dict(value) for value in plan.get("coordinates") or ()
            if value.get("coordinate_id") in set(batch.get("coordinate_ids") or ())
        ]
        epoch_rows = sorted(
            (dict(value) for value in source_epochs.get(entity, ()) if isinstance(value, Mapping)),
            key=lambda value: str(value.get("source_id") or ""),
        )
        source_epoch_body = {
            "candidate_leaf": row["candidate_leaf"],
            "candidate_as_of": (row.get("candidate_identity") or {}).get("as_of"),
            "sources": _material_source_rows(epoch_rows),
        }
        source_epoch_sha = stable_sha256(source_epoch_body)
        dossier = dict(prior_dossiers[entity])
        prior_dossier_leaf = _digest(
            coverage.get("prior_dossier_leaf"), f"{entity} prior dossier leaf",
        )
        prior_dossier_sha = _digest(
            dossier.get("dossier_sha256"), f"{entity} prior dossier content hash",
        )
        if dossier.get("entity_id") != entity:
            raise ValueError("activation research prior dossier crossed entity identity")
        proposal = row.get("proposal") if isinstance(row.get("proposal"), Mapping) else None
        question_frontier = (strategy_question_frontiers or {}).get(entity)
        matrix_assignment = matrix_assignments[entity]
        target_blockers = _addressable_blockers(
            row.get("blockers") or (), batch.get("downstream_contracts") or (),
            str(coverage.get("status") or ""),
        )
        request_body = {
            "schema": ACTIVATION_RESEARCH_REQUEST_SCHEMA,
            "request_id": (
                f"activation-research:{audit_sha[:16]}:{source_epoch_sha[:16]}:"
                f"{plan['source_plan_sha256'][:16]}:{entity}:{batch_id}"
            ),
            "created_at": compiled,
            "equity_audit_sha256": audit_sha,
            "discovery_run_sha256": audit.get("discovery_run_sha256"),
            "candidate_identity": {
                "entity_id": entity,
                "candidate_leaf": _digest(row["candidate_leaf"], f"{entity} candidate leaf"),
                "candidate_sha256": _digest(row["candidate_sha256"], f"{entity} candidate hash"),
                **dict(row.get("candidate_identity") or {}),
            },
            "proposal_identity": ({
                "proposal_id": proposal.get("proposal_id"),
                "proposal_sha256": proposal.get("proposal_sha256"),
            } if proposal else None),
            "proposal_status": row.get("status"),
            "prior_dossier_identity": {
                "dossier_leaf": prior_dossier_leaf,
                "dossier_sha256": prior_dossier_sha,
                "candidate_leaf": dossier.get("candidate_leaf"),
                "generated_at": dossier.get("generated_at"),
                "transport_allowed": False,
            },
            "coverage_identity": {
                "coverage_leaf": coverage.get("coverage_leaf"),
                "coverage_sha256": coverage["coverage_sha256"],
                "status": coverage.get("status"),
                "deep_research_activation": coverage.get("deep_research_activation"),
                "subscription_leaf": coverage.get("subscription_leaf"),
                "source_checks": list(coverage.get("source_checks") or ()),
            },
            "source_epoch": {**source_epoch_body, "source_epoch_sha256": source_epoch_sha},
            "source_receipt_snapshot": epoch_rows,
            **(
                {"research_question_frontier": dict(question_frontier)}
                if isinstance(question_frontier, Mapping) else {}
            ),
            "matrix_policy_assignment": matrix_assignment,
            "acquisition": {
                "source_plan_sha256": plan["source_plan_sha256"],
                "source_batch_id": batch_id,
                "information_yield_class": batch.get("information_yield_class"),
                "coordinate_ids": list(batch.get("coordinate_ids") or ()),
                "document_families": list(batch.get("document_families") or ()),
                "configured_source_ids": list(batch.get("configured_source_ids") or ()),
                "downstream_contracts": list(batch.get("downstream_contracts") or ()),
                "typed_coordinate_contracts": coordinates,
            },
            "target_blockers": target_blockers,
            "required_agent_output": {
                "source_change_classification": [
                    "unchanged", "changed_thesis_immaterial", "changed_re_underwrite", "source_gap",
                ],
                "dossier_transport_recommendation": [
                    "compile_coverage_bridge", "re_underwrite", "source_gap",
                ],
                "typed_observations_required": list(batch.get("coordinate_ids") or ()),
                "research_question_atom_ids": list(
                    ((question_frontier or {}).get("selected_program") or {}).get("atom_ids") or ()
                ),
                "primary_sources_only_for_company_facts": True,
                "opened_https_documents_required": True,
            },
            "deterministic_postconditions": [
                "verify every source and observation identity",
                "compile or refuse the candidate-bound research coverage bridge",
                "run only declared coordinate derivations whose preconditions hold",
                "recompile the business fingerprint, strategy frontier, and equity proposal",
                "retain factor expected-return and state-price completeness gaps until their own kernels resolve them",
            ],
            "expected_exit": "validated_transport_and_typed_observations_or_typed_failure",
            "capital_authority": False,
            "proposal_mutation_allowed": False,
            "activation_allowed": False,
        }
        request = validate_equity_activation_request({
            **request_body, "request_sha256": stable_sha256(request_body),
        })
        coordinate_ids = set(batch.get("coordinate_ids") or ())
        question_frontier_sha = (
            str(question_frontier.get("question_frontier_sha256"))
            if isinstance(question_frontier, Mapping) else None
        )
        covering = _active_covering_jobs(
            queue_snapshot, candidate_leaf=str(row["candidate_leaf"]),
            prior_dossier_leaf=prior_dossier_leaf, batch_id=batch_id,
            coordinate_ids=coordinate_ids, source_epoch_sha256=source_epoch_sha,
            question_frontier_sha256=question_frontier_sha,
            matrix_policy_assignment_sha256=str(
                matrix_assignment["assignment_sha256"]
            ),
        )
        exact = [
            value for value in covering
            if (value.get("payload") or {}).get("question_frontier_sha256")
            == question_frontier_sha
            and (value.get("payload") or {}).get("matrix_policy_assignment_sha256")
            == matrix_assignment["assignment_sha256"]
        ]
        claimed = next(
            (value for value in covering if value.get("status") == "claimed"), None,
        )
        existing = claimed or (exact[0] if exact else None)
        work_id = (
            str(existing["work_id"]) if existing
            else f"investment-activation-research:{request['request_sha256'][:24]}"
        )
        status = f"joined_{existing['status']}" if existing else "ready_to_enqueue"
        job_body = {
            "schema": ACTIVATION_RESEARCH_JOB_SCHEMA,
            "work_id": work_id, "request_sha256": request["request_sha256"],
            "candidate_leaf": row["candidate_leaf"],
            "prior_dossier_leaf": prior_dossier_leaf,
            "entity_id": entity, "source_batch_id": batch_id,
            "coordinate_ids": sorted(coordinate_ids),
            "source_epoch_sha256": source_epoch_sha,
            "source_material_sha256": source_epoch_sha,
            "question_frontier_sha256": question_frontier_sha,
            "matrix_policy_assignment_sha256": matrix_assignment["assignment_sha256"],
            "coalesced_work_ids": [
                str(value["work_id"]) for value in covering
                if value is not existing and value.get("status") == "queued"
            ],
            "target_blockers": target_blockers,
            "stage": status, "required_capability": "subscription_web_research",
            "expected_exit": request["expected_exit"], "capital_authority": False,
        }
        jobs.append({**job_body, "job_sha256": stable_sha256(job_body)})
        requests.append(request)
    body = {
        "schema": "jaggedthoughts-equity-activation-research-batch-v1",
        "compiled_at": compiled, "equity_audit_sha256": audit_sha,
        "selection": selection, "request_count": len(requests),
        "joined_job_count": sum(job["stage"].startswith("joined_") for job in jobs),
        "ready_job_count": sum(job["stage"] == "ready_to_enqueue" for job in jobs),
        "matrix_policy_experiment": {
            "experiment_id": MATRIX_POLICY_EXPERIMENT,
            "arms": list(MATRIX_POLICY_ARMS),
            "eligible_pair_count": sum(
                assignment["eligible"] for assignment in matrix_assignments.values()
            ) // 2,
            "assigned_counts": {
                arm: sum(
                    assignment["eligible"] and assignment["arm_id"] == arm
                    for assignment in matrix_assignments.values()
                )
                for arm in MATRIX_POLICY_ARMS
            },
            "capital_authority": False,
        },
        "requests": requests, "jobs": jobs,
        "authority": "research_acquisition_compilation_only",
        "capital_authority": False,
    }
    return {**body, "batch_sha256": stable_sha256(body)}


def compile_workspace_equity_activation_research(
    workspace: str | Path, *, compiled_at: str | None = None,
) -> dict[str, Any]:
    """Read current candidate, coverage, source, and queue identities without writing them."""
    root = Path(workspace).expanduser().resolve()
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("investment workspace configuration must be an object")
    owner = require_text(config.get("owner"), "workspace owner")
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    record = json.loads((root / "discovery" / "latest_record.json").read_text(encoding="utf-8"))
    prerequisite_times = [str(discovery.get("as_of") or "")]
    for candidate in discovery.get("candidates") or ():
        if candidate.get("entity_kind") != "public_equity" or candidate.get("screen_status") != "qualified":
            continue
        leaf = str((record.get("candidate_leaves") or {}).get(candidate["candidate_id"]) or "")
        try:
            coverage_record = store.head(
                owner, "research_evidence_coverage", f"research-coverage:{leaf}",
            )
            prerequisite_times.append(str(coverage_record["available_at"]))
            prior_leaf = str((coverage_record.get("payload") or {}).get("prior_dossier_leaf") or "")
            if prior_leaf:
                prior = store.get_leaf(prior_leaf).get("payload") or {}
                if prior.get("generated_at"):
                    prerequisite_times.append(str(prior["generated_at"]))
        except KeyError:
            pass
    default_compiled = max(
        [*prerequisite_times, MATRIX_POLICY_EFFECTIVE_AT], key=timestamp_key,
    )
    compiled = canonical_timestamp(
        compiled_at or default_compiled
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "activation research compiled_at",
    )
    rows, plans, coverages, dossiers, epochs, strategy_questions = [], {}, {}, {}, {}, {}
    transfer_path = root / "institutional_learning" / "strategy_transfer" / "latest.json"
    strategy_transfer_index = (
        json.loads(transfer_path.read_text(encoding="utf-8"))
        if transfer_path.exists() else None
    )
    matrix_policy_path = root / "research_jobs" / "activation" / "matrix_policy" / "latest.json"
    matrix_policy_learning = (
        json.loads(matrix_policy_path.read_text(encoding="utf-8"))
        if matrix_policy_path.exists() else None
    )
    learning_credit_assignment = None
    current_pair_set = None
    if matrix_policy_learning is not None:
        read_model_path = root / "state" / "read_model.json"
        read_model = (
            json.loads(read_model_path.read_text(encoding="utf-8"))
            if read_model_path.exists() else {}
        )
        learning_credit_assignment = read_model.get("learning_credit_assignment")
        try:
            from .prospective_response_matrix import (
                compile_workspace_activation_matrix_policy_learning,
            )
            current_policy = compile_workspace_activation_matrix_policy_learning(
                root,
                compiled_at=str(matrix_policy_learning.get("compiled_at") or compiled),
                minimum_pairs=int(matrix_policy_learning.get("minimum_pairs") or 20),
            )
            current_pair_set = current_policy.get("eligible_pair_set_sha256")
        except (OSError, TypeError, ValueError):
            current_pair_set = None
        if (
            not current_pair_set
            or matrix_policy_learning.get("eligible_pair_set_sha256") != current_pair_set
        ):
            matrix_policy_learning = None
    receipts = current_monitor_receipts(root)
    manifest = load_source_manifest(
        root / str(config.get("source_manifest") or "sources.yaml")
    )
    source_by_id = {
        str(value.get("id") or ""): dict(value)
        for value in (manifest or {}).get("sources") or () if isinstance(value, Mapping)
    }
    for candidate in discovery.get("candidates") or ():
        if candidate.get("entity_kind") != "public_equity" or candidate.get("screen_status") != "qualified":
            continue
        entity = str(candidate["entity_id"]).upper()
        candidate_leaf = str((record.get("candidate_leaves") or {}).get(candidate["candidate_id"]) or "")
        try:
            store.head(owner, "candidate_research_dossier", f"research:{entity}:{candidate_leaf}")
            continue
        except KeyError:
            pass
        try:
            coverage_record = store.head(
                owner, "research_evidence_coverage", f"research-coverage:{candidate_leaf}",
            )
        except KeyError:
            continue
        coverage = dict(coverage_record.get("payload") or {})
        prior_leaf = str(coverage.get("prior_dossier_leaf") or "")
        if not prior_leaf:
            continue
        prior = store.get_leaf(prior_leaf).get("payload")
        if not isinstance(prior, Mapping):
            continue
        prior_frontier = _prior_strategy_frontier(root, {
            "candidate_identity": {"entity_id": entity},
            "prior_dossier_identity": {"dossier_sha256": prior.get("dossier_sha256")},
            "created_at": compiled,
        })
        if prior_frontier is not None:
            strategy_questions[entity] = compile_research_question_frontier(
                {**candidate, "candidate_leaf": candidate_leaf},
                arm_id="disagreement_first", strategy_frontier=prior_frontier,
                strategy_transfer_index=strategy_transfer_index,
            )
        coverage = {**coverage, "coverage_leaf": coverage_record["leaf_sha256"]}
        try:
            plan = compile_workspace_fingerprint_acquisition_plan(
                root, entity, compiled_at=compiled, source_manifest=manifest,
            )
        except ValueError as error:
            # A subscription result can commit after this projection's snapshot
            # timestamp.  Defer that entity; the next projection will bind it.
            if str(error) == "business fingerprint compilation precedes its research dossier":
                continue
            raise
        checks = {
            str(value.get("source_id") or ""): dict(value)
            for value in coverage.get("source_checks") or () if isinstance(value, Mapping)
        }
        epoch_rows = []
        for source_id in sorted({
            str(value) for batch in plan.get("acquisition_batches") or ()
            for value in batch.get("configured_source_ids") or ()
        }):
            receipt = dict(receipts.get(source_id) or {})
            source = source_by_id.get(source_id) or {}
            check = checks.get(source_id) or {}
            cik = re.sub(r"\D", "", str(source.get("cik") or ""))
            adapter = str(source.get("adapter") or "")
            configured_url = (
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"
                if cik and adapter == "sec_companyfacts" else
                f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
                if cik and adapter == "sec_submissions" else source.get("url")
            )
            epoch_rows.append({
                "source_id": source_id, "adapter": adapter,
                "source_config_sha256": stable_sha256(source),
                "canonical_url": receipt.get("canonical_url") or configured_url,
                "status": check.get("status") or ("current_receipt" if receipt else "not_observed"),
                "status_available_at": coverage.get("available_at"),
                "receipt_sha256": receipt.get("receipt_sha256") or check.get("receipt_sha256"),
                "content_sha256": receipt.get("content_sha256") or check.get("content_sha256"),
                "retrieved_at": receipt.get("retrieved_at"),
            })
        rows.append({
            "entity_id": entity, "candidate_leaf": candidate_leaf,
            "candidate_sha256": candidate.get("candidate_sha256"),
            "candidate_identity": {
                "candidate_id": candidate.get("candidate_id"), "as_of": candidate.get("as_of"),
                "rank": candidate.get("rank"), "research_rank": candidate.get("research_rank"),
                "screen_status": candidate.get("screen_status"),
            },
            "status": "evidence_blocked", "activation_eligible": False,
            "blockers": ["candidate_bound_research_dossier_absent"], "proposal": None,
        })
        plans[entity], coverages[entity], dossiers[entity], epochs[entity] = (
            plan, coverage, dict(prior), epoch_rows,
        )
    audit_body = {
        "schema": AUDIT_SCHEMA, "compiled_at": compiled,
        "discovery_run_sha256": discovery.get("run_sha256"),
        "qualified_candidate_count": sum(
            candidate.get("entity_kind") == "public_equity" and candidate.get("screen_status") == "qualified"
            for candidate in discovery.get("candidates") or ()
        ),
        "proposal_count": 0, "eligible_count": 0, "blocked_count": len(rows),
        "rows": rows, "authority": "paper_research_proposal_audit_only",
        "capital_authority": False, "portfolio_authority": False,
        "brokerage_authority": False,
    }
    audit = {**audit_body, "audit_sha256": stable_sha256(audit_body)}
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        queue_rows = work_queue.list_items(connection, limit=10_000)
    finally:
        connection.close()
    for row in queue_rows:
        if row.get("kind") != ACTIVATION_RESEARCH_JOB_KIND:
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict) or payload.get("source_material_sha256"):
            continue
        relative = str(payload.get("dossier_request_path") or "")
        if not relative:
            continue
        try:
            request = json.loads((root / relative).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        activation = request.get("activation_research") or {}
        epoch = activation.get("source_epoch") or {}
        material_body = {
            "candidate_leaf": payload.get("candidate_leaf"),
            "candidate_as_of": request.get("as_of"),
            "sources": _material_source_rows(epoch.get("sources") or ()),
        }
        payload["source_material_sha256"] = stable_sha256(material_body)
    return compile_equity_activation_research(
        equity_audit=audit, acquisition_plans=plans, coverages=coverages,
        source_epochs=epochs, prior_dossiers=dossiers,
        strategy_question_frontiers=strategy_questions, queue_rows=queue_rows,
        matrix_policy_learning=matrix_policy_learning,
        learning_credit_assignment=learning_credit_assignment,
        current_eligible_pair_set_sha256=current_pair_set,
        compiled_at=compiled,
    )


def _prior_strategy_frontier(
    root: Path, activation: Mapping[str, Any],
) -> dict[str, Any] | None:
    entity = str((activation.get("candidate_identity") or {}).get("entity_id") or "").upper()
    dossier_sha = str((activation.get("prior_dossier_identity") or {}).get("dossier_sha256") or "")
    created_at = str(activation.get("created_at") or "")
    directory = root / "strategy_frontiers" / "results"
    directory_epoch = directory.stat().st_mtime_ns if directory.exists() else -1
    rows = list(_strategy_frontiers_by_entity(
        str(directory), directory_epoch,
    ).get(entity, ()))
    rows = [row for row in rows if timestamp_key(
        str(row.get("evidence_epoch") or "")
    ) <= timestamp_key(created_at)]
    return max(rows, key=lambda row: (
        (row.get("company") or {}).get("source_dossier_sha256") == dossier_sha,
        timestamp_key(str(row["evidence_epoch"])),
        int(row.get("compiler_contract_version") or 0),
        str(row.get("strategy_frontier_sha256") or ""),
    ), default=None)


@lru_cache(maxsize=8)
def _strategy_frontiers_by_entity(
    directory: str, directory_epoch: int,
) -> dict[str, tuple[dict[str, Any], ...]]:
    """Parse one immutable frontier-directory epoch once."""

    del directory_epoch
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in Path(directory).glob("*.json"):
        try:
            frontier = json.loads(path.read_text(encoding="utf-8"))
            company = dict(frontier.get("company") or {})
            entity = str(company.get("id") or "").upper()
            if not entity:
                continue
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
        grouped.setdefault(entity, []).append(frontier)
    return {key: tuple(value) for key, value in grouped.items()}


def _dossier_request(
    store: GoldenStore, activation: Mapping[str, Any], job: Mapping[str, Any], *,
    strategy_frontier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_id = activation["candidate_identity"]
    candidate = store.get_leaf(str(candidate_id["candidate_leaf"])).get("payload") or {}
    expected = {
        "candidate_sha256": candidate_id["candidate_sha256"],
        "entity_id": candidate_id["entity_id"], "as_of": candidate_id["as_of"],
    }
    if {key: candidate.get(key) for key in expected} != expected:
        raise ValueError("activation adapter crossed its discovery candidate identity")
    source_refs = sorted({
        *[str(value) for value in candidate.get("source_refs") or ()],
        *[
            str(value.get("canonical_url"))
            for value in (activation.get("source_epoch") or {}).get("sources") or ()
            if isinstance(value, Mapping) and value.get("canonical_url")
        ],
    })
    embedded_question = activation.get("research_question_frontier")
    question_frontier = (
        dict(embedded_question) if isinstance(embedded_question, Mapping) else
        compile_research_question_frontier(
            {**candidate, "candidate_leaf": candidate_id["candidate_leaf"]},
            arm_id="disagreement_first", strategy_frontier=strategy_frontier,
        )
        if strategy_frontier is not None else None
    )
    body = {
        "schema": RESEARCH_REQUEST_SCHEMA,
        "request_id": f"research:{activation['request_id']}",
        "created_at": activation["created_at"],
        "job_id": job["work_id"],
        "job_sha256": stable_sha256({
            "work_id": job["work_id"],
            "activation_request_sha256": activation["request_sha256"],
        }),
        "cycle_sha256": activation["equity_audit_sha256"],
        "candidate_leaf": candidate_id["candidate_leaf"],
        "candidate_sha256": candidate_id["candidate_sha256"],
        "candidate_id": candidate.get("candidate_id"),
        "entity_id": candidate_id["entity_id"], "entity_kind": "public_equity",
        "as_of": candidate_id["as_of"], "screen_status": candidate.get("screen_status"),
        "rank": candidate_id.get("rank"),
        "research_rank": candidate_id.get("research_rank"),
        "potential_rank": candidate.get("potential_rank"),
        "rank_score": candidate.get("rank_score"),
        "requested_measurements": list(activation["acquisition"]["coordinate_ids"]),
        "source_refs": source_refs,
        "discovery_run_id": candidate.get("discovery_run_id"),
        "discovery_run_sha256": activation.get("discovery_run_sha256"),
        "required_skill": "jaggedthoughts-capital-research",
        "required_output_schema": "jaggedthoughts-candidate-research-dossier-v1",
        "research_mode": "candidate_epoch_transport_and_filing_disaggregation",
        **(
            {"research_question_frontier": question_frontier}
            if question_frontier is not None else {}
        ),
        "activation_research": {
            "request_sha256": activation["request_sha256"],
            "prior_dossier_identity": activation["prior_dossier_identity"],
            "coverage_identity": activation["coverage_identity"],
            "source_epoch": activation["source_epoch"],
            "acquisition": activation["acquisition"],
            "target_blockers": activation["target_blockers"],
        },
        "next_activation": "submit_current_candidate_dossier_or_source_gap",
        "capital_authority": False,
        "activation_boundary": (
            "The agent may compare the frozen dossier with current primary evidence and return "
            "a candidate-bound dossier or typed source gap. Paper activation and capital remain held."
        ),
    }
    return {**body, "request_sha256": stable_sha256(body)}


def enqueue_workspace_equity_activation_research(
    workspace: str | Path, *, max_attempts: int = 3,
) -> dict[str, Any]:
    """Materialize current requests and subscribe them to the shared lease queue."""
    root = Path(workspace).expanduser().resolve()
    try:
        batch = compile_workspace_equity_activation_research(root)
    except ValueError as error:
        if str(error) == "equity audit has no blocked candidate with reusable research lineage":
            return {
                "schema": "jaggedthoughts-equity-activation-research-enqueue-v1",
                "batch_sha256": None, "queued_count": 0, "reused_count": 0,
                "queued": [], "reused": [], "capital_authority": False,
            }
        raise
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    owner = require_text(config.get("owner"), "workspace owner")
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    queued, reused, coalesced = [], [], []
    try:
        def current_items() -> dict[str, dict[str, Any]]:
            return {
                str(row["work_id"]): row
                for row in work_queue.list_items(connection, limit=10_000)
            }

        def covered_owner_available(
            row: Mapping[str, Any], rows: Mapping[str, Mapping[str, Any]],
        ) -> bool:
            seen: set[str] = set()
            current = row
            while True:
                work_id = str(current.get("work_id") or "")
                if not work_id or work_id in seen:
                    return False
                seen.add(work_id)
                status = str(current.get("status") or "")
                if status in {"queued", "claimed"}:
                    return True
                payload = current.get("payload") or {}
                if status != "done":
                    return False
                stage = str(payload.get("stage") or "")
                if stage != "covered_by_equivalent_active_request":
                    return stage in {"researched", "source_gap", "evidence_quarantined"}
                target = str(payload.get("coalesced_into_work_id") or "")
                successor = rows.get(target)
                if successor is None:
                    return False
                current = successor

        existing = {
            str(row["work_id"]): row for row in work_queue.list_items(connection, limit=10_000)
        }
        equivalent: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for row in existing.values():
            payload = row.get("payload") or {}
            if row.get("kind") != ACTIVATION_RESEARCH_JOB_KIND or row.get("status") != "queued":
                continue
            basis = (
                payload.get("candidate_leaf"), payload.get("prior_dossier_leaf"),
                payload.get("source_batch_id"),
                payload.get("source_material_sha256") or payload.get("source_epoch_sha256"),
                tuple(sorted(payload.get("coordinate_ids") or ())),
                payload.get("question_frontier_sha256"),
                payload.get("matrix_policy_assignment_sha256"),
            )
            if all(basis[:4]):
                equivalent.setdefault(basis, []).append(row)
        for rows in equivalent.values():
            ordered = sorted(rows, key=lambda row: str(row.get("work_id") or ""))
            owner_work_id = str(ordered[0]["work_id"])
            for duplicate in ordered[1:]:
                duplicate_id = str(duplicate["work_id"])
                worker_id = "investment-activation-research-coalescer"
                if not work_queue.claim_specific(
                    connection, work_id=duplicate_id, worker_id=worker_id, lease_s=60,
                ):
                    continue
                update = {
                    "stage": "covered_by_equivalent_active_request",
                    "result_status": "covered_by_equivalent_active_request",
                    "completed_at": batch["compiled_at"], "provider_called": False,
                    "coalesced_into_work_id": owner_work_id,
                }
                work_queue.heartbeat(
                    connection, work_id=duplicate_id, worker_id=worker_id,
                    lease_s=60, payload_update=update,
                )
                if work_queue.finish_specific(
                    connection, work_id=duplicate_id, worker_id=worker_id, done=True,
                ):
                    coalesced.append(duplicate_id)
        existing = current_items()
        jobs = {str(row["entity_id"]): row for row in batch["jobs"]}
        for raw in batch["requests"]:
            request = validate_equity_activation_request(raw)
            entity = str(request["candidate_identity"]["entity_id"])
            compiled_job = jobs[entity]
            work_id = str(compiled_job["work_id"])
            dossier_request = _dossier_request(
                store, request, compiled_job,
                strategy_frontier=_prior_strategy_frontier(root, request),
            )
            target_snapshot = existing.get(work_id)
            duplicate_ids = (
                compiled_job.get("coalesced_work_ids") or ()
                if target_snapshot is None
                or target_snapshot.get("status") in {"queued", "claimed"}
                else ()
            )
            for duplicate_id in duplicate_ids:
                duplicate = existing.get(str(duplicate_id))
                if not duplicate or duplicate.get("status") != "queued":
                    continue
                worker_id = "investment-activation-research-coalescer"
                if not work_queue.claim_specific(
                    connection, work_id=str(duplicate_id), worker_id=worker_id,
                    lease_s=60,
                ):
                    continue
                update = {
                    "stage": "covered_by_equivalent_active_request",
                    "result_status": "covered_by_equivalent_active_request",
                    "completed_at": batch["compiled_at"], "provider_called": False,
                    "coalesced_into_work_id": work_id,
                }
                work_queue.heartbeat(
                    connection, work_id=str(duplicate_id), worker_id=worker_id,
                    lease_s=60, payload_update=update,
                )
                if work_queue.finish_specific(
                    connection, work_id=str(duplicate_id), worker_id=worker_id,
                    done=True,
                ):
                    coalesced.append(str(duplicate_id))
            existing = current_items()
            prior = existing.get(work_id)
            if (
                prior
                and prior.get("status") == "done"
                and (prior.get("payload") or {}).get("stage")
                == "covered_by_equivalent_active_request"
                and not covered_owner_available(prior, existing)
            ):
                connection.execute(
                    "UPDATE work_items SET status='failed', claimed_by=NULL, "
                    "lease_until=NULL, updated_at=strftime('%s','now') WHERE work_id=?",
                    (work_id,),
                )
                connection.commit()
                prior = None
            if prior and prior.get("status") not in {"failed", "retired", "dead_letter"}:
                priority = research_rank_priority(dossier_request)
                if prior.get("status") == "queued":
                    work_queue.update_status(
                        connection, work_id=work_id, status="queued",
                        payload_update={
                            "rank": dossier_request.get("rank"),
                            "research_rank": dossier_request.get("research_rank"),
                            "potential_rank": dossier_request.get("potential_rank"),
                        },
                    )
                    connection.execute(
                        "UPDATE work_items SET priority=? WHERE work_id=? AND status='queued'",
                        (priority, work_id),
                    )
                    connection.commit()
                reused.append({
                    "work_id": work_id, "entity_id": entity,
                    "status": prior.get("status"), "priority": priority,
                })
                continue
            frozen_request_leaves = [
                store.get_leaf(str(row["leaf_sha256"]))
                for row in store.list_leaves(
                    owner=owner, object_kind="agent_research_request", limit=10_000,
                )
                if row.get("object_id") == dossier_request["request_id"]
                and row.get("available_at") == dossier_request["created_at"]
            ]
            if len(frozen_request_leaves) > 1:
                raise ValueError("activation dossier adapter has competing frozen requests")
            if frozen_request_leaves:
                frozen = frozen_request_leaves[0].get("payload") or {}
                if frozen.get("candidate_leaf") != dossier_request.get("candidate_leaf"):
                    raise ValueError("activation frozen request crossed its candidate identity")
                dossier_request = dict(frozen)
            activation_path = root / "research_jobs" / "activation" / "requests" / (
                f"{request['request_sha256']}.json"
            )
            dossier_path = root / "research_jobs" / "requests" / (
                f"{entity.lower()}-{str(dossier_request['candidate_sha256'])[:12]}-"
                f"{str(dossier_request['request_sha256'])[:12]}.json"
            )
            _immutable_json(activation_path, request)
            _immutable_json(dossier_path, dossier_request)
            request_leaves = [
                str(row["leaf_sha256"])
                for row in store.list_leaves(owner=owner, object_kind="agent_research_request", limit=10_000)
                if (store.get_leaf(str(row["leaf_sha256"])).get("payload") or {}).get(
                    "request_sha256"
                ) == dossier_request["request_sha256"]
            ]
            if len(request_leaves) > 1:
                raise ValueError("activation dossier adapter has multiple golden request leaves")
            request_leaf = request_leaves[0] if request_leaves else record_agent_research_request(
                store, owner=owner, request=dossier_request,
            )
            job_body = {
                "schema": ACTIVATION_RESEARCH_JOB_SCHEMA,
                "work_id": work_id, "request_sha256": request["request_sha256"],
                "request_path": activation_path.relative_to(root).as_posix(),
                "dossier_request_sha256": dossier_request["request_sha256"],
                "dossier_request_path": dossier_path.relative_to(root).as_posix(),
                "dossier_request_leaf": request_leaf,
                "candidate_leaf": dossier_request["candidate_leaf"],
                "rank": dossier_request.get("rank"),
                "research_rank": dossier_request.get("research_rank"),
                "potential_rank": dossier_request.get("potential_rank"),
                "prior_dossier_leaf": request["prior_dossier_identity"]["dossier_leaf"],
                "entity_id": entity,
                "source_batch_id": request["acquisition"]["source_batch_id"],
                "coordinate_ids": list(request["acquisition"]["coordinate_ids"]),
                "source_epoch_sha256": request["source_epoch"]["source_epoch_sha256"],
                "source_material_sha256": request["source_epoch"]["source_epoch_sha256"],
                "question_frontier_sha256": (
                    (request.get("research_question_frontier") or {}).get(
                        "question_frontier_sha256"
                    )
                ),
                "matrix_policy_assignment_sha256": (
                    request.get("matrix_policy_assignment") or {}
                ).get("assignment_sha256"),
                "target_blockers": request["target_blockers"],
                "stage": "queued", "required_capability": "subscription_web_research",
                "expected_exit": request["expected_exit"], "capital_authority": False,
            }
            job = {**job_body, "job_sha256": stable_sha256(job_body)}
            priority = research_rank_priority(dossier_request)
            work_queue.enqueue(
                connection, kind=ACTIVATION_RESEARCH_JOB_KIND, priority=priority,
                max_attempts=max_attempts, payload=job,
            )
            queued.append({
                "work_id": work_id, "entity_id": entity,
                "status": "queued", "priority": priority,
            })
            work_queue.append_event(
                str(root / "research_jobs" / "agent" / "events.jsonl"),
                {"event_type": "investment_activation_research_enqueued", "payload": job},
            )
    finally:
        connection.close()
    return {
        "schema": "jaggedthoughts-equity-activation-research-enqueue-v1",
        "batch_sha256": batch["batch_sha256"],
        "queued_count": len(queued), "reused_count": len(reused),
        "coalesced_count": len(coalesced),
        "queued": queued, "reused": reused, "coalesced_work_ids": coalesced,
        "next_automatic_transition": "shared_subscription_consumer_claim",
        "capital_authority": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(compile_workspace_equity_activation_research(
        args.workspace,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACTIVATION_RESEARCH_JOB_KIND", "ACTIVATION_RESEARCH_JOB_SCHEMA",
    "ACTIVATION_RESEARCH_REQUEST_SCHEMA", "activation_matrix_policy_assignment",
    "ALL_MATRIX_POLICY_ARMS",
    "compile_equity_activation_research",
    "MATRIX_POLICY_ARMS", "MATRIX_POLICY_ASSIGNMENT_SCHEMA",
    "MATRIX_POLICY_EFFECTIVE_AT", "MATRIX_POLICY_EXPERIMENT",
    "MATRIX_POLICY_LEARNING_SCHEMA",
    "compile_workspace_equity_activation_research",
    "enqueue_workspace_equity_activation_research",
    "validate_equity_activation_request",
]
