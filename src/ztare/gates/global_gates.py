"""Global behavioral gates for GP-086.

Engine-level deterministic gates that fire on every iteration regardless of
project substrate. These are LLM behavioral pathology checks — not substrate-
specific correctness checks. Substrate-specific gates live in each project's
gate_harness.py; this module adds a universal layer on top.

Architecture (GP-086 spec):
  - Execution logic lives here (this file, engine-level, never per-project)
  - Parameters live in rubric.json (evidence_fit_threshold, farther_tail_region,
    disable_*_gate with mandatory disable_reason)
  - Absent config key → loud FAIL (GP-077 precedent: no silent defaults)
  - Results are merged into the existing deterministic_charter_gates payload
    so that _extract_iteration_gate_metrics and _format_gate_surface_for_prompt
    work unchanged

Phase 0 gate:  evidence_fit
Phase 1 gates: uniqueness_gap, parsimony_violation, extrapolation_gap,
               named_import_check

Phases 3-4 (kernel contracts, extractor automation) are deferred pending
Phase 0-2 validation across ≥3 production runs.
"""

from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Gate result helpers
# ---------------------------------------------------------------------------

def _gate(
    name: str,
    passed: bool,
    actual: float | str | None,
    threshold: float | str | None,
    reason: str,
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
        "source": "global_gates",
    }


def _loud_fail(name: str, reason: str) -> dict[str, Any]:
    """Gate that fails loudly due to missing required configuration."""
    return _gate(
        name=name,
        passed=False,
        actual=None,
        threshold=None,
        reason=f"CONFIGURATION ERROR — {reason}",
        hard_fail=True,
    )


# ---------------------------------------------------------------------------
# Evidence parsing
# ---------------------------------------------------------------------------

def _parse_evidence(evidence_text: str) -> list[tuple[list[float], float]]:
    """Parse evidence.txt into list of (input_values, output_value) tuples.

    Two supported row shapes:
      Simple regression:        x  y                    → ([x], y)
      Multi-column numeric:     a b c d                 → ([a, b, c], d)  [last col = target]
      Multi-column categorical: z d q regime modality id → ([d, q], z)    [first col = target;
                                                                           string cols dropped]

    The categorical-tolerant variant (added 2026-05-02) handles enriched substrates
    where row schema is `target features categorical_tags row_id`. It detects this
    shape by finding a leading prefix of float-parseable columns and skipping the
    rest. Convention: if more than one numeric column AND any column fails float
    parse, treat first numeric col as target and remaining numerics as features
    (drops string tags, drops row_id).

    Skips comment lines (#) and section headers (===).
    """
    rows: list[tuple[list[float], float]] = []
    for raw in evidence_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("==="):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        # First try: all-numeric row (legacy 'x y' or all-numeric multi-col).
        try:
            floats = [float(p) for p in parts]
            rows.append((floats[:-1], floats[-1]))
            continue
        except ValueError:
            pass
        # Categorical-tolerant fallback: collect leading numeric columns,
        # stop at first non-numeric. Use first numeric as target, remaining
        # numerics as features. Requires at least 2 numeric columns.
        numeric_prefix: list[float] = []
        for p in parts:
            try:
                numeric_prefix.append(float(p))
            except ValueError:
                break
        if len(numeric_prefix) >= 2:
            target = numeric_prefix[0]
            features = numeric_prefix[1:]
            rows.append((features, target))
    return rows


