"""Autoresearch adapter for the neutral prediction-contract interface."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ztare.forecasting.prediction_contract import (
    PredictionContractDefaults,
    PredictionIssue,
    is_resolved_prediction,
    is_sealed_prediction,
    read_prediction_rows,
    score_binary_prediction_contract,
    summarize_prediction_contract_rows,
    validate_prediction_contract,
)


PREDICTION_FILENAMES = (
    "iteration_predictions.jsonl",
    "prediction_contracts.jsonl",
)


def validate_prediction_row(row: dict[str, Any]) -> list[PredictionIssue]:
    """Back-compat wrapper for autoresearch-local tests and callers."""
    return validate_prediction_contract(row, defaults=_defaults("unknown"))


def score_prediction_row(row: dict[str, Any]) -> dict[str, Any] | None:
    """Back-compat wrapper over binary Brier scoring."""
    return score_binary_prediction_contract(row)


def summarize_prediction_contracts(
    *,
    project_dir: Path,
    workspace_dir: Path | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    """Summarize project-local in-loop prediction contracts for trace reports."""
    workspace = workspace_dir or project_dir / "workspace"
    path = _first_existing(workspace, project_dir)
    empty = _empty_summary()
    if path is None:
        return empty

    rows, parse_issues = read_prediction_rows(path)
    summary = summarize_prediction_contract_rows(
        rows,
        parse_issues=parse_issues,
        defaults=_defaults(project_dir.name),
    )
    return {
        "available": True,
        "source_artifact": _rel(path, repo),
        "measurement_policy": "score_only_no_routing",
        **summary,
    }


def _defaults(project: str) -> PredictionContractDefaults:
    return PredictionContractDefaults(
        subject=f"autoresearch:{project}",
        source_surface="autoresearch_workspace",
        provenance_mode="in_loop",
        producer="autoresearch_loop",
    )


def _empty_summary() -> dict[str, Any]:
    return {
        "available": False,
        "status": "no_prediction_contracts",
        "source_artifact": None,
        "measurement_policy": "score_only_no_routing",
        "row_count": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "sealed_count": 0,
        "unresolved_count": 0,
        "resolved_count": 0,
        "scoreable_count": 0,
        "mean_brier": None,
        "mean_uniform_brier": None,
        "beats_uniform_baseline": None,
        "source_surfaces": {},
        "provenance_modes": {},
        "producers": {},
        "certified_count": 0,
        "excluded_from_calibration_count": 0,
        "membrane_eligible_count": 0,
        "authority": {
            "score_authority": "not_scoreable_yet",
            "calibration_authority": "not_calibration_authority",
            "membrane_authority": "not_membrane_evidence",
            "routing_authority": "none_trace_does_not_route_work",
            "decision_use_required_for_routing": True,
        },
        "issues": [],
    }


def _first_existing(workspace: Path, project_dir: Path) -> Path | None:
    for parent in (workspace, project_dir):
        for name in PREDICTION_FILENAMES:
            path = parent / name
            if path.exists():
                return path
    return None


def _rel(path: Path, repo: Path | None) -> str:
    if repo is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)
