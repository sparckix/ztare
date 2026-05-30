# GP-069 — Nesting-Cleared Live-Mutator Target Construction (seam)

> **Seam metadata** · `seam_id:` GP-069 · `track:` engine · `status:` DRAFT 2026-04-15. Seam-stage. Tier-3 ladder rung for GP-061  · `last_updated:` 2026-05-08


**Status:** DRAFT 2026-04-15. Seam-stage. Tier-3 ladder rung for GP-061 Component B.
**Purpose:** Define the construction criteria for a live-mutator-compatible fit-primitive target that (a) clears the GP-069 level-1 nesting-audit gate and (b) exercises a grammar axis distinct from the Planck `math.exp / X0 / X1` family. The repo currently has no such target — all existing fit-primitive projects are Planck-grammar, and sandbox_10 was sidestepped to R3b precisely because it does not clear level 1.

---

## Why construction is required

Audit of existing projects 2026-04-15:

- `gp023_sandbox_*` — Planck grammar (math.exp, eml).
- `gp042/043/044/045` — Planck grammar variants.
- `gp037_substrate_swap_01` — fit-primitive but no structural_memory harvest.
- `gp023_sandbox_10` — Kepler vis-viva, cross-grammar, **fails GP-069 level 1** (nesting-closure pathology documented in `GP-023_sandbox_10_nesting_collapse_audit.md`).

There is no existing live-mutator target where (a) the sealed GT is identifiable under single-start fitting without nesting collapse, AND (b) the grammar axis is distinct from Planck, AND (c) the autoresearch loop has produced a non-empty failed-family harvest.

Live-mutator cross-grammar evidence for Component B therefore cannot be sourced from the existing repo. It must be constructed.

## Construction criteria

A candidate target must satisfy all of:

1. **Grammar distinctness.** The declared grammar axis must use a function set disjoint from `{exp, eml, log}`. Examples: `{sin, cos, tan}` (trig), `{sinh, cosh, tanh}` (hyperbolic), `{erf, erfc}` (probability), `{gamma, beta}` (special). The feature-bag vocabulary (`fn:sin|arg0|has_op:*` etc.) should be populated by real families, not vacuous.

2. **Nesting-closure clearance (GP-069 level 1).** At seal time, the operator enumerates wrapper classes reachable in ≤ 1 mutator mutation from the sealed GT under the declared grammar. No enumerated wrapper may collapse to GT at null extra-parameter values. This is the seal-time static check from `GP-069_champion_nesting_audit_gate_seam.md`.

   The practical form: the sealed GT must not sit inside a polynomial-in-primitives closure. A GT like `sin(ωt + φ)` sits in an additive-in-phase closure and is at risk (`sin(ωt + φ + ε·g(t))` collapses at ε=0). A GT like `sin(ωt)·exp(−γt)` is safer — the mutator cannot add a wrapper that collapses to the product form at a null parameter without removing a factor. Each candidate must be audited individually.

3. **Identifiability under single-start fitting.** The parameters of the sealed GT must be uniquely recoverable from the evidence grid under a single fit invocation (not multistart) without rank deficiency. The sandbox_06 (α,β) degeneracy lesson applies — reparameterize or reject if the parameter space has a collapsed subspace.

4. **Live-mutator harvest must be non-empty.** The mutator, starting blind, must produce ≥ 3 `structural_misfit` families at the failure threshold before the autoresearch loop terminates. If the mutator fit-collapses at iter 1 like sandbox_10, the target fails criterion 2.

5. **Evidence surface must be non-trivial and non-cherry-picked.** ≥ 3 independent variables or ≥ 1 observable measured at ≥ 20 grid points with independent noise. No toy two-point grids.

## Candidate grammar axes worth enumerating

Not pre-committed — each needs its own level-1 audit.

- **Damped oscillator** — GT `A·exp(−γt)·cos(ωt + φ)`. Grammar: `{sin, cos, exp, Mult, Add, Sub}`. Needs audit of whether `cos(ωt + φ + ε·t²)` collapses at ε=0 (it does, to the GT form), so this is at risk under phase-extension wrappers. Possible mitigation: restrict grammar to forbid argument sums inside trig calls, at cost of losing `φ` expressibility — same problem as vis-viva.

