"""Sealed analyst-time holdouts for recursively generated strategy laws."""

from __future__ import annotations

from datetime import datetime, timezone
import inspect
from itertools import combinations
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import bh_fdr

from .historical_strategy_bulk_effects import _law, _rows
from .historical_strategy_law_search import _first_adoptions, _parent_cells, _checked
from .institutional_learning import evaluate_difference_in_differences


_ROOT = Path("institutional_learning/historical_strategy_bulk_outcomes/law-trials")
SCHEMA = "jaggedthoughts-historical-strategy-law-trial-v3"
SPARSE_SCHEMA = "jaggedthoughts-historical-strategy-law-trial-v4"
_SUPPORTED_SCHEMAS = {SCHEMA, SPARSE_SCHEMA}

_OUTCOMES = (
    {"metric_id": "owner_earnings_margin", "history_field": "owner_earnings_margin",
     "unit": "decimal", "role": "economic_primary",
     "definition": "(operating_cash_flow_fy - capital_expenditure_fy) / revenue_fy"},
    {"metric_id": "owner_earnings_balance", "history_field": "owner_earnings_balance",
     "unit": "score", "role": "unit_invariant_tail_stress",
     "definition": "owner_earnings_margin / (1 + abs(owner_earnings_margin))"},
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _trial_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    identity = {
        "program_id": row["program_id"],
        "moderator_fields": list(row["moderator_fields"]),
        "parent": dict(row["parent"]),
        "moderators": dict(row["moderators"]),
        "outcome_metric_ids": ["owner_earnings_margin", "owner_earnings_balance"],
        "estimator": "group_time_att_unadjusted",
        "expected_direction": "positive",
    }
    return {
        "candidate_identity": identity,
        "candidate_identity_sha256": stable_sha256(identity),
        "training_treated_entity_ids": sorted(row["treated_entity_ids"]),
        "training_future_adopter_entity_ids": sorted(row["future_adopter_entity_ids"]),
        "training_event_sha256s": sorted({
            *row["treated_event_sha256s"], *row["future_adopter_event_sha256s"],
        }),
    }


def _evaluation_contract() -> dict[str, Any]:
    body = {
        "schema": "jaggedthoughts-historical-strategy-law-trial-abi-v1",
        "outcomes": [dict(row) for row in _OUTCOMES],
        "estimator": {
            "kind": "difference_in_differences",
            "design": "group_time_att_unadjusted",
            "control_group": "not_yet_treated",
            "implementation_id": "ztare.investment.institutional_learning.group_time_att_v3",
            "parallel_trend_tolerance": 0.10,
            "bootstrap_iterations": 1000,
        },
        "minimum_support": {"treated_entities": 4, "future_adopter_entities": 4},
        "implementation_source_sha256": stable_sha256({
            "law": inspect.getsource(_law),
            "rows": inspect.getsource(_rows),
            "evaluate": inspect.getsource(evaluate_difference_in_differences),
            "first_adoptions": inspect.getsource(_first_adoptions),
            "parent_cells": inspect.getsource(_parent_cells),
            "evaluate_candidate": inspect.getsource(_evaluate_candidate),
        }),
    }
    return {**body, "contract_sha256": stable_sha256(body)}


def _sum_bools(z3: Any, values: Iterable[Any]) -> Any:
    rows = list(values)
    return z3.Sum([z3.If(value, 1, 0) for value in rows]) if rows else z3.IntVal(0)


def compile_sparse_strategy_law_trial_design(
    workspace: str | Path, *, law_search: Mapping[str, Any],
    reserve_per_role: int = 8, max_candidates: int = 3,
) -> dict[str, Any]:
    """Use SMT to reserve a disjoint, outcome-blind historical holdout family."""
    if reserve_per_role < 4 or max_candidates < 1:
        raise ValueError("sparse law trial requires four-plus reserves and a candidate")
    import z3

    root = Path(workspace).expanduser().resolve()
    corpus = _checked(
        root / "institutional_learning/historical_strategy_bulk_corpus/latest.json",
        "corpus_sha256",
    )
    coverage = _checked(
        root / "institutional_learning/historical_strategy_bulk_outcomes/coverage.json",
        "coverage_sha256",
    )
    event_path = (root / str(corpus["event_lake_path"])).resolve()
    event_path.relative_to(root)
    events = [
        json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    acquired = set()
    acquired_ciks = set()
    for directory in (
        root / "institutional_learning/historical_strategy_event_replay/filings",
        root / "institutional_learning/historical_strategy_bulk_learning/classifications",
    ):
        for path in directory.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                acquired.add(str(payload["accession_number"]))
                acquired_ciks.add(str(payload["cik"]))
            except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
    periods_by_cik = {
        str(row["cik"]): {int(value[:4]) for value in row["complete_periods"]}
        for row in coverage.get("entities") or ()
    }
    representatives: dict[str, Mapping[str, Any]] = {}
    for row in law_search.get("frozen_child_candidates") or ():
        behavior = stable_sha256({
            "parent": row["parent"],
            "treated_entity_ids": sorted(row["treated_entity_ids"]),
            "future_adopter_entity_ids": sorted(row["future_adopter_entity_ids"]),
        })
        prior = representatives.get(behavior)
        if prior is None or (
            len(row["moderator_fields"]), str(row["cell_sha256"])
        ) < (
            len(prior["moderator_fields"]), str(prior["cell_sha256"])
        ):
            representatives[behavior] = row
    rows = sorted(representatives.values(), key=lambda row: str(row["cell_sha256"]))
    candidates = {_trial_candidate(row)["candidate_identity_sha256"]: row for row in rows}
    eligible: dict[tuple[str, str], set[str]] = {}
    training: dict[str, set[str]] = {}
    for candidate_sha, row in candidates.items():
        parent = row["parent"]
        year, sic2 = int(parent["adoption_year"]), str(parent["sic2"])
        training[candidate_sha] = {
            *map(str, row["treated_entity_ids"]),
            *map(str, row["future_adopter_entity_ids"]),
        }
        eligible[candidate_sha, "treated"] = set()
        eligible[candidate_sha, "future_adopter"] = set()
        for event in events:
            accession, cik = str(event["accession_number"]), str(event["cik"])
            event_year = int(str(event["occurred_at"])[:4])
            periods = periods_by_cik.get(cik, set())
            if (
                accession in acquired or cik in acquired_ciks
                or cik in training[candidate_sha]
                or (str(event.get("sic") or "")[:2] or "unknown") != sic2
                or sum(value < event_year for value in periods) < 3
                or sum(value > event_year for value in periods) < 1
            ):
                continue
            if event_year == year:
                eligible[candidate_sha, "treated"].add(cik)
            elif event_year > year:
                eligible[candidate_sha, "future_adopter"].add(cik)

    capacity_candidates = sorted(
        candidate_sha for candidate_sha in candidates
        if all(len(eligible[candidate_sha, role]) >= reserve_per_role
               for role in ("treated", "future_adopter"))
    )

    def solve_reservation(candidate_ids: tuple[str, ...]) -> dict[str, Any] | None:
        family_training = set().union(*(training[value] for value in candidate_ids))
        solver = z3.Solver()
        assigned = {}
        for candidate_index, candidate_sha in enumerate(candidate_ids):
            for role_index, role in enumerate(("treated", "future_adopter")):
                variables = []
                for cik_index, cik in enumerate(sorted(
                    eligible[candidate_sha, role] - family_training
                )):
                    variable = z3.Bool(
                        f"reserve_{candidate_index}_{role_index}_{cik_index}"
                    )
                    assigned[candidate_sha, role, cik] = variable
                    variables.append(variable)
                solver.add(_sum_bools(z3, variables) == reserve_per_role)
        for cik in sorted({key[2] for key in assigned}):
            solver.add(_sum_bools(
                z3, (variable for key, variable in assigned.items() if key[2] == cik),
            ) <= 1)
        if solver.check() != z3.sat:
            return None
        model = solver.model()
        return {
            candidate_sha: {
                role: sorted(
                    cik for (owner, assigned_role, cik), variable in assigned.items()
                    if owner == candidate_sha and assigned_role == role
                    and z3.is_true(model.eval(variable, model_completion=True))
                )
                for role in ("treated", "future_adopter")
            }
            for candidate_sha in candidate_ids
        }

    cardinality_checks = []
    selected_ids: list[str] = []
    reservations = None
    for target in range(min(max_candidates, len(capacity_candidates)), 0, -1):
        tested = 0
        for candidate_ids in combinations(capacity_candidates, target):
            tested += 1
            witness = solve_reservation(candidate_ids)
            if witness is not None:
                selected_ids = list(candidate_ids)
                reservations = witness
                break
        cardinality_checks.append({
            "candidate_count": target, "combination_count_tested": tested,
            "verdict": "sat" if reservations is not None else "unsat",
        })
        if reservations is not None:
            break
    if reservations is None:
        raise ValueError("no recursively generated law has a viable sparse holdout")
    used = [cik for row in reservations.values() for ids in row.values() for cik in ids]
    if len(used) != len(set(used)) or any(
        len(reservations[candidate_sha][role]) < reserve_per_role
        for candidate_sha in selected_ids for role in ("treated", "future_adopter")
    ):
        raise ValueError("sparse law-trial reservation witness failed replay")
    body = {
        "schema": "jaggedthoughts-historical-strategy-law-trial-design-v1",
        "law_search_sha256": law_search["law_search_sha256"],
        "bulk_corpus_sha256": corpus["corpus_sha256"],
        "outcome_coverage_sha256": coverage["coverage_sha256"],
        "candidate_count_before_behavioral_dedup": len(
            law_search.get("frozen_child_candidates") or ()
        ),
        "candidate_count_after_behavioral_dedup": len(candidates),
        "capacity_candidate_count": len(capacity_candidates),
        "reserve_per_role": reserve_per_role, "max_candidates": max_candidates,
        "selected_candidate_identity_sha256s": selected_ids,
        "reservations": reservations,
        "selected_candidate_count": len(selected_ids),
        "solver": {
            "kind": "recursive_subset_enumeration_plus_z3", "version": z3.get_version_string(),
            "cardinality_checks": cardinality_checks,
            "candidate_tiebreak": "lexicographically_first_satisfiable_identity_set",
            "maximality_check": "every_larger_bounded_candidate_subset_unsat",
        },
        "selection_inputs": (
            "typed child-law identity, untouched Item 2.01 metadata, accounting coverage, "
            "and family-wide issuer separation"
        ),
        "outcomes_read_for_selection": False,
        "capital_authority": False,
    }
    return {**body, "trial_design_sha256": stable_sha256(body)}


def _freeze_trial(
    root: Path, law_search: Mapping[str, Any], panel: Mapping[str, Any],
    candidates: list[dict[str, Any]], *, schema: str,
    predecessor: Mapping[str, Any] | None = None,
    design: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    opened_at = _utc_now()
    contract = _evaluation_contract()
    source_evidence = sorted({
        str(row["classification_evidence_sha256"])
        for row in panel.get("history_status") or ()
    })
    identity = {
        "opened_at": opened_at,
        "source_law_search_sha256": law_search["law_search_sha256"],
        "source_panel_readiness_sha256": law_search["panel_readiness_sha256"],
        "candidate_identity_sha256s": [row["candidate_identity_sha256"] for row in candidates],
        "source_classification_set_sha256": panel["classification_set_sha256"],
        "evaluation_contract_sha256": contract["contract_sha256"],
        "predecessor_trial_sha256": (predecessor or {}).get("trial_sha256"),
        "trial_design_sha256": (design or {}).get("trial_design_sha256"),
    }
    body = {
        "schema": schema, "trial_id": f"strategy-law-{stable_sha256(identity)[:20]}",
        **identity, "candidates": candidates,
        "evaluation_contract": contract,
        "trial_design": dict(design or {}),
        "source_classification_evidence_sha256s": source_evidence,
        "evidence_design": (
            "sealed_sparse_smt_reserved_historical_holdout"
            if design else "sealed_analyst_time_historical_holdout"
        ),
        "settlement_rule": (
            "Score only treated and future-adopter entities absent from frozen training "
            "membership after a different classification-set panel is admitted; a sparse "
            "trial additionally requires the issuer to belong to its frozen reservation."
        ),
        "minimum_support": {"treated_entities": 4, "future_adopter_entities": 4},
        "status": "collecting_newly_typed_entities", "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    trial = {**body, "trial_sha256": stable_sha256(body)}
    _atomic_json(root / _ROOT / trial["trial_id"] / "trial.json", trial)
    _atomic_json(root / _ROOT / "current.json", trial)
    return trial


def freeze_bulk_strategy_law_trial(workspace: str | Path) -> dict[str, Any]:
    """Freeze the child frontier before more SEC documents are typed."""
    root = Path(workspace).expanduser().resolve()
    law_search = _checked(
        root / "institutional_learning/historical_strategy_bulk_outcomes/law-search.json",
        "law_search_sha256",
    )
    panel = _checked(
        root / "institutional_learning/historical_strategy_bulk_outcomes/panel-readiness.json",
        "readiness_sha256",
    )
    if law_search["panel_readiness_sha256"] != panel["readiness_sha256"]:
        raise ValueError("strategy law frontier and panel belong to different publication epochs")
    return _freeze_trial(
        root, law_search, panel,
        [_trial_candidate(row) for row in law_search["frozen_child_candidates"]],
        schema=SCHEMA,
    )


def freeze_sparse_bulk_strategy_law_trial(
    workspace: str | Path, predecessor: Mapping[str, Any],
) -> dict[str, Any]:
    """Replace an exhausted broad family with a maximal disjoint sparse trial."""
    root = Path(workspace).expanduser().resolve()
    law_search = _checked(
        root / "institutional_learning/historical_strategy_bulk_outcomes/law-search.json",
        "law_search_sha256",
    )
    panel = _checked(
        root / "institutional_learning/historical_strategy_bulk_outcomes/panel-readiness.json",
        "readiness_sha256",
    )
    if law_search["panel_readiness_sha256"] != panel["readiness_sha256"]:
        raise ValueError("sparse strategy law design requires one publication epoch")
    design = compile_sparse_strategy_law_trial_design(root, law_search=law_search)
    selected = set(design["selected_candidate_identity_sha256s"])
    candidates = []
    for row in law_search["frozen_child_candidates"]:
        candidate = _trial_candidate(row)
        candidate_sha = candidate["candidate_identity_sha256"]
        if candidate_sha not in selected:
            continue
        reservation = design["reservations"][candidate_sha]
        candidates.append({
            **candidate,
            "reserved_treated_entity_ids": reservation["treated"],
            "reserved_future_adopter_entity_ids": reservation["future_adopter"],
        })
    if {row["candidate_identity_sha256"] for row in candidates} != selected:
        raise ValueError("sparse strategy law design lost a selected candidate")
    return _freeze_trial(
        root, law_search, panel, candidates, schema=SPARSE_SCHEMA,
        predecessor=predecessor, design=design,
    )


def _matching_cell(histories, candidate):
    identity = candidate["candidate_identity"]
    fields = tuple(identity["moderator_fields"])
    first = _first_adoptions(histories, fields)
    cells = _parent_cells(first, fields, identity["parent"])
    return next((row for row in cells if row["moderators"] == identity["moderators"]), None), first


def _evaluate_candidate(panel, candidate, trial, *, evaluated_at):
    cell, first = _matching_cell(list(panel["history_status"]), candidate)
    if cell is None:
        return {"status": "no_matching_successor_cell", "evaluations": []}
    frozen_membership = {
        *map(str, candidate["training_treated_entity_ids"]),
        *map(str, candidate["training_future_adopter_entity_ids"]),
    }
    source_evidence = set(trial["source_classification_evidence_sha256s"])
    eligible_first = {
        str(row["cik"]): row for row in first
        if str(row["cik"]) not in frozen_membership
        and row.get("classification_admitted_at")
        and row["classification_evidence_sha256"] not in source_evidence
        and row["classification_admitted_at"] > trial["opened_at"]
        and (row.get("acquisition_selection_receipt") or {}).get("selection_mode")
        == "sealed_law_trial_holdout"
        and ((row.get("acquisition_selection_receipt") or {}).get("selection_basis") or {}).get(
            "trial_sha256"
        ) == trial["trial_sha256"]
        and ((row.get("acquisition_selection_receipt") or {}).get("selection_basis") or {}).get(
            "candidate_identity_sha256"
        ) == candidate["candidate_identity_sha256"]
    }
    heldout_treated = sorted(
        set(map(str, cell["treated_entity_ids"])) & set(eligible_first)
    )
    heldout_controls = sorted(
        set(map(str, cell["future_adopter_entity_ids"])) & set(eligible_first)
    )
    reserved_treated = set(map(str, candidate.get("reserved_treated_entity_ids") or ()))
    reserved_controls = set(map(
        str, candidate.get("reserved_future_adopter_entity_ids") or (),
    ))
    if (
        (reserved_treated and not set(heldout_treated) <= reserved_treated)
        or (reserved_controls and not set(heldout_controls) <= reserved_controls)
    ):
        raise ValueError("sealed sparse law trial admitted an unreserved issuer")
    if frozen_membership & (set(heldout_treated) | set(heldout_controls)):
        raise ValueError("frozen training membership crossed into the sealed holdout")
    if set(heldout_treated) & set(heldout_controls):
        raise ValueError("sealed holdout entity has both treated and control roles")
    heldout_ids = set(heldout_treated) | set(heldout_controls)
    heldout_first = [eligible_first[cik] for cik in sorted(heldout_ids)]
    heldout_cells = _parent_cells(
        heldout_first, tuple(candidate["candidate_identity"]["moderator_fields"]),
        candidate["candidate_identity"]["parent"],
    )
    heldout_cell = next((
        row for row in heldout_cells
        if row["moderators"] == candidate["candidate_identity"]["moderators"]
    ), None)
    support = {
        "treated_entity_count": len(heldout_treated),
        "future_adopter_entity_count": len(heldout_controls),
        "treated_entity_ids": heldout_treated,
        "future_adopter_entity_ids": heldout_controls,
    }
    if heldout_cell is None or min(len(heldout_treated), len(heldout_controls)) < 4:
        return {"status": "collecting_sealed_holdout_support", "support": support, "evaluations": []}

    evaluations = []
    for outcome in _OUTCOMES:
        law = _law(heldout_cell, panel["readiness_sha256"], trial["opened_at"], outcome)
        evaluation = evaluate_difference_in_differences(
            law, _rows(law, heldout_cell, heldout_first, outcome, {}),
            generated_at=evaluated_at,
        )
        evaluations.append({"outcome": outcome, "evaluation": evaluation})
    signs = {
        1 if float(row["evaluation"].get("details", {}).get("aggregate_att") or 0) > 0 else -1
        for row in evaluations
    }
    return {"status": "sealed_holdout_scored", "support": support,
            "evaluations": evaluations, "direction_agreement": len(signs) == 1}


def advance_bulk_strategy_law_trial(workspace: str | Path) -> dict[str, Any]:
    """Open a trial or score its unchanged candidates on a later admitted panel."""
    root = Path(workspace).expanduser().resolve()
    current_path = root / _ROOT / "current.json"
    if not current_path.is_file():
        return freeze_bulk_strategy_law_trial(root)
    trial = _checked(current_path, "trial_sha256")
    if trial.get("schema") not in _SUPPORTED_SCHEMAS:
        return freeze_bulk_strategy_law_trial(root)
    queue_path = (
        root / "institutional_learning/historical_strategy_bulk_learning/latest.json"
    )
    queue = _checked(queue_path, "learning_queue_sha256") if queue_path.is_file() else {}
    support_exhausted = False
    if queue:
        frontier = queue.get("sealed_law_trial_support_frontier") or ()
        exhausted = sum(
            row.get("status") == "metadata_support_exhausted" for row in frontier
        )
        support_exhausted = bool(
            queue.get("sealed_law_trial_sha256") == trial["trial_sha256"]
            and len(frontier) == len(trial["candidates"])
            and exhausted == len(frontier)
            and not queue.get("sealed_law_trial_reachable_candidate_count")
        )
        if support_exhausted:
            law_search = _checked(
                root / "institutional_learning/historical_strategy_bulk_outcomes/law-search.json",
                "law_search_sha256",
            )
            latest_path = root / _ROOT / "latest.json"
            latest = _checked(latest_path, "epoch_sha256") if latest_path.is_file() else {}
            new_candidate_epoch = (
                trial.get("schema") == SCHEMA
                or law_search["law_search_sha256"] != trial.get("source_law_search_sha256")
            )
            design_already_checked = (
                latest.get("status") == "support_exhausted"
                and latest.get("next_trial_design_law_search_sha256")
                == law_search["law_search_sha256"]
            )
            if new_candidate_epoch and not design_already_checked:
                try:
                    return freeze_sparse_bulk_strategy_law_trial(root, trial)
                except ValueError as error:
                    if str(error) != "no recursively generated law has a viable sparse holdout":
                        raise
    if trial.get("evaluation_contract") != _evaluation_contract():
        raise ValueError("sealed strategy-law trial evaluation ABI changed")
    panel = _checked(
        root / "institutional_learning/historical_strategy_bulk_outcomes/panel-readiness.json",
        "readiness_sha256",
    )
    if support_exhausted:
        evaluated_at = _utc_now()
        results = [{
            "candidate_identity_sha256": candidate["candidate_identity_sha256"],
            **_evaluate_candidate(panel, candidate, trial, evaluated_at=evaluated_at),
        } for candidate in trial["candidates"]]
        law_search = _checked(
            root / "institutional_learning/historical_strategy_bulk_outcomes/law-search.json",
            "law_search_sha256",
        )
        body = {
            "schema": "jaggedthoughts-historical-strategy-law-trial-epoch-v1",
            "trial_id": trial["trial_id"], "trial_sha256": trial["trial_sha256"],
            "evaluated_at": evaluated_at,
            "source_panel_readiness_sha256": panel["readiness_sha256"],
            "support_queue_sha256": queue["learning_queue_sha256"],
            "next_trial_design_law_search_sha256": law_search["law_search_sha256"],
            "results": results,
            "multiplicity": {
                "method": "Benjamini-Hochberg", "alpha": 0.05,
                "trial_count": len(trial["candidates"]),
                "status": "conservative_interim",
                "unscored_hypothesis_p_value": 1.0,
                "rows": bh_fdr([
                    (row["candidate_identity_sha256"], 1.0) for row in results
                ], alpha=0.05),
            },
            "status": "support_exhausted",
            "interpretation": (
                "The frozen issuer reserve cannot reach minimum support. The trial stays "
                "unscored; a later trial requires a changed outcome-blind candidate epoch "
                "and a fresh disjoint Z3 reservation."
            ),
            "promotion_eligible": False, "paper_policy_authority": False,
            "capital_authority": False,
        }
        epoch = {**body, "epoch_sha256": stable_sha256(body)}
        exhaustion_path = (
            root / _ROOT / trial["trial_id"] / "epochs"
            / f"support-exhausted-{queue['learning_queue_sha256']}.json"
        )
        _atomic_json(exhaustion_path, epoch)
        _atomic_json(root / _ROOT / "latest.json", epoch)
        return epoch
    if panel["readiness_sha256"] == trial["source_panel_readiness_sha256"]:
        return trial
    epoch_path = (
        root / _ROOT / trial["trial_id"] / "epochs"
        / f"{panel['readiness_sha256']}.json"
    )
    if epoch_path.is_file():
        epoch = _checked(epoch_path, "epoch_sha256")
        if (
            epoch.get("trial_sha256") != trial["trial_sha256"]
            or epoch.get("source_panel_readiness_sha256") != panel["readiness_sha256"]
        ):
            raise ValueError("sealed strategy-law epoch identity mismatch")
        _atomic_json(root / _ROOT / "latest.json", epoch)
        return epoch
    if panel.get("classification_set_sha256") == trial["source_classification_set_sha256"]:
        raise ValueError("strategy-law holdout panel has no new classification epoch")
    evaluated_at = _utc_now()
    results = [{"candidate_identity_sha256": candidate["candidate_identity_sha256"],
                **_evaluate_candidate(panel, candidate, trial, evaluated_at=evaluated_at)}
               for candidate in trial["candidates"]]
    p_values = []
    for result in results:
        primary = next((row for row in result.get("evaluations") or ()
                        if row["outcome"]["role"] == "economic_primary"), None)
        p_value = ((primary or {}).get("evaluation") or {}).get("details", {}).get("two_sided_p_value")
        p_values.append((
            result["candidate_identity_sha256"],
            float(p_value) if p_value is not None else 1.0,
        ))
    all_scored = all(row["status"] == "sealed_holdout_scored" for row in results)
    body = {
        "schema": "jaggedthoughts-historical-strategy-law-trial-epoch-v1",
        "trial_id": trial["trial_id"], "trial_sha256": trial["trial_sha256"],
        "evaluated_at": evaluated_at,
        "source_panel_readiness_sha256": panel["readiness_sha256"], "results": results,
        "multiplicity": {"method": "Benjamini-Hochberg", "alpha": 0.05,
                         "trial_count": len(trial["candidates"]),
                         "status": "family_scored" if all_scored else "conservative_interim",
                         "unscored_hypothesis_p_value": 1.0,
                         "rows": bh_fdr(p_values, alpha=0.05)},
        "status": ("sealed_holdout_scored" if any(
            row["status"] == "sealed_holdout_scored" for row in results
        ) else "collecting_sealed_holdout_support"),
        "interpretation": (
            "Analyst-time sealed historical holdout: may kill or prioritize a mechanism, "
            "but is not a prospective market or business outcome."
        ),
        "promotion_eligible": False, "paper_policy_authority": False,
        "capital_authority": False,
    }
    epoch = {**body, "epoch_sha256": stable_sha256(body)}
    _atomic_json(epoch_path, epoch)
    _atomic_json(root / _ROOT / "latest.json", epoch)
    return epoch


__all__ = ["advance_bulk_strategy_law_trial", "freeze_bulk_strategy_law_trial"]