def _load_model_fn(project_dir: Path):
    """Import a model function from test_model.py.

    Tries (in priority order):
      1. f(x) — legacy single-input scalar regression model
      2. I_model(features, params=None) — current GP-156+ standard;
         we adapt it by passing the input as features['d'] (or first feature)
         with optional MODEL_PARAMS from the module
      3. PARAMETRIC_FORM eval'd against features+params

    Returns a callable that takes positional float args and returns float.
    """
    test_model_path = project_dir / "test_model.py"
    if not test_model_path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("_global_gate_test_model", str(test_model_path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Path 1: legacy f(x) — preferred by original gate design.
        f = getattr(module, "f", None)
        if callable(f):
            return f
        # Path 2: GP-156+ I_model(features, params) — wrap as f(*args).
        # Convention: positional args fill features['d'], features['q'], ... in
        # the order the substrate's features.py exposes them. Rather than
        # hardcoding feature names here, we delegate to features.py if present;
        # otherwise we pass {'x0': args[0], 'x1': args[1], ...} as a generic
        # feature dict and let I_model handle missing keys defensively.
        I_model = getattr(module, "I_model", None)
        model_params = getattr(module, "MODEL_PARAMS", None) or {}
        if callable(I_model):
            # Try features.py adapter for proper feature-dict shape.
            try:
                feat_spec = importlib.util.spec_from_file_location(
                    "_global_gate_features",
                    str(project_dir / "features.py"),
                )
                if feat_spec is not None and feat_spec.loader is not None:
                    feat_mod = importlib.util.module_from_spec(feat_spec)
                    feat_spec.loader.exec_module(feat_mod)
                    features_for_row = getattr(feat_mod, "features_for_row", None)
                    feature_names_fn = getattr(feat_mod, "feature_names", None)
                    if callable(features_for_row) and callable(feature_names_fn):
                        # Build a minimal row dict from positional args. The
                        # evidence parser passes (features, target), so args
                        # are the numeric features in row-order. We only know
                        # the substrate's first numeric feature is `d`; pass
                        # remaining as 'q' if substrate exposes it, else extend.
                        def _adapter(*args):
                            row = {"d": float(args[0])}
                            if len(args) > 1:
                                row["q"] = float(args[1])
                            row["r"] = ""
                            row["m"] = ""
                            feats = features_for_row(row)
                            return float(I_model(feats, model_params or None))
                        return _adapter
            except Exception:
                pass
            # Fallback adapter: pass a generic feature dict.
            def _generic_adapter(*args):
                feats = {"d": float(args[0]) if args else 0.0}
                if len(args) > 1:
                    feats["q"] = float(args[1])
                # Common feature aliases the model might check
                if args:
                    import math as _m
                    d = max(float(args[0]), 1e-12)
                    feats.update({
                        "log_d": _m.log(d),
                        "log10_d": _m.log10(d),
                        "inv_d": 1.0 / d,
                        "inv_log_d": 1.0 / max(_m.log(d), 1e-12),
                        "sqrt_d": _m.sqrt(d),
                    })
                return float(I_model(feats, model_params or None))
            return _generic_adapter
        # Path 3: PARAMETRIC_FORM eval (last resort)
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Phase 0: evidence_fit gate
# ---------------------------------------------------------------------------

def _gate_evidence_fit(
    rubric_data: dict,
    project_dir: Path,
    evidence_text: str | None,
) -> dict[str, Any]:
    """Max normalised residual on training evidence < threshold.

    Reuses the same model function (f) that the project's gate_harness uses.
    Threshold is configurable via rubric field 'evidence_fit_threshold' (default 0.15).
    Missing config key → loud FAIL (no silent default on threshold presence check,
    but we do allow the default 0.15 since this is a calibration parameter, not
    a structural requirement).
    """
    name = "global_evidence_fit"

    if rubric_data.get("disable_evidence_fit_gate"):
        reason = rubric_data.get("disable_evidence_fit_gate_reason", "(no reason provided)")
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason=f"DISABLED by rubric config — reason: {reason}")

    # GP-121: discovery mode — gate becomes advisory (soft penalty, not hard fail)
    # Use for substrates where the solution is unknown and smooth templates
    # may not fit the data point-by-point (oscillatory, erratic, multiplicative)
    if rubric_data.get("evidence_fit_mode") == "discovery":
        # Run the fit check but report as soft (passed=True, no hard_fail)
        # The actual residual is logged for diagnostics but doesn't zero the score
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason="discovery mode: evidence_fit is advisory, not blocking. "
                            "The judge evaluates thesis quality; the gate logs fit diagnostics.")

    threshold = float(rubric_data.get("evidence_fit_threshold", 0.15))

    if evidence_text is None:
        return _loud_fail(name, "evidence_text not provided to global_gates — cannot evaluate evidence_fit")

    rows = _parse_evidence(evidence_text)
    if not rows:
        return _loud_fail(name, "evidence.txt parsed to zero rows — cannot evaluate evidence_fit")

    model_fn = _load_model_fn(project_dir)
    if model_fn is None:
        # No f() available — gate is skipped (test_model may not expose f yet)
        return _gate(name, passed=True, actual=None, threshold=threshold,
                     reason="test_model.py does not expose f() — evidence_fit gate skipped this iteration")

    predictions: list[float] = []
    observations: list[float] = []
    for inputs, obs in rows:
        try:
            if len(inputs) == 1:
                pred = float(model_fn(inputs[0]))
            else:
                pred = float(model_fn(*inputs))
        except Exception:
            pred = float("nan")

        if math.isnan(pred) or math.isinf(pred):
            bound_mode = rubric_data.get("evidence_fit_mode")
            if bound_mode in ("upper_bound", "lower_bound"):
                # In bound modes, treat NaN as a violation (the form doesn't
                # cover this point) rather than a hard crash
                pred = float("-inf") if bound_mode == "upper_bound" else float("inf")
            else:
                return _gate(name, passed=False, actual=float("inf"), threshold=threshold,
                             reason=f"model returned non-finite at inputs={inputs}; evidence_fit FAIL",
                             hard_fail=True)

        predictions.append(pred)
        observations.append(float(obs))

    # GP-121: Check for upper_bound or lower_bound mode
    # upper_bound: f(n) >= z(n) for all n (the function bounds the data from ABOVE)
    # lower_bound: f(n) <= z(n) for all n (the function bounds the data from BELOW)
    # default (absent): standard curve-fit mode (|f(n) - z(n)| < threshold)
    bound_mode = rubric_data.get("evidence_fit_mode")  # "upper_bound" | "lower_bound" | None

    if bound_mode == "upper_bound":
        # Every prediction must be >= every observation
        violations = [(o, p) for o, p in zip(observations, predictions) if p < o]
        max_obs_magnitude = max(abs(o) for o in observations)
        denom = max_obs_magnitude if max_obs_magnitude >= 1e-12 else 1.0
        if violations:
            worst = max(abs(o - p) / denom for o, p in violations)
            return _gate(
                name=name, passed=False, actual=round(worst, 6), threshold=0,
                reason=f"upper_bound mode: {len(violations)} violations (f(n) < z(n)); worst={worst:.4f}",
                hard_fail=True,
            )
        # All predictions >= observations — check margin
        margins = [(p - o) / denom for o, p in zip(observations, predictions)]
        min_margin = min(margins)
        return _gate(
            name=name, passed=True, actual=round(min_margin, 6), threshold=0,
            reason=f"upper_bound mode: ALL f(n) >= z(n), min_margin={min_margin:.4f}",
            hard_fail=False,
        )

    if bound_mode == "lower_bound":
        violations = [(o, p) for o, p in zip(observations, predictions) if p > o]
        max_obs_magnitude = max(abs(o) for o in observations)
        denom = max_obs_magnitude if max_obs_magnitude >= 1e-12 else 1.0
        if violations:
            worst = max(abs(o - p) / denom for o, p in violations)
            return _gate(
                name=name, passed=False, actual=round(worst, 6), threshold=0,
                reason=f"lower_bound mode: {len(violations)} violations (f(n) > z(n)); worst={worst:.4f}",
                hard_fail=True,
            )
        margins = [(o - p) / denom for o, p in zip(observations, predictions)]
        min_margin = min(margins)
        return _gate(
            name=name, passed=True, actual=round(min_margin, 6), threshold=0,
            reason=f"lower_bound mode: ALL f(n) <= z(n), min_margin={min_margin:.4f}",
            hard_fail=False,
        )

    # Default: standard curve-fit mode
    # Normalise by max(|obs|) across all rows — self-calibrating to the scale of the dataset.
    max_obs_magnitude = max(abs(o) for o in observations)
    denom = max_obs_magnitude if max_obs_magnitude >= 1e-12 else 1.0

    residuals = [abs(o - p) / denom for o, p in zip(observations, predictions)]
    max_norm_residual = max(residuals)

    passed = max_norm_residual < threshold
    return _gate(
        name=name,
        passed=passed,
        actual=round(max_norm_residual, 6),
        threshold=threshold,
        reason=(
            f"max_residual_normalised_by_scale={max_norm_residual:.4f} "
            f"(denom=max|obs|={denom:.4g}) "
            f"{'<' if passed else '>='} threshold={threshold}: "
            f"{'PASS' if passed else 'FAIL'}"
        ),
        hard_fail=not passed,
    )


