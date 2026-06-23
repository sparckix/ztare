#!/usr/bin/env python3
"""Validate the frozen evaluator-hardening proof-point suite.

The check is deliberately model-free. It reads the frozen constraint-memory
benchmark artifacts and verifies the public claim boundary:
deterministic gates remove false accepts, gates plus primitives keep false
accepts at zero while restoring good controls, and the ordinary-review arm is
still an explicit future gap rather than a hidden claim.
"""
from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / "benchmarks/evaluator_hardening_frozen/suite.json"
ORDINARY_REVIEW_CONTRACT = REPO / "benchmarks/evaluator_hardening_frozen/ordinary_review_arm_contract.json"
ORDINARY_REVIEW_BLOCKER = REPO / "benchmarks/evaluator_hardening_frozen/D_ordinary_review_blocker.json"
ORDINARY_REVIEW_PROMPT_PACKET = REPO / "benchmarks/evaluator_hardening_frozen/ordinary_review_prompt_packet"
RUNNER = REPO / "benchmarks/constraint_memory/run_benchmark.py"


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"missing required artifact: {path.relative_to(REPO)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"evaluator hardening frozen check failed: {message}")


def _condition(payload: dict[str, Any], name: str) -> dict[str, Any]:
    conditions = payload.get("conditions", {})
    row = conditions.get(name)
    _require(isinstance(row, dict), f"missing condition {name}")
    return row


