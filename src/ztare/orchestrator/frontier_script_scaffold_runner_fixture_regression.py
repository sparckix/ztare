from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ztare.orchestrator.frontier_script_scaffold_runner import (
    build_artifact_packet,
    run_frontier_script_meta_cold_shot,
)


@dataclass(frozen=True)
class _Usage:
    model_name: str = "fake-model"
    input_tokens: int = 10
    output_tokens: int = 20
    cache_read_input_tokens: int = 0
    thinking_tokens: int = 0
    direct_cost_usd: float | None = None


@dataclass(frozen=True)
class _Response:
    text: str
    model_name: str = "fake-model"
    usage: _Usage = _Usage()
    requested_model_id: str = "fake-model"
    effective_model_id: str = "fake-model"


def _fake_response(text: str) -> _Response:
    return _Response(text=text)


def _scaffold_payload() -> dict[str, Any]:
    return {
        "answer": "USE_TEMPLATE",
        "eigenquestion": "Does the existing artifact already answer the next test?",
        "script_family": "artifact_diagnostic",
        "template_script_path": "projects/demo/workspace/report_existing.py",
        "reuse_strategy": "Patch the existing report shape and keep output artifacts fixed.",
        "code_edit_mode": "patch_existing",
        "exact_hypothesis_under_test": "The diagnostic can be answered offline.",
        "target_script_path": "projects/demo/workspace/report_next.py",
        "script_purpose": "Summarize existing artifacts without new compute.",
        "inputs": ["projects/demo/workspace/result.json"],
        "outputs": ["projects/demo/workspace/next_report.json"],
        "command": "python3 projects/demo/workspace/report_next.py",
        "smoke_test_command": "python3 projects/demo/workspace/report_next.py --dry-run",
        "code": (
            "from __future__ import annotations\n\n"
            "def main() -> int:\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        ),
        "required_artifacts": ["next_report.json"],
        "abort_conditions": ["Abort if result.json is missing."],
        "safety_notes": ["No network or shell execution."],
    }


def run_frontier_script_scaffold_runner_fixture_regression() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        project = repo / "projects" / "demo"
        workspace = project / "workspace"
        workspace.mkdir(parents=True)
        (workspace / "report_existing.py").write_text(
            "def main():\n    return 0\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
            encoding="utf-8",
        )
        (workspace / "result.json").write_text('{"ok": true}\n', encoding="utf-8")
        packet = build_artifact_packet(
            project_dir=project,
            task="Choose the next diagnostic script.",
            allowed_roots=["projects/demo/workspace"],
            repo_root=repo,
            context_files=["projects/demo/workspace/result.json"],
        )
        call_count = {"n": 0}

        def fake_call(prompt: str) -> _Response:
            call_count["n"] += 1
            assert "meta-cold-shot" in prompt
            return _fake_response(json.dumps(_scaffold_payload()))

        first = run_frontier_script_meta_cold_shot(
            project_dir=project,
            task="Choose the next diagnostic script.",
            allowed_roots=["projects/demo/workspace"],
            model_id="fake-model",
            repo_root=repo,
            context_files=["projects/demo/workspace/result.json"],
            llm_call=fake_call,
        )
        second = run_frontier_script_meta_cold_shot(
            project_dir=project,
            task="Choose the next diagnostic script.",
            allowed_roots=["projects/demo/workspace"],
            model_id="fake-model",
            repo_root=repo,
            context_files=["projects/demo/workspace/result.json"],
            llm_call=fake_call,
        )
        latest = json.loads((workspace / "frontier_script_scaffold_latest.json").read_text(encoding="utf-8"))
        cases = [
            {
                "case_id": "packet_discovers_existing_report_script_and_context",
                "passed": (
                    "projects/demo/workspace/report_existing.py" in packet.existing_scripts
                    and packet.artifact_manifest == ["projects/demo/workspace/result.json"]
                    and '"ok": true' in packet.context
                ),
            },
            {
                "case_id": "runner_writes_scaffold_artifacts_without_materializing_code",
                "passed": (
                    Path(first["out_path"]).exists()
                    and latest["scaffold"]["target_script_path"] == "projects/demo/workspace/report_next.py"
                    and not (workspace / "report_next.py").exists()
                ),
            },
            {
                "case_id": "runner_uses_cache_on_second_identical_call",
                "passed": (
                    call_count["n"] == 1
                    and first["record"]["cache_status"] == "miss"
                    and second["record"]["cache_status"] == "hit"
                ),
            },
        ]
        outside = repo / "private_secret.txt"
        outside.write_text("SECRET", encoding="utf-8")
        restricted_packet = build_artifact_packet(
            project_dir=project,
            task="Do not leak outside roots.",
            allowed_roots=["projects/demo/workspace"],
            repo_root=repo,
            context_files=["private_secret.txt", "projects/demo/workspace/result.json"],
        )
        cases.append({
            "case_id": "packet_rejects_context_files_outside_allowed_roots",
            "passed": "SECRET" not in restricted_packet.context and restricted_packet.artifact_manifest == [
                "projects/demo/workspace/result.json"
            ],
        })
        bad_then_good = {"bad": 0, "good": 0}

        def bad_call(_prompt: str) -> _Response:
            bad_then_good["bad"] += 1
            return _fake_response("{not json")

        def good_call(_prompt: str) -> _Response:
            bad_then_good["good"] += 1
            return _fake_response(json.dumps(_scaffold_payload()))

        try:
            run_frontier_script_meta_cold_shot(
                project_dir=project,
                task="Malformed output should not poison cache.",
                allowed_roots=["projects/demo/workspace"],
                model_id="fake-model",
                repo_root=repo,
                context_files=["projects/demo/workspace/result.json"],
                llm_call=bad_call,
            )
        except ValueError:
            pass
        recovered = run_frontier_script_meta_cold_shot(
            project_dir=project,
            task="Malformed output should not poison cache.",
            allowed_roots=["projects/demo/workspace"],
            model_id="fake-model",
            repo_root=repo,
            context_files=["projects/demo/workspace/result.json"],
            llm_call=good_call,
        )
        cases.append({
            "case_id": "invalid_llm_output_is_not_cached_before_parse",
            "passed": (
                bad_then_good == {"bad": 1, "good": 1}
                and recovered["record"]["cache_status"] == "miss"
            ),
        })
    all_passed = all(bool(case["passed"]) for case in cases)
    return {
        "suite": "frontier_script_scaffold_runner_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frontier script scaffold runner fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    summary = run_frontier_script_scaffold_runner_fixture_regression()
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Frontier script scaffold runner fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
