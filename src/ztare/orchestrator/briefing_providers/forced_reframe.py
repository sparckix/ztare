"""GP-168 Forced REFRAME briefing provider.

Reads `workspace/eval_history.jsonl` + last submission's PARAMETRIC_FORM,
runs `forced_reframe.detect_forced_reframe_trigger`, and when triggered
renders a MANDATORY-DISJOINT-ARCHITECTURE block into the next iter's
mutator briefing. Alien-math alternatives are pulled from the GP-164
seam if available.

Provider-level integration only: no inline if-block
in autoresearch_loop. Provider self-decides via reading iter telemetry.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


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
        # 2026-04-27 hotfix: REFRAME fires from iter 1 (no stagnation
        # streak required) when EITHER:
        #   (a) tier_3_universal_law_target.active=true (variational target —
        #       framings should be visible immediately, not after 3
        #       iters of bridge replay), OR
        #   (b) substrate_domain is declared (the operator has wired
        #       domain-specific framings; surface them from iter 1)
        # For substrates without either signal, the legacy 3-iter
        # threshold preserves prior behavior.
        target = (ctx.rubric or {}).get("tier_3_universal_law_target") or {}
        domain = (ctx.rubric or {}).get("substrate_domain")
        if target.get("active", False) or (domain and str(domain).strip()):
            return True
        # Legacy substrates: need at least 3 prior iters for stagnation detection
        eh = self._load_eval_history(ctx)
        return len(eh) >= 3

    def _last_cap_kind(self, eh: list[dict]) -> str:
        """Classify the most recent capped iter's cap_kind. Returns 'none'
        when no prior caps exist or all are non-cap (cap_inactive_*)."""
        try:
            from ztare.orchestrator.cap_kind import classify_cap_kind
        except ImportError:
            return "unknown"
        for rec in reversed(eh):
            if not isinstance(rec, dict):
                continue
            reason = rec.get("score_cap_reason") or ""
            kind = classify_cap_kind(reason)
            if kind != "none":
                return kind
        return "none"

    def fragment(self, ctx: BriefingContext) -> str:
        try:
            from ztare.orchestrator.forced_reframe import (
                detect_forced_reframe_trigger,
                build_forced_reframe_briefing_block,
            )
        except ImportError:
            return ""
        eh = self._load_eval_history(ctx)

        # 2026-04-27 (cap-kind generalized fix): the last cap source
        # determines REFRAME vs REFINE. Gaming caps (R20-R24) → fire
        # REFRAME (escape attractor). Honest caps (PPN, generalization
        # gap, holdout miss) → render "Refine Prior Winner" instead —
        # the form is structurally engaging the variational contract and the
        # cap signals a refinement target, not an architectural pivot.
        if eh:
            last_kind = self._last_cap_kind(eh)
            if last_kind in ("generalization_gap", "physics_violation", "holdout_miss"):
                return self._render_refine_prior_winner(ctx, eh, last_kind)

        # 2026-04-27 hotfix: substrates with variational target OR substrate_domain
        # surface REFRAME framings from iter 1 (eval_history empty).
        target = (ctx.rubric or {}).get("tier_3_universal_law_target") or {}
        domain = (ctx.rubric or {}).get("substrate_domain")
        if not eh and (target.get("active", False) or (domain and str(domain).strip())):
            alts = self._load_alternatives(ctx)
            if not alts:
                return ""
            domain = (ctx.rubric or {}).get("substrate_domain", "")
            lines: list[str] = []
            lines.append("## REFRAME — Iter-1 Panel of Candidate Framings (variational target)")
            lines.append("")
            lines.append(
                f"This substrate has a variational-promotion target active. The apparatus "
                f"surfaces the panel-recommended framings below from iter 1 so you "
                f"can engage them directly instead of converging to the verified-"
                f"axiom basin and learning the cap mechanism through R20-R24 hits. "
                f"Pick one framing, derive the candidate from it, submit. The "
                f"K_extra <= 2 promotion floor and the strict structural caps "
                f"(R20-R24, Mercury PPN) gate every iter."
            )
            if domain:
                lines.append("")
                lines.append(f"Substrate domain: `{domain}` — framings below are domain-keyed.")
            lines.append("")
            for i, alt in enumerate(alts[:7], start=1):
                lines.append(f"### Framing {i} — {alt.get('name', 'unnamed')}")
                if alt.get("field_of_origin"):
                    lines.append(f"*Field of origin:* {alt['field_of_origin']}")
                lines.append("")
                lines.append("```")
                lines.append((alt.get("form") or "").rstrip())
                lines.append("```")
                if alt.get("what_it_captures"):
                    lines.append("")
                    lines.append(f"*What it captures:* {alt['what_it_captures']}")
                lines.append("")
            return "\n".join(lines) + "\n"
        if not eh:
            return ""
        stag_thresh = int(ctx.rubric.get("gp168_stagnation_threshold", 3))
        ast_bucket_thresh = int(ctx.rubric.get("gp168_ast_bucket_threshold", 5))
        max_fires = int(ctx.rubric.get("gp168_max_consecutive_fires", 2))
        # Qualitative-substrate Trigger 4 opt-in (2026-05-02). Defaults
        # OFF; numerical substrates (gp163d, gp161, etc.) never reach the
        # trigger. Qualitative rubrics (gp168 v3, gp169) opt in.
        enable_qual = bool(ctx.rubric.get("enable_qualitative_stagnation_detection", False))
        qual_thresh = int(ctx.rubric.get("qualitative_stagnation_threshold", 3))
        plateau_thresh = int(ctx.rubric.get("qualitative_plateau_threshold", 5))
        decision = detect_forced_reframe_trigger(
            eh,
            stagnation_threshold=stag_thresh,
            ast_bucket_threshold=ast_bucket_thresh,
            max_consecutive_fires=max_fires,
            enable_qualitative_stagnation=enable_qual,
            qualitative_stagnation_threshold=qual_thresh,
            qualitative_plateau_threshold=plateau_thresh,
        )
        if not decision.should_force:
            return ""
        alts = self._load_alternatives(ctx)
        block = build_forced_reframe_briefing_block(decision, alts)
        # Persist decision for telemetry / iter-history tagging
        try:
            from ztare.orchestrator.forced_reframe import (
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

    def _render_refine_prior_winner(
        self,
        ctx: BriefingContext,
        eh: list[dict],
        last_kind: str,
    ) -> str:
        """Render a 'REFINE PRIOR WINNER' block instead of REFRAME framings.

        Triggered when the most recent cap was an honest one (physics
        violation, generalization gap, holdout miss) — the form is
        engaging the variational contract and the apparatus's right move is to
        encourage the mutator to inherit and extend it, not pivot to a
        different architectural family.

        Selects the best honest-cap iter from history and surfaces it as
        the explicit refinement target. Names the cap source so the
        mutator knows which dimension to extend.
        """
        try:
            from ztare.orchestrator.cap_kind import find_best_honest_iter
        except ImportError:
            return ""
        best = find_best_honest_iter(eh)
        if best is None:
            return ""

        iter_idx = best.get("iteration", "?")
        score = best.get("score", "?")
        raw = best.get("raw_judge_score")
        cap_reason = (best.get("score_cap_reason") or "")[:300]
        form = (best.get("parametric_form") or "")[:600]
        weakest = (best.get("weakest_point") or "")[:300]

        kind_label = {
            "generalization_gap": "farther-tail per-class generalization gap",
            "physics_violation": "Solar-System PPN violation",
            "holdout_miss": "Class A holdout MRE miss",
        }.get(last_kind, last_kind)

        kind_advice = {
            "generalization_gap": (
                "The form passed Class A holdout AND the structural "
                "anti-pattern gates (R20-R24, R22) — it is structurally "
                "honest (no parameter laundering, no substrate-anchor "
                "literals). The cap is the per-class farther-tail MRE "
                "threshold on the withheld classes (B clusters and/or "
                "C wide-binaries). REFINE this form by adding a Class-"
                "specific structural piece: chameleon thin-shell coupling "
                "for cluster-scale physics, or AQUAL ν(y) = y/(1+y) "
                "interpolation for the deep-MOND regime. DO NOT pivot "
                "the architectural family."
            ),
            "physics_violation": (
                "The form passed structural / numerical gates but failed "
                "the strict Mercury-perihelion or Cassini-PPN bound at "
                "Solar-System acceleration. REFINE by deriving a screen "
                "from the Lagrangian potential V(φ) and coupling A(φ) — "
                "do NOT impose `1/(1 + (x/x_scr)²)` by hand (R20 catches "
                "the screen-scale literal). The screen must emerge from "
                "physics (chameleon thin-shell, f(R) Compton-mass, AQUAL "
                "external-field-effect) so PPN passes by construction."
            ),
            "holdout_miss": (
                "The form is structurally honest but doesn't fit Class A "
                "well enough. REFINE the parameter count or the "
                "interpolating function — the bridge envelope is the "
                "right structural skeleton; tune the c_eff modulation "
                "or eta exponent."
            ),
        }.get(last_kind, "Refine the prior form along the named gap.")

        lines: list[str] = []
        lines.append("## REFINE PRIOR WINNER (honest-cap signal — DO NOT pivot)")
        lines.append("")
        lines.append(
            f"**Most recent cap kind: `{last_kind}` ({kind_label})**. "
            f"This is an honest-form cap — the apparatus has detected "
            f"that the prior submission engaged the variational contract and "
            f"the cap signals a *refinement target*, not an "
            f"architectural failure. Diversity-forcing mechanisms "
            f"(REFRAME, Erdős re-query, structural pivot) are "
            f"SUPPRESSED for this iter — they would burn budget pivoting "
            f"away from a structurally-honest candidate."
        )
        lines.append("")
        lines.append(f"### Best prior honest-cap iter: iter {iter_idx} (score={score}{f', raw_judge={raw}' if raw is not None else ''})")
        lines.append("")
        if form:
            lines.append("Prior form (excerpt):")
            lines.append("")
            lines.append("```")
            lines.append(form)
            lines.append("```")
            lines.append("")
        if weakest:
            lines.append(f"Judge's named weakest point on the prior form:")
            lines.append("")
            lines.append(f"> {weakest}")
            lines.append("")
        lines.append(f"Apparatus cap reason: `{cap_reason}`")
        lines.append("")
        lines.append("### Refinement instruction")
        lines.append("")
        lines.append(kind_advice)
        lines.append("")
        lines.append(
            "Inherit the prior form's PARAMETER_NAMES and PARAMETRIC_FORM "
            "structure. Add ONE structural piece targeting the named gap. "
            "Keep K_extra ≤ 2-3. Do not propose a fundamentally different "
            "topology family — that mistakes refinement for reframe."
        )
        lines.append("")
        return "\n".join(lines) + "\n"

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
                from ztare.orchestrator.forced_reframe import (
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
        # REFRAME steer physics substrates toward variational/Lagrangian
        # derivation) instead of generic alien-math families.
        try:
            from ztare.orchestrator.alien_math_seam_loader import (
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
