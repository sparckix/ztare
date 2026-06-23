"""GP-211 — Lean-proof substrate runner.

Invoked from `test_thesis.py` (or any iteration driver) when the rubric's
`cage_meta.substrate_class == "lean_proof"`. Replaces the standard
`test_model.py` execution path with a real Lean compile + axiom audit, and
formats a structured "LEAN UNIT TEST RESULT" string the judge sees in
place of the tautological "✅ PASS: All discriminators passed" string.

Why this exists
---------------
GP-211 iter-1 (score 93) and iter-2 (score 95) both shipped a thesis that:
  - Cited two hallucinated Mathlib v4.30 lemmas in PROSE.
  - Wrote a Python tautology `I_model() -> 0.5` to `test_model.py`.
  - Had no ```lean fenced block at all.

The judge (gpt4.1) scored Lean-shaped prose + the tautology PASS as
"validated." This module severs that loop: when the rubric declares the
substrate is Lean, NO outcome is possible without `lake build` succeeding.

Public surface
--------------
- `is_lean_proof_substrate(rubric: dict) -> bool`
- `run_lean_substrate_iteration(project_dir, rubric, iteration) -> dict`
- `format_judge_facing_summary(result: dict) -> str`
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ztare.gates.lean_proof_gate import run_lean_proof_gate


# Repo root: <repo>/src/ztare/validator/lean_substrate_runner.py → parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ZTARE_PROOFS_ROOT = _REPO_ROOT / "ztare_proofs"


def is_lean_proof_substrate(rubric: dict[str, Any]) -> bool:
    """True iff the rubric routes to the Lean-proof substrate harness.

    The contract: any rubric whose `cage_meta.substrate_class == "lean_proof"`
    bypasses the standard `test_model.py` execution path. Other substrate
    classes (and rubrics with no `cage_meta`) are unaffected.
    """
    if not isinstance(rubric, dict):
        return False
    cage_meta = rubric.get("cage_meta") or {}
    if not isinstance(cage_meta, dict):
        return False
    return cage_meta.get("substrate_class") == "lean_proof"


def run_lean_substrate_iteration(
    project_dir: Path,
    rubric: dict[str, Any],
    iteration: int,
    ztare_proofs_root: Path | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run the Lean-proof gate for one iteration.

    Reads `project_dir/thesis.md`, dispatches to `run_lean_proof_gate`, and
    returns a result shaped to slot into the existing eval pipeline:

      {
        "test_suite_status": "pass" | "fail_assert" | "fail_runtime" | "missing",
        "test_result_summary": "<judge-facing string>",
        "lean_proof_gate": {<full gate dict>},
      }

    `test_suite_status` semantics map to the existing FAIL_ASSERT vs.
    FAIL_RUNTIME categories:
      - gate_passed → "pass"
      - compiled but axiom_audit_passed=False or forbidden_tokens → "fail_assert"
        (the Lean code IS correct shape but is smuggling axioms / sorry)
      - compile failed (incl. extracted=False) → "fail_assert"
        (the proof literally does not type-check; this IS substantive falsification)
      - timeout (lake_exit_code == -2) → "fail_runtime"
    """
    project_dir = Path(project_dir)
    thesis_path = project_dir / "thesis.md"
    proofs_root = Path(ztare_proofs_root) if ztare_proofs_root else _DEFAULT_ZTARE_PROOFS_ROOT
    project_slug = project_dir.name

    gate_result = run_lean_proof_gate(
        thesis_path=thesis_path,
        project_slug=project_slug,
        ztare_proofs_root=proofs_root,
        timeout_seconds=timeout_seconds,
    )

    # Map gate verdict → existing test_suite_status taxonomy.
    if gate_result.get("gate_passed"):
        status = "pass"
    elif gate_result.get("lake_exit_code") == -2:
        status = "fail_runtime"
    else:
        # Compile failure, extraction failure, axiom-audit failure, or
        # forbidden-token violation all count as substantive falsification —
        # the thesis is wrong, not the apparatus.
        status = "fail_assert"

    summary = format_judge_facing_summary(gate_result)
    return {
        "test_suite_status": status,
        "test_result_summary": summary,
        "lean_proof_gate": gate_result,
        "iteration": iteration,
    }


def format_judge_facing_summary(gate_result: dict[str, Any]) -> str:
    """Render the LEAN UNIT TEST RESULT block the judge consumes.

    Stable line-oriented format so downstream regex-based parsers (and
    operator skim) can extract individual fields.
    """
    lines = ["LEAN UNIT TEST RESULT"]
    lines.append(f"compiled: {gate_result.get('compiled', False)}")
    lines.append(f"lake_exit_code: {gate_result.get('lake_exit_code', -1)}")
    lines.append(f"compile_duration_s: {gate_result.get('compile_duration_s', 0.0)}")
    lines.append(f"axiom_audit_passed: {gate_result.get('axiom_audit_passed', False)}")
    lines.append(f"extra_axioms: {gate_result.get('extra_axioms', [])}")
    lines.append(f"forbidden_tokens: {gate_result.get('forbidden_tokens', [])}")
    lines.append(f"line_count: {gate_result.get('line_count', 0)}")
    lines.append(f"mathlib_lemma_count: {gate_result.get('mathlib_lemma_count', 0)}")
    lines.append(f"applied_lemmas: {gate_result.get('applied_lemmas', [])}")

    # Verdict marker — preserve the existing FAIL/PASS prose for any judge
    # rubric that pattern-matches on the legacy ✅/❌ prefix, but anchor the
    # actual decision to the LEAN-specific fields above.
    if gate_result.get("gate_passed"):
        lines.append("")
        lines.append("✅ PASS: Lean proof type-checked and axiom audit cleared.")
    else:
        lines.append("")
        lines.append("❌ FAIL: Lean proof did NOT type-check or violated audit.")
        rationale = gate_result.get("rationale") or ""
        if rationale:
            lines.append(f"Reason: {rationale}")
        # Show a tail of stderr so the judge can see the actual lake error.
        stderr = gate_result.get("compile_stderr") or ""
        if stderr.strip():
            lines.append("--- lake stderr (tail) ---")
            lines.append(stderr.strip()[-1500:])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


def _smoke() -> int:
    """Quick CLI: dispatch on GP-211 and print the judge-facing summary."""
    project = _REPO_ROOT / "projects" / "gp211_paper8_lean_proofs"
    rubric = {"cage_meta": {"substrate_class": "lean_proof"}}
    assert is_lean_proof_substrate(rubric)
    assert not is_lean_proof_substrate({})
    assert not is_lean_proof_substrate({"cage_meta": {"substrate_class": "fit"}})
    result = run_lean_substrate_iteration(project, rubric, iteration=0, timeout_seconds=120)
    print(f"test_suite_status: {result['test_suite_status']}")
    print()
    print(result["test_result_summary"])
    return 0 if result["test_suite_status"] in {"pass", "fail_assert", "fail_runtime"} else 1


if __name__ == "__main__":
    raise SystemExit(_smoke())
