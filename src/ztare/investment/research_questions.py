"""Typed research-question programs for public-market acquisition.

The compiler turns one frozen discovery candidate into a small question
language, recursively enumerates one- and two-probe programs, closes the
declared Pareto frontier, and selects within it under a frozen research-policy
arm.  Its scores are routing priors to be settled prospectively; they do not
measure expected return or grant capital authority.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.strategy import (
    CandidateEvaluation,
    FrontierScope,
    Neighborhood,
    OperatorGrammar,
    ProgramInterpretation,
    RepresentationAudit,
    TypedOperator,
    TypedTerminal,
    TypedValue,
    compile_jaggedthoughts_frontier,
    enumerate_typed_programs,
    interpret_program,
)

from .contracts import canonical_timestamp, require_text, timestamp_key
from .strategy_learning import strategy_option_comparison_identity
from .strategy_options import RESULT_SCHEMA as STRATEGY_FRONTIER_SCHEMA
from .strategy_transfer import STRATEGY_TRANSFER_INDEX_SCHEMA


RESEARCH_QUESTION_FRONTIER_SCHEMA = "jaggedthoughts-research-question-frontier-v1"
OBJECTIVES = (
    "decision_relevance_proxy",
    "rival_discrimination_proxy",
    "coverage",
    "source_efficiency",
)
_ARMS = {"coverage_first", "disagreement_first"}


def _bounded(value: Any, fallback: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    return min(1.0, max(0.0, result)) if math.isfinite(result) else fallback


def _mean(*values: float) -> float:
    return sum(values) / len(values)


def _metric_text(metrics: Mapping[str, Any], key: str, *, percent: bool = True) -> str:
    try:
        value = float(metrics[key])
    except (KeyError, TypeError, ValueError):
        return "unresolved"
    if not math.isfinite(value):
        return "unresolved"
    return f"{value:.1%}" if percent else f"{value:.3f}"


def _decision_boundary_atom(candidate: Mapping[str, Any]) -> dict[str, Any] | None:
    """Bind research to the measured criterion nearest the current disposition."""
    rows = []
    for raw in candidate.get("criteria") or ():
        if not isinstance(raw, Mapping) or raw.get("operator") not in {"ge", "gt", "le", "lt"}:
            continue
        try:
            observed, threshold = float(raw["observed"]), float(raw["threshold"])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(observed) or not math.isfinite(threshold):
            continue
        operator = str(raw["operator"])
        margin = observed - threshold if operator in {"ge", "gt"} else threshold - observed
        rows.append({
            "criterion_id": str(raw.get("criterion_id") or raw.get("path") or "unnamed"),
            "path": str(raw.get("path") or "unknown"),
            "operator": operator,
            "observed": observed,
            "threshold": threshold,
            "passed": bool(raw.get("passed")),
            "signed_margin": margin,
            "normalized_margin": margin / max(abs(threshold), 0.1),
        })
    if not rows:
        return None
    boundary = min(rows, key=lambda row: (
        float(row["normalized_margin"]), str(row["criterion_id"]),
    ))
    entity_id = require_text(candidate.get("entity_id"), "decision-boundary entity_id").upper()
    path = str(boundary["path"])
    if candidate.get("entity_kind") == "public_fund":
        source_kinds = (
            ("issuer_holdings", "issuer_fundamentals", "market_data")
            if any(token in path for token in ("earnings", "growth", "valuation")) else
            ("issuer_holdings", "issuer_methodology", "market_data")
        )
    elif any(token in path for token in ("price", "return", "growth", "valuation")):
        source_kinds = ("sec_filing", "issuer_results", "market_data")
    elif any(token in path for token in ("debt", "liquidity", "balance_sheet")):
        source_kinds = ("sec_filing", "debt_disclosure")
    else:
        source_kinds = ("sec_filing", "issuer_results")
    state = "passes" if boundary["passed"] else "does not pass"
    return {
        "atom_id": f"decision_boundary:{boundary['criterion_id']}",
        "question": (
            f"{entity_id}'s frozen {boundary['criterion_id']} criterion currently {state}: "
            f"{path} is {boundary['observed']:.6g} against {boundary['operator']} "
            f"{boundary['threshold']:.6g}. Which primary evidence could establish that the "
            "measured input is durable or nonrepresentative, and which later source-bound "
            "observation would cross this exact boundary in a future candidate epoch?"
        ),
        "dimensions": ("screen_decision_boundary", path),
        "source_kinds": source_kinds,
        "decision_relevance": 1.0,
        "rival_discrimination": 0.96,
        "decision_boundary": {
            **boundary,
            "candidate_screen_status": candidate.get("screen_status"),
            "candidate_sha256": candidate.get("candidate_sha256"),
            "decision_relevance_basis": "nearest_frozen_screen_criterion",
            "information_gain_estimated": False,
            "transition_scope": "future_candidate_epoch_only",
        },
    }


def _strategy_question_atom(
    candidate: Mapping[str, Any], frontier: Mapping[str, Any],
    strategy_transfer_index: Mapping[str, Any] | None = None,
) -> tuple[
    dict[str, Any] | None, dict[str, Any] | None,
    dict[str, Any] | None, dict[str, Any],
]:
    body = dict(frontier)
    declared = require_text(
        body.pop("strategy_frontier_sha256", ""), "strategy question frontier hash",
    )
    if body.get("schema") != STRATEGY_FRONTIER_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("strategy question frontier identity is invalid")
    entity_id = require_text(candidate.get("entity_id"), "strategy question entity_id").upper()
    company = dict(body.get("company") or {})
    if str(company.get("id") or "").upper() != entity_id:
        raise ValueError("strategy question frontier targets another entity")
    candidate_as_of = canonical_timestamp(
        candidate.get("as_of"), "strategy question candidate as_of",
    )
    evidence_epoch = canonical_timestamp(
        body.get("evidence_epoch"), "strategy question frontier evidence_epoch",
    )
    if timestamp_key(evidence_epoch) > timestamp_key(candidate_as_of):
        raise ValueError("strategy question frontier follows the candidate evidence epoch")

    frontier_programs = [
        dict(row) for row in body.get("frontier_programs") or () if isinstance(row, Mapping)
    ]
    frontier_ids = {str(row.get("program_id") or "") for row in frontier_programs}
    local_only = [
        dict(row) for row in body.get("local_peak_programs") or ()
        if isinstance(row, Mapping) and str(row.get("program_id") or "") not in frontier_ids
    ]
    candidates = []
    for option in body.get("option_catalog") or ():
        if not isinstance(option, Mapping) or option.get("claim_status") != "supported":
            continue
        option_id = require_text(option.get("option_id"), "strategy question option_id")
        frontier_members = [
            str(row["program_id"]) for row in frontier_programs
            if option_id in set(map(str, row.get("unique_option_ids") or ()))
        ]
        local_members = [
            str(row["program_id"]) for row in local_only
            if option_id in set(map(str, row.get("unique_option_ids") or ()))
        ]
        if not frontier_members and not local_members:
            continue
        event = option.get("implementation_event")
        contracts = [
            dict(row) for row in option.get("outcome_contracts") or ()
            if isinstance(row, Mapping)
        ]
        timing = str((event or {}).get("treatment_timing_status") or "")
        if timing == "exact_adoption_event" and contracts:
            continue
        if timing == "interval_censored_adoption_event":
            gap, readiness = "sharpen_implementation_interval", 3
        elif isinstance(event, Mapping) and not contracts:
            gap, readiness = "freeze_operating_outcome_contract", 2
        else:
            gap, readiness = "verify_operational_adoption", 1
        pair_discrimination = sum(
            (option_id in set(map(str, left.get("unique_option_ids") or ())))
            != (option_id in set(map(str, right.get("unique_option_ids") or ())))
            for left in frontier_programs for right in local_only
        )
        candidates.append({
            "option": dict(option), "option_id": option_id, "gap": gap,
            "readiness": readiness, "pair_discrimination": pair_discrimination,
            "frontier_program_ids": sorted(frontier_members),
            "local_only_peak_program_ids": sorted(local_members),
            "outcome_contract_sha256s": sorted(
                str(row.get("contract_sha256") or "") for row in contracts
                if row.get("contract_sha256")
            ),
        })
    selected = max(candidates, key=lambda row: (
        int(row["pair_discrimination"]), int(row["readiness"]),
        len(row["frontier_program_ids"]), len(row["local_only_peak_program_ids"]),
        str(row["option_id"]),
    ), default=None)
    context = {
        "strategy_frontier_sha256": declared,
        "strategy_frontier_evidence_epoch": evidence_epoch,
        "source_dossier_sha256": company.get("source_dossier_sha256"),
        "prior_candidate_leaf": company.get("candidate_leaf"),
        "prior_candidate_sha256": company.get("candidate_sha256"),
        "current_candidate_leaf": candidate.get("candidate_leaf"),
        "current_candidate_sha256": candidate.get("candidate_sha256"),
        "current_candidate_as_of": candidate_as_of,
        "selection_status": "selected" if selected else "no_unsettled_supported_frontier_option",
        "capital_authority": False,
    }
    option_vocabulary = [
        {
            "option_id": str(row.get("option_id") or ""),
            "description": str(row.get("description") or row.get("option_id") or ""),
        }
        for row in body.get("option_catalog") or ()
        if isinstance(row, Mapping) and row.get("option_id")
    ]
    constraint_count = sum(
        len((body.get("feasibility_constraints") or {}).get(key) or ())
        for key in ("incompatibilities", "prerequisites", "resources")
    )
    constraint_atom = None
    if len(option_vocabulary) >= 2 and constraint_count == 0:
        exact_options = "; ".join(
            f"{row['option_id']} ({row['description']})" for row in option_vocabulary
        )
        constraint_atom = {
            "atom_id": f"strategy_constraint_evidence:{declared[:16]}",
            "question": (
                f"Using {entity_id}'s exact prior option vocabulary—{exact_options}—which opened "
                "primary source establishes a mutual exclusion, prerequisite, or numeric "
                "common-unit resource limit, and which observed admitted bundle plus excluded "
                "bundle or implication discriminates that predicate from the alternatives?"
            ),
            "dimensions": (
                "strategy_feasibility", "constraint_discrimination", "choice_space",
            ),
            "source_kinds": (
                "sec_filing", "issuer_strategy", "issuer_results", "regulator",
            ),
            "decision_relevance": 1.0,
            "rival_discrimination": 1.0,
        }
        context["constraint_frontier"] = {
            "status": "source_bound_constraint_discovery_due",
            "parent_strategy_frontier_sha256": declared,
            "exact_option_vocabulary": option_vocabulary,
            "current_constraint_count": 0,
            "admission_rule": (
                "A later dossier must bind predicates and discriminating bundles to opened "
                "primary sources; deterministic replay selects the unique minimal set."
            ),
        }
    if selected is None:
        return None, constraint_atom, None, context
    option = selected.pop("option")
    option_id = str(selected["option_id"])
    description = str(option.get("description") or option_id)
    if selected["gap"] == "sharpen_implementation_interval":
        question = (
            f"Which dated primary disclosure narrows {entity_id}'s first operational adoption of "
            f"{option_id} ({description}) to an exact event, without treating a commitment or "
            "still-executing program as operational adoption?"
        )
    elif selected["gap"] == "freeze_operating_outcome_contract":
        question = (
            f"Which disclosed operating metric, unit, comparator, measurement start, and horizon "
            f"could prospectively test whether {entity_id}'s {option_id} ({description}) delivers "
            f"its typed {str((option.get('mechanism') or {}).get('economic_bridge') or 'economic')} bridge?"
        )
    else:
        question = (
            f"Which dated primary evidence establishes whether {entity_id}'s {option_id} "
            f"({description}) became operational after the prior frontier epoch, and which disclosed "
            "operating metric could later distinguish its mechanism from the strongest local-peak rival?"
        )
    selected_context = {
        **context, **selected,
        "option_sha256": option.get("option_sha256"),
        "mechanism_sha256": (option.get("mechanism") or {}).get("mechanism_sha256"),
        "prior_evidence_refs": sorted(map(str, option.get("evidence_refs") or ())),
        "selection_boundary": (
            "The prior, source-bound frontier selects an evidence question only. Current evidence "
            "must re-establish adoption and consequences for the current candidate epoch."
        ),
    }
    atom = {
        "atom_id": f"strategy_option_evidence:{option_id}",
        "question": question,
        "dimensions": ("strategy_option", "implementation", "operating_consequence"),
        "source_kinds": ("sec_filing", "issuer_results", "issuer_strategy"),
        "decision_relevance": 1.0,
        "rival_discrimination": min(
            1.0, 0.9 + 0.02 * int(selected["pair_discrimination"]),
        ),
    }
    transfer_atom, transfer_context = _strategy_transfer_atom(
        candidate=candidate, frontier=body, option=option,
        strategy_transfer_index=strategy_transfer_index,
    )
    if transfer_context is not None:
        selected_context[
            "transfer_counterexample"
            if transfer_context["kind"] == "counterexample" else "transfer_replication"
        ] = transfer_context
    return atom, constraint_atom, transfer_atom, selected_context


def _strategy_transfer_atom(
    *, candidate: Mapping[str, Any], frontier: Mapping[str, Any],
    option: Mapping[str, Any], strategy_transfer_index: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Compile one prior compatible outcome into a future-only research question."""
    if strategy_transfer_index is None or not isinstance(option.get("mechanism"), Mapping):
        return None, None
    index = dict(strategy_transfer_index)
    declared = require_text(index.pop("index_sha256", ""), "strategy transfer index hash")
    if index.get("schema") != STRATEGY_TRANSFER_INDEX_SCHEMA or stable_sha256(index) != declared:
        raise ValueError("strategy transfer index identity is invalid")
    candidate_as_of = canonical_timestamp(
        candidate.get("as_of"), "strategy transfer target as_of",
    )
    generated_at = canonical_timestamp(
        index.get("generated_at"), "strategy transfer index generated_at",
    )
    if timestamp_key(generated_at) >= timestamp_key(candidate_as_of):
        return None, None

    target = strategy_option_comparison_identity(frontier, option)
    target_contracts = {
        str(row.get("metric_id")): str(row.get("unit") or "")
        for row in option.get("outcome_contracts") or ()
        if isinstance(row, Mapping) and row.get("metric_id")
    }
    target_entity = require_text(candidate.get("entity_id"), "strategy transfer target entity").upper()
    matches = []
    for raw_card in index.get("cards") or ():
        if not isinstance(raw_card, Mapping):
            continue
        card = dict(raw_card)
        card_sha = str(card.pop("card_sha256", "") or "")
        declared_kinds = set(map(str, (
            ((card.get("learning_chain") or {}).get("cohort") or {}).get("declared_entity_kinds")
            or ()
        )))
        if (
            len(card_sha) != 64 or stable_sha256(card) != card_sha
            or card.get("mechanism_phenotype_sha256") != target["mechanism_phenotype_sha256"]
            or card.get("outcome_metric_id") not in target_contracts
            or "public_equity" not in declared_kinds
        ):
            continue
        for raw_witness in card.get("counterexamples") or ():
            if not isinstance(raw_witness, Mapping):
                continue
            witness = dict(raw_witness)
            witness_sha = str(witness.pop("counterexample_sha256", "") or "")
            try:
                available_at = canonical_timestamp(
                    witness.get("available_at"), "strategy transfer counterexample available_at",
                )
            except (TypeError, ValueError):
                continue
            if (
                len(witness_sha) != 64 or stable_sha256(witness) != witness_sha
                or timestamp_key(available_at) >= timestamp_key(candidate_as_of)
                or witness.get("metric_id") != card.get("outcome_metric_id")
                or dict(witness.get("moderators") or {}) != target["environment"]
                or not witness.get("source_refs")
            ):
                continue
            matches.append((2, available_at, card_sha, witness_sha, card, witness))
        for raw_witness in card.get("outcome_witnesses") or ():
            if not isinstance(raw_witness, Mapping):
                continue
            witness = dict(raw_witness)
            witness_sha = str(witness.pop("witness_sha256", "") or "")
            try:
                available_at = canonical_timestamp(
                    witness.get("available_at"), "strategy transfer witness available_at",
                )
            except (TypeError, ValueError):
                continue
            metric = str(witness.get("metric_id") or "")
            expected_unit = target_contracts.get(metric, "")
            if (
                witness.get("status") not in {"supports", "inconclusive"}
                or len(witness_sha) != 64 or stable_sha256(witness) != witness_sha
                or timestamp_key(available_at) >= timestamp_key(candidate_as_of)
                or metric != card.get("outcome_metric_id")
                or expected_unit and witness.get("unit") != expected_unit
                or dict(witness.get("moderators") or {}) != target["environment"]
                or str(witness.get("entity_id") or "").upper() == target_entity
                or not witness.get("source_refs")
            ):
                continue
            priority = 1 if witness["status"] == "inconclusive" else 0
            matches.append((priority, available_at, card_sha, witness_sha, card, witness))
    if not matches:
        return None, None
    priority, available_at, card_sha, witness_sha, card, witness = max(matches)
    source_entity = str(witness.get("entity_id") or "").upper()
    metric = str(witness["metric_id"])
    if priority < 2:
        status = str(witness["status"])
        context_body = {
            "schema": "jaggedthoughts-strategy-replication-question-edge-v1",
            "kind": "replication",
            "strategy_transfer_index_sha256": declared,
            "strategy_transfer_card_sha256": card_sha,
            "outcome_witness_sha256": witness_sha,
            "outcome_status": status,
            "source_entity_id": source_entity,
            "target_entity_id": target_entity,
            "entity_relation": "cross_entity_public_equity",
            "mechanism_phenotype_sha256": target["mechanism_phenotype_sha256"],
            "target_environment": target["environment"],
            "target_environment_sha256": target["environment_sha256"],
            "outcome_metric_id": metric,
            "source_refs": sorted(map(str, witness.get("source_refs") or ())),
            "witness_available_at": available_at,
            "target_candidate_as_of": candidate_as_of,
            "causal_claim": False,
            "paper_weight": False,
            "capital_authority": False,
            "use_boundary": (
                "Exact phenotype, environment, and metric compatibility selects a replication "
                "question only; the prior outcome does not transfer an effect or relabel the target."
            ),
        }
        context = {**context_body, "edge_sha256": stable_sha256(context_body)}
        atom = {
            "atom_id": f"strategy_replication:{witness_sha[:16]}",
            "question": (
                f"A source-bound {metric} outcome for {source_entity} was {status} for this exact "
                f"strategy phenotype in the same typed environment before {target_entity}'s current "
                "epoch. Which current primary evidence would replicate or falsify that operating "
                "pattern here without assuming the prior effect transfers?"
            ),
            "dimensions": ("strategy_replication", "transport_boundary", metric),
            "source_kinds": ("sec_filing", "issuer_results", "peer_filing"),
            "decision_relevance": 1.0,
            "rival_discrimination": 1.0,
            "transfer_replication": context,
        }
        return atom, context
    context_body = {
        "schema": "jaggedthoughts-strategy-counterexample-question-edge-v1",
        "kind": "counterexample",
        "strategy_transfer_index_sha256": declared,
        "strategy_transfer_card_sha256": card_sha,
        "counterexample_sha256": witness_sha,
        "source_entity_id": source_entity,
        "target_entity_id": target_entity,
        "entity_relation": "same_entity" if source_entity == target_entity else "cross_entity_public_equity",
        "mechanism_phenotype_sha256": target["mechanism_phenotype_sha256"],
        "target_environment": target["environment"],
        "target_environment_sha256": target["environment_sha256"],
        "outcome_metric_id": metric,
        "source_refs": sorted(map(str, witness.get("source_refs") or ())),
        "counterexample_available_at": available_at,
        "target_candidate_as_of": candidate_as_of,
        "causal_claim": False,
        "paper_weight": False,
        "capital_authority": False,
        "use_boundary": (
            "Exact phenotype, environment, and metric compatibility selects a question only; "
            "the prior outcome does not transfer an effect or relabel the target."
        ),
    }
    context = {**context_body, "edge_sha256": stable_sha256(context_body)}
    atom = {
        "atom_id": f"strategy_counterexample:{witness_sha[:16]}",
        "question": (
            f"A source-bound {metric} outcome for {source_entity} contradicted this exact strategy "
            f"phenotype in the same typed environment before {target_entity}'s current epoch. "
            "Which current primary evidence shows whether the recorded break condition applies here, "
            f"and which later {metric} observation would discriminate recurrence from transfer failure?"
        ),
        "dimensions": ("strategy_counterexample", "transport_boundary", metric),
        "source_kinds": ("sec_filing", "issuer_results", "peer_filing"),
        "decision_relevance": 1.0,
        "rival_discrimination": 1.0,
        "transfer_counterexample": context,
    }
    return atom, context


