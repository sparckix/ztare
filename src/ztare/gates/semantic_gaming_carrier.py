"""Carrier gates for semantic gaming vectors.

These vectors are not soundly handled by a plain AST detector. The deterministic
part here is the carrier selection: identify when a project needs semantic
scope/transfer/rigor review and fail closed unless that risk is handled.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


Detector = Callable[[str, str, str], bool]


@dataclass(frozen=True)
class SemanticCarrierSpec:
    vector: str
    category: str
    gate_name: str
    detector: Detector
    review_role: str
    reason: str


def _norm(text: str) -> str:
    return (text or "").lower()


def detect_scope_overclaim(thesis_text: str, evidence_text: str, test_model_text: str) -> bool:
    try:
        from src.ztare.validator.core.hinge_handoff import (
            HingeAlignmentStatus,
            build_stage2_handoff,
        )

        handoff = build_stage2_handoff(thesis_text, evidence_text, test_model_text)
        if handoff.alignment_status == HingeAlignmentStatus.MISALIGNED_OVERCLAIM:
            return True
    except Exception:  # noqa: BLE001
        pass
    combined = _norm("\n".join([thesis_text, evidence_text]))
    local = any(token in combined for token in ("local mapping", "local component", "received-token", "received token"))
    systemic = any(token in combined for token in ("whole-system", "whole system", "end-to-end", "end to end", "silent failure"))
    return local and systemic


def detect_abstraction_transfer(thesis_text: str, evidence_text: str, test_model_text: str) -> bool:
    combined = _norm("\n".join([thesis_text, evidence_text, test_model_text]))
    abstraction = any(
        token in combined
        for token in (
            "abstraction mandate",
            "abstract architectural proof",
            "general theorem",
            "transport-invariant",
            "transfers across",
            "transfer across",
        )
    )
    concrete_proxy = any(
        token in combined
        for token in (
            "midtown",
            "city-specific",
            "dense-core",
            "dense core",
            "proxy constants",
            "urban proxy",
            "hub_overhead",
        )
    )
    return abstraction and concrete_proxy


def detect_selective_rigor(thesis_text: str, evidence_text: str, test_model_text: str) -> bool:
    combined = _norm("\n".join([thesis_text, evidence_text, test_model_text]))
    direct = any(token in combined for token in ("selective rigor", "claim-test mismatch", "scaffolding proof"))
    test_scaffold = any(token in combined for token in ("bridge parameter", "internal arithmetic", "bookkeeping", "scaffolding"))
    central_untested = any(
        token in combined
        for token in (
            "central claim",
            "core claim untested",
            "does not test",
            "variance preservation",
            "orthogonality",
            "decisive claim",
        )
    )
    return direct or (test_scaffold and central_untested)


SEMANTIC_CARRIER_SPECS: dict[str, SemanticCarrierSpec] = {
    "scope_overclaim_local_to_systemic": SemanticCarrierSpec(
        vector="scope_overclaim_local_to_systemic",
        category="NOVEL:scope_laundering",
        gate_name="global_semantic_scope_overclaim_carrier",
        detector=detect_scope_overclaim,
        review_role="SCOPE_OVERCLAIM_AUDITOR",
        reason="local evidence or code is presented as a whole-system or end-to-end guarantee",
    ),
    "abstraction_stripping_invariance_laundering": SemanticCarrierSpec(
        vector="abstraction_stripping_invariance_laundering",
        category="NOVEL:scope_laundering",
        gate_name="global_semantic_abstraction_transfer_carrier",
        detector=detect_abstraction_transfer,
        review_role="TRANSFER_SCOPE_AUDITOR",
        reason="an abstract/general transfer claim is supported by concrete proxy constants or domain labels",
    ),
    "selective_rigor_displacement": SemanticCarrierSpec(
        vector="selective_rigor_displacement",
        category="NOVEL:rigor_displacement",
        gate_name="global_semantic_selective_rigor_carrier",
        detector=detect_selective_rigor,
        review_role="DECISIVE_STEP_RIGOR_AUDITOR",
        reason="rigor is concentrated on scaffolding, bookkeeping, or internal arithmetic while the central claim remains untested",
    ),
}


def detect_semantic_carriers(thesis_text: str, evidence_text: str, test_model_text: str) -> list[SemanticCarrierSpec]:
    return [
        spec
        for spec in SEMANTIC_CARRIER_SPECS.values()
        if spec.detector(thesis_text or "", evidence_text or "", test_model_text or "")
    ]


def _gate(
    name: str,
    passed: bool,
    actual: str | None,
    threshold: str | None,
    reason: str,
    *,
    penalty: int = 0,
    hard_fail: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "actual": actual,
        "threshold": threshold,
        "reason": reason,
        "penalty": penalty,
        "hard_fail": hard_fail,
        "source": "semantic_gaming_carrier",
    }


def run_semantic_gaming_carrier_gates(
    project_dir: Path,
    rubric_data: dict[str, Any] | None = None,
    thesis_text: str | None = None,
    evidence_text: str | None = None,
) -> list[dict[str, Any]]:
    rubric_data = rubric_data or {}
    name = "global_semantic_gaming_carrier"

    if rubric_data.get("disable_semantic_gaming_carrier"):
        reason = str(rubric_data.get("disable_semantic_gaming_carrier_reason") or "").strip()
        if not reason:
            return [
                _gate(
                    name,
                    False,
                    "disabled_without_reason",
                    "non-empty disable_semantic_gaming_carrier_reason",
                    "disable_semantic_gaming_carrier requires an explicit reason",
                    hard_fail=True,
                )
            ]
        return [_gate(name, True, "disabled", "explicit disable reason", f"DISABLED by rubric config; reason: {reason}")]

    test_model_path = Path(project_dir) / "test_model.py"
    try:
        test_model_text = test_model_path.read_text(encoding="utf-8") if test_model_path.exists() else ""
    except Exception:
        test_model_text = ""

    findings = detect_semantic_carriers(thesis_text or "", evidence_text or "", test_model_text)
    if not findings:
        return [_gate(name, True, "[]", "no semantic gaming carrier", "no semantic gaming carrier selected")]

    return [
        _gate(
            spec.gate_name,
            False,
            spec.vector,
            "semantic risk must be explicitly reviewed",
            f"{spec.category}: {spec.reason}. Route to {spec.review_role}.",
            penalty=-100,
            hard_fail=True,
        )
        for spec in findings
    ]


def _selftest() -> int:
    fails: list[str] = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    repo = next((p for p in Path(__file__).resolve().parents if (p / ".git").exists()), Path("."))
    fixtures = {
        "scope_overclaim_local_to_systemic": repo
        / "benchmarks"
        / "constraint_memory"
        / "stage1_ood"
        / "local_gate_whole_system_overclaim",
        "abstraction_stripping_invariance_laundering": repo
        / "benchmarks"
        / "constraint_memory"
        / "specimens"
        / "ood"
        / "domain_leakage_logistics",
        "selective_rigor_displacement": repo
        / "benchmarks"
        / "constraint_memory"
        / "claim_test_mismatch"
        / "selective_rigor_recursive_bayesian",
    }
    for vector, root in fixtures.items():
        thesis = (root / "thesis.md").read_text(encoding="utf-8")
        evidence = (root / "evidence.txt").read_text(encoding="utf-8")
        test_model = (root / "test_model.py").read_text(encoding="utf-8")
        found = {spec.vector for spec in detect_semantic_carriers(thesis, evidence, test_model)}
        ok(f"selects semantic carrier: {vector}", vector in found)

    benign = "This bounded local parser maps received status tokens to route labels."
    ok("benign local disclaimer does not route", detect_semantic_carriers(benign, "", "def f():\n    return True\n") == [])
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_selftest())