# ---------------------------------------------------------------------------
# Phase 1: uniqueness_gap gate
# ---------------------------------------------------------------------------

def _gate_uniqueness_gap(
    rubric_data: dict,
    thesis_text: str | None,
    score_contract: dict | None,
) -> dict[str, Any]:
    """Thesis must enumerate ≥2 distinct, falsified rival structural forms.

    Implementation uses the judge's rival_construction rubric dimension score
    when available (lower fragility than text parsing). If the dimension is
    absent or scores 0, the gate caps the score at 60.

    This gate fires only after evidence_fit passes (sequencing enforced by
    the caller — see run_global_gates).
    """
    name = "global_uniqueness_gap"

    if rubric_data.get("disable_uniqueness_gap_gate"):
        reason = rubric_data.get("disable_uniqueness_gap_gate_reason", "(no reason provided)")
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason=f"DISABLED by rubric config — reason: {reason}")

    # Option (pre-a): if the rubric itself declares a criterion key containing "rival",
    # the judge is already scoring rival construction as part of the rubric evaluation.
    # criteria_scores is not populated in raw_llm_score mode (dead code path), so
    # defer to rubric criterion coverage rather than falling through to the keyword heuristic.
    rubric_criteria = rubric_data.get("criteria", {})
    if isinstance(rubric_criteria, dict):
        for key in rubric_criteria:
            if "rival" in key.lower():
                return _gate(
                    name=name,
                    passed=True,
                    actual=None,
                    threshold=None,
                    reason=(
                        f"Rubric criterion '{key}' explicitly requires rival construction — "
                        "judge scores this as part of the rubric; gate defers to rubric criterion coverage. "
                        "(criteria_scores not wired in raw_llm_score mode — rubric-presence check substitutes)"
                    ),
                )

    # Option (a): use rival_construction rubric dimension score from score_contract
    rival_score: int | None = None
    if isinstance(score_contract, dict):
        criteria_scores = score_contract.get("criteria_scores", {})
        if isinstance(criteria_scores, dict):
            for key, val in criteria_scores.items():
                if "rival" in key.lower():
                    try:
                        rival_score = int(val)
                    except (TypeError, ValueError):
                        pass
                    break

    if rival_score is not None:
        passed = rival_score >= 1
        return _gate(
            name=name,
            passed=passed,
            actual=rival_score,
            threshold=1,
            reason=(
                f"rival_construction rubric dimension score={rival_score} "
                f"{'≥' if passed else '<'} 1: {'PASS' if passed else 'FAIL — score capped at 60'}"
            ),
            penalty=0 if passed else 0,  # cap enforced by caller
            hard_fail=False,  # cap, not FAIL
        )

    # Fallback: rubric dimension absent — check thesis text for rival mentions
    if thesis_text is None:
        return _gate(name, passed=False, actual=None, threshold=None,
                     reason="rival_construction dimension absent from score_contract and no thesis_text provided — cap at 60",
                     hard_fail=False)

    # Count distinct structural rival mentions (conservative text heuristic)
    lower = thesis_text.lower()
    rival_keywords = ["alternative", "rival", "competing form", "competing model",
                      "alternative hypothesis", "rejected form", "discarded"]
    rival_count = sum(1 for kw in rival_keywords if kw in lower)
    passed = rival_count >= 2
    return _gate(
        name=name,
        passed=passed,
        actual=rival_count,
        threshold=2,
        reason=(
            f"rival keyword count in thesis={rival_count} "
            f"{'≥' if passed else '<'} 2 (heuristic — no rival_construction dimension found): "
            f"{'PASS' if passed else 'FAIL — score capped at 60'}"
        ),
        hard_fail=False,
    )


