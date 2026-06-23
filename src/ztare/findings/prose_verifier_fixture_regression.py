from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from ztare.findings.prose_spec import (
    ProseAssertionType,
    ProseSpec,
    ProseSpecAssertion,
    load_prose_spec,
    prose_spec_to_dict,
    validate_prose_spec,
)
from ztare.findings.prose_verifier import verify_prose_file, verify_prose_markdown


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _build_valid_spec() -> ProseSpec:
    return ProseSpec(
        packet_id="paper4_intro_section",
        required_headers=("Introduction", "Managerial Split"),
        assertions=(
            ProseSpecAssertion(
                assertion_id="intro_contains_claim",
                section_header="Introduction",
                assertion_type=ProseAssertionType.CONTAINS_PHRASE,
                target="Managerial capitalism separates strategy from execution",
            ),
            ProseSpecAssertion(
                assertion_id="intro_contains_citation",
                section_header="Introduction",
                assertion_type=ProseAssertionType.CONTAINS_CITATION,
                target="(Chandler, 1962)",
            ),
            ProseSpecAssertion(
                assertion_id="intro_has_counterargument",
                section_header="Introduction",
                assertion_type=ProseAssertionType.HAS_SUBSECTION,
                target="Counter-Argument",
            ),
            ProseSpecAssertion(
                assertion_id="intro_word_count",
                section_header="Introduction",
                assertion_type=ProseAssertionType.WORD_COUNT_RANGE,
                target_min=20,
                target_max=120,
            ),
            ProseSpecAssertion(
                assertion_id="managerial_split_banned_phrase",
                section_header="Managerial Split",
                assertion_type=ProseAssertionType.ABSENT_PHRASE,
                target="fully autonomous without oversight",
            ),
        ),
        global_word_min=30,
        global_word_max=220,
    )


def _build_valid_markdown() -> str:
    return """## Introduction
Managerial capitalism separates strategy from execution in the same organization.
This makes the paper's control-plane argument concrete and historically grounded (Chandler, 1962).

### Counter-Argument
An owner-operator can still move faster in a narrow domain, but the scaling problem remains.

## Managerial Split
The factory should handle bounded execution while the principal retains capital allocation.
"""


def _build_legacy_shape_spec_payload() -> dict:
    return {
        "packet_id": "legacy_paper4_intro_section",
        "required_headers": [
            "Introduction",
            "Managerial Split",
        ],
        "required_citations": [
            {
                "section_header": "Introduction",
                "citation": "(Chandler, 1962)",
            }
        ],
        "required_phrases": [
            {
                "section_header": "Introduction",
                "phrase": "Managerial capitalism separates strategy from execution",
            }
        ],
        "banned_phrases": [
            {
                "section_header": "Managerial Split",
                "phrase": "fully autonomous without oversight",
            }
        ],
        "word_count_bounds": [
            {
                "section_header": "Introduction",
                "min_words": 20,
                "max_words": 120,
            },
            {
                "section_header": "__document__",
                "min_words": 30,
                "max_words": 220,
            },
        ],
    }


def _build_shorthand_canonical_spec_payload() -> dict:
    return {
        "packet_id": "shorthand_paper4_intro_section",
        "required_headers": [
            "Introduction",
            "Managerial Split",
        ],
        "assertions": [
            {"contains_phrase": "Managerial capitalism separates strategy from execution"},
            {"contains_citation": "(Chandler, 1962)"},
            {"has_subsection": "Counter-Argument"},
            {"absent_phrase": "fully autonomous without oversight"},
            {"word_count_range": {"min": 20, "max": 220}},
        ],
        "global_word_min": 30,
        "global_word_max": 220,
    }


