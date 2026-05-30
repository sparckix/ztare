from __future__ import annotations

import json

from src.ztare.orchestrator.science_claim_gate import assess_science_claim_packet


def _base_science_packet() -> dict[str, object]:
    return {
        "claim_id": "fixture_science",
        "claim_target": "paper",
        "claim": "candidate branch-native theorem object",
        "trigger_artifact": "workspace/source.md",
        "instrument_signal": "local transport ratio rose",
        "science_object": "matching at R forces lambdaMin <= exp(1 - R/C)",
        "why_not_instrument_only": "the object is an algebraic branch invariant, not a score",
        "overclaim_killed": ["raw transport ratio implies capacity deficit"],
        "rival_explanations": ["denominator choice", "parabolic escape"],
        "denominator_or_scale_audits": ["material vs parabolic denominator audit"],
        "scope_limits": ["finite corpus", "conditional on material control"],
        "nonclaims": ["not a global theorem", "not a parabolic capacity deficit"],
        "next_theorem_obligation": "prove sharp material control B <= C M",
        "evidence_artifacts": ["workspace/audit.md"],
        "falsifiers_run": [
            {
                "name": "hostile denominator audit",
                "status": "closed",
                "killed_overclaim": "raw transport ratio implies capacity deficit",
                "evidence_artifacts": ["workspace/audit.md"],
            }
        ],
        "ratio_or_scale_claim": True,
        "paper_wording": ["scoped wording"],
    }


def run_fixture_regression() -> dict[str, object]:
    cases: list[dict[str, object]] = []

    instrument = {
        "claim_id": "instrument_fixture",
        "claim_target": "instrument",
        "claim": "gate detects denominator drift",
        "trigger_artifact": "workspace/audit.json",
        "instrument_signal": "audit classification changed",
        "evidence_artifacts": ["workspace/audit.json"],
    }
    verdict = assess_science_claim_packet(instrument)
    cases.append({
        "case_id": "instrument_claim_does_not_become_science_ready",
        "passed": verdict.classification == "instrument_claim_ready" and not verdict.science_ready,
        "verdict": verdict.to_record(),
    })

    missing_falsifier = _base_science_packet()
    missing_falsifier["falsifiers_run"] = []
    verdict = assess_science_claim_packet(missing_falsifier)
    cases.append({
        "case_id": "science_claim_without_closed_falsifier_blocks",
        "passed": (not verdict.science_ready and any("no closed falsifier" in r for r in verdict.blocking_reasons)),
        "verdict": verdict.to_record(),
    })

    missing_denominator = _base_science_packet()
    missing_denominator.pop("denominator_or_scale_audits")
    verdict = assess_science_claim_packet(missing_denominator)
    cases.append({
        "case_id": "ratio_claim_without_denominator_audit_blocks",
        "passed": (not verdict.science_ready and any("denominator_or_scale" in r for r in verdict.blocking_reasons)),
        "verdict": verdict.to_record(),
    })

    formal = _base_science_packet()
    formal["formal_target"] = True
    verdict = assess_science_claim_packet(formal)
    cases.append({
        "case_id": "formal_target_without_resource_plan_blocks",
        "passed": (not verdict.science_ready and any("formal_resource_plan" in r for r in verdict.blocking_reasons)),
        "verdict": verdict.to_record(),
    })

    ready = _base_science_packet()
    ready["formal_target"] = True
    ready["formal_resource_plan"] = "standalone target under timeout and memory cap; no umbrella build"
    verdict = assess_science_claim_packet(ready)
    cases.append({
        "case_id": "complete_science_packet_ready",
        "passed": verdict.science_ready and verdict.classification == "science_claim_scope_ready",
        "verdict": verdict.to_record(),
    })

    return {
        "suite": "science_claim_gate_fixture_regression",
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
