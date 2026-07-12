"""GP-105 — M-Form Alignment Audit: Runtime Goodhart Detection for Qualitative Projects.

Fires stochastically when a qualitative run scores high in early iterations.
A "General Office" LLM call audits the champion thesis against the charter
while blinded to the rubric — detecting false frictionless success where the
Mutator optimized a narrow proxy of the charter rather than its full spirit.

Design decisions (from multidisciplinary debate, 2026-04-20):
- Stochastic trigger: p = 0.15 + 0.65 * sigmoid(score - 85). Not deterministic.
- Cross-family model separation: general_office_model != Judge model != Mutator model.
- Async boundary: audit fires after PHASE_F, finding applied at start of next iter.
- General Office is blinded to rubric; receives charter + thesis (metadata stripped).
- Appends new dimension at 15% weight; rebalances existing proportionally.
- Writes to rubrics/goodhart_log.jsonl (cross-run persistent log).
- max_audits_per_run = 2; iter > 10 skipped (late-run high scores are expected).

Integration points in autoresearch_loop.py:
1. Before main loop: _mform_audits_this_run = 0
2. Start of each iteration: rubric_data, _ = apply_mform_pending(...)
3. After PHASE_F: maybe_fire_mform_audit(...) -> bool; if True: _mform_audits_this_run += 1

Seam: GP-105 (internal seam)
Spec: GP-105 (internal seam)
"""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.common.llm_runtime import LLMRuntime, PRODUCTION_CALL_RETRIES
from ztare.common.paths import REPO_ROOT

_GOODHART_LOG_PATH = REPO_ROOT / "rubrics" / "goodhart_log.jsonl"
_MFORM_PENDING_FILENAME = "mform_pending.json"
_NEW_DIMENSION_WEIGHT_PCT = 15
_SIGMOID_CENTER = 85.0
_P_BASE = 0.15
_P_RANGE = 0.65
_MAX_AUDITS_PER_RUN = 2
_MAX_AUDIT_ITER = 10
_THESIS_EXCERPT_CHARS = 3000


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------

def compute_audit_probability(score: float) -> float:
    """Stochastic trigger probability. At score 60: ~15%. At 85: ~47%. At 94: ~78%.

    Not deterministic — prevents Mutator from learning to camp just below a fixed gate.
    """
    sig = 1.0 / (1.0 + math.exp(-(score - _SIGMOID_CENTER)))
    return _P_BASE + _P_RANGE * sig


def should_fire_audit(
    score: float,
    iteration: int,
    audits_so_far: int,
    rubric_data: dict,
) -> bool:
    """Return True if the General Office audit should fire this iteration."""
    if not rubric_data.get("enable_mform_audit", False):
        return False
    if audits_so_far >= _MAX_AUDITS_PER_RUN:
        return False
    if iteration > _MAX_AUDIT_ITER:
        return False
    p = compute_audit_probability(score)
    return random.random() < p


# ---------------------------------------------------------------------------
# General Office LLM call
# ---------------------------------------------------------------------------

_GENERAL_OFFICE_PROMPT_TEMPLATE = """\
You are the strategic Board of Directors reviewing whether a thesis engaged the full \
spirit of its charter.

You will receive the original project charter and a thesis written in response to it.
You do NOT have access to the scoring rubric. Your job is to assess whether the thesis \
engaged the implicit analytical breadth required by the charter — not whether it scored \
well on any specific criteria.

Charter:
{charter_text}

Thesis (first {excerpt_chars} characters):
{thesis_excerpt}

Ask yourself: could a thoughtful expert read this charter and feel that this thesis \
answered its full scope? Or did the thesis find a narrow, technically-valid-but-incomplete path?

Respond ONLY with a JSON object and nothing else:
{{
  "gap_detected": true or false,
  "gap_description": "what the charter implicitly required that the thesis did not engage \
(empty string if no gap)",
  "adversarial_criterion": "a criterion to add to the scoring rubric that would penalize \
this gap (empty string if no gap)",
  "criterion_name": "snake_case_short_name_under_30_chars (empty string if no gap)"
}}

Be conservative: flag a gap only if it is clear and significant — a major analytical \
requirement of the charter that the thesis systematically avoided, not a minor emphasis difference.
"""


