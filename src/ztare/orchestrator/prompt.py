"""GP-157 v5.0 Phase 4d — substrate-aware mutator prompt primitives.

Real fix for the gp159 mutator-empty-Python bug: the mutator prompt is
substrate-class-blind. The apparatus has THREE concurrent test_model.py
contracts (locked down 2026-04-25 after gp159 wrong-class
migration incident):

  Contract A — Assert-based discriminator suite. Mutator writes
              `def I_model(d, params=...)` plus `assert ...` blocks.
              Used by: legacy 1D substrates without authored
              test_model.py. Rubric pattern: cage_meta.class="1d".

  Contract B — Feature-dict I_model override.
              `def I_model(features: dict) -> float`.
              Used by: nd_features substrates with authored test_model.py
              + features.py (gp154 family). Rubric pattern:
              cage_meta.class ∈ {nd_features, audit, literature, proof_target}.

  Contract C — Scalar I_model override (1D with authored test_model.py).
              `def I_model(d: float, params: dict = ...) -> float`.
              Used by: 1D substrates that author their own test_model.py
              with VISIBLE_SET/HOLDOUT_SET embedded (gp159, gp160, gp161,
              gp145, gp146). Rubric pattern: cage_meta.class="1d" AND no
              fit primitive AND test_model.py is substrate-authored.

The bug we shipped Phase 4d to fix was the Contract A↔B confusion:
when neither fit primitive is engaged AND the substrate is custom
(authored its own test_model.py + features.py), the standard mutator
prompt describes Contract A while evidence.txt describes Contract B.
The mutator (gpt-4.1 in particular) sees the conflict and writes
nothing → I_model returns NaN → fail.

The follow-on bug (gp159 wrong-class migration) was Contract C: when
gp159/160/161 (Contract C substrates) were migrated to
cage_meta.class="nd_features", this module's Contract B hint fired
and told the mutator `from features import visible_rows`. Those
substrates have no features.py — R1 then rejected the import.

To prevent this class of bug recurring, `verify_class_consistency_with_substrate`
checks the cage_meta.class declaration against filesystem reality
before any contract hint is emitted.

This module emits a substrate_contract_hint string driven by:
  - cage_meta.class            — nd_features / audit / literature / proof_target
  - enable_fit_primitive       — when True, Contract A handled elsewhere
  - enable_fit_primitive_features — when True, separate FEATURE-VECTOR contract block fires

Returns "" when no hint is needed (existing prompt blocks already cover
the case). Wire one slot into the mutator prompt assembly; this module
contains the conditional logic + tests.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Optional

from ztare.research_director.primitive_class_rotation import (
    PrimitiveClassRotationDeclaration,
    PrimitiveClassTrackingResult,
    append_explored_primitive_class,
    extract_primitive_class_name,
    extract_proposal_class_name,
    maybe_track_primitive_class_rotation,
    read_cross_substrate_primitive_classes,
    read_explored_primitive_classes,
    should_track_primitive_class_proposal,
    summarize_explored_primitive_classes,
)


def select_specialized_submission_prompt(
    rubric_data: Mapping[str, Any],
    *,
    project_dir: str | Path,
    dynamics_assumption: str | None = None,
) -> dict[str, str] | None:
    """Return the prompt sections owned by a typed submission contract.

    The autoresearch loop is a general-purpose dispatcher.  Contract-specific
    vocabulary and teaching text live here; the loop receives only rendered
    sections plus an opaque contract id.
    """
    from ztare.orchestrator.submission_path_helpers import (
        is_worldmodel_submission_contract,
    )

    if not is_worldmodel_submission_contract(dict(rubric_data)):
        return None

    from ztare.validator.core.worldmodel_prompt_context import (
        strategy_card_obligation_prompt,
    )
    from ztare.validator.worldmodel_typed_payload import (
        worldmodel_typed_payload_contract_prompt,
    )

    typed_contract = worldmodel_typed_payload_contract_prompt()
    if (dynamics_assumption or "").strip().lower() == "lawful_time":
        typed_contract = worldmodel_typed_payload_contract_prompt("lawful_time")
    style_guide = """
    STYLE GUIDE — EXECUTABLE TRANSITION-LAW MODE:
        - Name the proposed causal object and the invariant that identifies it.
        - Treat colors, coordinates, clock values, and adapter fields as observations;
          they may witness an identity but cannot define it without a transport rule.
        - Separate environment/epoch transitions from within-epoch dynamics.
        - State the nearest rival transition law and the shortest replay witness that
          distinguishes the two carriers.
        - Keep substrate vocabulary in the typed payload or adapter-facing carrier.
    """
    output_requirements = f"""
    CRITICAL OUTPUT REQUIREMENT (THE EXECUTABLE TRANSITION LAW):
        - Return a typed payload whose candidate is a WORLD_MODEL_SPEC, PROGRAM, or step(grid, action, t) carrier.
        - PARAMETRIC_FORM, LAGRANGIAN, MODEL_PARAMS, and assertion-only suites are outside this carrier category.
        - A prose explanation cannot substitute for deterministic replay over visible transitions plus held-out rollout.

    {typed_contract}

    {strategy_card_obligation_prompt(project_dir)}
    """
    return {
        "contract_id": "worldmodel_transition.v1",
        "style_guide": style_guide,
        "output_requirements": output_requirements,
    }


# Substrate classes for which the I_model OVERRIDE contract (Contract B,
# `I_model(features: dict) -> float`) is the authoritative test_model.py
# shape. These substrates author their own test_model.py + features.py;
# the apparatus does NOT generate test_model.py from a FIT_DECLARATION block.
#
# NARROWED 2026-04-25: previously included {audit, literature,
# proof_target} but those substrates do NOT use the I_model(features)
# contract — audit substrates score on critique, literature on prose,
# proof_target on Lean tactics. Injecting the feature-dict hint for them
# was wrong. Per-class hints for those substrates are deferred until a
# concrete need surfaces. cage_meta.class for those classes still drives
# verify_class_consistency_with_substrate; only the prompt hint is
# class-specific.
_OVERRIDE_CONTRACT_CLASSES: frozenset[str] = frozenset({
    "nd_features",
})

# Substrate classes for which Contract C (scalar 1D `I_model(d, params=...) -> float`)
# is in force when the substrate authors its own test_model.py and no fit
# primitive is engaged. Only "1d" qualifies; other classes use Contract B
# above or have their own contracts.
_SCALAR_OVERRIDE_CONTRACT_CLASSES: frozenset[str] = frozenset({"1d"})


_I_MODEL_SCALAR_CONTRACT_HINT = """
    ### 🛑 AUTHORITATIVE CONTRACT — I_model SCALAR (Contract C) 🛑

    **THIS SECTION OVERRIDES ANY test_model.py SHAPE DESCRIBED ELSEWHERE.**
    If the prompt also includes a "current_test_model.py" snippet whose
    shape conflicts with the rules below, FOLLOW THIS SECTION, NOT THAT
    SNIPPET. The current_test_model snippet is for reference of the
    SCIENTIFIC content (parameters, functional form), NOT the structural
    shape.

    This substrate authors its own test_model.py with VISIBLE_SET +
    HOLDOUT_SET embedded (gp159 / gp160 / gp161 / gp145 / gp146 pattern).
    No fit primitive is engaged. The apparatus does NOT write test_model.py
    for you. You must.

    **Required test_model.py shape (copy this skeleton, edit the body):**

        # Module-level constants. The apparatus imports test_model.py;
        # whatever is at module scope runs at import.
        MODEL_PARAMS = {}        # populated by the apparatus AFTER fit;
                                 # may also already contain values from a
                                 # prior champion — either case is fine,
                                 # I_model must work for BOTH.

        VISIBLE_SET = [...]      # keep / regenerate from the scaffold
        HOLDOUT_SET = [...]

        def I_model(d, params=None):
            \"\"\"Scalar prediction. d is a float; params is a dict OR None.\"\"\"
            p = params if params is not None else MODEL_PARAMS
            a = p.get('a', 1.0)        # ALWAYS use .get with a default
            b = p.get('b', 0.0)
            return a * d + b           # always return a finite float

    **Hard rules — violations score zero:**
      1. DO NOT call `I_model(...)` at module scope. Not for sanity checks,
         not for asserts, not for "validating params", not at all. The
         apparatus runs test_model.py at IMPORT time when MODEL_PARAMS may
         be empty {}; any module-level call detonates the substrate.
      2. DO NOT define `_post_fit_sanity()`, `_validate()`, `_check()`,
         or any helper that buries asserts in a function the apparatus
         never invokes. Asserts go INSIDE I_model's body if they go
         anywhere; defer-them-to-a-helper is the gp159 anti-pattern that
         this hint exists to prevent.
      3. I_model MUST handle BOTH `params={}` (empty, on first import)
         AND `params={...filled...}` (post-fit). Use `p.get(name, default)`
         universally. Never `p[name]` — KeyError → caught → NaN.
      4. NEVER return `float('nan')`, `math.nan`, `np.nan`, or a list/dict/None
         from I_model. Return ONE finite float per call. Period.
      5. The CURRENT test_model.py shown in this prompt may have inherited
         non-empty MODEL_PARAMS — that is the apparatus's post-fit state,
         NOT a contract change. Your new test_model.py still starts with
         `MODEL_PARAMS = {}`. The apparatus will refill it on this iter.

    **What the apparatus does:**
      Imports test_model.py → calls I_model on each row's `d` → compares
      to `y`. Visible MRE drives fitting; holdout MRE gates the score.
      Both must be finite floats below the rubric threshold.

    **Why this hint exists:**
      gp159 mutator emitted the deferred-`_post_fit_sanity` anti-pattern
      twice in a row (iters 2-3, score 0). The mutator inferred a
      "module-level guard prohibition" and tried to comply by hiding
      ALL validation in non-called helpers, which left I_model returning
      NaN. The fix is: keep `def I_model(...)` simple, with `.get(default)`
      for every param read, and stop trying to be clever about
      module-load-time validation.