- **Saturation kinetics (Michaelis–Menten)** — GT `V_max·S/(K_m + S)`. Grammar: `{Div, Add, Mult}`. Sits inside a rational-function closure. Risk: `V_max·S/(K_m + S + ε·S²)` collapses at ε=0. Same pathology class.

- **Stretched exponential** — GT `exp(−(t/τ)^β)`. Grammar: `{exp, Pow, Div, USub}`. Risk: `exp(−(t/τ)^β + ε·(t/τ)^(β+δ))` collapses at ε=0. Pathology-class.

- **Power-law with threshold** — GT `A·(x − x_0)^n · θ(x − x_0)`. The Heaviside factor is not smoothly differentiable — fit primitive may not handle it. Grammar `{Pow, Sub, Mult}` with a step function. Nesting wrappers that multiply by `(1 + ε·(x − x_0))` collapse at ε=0 — still pathological.

- **Hyperbolic** — GT `tanh(x/L)`. Grammar `{tanh, Div}`. Wrapper `tanh(x/L + ε·x²/L²)` collapses at ε=0. Same pathology.

- **Hinge / piecewise-linear (the kink axis)** — GT `y = a·max(0, x − x₀) + b`. Grammar `{max, Add, Sub, Mult}` where `max(0, ·)` is a new primitive not present in Planck. The GT has a non-differentiable kink at `x = x₀` and is piecewise-linear in two regimes. **Algebraic nesting-collapse does not apply the same way:** a smooth additive wrapper `a·max(0, x − x₀) + b + ε·g(x)` does not collapse to GT at ε=0 unless `g ≡ 0`, which is the trivial case common to all nesting audits. More interestingly, there is no smooth reparameterization of `max(0, ·)` that reproduces it exactly — the kink is a boundary of the function space, not an interior point.

   **Honest caveat.** The pathology re-enters asymptotically rather than algebraically. A sigmoid wrapper `sigmoid((x−x₀)/τ)·(x−x₀)` approximates hinge in the limit `τ → 0⁺`. Under L2 residual on a discrete evidence grid, a fit primitive can drive `τ` toward grid spacing and score indistinguishably from GT. This is a *limit* collapse, not a *null-parameter* collapse — it needs a different audit question: "does the mutator's grammar admit a continuous family whose closure contains GT?" If yes, GP-069 level 1 as currently written does not catch it, and a level-1.5 check on family closures is required.

   **Practical status for GP-061 tier-3.** Hinge is the most promising candidate so far because (a) it is genuinely non-Planck in primitive vocabulary, (b) it does not sit inside a polynomial-in-primitives closure, and (c) Component B has a clean feature-bag story: voids on the non-smooth primitive are well-defined when the mutator proposes pure-polynomial or pure-`exp` families.

   **Grammar-admissibility check (2026-04-15).** `src/ztare/validator/fit_primitive.py:76` — `_ALLOWED_MATH_ATTRS` includes `fabs` but excludes `max`, `fmax`, `heaviside`. Direct `max(0, ·)` is therefore not admissible under the current whitelist. **But hinge is expressible via the identity `max(0, x−x₀) = (fabs(x−x₀) + (x−x₀)) / 2`**, which uses only whitelisted primitives. A sealed GT of the form

   ```
   y = a · (fabs(x − x₀) + (x − x₀)) / 2 + b
   ```

   fits in the existing fit primitive with no grammar extension. This is the cheapest path to a hinge sandbox: no `fit_primitive.py` edit, no new eval-namespace entry, just a new project directory with charter + evidence + GT and the regular autoresearch loop.

   **Nesting-closure audit under this expression (preliminary).** The wrapper set reachable in ≤1 mutation includes smooth-wrapper-over-`fabs` forms like `fabs(x−x₀)·(1+ε·f(x))` and `fabs(x−x₀+ε·g(x))`. The first does not collapse to GT at ε=0 except trivially. The second at ε=0 is GT. The critical question is whether a smooth `g(x)` exists such that `fabs(x−x₀+ε·g(x)) + (x−x₀+ε·g(x))` equals `fabs(x−x₀) + (x−x₀)` identically for small ε over the evidence grid. Answer: no, because `fabs` is not translation-invariant in the argument — shifting the kink by `ε·g(x)` moves which samples sit in the `x>x₀` regime. So null-parameter wrappers around `fabs` genuinely do change the residual on a finite grid. **This is the first candidate axis in the enumerated list that resists algebraic nesting-collapse at ε=0 under a natural grammar the validator already admits.**

   **Remaining risks to audit before sealing.**
   1. Sigmoid-limit approximation: the mutator could propose `sigmoid((x−x₀)/τ)·(x−x₀)` using `exp` (whitelisted) and reach hinge as `τ → 0⁺`. Level-1.5 check needed: does the fit primitive drive `τ` below grid spacing under L2 residual, and does its score become indistinguishable from the hinge GT?
   2. Identifiability of `x₀` (the kink location) under multistart fitting — parameter is not smooth-differentiable near the true value, so gradient-based fits may get stuck. Check whether the sandbox_06 rank-deficiency lesson applies in a different form here.
   3. Evidence grid must straddle `x₀` with ≥ 5 samples on each side; otherwise hinge degenerates to pure linear on the dominant side and identifiability of `a, x₀` collapses.