def _float(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    _require(isinstance(value, (int, float)), f"{key} is not numeric: {value!r}")
    return float(value)


def _source_specimen_ids(results: list[dict[str, Any]]) -> list[str]:
    ids = sorted({
        row.get("specimen_id")
        for row in results
        if isinstance(row, dict) and "error" not in row and isinstance(row.get("specimen_id"), str)
    })
    _require(ids, "source run must expose specimen ids")
    return ids


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _verify_ordinary_prompt_export(source_run: str, source_specimen_ids: list[str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ztare_ordinary_review_export_") as tmp:
        proc = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--suite",
                "main",
                "--conditions",
                "D_ordinary_review",
                "--match-source-run",
                source_run,
                "--ordinary-review-export-prompts",
                tmp,
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        _require(
            proc.returncode == 0,
            "ordinary-review prompt export failed:\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}",
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"ordinary-review prompt export did not emit JSON: {exc}") from exc
        _require(payload.get("ok") is True, "ordinary-review prompt export did not report ok")
        _require(payload.get("specimen_count") == len(source_specimen_ids), "ordinary-review prompt export count mismatch")

        manifest_path = Path(payload["manifest_path"])
        template_path = Path(payload["import_template_path"])
        readme_path = Path(payload["readme_path"])
        manifest = _read_json(manifest_path)
        template = _read_json(template_path)
        _require(readme_path.exists(), "ordinary-review prompt export missing README")
        readme_text = readme_path.read_text(encoding="utf-8")
        _require("benchmark-ordinary-review-validate-import" in readme_text, "ordinary-review export README missing preflight command")
        _require("benchmark-ordinary-review BENCH_ORDINARY_IMPORT" in readme_text, "ordinary-review export README missing freeze command")
        _require("benchmark-ordinary-review-freeze-check" in readme_text, "ordinary-review export README missing promotion check command")
        prompts = manifest.get("prompts")
        reviews = template.get("reviews")
        _require(isinstance(prompts, list), "ordinary-review prompt manifest missing prompts")
        _require(isinstance(reviews, list), "ordinary-review import template missing reviews")
        prompt_ids = sorted(row.get("specimen_id") for row in prompts)
        review_ids = sorted(row.get("specimen_id") for row in reviews)
        _require(prompt_ids == source_specimen_ids, "ordinary-review prompts do not match frozen source specimen ids")
        _require(review_ids == source_specimen_ids, "ordinary-review import template does not match frozen source specimen ids")
        _require(manifest.get("source_run") == source_run, "ordinary-review prompt manifest not bound to source run")
        omitted = set(manifest.get("answer_key_fields_omitted") or [])
        _require("label" in omitted, "ordinary-review manifest must declare label omission")
        _require("expected_exploit" in omitted, "ordinary-review manifest must declare expected-exploit omission")
        _require("detection_keywords" in omitted, "ordinary-review manifest must declare detection-keyword omission")

        hashes_by_id = {row["specimen_id"]: row["prompt_sha256"] for row in prompts}
        for row in reviews:
            _require(
                row.get("prompt_sha256") == hashes_by_id.get(row.get("specimen_id")),
                "ordinary-review import template prompt hash mismatch",
            )
        for row in prompts:
            prompt_path = manifest_path.parent / row["prompt_path"]
            prompt_text = prompt_path.read_text(encoding="utf-8")
            for forbidden in ("expected_exploit", "detection_keywords", "structural_expected_flags"):
                _require(forbidden not in prompt_text, f"ordinary-review prompt leaks answer-key field {forbidden}")

        synthetic_rows = []
        for row in reviews:
            filled = dict(row)
            filled["model"] = "synthetic-preflight-reviewer"
            filled["timestamp"] = "2026-06-19T00:00:00Z"
            filled["provider_runtime"] = "local/preflight-fixture"
            filled["review"] = {
                "accept_claim_as_stated": False,
                "score": 25,
                "fatal_flaw_identified": True,
                "flaw_summary": "synthetic preflight row; not benchmark evidence",
                "confidence": "low",
            }
            synthetic_rows.append(filled)
        import_path = manifest_path.parent / "ordinary_review_preflight_rows.json"
        import_path.write_text(json.dumps({"reviews": synthetic_rows}, indent=2) + "\n", encoding="utf-8")
        preflight = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--suite",
                "main",
                "--conditions",
                "D_ordinary_review",
                "--match-source-run",
                source_run,
                "--ordinary-review-import-results",
                str(import_path),
                "--ordinary-review-validate-import-only",
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
        _require(
            preflight.returncode == 0,
            "ordinary-review import preflight failed:\n"
            f"stdout:\n{preflight.stdout}\n"
            f"stderr:\n{preflight.stderr}",
        )
        try:
            preflight_payload = json.loads(preflight.stdout)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"ordinary-review import preflight did not emit JSON: {exc}") from exc
        _require(preflight_payload.get("ok") is True, "ordinary-review import preflight did not report ok")
        _require(
            preflight_payload.get("validated_row_count") == len(source_specimen_ids),
            "ordinary-review import preflight row count mismatch",
        )
        _require(
            sorted(preflight_payload.get("specimen_ids") or []) == source_specimen_ids,
            "ordinary-review import preflight specimen ids mismatch",
        )

        return {
            "source_run_bound": True,
            "specimen_count": len(source_specimen_ids),
            "specimen_ids": source_specimen_ids,
            "import_template_ready": True,
            "import_preflight_ready": True,
            "prompt_hashes": dict(sorted(hashes_by_id.items())),
            "answer_key_fields_omitted": sorted(omitted),
        }


def _verify_checked_in_ordinary_prompt_packet(
    source_run: str,
    source_specimen_ids: list[str],
    expected_prompt_hashes: dict[str, str],
) -> dict[str, Any]:
    manifest_path = ORDINARY_REVIEW_PROMPT_PACKET / "ordinary_review_prompt_manifest.json"
    template_path = ORDINARY_REVIEW_PROMPT_PACKET / "ordinary_review_import_template.json"
    readme_path = ORDINARY_REVIEW_PROMPT_PACKET / "README.md"
    manifest = _read_json(manifest_path)
    template = _read_json(template_path)
    _require(readme_path.exists(), "checked-in ordinary-review packet missing README")
    readme_text = readme_path.read_text(encoding="utf-8")
    _require("benchmark-ordinary-review-validate-import" in readme_text, "checked-in ordinary-review README missing preflight command")
    _require("benchmark-ordinary-review BENCH_ORDINARY_IMPORT" in readme_text, "checked-in ordinary-review README missing freeze command")
    _require("benchmark-ordinary-review-freeze-check" in readme_text, "checked-in ordinary-review README missing promotion check command")
    _require(source_run in readme_text, "checked-in ordinary-review README missing source-run binding")
    prompts = manifest.get("prompts")
    reviews = template.get("reviews")
    _require(isinstance(prompts, list), "checked-in ordinary-review manifest missing prompts")
    _require(isinstance(reviews, list), "checked-in ordinary-review template missing reviews")
    _require(manifest.get("source_run") == source_run, "checked-in ordinary-review packet not bound to source run")

    prompt_ids = sorted(row.get("specimen_id") for row in prompts)
    review_ids = sorted(row.get("specimen_id") for row in reviews)
    _require(prompt_ids == source_specimen_ids, "checked-in ordinary-review prompts do not match frozen source ids")
    _require(review_ids == source_specimen_ids, "checked-in ordinary-review template does not match frozen source ids")

    observed_hashes = {}
    for row in prompts:
        specimen_id = row.get("specimen_id")
        prompt_rel = row.get("prompt_path")
        prompt_hash = row.get("prompt_sha256")
        _require(isinstance(specimen_id, str), "checked-in ordinary-review prompt missing specimen_id")
        _require(isinstance(prompt_rel, str), f"checked-in ordinary-review prompt missing path: {specimen_id}")
        _require(isinstance(prompt_hash, str), f"checked-in ordinary-review prompt missing hash: {specimen_id}")
        _require(
            prompt_hash == expected_prompt_hashes.get(specimen_id),
            f"checked-in ordinary-review prompt hash not runner-generated: {specimen_id}",
        )
        prompt_path = ORDINARY_REVIEW_PROMPT_PACKET / prompt_rel
        prompt_text = prompt_path.read_text(encoding="utf-8")
        _require(
            _sha256_text(prompt_text) == prompt_hash,
            f"checked-in ordinary-review prompt file hash mismatch: {specimen_id}",
        )
        for forbidden in ("expected_exploit", "detection_keywords", "structural_expected_flags"):
            _require(forbidden not in prompt_text, f"checked-in ordinary-review prompt leaks {forbidden}")
        observed_hashes[specimen_id] = prompt_hash

    synthetic_rows = []
    for row in reviews:
        specimen_id = row.get("specimen_id")
        filled = dict(row)
        _require(
            filled.get("prompt_sha256") == observed_hashes.get(specimen_id),
            f"checked-in ordinary-review template hash mismatch: {specimen_id}",
        )
        filled["model"] = "synthetic-preflight-reviewer"
        filled["timestamp"] = "2026-06-19T00:00:00Z"
        filled["provider_runtime"] = "local/preflight-fixture"
        filled["review"] = {
            "accept_claim_as_stated": False,
            "score": 25,
            "fatal_flaw_identified": True,
            "flaw_summary": "synthetic preflight row; not benchmark evidence",
            "confidence": "low",
        }
        synthetic_rows.append(filled)

    with tempfile.TemporaryDirectory(prefix="ztare_checked_in_ordinary_review_") as tmp:
        import_path = Path(tmp) / "ordinary_review_preflight_rows.json"
        import_path.write_text(json.dumps({"reviews": synthetic_rows}, indent=2) + "\n", encoding="utf-8")
        preflight = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--suite",
                "main",
                "--conditions",
                "D_ordinary_review",
                "--match-source-run",
                source_run,
                "--ordinary-review-import-results",
                str(import_path),
                "--ordinary-review-validate-import-only",
            ],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
    _require(
        preflight.returncode == 0,
        "checked-in ordinary-review packet import preflight failed:\n"
        f"stdout:\n{preflight.stdout}\n"
        f"stderr:\n{preflight.stderr}",
    )

    return {
        "path": str(ORDINARY_REVIEW_PROMPT_PACKET.relative_to(REPO)),
        "source_run_bound": True,
        "specimen_count": len(source_specimen_ids),
        "specimen_ids": source_specimen_ids,
        "prompt_hashes_match_runner_export": True,
        "import_preflight_ready": True,
        "answer_key_fields_omitted": sorted(manifest.get("answer_key_fields_omitted") or []),
    }


def build_payload() -> dict[str, Any]:
    suite = _read_json(SUITE)
    source_run = REPO / suite["source_run"]
    summary_path = source_run / "metrics_summary.json"
    results_path = source_run / "results.json"
    summary = _read_json(summary_path)
    results = _read_json(results_path)
    source_specimen_ids = _source_specimen_ids(results)

    artifact_arms = [arm["id"] for arm in suite["artifact_backed_arms"]]
    future_arm_rows = suite["required_future_arms"]
    future_arms = [arm["id"] for arm in future_arm_rows]
    _require(artifact_arms == [
        "A_baseline_soft_judge",
        "B_deterministic_gates",
        "C_gates_plus_primitives",
    ], "unexpected artifact-backed arm order")
    _require(future_arms == ["D_ordinary_review"], "ordinary-review gap not explicit")
    future_arm = future_arm_rows[0]
    _require(
        future_arm.get("artifact_status") == "blocked_not_run",
        "ordinary-review arm must stay blocked until frozen artifacts exist",
    )
    _require(
        REPO / future_arm.get("contract", "") == ORDINARY_REVIEW_CONTRACT,
        "ordinary-review contract path mismatch",
    )
    _require(
        REPO / future_arm.get("blocker", "") == ORDINARY_REVIEW_BLOCKER,
        "ordinary-review blocker path mismatch",
    )
    ordinary_contract = _read_json(ORDINARY_REVIEW_CONTRACT)
    ordinary_blocker = _read_json(ORDINARY_REVIEW_BLOCKER)
    _require(ordinary_contract.get("status") == "specified_not_frozen", "ordinary-review contract status mismatch")
    required_import_provenance = ordinary_contract.get("required_import_provenance")
    _require(isinstance(required_import_provenance, dict), "ordinary-review contract must declare import provenance")
    for key in ("model", "timestamp", "prompt", "provider_runtime"):
        _require(key in required_import_provenance, f"ordinary-review import provenance missing {key}")
    _require(
        "runner-generated prompt hash" in ordinary_contract.get("prompt_binding_rule", ""),
        "ordinary-review contract must require runner-generated prompt hash binding",
    )
    _require(
        "ordinary_review_freeze_manifest.json" in ordinary_contract.get("upgrade_rule", "")
        and "can_promote_to_frozen_suite=true" in ordinary_contract.get("upgrade_rule", ""),
        "ordinary-review contract must require a promotion-ready freeze manifest",
    )
    _require(
        "review timestamp" in ordinary_contract.get("upgrade_rule", ""),
        "ordinary-review contract must require review timestamp provenance",
    )
    _require(ordinary_blocker.get("status") == "blocked_not_run", "ordinary-review blocker status mismatch")
    _require(
        "A_baseline_soft_judge" in ordinary_blocker.get("why_a_is_not_d", ""),
        "ordinary-review blocker must explain why A is not D",
    )
    _require(
        "prompt" in ordinary_blocker.get("blocker", "").lower()
        and "export" in ordinary_blocker.get("blocker", "").lower(),
        "ordinary-review blocker must surface reviewer-safe prompt export",
    )
    missing_dependencies = "\n".join(ordinary_blocker.get("missing_dependencies") or [])
    _require(
        "ordinary_review_freeze_manifest.json" in missing_dependencies
        and "can_promote_to_frozen_suite=true" in missing_dependencies,
        "ordinary-review blocker must require a promotion-ready freeze manifest",
    )

    conditions = {name: _condition(summary, name) for name in artifact_arms}
    a = conditions["A_baseline_soft_judge"]
    b = conditions["B_deterministic_gates"]
    c = conditions["C_gates_plus_primitives"]

    checks = suite["checks"]
    baseline_fa = _float(a, "false_accept_rate")
    b_fa = _float(b, "false_accept_rate")
    c_fa = _float(c, "false_accept_rate")
    c_fr = _float(c, "false_reject_rate")
    baseline_detect = _float(a, "exploit_detection_rate")
    b_detect = _float(b, "exploit_detection_rate")
    c_detect = _float(c, "exploit_detection_rate")

    _require(
        baseline_fa > float(checks["baseline_false_accept_rate_gt"]),
        "baseline must have nonzero false accepts",
    )
    _require(
        b_fa == float(checks["deterministic_false_accept_rate_eq"]),
        "deterministic gates must reduce false accepts to zero",
    )
    _require(
        c_fa == float(checks["gates_plus_primitives_false_accept_rate_eq"]),
        "gates plus primitives must keep false accepts at zero",
    )
    _require(
        c_fr == float(checks["gates_plus_primitives_false_reject_rate_eq"]),
        "gates plus primitives must restore good controls",
    )
    _require(
        b_detect >= baseline_detect and c_detect >= baseline_detect,
        "hardened detection rates must match or beat baseline",
    )

    result_conditions = {
        row.get("condition")
        for row in results
        if isinstance(row, dict) and "error" not in row
    }
    missing_result_arms = sorted(set(artifact_arms).difference(result_conditions))
    _require(not missing_result_arms, f"results missing arms: {missing_result_arms}")

    error_rows = [row for row in results if isinstance(row, dict) and "error" in row]
    _require(not error_rows, f"frozen run contains error rows: {len(error_rows)}")
    ordinary_prompt_export = _verify_ordinary_prompt_export(suite["source_run"], source_specimen_ids)
    checked_in_ordinary_prompt_packet = _verify_checked_in_ordinary_prompt_packet(
        suite["source_run"],
        source_specimen_ids,
        ordinary_prompt_export["prompt_hashes"],
    )

    return {
        "ok": True,
        "suite_id": suite["suite_id"],
        "source_run": suite["source_run"],
        "artifact_backed_arms": len(artifact_arms),
        "required_future_arms": future_arms,
        "complete_four_arm_suite": False,
        "ordinary_review_status": ordinary_blocker["status"],
        "ordinary_review_prompt_export_ready": True,
        "ordinary_review_prompt_export": ordinary_prompt_export,
        "ordinary_review_prompt_packet_ready": True,
        "ordinary_review_prompt_packet": checked_in_ordinary_prompt_packet,
        "claim_supported": suite["claim"],
        "metrics": {
            "A_baseline_soft_judge": a,
            "B_deterministic_gates": b,
            "C_gates_plus_primitives": c,
        },
        "deltas": {
            "false_accept_reduction_A_to_B": baseline_fa - b_fa,
            "false_accept_reduction_A_to_C": baseline_fa - c_fa,
            "false_reject_reduction_B_to_C": _float(b, "false_reject_rate") - c_fr,
            "exploit_detection_lift_A_to_B": b_detect - baseline_detect,
            "exploit_detection_lift_A_to_C": c_detect - baseline_detect,
        },
        "non_claims": suite["non_claims"],
        "next_falsifier": suite["next_falsifier"],
        "artifacts": {
            "suite": str(SUITE.relative_to(REPO)),
            "ordinary_review_contract": str(ORDINARY_REVIEW_CONTRACT.relative_to(REPO)),
            "ordinary_review_blocker": str(ORDINARY_REVIEW_BLOCKER.relative_to(REPO)),
            "summary": str(summary_path.relative_to(REPO)),
            "results": str(results_path.relative_to(REPO)),
        },
    }


def main() -> int:
    print(json.dumps(build_payload(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