"""


_I_MODEL_OVERRIDE_CONTRACT_HINT = """
    ### 🛑 AUTHORITATIVE CONTRACT — I_model FEATURES (Contract B) 🛑

    **THIS SECTION OVERRIDES ANY test_model.py SHAPE DESCRIBED ELSEWHERE.**
    If the prompt also includes a "current_test_model.py" snippet whose
    structural shape conflicts with the rules below, FOLLOW THIS SECTION,
    NOT THAT SNIPPET. The current_test_model snippet is for reference
    of SCIENTIFIC content, NOT structural shape.

    ### CUSTOM SUBSTRATE — I_model OVERRIDE CONTRACT (read carefully)

    This substrate authors its own test_model.py and features.py. The
    1D fit primitive and the N-D feature-vector fit primitive are BOTH
    OFF. The apparatus does NOT write test_model.py for you. You must.

    **Required test_model.py shape:**

        # Substrate scaffold: features.py is on sys.path and exports
        # FEATURES, feature_keys(), get_features(id), visible_rows(),
        # holdout_rows(). Do not redefine those — import them.
        from features import visible_rows, holdout_rows

        VISIBLE_SET = visible_rows()   # list of (id, y_observed, features_dict)
        HOLDOUT_SET = holdout_rows()   # same shape, held out from VISIBLE_SET

        def I_model(features):
            \"\"\"Return a float prediction for one row's features dict.

            features is a dict like {{'log10_N_params': 8.0, 'fit_convention': 'kaplan', ...}}.
            Return a single float (NOT NaN, NOT inf, NOT a list).
            \"\"\"
            # Your candidate goes here. Example skeleton:
            x = features.get('log10_N_params', 0.0)
            return -x * 0.07 + 1.5    # placeholder; substitute your form

    **What you are FORBIDDEN to do:**
      - Write `assert ...` based discriminator tests in test_model.py.
        That is the legacy 1D contract; it does NOT engage on this substrate.
      - Return NaN, inf, list, dict, or None from I_model.
      - Use module-level state that mutates per-call.
      - Re-implement visible_rows()/holdout_rows() — import them from features.

    **What the apparatus does with your I_model:**
      The gate harness imports test_model.py, calls I_model on every row
      in VISIBLE_SET to compute visible MRE, calls I_model on every row
      in HOLDOUT_SET to compute holdout MRE. Both must be finite floats.
      A NaN-returning I_model is a hard failure — apparatus reports
      "test_suite_status: fail_assert" and your iteration scores zero.

    **Why this hint is here:**
      Earlier custom-substrate runs hit a contract collision: the
      standard prompt described assert-based tests while evidence.txt
      described I_model override. gpt-4.1 wrote nothing, I_model
      returned NaN, all iterations failed. This explicit contract block
      removes the ambiguity.