def run_prose_verifier_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    valid_spec = _build_valid_spec()
    valid_markdown = _build_valid_markdown()

    valid_result = verify_prose_markdown(valid_markdown, valid_spec)
    results.append(
        {
            "case_id": "valid_markdown_passes_deterministic_prose_spec",
            "passed": valid_result.passed is True and not valid_result.failed_assertions,
        }
    )

    missing_citation = valid_markdown.replace("(Chandler, 1962)", "")
    missing_citation_result = verify_prose_markdown(missing_citation, valid_spec)
    results.append(
        {
            "case_id": "missing_required_citation_fails",
            "passed": missing_citation_result.passed is False
            and any(
                item.assertion_id == "intro_contains_citation"
                and item.reason == "required_citation_missing"
                for item in missing_citation_result.failed_assertions
            ),
        }
    )

    forbidden_phrase_markdown = valid_markdown + "\nThis program is fully autonomous without oversight.\n"
    forbidden_phrase_result = verify_prose_markdown(forbidden_phrase_markdown, valid_spec)
    results.append(
        {
            "case_id": "forbidden_phrase_fails_absent_phrase_assertion",
            "passed": forbidden_phrase_result.passed is False
            and any(
                item.assertion_id == "managerial_split_banned_phrase"
                and item.reason == "forbidden_phrase_present"
                for item in forbidden_phrase_result.failed_assertions
            ),
        }
    )

    missing_subsection = valid_markdown.replace("### Counter-Argument\n", "### Rebuttal\n")
    missing_subsection_result = verify_prose_markdown(missing_subsection, valid_spec)
    results.append(
        {
            "case_id": "missing_subsection_fails_header_assertion",
            "passed": missing_subsection_result.passed is False
            and any(
                item.assertion_id == "intro_has_counterargument"
                and item.reason == "required_subsection_missing"
                for item in missing_subsection_result.failed_assertions
            ),
        }
    )

    invalid_spec = ProseSpec(
        packet_id="bad_spec",
        required_headers=("Introduction",),
        assertions=(
            ProseSpecAssertion(
                assertion_id="bad_range",
                section_header="Introduction",
                assertion_type=ProseAssertionType.WORD_COUNT_RANGE,
                target_min=20,
                target_max=5,
            ),
        ),
        global_word_min=10,
        global_word_max=5,
    )
    invalid_validation = validate_prose_spec(invalid_spec)
    results.append(
        {
            "case_id": "invalid_spec_is_rejected_before_verification",
            "passed": invalid_validation["passed"] is False
            and "global_word_range_inverted" in invalid_validation["issues"]
            and "word_count_range_inverted:bad_range" in invalid_validation["issues"],
        }
    )

    with tempfile.TemporaryDirectory(prefix="prose_verifier_fixture_") as tmp:
        tmp_path = Path(tmp)
        spec_path = tmp_path / "prose_spec.json"
        draft_path = tmp_path / "draft.md"
        _write_json(spec_path, prose_spec_to_dict(valid_spec))
        draft_path.write_text(valid_markdown)
        file_result = verify_prose_file(draft_path=draft_path, spec_path=spec_path)
        results.append(
            {
                "case_id": "file_api_round_trip_passes",
                "passed": file_result.passed is True and file_result.total_word_count > 0,
            }
        )

        legacy_spec_path = tmp_path / "legacy_prose_spec.json"
        _write_json(legacy_spec_path, _build_legacy_shape_spec_payload())
        legacy_result = verify_prose_file(draft_path=draft_path, spec_path=legacy_spec_path)
        results.append(
            {
                "case_id": "legacy_shape_spec_round_trip_passes",
                "passed": legacy_result.passed is True and legacy_result.total_word_count > 0,
            }
        )

        shorthand_spec_path = tmp_path / "shorthand_prose_spec.json"
        _write_json(shorthand_spec_path, _build_shorthand_canonical_spec_payload())
        shorthand_loaded = load_prose_spec(shorthand_spec_path)
        shorthand_result = verify_prose_file(draft_path=draft_path, spec_path=shorthand_spec_path)
        results.append(
            {
                "case_id": "shorthand_assertion_shape_round_trip_passes",
                "passed": shorthand_result.passed is True
                and shorthand_result.total_word_count > 0
                and len(shorthand_loaded.assertions) == 5,
            }
        )

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "prose_verifier_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic prose verifier fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_prose_verifier_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Prose verifier fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
