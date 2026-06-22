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

# The API agentic leaf's TASK-NEUTRAL system prompt (kimi/deepseek via the OpenAI-compatible tool loop —
# `api_agentic_leaf.api_agentic_dispatch`). NEUTRAL by design: `default_dispatch` serves proving AND formalizing
# AND planning, so this must NOT hardcode "you are a prover" (that forced kimi to try to PROVE a formalize
# request → tool-loop stall, 2026-06-21). State the tools, obey the caller's prompt + output format.
API_LEAF_SYSTEM = (
    "You are an expert in Lean 4 and Mathlib4. You have two tools: `lean_check` (compile a full Lean snippet "
    "against the warm Mathlib environment and read the diagnostics — `sorry` is allowed) and `mathlib_search` "
    "(Loogle — find a declaration by name substring or type pattern). Use them as needed for the task. Follow "
    "the USER's instructions and requested OUTPUT FORMAT EXACTLY: if asked to PROVE a goal, iterate "
    "draft→lean_check→fix and return the complete proof in a ```lean block (and use `-- GAP:`/`-- STATEMENT-"
    "FALSE:` if you honestly cannot, exactly as the user's prompt specifies); if asked to STATE or FORMALIZE a "
    "theorem, return exactly the requested declaration (e.g. `… := by sorry`) — do NOT try to prove it. Do not "
    "impose a task the user did not ask for."
)


# ── MIGRATED (2026-06-21, byte-identical move): scattered inline move-module prompts consolidated here. ──

# From conjecture.py (_CONJECTURE_PROMPT): MOVE_CONJECTURE backward invent-a-lemma generation.
CONJECTURE_PROMPT = (
    "You are a Lean 4 prover reasoning BACKWARD. The goal below is hard to prove directly. INVENT "
    "exactly ONE genuinely-useful intermediate lemma that, if true, makes the goal provable, then "
    "prove the ORIGINAL goal USING it. Self-contained against `import Mathlib`. Output EXACTLY:\n"
    "LEMMA:\n```lean\ntheorem {lname} : <your lemma statement> := by sorry\n```\n"
    "PROOF:\n```lean\n{goal_head} := by\n  <tactics that REFERENCE {lname}>\n```\n"
    "Rules: the lemma must NOT be trivially true; the PROOF must cite `{lname}` and contain NO `sorry`.\n"
    "GOAL:\n{goal}\n"
)

# From conjecture.py (_SPECIALIZE_PROMPT): MOVE_SPECIALIZE — the "do the easy case first" move.
SPECIALIZE_PROMPT = (
    "You are a Lean 4 prover. The GOAL below may be HARD or OPEN — proving it in full may be infeasible. "
    "Do the mathematician's first move: produce a GENUINELY PROVABLE SPECIAL CASE G' — a real INSTANCE "
    "or RESTRICTION of the goal (fix a parameter to a concrete value; restrict to a small case like n=1; "
    "or add ONE simplifying hypothesis) that is STRICTLY EASIER but NOT vacuous (NOT `True`, not trivially "
    "satisfiable) — then PROVE G' COMPLETELY (NO sorry). G' must be a logical CONSEQUENCE of the original "
    "goal.\n"
    "CRITICAL — make it SUBSTANTIVE, not the TRIVIAL/DEGENERATE CORNER: do NOT set the main object to a "
    "trivial element (0, ∅, the empty/zero/identity/constant case) — that makes the goal's hypotheses "
    "VACUOUSLY true and the result shallow (the analogue of the u≡0 solution of a PDE, the all-zeros SAT "
    "witness, the degenerate fiber). The goal's CHARACTERISTIC HYPOTHESES must remain NON-VACUOUSLY in "
    "force — pick a genuinely easier but still MEANINGFUL instance (a specific NON-trivial parameter value, "
    "a non-empty restricted subclass) where the hard hypotheses still do real work. Output EXACTLY:\n"
    "SPECIAL:\n```lean\ntheorem {sname} : <the special-case statement> := by\n  <full proof, NO sorry>\n```\n"
    "IMPLIES:\n```lean\ntheorem {sname}_from_general (hG : <the original goal's conclusion>) : "
    "<the special case's conclusion> := by\n  <short proof deriving the special case FROM the general goal>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. Both theorems must be sorry-free.\n"
    "{ban}ORIGINAL GOAL to specialize FROM:\n{goal}\n"
)