def run_general_office_audit(
    charter_path: Path,
    thesis_path: Path,
    model_id: str,
    runtime: LLMRuntime,
) -> dict | None:
    """Call General Office LLM. Returns parsed JSON finding or None on failure."""
    try:
        charter_text = charter_path.read_text(encoding="utf-8") if charter_path.exists() else ""
        thesis_text = thesis_path.read_text(encoding="utf-8") if thesis_path.exists() else ""
        if not charter_text or not thesis_text:
            return None

        # Strip scoring metadata: remove lines that contain score numbers to
        # prevent the General Office anchoring to the rubric's verdict.
        thesis_excerpt = _strip_scoring_metadata(thesis_text)[:_THESIS_EXCERPT_CHARS]

        prompt = _GENERAL_OFFICE_PROMPT_TEMPLATE.format(
            charter_text=charter_text[:4000],
            thesis_excerpt=thesis_excerpt,
            excerpt_chars=_THESIS_EXCERPT_CHARS,
        )

        from ztare.common.dispatch_model import dispatch_call_text

        response = dispatch_call_text(
            "mform_alignment_audit",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=model_id,
                retries=PRODUCTION_CALL_RETRIES,
            ),
            timeout_seconds=300,
        )
        if not response:
            return None

        # GP-135 fix (2026-04-23): call_text returns an LLMTextResponse
        # dataclass, NOT a plain string. Previous code called
        # `response.strip()` which raised AttributeError on the dataclass
        # and got swallowed by the bare `except Exception`, producing
        # the cryptic "General Office: audit failed (LLM error)" on
        # every fire. Extract .text explicitly.
        raw_text = getattr(response, "text", None) or str(response)
        raw = raw_text.strip() if isinstance(raw_text, str) else ""
        if not raw:
            return None

        # Use the shared prose-tolerant parser (handles Claude-style
        # reasoning-before-JSON and embedded code fences).
        from ztare.common.utils import parse_llm_json
        try:
            finding = parse_llm_json(raw)
        except Exception:
            return None

        # Validate required keys
        if not isinstance(finding.get("gap_detected"), bool):
            return None
        return finding

    except Exception as _audit_exc:
        # GP-135: surface the exception class so future failures are not silent.
        import sys as _s
        _s.stderr.write(
            f"[GP-105 audit] skipped due to exception: "
            f"{type(_audit_exc).__name__}: {str(_audit_exc)[:200]}\n"
        )
        return None


