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

from ztare.leanmill.prompts import (
    AXIOM_PACK_BAND_WORD_PROPOSER_PROMPT,
    AXIOM_PACK_SEMANTIC_CHECKER_PROMPT,
    AXIOM_PACK_TYPED_PROPOSER_PROMPT,
)

# AXIOM-PACK typed proposal/checker prompts. These are deliberately separate
# roles: the proposer emits candidate structure; the checker judges intent and
# the host signs the verdict. Payloads are inserted as data at the call site.
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
    "  python -m ztare.formal.lean_check_server --check {socket} {probe}{sorry_flag}\n"
    "It returns in ~0.1s (warm Mathlib), reads the FILE on disk, and prints the EXACT `error:` lines to fix. "
    "Iterate write→check→fix until it is clean; only use `lake env lean` if it prints 'server unreachable'. A "
    "`sorry` does NOT count as done — the harness REJECTS any `sorry`, so keep going until the check shows zero "
    "errors AND the proof is complete (the `--reject-sorry` flag, when present, surfaces a remaining `sorry` in "
    "the file as an `error:` to fix — a bare `sorry` stub will NOT pass).")

LEAF_DIRECT_PREFIX = (
    "Prove `{target}` : {goal} by EDITING the file {probe} (currently `sorry`): WRITE the complete proof into "
    "that file, replacing the `sorry`. The SAVED file with no `sorry` is the deliverable — do NOT merely "
    "describe the proof or claim it is already done; the harness verifies the file ON DISK, not your message. ")

LEAF_DECOMPOSE_PREFIX = (
    "The theorem `{target}` : {goal} in {probe} is hard. {gap_fb}Work BACKWARD like a mathematician: "
    "identify the intermediate lemmas the real proof needs; prove each, or leave a `-- GAP:` on the ones you "
    "genuinely cannot; then assemble `{target}` from them. WRITE the full DAG (helper lemmas + the assembled "
    "`{target}`) into the file {probe} — the saved file is the deliverable, not your message. ")

LEAF_DECOMPOSE_GAP_FB = ("Your direct attempt diagnosed this missing piece: «{gap}». Build the decomposition "
                         "toward proving it. ")

# DIRECT-CONTINUATION (2026-07-03): a pure "next turn" nudge for warm-resume — `codex exec` is ONE turn, so on a
# hard proof the agent plans then its turn ends mid-proof; this gives it the next turn to finish its OWN work. It
# deliberately injects NO compiler errors and NO fix-strategy (that would be the harness driving — the reverted
# error-feedback loop): the agent re-runs its OWN warm-check and fixes its OWN proof. Affordance, not determinism.
LEAF_DIRECT_CONTINUE = (
    "Your proof of `{target}` in the file {probe} is NOT finished — it does not yet compile with zero errors. "
    "CONTINUE from where you left off (do NOT restart from scratch): keep editing that file and re-checking with "
    "the warm lean-check after each edit until it reports ZERO errors and contains NO `sorry`. Finish it.")

