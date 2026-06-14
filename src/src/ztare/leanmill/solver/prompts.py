"""Canonical home for the solver's LLM PROMPT templates (#49 consolidation — operator directive 2026-06-11).

The brittle pattern this replaces: every move hardcoded its own `_*_PROMPT` f-string in its own module, so a
prompt fix (the 2026-06-11 planner template-echo bug) touched scattered code and the shared "You are a Lean 4
prover … Output EXACTLY: ```lean block" boilerplate drifted. Per `docs/concepts/leanmill_typed_contracts.md`,
LLM prompts are **parameterised templates with DATA passed as data** (`.format(...)` at the call site) — they
stay as code, NOT YAML (the doc calls YAML-for-prompts an anti-pattern: no linting/highlighting). This module is
the ONE place the templates live; callers `from ztare.leanmill.solver import prompts` and `.format()` them.

MIGRATION (incremental, byte-identical move first, parameterise second — each behind an equivalence test):
  ✅ DEANCHOR_PROMPT (the planner DECOMPOSE prompt; was isomorphism_decompose._DEANCHOR_PROMPT — the highest-
     bug-risk one, it caused the echo bug). TODO (in order): conjecture.py's 7 (_CONJECTURE/_SPECIALIZE/_FALSIFY/
     _CORROBORATE/_TACTIC_STEP/_GENERALIZE/_REVIEW), autoformalize (_FORMALIZE_INTERACTIVE/_DEF_JUDGE),
     abduction, proof_margin_of_safety (_RUNG_TIGHTEN). Then factor the shared role/Output-EXACTLY boilerplate.
"""
from __future__ import annotations

# The PLANNER's DECOMPOSE prompt. Placeholders filled by the caller via `.format(iso_step=…, p=…, binders=…,
# goal_concl=…, ban=…, preamble=…, goal=…)`. Moved VERBATIM from isomorphism_decompose._DEANCHOR_PROMPT.
DEANCHOR_PROMPT = (
    "You are a strong research mathematician working in Lean 4. The goal below has its surface names "
    "neutralized — focus on its mathematical STRUCTURE. USE your full knowledge of which field/theory "
    "solves this structure to find the genuine attack — recognizing the structure is an ASSET, not "
    "forbidden. (You may NOT discharge the goal by merely CITING a famous theorem as if it were a Mathlib "
    "lemma — that is rejected by the kernel, which recompiles without the gold context — and no "
    "intermediate lemma may merely restate the goal, which the audit rejects as circular; so transport the "
    "proof's STRUCTURE into lemmas you could genuinely prove.) {iso_step}"
    "then TRANSPORT that field's proof shape into an intermediate LEMMA DAG. Output EXACTLY:\n"
    "DECOMP:\n```lean\n"
    "theorem {p}_lemma1 : <statement> := by sorry\n"
    "theorem {p}_lemma2 : <statement> := by sorry\n"
    "-- … as many sorried intermediate lemmas as the transported proof needs …\n"
    "theorem {p}_chain {binders}: {goal_concl} := by\n  <tactics that REFERENCE the {p}_lemmaᵢ; NO sorry>\n"
    "```\n"
    "RULES: REPLACE every `<...>` placeholder with REAL Lean — do NOT echo the literal `<statement>` / "
    "`<tactics ...>` scaffold (a verbatim template is NOT a decomposition and is rejected). Leave every "
    "intermediate lemma as `:= by sorry` (do NOT prove them); the CHAIN must be sorry-free and CITE the "
    "lemmas; NO lemma may merely restate the goal; self-contained against the PREAMBLE below.{ban}\n"
    "PREAMBLE (fixed; defines the objects):\n{preamble}\nGOAL:\n{goal}\n"
)
