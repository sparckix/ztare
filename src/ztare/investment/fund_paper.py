"""Compile public-fund research into a zero-weight paper decision boundary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256

from .contracts import (
    InvestmentProfileLifecycle,
    PositionActionSpec,
    canonical_timestamp,
    require_finite,
    require_text,
    timestamp_key,
)
from .funnel import FunnelObjectRef, FunnelTransitionReceipt
from .golden_store import GoldenLeaf, GoldenStore, record_funnel_transition
from .paper import PaperBook
from .research_jobs import validate_research_dossier
from .watchlist import compile_fund_holdings_graph


PROPOSAL_SCHEMA = "jaggedthoughts-public-fund-paper-proposal-v1"
DECISION_SCHEMA = "jaggedthoughts-public-fund-paper-decision-v1"
AUDIT_SCHEMA = "jaggedthoughts-public-fund-paper-proposal-audit-v1"
ACTIVATION_SCHEMA = "jaggedthoughts-public-fund-paper-activation-v1"


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    try:
        int(digest, 16)
    except ValueError as error:
        raise ValueError(f"{label} must be a SHA-256 digest") from error
    return digest


def _verified_payload(payload: Mapping[str, Any], field: str, label: str) -> tuple[dict[str, Any], str]:
    body = dict(payload)
    declared = _digest(body.pop(field, ""), f"{label} {field}")
    if stable_sha256(body) != declared:
        raise ValueError(f"{label} content hash mismatch")
    return {**body, field: declared}, declared


def _leaf(record: Mapping[str, Any], kind: str) -> tuple[dict[str, Any], str]:
    if record.get("object_kind") != kind or not isinstance(record.get("payload"), Mapping):
        raise ValueError(f"expected a golden {kind} leaf")
    return dict(record["payload"]), _digest(record.get("leaf_sha256"), f"{kind} leaf")


def _candidate_evidence(
    candidate_record: Mapping[str, Any],
    watchlist_record: Mapping[str, Any],
    dossier_record: Mapping[str, Any],
    fund_holdings_graph: Mapping[str, Any] | None = None,
    research_coverage_record: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate, candidate_leaf = _leaf(candidate_record, "discovery_candidate")
    candidate, candidate_sha = _verified_payload(
        candidate, "candidate_sha256", "discovery candidate"
    )
    if candidate.get("schema") != "jaggedthoughts-discovery-candidate-v1":
        raise ValueError("fund proposals require a typed discovery candidate")
    if candidate.get("entity_kind") != "public_fund" or candidate.get("screen_status") != "qualified":
        raise ValueError("fund proposals require a qualified public-fund candidate")

    watchlist, watchlist_leaf = _leaf(watchlist_record, "opportunity_watchlist")
    watchlist, watchlist_sha = _verified_payload(
        watchlist, "watchlist_sha256", "opportunity watchlist"
    )
    expected_watchlist = {
        "watchlist_id": candidate.get("watchlist_id"),
        "as_of": candidate.get("as_of"),
    }
    observed_watchlist = {
        "watchlist_id": watchlist.get("watchlist_id"),
        "as_of": watchlist.get("as_of"),
    }
    if observed_watchlist != expected_watchlist:
        raise ValueError("candidate and watchlist identities differ")
    fund = next((
        dict(row) for row in watchlist.get("candidates", ())
        if isinstance(row, Mapping)
        and row.get("candidate_id") == candidate.get("watchlist_candidate_id")
        and row.get("entity_id") == candidate.get("entity_id")
    ), None)
    if fund is None or fund.get("screen_status") != "qualified":
        raise ValueError("candidate-era watchlist has no matching qualified fund")
    analysis, analysis_sha = _verified_payload(
        dict(fund.get("analysis") or {}), "analysis_sha256", "fund factor analysis"
    )
    if analysis_sha != candidate.get("factor_analysis_sha256"):
        raise ValueError("candidate and factor-analysis digests differ")
    valuation = dict(fund.get("valuation") or {})
    if valuation != candidate.get("valuation"):
        raise ValueError("candidate and fund valuation projections differ")
    if dict(fund.get("fund_evidence") or {}) != dict(candidate.get("fund_evidence") or {}):
        raise ValueError("candidate and fund evidence projections differ")

    graph, graph_sha = _verified_payload(
        dict(fund_holdings_graph or watchlist.get("fund_holdings_graph") or {}),
        "fund_holdings_graph_sha256", "fund holdings graph",
    )
    if graph.get("target_entity_id") != candidate.get("entity_id") or graph.get("as_of") != candidate.get("as_of"):
        raise ValueError("fund holdings graph crossed candidate identity or epoch")

    dossier, dossier_leaf = _leaf(dossier_record, "candidate_research_dossier")
    coverage_evidence: dict[str, str] = {}
    if research_coverage_record is None:
        dossier = validate_research_dossier(dossier, expected_identity={
            "candidate_leaf": candidate_leaf,
            "candidate_sha256": candidate_sha,
            "entity_id": candidate["entity_id"],
            "as_of": candidate["as_of"],
        })
        research_binding = "exact_candidate_dossier"
    else:
        coverage, coverage_leaf = _leaf(
            research_coverage_record, "research_evidence_coverage",
        )
        coverage, coverage_sha = _verified_payload(
            coverage, "coverage_sha256", "research evidence coverage",
        )
        if coverage.get("schema") != "jaggedthoughts-research-evidence-coverage-v1":
            raise ValueError("fund proposals require typed research evidence coverage")
        expected_coverage = {
            "candidate_leaf": candidate_leaf,
            "candidate_sha256": candidate_sha,
            "entity_id": candidate["entity_id"],
        }
        if {key: coverage.get(key) for key in expected_coverage} != expected_coverage:
            raise ValueError("research coverage crossed candidate identity")
        if not coverage.get("covered") or coverage.get("prior_dossier_leaf") != dossier_leaf:
            raise ValueError("research coverage does not admit its prior dossier")
        dossier = validate_research_dossier(dossier, expected_identity={
            key: dossier.get(key)
            for key in ("candidate_leaf", "candidate_sha256", "entity_id", "as_of")
        })
        if dossier.get("entity_id") != candidate["entity_id"]:
            raise ValueError("covered dossier crossed fund identity")
        coverage_evidence = {
            "research_coverage_leaf": coverage_leaf,
            "research_coverage_sha256": coverage_sha,
        }
        research_binding = "candidate_coverage_to_prior_dossier"
    if dossier_record.get("epoch") != dossier["dossier_sha256"]:
        raise ValueError("dossier leaf epoch is not its dossier digest")
    evidence = {
        "candidate_leaf": candidate_leaf,
        "candidate_sha256": candidate_sha,
        "watchlist_leaf": watchlist_leaf,
        "watchlist_sha256": watchlist_sha,
        "factor_analysis_sha256": analysis_sha,
        "fund_valuation_sha256": stable_sha256(valuation),
        "fund_holdings_graph_sha256": graph_sha,
        "dossier_leaf": dossier_leaf,
        "dossier_sha256": dossier["dossier_sha256"],
        **coverage_evidence,
    }
    return candidate, fund, dossier, {
        "evidence": evidence, "analysis": analysis, "graph": graph,
        "evidence_binding": {
            "watchlist": (
                "candidate_dependency"
                if watchlist_leaf in candidate.get("input_golden_leaves", ())
                else "verified_candidate_projection"
            ),
            "research": research_binding,
        },
    }


def compile_inactive_fund_proposal(
    *,
    candidate_record: Mapping[str, Any],
    watchlist_record: Mapping[str, Any],
    dossier_record: Mapping[str, Any],
    compiled_at: str,
    paper_cash: float = 100_000.0,
    latest_watchlist: Mapping[str, Any] | None = None,
    fund_holdings_graph: Mapping[str, Any] | None = None,
    research_coverage_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile exact fund evidence into an inactive, cash-only paper proposal."""
    candidate, fund, dossier, joined = _candidate_evidence(
        candidate_record, watchlist_record, dossier_record, fund_holdings_graph,
        research_coverage_record,
    )
    compiled = canonical_timestamp(compiled_at, "fund proposal compiled_at")
    if timestamp_key(compiled) < timestamp_key(str(dossier["generated_at"])):
        raise ValueError("fund proposal cannot precede its research dossier")
    cash = require_finite(paper_cash, "fund proposal paper_cash")
    if cash <= 0:
        raise ValueError("fund proposal paper_cash must be positive")

    evidence = joined["evidence"]
    analysis = joined["analysis"]
    graph = joined["graph"]
    coverage = dict(graph.get("target_coverage") or {})
    review_gaps = [
        "declared_factor_premiums_are_scenario_assumptions",
        "historical_residual_alpha_is_not_an_expected_return",
    ]
    if not graph.get("scope_closed"):
        review_gaps.append("fund_holdings_scope_open")
    if float(coverage.get("uncovered_weight") or 0) > 0:
        review_gaps.append("underlying_company_quality_lookthrough_incomplete")
    if graph.get("missing_fund_entity_ids"):
        review_gaps.append("peer_fund_holdings_coverage_incomplete")

    blockers: list[str] = []
    successor_evidence: dict[str, Any] | None = None
    if latest_watchlist is not None:
        latest, latest_sha = _verified_payload(
            latest_watchlist, "watchlist_sha256", "latest opportunity watchlist"
        )
        if latest.get("watchlist_id") != candidate.get("watchlist_id"):
            raise ValueError("latest watchlist identity differs from the candidate")
        successor_evidence = {"as_of": latest.get("as_of"), "watchlist_sha256": latest_sha}
        if timestamp_key(str(latest["as_of"])) > timestamp_key(str(candidate["as_of"])):
            blockers.append("candidate_precedes_latest_watchlist_epoch")
        else:
            current_fund = next((
                row for row in latest.get("candidates") or ()
                if isinstance(row, Mapping)
                and row.get("candidate_id") == candidate.get("watchlist_candidate_id")
                and row.get("entity_id") == candidate.get("entity_id")
            ), None)
            current_analysis = dict((current_fund or {}).get("analysis") or {})
            if (
                current_fund is None
                or current_fund.get("screen_status") != "qualified"
                or current_analysis.get("analysis_sha256")
                    != candidate.get("factor_analysis_sha256")
                or dict(current_fund.get("valuation") or {})
                    != dict(candidate.get("valuation") or {})
                or dict(current_fund.get("fund_evidence") or {})
                    != dict(candidate.get("fund_evidence") or {})
            ):
                blockers.append("candidate_fund_evidence_is_not_current")

    book = PaperBook(
        book_id=f"fund-watch-cash:{candidate['entity_id']}", as_of=compiled,
        currency="USD", cash=cash, positions=(),
    )
    action = PositionActionSpec(
        action_id=f"watch:{candidate['entity_id']}", kind="watch",
        description="Track the fund prospectively while retaining cash.",
        target_weight=0.0, weight_delta=None, primitive_cost=0.0, irreversibility=0.0,
        evidence_refs=tuple(f"sha256:{value}" for value in evidence.values()),
    )
    seed = {
        "candidate_leaf": evidence["candidate_leaf"],
        "dossier_leaf": evidence["dossier_leaf"],
        "watchlist_leaf": evidence["watchlist_leaf"],
    }
    proposal_id = f"fund-paper:{candidate['entity_id']}:{stable_sha256(seed)[:16]}"
    required_confirmation = f"ACTIVATE {proposal_id} FOR ZERO-WEIGHT PAPER WATCH"
    body = {
        "schema": PROPOSAL_SCHEMA,
        "proposal_id": proposal_id,
        "compiled_at": compiled,
        "lifecycle": InvestmentProfileLifecycle("operator", "draft").to_dict(),
        "entity": {
            "entity_id": candidate["entity_id"], "entity_kind": "public_fund",
            "name": candidate["name"], "currency": "USD",
        },
        "candidate_identity": {
            "candidate_id": candidate["candidate_id"], "as_of": candidate["as_of"],
            "screen_status": candidate["screen_status"], "rank": candidate.get("rank"),
        },
        "evidence": evidence,
        "evidence_binding": joined["evidence_binding"],
        "research": {
            "thesis": dict(dossier["thesis"]), "rival_view": dict(dossier["rival_view"]),
            "decisive_observation": dict(dossier["decisive_observation"]),
        },
        "fund_coordinates": {
            "factor": {
                "fit": dict(analysis.get("fit") or {}),
                "historical": dict(analysis.get("historical") or {}),
                "assumption_implied": dict(analysis.get("assumption_implied") or {}),
                "expected_return_claim": False,
            },
            "aggregate_valuation": dict(fund.get("valuation") or {}),
            "implementation": dict((fund.get("fund_evidence") or {}).get("metrics") or {}),
            "lookthrough": {
                "scope_closed": bool(graph.get("scope_closed")),
                "target_coverage": coverage,
                "missing_peer_funds": list(graph.get("missing_fund_entity_ids") or ()),
                "acquisition_frontier_entity_ids": list(
                    graph.get("acquisition_frontier_entity_ids") or ()
                ),
            },
        },
        "review_gaps": sorted(review_gaps),
        "activation_eligible": not blockers,
        "activation_blockers": sorted(blockers),
        "successor_evidence": successor_evidence,
        "paper_policy": {
            "book": book.to_dict(), "action": action.to_dict(),
            "target_weight": 0.0, "cash_default": True,
            "portfolio_admission_allowed": False,
        },
        "required_operator_confirmation": required_confirmation,
        "next_activation": (
            "refresh_discovery_and_rebind_research" if blockers
            else "operator_activate_zero_weight_paper_watch"
        ),
        "authority": "paper_research_only",
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "proposal_sha256": stable_sha256(body)}