# From conjecture.py (_FALSIFY_PROMPT): MOVE_FALSIFY — the "is the target actually FALSE?" producer.
FALSIFY_PROMPT = (
    "You are a Lean 4 prover acting as a SKEPTIC (Popper inversion). The statement below is CONJECTURED "
    "and MIGHT BE FALSE. Your job is to try to REFUTE it: prove its NEGATION. Do not be diplomatic — if "
    "the statement is false, exhibit the disproof; if you cannot, say so.\n"
    "The refutation theorem's SIGNATURE is FIXED for you (you do NOT write it):\n"
    "    theorem {fname}_refute : ¬ ({gprop}) := <your proof>\n"
    "Typically: for a ∀-statement, supply a concrete COUNTEREXAMPLE witness and prove the predicate fails "
    "on it (`by intro h; ...`, `by push_neg`, `by simp`, `by omega`, `by decide`, or a proof TERM like "
    "`fun h => absurd (h 0) (by decide)`). Output EXACTLY:\n"
    "HELPERS:\n```lean\n<optional sorry-free helper lemmas/defs, or leave the block empty>\n```\n"
    "PROOF:\n```lean\n<the COMPLETE proof that goes after `:=` — a `by` tactic block OR a proof term; "
    "NO `theorem` line, NO sorry>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. If you genuinely cannot refute it, output an "
    "empty PROOF block (an honest non-refutation, NOT a sorry).\n"
    "{pre}CONJECTURED statement to REFUTE:\n{goal}\n"
)

# From conjecture.py (_CORROBORATE_PROMPT): MOVE_CORROBORATE — Popper dual of falsify (refute a consequence).
CORROBORATE_PROMPT = (
    "You are a Lean 4 prover acting as a SKEPTIC (Popper inversion via a CONSEQUENCE). The statement G below "
    "is CONJECTURED and MIGHT BE FALSE. Instead of refuting G directly, find a CONSEQUENCE K of G that is "
    "EASIER to decide — typically a concrete INSTANCE or a decidable corollary — and try to REFUTE that "
    "consequence. If `G → K` holds and `¬K` holds, then G is false (modus tollens).\n"
    "Choose K so that: (1) `G → K` is EASY to prove (K is a weakening/instance of G — apply G to a specific "
    "witness, project a conjunct, etc.), and (2) `¬K` is provable (K is a decidably/constructively FALSE "
    "consequence — e.g. evaluate at a counterexample with `by decide`/`by omega`/`by simp`).\n"
    "Output EXACTLY:\n"
    "CONSEQUENCE:\n```lean\n<the Prop K — JUST the type expression, e.g. `P 7` or `∀ n, n ≤ f n`; it may "
    "reference G's binders>\n```\n"
    "IMPLIES:\n```lean\n<the proof body after `:=` for `({G}) → (K)` — a `by` block or a term; NO theorem "
    "line, NO sorry>\n```\n"
    "REFUTE:\n```lean\n<the proof body after `:=` for `¬ (K)` — a `by` block or a term; NO sorry>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. If you cannot find a refutable consequence, "
    "output an empty REFUTE block (an honest non-refutation, NOT a sorry).\n"
    "{pre}CONJECTURED statement G:\n{goal}\n"
)

# From conjecture.py (_TACTIC_STEP_PROMPT): MOVE_TACTIC_STEP — per-step agentic tactic search.
TACTIC_STEP_PROMPT = (
    "You are proving a Lean 4 goal ONE TACTIC AT A TIME. Below is the CURRENT proof state (hypotheses and "
    "the goal remaining after the tactics applied so far). Emit the SINGLE next tactic that makes the most "
    "progress — JUST the tactic on one line: NO `by`, NO commentary, NO code fences. If the goal closes in "
    "one step, emit that closing tactic.{err}\n\nCURRENT PROOF STATE:\n{goal}\n"
)

