"""GP-184 cold-shot structural-seed briefing provider.

Reads `workspace/cold_shot_seed.json` (written pre-iter-1 by
`autoresearch_loop` when `rubric.enable_cold_shot_seed=true`) and
renders the proposed Lagrangian + PARAMETRIC_FORM into the iter 1+
mutator briefing as a HARD ARCHITECTURAL DIRECTIVE.

Why this provider exists
------------------------
The 2026-04-28 audit of run 1777403089 iter 1 (Director-mode external
falsification) found that the cold-shot fired successfully, produced a
clean latent-field Lagrangian seed, and the mutator IGNORED it.
Iter 1 submitted a 5-param exp/tanh/asinh apparatus-feature nest that
collapsed pathologically (n_starts_converged=0/3, log_amp escaped 2×
range). Iter 2 collapsed further (parametric_form="0").

Root cause: the cold-shot wrote `cold_shot_seed.json` and nothing read
it for the briefing. The seed lived in a black hole.

Routing fix (this provider): iter 1+ briefing renders the cold-shot's
LAGRANGIAN, PARAMETRIC_FORM, and PARAMETER_NAMES at priority 145 (just
above ColdLlmSeed@150 — the cold-shot is a stronger anchor than the
cross-domain de-anchor candidates and should render first). The
adherence directive states: USE THIS FORM as the iter-1 PARAMETRIC_FORM
or explicitly justify replacing it.

Director-audit appendix
-----------------------
External falsification (2026-04-28) found the cold-shot's perturbative
inversion is mathematically wrong — Q ∝ 1/ρ at high density instead of
J^(1/3) — so the latent term collapses to a constant under fitting.
The provider surfaces this as an explicit warning so the mutator can
either correct the inversion to a Padé form or replace the form
entirely. The Lagrangian itself is correct; only the algebraic
inversion is broken.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


_FEATURE_REF_RE = re.compile(r"""features\[['"]([^'"]+)['"]\]""")


def _project_feature_keys(ctx: BriefingContext) -> set[str]:
    """Best-effort feature-license recovery for older seed artifacts.

    Seeds written before 2026-05-01 did not persist
    `substrate_feature_keys`. Loading the current project's features.py
    prevents a stale cached seed from re-injecting variables copied from
    another substrate.
    """
    feat_path = ctx.project_dir / "features.py"
    if not feat_path.exists():
        return set()
    try:
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location("_cold_shot_brief_features", str(feat_path))
        if spec is None or spec.loader is None:
            return set()
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "feature_keys", None)
        if callable(fn):
            return {str(k) for k in fn()}
        rows_fn = getattr(mod, "visible_rows", None)
        if callable(rows_fn):
            rows = list(rows_fn())
            if rows and isinstance(rows[0], tuple) and len(rows[0]) == 3:
                return {str(k) for k in rows[0][2].keys()}
    except Exception:
        return set()
    return set()


class ColdShotSeedBriefingProvider(BriefingProvider):
    """Renders cold-shot Lagrangian + PARAMETRIC_FORM as iter-1+ directive."""

    name = "cold_shot_seed"
    # 145 — between PathBPromotionFloor (30) and ColdLlmSeed (150).
    # The cold-shot is a STRUCTURAL prior (specific Lagrangian); the
    # cold-LLM seed is a DE-ANCHOR primitive (cross-domain shapes). The
    # structural prior should render first so the mutator's working memory
    # anchors on the Lagrangian before seeing alternatives.
    priority = 145

    def applies(self, ctx: BriefingContext) -> bool:
        # Only fire if the cold-shot is enabled by rubric AND the artifact
        # exists with success=True. Failed cold-shot calls write the JSON
        # with success=False; we skip rendering rather than confuse the
        # mutator with a seed that didn't materialize.
        if not bool(ctx.rubric.get("enable_cold_shot_seed", False)):
            return False
        ws = ctx.workspace_dir or ctx.project_dir / "workspace"
        path = ws / "cold_shot_seed.json"
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        return bool(data.get("success"))

    def fragment(self, ctx: BriefingContext) -> str:
        ws = ctx.workspace_dir or ctx.project_dir / "workspace"
        try:
            seed = json.loads((ws / "cold_shot_seed.json").read_text(encoding="utf-8"))
        except Exception as exc:
            return (
                "## ⚠️  GP-184 cold-shot seed (UNAVAILABLE)\n\n"
                f"Read error: `{type(exc).__name__}: {exc}`. Proceed with "
                f"standard briefing.\n\n"
            )

        lagrangian = (seed.get("proposed_lagrangian") or "").strip()
        prediction = (seed.get("proposed_prediction") or "").strip()
        param_form = (seed.get("proposed_parametric_form") or "").strip()
        param_names = seed.get("proposed_parameter_names") or []
        q_vars = seed.get("proposed_q_variables") or []
        background = seed.get("proposed_background") or []
        rationale = (seed.get("rationale") or "").strip()
        model_id = seed.get("model_id_used") or "(unknown)"
        cache_hit = bool(seed.get("cache_hit"))
        available_feature_keys = set()
        try:
            # Avoid importing project-local features.py here; the prompt
            # builder already records the substrate signature in the seed.
            available_feature_keys = set(seed.get("substrate_feature_keys") or [])
        except Exception:
            available_feature_keys = set()
        if not available_feature_keys:
            available_feature_keys = _project_feature_keys(ctx)
        bad_background = (
            sorted(str(k) for k in background if str(k) not in available_feature_keys)
            if available_feature_keys else []
        )
        bad_param_refs = (
            sorted(set(_FEATURE_REF_RE.findall(param_form)) - available_feature_keys)
            if available_feature_keys and param_form else []
        )

        lines: list[str] = []
        lines.append("## GP-184 Cold-Shot Structural Seed\n")
        lines.append(
            "A separate pre-iter-1 LLM call (model: "
            f"`{model_id}`{' [cached]' if cache_hit else ' [fresh]'}) was "
            "given the substrate context, falsification gates B1-B4 as "
            "constraints, and the per-class Pareto target as objective. "
            "It returned a Lagrangian-derivable structural seed.\n"
        )
        lines.append(
            "**This is your iter-1 anchor.** Two equally acceptable submission contracts "
            "(labels match the formatting block at the end of the prompt):\n\n"
            "**Parametric model declaration — submit PARAMETRIC_FORM directly.** "
            "Declare `PARAMETRIC_FORM = \"...\"` and `PARAMETER_NAMES = [...]` in your "
            "test_model.py and skip the LAGRANGIAN. Use this when you have a hand-derived "
            "closed form already, or when the Lagrangian's E-L is non-trivial to solve in "
            "closed form, or when you are explicitly rejecting the cold-shot Lagrangian "
            "with stated reason in thesis prose.\n\n"
            "**Variational/Lagrangian declaration (preferred for invariant_search rubrics).** "
            "Declare `LAGRANGIAN = \"...\"`, `Q_VARIABLES = [...]`, `BACKGROUND = [...]`, "
            "`PARAMETER_NAMES = [...]`, and `PREDICTION = \"...\"` in your test_model.py. "
            "The GP-180 lagrangian_derivation primitive will (i) compute Euler-Lagrange "
            "equations via sympy, (ii) solve for the steady-state field q in terms of the "
            "background features, (iii) substitute into PREDICTION to derive the closed-form "
            "g_obs(features, params) automatically, and (iv) generate the apparatus-ready "
            "PARAMETRIC_FORM for you. You DO NOT need to manually solve the perturbative "
            "inversion — the apparatus will. Use this when the "
            "physics is cleaner expressed as an action principle than as a fitted polynomial. "
            "When in doubt for invariant_search, prefer the variational/Lagrangian declaration because the cold-shot already "
            "provides a Lagrangian seed and the apparatus's sympy auto-inversion sidesteps "
            "the cubic-Cardano / Padé-asymptote pitfalls that have killed prior iters.\n\n"
            "Apparatus-feature nests (chained tanh/asinh/exp without grounding in a stated "
            "Lagrangian) will be R1-struck under the action-principle contract regardless "
            "of which path you choose.\n\n"
            "**MUTUALLY EXCLUSIVE.** Pick one declaration form, not both. If you declare "
            "LAGRANGIAN you do NOT need PARAMETRIC_FORM (GP-180 generates it). If you "
            "declare PARAMETRIC_FORM you do NOT need LAGRANGIAN (you've hand-derived "
            "the closed form yourself). Submitting both means you are hedging because "
            "you do not trust the apparatus; the hedge typically introduces unbalanced "
            "parens and statement-block syntax errors in the redundant PARAMETRIC_FORM, "
            "and those R1-strike the iter unnecessarily. Trust the apparatus: pick ONE "
            "path.\n"
        )
        if available_feature_keys:
            lines.append("### Feature license\n")
            lines.append(
                "Allowed feature keys for this substrate are: "
                f"`{sorted(available_feature_keys)}`. Do not use any other "
                "row variables in `PARAMETRIC_FORM`.\n"
            )
        if bad_background or bad_param_refs:
            lines.append("### ⚠️ Seed feature-license warning\n")
            lines.append(
                "The cold-shot seed references feature keys that are not "
                "available in this substrate. Treat those references as "
                "invalid, not as instructions to add substrate columns. "
                f"Invalid BACKGROUND keys: `{bad_background}`. Invalid "
                f"PARAMETRIC_FORM feature refs: `{bad_param_refs}`. Rewrite "
                "the structural idea using only licensed keys or reject it "
                "explicitly in thesis prose.\n"
            )

        if lagrangian:
            lines.append("### Proposed LAGRANGIAN\n")
            lines.append("```python")
            lines.append(f'LAGRANGIAN = "{lagrangian}"')
            if q_vars:
                lines.append(f"Q_VARIABLES = {q_vars}")
            if background:
                lines.append(f"BACKGROUND = {background}")
            if param_names:
                lines.append(f"PARAMETER_NAMES = {param_names}")
            lines.append("```\n")

        if prediction:
            lines.append("### Proposed PREDICTION (closed-form g_obs)\n")
            lines.append("```python")
            lines.append(f'PREDICTION = "{prediction}"')
            lines.append("```\n")

        if param_form:
            lines.append("### Proposed PARAMETRIC_FORM (apparatus-ready)\n")
            lines.append("```python")
            lines.append(f'PARAMETRIC_FORM = "{param_form}"')
            lines.append("```\n")

        if rationale:
            lines.append("### Cold-shot RATIONALE\n")
            lines.append(rationale + "\n")

        # Director-audit appendix — surfaces external-falsification findings
        # the operator marked as known issues in the seed. Conservative:
        # only render if rubric enables it (default ON for invariant_search).
        if bool(ctx.rubric.get("cold_shot_director_audit_appendix", True)):
            lines.append("### ⚠️  Director-mode external-falsification audit\n")
            lines.append(
                "The 2026-04-28 audit found that cold-shot seeds tend to "
                "describe a plausible Lagrangian but produce an INCORRECT "
                "perturbative inversion in the PARAMETRIC_FORM. Verify the "
                "asymptotic behavior of any latent-field amplitude Q(J) "
                "in the form you submit, where J is a source built only "
                "from licensed feature keys:\n"
            )
            lines.append(
                "- **Linear regime** (small J): Q ∝ J for linear source coupling.\n"
                "- **Cubic regime** (large J, quartic self-interaction dominant): "
                "Q ∝ J^(1/3). **NOT** Q ∝ 1/J.\n"
                "- A Lorentzian denominator like `m2 + lambda*J**2` gives "
                "Q ∝ 1/J at large J. Use a Padé-style form like "
                "`m2 + (lambda*J)**(2/3)`.\n"
            )
            lines.append(
                "If the cold-shot's PARAMETRIC_FORM has the wrong asymptote, "
                "you may submit a corrected version of the SAME Lagrangian "
                "and explain the inversion fix in the thesis prose. That "
                "counts as engaging the seed, not rejecting it.\n"
            )

        lines.append("### Engagement requirement (R1)\n")
        lines.append(
            "Iter-1 thesis prose MUST: (a) state whether your submitted form "
            "parameterizes the cold-shot Lagrangian above, modifies it (e.g. "
            "via inversion correction), or rejects it with reason; (b) if "
            "modifying or replacing, justify with reference to the "
            "Director-audit asymptotic constraints. Submissions that ignore "
            "the cold-shot entirely receive an R1 strike at the apparatus "
            "level.\n"
        )
        required_couplings = [
            item for item in (ctx.rubric.get("cold_shot_required_feature_couplings") or [])
            if isinstance(item, dict) and str(item.get("key") or "") in available_feature_keys
        ]
        if required_couplings:
            lines.append("### ⚠️ Rubric-declared required feature couplings\n")
            for item in required_couplings:
                key = str(item.get("key") or "")
                reason = str(item.get("reason") or item.get("description") or "").strip()
                lines.append(f"- `features['{key}']`: {reason}\n")
        lines.append("### Anti-pattern reminder (B1 shadow on parallel workers)\n")
        lines.append(
            "Lagrangians of the form `½q̇² − ½(q − feature)²` (harmonic "
            "oscillator centered at a substrate variable) are TRIVIAL "
            "SUBSTITUTIONS — they fail G-LAGRANGIAN-NONTRIVIAL by "
            "construction because the static E-L gives `q = feature`. "
            "This was observed live in run 1777403089 iter-4 worker_00 "
            "where the field was centered on a single substrate feature. "
            "The blitz tournament now penalizes this pattern at scoring "
            "time. Use a "
            "non-trivial potential V(φ): polynomial `½m²φ² + (λ/4)φ⁴`, "
            "inverse-potential, cubic-source, or exponential potentials.\n"
        )
        return "\n".join(lines) + "\n"
