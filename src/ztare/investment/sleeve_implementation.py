"""Bind public household sleeves to evidence-backed implementation substitutes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .household_allocation import (
    CAPITAL_MARKET_BASIS_SCHEMA,
    HOUSEHOLD_ALLOCATION_SCHEMA,
)
from .fund_implementation_review import (
    AUDIT_SCHEMA as FUND_IMPLEMENTATION_REVIEW_AUDIT_SCHEMA,
    DECISION_SCHEMA as FUND_IMPLEMENTATION_REVIEW_DECISION_SCHEMA,
    PROPOSAL_SCHEMA as FUND_IMPLEMENTATION_REVIEW_PROPOSAL_SCHEMA,
)
from .golden_store import GoldenStore
from .paper_watch import paper_watch_decisions as current_paper_watch_decisions
from .public_capital_market_basis import PUBLIC_SLEEVE_IDS, public_sleeve_proxies
from .universe_catalog import CATALOG_SCHEMA
from .watchlist import (
    FUND_CHOICE_FRONTIER_SCHEMA,
    FUND_HOLDINGS_GRAPH_SCHEMA,
    WATCHLIST_RESULT_SCHEMA,
)


SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA = (
    "jaggedthoughts-sleeve-implementation-frontier-v1"
)
IMPLEMENTATION_CANDIDATE_SCHEMA = "jaggedthoughts-implementation-candidate-v1"

_FUND_PROPOSAL_SCHEMA = "jaggedthoughts-public-fund-paper-proposal-v1"
_EQUITY_PROPOSAL_SCHEMA = "jaggedthoughts-public-equity-paper-proposal-v1"
_PAPER_DECISION_SCHEMAS = {
    "jaggedthoughts-public-fund-paper-decision-v1",
    "jaggedthoughts-public-equity-paper-decision-v1",
}


def _equity_catalog_index(
    raw: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]]]:
    if raw is None:
        return None, {}
    catalog = _sealed(
        raw, schema=CATALOG_SCHEMA, digest_field="catalog_sha256",
        label="public-market catalog",
    )
    indexed: dict[str, dict[str, Any]] = {}
    for source in catalog.get("securities") or ():
        row = dict(source)
        if row.get("entity_kind") != "public_equity":
            continue
        entity = str(row.get("symbol") or "").upper()
        if not entity:
            continue
        if entity in indexed:
            raise ValueError(f"multiple public-equity catalog rows for {entity}")
        indexed[entity] = row
    return catalog, indexed


def _equity_sleeve_fit(
    entity: str, *, catalog: Mapping[str, Any] | None,
    index: Mapping[str, Mapping[str, Any]],
) -> tuple[str | None, dict[str, Any] | None, list[str]]:
    row = dict(index.get(entity) or {})
    if catalog is None:
        return None, None, ["public_market_catalog_absent"]
    if not row:
        return None, None, ["public_equity_catalog_identity_absent"]
    if row.get("security_id") != f"public_equity:{entity}":
        return None, None, ["public_equity_catalog_identity_mismatch"]
    if row.get("security_kind") != "common_equity":
        return None, None, ["public_equity_common_security_identity_absent"]
    country = str(row.get("country") or "").strip()
    if not country:
        return None, None, ["catalog_country_proxy_absent"]
    sleeve_id = "us_equity" if country == "United States" else "international_equity"
    receipt = next((
        dict(source) for source in catalog.get("source_receipts") or ()
        if source.get("source_id") == row.get("source_id")
    ), {})
    if not receipt or receipt.get("raw_path") != row.get("source_path"):
        return None, None, ["catalog_source_receipt_unbound"]
    fit = {
        "sleeve_id": sleeve_id,
        "method": "catalog_country_proxy",
        "catalog_country": country,
        "available_at": row.get("available_at"),
        "availability_mode": row.get("availability_mode"),
        "source_id": row.get("source_id"),
        "security_id": row.get("security_id"),
        "source_path": row.get("source_path"),
        "source_content_sha256": receipt.get("content_sha256"),
        "catalog_sha256": catalog.get("catalog_sha256"),
        "use_boundary": (
            "The catalog country supports a broad sleeve proxy only; it does not "
            "establish revenue, operating, tax, or currency exposure."
        ),
    }
    return sleeve_id, fit, []


def _sealed(
    raw: Mapping[str, Any], *, schema: str, digest_field: str, label: str,
) -> dict[str, Any]:
    payload = dict(raw)
    if payload.get("schema") != schema:
        raise ValueError(f"{label} schema must be {schema}")
    digest = str(payload.pop(digest_field, ""))
    if len(digest) != 64 or stable_sha256(payload) != digest:
        raise ValueError(f"{label} content hash mismatch")
    return {**payload, digest_field: digest}


def _proposal_rows(
    value: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        if value.get("schema") in {_FUND_PROPOSAL_SCHEMA, _EQUITY_PROPOSAL_SCHEMA}:
            return [{"proposal": dict(value)}]
        nested = value.get("rows")
        if nested is None:
            nested = value.get("proposals")
        return _proposal_rows(nested) if nested is not None else [dict(value)]
    return [row for raw in value for row in _proposal_rows(raw)]


def _proposal_index(
    value: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in _proposal_rows(value):
        proposal = row.get("proposal") if isinstance(row.get("proposal"), Mapping) else {}
        entity = str(
            row.get("entity_id") or (proposal.get("entity") or {}).get("entity_id") or ""
        ).upper()
        if not entity:
            continue
        if entity in indexed:
            raise ValueError(f"multiple proposal rows for implementation candidate {entity}")
        indexed[entity] = row
    return indexed


def _proposal_gate(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {
            "status": "proposal_audit_absent", "eligible": False,
            "blockers": ["proposal_audit_absent"], "proposal_sha256": None,
        }
    proposal = dict(row["proposal"]) if isinstance(row.get("proposal"), Mapping) else None
    if proposal:
        schema = str(proposal.get("schema") or "")
        if schema not in {_FUND_PROPOSAL_SCHEMA, _EQUITY_PROPOSAL_SCHEMA}:
            raise ValueError("implementation proposal has an unsupported identity")
        proposal = _sealed(
            proposal, schema=schema, digest_field="proposal_sha256",
            label="implementation proposal",
        )
    blockers = list(map(str, row.get("blockers") or ()))
    if proposal:
        blockers.extend(map(str, proposal.get("activation_blockers") or ()))
    eligible = bool(
        proposal
        and not blockers
        and row.get("activation_eligible", proposal.get("activation_eligible", True))
    )
    return {
        "status": str(row.get("status") or ("eligible_proposal" if eligible else "blocked")),
        "eligible": eligible,
        "blockers": sorted(set(blockers)),
        "proposal_sha256": proposal.get("proposal_sha256") if proposal else None,
    }


def _implementation_review_gate(row: Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return _proposal_gate(None)
    proposal = _sealed(
        dict(row.get("proposal") or {}), schema=FUND_IMPLEMENTATION_REVIEW_PROPOSAL_SCHEMA,
        digest_field="proposal_sha256", label="fund implementation review proposal",
    )
    blockers = sorted(set(map(str, (
        *(row.get("blockers") or ()), *(proposal.get("activation_blockers") or ()),
    ))))
    eligible = bool(
        not blockers
        and row.get("activation_eligible", proposal.get("activation_eligible"))
    )
    return {
        "status": str(row.get("status") or ("eligible_proposal" if eligible else "blocked")),
        "eligible": eligible,
        "blockers": blockers,
        "proposal_sha256": proposal["proposal_sha256"],
        "comparison_program_sha256": proposal["comparison_program_sha256"],
        "review_only": True,
    }


def _decision_index(
    values: Iterable[Mapping[str, Any]] = (),
) -> dict[str, dict[str, Any]]:
    """Index active cash-only paper watches by the proposal they approved."""
    indexed: dict[str, dict[str, Any]] = {}
    for raw in values:
        source = dict(raw)
        source.pop("transition", None)
        source.pop("decision_path", None)
        schema = str(source.get("schema") or "")
        if schema not in _PAPER_DECISION_SCHEMAS:
            raise ValueError("implementation decision has an unsupported identity")
        decision = _sealed(
            source, schema=schema, digest_field="decision_sha256",
            label="implementation decision",
        )
        proposal_sha = str(decision.get("proposal_sha256") or "")
        policy = dict(decision.get("paper_policy") or {})
        lifecycle = dict(decision.get("lifecycle") or {})
        if (
            len(proposal_sha) != 64
            or lifecycle.get("stage") != "active"
            or float(policy.get("target_weight", -1)) != 0
            or policy.get("allocation_allowed") is not False
            or decision.get("capital_authority") is not False
            or decision.get("brokerage_authority") is not False
        ):
            raise ValueError("implementation decision must be an active zero-weight paper watch")
        if proposal_sha in indexed:
            raise ValueError(f"multiple paper watches for proposal {proposal_sha}")
        indexed[proposal_sha] = decision
    return indexed


def _implementation_review_decision_index(
    values: Iterable[Mapping[str, Any]] = (),
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for raw in values:
        decision = _sealed(
            raw, schema=FUND_IMPLEMENTATION_REVIEW_DECISION_SCHEMA,
            digest_field="decision_sha256", label="fund implementation review decision",
        )
        proposal_sha = str(decision.get("proposal_sha256") or "")
        policy = dict(decision.get("review_policy") or {})
        if (
            len(proposal_sha) != 64
            or (decision.get("lifecycle") or {}).get("stage") != "active"
            or float(policy.get("target_weight", -1)) != 0
            or decision.get("portfolio_candidate") is not False
            or decision.get("allocation_allowed") is not False
            or decision.get("order_routing_allowed") is not False
            or decision.get("capital_authority") is not False
            or decision.get("brokerage_authority") is not False
        ):
            raise ValueError("implementation review decision crossed its authority boundary")
        if proposal_sha in indexed:
            raise ValueError(f"multiple implementation reviews for proposal {proposal_sha}")
        indexed[proposal_sha] = decision
    return indexed


def _decision_match(
    decisions: Mapping[str, Mapping[str, Any]], *, gate: Mapping[str, Any],
    proposal_row: Mapping[str, Any] | None, entity_id: str,
) -> tuple[Mapping[str, Any] | None, str | None]:
    """Resolve a watch across timestamp-only proposal recompilations."""
    proposal_sha = str(gate.get("proposal_sha256") or "")
    if proposal_sha in decisions:
        return decisions[proposal_sha], "exact_proposal"
    if gate.get("review_only"):
        return None, None
    candidate_sha = str((proposal_row or {}).get("candidate_sha256") or "")
    if len(candidate_sha) != 64:
        return None, None
    matches = [
        decision for decision in decisions.values()
        if str((decision.get("entity") or {}).get("entity_id") or "").upper()
        == entity_id.upper()
        and str((decision.get("evidence") or {}).get("candidate_sha256") or "")
        == candidate_sha
    ]
    if len(matches) > 1:
        raise ValueError("multiple current paper watches bind the same candidate epoch")
    return (matches[0], "exact_candidate_epoch") if matches else (None, None)


def _implementation_candidate(
    *, identity: Mapping[str, Any], gate: Mapping[str, Any],
    evidence_ready: bool, decision: Mapping[str, Any] | None,
    evidence_gaps: Iterable[str], as_of: str | None, lineage: Mapping[str, Any],
    decision_match_basis: str | None = None,
) -> dict[str, Any]:
    activated = decision is not None
    review_only = bool(gate.get("review_only"))
    admitted = bool(activated and gate.get("eligible") and evidence_ready)
    body = {
        "schema": IMPLEMENTATION_CANDIDATE_SCHEMA,
        "identity": dict(identity),
        "as_of": as_of,
        "lineage": dict(lineage),
        "proposal_sha256": gate.get("proposal_sha256"),
        "paper_watch_proposal_sha256": (
            decision.get("proposal_sha256") if decision and not review_only else None
        ),
        "paper_watch_match_basis": decision_match_basis,
        "paper_decision_id": decision.get("decision_id") if decision and not review_only else None,
        "paper_decision_sha256": (
            decision.get("decision_sha256") if decision and not review_only else None
        ),
        "implementation_review_decision_id": (
            decision.get("decision_id") if decision and review_only else None
        ),
        "implementation_review_decision_sha256": (
            decision.get("decision_sha256") if decision and review_only else None
        ),
        "status": (
            "admitted_to_implementation_review" if admitted else
            "paper_watch_evidence_incomplete" if activated else
            "awaiting_implementation_review_activation" if gate.get("review_only") else
            "awaiting_paper_watch_activation" if gate.get("eligible") else
            "research_only"
        ),
        "paper_watch_activated": activated and not review_only,
        "implementation_review_activated": activated and review_only,
        "implementation_review_admitted": admitted,
        "current_target_weight": 0.0,
        "portfolio_candidate": False,
        "allocation_allowed": False,
        "order_routing_allowed": False,
        "evidence_gaps": sorted(set(map(str, evidence_gaps))),
        "required_next_transition": (
            "compile_instrument_return_downside_tax_currency_contract"
            if admitted else
            "complete_evidence_or_activate_implementation_review"
            if gate.get("review_only") else
            "complete_evidence_or_activate_paper_watch"
        ),
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "implementation_candidate_sha256": stable_sha256(body)}


def _identity(
    entity_id: str, vehicle_kind: str, evidence_epoch: str | None,
) -> dict[str, Any]:
    security_kind = vehicle_kind or "public_fund"
    return {
        "subject_id": entity_id.upper(),
        "subject_kind": "public_security",
        "entity_kind": "public_fund",
        "security_kind": security_kind,
        "implementation_epoch": evidence_epoch,
    }


def _overlap_rows(graph: Mapping[str, Any], entity_id: str) -> list[dict[str, Any]]:
    result = []
    for raw in graph.get("pairwise_overlap") or ():
        row = dict(raw)
        left = str(row.get("left_entity_id") or "").upper()
        right = str(row.get("right_entity_id") or "").upper()
        if entity_id not in {left, right}:
            continue
        result.append({
            "counterpart_entity_id": right if left == entity_id else left,
            "shared_holding_count": row.get("shared_holding_count"),
            "holding_jaccard_similarity": row.get("holding_jaccard_similarity"),
            "weighted_overlap": row.get("weighted_overlap"),
            "disclosed_active_share": row.get("disclosed_active_share"),
        })
    return sorted(result, key=lambda row: (
        -float(row.get("weighted_overlap") or 0), str(row["counterpart_entity_id"]),
    ))


def _instrument(
    alternative: Mapping[str, Any], *, frontier: Mapping[str, Any],
    graph: Mapping[str, Any], proposal_row: Mapping[str, Any] | None,
    review_row: Mapping[str, Any] | None,
    decisions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    entity = str(alternative.get("entity_id") or "").upper()
    metrics = dict((alternative.get("fund_evidence") or {}).get("metrics") or {})
    objectives = dict(alternative.get("objective_values") or {})
    expense_ratio = metrics.get("expense_ratio", objectives.get("expense_ratio"))
    snapshot = next((
        dict(row) for row in graph.get("snapshots") or ()
        if str(row.get("entity_id") or "").upper() == entity
    ), None)
    if proposal_row is not None and review_row is not None:
        raise ValueError(f"{entity} has both opportunity and implementation-review proposals")
    gate = (
        _proposal_gate(proposal_row) if proposal_row is not None
        else _implementation_review_gate(review_row)
    )
    gaps = []
    if not alternative.get("factor_exposures"):
        gaps.append("factor_exposure_evidence_absent")
    if expense_ratio is None:
        gaps.append("expense_ratio_absent")
    for metric_id in (
        "median_bid_ask_spread", "average_daily_volume_30d", "fund_net_assets",
    ):
        if metric_id not in metrics:
            gaps.append(f"{metric_id}_absent")
    if snapshot is None:
        gaps.append("holdings_snapshot_absent")
    if proposal_row is None and not graph.get("scope_closed"):
        gaps.append("peer_holdings_scope_open")
    if proposal_row is None and review_row is None:
        gaps.append("proposal_audit_absent")
    gaps.extend(f"proposal:{blocker}" for blocker in gate["blockers"])
    lookthrough = {
        "snapshot_path": (alternative.get("fund_evidence") or {}).get(
            "holdings_snapshot_path"
        ),
        "position_count": snapshot.get("position_count") if snapshot else None,
        "disclosed_weight": snapshot.get("disclosed_weight") if snapshot else None,
        "snapshot_sha256": snapshot.get("snapshot_sha256") if snapshot else None,
        "peer_scope_closed": bool(graph.get("scope_closed")),
    }
    if str(graph.get("target_entity_id") or "").upper() == entity:
        lookthrough["underlying_company_coverage"] = dict(graph.get("target_coverage") or {})
    evidence_epoch = str(frontier.get("as_of") or "") or None
    identity = _identity(
        entity, str(alternative.get("vehicle_kind") or "public_fund"), evidence_epoch,
    )
    decision, decision_match_basis = _decision_match(
        decisions, gate=gate, proposal_row=proposal_row or review_row, entity_id=entity,
    )
    admission = _implementation_candidate(
        identity=identity, gate=gate, evidence_ready=not gaps,
        decision=decision, decision_match_basis=decision_match_basis,
        evidence_gaps=gaps, as_of=evidence_epoch,
        lineage={
            "proposal_sha256": gate.get("proposal_sha256"),
            **({"comparison_program_sha256": gate["comparison_program_sha256"]}
               if gate.get("comparison_program_sha256") else {}),
            "fund_choice_frontier_sha256": frontier.get("fund_choice_frontier_sha256"),
            "fund_holdings_graph_sha256": graph.get("fund_holdings_graph_sha256"),
            "alternative_sha256": stable_sha256(dict(alternative)),
        },
    )
    return {
        "identity": identity,
        "name": alternative.get("name"),
        "category": alternative.get("category"),
        "research_eligible": True,
        "factor_fit": {
            "exposures": dict(alternative.get("factor_exposures") or {}),
            "residual_alpha_uncertainty": dict(
                alternative.get("residual_alpha_uncertainty") or {}
            ),
            "source_frontier_sha256": frontier.get("fund_choice_frontier_sha256"),
            "expected_return_claim": False,
        },
        "lookthrough_fit": lookthrough,
        "fees": {
            "expense_ratio": expense_ratio,
            "evidence_status": "observed" if expense_ratio is not None else "missing",
            "portfolio_turnover": metrics.get("portfolio_turnover"),
        },
        "liquidity": {
            "median_bid_ask_spread": metrics.get("median_bid_ask_spread"),
            "average_daily_volume_30d": metrics.get("average_daily_volume_30d"),
            "fund_net_assets": metrics.get("fund_net_assets"),
        },
        "overlap": _overlap_rows(graph, entity),
        "economic_coordinates": {
            key: objectives.get(key) for key in (
                "factor_implied_return", "earnings_power_margin", "implied_growth",
                "drawdown_resilience",
            )
        },
        "tax_currency_coordinates": {
            key: metrics.get(key) for key in (
                "distribution_tax_character", "foreign_withholding_tax_rate",
                "trading_currency", "underlying_currency_exposure",
            )
        },
        "holdings_coordinates": {
            key: metrics.get(key) for key in (
                "portfolio_holdings_count", "portfolio_top10_concentration",
                "portfolio_max_holding_weight", "portfolio_holdings_hhi",
                "portfolio_sector_hhi", "portfolio_top_sector_weight",
            )
        },
        "fund_frontier_status": alternative.get("frontier_status"),
        "nearest_substitutes": list(alternative.get("nearest_substitutes") or ()),
        "proposal_gate": gate,
        "implementation_candidate": admission,
        "evidence_gaps": sorted(set(gaps)),
        "evidence_ready": not gaps,
    }


def _proxy_instrument(
    proxy: Mapping[str, Any], *, evidence_epoch: str | None, basis_sha256: str | None,
) -> dict[str, Any]:
    identity = _identity(
        str(proxy["symbol"]), "exchange_traded_fund", evidence_epoch,
    )
    gaps = [
        "expense_ratio_absent", "fund_net_assets_absent", "holdings_snapshot_absent",
        "factor_exposure_evidence_absent", "median_bid_ask_spread_absent",
        "average_daily_volume_30d_absent", "proposal_audit_absent",
    ]
    return {
        "identity": identity,
        "name": f"{proxy['sleeve_id']} public basis proxy",
        "category": "broad_sleeve_proxy",
        "research_eligible": True,
        "basis_proxy": True,
        "factor_fit": {"exposures": {}, "expected_return_claim": False},
        "lookthrough_fit": {"snapshot_path": None, "peer_scope_closed": False},
        "fees": {"expense_ratio": None, "evidence_status": "missing"},
        "liquidity": {
            "median_bid_ask_spread": None, "average_daily_volume_30d": None,
            "fund_net_assets": None,
        },
        "overlap": [],
        "proposal_gate": _proposal_gate(None),
        "implementation_candidate": _implementation_candidate(
            identity=identity, gate=_proposal_gate(None), evidence_ready=False,
            decision=None, evidence_gaps=gaps, as_of=evidence_epoch,
            lineage={
                "basis_sha256": basis_sha256,
                "proxy_sha256": stable_sha256(dict(proxy)),
            },
        ),
        "evidence_gaps": gaps,
        "evidence_ready": False,
    }


def compile_sleeve_implementation_frontier(
    *,
    capital_market_basis: Mapping[str, Any] | None,
    household_allocation: Mapping[str, Any] | None = None,
    fund_watchlists: Iterable[Mapping[str, Any]] = (),
    fund_proposal_audit: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None = None,
    equity_proposal_audit: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None = None,
    paper_decisions: Iterable[Mapping[str, Any]] = (),
    fund_implementation_review_audit: Mapping[str, Any] | None = None,
    implementation_review_decisions: Iterable[Mapping[str, Any]] = (),
    security_catalog: Mapping[str, Any] | None = None,
    fund_watchlist_entity_scopes: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Compile implementation research without copying household weights or authority."""
    blockers: list[str] = []
    mandate_blockers: list[str] = []
    basis = None
    if capital_market_basis is None:
        blockers.append("public_capital_market_basis_absent")
    else:
        basis = _sealed(
            capital_market_basis, schema=CAPITAL_MARKET_BASIS_SCHEMA,
            digest_field="basis_sha256", label="capital-market basis",
        )
        asset_ids = tuple(str(row.get("asset_id") or "") for row in basis["asset_classes"])
        if set(asset_ids) != set(PUBLIC_SLEEVE_IDS) or len(asset_ids) != len(PUBLIC_SLEEVE_IDS):
            raise ValueError("implementation frontier requires the exact public sleeve universe")

    allocation = None
    policy_consumed = False
    active_sleeves: set[str] = set()
    if household_allocation is None:
        blockers.append("household_allocation_frontier_absent")
    else:
        allocation = _sealed(
            household_allocation, schema=HOUSEHOLD_ALLOCATION_SCHEMA,
            digest_field="allocation_sha256", label="household allocation frontier",
        )
        if basis is not None and allocation.get("basis_sha256") != basis.get("basis_sha256"):
            raise ValueError("household allocation and public basis identities differ")
        if allocation.get("status") == "paper_policy_ready":
            if basis is None:
                blockers.append("public_basis_unavailable_for_policy_binding")
            else:
                selected = allocation.get("selected_policy")
                weights = dict(selected.get("weights") or {}) if isinstance(selected, Mapping) else {}
                if set(weights) != set(PUBLIC_SLEEVE_IDS):
                    raise ValueError(
                        "selected household policy must cover the exact public sleeve universe"
                    )
                active_sleeves = {key for key, value in weights.items() if float(value) > 0}
                policy_consumed = True
        else:
            mandate_blockers = list(map(str, allocation.get("blockers") or ()))
            blockers.append("household_policy_not_ready")

    proposals = _proposal_index(fund_proposal_audit)
    review_proposals = _proposal_index(
        _sealed(
            fund_implementation_review_audit,
            schema=FUND_IMPLEMENTATION_REVIEW_AUDIT_SCHEMA,
            digest_field="audit_sha256", label="fund implementation review audit",
        ) if fund_implementation_review_audit is not None else None
    )
    decisions = {
        **_decision_index(paper_decisions),
        **_implementation_review_decision_index(implementation_review_decisions),
    }
    catalog, catalog_equities = _equity_catalog_index(security_catalog)
    instruments: dict[str, list[dict[str, Any]]] = {
        sleeve_id: [] for sleeve_id in PUBLIC_SLEEVE_IDS
    }
    unassigned: list[dict[str, Any]] = []
    frontier_refs: dict[str, list[str]] = {sleeve_id: [] for sleeve_id in PUBLIC_SLEEVE_IDS}
    for raw_watchlist in fund_watchlists:
        watchlist = _sealed(
            raw_watchlist, schema=WATCHLIST_RESULT_SCHEMA,
            digest_field="watchlist_sha256", label="fund watchlist",
        )
        entity_scope = (
            {str(value).upper() for value in fund_watchlist_entity_scopes[
                watchlist["watchlist_sha256"]
            ]}
            if fund_watchlist_entity_scopes is not None
            and watchlist["watchlist_sha256"] in fund_watchlist_entity_scopes
            else None
        )
        frontier = _sealed(
            dict(watchlist.get("fund_choice_frontier") or {}),
            schema=FUND_CHOICE_FRONTIER_SCHEMA,
            digest_field="fund_choice_frontier_sha256", label="fund choice frontier",
        )
        graph = _sealed(
            dict(watchlist.get("fund_holdings_graph") or {}),
            schema=FUND_HOLDINGS_GRAPH_SCHEMA,
            digest_field="fund_holdings_graph_sha256", label="fund holdings graph",
        )
        available_entities = {
            str(row.get("entity_id") or "").upper()
            for row in frontier.get("alternatives") or ()
            if row.get("entity_id")
        }
        if entity_scope is not None and not entity_scope <= available_entities:
            raise ValueError("fund watchlist entity scope crosses its evidence")
        if (
            frontier.get("implementation_sleeve_id") is not None
            or watchlist.get("implementation_sleeve_id") is not None
        ):
            raise ValueError(
                "implementation sleeve identity cannot be inherited from a mixed watchlist"
            )
        for alternative in frontier.get("alternatives") or ():
            entity_id = str(alternative.get("entity_id") or "").upper()
            if entity_scope is not None and entity_id not in entity_scope:
                continue
            sleeve_id = alternative.get("implementation_sleeve_id")
            if sleeve_id is None:
                unassigned.append({
                "identity": _identity(
                    str(alternative.get("entity_id") or ""),
                    str(alternative.get("vehicle_kind") or "public_fund"),
                    str(frontier.get("as_of") or "") or None,
                ),
                "source_frontier_sha256": frontier["fund_choice_frontier_sha256"],
                "evidence_gap": "sleeve_identity_unbound",
                })
                continue
            if sleeve_id not in PUBLIC_SLEEVE_IDS:
                raise ValueError(f"unknown public implementation sleeve: {sleeve_id}")
            if not alternative.get("implementation_sleeve_source_refs"):
                raise ValueError(
                    f"{alternative.get('entity_id')} implementation sleeve is unsourced"
                )
            frontier_refs[str(sleeve_id)].append(
                frontier["fund_choice_frontier_sha256"]
            )
            instruments[str(sleeve_id)].append(_instrument(
                alternative, frontier=frontier, graph=graph,
                proposal_row=proposals.get(str(alternative.get("entity_id") or "").upper()),
                review_row=review_proposals.get(
                    str(alternative.get("entity_id") or "").upper()
                ),
                decisions=decisions,
            ))

    for row in _proposal_rows(equity_proposal_audit):
        proposal = row.get("proposal") if isinstance(row.get("proposal"), Mapping) else {}
        entity = str(
            row.get("entity_id") or (proposal.get("entity") or {}).get("entity_id") or ""
        ).upper()
        if entity:
            candidate_identity = dict(proposal.get("candidate_identity") or {})
            evidence_epoch = str(candidate_identity.get("as_of") or "") or None
            proposal_evidence = dict(proposal.get("evidence") or {})
            identity = {
                "subject_id": entity, "subject_kind": "public_security",
                "entity_kind": "public_equity", "security_kind": "common_equity",
                "implementation_epoch": evidence_epoch,
            }
            gate = _proposal_gate(row)
            sleeve_id, sleeve_fit, fit_gaps = _equity_sleeve_fit(
                entity, catalog=catalog, index=catalog_equities,
            )
            if entity in catalog_equities:
                identity["security_kind"] = catalog_equities[entity]["security_kind"]
            lineage = {
                "proposal_sha256": gate.get("proposal_sha256"),
                "candidate_sha256": row.get("candidate_sha256"),
                "proposal_evidence_sha256": (
                    stable_sha256(proposal_evidence) if proposal_evidence else None
                ),
                "catalog_sha256": catalog.get("catalog_sha256") if catalog else None,
                "catalog_security_sha256": (
                    stable_sha256(catalog_equities[entity])
                    if entity in catalog_equities else None
                ),
            }
            evidence_epoch = max(filter(None, (
                evidence_epoch,
                str((sleeve_fit or {}).get("available_at") or "") or None,
            )), default=None)
            identity["implementation_epoch"] = evidence_epoch
            decision, decision_match_basis = _decision_match(
                decisions, gate=gate, proposal_row=row, entity_id=entity,
            )
            admission = _implementation_candidate(
                identity=identity, gate=gate, evidence_ready=not fit_gaps,
                decision=decision, decision_match_basis=decision_match_basis,
                evidence_gaps=fit_gaps, as_of=evidence_epoch, lineage=lineage,
            )
            if sleeve_id is None:
                unassigned.append({
                    "identity": identity,
                    "proposal_status": row.get("status"),
                    "evidence_gap": "broad_sleeve_fit_unbound",
                    "evidence_gaps": fit_gaps,
                    "implementation_candidate": admission,
                })
                continue
            instruments[sleeve_id].append({
                "identity": identity,
                "name": catalog_equities[entity].get("name"),
                "category": catalog_equities[entity].get("sector"),
                "research_eligible": True,
                "basis_proxy": False,
                "sleeve_fit": sleeve_fit,
                "factor_fit": {"exposures": {}, "expected_return_claim": False},
                "lookthrough_fit": {"applicable": False},
                "fees": {"expense_ratio": None, "evidence_status": "not_applicable"},
                "liquidity": {
                    "quoted_volume": catalog_equities[entity].get("volume"),
                    "evidence_status": "retrieval_only",
                },
                "overlap": [],
                "proposal_gate": gate,
                "implementation_candidate": admission,
                "evidence_gaps": [],
                "evidence_ready": True,
            })

    proxies = {row["sleeve_id"]: row for row in public_sleeve_proxies()}
    sleeves = []
    for sleeve_id in PUBLIC_SLEEVE_IDS:
        candidates = sorted(
            instruments[sleeve_id], key=lambda row: str(row["identity"]["subject_id"]),
        )
        proxy = _proxy_instrument(
            proxies[sleeve_id],
            evidence_epoch=(str(basis.get("as_of") or "") or None) if basis else None,
            basis_sha256=basis.get("basis_sha256") if basis else None,
        )
        eligible = [proxy, *candidates]
        nondominated = [
            row["identity"] for row in candidates
            if row.get("fund_frontier_status") == "frontier"
        ]
        if not nondominated:
            nondominated = [proxy["identity"]]
        sleeve_active = policy_consumed and sleeve_id in active_sleeves
        for row in eligible:
            row["policy_implementation_eligible"] = bool(
                sleeve_active
                and row.get("evidence_ready")
                and row["implementation_candidate"]["implementation_review_admitted"]
            )
        sleeves.append({
            "sleeve_id": sleeve_id,
            "policy_status": (
                "selected" if sleeve_active else
                "not_selected" if policy_consumed else "mandate_blocked"
            ),
            "basis_proxy": proxy["identity"],
            "eligible_instruments": eligible,
            "nondominated_substitutes": nondominated,
            "dominance_authority": (
                "fund_choice_frontier_only" if frontier_refs[sleeve_id]
                else "basis_proxy_fallback_only"
            ),
            "source_frontier_sha256s": sorted(set(frontier_refs[sleeve_id])),
            "evidence_gaps": sorted(set(
                gap for row in eligible for gap in row.get("evidence_gaps") or ()
            )),
        })

    body = {
        "schema": SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA,
        "as_of": (
            allocation.get("as_of") if allocation else
            basis.get("as_of") if basis else None
        ),
        "basis_sha256": basis.get("basis_sha256") if basis else None,
        "allocation_sha256": allocation.get("allocation_sha256") if allocation else None,
        "policy_consumed": policy_consumed,
        "status": "policy_bound" if policy_consumed else "evidence_only",
        "mandate_blockers": mandate_blockers,
        "implementation_blockers": sorted(set(blockers)),
        "sleeves": sleeves,
        "unassigned_evidence": sorted(unassigned, key=lambda row: (
            str((row.get("identity") or {}).get("entity_kind") or ""),
            str((row.get("identity") or {}).get("subject_id") or ""),
        )),
        "paper_watch_activation_count": len(decisions),
        "implementation_review_admitted_count": sum(
            row["implementation_candidate"]["implementation_review_admitted"]
            for sleeve in sleeves for row in sleeve["eligible_instruments"]
        ),
        "implementation_candidate_schema": IMPLEMENTATION_CANDIDATE_SCHEMA,
        "subject_kind_registry": [
            {
                "subject_kind": "public_security", "entity_kind": "public_fund",
                "security_kinds": ["exchange_traded_fund", "mutual_fund", "public_fund"],
                "supported": True,
            },
            {
                "subject_kind": "public_security", "entity_kind": "public_equity",
                "security_kinds": ["common_equity"], "supported": True,
                "implementation_condition": "exact_broad_sleeve_fit_required",
            },
            {
                "subject_kind": "fund_interest", "entity_kind": "private_fund_interest",
                "security_kinds": ["private_fund_interest"], "supported": False,
                "evidence_gap": "private_fund_interest_adapter_not_implemented",
            },
        ],
        "expected_return_invented": False,
        "authority": "implementation_research_projection_only",
        "capital_authority": False,
        "brokerage_authority": False,
    }
    return {**body, "sleeve_implementation_sha256": stable_sha256(body)}