# From conjecture.py (_GENERALIZE_PROMPT): MOVE_GENERALIZE — the induction-strengthening move.
GENERALIZE_PROMPT = (
    "You are a Lean 4 prover. The GOAL below is hard, likely because it is TOO SPECIFIC — proving it "
    "directly gives no inductive leverage. Use the INDUCTION-STRENGTHENING move: inside the proof, first "
    "establish a STRONGER, more general fact G' (via `have`/`suffices`) that is EASIER to prove because "
    "the stronger statement yields a stronger inductive hypothesis; then close the ORIGINAL goal as an "
    "INSTANCE of G'. Output EXACTLY one fenced block — the COMPLETE proof of the original goal AS STATED "
    "(do NOT change its statement), NO sorry, NO admit:\n"
    "PROOF:\n```lean\nby\n  -- strengthen: have {gname} : <stronger statement> := by <proof of the stronger fact>\n"
    "  -- then close the original goal from {gname}\n  <full tactic proof, NO sorry>\n```\n"
    "The proof body must be self-contained against `import Mathlib` + the PREAMBLE and must fit directly "
    "after the goal's `:=`.\nORIGINAL GOAL (prove EXACTLY this, do not weaken or restate):\n{goal}\n"
)

# From conjecture.py (_REVIEW_PROMPT): decomposition_review — per-edge productivity filter (advisory).
REVIEW_PROMPT = (
    "You are reviewing a proposed proof DECOMPOSITION. The MAIN goal G is:\n{goal}\n\n"
    "A prover proposes proving G via this intermediate lemma L:\n{lemma}\n\n"
    "Judge whether L is a GOOD decomposition. YES only if ALL hold: (1) L is STRICTLY EASIER than G "
    "(a genuine reduction, not the same difficulty); (2) L is NOT a restatement of G or a trivial "
    "rephrasing (non-circular); (3) proving L plausibly makes G follow. Answer with EXACTLY one token "
    "on the first line: WORTHY or NOT_WORTHY, then a one-line reason."
)

# From reflection.py (_REFLECTION_PROMPT): MOVE_REFLECTION — proof by reflection/evaluation.
REFLECTION_PROMPT = (
    "You are a Lean 4 prover using PROOF BY REFLECTION / EVALUATION. The GOAL below is FINITE / DECIDABLE "
    "(a concrete instance, a bounded `∀ n < N`, an enumerable case split, a fixed numeric/finite-set fact). "
    "Do NOT prove it by hand. Instead:\n"
    "  1. Write an EFFICIENT, structurally-recursive Boolean PROGRAM `def {cname} {binders} : Bool := <body>` "
    "that DECIDES the goal's predicate by COMPUTATION. CRITICAL — the whole point of reflection is a Bool "
    "program the KERNEL reduces FASTER than the goal's auto-derived `Decidable` instance, so:\n"
    "     • USE a fold / `.all` / `.any` / `.filter` over `List.range N` (or an `Array`) with cheap `Nat` "
    "ops (`Nat.ble`, `==`, `%`, `&&`, `||`, binary arithmetic). This avoids the unary `Nat.decidableBallLT` / "
    "`Finset.decidableBAll` recursion that makes plain `decide` blow up.\n"
    "     • Do NOT write `def {cname} := decide (<the goal>)` or call `decide`/`Decidable` INSIDE the body — "
    "that just re-runs the SAME slow instance plain `decide` already uses and gains ZERO lift (it is rejected).\n"
    "     • The body MUST do real work — NOT the constant `true`/`false`.\n"
    "  2. Prove its SOUNDNESS: `theorem {sname} {binders} : {cname} {args} = true → <the goal's conclusion> "
    ":= by <proof>` — i.e. if the program returns `true`, the goal's predicate HOLDS. NO sorry.\n"
    "  3. Close the ORIGINAL goal by EVALUATION: apply the soundness theorem to a `by decide` proof that the "
    "program returns `true` on the goal's arguments.\n"
    "Use plain `by decide` (it is kernel-checked and axiom-clean); do NOT use `native_decide` (it adds the "
    "Lean.ofReduceBool axiom, which is BANNED here).\n"
    "Output EXACTLY three fenced blocks:\n"
    "CHECK:\n```lean\ndef {cname} {binders} : Bool := <decision procedure — NOT a constant>\n```\n"
    "SOUND:\n```lean\ntheorem {sname} {binders} : {cname} {args} = true → <goal conclusion> := by\n  <proof, NO sorry>\n```\n"
    "CLOSE:\n```lean\n<the proof body that goes after the goal's `:=` — e.g. `{sname} (by decide)` or "
    "`by exact {sname} (by decide)` — NO sorry, NO native_decide>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. If the goal is NOT finite/decidable (no "
    "terminating decision procedure exists), output an EMPTY CHECK block (an honest non-attempt, NOT a sorry).\n"
    "{pre}GOAL to decide by reflection:\n{goal}\n"
)

