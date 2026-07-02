#!/usr/bin/env python3
"""Replay compression-progress advice over existing project artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from ztare.validator.core.compression_progress import (  # noqa: E402
    CompressionObservation,
    evaluate_compression_progress,
    observations_from_rows,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Project slug under projects/.")
    parser.add_argument(
        "--scan-projects",
        action="store_true",
        help="Compare prefix-by-prefix compression advice against historical loop decisions.",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "telemetry", "fit-results", "framer"),
        default="auto",
        help="Replay source. auto prefers telemetry with compression fields, then fit results, then framer reports.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. Text output is not implemented yet.")
    args = parser.parse_args(argv)

    if args.scan_projects:
        payload = scan_projects()
    elif args.project:
        payload = replay_project(args.project, source=args.source)
    else:
        parser.error("--project is required unless --scan-projects is set")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


def replay_project(project: str, *, source: str = "auto") -> dict[str, Any]:
    project_dir = REPO / "projects" / project
    workspace = project_dir / "workspace"
    if not project_dir.exists():
        return {"ok": False, "error": f"project not found: projects/{project}", "project": project}

    candidates: list[tuple[str, list[CompressionObservation], list[str]]] = []
    if source in {"auto", "telemetry"}:
        observations, refs = observations_from_telemetry(workspace / "iteration_telemetry.jsonl")
        candidates.append(("telemetry", observations, refs))
    if source in {"auto", "fit-results"}:
        observations, refs = observations_from_fit_results(workspace)
        candidates.append(("fit-results", observations, refs))
    if source in {"auto", "framer"}:
        observations, refs = observations_from_framer(workspace)
        candidates.append(("framer", observations, refs))

    selected_source = ""
    selected_observations: list[CompressionObservation] = []
    selected_refs: list[str] = []
    for candidate_source, observations, refs in candidates:
        decision = evaluate_compression_progress(observations)
        if decision.usable_observations >= 2:
            selected_source = candidate_source
            selected_observations = observations
            selected_refs = refs
            break
    if not selected_source and candidates:
        selected_source, selected_observations, selected_refs = max(
            candidates,
            key=lambda item: evaluate_compression_progress(item[1]).usable_observations,
        )

    decision = evaluate_compression_progress(selected_observations)
    return {
        "ok": True,
        "schema": "ztare-compression-progress-replay-v1",
        "project": project,
        "source": selected_source or source,
        "source_refs": selected_refs[:20],
        "observation_count": len(selected_observations),
        "usable_observations": decision.usable_observations,
        "decision": decision.__dict__,
        "observations": [
            {
                "iteration_index": item.iteration_index,
                "complexity": item.complexity,
                "family": item.family,
                "novelty": item.novelty,
                "label": item.label,
            }
            for item in selected_observations[:100]
        ],
    }


def observations_from_telemetry(path: Path) -> tuple[list[CompressionObservation], list[str]]:
    rows = read_jsonl(path)
    return observations_from_rows(rows), [repo_rel(path)] if path.exists() else []


def observations_from_fit_results(workspace: Path) -> tuple[list[CompressionObservation], list[str]]:
    observations: list[CompressionObservation] = []
    refs: list[str] = []
    for path in sorted(workspace.glob("fit_result_iter_*.json"), key=fit_result_sort_key):
        payload = read_json(path)
        bic = fit_bic_proxy(payload)
        if bic is None:
            continue
        observations.append(
            CompressionObservation(
                iteration_index=fit_result_iteration(path),
                complexity=bic,
                family="fit_bic",
                novelty=False,
                label=path.name,
            )
        )
        refs.append(repo_rel(path))
    return observations, refs


def scan_projects() -> dict[str, Any]:
    """Backtest compression-progress advice against existing project histories.

    This is deliberately diagnostic. It compares the compression-progress advice
    available after iteration ``i`` with the loop decision already recorded after
    the same iteration, then checks whether the next iteration improved score or
    BIC. It is not a causal claim because the historical run did not follow the
    counterfactual advice.
    """

    decisions: list[dict[str, Any]] = []
    workspaces: list[dict[str, Any]] = []
    for workspace in sorted((REPO / "projects").glob("**/workspace")):
        observations, refs = observations_from_fit_results(workspace)
        telemetry = iteration_telemetry_rows(workspace / "iteration_telemetry.jsonl")
        if len(observations) < 3 or not telemetry:
            continue
        project = repo_rel(workspace.parent)
        observations = [
            item
            for item in observations
            if item.iteration_index in telemetry
        ]
        if len(observations) < 3:
            continue
        final_decision = evaluate_compression_progress(observations)
        disagreements = 0
        for offset, current in enumerate(observations[:-1], start=1):
            prefix = observations[:offset]
            if len(prefix) < 2:
                continue
            next_observation = observations[offset]
            current_row = telemetry.get(current.iteration_index, {})
            next_row = telemetry.get(next_observation.iteration_index, {})
            compression = evaluate_compression_progress(prefix)
            old_action = str(current_row.get("pending_loop_action") or "missing")
            cp_intervention = compression.recommendation in {
                "measure_before_continuing",
                "narrow_or_pivot",
            }
            old_intervention = old_action in {
                "REFRESH_SPECIALISTS",
                "PIVOT_REQUIRED",
                "UNDERIDENTIFIED",
            }
            if cp_intervention != old_intervention:
                disagreements += 1
            best_score = max(
                safe_float(telemetry.get(item.iteration_index, {}).get("score"), default=0.0)
                for item in prefix
            )
            best_complexity = min(float(item.complexity) for item in prefix if item.complexity is not None)
            next_score = safe_float(next_row.get("score"), default=0.0)
            next_complexity = float(next_observation.complexity)
            decisions.append({
                "project": project,
                "iteration": current.iteration_index,
                "compression_recommendation": compression.recommendation,
                "compression_stagnation_length": compression.stagnation_length,
                "previous_loop_action": old_action,
                "compression_intervention": cp_intervention,
                "previous_intervention": old_intervention,
                "next_score_improved": bool(
                    next_row.get("score_improved") or next_row.get("champion_promoted")
                ),
                "next_score_beats_prefix_best": next_score > best_score,
                "next_compresses": next_complexity < best_complexity - 1e-9,
                "next_score": next_score,
                "next_complexity": next_complexity,
            })
        workspaces.append({
            "project": project,
            "usable_observations": len(observations),
            "source_refs": refs[:5],
            "final_recommendation": final_decision.recommendation,
            "final_stagnation_length": final_decision.stagnation_length,
            "compression_drop_count": final_decision.compression_drop_count,
            "best_complexity": final_decision.best_complexity,
            "latest_complexity": final_decision.latest_complexity,
            "prefix_disagreements": disagreements,
        })

    return {
        "ok": True,
        "schema": "ztare-compression-progress-backtest-v1",
        "workspace_count": len(workspaces),
        "prefix_decision_count": len(decisions),
        "recommendation_counts": count_by(decisions, "compression_recommendation"),
        "previous_action_counts": count_by(decisions, "previous_loop_action"),
        "intervention_overlap": count_by_pair(
            decisions,
            "compression_intervention",
            "previous_intervention",
        ),
        "outcome_rates": outcome_rates(decisions),
        "final_narrow_or_pivot_projects": [
            item
            for item in sorted(
                workspaces,
                key=lambda row: (
                    -(row.get("final_stagnation_length") or 0),
                    -int(row.get("usable_observations") or 0),
                    str(row.get("project") or ""),
                ),
            )
            if item.get("final_recommendation") == "narrow_or_pivot"
        ][:20],
        "disagreement_examples": {
            "compression_intervenes_previous_continues": [
                item
                for item in decisions
                if item["compression_intervention"] and not item["previous_intervention"]
            ][:20],
            "previous_intervenes_compression_continues": [
                item
                for item in decisions
                if not item["compression_intervention"] and item["previous_intervention"]
            ][:20],
        },
        "method_note": (
            "Backtest is observational: it compares advice against the next historical "
            "iteration, not against a rerun that followed the counterfactual advice."
        ),
    }


def observations_from_framer(workspace: Path) -> tuple[list[CompressionObservation], list[str]]:
    observations: list[CompressionObservation] = []
    refs: list[str] = []
    paths = sorted(workspace.glob("**/framing_report*.json"))
    for index, path in enumerate(paths):
        payload = read_json(path)
        gain = finite_float(payload.get("MDL_gain_bits"))
        if gain is None:
            continue
        observations.append(
            CompressionObservation(
                iteration_index=index,
                complexity=-gain,
                family="framer_mdl_gain_bits",
                novelty=False,
                label=path.name,
            )
        )
        refs.append(repo_rel(path))
    return observations, refs


def iteration_telemetry_rows(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if row.get("record_type") != "iteration":
            continue
        iteration_index = safe_int_or_none(row.get("iteration_index"))
        if iteration_index is not None:
            rows[iteration_index] = row
    return rows


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        candidate = float(value)
    elif isinstance(value, str):
        try:
            candidate = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if candidate != candidate or candidate in (float("inf"), float("-inf")):
        return None
    return candidate


def fit_bic_proxy(payload: dict[str, Any]) -> float | None:
    direct = finite_float(payload.get("bic"))
    if direct is not None:
        return direct
    rmse = finite_float(payload.get("rmse"))
    if rmse is None or rmse <= 0:
        return None
    residual_map = payload.get("residual_map")
    n_rows = safe_int_or_none(payload.get("n_fit_rows"))
    if n_rows is None and isinstance(residual_map, list):
        n_rows = len(residual_map)
    params = payload.get("parameter_names")
    k_params = safe_int_or_none(payload.get("k_params"))
    if k_params is None and isinstance(params, list):
        k_params = len(params)
    if n_rows is None or n_rows < 2 or k_params is None:
        return None
    return float(n_rows) * math.log(rmse * rmse) + float(k_params) * math.log(float(n_rows))


def safe_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def safe_float(value: Any, *, default: float) -> float:
    candidate = finite_float(value)
    return candidate if candidate is not None else default


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key))
        counts[value] = counts.get(value, 0) + 1
    return counts


def count_by_pair(rows: list[dict[str, Any]], left_key: str, right_key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = f"{bool(row.get(left_key))}/{bool(row.get(right_key))}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def outcome_rates(decisions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "compression_continue": [
            row for row in decisions if row.get("compression_recommendation") == "continue"
        ],
        "compression_watch": [
            row for row in decisions if row.get("compression_recommendation") == "watch"
        ],
        "compression_measure": [
            row
            for row in decisions
            if row.get("compression_recommendation") == "measure_before_continuing"
        ],
        "compression_narrow_or_pivot": [
            row
            for row in decisions
            if row.get("compression_recommendation") == "narrow_or_pivot"
        ],
        "previous_continue": [
            row for row in decisions if row.get("previous_loop_action") == "CONTINUE"
        ],
        "previous_intervention": [
            row
            for row in decisions
            if row.get("previous_loop_action")
            in {"REFRESH_SPECIALISTS", "PIVOT_REQUIRED", "UNDERIDENTIFIED"}
        ],
    }
    return {name: summarize_outcomes(rows) for name, rows in groups.items() if rows}


def summarize_outcomes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(key: str) -> float:
        return round(sum(bool(row.get(key)) for row in rows) / len(rows), 3)

    return {
        "n": len(rows),
        "next_score_improved_rate": rate("next_score_improved"),
        "next_score_beats_prefix_best_rate": rate("next_score_beats_prefix_best"),
        "next_compresses_rate": rate("next_compresses"),
    }


def fit_result_iteration(path: Path) -> int:
    match = re.search(r"_iter_(\d+)\.json$", path.name)
    return int(match.group(1)) if match else 0


def fit_result_sort_key(path: Path) -> tuple[int, str]:
    return (fit_result_iteration(path), path.name)


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