# SCAFFOLD-CONTINUE (2026-07-06, gale-Shapley thrash fix): the file is pre-seeded with helper lemmas HARVESTED
# from your own prior attempts on this goal — they are already PROVEN and compile. The point is to stop you
# rebuilding them every dispatch. So: do NOT re-derive or rewrite the helper lemmas above; cite them and prove
# ONLY the remaining `sorry` target on top of them.
LEAF_SCAFFOLD_CONTINUE = (
    "The file {probe} already contains helper lemmas that are PROVEN and compile — they are the reusable pieces "
    "from earlier attempts on `{target}`. Do NOT rewrite, re-derive, or delete them. Prove ONLY the remaining "
    "`sorry` (the `{target}` goal) by BUILDING ON those helpers: cite them by name. Re-check with the warm "
    "lean-check after each edit until it reports ZERO errors and contains NO `sorry`.")

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
    # MECE framing (2026-06-23): two ORTHOGONAL dimensions, asked truth-FIRST. Dim A (truth: TRUE→prove vs
    # FALSE→falsify) is a clean ME+CE binary; Dim B (proof-HOW: direct vs decompose) is a sub-choice under
    # "prove". FALSIFY is the truth-dimension OTHER-branch, NOT a flat peer of direct/decompose — see
    # docs/concepts/leanmill_architecture.md §4.3a. The "context may already refute it" cue is GENERAL (any goal
    # can be false; any context can hold a refutation) — not a target-specific hint, so it does not overfit.
    "You are a Lean 4 proof strategist. FIRST decide whether the GOAL is even TRUE, THEN how to act:\n"
    "  1. Is the goal plausibly TRUE? If so, choose HOW to prove it — DEFAULT TO SOLVE_DIRECT:\n"
    "     • SOLVE_DIRECT — prove G yourself in ONE proof, GRINDING a long/careful proof if needed. You are a "
    "frontier prover: an induction, a `cases`/`split` on a definition's branches, chasing `OrderDual`/`max?`/"
    "membership/`filter` facts through 50–150 lines is STILL direct — length and difficulty are what "
    "SOLVE_DIRECT is FOR. Prove it here.\n"
    "     • DECOMPOSE — ONLY when the proof genuinely needs a REUSABLE lemma that must be stated + proven + "
    "cited on its own: a general prerequisite several siblings share, or a lemma Mathlib lacks. If you cannot "
    "NAME that reusable prerequisite and say why it must be separate, the goal is within reach — choose "
    "SOLVE_DIRECT. Splitting a leaf you could just prove is the failure mode; 'it is long' / 'it is hard' is "
    "NOT a reason to decompose.\n"
    "  2. Or is the goal FALSE as stated? Before assuming you must prove it, judge whether it is even true — "
    "your CONTEXT / SUBSTRATE may ALREADY REFUTE this formulation (an impossibility theorem, or a counterexample "
    "to a too-weak hypothesis). If it is false:\n"
    "     • FALSIFY — prove ¬GOAL (a kernel-checked counterexample). Do NOT grind a proof that cannot exist; the "
    "engine will then reformulate toward the intended TRUE statement.\n"
    "Be decisive: DECOMPOSE only earns its place when it buys a REUSABLE sub-lemma you can NAME — otherwise "
    "default to SOLVE_DIRECT and grind the full proof. Do NOT grind a proof of a FALSE statement (choose "
    "FALSIFY). Judge the MATHEMATICAL content, not the surface length.\n"
    "Answer with EXACTLY one token on the FIRST line: SOLVE_DIRECT, DECOMPOSE, or FALSIFY.\n\nGOAL:\n{goal}\n"
)

# Reformulation re-entry feedback (general-purpose; assembled by `autoformalize._reformulate_feedback`). Fires
# AFTER a formalization is KERNEL-REFUTED (¬G proven). ADVISORY, not coercive — it orients the agent to
# strengthen the too-weak hypothesis and OFFERS its own already-proven substrate results to cite IF one matches;
# the agent judges relevance and the kernel re-verifies every citation (a wrong `exact` simply fails to compile),
# so it cannot launder or mislead into a false close. No domain specifics. `{shelf_block}` is empty unless the
# substrate has proven theorems. Filled VALUES may contain Lean braces — that is safe (`str.format` only expands
# the template's own `{…}` placeholders, never the substituted values).
REFORMULATE_FEEDBACK = (
    "\n\n[REFORMULATE] A prior formalization of this target was REFUTED as FALSE during proving:\n"
    "  {prior_stmt}\n"
    "Refutation (the case that BREAKS it — read it to see WHICH hypothesis is too weak):\n"
    "  {refutation}\n"
    "The refutation means the literal reading is FALSE: a hypothesis is too weak for the conclusion to hold. "
    "Produce the INTENDED, TRUE statement — which usually needs a STRONGER hypothesis than the most literal "
    "reading of the prose (a named order / complementarity / regularity condition typically means the version "
    "under which the result is actually true).{shelf_block} STRENGTHEN the offending hypothesis to exclude the "
    "refuting case; do not weaken the conclusion, and do not re-emit a hypothesis as weak as the refuted one. The "
    "faithfulness firewall re-checks against the original problem: a strengthening toward the intended mathematics "
    "is faithful; a different or weaker theorem is not."
)
# Offered ONLY when the substrate has proven results — advisory ("IF one matches … else prove it yourself"), so
# it routes the agent to its own correction without forcing a (kernel-gated) wrong cite.
REFORMULATE_SHELF_BLOCK = (
    " If one of these ALREADY-PROVEN (sorry-free, kernel-checked) results from your substrate IS the intended "
    "theorem, formalize the target to match it and CITE it (e.g. `exact <name> …`) instead of re-deriving; if "
    "none matches, state and prove the strengthened version yourself:\n{shelf}"
)

