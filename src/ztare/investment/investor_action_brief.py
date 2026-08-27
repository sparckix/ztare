"""Compile current investment artifacts into a small, read-only action brief."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256


BRIEF_SCHEMA = "jaggedthoughts-investor-action-brief-v2"


def _shadow_book(portfolio_policy: Mapping[str, Any] | None) -> dict[str, Any]:
    """Project the latest sealed policy trial without turning it into advice."""
    status = dict(portfolio_policy or {})
    run = dict(status.get("latest_run") or {})
    if not run:
        return {
            "status": "not_open", "policy_count": 0, "policies": [],
            "capital_authority": False, "recommendation_claim": False,
        }
    if run.get("schema") != "jaggedthoughts-portfolio-policy-run-v1":
        raise ValueError("automated shadow book requires a portfolio-policy run")
    policies = []
    for raw in run.get("policies") or ():
        row = dict(raw)
        weights = {
            str(entity): float(weight)
            for entity, weight in dict(row.get("weights") or {}).items()
        }
        policies.append({
            "policy_id": row.get("policy_id"),
            "policy_sha256": row.get("policy_sha256"),
            "method": row.get("method"),
            "evaluation_role": row.get("evaluation_role"),
            "gross_weight": float(row.get("gross_weight") or 0),
            "cash_weight": float(row.get("cash_weight") or 0),
            "positions": [
                {"entity_id": entity, "weight": weight}
                for entity, weight in sorted(
                    weights.items(), key=lambda item: (-item[1], item[0])
                )
            ],
            "capital_authority": False,
        })
    return {
        "status": run.get("status"),
        "run_id": run.get("run_id"),
        "run_sha256": run.get("run_sha256"),
        "opened_at": run.get("opened_at"),
        "end_at": run.get("end_at"),
        "horizon_days": run.get("horizon_days"),
        "policy_count": len(policies),
        "policies": policies,
        "learning": {
            "settled_block_count": int(status.get("settled_count") or 0),
            "pending_block_count": int(status.get("pending_count") or 0),
            "minimum_inference_blocks": int(
                (status.get("scoreboard") or {}).get("minimum_inference_blocks") or 0
            ),
            "next_activation": (status.get("scoreboard") or {}).get("next_activation"),
        },
        "authority": "prospective_shadow_evaluation",
        "capital_authority": False,
        "recommendation_claim": False,
    }


def _planning_book(
    planning_scenario: Mapping[str, Any] | None,
    sleeve_implementation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Lower the assumption-labeled sleeve result to its public proxy positions."""
    scenario = dict(planning_scenario or {})
    if not scenario:
        return {
            "status": "not_compiled", "positions": [],
            "paper_policy_authority": False, "capital_authority": False,
            "recommendation_claim": False,
        }
    if scenario.get("schema") != "jaggedthoughts-household-allocation-scenario-v1":
        raise ValueError("planning book requires a household allocation scenario")
    weights = dict((scenario.get("selected_policy") or {}).get("weights") or {})
    proxies = {}
    for sleeve in (sleeve_implementation or {}).get("sleeves") or ():
        basis = [
            row for row in sleeve.get("eligible_instruments") or ()
            if row.get("basis_proxy") is True
        ]
        if len(basis) == 1:
            proxies[str(sleeve.get("sleeve_id") or "")] = str(
                (basis[0].get("identity") or {}).get("subject_id") or ""
            )
    positions = []
    for sleeve_id, raw_weight in sorted(weights.items()):
        weight = float(raw_weight)
        if weight <= 0:
            continue
        entity_id = proxies.get(str(sleeve_id))
        if not entity_id:
            raise ValueError(f"planning sleeve {sleeve_id} has no unique public basis proxy")
        positions.append({
            "sleeve_id": str(sleeve_id), "entity_id": entity_id, "weight": weight,
            "implementation_role": "broad_sleeve_proxy",
        })
    return {
        "status": "assumption_labeled_projection",
        "scenario_sha256": scenario.get("scenario_sha256"),
        "selected_program_id": (scenario.get("selected_policy") or {}).get("program_id"),
        "positions": positions,
        "cash_weight": float(weights.get("cash") or 0),
        "operator_policy_blockers": list(scenario.get("operator_policy_blockers") or ()),
        "next_transition": "complete_operator_mandate_and_select_one_reviewed_policy",
        "authority": "planning_scenario_only",
        "paper_policy_authority": False,
        "capital_authority": False,
        "recommendation_claim": False,
    }


