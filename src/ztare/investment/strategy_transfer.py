"""Queryable projections of strategy laws, moderators, and counterexamples."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .institutional_learning import (
    LAW_EVALUATION_SCHEMA,
    LEARNING_STATE_SCHEMA,
    compile_law_candidate,
)
from .strategy_learning import STRATEGY_MOVE_LIBRARY_SCHEMA


STRATEGY_TRANSFER_INDEX_SCHEMA = "jaggedthoughts-strategy-transfer-index-v1"
STRATEGY_TRANSFER_CARD_SCHEMA = "jaggedthoughts-strategy-transfer-law-card-v1"
STRATEGY_LEARNING_CHAIN_SCHEMA = "jaggedthoughts-strategy-learning-chain-v1"
STRATEGY_PROGRAM_TRANSFER_INDEX_SCHEMA = "jaggedthoughts-strategy-program-transfer-index-v1"


def _moderator_slice(move: Mapping[str, Any]) -> dict[str, Any]:
    environment = dict(move.get("environment") or {})
    return {
        "industry_boundary": str(environment.get("industry_boundary") or "unclassified"),
        "addressed_actor_kinds": sorted(map(str, environment.get("addressed_actor_kinds") or ())),
        "industry_actor_kinds": sorted(map(str, environment.get("industry_actor_kinds") or ())),
    }


def _card_status(
    episodes: list[dict[str, Any]], evaluation: Mapping[str, Any] | None,
    *, entity_count: int, moderator_count: int,
) -> str:
    statuses = {row["status"] for row in episodes}
    evaluation_status = str((evaluation or {}).get("status") or "")
    if "contradicts" in statuses:
        return "challenged_by_settled_operating_outcome"
    if evaluation_status.startswith("challenged"):
        return "challenged_by_causal_diagnostic"
    if evaluation_status in {"diagnostic_supported", "prospective_transfer_candidate"}:
        return "prospective_transfer_candidate"
    if "supports" in statuses and entity_count > 1 and moderator_count > 1:
        return "descriptive_cross_environment_pattern"
    if episodes:
        return "descriptive_operating_evidence"
    return "conjecture_awaiting_outcomes"


def _learning_chain(
    candidate: Mapping[str, Any], moves: list[dict[str, Any]],
    episodes: list[dict[str, Any]], evaluation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Expose the falsifiable strategy-law lifecycle without re-estimating it."""
    diagnostic = dict(evaluation or {})
    regularity = dict(diagnostic.get("strategy_regularity") or {})
    holdout = dict(regularity.get("prospective_holdout") or {})
    required = dict(holdout.get("required") or {})
    observed = dict(holdout.get("observed") or {})
    receipt = dict(candidate.get("generation_receipt") or {})
    multiplicity_rows = list((diagnostic.get("multiplicity") or {}).get("rows") or ())
    gaps = []
    for label, required_key, observed_key in (
        ("independent_treated_units", "treated_units", "independent_treated_units"),
        ("bounded_control_units", "control_units", "bounded_control_units"),
        ("transfer_environments", "transfer_environments", "transfer_environments"),
    ):
        missing = max(0, int(required.get(required_key) or 0) - int(observed.get(observed_key) or 0))
        if missing:
            gaps.append({"kind": label, "missing_count": missing})
    if not regularity:
        gaps.append({"kind": "prospective_holdout", "missing_count": 1})
    if diagnostic.get("status") == "prospective_transfer_candidate" and not (
        multiplicity_rows and all(row.get("rejected_at_alpha") for row in multiplicity_rows)
    ):
        gaps.append({"kind": "multiplicity_clearance", "missing_count": 1})

    frontier_shas = sorted({
        str(row["strategy_frontier_sha256"])
        for row in moves if row.get("strategy_frontier_sha256")
    })
    move_entities = sorted({str(row.get("entity_id")) for row in moves})
    latest_outcome = max((str(row["available_at"]) for row in episodes), default=None)
    body = {
        "schema": STRATEGY_LEARNING_CHAIN_SCHEMA,
        "frontier_origin": {
            "strategy_frontier_sha256s": frontier_shas,
            "frontier_member_move_count": sum(bool(row.get("frontier_bundle_count")) for row in moves),
            "local_peak_move_count": sum(bool(row.get("local_peak_bundle_count")) for row in moves),
            "boundary": "Frontier membership is frozen pre-outcome description, never an effect label.",
        },
        "conjecture": {
            "law_key": candidate["law_key"], "law_sha256": candidate["law_sha256"],
            "question": candidate["question"], "not_before": candidate["not_before"],
            "outcome_metric_id": candidate["outcome_metric_id"],
        },
        "typed_phenotype": {
            "mechanism_phenotype_sha256": receipt.get("mechanism_phenotype_sha256"),
            "mechanism_phenotype": dict(moves[0].get("mechanism_phenotype") or {}),
            "focal_move_sha256s": sorted(str(row.get("move_sha256")) for row in moves),
        },
        "cohort": {
            "seed_industry_ids": sorted(map(str, receipt.get("seed_industry_ids") or ())),
            "observed_entity_ids": move_entities,
            "observed_company_count": len(move_entities),
            "declared_entity_kinds": list(candidate["cohort"]["entity_kinds"]),
        },
        "point_in_time_outcomes": {
            "settled_episode_count": len(episodes),
            "episode_sha256s": sorted(str(row["episode_sha256"]) for row in episodes),
            "latest_available_at": latest_outcome,
            "prospective_panel_row_count": len(
                (regularity.get("provenance") or {}).get("prospective_panel_row_sha256s") or ()
            ),
        },
        "holdout_and_power": {
            "status": regularity.get("status", "awaiting_prospective_holdout"),
            "eligible": bool(holdout.get("eligible")),
            "power_status": holdout.get("power_status", "unmeasured"),
            "required": required, "observed": observed,
            "two_sided_p_value": holdout.get("two_sided_p_value"),
            "multiplicity_cleared": bool(multiplicity_rows) and all(
                row.get("rejected_at_alpha") for row in multiplicity_rows
            ),
        },
        "transfer": {
            "cross_company_observed": len(move_entities) >= 2,
            "cross_industry_tested": int(observed.get("transfer_environments") or 0) >= 2,
            "promotion_eligible": bool(diagnostic.get("promotion_eligible")),
            "counterexample_count": len(regularity.get("counterexamples") or ()),
            "remaining_gaps": gaps,
        },
        "capital_authority": False,
    }
    return {**body, "learning_chain_sha256": stable_sha256(body)}


