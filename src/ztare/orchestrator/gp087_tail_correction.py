"""GP-087 tail-correction seed proposer (Phase 4g, 2026-05-06 PM).

Single coherent extraction: when the farther-tail gate fails (or
contract-stagnation mode triggers), propose composition seeds by
appending one of five tail-correction primitives to the champion
expression. The seeds flow into ``composition_seed.json`` for the
next iter's mutator briefing.

Two firing modes:

  Mode 1 — explicit gate fail:
    A ``deterministic_charter_gates.results`` entry whose ``name``
    contains "farther_tail" and whose ``passed`` is False. Standard
    path for rubrics with explicit farther-tail hard gates.

  Mode 2 — contract-stagnation:
    Rubric declares ``farther_tail_contract: true`` (no explicit
    gate) AND eval score < 100 AND stagnation_count >= 1. This
    covers veto-mode rubrics where the judge's weakest_point
    reflects the farther-tail failure but no deterministic gate
    surfaces it directly.

Information boundary: emits only primitive names + composed
expressions + parameter names. No farther-tail residual values
ever leak into the seed (charter-contamination defense).

Pure function — no apparatus state, no module globals. Behaviour
preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


# Primitives that produce a correction term decaying toward zero at large u.
# These are candidates when the farther-tail gate fails because the model
# overshoots or undershoots the true asymptote. Parameter prefix "tail_"
# avoids collision with the symbolic-regression "d2_" prefix — the champion
# expression may already contain d2_a, d2_b, d2_c from a prior depth-2
# composition; reusing those names would create duplicate assignments
# in test_model.py and break the fit.
GP087_TAIL_CORRECTION_PRIMITIVES: list[tuple[str, str, list[str]]] = [
    ("reciprocal",      "tail_a / {var} + tail_b",                       ["tail_a", "tail_b"]),
    ("harmonic",        "tail_a / {var} + tail_b / {var}**2 + tail_c",   ["tail_a", "tail_b", "tail_c"]),
    ("log_reciprocal",  "tail_a * math.log({var}) / {var} + tail_b",     ["tail_a", "tail_b"]),
    ("sqrt_reciprocal", "tail_a / math.sqrt({var}) + tail_b",            ["tail_a", "tail_b"]),
    ("exp_decay",       "tail_a * math.exp(-tail_b * {var}) + tail_c",   ["tail_a", "tail_b", "tail_c"]),
]


def propose_tail_correction_seeds(
    eval_results: dict,
    workspace_dir: Path,
    rubric_data: dict,
    iteration_index: int,
    stagnation_count: int = 0,
) -> list[dict] | None:
    """Propose composition seeds when the farther-tail gate fails.

    Returns a list of seed candidates (same format as
    ``composition_seed.json``) or None if GP-087 does not fire.

    See module docstring for the two firing modes + the information-
    boundary discipline.
    """
    score_contract = eval_results.get("score_contract", {})
    if not isinstance(score_contract, dict):
        return None

    det = score_contract.get("deterministic_charter_gates", {})
    if not isinstance(det, dict):
        return None

    results = det.get("results", [])
    if not isinstance(results, list):
        return None

    # Mode 1: any explicit farther-tail gate failed?
    farther_tail_failed = False
    for item in results:
        name = str(item.get("name", ""))
        if "farther_tail" in name and not bool(item.get("passed", False)):
            farther_tail_failed = True
            break

    # Mode 2: contract-stagnation fallback. Fires only when NO explicit
    # farther-tail gate exists AND rubric declares farther_tail_contract.
    # Prevents double-firing when Mode 1 already covers the same signal.
    if not farther_tail_failed and rubric_data.get("farther_tail_contract"):
        explicit_tail_gate_exists = any(
            "farther_tail" in str(item.get("name", "")) for item in results
        )
        if not explicit_tail_gate_exists:
            current_score = eval_results.get("score", 100)
            if (
                isinstance(current_score, (int, float))
                and current_score < 100
                and stagnation_count >= 1
            ):
                farther_tail_failed = True
                print(
                    f"    >> GP-087: farther_tail_contract active, "
                    f"score={current_score}, stagnation={stagnation_count} "
                    f"— contract-stagnation mode"
                )

    if not farther_tail_failed:
        return None

    # Read the current best expression from fit_result.json
    fit_result_path = workspace_dir / "fit_result.json"
    if not fit_result_path.exists():
        return None

    try:
        fit_result = json.loads(fit_result_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    champion_expr = fit_result.get("expression", "")
    champion_params = list(fit_result.get("fitted_params", {}).keys())
    if not champion_expr:
        return None

    # Build the variable name from rubric
    ind_vars: list[str] = rubric_data.get("fit_required_vars", ["n"])
    var_name: str = ind_vars[0] if ind_vars else "n"

    # Grammar filter — `math_exp_only` rubrics ban trig primitives
    grammar = str(rubric_data.get("fit_expression_grammar", "") or "").strip().lower()
    forbidden_re = None
    if grammar == "math_exp_only":
        forbidden_re = re.compile(
            r"math\.(sin|cos|tan|sinh|cosh|tanh|asin|acos|atan)"
        )

    # Compose each tail-correction primitive with the champion expression
    seeds: list[dict] = []
    for prim_name, prim_template, prim_params in GP087_TAIL_CORRECTION_PRIMITIVES:
        correction_expr = prim_template.format(var=var_name)

        if forbidden_re and forbidden_re.search(correction_expr):
            continue

        # Skip if the correction primitive's params are already present in the
        # champion — prevents double-composition when GP-087 runs against a
        # champion that was itself a prior GP-087 tail-corrected seed.
        if any(p in champion_params for p in prim_params):
            continue

        composed_expr = f"({champion_expr}) + ({correction_expr})"
        all_params = champion_params + prim_params

        seeds.append({
            "source": "gp087_residual_driven",
            "expression": composed_expr,
            "independent_vars": ind_vars,
            "parameter_names": all_params,
            "correction_primitive": prim_name,
            "iteration_synthesized": iteration_index,
            "round": f"gp087_tail_correction/{prim_name}/+",
        })

    return seeds if seeds else None
