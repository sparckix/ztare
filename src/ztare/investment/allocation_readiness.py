"""Read-only join from research priority to paper-allocation lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .capital_cycle import operator_forecast_decisions
from .contracts import canonical_timestamp
from .paper_watch import (
    paper_watch_decisions as current_paper_watch_decisions,
    verify_paper_watch_decision,
)


READINESS_SCHEMA = "jaggedthoughts-allocation-readiness-v1"


def _verified(raw: Mapping[str, Any], schema: str, digest_field: str) -> dict[str, Any]:
    row = dict(raw)
    if row.get("schema") != schema:
        raise ValueError(f"expected {schema}")
    claimed = str(row.pop(digest_field, ""))
    if not claimed or stable_sha256(row) != claimed:
        raise ValueError(f"{schema} content hash mismatch")
    return {**row, digest_field: claimed}


def _latest_decisions(decisions: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for raw in decisions:
        source = dict(raw); source.pop("decision_path", None)
        row = _verified(source, "jaggedthoughts-investment-decision-v1", "decision_record_sha256")
        lifecycle = row.get("profile_lifecycle") or {}
        if lifecycle.get("data_class") != "operator" or lifecycle.get("stage") not in {"draft", "active"}:
            continue
        entity = str((row.get("entity") or {}).get("entity_id") or "").upper()
        if not entity:
            continue
        if entity not in latest or (str(row.get("as_of") or ""), str(row["decision_id"])) > (
            str(latest[entity].get("as_of") or ""), str(latest[entity]["decision_id"]),
        ):
            latest[entity] = row
    return latest


def _latest_paper_watches(
    decisions: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for raw in decisions:
        source = dict(raw); source.pop("decision_path", None)
        row = verify_paper_watch_decision(source)
        entity = str((row.get("entity") or {}).get("entity_id") or "").upper()
        if not entity:
            continue
        if entity not in latest or (
            str(row.get("activated_at") or ""), str(row["decision_id"])
        ) > (str(latest[entity].get("activated_at") or ""), str(latest[entity]["decision_id"])):
            latest[entity] = row
    return latest


def _run_ids(rows: Iterable[Mapping[str, Any]], *, schema: str, digest_field: str) -> list[dict[str, Any]]:
    return [_verified(row, schema, digest_field) for row in rows]


def _activation(
    *, entity_kind: str, screen: str, rank_eligible: bool, dossier: bool,
    decision: Mapping[str, Any] | None, lineage_exact: bool,
    portfolio_candidate: bool, allocated: bool,
    fund_proposal: Mapping[str, Any] | None = None,
    paper_watch: Mapping[str, Any] | None = None,
    paper_watch_lineage_exact: bool = False,
    instrument_admission: Mapping[str, Any] | None = None,
) -> tuple[str, list[str], str]:
    gaps: list[str] = []
    state = "screened"
    if not rank_eligible:
        gaps.append("underwriting_research_rank_ineligible")
    if screen != "qualified":
        gaps.append(f"discovery_screen_{screen}")
        return state, gaps, "research_or_repair_screen"
    if paper_watch is not None:
        if not paper_watch_lineage_exact:
            gaps.append("paper_watch_not_bound_to_current_candidate")
            return state, gaps, "refresh_candidate_bound_research_and_paper_watch"
        admission = dict(
            (instrument_admission or {}).get("eligibility")
            or paper_watch.get("position_admission")
            or paper_watch.get("portfolio_eligibility") or {}
        )
        gaps.extend(f"instrument_admission:{value}" for value in admission.get("blockers") or ())
        admitted = (
            admission.get("research_paper_portfolio_candidate") is True
            if instrument_admission is not None else admission.get("eligible") is True
        )
        if not admitted:
            gaps.append("instrument_portfolio_admission_absent")
            return "active_paper", gaps, "compile_instrument_portfolio_admission_contract"
        if instrument_admission is not None and not portfolio_candidate:
            gaps.append("household_policy_rival_not_selected")
            return "portfolio_candidate", gaps, "review_household_policy_rivals"
        if not portfolio_candidate:
            gaps.append("active_paper_watch_not_in_current_portfolio_assembly")
            return "active_paper", gaps, "compile_portfolio_with_admitted_instrument"
        if not allocated:
            gaps.append("portfolio_frontier_selected_zero_weight")
            return "portfolio_candidate", gaps, "review_portfolio_decline_or_binding_constraint"
        return "allocated_paper", gaps, "await_or_settle_point_in_time_outcome"
    if entity_kind == "public_fund":
        if fund_proposal is None:
            if not dossier:
                gaps.append("candidate_bound_fund_review_absent")
                return state, gaps, "complete_candidate_bound_fund_review"
            gaps.append("candidate_bound_fund_proposal_absent")
            return state, gaps, "compile_candidate_bound_inactive_fund_proposal"
        blockers = list(map(str, fund_proposal.get("blockers") or ()))
        if not isinstance(fund_proposal.get("proposal"), Mapping):
            blockers.append("candidate_bound_inactive_proposal_absent")
        if blockers or not fund_proposal.get("activation_eligible"):
            gaps.extend(f"fund_paper_proposal:{value}" for value in blockers)
            return state, gaps, "repair_fund_proposal_evidence"
        if not dossier:
            gaps.append("candidate_bound_fund_review_absent")
            return state, gaps, "complete_candidate_bound_fund_review"
        gaps.append("paper_watch_activation_required")
        return "draft", gaps, "apply_manual_or_standing_zero_weight_watch_policy"
    if not dossier:
        gaps.append("candidate_bound_research_dossier_absent")
    if decision is None:
        gaps.append("candidate_bound_operator_draft_absent")
        return state, gaps, "research_then_create_inactive_draft"
    if not lineage_exact:
        gaps.append("operator_decision_not_bound_to_current_candidate")
        return state, gaps, "create_candidate_bound_inactive_draft"
    stage = str((decision.get("profile_lifecycle") or {}).get("stage") or "")
    state = "draft" if stage == "draft" else "active_paper"
    if stage == "draft":
        gaps.append("paper_watch_activation_required")
        return state, gaps, "apply_manual_or_standing_zero_weight_watch_policy"
    if not portfolio_candidate:
        gaps.append("active_paper_decision_not_in_current_portfolio_assembly")
        return state, gaps, "compile_portfolio_with_active_decision"
    state = "allocated_paper" if allocated else "portfolio_candidate"
    if not allocated:
        gaps.append("portfolio_frontier_selected_zero_weight")
        return state, gaps, "review_portfolio_decline_or_binding_constraint"
    return state, gaps, "await_or_settle_point_in_time_outcome"


def compile_allocation_readiness(
    *, opportunity_book: Mapping[str, Any], underwriting_index: Mapping[str, Any],
    rank_program_input: Mapping[str, Any],
    decisions: Iterable[Mapping[str, Any]] = (), portfolio_assembly: Mapping[str, Any] | None = None,
    portfolio_policy_runs: Iterable[Mapping[str, Any]] = (),
    portfolio_policy_settlement_run_ids: Iterable[str] = (),
    closed_book_runs: Iterable[Mapping[str, Any]] = (),
    closed_book_settlement_run_ids: Iterable[str] = (),
    fund_watchlists: Iterable[Mapping[str, Any]] = (),
    fund_proposal_audit: Mapping[str, Any] | None = None,
    paper_watch_decisions: Iterable[Mapping[str, Any]] = (),
    instrument_portfolio_admissions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile exact lifecycle readiness without assigning weights or return forecasts."""
    book = _verified(opportunity_book, "jaggedthoughts-opportunity-book-v1", "book_sha256")
    underwriting = _verified(
        underwriting_index, "jaggedthoughts-underwriting-opportunity-index-v1",
        "underwriting_index_sha256",
    )
    if book.get("discovery_run_sha256") != underwriting.get("discovery_run_sha256"):
        raise ValueError("opportunity book and underwriting index use different discovery epochs")
    rank_input = _verified(
        rank_program_input, "jaggedthoughts-rank-program-input-v1",
        "rank_program_input_sha256",
    )
    if rank_input.get("discovery_run_id") != book.get("discovery_run_id"):
        raise ValueError("opportunity book and rank-program input use different discovery epochs")
    rank_by_candidate_id: dict[str, dict[str, Any]] = {}
    for lane in rank_input.get("lanes") or ():
        for raw in lane.get("candidates") or ():
            row = dict(raw)
            candidate_id = str(row.get("candidate_id") or "")
            if not candidate_id or candidate_id in rank_by_candidate_id:
                raise ValueError("rank-program input has a missing or duplicate candidate identity")
            if not isinstance(row.get("rank_program_eligible"), bool):
                raise ValueError("rank-program eligibility must be an explicit boolean")
            rank_by_candidate_id[candidate_id] = row
    underwriting_by_sha = {
        str(row.get("candidate_sha256") or ""): row for row in underwriting.get("candidates") or ()
    }
    decision_by_entity = _latest_decisions(decisions)
    watch_by_entity = _latest_paper_watches(paper_watch_decisions)
    admission_set_sha = None
    admission_by_candidate: dict[tuple[str, str, str], dict[str, Any]] = {}
    if instrument_portfolio_admissions:
        admission_set = _verified(
            instrument_portfolio_admissions,
            "jaggedthoughts-workspace-instrument-portfolio-admissions-v1",
            "workspace_admissions_sha256",
        )
        admission_set_sha = admission_set["workspace_admissions_sha256"]
        for raw in admission_set.get("admissions") or ():
            admission = _verified(
                raw, "jaggedthoughts-instrument-portfolio-admission-v1",
                "admission_sha256",
            )
            subject = dict(admission.get("subject") or {})
            research = dict(admission.get("research_identity") or {})
            key = (
                str(subject.get("entity_kind") or ""),
                str(subject.get("subject_id") or "").upper(),
                str(research.get("candidate_sha256") or ""),
            )
            if not all(key) or research.get("kind") != key[0]:
                raise ValueError("instrument admission has incomplete candidate identity")
            if key in admission_by_candidate:
                raise ValueError(f"multiple instrument admissions bind current candidate {key[1]}")
            admission_by_candidate[key] = admission
    portfolio = None
    portfolio_decisions: set[str] = set()
    selected_weights: dict[str, float] = {}
    if portfolio_assembly:
        portfolio = _verified(
            portfolio_assembly, "jaggedthoughts-portfolio-assembly-v1", "portfolio_assembly_sha256",
        )
        portfolio_decisions = {str(row.get("decision_id") or "") for row in portfolio.get("candidates") or ()}
        selected_weights = {
            str(entity).upper(): float(value)
            for entity, value in (portfolio.get("selected_target_weights") or {}).items()
        }
    policy_runs = _run_ids(
        portfolio_policy_runs, schema="jaggedthoughts-portfolio-policy-run-v1", digest_field="run_sha256",
    )
    forecast_runs = _run_ids(
        closed_book_runs, schema="jaggedthoughts-closed-book-forecast-run-v1", digest_field="run_sha256",
    )
    policy_settled = set(map(str, portfolio_policy_settlement_run_ids))
    forecast_settled = set(map(str, closed_book_settlement_run_ids))
    watchlist_by_entity: dict[str, dict[str, Any]] = {}
    for raw in fund_watchlists:
        watchlist = _verified(
            raw, "jaggedthoughts-opportunity-watchlist-result-v1", "watchlist_sha256",
        )
        for candidate in watchlist.get("candidates") or ():
            entity = str(candidate.get("entity_id") or "").upper()
            if entity and (
                entity not in watchlist_by_entity
                or str(watchlist.get("as_of") or "") > str(watchlist_by_entity[entity].get("as_of") or "")
            ):
                watchlist_by_entity[entity] = {
                    "watchlist_id": watchlist.get("watchlist_id"), "as_of": watchlist.get("as_of"),
                    "watchlist_sha256": watchlist.get("watchlist_sha256"),
                    "screen_status": candidate.get("screen_status"),
                }
    fund_proposals: dict[tuple[str, str], dict[str, Any]] = {}
    fund_audit_sha = None
    if fund_proposal_audit:
        audit = _verified(
            fund_proposal_audit,
            "jaggedthoughts-public-fund-paper-proposal-audit-v1", "audit_sha256",
        )
        fund_audit_sha = audit["audit_sha256"]
        for raw in audit.get("rows") or ():
            row = dict(raw)
            key = (
                str(row.get("entity_id") or "").upper(),
                str(row.get("candidate_sha256") or ""),
            )
            if not all(key):
                continue
            if key in fund_proposals:
                raise ValueError(f"multiple fund proposal rows bind current candidate {key[0]}")
            proposal = row.get("proposal")
            if isinstance(proposal, Mapping):
                sealed = _verified(
                    proposal, "jaggedthoughts-public-fund-paper-proposal-v1",
                    "proposal_sha256",
                )
                evidence = dict(sealed.get("evidence") or {})
                if (
                    str((sealed.get("entity") or {}).get("entity_id") or "").upper(),
                    str(evidence.get("candidate_sha256") or ""),
                ) != key:
                    raise ValueError("fund proposal audit crossed candidate identity")
                row["proposal"] = sealed
            fund_proposals[key] = row
    rows = []
    for candidate in book.get("candidates") or ():
        candidate_id = str(candidate.get("candidate_id") or "")
        candidate_sha = str(candidate.get("candidate_sha256") or "")
        rank_input_row = rank_by_candidate_id.get(candidate_id)
        if rank_input_row is None:
            raise ValueError(f"rank-program row missing for candidate {candidate_id}")
        rank_eligible = bool(rank_input_row["rank_program_eligible"])
        underwriting_row = underwriting_by_sha.get(candidate_sha)
        if underwriting_row is None or underwriting_row.get("entity_id") != candidate.get("entity_id"):
            raise ValueError(f"underwriting row missing for candidate {candidate_sha}")
        ranking = underwriting_row.get("ranking") or {}
        if ranking.get("research_priority_is_expected_return") is not False:
            raise ValueError("research priority must remain explicitly separate from expected return")
        entity = str(candidate.get("entity_id") or "").upper()
        entity_kind = str(candidate.get("entity_kind") or "")
        decision = decision_by_entity.get(entity)
        paper_watch = watch_by_entity.get(entity)
        watch_evidence = dict((paper_watch or {}).get("evidence") or {})
        paper_watch_lineage_exact = bool(
            paper_watch and watch_evidence.get("candidate_sha256") == candidate_sha
        )
        instrument_admission = admission_by_candidate.get(
            (entity_kind, entity, candidate_sha)
        )
        origin = (decision or {}).get("discovery_origin") or {}
        lineage_exact = bool(decision and origin.get("candidate_sha256") == candidate_sha)
        decision_id = str((decision or {}).get("decision_id") or "")
        portfolio_candidate = bool(lineage_exact and decision_id in portfolio_decisions)
        target_weight = selected_weights.get(entity) if portfolio_candidate else None
        allocated = target_weight is not None and target_weight > 1e-12
        fund_proposal = fund_proposals.get((entity, candidate_sha))
        state, gaps, next_activation = _activation(
            entity_kind=entity_kind, screen=str(candidate.get("screen_status") or "blocked"),
            rank_eligible=rank_eligible,
            dossier=bool((candidate.get("research") or {}).get("dossier_available")),
            decision=decision, lineage_exact=lineage_exact,
            portfolio_candidate=portfolio_candidate, allocated=allocated,
            fund_proposal=fund_proposal,
            paper_watch=paper_watch,
            paper_watch_lineage_exact=paper_watch_lineage_exact,
            instrument_admission=instrument_admission,
        )
        candidate_policy = [
            run for run in policy_runs
            if any(row.get("candidate_sha256") == candidate_sha for row in run.get("universe") or ())
        ]
        candidate_forecasts = [
            run for run in forecast_runs
            if (
                (run.get("subject") or {}).get("subject_sha256") == candidate_sha
                or (run.get("subject") or {}).get("candidate_sha256") == candidate_sha
            )
        ]
        paper_identity = paper_watch if paper_watch_lineage_exact else decision
        paper_identity_sha = (
            (paper_identity or {}).get("decision_sha256")
            or (paper_identity or {}).get("decision_record_sha256")
        )
        rows.append({
            "candidate_id": candidate_id, "candidate_sha256": candidate_sha,
            "entity_id": entity, "entity_kind": entity_kind,
            "research_priority": {
                "eligible": rank_eligible,
                "rank": ranking.get("rank") if rank_eligible else None,
                "score": ranking.get("research_priority_score") if rank_eligible else None,
                "is_expected_return": False,
                "eligibility_source_sha256": rank_input["rank_program_input_sha256"],
            },
            "watchlist": {
                "opportunity_book_sha256": book["book_sha256"],
                "screen_status": candidate.get("screen_status"),
                "activation_class": candidate.get("activation_class"),
                "fund_watchlist": watchlist_by_entity.get(entity),
            },
            "paper": {
                "state": state,
                "decision_id": (paper_identity or {}).get("decision_id"),
                "decision_record_sha256": paper_identity_sha,
                "decision_stage": (
                    ((paper_watch or {}).get("lifecycle") or {}).get("stage")
                    if paper_watch_lineage_exact
                    else ((decision or {}).get("profile_lifecycle") or {}).get("stage")
                ),
                "decision_schema": (paper_identity or {}).get("schema"),
                "candidate_lineage_exact": bool(
                    lineage_exact or paper_watch_lineage_exact
                    or isinstance((fund_proposal or {}).get("proposal"), Mapping)
                ),
                "proposal_id": (
                    (paper_watch or {}).get("proposal_id")
                    or ((fund_proposal or {}).get("proposal") or {}).get("proposal_id")
                ),
                "proposal_sha256": (
                    (paper_watch or {}).get("proposal_sha256")
                    or ((fund_proposal or {}).get("proposal") or {}).get("proposal_sha256")
                ),
                "portfolio_assembly_sha256": portfolio.get("portfolio_assembly_sha256") if portfolio_candidate else None,
                "target_weight": target_weight,
                "instrument_admission": (
                    {
                        "admission_id": instrument_admission.get("admission_id"),
                        "admission_sha256": instrument_admission.get("admission_sha256"),
                        "status": (instrument_admission.get("eligibility") or {}).get("status"),
                    }
                    if instrument_admission is not None else None
                ),
            },
            "prospective_learning": {
                "closed_book_pending_count": sum(run["run_id"] not in forecast_settled for run in candidate_forecasts),
                "closed_book_settled_count": sum(run["run_id"] in forecast_settled for run in candidate_forecasts),
                "portfolio_policy_pending_count": sum(run["run_id"] not in policy_settled for run in candidate_policy),
                "portfolio_policy_settled_count": sum(run["run_id"] in policy_settled for run in candidate_policy),
            },
            "activation_gaps": gaps, "next_activation": next_activation,
            "allocation_ready": state in {"portfolio_candidate", "allocated_paper"} and not gaps,
            "allocated_paper": state == "allocated_paper",
            "capital_authority": False,
        })
    rows.sort(key=lambda row: (
        row["research_priority"]["rank"] if row["research_priority"]["rank"] is not None else 10**9,
        row["entity_id"],
    ))
    counts = {
        "candidate_count": len(rows),
        "research_rank_eligible_count": sum(row["research_priority"]["eligible"] for row in rows),
        "qualified_watchlist_count": sum(row["watchlist"]["screen_status"] == "qualified" for row in rows),
        "candidate_bound_draft_count": sum(row["paper"]["state"] == "draft" for row in rows),
        "active_paper_count": sum(row["paper"]["state"] == "active_paper" for row in rows),
        "portfolio_candidate_count": sum(row["paper"]["state"] == "portfolio_candidate" for row in rows),
        "allocated_paper_count": sum(row["paper"]["state"] == "allocated_paper" for row in rows),
        "unbound_operator_decision_count": sum(
            row["paper"]["decision_id"] is not None and not row["paper"]["candidate_lineage_exact"] for row in rows
        ),
    }
    body = {
        "schema": READINESS_SCHEMA,
        "as_of": canonical_timestamp(book.get("generated_at"), "allocation readiness as_of"),
        "discovery_run_sha256": book["discovery_run_sha256"],
        "opportunity_book_sha256": book["book_sha256"],
        "underwriting_index_sha256": underwriting["underwriting_index_sha256"],
        "rank_program_input_sha256": rank_input["rank_program_input_sha256"],
        "fund_proposal_audit_sha256": fund_audit_sha,
        "instrument_portfolio_admissions_sha256": admission_set_sha,
        "counts": counts, "candidates": rows,
        "settlement_machinery": {
            "closed_book_run_count": len(forecast_runs),
            "closed_book_settled_count": sum(run["run_id"] in forecast_settled for run in forecast_runs),
            "portfolio_policy_run_count": len(policy_runs),
            "portfolio_policy_settled_count": sum(run["run_id"] in policy_settled for run in policy_runs),
            "current_book_policy_run_count": sum(
                run.get("opportunity_book_sha256") == book["book_sha256"] for run in policy_runs
            ),
        },
        "authority": "paper_readiness_projection", "capital_authority": False,
    }
    return {**body, "readiness_sha256": stable_sha256(body)}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: Path) -> list[dict[str, Any]]:
    return [_read(row) for row in sorted(path.glob("*.json"))] if path.is_dir() else []