# ---------------------------------------------------------------------------
# Phase 1: parsimony_violation gate
# ---------------------------------------------------------------------------

def _gate_parsimony_violation(
    rubric_data: dict,
    evidence_text: str | None,
    fit_declaration: dict | None,
) -> dict[str, Any]:
    """param_count > evidence_point_count → -15 penalty.

    Penalty (not FAIL) — avoids killing legitimate sparse-data domain theses.
    param_count comes from fit_declaration.parameter_names when available.
    evidence_point_count is the number of parsed evidence rows.
    """
    name = "global_parsimony_violation"

    if rubric_data.get("disable_parsimony_gate"):
        reason = rubric_data.get("disable_parsimony_gate_reason", "(no reason provided)")
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason=f"DISABLED by rubric config — reason: {reason}")

    # Get param_count from fit_declaration
    param_count: int | None = None
    if isinstance(fit_declaration, dict):
        param_names = fit_declaration.get("parameter_names", [])
        if isinstance(param_names, list):
            param_count = len(param_names)

    if param_count is None:
        # No fit declaration — gate does not fire (fit not attempted this iteration)
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason="no FitDeclaration present — parsimony gate skipped this iteration")

    if evidence_text is None:
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason="evidence_text not available — parsimony gate skipped")

    rows = _parse_evidence(evidence_text)
    evidence_count = len(rows)

    if evidence_count == 0:
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason="evidence.txt parsed to zero rows — parsimony gate skipped")

    passed = param_count <= evidence_count
    return _gate(
        name=name,
        passed=passed,
        actual=param_count,
        threshold=evidence_count,
        reason=(
            f"param_count={param_count} {'≤' if passed else '>'} evidence_points={evidence_count}: "
            f"{'PASS' if passed else 'FAIL — -15 penalty applied'}"
        ),
        penalty=0 if passed else -15,
        hard_fail=False,
    )


# ---------------------------------------------------------------------------
# Phase 1: named_import_check gate
# ---------------------------------------------------------------------------