def _household_shadow_book(
    household_policy_tournament: Mapping[str, Any] | None,
) -> dict[str, Any]:
    status = dict(household_policy_tournament or {})
    run = dict(status.get("latest_run") or {})
    if not run:
        return {
            "status": "not_open", "policy_count": 0, "policies": [],
            "capital_authority": False, "recommendation_claim": False,
        }
    if run.get("schema") != "jaggedthoughts-household-policy-tournament-run-v1":
        raise ValueError("household shadow book requires a household-policy run")
    policies = []
    for raw in run.get("policies") or ():
        row = dict(raw)
        positions = [
            {"entity_id": str(entity), "weight": float(weight)}
            for entity, weight in sorted(
                dict(row.get("weights") or {}).items(),
                key=lambda item: (-float(item[1]), str(item[0])),
            )
        ]
        policies.append({
            "policy_id": row.get("policy_id"), "method": row.get("method"),
            "policy_sha256": row.get("policy_sha256"),
            "decision_equivalence_id": row.get("decision_equivalence_id"),
            "positions": positions, "capital_authority": False,
        })
    return {
        "status": run.get("status") or run.get("lifecycle_status"),
        "run_id": run.get("run_id"), "run_sha256": run.get("run_sha256"),
        "opened_at": run.get("opened_at"), "end_at": run.get("end_at"),
        "horizon_days": run.get("horizon_days"),
        "control_policy_id": run.get("control_policy_id"),
        "policy_count": len(policies),
        "distinct_decision_count": len({
            row["decision_equivalence_id"] for row in policies
            if row.get("decision_equivalence_id")
        }),
        "policies": policies,
        "learning": {
            "settled_block_count": int(status.get("settled_count") or 0),
            "pending_block_count": int(status.get("pending_count") or 0),
            "minimum_inference_blocks": int(status.get("minimum_inference_blocks") or 0),
            "next_activation": status.get("next_activation"),
        },
        "authority": "prospective_household_shadow_evaluation",
        "capital_authority": False, "recommendation_claim": False,
    }


