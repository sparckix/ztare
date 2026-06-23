#!/usr/bin/env python3
"""Model-free claim-discipline demo for public review.

This is a deterministic companion to `make demo`. It does not reproduce old
case studies and does not call a model. Instead it runs a small public claim
packet through current claim-discipline/read-model surfaces and emits the
demoted public wording as JSON.
"""
from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ztare.orchestrator.promotion_guard import assess_promotion_readiness  # noqa: E402
from ztare.reports.operations_intelligence import build_source_readiness  # noqa: E402


def _load_linter_module() -> Any:
    path = REPO / "scripts/public/control/closure_claim_discipline_linter.py"
    spec = importlib.util.spec_from_file_location("closure_claim_discipline_linter", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LINTER = _load_linter_module()


CLAIM_PACKET: dict[str, Any] = {
    "packet_id": "public_demo_overpromoted_best_system_claim_v1",
    "claim_text": (
        "ZTARE is the best available autonomous mathematical-research system "
        "and should be described as the current best research engine."
    ),
    "proposed_public_wording": (
        "ZTARE is the best available autonomous mathematical-research system."
    ),
    "evidence_refs": [
        "docs/public_claim_register.md",
        "benchmarks/benchmark_evidence.md",
        "papers/experimental_math_letter/evidence/pysr_baseline_full.json",
        "scripts/public/control/closure_claim_discipline_linter.py",
        "scripts/public/control/action_intelligence.py",
    ],
    "claimed_scope": [
        "autonomous mathematical research",
        "general research-engine superiority",
        "best-available-system comparison",
    ],
    "available_evidence": [
        "public claim register requires explicit non-claims and next falsifiers",
        "PySR baseline evidence supports bounded null-returning gate discipline",
        "claim-discipline linter is available for artifact-level checks",
        "operations-intelligence source-readiness read model can label partial/blocked sources",
    ],
}


def _artifact_text(packet: dict[str, Any]) -> str:
    """Render the claim packet as the kind of artifact the linter reads."""
    return "\n".join(
        [
            "# Public claim packet",
            "",
            f"Claim: {packet['claim_text']}",
            "",
            "## Layer 1: claim-discipline surface",
            "",
            "ZTARE is asserted to be the best available system. It cites internal surfaces but "
            "does not provide a benchmark artifact, pass threshold, measurement, "
            "external baseline adapter, or scoped falsifier.",
            "",
            "## Evidence refs",
            *[f"- {ref}" for ref in packet.get("evidence_refs", [])],
        ]
    )


def _source_readiness() -> dict[str, Any]:
    source_map = {
        "rows": [
            {
                "source_id": "public_claim_register",
                "feeds": ["docs/public_claim_register.md"],
                "source_refs": ["docs/public_claim_register.md"],
                "source_gaps": [],
            },
            {
                "source_id": "partial_external_baselines",
                "feeds": ["benchmarks/benchmark_evidence.md"],
                "source_refs": [
                    "benchmarks/benchmark_evidence.md",
                    "papers/experimental_math_letter/evidence/pysr_baseline_full.json",
                ],
                "source_gaps": [
                    "PySR comparison is a bounded symbolic-regression baseline, not a broad best-system suite",
                    "no frozen external benchmark matrix covers autonomous mathematical research generally",
                ],
            },
            {
                "source_id": "broad_best_system_benchmarks",
                "feeds": [],
                "source_refs": [],
                "source_gaps": [
                    "no external benchmark adapter for broad best-system comparison is attached",
                    "no pre-registered broad best-system metric or comparison population is attached",
                ],
            },
            {
                "source_id": "claim_falsifier_packet",
                "feeds": [],
                "source_refs": [],
                "source_gaps": ["next falsifier exists only as a required plan, not as a result"],
            },
        ]
    }
    payload = {
        "source_map": source_map,
        "source_improvement_backlog": [
            {
                "source_id": "broad_best_system_benchmarks",
                "gap": "freeze a public benchmark matrix before any broad best-system wording",
                "recommended_action": "improve_source_emitter_or_schema",
            },
            {
                "source_id": "claim_falsifier_packet",
                "gap": "pre-register a binary falsifier for the bounded claim",
                "recommended_action": "improve_source_emitter_or_schema",
            },
        ],
        "etl_manifest": {
            "validate": {
                "issues": [
                    {
                        "severity": "blocking",
                        "source_id": "broad_best_system_benchmarks",
                        "issue": "superiority claim exceeds the existing bounded PySR and evaluator benchmarks",
                    }
                ]
            }
        },
    }
    return build_source_readiness(payload)


def _claim_discipline_checks(text: str) -> list[dict[str, Any]]:
    checks = [
        LINTER.check_ap012_per_step_verification(text),
        LINTER.check_mp023_scope_coverage(text),
        LINTER.check_mp022_op_enumeration(text),
        LINTER.check_anti_pattern_012_specific(text),
        LINTER.check_pattern_026_architecture_validation(text),
    ]
    return [
        {
            "surface": "closure_claim_discipline_linter",
            "check": check.get("check") or check.get("name"),
            "passes": bool(check.get("passes")),
            "detail": {
                key: value
                for key, value in check.items()
                if key not in {"check", "name", "passes"}
            },
        }
        for check in checks
    ]


def build_demo_payload(packet: dict[str, Any] | None = None) -> dict[str, Any]:
    packet = dict(packet or CLAIM_PACKET)
    artifact_text = _artifact_text(packet)
    discipline_checks = _claim_discipline_checks(artifact_text)
    readiness = _source_readiness()
    promotion = assess_promotion_readiness(
        REPO / "public_demo_claim_discipline",
        records=[
            {
                "project": "public_demo_claim_discipline",
                "status": "open",
                "license_stage": "scratchpad",
                "severity_level": 2,
                "promotion_blocking": False,
                "can_support_promotion": False,
            }
        ],
    ).to_record()

    missing_evidence = [
        "broad external best-system benchmark comparison beyond the bounded PySR baseline",
        "pre-registered benchmark metric and comparison population",
        "closed L4/L5 promotion discriminator with explicit evidence artifacts",
        "binary falsifier that would demote the bounded public claim",
    ]
    next_falsifier = {
        "question": (
            "On a small public benchmark with named external baselines, does "
            "ZTARE beat the baseline under the pre-registered metric?"
        ),
        "demote_if": "no external-baseline win, no reproducible metric, or no closed promotion-grade discriminator",
        "promote_only_to": "benchmark-specific bounded claim, not general best-system status",
    }
    bounded_wording = (
        "ZTARE currently demonstrates public claim-discipline machinery: it "
        "can inspect an overpromoted best-system claim, surface missing evidence, "
        "state non-claims, and route the claim to a next falsifier. This demo "
        "does not establish a model-performance or best-system claim."
    )

    ok = (
        readiness["summary"]["blocked"] >= 1
        and not promotion["promotion_ready"]
        and any(not check["passes"] for check in discipline_checks)
    )
    return {
        "ok": ok,
        "demo": "claim_discipline_demo",
        "model_free": True,
        "writes_persistent_runtime_state": False,
        "input_claim_packet": packet,
        "current_public_surfaces_used": [
            "scripts/public/control/closure_claim_discipline_linter.py",
            "src/ztare/reports/operations_intelligence.py::build_source_readiness",
            "src/ztare/orchestrator/promotion_guard.py::assess_promotion_readiness",
        ],
        "claim_discipline_checks": discipline_checks,
        "source_readiness": readiness,
        "promotion_guard": promotion,
        "decision": {
            "verdict": "demote_to_bounded_wording",
            "claim_allowed": False,
            "bounded_wording": bounded_wording,
            "missing_evidence": missing_evidence,
            "non_claims": [
                "not a best-system claim",
                "not a model-performance claim",
                "not evidence of autonomous mathematical-research superiority",
                "not a replacement for external baselines or closed discriminators",
            ],
            "next_falsifier": next_falsifier,
        },
    }


def main() -> int:
    payload = build_demo_payload()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