### Level-1.5 sigmoid-limit probe (run 2026-04-15)

**Script:** `src/ztare/validator/gp069_hinge_sigmoid_limit_probe.py` (standalone, no LLM calls).

**Method.** Sealed hinge GT `y = 2·max(0, x−0.37) + 0.5` on 30 uniform samples in `[−1, 1]` (grid spacing ≈ 0.069, noise σ = 0.02). Fit two models via scipy `least_squares` with multistart: (H) the hinge form; (S) sigmoid approximation `a·σ((x−x₀)/τ)·(x−x₀) + b`. Varied a floor on `τ` to simulate practical lower bounds.

**Result.**

| τ floor | Sigmoid L2 | Hinge L2 | Delta |
|---|---|---|---|
| 1e-6 (idealized) | 0.10424 | 0.10440 | **−0.00017** (sigmoid better) |
| grid/10 = 0.0069 | 0.10424 | 0.10440 | −0.00017 |
| grid/2 = 0.0345 | 0.10432 | 0.10440 | −0.00008 |
| grid = 0.0690 | 0.11331 | 0.10440 | +0.00891 |

Noise-free repeat: hinge hits 0 residual; sigmoid hits 0 residual at `τ=1e-6`; sigmoid at `τ=grid/10` hits 0.003; sigmoid at `τ=grid` hits 0.052.

**Reading.** The sigmoid-limit collapse is real and decisive, not a theoretical concern. Under finite-grid L2 scoring, as long as `τ` is permitted below grid spacing, the sigmoid approximation reaches hinge's residual — at measurable noise it *beats* hinge slightly (regularization effect on the noisy samples near the kink). Only when `τ` is hard-clamped at `≥ grid_spacing` does a gap open, and at σ=0.02 noise even that gap (0.009) is below the noise floor.

**Verdict for the hinge sandbox (2026-04-15, initial).** GP-069 level-1.5 appears to fail under the naive pre-registration.

