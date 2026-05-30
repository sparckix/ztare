"""GP-169 Cold-LLM Erdős seed briefing provider.

Reads `workspace/cold_llm_seed_iter0.json` (written pre-iter-1 by
`pre_iter1_dispatch.dispatch_pre_iter1_cage`) and renders the three
cross-domain candidate forms into the iter 1+ mutator briefing as
MANDATORY-CONSIDER alternatives.

Per GP-169 seam §Phase 1: candidates surface as constraints, not optional
suggestions. The iter-1 prompt explicitly says: pick one, modify one,
or justify rejecting all three in prose. Iter-1 submissions that ignore
the seed entirely receive an R1 strike via the adherence layer (see
`autoresearch_loop.py` adherence-rule wiring).

Adherence-rule enforcement (panel Blindspot 3 fix): the proposed
"AST-distance to seed candidates vs prior champion" check is queued
as a follow-up; for the initial wire-in the provider surfaces the
candidates and the briefing prose, and the prose-engagement adherence
rule R1-strikes iter-1 submissions that don't reference at least one
seed candidate by structural shape. Operators who believe the
prose-only check is gameable should ship the AST-distance enhancement.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class ColdLlmSeedBriefingProvider(BriefingProvider):
    """Renders cold-LLM-seeded cross-domain candidates as MANDATORY-CONSIDER."""

    name = "cold_llm_seed"
    priority = 150  # high priority — render early in the briefing

    def applies(self, ctx: BriefingContext) -> bool:
        if not bool(ctx.rubric.get("enable_cold_llm_erdos_seed", False)):
            return False
        ws = ctx.workspace_dir or ctx.project_dir / "workspace"
        # Either the iter-0 baseline OR a requery artifact suffices.
        return (
            (ws / "cold_llm_seed_iter0.json").exists()
            or any(ws.glob("cold_llm_seed_requery_iter_*.json"))
        )

    def fragment(self, ctx: BriefingContext) -> str:
        ws = ctx.workspace_dir or ctx.project_dir / "workspace"

        # GP-169 Phase 2 (Q2 2026-04-26): if stagnation detected, refresh
        # the seed before rendering. The re-query is idempotent within a
        # stagnation event (same signature → cached hit, no LLM call).
        # The briefing provider runs every iter, so this is the natural
        # place to gate the refresh — same channel that delivers iter-0
        # delivers the refreshed candidates.
        try:
            from src.ztare.orchestrator.cold_llm_seed_requery import (
                maybe_requery_cold_seed,
                latest_seed_artifact,
            )
            eh = self._load_eval_history(ws)
            verdict = maybe_requery_cold_seed(
                project_dir=ctx.project_dir,
                rubric_data=dict(ctx.rubric),
                iter_index=int(ctx.iter_index),
                eval_history=eh,
                workspace_dir=ws,
                mutator_model_id=getattr(ctx, "mutator_model_id", None),
            )
            for ln in verdict.log_lines:
                print(ln)
            seed_path = latest_seed_artifact(ws) or (ws / "cold_llm_seed_iter0.json")
            # Refreshed banner fires whenever the resolved seed file is a
            # requery artifact, regardless of whether THIS provider call
            # triggered the LLM (cached requeries from prior iters still
            # qualify — they ARE refreshed seeds).
            is_refreshed = seed_path is not None and "requery" in seed_path.name
        except Exception as exc:
            print(f"🔎 GP-169 re-query: provider hook failed ({exc}); using iter-0 seed.")
            seed_path = ws / "cold_llm_seed_iter0.json"
            is_refreshed = False

        try:
            seed = json.loads(seed_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return (
                "## ⚠️  GP-169 Cold-LLM Erdős seed (UNAVAILABLE)\n\n"
                f"Seed-load error: `{type(exc).__name__}: {exc}`. The pre-iter-1 cold-LLM "
                f"call did not produce a usable seed JSON. Iter-1 proceeds with the "
                f"standard briefing; the seed-engagement adherence rule is auto-disabled "
                f"for this iter.\n\n"
            )

        qualitative_mode = bool(seed.get("qualitative_mode"))
        candidates = seed.get("candidates") or []
        valid = [c for c in candidates if c.get("valid_python")]

        # Panel-Blindspot-7 fix (unsuitability lock): if fewer than 2 valid
        # candidates survived validation, surface the failure honestly and
        # disable the adherence rule for this iter rather than forcing
        # rejection-prose theater.
        if len(valid) < 2:
            err = seed.get("error") or "fewer than 2 valid candidates after pre-flight"
            n_total = len(candidates)
            return (
                "## ⚠️  GP-169 Cold-LLM Erdős seed (DEGRADED)\n\n"
                f"Pre-iter-1 cold-LLM call returned {n_total} candidate(s), of which "
                f"{len(valid)} survived form-validation. Reason: `{err}`. The seed "
                f"mechanism is auto-disabled for this iter; proceed with standard "
                f"briefing. Telemetry event: `cold_seed_degraded`.\n\n"
            )

        forbid = seed.get("forbidden_domain") or "(none)"
        sigil = seed.get("fingerprint_signature", "")[:120]
        requery_meta = seed.get("requery_meta") or {}
        lines: list[str] = []
        if is_refreshed and requery_meta:
            # Q2 fix (2026-04-26): refreshed seed banner — make it
            # obvious to the mutator that the candidates reflect the
            # CURRENT residual state, not the iter-0 baseline.
            lines.append(
                f"## 🔎 GP-169 Cold-LLM Erdős seed — REFRESHED (iter "
                f"{requery_meta.get('iter_index', '?')}, MANDATORY CONSIDER)\n"
            )
            lines.append(
                "Stagnation has been detected and the cold-LLM was re-queried "
                "with the *current* residual fingerprint (not the iter-0 baseline). "
                f"Trigger: `{requery_meta.get('stagnation_reason', 'unspecified')}`. "
                "The candidates below reflect what the apparatus is stuck on NOW. "
                "Treat them with higher priority than the iter-0 seed — they are "
                "your second cold draw, evidence-driven this time.\n"
            )
        else:
            lines.append("## 🔎 GP-169 Cold-LLM Erdős seed — MANDATORY CONSIDER\n")
            lines.append(
                "A pre-iter-1 cold LLM call (separate from the mutator and judge, no "
                "shared context) was given an anonymized residual fingerprint and "
                "asked for cross-domain candidate forms. The cold LLM was explicitly "
                f"forbidden from using methods from `{forbid}` and adjacent fields. "
                "The candidates below are the apparatus's iter-1 architectural seeds — "
                "pick one as your starting form, modify one, or explicitly justify "
                "rejecting all three in your thesis prose.\n"
            )
        lines.append(f"Fingerprint signature (quantized): `{sigil}`\n")
        lines.append("### Mandatory architectural alternatives\n")
        for i, cand in enumerate(valid[:3], 1):
            name = cand.get("name", f"Alternative {i}")
            field = cand.get("field_of_origin", "(unspecified)")
            captures = cand.get("what_it_captures", "(unspecified)")
            form = cand.get("form", "")
            lines.append(f"#### Alternative {i}: {name}")
            lines.append(f"**Field of origin (cold-LLM tag, not validated):** {field}\n")
            lines.append(f"**What this captures:** {captures}\n")
            if qualitative_mode:
                # Argument structure rendered as prose block, not Python.
                lines.append("**Core structural commitment:**")
                lines.append(f"> {form.strip()}\n")
            else:
                lines.append("```python")
                lines.append(form.strip())
                lines.append("```\n")
        lines.append("### Adherence requirement\n")
        if qualitative_mode:
            lines.append(
                "Iter-1 thesis MUST: (a) reference at least one of the three "
                "argument structures above by its structural commitment (e.g. "
                "\"adopting the causal-identification move from Alternative 2\"), "
                "AND (b) state whether your thesis derives from, modifies, or "
                "explicitly rejects that structural family with a stated reason. "
                "Submissions that ignore all three receive an R1 strike. "
                "From iter 2 onward they remain as architectural alternatives; "
                "engagement is no longer mandatory.\n"
            )
        else:
            lines.append(
                "Iter-1 thesis prose MUST: (a) reference at least one of the three "
                "candidates above by its structural shape (e.g. \"the logistic from "
                "Alternative 1's RG-flow framing\"), AND (b) state whether the form "
                "you submit is derived from that candidate, modifies it, or rejects "
                "it with a stated reason. Iter-1 submissions that do not reference "
                "any of the three candidates receive an R1 strike at apparatus "
                "level. From iter 2 onward the candidates remain in your context "
                "as alternative architectures; engagement is no longer mandatory.\n"
            )
        lines.append(
            "### Caveat (panel Blindspot 2 — forbid-clause is a negative "
            "instruction)\n"
        )
        lines.append(
            "LLMs ignore negative instructions; the cold-LLM may have produced a "
            f"form structurally identical to a `{forbid}`-domain canonical even "
            "while tagging it as cross-domain. Treat the field-of-origin label "
            "as an unverified self-tag. The substrate critic + R10/R11 + "
            "(when shipped) GP-170 symbolic logic cage will catch forms that "
            "structurally violate the substrate's algebraic constraints "
            "regardless of the cold-LLM's labeling.\n"
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _load_eval_history(workspace_dir: Path) -> list[dict]:
        """Read eval_history.jsonl + augment with parametric_form per iter
        from submissions/. Used by the re-query stagnation detector."""
        out: list[dict] = []
        eh_path = workspace_dir / "eval_history.jsonl"
        if not eh_path.exists():
            return out
        try:
            for ln in eh_path.read_text(encoding="utf-8").splitlines():
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
        # 2026-04-27: AST-based enrichment (replaces regex that failed on
        # multi-line implicit-concatenation forms). See
        # extract_parametric_form_from_source docstring for context.
        subs_dir = workspace_dir / "submissions"
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