def _question_atoms(
    candidate: Mapping[str, Any], *, strategy_atom: Mapping[str, Any] | None = None,
    constraint_atom: Mapping[str, Any] | None = None,
    transfer_atom: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    entity_id = require_text(candidate.get("entity_id"), "research question entity_id").upper()
    entity_kind = require_text(candidate.get("entity_kind"), "research question entity_kind")
    scores = candidate.get("score_components") if isinstance(candidate.get("score_components"), Mapping) else {}
    metrics = candidate.get("metrics") if isinstance(candidate.get("metrics"), Mapping) else {}

    if entity_kind == "public_equity":
        earnings = _mean(
            _bounded(scores.get("durable_earnings_power"), 0.5),
            _bounded(scores.get("earnings_power_margin"), 0.5),
        )
        expectations = _mean(
            _bounded(scores.get("low_implied_growth"), 0.5),
            _bounded(scores.get("price_implied_excess_return"), 0.5),
        )
        quality = _bounded(scores.get("durable_earnings_power"), 0.5)
        atoms = [
            {
                "atom_id": "earnings_power_durability",
                "question": (
                    f"What primary-source evidence shows whether {entity_id}'s measured owner-earnings "
                    f"power (screen margin {_metric_text(metrics, 'earnings_power_margin')}) persists "
                    "through a weaker demand or margin state?"
                ),
                "dimensions": ("earnings_power", "durability"),
                "source_kinds": ("sec_filing", "issuer_results", "peer_filing"),
                "decision_relevance": earnings,
                "rival_discrimination": 0.78,
            },
            {
                "atom_id": "price_implied_expectations",
                "question": (
                    f"Which observable operating path would make {entity_id}'s price-implied growth "
                    f"({_metric_text(metrics, 'implied_growth')}) too low, and which path would make it justified?"
                ),
                "dimensions": ("valuation", "expectations"),
                "source_kinds": ("sec_filing", "issuer_guidance", "market_data"),
                "decision_relevance": expectations,
                "rival_discrimination": 0.82,
            },
            {
                "atom_id": "balance_sheet_survivability",
                "question": (
                    f"What liquidity, debt, dilution, and reinvestment constraints could prevent {entity_id} "
                    "from surviving long enough for the expectations gap to close?"
                ),
                "dimensions": ("balance_sheet", "capital_allocation"),
                "source_kinds": ("sec_filing", "debt_disclosure"),
                "decision_relevance": _mean(quality, 0.65),
                "rival_discrimination": 0.64,
            },
            {
                "atom_id": "industry_response",
                "question": (
                    f"Which customer, supplier, entrant, substitute, or incumbent response most threatens "
                    f"{entity_id}'s profit pool, and what primary evidence would reveal that response?"
                ),
                "dimensions": ("industry", "competitive_response"),
                "source_kinds": ("peer_filing", "regulator", "industry_primary"),
                "decision_relevance": 0.72,
                "rival_discrimination": 0.86,
            },
            {
                "atom_id": "choice_system_coherence",
                "question": (
                    f"Which reinforcing choices protect {entity_id}'s earnings power, which choices conflict, "
                    "and what feasible rival response could break the system?"
                ),
                "dimensions": ("strategy_choices", "reinforcement", "rival_response"),
                "source_kinds": ("sec_filing", "issuer_strategy", "peer_filing"),
                "decision_relevance": _mean(earnings, expectations),
                "rival_discrimination": 0.92,
            },
            {
                "atom_id": "rival_mechanism_falsifier",
                "question": (
                    f"What strongest rival mechanism explains {entity_id}'s current valuation and operating "
                    "facts, and which time-bounded observation would discriminate it from the thesis?"
                ),
                "dimensions": ("rival_mechanism", "falsifier"),
                "source_kinds": ("sec_filing", "issuer_results", "peer_filing"),
                "decision_relevance": max(earnings, expectations),
                "rival_discrimination": 1.0,
            },
        ]
        if decision_atom := _decision_boundary_atom(candidate):
            atoms.append(decision_atom)
        if strategy_atom is not None:
            atoms.append(dict(strategy_atom))
        if constraint_atom is not None:
            atoms.append(dict(constraint_atom))
        if transfer_atom is not None:
            atoms.append(dict(transfer_atom))
        return atoms

    if entity_kind != "public_fund":
        raise ValueError("research question programs support public equities and funds")
    factor = _mean(
        _bounded(scores.get("factor_fit"), 0.5),
        _bounded(scores.get("value_exposure"), 0.5),
        _bounded(scores.get("factor_implied_return"), 0.5),
    )
    valuation = _mean(
        _bounded(scores.get("low_implied_growth"), 0.5),
        _bounded(scores.get("earnings_power_margin"), 0.5),
    )
    drawdown = _bounded(scores.get("drawdown_resilience"), 0.5)
    atoms = [
        {
            "atom_id": "factor_exposure_identity",
            "question": (
                f"Which disclosed holdings and return evidence show whether {entity_id}'s apparent factor "
                "exposures are persistent portfolio design rather than a sample-period label?"
            ),
            "dimensions": ("factor_exposure", "persistence"),
            "source_kinds": ("issuer_holdings", "issuer_methodology", "market_data"),
            "decision_relevance": factor,
            "rival_discrimination": 0.84,
        },
        {
            "atom_id": "valuation_lookthrough",
            "question": (
                f"What do issuer-disclosed holdings imply about {entity_id}'s aggregate earnings yield, "
                f"growth expectations ({_metric_text(metrics, 'implied_growth')}), and concentration?"
            ),
            "dimensions": ("holdings", "valuation", "expectations"),
            "source_kinds": ("issuer_holdings", "issuer_fundamentals"),
            "decision_relevance": valuation,
            "rival_discrimination": 0.72,
        },
        {
            "atom_id": "implementation_drag",
            "question": (
                f"After fees, spreads, turnover, liquidity, taxes, and rebalance mechanics, what exposure "
                f"does an investor in {entity_id} retain?"
            ),
            "dimensions": ("fees", "liquidity", "rebalance", "tax"),
            "source_kinds": ("issuer_prospectus", "issuer_factsheet", "market_data"),
            "decision_relevance": 0.82,
            "rival_discrimination": 0.68,
        },
        {
            "atom_id": "drawdown_state_dependence",
            "question": (
                f"Which market states produced {entity_id}'s observed drawdown profile, and what portfolio "
                "mechanism would make the next state materially different?"
            ),
            "dimensions": ("drawdown", "state_dependence"),
            "source_kinds": ("issuer_holdings", "issuer_methodology", "market_data"),
            "decision_relevance": drawdown,
            "rival_discrimination": 0.76,
        },
        {
            "atom_id": "portfolio_fit",
            "question": (
                f"Which existing portfolio exposures does {entity_id} add, duplicate, or concentrate when "
                "measured through its disclosed holdings rather than its label?"
            ),
            "dimensions": ("portfolio_fit", "overlap", "concentration"),
            "source_kinds": ("issuer_holdings", "portfolio_holdings"),
            "decision_relevance": _mean(factor, drawdown),
            "rival_discrimination": 0.74,
        },
        {
            "atom_id": "rival_vehicle_falsifier",
            "question": (
                f"Which lower-cost or more precise vehicle is the strongest rival to {entity_id}, and which "
                "time-bounded exposure or implementation observation would decide between them?"
            ),
            "dimensions": ("rival_vehicle", "falsifier", "implementation"),
            "source_kinds": ("issuer_prospectus", "issuer_holdings", "market_data"),
            "decision_relevance": max(factor, valuation, drawdown),
            "rival_discrimination": 1.0,
        },
    ]
    if decision_atom := _decision_boundary_atom(candidate):
        atoms.append(decision_atom)
    return atoms


def _program_row(
    program: Any,
    atoms: Mapping[str, Mapping[str, Any]],
    *,
    arm_id: str,
    grammar: OperatorGrammar,
    interpretation: ProgramInterpretation,
) -> dict[str, Any]:
    atom_ids = tuple(interpret_program(
        program,
        grammar=grammar,
        interpretation=interpretation,
    ).value)
    selected_atoms = [atoms[atom_id] for atom_id in atom_ids]
    if arm_id == "disagreement_first":
        selected_atoms.sort(key=lambda row: (-float(row["rival_discrimination"]), str(row["atom_id"])))
    else:
        selected_atoms.sort(key=lambda row: (
            -len(row["dimensions"]), -float(row["decision_relevance"]), str(row["atom_id"]),
        ))
    dimensions = sorted({item for atom in selected_atoms for item in atom["dimensions"]})
    source_kinds = sorted({item for atom in selected_atoms for item in atom["source_kinds"]})
    relevance = sum(float(atom["decision_relevance"]) for atom in selected_atoms) / len(selected_atoms)
    discrimination = max(float(atom["rival_discrimination"]) for atom in selected_atoms)
    coverage = len(dimensions) / len({item for atom in atoms.values() for item in atom["dimensions"]})
    source_calls = max(1, len(source_kinds))
    objectives = (relevance, discrimination, coverage, 1.0 / source_calls)
    question = " ".join(
        f"({index}) {atom['question']}" for index, atom in enumerate(selected_atoms, start=1)
    )
    weights = (
        (0.30, 0.15, 0.45, 0.10)
        if arm_id == "coverage_first" else
        (0.30, 0.45, 0.15, 0.10)
    )
    return {
        "program_id": program.program_id,
        "ast": program.to_dict(),
        "atom_ids": [str(atom["atom_id"]) for atom in selected_atoms],
        "question": question,
        "source_plan": source_kinds,
        "dimensions": dimensions,
        "objectives": dict(zip(OBJECTIVES, objectives, strict=True)),
        "estimated_source_calls": source_calls,
        "selection_score": sum(weight * value for weight, value in zip(weights, objectives, strict=True)),
        "decision_boundaries": [
            dict(atom["decision_boundary"]) for atom in selected_atoms
            if isinstance(atom.get("decision_boundary"), Mapping)
        ],
    }


def compile_research_question_frontier(
    candidate: Mapping[str, Any], *, arm_id: str,
    strategy_frontier: Mapping[str, Any] | None = None,
    strategy_transfer_index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile and select one immutable question program for an agent request."""
    if arm_id not in _ARMS:
        raise ValueError(f"unsupported research question arm: {arm_id}")
    candidate_sha = require_text(candidate.get("candidate_sha256"), "research question candidate hash")
    entity_id = require_text(candidate.get("entity_id"), "research question entity_id").upper()
    strategy_atom, constraint_atom, transfer_atom, strategy_context = (
        _strategy_question_atom(
            candidate, strategy_frontier,
            strategy_transfer_index=strategy_transfer_index,
        )
        if strategy_frontier is not None else (None, None, None, None)
    )
    atom_rows = _question_atoms(
        candidate, strategy_atom=strategy_atom, constraint_atom=constraint_atom,
        transfer_atom=transfer_atom,
    )
    atoms = {str(row["atom_id"]): row for row in atom_rows}
    grammar = OperatorGrammar(
        grammar_id="jaggedthoughts.investment.research-question",
        version="1",
        terminals=tuple(
            TypedTerminal(str(row["atom_id"]), "QuestionAtom", description=str(row["question"]))
            for row in atom_rows
        ),
        operators=(
            TypedOperator("investigate", ("QuestionAtom",), "ResearchQuestionProgram"),
            TypedOperator("extend", ("ResearchQuestionProgram", "QuestionAtom"), "ResearchQuestionProgram"),
        ),
    )
    enumeration = enumerate_typed_programs(grammar, max_depth=2, max_programs=100)
    interpretation = ProgramInterpretation(
        interpretation_id=f"research-question:{entity_id}:{candidate_sha}",
        grammar_digest=grammar.grammar_digest,
        terminal_values={
            atom_id: TypedValue("QuestionAtom", (atom_id,)) for atom_id in atoms
        },
        operator_functions={
            "investigate": lambda values: TypedValue("ResearchQuestionProgram", tuple(values[0].value)),
            "extend": lambda values: TypedValue(
                "ResearchQuestionProgram", tuple(sorted(set(values[0].value) | set(values[1].value))),
            ),
        },
    )
    programs = enumeration.programs_of_type("ResearchQuestionProgram")
    rows = {
        program.program_id: _program_row(
            program,
            atoms,
            arm_id=arm_id,
            grammar=grammar,
            interpretation=interpretation,
        )
        for program in programs
    }
    evaluations = tuple(
        CandidateEvaluation(
            program_id=program_id,
            objective_values=tuple(float(row["objectives"][name]) for name in OBJECTIVES),
            behavior_signature=tuple(row["atom_ids"]),
            evidence_refs=tuple([
                f"candidate:{candidate_sha}",
                *(
                    [f"strategy_frontier:{strategy_context['strategy_frontier_sha256']}"]
                    if strategy_context is not None
                    and any(str(atom_id).startswith((
                        "strategy_option_evidence:", "strategy_constraint_evidence:",
                    )) for atom_id in row["atom_ids"]) else []
                ),
                *(
                    [
                        f"strategy_transfer_card:{strategy_context['transfer_counterexample']['strategy_transfer_card_sha256']}",
                        f"strategy_counterexample:{strategy_context['transfer_counterexample']['counterexample_sha256']}",
                    ]
                    if strategy_context is not None
                    and isinstance(strategy_context.get("transfer_counterexample"), Mapping)
                    and any(
                        str(atom_id).startswith("strategy_counterexample:")
                        for atom_id in row["atom_ids"]
                    ) else []
                ),
                *(
                    [
                        f"strategy_transfer_card:{strategy_context['transfer_replication']['strategy_transfer_card_sha256']}",
                        f"strategy_replication:{strategy_context['transfer_replication']['outcome_witness_sha256']}",
                    ]
                    if strategy_context is not None
                    and isinstance(strategy_context.get("transfer_replication"), Mapping)
                    and any(
                        str(atom_id).startswith("strategy_replication:")
                        for atom_id in row["atom_ids"]
                    ) else []
                ),
            ]),
        )
        for program_id, row in rows.items()
    )
    signatures = {program_id: set(row["atom_ids"]) for program_id, row in rows.items()}
    edges = tuple(
        (left, right)
        for index, left in enumerate(sorted(signatures))
        for right in sorted(signatures)[index + 1:]
        if len(signatures[left] ^ signatures[right]) == 1
    )
    neighborhood = Neighborhood(
        neighborhood_id=f"research-question-edit:{candidate_sha}", edges=edges,
    )
    scope = FrontierScope(
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type="ResearchQuestionProgram",
        max_depth=enumeration.max_depth,
        max_programs=enumeration.max_programs,
        evaluation_model_id="research-question-routing-prior-v1",
        landscape_mode="fixed",
        evidence_epoch=candidate_sha,
        objective_names=OBJECTIVES,
        neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope,
        enumeration=enumeration,
        evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=RepresentationAudit(
            audit_id=f"research-question-library:{candidate_sha}",
            status="residual",
            residuals=("The fixed atom library may omit a decisive candidate-specific question.",),
            evidence_refs=(f"candidate:{candidate_sha}",),
        ),
    )
    frontier_rows = [rows[program_id] for program_id in certificate.frontier_program_ids]
    selected = max(
        frontier_rows,
        key=lambda row: (
            float(row["selection_score"]),
            -int(row["estimated_source_calls"]),
            str(row["program_id"]),
        ),
    )
    decision_context = next((
        dict(row["decision_boundary"]) for row in atom_rows
        if isinstance(row.get("decision_boundary"), Mapping)
    ), None)
    body: dict[str, Any] = {
        "schema": RESEARCH_QUESTION_FRONTIER_SCHEMA,
        "entity_id": entity_id,
        "candidate_sha256": candidate_sha,
        "policy_arm": arm_id,
        "grammar": grammar.to_dict(),
        "enumeration": {
            "enumeration_digest": enumeration.enumeration_digest,
            "program_count": len(enumeration.programs),
            "target_program_count": len(programs),
            "max_depth": enumeration.max_depth,
            "max_programs": enumeration.max_programs,
            "exhausted_within_scope": enumeration.exhausted_within_scope,
            "residuals": [row.to_dict() for row in enumeration.residuals],
        },
        "closure": {
            "certificate_sha256": certificate.certificate_sha256,
            "frontier_program_ids": list(certificate.frontier_program_ids),
            "frontier_count": len(certificate.frontier_program_ids),
            "dominated_count": len(certificate.dominated),
            "equivalent_count": len(certificate.equivalent),
            "local_peak_program_ids": list(certificate.local_peak_program_ids),
            "scope_closed": certificate.scope_closed,
            "decision_closed": certificate.decision_closed,
            "representation_residuals": list(certificate.representation_audit.residuals),
        },
        "frontier_programs": frontier_rows,
        "selected_program": selected,
        **({"decision_context": decision_context} if decision_context is not None else {}),
        **({"strategy_context": strategy_context} if strategy_context is not None else {}),
        "score_identity": "unsettled_research_routing_prior_v1",
        "capital_authority": False,
        "use_boundary": (
            "The selected program orders public evidence acquisition. Its proxy scores require "
            "prospective matched settlement and cannot label an investment or alter a portfolio."
        ),
    }
    return {**body, "question_frontier_sha256": stable_sha256(body)}


__all__ = [
    "OBJECTIVES",
    "RESEARCH_QUESTION_FRONTIER_SCHEMA",
    "compile_research_question_frontier",
]