def compile_workspace_sleeve_implementation_frontier(
    workspace: str | Path,
) -> dict[str, Any]:
    """Project current workspace evidence through the sleeve bridge."""
    root = Path(workspace).expanduser().resolve()

    def read(path: Path) -> dict[str, Any] | None:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    acquired = read(root / "household" / "capital_market_basis" / "latest.json")
    basis = None
    if acquired:
        basis = (
            acquired.get("capital_market_basis")
            if acquired.get("schema") != CAPITAL_MARKET_BASIS_SCHEMA else acquired
        )
    latest_build = read(root / "state" / "latest_build.json") or {}
    watchlists = []
    watchlist_entity_scopes: dict[str, set[str]] = {}
    for status in latest_build.get("watchlist_statuses") or ():
        if (
            not isinstance(status, Mapping)
            or status.get("status") != "compiled"
            or len(str(status.get("golden_leaf") or "")) != 64
            or not status.get("result_path")
        ):
            continue
        path = (root / str(status["result_path"])).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("watchlist result path escapes the workspace") from error
        watchlist = read(path)
        if watchlist is None or watchlist.get("watchlist_id") != status.get("watchlist_id"):
            raise ValueError("compiled watchlist status and result identity differ")
        watchlists.append(watchlist)
        watchlist_entity_scopes[str(watchlist["watchlist_sha256"])] = {
            str(row.get("entity_id") or "").upper()
            for row in (watchlist.get("fund_choice_frontier") or {}).get(
                "alternatives", ()
            )
            if row.get("entity_id")
        }
    latest_fund = read(root / "paper_proposals" / "funds" / "latest.json")
    fund_proposals = [latest_fund] if latest_fund else [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "paper_proposals" / "funds").glob("*.json"))
    ]
    decisions = current_paper_watch_decisions(root)
    # A paper watch owns the immutable evidence epoch it activated.  Keep that
    # watchlist in the projection even after a later screen drops the fund.
    current_watchlist_hashes = {
        str(row.get("watchlist_sha256") or "") for row in watchlists
    }
    store: GoldenStore | None = None
    for decision in decisions:
        if (decision.get("entity") or {}).get("entity_kind") != "public_fund":
            continue
        entity = str((decision.get("entity") or {}).get("entity_id") or "").upper()
        if not entity:
            raise ValueError("active fund paper watch has no fund identity")
        evidence = dict(decision.get("evidence") or {})
        watchlist_sha = str(evidence.get("watchlist_sha256") or "")
        for scope in watchlist_entity_scopes.values():
            scope.discard(entity)
        if watchlist_sha in current_watchlist_hashes:
            watchlist_entity_scopes[watchlist_sha].add(entity)
            continue
        leaf_sha = str(evidence.get("watchlist_leaf") or "")
        if len(leaf_sha) != 64:
            raise ValueError("active fund paper watch has no immutable watchlist leaf")
        if store is None:
            store = GoldenStore(root / "state" / "golden_store.sqlite3")
        leaf = store.get_leaf(leaf_sha)
        if (
            leaf.get("object_kind") != "opportunity_watchlist"
            or leaf.get("payload_schema") != WATCHLIST_RESULT_SCHEMA
        ):
            raise ValueError("active fund paper watch binds a non-watchlist leaf")
        watchlist = dict(leaf.get("payload") or {})
        if watchlist.get("watchlist_sha256") != evidence.get("watchlist_sha256"):
            raise ValueError("active fund paper watch crossed its watchlist evidence")
        alternatives = {
            str(row.get("entity_id") or "").upper()
            for row in (watchlist.get("fund_choice_frontier") or {}).get(
                "alternatives", ()
            )
            if row.get("entity_id")
        }
        if entity not in alternatives:
            raise ValueError("active fund paper watch is absent from its watchlist evidence")
        watchlists.append(watchlist)
        watchlist_entity_scopes[watchlist_sha] = {entity}
        current_watchlist_hashes.add(str(watchlist["watchlist_sha256"]))
    review_audit = read(
        root / "paper_proposals" / "fund_implementation_reviews" / "latest.json"
    )
    review_decisions = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(
            (root / "paper_decisions" / "fund_implementation_reviews").glob("*.json")
        )
    ]
    return compile_sleeve_implementation_frontier(
        capital_market_basis=basis,
        household_allocation=read(root / "household" / "allocation" / "latest.json"),
        fund_watchlists=watchlists,
        fund_proposal_audit=fund_proposals,
        equity_proposal_audit=read(root / "paper_proposals" / "equities" / "latest.json"),
        paper_decisions=decisions,
        fund_implementation_review_audit=review_audit,
        implementation_review_decisions=review_decisions,
        security_catalog=read(root / "universe" / "catalog-latest.json"),
        fund_watchlist_entity_scopes=watchlist_entity_scopes,
    )


__all__ = [
    "IMPLEMENTATION_CANDIDATE_SCHEMA",
    "SLEEVE_IMPLEMENTATION_FRONTIER_SCHEMA",
    "compile_sleeve_implementation_frontier",
    "compile_workspace_sleeve_implementation_frontier",
]