def _gate_named_import_check(
    project_dir: Path,
    thesis_text: str | None,
    rubric_data: dict,
) -> dict[str, Any]:
    """Scan thesis text for named-import denylist terms — hard fail if any hit found.

    Term source (in priority order):
      1. rubric_data["thesis_denylist"] — curated list of explicit identifiers
         (function names, OEIS IDs, named theorems) that should trigger hard-fail.
         Use this for precision: only include terms that cannot appear in a
         legitimate data-driven derivation.
      2. .denylist file in project_dir — fallback to the leak-sentinel denylist.
         This list is designed for static artifact scanning and may include
         generic terms (e.g. "prime", "divisor") that produce false positives
         in thesis text. Prefer thesis_denylist for thesis scanning.

    Rationale: if the mutator explicitly names a mathematical function or sequence
    from its training weights (sopfr, A001414, q(n), Hardy-Ramanujan), the
    derivation cannot be considered independent abduction — the thesis is tainted
    regardless of fit quality.

    Graceful degradation:
      - No thesis_denylist in rubric AND no .denylist file → gate passes (skipped)
      - thesis_text is None → gate passes (not available yet this iteration)
    """
    name = "global_named_import_check"

    if rubric_data.get("disable_named_import_gate"):
        reason = rubric_data.get("disable_named_import_gate_reason", "(no reason provided)")
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason=f"DISABLED by rubric config — reason: {reason}")

    # Priority 1: .thesis_denylist file (curated for thesis scanning, sentinel-safe)
    thesis_denylist_path = project_dir / ".thesis_denylist"
    if thesis_denylist_path.exists():
        raw_lines = thesis_denylist_path.read_text(encoding="utf-8").splitlines()
        terms = [
            line.strip() for line in raw_lines
            if line.strip() and not line.strip().startswith("#")
        ]
        source = ".thesis_denylist file"
    elif "thesis_denylist" in rubric_data:
        # Priority 2: thesis_denylist in rubric (legacy path — avoid for sentinel-scanned rubrics)
        raw = rubric_data["thesis_denylist"]
        terms = [t.strip() for t in (raw if isinstance(raw, list) else []) if t.strip()]
        source = "rubric thesis_denylist"
    else:
        # Priority 3: .denylist file (leak-sentinel list — may be too broad for thesis scanning)
        denylist_path = project_dir / ".denylist"
        if not denylist_path.exists():
            return _gate(name, passed=True, actual=None, threshold=None,
                         reason="no .thesis_denylist, no rubric thesis_denylist, no .denylist — named_import_check skipped")
        raw_lines = denylist_path.read_text(encoding="utf-8").splitlines()
        terms = [
            line.strip() for line in raw_lines
            if line.strip() and not line.strip().startswith("#")
        ]
        source = ".denylist file (fallback)"

    if not terms:
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason=".denylist is empty — named_import_check skipped")

    if thesis_text is None:
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason="thesis_text not provided — named_import_check skipped this iteration")

    hits = []
    text_lower = thesis_text.lower()
    for term in terms:
        term_lower = term.lower()
        # Multi-word terms: substring match is fine (phrase is already specific)
        # Single-word terms: require word boundary to avoid partial-word false positives
        # e.g., "factor" should not match inside "Fundamental"; "omega" should not match "omega-3"
        if " " in term_lower or "_" in term_lower:
            pattern = re.escape(term_lower)
        else:
            pattern = r"\b" + re.escape(term_lower) + r"\b"
        if re.search(pattern, text_lower):
            hits.append(term)

    if hits:
        return _gate(
            name=name,
            passed=False,
            actual=str(hits),
            threshold="[]",
            reason=(
                f"NAMED IMPORT DETECTED — denylist terms found in thesis: {hits}. "
                "The mutator cited a named mathematical result or sequence that is on the "
                "project denylist. The derivation cannot be considered independent abduction. "
                "Hard fail: score zeroed."
            ),
            hard_fail=True,
        )

    return _gate(name, passed=True, actual="[]", threshold="[]",
                 reason=f"no denylist terms found in thesis text ({len(terms)} terms checked): PASS")


# ---------------------------------------------------------------------------
# Phase 1: extrapolation_gap gate
# ---------------------------------------------------------------------------

