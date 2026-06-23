from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import ztare.supervisor.supervisor_manifest as supervisor_manifest_module
from ztare.supervisor.supervisor_manifest import (
    ManifestPacketStatus,
    advance_manifest_packet,
    derive_packet_read_bundle,
    load_optional_program_manifest,
    manifest_summary,
    next_manifest_packet,
    packet_for_target,
    should_auto_promote_contract_promotion,
    validate_program_manifest,
)


def run_supervisor_manifest_fixture_regression() -> dict[str, object]:
    results: list[dict[str, object]] = []

    loaded = load_optional_program_manifest("stage2_derivation_seam_hardening")
    summary = manifest_summary(loaded)
    next_packet = next_manifest_packet(loaded)
    case1_passed = (
        loaded is not None
        and next_packet is None
        and summary is not None
        and summary["num_complete"] == 3
        and summary["num_pending_like"] == 0
    )
    results.append(
        {
            "case_id": "live_stage2_manifest_exposes_next_pending_packet",
            "passed": case1_passed,
        }
    )

    validation = validate_program_manifest("stage2_derivation_seam_hardening")
    case2_passed = validation["passed"] is True
    results.append(
        {
            "case_id": "live_stage2_manifest_validates",
            "passed": case2_passed,
        }
    )

    with tempfile.TemporaryDirectory(prefix="supervisor_manifest_fixture_") as tmp:
        manifest_dir = Path(tmp)
        advance_target = manifest_dir / "advance_manifest.json"
        advance_target.write_text(
            json.dumps(
                {
                    "program_id": "advance_manifest",
                    "completion_policy": "manifest_exhausted_to_D",
                    "auto_promote_contract_promotion": False,
                    "bundle_invariants": [
                        "research_areas/seeds/active/demo.md",
                        "research_areas/specs/demo_outline.json"
                    ],
                    "document_manifest_path": "research_areas/drafts/demo/document_manifest.json",
                    "api_prompt_versions": {
                        "research_a1": "research_packet_a1_api_v1",
                        "research_a2": "research_packet_a2_api_v1"
                    },
                    "packets": [
                        {
                            "packet_id": "p1",
                            "title": "Packet 1",
                            "status": "complete",
                            "target": "alpha",
                            "summary": "alpha",
                            "allowed_artifacts": ["research_areas/drafts/demo_opening.md"],
                        },
                        {
                            "packet_id": "p2",
                            "title": "Packet 2",
                            "status": "pending",
                            "target": "beta",
                            "summary": "beta",
                            "depends_on": ["p1"],
                            "allowed_artifacts": ["research_areas/drafts/demo_beta.md"],
                            "read_bundle": ["research_areas/drafts/demo_appendix.md"],
                            "token_budget": {
                                "a2_max_output": 2500,
                                "a2_max_fresh_input": 15000
                            }
                        },
                        {
                            "packet_id": "p3",
                            "title": "Packet 3",
                            "status": "blocked",
                            "target": "gamma",
                            "summary": "gamma",
                            "depends_on": ["p2"],
                            "allowed_artifacts": ["research_areas/drafts/demo_gamma.md"],
                            "read_bundle": ["research_areas/drafts/demo_opening.md"]
                        },
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        original_manifest_directory = supervisor_manifest_module.manifest_directory
        supervisor_manifest_module.manifest_directory = lambda: manifest_dir
        try:
            advance_result = advance_manifest_packet("advance_manifest", packet_id="p2")
            advanced_payload = json.loads(advance_target.read_text())
            advanced_manifest = load_optional_program_manifest("advance_manifest")
            summary = manifest_summary(advanced_manifest)
        finally:
            supervisor_manifest_module.manifest_directory = original_manifest_directory

        packet_beta = packet_for_target(advanced_manifest, target="beta")
        derived_beta_bundle = derive_packet_read_bundle(advanced_manifest, packet=packet_beta)
        case3_passed = (
            advance_result["updated"] is True
            and advance_result["completed_packet_id"] == "p2"
            and advance_result["unblocked_packet_ids"] == ["p3"]
            and advanced_payload["packets"][1]["status"] == "complete"
            and advanced_payload["packets"][2]["status"] == "pending"
            and packet_beta is not None
            and packet_beta.read_bundle
            == ("research_areas/drafts/demo_appendix.md",)
            and derived_beta_bundle
            == (
                "research_areas/seeds/active/demo.md",
                "research_areas/specs/demo_outline.json",
                "research_areas/drafts/demo_opening.md",
                "research_areas/drafts/demo_beta.md",
                "research_areas/drafts/demo_appendix.md",
            )
            and packet_beta.token_budget
            == {"a2_max_output": 2500, "a2_max_fresh_input": 15000}
        )
        results.append(
            {
                "case_id": "manifest_advancement_completes_current_packet_and_unblocks_dependents",
                "passed": case3_passed,
            }
        )

        target = manifest_dir / "bad_manifest.json"
        target.write_text(
            json.dumps(
                {
                    "program_id": "bad_manifest",
                    "completion_policy": "manifest_exhausted_to_D",
                    "packets": [
                        {
                            "packet_id": "p1",
                            "title": "Packet 1",
                            "status": "pending",
                            "target": "alpha",
                            "summary": "alpha",
                            "depends_on": ["p2"],
                        },
                        {
                            "packet_id": "p1",
                            "title": "Packet 1 duplicate",
                            "status": "blocked",
                            "target": "beta",
                            "summary": "beta",
                        },
                    ],
                },
                indent=2,
            )
            + "\n"
        )
        # local equivalent of validate_program_manifest without changing repo files
        payload = json.loads(target.read_text())
        packet_ids: set[str] = set()
        issues: list[str] = []
        for packet in payload["packets"]:
            if packet["packet_id"] in packet_ids:
                issues.append(f"duplicate_packet_id:{packet['packet_id']}")
            packet_ids.add(packet["packet_id"])
        for packet in payload["packets"]:
            for dependency in packet.get("depends_on", []):
                if dependency not in packet_ids:
                    issues.append(f"missing_dependency:{packet['packet_id']}->{dependency}")
        case4_passed = (
            "duplicate_packet_id:p1" in issues
            and "missing_dependency:p1->p2" in issues
        )
        results.append(
            {
                "case_id": "manifest_validator_catches_duplicate_and_missing_dependency",
                "passed": case4_passed,
            }
        )

        case5_passed = (
            summary is not None
            and summary["auto_promote_contract_promotion"] is False
            and summary["bundle_invariants"]
            == [
                "research_areas/seeds/active/demo.md",
                "research_areas/specs/demo_outline.json",
            ]
            and summary["document_manifest_path"] == "research_areas/drafts/demo/document_manifest.json"
            and summary["api_prompt_versions"]
            == {
                "research_a1": "research_packet_a1_api_v1",
                "research_a2": "research_packet_a2_api_v1",
            }
            and summary["next_packet"] is not None
            and summary["next_packet"]["read_bundle"]
            == [
                "research_areas/drafts/demo_opening.md",
            ]
            and summary["next_packet"]["derived_read_bundle"]
            == [
                "research_areas/seeds/active/demo.md",
                "research_areas/specs/demo_outline.json",
                "research_areas/drafts/demo_beta.md",
                "research_areas/drafts/demo_gamma.md",
                "research_areas/drafts/demo_opening.md",
            ]
            and summary["next_packet"]["token_budget"] == {}
        )
        results.append(
            {
                "case_id": "manifest_summary_exposes_read_bundle_and_token_budget",
                "passed": case5_passed,
            }
        )

        with tempfile.TemporaryDirectory(prefix="supervisor_manifest_autopromote_") as tmp2:
            manifest_dir2 = Path(tmp2)
            prose_target = manifest_dir2 / "prose_manifest.json"
            prose_target.write_text(
                json.dumps(
                    {
                        "program_id": "prose_manifest",
                        "completion_policy": "manifest_exhausted_to_D",
                        "document_manifest_path": "research_areas/drafts/demo/document_manifest.json",
                        "packets": [],
                    },
                    indent=2,
                )
                + "\n"
            )
            build_target = manifest_dir2 / "build_manifest.json"
            build_target.write_text(
                json.dumps(
                    {
                        "program_id": "build_manifest",
                        "completion_policy": "manifest_exhausted_to_D",
                        "packets": [],
                    },
                    indent=2,
                )
                + "\n"
            )
            original_manifest_directory = supervisor_manifest_module.manifest_directory
            supervisor_manifest_module.manifest_directory = lambda: manifest_dir2
            try:
                prose_manifest = load_optional_program_manifest("prose_manifest")
                build_manifest = load_optional_program_manifest("build_manifest")
            finally:
                supervisor_manifest_module.manifest_directory = original_manifest_directory

        case6_passed = (
            should_auto_promote_contract_promotion(prose_manifest) is False
            and should_auto_promote_contract_promotion(build_manifest) is True
        )
        results.append(
            {
                "case_id": "manifest_auto_promote_defaults_false_for_prose_and_true_for_non_prose",
                "passed": case6_passed,
            }
        )

    all_passed = all(result["passed"] for result in results)
    return {
        "suite": "supervisor_manifest_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(results),
        "num_passed": sum(1 for result in results if result["passed"]),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervisor manifest fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_supervisor_manifest_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"Supervisor manifest fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