**Verdict for the hinge sandbox (2026-04-15, revised after BIC re-audit + skeptical review).** The raw-L2 collapse is an artifact of **missing complexity penalty**, not a structural property of the scorer. BIC/AIC applied to the same fit results prefer hinge over sigmoid by Δ BIC = −3.30 and Δ AIC = −1.90 (the sigmoid's extra `τ` parameter is penalized enough to erase the 0.00017 raw-L2 advantage). A sigmoid approximation cannot claim parity with hinge once the scorer charges for parameter count — which every serious symbolic-regression system since ~2009 already does (PySR parsimony, AI Feynman complexity pruning, Schmidt-Lipson Eureqa Pareto, MDL/BIC literature). **The hinge target may be viable after all, provided ZTARE's fit primitive adds a complexity penalty before being used as the GP-069-clearing target scorer.**

**Implications for INS-011 and the tier-3 ladder (revised 2026-04-15 post-skeptic review).**
- The initial reading — "finite-sample L2 cannot separate a GT from any smooth family whose closure contains it" — is retracted as overreach. It is Weierstrass/SRM/MDL territory dressed up with LLM-mutator framing, and the field has a standard defense (complexity penalty) that the BIC re-audit confirms works on the probe.
- **Actual decisive observation.** ZTARE's fit primitive at `src/ztare/validator/fit_primitive.py` does not currently apply a complexity penalty when scoring fit candidates. Under unregularized L2 it is exploitable by any smooth wrapper that drives an extra parameter to a null or asymptotic value. This is an apparatus bug, not a frontier finding.
- **Engineering action (precedes any new sandbox).** Add a complexity penalty term (BIC, AIC, or a parameter-count Pareto) to the fit primitive's candidate selection. Re-run the hinge-vs-sigmoid probe under the penalized scorer. Verify that hinge is preferred. Also re-run sandbox_09 v2 / sandbox_10 retrospectively under the penalized scorer — if the historical fit-collapses survive the penalty (they may, because both cases involved structural over-parameterization that BIC also penalizes), the story is stronger; if they disappear, the whole nesting-collapse narrative needs revision.
- **Only after the apparatus fix** should a hinge sandbox pre-registration be considered. Under a complexity-penalized scorer, hinge may be a genuine tier-3 candidate — but that claim is separate and has not been tested.

**Apparatus fix status — SHIPPED 2026-04-15 (task #65).** The minimal wiring landed in `src/ztare/validator/structural_memory.py`: every `FitSuccess.bic` is now carried through to the per-family memory record as `best_bic` / `latest_bic`, and `render_structural_memory_prompt_section` ranks cross-family by BIC ascending when `rubric_data["complexity_penalty_enabled"]` is set. Default is off so running sandboxes are unaffected without explicit opt-in. The live wiring is verified end-to-end by `structural_memory_fixture_regression.py::gp069_bic_flag_flips_hinge_vs_sigmoid_ordering`, which constructs a hinge-like (k=3) and sigmoid-like (k=4) pair at near-identical L2 and asserts that flag-off ranks sigmoid first while flag-on flips to hinge-first. `gp069_hinge_sigmoid_limit_probe.py` continues to report ΔBIC = −3.30 / ΔAIC = −1.90 in favor of hinge under the same n=30, σ=0.02 conditions. The scorer-side prerequisite for any hinge pre-registration is therefore closed. Not done and explicitly deferred: (a) multi-candidate re-ranking inside `fit_parameters` itself — not needed because `fit_parameters` is a single-candidate fitter and cross-candidate comparison lives in structural memory; (b) retroactive audit of sandbox_09 v2 / sandbox_10 via stored memory — non-informative because both runs' winning families converged to residual ≈ 0 and the SSE term dominates BIC regardless. A true retroactive under the penalized scorer would need to walk each iteration's `fit_result_iter_NNN.json` and re-rank across all proposed candidates per iteration, which is a bigger track and not blocking a hinge pre-registration.

## Tier-3 frontier note (added 2026-04-15 after two-pass bounded skeptic review)

This section supersedes the earlier "Preliminary observation" and "Pre-decision" paragraphs that concluded tier-3 may be capped at tier 2 under continuous-physics grammar. Those paragraphs were correct about the pathology but missed the inversion: continuous L2 is the cage the AI escapes through, not the cage that holds it. Moving to discrete graders closes the escape.

### What changed

A prior entry in this seam (2026-04-15, pre-BIC) read the sigmoid-limit probe as evidence that "finite-sample L2 cannot separate a GT from any smooth family whose closure contains it," and concluded that tier-3 under continuous physics may be unreachable. The BIC re-audit retracted the overreach: once a complexity penalty is applied, hinge beats sigmoid cleanly and the probe's "collapse" is revealed as an apparatus bug, not a structural limit.

That retraction was correct but incomplete. **BIC is a partial patch, not a root-cause fix.** This section records the completion.

### Why BIC is partial

BIC (`n·ln(SSE/n) + k·ln(n)`) separates two smooth candidates only when they differ in parameter count `k`. The hinge-vs-sigmoid case works because sigmoid carries an extra `τ` parameter — BIC charges for it, hinge wins by Δ BIC = −3.30.

**A note on the edge case this section is pointing at.** If two candidates have identical `k` and `n`, then BIC ordering reduces to SSE ordering — the complexity term `k·ln(n)` cancels, and "ties on BIC and wins on raw L2" becomes self-contradictory. The residual attack surface is therefore *not* "a same-parameter-count smooth alternative." It is more specific: **a smooth family whose internal structure includes a non-fitted grid-scale constant** (an implementation choice like a floor on `τ`, a bandwidth, a grid-spacing parameter, or a numerical regularizer) that the pre-registration does not count as a "parameter" but which in practice acts as one. The sigmoid-limit probe (§level-1.5 above) makes this concrete: when `τ` is a free parameter, BIC charges for it and hinge wins; when `τ` is instead fixed as a "small number" below grid spacing and not counted in `k`, BIC does not charge and the sigmoid wins on raw L2.

The residual attack surface after the BIC patch is therefore **smuggled-parameter families**: families whose GT-approximating behavior depends on a tunable constant the pre-reg's `k` accounting does not acknowledge. BIC closes the honestly-counted exploit path through continuous L2; it does not close the surface to adversarial parameter-count accounting. Discrete graders close both at once because there is no continuous direction along which a smuggled parameter can steer the prediction.

**Honest statement of what BIC does:** it closes the cheapest exploit path through continuous L2 — the class where the alternative pays an honest extra-parameter tax. It does not close the smuggled-parameter class described above, which requires either pre-registration discipline on parameter accounting or a discrete grader that removes the continuous direction entirely.

### The inversion

If the AI's escape vector is calculus — ε-wrappers, grid-scale τ, smooth closures — then the cage needs a domain where calculus does not apply. Not "where calculus is hard," but where there is no such thing as smoothly approaching the answer. Discrete-residual graders are this cage: each evidence sample is a pass/fail (or Hamming-distance) commitment, not a continuous residual. An ε-wrapper that shifts a prediction by 0.0001 does not reduce the loss because the prediction was either in the correct discrete class or it wasn't.

This is not a new insight in the literature — discrete graders are standard in program synthesis, SAT, and symbolic regression over Boolean domains. It is new *for ZTARE*, which has been continuous-L2-only since inception.

### Cheapest discrete entry: modular arithmetic

Three candidate discrete domains rank-ordered by engineering cost:

| Domain | New execution layer? | Grammar extension | Epistemic cost |
|---|---|---|---|
| **Modular arithmetic** | No — runs in existing Python eval namespace | One line: add `Mod` to `_GENERALIZED_OPS` (fit primitive already admits `ast.Mod`) | Build discrete taxonomy from scratch |
| Program synthesis (sort/regex) | Yes — new executor + test harness | New control-flow primitives (`If`, `While`) | Same + executor validation |
| Quantum circuits | Yes — qiskit + gate-sequence equivalence | New primitive class (unitary gates) | Same + circuit audit tooling |

Modular arithmetic is the only entry that needs no new executor. A sealed GT of the form `y = (a·x + b) mod p` with evidence as `(x_i, y_i)` pairs, and a discrete residual scorer returning `1.0 − (#exact_matches / n)`, runs through the existing fit primitive with the following changes — *corrected against the actual code 2026-04-15:*

1. **AST admission — already done.** `ast.Mod` is already in `_ALLOWED_NODE_TYPES` at `src/ztare/validator/fit_primitive.py:138`. The mutator can emit `x % p` today and it will parse. No fit_primitive edit is required on this axis. (An earlier draft of this section claimed `_ALLOWED_MATH_ATTRS` needed a new entry — that was wrong. `_ALLOWED_MATH_ATTRS` governs `math.*` attribute reads, not AST operators.)

2. **Structural extractor one-line add.** `_GENERALIZED_OPS` at `src/ztare/validator/structural_constraint_extractor.py:224` is the hardcoded op dict that the feature walker iterates over with `isinstance(n.op, op_cls)`. Adding `"Mod": ast.Mod` to that dict is literally one line and is picked up by the existing walker for free. Verified by reading the walker. **Cross-reference:** the companion vocabulary-ceiling entry in the insights ledger documents *two* independent gates on Component B's effective vocabulary — this static-whitelist axis (axis 1) and the corpus-derived universe axis (axis 2 in that entry). Both must be satisfied for the modular pilot to emit a `Mod` void. Changes (1)–(3) here cover axis 1 and the scoring mode; the corpus-seeding gate in (4) below is the axis-2 side of the same coin and cannot be elided.

3. **Discrete scoring mode — new bounded branch.** The fit primitive currently computes L2-over-float residuals. A new `score_mode="discrete_exact"` branch is needed that returns `1.0 − (#exact_matches / n)` (or a Hamming variant). This is not a one-liner — it requires a new code path through the objective function — but it is bounded and local to `fit_primitive.py`. Estimate: half a day of code plus unit tests.

4. **Corpus-seeding gate — design decision, not code.** Component B's `_candidate_universe` at `src/ztare/validator/negative_space_extractor.py:64` builds its void universe from `(fname, arg_pos)` keys actually observed in the failed-family corpus. Even with changes 1–3 in place, Component B will not emit a `Mod` void until at least one failed family has emitted `Mod(...)` first — the universe is corpus-derived, not static. This is a design question the pilot pre-reg has to answer explicitly: does the modular pilot (a) rely on the mutator emitting `Mod` organically before Component B can steer toward it, (b) pre-seed a synthetic failed family at run start to prime the universe, or (c) lift the corpus-seeding rule for pre-registered grammar extensions? None of these are hard, but all three are choices and the pilot cannot skip them.

Selection logic, BIC/AIC telemetry fields, and the Component B op-detection path are otherwise unchanged. The L2-specific BIC formula `n·ln(SSE/n) + k·ln(n)` is undefined when SSE is an integer miscount, so the discrete branch needs its own complexity-penalty formulation — noted here as a known sub-task, not a blocker.

### Nesting-closure audit template under modular-arithmetic grammar

**This sub-section is a template, not an audit.** A real level-1 audit enumerates wrapper classes reachable in ≤ 1 mutation from the sealed GT under the declared grammar and checks each one individually. This template sketches what the audit looks like; it does not substitute for the enumeration.

Under continuous physics grammar, every natural GT sits inside a polynomial-in-primitives closure and level-1 audit fails generically. Under modular-arithmetic grammar, the audit question inverts:

- A single example wrapper: `((a·x + b) + ε·g(x)) mod p` at ε=0 is GT, trivially. The non-trivial check is: for any non-constant `g(x)` and any ε, does the wrapper equal GT on every evidence sample? On a finite integer-valued grid, the answer is no unless `ε·g(x_i) ≡ 0 (mod p)` for all `i`, which forces `ε·g` into the ideal and collapses the wrapper to GT structurally, not via a null-parameter limit.
- There is no "grid-scale" internal constant in a discrete-residual scorer — the scorer is flat-zero-or-flat-one per sample, with no continuous direction to slide along.

**What a real audit would have to enumerate and check (non-exhaustive, for the pre-reg to complete):**

1. Additive wrappers inside and outside the `mod`: `(a·x + b + ε·g(x)) mod p` and `((a·x + b) mod p) + ε·h(x)`.
2. Multiplicative wrappers inside the `mod`: `((a + ε)·x + b) mod p` and `(a·x + b + ε·x²) mod p`.
3. Modulus perturbation: `(a·x + b) mod (p + ε)` — note `p` is a structural constant, so "perturbation" here means "does the mutator propose a non-integer effective modulus or a different integer modulus under the same structure?"
4. Compositional wrappers: `((a·x + b) mod p + c·x) mod p`, and more generally nested mods.
5. Sigmoid-limit style attacks: can a continuous family whose limit contains `mod` be emitted under the extended grammar? The natural candidate is `p · sawtooth((a·x + b) / p)` using a smoothed sawtooth. Whether such emissions are admissible under the declared pilot grammar is a pre-reg decision.

Each of these needs its own algebraic collapse analysis. The generic obstruction from continuous physics (smooth wrapper collapses at ε=0) does not apply, but that is a claim about a *class* of obstructions, not a promise that no obstruction exists for any specific candidate. The pilot pre-reg must produce the enumeration, not inherit it from this template.

### What this does NOT claim

- Not a claim that tier-3 is now easy. The epistemic cost of building a discrete-domain failure taxonomy from scratch is real — it is the same 2–4 weeks of manual audit work that went into the continuous-math taxonomy, and it has to be redone because the failure modes are different.
- Not a claim that Component B will work without modification. See the vocabulary-ceiling entry in the insights ledger. Component B's feature extractor needs to admit the new primitives before it can name voids in them.
- Not a claim that modular arithmetic is the only or best discrete domain — only that it is the cheapest entry for scoping purposes. Program synthesis and quantum may be strictly stronger demonstrations but pay an executor tax this seam is not ready to commit.
- Not a claim that BIC was a wasted ship. BIC closes the cheapest exploit and is decisive for continuous-domain work regardless of tier-3. The apparatus fix was correct; the overreach was in framing it as a solution to the nesting-collapse class.
- Not a claim that tier-2 (phase-2 steering measurement) needs to wait. Tier-2 is an independent measurement on continuous grammar; it ships on its own terms. Tier-3 is a dated follow-up rung, not a blocker.
- **Not a claim that this section proposes any change to phase-2 methodology, model pinning, grammar, iteration budget, or success criteria.** Phase-2 was sealed 2026-04-15 under §9 of the GP-061 steering A/B pre-registration. This tier-3 note is fully downstream of phase-2 and does not modify its scope in any direction. Any pressure to fold tier-3 decisions into phase-2's in-flight run should be rejected as scope creep. (Explicit guard against the overreach pattern that produced the withdrawn §9a flash amendment.)
- **Not a claim that the proposed sequencing is phase-2-independent.** The three-stage sequence (ship phase-2 → draft tier-3 scope → build tier-3) assumes phase-2 produces an interpretable tier-2 result, positive or null. If phase-2 produces an uninterpretable result, tier-3 scope may need revision — for instance, if the tier-2 measurement itself is contaminated, tier-3 cannot be framed as "the next rung" and the whole ladder story needs re-examination. The sequencing is recommended, not structurally decisive; it fails gracefully if phase-2 fails, it does not pre-commit to a forced march.

## Pre-decision (updated 2026-04-15)

Do not seal a modular-arithmetic target yet. Before writing a pre-reg:

1. Ship phase-2 (tier-2 measurement).
2. Draft the modular-arithmetic pilot as a sandbox-stage pre-reg with: sealed GT, discrete scorer signature, grammar extension, level-1 audit under the new template above.
3. Only then build the discrete scorer and run the pilot.

The build order stays sequential: tier-2 ships first, tier-3 scope is written second, tier-3 code is written third. Do not shortcut. Tier-3 scope may pivot to GP-069 level 2 debate only if phase-2 fails in a way that contaminates the tier-2 story; otherwise level 2 remains deferred.

## Cross-references

- `GP-069_champion_nesting_audit_gate_seam.md` — level 1 gate definition
- `GP-023_sandbox_10_nesting_collapse_audit.md` — the motivating pathology
- `GP-061_void_driven_steering_measurement_seam.md` — tier-2 measurement (runnable now, independent of this)
- `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` — v4 amendment, R3b/R4 protocol
- `src/ztare/validator/fit_primitive.py` — BIC/AIC telemetry patch (2026-04-15), and the file that needs the `score_mode="discrete_exact"` branch for the discrete scorer
- `src/ztare/validator/structural_constraint_extractor.py:224` — `_GENERALIZED_OPS` one-line extension point for modular pilot
- `src/ztare/validator/negative_space_extractor.py:64` — `_candidate_universe` corpus-seeding gate (axis 2 of the vocabulary-ceiling entry)
- `insights_ledger.md` — INS-011 (partial retraction standing), and the new Component B vocabulary-ceiling entry
