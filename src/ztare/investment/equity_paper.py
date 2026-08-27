"""Compile current public-equity evidence into inactive cash-only paper proposals."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .business_fingerprint import (
    BUSINESS_FINGERPRINT_SCHEMA,
    compile_business_fingerprint,
)
from .contracts import (
    InvestmentProfileLifecycle,
    PositionActionSpec,
    canonical_timestamp,
    require_finite,
    require_text,
    timestamp_key,
)
from .discovery import DISCOVERY_CANDIDATE_SCHEMA, DISCOVERY_RUN_SCHEMA
from .funnel import FunnelObjectRef, FunnelTransitionReceipt
from .golden_store import (
    GoldenLeaf,
    GoldenStore,
    record_funnel_transition,
    research_evidence_admissibility,
    research_evidence_is_admissible,
)
from .paper import PaperBook
from .research_jobs import validate_research_dossier
from .research_memory import RESEARCH_COVERAGE_SCHEMA
from .state_price_authoring import audit_workspace_modeled_grids
from .underwriting_adapter import (
    UNDERWRITING_INDEX_SCHEMA,
    VALUATION_ENVELOPE_SCHEMA,
    compile_workspace_underwriting_index,
)


PROPOSAL_SCHEMA = "jaggedthoughts-public-equity-paper-proposal-v1"
DECISION_SCHEMA = "jaggedthoughts-public-equity-paper-decision-v1"
AUDIT_SCHEMA = "jaggedthoughts-public-equity-paper-proposal-audit-v1"
ACTIVATION_SCHEMA = "jaggedthoughts-public-equity-paper-activation-v1"
GRID_AUDIT_SCHEMA = "jaggedthoughts-modeled-payoff-grid-audit-v1"
STRATEGY_FRONTIER_SCHEMA = "jaggedthoughts-company-strategy-frontier-v1"


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
    declared = _digest(body.pop(digest_field, ""), f"{label} {digest_field}")
    if body.get("schema") != schema or stable_sha256(body) != declared:
        raise ValueError(f"{label} identity is invalid")
    return {**body, digest_field: declared}, declared


def _frontier_residuals(frontier: Mapping[str, Any]) -> dict[str, Any]:
    certificate = dict(frontier.get("certificate") or {})
    representation = dict(certificate.get("representation_audit") or {})
    return {
        "scope_closed": bool(frontier.get("scope_closed")),
        "decision_closed": bool(frontier.get("decision_closed")),
        "claim_residual_count": len(certificate.get("residuals") or ()),
        "representation_residuals": list(representation.get("residuals") or ()),
    }


def compile_inactive_equity_proposal(
    *, discovery_run: Mapping[str, Any], candidate_leaf: str,
    dossier: Mapping[str, Any], dossier_leaf: str,
    underwriting_index: Mapping[str, Any], valuation_artifact: Mapping[str, Any],
    business_fingerprint: Mapping[str, Any], modeled_grid_audit: Mapping[str, Any],
    compiled_at: str, strategy_frontier: Mapping[str, Any] | None = None,
    research_coverage: Mapping[str, Any] | None = None,
    research_coverage_leaf: str | None = None, paper_cash: float = 100_000.0,
) -> dict[str, Any]:
    """Join exact evidence without creating a position, portfolio admission, or order."""
    discovery, discovery_sha = _verified(
        discovery_run, schema=DISCOVERY_RUN_SCHEMA, digest_field="run_sha256",
        label="discovery run",
    )
    leaf = _digest(candidate_leaf, "candidate leaf")
    coverage: dict[str, Any] | None = None
    coverage_sha: str | None = None
    if research_coverage is not None:
        coverage, coverage_sha = _verified(
            research_coverage, schema=RESEARCH_COVERAGE_SCHEMA,
            digest_field="coverage_sha256", label="research coverage",
        )
        if coverage.get("candidate_leaf") != leaf:
            raise ValueError("research coverage does not bind the current candidate leaf")

    candidates = [
        dict(row) for row in discovery.get("candidates") or ()
        if isinstance(row, Mapping) and row.get("candidate_id")
    ]
    candidate_sha_hint = (
        coverage.get("candidate_sha256") if coverage and coverage.get("covered")
        else dossier.get("candidate_sha256")
    )
    candidate = next((row for row in candidates if row.get("entity_kind") == "public_equity"
                      and row.get("candidate_sha256") == candidate_sha_hint), None)
    if candidate is None and coverage is None:
        same_entity = [
            row for row in candidates
            if row.get("entity_kind") == "public_equity"
            and str(row.get("entity_id") or "").upper()
            == str(dossier.get("entity_id") or "").upper()
        ]
        candidate = same_entity[0] if len(same_entity) == 1 else None
    if candidate is None:
        raise ValueError("proposal dossier does not identify one current public-equity candidate")
    candidate, candidate_sha = _verified(
        candidate, schema=DISCOVERY_CANDIDATE_SCHEMA, digest_field="candidate_sha256",
        label="discovery candidate",
    )
    if candidate.get("screen_status") != "qualified":
        raise ValueError("equity proposals require a qualified current candidate")
    entity = require_text(candidate.get("entity_id"), "proposal entity_id").upper()

    dossier_is_current = (
        dossier.get("candidate_leaf"), dossier.get("candidate_sha256"), dossier.get("as_of")
    ) == (leaf, candidate_sha, candidate["as_of"])
    if not dossier_is_current:
        if not coverage or not coverage.get("covered"):
            raise ValueError("a prior dossier requires covered current research evidence")
        if (
            coverage.get("entity_id"), coverage.get("candidate_sha256"),
            coverage.get("prior_dossier_leaf")
        ) != (entity, candidate_sha, dossier_leaf):
            raise ValueError("research coverage does not bridge the current candidate to this dossier")
        excluded = set(coverage.get("excluded_scope") or ())
        if coverage.get("scope") != "qualitative_strategy_industry_and_durable_earnings_only" or not {
            "current_candidate_metrics", "valuation", "rank", "factor_estimates",
            "portfolio_or_capital_action",
        }.issubset(excluded):
            raise ValueError("research coverage does not preserve current quantitative identity")
        if not research_coverage_leaf:
            raise ValueError("covered prior research requires its golden-store leaf")
    normalized_dossier = validate_research_dossier(dossier, expected_identity={
        "candidate_leaf": dossier.get("candidate_leaf"),
        "candidate_sha256": dossier.get("candidate_sha256"),
        "entity_id": entity, "as_of": dossier.get("as_of"),
    })
    dossier_sha = _digest(normalized_dossier["dossier_sha256"], "dossier hash")
    dossier_leaf_sha = _digest(dossier_leaf, "dossier leaf")
    coverage_leaf_sha = (
        _digest(research_coverage_leaf, "research coverage leaf")
        if research_coverage_leaf else None
    )

    underwriting, underwriting_sha = _verified(
        underwriting_index, schema=UNDERWRITING_INDEX_SCHEMA,
        digest_field="underwriting_index_sha256", label="underwriting index",
    )
    if underwriting.get("discovery_run_sha256") != discovery_sha:
        raise ValueError("underwriting index and discovery run identities differ")
    row = next((dict(value) for value in underwriting.get("candidates") or ()
                if value.get("candidate_sha256") == candidate_sha), None)
    if row is None or row.get("entity_id") != entity:
        raise ValueError("candidate-bound underwriting coordinates are absent")
    row_body = dict(row)
    row_sha = _digest(row_body.pop("underwriting_row_sha256", ""), "underwriting row hash")
    if stable_sha256(row_body) != row_sha:
        raise ValueError("underwriting row content hash mismatch")

    valuation, valuation_sha = _verified(
        valuation_artifact, schema=VALUATION_ENVELOPE_SCHEMA,
        digest_field="envelope_sha256", label="valuation envelope",
    )
    projected = dict(candidate.get("valuation") or {})
    if (valuation.get("entity_id"), valuation.get("evidence_epoch"), valuation_sha) != (
        entity, candidate.get("as_of"), projected.get("envelope_sha256")
    ):
        raise ValueError("valuation envelope crossed candidate identity or evidence epoch")
    enumeration = dict(valuation.get("enumeration") or {})

    fingerprint, fingerprint_sha = _verified(
        business_fingerprint, schema=BUSINESS_FINGERPRINT_SCHEMA,
        digest_field="business_fingerprint_sha256", label="business fingerprint",
    )
    dossier_component = dict((fingerprint.get("component_identity") or {}).get("research_dossier") or {})
    if (fingerprint.get("entity_id"), dossier_component.get("candidate_leaf"),
            dossier_component.get("sha256")) != (
                entity, normalized_dossier.get("candidate_leaf"), dossier_sha,
            ):
        raise ValueError("business fingerprint does not bind the selected dossier")

    grid_audit, grid_audit_sha = _verified(
        modeled_grid_audit, schema=GRID_AUDIT_SCHEMA,
        digest_field="audit_sha256", label="modeled-grid audit",
    )
    if grid_audit.get("discovery_run_sha256") != discovery_sha:
        raise ValueError("modeled-grid audit and discovery run identities differ")
    grid = next((dict(value) for value in grid_audit.get("rows") or ()
                 if value.get("candidate_sha256") == candidate_sha), None)
    if grid is None or grid.get("entity_id") != entity:
        raise ValueError("candidate-bound modeled payoff grid is absent")

    frontier_projection = None
    frontier_details: dict[str, Any] = {}
    if strategy_frontier is not None:
        frontier, frontier_sha = _verified(
            strategy_frontier, schema=STRATEGY_FRONTIER_SCHEMA,
            digest_field="strategy_frontier_sha256", label="strategy frontier",
        )
        company = dict(frontier.get("company") or {})
        if (company.get("id"), company.get("candidate_leaf"),
                company.get("source_dossier_sha256")) != (
                    entity, normalized_dossier.get("candidate_leaf"), dossier_sha,
                ):
            raise ValueError("strategy frontier does not bind the selected dossier")
        frontier_details = _frontier_residuals(frontier)
        frontier_projection = {
            "strategy_frontier_sha256": frontier_sha,
            "evidence_epoch": frontier.get("evidence_epoch"),
            **frontier_details,
            "program_count": len(frontier.get("programs") or ()),
            "frontier_program_ids": list(frontier.get("frontier_program_ids") or ()),
            "local_peak_program_ids": list(frontier.get("local_peak_program_ids") or ()),
            "pressure_to_option_coverage": dict(frontier.get("pressure_to_option_coverage") or {}),
        }

    compiled = canonical_timestamp(compiled_at, "equity proposal compiled_at")
    if timestamp_key(compiled) < timestamp_key(str(normalized_dossier["generated_at"])):
        raise ValueError("equity proposal cannot precede its research dossier")
    cash = require_finite(paper_cash, "equity proposal paper_cash")
    if cash <= 0:
        raise ValueError("equity proposal paper_cash must be positive")

    blocker_details = {
        "underwriting_gaps": list(row.get("gaps") or ()),
        "valuation_residuals": list(enumeration.get("residuals") or ()),
        "business_fingerprint_unknowns": list(fingerprint.get("unknowns") or ()),
        "strategy_frontier": frontier_details,
        "research_coverage": dict(coverage or {}),
        "modeled_grid": {
            "no_arbitrage_certificate": bool(grid.get("no_arbitrage_certificate")),
            "market_complete": bool(grid.get("market_complete")),
            "residual_trigger": grid.get("residual_trigger"),
            "evidence_request_count": int(grid.get("evidence_request_count") or 0),
        },
    }
    position_blockers = []
    position_blockers.extend(f"underwriting:{gap}" for gap in blocker_details["underwriting_gaps"])
    if not enumeration.get("exhausted_within_scope"):
        position_blockers.append("valuation_enumeration_scope_open")
    if blocker_details["valuation_residuals"]:
        position_blockers.append("valuation_enumeration_residuals_present")
    if blocker_details["business_fingerprint_unknowns"]:
        position_blockers.append("business_fingerprint_unknowns_present")
    if strategy_frontier is not None and not frontier_details["scope_closed"]:
        position_blockers.append("strategy_frontier_scope_open")
    if strategy_frontier is not None and frontier_details["claim_residual_count"]:
        position_blockers.append("strategy_frontier_claim_residuals_present")
    if strategy_frontier is not None and frontier_details["representation_residuals"]:
        position_blockers.append("strategy_frontier_representation_residuals_present")
    if not grid.get("no_arbitrage_certificate"):
        position_blockers.append("modeled_grid_no_arbitrage_certificate_absent")
    if not grid.get("market_complete"):
        position_blockers.append("modeled_grid_market_incomplete")
    if grid.get("residual_trigger"):
        position_blockers.append(f"modeled_grid:{grid['residual_trigger']}")
    if coverage and not coverage.get("covered"):
        position_blockers.append(f"research_coverage:{coverage.get('status') or 'not_current'}")
    position_blockers = sorted(set(position_blockers))

    evidence = {
        "discovery_run_sha256": discovery_sha,
        "candidate_leaf": leaf, "candidate_sha256": candidate_sha,
        "dossier_leaf": dossier_leaf_sha, "dossier_sha256": dossier_sha,
        "research_coverage_leaf": coverage_leaf_sha,
        "research_coverage_sha256": coverage_sha,
        "underwriting_index_sha256": underwriting_sha, "underwriting_row_sha256": row_sha,
        "valuation_envelope_sha256": valuation_sha,
        "business_fingerprint_sha256": fingerprint_sha,
        "strategy_frontier_sha256": (
            frontier_projection or {}
        ).get("strategy_frontier_sha256"),
        "modeled_grid_audit_sha256": grid_audit_sha,
        "modeled_grid_sha256": grid.get("modeled_grid_sha256"),
        "state_price_result_sha256": grid.get("result_sha256"),
    }
    evidence_refs = tuple(f"sha256:{value}" for value in evidence.values() if value)
    proposal_id = f"equity-paper:{entity}:{stable_sha256(evidence)[:16]}"
    book = PaperBook(
        book_id=f"equity-watch-cash:{entity}", as_of=compiled,
        currency="USD", cash=cash, positions=(),
    )
    action = PositionActionSpec(
        action_id=f"watch:{entity}", kind="watch",
        description="Track the candidate prospectively while retaining cash.",
        target_weight=0.0, weight_delta=None, primitive_cost=0.0,
        irreversibility=0.0, evidence_refs=evidence_refs,
    )
    body = {
        "schema": PROPOSAL_SCHEMA,
        "proposal_id": proposal_id, "compiled_at": compiled,
        "lifecycle": InvestmentProfileLifecycle("operator", "draft").to_dict(),
        "entity": {"entity_id": entity, "entity_kind": "public_equity",
                   "name": candidate.get("name") or entity, "currency": "USD"},
        "candidate_identity": {
            "candidate_id": candidate["candidate_id"], "as_of": candidate["as_of"],
            "rank": candidate.get("rank"), "screen_status": candidate["screen_status"],
        },
        "evidence": evidence,
        "research": {
            "thesis": dict(normalized_dossier["thesis"]),
            "rival_view": dict(normalized_dossier["rival_view"]),
            "decisive_observation": dict(normalized_dossier["decisive_observation"]),
            "falsifiers": list(normalized_dossier["falsifiers"]),
        },
        "underwriting_coordinates": {
            "valuation": dict(row.get("valuation") or {}),
            "factor": dict(row.get("factor") or {}),
            "market_context_sha256": row.get("market_context_sha256"),
            "research_priority_is_expected_return": False,
        },
        "valuation_program": {
            "grammar_id": enumeration.get("grammar_id"),
            "grammar_version": enumeration.get("grammar_version"),
            "grammar_digest": enumeration.get("grammar_digest"),
            "enumeration_digest": enumeration.get("enumeration_digest"),
            "exhausted_within_scope": bool(enumeration.get("exhausted_within_scope")),
            "residuals": list(enumeration.get("residuals") or ()),
            "summary": dict(valuation.get("summary") or {}),
        },
        "modeled_state_price_grid": {
            **grid, "scope_boundary": grid_audit.get("scope_boundary"),
            "physical_probability_claim": False, "expected_return_claim": False,
        },
        "business_fingerprint": {
            "business_fingerprint_sha256": fingerprint_sha,
            "axis_coverage": dict(fingerprint.get("axis_coverage") or {}),
            "unknowns": list(fingerprint.get("unknowns") or ()),
            "cross_industry_comparability": dict(
                fingerprint.get("cross_industry_comparability") or {}
            ),
        },
        "strategy_frontier": frontier_projection,
        # Compiling exact current evidence is sufficient for an operator to start a
        # zero-weight watch. Research completeness belongs to the later position gate.
        "activation_eligible": True,
        "activation_blockers": [],
        "watch_activation": {
            "eligible": True,
            "target_weight": 0.0,
            "blockers": [],
        },
        "position_admission": {
            "eligible": not position_blockers,
            "blockers": position_blockers,
        },
        "research_obligations": position_blockers,
        "activation_blocker_details": blocker_details,
        "paper_policy": {
            "book": book.to_dict(), "action": action.to_dict(),
            "target_weight": 0.0, "cash_default": True,
            "portfolio_admission_allowed": False, "order_routing_allowed": False,
        },
        "required_operator_confirmation": f"ACTIVATE {proposal_id} FOR ZERO-WEIGHT PAPER WATCH",
        "next_activation": (
            "operator_review_and_activate_zero_weight_paper_watch"
        ),
        "authority": "paper_research_proposal_only",
        "capital_authority": False, "portfolio_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "proposal_sha256": stable_sha256(body)}


def _matching_frontier(
    root: Path, entity: str, candidate_leaf: str, dossier_sha: str, *,
    store: GoldenStore, owner: str, dossier_leaf: str,
) -> dict[str, Any] | None:
    if not research_evidence_is_admissible(
        store, owner=owner, target_leaf=dossier_leaf,
    ):
        return None
    rows = []
    for path in (root / "strategy_frontiers" / "results").glob(f"{entity.lower()}-*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        company = dict(payload.get("company") or {})
        if (company.get("candidate_leaf"), company.get("source_dossier_sha256")) == (
            candidate_leaf, dossier_sha,
        ):
            request_sha = str(company.get("strategy_frontier_request_sha256") or "")
            request_path = (
                root / "research_jobs" / "strategy_frontiers" / "requests"
                / f"{request_sha}.json"
            )
            request = (
                json.loads(request_path.read_text(encoding="utf-8"))
                if request_sha and request_path.exists() else {}
            )
            request_body = {
                key: value for key, value in request.items() if key != "request_sha256"
            }
            request_valid = bool(
                request.get("request_sha256") == request_sha
                and stable_sha256(request_body) == request_sha
                and request.get("candidate_leaf") == candidate_leaf
                and request.get("dossier_sha256") == dossier_sha
            )
            prior_epoch = (
                (request.get("prior_representation") or {}).get("evidence_epoch")
                if request_valid else None
            )
            rows.append((
                timestamp_key(str(prior_epoch or "1970-01-01T00:00:00Z")),
                request_valid,
                request_sha,
                str(payload.get("strategy_frontier_sha256") or ""),
                payload,
            ))
    return max(rows)[-1] if rows else None


def compile_workspace_equity_proposals(
    workspace: str | Path, *, compiled_at: str | None = None,
    paper_cash: float = 100_000.0,
) -> dict[str, Any]:
    """Audit every current qualified equity and compile all evidence-complete proposals."""
    root = Path(workspace).expanduser().resolve()
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("investment workspace configuration must be an object")
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    record = json.loads((root / "discovery" / "latest_record.json").read_text(encoding="utf-8"))
    underwriting = compile_workspace_underwriting_index(root)
    grid_audit = json.loads((root / "state_pricing" / "modeled-grid-audit.json").read_text(encoding="utf-8"))
    if grid_audit.get("discovery_run_sha256") != discovery.get("run_sha256"):
        grid_audit = audit_workspace_modeled_grids(root, materialize_limit=1)
    if grid_audit.get("discovery_run_sha256") != discovery.get("run_sha256"):
        raise ValueError("modeled payoff-grid audit differs from current discovery")
    owner = require_text(config.get("owner"), "workspace owner")
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    compiled = compiled_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []
    for candidate in discovery.get("candidates") or ():
        if candidate.get("entity_kind") != "public_equity" or candidate.get("screen_status") != "qualified":
            continue
        entity = str(candidate["entity_id"]).upper()
        candidate_leaf = (record.get("candidate_leaves") or {}).get(candidate["candidate_id"])
        missing = []
        if not candidate_leaf:
            missing.append("current_candidate_leaf_absent")
        else:
            candidate_record = store.get_leaf(candidate_leaf)
            if (candidate_record.get("object_kind"), candidate_record.get("payload")) != (
                "discovery_candidate", candidate,
            ):
                raise ValueError(f"golden candidate leaf differs from current discovery: {entity}")
        coverage_record = None
        if candidate_leaf:
            try:
                coverage_record = store.head(
                    owner, "research_evidence_coverage", f"research-coverage:{candidate_leaf}",
                )
            except KeyError:
                pass
        coverage = dict((coverage_record or {}).get("payload") or {})
        try:
            dossier_record = store.head(
                owner, "candidate_research_dossier", f"research:{entity}:{candidate_leaf}"
            ) if candidate_leaf else None
        except KeyError:
            dossier_record = None
            if coverage.get("covered") and coverage.get("prior_dossier_leaf"):
                dossier_record = store.get_leaf(str(coverage["prior_dossier_leaf"]))
                if (
                    dossier_record.get("owner") != owner
                    or dossier_record.get("object_kind") != "candidate_research_dossier"
                ):
                    raise ValueError(f"research coverage points outside owned dossiers: {entity}")
            else:
                missing.append(
                    f"research_coverage:{coverage.get('status') or 'candidate_bound_dossier_absent'}"
                )
        if dossier_record is not None:
            dossier_leaf = str(dossier_record["leaf_sha256"])
            admission = research_evidence_admissibility(
                store, owner=owner, target_leaf=dossier_leaf,
            )
            if not admission["admissible"]:
                missing.append(
                    "research_evidence_quarantined:"
                    + str(admission.get("reason_code") or dossier_leaf)
                )
        valuation_path = (candidate.get("valuation") or {}).get("artifact_path")
        if not valuation_path:
            missing.append("candidate_bound_valuation_envelope_absent")
        if not any(row.get("candidate_sha256") == candidate.get("candidate_sha256")
                   for row in underwriting.get("candidates") or ()):
            missing.append("candidate_bound_underwriting_coordinates_absent")
        if not any(row.get("candidate_sha256") == candidate.get("candidate_sha256")
                   for row in grid_audit.get("rows") or ()):
            missing.append("candidate_bound_modeled_grid_absent")
        if missing:
            rows.append({
                "entity_id": entity, "candidate_leaf": candidate_leaf,
                "candidate_sha256": candidate.get("candidate_sha256"),
                "status": "evidence_blocked", "activation_eligible": False,
                "blockers": sorted(set(missing)), "proposal": None,
            })
            continue

        dossier = dict(dossier_record["payload"])
        try:
            dossier = validate_research_dossier(dossier, expected_identity={
                "candidate_leaf": dossier.get("candidate_leaf"),
                "candidate_sha256": dossier.get("candidate_sha256"),
                "entity_id": entity, "as_of": dossier.get("as_of"),
            })
        except ValueError as error:
            rows.append({
                "entity_id": entity, "candidate_leaf": candidate_leaf,
                "candidate_sha256": candidate.get("candidate_sha256"),
                "status": "evidence_blocked", "activation_eligible": False,
                "blockers": [f"candidate_research_dossier_invalid:{error}"],
                "proposal": None,
            })
            continue
        dossier_sha = str(dossier["dossier_sha256"])
        bridged_coverage = coverage if dossier.get("candidate_leaf") != candidate_leaf else None
        frontier = _matching_frontier(
            root, entity, str(dossier["candidate_leaf"]), dossier_sha,
            store=store, owner=owner, dossier_leaf=str(dossier_record["leaf_sha256"]),
        )
        fingerprint = compile_business_fingerprint(
            company_quality=json.loads(
                (root / "quality" / f"{entity.lower()}.json").read_text(encoding="utf-8")
            ),
            research_dossier=dossier, strategy_frontier=frontier, compiled_at=compiled,
        )
        proposal = compile_inactive_equity_proposal(
            discovery_run=discovery, candidate_leaf=str(candidate_leaf),
            dossier=dossier, dossier_leaf=str(dossier_record["leaf_sha256"]),
            underwriting_index=underwriting,
            valuation_artifact=json.loads((root / str(valuation_path)).read_text(encoding="utf-8")),
            business_fingerprint=fingerprint, modeled_grid_audit=grid_audit,
            strategy_frontier=frontier,
            research_coverage=bridged_coverage,
            research_coverage_leaf=(
                (coverage_record or {}).get("leaf_sha256") if bridged_coverage else None
            ),
            compiled_at=compiled, paper_cash=paper_cash,
        )
        rows.append({
            "entity_id": entity, "candidate_leaf": candidate_leaf,
            "candidate_sha256": candidate.get("candidate_sha256"),
            "status": "eligible_proposal" if proposal["activation_eligible"] else "proposed_blocked",
            "activation_eligible": proposal["activation_eligible"],
            "blockers": list(proposal["activation_blockers"]), "proposal": proposal,
        })

    body = {
        "schema": AUDIT_SCHEMA,
        "compiled_at": canonical_timestamp(compiled, "equity proposal audit compiled_at"),
        "discovery_run_sha256": discovery.get("run_sha256"),
        "qualified_candidate_count": len(rows),
        "proposal_count": sum(row["proposal"] is not None for row in rows),
        "eligible_count": sum(row["activation_eligible"] for row in rows),
        "blocked_count": sum(not row["activation_eligible"] for row in rows),
        "rows": rows,
        "authority": "paper_research_proposal_audit_only",
        "capital_authority": False, "portfolio_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "audit_sha256": stable_sha256(body)}


def activate_equity_proposal(
    proposal: Mapping[str, Any], *, confirmation: str, operator_id: str,
    activated_at: str, audit_sha256: str | None = None,
) -> dict[str, Any]:
    """Approve an exact proposal as a zero-weight watch, never as a position."""
    verified, proposal_sha = _verified(
        proposal, schema=PROPOSAL_SCHEMA, digest_field="proposal_sha256",
        label="equity proposal",
    )
    if (verified.get("lifecycle") or {}).get("stage") != "draft":
        raise ValueError("equity activation requires an inactive draft")
    if verified.get("activation_eligible") is not True:
        raise ValueError("equity proposal is not activation eligible")
    if list(verified.get("activation_blockers") or ()):
        raise ValueError("equity proposal has activation blockers")
    watch = dict(verified.get("watch_activation") or {})
    if watch.get("eligible") is not True or float(watch.get("target_weight", -1)) != 0:
        raise ValueError("equity proposal is not eligible for a zero-weight watch")
    required = require_text(
        verified.get("required_operator_confirmation"), "required operator confirmation",
    )
    if confirmation != required:
        raise ValueError(f"operator confirmation must equal: {required}")
    occurred = canonical_timestamp(activated_at, "equity decision activated_at")
    if timestamp_key(occurred) < timestamp_key(str(verified["compiled_at"])):
        raise ValueError("equity activation cannot precede proposal compilation")
    operator = require_text(operator_id, "equity decision operator_id")
    policy = dict(verified.get("paper_policy") or {})
    book = dict(policy.get("book") or {})
    action = dict(policy.get("action") or {})
    if (
        float(policy.get("target_weight", -1)) != 0
        or policy.get("cash_default") is not True
        or book.get("positions") != []
        or action.get("kind") != "watch"
        or float(action.get("target_weight", -1)) != 0
    ):
        raise ValueError("equity paper-watch activation requires a cash-only zero-weight policy")
    policy.update({
        "portfolio_admission_allowed": False,
        "allocation_allowed": False,
        "order_routing_allowed": False,
    })
    decision_id = f"equity-paper-decision:{verified['entity']['entity_id']}:{proposal_sha[:16]}"
    body = {
        "schema": DECISION_SCHEMA, "decision_id": decision_id,
        "activated_at": occurred,
        "lifecycle": InvestmentProfileLifecycle("operator", "active").to_dict(),
        "operator_id": operator, "proposal_id": verified["proposal_id"],
        "proposal_sha256": proposal_sha, "entity": dict(verified["entity"]),
        "candidate_identity": dict(verified["candidate_identity"]),
        "evidence": dict(verified["evidence"]), "research": dict(verified["research"]),
        "underwriting_coordinates": dict(verified.get("underwriting_coordinates") or {}),
        "business_fingerprint": dict(verified.get("business_fingerprint") or {}),
        "strategy_frontier": verified.get("strategy_frontier"),
        "position_admission": dict(verified.get("position_admission") or {}),
        "research_obligations": list(verified.get("research_obligations") or ()),
        "paper_policy": policy,
        "watch_registry": {
            "eligible": True, "current_target_weight": 0.0,
            "position_admission_allowed": False, "allocation_allowed": False,
            "required_next_transition": "equity_specific_position_admission_review",
        },
        "operator_confirmation_sha256": stable_sha256(confirmation),
        "next_activation": "equity_specific_position_admission_review",
        "authority": "operator_paper_watch", "capital_authority": False,
        "portfolio_authority": False, "brokerage_authority": False,
    }
    decision_sha = stable_sha256(body)
    guard_refs = [
        f"proposal:{proposal_sha}", f"operator:{stable_sha256(operator)}",
    ]
    if audit_sha256:
        guard_refs.append(f"audit:{_digest(audit_sha256, 'equity proposal audit hash')}")
    transition = FunnelTransitionReceipt(
        transition_id=f"activate:{decision_id}", from_state="draft",
        event="activate_paper", to_state="active_paper", occurred_at=occurred,
        predecessor=FunnelObjectRef(
            "public_equity_paper_proposal", verified["proposal_id"], proposal_sha,
        ),
        successor=FunnelObjectRef(
            "public_equity_paper_decision", decision_id, decision_sha,
        ),
        guard_refs=tuple(guard_refs),
        context={"cash_default": True, "target_weight": 0.0},
    )
    return {**body, "decision_sha256": decision_sha, "transition": transition.to_dict()}


def activate_workspace_equity_paper_watch(
    workspace: str | Path, entity_id: str, *, proposal_sha256: str,
    confirmation: str, operator_id: str, activated_at: str | None = None,
) -> dict[str, Any]:
    """Persist approval only when the submitted SHA is the current audited proposal."""
    root = Path(workspace).expanduser().resolve()
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("investment workspace configuration must be an object")
    audit, audit_sha = _verified(
        json.loads((root / "paper_proposals" / "equities" / "latest.json").read_text(
            encoding="utf-8"
        )), schema=AUDIT_SCHEMA, digest_field="audit_sha256", label="equity proposal audit",
    )
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    if audit.get("discovery_run_sha256") != discovery.get("run_sha256"):
        raise ValueError("equity proposal audit is stale against current discovery")
    entity = require_text(entity_id, "equity activation entity_id").upper()
    matches = [
        row for row in audit.get("rows") or ()
        if str(row.get("entity_id") or "").upper() == entity
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("proposal"), Mapping):
        raise ValueError(f"current equity proposal is absent or ambiguous: {entity}")
    proposal = dict(matches[0]["proposal"])
    expected_sha = _digest(proposal_sha256, "equity activation proposal_sha256")
    if proposal.get("proposal_sha256") != expected_sha:
        raise ValueError("equity activation proposal hash is not current")
    decision = activate_equity_proposal(
        proposal, confirmation=confirmation, operator_id=operator_id,
        activated_at=(activated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")),
        audit_sha256=audit_sha,
    )
    destination = root / "paper_decisions" / "equities" / (
        f"{decision['decision_id'].replace(':', '--')}.json"
    )
    if destination.is_file():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        if (
            existing.get("decision_sha256") == decision.get("decision_sha256")
            or (
                existing.get("proposal_sha256") == expected_sha
                and existing.get("operator_id") == operator_id
            )
        ):
            return {
                "schema": ACTIVATION_SCHEMA, "ok": True, "status": "replayed",
                "artifact_path": destination.relative_to(root).as_posix(),
                "decision": existing, "audit_sha256": audit_sha,
                "capital_authority": False, "brokerage_authority": False,
            }
        raise ValueError("equity proposal was already activated by a different operator identity")
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    owner = require_text(config.get("owner"), "workspace owner")
    source_refs = tuple(
        f"sha256:{value}" for value in [expected_sha, *dict(decision["evidence"]).values()]
        if isinstance(value, str) and value
    )
    decision_leaf = store.append_leaf(GoldenLeaf(
        owner=owner, object_kind="public_equity_paper_decision",
        object_id=str(decision["decision_id"]), epoch=str(decision["decision_sha256"]),
        occurred_at=str(decision["activated_at"]), available_at=str(decision["activated_at"]),
        payload=decision, source_refs=source_refs,
    ))
    transition_leaf = record_funnel_transition(store, owner=owner, receipt=decision["transition"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return {
        "schema": ACTIVATION_SCHEMA, "ok": True, "status": "activated_paper_watch",
        "artifact_path": destination.relative_to(root).as_posix(), "decision": decision,
        "decision_leaf": decision_leaf, "transition_leaf": transition_leaf,
        "audit_sha256": audit_sha, "watch_registry_eligible": True,
        "target_weight": 0.0, "capital_authority": False, "brokerage_authority": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--paper-cash", type=float, default=100_000.0)
    args = parser.parse_args(argv)
    print(json.dumps(compile_workspace_equity_proposals(
        args.workspace, paper_cash=args.paper_cash,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACTIVATION_SCHEMA", "AUDIT_SCHEMA", "DECISION_SCHEMA", "PROPOSAL_SCHEMA",
    "activate_equity_proposal", "activate_workspace_equity_paper_watch",
    "compile_inactive_equity_proposal", "compile_workspace_equity_proposals",
]
