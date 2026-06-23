from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ztare.supervisor.supervisor_genesis import validate_program_genesis


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run_supervisor_genesis_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    with TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)

        valid_path = base / "stage2_derivation_seam_hardening.json"
        _write_json(
            valid_path,
            {
                "program_id": "stage2_derivation_seam_hardening",
                "seed_spec_path": "research_areas/seeds/deferred/systems_to_algorithms.md",
                "origin_programs": [
                    "epistemic_engine_v4_bridge_hardening",
                    "runner_hardening",
                ],
                "origin_turn_refs": [
                    "research_areas/debates/kernel/v4_bridge_hardening.md#Turn28",
                    "research_areas/debates/kernel/runner_hardening.md#Turn28",
                ],
                "problem_statement": "Fabricated safe-harbor anchors can survive into downstream hardened layers unless the derivation seam fails closed.",
                "contract_boundary": "TextInput -> HingeObject derivation seam",
                "success_condition": "safe-harbor disclaimers are independently grounded or fail closed",
                "out_of_scope": [
                    "reopening bridge hardening",
                    "reopening runner hardening",
                ],
                "opened_date": "2026-04-06",
                "opened_by": "human",
            },
        )
        valid = validate_program_genesis(valid_path)
        results.append(
            {
                "case_id": "valid_genesis_with_deferred_seed",
                "passed": valid["passed"],
                "issues": valid["issues"],
            }
        )

        closed_seed_path = base / "closed_seed_program.json"
        _write_json(
            closed_seed_path,
            {
                "program_id": "legacy_v3_interface_followup",
                "seed_spec_path": "research_areas/seeds/legacy/v3_interface.md",
                "origin_programs": [],
                "origin_turn_refs": [],
                "problem_statement": "Legacy interface spec follow-up.",
                "contract_boundary": "Legacy v3 interface seam",
                "success_condition": "n/a",
                "out_of_scope": ["n/a"],
                "opened_date": "2026-04-06",
                "opened_by": "human",
            },
        )
        closed_seed = validate_program_genesis(closed_seed_path)
        results.append(
            {
                "case_id": "closed_seed_allowed",
                "passed": closed_seed["passed"],
                "issues": closed_seed["issues"],
            }
        )

        unregistered_seed_path = base / "unregistered_seed_program.json"
        _write_json(
            unregistered_seed_path,
            {
                "program_id": "unregistered_seed_program",
                "seed_spec_path": "research_areas/README.md",
                "origin_programs": [],
                "origin_turn_refs": [],
                "problem_statement": "Unregistered seed should be rejected.",
                "contract_boundary": "n/a",
                "success_condition": "n/a",
                "out_of_scope": ["n/a"],
                "opened_date": "2026-04-06",
                "opened_by": "human",
            },
        )
        unregistered_seed = validate_program_genesis(unregistered_seed_path)
        results.append(
            {
                "case_id": "unregistered_seed_rejected",
                "passed": (not unregistered_seed["passed"]) and ("seed_spec_not_registered" in unregistered_seed["issues"]),
                "issues": unregistered_seed["issues"],
            }
        )

        active_origin_path = base / "bad_origin_program.json"
        _write_json(
            active_origin_path,
            {
                "program_id": "bad_origin_program",
                "seed_spec_path": "research_areas/seeds/deferred/ztare_open_source.md",
                "origin_programs": ["stage2_derivation_seam_hardening"],
                "origin_turn_refs": [],
                "problem_statement": "Bad active-origin case.",
                "contract_boundary": "n/a",
                "success_condition": "n/a",
                "out_of_scope": ["n/a"],
                "opened_date": "2026-04-06",
                "opened_by": "human",
            },
        )
        active_origin = validate_program_genesis(active_origin_path)
        results.append(
            {
                "case_id": "active_origin_program_rejected",
                "passed": (not active_origin["passed"]) and any(
                    issue.startswith("origin_program_not_closed_or_frozen:stage2_derivation_seam_hardening")
                    for issue in active_origin["issues"]
                ),
                "issues": active_origin["issues"],
            }
        )

    all_passed = all(item["passed"] for item in results)
    return {
        "suite": "supervisor_genesis_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor genesis fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_genesis_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor genesis fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
        if not result["passed"]:
            print(f"       issues: {', '.join(result['issues'])}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