# ESTABLISHED VOCABULARY (2026-06-24, the orphaned-shelf / def-drift cure). Surfaces the campaign's CANONICAL
# definition BODIES (the proven lemmas were checked against THESE) so a fresh formalizer reuses them by reference
# instead of re-deriving a divergent same-named def from the prose — the drift that silently orphans the shelf at
# compose time (the proven lemmas can't be cited against a different body, so the target solves bare → exact_gap).
# AGENCY-preserving: it supplies vocabulary + a norm; the agent still chooses (reuse, or extend under a NEW name +
# bridge). The faithfulness firewall + the compose conflict-check remain the only deterministic boundary.
ESTABLISHED_DEFS_NOTE = (
    "\n\n## Established definitions (reuse VERBATIM — do NOT redefine)\n"
    "The campaign's already-proven lemmas were checked against these EXACT definitions. When your statement "
    "uses any of these concepts, COPY the definition verbatim into your probe; do NOT re-derive it from the prose. "
    "A same-named definition with a DIFFERENT body silently orphans the proven lemmas (they cannot be cited against "
    "it), forcing everything to be re-proved from scratch. If the intended theorem genuinely needs a STRONGER "
    "notion than one of these, introduce a NEW name (e.g. `FooStrict`) plus a bridge lemma relating it to the "
    "established `Foo` — never shadow an established name with a different body.\n```lean\n{defs}\n```"
)

# PROVEN-SHELF AT FORMALIZE (2026-06-25, the AMM `reachable_pool_wellFormed` gap RCA). The DEFINITION-body
# companion above surfaces the canonical DEFS at the formalize chokepoint, but the proven-LEMMA shelf
# (`_substrate_proven_shelf` — each banked rung's EXACT, kernel-checked conclusion) was surfaced ONLY in the
# reformulation feedback, never at FIRST-PASS formalize. So a compounding target whose prose NAMES a banked rung
# (e.g. "cite executeTrades_keep_wellFormed for endpoint well-formedness") was formalized BLIND to what that rung
# actually CONCLUDES — the bank proves the trajectory predicate `TradesKeepWellFormed`, not the endpoint
# `PoolWellFormed (executeTrades …)`, so the target matched no banked conclusion, no cite fired, and the
# decomposition produced only the single-trade base case → honest gap. Surfacing the actual conclusions here lets
# the formalizer either MATCH a banked rung's statement (instant cite) or introduce the target as a DISCLOSED
# corollary that cites the rung plus a small bridge — instead of inventing a citable-SOUNDING statement that is
# not. Advisory + AGENCY-preserving (the faithfulness firewall still gates; the agent still chooses match vs
# extend); embedder-INDEPENDENT (lexical read of the substrate .lean), so it holds even when the semantic shelf
# is dead. "" ⇒ byte-identical to before.
PROVEN_SHELF_NOTE = (
    "\n\n## Already-PROVEN, kernel-checked results in this campaign's library (CITE — do NOT re-derive)\n"
    "These lemmas are banked and in scope. Read their EXACT conclusions: if your target IS one of them, "
    "formalize it to MATCH the banked statement and cite it (`exact <name> …`). If your target is a COROLLARY of "
    "one (e.g. an ENDPOINT extracted from a trajectory/sequence invariant, or a specialization), state it as a NEW "
    "lemma that CITES the banked rung and discharges the small remaining bridge — do NOT restate a banked result "
    "under a conclusion it does NOT have (that matches no banked lemma, so nothing can be cited and the whole "
    "result is re-proved from scratch or gaps). The prose may NAME a rung loosely; trust these signatures over the "
    "prose's paraphrase of what they conclude.\n{shelf}"
)

