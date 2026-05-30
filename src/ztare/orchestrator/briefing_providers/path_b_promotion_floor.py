"""Path-B promotion floor — load-bearing score-cap explainer for the mutator.

When a substrate has a path-b promotion target (e.g.,
`tier_3_universal_law_target.promotion_floor_raw_score = 100`) AND prior
iters were capped at 50 by R20-R24 (parameterized-bridge detection) or
by Solar-System PPN (Mercury/Cassini violation), this provider renders an
unambiguous instruction at the TOP of the mutator briefing telling the
mutator *why* its prior submissions capped and what the only path to
exceed 50 looks like.

Motivation (2026-04-27): the gp163d run produced 5 iters where gpt-5.5
returned to the verified-axiom bridge despite REFRAME, Erdős cold-LLM
seed, topological pivot, and even axiom purge. The briefing was dense
but no single block explained the cap mechanism in load-bearing terms.
This provider is that explanation, surfaced first, every iter.

Priority 30 — renders BEFORE verified_axioms (50), forced_reframe (130),
cold_llm_seed (150) so the mutator reads the cap explanation first and
the framings second.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class PathBPromotionFloorProvider(BriefingProvider):
    """Render path-b promotion floor + cap-mechanism explanation."""

    name = "path_b_promotion_floor"
    priority = 30  # render FIRST, before everything else

    def applies(self, ctx: BriefingContext) -> bool:
        # Only fire when the substrate declares a path-b promotion target.
        target = (ctx.rubric or {}).get("tier_3_universal_law_target") or {}
        if not target.get("active", False):
            return False
        # Only fire after iter 1 — we need a prior cap to explain.
        eh = self._load_eval_history(ctx)
        return len(eh) >= 1

    def fragment(self, ctx: BriefingContext) -> str:
        eh = self._load_eval_history(ctx)
        if not eh:
            return ""

        target = (ctx.rubric or {}).get("tier_3_universal_law_target") or {}
        floor = int(target.get("promotion_floor_raw_score", 100))
        domain = (ctx.rubric or {}).get("substrate_domain", "")

        # 2026-04-27 (cap-kind generalized fix): use cap_kind classifier
        # so this provider fires on ALL non-trivial cap kinds, not just
        # R20-R24 + PPN. Previously the provider went dark when the
        # mutator hit farther-tail per-class or holdout caps — exactly
        # when it was most needed.
        try:
            from src.ztare.orchestrator.cap_kind import classify_cap_kind
        except ImportError:
            classify_cap_kind = None  # type: ignore

        recent = eh[-3:]
        cap_kinds: list[str] = []
        cap_reasons: list[str] = []
        for rec in recent:
            reason = rec.get("score_cap_reason") or ""
            if not reason:
                continue
            kind = classify_cap_kind(reason) if classify_cap_kind else "unknown"
            if kind == "none":
                continue
            label_map = {
                "gaming": "parameter-laundering",
                "physics_violation": "ppn-violation",
                "generalization_gap": "farther-tail-fail",
                "holdout_miss": "holdout-fail",
                "numerical_failure": "numerical-fail",
                "unknown": "uncategorized-cap",
            }
            label = label_map.get(kind, kind)
            if label not in cap_kinds:
                cap_kinds.append(label)
            cap_reasons.append(reason[:200])

        if not cap_kinds:
            # No prior cap — provider has no work to do this iter.
            return ""

        lines: list[str] = []
        lines.append("## Path-B Promotion Floor (Apparatus-Deterministic)")
        lines.append("")
        lines.append(
            f"**Your prior submission(s) capped at 50.** The judge gave qualitative "
            f"raw scores up to 100, but the apparatus capped to 50 because the "
            f"submitted form(s) failed deterministic structural gates. Below is a "
            f"load-bearing summary of the cap mechanism — this is not advice, it "
            f"is the protocol."
        )
        lines.append("")

        if "parameter-laundering" in cap_kinds:
            lines.append("### Cap reason: R20/R21/R22/R24 — parameter-laundering / kernel-camouflage")
            lines.append("")
            lines.append(
                "The form contains hardcoded literals that coincide with substrate-"
                "anchor statistics (visible-class min/max/median on mass_log10, "
                "radius_log10, etc.). These literals are structural degrees of "
                "freedom — they should be declared parameters, derived from "
                "physics, or both. Effective K (declared K + hardcoded literals) "
                "exceeds declared K by enough to trigger R21."
            )
            lines.append("")
            lines.append(
                "**Critical:** parameterizing the literals (turning `11.43` into "
                "`params['m_shell']`) DOES NOT escape this gate when the *fitted "
                "value* of m_shell ends up near the original literal. The cage "
                "checks structural form, not surface syntax. Iter-by-iter "
                "evidence: every parameterized-bridge submission caps at 50."
            )
            lines.append("")

        if "ppn-violation" in cap_kinds:
            lines.append("### Cap reason: G-MERCURY-PRECESSION / G-CASSINI-PPN — Solar-System bound violation")
            lines.append("")
            lines.append(
                "The form's high-acceleration limit deviates from Newton by more "
                "than the strict observed bound. Mercury requires `|y/g_bar - 1| "
                "< 4e-10` at g_bar = 3.96e-2 m/s²; Cassini requires `|γ-1| < "
                "2.3e-5`. Adding a hardcoded screen (`1/(1 + (x/x_scr)^n)`) with "
                "x_scr fitted as a free parameter trips R20 (substrate-anchor "
                "literal coincidence on x_scr) AND fails to explain why the "
                "screen exists."
            )
            lines.append("")
            lines.append(
                "**Path-b answer:** the screen must emerge from the Lagrangian's "
                "potential V(φ) and coupling A(φ), not be imposed by hand. "
                "Chameleon screening, f(R) Compton-mass screening, and AQUAL+A(φ) "
                "all derive a screening scale from a single physical parameter."
            )
            lines.append("")

        lines.append("### The only path to exceed score 50")
        lines.append("")
        lines.append(
            f"Apparatus promotion floor = raw {floor}. To exceed 50, your "
            f"submission must:"
        )
        lines.append("")
        lines.append(
            "1. **Derive** the form from a Lagrangian (Euler-Lagrange + spherical "
            "weak-field reduction). The REFRAME briefing block below lists "
            f"{('candidate Lagrangians for substrate_domain=' + repr(domain)) if domain else 'candidate framings'}. "
            "Pick one and do the derivation."
        )
        lines.append(
            "2. **No hardcoded substrate-anchor literals.** Every numerical "
            "constant that does NOT come from a published physical constant "
            "(see whitelist below) must be a fitted parameter. Sigmoid centers, "
            "screen scales, exponents — all parameters."
        )
        lines.append(
            "3. **K_extra ≤ 2** (one or two physical scales beyond the published "
            "constants). The bridge's hardcoded centers count as 5+ hidden "
            "DoFs; deriving them from a single chameleon scale M_* reduces "
            "K_extra to 1."
        )
        lines.append(
            "4. **Cassini and Mercury PPN pass by construction**, not by tuning. "
            "If your form has a hand-imposed high-x screen, the gates will "
            "still fail because R20 catches the screen-scale literal."
        )
        lines.append("")
        lines.append("### Honest path-b template (cage-whitelist friendly)")
        lines.append("")
        lines.append(
            "**Published physical constants are auto-whitelisted by R20/R21.** "
            "Using G, c, ℏ, M_sun, M_pl, kpc-to-m etc. as numerical literals in "
            "PARAMETRIC_FORM does NOT increase effective K and does NOT count as "
            "substrate-anchor leakage. The cage knows the difference between "
            "`6.67430e-11` (G) and `11.43` (a substrate-anchor mass-bin centroid)."
        )
        lines.append("")
        lines.append("Whitelisted (cage-clean): `G=6.67430e-11`, `c=2.99792458e8`, "
                     "`ℏ=1.054571817e-34`, `M_sun=1.98847e30`, `M_pl=2.176434e-8`, "
                     "`kpc=3.0856775814913673e19`, plus standard CODATA SI constants.")
        lines.append("")
        lines.append("NOT whitelisted: `1.2e-10` (a_0, MOND — denylisted as answer-recital), "
                     "any value matching a substrate-anchor statistic on visible-class data.")
        lines.append("")
        lines.append(
            "**Worked template** (chameleon thin-shell, K_extra=2):"
        )
        lines.append("")
        lines.append("```python")
        lines.append("# Two fitted physical scales: M_*  (chameleon mass) and ")
        lines.append("# alpha (thin-shell coupling). Everything else is derived ")
        lines.append("# from {G, c, ℏ, M_sun, kpc} via Euler-Lagrange.")
        lines.append("PARAMETER_NAMES = ['log_M_star', 'log_alpha']")
        lines.append("PARAMETRIC_FORM = (")
        lines.append("    \"features['x'] * (1.0 + (\"")
        lines.append("    \"  exp(params['log_alpha']) * \"")
        lines.append("    \"  6.67430e-11 * 1.98847e30 * exp(log(10) * features['mass_log10']) / \"   # G·M = published")
        lines.append("    \"  ((3.0856775814913673e19 * 10**features['radius_log10'])**2 * \"          # r² in m, kpc whitelisted")
        lines.append("    \"   exp(params['log_M_star'])**2)\"                                          # M_* scale = the ONE new physical input")
        lines.append("    \"))\"")
        lines.append(")")
        lines.append("```")
        lines.append("")
        lines.append(
            "K declared = 2 (log_M_star, log_alpha). Effective K = 2 (G, M_sun, "
            "kpc-to-m all whitelisted). R21 clean. R20 clean. Mercury/Cassini PPN "
            "depend on the form's high-x asymptote — design the screening into "
            "the Lagrangian (V(φ) potential, A(φ) coupling) so PPN passes by "
            "construction, not by adding a hand-imposed `1/(1+(x/x_scr)²)`."
        )
        lines.append("")
        lines.append(
            "If the previous iter's form used G·M_sun directly (not substrate-"
            "anchor literals) and only got capped by R21 due to over-counting, "
            "**resubmit a structurally-similar form** — the cage now whitelists "
            "physical constants. The score will reflect actual K_extra, not "
            "false positives on G/M_sun/kpc."
        )
        lines.append("")
        lines.append(
            "**Submitting another parameterized bridge (any form sharing 3+ "
            "literals or their parameterized synonyms with the verified axiom) "
            "will cap at 50 again. The numerical fit will pass, the cage will "
            "still cap. Token-burn without progress.**"
        )
        lines.append("")
        lines.append(
            "If you cannot complete a Lagrangian derivation in this iter, "
            "submit the *partial* derivation with explicit holes named and a "
            "K_extra ≤ 2 fitted form. The judge can score partial path-b "
            "progress > 50; only complete-and-laundered bridge submissions "
            "trigger the 50-cap."
        )
        lines.append("")

        return "\n".join(lines) + "\n"

    def _load_eval_history(self, ctx: BriefingContext) -> list[dict]:
        ws = ctx.workspace_dir or (ctx.project_dir / "workspace" if ctx.project_dir else None)
        if ws is None:
            return []
        path = Path(ws) / "eval_history.jsonl"
        if not path.exists():
            return []
        out: list[dict] = []
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
        except Exception:
            return []
        return out
