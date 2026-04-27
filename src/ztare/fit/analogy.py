"""GP-164 ANALOGY primitive — L1 cross-domain tool transfer.

When the operator-curated grammar exhausts (no template passes
holdout) AND the apparatus has a non-trivial residual fingerprint,
this primitive queries a frontier LLM with ONLY the structural
residual fingerprint (no domain hints, no variable names, no
charter prose) and asks: *"what mathematical structure from any
domain produces this residual shape?"*

The LLM's response is treated as a HYPOTHESIS, not truth. Returned
candidate forms are added to a per-iter analogy library that feeds
the next COMPRESS cycle. The holdout gate verifies. The deterministic
gate either confirms or kills the cross-domain proposal.

Architectural commitments (per GP-164 seam, Turn 2):

  * **Structural, not semantic.** The LLM sees per-region residual
    statistics, not the substrate's variable names or domain. It can
    say "the residual has the shape of a saturation curve with
    asymptote at y=K" but it cannot say "this looks like
    Michaelis-Menten enzyme kinetics." Structural descriptors feed
    the solver; domain axioms contaminate.
  * **Apparatus disposes, not LLM.** The LLM proposes; the holdout
    gate verifies. A proposed analogy that fails the gate is logged
    as a rejected analogy and discarded.
  * **Audit trail.** Every analogy query and response is persisted to
    `workspace/analogy_log.jsonl` for post-hoc review of which
    cross-domain transfers the apparatus actually attempted.
  * **Conservation discipline.** Analogies are added to the per-iter
    library only; they do NOT modify the operator's static grammar.
    Cross-substrate adoption requires explicit operator promotion to
    `global_primitives/approved/`, same shape as G-CIRC and G-FALSIFY
    precedents.

This module ships in OBSERVE mode by default: it computes the
structural fingerprint and runs the LLM query, but the returned
candidate forms are logged without being injected into the next
COMPRESS cycle. Active mode (rubric flag `enable_analogy_active=True`)
wires the candidates into the next-iter mutator prompt as additional
template hints.

Public API:
  build_residual_fingerprint(fit_result) -> dict
  query_analogy(fingerprint, model_id, *, observe_only=True) -> AnalogyResponse
  log_analogy(workspace_dir, fingerprint, response) -> None
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ── Residual topology helpers (GP-167 Turn 7 enrichment) ────────────────
#
# The original v1 fingerprint exposed only summary statistics: per-category
# residual means and y-magnitude envelope. The gp165 audit (2026-04-25
# night) caught the failure mode: under aggressive C1 anonymization, the
# LLM has no semantic anchor and falls back to vanilla baselines (`a`,
# `a*x+b`, `c*exp(d*x)`). The cross-domain transfer mechanism degrades
# to "what would polyfit do?"
#
# The fix, within the same seam, is to add two things — both structural,
# both upholding C1:
#
#   1. Residual TOPOLOGY features. The shape of the failure, not its
#      magnitude. Smooth vs step, monotone vs non-monotone, regime-break
#      detection, heavy-tail flag. These are the same signals the
#      noise_profile diagnostic uses, but framed as "what kind of failure
#      is this" rather than "what kind of noise is in the data."
#
#   2. Optional LIGHT semantic anchor. The operator may declare a BROAD
#      domain category in the rubric (`analogy_domain_hint = "physics" |
#      "biology" | "math" | "social" | None`). This is the field, not
#      the answer. "Physics" does not name MOND or Planck; "biology"
#      does not name Michaelis-Menten or logistic growth. The category
#      is broad enough to be a domain-prior for the LLM but not specific
#      enough to be answer-recital. Default None → no semantic anchor,
#      strict v1 behavior preserved.
#
# Both additions are read-and-injected at fingerprint build time. The
# query prompt branches on their presence.


def _compute_residuals_for_topology(
    fit_result_json: dict,
    visible_data: list[tuple[dict, float]] | None,
    primary_feature_key: str,
) -> tuple[list[float], list[float]]:
    """Re-compute per-row residuals + primary-feature values from the
    fit result. Returns ([], []) if any input is missing or compilation
    fails — topology features are then omitted from the fingerprint.
    """
    if not visible_data:
        return [], []
    form = fit_result_json.get("form")
    fitted = fit_result_json.get("fitted_params") or {}
    if not form or not fitted:
        return [], []
    try:
        from src.ztare.fit.fit_primitive_features import _safe_compile_form
        fn = _safe_compile_form(form)
    except Exception:
        return [], []
    residuals: list[float] = []
    xs: list[float] = []
    for feats, y_obs in visible_data:
        try:
            y_pred = fn(feats, fitted)
            if y_pred is None or (isinstance(y_pred, float) and (math.isnan(y_pred) or math.isinf(y_pred))):
                continue
            residuals.append(float(y_obs) - float(y_pred))
            v = feats.get(primary_feature_key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                xs.append(float(v))
            else:
                xs.append(0.0)
        except Exception:
            continue
    return residuals, xs


def _residual_topology(
    residuals: list[float], xs: list[float]
) -> dict:
    """Compute structural topology features from per-row residuals.

    All features are dimensionless or ratio-of-residuals — no absolute
    magnitudes, no domain leakage. The features describe the SHAPE of
    the failure surface as the LLM would need to anchor cross-domain
    transfer.
    """
    if len(residuals) < 10 or len(residuals) != len(xs):
        return {"available": False, "reason": "insufficient_rows"}
    try:
        import numpy as np
    except ImportError:
        return {"available": False, "reason": "numpy_unavailable"}

    res = np.asarray(residuals, dtype=float)
    x = np.asarray(xs, dtype=float)
    order = np.argsort(x)
    res_sorted = res[order]
    x_sorted = x[order]
    n = len(res_sorted)

    out: dict[str, Any] = {"available": True, "n_rows": n}

    # Smooth vs step: max |Δresid| / median |Δresid| over sorted-by-x.
    # A smooth surface has all step magnitudes similar; a step
    # discontinuity has one |Δresid| much larger than the rest.
    diffs = np.abs(np.diff(res_sorted))
    if len(diffs) >= 3 and np.median(diffs) > 0:
        ratio = float(np.max(diffs) / np.median(diffs))
        out["max_to_median_step_ratio"] = round(ratio, 2)
        out["shape"] = "step_discontinuity_likely" if ratio > 8.0 else "smooth"
    else:
        out["shape"] = "indeterminate"

    # Monotonicity: Spearman rank correlation of residuals with primary x.
    # Strong positive or negative → form has a missing monotone term in x.
    try:
        from scipy.stats import spearmanr
        rho, p = spearmanr(x_sorted, res_sorted)
        if rho is not None and not math.isnan(rho):
            out["spearman_rho_residuals_vs_x"] = round(float(rho), 3)
            out["spearman_p"] = round(float(p), 4)
            if abs(rho) > 0.3 and p < 0.01:
                out["monotonicity"] = "strong_positive" if rho > 0 else "strong_negative"
            else:
                out["monotonicity"] = "weak_or_none"
    except Exception:
        pass

    # Regime break: a sharp transition in residuals at one location.
    # Use the ratio of the largest single-window step to the spread
    # of windowed means. A real regime break shows ONE big step
    # between adjacent windows; smooth-monotone misspecification
    # shows a graded sequence.
    try:
        nw = max(4, min(8, n // 8))
        if nw >= 4 and n >= nw * 2:
            window_means = np.array([
                float(np.mean(b)) for b in np.array_split(res_sorted, nw)
            ])
            adj_steps = np.abs(np.diff(window_means))
            if len(adj_steps) >= 3 and adj_steps.std() > 0:
                largest_step_z = float(
                    (adj_steps.max() - adj_steps.mean()) / adj_steps.std()
                )
                out["largest_window_step_z"] = round(largest_step_z, 2)
                out["regime_break_likely"] = bool(largest_step_z > 1.5)
            else:
                out["regime_break_likely"] = False
    except Exception:
        pass

    # Heavy tail: kurtosis of residuals. Excess > 2 (Pearson > 5) → likely
    # outlier-driven failure or genuinely heavy-tailed noise.
    try:
        from scipy.stats import kurtosis
        kt = float(kurtosis(res_sorted, fisher=False))
        out["kurtosis_pearson"] = round(kt, 2)
        out["heavy_tail"] = bool(kt > 5.0)
    except Exception:
        pass

    # Sign pattern across sorted-by-x bins. Tells the LLM whether the
    # failure is "always under-predicting" vs "alternating" vs "regime-flip".
    try:
        bins = np.array_split(res_sorted, min(5, max(2, n // 10)))
        signs = [int(np.sign(np.mean(b))) for b in bins if len(b) > 0]
        out["binned_residual_signs"] = signs
        if all(s == signs[0] for s in signs):
            out["sign_pattern"] = "uniform"
        elif signs[0] != signs[-1]:
            out["sign_pattern"] = "regime_flip_endpoints"
        else:
            out["sign_pattern"] = "alternating"
    except Exception:
        pass

    return out


# ── Structural residual fingerprint ─────────────────────────────────────


def build_residual_fingerprint(
    fit_result_json: dict,
    visible_data: list[tuple[dict, float]] | None = None,
    *,
    domain_hint: Optional[str] = None,
    primary_feature_key: str = "x",
) -> dict:
    """Build a STRUCTURAL fingerprint of the prior fit's residuals.

    The fingerprint is intentionally domain-stripped:
      * No feature names (only "feature_0", "feature_1", ...)
      * No variable names from the substrate's evidence files
      * No charter text
      * Only structural statistics (residual sign pattern, magnitude
        envelope, monotonicity of |res| vs each feature, etc.)

    The intent is to make the LLM see the SHAPE of the failure, not
    the answer. The refined contamination posture (2026-04-25 night)
    distinguishes three retrieval cases:

      * Case 1 — retrieve a known FORM, fit new constants from data.
        Fine. This is curve fitting; the apparatus wants the LLM's
        full repertoire of forms.
      * Case 2 — retrieve known CONSTANTS, claim they came from data.
        Bad. The anti-retrieval gate and cold variable names defend
        against this.
      * Case 3 — retrieve a known RESULT, claim the apparatus found it.
        Bad. Cold variables prevent the LLM from knowing what data is
        in front of it.

    GP-167 Turn 7 extensions are aimed at case 1. They restore the
    LLM's ability to anchor cross-domain transfer (which the gp165
    audit showed had degenerated to vanilla baselines under aggressive
    C1) without leaking constants or results.

      * Residual topology features (shape, monotonicity, regime-break,
        heavy-tail, sign pattern). These are derived from per-row
        residuals computed by re-evaluating the fitted form on visible
        data. They describe the SHAPE of where the form fails, which
        is enough structural anchor for form-retrieval (case 1) without
        being constants or results.

      * Optional `domain_hint` (broad field category, operator-set in
        rubric: "physics", "biology", "math", "social", "engineering",
        or None). This is the field, NOT the answer. "Physics" does
        not name MOND; "biology" does not name Michaelis-Menten. The
        category anchors form-retrieval (case 1) without naming
        constants (case 2) or results (case 3). None preserves strict
        v1 behavior.
    """
    fp: dict[str, Any] = {
        "schema_version": "analogy-fp-v2",
        "fit_succeeded": bool(fit_result_json.get("success")),
        "convergence": fit_result_json.get("classification"),
        "n_fit_rows": fit_result_json.get("n_fit_rows"),
        "k_params": fit_result_json.get("k_params"),
        "bic": fit_result_json.get("bic"),
        "max_abs_residual": fit_result_json.get("max_abs_residual"),
        "mean_abs_residual": fit_result_json.get("mean_abs_residual"),
        "pathological": bool(fit_result_json.get("pathological", False)),
    }

    # Per-categorical-group residuals (anonymized)
    res_by_cat = fit_result_json.get("residual_by_category") or {}
    if isinstance(res_by_cat, dict):
        anon: dict[str, dict[str, float]] = {}
        for fk_idx, (fk, vc) in enumerate(res_by_cat.items()):
            if not isinstance(vc, dict):
                continue
            anon_key = f"cat_feature_{fk_idx}"
            anon_inner: dict[str, float] = {}
            for v_idx, (v, stats) in enumerate(vc.items()):
                if isinstance(stats, dict):
                    anon_inner[f"value_{v_idx}"] = float(stats.get("mean_residual", 0.0))
                elif isinstance(stats, (int, float)):
                    anon_inner[f"value_{v_idx}"] = float(stats)
            if anon_inner:
                anon[anon_key] = anon_inner
        fp["residual_by_category_anonymized"] = anon

    # Magnitude envelope across visible rows (if provided)
    if visible_data:
        ys = [y for _, y in visible_data if y is not None]
        if ys:
            ys_abs = [abs(y) for y in ys if y != 0]
            if ys_abs:
                fp["y_min_abs_nonzero"] = min(ys_abs)
                fp["y_max_abs"] = max(ys_abs)
                if min(ys_abs) > 0:
                    fp["y_dynamic_range_decades"] = round(
                        math.log10(max(ys_abs) / min(ys_abs)), 2
                    )
            fp["y_sign_homogeneous"] = (
                all(y >= 0 for y in ys) or all(y <= 0 for y in ys)
            )
            fp["n_visible_rows"] = len(ys)

    # GP-167 Turn 7: residual topology features. The "shape of the
    # failure surface" — what kind of misspecification the current form
    # has — is what the LLM needs to anchor cross-domain transfer.
    # Computed from per-row residuals re-evaluated against the fitted
    # form. Skipped silently if visible_data or fitted form unavailable.
    residuals, xs = _compute_residuals_for_topology(
        fit_result_json, visible_data, primary_feature_key
    )
    if residuals:
        fp["residual_topology"] = _residual_topology(residuals, xs)

    # GP-167 Turn 7: optional light semantic anchor. Operator-declared
    # broad field category. The LLM uses this to choose appropriate
    # FORMS (case 1, fine) — it cannot derive constants or results
    # from a category alone. Validated: must be one of an enumerated
    # set so the operator cannot accidentally smuggle a theory name
    # in this slot.
    _ALLOWED_DOMAIN_HINTS = {
        "physics", "biology", "chemistry", "math", "social",
        "engineering", "economics", "computer_science", "linguistics",
        "ecology", "medicine",
    }
    if domain_hint:
        dh = str(domain_hint).strip().lower()
        if dh in _ALLOWED_DOMAIN_HINTS:
            fp["domain_hint"] = dh
        else:
            fp["domain_hint_rejected"] = (
                f"{dh!r} not in allowed broad-category set; ignored. "
                f"Allowed: {sorted(_ALLOWED_DOMAIN_HINTS)}"
            )

    return fp


# ── LLM query result ────────────────────────────────────────────────────


@dataclass
class AnalogyResponse:
    """Structured response from the LLM analogy query."""
    candidate_forms: list[str] = field(default_factory=list)
    reasoning: str = ""
    structural_descriptors: list[str] = field(default_factory=list)
    raw_response: str = ""
    model_id: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    error: Optional[str] = None


# ── LLM query (single call, no retries) ────────────────────────────────


def _build_query_prompt(fingerprint: dict) -> str:
    """Construct the LLM query prompt.

    The prompt distinguishes three retrieval cases (per the 2026-04-25
    night refinement of contamination posture) and explicitly asks for
    case 1 — known FORMS that match the structural shape — while
    forbidding case 2 (constants from training) and case 3 (specific
    results from training).

    When the fingerprint includes residual topology features, the prompt
    surfaces them so the LLM can choose forms whose failure-shape
    matches. When it includes a domain_hint (broad field category), the
    prompt narrows the form-pool to that field's idioms — still without
    naming the answer.
    """
    fp_json = json.dumps(fingerprint, indent=2, sort_keys=True)
    domain_hint = fingerprint.get("domain_hint")
    topology = fingerprint.get("residual_topology") or {}

    # Domain-hint clause — present only when operator declared a category
    if domain_hint:
        domain_clause = (
            f"The operator has declared a broad field category: "
            f"`{domain_hint}`. This is the FIELD, not the answer. Use it "
            f"to choose forms idiomatic to {domain_hint} (case 1: known "
            f"forms with new constants from data — fine). Do NOT name "
            f"specific theories or results within {domain_hint} (case 2: "
            f"constants from training — forbidden) (case 3: specific "
            f"results from training — forbidden). Forms only.\n\n"
        )
    else:
        domain_clause = (
            "No domain hint provided. Propose forms drawn from any "
            "field. Do not name specific theories or results.\n\n"
        )

    # Topology clause — present only when topology features computed
    if topology.get("available"):
        shape = topology.get("shape", "indeterminate")
        monotonicity = topology.get("monotonicity", "unknown")
        regime_break = topology.get("regime_break_likely", False)
        heavy_tail = topology.get("heavy_tail", False)
        sign_pattern = topology.get("sign_pattern", "unknown")
        topology_clause = (
            "RESIDUAL FAILURE SHAPE (where the current form fails):\n"
            f"  - shape: {shape}\n"
            f"  - monotonicity vs primary feature: {monotonicity}\n"
            f"  - regime break likely: {regime_break}\n"
            f"  - heavy tail: {heavy_tail}\n"
            f"  - sign pattern across binned ranges: {sign_pattern}\n\n"
            "Choose candidate forms whose structural shape matches "
            "this failure pattern. For example, a regime-break-likely "
            "+ uniform-sign pattern suggests a crossover or "
            "saturation form. A strong-monotone signal suggests a "
            "missing monotone term. Heavy-tail suggests a robust-loss "
            "or outlier-aware reformulation, not a different form.\n\n"
        )
    else:
        topology_clause = (
            "No residual topology data available; propose forms based "
            "on the summary statistics in the fingerprint alone.\n\n"
        )

    return (
        "You are a mathematical pattern matcher for a research "
        "apparatus that searches closed-form expressions. The "
        "apparatus has fitted a candidate form to data and produced "
        "a residual fingerprint that describes the SHAPE of where the "
        "form fails. Your task is to propose candidate MATHEMATICAL "
        "FORMS whose structural shape matches the failure shape.\n\n"
        "CONTAMINATION POSTURE (read carefully):\n"
        "  - Case 1 — retrieve a known FORM, fit new constants from "
        "data: this is what we want. Use your full repertoire of forms.\n"
        "  - Case 2 — retrieve known CONSTANTS from training and claim "
        "they came from data: forbidden. Do not name specific numerical "
        "constants from any theory.\n"
        "  - Case 3 — retrieve a known RESULT from training and claim "
        "the apparatus found it: forbidden. Do not name specific "
        "phenomena or theories.\n\n"
        + domain_clause
        + topology_clause +
        "Output format (strict JSON, no markdown):\n"
        "  {\n"
        '    "candidate_forms": ["expr1", "expr2", "expr3"],\n'
        '    "structural_descriptors": ["what shape each form captures"],\n'
        '    "reasoning": "<2-3 sentences on the structural match>"\n'
        "  }\n\n"
        "Constraints:\n"
        "  1. Propose 3-5 candidate forms. Each form is a closed-form "
        "expression in placeholder variables x, y, z (or features['x'] "
        "/ params['c'] notation if more natural). No domain names.\n"
        "  2. Each form must be NON-TRIVIAL — strictly more structural "
        "than `a`, `a*x+b`, `a*exp(b*x)`. If you can only produce "
        "those baselines, the fingerprint is too sparse and you should "
        "return an empty list with a note.\n"
        "  3. State the structural pattern each candidate captures.\n"
        "  4. If the fingerprint is too sparse to discriminate, return "
        "candidate_forms: [] with reasoning explaining what additional "
        "topology signal would be needed.\n\n"
        "Residual fingerprint:\n"
        f"{fp_json}\n"
    )


def query_analogy(
    fingerprint: dict,
    *,
    model_id: Optional[str] = None,
    runtime: Any = None,
    observe_only: bool = True,
    timeout_seconds: int = 90,
) -> AnalogyResponse:
    """Single-call LLM query for cross-domain analogy candidates.

    Routes through `src.ztare.common.llm_runtime.LLMRuntime.call_text`,
    which is provider-agnostic (OpenAI / Anthropic / Gemini), already
    has the retry / fallback / token-tracking discipline used by the
    rest of the apparatus, and respects `ZTARE_DISABLE_MODEL_FALLBACK`
    for cross-family hygiene.

    The caller MUST provide a `model_id` — typically the run's judge
    model (already configured per cross-family discipline). Defaulting
    to a hard-coded model is forbidden because (a) it forks the run's
    declared model surface and (b) it breaks the cross-family epistemic
    airgap when the judge is intentionally on a different provider.

    Args:
        fingerprint: structural residual fingerprint (already
            anonymized by build_residual_fingerprint).
        model_id: required. The model to query. Convention: the run's
            judge model. Caller (autoresearch_loop dispatch hook) is
            responsible for selecting and passing it.
        runtime: optional LLMRuntime instance. If None, a fresh one is
            instantiated (same provider clients as the rest of the run).
        observe_only: True (default) — caller logs the response but
            does NOT inject candidates into the mutator prompt this
            iter. False — caller is responsible for injection (the
            briefing provider does this when enable_analogy_active=True).
        timeout_seconds: per-attempt timeout passed to call_text.

    Returns:
        AnalogyResponse with .candidate_forms populated on success,
        .error set on failure. Failure is non-fatal — caller should
        skip injection when error is set.
    """
    if not model_id:
        return AnalogyResponse(
            error=(
                "no model_id supplied; analogy must use the run's judge "
                "or mutator model (cross-family hygiene). Pass model_id "
                "explicitly from the dispatch hook."
            ),
        )

    # Lazy import to avoid forcing llm_runtime as a module-level dep
    # when analogy.py is used in a unit-test context.
    if runtime is None:
        from src.ztare.common.llm_runtime import LLMRuntime as _LLMRuntime
        runtime = _LLMRuntime()

    prompt = _build_query_prompt(fingerprint)

    try:
        response = runtime.call_text(
            prompt,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            request_label="gp164_analogy",
            retries=2,
        )
    except Exception as e:
        return AnalogyResponse(
            error=f"{type(e).__name__}: {e!s}"[:300],
            model_id=model_id,
        )

    raw = response.text or ""
    usage = response.usage if hasattr(response, "usage") else None
    tokens_in = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    tokens_out = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    actual_model_id = getattr(response, "model_id_used", model_id) or model_id

    # Parse the LLM's JSON response. May arrive wrapped in markdown
    # fences depending on provider; strip and retry once.
    parsed: dict = {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            stripped = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            )
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return AnalogyResponse(
                error="LLM returned non-JSON response",
                raw_response=raw[:500],
                model_id=actual_model_id,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

    candidate_forms = parsed.get("candidate_forms") or []
    structural_descriptors = parsed.get("structural_descriptors") or []
    reasoning = parsed.get("reasoning") or ""

    # Post-call baseline rejector (panel review 2026-04-25 night). The
    # prompt instructs the LLM to return [] rather than baselines, but
    # an LLM under marginal-fingerprint conditions can still emit
    # `a*x+b` with a paragraph of justification. This is exactly the
    # vanilla-collapse failure mode gp165 caught. Insurance: scan each
    # candidate after parsing; if ALL of them match the baseline
    # signature, treat the response as "vanilla collapse" and return
    # an empty list with an explicit error tag so the caller can log
    # the collapse without injecting useless forms into the briefing.
    BASELINE_PATTERNS = [
        # constant only
        r"^\s*[a-zA-Z]\s*$",
        # ax + b family
        r"^\s*[+\-]?\s*[a-zA-Z]\s*\*\s*[xyzXYZ]\s*([+\-]\s*[a-zA-Z])?\s*$",
        r"^\s*[a-zA-Z]\s*[+\-]\s*[a-zA-Z]\s*\*\s*[xyzXYZ]\s*$",
        # a*exp(b*x) family (unary scale only)
        r"^\s*[a-zA-Z]\s*\*\s*exp\s*\(\s*[+\-]?\s*[a-zA-Z]\s*\*\s*[xyzXYZ]\s*\)\s*$",
        r"^\s*exp\s*\(\s*[+\-]?\s*[a-zA-Z]\s*\*\s*[xyzXYZ]\s*\)\s*$",
        # a*log(b*x) family
        r"^\s*[a-zA-Z]\s*\*\s*log\s*\(\s*[a-zA-Z]?\s*\*?\s*[xyzXYZ]\s*\)\s*$",
        # a/x or a*x
        r"^\s*[a-zA-Z]\s*[*/]\s*[xyzXYZ]\s*$",
    ]
    import re as _re_baseline
    cleaned_forms = [str(c).strip() for c in candidate_forms if c]
    if cleaned_forms:
        is_baseline = lambda f: any(
            _re_baseline.match(p, f) for p in BASELINE_PATTERNS
        )
        all_baseline = all(is_baseline(f) for f in cleaned_forms)
        if all_baseline:
            return AnalogyResponse(
                candidate_forms=[],
                structural_descriptors=[str(s) for s in structural_descriptors if s][:8],
                reasoning=str(reasoning)[:500],
                raw_response=raw[:2000],
                model_id=actual_model_id,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                error=(
                    "vanilla_collapse: all returned candidates matched "
                    "baseline patterns (a, a*x+b, a*exp(b*x), a*log(x), "
                    "a*x, a/x). Per the prompt's guidance, this is a "
                    "signal that the residual fingerprint is too sparse "
                    "to discriminate non-trivial forms; returning empty "
                    "candidate list."
                ),
            )

    return AnalogyResponse(
        candidate_forms=[str(c) for c in candidate_forms if c][:5],
        structural_descriptors=[str(s) for s in structural_descriptors if s][:8],
        reasoning=str(reasoning)[:500],
        raw_response=raw[:2000],
        model_id=actual_model_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )


# ── Persistence ─────────────────────────────────────────────────────────


def log_analogy(
    workspace_dir: Path,
    fingerprint: dict,
    response: AnalogyResponse,
    iter_index: Optional[int] = None,
) -> None:
    """Persist the analogy query and response for operator audit."""
    workspace_dir = Path(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    log_path = workspace_dir / "analogy_log.jsonl"
    record = {
        "iter": iter_index,
        "fingerprint": fingerprint,
        "candidate_forms": response.candidate_forms,
        "structural_descriptors": response.structural_descriptors,
        "reasoning": response.reasoning,
        "model_id": response.model_id,
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
        "error": response.error,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


# ── Engagement predicate ────────────────────────────────────────────────


def should_engage(
    rubric_data: dict,
    fit_result_json: dict,
    stagnation_count: int,
) -> tuple[bool, str]:
    """Decide whether ANALOGY should fire on this iter.

    Triggers:
      1. rubric flag enable_analogy=true
      2. prior fit succeeded (we have a residual fingerprint)
      3. stagnation_count >= analogy_min_stagnation (default 3) OR
         pathological flag is set on the prior fit

    Returns (should_engage, reason).
    """
    if not rubric_data.get("enable_analogy", False):
        return False, "rubric flag enable_analogy is False"
    if not fit_result_json:
        return False, "no prior fit result"
    if not fit_result_json.get("success"):
        return False, "prior fit failed; analogy needs a residual fingerprint"
    min_stag = int(rubric_data.get("analogy_min_stagnation", 3))
    pathological = bool(fit_result_json.get("pathological", False))
    if stagnation_count < min_stag and not pathological:
        return False, (
            f"stagnation_count={stagnation_count} < {min_stag} "
            f"and prior fit not flagged pathological"
        )
    return True, (
        f"engaged (stagnation={stagnation_count} >= {min_stag}"
        + (" or pathological" if pathological else "")
        + ")"
    )


# ── R15 Cage adapter (per GP-157 §3a) ──────────────────────────────────


def r15_can_handle(substrate, candidate) -> tuple[bool, str]:
    """R15 ANALOGY engagement predicate.

    Engages when:
      - rubric.enable_analogy is true (analogy is opt-IN: it makes a
        cold-LLM call with token cost, so default OFF is the right
        posture for general substrates)
      - candidate exposes a successful prior fit + stagnation_count
      - should_engage's stagnation/pathology gating returns True

    Refusal reasons preserved verbatim from should_engage so existing
    log readers continue to see the same diagnostic strings.
    """
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    if not bool(rubric.get("enable_analogy", False)):
        return False, "R15 refused: rubric.enable_analogy is False"
    fit_json = getattr(candidate, "fit_result_json", None)
    if not fit_json:
        return False, "R15 refused: candidate.fit_result_json missing or empty"
    stag = int(getattr(candidate, "stagnation_count", 0) or 0)
    engage, reason = should_engage(rubric, fit_json, stag)
    if not engage:
        return False, f"R15 refused: {reason}"
    return True, f"R15 engaged ({reason})"


def r15_run(substrate, candidate) -> dict:
    """POST_FIT adapter: build residual fingerprint, query the analogy
    LLM, log to workspace/analogy_log.jsonl. Returns a summary dict.

    Behavior preserves the legacy direct-wire semantics: defaults to
    OBSERVE mode unless rubric.enable_analogy_active is true; uses the
    iter's MUTATOR model unless rubric.analogy_model_id overrides;
    surfaces the same diagnostic shape on errors.
    """
    from pathlib import Path as _Path
    rubric = getattr(substrate, "rubric_flags", {}) or {}
    workspace_dir = _Path(getattr(candidate, "workspace_dir", _Path(".") / "workspace"))
    iter_index = int(getattr(candidate, "iter_index", 0) or 0)
    fit_json = getattr(candidate, "fit_result_json", None) or {}
    visible = getattr(candidate, "visible_pairs", None) or []
    runtime = getattr(candidate, "runtime", None)
    mutator_model_id = str(getattr(candidate, "mutator_model_id", "") or "")

    domain_hint = rubric.get("analogy_domain_hint")
    primary_key = str(rubric.get("framer_primary_feature_key", "x"))

    try:
        fp = build_residual_fingerprint(
            fit_json, visible,
            domain_hint=domain_hint,
            primary_feature_key=primary_key,
        )
    except Exception as exc:
        return {
            "engaged": True,
            "skipped": True,
            "reason": f"fingerprint build failed: {type(exc).__name__}: {exc}",
        }

    model_id = str(rubric.get("analogy_model_id") or mutator_model_id)
    if not model_id:
        return {
            "engaged": True,
            "skipped": True,
            "reason": "no model_id available (rubric.analogy_model_id and candidate.mutator_model_id both empty)",
        }
    observe_only = not bool(rubric.get("enable_analogy_active", False))

    try:
        response = query_analogy(
            fp,
            model_id=model_id,
            runtime=runtime,
            observe_only=observe_only,
        )
        log_analogy(workspace_dir, fp, response, iter_index=iter_index)
    except Exception as exc:
        return {
            "engaged": True,
            "skipped": True,
            "reason": f"query/log failed: {type(exc).__name__}: {exc}",
        }

    return {
        "engaged": True,
        "n_candidates": len(response.candidate_forms),
        "candidates_preview": [c[:120] for c in response.candidate_forms[:3]],
        "model_id": response.model_id,
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
        "error": response.error,
    }


def register_r15_gate(cage) -> None:
    """Register R15 ANALOGY gate with a Cage instance. POST_FIT phase."""
    try:
        from src.ztare.gates.cage import Gate
    except ImportError:
        return
    g = Gate(
        name="R15_analogy",
        phase="POST_FIT",
        can_handle=r15_can_handle,
        run=r15_run,
        dependencies=[],
    )
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        cage.gates[g.name] = g
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None
