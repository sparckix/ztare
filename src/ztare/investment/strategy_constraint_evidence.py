"""Independent public-evidence challenge for strategy feasibility predicates."""

from __future__ import annotations

import json
from pathlib import Path
import re
import time
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

from ztare.common.equivariance import stable_sha256
from ztare.common.information_yield_pricing import price_experiment
from ztare.leanmill import work_queue

from .contracts import canonical_timestamp, require_text, timestamp_key
from .strategy_constraint_challenge import (
    REQUEST_SCHEMA as CHALLENGE_REQUEST_SCHEMA,
    RUNTIME_PROVENANCE_SCHEMA,
    compile_strategy_constraint_frontier_gate,
    strategy_constraint_predicate_permits,
)


REQUEST_SCHEMA = "jaggedthoughts-strategy-constraint-evidence-request-v1"
PROPOSAL_SCHEMA = "jaggedthoughts-strategy-constraint-evidence-proposal-v1"
RESULT_SCHEMA = "jaggedthoughts-strategy-constraint-evidence-result-v1"
JOB_SCHEMA = "jaggedthoughts-strategy-constraint-evidence-job-v1"
JOB_KIND = "jaggedthoughts_strategy_constraint_evidence_research"
MIN_COMPETING_EFFECTS = 2


def _intact(row: Mapping[str, Any], hash_field: str) -> bool:
    return row.get(hash_field) == stable_sha256({
        key: value for key, value in row.items() if key != hash_field
    })


def strategy_source_identity(url: str) -> str:
    parsed = urlsplit(url)
    normalized = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))
    accession = re.search(r"/Archives/edgar/data/\d+/(\d{18})/", parsed.path)
    return f"sec-accession:{accession.group(1)}" if accession else normalized.rstrip("/")