# CARRIER-PRESERVATION (2026-07-05, the CLOB carrier-ghost that blocked autonomous closure). The def bodies above
# carry the substrate's EXACT typeclass instances (e.g. `[LinearOrder K]`), but a self-contained re-declaration lets
# the LLM substitute a WEAKER order (`[LT K]`/`[LE K]`) — a partial-order version that is a DIFFERENT, FALSE theorem
# (an antisymmetric partial order cannot compare all prices, so the "best bid ≤ every bid" safety claim fails). The
# carrier gate then correctly REJECTS it → reject loop → the campaign never closes. Surface the substrate's own
# `variable` context VERBATIM (the single-door `campaign_variables`) so the formalizer preserves the instances at the
# SOURCE, instead of the gate catching the weakening downstream every run. Monotone (only the substrate's consistent
# carrier) + ADVISORY (the firewall + carrier gate stay the deterministic boundary); domain-agnostic. "" ⇒ byte-parity.
CARRIER_CONTEXT_NOTE = (
    "\n\n## Carrier context (use these `variable` declarations VERBATIM — do NOT weaken the order)\n"
    "The established definitions above were registered under these EXACT `variable` declarations and typeclass "
    "instances. Re-state them verbatim in your probe. Do NOT substitute a WEAKER order instance — never replace a "
    "`[LinearOrder _]` with `[LT _]`/`[LE _]`/`[Preorder _]`/`[PartialOrder _]`: the theorem is FALSE under a weaker "
    "order (a partial order cannot compare all elements), and a weakened re-declaration is REJECTED as unfaithful to "
    "the registered substrate.\n```lean\n{carrier}\n```"
)

# LITERAL-FIRST cue (general-purpose; the INVERSE of REFORMULATE_FEEDBACK). Injected on the ONE bounded re-entry
# after the firewall REJECTED a first formalization as a silent STRENGTHENING of the literal claim (round-trip-
# unfaithful + extra hypotheses) with no ¬G license yet. The honest, non-gamable order is truth-FIRST: render the
# claim EXACTLY as the text states it, let the engine establish its truth-status with the KERNEL (prove or refute),
# and only THEN — if it is false — propose the strengthened, true version as a DISCLOSED correction (the existing
# reformulation path). This cue is purely a FAITHFULNESS instruction (the firewall's own contract), so it can feed
# no answer and launder nothing; the firewall re-checks the result. No domain specifics.
LITERAL_FIRST_CUE = (
    "\n\n[LITERAL-FIRST] Formalize the claim EXACTLY as the natural-language text states it — its most literal "
    "reading. Do NOT pre-emptively add hypotheses you believe are needed to make it true, and do NOT substitute a "
    "stronger corrected theorem even if your context/substrate already contains one: render the LITERAL claim here. "
    "If the literal claim turns out to be false, that is expected and fine — the engine establishes its truth-status "
    "with the kernel and will then invite you to propose the strengthened, true version as a disclosed correction. "
    "State the literal claim now."
)

