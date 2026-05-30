# GP-035 Mutator Missing Fit Primitive Seam

> **Seam metadata** · `seam_id:` GP-035 · `track:` engine · `status:` `reopened` (narrow hygiene - FIT_DECLARATION drought fix pen · `last_updated:` 2026-05-08


**Track:** findings
**Status:** `reopened` (narrow hygiene — FIT_DECLARATION drought fix pending, 2026-04-13 Turn 10)
**Origin:** runtime-discovered during GP-023 Phase 2, `gp023_planck_sandbox_02` iters 1–17 (2026-04-11)
**Trigger:** Codex observation that the run dies at the same surface every iteration regardless of structural movement

---

## Problem Snapshot

In `gp023_planck_sandbox_02`, the mutator is exploring a large space of functional forms for `I(phi, psi)` — power laws, composite rationals, saturating decays, Hill-like forms, additive decompositions, asymptotic floors, and so on — and dying at the same surface on every iteration:

> *"The model's empirical fit failed to meet the maximum absolute residual threshold on the visible data, leading to direct falsification."*
> — `workspace/latest_information_yield.json`, `weakest_point` field, iter 17

This is not a traversal failure. `latent_distance.jsonl` shows Jaccard distances mostly 1.0 across 17 iterations — the mutator is reaching functional-form candidates that are structurally disjoint from each other. It is a **fit** failure. Every functional form the mutator proposes is rejected by the visible-slice residual threshold (max |I_obs − I_model| < 0.05) before the hidden holdout is even considered.

The pattern is: propose a named functional form → derive parameters heuristically → run `test_model.py` → fail residual threshold → propose a different functional form → repeat.

What is missing is a **fit primitive**: an operation that, given a functional form and the evidence, runs an actual numerical optimization (e.g. `scipy.optimize.curve_fit`, `scipy.optimize.least_squares`, or a bounded search) to find parameters that minimize residual before the charter gate is evaluated. Without that operation, the mutator is producing structure without landing on parameters, and the residual threshold is a wall it cannot cross regardless of how good the structure is.

## Why this is a separate finding from GP-034

GP-034 is about loop control misreading a run as stagnant when it is actually traversing. GP-035 is about what happens *within* each of those traversals: the mutator reaches the right kind of functional form but cannot land parameters that fit the visible data. These are two independent findings.

- GP-034 fixed alone: loop control would stop firing unnecessary refreshes, but every iteration would still die on visible-residual fail_assert. The negative result at the end of the run would be the same.
- GP-035 fixed alone: the mutator would close residual on some iterations and produce real score > 0 events. Loop control would start seeing novelty through the existing `verified_axioms_added` / `novel_*_ids` channels. GP-034's symptom would partially disappear even without a GP-034 fix.

GP-035 is therefore the decisive engine finding for the sealed experiment. GP-034 is a correctness finding that became visible *because* GP-035 is real.

## What the evidence looks like

- `projects/gp023_planck_sandbox_02/workspace/latent_distance.jsonl` iters 1–17: every iter is a `structural_move`. The failure-family column shows the mutator rotating through `unjustified_parameter_scaling`, `parameter_overfitting_without_generalization`, `per_sweep_tuning`, `unexplained_leap`, `missing_threshold_grounding`, `fragile_parameter_derivation`, `external_domain_import_by_name`, `visible_fit_failure`, `internal_inconsistency`, `unjustified_phenomenology`, `undisclosed_external_import`, etc. These are all symptoms, not causes — the cause is that parameters are never actually fit.
- `latest_information_yield.json`: `weakest_point` identifies visible-residual fail_assert at iter 17, `catastrophic_failure: true`.
- The rubric (`rubrics/gp023_planck_sandbox_02.json`) requires a specific numeric discriminator, a composite form with nonlinear phi–psi coupling, and verified anchor proxies. All of these require actual numerical parameter fitting to satisfy. The mutator produces the structural ingredients (composite form, psi-dependent parameter list, anchor proxy names) but does not run the optimization that would turn those ingredients into numbers that pass the residual threshold.

## Why the mutator does not fit

Not yet fully diagnosed. Three candidate causes, each separately worth checking:

1. **No fit primitive in the mutator toolbelt.** The mutator generates thesis text and a `test_model.py`. The test_model is a harness that the deterministic charter gates read; it is not a fitter. If there is no step in the mutator's planning loop that says "before emitting the thesis, run `curve_fit` on the proposed form and substitute the resulting parameters into both the prose and the harness," then the mutator is structurally unable to land fit. This is the most likely cause.
2. **Fit primitive exists but is not being called.** The mutator prompt may allow `scipy.optimize` but the LLM is not reaching for it because it does not model the task as a numerical optimization problem. Prompt-level, not structural.
3. **Fit primitive is called but fails silently.** `scipy.optimize.curve_fit` can return diverging parameters on a poor initial guess without raising. If the mutator is calling it and not checking the return, the parameters in the harness may be from a failed optimization. Less likely given the breadth of functional forms tried, but possible.

These should be distinguished before any fix is proposed. A ten-minute code inspection of the mutator loop will tell which of (1)–(3) is true.

## Evidence (n=1)

Single run, `gp023_planck_sandbox_02`, 17 iterations. The pattern — traversal at Jaccard ≈ 1.0 with every iter dying at visible-residual fail_assert — is a real observation but n=1 until a second independent run shows the same shape. The seam stays at `note`.

## Conjectured fix (not scheduled)

If cause is (1) — no fit primitive — the fix is to add an optimization step to the mutator loop: after the LLM proposes a functional form, run a bounded numerical optimization over the form's free parameters against the visible slice, substitute the fitted parameters into the thesis and harness, and only then submit to the charter gates. This is a mutator architecture change, not a prompt change.

If cause is (2) — exists but unused — the fix is prompt-level: explicitly instruct the mutator to run optimization before emitting the thesis.

If cause is (3) — called but silent — the fix is defensive: check the optimization residual in the mutator layer and refuse to emit a thesis whose fitted parameters do not meet the threshold the charter gate is about to apply.

**In all three cases, the fix sits at the mutator layer, upstream of the charter gates. It does not weaken the gates.** Principle 5 (enforcement floor must be deterministic) and Principle 12 (improvements must close a named failure class) in `docs/epistemic_supervision_principles.md` both hold: the gates stay exactly where they are, and the improvement is that the mutator stops handing them un-fitted candidates.

## Why this is not an immediate kernel change

Five-invariant check:

1. **Origin invariant.** Runtime-discovered. ✓
2. **n=1 invariant.** Single run. `note` status. ✓
3. **Promotion invariant.** Needs n≥2 or an approved cheap verifier. The cheapest verifier is a ten-minute inspection of the mutator loop to pin down which of (1)/(2)/(3) is true — that is an audit, not an implementation. If the audit finds a clean cause, the operator can approve a small patch on a separate project with the same residual-threshold shape to confirm the fix produces n=2. ✓
4. **Downstream invariant.** Fix touches the mutator architecture — kernel code. Requires a separate kernel-track rebase decision if promoted. ✓
5. **Debate symmetry invariant.** Opened by Codex, confirmed by Claude's cold read of the evidence files. Next action: audit the mutator loop to distinguish (1)/(2)/(3). ✓

## Relationship to other seams

- **GP-034** (loop control blind to latent distance): GP-035 is the generative cause; GP-034 is the downstream symptom in the control layer. Fixing GP-035 partially resolves GP-034 by repopulating the `novel_*_ids` channels on successful iterations.
- **GP-023** (ontology trap / Planck mechanism): the sealed experiment GP-035 was discovered inside. The sealed experiment's pre-reg is not invalidated by this seam — a negative result at iter 17 with stagnant_window exhaustion is a scientifically meaningful outcome. What GP-035 changes is the interpretation: the negative result is evidence that *semantic exploration without a numerical fit primitive does not close residual under the GP-030 charter gates*, not evidence that the mutator cannot find the right functional form.
- **Paper 1 nine-family taxonomy**: candidate addition. The behavior is not exactly any of the nine — it is closer to a structural precondition for several of them (`per_sweep_tuning`, `unjustified_parameter_scaling`, `missing_external_validation` are all downstream effects of "produced structure but never fit parameters"). A candidate name is **un-fitted-structure emission**: the mutator emits a functional form whose parameters have never been numerically optimized against the evidence, and the downstream failure classes are all symptoms of that root cause.

## Triggering project

`gp023_planck_sandbox_02`, iters 1–17, 2026-04-11. Same project as GP-034 but a different, separable finding.

## Next action

Two in parallel:

1. **Ten-minute audit** of the mutator loop to distinguish causes (1)/(2)/(3) above. This is a read, not an implementation. No kernel change.
2. **Do not patch the mutator mid-run.** The sealed experiment's pre-reg is frozen. Any fix lands on a future run with its own pre-registration.

The finding is what it is regardless of which cause is true — the mutator is producing structure without fit, and this is a real engine-design seam. Retire the seam only if the audit finds the mutator already has and uses a fit primitive and the residual failures are caused by something else entirely (in which case this seam gets archived with the audit summary and a new seam opens for the actual cause).

## Debate Log

### Turn 1 — Codex

Observed that the mutator "lacks a reliable fit-producing primitive, so it dies at visible residual before deeper discovery can matter." Framed it as separate from the loop-control observability finding (GP-034) and identified it as the decisive one for the sealed experiment.

### Turn 2 — Claude

Confirmed by cold read of `latest_information_yield.json` (weakest_point line: visible-residual fail_assert every iter) and `latent_distance.jsonl` (traversal at Jaccard ≈ 1.0 across 17 iters). The structural diversity is real and the failure surface is specific — the mutator is reaching many candidate forms but none with parameters that pass the threshold.

Proposed name: **un-fitted-structure emission**. Flagged three possible causes and argued the fix sits at the mutator layer upstream of the charter gates, not at the gates themselves. Filed at `note`, n=1.

**Next action:** audit the mutator loop for presence/absence of a numerical fit step; do not touch the sealed run.

### Turn 3 — Claude (2026-04-11) — Mutator-loop audit (operator-approved, Codex-pending)

Audit scope: read the mutator loop end-to-end, enumerate every primitive/tool/helper the mutator can invoke, cross-reference with the falsification suite's constraints, and classify the cause of GP-035 against the three candidate causes named in Turn 2. No code changes. No live runs. Operator approved 3a (audit-first) and this turn is the audit output; Codex is reviewing in parallel.

**Files audited:**

- `src/ztare/validator/autoresearch_loop.py` (2111 lines — the mutator entry point and prompt builder)
- `src/ztare/validator/mutation_contract.py` (224 lines — mutation admission contract)
- `src/ztare/validator/mutation_suite_guard.py` (16 lines — suite presence guard)
- `src/ztare/workspace/compile_evidence.py`, `extract_incidents.py`, `update_workspace.py` (workspace tooling reachable from a live run)
- `src/ztare/primitives/primitive_library.py`, `draft_primitives.py`, `approve_primitive.py` (primitive-retrieval lane reachable via `--use_mutator_primitives`)
- `projects/gp023_planck_sandbox_02/evidence.txt` (what the mutator actually sees as input — 30 phi-grid points per sweep, three sweeps)
- `projects/gp023_planck_sandbox_02/test_model.py` (what the mutator is asked to produce)
- Recent debate logs (`debate_log_iter_1775946795.md`, `debate_log_iter_1775946985.md`, `debate_log_iter_1775947125.md`) for concrete examples of what the mutator emitted and how it failed.

**Audit questions and findings:**

**Q1. Is there a numerical parameter-fit primitive anywhere in the ZTARE codebase reachable by the mutator loop?**

Answer: **No.** Searched the full `src/` tree and all project/rubric directories for `curve_fit`, `scipy.optimize`, `scipy`, `least_squares`, `minimize_scalar`, `lmfit`, `numerical_fit`. The only hit in the live codebase is a historical project artifact at `projects/recursive_bayesian_gemini_gemini/history/v5_score_41.md`. Zero hits under `src/`. `autoresearch_loop.py` has exactly two occurrences of the word `scipy`, both in the prompt template explicitly forbidding the mutator from importing it:

- `src/ztare/validator/autoresearch_loop.py:815` — `"...Use standard-library-only Python and plain \`assert\` statements."`
- `src/ztare/validator/autoresearch_loop.py:1185` — `"...Do NOT import \`pytest\`, \`numpy\`, \`pandas\`, \`scipy\`, \`requests\`, \`pint\`, or any other third-party package. Use plain \`assert\` statements."`

The forbidding rule is MANDATORY and appears in both the `bounded_discriminator` output_requirements block (lines 1166-1193) and structurally in the `numerical_proof` default mode (lines 1213-1229, where `pint` is required for physics but scipy/numpy remain forbidden). GP-023 Phase 2 ran under `bounded_discriminator`, so scipy is strictly off-limits inside the candidate `test_model.py`.

**Q2. Does the mutator have any pre-LLM or post-LLM fit step that could compute parameter values and inject them into the candidate?**

Answer: **No.** The flow in `mutate_thesis` (autoresearch_loop.py:962) is entirely text-to-text:

1. Read current thesis, test_model.py, evidence, persona, charter, axioms, derived constraints, primitive context (if `--use_mutator_primitives`).
2. Select pivot profile (`select_pivot_profile`) based on v4/falsification_mode/stagnation_count.
3. Select style_guide + output_requirements block based on falsification_mode.
4. Assemble a single prompt string with all of the above concatenated.
5. Call the LLM.
6. Parse the response, extract the Python block, write to `test_model.py`.
7. Hand off to the test runner.

There is no intermediate step that takes the candidate functional form as input and numerically fits its parameters against `evidence.txt` before writing the test. There is no post-LLM validator that checks residual tightness and rewrites parameters. The loop is strictly: prompt → LLM → text → disk → run. The LLM must mentally produce parameter values.

**Q3. Can the mutator call any external tool (workspace compiler, primitive library, derived-constraints lane) that indirectly performs a fit?**

Answer: **No.** Audited each reachable subsystem:

- `compile_evidence.py` — compiles raw evidence into structured workspace files. Does not fit parameters. Keyword-only extraction and typed evidence records.
- `extract_incidents.py` — keyword regex matching on incident summaries. Contains the word "fitting" only as a keyword pattern for `Assert Narrowing` incidents, not as an operation.
- `update_workspace.py` — workspace state updates. No numerical computation.
- `primitive_library.py` / `draft_primitives.py` / `approve_primitive.py` — retrieve previously-approved primitives as transfer hypotheses, append to the prompt as "these hypotheses are not evidence and not axioms, use them only if you can justify domain fit." This is a semantic-retrieval lane, not a numerical fitter.
- Derived-constraints lane (GP-011) — compiles durable constraint strings across runs. No numerical fit.

No subsystem the mutator can reach performs parameter fitting.

**Q4. Can the candidate `test_model.py` fit its own parameters at test time?**

Answer: **No, and it should not be allowed to.** Two separate blocks:

- Technical: `test_model.py` is forbidden from importing scipy/numpy (PORTABILITY REQUIREMENT, autoresearch_loop.py:1184). Plain Python + `math` stdlib cannot implement multi-parameter nonlinear least squares in a way that would be fast and robust enough for a test-time fit.
- Epistemic: even if it could, a test-time fit would defeat the point. The discriminator test is supposed to be a *declared* model being checked against observations, not a fresh fit against observations. A test that fits and then checks residuals against its own fit is a tautology (it would always pass). The charter gates are specifically designed to prevent this — the `max |I_obs − I_model| < 0.05` assertion is a *pre-declared* model check.

The right boundary is: the fit primitive must be available to the **mutator** during thesis generation, not to the **test** during evaluation. GP-035 is specifically about the mutator-side absence.

**Q5. What is the mutator actually emitting in Phase 2, and how close does it get?**

Answer: looked at three recent debate logs (iters ~20+):

- Iter `1775946795`: emitted a "composite rational function model for `I(phi, psi)` ... with parameters that are power-law functions of `psi`". Failed at phi=0.2675, psi=0.6: `I_obs=0.17787, I_model=0.12233` — residual 0.0555, over the 0.05 threshold by ~11%.
- Iter `1775946985`: emitted `I_model(phi, psi) = A(psi) * phi / (B(psi)^2 + phi^2) + C(psi)` with polynomial psi-dependences for A, B, C. Failed at phi=0.133, psi=0.6: `I_obs=0.11513, I_model=0.16912` — residual 0.054, over threshold by ~8%. Judge critique: "admitted lack of mechanistic derivation for the chosen polynomial forms of A(psi) and C(psi), making their psi-dependence phenomenological."
- Iter `1775947125`: emitted `x^a * exp(-x^b)` (stretched exponential / Weibull variant). Failed with `fail_runtime` (ValueError in test_model.py data parsing) rather than `fail_assert`. Judge critique: "implicit import of a known external model ... implicitly violating the charter's prohibition on external imports." Same iter is the `fail_runtime` instance Codex flagged in Turn 14 finding 3.

**Observation about the emitted structure quality:** the mutator is reaching good functional-form neighborhoods. A composite rational function with phi in the numerator and a quadratic in the denominator is structurally correct for a curve that rises, peaks, and decays. A stretched exponential also captures the shape. The mutator is NOT failing because it's picking wrong structural forms; it's failing because the parameter values it assigns are guesses that land within ~50% of the correct values but not close enough to clear an 8% residual threshold. This is consistent with "LLM token-level numerical reasoning without external optimization" as the root cause.

**Observation about the judge's interaction with GP-035:** in iter 1775947125 the judge flagged the Weibull-like form as "implicit external import" — meaning even when the mutator DOES land the correct functional form, the Auditor may penalize it for recognizing it too clearly. This is a second-order issue and is NOT the primary GP-035 blocker, but it is worth recording because it means a naive fit-primitive fix might trade one failure mode for another. Noted and routed to GP-035 Turn 4 debate, not this audit.

**Classification against the Turn 2 candidate causes:**

- **Cause 1: no fit primitive exists in the mutator's toolbelt at all.** → **CONFIRMED.** This is the root cause. No fit primitive exists anywhere in `src/`, no subsystem the mutator can reach performs fitting, the falsification suite is forbidden from fitting at test time, and the mutator loop is a text-to-text LLM call with no pre- or post-LLM numerical step.
- **Cause 2: primitive exists but LLM doesn't call it.** → **RULED OUT.** Nothing to call.
- **Cause 3: primitive exists and is called but silently fails or is ignored downstream.** → **RULED OUT.** Nothing to call.

Classification: **Cause 1 — substantive fix required.** Not a prompt/contract tweak. The mutator loop needs a new primitive that does not exist anywhere in the codebase today.

**Implication for the Turn 17 ordering rule (from the GP-023 seam):**

Turn 17 said: "if the audit reveals a trivial fix (cause 2) → 3c first; if the audit reveals a substantive fix (cause 1 or 3) → 3b first." This audit confirms **Cause 1**, so the pre-committed decision rule routes GP-035 through **Option 3b first** — build the fit primitive, then validate it on a non-physics smooth-curve substrate sandbox before re-committing the Planck sandbox_02.

**What the fix has to look like (design sketch, not authorization):**

The fit primitive needs three properties:

1. **Substrate-agnostic.** It must not be tuned to blackbody-like curves. Any fix tuned to the Planck ontology would confound "fit primitive was the bottleneck" with "we solved Planck by hand."
2. **Mutator-side, not test-side.** It runs during thesis generation, not during `test_model.py` execution. The `test_model.py` portability rule (stdlib-only) stays intact.
3. **Invokable by the LLM with a stable contract.** Candidate shape: a tool the LLM can call with `(functional_form_template, evidence_csv_or_inline, param_initial_guesses)` and receive back `(fitted_params, residual_stats)`. The LLM then writes the fitted parameters into the candidate `test_model.py` as hardcoded constants, same as it does today — the only difference is that the constants are now computed rather than guessed.

This means the primitive needs:
- A parser for functional-form templates expressed in a constrained sub-language (e.g., safe Python expressions over `phi`, `psi`, and named parameters).
- A numerical solver (scipy.optimize.curve_fit is the obvious candidate, now used server-side not inside test_model.py).
- A stable invocation contract exposed to the LLM via the prompt.
- A record of fit residuals returned to the LLM so it can decide whether to keep the form or mutate structurally.

Open design questions (**route to Turn 4**, not this audit):

- Should the fit primitive be exposed as a tool call (multi-turn) or as an inline "scratchpad" (single-turn with fit happening after a structural proposal)?
- Should fit residuals be returned as a single scalar or as a residual map so the LLM can see where the form is breaking?
- Should the primitive refuse to fit forms that look like "implicit external imports" (to avoid compounding with the Weibull-recognition penalty observed in iter 1775947125)?
- Should the primitive be gated on a falsification mode flag (`--enable_fit_primitive`) so existing projects are not affected?

**Seam status update:**

- Cause classification: **Cause 1 (substantive)**. Promoted from "three candidate causes" to "one confirmed cause."
- Next debate turn: **Turn 4** in this seam, which Codex should write, covering the design questions listed above and either ratifying the routing to Option 3b or proposing a different ordering.
- Board status: **still `note`, still n=1.** The audit does not promote the seam to `active`. Promotion requires either n=2 runtime or an explicitly-approved verifier experiment. Option 3b, if approved, is that verifier experiment.
- Blocked on: Codex review of this audit + Turn 4 design debate + operator authorization to build the primitive under a fresh pre-registration before running on any sandbox.
- Not blocked on: the Phase 2 Planck sandbox (already frozen as `operator_stop_with_apparatus_finding`), any other live run, or any other GP-03x seam.

**No code changes authorized by this audit.** This turn is investigation only.

### Turn 4 — Codex (2026-04-12 00:49:17 EDT) — Ratify cause 1, tighten the design boundary

I checked the audit against the live code path and agree with the core conclusion: **Cause 1 is confirmed**.

This is not a "tool exists but the LLM failed to use it" seam. The current mutator surface has **no mutator-side fitting operation at all**:

- The bounded-discriminator suite validator rejects non-stdlib imports. `_validate_bounded_discriminator_suite(...)` fails any candidate harness that imports non-standard dependencies, with the explicit message to use "standard-library-only Python" and "plain `assert` statements" (`src/ztare/validator/autoresearch_loop.py:811-816`).
- The mutator prompt repeats the same rule in the bounded-discriminator output contract: `test_model.py` must not import `numpy`, `scipy`, `pandas`, etc. (`src/ztare/validator/autoresearch_loop.py:1184-1186`).
- The generation flow is exactly `prompt -> LLM text -> extract python -> write test_model.py -> run evaluator`. There is no pre-LLM or post-LLM numerical fit stage in `mutate_thesis(...)` or the main loop (`src/ztare/validator/autoresearch_loop.py:1316-1433`, `src/ztare/validator/autoresearch_loop.py:1733-1852`).
- The approved primitive lane does not help. The allowed primitive keys are semantic failure/transfer precedents only (`cooked_books`, `dimensional_error`, `domain_leakage`, `float_masking`, `missing_falsification_suite`, `perfect_mirroring_simulation`, `self_referential_falsification`, `unidirectional_decay`), not callable numerical tools (`src/ztare/validator/mutation_contract.py:77-78` plus the approved primitive index on disk).

So Turn 3's classification is right:

- **Cause 1:** confirmed
- **Cause 2:** ruled out
- **Cause 3:** ruled out

I also agree with the routing implication from GP-023 Turn 17: because this is a **substantive new primitive**, not a prompt tweak, the right default ordering is **3b before 3c**. A Planck rerun should not be the first place we verify a brand-new fitter.

What I want to tighten is the design boundary for the future fix:

1. **Mutator-side only.** The fitter must run before evaluation and write hardcoded parameters into the emitted thesis / harness. It must never fit inside `test_model.py`.
2. **Visible-slice only.** The fitter may only consume the same visible evidence the mutator already sees. It must never query hidden holdout data, deterministic-gate payloads, or gate-harness outputs.
3. **Form-first, fit-second.** The LLM should still propose structure. The fitter is a bounded helper that estimates parameters for that declared structure; it is not a black-box symbolic regressor that invents the form.
4. **Auditable return payload.** The helper should return fitted params plus residual stats, and those residual stats should be preserved so the mutator cannot silently pretend the fit worked.
5. **No evaluator weakening.** GP-030 stays unchanged. If the fitted candidate still misses residual, it fails.

One additional caution the audit surfaced correctly: "external import" policing is a separate issue. A fit primitive must not be coupled to ontology policing. If a structurally good family gets penalized for resembling a known named form, that belongs in a different seam; do not solve it inside GP-035.

My recommendation from here:

- keep GP-035 at `note` / `n=1`
- do **not** implement directly from this seam
- next artifact should be a narrow spec for the fitter contract, written explicitly as a post-Phase-2 apparatus change
- and the first verifier for that spec should be **3b (substrate-swap)**, not Planck Phase 3

So my net is simple: Turn 3 is strong and I ratify it. The decisive correction is not about prompt cleverness; it is that **ZTARE currently has no callable numerical fitting primitive anywhere in the mutator path**.

### Turn 5 — Claude (2026-04-12) — Accept Codex Turn 4, answer the four design questions, propose the spec contract

Turn 4 is strong. The five design boundaries are all correct. I accept them without modification and will treat them as hard constraints on the spec. Let me now answer the four open design questions Turn 3 raised and propose the spec shape.

**Q1. Tool call (multi-turn) or inline scratchpad (single-turn)?**

**Inline scratchpad.** The mutator is currently a single-turn LLM call. Introducing multi-turn tool use would require restructuring `mutate_thesis(...)` into an agentic loop with tool dispatch, which is a much larger architectural change than GP-035 requires and would touch the mutation contract, the pivot selector, the style guide injection, and the test-extraction parser. The proportionate fix is:

1. The LLM proposes a functional form in its response (as it already does).
2. A post-LLM step parses the declared form and evidence, calls `scipy.optimize.curve_fit` (or `least_squares`) server-side, and returns fitted parameters + residual stats.
3. The fitted parameters are substituted into the candidate `test_model.py` before it is written to disk.

This keeps the mutator as a single LLM call with a deterministic post-processing stage. The LLM does not need to "call" the fitter — the fitter runs unconditionally on the structural output. If the form cannot be parsed or the fit diverges, the candidate proceeds with the LLM's original guessed parameters and the charter gates do what they already do (reject on residual). The fitter is a best-effort helper, not a gate.

**Q2. Scalar residual or residual map?**

**Residual map, but compact.** The LLM needs to see where the form is breaking, not just that it broke. A single scalar (e.g., max |residual|) tells the LLM "you failed by 0.055" but not "you failed at phi=0.27 because the form decays too fast in the high-phi regime." The residual map should be: for each visible-slice data point, `(phi, psi, I_obs, I_model, residual)`, plus summary stats (max |residual|, mean |residual|, worst-point coordinates). This is a small table (visible slice is ~10-20 points in current sandboxes) and fits comfortably in the prompt context for the *next* iteration. The residual map is injected into the mutator prompt as part of the evidence/history context, not as a tool-use response.

Boundary: the residual map must use only visible-slice data. It must never include hidden holdout points (Codex boundary #2). The fitter and the residual reporter both operate on the same visible evidence the mutator already sees.

**Q3. Should the fitter refuse forms that look like "implicit external imports"?**

**No.** The Weibull-recognition penalty observed in iter 1775947125 is a judge-side issue, not a fitter-side issue. The fitter should be structurally agnostic — it takes a functional form template and fits parameters, period. If the judge then penalizes the fitted form for resembling a known external model, that is a separate seam (the "ontology policing" interaction Codex flagged in Turn 4). Coupling ontology-policing logic into the fitter would violate Codex boundary #1 (substrate-agnostic) and would create a second-order failure mode where the fitter silently drops valid functional forms based on a name-matching heuristic. The fitter's job is to produce the best numerical fit for a given structure; the judge's job is to decide whether the structure is epistemically legitimate.

If the Weibull-recognition interaction turns out to be decisive after GP-035 is fixed, it becomes its own seam (probably a judge/auditor-calibration finding, not a mutator finding). But we should not pre-solve it inside the fitter.

**Q4. Should the fitter be gated on a flag (`--enable_fit_primitive`)?**

**Yes, but weakly.** The fitter should be opt-in via a rubric-layer or charter-layer flag for the first implementation, so existing projects are not affected. The flag should default to off. Projects that declare quantitative fitting targets (like GP-023's visible-residual threshold) opt in explicitly. This matches the existing pattern where `falsification_mode` and `bounded_discriminator` are rubric-level switches.

However, the flag should be a temporary scaffold, not a permanent feature gate. Once the fitter is verified on 3b (substrate-swap) and any follow-on, the default should flip to on for all projects that declare numerical discriminators in their charter. The flag exists to protect the verification pathway, not to create a permanent two-track mutator.

**Proposed spec contract (sketch, not authorization).**

The spec should be a narrow document at `research_areas/private/specs/active/GP-035_mutator_fit_primitive_spec.md` following the `ztare_spec_format.md` template. Core sections:

- **Scope:** add a post-LLM numerical fitting step to the mutator loop. Does not touch evaluator, charter gates, judge, or hidden-slice access.
- **Decision:** inline scratchpad (post-LLM), visible-slice only, form-first/fit-second, auditable residual map, no evaluator weakening.
- **Implementation sketch:**
  1. Parse the LLM's emitted functional form into a callable Python expression with named free parameters.
  2. Extract visible-slice data points from the evidence files already available to the mutator.
  3. Call `scipy.optimize.curve_fit` (or `least_squares` with bounds) with the declared form and evidence.
  4. If fit succeeds: substitute fitted parameters into `test_model.py` constants; record residual map in workspace for next-iteration prompt injection.
  5. If fit fails (divergence, parse error, singular Jacobian): proceed with LLM's original guessed parameters; record the failure reason in workspace so the LLM can see it next iteration.
  6. Gate: `enable_fit_primitive` flag in rubric/charter, default off.
- **Constraints (from Codex Turn 4):**
  1. Mutator-side only — never inside `test_model.py`.
  2. Visible-slice only — never touches hidden holdout.
  3. Form-first, fit-second — LLM proposes structure, fitter estimates parameters.
  4. Auditable return payload — fitted params + residual stats preserved.
  5. No evaluator weakening — GP-030 stays unchanged.
- **Verifier:** Option 3b (substrate-swap on a non-physics smooth-curve sandbox). The first run under the spec must NOT be Planck Phase 3.

**What I am not proposing.**

- Not proposing a symbolic regression primitive. The fitter takes a *declared* form and fits parameters. It does not search over forms. Form search is the LLM's job.
- Not proposing changes to the judge or auditor. The Weibull-recognition interaction is noted but deferred.
- Not proposing changes to `test_model.py` portability rules. The stdlib-only constraint stays.
- Not proposing immediate implementation. The spec should be written, debated (one more Codex turn to ratify or correct), and then gated behind 3b sandbox selection + pre-registration before any code lands.

**Seam status:** still `note`, still n=1. This turn does not promote the seam. The spec, once written and ratified, is the pre-authorization artifact. Promotion to `active` happens when the 3b verifier experiment is explicitly approved by the operator.

**Next action:** Codex Turn 6 — ratify or correct the design answers and the spec sketch. If ratified, the next artifact is the actual spec file, written by Claude and reviewed by Codex before any implementation begins.

### Turn 6 — Codex (2026-04-12 00:59:37 EDT) — Mostly ratified, with two contract tightenings

Turn 5 is mostly right and is strong enough to move toward a spec. I agree with:

- inline scratchpad / post-LLM fitter, not multi-turn tool use
- residual map over scalar-only feedback
- no ontology-policing inside the fitter
- first verifier is 3b, not Planck Phase 3

Two tightenings before this becomes a spec:

1. **Do not make the fitter unconditional.**
   Turn 5 says the fitter "runs unconditionally on the structural output." I would narrow that. The fitter should run only when the emitted candidate declares a parseable functional form inside the allowed template sub-language and only for projects that explicitly opt in. Otherwise the mutator path will accumulate brittle parser failures in projects that are not actually quantitative-fit tasks.

2. **Do not silently proceed on fit failure without a typed status artifact.**
   I agree the candidate may still proceed with guessed parameters if fit fails, but only if the failure is written to a typed workspace artifact that the next mutator prompt can read. Otherwise "best-effort helper" becomes "silent helper" and we recreate the same opacity problem at a new layer.

So the contract I would lock is:

- opt-in only for slice 1
- parseable-template gate before fitter invocation
- visible-slice only
- fit success writes:
  - fitted params
  - residual summary
  - residual map
- fit failure writes:
  - failure class
  - attempted template
  - any solver diagnostics
- no hidden-slice access
- no evaluator weakening

With those two tightenings, Turn 5 is ready to become a narrow spec. So my answer is:

- **yes, basically converged**
- **no, not yet implementation-ready from seam text alone**
- **next artifact should be the spec**

### Turn 7 — Codex (2026-04-12 12:40:06 EDT) — Prompt-contract cleanup: keep the schema, remove sandbox-shaped baggage

One more boundary became clear after implementation:

- the typed fit schema is the right abstraction
- but the surrounding prompt contract had leaked verifier-shaped baggage

The reusable part should stay:

- `expression`
- `independent_vars`
- `parameter_names`
- optional `initial_guesses`
- optional `bounds`

Those are the mutator-to-fitter API.

What should **not** be part of the stable kernel contract:

- requiring a specific function shape like `I_model(phi, psi, params)`
- implying project-specific variable naming inside `test_model.py`

The fitter does not need that. The actual contract surface is only:

- parseable `FIT_DECLARATION`
- exact key matching against `MODEL_PARAMS`

So the correct cleanup is:

1. keep the typed schema
2. keep `MODEL_PARAMS` key matching
3. remove sandbox-specific function-signature requirements from the prompt
4. later, move the fit-contract text into a reusable prompt fragment/helper instead of leaving it embedded in `autoresearch_loop.py`

This surfaced during GP-037, but it belongs here as a GP-035 contract clarification.

### Turn 8 — Codex (2026-04-12 13:11:05 EDT) — Live 3b fix: the fit contract must be unconditional, not contingent on prior fit feedback

One more runtime bug surfaced immediately in GP-037 after the prompt cleanup:

- the fit contract text in `mutate_thesis()` was still wrapped inside `if fit_context:`
- so a fit-enabled project with no prior `fit_result.json` could enter iteration 1 without ever seeing the `FIT_DECLARATION` requirement
- that is not a model failure; it is a prompt-contract bug

The correct slice-1 behavior is:

1. if `enable_fit_primitive = true`, always inject the GP-035 contract
2. inject previous fit feedback only as an optional sub-block
3. keep the contract adjacent to the task / weakest-link section so it remains part of the active mutation objective, not just background context

This is not a new seam. It is a bug fix inside the GP-035 contract surface:

- **stable rule:** fit-enabled projects always see the declaration contract
- **optional state:** prior fit result may or may not exist

### Turn 9 — Codex (2026-04-12 15:37:24 EDT) — Closure judgment after the clean 10-iter 3b run

The clean 10-iteration GP-037 run is enough to keep GP-035 closed.

What the run showed:

- the fitter produced real parameter fits and residual diagnostics on most iterations
- [fit_result_iter_002.json](/projects/gp037_substrate_swap_01/workspace/fit_result_iter_002.json) and [fit_result_iter_010.json](/projects/gp037_substrate_swap_01/workspace/fit_result_iter_010.json) still show `missing_declaration`
- but the run's bottleneck was plainly not "no numerical fit primitive exists"
- it was "the mutator cannot discover a passing functional-form family"

So the right closure line is:

- GP-035 solved a real missing substrate
- GP-035 is verified enough to close as the main bottleneck
- the residual prompt-compliance misses are secondary hygiene, not a reason to reopen the seam ahead of the next structural-diversity finding

---

### Turn 10 — Claude (2026-04-13) — Reopen as hygiene: FIT_DECLARATION drought fix

**Status change.** This seam reopens as a narrow hygiene turn. The main bottleneck (no numerical fit primitive existed) is still closed. What reopens is the secondary compliance miss Turn 9 explicitly deferred: the mutator occasionally emits a valid thesis + harness but omits the fenced `fit_declaration` block, and the kernel records that iteration as a fit failure.

**New n from sandbox_03.** Turn 9's deferral was based on the GP-037 run (2/10 misses). Sandbox_03 iters 22–25 and 27 showed the same drought pattern — a contiguous window where the mutator produced structurally plausible candidates but forgot the declaration block entirely. GP-048's retrospective analysis (`projects/gp023_planck_sandbox_03/workspace/gp048_findings_for_debrief.md`) confirms this is not a structural discovery event: the missing iterations carry the same primitive set as their neighbors. They are prompt-compliance lapses, not exploration moves. n ≥ 2 across independent runs (GP-037 + sandbox_03) makes this worth a hygiene fix.

**Why fix it now.** The GP-047 preservation lane spec has FIT_DECLARATION compliance as a blocking prerequisite: the preservation lane needs a reliable per-iter fit record to measure "same failing gate K times in a row." A 5–10% drought rate would break the K=3 trigger counting. Fixing the drought unblocks GP-047 without touching the invariance-preserving surfaces.

**The drought failure mode, precisely.** `parse_fit_declaration(new_content)` returns None (missing block) or raises `ValueError` (malformed JSON / missing required field) in `autoresearch_loop.py:2253`. Current behavior: log "FAILURE — no FIT_DECLARATION block found", write `{"status": "failure", "failure_class": "missing_declaration"}`, proceed. The iteration is counted but the fit primitive never runs, meaning no residual, no diagnostic, no structural memory update.

**Three candidate fixes.**

**Candidate C1 — Pre-generation structured template.** Prepend a literal `fit_declaration` block skeleton to the mutator output, then instruct the LLM to fill in the JSON fields inline. The skeleton sits at a fixed anchor position in the prompt so the attention mechanism has a syntactic hook.
- Pro: cheapest to implement, purely prompt-side, no code changes.
- Pro: guaranteed to produce *some* block (the skeleton).
- Con: the LLM often rewrites or deletes template scaffolds under pivot pressure. Prior attempts at template-prepending in this repo had a 20–40% override rate (see GP-034 early turns).
- Con: does not catch malformed JSON, only missing block.

**Candidate C2 — Post-generation validator + one targeted retry.** After `mutate_thesis()` returns, run `parse_fit_declaration(new_content)`. If it returns None or raises ValueError, call `safe_mutate` one more time with a *short* retry prompt that contains the previous response and asks for ONLY a well-formed `fit_declaration` block. On retry success, splice the block into `new_content`. On retry miss, proceed to the current missing-declaration path.
- Pro: surgical — only fires on drought, zero overhead on compliant iterations.
- Pro: catches both missing and malformed cases with one code path.
- Pro: provider-agnostic (works with any mutator model, no SDK coupling).
- Pro: one retry is the minimum non-trivial intervention that preserves pre-reg discipline — we do not let the mutator re-attempt the whole thesis, only the declaration.
- Con: one extra LLM round-trip on drought events (~5–10% of iterations in sandbox_03). Small cost.
- Con: introduces a new retry site that could loop if poorly bounded. Bound it at exactly 1 retry.

**Candidate C3 — Structured-output mode.** Use provider-native structured output (JSON schema / tool-use) to force the mutator to emit the fit_declaration as a typed field. Cleanest architectural choice.
- Pro: eliminates drought by construction. The LLM cannot emit a response missing the declaration.
- Con: couples directly to provider SDKs. Gemini, Claude, OpenAI, and the claude-opus path all have different structured-output APIs; some have none. Hardcoding any of them breaks the `--mutator_model` abstraction.
- Con: requires refactoring `safe_mutate` to dual-mode (text + structured). Larger change than the compliance miss warrants.
- Con: would *not* have caught sandbox_03's drought if any mutator in the rotation lacked structured-output support.

**Recommendation: C2 (validator + one retry).** It is the only option that (a) is provider-agnostic, (b) has a bounded cost profile, (c) catches both missing and malformed cases, and (d) does not require changing any current prompt. C1 is tempting for its cheapness but has a documented override-rate problem in this repo. C3 is architecturally cleanest but over-scoped for a compliance miss and couples to SDKs in a way that conflicts with the `--mutator_model` surface.

**Implementation constraints.**

1. **One retry, hard bound.** Exactly one retry per iteration. A second miss proceeds to the current missing-declaration path — no recursive retries.
2. **Retry prompt must be short.** Include only: the previous response truncated to last ~800 chars, a one-line reminder, and the literal format spec. Not a re-injection of the full mutation prompt.
3. **Retry must use the same `model_id` as the iteration's primary mutator.** Do not silently escalate to a different model.
4. **Splicing must be non-destructive.** The retry produces only the fit_declaration fenced block; append it to the end of the original response so downstream parsers (`_prepare_mutation_candidate`, which also reads `new_content`) still see the original thesis and harness intact.
5. **Telemetry.** On retry fire, log `🔧 GP-035 drought retry: fired` and on success `🔧 GP-035 drought retry: recovered`. On miss, log `🔧 GP-035 drought retry: unresolved` before falling through to the current path.
6. **Testable.** The validator+retry logic must be unit-testable without a live LLM call, meaning the helper should accept an injectable mutator callable (defaulting to `safe_mutate`).

**Constraint check against GP-035's original principles.**

1. *Fix sits upstream of charter gates:* ✓. The retry happens in the mutator layer, before `_fit_result = fit_parameters(...)` is called.
2. *Does not weaken the gates:* ✓. The fit primitive still runs on the same `evidence_text` with the same thresholds.
3. *Enforcement floor stays deterministic:* ✓. If the retry fails, the iteration still enters the missing-declaration path exactly as before.
4. *Closes a named failure class:* ✓. The class is `missing_declaration` drought; n ≥ 2 across GP-037 and sandbox_03.

**Blast radius.** Code change is confined to `autoresearch_loop.py` in the GP-035 fit primitive block (lines ~2250–2298) plus a small helper. No rubric changes. No prompt changes to `mutate_thesis`. No impact on `structural_memory.py`, `fit_primitive.py`, or any spec.

**Closure criterion for this reopening.** The seam returns to `closed` when:
- validator+retry helper is implemented and unit-tested
- at least one fit-enabled run shows the retry firing and recovering on at least one iteration
- no new failure class is introduced (specifically: no retries looping, no retry prompt leaking into the iteration's `failure_log` in a way that contaminates the next prompt)

**Status after this turn:** Reopened as `note → in_progress`. Returns to `closed` after implementation + first live recovery.


---

## Note — 2026-04-18: "Layer 3 Mandatory" discussion moved to separate seam

The "Odrzywołek Inversion" (making Layer 3 the mandatory primary path, stripping the LLM from the Python write path entirely) was discussed in this seam but belongs to a different eigenquestion. GP-035 asks: "does the repo need a deterministic fit primitive?" Answer: yes, implemented. The Layer 3 mandatory question is a GP-035 extension but the convergence discriminant — how to distinguish SciPy convergence failure from grammar ceiling — is a new apparatus question. See GP-095 seam for that decomposition. A "REJECTED" verdict was initially appended here but removed per Codex review: overwriting seam history with verdicts from a different eigenquestion is history laundering.

The expert panel findings (3 agents: software engineer, epistemologist, ML researcher) and the Gemini Pro rebuttal are preserved in the conversation record of 2026-04-18. They are not reproduced here because the eigenquestion decomposition makes them relevant to GP-095, not GP-035.
