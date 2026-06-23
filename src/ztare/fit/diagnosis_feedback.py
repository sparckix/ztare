"""GP-113: Diagnosis-Informed LLM Feedback Loop.

When GP-112 returns PERSIST_GRAMMAR_EXHAUSTED, this module constructs a
diagnosis-informed prompt for a second Phase 1 pass. The LLM sees:
- The champion form (best the deterministic search produced)
- The GP-112 diagnosis (spectral slope, autocorrelation, noise class)
- Explicit instruction to propose forms OUTSIDE the standard grammar

The LLM does what it does well (structural analogy, cross-domain transfer)
informed by what the deterministic system measured.

Usage:
    from ztare.fit.diagnosis_feedback import build_diagnosis_prompt
    prompt = build_diagnosis_prompt(project_dir)
    # Feed to autoresearch_loop as Phase 1b seed
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_diagnosis_prompt(project_dir: Path) -> str | None:
    """Build a diagnosis-informed prompt from GP-112 output.

    Returns a prompt string for the LLM mutator, or None if no diagnosis
    is available (GP-112 did not run or did not PERSIST).
    """
    ms_path = project_dir / "workspace" / "margin_of_safety.json"
    if not ms_path.exists():
        return None

    ms = json.loads(ms_path.read_text(encoding="utf-8"))

    # Only fire on PERSIST
    remediation = ms.get("remediation")
    if not remediation:
        return None
    verdict = remediation.get("verdict", "")
    if "PERSIST" not in verdict:
        return None

    # Extract diagnosis
    champion_expr = ms.get("champion_expression", "unknown")
    champion_params = ms.get("champion_params", {})

    # Spectral characterization
    rc = ms.get("residual_characterization", {})
    spectral_slope = rc.get("spectral_slope", "unknown")
    noise_class = rc.get("noise_class", "unknown")

    # Autocorrelation from tests
    lag1 = "unknown"
    for t in ms.get("tests", []):
        if t.get("test") == "residual_autocorrelation":
            lag1 = t.get("lag1_autocorrelation", "unknown")

    # Extensions tried and failed
    n_tried = remediation.get("candidates_tried", 0)

    # Build the prompt (cold, no domain vocabulary)
    prompt = f"""The deterministic compression found a champion form:
  {champion_expr}
with parameters: {json.dumps({k: round(v, 6) for k, v in champion_params.items()})}

This form passes holdout gates but has thin margin. An automated
margin-of-safety assessment found:
- Residual lag-1 autocorrelation: {lag1}
- Residual spectral slope: {spectral_slope} (noise class: {noise_class})
- {n_tried} single-term additive extensions were tried (loglog, sqrt, exp,
  power, reciprocal, log-squared). NONE reduced the autocorrelation.

The structured residuals are NOT addressable by adding any single smooth
term to the champion. The residual structure may be:
- MULTIPLICATIVE (the champion needs a relative correction, not absolute)
- NON-SMOOTH (the data has discrete jumps or periodicity)
- MULTI-TERM (two or more missing terms interact)
- REGIME-DEPENDENT (different corrections at different scales)

Propose a functional form that addresses the residual structure described
above. You may use any mathematical operation (not limited to the standard
grammar). Include a fit_declaration block. Focus on the STRUCTURAL cause
of the autocorrelation, not on reducing the residual magnitude."""

    return prompt


def build_phase_1b_seed(project_dir: Path) -> dict | None:
    """Build a complete Phase 1b seed including the diagnosis prompt
    and configuration for a limited-budget LLM run.

    Returns a dict with keys: prompt, budget, champion_form, diagnosis.
    """
    prompt = build_diagnosis_prompt(project_dir)
    if prompt is None:
        return None

    ms = json.loads((project_dir / "workspace" / "margin_of_safety.json").read_text())
    rc = ms.get("residual_characterization", {})

    return {
        "prompt": prompt,
        "budget": 5,  # Limited iterations for Phase 1b
        "champion_form": ms.get("champion_expression"),
        "champion_params": ms.get("champion_params"),
        "diagnosis": {
            "spectral_slope": rc.get("spectral_slope"),
            "noise_class": rc.get("noise_class"),
            "verdict": ms.get("remediation", {}).get("verdict"),
            "extensions_exhausted": ms.get("remediation", {}).get("candidates_tried", 0),
        },
    }


def inject_diagnosis_into_constraints(project_dir: Path) -> bool:
    """Inject the GP-112 diagnosis as a confirmed constraint in the JSON ledger.

    The autoresearch_loop reads confirmed constraints from
    workspace/derived_constraints.json via render_confirmed_constraints_prompt_section().
    This is the ONLY path from derived constraints to the mutator prompt.
    The brief markdown is for operator readability only.

    Returns True if injection succeeded.
    """
    seed = build_phase_1b_seed(project_dir)
    if seed is None:
        return False

    ledger_path = project_dir / "workspace" / "derived_constraints.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing ledger (dict with confirmed_constraints and provisional_constraints)
    ledger = {"confirmed_constraints": [], "provisional_constraints": [],
              "confirmed_constraint_count": 0}
    if ledger_path.exists():
        try:
            loaded = json.loads(ledger_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                ledger = loaded
        except Exception:
            pass

    confirmed = ledger.get("confirmed_constraints", [])

    # Check if already injected
    for entry in confirmed:
        if entry.get("failure_family") == "gp112_diagnosis":
            return False

    # Build the constraint entry matching the render format exactly
    diagnosis = seed["diagnosis"]
    constraint = {
        "constraint_id": f"DC-GP112-{len(confirmed)+1:03d}",
        "seen_count_runs": 1,
        "failure_family": "gp112_diagnosis",
        "applies_to": "all candidate models",
        "constraint": (
            f"The deterministic compression exhausted {diagnosis['extensions_exhausted']} "
            f"single-term additive extensions. None reduced residual autocorrelation. "
            f"Residual noise class: {diagnosis.get('noise_class', 'unknown')} "
            f"(spectral slope {diagnosis.get('spectral_slope', 'unknown')}). "
            f"Any valid next candidate MUST use a NON-ADDITIVE correction "
            f"(multiplicative, regime-dependent, or structurally novel form). "
            f"Do NOT propose another additive single-term extension."
        ),
    }

    confirmed.append(constraint)
    ledger["confirmed_constraints"] = confirmed
    ledger["confirmed_constraint_count"] = len(confirmed)
    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    # Also update the brief for operator readability
    brief_path = project_dir / "workspace" / "derived_constraints_brief.md"
    brief_content = ""
    if brief_path.exists():
        brief_content = brief_path.read_text(encoding="utf-8")

    if "GP-112 Structural Diagnosis" not in brief_content:
        brief_content += f"\n\n## GP-112 Structural Diagnosis\n\n{constraint['constraint']}\n"
        brief_path.write_text(brief_content, encoding="utf-8")

    return True