def strategy_constraint_evidence_readiness(
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Separate singleton falsification from competing-rule discrimination."""
    rows = list(candidates)
    effects = {
        str(row.get("predicate_effect_sha256") or "") for row in rows
    } - {""}
    has_candidate = bool(rows and effects)
    competing = len(effects) >= MIN_COMPETING_EFFECTS
    return {
        "status": (
            "competing_candidate_discrimination" if competing else
            "single_candidate_falsification" if has_candidate else
            "candidate_expansion_required"
        ),
        "candidate_predicate_count": len(rows),
        "candidate_effect_count": len(effects),
        "minimum_competing_effect_count": MIN_COMPETING_EFFECTS,
        "next_action": (
            "run_candidate_blind_source_disjoint_replay" if has_candidate else
            "acquire_behaviorally_distinct_source_supported_predicates"
        ),
        "subscription_call_eligible": has_candidate,
        "institutional_law_eligible": competing,
        "capital_authority": False,
    }


def _holdout_visible_projection(request: Mapping[str, Any]) -> dict[str, Any]:
    visible = {key: request[key] for key in (
        "request_sha256", "entity_id", "option_vocabulary",
        "source_embargo_sha256", "evidence_cutoff",
    )}
    visible["probe_bundles"] = [
        {"option_ids": row["option_ids"]}
        for row in (request.get("probe_frontier") or {}).get("targets") or ()
    ]
    return visible


def _constraint_probe_frontier(
    parent: Mapping[str, Any], predicates: list[Mapping[str, Any]],
) -> dict[str, Any]:
    committee: list[Mapping[str, Any] | None] = [None, *predicates]
    rows = []
    for raw in (parent.get("choice_space_certificate") or {}).get("feasible_bundles") or ():
        option_ids = sorted(map(str, raw.get("option_ids") or ()))
        priced = price_experiment(
            committee,
            lambda predicate: (
                True if predicate is None
                else strategy_constraint_predicate_permits(predicate, option_ids)
            ),
            lambda _: 1,
            novel_context=False,
        )
        predictions = [
            True if predicate is None
            else strategy_constraint_predicate_permits(predicate, option_ids)
            for predicate in committee
        ]
        if len(set(predictions)) < 2:
            continue
        rows.append({
            "option_ids": option_ids,
            "committee_permits_count": sum(predictions),
            "committee_rejects_count": len(predictions) - sum(predictions),
            "identification_upper_bound": round(priced.identification, 8),
            "compression_upper_bound": round(priced.compression_gain, 8),
        })
    rows.sort(key=lambda row: (
        -row["identification_upper_bound"], -row["compression_upper_bound"],
        len(row["option_ids"]), row["option_ids"],
    ))
    body = {
        "schema": "jaggedthoughts-strategy-constraint-probe-frontier-v1",
        "committee_size": len(committee),
        "includes_parent_null": True,
        "informative_bundle_count": len(rows),
        "targets": rows[:8],
        "selection_rule": "max_information_then_compression_then_minimum_bundle_size",
        "authority": "holdout_search_target_only",
        "capital_authority": False,
    }
    return {**body, "probe_frontier_sha256": stable_sha256(body)}


def compile_strategy_constraint_evidence_request(
    parent: Mapping[str, Any], diagnostic_gate: Mapping[str, Any], *,
    parent_path: str, entity_id: str, dossier_sha256: str,
    option_vocabulary: list[Mapping[str, Any]],
    forbidden_sources: list[Mapping[str, Any]],
    candidate_call_receipt_sha256: str,
    candidate_freeze: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze a blind, source-disjoint search for observed choice combinations."""
    challenge = diagnostic_gate.get("challenge_request") or {}
    if not _intact(parent, "strategy_frontier_sha256"):
        raise ValueError("constraint evidence parent frontier identity is invalid")
    frozen_candidates = dict(candidate_freeze or {})
    if frozen_candidates:
        if (
            frozen_candidates.get("schema")
            != "jaggedthoughts-strategy-constraint-candidate-freeze-v1"
            or not _intact(frozen_candidates, "candidate_freeze_sha256")
            or frozen_candidates.get("parent_strategy_frontier_sha256")
            != parent.get("strategy_frontier_sha256")
        ):
            raise ValueError("constraint evidence candidate freeze identity is invalid")
    elif (
        challenge.get("schema") != CHALLENGE_REQUEST_SCHEMA
        or not _intact(challenge, "request_sha256")
        or challenge.get("parent_strategy_frontier_sha256")
        != parent.get("strategy_frontier_sha256")
    ):
        raise ValueError("constraint evidence requires a candidate freeze or challenge")
    receipt = require_text(
        frozen_candidates.get("candidate_call_receipt_sha256")
        or candidate_call_receipt_sha256,
        "constraint candidate call receipt",
    )
    if len(receipt) != 64 or any(character not in "0123456789abcdef" for character in receipt):
        raise ValueError("constraint candidate call receipt must be a sha256")
    option_ids = set(map(str, (parent.get("choice_space_certificate") or {}).get("option_ids") or ()))
    options = sorted(({
        "option_id": require_text(row.get("option_id"), "constraint option id"),
        "description": require_text(row.get("description"), "constraint option description"),
    } for row in option_vocabulary), key=lambda row: row["option_id"])
    if {row["option_id"] for row in options} != option_ids:
        raise ValueError("constraint evidence option vocabulary differs from its parent")
    all_forbidden = list(forbidden_sources)
    forbidden = sorted(({
        "source_id": require_text(row.get("source_id"), "forbidden source id"),
        "url": (url := require_text(row.get("url"), "forbidden source url")),
        "source_identity": row.get("source_identity") or strategy_source_identity(url),
    } for row in all_forbidden), key=lambda row: (row["source_id"], row["url"]))
    predicates = list(
        frozen_candidates.get("candidate_predicates") or challenge["candidate_predicates"]
    )
    readiness = strategy_constraint_evidence_readiness(predicates)
    if not readiness["subscription_call_eligible"]:
        raise ValueError(
            "constraint evidence requires at least one non-vacuous behavioral predicate"
        )
    probe_frontier = _constraint_probe_frontier(parent, predicates)
    embargo_sha = stable_sha256(sorted({row["source_identity"] for row in forbidden}))
    body = {
        "schema": REQUEST_SCHEMA,
        "request_id": (
            "strategy-constraint-evidence:"
            f"{str(frozen_candidates.get('candidate_freeze_sha256') or challenge['request_sha256'])[:24]}"
        ),
        "entity_id": require_text(entity_id, "constraint evidence entity"),
        "source_dossier_sha256": require_text(dossier_sha256, "constraint evidence dossier"),
        "parent_strategy_frontier_sha256": parent["strategy_frontier_sha256"],
        "parent_path": require_text(parent_path, "constraint evidence parent path"),
        "diagnostic_gate_sha256": require_text(
            diagnostic_gate.get("gate_sha256"), "diagnostic constraint gate",
        ),
        "diagnostic_challenge_request_sha256": challenge.get("request_sha256"),
        "candidate_predicates": predicates,
        "evidence_mode": readiness["status"],
        "institutional_law_eligible_if_accepted": readiness[
            "institutional_law_eligible"
        ],
        "probe_frontier": probe_frontier,
        "candidate_predicate_sha256s": [
            row["predicate_sha256"] for row in predicates
        ],
        "candidate_freeze_sha256": frozen_candidates.get("candidate_freeze_sha256"),
        "candidate_semantics_set_sha256": frozen_candidates.get(
            "candidate_semantics_set_sha256"
        ) or stable_sha256(sorted(
            str(row.get("predicate_semantics_sha256") or "") for row in predicates
        )),
        "candidate_effect_set_sha256": frozen_candidates.get(
            "candidate_effect_set_sha256"
        ),
        "candidate_call_receipt_sha256": receipt,
        "candidate_source_family_ids": list(
            frozen_candidates.get("candidate_source_family_ids")
            or sorted({row["source_identity"] for row in forbidden})
        ),
        "candidate_frozen_at": (
            frozen_candidates.get("available_at") or challenge.get("available_at")
        ),
        "option_vocabulary": options,
        "forbidden_sources": forbidden,
        "source_embargo_sha256": embargo_sha,
        "evidence_cutoff": str(
            frozen_candidates.get("available_at") or challenge["available_at"]
        ),
        "required_capability": "subscription_strategy_constraint_evidence",
        "expected_exit": "candidate_blind_source_disjoint_replay",
        "research_claim_authority": False,
        "capital_authority": False,
    }
    return {**body, "request_sha256": stable_sha256(body)}


def validate_strategy_constraint_evidence_request(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = require_text(body.pop("request_sha256", ""), "constraint evidence request hash")
    if body.get("schema") != REQUEST_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("constraint evidence request identity is invalid")
    return {**body, "request_sha256": declared}


def strategy_constraint_evidence_output_schema(request_sha256: str) -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    evidence_refs = {"type": "array", "minItems": 1, "items": text}
    bundle = {
        "type": "object",
        "properties": {
            "example_id": text,
            "option_ids": {"type": "array", "minItems": 1, "items": text},
            "evidence_refs": evidence_refs,
        },
        "required": ["example_id", "option_ids", "evidence_refs"],
        "additionalProperties": False,
    }
    implication = {
        "type": "object",
        "properties": {
            "example_id": text,
            "antecedent_option_ids": {"type": "array", "minItems": 1, "items": text},
            "required_option_ids": {"type": "array", "minItems": 1, "items": text},
            "evidence_refs": evidence_refs,
        },
        "required": [
            "example_id", "antecedent_option_ids", "required_option_ids", "evidence_refs",
        ],
        "additionalProperties": False,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "schema": {"type": "string", "const": PROPOSAL_SCHEMA},
            "request_sha256": {"type": "string", "const": request_sha256},
            "sources": {
                "type": "array", "items": {
                    "type": "object",
                    "properties": {"url": text, "title": text, "published_at": text},
                    "required": ["url", "title", "published_at"],
                    "additionalProperties": False,
                },
            },
            "admitted_bundles": {"type": "array", "items": bundle},
            "excluded_bundles": {"type": "array", "items": bundle},
            "implication_pairs": {"type": "array", "items": implication},
            "residual": text,
        },
        "required": [
            "schema", "request_sha256", "sources", "admitted_bundles",
            "excluded_bundles", "implication_pairs", "residual",
        ],
        "additionalProperties": False,
    }


def render_strategy_constraint_evidence_prompt(request: Mapping[str, Any]) -> str:
    frozen = validate_strategy_constraint_evidence_request(request)
    readiness = strategy_constraint_evidence_readiness(
        frozen.get("candidate_predicates") or ()
    )
    if not readiness["subscription_call_eligible"]:
        raise ValueError(
            "constraint evidence request cannot spend a subscription call without a "
            "non-vacuous behavioral predicate"
        )
    visible = _holdout_visible_projection(frozen)
    return (
        "Find public primary evidence for observed combinations of the exact strategy "
        "options below. Do not infer combinations from descriptions. Return admitted "
        "bundles only when a source shows the options operating together; excluded "
        "bundles only when a source says the combination was rejected or impossible; "
        "and implications only when a source states the prerequisite. The kernel will "
        "reject evidence from the embargoed prior information families; those sources "
        "are intentionally hidden from you. A valid discriminator needs at "
        "least one admitted bundle and either an excluded bundle or implication. "
        "Use only primary sources published after the evidence cutoff. Empty arrays are "
        "correct when source-disjoint evidence is absent. Start with the exact probe "
        "bundles selected from the parent Z3-feasible space, then report any other exact "
        "observed combinations. Do not propose or select "
        "a predicate, value a security, rank it, or allocate capital. Return only the "
        "requested JSON.\n\nFROZEN BLIND ASSIGNMENT:\n"
        + json.dumps(visible, indent=2, sort_keys=True)
    )


def _candidate_constraints(predicates: list[Mapping[str, Any]]) -> dict[str, Any]:
    grouped = {"incompatibilities": [], "prerequisites": [], "resources": []}
    for predicate in predicates:
        key = {
            "incompatibility": "incompatibilities",
            "prerequisite": "prerequisites",
            "resource_limit": "resources",
        }[str(predicate["predicate_kind"])]
        grouped[key].append({
            field: value for field, value in predicate.items()
            if field not in {"predicate_kind", "predicate_sha256"}
        })
    return grouped


def compile_strategy_constraint_evidence_result(
    request: Mapping[str, Any], proposal: Mapping[str, Any], parent: Mapping[str, Any], *,
    accepted_at: str, provider_result_provenance: Mapping[str, Any],
    source_captures: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    frozen = validate_strategy_constraint_evidence_request(request)
    raw = dict(proposal)
    if raw.get("schema") != PROPOSAL_SCHEMA or raw.get("request_sha256") != frozen["request_sha256"]:
        raise ValueError("constraint evidence proposal identity is invalid")
    available = canonical_timestamp(accepted_at, "constraint evidence accepted_at")
    if timestamp_key(available) < timestamp_key(str(frozen["evidence_cutoff"])):
        raise ValueError("constraint evidence predates its frozen cutoff")
    provenance = dict(provider_result_provenance)
    provenance_sha = require_text(
        provenance.pop("provenance_sha256", ""), "constraint evidence provider provenance",
    )
    if stable_sha256(provenance) != provenance_sha:
        raise ValueError("constraint evidence provider provenance is invalid")
    holdout_receipt = require_text(
        provenance.get("call_receipt_sha256"), "constraint holdout call receipt",
    )
    option_ids = {row["option_id"] for row in frozen["option_vocabulary"]}
    forbidden = {
        str(value) for row in frozen["forbidden_sources"]
        for value in (row["source_id"], row["url"], row["source_identity"])
    }
    captures_by_url: dict[str, dict[str, Any]] = {}
    for raw_capture in source_captures:
        capture = dict(raw_capture)
        if (
            capture.get("schema") != "jaggedthoughts-sec-filing-url-capture-v1"
            or not _intact(capture, "capture_sha256")
            or capture.get("publication_time_authority")
            != "sec_provider_acceptance_time"
        ):
            raise ValueError("constraint evidence source capture is invalid")
        capture_url = require_text(capture.get("source_url"), "captured source url")
        if not strategy_source_identity(capture_url).startswith("sec-accession:"):
            raise ValueError("constraint evidence capture is not an SEC accession")
        digest = require_text(capture.get("content_sha256"), "captured source content hash")
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("constraint evidence source capture lacks a content sha256")
        canonical_timestamp(capture.get("accepted_at"), "captured source accepted_at")
        if capture_url in captures_by_url:
            raise ValueError("constraint evidence source capture is duplicated")
        captures_by_url[capture_url] = capture
    normalized_sources = []
    for row in raw.get("sources") or ():
        url = require_text(row.get("url"), "constraint evidence source url")
        capture = captures_by_url.get(url)
        published = canonical_timestamp(
            capture.get("accepted_at") if capture else row.get("published_at"),
            "constraint evidence source published_at",
        )
        if timestamp_key(published) <= timestamp_key(str(frozen["evidence_cutoff"])):
            raise ValueError("constraint holdout source is not post-freeze")
        normalized_sources.append({
            **dict(row), "url": url, "published_at": published,
            "source_identity": strategy_source_identity(url),
            "source_capture_sha256": (capture or {}).get("capture_sha256"),
            "publication_time_authority": (
                (capture or {}).get("publication_time_authority") or "model_reported"
            ),
        })
    source_urls = sorted({row["url"] for row in normalized_sources})
    if any(
        not url.startswith("https://")
        or url in forbidden
        or strategy_source_identity(url) in forbidden
        for url in source_urls
    ):
        raise ValueError("constraint holdout source is forbidden or non-HTTPS")

    def refs(row: Mapping[str, Any]) -> list[str]:
        values = sorted({
            require_text(value, "constraint example evidence ref")
            for value in row.get("evidence_refs") or ()
        })
        if not values or not set(values) <= set(source_urls):
            raise ValueError("constraint example cites outside its independent sources")
        return values

    def bundle(row: Mapping[str, Any], field: str) -> list[str]:
        values = sorted({require_text(value, "constraint example option") for value in row[field]})
        if not values or not set(values) <= option_ids:
            raise ValueError("constraint example crosses the frozen option vocabulary")
        return values

    admitted = [{"option_ids": bundle(row, "option_ids"), "evidence_refs": refs(row)}
                for row in raw.get("admitted_bundles") or ()]
    excluded = [{"option_ids": bundle(row, "option_ids"), "evidence_refs": refs(row)}
                for row in raw.get("excluded_bundles") or ()]
    implications = [{
        "antecedent_option_ids": bundle(row, "antecedent_option_ids"),
        "required_option_ids": bundle(row, "required_option_ids"),
        "evidence_refs": refs(row),
    } for row in raw.get("implication_pairs") or ()]
    has_discriminator = bool(admitted and (excluded or implications))
    gate = None
    if has_discriminator:
        runtime_body = {
            "schema": RUNTIME_PROVENANCE_SCHEMA,
            "authority": "worker_verified_subscription_receipts",
            "candidate_call_receipt_sha256": frozen["candidate_call_receipt_sha256"],
            "example_call_receipt_sha256": holdout_receipt,
            "candidate_source_family_ids": frozen["candidate_source_family_ids"],
            "example_source_family_ids": sorted({
                strategy_source_identity(url) for url in source_urls
            }),
            "candidate_semantics_set_sha256": frozen[
                "candidate_semantics_set_sha256"
            ],
            "candidate_freeze_sha256": frozen.get("candidate_freeze_sha256"),
            "candidate_frozen_at": frozen["candidate_frozen_at"],
            "holdout_completed_at": available,
            "holdout_predicates_hidden": True,
            "example_source_receipts_verified": bool(source_urls) and set(
                source_urls
            ) <= set(captures_by_url),
            "holdout_visible_projection_sha256": stable_sha256(
                _holdout_visible_projection(frozen)
            ),
            "holdout_request_sha256": frozen["request_sha256"],
        }
        runtime = {**runtime_body, "provenance_sha256": stable_sha256(runtime_body)}
        examples = {
            "admitted_bundles": [row["option_ids"] for row in admitted],
            "excluded_bundles": [row["option_ids"] for row in excluded],
            "implication_pairs": [{
                "antecedent_option_ids": row["antecedent_option_ids"],
                "required_option_ids": row["required_option_ids"],
            } for row in implications],
            "evidence_provenance": {"example_source_ids": source_urls},
        }
        candidate_sources = sorted({
            str(ref) for row in frozen["candidate_predicates"]
            for ref in row.get("evidence_refs") or ()
        })
        gate = compile_strategy_constraint_frontier_gate(
            parent,
            candidate_constraints=_candidate_constraints(frozen["candidate_predicates"]),
            examples=examples, source_ids=[*candidate_sources, *source_urls],
            observed_at=available, available_at=available,
            runtime_provenance=runtime,
        )
    body = {
        "schema": RESULT_SCHEMA,
        "request_sha256": frozen["request_sha256"],
        "entity_id": frozen["entity_id"],
        "parent_strategy_frontier_sha256": frozen["parent_strategy_frontier_sha256"],
        "accepted_at": available,
        "status": "replayed" if gate else "no_independent_discriminator",
        "sources": sorted(normalized_sources, key=stable_sha256),
        "source_capture_sha256s": sorted(
            str(row["capture_sha256"]) for row in captures_by_url.values()
        ),
        "examples": {
            "admitted_bundles": admitted, "excluded_bundles": excluded,
            "implication_pairs": implications,
        },
        "strategy_constraint_gate": gate,
        "evidence_grade": (gate or {}).get("evidence_grade", "insufficient"),
        "research_claim_eligible": bool((gate or {}).get("research_claim_eligible")),
        "residual": require_text(raw.get("residual"), "constraint evidence residual"),
        "provider_result_provenance": {**provenance, "provenance_sha256": provenance_sha},
        "research_claim_authority": False,
        "capital_authority": False,
    }
    return {**body, "result_sha256": stable_sha256(body)}


def validate_strategy_constraint_evidence_result(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = require_text(body.pop("result_sha256", ""), "constraint evidence result hash")
    if body.get("schema") != RESULT_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("constraint evidence result identity is invalid")
    return {**body, "result_sha256": declared}


def enqueue_strategy_constraint_evidence_request(
    workspace: str | Path, request: Mapping[str, Any], *, max_attempts: int = 3,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    frozen = validate_strategy_constraint_evidence_request(request)
    readiness = strategy_constraint_evidence_readiness(
        frozen.get("candidate_predicates") or ()
    )
    if not readiness["subscription_call_eligible"]:
        raise ValueError(
            "constraint evidence request cannot spend a subscription call without a "
            "non-vacuous behavioral predicate"
        )
    request_path = root / "research_jobs" / "strategy_constraint_evidence" / "requests" / (
        f"{frozen['request_sha256']}.json"
    )
    request_path.parent.mkdir(parents=True, exist_ok=True)
    if not request_path.exists():
        temporary = request_path.with_name(f".{request_path.name}.tmp")
        temporary.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(request_path)
    work_id = f"investment-strategy-constraint-evidence:{frozen['request_sha256'][:24]}"
    predicates = list(frozen.get("candidate_predicates") or ())
    parent_path = (root / frozen["parent_path"]).resolve()
    if root not in parent_path.parents:
        raise ValueError("constraint evidence parent path escapes its workspace")
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    parent_feasible_count = int(
        (parent.get("choice_space_certificate") or {}).get("feasible_bundle_count") or 0
    )
    job_body = {
        "schema": JOB_SCHEMA, "work_id": work_id,
        "request_sha256": frozen["request_sha256"],
        "request_path": request_path.relative_to(root).as_posix(),
        "entity_id": frozen["entity_id"], "stage": "queued",
        "source_dossier_sha256": frozen["source_dossier_sha256"],
        "parent_strategy_frontier_sha256": frozen["parent_strategy_frontier_sha256"],
        "candidate_freeze_sha256": frozen.get("candidate_freeze_sha256"),
        "candidate_predicate_count": len(predicates),
        "candidate_effect_count": len({
            str(row.get("predicate_effect_sha256") or "") for row in predicates
        } - {""}),
        "evidence_mode": frozen.get("evidence_mode"),
        "institutional_law_eligible_if_accepted": bool(
            frozen.get("institutional_law_eligible_if_accepted")
        ),
        "candidate_rejected_parent_bundle_counts": [
            int(row.get("rejected_parent_bundle_count") or 0) for row in predicates
        ],
        "parent_feasible_bundle_count": parent_feasible_count,
        "candidate_source_family_count": len(
            set(map(str, frozen.get("candidate_source_family_ids") or ()))
        ),
        "frozen_chain_priority": 1_030_000,
        "probe_frontier_sha256": (frozen.get("probe_frontier") or {}).get(
            "probe_frontier_sha256"
        ),
        "informative_probe_bundle_count": int(
            (frozen.get("probe_frontier") or {}).get("informative_bundle_count") or 0
        ),
        "probe_target_count": len((frozen.get("probe_frontier") or {}).get("targets") or ()),
        "holdout_predicates_hidden": True,
        "required_capability": frozen["required_capability"],
        "expected_exit": frozen["expected_exit"],
        "capital_authority": False,
    }
    job = {**job_body, "job_sha256": stable_sha256(job_body)}
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        for row in work_queue.list_items(connection, limit=10_000):
            prior = row.get("payload") or {}
            if (
                row.get("kind") == JOB_KIND and row.get("status") == "queued"
                and prior.get("entity_id") == frozen["entity_id"]
                and prior.get("request_sha256") != frozen["request_sha256"]
            ):
                work_queue.update_status(
                    connection, work_id=str(row["work_id"]), status="retired",
                    payload_update={
                        "stage": "superseded_request_contract",
                        "superseded_by_request_sha256": frozen["request_sha256"],
                        "provider_called": False, "error": None,
                    },
                )
        existing = connection.execute(
            "SELECT 1 FROM work_items WHERE work_id=?", (work_id,),
        ).fetchone()
        work_queue.enqueue(
            connection, kind=JOB_KIND, priority=1_030_000,
            max_attempts=max_attempts, payload=job,
        )
        connection.execute(
            "UPDATE work_items SET priority=?, payload_json=?, required_capability=?, updated_at=? "
            "WHERE work_id=? AND status='queued'",
            (
                1_030_000, json.dumps(job, sort_keys=True), frozen["required_capability"],
                int(time.time()), work_id,
            ),
        )
        connection.commit()
        if existing is None:
            work_queue.append_event(
                str(root / "research_jobs" / "agent" / "events.jsonl"),
                {"event_type": "investment_strategy_constraint_evidence_requested", "payload": job},
            )
    finally:
        connection.close()
    return {
        "schema": "jaggedthoughts-strategy-constraint-evidence-enqueue-v1",
        "status": "queued", "work_id": work_id,
        "request_path": request_path.relative_to(root).as_posix(),
        "request_sha256": frozen["request_sha256"], "capital_authority": False,
    }


__all__ = [
    "JOB_KIND", "JOB_SCHEMA", "REQUEST_SCHEMA", "RESULT_SCHEMA",
    "compile_strategy_constraint_evidence_request",
    "compile_strategy_constraint_evidence_result",
    "enqueue_strategy_constraint_evidence_request",
    "render_strategy_constraint_evidence_prompt",
    "strategy_source_identity",
    "strategy_constraint_evidence_output_schema",
    "strategy_constraint_evidence_readiness",
    "validate_strategy_constraint_evidence_request",
    "validate_strategy_constraint_evidence_result",
]
