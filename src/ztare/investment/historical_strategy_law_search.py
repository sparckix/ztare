"""Outcome-blind recursive refinement of challenged strategy-law diagnostics."""

from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.strategy import (
    CandidateEvaluation, FrontierScope, Neighborhood, RepresentationAudit,
    compile_enumeration_result, compile_jaggedthoughts_frontier,
)

from .historical_strategy_bulk_outcomes import (
    compile_strategy_group_time_support, strategy_history_ready_at,
)
from .historical_strategy_control_design import (
    enumerate_historical_strategy_moderator_programs,
)


HISTORICAL_STRATEGY_LAW_SEARCH_SCHEMA = "jaggedthoughts-historical-strategy-law-search-v1"
HISTORICAL_STRATEGY_REFINEMENT_DIMENSIONS = (
    "transaction_form", "operating_object_scope", "issuer_role",
)
_ROOT = Path("institutional_learning/historical_strategy_bulk_outcomes")


def _checked(path: Path, digest_field: str) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    body = dict(row)
    declared = str(body.pop(digest_field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{path.name} content hash mismatch")
    return row


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _first_adoptions(
    histories: list[dict[str, Any]], fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    first: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in histories:
        key = (
            str(row["cik"]), str(row["implementation_mode"]),
            *(str(row[field]) for field in fields),
        )
        if key not in first or (row["occurred_at"], row["accession_number"]) < (
            first[key]["occurred_at"], first[key]["accession_number"],
        ):
            first[key] = row
    return list(first.values())


def _parent_cells(
    first: list[dict[str, Any]], fields: tuple[str, ...], parent: Mapping[str, Any],
) -> list[dict[str, Any]]:
    sic2 = str(parent["sic2"])
    mode = str(parent["implementation_mode"])
    year = int(parent["adoption_year"])
    population = [
        row for row in first
        if str(row["sic2"]) == sic2 and str(row["implementation_mode"]) == mode
    ]
    phenotypes = sorted({tuple(str(row[field]) for field in fields) for row in population})
    cells = []
    for values in phenotypes:
        members = [
            row for row in population
            if tuple(str(row[field]) for field in fields) == values
        ]
        treated = [row for row in members if int(row["event_year"]) == year]
        future = [row for row in members if int(row["event_year"]) > year]
        ready_treated = [row for row in treated if strategy_history_ready_at(row, year)]
        ready_future = [row for row in future if strategy_history_ready_at(row, year)]
        design = compile_strategy_group_time_support(ready_treated, ready_future, year)
        treated_ids = sorted({str(row["cik"]) for row in ready_treated})
        control_ids = sorted({str(row["cik"]) for row in ready_future})
        structural = len(treated_ids) >= 4 and len(control_ids) >= 4
        joint_treated_gap = max(0, 4 - min(
            int(design["pre_treated_count"]), int(design["post_treated_count"]),
        ))
        joint_control_gap = max(0, 4 - min(
            int(design["pre_control_count"]), int(design["post_control_count"]),
        ))
        body = {
            "parent": {"sic2": sic2, "implementation_mode": mode, "adoption_year": year},
            "moderators": dict(zip(fields, values)),
            "treated_entity_ids": treated_ids,
            "future_adopter_entity_ids": control_ids,
            "treated_event_sha256s": sorted(str(row["event_sha256"]) for row in ready_treated),
            "future_adopter_event_sha256s": sorted(
                str(row["event_sha256"]) for row in ready_future
            ),
            "history_ready_treated_count": len(treated_ids),
            "history_ready_future_adopter_count": len(control_ids),
            "treated_support_gap": max(0, 4 - len(treated_ids)),
            "future_adopter_support_gap": max(0, 4 - len(control_ids)),
            "joint_treated_support_gap": joint_treated_gap,
            "joint_future_adopter_support_gap": joint_control_gap,
            "structural_support_ready": structural,
            "joint_design": design,
            "group_time_ready": structural and bool(design["joint_support_ready"]),
        }
        cells.append(body)
    partition_count = len(cells)
    return [
        {
            **cell,
            "parent_partition_count": partition_count,
            "refines_parent_membership": partition_count > 1,
            "cell_sha256": stable_sha256({
                **cell,
                "parent_partition_count": partition_count,
                "refines_parent_membership": partition_count > 1,
            }),
        }
        for cell in cells
    ]


def _partition_entropy(cells: list[Mapping[str, Any]]) -> float:
    sizes = [
        len(set(cell["treated_entity_ids"]) | set(cell["future_adopter_entity_ids"]))
        for cell in cells
    ]
    total = sum(sizes)
    if total <= 1:
        return 0.0
    entropy = -sum((size / total) * math.log(size / total) for size in sizes if size)
    return entropy / math.log(total)


def _behavior_signature(cells: list[Mapping[str, Any]]) -> tuple[str, ...]:
    signature = []
    for cell in cells:
        signature.append(stable_sha256({
            "parent": cell["parent"],
            "treated_entity_ids": cell["treated_entity_ids"],
            "future_adopter_entity_ids": cell["future_adopter_entity_ids"],
        }))
    return tuple(sorted(signature)) or ("empty-projection",)


def compile_bulk_strategy_law_search(workspace: str | Path) -> dict[str, Any]:
    """Freeze the structural child-law frontier before inspecting child outcomes."""
    root = Path(workspace).expanduser().resolve()
    panel = _checked(root / _ROOT / "panel-readiness.json", "readiness_sha256")
    diagnostics = _checked(root / _ROOT / "effect-diagnostics.json", "diagnostics_sha256")
    if diagnostics.get("panel_readiness_sha256") != panel["readiness_sha256"]:
        raise ValueError("strategy parent diagnostics and panel belong to different epochs")
    robustness_path = root / _ROOT / "outcome-robustness.json"
    robustness = _checked(robustness_path, "robustness_sha256") \
        if robustness_path.is_file() else {}
    if robustness.get("panel_readiness_sha256") != panel["readiness_sha256"]:
        robustness = {}
    grammar, programs, fields_by_program = enumerate_historical_strategy_moderator_programs(
        HISTORICAL_STRATEGY_REFINEMENT_DIMENSIONS
    )
    enumeration = compile_enumeration_result(
        grammar, programs=programs,
        max_depth=len(HISTORICAL_STRATEGY_REFINEMENT_DIMENSIONS),
        max_programs=2 ** len(HISTORICAL_STRATEGY_REFINEMENT_DIMENSIONS),
    )
    parents = [
        {"cell": row["cell"], "diagnostic_status": row["evaluation"]["diagnostic_status"],
         "evaluation_sha256": row["evaluation"]["evaluation_sha256"]}
        for row in diagnostics.get("diagnostics") or ()
    ]
    projections, evaluations = [], []
    for program in programs:
        fields = fields_by_program[program.program_id]
        first = _first_adoptions(panel["history_status"], fields)
        cells = [
            cell for parent in parents
            for cell in _parent_cells(first, fields, parent["cell"])
        ]
        joint_treated = {
            entity for cell in cells if cell["group_time_ready"]
            for entity in cell["treated_entity_ids"]
        }
        joint_controls = {
            entity for cell in cells if cell["group_time_ready"]
            for entity in cell["future_adopter_entity_ids"]
        }
        total_treated = {
            entity for cell in cells for entity in cell["treated_entity_ids"]
        }
        total_controls = {
            entity for cell in cells for entity in cell["future_adopter_entity_ids"]
        }
        objectives = (
            len(joint_treated) / max(1, len(total_treated)),
            len(joint_controls) / max(1, len(total_controls)),
            _partition_entropy(cells),
        )
        evaluations.append(CandidateEvaluation(
            program_id=program.program_id, objective_values=objectives,
            behavior_signature=_behavior_signature(cells),
            evidence_refs=(panel["readiness_sha256"], diagnostics["diagnostics_sha256"]),
        ))
        projections.append({
            "program_id": program.program_id, "moderator_fields": list(fields),
            "partition_entropy": objectives[2], "cell_count": len(cells),
            "structural_support_ready_cell_count": sum(
                cell["structural_support_ready"] for cell in cells
            ),
            "group_time_ready_cell_count": sum(cell["group_time_ready"] for cell in cells),
            "cells": cells,
        })
    edges = []
    for left in programs:
        left_fields = set(fields_by_program[left.program_id])
        for right in programs:
            right_fields = set(fields_by_program[right.program_id])
            if left_fields < right_fields and len(right_fields) == len(left_fields) + 1:
                edges.append((left.program_id, right.program_id))
    neighborhood = Neighborhood("one-source-bound-phenotype-refinement", tuple(edges))
    scope = FrontierScope(
        grammar_id=grammar.grammar_id, grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type="historical_strategy_projection",
        max_depth=len(HISTORICAL_STRATEGY_REFINEMENT_DIMENSIONS),
        max_programs=2 ** len(HISTORICAL_STRATEGY_REFINEMENT_DIMENSIONS),
        evaluation_model_id="outcome-blind-identification-support-v1",
        landscape_mode="fixed", evidence_epoch=panel["classification_set_sha256"],
        objective_names=(
            "joint_treated_coverage", "joint_future_adopter_coverage",
            "phenotype_partition_resolution",
        ),
        neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope, enumeration=enumeration, evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=RepresentationAudit(
            "historical-strategy-child-law-representation", status="residual",
            residuals=tuple([
                "narrow_phenotype_support_incomplete",
                "event_time_environment_not_modeled",
                *([] if robustness else ["outcome_robustness_family_not_frozen"]),
            ]),
            evidence_refs=(panel["readiness_sha256"],),
        ),
    )
    frontier_ids = set(certificate.frontier_program_ids)
    equivalent_ids = {row.program_id for row in certificate.equivalent}
    rows = [
        {**row, "frontier_status": (
            "equivalent" if row["program_id"] in equivalent_ids else
            "frontier" if row["program_id"] in frontier_ids else "dominated"
        )}
        for row in projections
    ]
    frozen_children = [
        {"program_id": row["program_id"], "moderator_fields": row["moderator_fields"], **cell}
        for row in rows
        if row["frontier_status"] == "frontier" and row["moderator_fields"]
        for cell in row["cells"]
        if cell["group_time_ready"] and cell["refines_parent_membership"]
    ]
    acquisition_frontier = sorted((
        {"program_id": row["program_id"], "moderator_fields": row["moderator_fields"], **cell}
        for row in rows if row["frontier_status"] == "frontier" and row["moderator_fields"]
        for cell in row["cells"]
        if cell["refines_parent_membership"]
        and cell["history_ready_treated_count"] and cell["history_ready_future_adopter_count"]
        and not cell["group_time_ready"]
    ), key=lambda cell: (
        cell["joint_treated_support_gap"]
        + cell["joint_future_adopter_support_gap"],
        cell["treated_support_gap"] + cell["future_adopter_support_gap"],
        -cell["history_ready_treated_count"],
        -cell["history_ready_future_adopter_count"], cell["cell_sha256"],
    ))[:32]
    body = {
        "schema": HISTORICAL_STRATEGY_LAW_SEARCH_SCHEMA,
        "generated_at": panel["generated_at"],
        "panel_readiness_sha256": panel["readiness_sha256"],
        "parent_diagnostics_sha256": diagnostics["diagnostics_sha256"],
        "outcome_robustness_sha256": robustness.get("robustness_sha256"),
        "parent_diagnostics": parents,
        "grammar": grammar.to_dict(), "enumeration": enumeration.to_dict(),
        "projections": rows, "certificate": certificate.to_dict(),
        "frozen_child_candidate_count": len(frozen_children),
        "frozen_child_candidates": frozen_children,
        "acquisition_frontier_count": len(acquisition_frontier),
        "acquisition_frontier": acquisition_frontier,
        "selection_boundary": {
            "parent_result_use": "trigger_refinement_only",
            "child_outcomes_read": False,
            "structural_inputs": [
                "source_bound_transaction_phenotype", "issuer_identity",
                "first_adoption_timing", "point_in_time_accounting_period_availability",
            ],
            "frozen_before_child_estimation": True,
        },
        "status": (
            "child_candidates_frozen" if frozen_children
            else "narrow_children_blocked_on_identification_support"
        ),
        "next_activation": (
            "Estimate only the frozen child cells against a new evidence epoch."
            if frozen_children else
            "Acquire the nearest source-bound phenotype cells; do not mine the current outcomes for a winning subgroup."
        ),
        "causal_claim": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    result = {**body, "law_search_sha256": stable_sha256(body)}
    _atomic_json(root / _ROOT / "law-search.json", result)
    return result


__all__ = [
    "HISTORICAL_STRATEGY_LAW_SEARCH_SCHEMA",
    "HISTORICAL_STRATEGY_REFINEMENT_DIMENSIONS",
    "compile_bulk_strategy_law_search",
]