# From spectral_lift.py (_FUNCTOR_LIFT_PROMPT): MOVE_FUNCTOR_LIFT — discrete→spectral lift.
FUNCTOR_LIFT_PROMPT = (
    "You are a Lean 4 + spectral-graph-theory expert. The GOAL below is a DISCRETE / combinatorial claim "
    "about a FINITE structure (a graph, a finite 0/1 or integer matrix, a finite group's Cayley graph). "
    "Proving it directly is hard. Use the FUNCTOR LIFT: map the discrete object to a MATRIX, pass to its "
    "SPECTRUM (eigenvalues / spectral gap), and bound the discrete property with a CONTINUOUS spectral "
    "bound (Expander Mixing Lemma, Cheeger inequality, Hoffman bound, eigenvalue interlacing).\n"
    "CRITICAL — the continuous bound must be discharged by an EXISTING Mathlib lemma (the 'bridge'/pullback "
    "of the spectral statement back to the discrete one). NAME that exact Mathlib lemma; do NOT invent a new "
    "one (a bridge that does not already exist will be REJECTED — that is not your job here).\n"
    "Output EXACTLY these four blocks:\n"
    "MATRIX:\n```json\n{{\"matrix\": [[<row0>], [<row1>], ...], \"kind\": \"adjacency\"}}\n```\n"
    "   (the concrete finite matrix the discrete object maps to — a rectangular list-of-lists of integers; "
    "for a graph use its symmetric 0/1 adjacency matrix)\n"
    "BRIDGE:\n```lean\n<the fully-qualified name of the EXISTING Mathlib bridge lemma, e.g. "
    "`Matrix.IsHermitian.eigenvalues` — JUST the name, nothing else>\n```\n"
    "SPECTRAL:\n```lean\n<a one-line Lean comment stating the continuous bound you will instantiate, e.g. "
    "`-- e(S,T) ≤ (d/n)|S||T| + λ√(|S||T|)` — for the human/audit log only>\n```\n"
    "PROOF:\n```lean\n{goal_head} := by\n  <tactics that APPLY the BRIDGE lemma to close the goal; NO sorry, "
    "NO admit; must reference the bridge lemma>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. The PROOF must cite the BRIDGE lemma in real "
    "tactic text and contain NO sorry.\nGOAL:\n{goal}\n"
)

# From proof_margin_of_safety.py (_RUNG_TIGHTEN_PROMPT): RUNG-TIGHTENING (M5) — proof mining.
RUNG_TIGHTEN_PROMPT = (
    "You are a Lean 4 prover doing PROOF MINING. The kernel-verified RUNG below proves a NON-CONSTRUCTIVE "
    "fact (an existence / a non-explicit bound). Extract the EXPLICIT, STRICTLY STRONGER statement B it "
    "implies — make a witness/constant/rate CONCRETE (e.g. the rung asserts `∃ N, P N`; B is `P 5` for a "
    "specific value, or an explicit rate in place of `∃ C`). Then PROVE B completely, and prove that B "
    "IMPLIES the rung. Output EXACTLY:\n"
    "BOUND:\n```lean\ntheorem {bname} : <the explicit stronger statement B> := by\n  <full proof, NO sorry>\n```\n"
    "IMPLIES:\n```lean\ntheorem {bname}_to_rung (hB : <B's conclusion>) : <the rung's conclusion> := by\n"
    "  <short proof deriving the rung FROM B>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. Both sorry-free. B must be STRICTLY STRONGER "
    "(more explicit) than the rung — NOT a restatement.\n{pre}RUNG:\n{rung}\n"
)