# GOVERNANCE proof-constraint lines injected into the PROVING leaf prompt (via move_cards.render_tool_block).
# The agent's proof is re-audited with `#print axioms`, so a `native_decide`/`sorry`/`admit` "closure" is
# rejected even though it compiles — tell it UP FRONT (#104) so it doesn't waste effort on a banned tactic.
GOVERNANCE_PROOF_CONSTRAINTS_LINES = (
    "GOVERNANCE (your proof is re-audited with `#print axioms`): do NOT use `native_decide` — it adds the",
    "`Lean.ofReduceBool` compiler-trust axiom and your closure is REJECTED even though it 'compiles'. Use",
    "`decide` for kernel-decidable goals (kernel-checked, axiom-clean). Never use `sorry`/`admit`.",
)

STRUCTURAL_ISOMORPHISM_MOVE_CARD = (
    "De-anchor from the current surface and ask the shared research-isomorphism engine for structural analogies "
    "or conjectural correspondences. Use it when your current heuristics are cycling, when an AxiomPack blueprint "
    "needs candidate structure, or when the same residual appears under several names. The output is a "
    "quarantined proposal with kill conditions and mappings; it may seed a blueprint, lemma plan, or research "
    "note, but it is not proof credit and cannot mutate the Lean substrate."
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

# GENERALITY-FIDELITY judge (the neural half of the typeclass-generality leg, `autoformalize.typeclass_generality_audit`).
# The model knows the Lean instance hierarchy + mathematical generality — so it replaces a hardcoded class/keyword
# registry (which was overfit + brittle). Majority-of-N, advisory (FLAG only on a strict majority of NARROWER).
GENERALITY_JUDGE_PROMPT = (
    "You are checking GENERALITY FIDELITY of a Lean 4 formalization against its informal intent: does the formal "
    "statement assume a MORE SPECIAL / STRONGER mathematical structure than the intent's stated generality, thereby "
    "silently NARROWING the claim?\n\n"
    "The statement assumes these typeclass instances: {classes}\n"
    "Formal statement (signature): {stmt}\n\n"
    "Informal intent (may be a blueprint that states the GENERAL form AND also mentions special cases):\n{nl}\n\n"
    "The Lean instance hierarchy is a STRENGTH order — a stronger instance is a stronger hypothesis, hence a NARROWER "
    "theorem. NARROWING examples: intent says 'partial order / pari-passu / incomparable allowed' but the statement "
    "assumes `[LinearOrder]` (a strict TOTAL order — prohibits incomparable elements); intent 'arbitrary ring' but "
    "`[Field]`; intent gives no finiteness/decidability but the statement adds `[Fintype]`/`[DecidableEq]`. It is "
    "FAITHFUL when the intent EXPLICITLY restricts to the strong structure ('linear/total order', 'field', 'finite'), "
    "or when the assumed instances are no stronger than the intent implies. When the intent states a general form AND "
    "names a special case, shipping ONLY the special case is NARROWER.\n\n"
    "Answer on the FIRST line EXACTLY one of:\n"
    "  NARROWER: <which assumed instance is too strong; what more-general structure the intent implied>\n"
    "  FAITHFUL"
)

# The ADDED-HYPOTHESIS face of the same ambition gap (§4.2a: nothing formal checks statement ⊨ NL ambition).
# GENERALITY_JUDGE_PROMPT covers narrowing hidden in INSTANCE binders; this covers narrowing added as an EXPLICIT
# hypothesis binder — the round-trip judge's documented weak leg ("if the round-trip judge does not reliably catch
# *added-hypothesis* weakenings ... that is the frontier to harden", §4.2a). Canonical instance: Topkis' blueprint-era
# "the unique maximizer" — a uniqueness HYPOTHESIS yields a true-but-WEAK theorem whose conclusion round-trips
# identically, so NL↔Lean faithfulness is blind to it.
ADDED_HYPOTHESIS_JUDGE_PROMPT = (
    "You are checking AMBITION FIDELITY of a Lean 4 formalization against its informal intent: does the formal "
    "statement ASSUME (as an explicit hypothesis) something the intent never granted, thereby silently NARROWING "
    "the claim?\n\n"
    "The statement's explicit propositional hypotheses:\n{hyps}\n"
    "Formal statement (signature): {stmt}\n\n"
    "Informal intent:\n{nl}\n\n"
    "An ADDED hypothesis is one the intent does not state and does not clearly imply — typical smuggles: uniqueness "
    "of an optimum/witness; extra positivity/non-degeneracy; an ordering/comparability assumption; finiteness; "
    "assuming a property the theorem was supposed to PROVE. It is LICENSED when the intent states it, clearly "
    "implies it (well-formedness of the very data the intent describes counts), or it is definitional plumbing "
    "that does not shrink the claim's scope.\n\n"
    "Answer on the FIRST line EXACTLY one of:\n"
    "  ADDED: <which hypothesis is unlicensed; what the intent actually granted>\n"
    "  LICENSED"
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
    "VERIFY BEFORE YOU OUTPUT (this is the difference between a real refutation and a plausible-but-wrong one): "
    "your proof MUST compile. Assemble the full file yourself — the PREAMBLE + `import Mathlib` + "
    "`theorem {fname}_refute : ¬ ({gprop}) := <your proof>` — RUN the Lean checker on it, read the errors, and "
    "ITERATE until ZERO errors and ZERO `sorry`. Use your FULL budget to get it compiling; a single unchecked "
    "shot is worthless. Match the EXACT defs in the PREAMBLE — correct arities, type-class instances, and "
    "namespaces (a structure `Foo (A B : Type*) [inst]` is applied as `Foo A B`, never `Foo A`). Only output "
    "once your own check passes.\n"
    "{nugget}{pre}CONJECTURED statement to REFUTE:\n{goal}\n"
)

# The counterexample NUGGET seed (CEGAR/proof-sketch reuse): when a prior skeptic/leaf already DISCOVERED the
# crux (the witness idea), we reuse the INSIGHT — not the full self-contained proof (which restates over concrete
# types and does not port). The goal below is still OURS and the kernel still verifies, so a wrong nugget merely
# fails to help (it cannot launder). Injected into FALSIFY_PROMPT's `{nugget}` slot.
FALSIFY_NUGGET_SEED = (
    "PRIOR COUNTEREXAMPLE INSIGHT — a skeptic already found the crux for THIS statement. ADAPT it to the exact "
    "goal + preamble below (build the concrete carrier/witness it names and prove the predicate fails); do NOT "
    "re-derive from a blank page. The insight (and any construction) is a HINT — the refutation theorem's "
    "signature is still fixed for you and the kernel re-checks your proof:\n{nugget}\n\n"
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
    "intended concept — a self-consistent decoy can pass them all. So for EACH new `def`, state a kernel-"
    "checkable `anchor_<def>_…`-named theorem tying it to a TRUSTED Mathlib concept (Loogle/warm checker to "
    "find names). A FULL Mathlib equivalent is the easy case, but you almost NEVER need one — a built concept "
    "Mathlib lacks is still pinnable by a WEAKER anchor, and you should ALWAYS find one of these before "
    "reaching for `@no-anchor`:\n"
    "   • OVERLAP-AGREEMENT: `<def> … = <Mathlib concept> …` on the domain where both are defined.\n"
    "   • SPECIAL-CASE REDUCTION: your def on a CANONICAL special case equals/iff a Mathlib concept — e.g. a "
    "set/relation order on SINGLETONS reduces to the element order (`yourSetLE {{a}} {{b}} ↔ a ≤ b`); an operation "
    "at a unit reduces to identity; a parametric family at a constant reduces to a known object. This pins a "
    "concept (a strong set order, a refinement, a divergence) that has NO single Mathlib equal.\n"
    "   • CHARACTERIZATION: `<def> ↔ <property expressible with Mathlib primitives>` (e.g. an increasing-"
    "differences predicate ↔ `∀ x≤x', Monotone (fun t => f x' t - f x t)`).\n"
    "Immediately precede each anchor with a machine-readable declaration: `-- @denotation-anchor: "
    "anchor=<theorem_name>; target=<def>; kind=<definitional|extensional|special_case|model_instance>; "
    "external=<Mathlib_or_Lean_reference>`. The external reference must occur in the theorem type (notation "
    "may use its canonical name, such as `LE.le` for `≤`) and must be distinct from every definition introduced "
    "in this theory. A reflexive theorem such as `<def> = <def>` is rejected before kernel verification.\n"
    "These `anchor_…` theorems may be `sorry` — each becomes a work item like any API lemma; a kernel-PROVEN "
    "anchor pins the def (a decoy cannot prove agreement/reduction/characterization with the established "
    "concept). Reserve `-- @no-anchor: <def>: <why NONE of overlap/reduction/characterization reaches any "
    "Mathlib concept>` for a def that is GENUINELY unanchorable, and justify why each of the three routes "
    "fails — 'Mathlib has no equal' is NOT sufficient when a reduction or characterization exists. An "
    "unanchored def is reported UNDER-DETERMINED (an honest gap, never a false certification). Name every "
    "such theorem with the `anchor_` prefix.\n"
    "(6) GUARD AGAINST VACUOUS TRUTH. A `Prop` def that universally quantifies over set MEMBERSHIP "
    "(`∀ x ∈ s, …` / `∀ ⦃x⦄, x ∈ s → …`) is VACUOUSLY TRUE when the set is EMPTY — so a theorem concluding that "
    "property of a CONSTRUCTED set (an argmax set, a solution/fixed-point set, a correspondence's value) can be "
    "kernel-true while asserting NOTHING. For each such def, either prove a kernel-checked "
    "`theorem witness_<def>_nonvacuous …` establishing the relevant set is NON-EMPTY in a stated meaningful "
    "instance — or under the existence conditions the result actually needs (e.g. a complete lattice + order-"
    "continuity / compactness for an argmax to be inhabited) — OR honestly flag "
    "`-- @vacuity-scope: <def>: <when the set is ∅, and what existence requires>`. The harness reports an "
    "unwitnessed set-property as VACUITY-EXPOSED (an honest gap, never a false certification). Name witnesses "
    "with the `witness_` prefix. This is the existence half of monotone-comparative-statics-style results: state "
    "the comparative statics, and EITHER establish existence OR scope it explicitly — never let `∅` pass as a "
    "theorem.\n"
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

# From autoformalize_notes.py (REVISE_DEF_PROMPT): SUPERSESSION-ACTING — governed strengthening of a too-weak def.
REVISE_DEF_PROMPT = (
    "A theorem in the campaign theory file `{path}` was KERNEL-CONFIRMED FALSE — a DEFINITION it depends on is "
    "too WEAK (it admits a counterexample). The false theorem:\n  {false_lemma}\nThe kernel-confirmed refutation "
    "/ counterexample:\n  {counterexample}\n\n"
    "Identify the too-weak definition and STRENGTHEN it so the intended theorem becomes TRUE — under STRICT "
    "governance (this is the ONLY sanctioned way to change an existing def; a free edit is auto-rejected). Call "
    "the def D. Do ALL THREE, changing nothing else:\n"
    "  1. PRESERVE the current definition VERBATIM, only renaming it to `D__pre` (identical body).\n"
    "  2. Write the STRENGTHENED `def D` — SAME signature, a STRONGER body (add the missing hypothesis/clause "
    "the counterexample exploits; e.g. a single-crossing condition needs BOTH its weak AND its strict half).\n"
    "  3. PROVE the strengthening: `theorem witness_strengthen_D : <binders>, D <args> -> D__pre <args> := <proof>` "
    "(the new def IMPLIES the old). The kernel verifies this; a weakening or trivialization cannot prove it and is "
    "rejected.\n"
    "Append-only for EVERYTHING else: every other definition and theorem must stay byte-identical, and you must "
    "NOT alter any theorem's statement. The strengthened def must remain FAITHFUL to the intended concept "
    "(re-checked). If no strengthening makes the theorem true, leave the file unchanged and say why.\n")

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
