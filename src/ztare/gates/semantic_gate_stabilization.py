from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SelfReferenceEvidence:
    target_claim: str = ""
    asserted_variable: str = ""
    asserted_variable_origin: str = "unknown"
    independent_grounding_present: bool = False
    test_recomputes_thesis_authored_target: bool = False
    causal_variable_perturbed: bool = False
    load_bearing_claim_directly_tested: bool = False
    local_component_scope_disclaimer_present: bool = False
    whole_system_availability_claim_present: bool = False
    verifies_authored_mapping_only: bool = False
    evidence_lines: list[str] = field(default_factory=list)
    counterevidence_lines: list[str] = field(default_factory=list)
    confidence: str = "low"


@dataclass
class UnresolvedDiagnosis:
    required_clear_conditions_unmet: list[str] = field(default_factory=list)
    potential_falsification_unverified: bool = False


@dataclass
class DiagnosticSummary:
    total_unresolved_gates_processed: int = 0
    unmet_clear_condition_counts: dict[str, int] = field(default_factory=dict)
    potential_falsification_unverified_count: int = 0


@dataclass
class SemanticGateAnalysis:
    semantic_gate_status: str
    proof_is_self_referential: bool
    self_reference_rule_fired: str
    self_reference_quorum_used: bool
    self_reference_evidence: SelfReferenceEvidence
    unresolved_diagnosis: UnresolvedDiagnosis | None = None
    diagnostic_summary: DiagnosticSummary | None = None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_origin(value: Any) -> str:
    origin = str(value or "unknown").strip().lower()
    if origin in {"internal", "external", "mixed", "unknown"}:
        return origin
    return "unknown"


def _normalize_confidence(value: Any) -> str:
    confidence = str(value or "low").strip().lower()
    if confidence in {"high", "medium", "low"}:
        return confidence
    return "low"


def normalize_self_reference_evidence(raw: Any) -> SelfReferenceEvidence:
    raw = raw if isinstance(raw, dict) else {}
    return SelfReferenceEvidence(
        target_claim=str(raw.get("target_claim", "") or ""),
        asserted_variable=str(raw.get("asserted_variable", "") or ""),
        asserted_variable_origin=_normalize_origin(raw.get("asserted_variable_origin")),
        independent_grounding_present=_as_bool(raw.get("independent_grounding_present")),
        test_recomputes_thesis_authored_target=_as_bool(
            raw.get("test_recomputes_thesis_authored_target")
        ),
        causal_variable_perturbed=_as_bool(raw.get("causal_variable_perturbed")),
        load_bearing_claim_directly_tested=_as_bool(
            raw.get("load_bearing_claim_directly_tested")
        ),
        local_component_scope_disclaimer_present=_as_bool(
            raw.get("local_component_scope_disclaimer_present")
        ),
        whole_system_availability_claim_present=_as_bool(
            raw.get("whole_system_availability_claim_present")
        ),
        verifies_authored_mapping_only=_as_bool(raw.get("verifies_authored_mapping_only")),
        evidence_lines=_as_str_list(raw.get("evidence_lines")),
        counterevidence_lines=_as_str_list(raw.get("counterevidence_lines")),
        confidence=_normalize_confidence(raw.get("confidence")),
    )


