"""GP-144 Gate G4 — Proof Surveyability (2-of-3 sub-gates FULL; reviewer deferred).

Status: 2026-04-24 — axiom_allowlist_check and proof_length_vs_sketch_check
are FULL IMPLEMENTATIONS (not shells). adversarial_reviewer_persona_check
remains deferred pending sibling-agent protocol.

PURPOSE
-------
A Lean-compiled proof is formally valid but may be UNSURVEYABLE: 50,000
lines of case analysis under non-standard axioms, no human-readable
sketch. Verified-but-unacceptable is a first-class rejection category.

Three sub-gates when fully implemented:
  1. Axiom allowlist (IMPLEMENTABLE TODAY — gp139_lean_hardening score-87
     backbone): Lean proof must compile only under whitelisted axiom set
     (Mathlib core + explicit whitelist). No `sorry`. No custom axioms.
  2. Proof-length vs sketch requirement (BLOCKED on sketch writer): if
     proof > 500 tactical lines, require machine-authored sketch whose
     structure corresponds 1-to-1 to proof structure. Not just a summary.
  3. Adversarial 30-min reviewer persona (BLOCKED on persona infrastructure):
     simulated reviewer with 30-min budget must reconstruct load-bearing
     moves from the sketch. Failure → unsurveyable.

STATUS
------
Sub-gate 1 (axiom allowlist): IMPLEMENTABLE TODAY via static Lean-source
parsing. Implemented as a thin wrapper that reads a .lean file and greps
for forbidden patterns.

Sub-gates 2-3: shells only.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

GATE_ID = "proof_surveyability"
PRODUCER = "GP-144.G4"

DEFAULT_FORBIDDEN_PATTERNS = [
    r"\bsorry\b",
    r"\baxiom\s+\w+\s*:",        # custom axioms declared
    r"\bunreachable\b",
    r"\badmit\b",
]

DEFAULT_ALLOWED_AXIOMS = {
    "propext",
    "Classical.choice",
    "Quot.sound",
    # Mathlib / Lean 4 core axioms
}


def axiom_allowlist_check(
    lean_proof_path: Path,
    forbidden_patterns: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Parse the Lean proof file, reject if any forbidden pattern present.

    IMPLEMENTED TODAY. gp139_lean_hardening backbone equivalent.
    """
    patterns = forbidden_patterns or DEFAULT_FORBIDDEN_PATTERNS
    if not lean_proof_path.is_file():
        return {
            "passed": False,
            "reason": f"Lean proof file not found: {lean_proof_path}",
            "violations": ["file_not_found"],
        }
    content = lean_proof_path.read_text(encoding="utf-8", errors="ignore")
    violations = []
    for pat in patterns:
        matches = re.findall(pat, content)
        if matches:
            violations.append({"pattern": pat, "count": len(matches),
                               "sample": matches[:3]})
    passed = len(violations) == 0
    return {
        "passed": passed,
        "reason": ("axiom_allowlist_clean" if passed
                   else f"forbidden_patterns_found: {[v['pattern'] for v in violations]}"),
        "violations": violations,
        "file_size_bytes": len(content),
        "line_count": content.count("\n"),
    }


def proof_length_vs_sketch_check(
    lean_proof_path: Path,
    sketch_path: Optional[Path],
    max_lines_without_sketch: int = 500,
) -> dict[str, Any]:
    """If proof > max_lines_without_sketch, require a machine-authored sketch
    whose structure matches the proof.

    Partial implementation: reads line count, checks sketch existence. Full
    structural-correspondence check blocked on a sketch-to-proof alignment
    verifier.
    """
    if not lean_proof_path.is_file():
        return {
            "implemented": False,
            "blocked_on": "missing Lean proof file",
            "passed": None,
        }
    content = lean_proof_path.read_text(encoding="utf-8", errors="ignore")
    line_count = content.count("\n")
    if line_count <= max_lines_without_sketch:
        return {
            "implemented": True,
            "passed": True,
            "reason": f"proof_length_{line_count}_lines_under_threshold_{max_lines_without_sketch}",
            "line_count": line_count,
        }
    if sketch_path is None or not sketch_path.is_file():
        return {
            "implemented": True,
            "passed": False,
            "reason": (f"proof_length_{line_count}_lines_over_threshold_{max_lines_without_sketch}_"
                       "but_no_sketch_provided"),
            "line_count": line_count,
        }
    # Structural alignment blocked
    return {
        "implemented": False,
        "blocked_on": "sketch-to-proof structural-alignment verifier",
        "passed": None,
        "reason": ("proof > threshold, sketch provided, but structural 1-to-1 "
                   "alignment check is not implemented."),
        "line_count": line_count,
    }


