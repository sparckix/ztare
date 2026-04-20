from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.supervisor.supervisor_registry import validate_program_registry


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate supervisor/program_registry.json for supervisor readiness.")
    parser.add_argument("--registry-path", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = validate_program_registry(args.registry_path)
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor registry check: {summary['num_passed']}/{summary['num_programs']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"  {status} {result['program_id']}: status={result['status']} owner_mode={result['owner_mode']} last_turn={result['last_turn']}"
        )
        if not result["passed"]:
            print(f"       issues: {', '.join(result['issues'])}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