def compile_strategy_transfer_index(
    move_library: Mapping[str, Any], learning_state: Mapping[str, Any], *, generated_at: str,
) -> dict[str, Any]:
    """Project existing strategy-law evidence into searchable cards.

    This function estimates nothing. It preserves the current law evaluation and
    exposes source-bound operating contradictions as first-class witnesses.
    """
    if move_library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        raise ValueError(f"strategy transfer requires {STRATEGY_MOVE_LIBRARY_SCHEMA}")
    if learning_state.get("schema") != LEARNING_STATE_SCHEMA:
        raise ValueError(f"strategy transfer requires {LEARNING_STATE_SCHEMA}")
    epoch = canonical_timestamp(generated_at, "strategy transfer generated_at")
    evaluations = {
        str(row.get("law_key")): dict(row)
        for row in learning_state.get("evaluations") or ()
        if isinstance(row, Mapping)
        and row.get("schema") == LAW_EVALUATION_SCHEMA
        and timestamp_key(str(row.get("generated_at"))) <= timestamp_key(epoch)
    }
    moves_by_phenotype: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in move_library.get("moves") or ():
        if isinstance(raw, Mapping) and raw.get("mechanism_phenotype_sha256"):
            moves_by_phenotype[str(raw["mechanism_phenotype_sha256"])].append(dict(raw))

    cards = []
    for raw_candidate in learning_state.get("candidates") or ():
        if not isinstance(raw_candidate, Mapping) or raw_candidate.get("origin") != "strategy_phenotype_compiler":
            continue
        candidate = compile_law_candidate(raw_candidate)
        if timestamp_key(candidate["created_at"]) > timestamp_key(epoch):
            continue
        phenotype_sha = str(candidate["generation_receipt"].get("mechanism_phenotype_sha256") or "")
        moves = moves_by_phenotype.get(phenotype_sha, [])
        if len(phenotype_sha) != 64 or not moves:
            continue
        if any(str(row.get("mechanism_phenotype_sha256")) != phenotype_sha for row in moves):
            raise ValueError("strategy transfer card crossed phenotype identity")
        phenotype = dict(moves[0].get("mechanism_phenotype") or {})
        if any(dict(row.get("mechanism_phenotype") or {}) != phenotype for row in moves):
            raise ValueError("one phenotype hash resolved to incompatible strategy phenotypes")

        episodes = []
        episode_moves: dict[str, dict[str, Any]] = {}
        for move in moves:
            for raw_episode in move.get("outcome_episodes") or ():
                episode = dict(raw_episode)
                if timestamp_key(str(episode.get("available_at"))) > timestamp_key(epoch):
                    continue
                if episode.get("status") not in {"supports", "contradicts", "inconclusive"}:
                    raise ValueError("strategy outcome episode has an unsupported status")
                episode_sha = str(episode.get("episode_sha256") or "")
                if len(episode_sha) != 64 or not episode.get("source_refs"):
                    raise ValueError("strategy transfer outcomes require hashed source-bound episodes")
                if episode_sha in episode_moves and episode_moves[episode_sha] != move:
                    raise ValueError("strategy outcome episode crossed move identity")
                episodes.append(episode)
                episode_moves[episode_sha] = move

        slices: dict[str, dict[str, Any]] = {}
        for move in moves:
            moderators = _moderator_slice(move)
            moderator_sha = stable_sha256(moderators)
            row = slices.setdefault(moderator_sha, {
                "moderator_sha256": moderator_sha,
                "moderators": moderators,
                "entity_ids": set(),
                "move_sha256s": set(),
                "outcome_episode_sha256s": [],
                "outcome_status_counts": Counter(),
            })
            row["entity_ids"].add(str(move.get("entity_id")))
            row["move_sha256s"].add(str(move.get("move_sha256")))
        for episode in episodes:
            move = episode_moves[episode["episode_sha256"]]
            row = slices[stable_sha256(_moderator_slice(move))]
            row["outcome_episode_sha256s"].append(episode["episode_sha256"])
            row["outcome_status_counts"][episode["status"]] += 1
        moderator_slices = [{
            **row,
            "entity_ids": sorted(row["entity_ids"]),
            "move_sha256s": sorted(row["move_sha256s"]),
            "outcome_episode_sha256s": sorted(row["outcome_episode_sha256s"]),
            "outcome_status_counts": dict(sorted(row["outcome_status_counts"].items())),
        } for _, row in sorted(slices.items())]

        counterexamples = []
        outcome_witnesses = []
        for episode in episodes:
            move = episode_moves[episode["episode_sha256"]]
            witness = {
                "kind": "settled_operating_outcome",
                "episode_sha256": episode["episode_sha256"],
                "move_sha256": move["move_sha256"],
                "entity_id": episode["entity_id"],
                "metric_id": episode["metric_id"],
                "unit": episode.get("unit"),
                "estimated_effect": episode["estimated_effect"],
                "status": episode["status"],
                "available_at": episode["available_at"],
                "moderators": _moderator_slice(move),
                "source_refs": list(episode["source_refs"]),
            }
            outcome_witnesses.append({**witness, "witness_sha256": stable_sha256(witness)})
            if episode["status"] == "contradicts":
                counterexample = {
                    key: value for key, value in witness.items()
                    if key not in {"unit", "status"}
                }
                counterexamples.append({
                    **counterexample,
                    "counterexample_sha256": stable_sha256(counterexample),
                })
        evaluation = evaluations.get(candidate["law_key"])
        if evaluation and evaluation.get("law_sha256") != candidate["law_sha256"]:
            raise ValueError("strategy transfer evaluation crossed law identity")
        entity_ids = sorted({str(row.get("entity_id")) for row in moves})
        status = _card_status(
            episodes, evaluation, entity_count=len(entity_ids), moderator_count=len(moderator_slices),
        )
        learning_chain = _learning_chain(candidate, moves, episodes, evaluation)
        body = {
            "schema": STRATEGY_TRANSFER_CARD_SCHEMA,
            "card_id": f"strategy-transfer:{phenotype_sha[:16]}:{candidate['law_sha256'][:12]}",
            "law_key": candidate["law_key"],
            "law_sha256": candidate["law_sha256"],
            "mechanism_phenotype_sha256": phenotype_sha,
            "mechanism_phenotype": phenotype,
            "outcome_metric_id": candidate["outcome_metric_id"],
            "entity_ids": entity_ids,
            "move_sha256s": sorted(str(row.get("move_sha256")) for row in moves),
            "moderator_slices": moderator_slices,
            "settled_operating_outcome_count": len(episodes),
            "outcome_status_counts": dict(sorted(Counter(row["status"] for row in episodes).items())),
            "causal_diagnostic": evaluation,
            "learning_chain": learning_chain,
            "outcome_witnesses": sorted(
                outcome_witnesses, key=lambda row: row["witness_sha256"],
            ),
            "counterexamples": sorted(counterexamples, key=lambda row: row["counterexample_sha256"]),
            "status": status,
            "promotion_eligible": (
                status == "prospective_transfer_candidate"
                and bool((evaluation or {}).get("promotion_eligible", False))
            ),
            "authority": "research_projection_only",
            "capital_authority": False,
        }
        cards.append({**body, "card_sha256": stable_sha256(body)})
    index_body = {
        "schema": STRATEGY_TRANSFER_INDEX_SCHEMA,
        "generated_at": epoch,
        "move_library_sha256": move_library.get("library_sha256"),
        "learning_state_sha256": learning_state.get("state_sha256"),
        "card_count": len(cards),
        "settled_operating_outcome_count": sum(
            row["settled_operating_outcome_count"] for row in cards
        ),
        "counterexample_count": sum(len(row["counterexamples"]) for row in cards),
        "cross_company_observed_count": sum(
            bool(row["learning_chain"]["transfer"]["cross_company_observed"]) for row in cards
        ),
        "cross_industry_tested_count": sum(
            bool(row["learning_chain"]["transfer"]["cross_industry_tested"]) for row in cards
        ),
        "cards": sorted(cards, key=lambda row: row["card_id"]),
        "status": (
            "no_exact_strategy_law"
            if not cards
            else "prospective_transfer_candidate"
            if any(row["status"] == "prospective_transfer_candidate" for row in cards)
            else "learning_from_operating_outcomes"
            if any(row["settled_operating_outcome_count"] for row in cards)
            else "conjectures_awaiting_operating_outcomes"
        ),
        "next_activation": (
            "Compile an exact strategy phenotype into a law candidate."
            if not cards
            else "Settle source-bound operating outcomes and search for break cases across moderator slices."
        ),
        "authority": "research_projection_only",
        "capital_authority": False,
    }
    return {**index_body, "index_sha256": stable_sha256(index_body)}