def derive_self_reference_gate(
    raw_evidence: Any, raw_flag: bool = False
) -> SemanticGateAnalysis:
    evidence = normalize_self_reference_evidence(raw_evidence)

    hard_self_reference = (
        evidence.asserted_variable_origin in {"internal", "mixed"}
        and not evidence.independent_grounding_present
        and evidence.test_recomputes_thesis_authored_target
    )
    safe_harbor_local_mapping = (
        evidence.local_component_scope_disclaimer_present
        and not evidence.whole_system_availability_claim_present
        and evidence.verifies_authored_mapping_only
    )
    claim_test_mismatch = (
        not evidence.load_bearing_claim_directly_tested
        and not evidence.causal_variable_perturbed
    )
    low_confidence = evidence.confidence == "low"
    unresolved_unmet: list[str] = []
    if not evidence.load_bearing_claim_directly_tested:
        unresolved_unmet.append("load_bearing_claim_directly_tested")
    if not evidence.independent_grounding_present:
        unresolved_unmet.append("independent_grounding_present")
    if not evidence.causal_variable_perturbed:
        unresolved_unmet.append("causal_variable_perturbed")
    if evidence.test_recomputes_thesis_authored_target:
        unresolved_unmet.append("independent_falsification_environment_present")

    potential_falsification_unverified = bool(
        evidence.counterevidence_lines and not evidence.load_bearing_claim_directly_tested
    )

    if hard_self_reference and safe_harbor_local_mapping:
        unresolved_unmet.append("safe_harbor_local_mapping_requires_manual_review")
        return SemanticGateAnalysis(
            semantic_gate_status="unresolved",
            proof_is_self_referential=False,
            self_reference_rule_fired="safe_harbor_downgrade",
            self_reference_quorum_used=False,
            self_reference_evidence=evidence,
            unresolved_diagnosis=UnresolvedDiagnosis(
                required_clear_conditions_unmet=unresolved_unmet,
                potential_falsification_unverified=potential_falsification_unverified,
            ),
        )

    if hard_self_reference:
        return SemanticGateAnalysis(
            semantic_gate_status="resolved",
            proof_is_self_referential=True,
            self_reference_rule_fired="hard_self_reference",
            self_reference_quorum_used=False,
            self_reference_evidence=evidence,
        )

    if claim_test_mismatch or low_confidence:
        return SemanticGateAnalysis(
            semantic_gate_status="unresolved",
            proof_is_self_referential=False,
            self_reference_rule_fired="claim_test_mismatch_escalation",
            self_reference_quorum_used=False,
            self_reference_evidence=evidence,
            unresolved_diagnosis=UnresolvedDiagnosis(
                required_clear_conditions_unmet=unresolved_unmet,
                potential_falsification_unverified=potential_falsification_unverified,
            ),
        )

    # If the structured evidence is clean, resolved, and does not fire the hard rule,
    # prefer the structured result over the raw boolean to avoid single-boolean drift.
    return SemanticGateAnalysis(
        semantic_gate_status="resolved",
        proof_is_self_referential=False,
        self_reference_rule_fired="none",
        self_reference_quorum_used=False,
        self_reference_evidence=evidence,
    )


def aggregate_unresolved_diagnoses(
    analyses: list[SemanticGateAnalysis],
) -> DiagnosticSummary:
    unmet_counter: Counter[str] = Counter()
    unresolved_count = 0
    potential_unverified_count = 0

    for analysis in analyses:
        if analysis.semantic_gate_status != "unresolved" or analysis.unresolved_diagnosis is None:
            continue
        unresolved_count += 1
        for item in analysis.unresolved_diagnosis.required_clear_conditions_unmet:
            unmet_counter[item] += 1
        if analysis.unresolved_diagnosis.potential_falsification_unverified:
            potential_unverified_count += 1

    return DiagnosticSummary(
        total_unresolved_gates_processed=unresolved_count,
        unmet_clear_condition_counts=dict(unmet_counter),
        potential_falsification_unverified_count=potential_unverified_count,
    )


def persist_semantic_gate_analysis(
    project_dir: Path, analysis: SemanticGateAnalysis
) -> DiagnosticSummary:
    observations_path = project_dir / "semantic_gate_observations.jsonl"
    existing: list[SemanticGateAnalysis] = []
    if observations_path.exists():
        for line in observations_path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            existing.append(
                SemanticGateAnalysis(
                    semantic_gate_status=row["semantic_gate_status"],
                    proof_is_self_referential=row["proof_is_self_referential"],
                    self_reference_rule_fired=row["self_reference_rule_fired"],
                    self_reference_quorum_used=row.get("self_reference_quorum_used", False),
                    self_reference_evidence=normalize_self_reference_evidence(
                        row.get("self_reference_evidence", {})
                    ),
                    unresolved_diagnosis=UnresolvedDiagnosis(**row["unresolved_diagnosis"])
                    if row.get("unresolved_diagnosis")
                    else None,
                )
            )

    existing.append(analysis)
    payload = asdict(analysis)
    payload["recorded_at"] = int(time.time())
    with observations_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")

    summary = aggregate_unresolved_diagnoses(existing)
    (project_dir / "semantic_gate_summary.json").write_text(
        json.dumps(asdict(summary), indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