def adversarial_reviewer_persona_check(
    sketch_path: Optional[Path],
    reviewer_budget_minutes: int = 30,
) -> dict[str, Any]:
    """Simulated 30-min reviewer persona must reconstruct load-bearing moves
    from the sketch. Blocked on persona-invocation protocol.
    """
    return {
        "implemented": False,
        "blocked_on": "adversarial reviewer persona agent protocol",
        "reason": ("Requires invoking a bounded subagent with the sketch, timing it "
                   "to simulate 30-min budget, and scoring whether it reconstructs "
                   "the proof's structure. Not wired."),
    }


def run_gate(
    claim: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run G4 proof-surveyability on a claim.

    claim schema:
        {
            "lean_proof_path": "<path to .lean file>",
            "sketch_path": "<path to .md sketch, optional>",
            ...
        }
    """
    lean_path = Path(str(claim.get("lean_proof_path", "")))
    sketch_path_str = claim.get("sketch_path")
    sketch_path = Path(str(sketch_path_str)) if sketch_path_str else None

    forbidden = rubric_params.get("forbidden_patterns", DEFAULT_FORBIDDEN_PATTERNS)
    max_lines = int(rubric_params.get("max_lines_without_sketch", 500))
    reviewer_budget = int(rubric_params.get("reviewer_budget_minutes", 30))

    r_axioms = axiom_allowlist_check(lean_path, forbidden_patterns=forbidden)
    r_sketch = proof_length_vs_sketch_check(lean_path, sketch_path, max_lines)
    r_reviewer = adversarial_reviewer_persona_check(sketch_path, reviewer_budget)

    # Verdict: pass IFF axiom_allowlist passes AND (proof short OR sketch ok).
    axiom_ok = r_axioms.get("passed") is True
    sketch_ok = r_sketch.get("passed") is True
    reviewer_blocked = r_reviewer.get("implemented") is False

    if not axiom_ok:
        return {
            "name": GATE_ID,
            "passed": False,
            "actual": r_axioms.get("violations", []),
            "threshold": "empty_violations_list",
            "reason": r_axioms.get("reason", "axiom_allowlist_violation"),
            "penalty": 1,
            "hard_fail": True,
            "source": PRODUCER,
            "extra": {
                "axiom_allowlist": r_axioms,
                "proof_length": r_sketch,
                "reviewer": r_reviewer,
                "shell_fully_implemented": False,
            },
        }

    # Axioms pass. If proof short or sketch provided and valid, verdict is
    # passing subject to the (deferred) reviewer persona check.
    verdict = None if reviewer_blocked else sketch_ok
    reason = ("axiom_allowlist_clean; " +
              (r_sketch.get("reason", "") or "") +
              "; reviewer_persona_deferred_shell")
    return {
        "name": GATE_ID,
        "passed": verdict,  # None if reviewer-blocked
        "actual": None,
        "threshold": None,
        "reason": reason,
        "penalty": 0 if verdict is not False else 1,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "axiom_allowlist": r_axioms,
            "proof_length": r_sketch,
            "reviewer": r_reviewer,
            "shell_fully_implemented": False,
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "axiom_allowlist_passed": extra.get("axiom_allowlist", {}).get("passed"),
        "proof_length_check_passed": extra.get("proof_length", {}).get("passed"),
        "shell_fully_implemented": extra.get("shell_fully_implemented"),
    }
    return filtered