def _strip_scoring_metadata(text: str) -> str:
    """Remove score lines and rubric artifacts from thesis text."""
    import re
    # Remove lines like "Score: 87" or "score_contract" or "## Fit Declaration"
    stripped = re.sub(r"^.*score[_\s]*(?:contract|:).*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
    stripped = re.sub(r"^```fit_declaration.*?^```", "", stripped, flags=re.MULTILINE | re.DOTALL)
    return stripped


# ---------------------------------------------------------------------------
# Async pending file
# ---------------------------------------------------------------------------

def write_mform_pending(finding: dict, workspace_dir: Path) -> None:
    """Write finding to pending file for application at next iteration start."""
    from ztare.common.pending_file import write_pending
    write_pending(workspace_dir, _MFORM_PENDING_FILENAME, finding)


def load_mform_pending(workspace_dir: Path) -> dict | None:
    """Load and delete pending finding. Returns None if absent."""
    from ztare.common.pending_file import take_pending
    return take_pending(workspace_dir, _MFORM_PENDING_FILENAME)


# ---------------------------------------------------------------------------
# Rubric rewrite
# ---------------------------------------------------------------------------

def apply_mform_pending(
    rubric_data: dict,
    workspace_dir: Path,
    rubrics_dir: Path,
    rubric_name: str,
) -> tuple[dict, bool]:
    """Load any pending M-Form finding and apply it to rubric_data.

    Returns updated rubric_data and a bool indicating whether a finding was applied.
    Fail-silent: if anything goes wrong, returns original rubric_data unchanged.
    """
    finding = load_mform_pending(workspace_dir)
    if finding is None:
        return rubric_data, False
    if not finding.get("gap_detected", False):
        return rubric_data, False

    adversarial_criterion = finding.get("adversarial_criterion", "").strip()
    criterion_name = finding.get("criterion_name", "").strip() or "mform_adversarial"
    gap_description = finding.get("gap_description", "")

    if not adversarial_criterion:
        return rubric_data, False

    try:
        # 1. Append to rubric["criteria"]
        safe_key = f"mform_{criterion_name}"[:40]
        if "criteria" not in rubric_data or not isinstance(rubric_data["criteria"], dict):
            rubric_data["criteria"] = {}
        rubric_data["criteria"][safe_key] = adversarial_criterion

        # 2. Append new dimension at _NEW_DIMENSION_WEIGHT_PCT; rebalance existing.
        #
        # Iatrogenic-bug fix (2026-04-24, gp152 run-2 surfaced this):
        #   Newton-mode rubrics (`rubric_mode == "newton"`) require a
        #   "Generative Yield" dimension with weight >= 15 per
        #   docs/concepts/rubric_specification.md §18. The previous uniform
        #   multiplicative rebalance crushed Generative Yield from 15 to ~10.84
        #   when an M-Form criterion was added, violating the Newton-mode
        #   invariant and causing the next launch's pre-flight gate to FAIL.
        # Fix: protect Generative Yield (and any other dimension flagged via
        #   `_protected_in_rebalance: true`) from the rebalance multiplier;
        #   take the new dimension's weight from the unprotected dimensions
        #   only. Also enforces sum=100 exactly via residual rounding-error
        #   correction on the largest unprotected dimension.
        dims = rubric_data.get("dimensions")
        if isinstance(dims, list) and dims:
            W = _NEW_DIMENSION_WEIGHT_PCT
            is_newton = str(rubric_data.get("rubric_mode") or "").strip().lower() == "newton"

            def _is_protected(d: dict) -> bool:
                if d.get("_protected_in_rebalance") is True:
                    return True
                # Auto-protect Generative Yield in Newton-mode rubrics
                if is_newton and "generative yield" in str(d.get("name", "")).lower():
                    return True
                return False

            protected = [d for d in dims if _is_protected(d)]
            unprotected = [d for d in dims if not _is_protected(d)]

            protected_total = sum(float(d.get("weight", 0)) for d in protected)
            unprotected_total = sum(float(d.get("weight", 0)) for d in unprotected)
            target_unprotected_total = max(0.0, 100.0 - W - protected_total)

            if unprotected_total > 0 and target_unprotected_total > 0:
                scale = target_unprotected_total / unprotected_total
                for dim in unprotected:
                    if isinstance(dim.get("weight"), (int, float)):
                        dim["weight"] = round(float(dim["weight"]) * scale, 2)
            elif protected_total + W > 100:
                # Pathological: protected dims + new W already exceed 100.
                # Cap the new dim at remainder; warn via description.
                W = max(0.0, 100.0 - protected_total)

            dims.append({
                "name": f"M-Form Charter Alignment: {criterion_name}",
                "weight": W,
                "description": (
                    f"[GP-105 General Office insertion] {adversarial_criterion} "
                    f"Gap detected: {gap_description}"
                ),
            })

            # Final rounding-error correction: ensure sum is exactly 100.0
            # by adjusting the largest unprotected dimension by the residual.
            current_sum = sum(float(d.get("weight", 0)) for d in dims)
            residual = round(100.0 - current_sum, 2)
            if abs(residual) > 1e-9 and unprotected:
                # Apply to the largest unprotected dimension (avoid tiny ones)
                largest = max(unprotected, key=lambda d: float(d.get("weight", 0)))
                largest["weight"] = round(float(largest["weight"]) + residual, 2)

            rubric_data["dimensions"] = dims

        # 3. Write updated rubric to disk so test_thesis.py subprocess sees it
        try:
            rubric_file = rubrics_dir / f"{rubric_name}.json"
            rubric_file.write_text(json.dumps(rubric_data, indent=2), encoding="utf-8")
        except Exception:
            pass  # in-memory update still applies for this run

        # 4. Write to goodhart_log.jsonl
        _append_goodhart_log(
            project=workspace_dir.parent.name,
            finding=finding,
            workspace_dir=workspace_dir,
        )

        print(
            f"\n🏛️  GP-105 General Office: charter-spirit gap detected.\n"
            f"   Gap: {gap_description[:120]}\n"
            f"   Appended adversarial criterion at {_NEW_DIMENSION_WEIGHT_PCT}% weight.\n"
            f"   Existing dimensions rebalanced. Mutator resumes under hardened rubric.\n"
        )
        return rubric_data, True

    except Exception:
        return rubric_data, False  # fail-silent


# ---------------------------------------------------------------------------
# goodhart_log.jsonl
# ---------------------------------------------------------------------------

def _append_goodhart_log(
    project: str,
    finding: dict,
    workspace_dir: Path,
) -> None:
    """Append GP-105 finding to the cross-run goodhart log. Fail-silent."""
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project": project,
            "domain_type": "qualitative",
            "gap_description": finding.get("gap_description", ""),
            "adversarial_criterion": finding.get("adversarial_criterion", ""),
            "criterion_name": finding.get("criterion_name", ""),
            "score_at_detection": finding.get("_score_at_detection"),
            "iteration": finding.get("_iteration"),
            "dimension_weight_pct": _NEW_DIMENSION_WEIGHT_PCT,
        }
        _GOODHART_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _GOODHART_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main entry point called from autoresearch_loop.py