def compile_workspace_fund_proposals(
    workspace: str | Path, *, compiled_at: str | None = None,
    paper_cash: float = 100_000.0,
) -> dict[str, Any]:
    """Audit current qualified funds and compile candidate-bound inactive drafts."""
    root = Path(workspace).expanduser().resolve()
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("investment workspace configuration must be an object")
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    receipt = json.loads((root / "discovery" / "latest_record.json").read_text(encoding="utf-8"))
    owner = require_text(config.get("owner"), "workspace owner")
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    compiled = compiled_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    rows = []
    for candidate in discovery.get("candidates") or ():
        if candidate.get("entity_kind") != "public_fund" or candidate.get("screen_status") != "qualified":
            continue
        entity = str(candidate["entity_id"]).upper()
        candidate_leaf = (receipt.get("candidate_leaves") or {}).get(candidate["candidate_id"])
        missing = []
        candidate_record = None
        watchlist_record = None
        dossier_record = None
        research_coverage_record = None
        if not candidate_leaf:
            missing.append("current_candidate_leaf_absent")
        else:
            candidate_record = store.get_leaf(candidate_leaf)
            if (candidate_record.get("object_kind"), candidate_record.get("payload")) != (
                "discovery_candidate", candidate,
            ):
                raise ValueError(f"golden candidate leaf differs from current discovery: {entity}")
            watchlists = []
            for leaf in candidate.get("input_golden_leaves") or ():
                record = store.get_leaf(str(leaf))
                if record.get("object_kind") == "opportunity_watchlist":
                    watchlists.append(record)
            if len(watchlists) != 1:
                try:
                    current_watchlist = store.head(
                        owner, "opportunity_watchlist", str(candidate["watchlist_id"]),
                    )
                except KeyError:
                    current_watchlist = None
                payload = (current_watchlist or {}).get("payload") or {}
                if payload.get("as_of") != candidate.get("as_of"):
                    missing.append("candidate_bound_opportunity_watchlist_absent")
                else:
                    watchlist_record = current_watchlist
            else:
                watchlist_record = watchlists[0]
            try:
                dossier_record = store.head(
                    owner, "candidate_research_dossier", f"research:{entity}:{candidate_leaf}",
                )
            except KeyError:
                try:
                    research_coverage_record = store.head(
                        owner, "research_evidence_coverage",
                        f"research-coverage:{candidate_leaf}",
                    )
                except KeyError:
                    missing.append("candidate_bound_fund_review_absent")
                else:
                    coverage = research_coverage_record.get("payload") or {}
                    if not coverage.get("covered"):
                        missing.append(
                            f"research_coverage:{coverage.get('status') or 'not_current'}"
                        )
                    else:
                        dossier_record = store.get_leaf(
                            require_text(
                                coverage.get("prior_dossier_leaf"),
                                "fund research coverage prior dossier leaf",
                            )
                        )
        if missing:
            rows.append({
                "entity_id": entity, "candidate_leaf": candidate_leaf,
                "candidate_sha256": candidate.get("candidate_sha256"),
                "status": "evidence_blocked", "activation_eligible": False,
                "blockers": sorted(set(missing)), "proposal": None,
            })
            continue

        dossier_payload = dict(dossier_record.get("payload") or {})
        try:
            validate_research_dossier(dossier_payload, expected_identity={
                key: dossier_payload.get(key)
                for key in ("candidate_leaf", "candidate_sha256", "entity_id", "as_of")
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

        latest_path = root / "watchlists" / "results" / f"{candidate['watchlist_id']}.json"
        latest = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.is_file() else None
        watchlist_payload = dict(watchlist_record.get("payload") or {})
        candidate_graph = compile_fund_holdings_graph(
            root=root,
            as_of=str(candidate["as_of"]),
            fund_entity_ids={
                str(row.get("entity_id") or "").upper()
                for row in watchlist_payload.get("candidates") or ()
                if isinstance(row, Mapping) and row.get("entity_id")
            },
            target_entity_id=entity,
        )
        proposal = compile_inactive_fund_proposal(
            candidate_record=candidate_record, watchlist_record=watchlist_record,
            dossier_record=dossier_record, compiled_at=compiled,
            paper_cash=paper_cash, latest_watchlist=latest,
            fund_holdings_graph=candidate_graph,
            research_coverage_record=research_coverage_record,
        )
        rows.append({
            "entity_id": entity, "candidate_leaf": candidate_leaf,
            "candidate_sha256": candidate.get("candidate_sha256"),
            "status": (
                "eligible_proposal" if proposal["activation_eligible"] else "proposed_blocked"
            ),
            "activation_eligible": proposal["activation_eligible"],
            "blockers": list(proposal["activation_blockers"]), "proposal": proposal,
        })

    body = {
        "schema": AUDIT_SCHEMA,
        "compiled_at": canonical_timestamp(compiled, "fund proposal audit compiled_at"),
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


def activate_fund_proposal(
    proposal: Mapping[str, Any], *, confirmation: str, operator_id: str, activated_at: str,
) -> dict[str, Any]:
    """Create an operator-policy paper watch without allocating or routing an order."""
    verified, proposal_sha = _verified_payload(proposal, "proposal_sha256", "fund proposal")
    if verified.get("schema") != PROPOSAL_SCHEMA:
        raise ValueError(f"fund activation requires {PROPOSAL_SCHEMA}")
    if (verified.get("lifecycle") or {}).get("stage") != "draft":
        raise ValueError("fund activation requires an inactive draft")
    blockers = list(verified.get("activation_blockers") or ())
    if blockers:
        raise ValueError(f"fund proposal has activation blockers: {blockers}")
    if verified.get("activation_eligible") is not True:
        raise ValueError("fund proposal is not activation eligible")
    required = require_text(
        verified.get("required_operator_confirmation"), "required operator confirmation"
    )
    if confirmation != required:
        raise ValueError(f"operator confirmation must equal: {required}")
    occurred = canonical_timestamp(activated_at, "fund decision activated_at")
    if timestamp_key(occurred) < timestamp_key(str(verified["compiled_at"])):
        raise ValueError("fund activation cannot precede proposal compilation")
    operator = require_text(operator_id, "fund decision operator_id")
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
        raise ValueError("fund paper-watch activation requires a cash-only zero-weight policy")
    decision_id = f"fund-paper-decision:{verified['entity']['entity_id']}:{proposal_sha[:16]}"
    policy.update({
        "implementation_review_allowed": True,
        "portfolio_admission_allowed": False,
        "allocation_allowed": False,
        "order_routing_allowed": False,
    })
    body = {
        "schema": DECISION_SCHEMA,
        "decision_id": decision_id,
        "activated_at": occurred,
        "lifecycle": InvestmentProfileLifecycle("operator", "active").to_dict(),
        "operator_id": operator,
        "proposal_id": verified["proposal_id"],
        "proposal_sha256": proposal_sha,
        "entity": dict(verified["entity"]),
        "candidate_identity": dict(verified["candidate_identity"]),
        "evidence": dict(verified["evidence"]),
        "research": dict(verified["research"]),
        "review_gaps_accepted_for_paper_watch": list(verified.get("review_gaps") or ()),
        "paper_policy": policy,
        "portfolio_eligibility": {
            "eligible": False, "implementation_review_allowed": True,
            "data_class": "operator", "reference_fixture": False,
            "current_target_weight": 0.0, "allocation_allowed": False,
            "required_next_transition": "fund_specific_portfolio_admission_review",
        },
        "operator_confirmation_sha256": stable_sha256(confirmation),
        "next_activation": "fund_specific_portfolio_admission_review",
        "authority": "operator_paper_watch",
        "capital_authority": False,
        "brokerage_authority": False,
    }
    decision_sha = stable_sha256(body)
    transition = FunnelTransitionReceipt(
        transition_id=f"activate:{decision_id}", from_state="draft",
        event="activate_paper", to_state="active_paper", occurred_at=occurred,
        predecessor=FunnelObjectRef("public_fund_paper_proposal", verified["proposal_id"], proposal_sha),
        successor=FunnelObjectRef("public_fund_paper_decision", decision_id, decision_sha),
        guard_refs=(f"proposal:{proposal_sha}", f"operator:{stable_sha256(operator)}"),
        context={"cash_default": True, "target_weight": 0.0},
    )
    return {**body, "decision_sha256": decision_sha, "transition": transition.to_dict()}


def activate_workspace_fund_paper_watch(
    workspace: str | Path, entity_id: str, *, proposal_sha256: str,
    confirmation: str, operator_id: str, activated_at: str | None = None,
) -> dict[str, Any]:
    """Persist one operator-policy activation from the current sealed audit."""
    root = Path(workspace).expanduser().resolve()
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("investment workspace configuration must be an object")
    audit_path = root / "paper_proposals" / "funds" / "latest.json"
    audit, audit_sha = _verified_payload(
        json.loads(audit_path.read_text(encoding="utf-8")), "audit_sha256", "fund proposal audit",
    )
    if audit.get("schema") != AUDIT_SCHEMA:
        raise ValueError(f"fund activation requires {AUDIT_SCHEMA}")
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    if audit.get("discovery_run_sha256") != discovery.get("run_sha256"):
        raise ValueError("fund proposal audit is stale against current discovery")
    entity = require_text(entity_id, "fund activation entity_id").upper()
    matches = [row for row in audit.get("rows") or () if str(row.get("entity_id") or "").upper() == entity]
    if len(matches) != 1 or not isinstance(matches[0].get("proposal"), Mapping):
        raise ValueError(f"current fund proposal is absent or ambiguous: {entity}")
    proposal = dict(matches[0]["proposal"])
    expected_sha = _digest(proposal_sha256, "fund activation proposal_sha256")
    if proposal.get("proposal_sha256") != expected_sha:
        raise ValueError("fund activation proposal hash is not current")
    occurred = activated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    decision = activate_fund_proposal(
        proposal, confirmation=confirmation, operator_id=operator_id, activated_at=occurred,
    )
    destination = root / "paper_decisions" / "funds" / f"{decision['decision_id'].replace(':', '--')}.json"
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
        raise ValueError("fund proposal was already activated by a different operator identity")
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    owner = require_text(config.get("owner"), "workspace owner")
    source_refs = tuple(
        f"sha256:{value}" for value in [expected_sha, *dict(decision["evidence"]).values()]
        if isinstance(value, str) and value
    )
    decision_leaf = store.append_leaf(GoldenLeaf(
        owner=owner, object_kind="public_fund_paper_decision",
        object_id=str(decision["decision_id"]), epoch=str(decision["decision_sha256"]),
        occurred_at=str(decision["activated_at"]), available_at=str(decision["activated_at"]),
        payload=decision, source_refs=source_refs,
    ))
    transition_leaf = record_funnel_transition(
        store, owner=owner, receipt=decision["transition"],
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return {
        "schema": ACTIVATION_SCHEMA, "ok": True, "status": "activated_paper_watch",
        "artifact_path": destination.relative_to(root).as_posix(), "decision": decision,
        "decision_leaf": decision_leaf, "transition_leaf": transition_leaf,
        "audit_sha256": audit_sha, "portfolio_eligible": False,
        "implementation_review_allowed": True,
        "target_weight": 0.0, "capital_authority": False, "brokerage_authority": False,
    }


def compile_workspace_fund_proposal(
    workspace: str | Path, entity_id: str, *, compiled_at: str | None = None,
    paper_cash: float = 100_000.0,
) -> dict[str, Any]:
    """Resolve a fund's exact candidate, watchlist, and dossier golden leaves."""
    root = Path(workspace).expanduser().resolve()
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    discovery = json.loads((root / "discovery" / "latest.json").read_text(encoding="utf-8"))
    receipt = json.loads((root / "discovery" / "latest_record.json").read_text(encoding="utf-8"))
    entity = require_text(entity_id, "fund entity_id").upper()
    candidate = next((
        row for row in discovery.get("candidates", ()) if row.get("entity_id") == entity
    ), None)
    if candidate is None:
        raise ValueError(f"discovery candidate absent: {entity}")
    candidate_leaf = (receipt.get("candidate_leaves") or {}).get(candidate["candidate_id"])
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    candidate_record = store.get_leaf(_digest(candidate_leaf, "candidate leaf"))
    watchlist_record = next((
        store.get_leaf(leaf) for leaf in candidate.get("input_golden_leaves", ())
        if store.get_leaf(leaf).get("object_kind") == "opportunity_watchlist"
    ), None)
    if watchlist_record is None:
        raise ValueError("candidate has no exact opportunity-watchlist leaf")
    dossier_record = store.head(
        require_text(config.get("owner"), "workspace owner"),
        "candidate_research_dossier", f"research:{entity}:{candidate_leaf}",
    )
    latest_path = root / "watchlists" / "results" / f"{candidate['watchlist_id']}.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.is_file() else None
    return compile_inactive_fund_proposal(
        candidate_record=candidate_record, watchlist_record=watchlist_record,
        dossier_record=dossier_record,
        compiled_at=compiled_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        paper_cash=paper_cash, latest_watchlist=latest,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entity_id")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--paper-cash", type=float, default=100_000.0)
    args = parser.parse_args(argv)
    print(json.dumps(compile_workspace_fund_proposal(
        args.workspace, args.entity_id, paper_cash=args.paper_cash,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACTIVATION_SCHEMA", "AUDIT_SCHEMA", "DECISION_SCHEMA", "PROPOSAL_SCHEMA",
    "activate_fund_proposal", "activate_workspace_fund_paper_watch",
    "compile_inactive_fund_proposal", "compile_workspace_fund_proposal",
    "compile_workspace_fund_proposals",
]
