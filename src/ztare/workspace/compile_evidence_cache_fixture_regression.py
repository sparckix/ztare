import argparse
import json
import tempfile
from pathlib import Path

from src.ztare.workspace import compile_evidence as ce


def _packet_for(path: str) -> dict[str, object]:
    return {
        "project": "fixture_project",
        "compiler_summary": "Fixture compile output.",
        "immutable_ground_truth": [
            {
                "statement": "A grounded fact exists.",
                "strength": "high",
                "source_ids": ["S001"],
            }
        ],
        "numerical_ranges_and_constraints": [],
        "identified_contradictions": [],
        "epistemic_voids": [],
        "provenance": [
            {
                "source_id": "S001",
                "path": path,
                "kind": "md",
                "summary": "Fixture source summary.",
            }
        ],
        "candidate_claims_to_test": [],
    }


def run_compile_evidence_cache_fixture_regression() -> dict[str, object]:
    original_llm_client = ce.LLMClient

    class StubLLMClient:
        call_count = 0
        responses: list[str] = []

        def __init__(self, model_family: str):
            self.model_family = model_family
            self.model_id = ce.MODEL_MAP[model_family]

        def call(self, prompt: str, retries: int = 4) -> str:
            type(self).call_count += 1
            if not type(self).responses:
                raise AssertionError("Unexpected LLM call during compile_evidence cache regression.")
            return type(self).responses.pop(0)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project_dir = tmp / "project"
        raw_dir = project_dir / "raw"
        workspace_dir = project_dir / "workspace"
        raw_dir.mkdir(parents=True, exist_ok=True)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        raw_file = raw_dir / "source.md"
        raw_file.write_text(
            "---\nsource_type: source_evidence\n---\nAlpha evidence line.\n",
            encoding="utf-8",
        )

        try:
            ce.LLMClient = StubLLMClient

            StubLLMClient.responses = [json.dumps(_packet_for("source.md"))]
            packet_1, manifest_1, evidence_1 = ce.compile_from_raw(
                project_dir=project_dir,
                raw_dir=raw_dir,
                workspace_dir=workspace_dir,
                model="claude",
                max_files=10,
                max_chars_per_file=2000,
                max_total_chars=5000,
            )
            first_call_count = StubLLMClient.call_count

            packet_2, manifest_2, evidence_2 = ce.compile_from_raw(
                project_dir=project_dir,
                raw_dir=raw_dir,
                workspace_dir=workspace_dir,
                model="claude",
                max_files=10,
                max_chars_per_file=2000,
                max_total_chars=5000,
            )
            second_call_count = StubLLMClient.call_count
            latest_hit_after_second = ce.read_json(workspace_dir / ce.LATEST_COMPILE_CACHE_HIT)

            raw_file.write_text(
                "---\nsource_type: source_evidence\n---\nAlpha evidence line changed.\n",
                encoding="utf-8",
            )
            StubLLMClient.responses = [json.dumps(_packet_for("source.md"))]
            _, manifest_3, _ = ce.compile_from_raw(
                project_dir=project_dir,
                raw_dir=raw_dir,
                workspace_dir=workspace_dir,
                model="claude",
                max_files=10,
                max_chars_per_file=2000,
                max_total_chars=5000,
            )
            third_call_count = StubLLMClient.call_count

            raw_file.write_text(
                "---\nsource_type: source_evidence\n---\nAlpha evidence line.\n",
                encoding="utf-8",
            )
            StubLLMClient.responses = [json.dumps(_packet_for("source.md"))]
            _, manifest_4, _ = ce.compile_from_raw(
                project_dir=project_dir,
                raw_dir=raw_dir,
                workspace_dir=workspace_dir,
                model="claude",
                max_files=10,
                max_chars_per_file=5,
                max_total_chars=5000,
            )
            fourth_call_count = StubLLMClient.call_count

        finally:
            ce.LLMClient = original_llm_client

        cache_index = ce.read_json(workspace_dir / ce.RAW_COMPILE_CACHE_INDEX)

        cases = [
            {
                "case_id": "second_identical_raw_compile_is_cache_hit",
                "passed": (
                    first_call_count == 1
                    and second_call_count == 1
                    and manifest_1.get("cache_hit") is False
                    and manifest_2.get("cache_hit") is True
                    and packet_1 == packet_2
                    and evidence_1 != ""
                    and evidence_2 != ""
                ),
            },
            {
                "case_id": "source_content_change_invalidates_cache",
                "passed": (
                    third_call_count == 2
                    and manifest_3.get("cache_hit") is False
                ),
            },
            {
                "case_id": "budget_change_invalidates_cache",
                "passed": (
                    fourth_call_count == 3
                    and manifest_4.get("cache_hit") is False
                ),
            },
            {
                "case_id": "cache_artifacts_are_persisted_and_latest_hit_is_recorded",
                "passed": (
                    isinstance(cache_index.get("entries"), dict)
                    and len(cache_index.get("entries", {})) >= 2
                    and latest_hit_after_second.get("cache_key") == manifest_2.get("cache_key")
                ),
            },
        ]

    all_passed = all(case["passed"] for case in cases)
    return {
        "suite": "compile_evidence_cache_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run compile evidence cache fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_compile_evidence_cache_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Compile evidence cache fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