# ---------------------------------------------------------------------------

def maybe_fire_mform_audit(
    score: float,
    iteration: int,
    audits_so_far: int,
    rubric_data: dict,
    workspace_dir: Path,
    project_dir: Path,
    runtime: LLMRuntime,
) -> bool:
    """Fire the General Office audit if stochastic trigger activates.

    Writes mform_pending.json if a gap is found. The finding is applied
    at the START of the next iteration (async boundary).

    Returns True if the audit fired (regardless of gap_detected result).
    """
    if not should_fire_audit(score, iteration, audits_so_far, rubric_data):
        return False

    model_id_str = rubric_data.get("general_office_model", "gpt4.1")
    # Import resolve_model_id lazily to avoid circular import at module load
    try:
        from ztare.common.llm_runtime import resolve_model_id
        model_id = resolve_model_id(model_id_str)
    except Exception:
        model_id = model_id_str

    charter_path = project_dir / "project_charter.md"
    thesis_path = project_dir / "thesis.md"

    print(
        f"\n🏛️  GP-105: General Office audit firing (iter {iteration}, "
        f"score {score:.0f}, p≈{compute_audit_probability(score):.2f})..."
    )

    finding = run_general_office_audit(
        charter_path=charter_path,
        thesis_path=thesis_path,
        model_id=model_id,
        runtime=runtime,
    )

    if finding is None:
        print("    General Office: audit failed (LLM error) — skipping.")
        return True  # audit fired, just failed silently

    if not finding.get("gap_detected", False):
        print("    General Office: no charter-spirit gap detected — thesis is on target.")
        return True

    # Enrich finding with metadata for logging
    finding["_score_at_detection"] = score
    finding["_iteration"] = iteration

    write_mform_pending(finding, workspace_dir)
    print(
        f"    General Office: gap detected — pending criterion queued for next iteration.\n"
        f"    Gap: {finding.get('gap_description', '')[:100]}"
    )
    return True