def _gate_extrapolation_gap(
    rubric_data: dict,
    evidence_text: str | None,
) -> dict[str, Any]:
    """farther_tail_region must be declared in rubric.json and validated.

    Absent declaration → loud FAIL (GP-077 precedent: no silent defaults).
    Declared null with disable_reason → allowed opt-out.
    Per-dimension overlap check: declared range must extend beyond training data
    by at least one std dev of training spacing in that dimension.

    Class-aware bypass (2026-04-25): for cage_meta.class in
    {"audit", "literature", "proof_target", "closed_form_constant"} the
    gate auto-skips because those substrate classes have no numeric
    extrapolation regime by definition (audit = critique of artifact;
    literature = textual review; proof_target = formal-proof; closed-
    form = constant discovery). Without this bypass the gate hard-fails
    every audit run that legitimately has no farther_tail_region — a
    class-routing bug surfaced by gp165.
    """
    name = "global_extrapolation_gap"

    cage_meta = rubric_data.get("cage_meta") or {}
    cage_class = (cage_meta.get("class") or "").strip().lower() if isinstance(cage_meta, dict) else ""
    NO_EXTRAPOLATION_CLASSES = {"audit", "literature", "proof_target", "closed_form_constant"}
    if cage_class in NO_EXTRAPOLATION_CLASSES:
        return _gate(
            name, passed=True, actual=None, threshold=None,
            reason=(
                f"cage_meta.class='{cage_class}' has no numeric extrapolation regime "
                f"by definition — gate auto-skipped."
            ),
        )

    farther_tail = rubric_data.get("farther_tail_region", "__ABSENT__")

    if farther_tail == "__ABSENT__":
        return _loud_fail(
            name,
            "farther_tail_region not declared in rubric.json — extrapolation validation impossible. "
            "Declare farther_tail_region: null with a disable_reason to opt out explicitly."
        )

    if farther_tail is None:
        reason = rubric_data.get("farther_tail_region_disable_reason", "(no reason provided)")
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason=f"farther_tail_region explicitly null — opt-out accepted. Reason: {reason}")

    if not isinstance(farther_tail, dict):
        return _loud_fail(name, f"farther_tail_region must be a dict of {{dim: [min, max]}}, got {type(farther_tail)}")

    if evidence_text is None:
        # Can't validate overlap without evidence, but declaration exists — soft pass
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason="farther_tail_region declared but evidence_text unavailable — overlap check skipped")

    rows = _parse_evidence(evidence_text)
    if not rows:
        return _gate(name, passed=True, actual=None, threshold=None,
                     reason="evidence.txt empty — overlap check skipped")

    # Per-dimension validation
    warnings: list[str] = []
    n_dims = len(rows[0][0]) if rows else 0

    dim_keys = list(farther_tail.keys())
    for dim_idx, dim_key in enumerate(dim_keys):
        declared_range = farther_tail[dim_key]
        if not isinstance(declared_range, (list, tuple)) or len(declared_range) != 2:
            warnings.append(f"dim {dim_key}: invalid range {declared_range}")
            continue

        decl_min, decl_max = float(declared_range[0]), float(declared_range[1])

        # Extract training values for this dimension
        if dim_idx >= n_dims:
            warnings.append(f"dim {dim_key}: index {dim_idx} exceeds evidence column count {n_dims}")
            continue

        train_vals = sorted(row[0][dim_idx] for row in rows if dim_idx < len(row[0]))
        if not train_vals:
            continue

        train_min, train_max = train_vals[0], train_vals[-1]

        # Check if declared region extends beyond training boundary
        extends_below = decl_min < train_min
        extends_above = decl_max > train_max

        if not (extends_below or extends_above):
            warnings.append(
                f"dim {dim_key}: declared [{decl_min}, {decl_max}] is entirely interior to "
                f"training [{train_min}, {train_max}] — no extrapolation pressure"
            )

    if warnings:
        return _gate(
            name=name,
            passed=True,  # warning only, not hard FAIL — domain may have legitimate full-range training
            actual=str(warnings),
            threshold=None,
            reason="farther_tail_region declared but overlap warnings: " + "; ".join(warnings),
            hard_fail=False,
        )

    return _gate(name, passed=True, actual=str(farther_tail), threshold=None,
                 reason="farther_tail_region declared and extends beyond training boundaries: PASS")


# ---------------------------------------------------------------------------
# Phase 1: audit_mock_bypass gate (GP-166)
# ---------------------------------------------------------------------------