# From autoformalize_notes.py (_THEORY_PROMPT): THEORY CONSOLIDATION — campaign theory-building dispatch.
THEORY_PROMPT = (
    "THEORY CONSOLIDATION (definitions are first-class deliverables). You own the campaign theory file "
    "`{path}` in the Lean project `{root}`. The campaign target:\n{target}\n\nBlueprint notes follow at the "
    "end. Your job THIS dispatch: EXTEND the theory file with the missing FORMAL SUBSTRATE the blueprint "
    "needs and Mathlib lacks.\n"
    "DEFINITION DISCIPLINE — a definition has NO kernel oracle; it is judged by WORKABILITY, so work "
    "like a library designer, not a prover: (1) DIVERGE: for each needed concept draft 2-3 candidate "
    "formalizations (different shapes: a def via derivatives vs via coefficients vs via an existing "
    "Mathlib structure). (2) TRIAL: for each candidate, try to prove its MODEL-CASE sanity lemmas "
    "IMMEDIATELY (e.g. the concept evaluated on the simplest known instance gives the known answer; "
    "consistency with already-proven campaign rungs). (3) SELECT the candidate whose sanity lemmas "
    "PROVED — workability evidence, never taste — and ship: the chosen `def`/`structure`, its PROVEN "
    "sanity lemmas (no sorry on these), and the deeper API lemma STATEMENTS (those may be `sorry`; each "
    "becomes a solver work item). Prefer Mathlib-idiomatic shapes (typeclasses, existing algebraic "
    "structures) so library lemmas apply — search before inventing. (4) KILL LEG: if a candidate (or an "
    "EXISTING campaign structure) resists EVERY sanity instance, suspect it is UNINHABITED — try to PROVE "
    "`<name>_impossible` (its hypothesis set implies False / no instance exists). A COMPILED impossibility "
    "is a first-class deliverable: it kernel-certifies the route correction, and nothing may be built on "
    "that structure afterward. Prefer definitional bundling over compatibility hypotheses (fields "
    "definitionally equal to the source formula beat `h_compat : a = b` side-conditions — fewer "
    "assumptions to kill later). CREDIT: definitions earn through USE — your proven sanity lemmas count "
    "as rungs now; the definition itself is credited when campaign lemmas cite it.\n"
    "(5) PIN THE DENOTATION (anti-decoy). Sanity lemmas prove a def is WORKABLE, not that it MEANS the "
    "intended concept — a self-consistent decoy can pass them all. So for EACH new `def`, anchor it to a "
    "TRUSTED reference: search Mathlib (Loogle/warm checker) for the concept your def extends, and if one "
    "exists state `theorem anchor_<def>_agrees_<ref> : ∀ …, <your def> … = <Mathlib concept> …` over the "
    "OVERLAP domain (where both are defined). These `anchor_…` theorems may be `sorry` — each becomes a "
    "work item like any API lemma; a kernel-PROVEN anchor pins the def's denotation (a decoy cannot prove "
    "agreement with the established concept). If your def is genuinely BEYOND Mathlib (no overlapping "
    "concept), say so honestly in a `-- @no-anchor: <def>: <why no Mathlib overlap>` comment — its "
    "denotation then rests only on API + composition (the harness reports this as UNDER-DETERMINED, an "
    "honest gap, never a false certification). Name every such theorem with the `anchor_` prefix.\n"
    "APPEND-ONLY THIS DISPATCH: never modify or delete existing content (governance reverts the round if "
    "existing bytes change). If an EXISTING definition is wrong-shaped, do not edit it — state "
    "`-- SUPERSEDE: <name>: <why>` and the harness routes a governed revision. Verify the file COMPILES "
    "(sorry allowed only on deep API) with the warm checker before finishing. Quality bar: minimal, "
    "citable, foundational-first — a library others build on.\n\nBLUEPRINT:\n{notes}\n")

# From solver_core.py (_POOL_PROMPT_TMPL): the governed proposer-pool prove-this template.
POOL_PROMPT_TMPL = (
    "Prove this Lean 4 (Mathlib) theorem. Output ONLY the proof — a single `by ...` tactic block — inside ONE "
    "```lean fenced code block. Do NOT restate the signature and put NO prose inside the fence.\n\n"
    "{goal} := by\n  sorry\n")

# From witness_transport.py (SCRIPT_PROMPT): MOVE_WITNESS_TRANSPORT — SymPy witness-finding script writer.
SCRIPT_PROMPT = (
    "You are a Python tool-writer. Below is a Lean 4 EXISTENTIAL goal. Do NOT prove it. WRITE A PYTHON SCRIPT "
    "using ONLY sympy (and json/math) that EXTRACTS the algebraic constraints and FINDS a satisfying witness "
    "for the existential variables, then prints EXACTLY ONE JSON object to stdout:\n"
    '  {{"ok": true, "witnesses": ["<v0>", "<v1>", ...]}}\n'
    "Solve in the goal’s domain (integers for ℕ/ℤ; reals/rationals for ℝ/ℚ). Output integer/rational "
    'LITERALS (no floats — use 6 or 3/2). If no witness, print {{"ok": false, "witnesses": []}}. Output ONLY '
    "the script in one ```python block — no prose, no file/network/os access.\nGOAL:\n{goal}\n"
)
