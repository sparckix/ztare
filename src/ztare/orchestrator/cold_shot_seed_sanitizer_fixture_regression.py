from __future__ import annotations

import json

from src.ztare.orchestrator.cold_shot_seed import _sanitize_prompt_for_denylist


def run_fixture_regression() -> dict[str, object]:
    cases = []

    prompt = "Use Milgrom anchors, a_0 scale, and a neutral alpha parameter."
    sanitized, hits = _sanitize_prompt_for_denylist(prompt, ["Milgrom", "a_0"])
    cases.append({
        "case_id": "redacts_prompt_denylist_terms",
        "passed": (
            "Milgrom" not in sanitized
            and "a_0" not in sanitized
            and hits == ["Milgrom", "a_0"]
        ),
        "sanitized": sanitized,
        "hits": hits,
    })

    prompt = "The catalog should not redact cataloged as log."
    sanitized, hits = _sanitize_prompt_for_denylist(prompt, ["cat"])
    cases.append({
        "case_id": "single_word_uses_boundaries",
        "passed": sanitized == prompt and hits == [],
        "sanitized": sanitized,
        "hits": hits,
    })

    return {
        "suite": "cold_shot_seed_sanitizer_fixture_regression",
        "all_passed": all(bool(c["passed"]) for c in cases),
        "num_cases": len(cases),
        "num_passed": sum(1 for c in cases if c["passed"]),
        "results": cases,
    }


def main() -> int:
    summary = run_fixture_regression()
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
