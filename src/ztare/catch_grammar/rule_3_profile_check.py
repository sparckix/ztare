"""Deterministic verifier for catch grammar rule 3.

Rule 3 (`profile_dependent_claim_as_unconditional`) says: whenever a seam or
spec asserts "kernel has X", resolve X to a module name and verify its
inclusion in the profile that will actually run. This file is the non-LLM
existence proof the multi-agent scorer contract demands before any LLM role
is wired up.

No LLM calls. No network. Stdlib only. Imports the live profile table from
`ztare.validator.pivot_heuristics` so the check tracks the real runtime
configuration rather than a transcribed copy.

Exit code 0 = claim holds. Exit code 1 = claim violated. Exit code 2 = usage
error or unknown profile.
"""
from __future__ import annotations

import json
import sys
from typing import Iterable

from src.ztare.validator.utilities.pivot_heuristics import PROFILE_MODULES

RULE = "profile_dependent_claim_as_unconditional"


def check_profile_contains(profile_name: str, required_modules: Iterable[str]) -> dict:
    if profile_name not in PROFILE_MODULES:
        return {
            "rule": RULE,
            "profile": profile_name,
            "verdict": "unknown_profile",
            "present": [],
            "missing": list(required_modules),
            "known_profiles": sorted(PROFILE_MODULES.keys()),
            "message": f"profile {profile_name!r} not defined in pivot_heuristics.PROFILE_MODULES",
        }
    profile_modules = set(PROFILE_MODULES[profile_name])
    required = list(required_modules)
    present = [m for m in required if m in profile_modules]
    missing = [m for m in required if m not in profile_modules]
    verdict = "pass" if not missing else "fail"
    message = (
        f"profile {profile_name!r} contains all {len(required)} required modules"
        if verdict == "pass"
        else f"profile {profile_name!r} is missing {len(missing)} required module(s): {missing}"
    )
    return {
        "rule": RULE,
        "profile": profile_name,
        "verdict": verdict,
        "present": present,
        "missing": missing,
        "profile_modules": sorted(profile_modules),
        "message": message,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "usage: python -m src.ztare.catch_grammar.rule_3_profile_check "
            "<profile_name> <required_module> [<required_module> ...]",
            file=sys.stderr,
        )
        return 2
    result = check_profile_contains(argv[1], argv[2:])
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["verdict"] == "pass":
        return 0
    if result["verdict"] == "unknown_profile":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
