"""Canonical home for the solver's LLM PROMPT templates (#49 consolidation — operator directive 2026-06-11).

The brittle pattern this replaces: every move hardcoded its own `_*_PROMPT` f-string in its own module, so a
prompt fix (the 2026-06-11 planner template-echo bug) touched scattered code and the shared "You are a Lean 4
prover … Output EXACTLY: ```lean block" boilerplate drifted. Per `docs/concepts/leanmill_architecture.md`
(§ "Typed contracts"), LLM prompts are **parameterised templates with DATA passed as data** (`.format(...)` at the call site) — they
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

# The iso PLANNER's WARM-CHECK block (runtime-specific: `{probe}` file + `{leancheck}` command filled by
# `isomorphism_decompose.attack`). Surfaces the warm `lean_check_server --check` so codex stops cold-compiling
# with `lake env lean` (~90s) and getting guillotined before it emits — the 2026-06-11 planner foot-gun.
ISO_PLANNER_WARMCHECK_BLOCK = (
    "FAST VERIFICATION — use the WARM checker, do NOT cold-compile: to typecheck your decomposition, "
    "write the full DAG (sorried lemmas + the sorry-free chain, with `import Mathlib` first) to:\n  {probe}\n"
    "then check it WARM (~0.1s; prints the EXACT Lean errors or 'OK'):\n  {leancheck}\n"
    "Do NOT run `lake env lean` — a cold Mathlib reload takes ~90s and will exhaust your time budget "
    "before you answer. Iterate write→warm-check→fix until the DAG typechecks (the intermediate lemmas "
    "stay `:= by sorry`; the CHAIN must be sorry-free), THEN emit the DECOMP block. The kernel re-audits "
    "your DAG downstream — this warm check just lets you CONVERGE fast within budget.\n\n"
)

# ── LEAF SOLVE prompts (the warm agentic leaf — `agentic_leaf._leaf_prompt`). UPLEVELED 2026-06-11: the leaf
# is a FRONTIER agent (codex-5.5 / opus-4.8 class), so the prompt gives it the ENVIRONMENT + AUTONOMY + the
# hard soundness RULES and TRUSTS it — it is NOT told which commands to run (it knows it can grep/search/iterate).
# Thin-harness principle: "the leaf solver IS the agents; leanmill is the environment." `{target}/{goal}/{probe}`
# are filled at the call site; their Lean-brace VALUES are safe (`.format` does not re-scan substituted values).
LEAF_SOLVE_COMMON = (
    "You are a frontier research mathematician working AUTONOMOUSLY in this Lean 4 project from a "
    "workspace-write terminal — the full Mathlib library is available and the kernel checks your work. "
    "Operate exactly as you would on your own machine: explore the library, recognize the underlying "
    "structure, write, check, iterate, and invent + prove your own auxiliary lemmas. You do not need to be "
    "told which commands to run — use your judgment. The compile is the VERIFICATION, not the objective. "
    "HARD RULES — governance auto-rejects these, no exceptions even when stuck (a proof that only compiles "
    "by breaking them is worthless and wastes the attempt): no `sorry`/`admit`/added `axiom`; nothing "
    "(instance / `notation` / `macro` / `set_option` / a changed or shadowed definition) that alters what "
    "the statement MEANS; no restating the goal as its own hypothesis. A COMPLETE, genuine proof is the "
    "goal — when a direct proof resists, DECOMPOSE into sub-lemmas and prove those rather than giving up. "
    "Only as a genuine LAST RESORT, having actually tried, may you leave a `sorry` with a precise "
    "`-- GAP: <the exact lemma you could not prove>` — that localizes the open mathematics honestly, but it "
    "is a last resort, never an easy out. DISTINCT from a gap: if the TARGET ITSELF is FALSE as stated — you "
    "found a counterexample, i.e. it is a MIS-FORMALIZATION, not merely a hard proof — do NOT force a proof; "
    "say so with `-- STATEMENT-FALSE: <the counterexample, and the corrected hypothesis the TRUE statement "
    "needs>`. That is an HONEST, VALUED outcome (the apparatus re-formalizes the intended statement and "
    "re-checks faithfulness), never a failure. BUT this is a HARD claim that the harness VERIFIES with the "
    "kernel: it will dispatch a skeptic to PROVE `¬(the goal)` and only act on your claim if that negation "
    "compiles. So claim STATEMENT-FALSE only when you could actually write that disproof. A real "
    "counterexample MUST satisfy EVERY hypothesis — including each field of any structure the statement "
    "binds; if your witness violates a hypothesis (e.g. a structure's `_eq` field, a `q ≠ 0`) it is NOT a "
    "counterexample and the statement is consistent-with-true — so PROVE it, don't flag it. An unverified "
    "STATEMENT-FALSE claim is rejected and you are sent back to prove the statement as given.")

# Appended to LEAF_SOLVE_COMMON only when the harness started the warm REPL (a NON-discoverable affordance —
# the agent can't know the socket path; this is environment, not hand-holding). `{socket}` / `{probe}` filled.
LEAF_WARMCHECK_HINT = (
    "\n\nFAST COMPILE — check EVERY iteration against the WARM Lean REPL (not cold `lake env lean`):\n"
    "  python -m ztare.formal.lean_check_server --check {socket} {probe}\n"
    "It returns in ~0.1s (warm Mathlib) and prints the EXACT `error:` lines to fix. Iterate against it "
    "rapidly; only use `lake env lean` if it prints 'server unreachable'.")

LEAF_DIRECT_PREFIX = "Prove `{target}` : {goal} in {probe} (currently `sorry`). "

LEAF_DECOMPOSE_PREFIX = (
    "The theorem `{target}` : {goal} in {probe} is hard. {gap_fb}Work BACKWARD like a mathematician: "
    "identify the intermediate lemmas the real proof needs; prove each, or leave a `-- GAP:` on the ones you "
    "genuinely cannot; then assemble `{target}` from them. ")

LEAF_DECOMPOSE_GAP_FB = ("Your direct attempt diagnosed this missing piece: «{gap}». Build the decomposition "
                         "toward proving it. ")

# Legacy A/B baseline prompts (ZTARE_LEANMILL_LEGACY_PROMPT=1) — kept for the prompt A/B. `{target}/{goal}/{probe}`.
LEAF_LEGACY_DECOMPOSE_PROMPT = (
    "The theorem `{target}` : {goal} in {probe} is hard and still has a sorry. DECOMPOSE it: state and prove "
    "auxiliary helper lemmas (lemma/have) that build toward it, then assemble `{target}` from them. Run "
    "`lake env lean {probe}` and iterate until ZERO errors and NO sorry anywhere. Do not add axioms.")
LEAF_LEGACY_DIRECT_PROMPT = (
    "Prove the theorem `{target}` in {probe} (currently `sorry`): theorem {target} : {goal}. Edit the file to "
    "replace the sorry with a real proof, then run `lake env lean {probe}` and iterate until it compiles with "
    "zero errors and no sorry. The needed definitions are already in the file. Do not add axioms or sorry.")


# STRATEGY ASSESSMENT (#106 follow-up): one cheap up-front question so the AGENT — not a hardcoded gate —
# decides decompose-vs-direct on ANY target, even without a human-seeded blueprint (the operator's "the agent
# should NOTICE it can't close this directly" point). `{goal}` filled at the call site.
STRATEGY_ASSESSMENT_PROMPT = (
    "You are a Lean 4 proof strategist. Assess the GOAL below and choose the BEST FIRST move:\n"
    "  • SOLVE_DIRECT — it can plausibly be closed by a SHORT direct proof (a handful of tactics / Mathlib "
    "lemmas).\n"
    "  • DECOMPOSE — it is a multi-step or research-level result; a one-shot direct proof would FAIL, and the "
    "right first move is to break it into intermediate sub-lemmas.\n"
    "Be honest and decisive: if a direct proof is unlikely to succeed, choose DECOMPOSE — do NOT waste effort "
    "grinding a doomed direct attempt (that is exactly the failure we are avoiding). Judge the MATHEMATICAL "
    "depth, not the surface length.\n"
    "Answer with EXACTLY one token on the FIRST line: SOLVE_DIRECT or DECOMPOSE.\n\nGOAL:\n{goal}\n"
)

# GOVERNANCE proof-constraint lines injected into the PROVING leaf prompt (via move_cards.render_tool_block).
# The agent's proof is re-audited with `#print axioms`, so a `native_decide`/`sorry`/`admit` "closure" is
# rejected even though it compiles — tell it UP FRONT (#104) so it doesn't waste effort on a banned tactic.
GOVERNANCE_PROOF_CONSTRAINTS_LINES = (
    "GOVERNANCE (your proof is re-audited with `#print axioms`): do NOT use `native_decide` — it adds the",
    "`Lean.ofReduceBool` compiler-trust axiom and your closure is REJECTED even though it 'compiles'. Use",
    "`decide` for kernel-decidable goals (kernel-checked, axiom-clean). Never use `sorry`/`admit`.",
)

# NL → one-sentence NL back-translation (the faithfulness round-trip's render leg). `{lean_statement}` filled
# at the call site; the VALUE may contain Lean braces — safe, `.format` does not re-scan substituted values.
BACKTRANSLATE_PROMPT = (
    "Translate this Lean 4 theorem statement into a precise one-sentence natural-language math "
    "statement. Preserve EVERY hypothesis and the exact conclusion (do not strengthen, weaken, "
    "or drop anything). Output ONLY the sentence.\n\n{lean_statement}"
)

# DIRECTIONAL faithfulness judge (the round-trip's adjudicate leg). MAJORITY-OF-N at the call site; the prompt
# explicitly says MORE PRECISION is NOT strengthening — the 2026-06-11 flaky-judge fix (#105).
DIRECTIONAL_JUDGE_PROMPT = (
    "You are a strict faithfulness judge for a PROVING pipeline. Two natural-language math statements:\n"
    "ORIGINAL (informal): {orig_nl}\nCANDIDATE (back-translated from a formalization): {back_nl}\n\n"
    "The test is: would PROVING the CANDIDATE establish the ORIGINAL's claim, on the SAME hypotheses (none "
    "added or dropped)? Answer NOT_EQUIVALENT if the candidate DROPS, ADDS, or RESTRICTS a hypothesis (e.g. "
    "narrows the domain, assumes the field splits / poles are rational, adds a side condition the original "
    "lacks), or makes the conclusion WEAKER or DIFFERENT (e.g. = weakened to ≤, an equality changed, a "
    "∀-claim weakened to ∃). TWO things are FAITHFUL — do NOT flag them: (1) the candidate may be MORE PRECISE "
    "/ MORE EXPLICIT (spelling out quantifiers, naming the field/extension a root or residue lives in, making "
    "an implicit 'for all' explicit) — that is the faithful FORMAL meaning; (2) for an EXISTENCE conclusion the "
    "candidate may be CONSTRUCTIVE / EXHIBIT AN EXPLICIT WITNESS (e.g. 'F = <formula> with F' = f' instead of "
    "'∃ F, F' = f') — a construction PROVES the existence, so a STRONGER or more-explicit CONCLUSION is "
    "faithful and can NEVER launder (proving more is harder, not easier). In short: a stronger-or-equal "
    "CONCLUSION on the same-or-weaker HYPOTHESES is EQUIVALENT-for-proving; only a weaker/changed conclusion "
    "or a changed/restricted hypothesis set is NOT_EQUIVALENT. Judge the MATHEMATICAL content (does proving "
    "the candidate prove the original?), not the wording. Answer with EXACTLY one token on the first line: "
    "EQUIVALENT or NOT_EQUIVALENT."
)

# Cold cross-family judge for ONE Lean DEFINITION vs the NL intent (def-faithfulness leg). Majority-of-N at
# the call site. `{nl}` / `{decl}` filled at the call site. Moved verbatim from autoformalize._DEF_JUDGE_PROMPT.
DEF_JUDGE_PROMPT = (
    "A natural-language math problem and a Lean DEFINITION extracted from its formalization:\n"
    "PROBLEM: {nl}\nDEFINITION (Lean): {decl}\n\n"
    "Is this definition a FAITHFUL formalization of an object/notion the problem refers to — or is it a "
    "PLACEHOLDER / SHELL / WRONG object (a constant stand-in, an opaque parameter, or a DIFFERENT notion "
    "than intended)? Answer with EXACTLY one token on the first line: FAITHFUL or UNFAITHFUL, then a "
    "one-line reason."
)