"""


def _no_fit_primitive(rubric_data: Mapping[str, Any]) -> bool:
    """True iff neither legacy 1D nor N-D feature fit primitive is engaged."""
    if bool(rubric_data.get("enable_fit_primitive", False)):
        return False
    if bool(rubric_data.get("enable_fit_primitive_features", False)):
        return False
    return True


def _declared_class(rubric_data: Mapping[str, Any]) -> str:
    cage_meta = rubric_data.get("cage_meta") or {}
    if not isinstance(cage_meta, Mapping):
        return ""
    return (cage_meta.get("class") or "").strip().lower()


def needs_override_contract_hint(rubric_data: Mapping[str, Any]) -> bool:
    """Return True iff the mutator should be told the Contract B
    (feature-dict I_model override).

    Triggers iff ALL of:
      - enable_fit_primitive is False (1D contract not in force)
      - enable_fit_primitive_features is False (N-D feature contract not in force)
      - cage_meta.class is one of the override-substrate classes

    Ignores legacy 1D substrates (no cage_meta or class="1d") — they
    use Contract C if they author their own test_model.py.
    """
    if not _no_fit_primitive(rubric_data):
        return False
    return _declared_class(rubric_data) in _OVERRIDE_CONTRACT_CLASSES


def needs_scalar_contract_hint(
    rubric_data: Mapping[str, Any],
    project_dir: Optional[Path] = None,
) -> bool:
    """Return True iff the mutator should be told Contract C
    (scalar I_model override for 1D substrates with authored test_model.py).

    Triggers iff ALL of:
      - No fit primitive engaged
      - cage_meta.class == "1d"
      - project_dir provided AND `test_model.py` exists with `def I_model(`
        (scaffold mutator-authored, not generated by fit primitive)
      - project_dir does NOT have `features.py` (Contract B substrates
        are excluded — those have features.py and use override hint)

    Without project_dir, returns False — silent rather than noisy. The
    autoresearch_loop wires PROJECT_DIR; standalone callers can omit.
    """
    if not _no_fit_primitive(rubric_data):
        return False
    if _declared_class(rubric_data) not in _SCALAR_OVERRIDE_CONTRACT_CLASSES:
        return False
    if project_dir is None:
        return False
    test_model_path = project_dir / "test_model.py"
    if not test_model_path.exists():
        return False
    if (project_dir / "features.py").exists():
        # Substrate with features.py is Contract B territory; do not
        # double-inject Contract C.
        return False
    try:
        text = test_model_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    # Authored test_model.py has a def I_model(; if absent, the substrate
    # is in some other state we should not override.
    return "def I_model(" in text


def select_substrate_contract_hint(
    rubric_data: Mapping[str, Any],
    project_dir: Optional[Path] = None,
) -> str:
    """Return the prompt block to inject, or "" when no hint is needed.

    Resolution order (Contract B before Contract C — they're mutually
    exclusive at the rubric level since cage_meta.class differs):
      1. Contract B (`I_model(features)`) — feature-dict override.
      2. Contract C (`I_model(d, params=...)`) — scalar override.

    Single seam for substrate-class-aware contract instructions. Wire
    once into the mutator prompt assembly; logic + tests live here.
    """
    if needs_override_contract_hint(rubric_data):
        return _I_MODEL_OVERRIDE_CONTRACT_HINT
    if needs_scalar_contract_hint(rubric_data, project_dir=project_dir):
        return _I_MODEL_SCALAR_CONTRACT_HINT
    return ""


def active_contract_label(
    rubric_data: Mapping[str, Any],
    project_dir: Optional[Path] = None,
) -> str:
    """Return a one-line summary of the active test_model.py contract.

    Prompt-engineer panel recommendation 2026-04-25: LLMs anchor on
    first + last sections of the prompt; surface the active contract at
    BOTH ends. This function returns the short label suitable for a top-
    of-prompt anchor; select_substrate_contract_hint returns the full
    block for the terminal-third position.

    Returns "" when no specific contract is in force (Contract A legacy
    path is the silent default).
    """
    if needs_override_contract_hint(rubric_data):
        return (
            "ACTIVE CONTRACT: B (I_model(features: dict) -> float). "
            "See 'I_model FEATURES' block below — it OVERRIDES any "
            "test_model.py shape implied elsewhere in this prompt."
        )
    if needs_scalar_contract_hint(rubric_data, project_dir=project_dir):
        return (
            "ACTIVE CONTRACT: C (I_model(d: float, params=None) -> float). "
            "See 'I_model SCALAR' block below — it OVERRIDES any "
            "test_model.py shape implied elsewhere in this prompt."
        )
    return ""


# ────────────────────────────────────────────────────────────────────
# PARAMETRIC_FORM theorem-packet (2026-05-06)
# ────────────────────────────────────────────────────────────────────
# Borrows from Codex NS Track B Phase 5CV+ theorem-packet pattern:
# pre-declare the grammar BEFORE the mutator generates content. Reduces
# R1 compiler-bounce noise (PARAMETRIC_FORM AST whitelist failures) by
# making the whitelist visible at top of prompt + showing class-specific
# valid stubs.
#
# Opt-in via rubric flag `enable_parametric_form_theorem_packet: true`.
# Default off — preserves existing behavior. Operator enables per
# substrate (qualitative substrates that don't actually fit benefit
# most; numeric substrates already do fine without it).

_PARAMETRIC_FORM_ALLOWED_NAMES = (
    # Arithmetic operators are AST-level, not function calls — implicit.
    # Function calls allowed:
    "abs", "bool", "cos", "erf", "exp", "float", "int", "len",
    "log", "log10", "max", "min", "pow", "sigmoid", "sin", "sqrt",
    "str", "tan", "tanh", "where",
)

_PARAMETRIC_FORM_FORBIDDEN_COMMON_FAILS = (
    # Names mutators frequently try that get R1-bounced. Listing
    # them explicitly with "DO NOT use" is more effective than
    # listing only the allowed set, per Codex NS theorem-packet
    # observation.
    "isinstance", "sum", "is_significant", "any", "all", "round",
    "type", "hasattr", "getattr", "callable", "format", "print",
    "input", "open", "eval", "exec", "compile", "globals", "locals",
)

# Per-substrate-class ceremonial-stub examples. For substrates where
# PARAMETRIC_FORM doesn't actually fit (qualitative / audit / proof_target),
# the form is just a syntactic placeholder; these stubs are valid + cheap.
_PARAMETRIC_FORM_STUB_EXAMPLES_BY_CLASS: dict[str, list[str]] = {
    "audit": [
        "1 if rival_active == 0 and loop_revived == 1 and patches_delta >= 2 else 0",
        "int(score >= threshold) if features.get('eligible', False) else 0",
        "params['a'] * (1 if features.get('flag') == 'on' else 0)",
    ],
    "literature": [
        "1 if features.get('citation_count', 0) >= params['threshold'] else 0",
    ],
    "proof_target": [
        "int(features.get('proven', False))",
        "1 if features.get('lemma_count', 0) >= params['n_min'] else 0",
    ],
    # Numeric classes — full expressivity assumed; example shows the
    # non-trivial form pattern.
    "1d": [
        "params['a'] * features['x'] + params['b']",
        "params['a'] * exp(-params['k'] * features['t']) + params['c']",
    ],
    "nd_features": [
        "params['a'] * features['x'] + params['b'] * features['y'] + params['c']",
    ],
}
_PARAMETRIC_FORM_STUB_EXAMPLES_DEFAULT = _PARAMETRIC_FORM_STUB_EXAMPLES_BY_CLASS["audit"]


def parametric_form_theorem_packet(rubric_data: Mapping[str, Any]) -> str:
    """Return a typed theorem-packet block listing the AST whitelist
    explicitly + class-specific stub examples + common-fail blacklist.

    Returns "" when the rubric does not opt in via
    ``enable_parametric_form_theorem_packet: true``.

    Pattern: Codex NS Track B Phase 5CV theorem-packet — pre-declare
    grammar before mutator generates content. Reduces R1 bounce noise.
    """
    if not bool(rubric_data.get("enable_parametric_form_theorem_packet", False)):
        return ""
    cage_meta = rubric_data.get("cage_meta") or {}
    class_name = str(cage_meta.get("class") or "").strip().lower() or "unknown"
    examples = _PARAMETRIC_FORM_STUB_EXAMPLES_BY_CLASS.get(
        class_name, _PARAMETRIC_FORM_STUB_EXAMPLES_DEFAULT
    )
    allowed = ", ".join(sorted(_PARAMETRIC_FORM_ALLOWED_NAMES))
    forbidden = ", ".join(sorted(_PARAMETRIC_FORM_FORBIDDEN_COMMON_FAILS))
    examples_block = "\n".join(f"      {e}" for e in examples)
    return (
        "\n"
        "    ── PARAMETRIC_FORM theorem packet (R1 pre-flight) ──\n"
        "\n"
        "    ALLOWED FUNCTION NAMES (anything else is rejected by R1 AST whitelist):\n"
        f"      {allowed}\n"
        "\n"
        "    FORBIDDEN COMMON-FAILS (do NOT use these — they will R1-bounce):\n"
        f"      {forbidden}\n"
        "\n"
        f"    VALID STUB EXAMPLES for your substrate class ({class_name!r}):\n"
        f"{examples_block}\n"
        "\n"
        "    NOTES:\n"
        "      - Arithmetic operators (+ - * / ** % //) are AST-level, no function-call.\n"
        "      - Subscript ONLY on `features` (e.g. features['x']) and `params`.\n"
        "      - For conditional logic use `a if cond else b`, NOT isinstance/type checks.\n"
        "      - For collection logic use direct comparisons, NOT sum/any/all.\n"
        "      - Arithmetic: x**y not pow(x,y); bare exp() not np.exp() or math.exp().\n"
    )


# ────────────────────────────────────────────────────────────────────
# Primitive-class rotation discipline (2026-05-06 PM, post-run-4)
# ────────────────────────────────────────────────────────────────────
# Run 4 of ztare_on_ztare_v2_expanded_scope produced ACRR primitive at
# iter 4 then anchored — iters 5+ refined ACRR instead of proposing
# alternative primitive classes. Rotation discipline tracks which
# classes have been explored in workspace/explored_primitive_classes.jsonl
# and injects the list into next iter's mutator prompt so the mutator
# knows what it has already tried.
#
# Opt-in via rubric flag `enable_primitive_class_rotation: true`.
# Default off — preserves existing behavior. Operator enables per
# substrate (substrates that have a primitive-class lane benefit;
# substrates that don't are unaffected).


_read_explored_classes = read_explored_primitive_classes
_read_cross_substrate_classes = read_cross_substrate_primitive_classes


def primitive_class_history_packet(
    rubric_data: Mapping[str, Any],
    project_dir: Optional[Path] = None,
) -> str:
    """Inject the primitive-class history into the mutator prompt.

    Returns "" when the rubric does not opt in via
    ``enable_primitive_class_rotation: true``.

    The packet:
      1. Lists all primitive classes already proposed in this run
      2. Per class, shows the score it received and the iter count
      3. Tells the mutator which classes are at-or-near the per-class
         ceiling cap (so refining further is dominated by rotation)
      4. (v0.5) When enable_cross_substrate_exclusion: true, ALSO lists
         primitive classes proposed by OTHER substrates so the mutator
         doesn't re-discover them
    """
    if not bool(rubric_data.get("enable_primitive_class_rotation", False)):
        return ""
    summary = summarize_explored_primitive_classes(
        project_dir,
        include_cross_substrate=bool(rubric_data.get("enable_cross_substrate_exclusion", False)),
    )
    history = summary["history"]
    cross_other = summary["cross_other"]
    if not history and not cross_other:
        return (
            "\n"
            "    ── PRIMITIVE-CLASS ROTATION (no classes explored yet) ──\n"
            "\n"
            "    No primitive classes have been proposed in this run yet. If you\n"
            "    propose a candidate with mechanism = propose_new_primitive_class,\n"
            "    you have full ceiling 95 available. Subsequent iters that propose\n"
            "    THE SAME CLASS will be capped at 80 (2nd iter), 65 (3rd), 50 (4th+).\n"
            "    Plan accordingly: a single refinement pass is allowed, but anchoring\n"
            "    on one class for many iters will be score-dominated by class rotation.\n"
        )
    per_class = summary["per_class"]
    lines = ["    ── PRIMITIVE-CLASS ROTATION HISTORY (this run) ──", ""]
    rotation_pressure: list[tuple[int, int, float, str, dict[str, Any]]] = []
    for cls, info in per_class.items():
        outcomes = info.get("outcomes") or {}
        negative_count = sum(
            int(outcomes.get(name) or 0)
            for name in ("r3_rejected", "non_improving_candidate", "r1_exhausted")
        )
        repeat_count = max(0, int(info.get("count") or 0) - 1)
        if negative_count or repeat_count:
            rotation_pressure.append(
                (
                    negative_count,
                    repeat_count,
                    float(info.get("best_score") or 0.0),
                    cls,
                    info,
                )
            )
    if rotation_pressure:
        lines.append("    Rotate away first:")
        for negative_count, repeat_count, _best_score, cls, info in sorted(
            rotation_pressure,
            key=lambda item: (-item[0], -item[1], -item[2], item[3]),
        )[:5]:
            lines.append(
                f"      - {cls!r}: repeats={repeat_count}, "
                f"rejected_or_flat={negative_count}, best score {info['best_score']}"
            )
        lines.append("")
    lines.append("    Classes already proposed this run (per-class score cap applies):")
    for cls, info in sorted(per_class.items(), key=lambda kv: -kv[1]["best_score"]):
        n = info["count"]
        if n >= 4:
            cap = 50
        elif n == 3:
            cap = 65
        elif n == 2:
            cap = 80
        else:
            cap = 95
        next_cap = max(50, cap - 15)
        outcomes = info.get("outcomes") or {}
        outcome_text = ", ".join(
            f"{name}={count}" for name, count in sorted(outcomes.items())
        )
        outcome_suffix = f", outcomes: {outcome_text}" if outcome_text else ""
        lines.append(
            f"      - {cls!r}: proposed {n}× (best score {info['best_score']}, "
            f"current ceiling {cap}, next-iter ceiling if refined again: {next_cap}"
            f"{outcome_suffix})"
        )
    lines.append("")
    lines.append(
        "    DISCIPLINE: propose a class NOT in the list above. If you must refine\n"
        "    an existing class, justify explicitly why the new iter adds substantive\n"
        "    mechanism (not just deeper detail of the same mechanism); be aware the\n"
        "    judge will apply the per-class cap regardless of refinement quality."
    )
    # v0.5: cross-substrate exclusion list (if enabled)
    if cross_other:
        cross_per_class = summary["cross_per_class"]
        lines.append("")
        lines.append(
            "    ── CROSS-SUBSTRATE EXCLUSION (v0.5) ──"
        )
        lines.append(
            "    Other ZTARE-on-ZTARE substrates have proposed these primitive classes;\n"
            "    re-proposing one is a known-redundancy and capped at score 50:"
        )
        for cls, info in sorted(
            cross_per_class.items(), key=lambda kv: -kv[1]["best_score"]
        ):
            substrates_list = ", ".join(sorted(info["substrates"]))[:120]
            lines.append(
                f"      - {cls!r}: best score {info['best_score']} (from: {substrates_list})"
            )
    return "\n" + "\n".join(lines) + "\n"


def verify_convention_bridge_in_form(
    parametric_form_str: str,
    cage_meta: Mapping[str, Any],
) -> Optional[str]:
    """GP-157 v5.0 Gap #4 — convention-bridging assertion.

    Per panel Failure Mode 2 + Class K finding: when a substrate declares
    `target_convention_homogeneity: "heterogeneous"` (multiple physical
    quantities pooled — Kaplan + Chinchilla + Bahri exponents, etc.),
    the mutator's parametric form MUST include a bridging parameter
    (scaling or shifting) keyed off `features['fit_convention']` (or
    equivalent convention column) — otherwise scipy will silently
    blend incommensurable units into a meaningless average.

    This is a static AST-style scan of the FORM string. Returns None
    when the bridge is present (or homogeneous, no bridge required).
    Returns a diagnostic when the bridge is missing for a heterogeneous
    substrate — caller raises ContractError or surfaces to mutator.
    """
    homogeneity = (cage_meta.get("target_convention_homogeneity") or "").strip().lower()
    if homogeneity != "heterogeneous":
        return None  # bridge not required

    form = parametric_form_str or ""
    # Heuristic: the form must reference fit_convention (or a per-row
    # convention indicator) somewhere. Either as a feature subscript or
    # as a multiplicative/additive bridge term.
    bridge_indicators = (
        "fit_convention",
        "convention_offset",
        "convention_scale",
        "kaplan",         # explicit per-convention coefficient is acceptable
        "chinchilla",
        "if features.get(",  # conditional on convention
    )
    if any(token in form for token in bridge_indicators):
        return None

    return (
        "heterogeneous substrate (target_convention_homogeneity='heterogeneous') "
        "but PARAMETRIC_FORM contains no convention-bridging term. "
        "Without a bridge keyed off features['fit_convention'] (or per-convention "
        "coefficient), scipy will blend incommensurable units into a meaningless "
        "average. Add a multiplicative/additive correction conditioned on the "
        "convention column."
    )


def verify_class_consistency_with_substrate(
    cage_meta_class: str,
    project_dir: Path,
) -> Optional[str]:
    """Detect cage_meta.class declarations that contradict filesystem reality.

    Returns None when consistent; returns a diagnostic string when the
    declared class is inconsistent with the substrate's authored files.

    Rules (locked down 2026-04-25 after gp159 wrong-class migration
    incident — gp159/160/161 declared class="nd_features" but had no
    features.py, causing Contract B hint to inject `from features import`
    against substrates that don't have it):

      - class="nd_features" requires `features.py` to exist alongside
        `test_model.py`. Without features.py, Contract B (`I_model(features)`)
        cannot be honored.
      - class="proof_target" requires the substrate to have any indicator
        of Lean tooling (a `.lean` file, a `lean_compiler` reference in
        evidence/test_model, etc.). Absent → declaration is suspect.
      - class="closed_form_constant" requires a `pslq` or
        `integer_relation` reference somewhere — absent is suspect.
      - class="audit" requires neither features.py nor a fitting
        gate_harness.py (audit substrates score on critique). If
        gate_harness.py exists with `_ground_truth`, the substrate is
        likely a fitting target mis-declared as audit.

    Invoke at seal-time and at autoresearch_loop init; raising the
    returned diagnostic prevents the substrate from running with a
    wrong contract hint silently injected.
    """
    cls = (cage_meta_class or "").strip().lower()
    if not cls:
        return None  # No declaration → nothing to verify

    if cls == "nd_features":
        if not (project_dir / "features.py").exists():
            return (
                f"cage_meta.class='nd_features' but {project_dir}/features.py does not exist. "
                f"nd_features substrates must author features.py (with FEATURES, feature_keys(), "
                f"visible_rows(), holdout_rows()). Either create features.py OR change the "
                f"declaration to 'class=\"1d\"' if this is a 1D scalar substrate (gp159/160/161 pattern)."
            )

    if cls == "proof_target":
        # Look for any Lean indicator. Word-boundary regex per panel
        # review: bare "Lean" substring matches "cleanly", "Leans toward"
        # in evidence prose; require whole-word match.
        import re as _re
        has_lean_files = any(project_dir.rglob("*.lean"))
        evidence = project_dir / "evidence.txt"
        has_lean_in_evidence = False
        if evidence.exists():
            etext = evidence.read_text(encoding="utf-8", errors="ignore")
            lean_pat = _re.compile(r"\b(Lean|lean_compiler|theorem|tactic)\b")
            has_lean_in_evidence = bool(lean_pat.search(etext))
        if not (has_lean_files or has_lean_in_evidence):
            return (
                f"cage_meta.class='proof_target' but no Lean indicators found in {project_dir}. "
                f"Expected: a .lean file OR Lean references in evidence.txt. Verify the class declaration."
            )

    if cls == "closed_form_constant":
        import re as _re
        evidence = project_dir / "evidence.txt"
        has_pslq = False
        if evidence.exists():
            etext = evidence.read_text(encoding="utf-8", errors="ignore")
            pslq_pat = _re.compile(r"\b(PSLQ|integer.relation|integer-relation|continued.fraction)\b", _re.IGNORECASE)
            has_pslq = bool(pslq_pat.search(etext))
        if not has_pslq:
            return (
                f"cage_meta.class='closed_form_constant' but no PSLQ / integer-relation references "
                f"found in {project_dir}/evidence.txt. Verify the class declaration."
            )

    if cls == "audit":
        # Audit substrates should not have a fitting gate_harness.
        harness = project_dir / "gate_harness.py"
        if harness.exists():
            harness_text = harness.read_text(encoding="utf-8", errors="ignore")
            if "_ground_truth" in harness_text:
                return (
                    f"cage_meta.class='audit' but {project_dir}/gate_harness.py contains "
                    f"`_ground_truth` — this substrate looks like a fitting target, not an audit. "
                    f"Audit substrates score on critique of a research artifact, not curve-fitting."
                )

    return None