def _gate_audit_mock_bypass(
    rubric_data: dict,
    project_dir: Path,
) -> dict[str, Any]:
    """Cap audit-class scores at 50 when the bypass exploit uses Mocks
    instead of real imports of the components under audit.

    Audit substrates (cage_meta.class="audit") have all numerical
    validation gates disabled — the score is determined entirely by
    LLM-judge prose grading against the rubric. A common LLM failure
    mode is to satisfy the rubric's "runnable bypass exploit"
    requirement by building Mock classes in-script and asserting
    behavior against the Mocks. The exploit is technically runnable
    but demonstrates nothing about the real codebase. This gate
    detects that pattern and caps the score so the rubric's "concrete
    bypass demonstrated" dimension cannot be over-rewarded.

    Detection patterns (any one fires):
      - `unittest.mock` import or `from unittest.mock` import
      - `MagicMock` reference
      - Class definition matching `^class\\s+Mock[A-Z]\\w*` (e.g.,
        `class MockFramerND`, `class MockAnalogy`)

    The check runs against the latest submitted Python in
    `workspace/submissions/iter_*.py`. Operator override:
    `disable_audit_mock_bypass_gate=True`.

    Skips entirely when cage_meta.class is not "audit" — non-audit
    substrates have other validation gates that already discipline
    the bypass-quality requirement.
    """
    name = "global_audit_mock_bypass"

    if rubric_data.get("disable_audit_mock_bypass_gate"):
        return _gate(
            name, passed=True, actual=None, threshold=None,
            reason="DISABLED by rubric config — operator override accepted",
        )

    cage_meta = rubric_data.get("cage_meta") or {}
    cage_class = (cage_meta.get("class") or "").strip().lower() if isinstance(cage_meta, dict) else ""
    if cage_class != "audit":
        return _gate(
            name, passed=True, actual=None, threshold=None,
            reason=f"cage_meta.class={cage_class!r} (not audit) — gate not applicable",
        )

    sub_dir = project_dir / "workspace" / "submissions"
    if not sub_dir.exists():
        return _gate(
            name, passed=True, actual=None, threshold=None,
            reason="no submissions yet — gate skipped this iter",
        )

    py_subs = sorted(sub_dir.glob("iter_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not py_subs:
        return _gate(
            name, passed=True, actual=None, threshold=None,
            reason="no Python submissions yet — gate skipped",
        )

    try:
        text = py_subs[0].read_text(encoding="utf-8")
    except Exception:
        return _gate(
            name, passed=True, actual=None, threshold=None,
            reason=f"could not read latest submission ({py_subs[0].name})",
        )

    import re as _re
    hits: list[str] = []
    if _re.search(r"\bfrom\s+unittest\.mock\b|\bimport\s+unittest\.mock\b", text):
        hits.append("unittest.mock import")
    if _re.search(r"\bMagicMock\b", text):
        hits.append("MagicMock reference")
    mock_class_matches = _re.findall(r"^class\s+(Mock[A-Z]\w*)", text, _re.MULTILINE)
    if mock_class_matches:
        hits.append(f"Mock class definitions: {mock_class_matches[:3]}")

    if hits:
        return _gate(
            name=name,
            passed=False,
            actual=str(hits),
            threshold="no Mock-based bypass",
            reason=(
                f"AUDIT-CLASS MOCK BYPASS DETECTED. The bypass exploit imports or defines "
                f"Mocks for components under audit ({hits}) instead of importing the real "
                f"src.ztare.* modules and calling their real signatures. Per the rubric's "
                f"Concrete Bypass Exploit dimension, a bypass against Mocks demonstrates "
                f"behavioral simulation, not a real apparatus vulnerability. Score capped "
                f"at 50. To unlock full credit, rewrite the exploit to import the actual "
                f"components (e.g., `from src.ztare.fit.analogy import build_residual_fingerprint`) "
                f"and run the bypass against their real signatures."
            ),
            penalty=-50,
        )

    return _gate(
        name, passed=True, actual="real-imports", threshold="no Mock-based bypass",
        reason="bypass exploit uses real imports of audited components: PASS",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_global_gates(
    project_dir: Path,
    rubric_data: dict,
    thesis_text: str | None = None,
    evidence_text: str | None = None,
    fit_declaration: dict | None = None,
    score_contract: dict | None = None,
) -> dict[str, Any]:
    """Run all active global behavioral gates and return a gate payload dict.

    The returned dict uses the same schema as deterministic_charter_gates so
    it can be merged into the existing score_contract by the caller.

    Sequencing: uniqueness_gap only fires if evidence_fit passes first.
    """
    gates: list[dict[str, Any]] = []
    total_penalty = 0
    any_hard_fail = False

    # Phase 0: evidence_fit (prerequisite for uniqueness_gap)
    evidence_fit_result = _gate_evidence_fit(rubric_data, project_dir, evidence_text)
    gates.append(evidence_fit_result)
    if not evidence_fit_result["passed"] and evidence_fit_result.get("hard_fail"):
        any_hard_fail = True

    # Phase 1: uniqueness_gap (only if evidence_fit passed)
    if evidence_fit_result["passed"]:
        uq = _gate_uniqueness_gap(rubric_data, thesis_text, score_contract)
        gates.append(uq)
        # Uniqueness gap applies a score cap (handled by caller via penalty field convention)
        # We encode cap as a large negative penalty so caller can decide
        if not uq["passed"]:
            total_penalty += -40  # encode cap-at-60 as -40 if base score would be 100

    # Phase 1: parsimony_violation (independent of evidence_fit)
    pv = _gate_parsimony_violation(rubric_data, evidence_text, fit_declaration)
    gates.append(pv)
    if not pv["passed"]:
        total_penalty += pv.get("penalty", -15)

    # Phase 1: named_import_check (independent of evidence_fit; hard fail on hit)
    ni = _gate_named_import_check(project_dir, thesis_text, rubric_data)
    gates.append(ni)
    if not ni["passed"] and ni.get("hard_fail"):
        any_hard_fail = True

    # Phase 1: extrapolation_gap (independent of evidence_fit)
    eg = _gate_extrapolation_gap(rubric_data, evidence_text)
    gates.append(eg)
    if not eg["passed"] and eg.get("hard_fail"):
        any_hard_fail = True

    # Phase 1: audit_mock_bypass (GP-166 Fix E, 2026-04-25).
    # Audit substrates have all numerical-validation gates disabled by
    # design (no holdout, no fit, no uniqueness gap), leaving only the
    # rubric prose for the LLM judge to grade against. A common LLM
    # failure mode: the mutator writes a "runnable bypass exploit" that
    # imports unittest.mock and builds Mock* classes for the components
    # under audit, then asserts behavior against the Mocks. This is
    # technically runnable but proves nothing about the real codebase.
    # The gate caps audit-class scores at 50 when this pattern is
    # detected in the submitted Python; the judge can still grade the
    # rest of the thesis but cannot award the full bypass-exploit points.
    am = _gate_audit_mock_bypass(rubric_data, project_dir)
    gates.append(am)
    if not am["passed"]:
        # Encode cap-at-50 as a -50 penalty on a base of 100
        total_penalty += am.get("penalty", -50)

    # Autoresearch gaming gates (GP-086 follow-on). These are deterministic
    # AST/provenance checks for fixture-backed autoresearch vectors. Semantic
    # transfer/rigor vectors remain outside this syntactic gate and route
    # through their own carriers.
    from src.ztare.gates.autoresearch_gaming_gates import run_autoresearch_gaming_gates

    psg_results = run_autoresearch_gaming_gates(project_dir, rubric_data)
    gates.extend(psg_results)
    for psg in psg_results:
        if not psg["passed"] and psg.get("hard_fail"):
            any_hard_fail = True
        if not psg["passed"]:
            total_penalty += psg.get("penalty", 0)

    # Semantic gaming carrier gates. These do not claim syntactic proof of
    # semantic failure; they select the appropriate scope/transfer/rigor review
    # carrier and fail closed when that risk is present.
    from src.ztare.gates.semantic_gaming_carrier import run_semantic_gaming_carrier_gates

    sgc_results = run_semantic_gaming_carrier_gates(project_dir, rubric_data, thesis_text, evidence_text)
    gates.extend(sgc_results)
    for sgc in sgc_results:
        if not sgc["passed"] and sgc.get("hard_fail"):
            any_hard_fail = True
        if not sgc["passed"]:
            total_penalty += sgc.get("penalty", 0)

    failed_gates = [g["name"] for g in gates if not g["passed"]]
    return {
        "source": "global_gates",
        "harness_invoked": True,
        "declared": [g["name"] for g in gates],
        "results": gates,
        "failure_count": len(failed_gates),
        "failed_gate_ids": failed_gates,
        "total_penalty": total_penalty,
        "any_hard_fail": any_hard_fail,
    }


def merge_into_score_contract(
    score_contract: dict,
    global_gate_payload: dict,
) -> dict:
    """Merge global gate results into an existing score_contract dict.

    Merges gate results into deterministic_charter_gates, accumulates
    failure_count, and appends hard_fail_reasons if any global gate hard-failed.
    Modifies score_contract in place and returns it.
    """
    existing = score_contract.get("deterministic_charter_gates")
    if not isinstance(existing, dict):
        existing = {"harness_invoked": False, "declared": [], "results": [], "failure_count": 0}

    # Merge results
    existing_results = existing.get("results", [])
    existing_results.extend(global_gate_payload.get("results", []))
    existing["results"] = existing_results
    existing["declared"] = list(existing.get("declared", [])) + global_gate_payload.get("declared", [])
    existing["failure_count"] = int(existing.get("failure_count", 0)) + global_gate_payload.get("failure_count", 0)
    existing["harness_invoked"] = True
    existing["global_gates_fired"] = True

    score_contract["deterministic_charter_gates"] = existing

    # Propagate hard fails to hard_fail_reasons
    if global_gate_payload.get("any_hard_fail"):
        hard_fails = [
            g["name"] for g in global_gate_payload.get("results", [])
            if not g["passed"] and g.get("hard_fail")
        ]
        existing_hfr = score_contract.get("hard_fail_reasons", [])
        if isinstance(existing_hfr, list):
            existing_hfr.extend(hard_fails)
        else:
            existing_hfr = hard_fails
        score_contract["hard_fail_reasons"] = existing_hfr

    # Propagate score penalty
    penalty = global_gate_payload.get("total_penalty", 0)
    if penalty != 0:
        soft_caps = score_contract.get("soft_score_caps", [])
        if not isinstance(soft_caps, list):
            soft_caps = []
        soft_caps.append({
            "cap": None,
            "penalty": penalty,
            "reason": f"global_gates penalty: {penalty} points",
        })
        score_contract["soft_score_caps"] = soft_caps

    return score_contract
