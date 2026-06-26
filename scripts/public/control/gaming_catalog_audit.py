#!/usr/bin/env python3
"""Validate the public gaming catalog against the live registry shape.

This is not the promotion gate for new vectors; that lives in
``gaming_vector_meta_runner``. This audit checks the reader-facing contract:
the public catalog, registry, promotion receipts, and routing map must agree on
what is paper lineage, what is live engineering registry, and what evidence is
actually present.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CATALOG = REPO / "docs/gaming_behavior_catalog.md"
MAP = REPO / "docs/concepts/gaming_behavior_catalog_map.md"
REGISTRY = REPO / "analytics/public/queries/gaming_vector_catalog.jsonl"
PROMOTION_ROOT = REPO / "analytics/public/queries/gaming_vector_promotion_evidence"
PAPER_README = REPO / "papers/cognitive-camouflage/README.md"
PAPER_DRAFT = REPO / "papers/cognitive-camouflage/draft.md"
ROOT_PAPER_README = REPO / "cognitive-camouflage/README.md"
ROOT_PAPER_DRAFT = REPO / "cognitive-camouflage/draft.md"

ALLOWED_STATUSES = {"open", "gated", "wontfix", "deferred"}
ALLOWED_EVIDENCE_TIERS = {
    "registry_row",
    "reproduced_incident",
    "promotion_receipt",
    "runtime_gate",
    "external_reproduction",
}

ORIGINAL_NINE = (
    "Severity Averaging",
    "Tolerance Abuse",
    "Stubbed Implementation",
    "Step-Index Leakage",
    "Claim-Test Mismatch",
    "Fudge-Factor Patching",
    "Partial-Domain Miscalibration",
    "Parameter Overfitting",
    "Weak Baseline",
)

EXECUTABLE_ANCHOR_FIXTURES = {
    "undeclared_parameters_body": REPO
    / "benchmarks/constraint_memory/derived_subtle/undeclared_parameters_body/test_model.py",
    "definitional_tautology_self_confirming_metric": REPO
    / "benchmarks/constraint_memory/specimens/bad/self_referential_falsification/test_model.py",
    "fabricated_calibration_set_threshold_laundering": REPO
    / "benchmarks/constraint_memory/derived_subtle/threshold_rigging_submerged/test_model.py",
    "assumption_as_evidence_relabeling": REPO
    / "benchmarks/constraint_memory/auxiliary_historical/central_station_hypothetical_target_laundering/test_model.py",
    "receipt_replay_absence_static_asserts": REPO
    / "benchmarks/constraint_memory/derived_subtle/receipt_replay_absence/test_model.py",
}

BENIGN_GATE_CONTROL = "def f(x):\n    return x + 1\n\nassert f(2) == 3\n"

REQUIRED_CATALOG_PHRASES = (
    "How to read this as a field guide",
    "Name Policy",
    "Canonical Invariant Map",
    "Historical alias",
    "Earlier artifacts may use these aliases",
    "Start Here: 9 Ways LLMs Game Their Own Evaluations",
    "Part II: Mined Cross-Domain Vectors",
    "original 9 have paper benchmark lineage",
    "keeping them separate from the original paper's benchmark claim",
    "NOT a complete taxonomy",
    "NOT MECE",
)

REQUIRED_INVARIANT_LABELS = (
    "criticality-dilution break",
    "precision-invariance break",
    "mechanism-responsiveness break",
    "data-dependence break",
    "claim-test equivalence break",
    "dimensional-invariance break",
    "probability-bounds break",
    "parameter-provenance break",
    "comparator-fairness break",
)

REQUIRED_HISTORICAL_ALIASES = (
    "Blame Shield",
    "Axiom Bundle Dilution",
    "Float Masking",
    "Adversarial Precision Truncation",
    "Fake AutoDiff",
    "Interface Deception",
    "Cooked Book RNG",
    "Environment Rigging",
    "Assert Narrowing",
    "Range Hardcoding",
    "Dimensional Correction Factor",
    "Unit Masking",
    "Unidirectional Decay",
    "Formula Incoherence",
    "Gravity Constant Fabrication",
    "Ungrounded Coupling",
    "Comparator Engineering",
)

REQUIRED_MAP_PHRASES = (
    "Precedence when files disagree",
    "Current Coverage Snapshot",
    "Layer Ownership",
    "Name Policy",
    "Invariant Axis",
    "historical-alias column",
    "File Contract",
    "SOP",
    "Do not present the 18 live rows as a complete taxonomy",
)

REQUIRED_PAPER_BOUNDARY_PHRASES = (
    "historical run-output aliases",
    "canonical public names",
    "not part of the benchmarked 9-strategy claim",
)


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    findings: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append(f"{path.relative_to(REPO)}:{line_no}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict):
            findings.append(f"{path.relative_to(REPO)}:{line_no}: row is not an object")
            continue
        rows.append(row)
    return rows, findings


def _map_declared_registry_count(text: str) -> int | None:
    match = re.search(r"currently has\s+(\d+)\s+registry rows", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _has_phrase(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def _validate_registry(rows: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    names: list[str] = []
    required = ("name", "status", "substrate", "mechanism", "severity", "category")

    for idx, row in enumerate(rows, start=1):
        label = str(row.get("name") or f"row_{idx}")
        names.append(label)
        for key in required:
            if not str(row.get(key, "")).strip():
                findings.append(f"registry row {label}: missing `{key}`")
        tiers_raw = row.get("evidence_tiers")
        if not isinstance(tiers_raw, list) or not tiers_raw:
            findings.append(f"registry row {label}: missing non-empty `evidence_tiers` list")
            tiers: set[str] = set()
        else:
            tiers = {str(item) for item in tiers_raw}
            unsupported = sorted(tiers - ALLOWED_EVIDENCE_TIERS)
            if unsupported:
                findings.append(
                    f"registry row {label}: unsupported evidence tier(s) {unsupported}"
                )
            if "registry_row" not in tiers:
                findings.append(f"registry row {label}: evidence_tiers lacks `registry_row`")
        status = row.get("status")
        if status not in ALLOWED_STATUSES:
            findings.append(f"registry row {label}: unsupported status `{status}`")
        if status == "gated" and not (
            str(row.get("already_gated_by", "")).strip()
            or str(row.get("gate_name", "")).strip()
            or str(row.get("proposed_gate", "")).strip()
        ):
            findings.append(f"registry row {label}: gated row lacks gate/proposed gate")
        if status == "gated" and "runtime_gate" not in tiers:
            findings.append(f"registry row {label}: gated row lacks `runtime_gate` tier")
        has_incident_evidence = bool(
            str(row.get("evidence", "")).strip()
            or str(row.get("reproduce_result", "")).strip()
        )
        if has_incident_evidence and "reproduced_incident" not in tiers:
            findings.append(
                f"registry row {label}: exposing evidence lacks `reproduced_incident` tier"
            )

        promotion = str(row.get("promotion_evidence", "")).strip()
        if promotion:
            if "promotion_receipt" not in tiers:
                findings.append(
                    f"registry row {label}: promotion evidence lacks `promotion_receipt` tier"
                )
            evidence_path = (REPO / promotion).resolve()
            try:
                evidence_path.relative_to(REPO)
            except ValueError:
                findings.append(f"registry row {label}: promotion evidence escapes repo")
                continue
            if not evidence_path.exists():
                findings.append(f"registry row {label}: missing promotion evidence {promotion}")
                continue
            try:
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                findings.append(f"registry row {label}: invalid promotion evidence JSON: {exc}")
                continue
            if evidence.get("vector") != row.get("name"):
                findings.append(f"registry row {label}: promotion evidence vector mismatch")
            if evidence.get("substrate") != row.get("substrate"):
                findings.append(f"registry row {label}: promotion evidence substrate mismatch")
            if evidence.get("promotion_recommendation") is not True:
                findings.append(f"registry row {label}: promotion evidence lacks positive recommendation")
            if evidence.get("scope", {}).get("vector_only") is not True:
                findings.append(f"registry row {label}: promotion evidence is not scoped vector-only")

    for name, count in Counter(names).items():
        if count > 1:
            findings.append(f"registry duplicate vector name: {name}")
    return findings


def _validate_catalog(text: str) -> list[str]:
    findings: list[str] = []
    for phrase in REQUIRED_CATALOG_PHRASES:
        if not _has_phrase(text, phrase):
            findings.append(f"catalog missing phrase: {phrase}")
    for label in REQUIRED_INVARIANT_LABELS:
        if label not in text:
            findings.append(f"catalog missing invariant label: {label}")
    for alias in REQUIRED_HISTORICAL_ALIASES:
        if alias not in text:
            findings.append(f"catalog missing historical alias: {alias}")
    for idx, name in enumerate(ORIGINAL_NINE, start=1):
        heading = f"### {idx}. {name}"
        if heading not in text:
            findings.append(f"catalog missing original-nine heading: {heading}")
    return findings


def _validate_map(text: str, registry_count: int) -> list[str]:
    findings: list[str] = []
    for phrase in REQUIRED_MAP_PHRASES:
        if not _has_phrase(text, phrase):
            findings.append(f"catalog map missing phrase: {phrase}")
    declared = _map_declared_registry_count(text)
    if declared is None:
        findings.append("catalog map does not declare current registry row count")
    elif declared != registry_count:
        findings.append(
            f"catalog map registry count drift: declared {declared}, actual {registry_count}"
        )
    return findings


def _validate_paper_boundaries() -> list[str]:
    findings: list[str] = []
    required_targets = {
        "papers/cognitive-camouflage/README.md": PAPER_README,
    }
    optional_targets = {
        "cognitive-camouflage/README.md": ROOT_PAPER_README,
    }
    for label, path in required_targets.items():
        if not path.exists():
            findings.append(f"missing cognitive-camouflage boundary file: {label}")
            continue
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        missing = [
            phrase
            for phrase in REQUIRED_PAPER_BOUNDARY_PHRASES
            if phrase not in text
        ]
        if missing:
            findings.append(f"{label}: missing paper/catalog boundary phrase(s) {missing}")
    for label, path in optional_targets.items():
        if not path.exists():
            continue
        text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
        missing = [
            phrase
            for phrase in REQUIRED_PAPER_BOUNDARY_PHRASES
            if phrase not in text
        ]
        if missing:
            findings.append(f"{label}: missing paper/catalog boundary phrase(s) {missing}")
    return findings


def _paper_boundary_file_count() -> int:
    paths = (PAPER_README, PAPER_DRAFT, ROOT_PAPER_README, ROOT_PAPER_DRAFT)
    return sum(1 for path in paths if path.exists())


def _validate_executable_anchors(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    findings: list[str] = []
    checked_vectors: list[str] = []
    checked_gates: list[str] = []
    registry_by_name = {str(row.get("name", "")): row for row in rows}

    try:
        from ztare.gates.autoresearch_gaming_gates import (
            AUTORESEARCH_GAMING_DETECTORS,
            detect_autoresearch_gaming_vectors,
            run_autoresearch_gaming_gates,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "checked_vectors": checked_vectors,
            "checked_gates": checked_gates,
            "benign_control_passed": False,
        }, [f"could not import executable gaming gates: {exc}"]

    for vector, path in EXECUTABLE_ANCHOR_FIXTURES.items():
        row = registry_by_name.get(vector)
        if row is None:
            findings.append(f"executable anchor {vector}: missing registry row")
            continue
        if row.get("status") != "gated":
            findings.append(f"executable anchor {vector}: registry row is not gated")
        if "runtime_gate" not in set(row.get("evidence_tiers") or []):
            findings.append(f"executable anchor {vector}: registry row lacks runtime_gate tier")

        spec = AUTORESEARCH_GAMING_DETECTORS.get(vector)
        if spec is None:
            findings.append(f"executable anchor {vector}: missing detector spec")
            continue
        if not path.exists():
            findings.append(
                f"executable anchor {vector}: missing fixture {path.relative_to(REPO)}"
            )
            continue

        source = path.read_text(encoding="utf-8")
        detected = {detector.vector for detector in detect_autoresearch_gaming_vectors(source)}
        if vector not in detected:
            findings.append(f"executable anchor {vector}: detector did not fire on fixture")
            continue

        gate_results = run_autoresearch_gaming_gates(path.parent)
        gate_failed = any(
            result.get("name") == spec.gate_name
            and result.get("actual") == vector
            and result.get("hard_fail") is True
            and result.get("passed") is False
            for result in gate_results
        )
        if not gate_failed:
            findings.append(
                f"executable anchor {vector}: gate {spec.gate_name} did not hard-fail fixture"
            )
            continue

        checked_vectors.append(vector)
        checked_gates.append(spec.gate_name)

    benign_control_passed = False
    with tempfile.TemporaryDirectory(prefix="ztare_gaming_catalog_audit_") as tmp:
        project_dir = Path(tmp)
        (project_dir / "test_model.py").write_text(BENIGN_GATE_CONTROL, encoding="utf-8")
        benign_results = run_autoresearch_gaming_gates(project_dir)
        benign_control_passed = bool(benign_results) and all(
            result.get("passed") is True and result.get("hard_fail") is not True
            for result in benign_results
        )
    if not benign_control_passed:
        findings.append("executable anchors: benign gate control did not pass cleanly")

    return {
        "checked_vectors": sorted(checked_vectors),
        "checked_gates": sorted(checked_gates),
        "benign_control_passed": benign_control_passed,
    }, findings


def build_payload() -> dict[str, Any]:
    findings: list[str] = []
    for path in (CATALOG, MAP, REGISTRY, PROMOTION_ROOT):
        if not path.exists():
            findings.append(f"missing required path: {path.relative_to(REPO)}")

    rows: list[dict[str, Any]] = []
    if REGISTRY.exists():
        rows, jsonl_findings = _load_jsonl(REGISTRY)
        findings.extend(jsonl_findings)
        findings.extend(_validate_registry(rows))

    catalog_text = CATALOG.read_text(encoding="utf-8") if CATALOG.exists() else ""
    map_text = MAP.read_text(encoding="utf-8") if MAP.exists() else ""
    findings.extend(_validate_catalog(catalog_text))
    findings.extend(_validate_map(map_text, len(rows)))
    findings.extend(_validate_paper_boundaries())
    executable_anchors, executable_findings = _validate_executable_anchors(rows)
    findings.extend(executable_findings)

    status_counts = Counter(str(row.get("status", "")) for row in rows)
    substrate_counts = Counter(str(row.get("substrate", "")) for row in rows)
    evidence_tier_counts = Counter(
        str(tier)
        for row in rows
        for tier in (row.get("evidence_tiers") if isinstance(row.get("evidence_tiers"), list) else [])
    )
    promotion_count = sum(1 for row in rows if str(row.get("promotion_evidence", "")).strip())

    return {
        "ok": not findings,
        "registry_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "substrate_counts": dict(sorted(substrate_counts.items())),
        "evidence_tier_counts": dict(sorted(evidence_tier_counts.items())),
        "promotion_evidence_rows": promotion_count,
        "original_nine_headings": len(ORIGINAL_NINE),
        "paper_boundary_files": _paper_boundary_file_count(),
        "executable_anchor_count": len(executable_anchors["checked_vectors"]),
        "executable_anchor_vectors": executable_anchors["checked_vectors"],
        "executable_anchor_gates": executable_anchors["checked_gates"],
        "executable_anchor_benign_control_passed": executable_anchors[
            "benign_control_passed"
        ],
        "finding_count": len(findings),
        "findings": findings,
    }


def main() -> int:
    payload = build_payload()
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["ok"]:
        raise SystemExit("gaming catalog audit failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