def compile_strategy_program_transfer_index(
    plans: list[Mapping[str, Any]], episodes: list[Mapping[str, Any]], *, generated_at: str,
) -> dict[str, Any]:
    """Group prospective program outcomes by transferable constituent phenotype."""
    epoch = canonical_timestamp(generated_at, "strategy program transfer generated_at")
    valid_plans = {}
    for plan in plans:
        if plan.get("schema") != "jaggedthoughts-strategy-program-outcome-plan-v1":
            continue
        declared = str(plan.get("plan_sha256") or "")
        if declared != stable_sha256({key: value for key, value in plan.items() if key != "plan_sha256"}):
            continue
        valid_plans[declared] = dict(plan)
    readout_owner = {
        str(readout.get("readout_sha256")): plan_sha
        for plan_sha, plan in valid_plans.items()
        for readout in plan.get("readouts") or () if readout.get("readout_sha256")
    }
    episode_by_readout = {}
    for episode in episodes:
        if episode.get("schema") != "jaggedthoughts-strategy-program-outcome-v1":
            continue
        declared = str(episode.get("episode_sha256") or "")
        if declared != stable_sha256({key: value for key, value in episode.items() if key != "episode_sha256"}):
            continue
        if (
            str(episode.get("plan_sha256") or "") not in valid_plans
            or readout_owner.get(str(episode.get("readout_sha256") or ""))
            != str(episode.get("plan_sha256") or "")
        ):
            raise ValueError("strategy program outcome crossed its prospective plan")
        if timestamp_key(str(episode["available_at"])) <= timestamp_key(epoch):
            episode_by_readout[str(episode["readout_sha256"])] = dict(episode)

    groups: dict[tuple[Any, ...], list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for plan in valid_plans.values():
        if "global_frontier" not in set(map(str, plan.get("program_roles") or ())):
            continue
        phenotype_sha = str(plan.get("program_phenotype_sha256") or "")
        if not phenotype_sha:
            continue
        for readout in plan.get("readouts") or ():
            key = (
                phenotype_sha, str(readout["metric_id"]), str(readout["unit"]),
                str(readout["direction"]), float(readout["minimum_effect"]),
                int(readout["horizon_days"]),
                str(readout.get("outcome_role") or "terminal_operating"),
                str(readout.get("acquisition_mode") or "subscription_primary_document"),
                str(readout.get("source_definition_sha256") or ""),
            )
            groups[key].append((plan, dict(readout)))

    cards = []
    for key, rows in sorted(groups.items()):
        (
            phenotype_sha, metric_id, unit, direction, threshold, horizon_days,
            outcome_role, acquisition_mode, source_definition_sha256,
        ) = key
        settled = [
            episode_by_readout[str(readout["readout_sha256"])]
            for _, readout in rows if str(readout["readout_sha256"]) in episode_by_readout
        ]
        entity_ids = sorted({str(plan["entity_id"]) for plan, _ in rows})
        environments = sorted({
            value for plan, _ in rows for value in plan.get("environment_boundaries") or ()
        })
        status_counts = Counter(str(row["assessment"]) for row in settled)
        descriptive_support_ready = (
            len(entity_ids) >= 4 and len(environments) >= 2 and len(settled) >= 4
        )
        program_roles = sorted({
            str(role)
            for plan, _ in rows for role in plan.get("program_roles") or ()
            if role in {"global_frontier", "local_peak"}
        })
        composition_blockers = ["same_constituent_fragmented_controls_missing"]
        if not program_roles:
            composition_blockers.append("frozen_frontier_role_missing")
        body = {
            "schema": "jaggedthoughts-strategy-program-transfer-card-v1",
            "program_phenotype_sha256": phenotype_sha,
            "program_phenotype": rows[0][0]["program_phenotype"],
            "metric_id": metric_id, "unit": unit, "direction": direction,
            "minimum_effect": threshold, "horizon_days": horizon_days,
            "outcome_role": outcome_role, "acquisition_mode": acquisition_mode,
            "source_definition_sha256": source_definition_sha256,
            "entity_ids": entity_ids, "environment_boundaries": environments,
            "prospective_plan_count": len(rows), "settled_episode_count": len(settled),
            "episode_sha256s": sorted(str(row["episode_sha256"]) for row in settled),
            "outcome_status_counts": dict(sorted(status_counts.items())),
            "counterexample_episode_sha256s": sorted(
                str(row["episode_sha256"]) for row in settled
                if row["assessment"] == "contradicts"
            ),
            "descriptive_support_ready": descriptive_support_ready,
            # The current input contract contains exact integrated-program plans
            # and outcomes only.  Counts on that treated support cannot identify
            # whether coordination added value beyond the same moves in isolation.
            "composition_increment_design": {
                "estimand": "joint_program_minus_same_constituents_without_joint_adoption",
                "treated_identity": "exact_integrated_program_adoption",
                "control_identity": "same_constituent_moves_without_joint_execution_evidence",
                "held_constant": [
                    "constituent_mechanism_phenotype_sha256s", "metric_id", "unit",
                    "direction", "minimum_effect", "horizon_days", "environment",
                    "outcome_role", "acquisition_mode", "source_definition_sha256",
                ],
                "program_roles": program_roles,
                "matched_fragmented_control_count": 0,
                "ready": False,
                "blockers": composition_blockers,
            },
            "composition_increment_ready": False,
            "comparison_ready": descriptive_support_ready,
            "status": (
                "descriptive_support_ready_missing_composition_control"
                if descriptive_support_ready else
                "descriptive_cross_company_pattern" if len(entity_ids) >= 2 and settled else
                "descriptive_single_company_outcome" if settled else
                "awaiting_program_outcomes"
            ),
            "causal_program_credit_eligible": False,
            "rank_authority": False, "capital_authority": False,
        }
        cards.append({**body, "card_sha256": stable_sha256(body)})
    body = {
        "schema": STRATEGY_PROGRAM_TRANSFER_INDEX_SCHEMA, "generated_at": epoch,
        "card_count": len(cards), "settled_episode_count": len(episode_by_readout),
        "cross_company_card_count": sum(len(row["entity_ids"]) >= 2 for row in cards),
        "comparison_ready_card_count": sum(row["comparison_ready"] for row in cards),
        "composition_increment_ready_card_count": sum(
            row["composition_increment_ready"] for row in cards
        ),
        "cards": cards,
        "next_activation": (
            "Acquire matched same-constituent fragmented-adoption controls before assigning program-composition or frontier credit."
            if any(row["comparison_ready"] for row in cards) else
            "Accumulate independent program adoptions and prospective outcomes across environments."
        ),
        "causal_program_credit": False, "capital_authority": False,
    }
    return {**body, "index_sha256": stable_sha256(body)}


def query_strategy_transfer(
    index: Mapping[str, Any], *, phenotype_sha256: str | None = None,
    action: str | None = None, economic_bridge: str | None = None,
    moderators: Mapping[str, Any] | None = None, status: str | None = None,
) -> dict[str, Any]:
    """Return exact-matching cards and their operating counterexamples."""
    if index.get("schema") != STRATEGY_TRANSFER_INDEX_SCHEMA:
        raise ValueError(f"strategy transfer query requires {STRATEGY_TRANSFER_INDEX_SCHEMA}")
    wanted = dict(moderators or {})

    def matches(card: Mapping[str, Any]) -> bool:
        phenotype = card["mechanism_phenotype"]
        if phenotype_sha256 and card["mechanism_phenotype_sha256"] != phenotype_sha256:
            return False
        if action and phenotype.get("action") != action:
            return False
        if economic_bridge and phenotype.get("economic_bridge") != economic_bridge:
            return False
        if status and card["status"] != status:
            return False
        return not wanted or any(
            all(row["moderators"].get(key) == value for key, value in wanted.items())
            for row in card["moderator_slices"]
        )

    cards = [dict(row) for row in index.get("cards") or () if matches(row)]
    return {
        "schema": "jaggedthoughts-strategy-transfer-query-result-v1",
        "index_sha256": index.get("index_sha256"),
        "card_count": len(cards),
        "counterexample_count": sum(len(row["counterexamples"]) for row in cards),
        "cards": cards,
        "capital_authority": False,
    }


__all__ = [
    "STRATEGY_TRANSFER_CARD_SCHEMA",
    "STRATEGY_TRANSFER_INDEX_SCHEMA",
    "STRATEGY_LEARNING_CHAIN_SCHEMA",
    "STRATEGY_PROGRAM_TRANSFER_INDEX_SCHEMA",
    "compile_strategy_program_transfer_index",
    "compile_strategy_transfer_index",
    "query_strategy_transfer",
]
