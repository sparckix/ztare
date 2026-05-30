"""Contract-rules briefing provider — preemptive teaching of apparatus rules.

Compressed (2026-04-28 mid-day). Earlier prose-form briefing rendered ~9k
chars per iter; ZTARE has ~5-6 iters per run, so the same content was
re-rendered 5-6×. Compressed strategy:

- Iter 1: full rules in schema form (~3k chars vs ~9k prose).
- Iter ≥ 2: one-line pointer back to iter-1 briefing (apparatus contracts
  do not change mid-run; the mutator already saw the rules once and the
  apparatus already enforces them downstream).

Total cost saving on a 6-iter run: ~9k × 5 = 45k chars / ~11k tokens of
input, plus the corresponding reasoning tokens. The teaching is upstream;
once the mutator has seen it, the gates (downstream) enforce compliance.

Priority 20 — renders first; before path_b_promotion_floor (30),
lagrangian_worked_example (25), VerifiedAxioms (50), ForcedReframe (130),
ColdLLM (150).
"""
from __future__ import annotations

from pathlib import Path

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class ContractRulesProvider(BriefingProvider):
    """Render apparatus + substrate contract rules at top of briefing."""

    name = "contract_rules"
    priority = 20  # render FIRST, before everything

    def _theorem_packet_fragment(self, rubric: dict, *, compact: bool) -> str:
        contract = rubric.get("theorem_packet_contract") or {}
        required = list(contract.get("required_top_level_functions") or [])
        if not required:
            return ""
        fn_list = ", ".join(f"{name}()" for name in required)
        if compact:
            return (
                "## Apparatus Contract Rules — theorem-packet recap\n\n"
                "```\n"
                "contract_class      : theorem_packet\n"
                f"required_functions : {fn_list}\n"
                "numeric_scaffold    : optional compatibility only; never the main result\n"
                "I_model             : optional, not required for this substrate\n"
                "hard_rule           : define every required function at module scope; keep imports stdlib-only; no module-level execution\n"
                "```\n"
            )
        lines = [
            "## Apparatus Contract Rules — theorem-packet substrate",
            "",
            "This project is evaluated as a theorem packet, not as a scalar fit.",
            "The deterministic gate reads `test_model.py` with AST extraction before paid judge scoring.",
            "",
            "```",
            "CONTRACT: required top-level Python functions at module scope",
        ]
        for name in required:
            lines.append(f"  - def {name}(): ...")
        lines.extend(
            [
                "I_model: optional compatibility scaffold only; not required here",
                "PARAMETRIC_FORM/LAGRANGIAN: optional compatibility only; do not replace the theorem-packet API",
                "IMPORTS: stdlib only unless evidence explicitly allows more",
                "SAFETY: no module-level I_model(...) calls, assertions that execute heavy work, or side effects at import",
                "```",
                "",
            ]
        )
        return "\n".join(lines)

    def applies(self, ctx: BriefingContext) -> bool:
        return not bool((ctx.rubric or {}).get("suppress_contract_rules", False))

    def fragment(self, ctx: BriefingContext) -> str:
        # Iter ≥ 2: lossless compact schema. All rules retained (no
        # information loss vs iter-1) but rendered as a 600-char
        # checklist instead of a 9k-char prose teaching block. The
        # mutator already saw the full prose form on iter 1; this is
        # the hard-rule recap.
        if ctx.iter_index and ctx.iter_index >= 2:
            rubric = ctx.rubric or {}
            theorem_packet = self._theorem_packet_fragment(rubric, compact=True)
            if theorem_packet:
                return theorem_packet
            denylist_terms: list[str] = []
            project_dir = ctx.project_dir
            if project_dir is not None:
                for fname in (".thesis_denylist", ".denylist"):
                    p = Path(project_dir) / fname
                    if p.exists():
                        try:
                            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                                term = line.strip()
                                if term and not term.startswith("#"):
                                    denylist_terms.append(term)
                            break
                        except Exception:
                            continue
            require_i_model = bool(rubric.get("require_i_model_in_submission", True))
            rubric_mode = rubric.get("rubric_mode", "newton")
            denylist_str = (
                ", ".join(f"`{t}`" for t in denylist_terms) if denylist_terms else "(none)"
            )
            return (
                "## Apparatus Contract Rules — recap (lossless schema, full prose in iter-1 briefing)\n\n"
                "```\n"
                f"DENYLIST (banned in thesis prose + comments): {denylist_str}\n"
                f"  → any occurrence → score 0 via global_named_import_check\n"
                f"\n"
                f"test_model.py contract:\n"
                f"  required_signature : def I_model(features|d, params=None) -> float  [required={require_i_model}]\n"
                f"  imports            : stdlib only — math, re, itertools, collections. NO numpy/scipy/pandas/pint/sympy.\n"
                f"  injected_primitives: sigmoid, where, erf (auto-inserted at file top)\n"
                f"  required_decls     : MODEL_PARAMS, PARAMETER_NAMES, INIT_RANGE, and ONE OF (PARAMETRIC_FORM | LAGRANGIAN+PREDICTION)\n"
                f"  invariant_search    : LAGRANGIAN+Q_VARIABLES+BACKGROUND+PREDICTION → GP-180 sympy auto-derives PARAMETRIC_FORM\n"
                f"\n"
                f"PARAMETRIC_FORM grammar (R1 rejects):\n"
                f"  reject pseudo-code   : IF/WHEN/GIVEN/THEN  → use ternary (A if cond else B)\n"
                f"  reject Greek symbols : α β γ π ω           → use ASCII (alpha, beta, ...)\n"
                f"  reject inline notes  : (8 params), K=5     → move to PARAMETER_NAMES\n"
                f"  reject bare ids      : d, regime           → use features['key']\n"
                f"  reject hidden params : params.get('a', 0.34) in PARAMETRIC_FORM → use params['a']; defaults belong in I_model only\n"
                f"  reject statements    : = / return / def    → expressions only\n"
                f"  reject unicode arrows: → ⇒                 → use ==, >=, etc.\n"
                f"  accept scope         : features[k], params[k], math primitives, sigmoid/where/erf\n"
                f"\n"
                f"Mode: {rubric_mode}"
                + ("  → secondary observable + falsifying observation required in thesis" if rubric_mode == "newton" else "")
                + "\n"
                "```\n"
            )

        # Iter 1: schema-form rendering of the full contract.
        rubric = ctx.rubric or {}
        theorem_packet = self._theorem_packet_fragment(rubric, compact=False)
        if theorem_packet:
            return theorem_packet
        project_dir = ctx.project_dir

        denylist_terms: list[str] = []
        if project_dir is not None:
            for fname in (".thesis_denylist", ".denylist"):
                p = Path(project_dir) / fname
                if p.exists():
                    try:
                        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                            term = line.strip()
                            if term and not term.startswith("#"):
                                denylist_terms.append(term)
                        break
                    except Exception:
                        continue

        require_i_model = bool(rubric.get("require_i_model_in_submission", True))
        rubric_mode = rubric.get("rubric_mode", "newton")
        is_qualitative = (
            not bool(rubric.get("enable_fit_primitive", True))
            and rubric.get("fit_score_mode") == "none"
        )

        lines: list[str] = []
        lines.append("## Apparatus Contract Rules — iter-1 baseline (R1 enforcement)")
        lines.append("")
        lines.append(
            "The apparatus enforces deterministic contracts before judge scoring. "
            "Violations trigger R1 retries (max 3); after that the iter is consumed "
            "with no signal. Comply on the FIRST submission."
        )
        lines.append("")

        # Section 1 — denylist (compact form)
        if denylist_terms:
            lines.append("### Denylist (banned in thesis prose AND in code comments)")
            lines.append("")
            lines.append(
                f"Forbidden terms: {', '.join(f'`{t}`' for t in denylist_terms)}"
            )
            lines.append(
                "Hard rule: any occurrence → score 0 via global_named_import_check. "
                "Allowed: language describing the *question*. Banned: language "
                "naming the *answer* or the canonical-source authors/catalogs."
            )
            lines.append("")

        # Section 2 — Python suite contract (schema-form)
        lines.append("### test_model.py contract")
        lines.append("")
        lines.append("```")
        if require_i_model:
            lines.append("REQUIRED:    def I_model(features|d, params=None) → float")
        else:
            lines.append("REQUIRED:    none (qualitative substrate)")
            lines.append("BANNED:      DO NOT define or call I_model() anywhere in test_model.py.")
            lines.append("             DO NOT write PARAMETRIC_FORM, LAGRANGIAN, MODEL_PARAMS,")
            lines.append("             PARAMETER_NAMES, or INIT_RANGE. These are numeric-substrate")
            lines.append("             artifacts that cause R1 rejection on qualitative runs.")
            lines.append("             Any module-level I_model(...) call → immediate R1.")
        lines.append("STDLIB ONLY: no numpy, scipy, pandas, pint, sympy. Use math, re, itertools, collections.")
        lines.append("INJECTED:    sigmoid, where, erf (auto-inserted at file top)")
        if require_i_model:
            lines.append("DECLARE:     MODEL_PARAMS, PARAMETER_NAMES, INIT_RANGE,")
            lines.append("             AND ONE OF:")
            lines.append("               (a) PARAMETRIC_FORM = \"<closed expr in features+params>\"     [legacy / direct]")
            lines.append("               (b) LAGRANGIAN = \"<sympy expr in q,q_dot,background>\"")
            lines.append("                   + Q_VARIABLES = [...] + BACKGROUND = [...] + PREDICTION = \"<expr in q+features>\"")
            lines.append("                   → GP-180 lagrangian_derivation auto-solves Euler-Lagrange,")
            lines.append("                     substitutes steady-state q, and emits the apparatus-ready")
            lines.append("                     PARAMETRIC_FORM. Mutator does NOT manually invert E-L.")
        lines.append("```")
        lines.append("")

        # Section 3 — PARAMETRIC_FORM grammar (schema-form rejections)
        if require_i_model:
            lines.append("### PARAMETRIC_FORM grammar — common R1 rejects")
            lines.append("")
            lines.append("```")
            lines.append("REJECT  pseudo-code:    IF/WHEN/GIVEN/THEN  → use ternary (A if cond else B)")
            lines.append("REJECT  Greek symbols:  α β γ π ω           → use ASCII (alpha, beta, ...)")
            lines.append("REJECT  inline notes:   (8 params), K=5     → move to PARAMETER_NAMES")
            lines.append("REJECT  bare identifiers: d, regime          → use features['key']")
            lines.append("REJECT  hidden defaults: params.get('a', 0.34) in PARAMETRIC_FORM")
            lines.append("REJECT  statement blocks: = / return / def   → expressions only")
            lines.append("REJECT  unicode arrows:  → ⇒                → use ==, >=, etc.")
            lines.append("ACCEPT  scope: features[k], params[k], math primitives, sigmoid/where/erf")
            lines.append("IMPORT-SAFE PATTERN: PARAMETRIC_FORM uses params['a']; I_model builds p={name: neutral_default} outside the form before eval/calc")
            lines.append("```")
            lines.append("")

        # Section 4 — mode reminder (one-liner)
        if is_qualitative:
            lines.append("### Mode: kepler (qualitative)")
            lines.append("Thesis prose is the deliverable. test_model.py can be a stub.")
            lines.append("")
        elif rubric_mode == "newton":
            lines.append("### Mode: newton (Generative Yield enforced)")
            lines.append(
                "Thesis must name (a) a secondary observable the form predicts, "
                "(b) the falsifying observation that would force abandonment."
            )
            lines.append("")

        return "\n".join(lines) + "\n"
