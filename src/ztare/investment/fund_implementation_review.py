"""Comparison-bound fund research and implementation-review contracts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import (
    InvestmentProfileLifecycle,
    canonical_timestamp,
    require_finite,
    require_text,
    timestamp_key,
)


RESEARCH_REQUEST_SCHEMA = "jaggedthoughts-fund-implementation-research-request-v1"
RESEARCH_EVIDENCE_SCHEMA = "jaggedthoughts-fund-implementation-research-evidence-v1"
PROPOSAL_SCHEMA = "jaggedthoughts-fund-implementation-review-proposal-v1"
AUDIT_SCHEMA = "jaggedthoughts-fund-implementation-review-audit-v1"
DECISION_SCHEMA = "jaggedthoughts-fund-implementation-review-decision-v1"
IMPLEMENTATION_SCOPES = ("fees", "holdings", "liquidity", "mechanics", "tax_fit")
SCOPE_FIELDS = {
    "fees": ("expense_ratio",),
    "holdings": ("portfolio_holdings_count",),
    "liquidity": ("median_bid_ask_spread", "average_daily_volume_30d", "fund_net_assets"),
    "mechanics": ("portfolio_turnover",),
    "tax_fit": (
        "distribution_tax_character", "foreign_withholding_tax_rate",
        "trading_currency", "underlying_currency_exposure",
    ),
}


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    try:
        int(digest, 16)
    except ValueError as error:
        raise ValueError(f"{label} must be a SHA-256 digest") from error
    return digest


def _sealed(
    raw: Mapping[str, Any], *, schema: str, digest_field: str, label: str,
) -> dict[str, Any]:
    body = dict(raw)
    claimed = _digest(body.pop(digest_field, ""), f"{label} {digest_field}")
    if body.get("schema") != schema or stable_sha256(body) != claimed:
        raise ValueError(f"{label} identity is invalid")
    return {**body, digest_field: claimed}


def _evidence_timestamp(value: Any, label: str) -> str:
    text = require_text(value, label)
    if len(text) == 10:
        text = f"{text}T23:59:59Z"
    return canonical_timestamp(text, label)


def _typed_scope_values(
    coordinate: str, values: Mapping[str, Any], *, allow_partial: bool,
) -> dict[str, Any]:
    required = set(SCOPE_FIELDS[coordinate])
    supplied = set(values)
    if not supplied <= required or (not allow_partial and supplied != required):
        raise ValueError(f"{coordinate} must contain only its declared typed fields")
    normalized = dict(values)
    numeric = {
        "expense_ratio", "portfolio_holdings_count", "median_bid_ask_spread",
        "average_daily_volume_30d", "fund_net_assets", "portfolio_turnover",
        "foreign_withholding_tax_rate",
    }
    for field, value in normalized.items():
        if field in numeric:
            number = require_finite(value, f"fund implementation {coordinate}.{field}")
            if number < 0 or (field == "foreign_withholding_tax_rate" and number > 1):
                raise ValueError(f"fund implementation {coordinate}.{field} is outside bounds")
            if field == "portfolio_holdings_count" and not number.is_integer():
                raise ValueError("fund implementation holdings count must be an integer")
            normalized[field] = int(number) if field == "portfolio_holdings_count" else number
        else:
            normalized[field] = require_text(
                value, f"fund implementation {coordinate}.{field}",
            )
    return normalized


def compile_fund_implementation_research_request(
    *, candidate: Mapping[str, Any], candidate_leaf: str,
    comparison_program: Mapping[str, Any], created_at: str,
) -> dict[str, Any]:
    """Select a monitor fund for implementation research without qualifying it."""
    candidate_body = dict(candidate)
    candidate_sha = _digest(
        candidate_body.pop("candidate_sha256", ""), "implementation candidate sha256",
    )
    if (
        candidate_body.get("schema") != "jaggedthoughts-discovery-candidate-v1"
        or stable_sha256(candidate_body) != candidate_sha
        or candidate_body.get("entity_kind") != "public_fund"
        or candidate_body.get("screen_status") != "monitor"
    ):
        raise ValueError("implementation research requires a sealed monitor fund candidate")
    program_body = dict(comparison_program)
    program_sha = _digest(
        program_body.pop("program_sha256", ""), "comparison program sha256",
    )
    identity = dict(program_body.get("identity") or {})
    if (
        stable_sha256(program_body) != program_sha
        or not program_body.get("comparison_eligible")
        or identity.get("subject_id") != candidate_body.get("entity_id")
        or identity.get("entity_kind") != "public_fund"
        or identity.get("implementation_epoch") != candidate_body.get("as_of")
    ):
        raise ValueError("implementation research requires the candidate's eligible comparison program")
    leaf = _digest(candidate_leaf, "implementation research candidate leaf")
    created = canonical_timestamp(created_at, "implementation research created_at")
    if timestamp_key(created) < timestamp_key(str(candidate_body["as_of"])):
        raise ValueError("implementation research cannot precede its candidate epoch")
    body = {
        "schema": RESEARCH_REQUEST_SCHEMA,
        "request_id": f"fund-implementation-research:{candidate_body['entity_id']}:{program_sha[:16]}",
        "created_at": created,
        "entity_id": candidate_body["entity_id"],
        "entity_kind": "public_fund",
        "screen_status": "monitor",
        "candidate_leaf": leaf,
        "candidate_sha256": candidate_sha,
        "comparison_program_id": program_body.get("program_id"),
        "comparison_program_sha256": program_sha,
        "research_scope": ["fees", "holdings", "liquidity", "mechanics", "tax_fit"],
        "authority": "fund_implementation_research_only",
        "opportunity_qualified": False,
        "capital_authority": False,
    }
    return {**body, "request_sha256": stable_sha256(body)}


def compile_fund_implementation_research_evidence(
    *, request: Mapping[str, Any], findings: Mapping[str, Any], completed_at: str,
) -> dict[str, Any]:
    """Seal implementation findings; this object carries no absolute thesis."""
    verified = _sealed(
        request, schema=RESEARCH_REQUEST_SCHEMA, digest_field="request_sha256",
        label="fund implementation research request",
    )
    if set(findings) != set(IMPLEMENTATION_SCOPES):
        raise ValueError("fund implementation research requires every declared scope coordinate")
    normalized = {}
    missing_coordinates = []
    for coordinate in IMPLEMENTATION_SCOPES:
        row = dict(findings[coordinate])
        status = row.get("status")
        source_refs = sorted(set(map(str, row.get("source_refs") or ())))
        required_fields = set(SCOPE_FIELDS[coordinate])
        if status == "observed":
            values = dict(row.get("values") or {})
            if (
                not source_refs
                or any(values.get(field) is None for field in required_fields)
            ):
                raise ValueError(
                    f"observed {coordinate} requires its typed fields and source refs"
                )
            normalized[coordinate] = {
                "status": "observed", "values": values, "source_refs": source_refs,
            }
        elif status == "source_gap":
            missing = sorted(set(map(str, row.get("missing_fields") or ())))
            observed = dict(row.get("observed_values") or {})
            expected_missing = sorted(
                field for field in required_fields if observed.get(field) is None
            )
            if missing != expected_missing or not missing or (observed and not source_refs):
                raise ValueError(
                    f"source-gap {coordinate} must name its missing typed fields"
                )
            normalized[coordinate] = {
                "status": "source_gap", "missing_fields": missing,
                "observed_values": observed, "source_refs": source_refs,
            }
            missing_coordinates.append(coordinate)
        else:
            raise ValueError(f"{coordinate} status must be observed or source_gap")
    completed = canonical_timestamp(completed_at, "implementation research completed_at")
    if timestamp_key(completed) < timestamp_key(verified["created_at"]):
        raise ValueError("implementation research cannot precede its request")
    body = {
        "schema": RESEARCH_EVIDENCE_SCHEMA,
        "completed_at": completed,
        "entity_id": verified["entity_id"],
        "candidate_leaf": verified["candidate_leaf"],
        "candidate_sha256": verified["candidate_sha256"],
        "comparison_program_sha256": verified["comparison_program_sha256"],
        "request_sha256": verified["request_sha256"],
        "findings": normalized,
        "coverage_status": "partial_source_gap" if missing_coordinates else "complete",
        "missing_coordinates": missing_coordinates,
        "blockers": [f"source_gap:{coordinate}" for coordinate in missing_coordinates],
        "authority": "fund_implementation_evidence_only",
        "absolute_opportunity_thesis": False,
        "capital_authority": False,
    }
    return {**body, "evidence_sha256": stable_sha256(body)}


def compile_fund_implementation_review_proposal(
    *, evidence: Mapping[str, Any], compiled_at: str,
) -> dict[str, Any]:
    verified = _sealed(
        evidence, schema=RESEARCH_EVIDENCE_SCHEMA, digest_field="evidence_sha256",
        label="fund implementation research evidence",
    )
    blockers = list(map(str, verified.get("blockers") or ()))
    entity = verified["entity_id"]
    proposal_id = f"fund-implementation-review:{entity}:{verified['evidence_sha256'][:16]}"
    compiled = canonical_timestamp(compiled_at, "implementation review compiled_at")
    if timestamp_key(compiled) < timestamp_key(verified["completed_at"]):
        raise ValueError("implementation review cannot precede its research evidence")
    body = {
        "schema": PROPOSAL_SCHEMA,
        "proposal_id": proposal_id,
        "compiled_at": compiled,
        "lifecycle": InvestmentProfileLifecycle("operator", "draft").to_dict(),
        "entity": {"entity_id": entity, "entity_kind": "public_fund"},
        "candidate_leaf": verified["candidate_leaf"],
        "candidate_sha256": verified["candidate_sha256"],
        "comparison_program_sha256": verified["comparison_program_sha256"],
        "research_evidence_sha256": verified["evidence_sha256"],
        "activation_eligible": not blockers,
        "activation_blockers": sorted(set(blockers)),
        "required_operator_confirmation": f"ACTIVATE {proposal_id} FOR IMPLEMENTATION REVIEW ONLY",
        "authority": "fund_implementation_review_only",
        "portfolio_candidate": False,
        "allocation_allowed": False,
        "order_routing_allowed": False,
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "proposal_sha256": stable_sha256(body)}


def compile_fund_implementation_review_audit(
    proposals: Iterable[Mapping[str, Any]], *, compiled_at: str,
) -> dict[str, Any]:
    compiled = canonical_timestamp(compiled_at, "implementation review audit compiled_at")
    rows = []
    seen = set()
    for raw in proposals:
        proposal = _sealed(
            raw, schema=PROPOSAL_SCHEMA, digest_field="proposal_sha256",
            label="fund implementation review proposal",
        )
        if timestamp_key(compiled) < timestamp_key(proposal["compiled_at"]):
            raise ValueError("implementation review audit cannot precede its proposal")
        entity = str((proposal.get("entity") or {}).get("entity_id") or "")
        if not entity or entity in seen:
            raise ValueError("implementation review proposals require unique fund identities")
        seen.add(entity)
        rows.append({
            "entity_id": entity,
            "candidate_leaf": proposal["candidate_leaf"],
            "candidate_sha256": proposal["candidate_sha256"],
            "status": "eligible_proposal" if proposal["activation_eligible"] else "blocked",
            "activation_eligible": proposal["activation_eligible"],
            "blockers": list(proposal["activation_blockers"]),
            "proposal": proposal,
        })
    body = {
        "schema": AUDIT_SCHEMA,
        "compiled_at": compiled,
        "rows": sorted(rows, key=lambda row: row["entity_id"]),
        "authority": "fund_implementation_review_audit_only",
        "portfolio_authority": False,
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "audit_sha256": stable_sha256(body)}


def activate_fund_implementation_review(
    proposal: Mapping[str, Any], *, confirmation: str, operator_id: str,
    activated_at: str,
) -> dict[str, Any]:
    verified = _sealed(
        proposal, schema=PROPOSAL_SCHEMA, digest_field="proposal_sha256",
        label="fund implementation review proposal",
    )
    if verified.get("activation_blockers") or not verified.get("activation_eligible"):
        raise ValueError("fund implementation review proposal is blocked")
    if confirmation != verified["required_operator_confirmation"]:
        raise ValueError("fund implementation review confirmation is invalid")
    entity = dict(verified["entity"])
    activated = canonical_timestamp(activated_at, "implementation review activated_at")
    if timestamp_key(activated) < timestamp_key(verified["compiled_at"]):
        raise ValueError("implementation review activation cannot precede its proposal")
    body = {
        "schema": DECISION_SCHEMA,
        "decision_id": f"fund-implementation-review-decision:{entity['entity_id']}:{verified['proposal_sha256'][:16]}",
        "activated_at": activated,
        "lifecycle": InvestmentProfileLifecycle("operator", "active").to_dict(),
        "operator_id": require_text(operator_id, "implementation review operator_id"),
        "proposal_sha256": verified["proposal_sha256"],
        "entity": entity,
        "evidence": {
            "candidate_leaf": verified["candidate_leaf"],
            "candidate_sha256": verified["candidate_sha256"],
            "comparison_program_sha256": verified["comparison_program_sha256"],
            "research_evidence_sha256": verified["research_evidence_sha256"],
        },
        "review_policy": {"target_weight": 0.0},
        "authority": "operator_fund_implementation_review",
        "portfolio_candidate": False,
        "allocation_allowed": False,
        "order_routing_allowed": False,
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "decision_sha256": stable_sha256(body)}


def compile_fund_implementation_gap_evidence(
    *, request: Mapping[str, Any], prior_evidence: Mapping[str, Any],
    acquisition: Mapping[str, Any], accepted_at: str,
) -> dict[str, Any]:
    """Merge a source-bound gap result without changing comparison evidence."""
    verified_request = _sealed(
        request, schema=RESEARCH_REQUEST_SCHEMA, digest_field="request_sha256",
        label="fund implementation research request",
    )
    prior = _sealed(
        prior_evidence, schema=RESEARCH_EVIDENCE_SCHEMA,
        digest_field="evidence_sha256", label="fund implementation research evidence",
    )
    if prior.get("request_sha256") != verified_request["request_sha256"]:
        raise ValueError("fund implementation gap evidence crossed its request")
    expected_identity = {
        "schema": "jaggedthoughts-fund-implementation-gap-evidence-v1",
        "request_sha256": verified_request["request_sha256"],
        "prior_evidence_sha256": prior["evidence_sha256"],
        "candidate_leaf": verified_request["candidate_leaf"],
        "candidate_sha256": verified_request["candidate_sha256"],
        "comparison_program_sha256": verified_request["comparison_program_sha256"],
        "entity_id": verified_request["entity_id"],
        "capital_authority": False,
    }
    if {key: acquisition.get(key) for key in expected_identity} != expected_identity:
        raise ValueError("fund implementation gap result changed its frozen identity")
    requested = tuple(sorted(set(map(str, acquisition.get("requested_coordinates") or ()))))
    missing = set(map(str, prior.get("missing_coordinates") or ()))
    already_attempted = set(map(
        str, (prior.get("gap_acquisition") or {}).get("requested_coordinates") or (),
    ))
    fresh_missing = missing - already_attempted
    if not requested or set(requested) != fresh_missing:
        raise ValueError("fund implementation acquisition must target only fresh source gaps")
    findings = acquisition.get("findings")
    if not isinstance(findings, Mapping) or set(findings) != set(requested):
        raise ValueError("fund implementation acquisition must settle each requested coordinate")

    accepted = canonical_timestamp(accepted_at, "fund implementation gap accepted_at")
    researched = _evidence_timestamp(
        acquisition.get("researched_at"), "fund implementation gap researched_at",
    )
    if not (
        timestamp_key(verified_request["created_at"])
        <= timestamp_key(researched) <= timestamp_key(accepted)
    ):
        raise ValueError("fund implementation gap research is outside its request window")
    sources = acquisition.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("fund implementation gap research requires primary public sources")
    normalized_sources: list[dict[str, Any]] = []
    source_by_id: dict[str, dict[str, Any]] = {}
    allowed_supports = {
        f"{coordinate}.{field}" for coordinate in requested
        for field in SCOPE_FIELDS[coordinate]
    }
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping):
            raise ValueError(f"fund implementation source {index} must be an object")
        normalized = dict(source)
        source_id = require_text(normalized.get("id"), f"fund implementation source {index} id")
        if source_id in source_by_id:
            raise ValueError(f"fund implementation source id is duplicated: {source_id}")
        if normalized.get("source_kind") not in {"filing", "issuer", "regulator", "government"}:
            raise ValueError("fund implementation gap research accepts primary sources only")
        for field in ("title", "publisher"):
            normalized[field] = require_text(
                normalized.get(field), f"fund implementation source {index} {field}",
            )
        url = require_text(normalized.get("url"), f"fund implementation source {index} url")
        if not url.startswith("https://"):
            raise ValueError("fund implementation source URLs must use https")
        normalized["url"] = url
        published = _evidence_timestamp(
            normalized.get("published_at"), f"fund implementation source {index} published_at",
        )
        accessed = _evidence_timestamp(
            normalized.get("accessed_at"), f"fund implementation source {index} accessed_at",
        )
        if timestamp_key(accessed) > timestamp_key(accepted):
            if timestamp_key(accessed).date() != timestamp_key(accepted).date():
                raise ValueError("fund implementation source was accessed after acceptance")
            accessed = accepted
        if timestamp_key(accessed) < timestamp_key(verified_request["created_at"]):
            raise ValueError("fund implementation source access predates its request")
        if timestamp_key(published) > timestamp_key(accessed):
            if timestamp_key(published).date() != timestamp_key(accessed).date():
                raise ValueError("fund implementation source publication follows access")
            published = accessed
        supports = sorted(set(map(str, normalized.get("supports") or ())))
        if not supports or not set(supports) <= allowed_supports:
            raise ValueError("fund implementation source supports undeclared fields")
        normalized.update({
            "published_at": published, "accessed_at": accessed, "supports": supports,
        })
        source_by_id[source_id] = normalized
        normalized_sources.append(normalized)

    replacements: dict[str, dict[str, Any]] = {}
    for coordinate in requested:
        row = findings[coordinate]
        if not isinstance(row, Mapping):
            raise ValueError(f"fund implementation {coordinate} finding must be an object")
        refs = sorted(set(map(str, row.get("source_refs") or ())))
        if not refs or not set(refs) <= set(source_by_id):
            raise ValueError(f"fund implementation {coordinate} cites undeclared sources")
        supported = {
            item for ref in refs for item in source_by_id[ref]["supports"]
        }
        required_tokens = {f"{coordinate}.{field}" for field in SCOPE_FIELDS[coordinate]}
        if not required_tokens <= supported:
            raise ValueError(f"fund implementation {coordinate} sources do not cover its fields")
        if row.get("status") == "observed":
            replacements[coordinate] = {
                "status": "observed",
                "values": _typed_scope_values(
                    coordinate, dict(row.get("values") or {}), allow_partial=False,
                ),
                "source_refs": refs,
            }
        elif row.get("status") == "source_gap":
            observed = _typed_scope_values(
                coordinate, dict(row.get("observed_values") or {}), allow_partial=True,
            )
            expected_missing = sorted(set(SCOPE_FIELDS[coordinate]) - set(observed))
            if sorted(set(map(str, row.get("missing_fields") or ()))) != expected_missing:
                raise ValueError(f"fund implementation {coordinate} source gap is not exact")
            replacements[coordinate] = {
                "status": "source_gap", "missing_fields": expected_missing,
                "observed_values": observed, "source_refs": refs,
            }
        else:
            raise ValueError(f"fund implementation {coordinate} status is unsupported")

    merged_findings = {key: dict(value) for key, value in prior["findings"].items()}
    merged_findings.update(replacements)
    merged = compile_fund_implementation_research_evidence(
        request=verified_request, findings=merged_findings, completed_at=accepted,
    )
    body = {key: value for key, value in merged.items() if key != "evidence_sha256"}
    body.update({
        "prior_evidence_sha256": prior["evidence_sha256"],
        "external_sources": sorted(normalized_sources, key=lambda row: row["id"]),
        "automatic_decision": False,
        "rank_authority": False,
        "portfolio_authority": False,
        "order_routing_allowed": False,
        "gap_acquisition": {
            "schema": "jaggedthoughts-fund-implementation-gap-acquisition-v1",
            "researched_at": researched,
            "accepted_at": accepted,
            "requested_coordinates": list(requested),
            "source_ids": sorted(source_by_id),
            "authority": "fund_implementation_evidence_only",
            "automatic_decision": False,
            "capital_authority": False,
        },
    })
    return {**body, "evidence_sha256": stable_sha256(body)}


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def current_fund_implementation_gap_targets(
    workspace: str | Path,
) -> list[dict[str, Any]]:
    """Return only current, comparison-bound gaps not already web-researched."""
    root = Path(workspace).expanduser().resolve()
    status_path = root / "research_jobs" / "fund_implementation" / "latest.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status_body = dict(status)
    status_sha = _digest(
        status_body.pop("status_sha256", ""), "fund implementation status sha256",
    )
    if (
        status_body.get("schema") != "jaggedthoughts-workspace-fund-implementation-review-v1"
        or stable_sha256(status_body) != status_sha
    ):
        raise ValueError("fund implementation status identity is invalid")
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    receipt = json.loads(
        (root / "discovery" / "latest_record.json").read_text(encoding="utf-8")
    )
    if discovery.get("run_sha256") != receipt.get("run_sha256"):
        return []
    candidates = {
        (str(row.get("entity_id") or ""), str(row.get("candidate_sha256") or "")): row
        for row in discovery.get("candidates") or () if isinstance(row, Mapping)
    }
    leaves = dict(receipt.get("candidate_leaves") or {})
    comparison = json.loads(
        (root / "portfolio" / "fund_sleeve_comparison" / "latest.json").read_text(
            encoding="utf-8"
        )
    )
    comparison_body = dict(comparison)
    comparison_sha = _digest(
        comparison_body.pop("fund_sleeve_comparison_sha256", ""),
        "fund sleeve comparison sha256",
    )
    if stable_sha256(comparison_body) != comparison_sha:
        return []
    programs: dict[tuple[str, str], dict[str, Any]] = {
        (
            str(program.get("program_id") or ""),
            str((program.get("identity") or {}).get("subject_id") or ""),
        ): dict(program)
        for sleeve in comparison.get("sleeves") or ()
        for program in sleeve.get("programs") or ()
        if isinstance(program, Mapping) and program.get("comparison_eligible")
    }
    evidence_by_request: dict[str, tuple[Path, dict[str, Any]]] = {}
    evidence_root = root / "research_jobs" / "fund_implementation" / "evidence"
    for path in sorted(evidence_root.glob("*.json")):
        evidence = _sealed(
            json.loads(path.read_text(encoding="utf-8")), schema=RESEARCH_EVIDENCE_SCHEMA,
            digest_field="evidence_sha256", label="fund implementation research evidence",
        )
        request_sha = str(evidence.get("request_sha256") or "")
        if request_sha in evidence_by_request:
            raise ValueError(f"multiple fund implementation evidence rows for {request_sha}")
        evidence_by_request[request_sha] = (path, evidence)

    targets = []
    for row in status.get("requests") or ():
        if not isinstance(row, Mapping):
            continue
        request_path = root / str(row.get("artifact_path") or "")
        request_path.resolve().relative_to(root)
        request = _sealed(
            json.loads(request_path.read_text(encoding="utf-8")),
            schema=RESEARCH_REQUEST_SCHEMA, digest_field="request_sha256",
            label="fund implementation research request",
        )
        if request.get("request_sha256") != row.get("request_sha256"):
            continue
        candidate = candidates.get((request["entity_id"], request["candidate_sha256"]))
        program = programs.get((
            str(request.get("comparison_program_id") or ""), request["entity_id"],
        ))
        if (
            not candidate or candidate.get("screen_status") != "monitor"
            or leaves.get(str(candidate.get("candidate_id") or "")) != request["candidate_leaf"]
            or not program
            or (program.get("identity") or {}).get("subject_id") != request["entity_id"]
            or (program.get("identity") or {}).get("implementation_epoch")
            != candidate.get("as_of")
        ):
            continue
        evidence_pair = evidence_by_request.get(str(request["request_sha256"]))
        if not evidence_pair:
            continue
        evidence_path, evidence = evidence_pair
        attempted = set(map(
            str, (evidence.get("gap_acquisition") or {}).get("requested_coordinates") or (),
        ))
        coordinates = sorted(
            set(map(str, evidence.get("missing_coordinates") or ())) - attempted
        )
        if not coordinates:
            continue
        targets.append({
            "request": request,
            "request_path": request_path.relative_to(root).as_posix(),
            "prior_evidence": evidence,
            "evidence_path": evidence_path.relative_to(root).as_posix(),
            "requested_coordinates": coordinates,
            "requested_fields": {
                coordinate: list(SCOPE_FIELDS[coordinate]) for coordinate in coordinates
            },
            "discovery_rank": candidate.get("rank"),
            "potential_rank": candidate.get("potential_rank"),
        })
    return sorted(targets, key=lambda row: str(row["request"]["entity_id"]))


def _comparison_findings(
    program: Mapping[str, Any], *, comparison_sha256: str,
) -> dict[str, Any]:
    """Project only fields already carried by the sealed comparison program."""
    program_sha = str(program["program_sha256"])
    base_refs = [f"sha256:{comparison_sha256}", f"sha256:{program_sha}"]
    portfolio = dict(program.get("portfolio_evidence") or {})
    fees_liquidity = dict(portfolio.get("fees_liquidity") or {})

    def row(values: Mapping[str, Any], required: Iterable[str], refs: Iterable[str]) -> dict[str, Any]:
        observed = {key: value for key, value in values.items() if value is not None}
        missing = [key for key in required if values.get(key) is None]
        sources = sorted(set(filter(None, map(str, refs))))
        if missing:
            return {
                "status": "source_gap", "missing_fields": missing,
                "observed_values": observed, "source_refs": sources if observed else [],
            }
        return {"status": "observed", "values": observed, "source_refs": sources}

    holdings = dict(program.get("holdings") or {})
    holdings_quality = dict(portfolio.get("holdings_weighted_earnings_power") or {})
    holdings_refs = [
        *base_refs,
        *[f"sha256:{value}" for value in holdings_quality.get("quality_report_sha256s") or ()],
        f"sha256:{holdings_quality.get('snapshot_sha256')}"
        if holdings_quality.get("snapshot_sha256") else "",
    ]
    liquidity = dict(program.get("liquidity") or {})
    tax = dict(portfolio.get("tax_currency") or {})
    return {
        "fees": row(
            {"expense_ratio": fees_liquidity.get("expense_ratio")},
            ("expense_ratio",), base_refs,
        ),
        "holdings": row(
            holdings, ("portfolio_holdings_count",), holdings_refs,
        ),
        "liquidity": row(
            liquidity,
            ("median_bid_ask_spread", "average_daily_volume_30d", "fund_net_assets"),
            (*base_refs, *(program.get("price_evidence_refs") or ())),
        ),
        "mechanics": row(
            {"portfolio_turnover": program.get("internal_portfolio_turnover")},
            ("portfolio_turnover",), base_refs,
        ),
        "tax_fit": row(
            tax,
            ("distribution_tax_character", "foreign_withholding_tax_rate",
             "trading_currency", "underlying_currency_exposure"),
            base_refs,
        ),
    }


def compile_workspace_fund_implementation_review(
    workspace: str | Path, *, comparison: Mapping[str, Any] | None = None,
    compiled_at: str | None = None,
) -> dict[str, Any]:
    """Persist current comparison requests and proposals from pre-existing evidence."""
    root = Path(workspace).expanduser().resolve()
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    receipt = json.loads((root / "discovery" / "latest_record.json").read_text(encoding="utf-8"))
    if receipt.get("run_sha256") != discovery.get("run_sha256"):
        raise ValueError("fund implementation review requires the current discovery record")
    compared = dict(comparison or json.loads(
        (root / "portfolio" / "fund_sleeve_comparison" / "latest.json").read_text(
            encoding="utf-8"
        )
    ))
    comparison_body = dict(compared)
    comparison_sha = _digest(
        comparison_body.pop("fund_sleeve_comparison_sha256", ""),
        "fund sleeve comparison sha256",
    )
    if (
        comparison_body.get("schema") != "jaggedthoughts-fund-sleeve-comparison-v1"
        or stable_sha256(comparison_body) != comparison_sha
        or comparison_body.get("authority") != "normalized_paper_comparison_only"
    ):
        raise ValueError("fund implementation review requires a sealed comparison artifact")
    occurred = canonical_timestamp(
        compiled_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace implementation review compiled_at",
    )
    leaves = dict(receipt.get("candidate_leaves") or {})
    candidates = [
        dict(row) for row in discovery.get("candidates") or ()
        if isinstance(row, Mapping)
        and row.get("entity_kind") == "public_fund"
        and row.get("screen_status") == "monitor"
    ]
    programs = [
        dict(program)
        for sleeve in compared.get("sleeves") or ()
        for program in sleeve.get("programs") or ()
        if isinstance(program, Mapping) and program.get("comparison_eligible")
    ]
    requests = []
    programs_by_request = {}
    request_dir = root / "research_jobs" / "fund_implementation" / "requests"
    persisted_by_candidate = {}
    for path in sorted(request_dir.glob("*.json")):
        persisted = _sealed(
            json.loads(path.read_text(encoding="utf-8")), schema=RESEARCH_REQUEST_SCHEMA,
            digest_field="request_sha256", label="fund implementation research request",
        )
        key = (str(persisted.get("entity_id") or ""), str(persisted.get("candidate_leaf") or ""))
        if key in persisted_by_candidate:
            raise ValueError(f"multiple fund implementation requests for {key}")
        persisted_by_candidate[key] = (persisted, path)
    for program in programs:
        identity = dict(program.get("identity") or {})
        matches = [
            row for row in candidates
            if row.get("entity_id") == identity.get("subject_id")
            and row.get("as_of") == identity.get("implementation_epoch")
        ]
        if len(matches) != 1:
            continue
        candidate = matches[0]
        candidate_leaf = leaves.get(str(candidate.get("candidate_id") or ""))
        if not candidate_leaf:
            continue
        persisted = persisted_by_candidate.get((str(candidate["entity_id"]), str(candidate_leaf)))
        if persisted is not None:
            request, path = persisted
            expected = {
                "candidate_leaf": str(candidate_leaf),
                "candidate_sha256": candidate["candidate_sha256"],
            }
            if {key: request.get(key) for key in expected} != expected:
                raise ValueError("persisted fund implementation request crossed current identity")
            relative = path.relative_to(root)
        else:
            request = compile_fund_implementation_research_request(
                candidate=candidate, candidate_leaf=str(candidate_leaf),
                comparison_program=program, created_at=occurred,
            )
            relative = Path("research_jobs") / "fund_implementation" / "requests" / (
                f"{str(candidate['entity_id']).lower()}-"
                f"{str(program['program_sha256'])[:12]}.json"
            )
            path = root / relative
            _atomic_json(path, request)
        requests.append({**request, "artifact_path": relative.as_posix()})
        programs_by_request[str(request["request_sha256"])] = program

    evidence_by_request = {}
    for path in sorted((root / "research_jobs" / "fund_implementation" / "evidence").glob("*.json")):
        evidence = _sealed(
            json.loads(path.read_text(encoding="utf-8")), schema=RESEARCH_EVIDENCE_SCHEMA,
            digest_field="evidence_sha256", label="fund implementation research evidence",
        )
        request_sha = str(evidence.get("request_sha256") or "")
        if request_sha in evidence_by_request:
            raise ValueError(f"multiple fund implementation evidence rows for {request_sha}")
        evidence_by_request[request_sha] = evidence
    current_request_shas = {str(row["request_sha256"]) for row in requests}
    evidence_dir = root / "research_jobs" / "fund_implementation" / "evidence"
    for request in requests:
        request_sha = str(request["request_sha256"])
        program = programs_by_request[request_sha]
        if (
            request_sha in evidence_by_request
            or request.get("comparison_program_sha256") != program.get("program_sha256")
        ):
            continue
        evidence = compile_fund_implementation_research_evidence(
            request={key: value for key, value in request.items() if key != "artifact_path"},
            findings=_comparison_findings(program, comparison_sha256=comparison_sha),
            completed_at=str(request["created_at"]),
        )
        _atomic_json(
            evidence_dir / f"{str(request['entity_id']).lower()}-{request_sha[:12]}.json",
            evidence,
        )
        evidence_by_request[request_sha] = evidence
    current_evidence = [
        evidence_by_request[request_sha] for request_sha in sorted(current_request_shas)
        if request_sha in evidence_by_request
    ]
    proposals = [
        compile_fund_implementation_review_proposal(
            evidence=row, compiled_at=str(row["completed_at"]),
        )
        for row in current_evidence
    ]
    audit = compile_fund_implementation_review_audit(proposals, compiled_at=occurred)
    audit_relative = Path("paper_proposals/fund_implementation_reviews/latest.json")
    _atomic_json(root / audit_relative, audit)
    decision_count = sum(
        1 for path in (root / "paper_decisions" / "fund_implementation_reviews").glob("*.json")
        if _sealed(
            json.loads(path.read_text(encoding="utf-8")), schema=DECISION_SCHEMA,
            digest_field="decision_sha256", label="fund implementation review decision",
        ).get("proposal_sha256") in {row["proposal_sha256"] for row in proposals}
    )
    eligible_count = sum(row["activation_eligible"] for row in audit["rows"])
    next_missing_coordinates = sorted({
        coordinate for row in current_evidence
        for coordinate in row.get("missing_coordinates") or ()
    })
    status = (
        "implementation_review_active" if decision_count
        else "operator_review_ready" if eligible_count
        else "implementation_evidence_source_gaps" if proposals
        else "awaiting_typed_evidence" if requests
        else "no_comparison_eligible_monitor_fund"
    )
    body = {
        "schema": "jaggedthoughts-workspace-fund-implementation-review-v1",
        "compiled_at": occurred,
        "comparison_sha256": comparison_sha,
        "status": status,
        "request_count": len(requests),
        "evidence_count": len(current_evidence),
        "proposal_count": len(proposals),
        "eligible_proposal_count": eligible_count,
        "decision_count": decision_count,
        "next_missing_coordinates": next_missing_coordinates,
        "requests": requests,
        "request_directory": request_dir.relative_to(root).as_posix(),
        "evidence_directory": "research_jobs/fund_implementation/evidence",
        "audit_path": audit_relative.as_posix(),
        "automatic_activation": False,
        "portfolio_candidate": False,
        "allocation_allowed": False,
        "order_routing_allowed": False,
        "capital_authority": False,
        "brokerage_authority": False,
    }
    result = {**body, "status_sha256": stable_sha256(body)}
    _atomic_json(root / "research_jobs" / "fund_implementation" / "latest.json", result)
    return result


__all__ = [
    "AUDIT_SCHEMA", "DECISION_SCHEMA", "PROPOSAL_SCHEMA", "RESEARCH_EVIDENCE_SCHEMA",
    "RESEARCH_REQUEST_SCHEMA", "activate_fund_implementation_review",
    "compile_fund_implementation_gap_evidence",
    "compile_fund_implementation_research_evidence",
    "compile_fund_implementation_research_request",
    "compile_fund_implementation_review_audit",
    "compile_fund_implementation_review_proposal",
    "compile_workspace_fund_implementation_review",
    "current_fund_implementation_gap_targets",
]
