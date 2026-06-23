from __future__ import annotations

import argparse
import json
from pathlib import Path

from ztare.orchestrator.frontier_script_scaffold import (
    build_frontier_script_scaffold_prompt,
    parse_frontier_script_scaffold_json,
)


ALLOWED_ROOTS = [
    "projects/ns_millennium_hunt/workspace",
    "projects/gp163d_unified_accel/raw/three_d_gravity_sandbox",
]


def _valid_code() -> str:
    return '''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    payload = {"dry_run": args.dry_run}
    Path("projects/ns_millennium_hunt/workspace/meta_scaffold_smoke.json").write_text(
        json.dumps(payload, indent=2) + "\\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "answer": "FORK_EXISTING_COLD_SHOT_RUNNER",
        "eigenquestion": "Does the next proof target require an anti-cancellation cold shot or an artifact diagnostic?",
        "script_family": "cold_shot_panel",
        "template_script_path": "projects/ns_millennium_hunt/workspace/run_cold_shot_cone_mass_anti_cancellation.py",
        "reuse_strategy": "Fork the prompt-packet/strict-JSON/dual-model/raw-artifact pattern; replace only packet inputs and schema.",
        "code_edit_mode": "new_file_from_template",
        "exact_hypothesis_under_test": "A local core/sheath theorem target survives hostile cold-shot review.",
        "target_script_path": "projects/ns_millennium_hunt/workspace/run_cold_shot_next_frontier_target.py",
        "script_purpose": "Run an attributable two-model cold shot against the next frontier proof target.",
        "inputs": ["ztare_proofs/ZtareProofs/*.lean", "projects/ns_millennium_hunt/workspace/*.md"],
        "outputs": ["projects/ns_millennium_hunt/workspace/cold_shot_next_frontier_target.json"],
        "command": "python3 projects/ns_millennium_hunt/workspace/run_cold_shot_next_frontier_target.py",
        "smoke_test_command": "python3 projects/ns_millennium_hunt/workspace/run_cold_shot_next_frontier_target.py --dry-run",
        "code": _valid_code(),
        "required_artifacts": ["raw model response files", "strict parsed JSON summary"],
        "abort_conditions": ["Abort if the input proof target file is missing."],
        "safety_notes": ["No SSH, no destructive commands, no automatic GPU launch."],
    }
    payload.update(overrides)
    return payload


def run_frontier_script_scaffold_fixture_regression() -> dict[str, object]:
    prompt = build_frontier_script_scaffold_prompt(
        context="Recent manual loops used run_cold_shot_cone_mass_anti_cancellation.py as a reusable pattern.",
        task="Choose the smallest script needed for the next hostile proof review.",
        allowed_roots=ALLOWED_ROOTS,
        existing_scripts=[
            "projects/ns_millennium_hunt/workspace/run_cold_shot_cone_mass_anti_cancellation.py",
            "projects/gp163d_unified_accel/raw/three_d_gravity_sandbox/report_angle_ladder.py",
        ],
        forbidden_actions=["No SSH or cloud launch."],
    )
    parsed = parse_frontier_script_scaffold_json(json.dumps(_payload()), allowed_roots=ALLOWED_ROOTS)
    cases = [
        {
            "case_id": "prompt_demands_meta_template_selection",
            "passed": (
                "meta-cold-shot" in prompt
                and "script family" in prompt
                and "template_script_path" in prompt
                and "new_file_from_template" in prompt
            ),
        },
        {
            "case_id": "parser_accepts_template_fork_payload",
            "passed": (
                parsed.script_family == "cold_shot_panel"
                and parsed.template_script_path.endswith("run_cold_shot_cone_mass_anti_cancellation.py")
                and parsed.code_edit_mode == "new_file_from_template"
                and parsed.to_record()["schema_version"] == 2
            ),
        },
        {
            "case_id": "parser_rejects_absolute_target_path",
            "passed": False,
        },
        {
            "case_id": "parser_rejects_banned_subprocess",
            "passed": False,
        },
        {
            "case_id": "parser_rejects_missing_main_guard",
            "passed": False,
        },
        {
            "case_id": "parser_accepts_no_code_needed_without_template",
            "passed": False,
        },
        {
            "case_id": "parser_rejects_destructive_command_text",
            "passed": False,
        },
        {
            "case_id": "parser_rejects_empty_code_for_new_file",
            "passed": False,
        },
        {
            "case_id": "parser_rejects_subprocess_alias_import",
            "passed": False,
        },
    ]
    try:
        parse_frontier_script_scaffold_json(
            json.dumps(_payload(target_script_path="/tmp/bad.py")),
            allowed_roots=ALLOWED_ROOTS,
        )
    except ValueError:
        cases[2]["passed"] = True
    try:
        parse_frontier_script_scaffold_json(
            json.dumps(_payload(code="import subprocess\nsubprocess.run(['true'])\n")),
            allowed_roots=ALLOWED_ROOTS,
        )
    except ValueError:
        cases[3]["passed"] = True
    try:
        parse_frontier_script_scaffold_json(
            json.dumps(_payload(code="def main():\n    return 0\n")),
            allowed_roots=ALLOWED_ROOTS,
        )
    except ValueError:
        cases[4]["passed"] = True
    no_code = parse_frontier_script_scaffold_json(
        json.dumps(
            _payload(
                template_script_path="",
                code_edit_mode="no_code_needed",
                code="",
                abort_conditions=["Existing artifact already answers the question."],
            )
        ),
        allowed_roots=ALLOWED_ROOTS,
    )
    cases[5]["passed"] = no_code.code == "" and no_code.template_script_path == ""
    try:
        parse_frontier_script_scaffold_json(
            json.dumps(_payload(command="rm -rf projects/ns_millennium_hunt/workspace")),
            allowed_roots=ALLOWED_ROOTS,
        )
    except ValueError:
        cases[6]["passed"] = True
    try:
        parse_frontier_script_scaffold_json(
            json.dumps(_payload(code="")),
            allowed_roots=ALLOWED_ROOTS,
        )
    except ValueError:
        cases[7]["passed"] = True
    try:
        parse_frontier_script_scaffold_json(
            json.dumps(
                _payload(
                    code=(
                        "import subprocess as sp\n\n"
                        "def main() -> int:\n"
                        "    sp.run(['true'])\n"
                        "    return 0\n\n"
                        "if __name__ == '__main__':\n"
                        "    raise SystemExit(main())\n"
                    )
                )
            ),
            allowed_roots=ALLOWED_ROOTS,
        )
    except ValueError:
        cases[8]["passed"] = True
    all_passed = all(bool(case["passed"]) for case in cases)
    return {
        "suite": "frontier_script_scaffold_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frontier script scaffold fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    summary = run_frontier_script_scaffold_fixture_regression()
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Frontier script scaffold fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
