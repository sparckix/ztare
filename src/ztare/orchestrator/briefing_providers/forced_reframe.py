"""GP-168 Forced REFRAME briefing provider — task #141 wire-in.

Reads `workspace/eval_history.jsonl` + last submission's PARAMETRIC_FORM,
runs `forced_reframe.detect_forced_reframe_trigger`, and when triggered
renders a MANDATORY-DISJOINT-ARCHITECTURE block into the next iter's
mutator briefing. Alien-math alternatives are pulled from the GP-164
seam if available.

Per Phase-4g shape: provider-level integration only — no inline if-block
in autoresearch_loop. Provider self-decides via reading iter telemetry.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


# Hardcoded fallback alien-math alternatives (from GP-164 seam appendix).
# Used when the alien_math_framings.md seam isn't accessible.
_FALLBACK_ALTERNATIVES = [
    {
        "name": "RG-flow logistic with logarithmic mass running",
        "field_of_origin": "renormalization-group / statistical mechanics",
        "form": (
            "params['u0'] / (1.0 + (features['x']/params['g_star'])**(1.0 + "
            "params['gamma']*log(max(features.get('mass_log10', 1.0), 1e-9)))) "
            "* features['x'] + features['x']"
        ),
        "what_it_captures": (
            "universal logistic shape in log-log space with slow logarithmic "
            "mass running; no kernels, no piecewise switches, slow regime drift"
        ),
    },
    {
        "name": "Multifractal Legendre quadratic",
        "field_of_origin": "multifractal analysis / dynamical systems",
        "form": (
            "features['x'] * 10**(params['alpha0']*log10(features['x']/"
            "params['g_star']) + params['c2']*(log10(features['x']/"
            "params['g_star']) + params['q0'])**2)"
        ),
        "what_it_captures": (
            "parabolic structure in log-log residuals; asymmetry between "
            "regimes captured by single offset q0 (not separate kernels)"
        ),
    },
    {
        "name": "Modular q-expansion oscillation",
        "field_of_origin": "modular forms / number-theoretic harmonic analysis",
        "form": (
            "features['x'] * (1.0 + params['A']*exp(-params['kappa']*"
            "features['x']**params['p']) * cos(params['omega']*"
            "log(max(features.get('mass_log10', 1.0), 1e-9)) + params['phi']))"
        ),
        "what_it_captures": (
            "periodic structure in log-mass; cluster enhancement and any "
            "suppressed regimes appear as consecutive lobes of one oscillation"
        ),
    },
]


class ForcedReframeBriefingProvider(BriefingProvider):
    """Renders GP-168 forced-reframe block when stagnation triggers fire."""

    name = "forced_reframe"
    priority = 130  # render before cold-LLM seed (which is 150)

    def applies(self, ctx: BriefingContext) -> bool:
        if not bool(ctx.rubric.get("enable_forced_reframe", True)):
            return False
        # Need at least 3 prior iters for stagnation detection
        eh = self._load_eval_history(ctx)
        return len(eh) >= 3

    def fragment(self, ctx: BriefingContext) -> str:
        try:
            from src.ztare.orchestrator.forced_reframe import (
                detect_forced_reframe_trigger,
                build_forced_reframe_briefing_block,
            )
        except ImportError:
            return ""
        eh = self._load_eval_history(ctx)
        if not eh:
            return ""
        stag_thresh = int(ctx.rubric.get("gp168_stagnation_threshold", 3))
        ast_bucket_thresh = int(ctx.rubric.get("gp168_ast_bucket_threshold", 5))
        max_fires = int(ctx.rubric.get("gp168_max_consecutive_fires", 2))
        decision = detect_forced_reframe_trigger(
            eh,
            stagnation_threshold=stag_thresh,
            ast_bucket_threshold=ast_bucket_thresh,
            max_consecutive_fires=max_fires,
        )
        if not decision.should_force:
            return ""
        alts = self._load_alternatives(ctx)
        block = build_forced_reframe_briefing_block(decision, alts)
        # Persist decision for telemetry / iter-history tagging
        try:
            from src.ztare.orchestrator.forced_reframe import (
                write_forced_reframe_decision,
            )
            write_forced_reframe_decision(
                ctx.workspace_dir or (ctx.project_dir / "workspace"),
                ctx.iter_index,
                decision,
            )
        except Exception:
            pass
        return block

    def _load_eval_history(self, ctx: BriefingContext) -> list[dict]:
        ws = ctx.workspace_dir or ctx.project_dir / "workspace"
        path = ws / "eval_history.jsonl"
        out: list[dict] = []
        if not path.exists():
            return out
        try:
            for ln in path.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                try:
                    rec = json.loads(ln)
                except Exception:
                    continue
                rec.setdefault("parametric_form", "")
                rec.setdefault("forced_reframe_fired", False)
                out.append(rec)
        except Exception:
            return []
        # 2026-04-27: AST-based enrichment replaces the prior regex pattern
        # which captured multi-line PARAMETRIC_FORM = ( "..." "..." ) with
        # embedded newlines, then ast.parse() rejected it as syntax_error.
        # That false-positive bucketed every form as `syntax_error` and
        # triggered the AST-bucket-lock REFRAME on a phantom signal across
        # 5 consecutive iters in run_id 1777250273. Use the shared AST
        # helper so implicit string concatenation resolves correctly.
        subs_dir = ws / "submissions"
        if subs_dir.is_dir() and out:
            try:
                from src.ztare.orchestrator.forced_reframe import (
                    extract_parametric_form_from_source as _extract_form,
                )
            except ImportError:
                _extract_form = None  # type: ignore
            if _extract_form is not None:
                for rec in out:
                    if rec.get("parametric_form"):
                        continue
                    idx = rec.get("iteration") or rec.get("iter_index")
                    if idx is None:
                        continue
                    cands = sorted(subs_dir.glob(f"iter_{int(idx):03d}_*.py"))
                    if not cands:
                        continue
                    try:
                        src = cands[-1].read_text(encoding="utf-8", errors="replace")
                        form = _extract_form(src)
                        if form:
                            rec["parametric_form"] = form
                    except Exception:
                        continue
        return out

    def _load_alternatives(self, ctx: BriefingContext) -> list[dict]:
        # 2026-04-27: domain-aware loader — when rubric declares
        # substrate_domain='modified_gravity', the loader returns
        # Lagrangian framings (chameleon, f(R), AQUAL, MOG, TeVeS)
        # instead of the default math-family framings. This makes
        # REFRAME steer physics substrates toward path-b (Lagrangian
        # derivation) instead of generic alien-math families.
        try:
            from src.ztare.orchestrator.alien_math_seam_loader import (
                load_alien_math_alternatives,
            )
            domain = None
            try:
                domain = (ctx.rubric or {}).get("substrate_domain")
            except Exception:
                domain = None
            return load_alien_math_alternatives(ctx.project_dir, domain=domain)
        except Exception:
            return list(_FALLBACK_ALTERNATIVES)