def compile_workspace_allocation_readiness(
    workspace: str | Path, *, opportunity_book: Mapping[str, Any] | None = None,
    underwriting_index: Mapping[str, Any] | None = None,
    instrument_portfolio_admissions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    portfolio_path = root / "portfolio" / "latest_assembly.json"
    discovery = _read(root / "discovery" / "latest.json")
    policies = _rows(root / "portfolio_policy" / "runs")
    forecasts = _rows(root / "closed_book" / "runs")
    return compile_allocation_readiness(
        opportunity_book=opportunity_book or _read(root / "opportunity_books" / "latest.json"),
        underwriting_index=underwriting_index or _read(root / "underwriting" / "latest.json"),
        rank_program_input=discovery["rank_program_input"],
        decisions=operator_forecast_decisions(root, include_drafts=True),
        paper_watch_decisions=current_paper_watch_decisions(root),
        portfolio_assembly=_read(portfolio_path) if portfolio_path.is_file() else None,
        portfolio_policy_runs=policies,
        portfolio_policy_settlement_run_ids=(
            str(row.get("run_id") or "") for row in _rows(root / "portfolio_policy" / "settlements")
        ),
        closed_book_runs=forecasts,
        closed_book_settlement_run_ids=(
            str(row.get("run_id") or "") for row in _rows(root / "closed_book" / "settlements")
        ),
        fund_watchlists=_rows(root / "watchlists" / "results"),
        fund_proposal_audit=(
            _read(root / "paper_proposals" / "funds" / "latest.json")
            if (root / "paper_proposals" / "funds" / "latest.json").is_file()
            else None
        ),
        instrument_portfolio_admissions=(
            instrument_portfolio_admissions
            or _read(root / "portfolio" / "instrument_admissions" / "latest.json")
            if instrument_portfolio_admissions
            or (root / "portfolio" / "instrument_admissions" / "latest.json").is_file()
            else None
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    args = parser.parse_args(argv)
    print(json.dumps(compile_workspace_allocation_readiness(args.workspace), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["READINESS_SCHEMA", "compile_allocation_readiness", "compile_workspace_allocation_readiness"]
