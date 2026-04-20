from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.ztare.common.paths import PROJECTS_DIR, REPO_ROOT


BENCH_ROOT = REPO_ROOT / "benchmarks" / "constraint_memory"
RUNS_ROOT = BENCH_ROOT / "runs"
SPECIMEN_SEARCH_ROOT = BENCH_ROOT


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _latest_run_path() -> Path:
    runs = sorted([p for p in RUNS_ROOT.iterdir() if p.is_dir()], reverse=True)
    if not runs:
        raise SystemExit("No benchmark runs found.")
    return runs[0]


def _run_path(run_id: str | None) -> Path:
    if run_id:
        path = RUNS_ROOT / run_id
        if not path.exists():
            raise SystemExit(f"Run not found: {run_id}")
        return path
    return _latest_run_path()


def _index_specimens() -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for path in SPECIMEN_SEARCH_ROOT.rglob("specimen.json"):
        try:
            meta = _load_json(path)
        except Exception:
            continue
        specimen_id = meta.get("id")
        if specimen_id:
            indexed[specimen_id] = meta
    return indexed


def _collect_condition_eval(specimen_dir: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for condition_dir in sorted([p for p in specimen_dir.iterdir() if p.is_dir()]):
        eval_path = condition_dir / "eval_results.json"
        if eval_path.exists():
            result[condition_dir.name] = _load_json(eval_path)
    return result


def _extract_failure_signature(eval_data: dict[str, Any]) -> dict[str, Any]:
    score_contract = eval_data.get("score_contract", {})
    return {
        "score": eval_data.get("score"),
        "weakest_point": eval_data.get("weakest_point"),
        "debate_summary": eval_data.get("debate_summary"),
        "proof_is_self_referential": eval_data.get("proof_is_self_referential"),
        "proof_is_self_referential_model_raw": eval_data.get("proof_is_self_referential_model_raw"),
        "semantic_gate_status": eval_data.get("semantic_gate_status"),
        "self_reference_rule_fired": eval_data.get("self_reference_rule_fired"),
        "self_reference_evidence": eval_data.get("self_reference_evidence"),
        "semantic_gate_unresolved_diagnosis": eval_data.get("semantic_gate_unresolved_diagnosis"),
        "hard_fail_reasons": score_contract.get("hard_fail_reasons", []),
        "soft_score_caps": score_contract.get("soft_score_caps", []),
    }


def _classify_condition_delta(
    specimen: str, b_sig: dict[str, Any] | None, c_sig: dict[str, Any] | None, pass_threshold: int
) -> dict[str, Any]:
    if not b_sig or not c_sig:
        return {
            "specimen": specimen,
            "classification": "insufficient_data",
            "explanation": "Missing B or C evaluation data.",
        }

    b_pass = (b_sig.get("score") or 0) >= pass_threshold
    c_pass = (c_sig.get("score") or 0) >= pass_threshold
    b_hard = b_sig.get("hard_fail_reasons") or []
    c_hard = c_sig.get("hard_fail_reasons") or []

    if b_pass and not c_pass and c_hard:
        return {
            "specimen": specimen,
            "classification": "c_stack_hard_fail_regression",
            "explanation": "B passes but C fails via hard-fail reasons. The regression is in the C stack interaction, not the semantic safe-harbor downgrade itself.",
            "b_signature": b_sig,
            "c_signature": c_sig,
        }

    if specimen == "t2_ai_inference":
        if (
            b_sig.get("self_reference_rule_fired") == "hard_self_reference"
            and c_sig.get("self_reference_rule_fired") == "hard_self_reference"
            and not b_hard
            and not c_hard
            and (b_sig.get("score") == 25 and c_sig.get("score") == 25)
        ):
            return {
                "specimen": specimen,
                "classification": "target_detection_soft_cap_only",
                "explanation": "Target case is only soft-capped under both B and C. Detection is present, but the current contract no longer converts this target class into a hard kill.",
                "b_signature": b_sig,
                "c_signature": c_sig,
            }

    if not b_pass and not c_pass:
        return {
            "specimen": specimen,
            "classification": "shared_failure",
            "explanation": "Both B and C fail this specimen; the issue is not isolated to the C stack.",
            "b_signature": b_sig,
            "c_signature": c_sig,
        }

    if b_pass and c_pass:
        return {
            "specimen": specimen,
            "classification": "stable_across_conditions",
            "explanation": "Both B and C behave acceptably on this specimen.",
            "b_signature": b_sig,
            "c_signature": c_sig,
        }

    return {
        "specimen": specimen,
        "classification": "mixed_condition_behavior",
        "explanation": "Condition behavior differs, but no stronger classification rule matched.",
        "b_signature": b_sig,
        "c_signature": c_sig,
    }


def _candidate_negative_constraints(
    target_case: dict[str, Any], failed_good_controls: list[dict[str, Any]]
) -> list[str]:
    constraints: list[str] = []

    def is_local_safe_harbor_candidate(item: dict[str, Any]) -> bool:
        description = (item.get("description") or "").lower()
        weakest = (item["signature"].get("weakest_point") or "").lower()
        summary = (item["signature"].get("debate_summary") or "").lower()
        local_component = (
            "local component" in description
            or "deterministic local mapping" in summary
            or "safe harbor" in summary
        )
        whole_system_overclaim = any(
            phrase in (weakest + " " + summary)
            for phrase in [
                "cannot quietly pass through evaluation",
                "no token",
                "absence of any status token",
                "whole-system",
                "transport-layer",
                "upstream failure",
            ]
        )
        return local_component and not whole_system_overclaim

    shared_hard_self_reference = [
        item
        for item in failed_good_controls
        if item["signature"].get("self_reference_rule_fired") == "hard_self_reference"
    ]
    if target_case and target_case.get("signature", {}).get("self_reference_rule_fired") == "hard_self_reference" and shared_hard_self_reference:
        safe_harbor_items = [item for item in shared_hard_self_reference if is_local_safe_harbor_candidate(item)]
        if safe_harbor_items:
            constraints.append(
                "Do not fire `hard_self_reference` for bounded safe-harbor local mappings whose claim is only deterministic behavior over received opaque inputs and whose thesis explicitly disclaims upstream truthfulness or whole-system availability."
            )

    if any(
        "no status token" in (item["signature"].get("weakest_point") or "").lower()
        or "absence of any status token" in (item["signature"].get("debate_summary") or "").lower()
        for item in failed_good_controls
    ):
        constraints.append(
            "Do not falsify a local fail-closed token-mapping component for total upstream token non-delivery unless the thesis explicitly claims to solve transport-layer absence."
        )

    for item in failed_good_controls:
        signature = item["signature"]
        if (
            is_local_safe_harbor_candidate(item)
            and signature.get("semantic_gate_status") == "resolved"
            and signature.get("self_reference_rule_fired") == "hard_self_reference"
        ):
            constraints.append(
                "If a specimen is explicitly scoped as a local component and passes the safe-harbor conditions, downgrade self-reference from `resolved/hard_self_reference` to `unresolved` or `none` only when the thesis makes no whole-system availability claim."
            )
            break

    if not constraints:
        constraints.append(
            "No specific negative constraint inferred; inspect failed good-control signatures manually."
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for item in constraints:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


DEFAULT_RELEVANT_CONDITIONS = {
    "B_deterministic_gates",
    "C_gates_plus_primitives",
}


def build_report(
    run_path: Path, target_specimen: str, relevant_conditions: set[str] | None = None
) -> dict[str, Any]:
    specimen_index = _index_specimens()
    metrics = _load_json(run_path / "metrics_summary.json")
    target_case: dict[str, Any] | None = None
    failed_good_controls: list[dict[str, Any]] = []
    condition_comparisons: list[dict[str, Any]] = []
    relevant_conditions = relevant_conditions or DEFAULT_RELEVANT_CONDITIONS

    for specimen_dir in sorted([p for p in run_path.iterdir() if p.is_dir()]):
        specimen_id = specimen_dir.name
        meta = specimen_index.get(specimen_id, {"id": specimen_id, "label": "unknown"})
        condition_evals = {
            name: eval_data
            for name, eval_data in _collect_condition_eval(specimen_dir).items()
            if name in relevant_conditions
        }
        pass_threshold = meta.get("pass_threshold", 60)

        if specimen_id == target_specimen:
            target_case = {
                "specimen": specimen_id,
                "description": meta.get("description"),
                "conditions": {
                    name: _extract_failure_signature(eval_data)
                    for name, eval_data in condition_evals.items()
                },
            }

        if condition_evals:
            b_sig = (
                _extract_failure_signature(condition_evals["B_deterministic_gates"])
                if "B_deterministic_gates" in condition_evals
                else None
            )
            c_sig = (
                _extract_failure_signature(condition_evals["C_gates_plus_primitives"])
                if "C_gates_plus_primitives" in condition_evals
                else None
            )
            if b_sig or c_sig:
                condition_comparisons.append(
                    _classify_condition_delta(specimen_id, b_sig, c_sig, pass_threshold)
                )

        if meta.get("label") != "good":
            continue

        for condition_name, eval_data in condition_evals.items():
            score = eval_data.get("score", 0)
            if score < pass_threshold:
                failed_good_controls.append(
                    {
                        "specimen": specimen_id,
                        "description": meta.get("description"),
                        "condition": condition_name,
                        "pass_threshold": pass_threshold,
                        "signature": _extract_failure_signature(eval_data),
                    }
                )

    report = {
        "run_id": run_path.name,
        "metrics_summary": metrics,
        "target_case": target_case,
        "failed_good_controls": failed_good_controls,
        "condition_comparisons": condition_comparisons,
        "candidate_negative_constraints": _candidate_negative_constraints(
            target_case or {}, failed_good_controls
        ),
        "summary": {
            "num_failed_good_controls": len(failed_good_controls),
            "target_case_assessed": target_case is not None,
            "stage1_status": (
                "target_case_improved_but_good_controls_regressed"
                if target_case and failed_good_controls
                else "insufficient_signal"
            ),
        },
    }
    return report


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a forensic report for a constraint_memory benchmark run."
    )
    parser.add_argument("--project", default="epistemic_engine_v4")
    parser.add_argument("--run-id", default=None, help="Benchmark run id. Defaults to latest.")
    parser.add_argument("--target-specimen", default="t2_ai_inference")
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=sorted(DEFAULT_RELEVANT_CONDITIONS),
        help="Relevant benchmark conditions to inspect. Defaults to deterministic stage-1 conditions only.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path. Defaults to projects/<project>/forensic_report.json",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_path = _run_path(args.run_id)
    report = build_report(run_path, args.target_specimen, set(args.conditions))

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = PROJECTS_DIR / args.project / "forensic_report.json"
    write_report(report, output_path)

    print(f"Run: {run_path.name}")
    print(f"Output: {output_path}")
    print(f"Target assessed: {report['summary']['target_case_assessed']}")
    print(f"Failed good controls: {report['summary']['num_failed_good_controls']}")
    for idx, item in enumerate(report["candidate_negative_constraints"], start=1):
        print(f"{idx}. {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