def _rows(value: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        if value.get("schema") in {
            "jaggedthoughts-public-equity-paper-proposal-v1",
            "jaggedthoughts-public-fund-paper-proposal-v1",
        }:
            return [{"proposal": dict(value)}]
        return [dict(row) for row in value.get("rows") or value.get("proposals") or ()]
    return [dict(row) for row in value]


def _candidate_key(row: Mapping[str, Any]) -> tuple[str, str]:
    proposal = row.get("proposal") if isinstance(row.get("proposal"), Mapping) else {}
    evidence = proposal.get("evidence") if isinstance(proposal.get("evidence"), Mapping) else {}
    identity = (
        proposal.get("candidate_identity")
        if isinstance(proposal.get("candidate_identity"), Mapping) else {}
    )
    entity = row.get("entity_id") or (proposal.get("entity") or {}).get("entity_id")
    digest = (
        row.get("candidate_sha256")
        or evidence.get("candidate_sha256")
        or identity.get("candidate_sha256")
    )
    return str(entity or "").upper(), str(digest or "")


def _proposal_index(
    value: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in _rows(value):
        key = _candidate_key(row)
        if not all(key):
            continue
        if key in indexed:
            raise ValueError(f"multiple proposal-audit rows for current candidate {key[0]}")
        indexed[key] = row
    return indexed


def _proposal_gate(row: Mapping[str, Any] | None) -> tuple[bool, list[str], dict[str, Any] | None]:
    if row is None:
        return False, ["candidate_not_present"], None
    proposal = row.get("proposal") if isinstance(row.get("proposal"), Mapping) else None
    blockers = list(row.get("blockers") or ())
    if proposal:
        blockers.extend(proposal.get("activation_blockers") or ())
    eligible = bool(
        proposal
        and not blockers
        and row.get("activation_eligible", proposal.get("activation_eligible", True))
    )
    return eligible, sorted(set(map(str, blockers))), dict(proposal) if proposal else None


def _queue_index(research_queue: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    indexed: dict[str, list[dict[str, Any]]] = {}
    for raw in (research_queue or {}).get("jobs") or ():
        row = dict(raw)
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        entity = str(payload.get("entity_id") or payload.get("symbol") or "").upper()
        if entity:
            indexed.setdefault(entity, []).append(row)
    for rows in indexed.values():
        rows.sort(key=lambda row: (-int(row.get("priority") or 0), str(row.get("work_id") or "")))
    return indexed


def _queue_projection(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "work_id": row.get("work_id"),
        "kind": row.get("kind"),
        "status": row.get("status"),
        "priority": row.get("priority"),
        "available_at": row.get("available_at"),
        "expected_exit": row.get("expected_exit"),
    } for row in rows if row.get("status") in {"queued", "leased"}]


def _coordinates(
    opportunity: Mapping[str, Any], underwriting: Mapping[str, Any] | None,
) -> dict[str, Any]:
    valuation = (underwriting or {}).get("valuation") or {}
    factor = (underwriting or {}).get("factor") or {}
    return {
        "economic_coordinates": dict(opportunity.get("economic_coordinates") or {}),
        "valuation_return_coordinates": list(valuation.get("return_coordinates") or ()),
        "factor_coordinates": {
            "assumption_implied_return": factor.get("assumption_implied_return"),
            "historical_residual_alpha": factor.get("historical_residual_alpha"),
        },
        "coordinate_contract": ((underwriting or {}).get("ranking") or {}).get(
            "coordinate_contract"
        ),
    }


def _blockers(
    *, kind: str, proposal_row: Mapping[str, Any] | None,
    readiness: Mapping[str, Any] | None, underwriting: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    _, proposal_codes, _ = _proposal_gate(proposal_row)
    owners = [
        {
            "owner_gate": (
                "public_fund_paper_proposal_audit"
                if kind == "public_fund" else "public_equity_paper_proposal_audit"
            ),
            "codes": proposal_codes,
        },
        {
            "owner_gate": "allocation_readiness",
            "codes": (
                list(readiness.get("activation_gaps") or ())
                if readiness is not None else ["candidate_not_present"]
            ),
        },
        {
            "owner_gate": "underwriting_index",
            "codes": (
                list(underwriting.get("gaps") or ())
                if underwriting is not None else ["candidate_not_present"]
            ),
        },
    ]
    return [row for row in owners if row["codes"]]


def _decision_summary(
    *, breadth_audit: Mapping[str, Any], research_now: list[dict[str, Any]],
    paper: list[dict[str, Any]], funded: list[dict[str, Any]],
    implementation_candidates: list[dict[str, Any]],
    review_now: list[dict[str, Any]], service: Mapping[str, Any],
    paper_cash: Mapping[str, Any],
    sleeve_implementation_frontier: Mapping[str, Any] | None,
    fund_sleeve_comparison: Mapping[str, Any] | None,
    automated_shadow_book: Mapping[str, Any],
    household_shadow_book: Mapping[str, Any],
) -> dict[str, Any]:
    """Answer the five investor questions from the already-owned typed state."""
    scopes = []
    for row in breadth_audit.get("active_scout_scope") or ():
        mode = str(row.get("mode") or "")
        scopes.append({
            "scope_id": row.get("intent_id"),
            "scope_class": (
                "broad_periodic_scout" if mode in {"broad_equity", "broad_fund"}
                else "explicit_challenger_cohort"
            ),
            "entity_kind": (row.get("entity_kinds") or [None])[0],
            "eligible_count": row.get("eligible_count"),
            "returned_count": row.get("returned_count"),
            "capitalization": row.get("capitalization"),
            "styles": list(row.get("styles") or ()),
        })
    funnel = breadth_audit.get("funnel") or {}
    branches = funnel.get("branches") or {}
    equities = [row for row in research_now if row.get("entity_kind") == "public_equity"]
    funds = [row for row in research_now if row.get("entity_kind") == "public_fund"]
    activation = (fund_sleeve_comparison or {}).get("invest_vs_cash_activation") or {}
    fund_comparison_rows = [dict(row) for row in activation.get("ranked_research_candidates") or ()]
    fund_programs = {
        str(program.get("program_id") or ""): program
        for sleeve in (fund_sleeve_comparison or {}).get("sleeves") or ()
        for program in sleeve.get("programs") or ()
        if program.get("program_id")
    }
    fund_shortlist = []
    for sleeve_id in sorted({str(row.get("sleeve_id") or "") for row in fund_comparison_rows}):
        fund_shortlist.extend(sorted(
            (row for row in fund_comparison_rows if row.get("sleeve_id") == sleeve_id),
            key=lambda row: (
                int(row.get("research_priority_rank_within_sleeve") or 0),
                str(row.get("entity_id") or ""),
            ),
        )[:3])

    def priority_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        qualified = [row for row in rows if (row.get("why_present") or {}).get("screen_status") == "qualified"]
        selected = (qualified + [row for row in rows if row not in qualified])[:5]
        return [{
            "entity_id": row.get("entity_id"),
            "research_rank": row.get("existing_research_rank"),
            "screen_status": (row.get("why_present") or {}).get("screen_status"),
            "next_transition": row.get("next_transition"),
        } for row in selected]

    basis = []
    for sleeve in (sleeve_implementation_frontier or {}).get("sleeves") or ():
        for instrument in sleeve.get("eligible_instruments") or ():
            if instrument.get("basis_proxy"):
                basis.append({
                    "sleeve_id": sleeve.get("sleeve_id"),
                    "entity_id": (instrument.get("identity") or {}).get("subject_id"),
                })
    challenger_programs = []
    for sleeve in (fund_sleeve_comparison or {}).get("sleeves") or ():
        for program in sleeve.get("programs") or ():
            challenger_programs.append({
                "sleeve_id": sleeve.get("sleeve_id"),
                "entity_id": (program.get("identity") or {}).get("subject_id"),
                "comparison_eligible": bool(program.get("comparison_eligible")),
            })

    qualified_equities = [row["entity_id"] for row in priority_rows(equities)
                          if row["screen_status"] == "qualified"]
    qualified_funds = [row["entity_id"] for row in priority_rows(funds)
                       if row["screen_status"] == "qualified"]
    source_universe = breadth_audit.get("source_universe") or {}
    deep_equities = (branches.get("public_equity") or {}).get("discovery_candidates", 0)
    deep_funds = (branches.get("public_fund") or {}).get("discovery_candidates", 0)
    scan_text = (
        f"The source catalog has {int(source_universe.get('eligible_count') or 0):,} eligible "
        f"securities. The latest broad scouts sampled "
        f"{sum(int(row['returned_count'] or 0) for row in scopes if row['scope_class'] == 'broad_periodic_scout')} "
        f"equity/fund identities; the explicit challenger cohort returned "
        f"{sum(int(row['returned_count'] or 0) for row in scopes if row['scope_class'] == 'explicit_challenger_cohort')}. "
        f"The cumulative deep screen currently contains {deep_equities} companies and {deep_funds} funds."
    )
    fund_attention_count = len({
        str(row.get("entity_id") or "") for row in [*funds, *fund_comparison_rows]
        if row.get("entity_id")
    })
    attention_text = (
        f"Research attention currently covers {len(equities)} companies and "
        f"{fund_attention_count} funds. "
        f"The qualified company queue starts with {', '.join(qualified_equities) or 'none'}; "
        f"the qualified fund dossier queue starts with {', '.join(qualified_funds) or 'none'}. "
        f"The within-sleeve fund shortlist starts with "
        f"{', '.join(str(row.get('entity_id')) for row in fund_shortlist) or 'none'}. "
        "These are research priorities, not return forecasts."
    )
    paper_review = [row for row in review_now if row.get("review_state") == "operator_review"]
    if funded:
        decision_text = f"{len(funded)} candidate(s) clear funded gates."
    elif paper:
        decision_text = (
            f"{len(paper)} candidate(s) clear paper gates and {len(paper_review)} await operator review; "
            "brokerage authority remains absent."
        )
    elif implementation_candidates:
        names = ", ".join(row["entity_id"] for row in implementation_candidates)
        decision_text = (
            f"{len(implementation_candidates)} current paper implementation candidate(s) "
            f"({names}) are ready for household-policy comparison. None is selected, so the "
            f"paper book remains {int(float(paper_cash.get('cash_weight') or 0) * 100)}% cash."
        )
    else:
        decision_text = (
            "No company or fund clears every proposal and allocation gate, so the paper book "
            f"remains {int(float(paper_cash.get('cash_weight') or 0) * 100)}% cash."
        )
    if automated_shadow_book.get("policy_count"):
        decision_text += (
            f" Separately, the engine has {int(automated_shadow_book['policy_count'])} sealed "
            f"shadow portfolio policies collecting outcomes through "
            f"{automated_shadow_book.get('end_at') or 'their frozen horizon'}; these evaluate "
            "methods and do not authorize an operator position."
        )
    if household_shadow_book.get("policy_count"):
        decision_text += (
            f" A separate {int(household_shadow_book['policy_count'])}-policy household "
            f"implementation trial scores after "
            f"{household_shadow_book.get('end_at') or 'its frozen horizon'}."
        )
    due = service.get("next_due_at")
    next_kind = str(service.get("next_transition") or service.get("service_mode") or "due_check")
    next_label = {
        "jaggedthoughts_subscription_research": "researches current public evidence",
        "jaggedthoughts_reassessment_research": "reassesses changed public evidence",
        "jaggedthoughts_strategy_outcome_research": "checks a matured strategy outcome",
        "jaggedthoughts_strategy_cohort_research": "checks strategy transfer in a peer cohort",
        "jaggedthoughts_strategy_frontier_research": "expands a strategy-choice frontier",
        "jaggedthoughts_strategy_program_adoption_research": (
            "checks which integrated strategy program was adopted"
        ),
        "jaggedthoughts_strategy_event_refinement_research": (
            "pins strategy-event timing to primary sources"
        ),
        "jaggedthoughts_activation_research": "deepens paper-watch evidence",
        "jaggedthoughts_autoresearch_project": "runs the next sealed model experiment",
        "jaggedthoughts_fund_implementation_gap_research": (
            "fills a fund implementation evidence gap"
        ),
    }.get(next_kind, next_kind.replace("_", " "))
    next_work = str(service.get("work_id") or "")
    next_subject = str(service.get("subject_id") or "")
    selection_note = {
        "frozen_chain_successor": (
            " It goes first because it closes an already-open evidence chain."
        ),
        "activation_service_cadence": (
            " It goes first because the activation-evidence lane is due service."
        ),
        "fund_service_cadence": (
            " It goes first because the fund-evidence lane is due service."
        ),
        "candidate_service_cadence": (
            " It goes first because the candidate-underwriting lane is due service."
        ),
        "queue_priority": " It is currently first in the executable queue.",
    }.get(str(service.get("dispatch_selection_basis") or ""), "")
    next_text = (
        f"Now, the owning subscription worker {next_label}"
        f"{f' for {next_subject}' if next_subject else ''}.{selection_note}"
        if service.get("active") else
        f"At {due}, the owning subscription worker {next_label}"
        f"{f' for {next_subject}' if next_subject else f' ({next_work})' if next_work else ''}."
        f"{selection_note}"
        if service.get("enabled") and due else
        "No automatic due transition is currently scheduled."
    )

    equity_reassessment = sorted({
        row.get("entity_id") for row in equities
        if any("research_coverage:" in str(code)
               for gate in row.get("blockers") or () for code in gate.get("codes") or ())
    })
    fund_reviews = sorted({
        row.get("entity_id") for row in funds
        if any(code == "candidate_bound_fund_review_absent"
               for gate in row.get("blockers") or () for code in gate.get("codes") or ())
    })
    changes = []
    if equity_reassessment:
        changes.append({
            "applies_to": equity_reassessment,
            "evidence": "Current source-hash reassessment or a candidate-bound dossier, followed by an inactive operator draft.",
            "owner": "public_equity_paper_proposal_audit",
        })
    if fund_reviews:
        changes.append({
            "applies_to": fund_reviews,
            "evidence": "A candidate-bound fund review covering valuation, exposure, concentration, fees, liquidity, and source fit.",
            "owner": "public_fund_paper_proposal_audit",
        })
    if (
        challenger_programs
        and int((fund_sleeve_comparison or {}).get("implementation_review_admitted_count") or 0) == 0
    ):
        changes.append({
            "applies_to": [row["entity_id"] for row in challenger_programs if row["entity_id"]],
            "evidence": "The missing holdings-quality, liquidity, tax/currency, or proposal evidence recorded by each fund-program gate.",
            "owner": "fund_sleeve_comparison",
        })

    return {
        "scan": {"text": scan_text, "scopes": scopes},
        "attention": {
            "text": attention_text,
            "companies": priority_rows(equities),
            "funds": priority_rows(funds),
            "fund_sleeve_candidate_count": len(fund_comparison_rows),
            "fund_sleeve_candidates": [{
                "entity_id": row.get("entity_id"),
                "sleeve_id": row.get("sleeve_id"),
                "rank_within_sleeve": row.get("research_priority_rank_within_sleeve"),
                "factor_assumption_spread_vs_cash": row.get("required_excess_return_vs_cash"),
                "ranking_semantics": row.get("ranking_semantics"),
                "comparison_metrics": dict(
                    (fund_programs.get(str(row.get("program_id") or "")) or {}).get(
                        "comparison_metrics"
                    ) or {}
                ),
                "evidence_gaps": sorted(set(map(str, (
                    (fund_programs.get(str(row.get("program_id") or "")) or {}).get(
                        "blockers"
                    ) or ()
                )))),
                "portfolio_policy_evidence_complete": bool(
                    ((fund_programs.get(str(row.get("program_id") or "")) or {}).get(
                        "portfolio_evidence"
                    ) or {}).get("portfolio_policy_evidence_complete")
                ),
                "next_transition": activation.get("required_next_transition"),
                "capital_authority": False,
            } for row in fund_shortlist],
        },
        "decision": {
            "text": decision_text,
            "paper_count": len(paper), "funded_count": len(funded),
            "implementation_candidate_count": len(implementation_candidates),
            "implementation_candidate_ids": [
                row["entity_id"] for row in implementation_candidates
            ],
            "operator_review_count": len(paper_review),
        },
        "next": {"text": next_text, "due_epoch": due},
        "answer_changing_evidence": changes,
        "fund_identity_boundary": {
            "text": "Broad asset-class sleeves are portfolio basis objects; the value-fund challenger cohort is a separate within-sleeve research tournament.",
            "broad_sleeves": basis,
            "challenger_program_count": len(challenger_programs),
            "comparison_eligible_count": sum(row["comparison_eligible"] for row in challenger_programs),
        },
    }


def compile_investor_action_brief(
    *,
    breadth_audit: Mapping[str, Any],
    discovery_run: Mapping[str, Any],
    opportunity_book: Mapping[str, Any],
    underwriting_index: Mapping[str, Any],
    allocation_readiness: Mapping[str, Any],
    equity_proposal_audit: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None = None,
    fund_proposal_audit: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None = None,
    paper_watch_decisions: Iterable[Mapping[str, Any]] = (),
    research_queue: Mapping[str, Any] | None = None,
    research_service: Mapping[str, Any] | None = None,
    sleeve_implementation_frontier: Mapping[str, Any] | None = None,
    fund_sleeve_comparison: Mapping[str, Any] | None = None,
    portfolio_policy: Mapping[str, Any] | None = None,
    planning_scenario: Mapping[str, Any] | None = None,
    household_policy_tournament: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project existing ranks and gates without valuing, recommending, or allocating."""
    paper_watch_rows = [dict(row) for row in paper_watch_decisions]
    discovery = {
        (str(row.get("entity_id") or "").upper(), str(row.get("candidate_sha256") or "")): row
        for row in discovery_run.get("candidates") or ()
    }
    opportunities = {
        (str(row.get("entity_id") or "").upper(), str(row.get("candidate_sha256") or "")): row
        for row in opportunity_book.get("candidates") or ()
    }
    underwriting = {
        (str(row.get("entity_id") or "").upper(), str(row.get("candidate_sha256") or "")): row
        for row in underwriting_index.get("candidates") or ()
    }
    readiness = {
        (str(row.get("entity_id") or "").upper(), str(row.get("candidate_sha256") or "")): row
        for row in allocation_readiness.get("candidates") or ()
    }
    proposal_indexes = {
        "public_equity": _proposal_index(equity_proposal_audit),
        "public_fund": _proposal_index(fund_proposal_audit),
    }
    watch_by_proposal = {
        str(row.get("proposal_sha256") or ""): dict(row)
        for row in paper_watch_rows if row.get("proposal_sha256")
    }
    watch_by_candidate = {}
    for row in paper_watch_rows:
        entity = row.get("entity") if isinstance(row.get("entity"), Mapping) else {}
        evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
        key = (
            str(entity.get("entity_kind") or ""),
            str(entity.get("entity_id") or "").upper(),
            str(evidence.get("candidate_sha256") or ""),
        )
        if all(key):
            watch_by_candidate[key] = dict(row)
    queue = _queue_index(research_queue)

    review_now = []
    for kind, index in proposal_indexes.items():
        for key, proposal_row in index.items():
            if str((discovery.get(key) or {}).get("entity_kind") or "") != kind:
                continue
            eligible, blockers, proposal = _proposal_gate(proposal_row)
            if not proposal:
                continue
            # Proposal compilations are dated projections. The active watch owns
            # the entity at the candidate-evidence epoch and therefore survives
            # proposal-hash churn while that candidate identity is unchanged.
            active = watch_by_candidate.get((kind, key[0], key[1]))
            if active is None:
                active = watch_by_proposal.get(str(proposal.get("proposal_sha256") or ""))
            review_now.append({
                "candidate_sha256": key[1], "entity_id": key[0], "entity_kind": kind,
                "proposal_id": proposal.get("proposal_id"),
                "proposal_sha256": proposal.get("proposal_sha256"),
                "required_operator_confirmation": proposal.get("required_operator_confirmation"),
                "review_state": (
                    "active_paper_watch" if active else
                    "operator_review" if eligible else "blocked"
                ),
                "activation_eligible": eligible and active is None,
                "activation_blockers": blockers,
                "position_admission": dict(proposal.get("position_admission") or {}),
                "active_decision_id": (active or {}).get("decision_id"),
                "active_decision_path": (active or {}).get("artifact_path"),
                "next_transition": (
                    (active or {}).get("next_activation")
                    or proposal.get("next_activation")
                ),
                "capital_authority": False, "brokerage_authority": False,
            })
    review_now.sort(key=lambda row: (row["entity_kind"], row["entity_id"]))

    declared_research = list(opportunity_book.get("research_queue") or ())
    declared_keys = {
        (str(row.get("entity_id") or "").upper(), str(row.get("candidate_sha256") or ""))
        for row in declared_research
    }
    # A qualified candidate can sit outside the book's research queue while its
    # current proposal audit still says the candidate-bound dossier is absent.
    for row in opportunity_book.get("candidates") or ():
        key = (str(row.get("entity_id") or "").upper(), str(row.get("candidate_sha256") or ""))
        if (
            key not in declared_keys
            and row.get("screen_status") != "blocked"
            and row.get("research_priority_score") is not None
            and (row.get("research") or {}).get("dossier_available") is not True
        ):
            declared_research.append(row)
            declared_keys.add(key)

    research_now = []
    for position, raw in enumerate(declared_research):
        row = dict(raw)
        key = (str(row.get("entity_id") or "").upper(), str(row.get("candidate_sha256") or ""))
        if key not in discovery:
            continue
        if row.get("research_priority_is_expected_return") is not False:
            raise ValueError("research priority must remain separate from expected return")
        kind = str(row.get("entity_kind") or "")
        proposal_row = proposal_indexes.get(kind, {}).get(key)
        readiness_row = readiness.get(key)
        research_now.append({
            "candidate_id": row.get("candidate_id"),
            "candidate_sha256": key[1],
            "entity_id": key[0],
            "entity_kind": kind,
            "existing_research_rank": row.get("rank"),
            "research_priority_score": row.get("research_priority_score"),
            "research_priority_is_expected_return": False,
            "why_present": {
                "owner_gate": (
                    "opportunity_book.research_queue"
                    if position < len(opportunity_book.get("research_queue") or ())
                    else "candidate_research_dossier"
                ),
                "activation_class": row.get("activation_class"),
                "screen_status": row.get("screen_status"),
                "research_prompt": (row.get("research") or {}).get("research_prompt"),
                "next_action": row.get("next_action"),
            },
            "blockers": _blockers(
                kind=kind, proposal_row=proposal_row,
                readiness=readiness_row, underwriting=underwriting.get(key),
            ),
            "next_transition": (
                (readiness_row or {}).get("next_activation")
                or row.get("kernel_next_activation")
            ),
            "queued_work": _queue_projection(queue.get(key[0], ())),
            "return_coordinates": _coordinates(row, underwriting.get(key)),
            "_source_position": position,
        })
    research_now.sort(key=lambda row: (
        row["existing_research_rank"] is None,
        row["existing_research_rank"] if row["existing_research_rank"] is not None else 0,
        row["_source_position"],
    ))
    for row in research_now:
        row.pop("_source_position")

    paper, funded = [], []
    for key, ready in readiness.items():
        opportunity = opportunities.get(key)
        if opportunity is None or key not in discovery or key not in underwriting:
            continue
        kind = str(ready.get("entity_kind") or opportunity.get("entity_kind") or "")
        proposal_row = proposal_indexes.get(kind, {}).get(key)
        proposal_eligible, _, proposal = _proposal_gate(proposal_row)
        paper_eligible = bool(
            ready.get("allocation_ready")
            and not ready.get("activation_gaps")
            and proposal_eligible
        )
        if not paper_eligible:
            continue
        item = {
            "candidate_id": opportunity.get("candidate_id"),
            "candidate_sha256": key[1],
            "entity_id": key[0],
            "entity_kind": kind,
            "why_present": {
                "allocation_gate": "allocation_ready",
                "paper_proposal_id": (proposal or {}).get("proposal_id"),
                "paper_state": (ready.get("paper") or {}).get("state"),
            },
            "next_transition": ready.get("next_activation"),
            "return_coordinates": _coordinates(opportunity, underwriting[key]),
        }
        paper.append(item)
        if (
            allocation_readiness.get("capital_authority") is True
            and ready.get("capital_authority") is True
            and (proposal or {}).get("capital_authority") is True
            and (proposal or {}).get("brokerage_authority") is True
        ):
            funded.append(item)
    paper.sort(key=lambda row: (row["entity_kind"], row["entity_id"]))
    funded.sort(key=lambda row: (row["entity_kind"], row["entity_id"]))
    implementation_candidates = sorted(({
        "candidate_sha256": key[1],
        "entity_id": key[0],
        "entity_kind": ready.get("entity_kind"),
        "admission": dict((ready.get("paper") or {}).get("instrument_admission") or {}),
        "next_transition": ready.get("next_activation"),
    } for key, ready in readiness.items() if (
        (ready.get("paper") or {}).get("state") == "portfolio_candidate"
    )), key=lambda row: (str(row["entity_kind"]), row["entity_id"]))

    service = dict(research_service or {})
    paper_cash = dict(opportunity_book.get("paper_posture") or {})
    automated_shadow_book = _shadow_book(portfolio_policy)
    planning_book = _planning_book(planning_scenario, sleeve_implementation_frontier)
    household_shadow_book = _household_shadow_book(household_policy_tournament)
    body = {
        "schema": BRIEF_SCHEMA,
        "as_of": opportunity_book.get("generated_at"),
        "universe_breadth": {
            "audit_sha256": breadth_audit.get("audit_sha256"),
            "source_universe": dict(breadth_audit.get("source_universe") or {}),
            "breadth_verdict": dict(breadth_audit.get("breadth_verdict") or {}),
        },
        "artifact_lineage": {
            "discovery_run_sha256": discovery_run.get("run_sha256"),
            "opportunity_discovery_run_sha256": opportunity_book.get("discovery_run_sha256"),
            "underwriting_discovery_run_sha256": underwriting_index.get("discovery_run_sha256"),
            "allocation_discovery_run_sha256": allocation_readiness.get("discovery_run_sha256"),
            "opportunity_current": (
                opportunity_book.get("discovery_run_sha256") == discovery_run.get("run_sha256")
            ),
            "underwriting_current": (
                underwriting_index.get("discovery_run_sha256") == discovery_run.get("run_sha256")
            ),
            "allocation_current": (
                allocation_readiness.get("discovery_run_sha256") == discovery_run.get("run_sha256")
            ),
        },
        "investable_now": {"paper": paper, "funded": funded},
        "implementation_candidates": implementation_candidates,
        "planning_book": planning_book,
        "automated_shadow_book": automated_shadow_book,
        "household_shadow_book": household_shadow_book,
        "review_now": review_now,
        "active_paper_watches": [{
            "decision_id": row.get("decision_id"),
            "proposal_sha256": row.get("proposal_sha256"),
            "entity": dict(row.get("entity") or {}),
            "activated_at": row.get("activated_at"),
            "target_weight": ((row.get("paper_policy") or {}).get("target_weight")),
            "next_transition": row.get("next_activation"),
            "artifact_path": row.get("artifact_path"),
            "capital_authority": False, "brokerage_authority": False,
        } for row in paper_watch_rows],
        "research_now": research_now,
        "next_automatic_transition": {
            "enabled": bool(service.get("enabled")),
            "transition": service.get("next_transition") or service.get("service_mode"),
            "due_epoch": service.get("next_due_at"),
            "work_id": service.get("work_id"),
            "job_kind": service.get("job_kind"),
            "subject_id": service.get("subject_id"),
            "active": bool(service.get("active")),
            "status": service.get("status"),
            "dispatch_selection_basis": service.get("dispatch_selection_basis"),
            "blocked_reasons": list(service.get("blocked_reasons") or ()),
            "starter": service.get("starter"),
        },
        "cash_posture": {
            "paper": paper_cash,
            "funded": {
                "capital_authority": allocation_readiness.get("capital_authority") is True,
                "state": None,
                "cash_weight": None,
            },
        },
        "authority": "read_only_investor_action_projection",
        "capital_authority": False,
        "recommendation_claim": False,
        "expected_return_claim": False,
    }
    body["decision_summary"] = _decision_summary(
        breadth_audit=breadth_audit, research_now=research_now,
        paper=paper, funded=funded, implementation_candidates=implementation_candidates,
        review_now=review_now, service=service,
        paper_cash=paper_cash,
        sleeve_implementation_frontier=sleeve_implementation_frontier,
        fund_sleeve_comparison=fund_sleeve_comparison,
        automated_shadow_book=automated_shadow_book,
        household_shadow_book=household_shadow_book,
    )
    return {**body, "brief_sha256": stable_sha256(body)}


__all__ = ["BRIEF_SCHEMA", "compile_investor_action_brief"]
