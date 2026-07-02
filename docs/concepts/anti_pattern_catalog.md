---
description: "Mining-derived catalogue of epistemic failure modes with cross-LLM validation."
---

# Anti-Pattern Catalog, Mining-Derived

> Up: [Documentation map](../README.md)

> Role among the concept docs. The canonical *operational field guide* to epistemic failure modes: the catalogued instances. The canonical *structural* statement of why they occur is [epistemic_principles.md](epistemic_principles.md) Part I. [cognitive_gym.md](cognitive_gym.md) and [agentic_engineering_patterns.md](agentic_engineering_patterns.md) point here for the catalogue.

> ⚠ 2026-04-24 CROSS-LLM VALIDATION UPDATE, cross-provider classifier audit (100-record sample, 3 providers: gpt-4.1-mini / claude-haiku-4.5 / gemini-3.1-flash-lite) produced 48% three-way agreement (pairwise κ 0.56-0.58). Verdict: FAILS cross-LLM validation (<0.60 threshold).
>
> What this means in practice:
> - PART 1 (Structural Blockers) REMAIN VALID, they come from a DETERMINISTIC regex taxonomy, not the LLM classifier. Cross-LLM disagreement does not apply.
> - PART 2 (Ceiling-Breakers) ARE DISPUTED, the class labels (`missing_counterfactual`, `overclaimed_scope`, `parameter_sensitivity`, etc.) come from the LLM classifier. Three LLMs disagree on them significantly. Example per-class three-way stability: `missing_counterfactual` 9.5%, `overclaimed_scope` 25%, `missing_mechanism` 40%, `parameter_sensitivity` 34.8%, `unfalsifiable_claim` 20%.
>
> Key implication: the `"ceilingbreaker"` and `"both"` modes of `inject_antipattern_catalog` inject class-labels that different LLMs would assign differently. Operators should treat those modes as EXPERIMENTAL, not validated. Use `"hardkill"` mode by default. Full audit: `analytics/queries/cross_provider_classifier_agreement_2026-04-24.json`.
>
> 2026-04-24 SUPER-CLASS COLLAPSE TEST ([GP-151](../../research_areas/seams/engine/diagnostics/GP-151_classifier_telemetry_downgrade_seam.md) §5.4): same 100-record sample, labels collapsed from 15 classes to 3 super-classes (`structural_blocker` / `ceiling_breaker` / `other`). Three-way agreement jumps 48% → 75% (below the 90% gate for live adoption). Per-super-class stability: `ceiling_breaker` 72.2%, `structural_blocker` 28.6%. Verdict: observability-only, do not adopt live super-class routing. Task 12 stagnation-reset on fine-grained regex labels remains live because regex is deterministic within-session. See `GP-151 (internal seam)` §8.
>
> 2026-06-02 STRONG-MODEL RETEST (better design): the 2026-04-24 run used weak models (gpt-4.1-mini / haiku / flash-lite). Re-ran on the same records with a sharp 2-stage super-class prompt and STRONG cross-family raters routed correctly (deepseek via API; codex-GPT + claude via subscription CLI), each gated by a positive control. n=50, 3 raters: 3-way super-class agreement 70%, but the two frontier raters agree substantially: codex↔claude κ=0.72 (deepseek is the divergent/weaker rater, κ≈0.50 vs each). Diagnosis of the residual: the disagreements are principled, not noise, ~25% of critiques are truly dual (an unsupported assumption that ALSO overclaims scope; a missing mechanism that IS a scope limitation), so a forced single dominant label caps agreement. Net: the original FINE 15-class failure was over-granularity (stands); the ceiling-breaker SUPER-CLASS is substantially reliable between strong raters (κ=0.72); the right fix is MULTI-LABEL (a critique can be both structural and ceiling), where a finer single-label taxonomy would not help. Script: `scripts/public/mining/research_mode/ceiling_breaker_retest.py`; data: `analytics/public/queries/classification/ceiling_breaker_retest_2026-06-02.json`.


*Source:* first mining pass over the enriched trajectory archive (1825 records, 84 projects, 2026-04-24). Findings reported in `GP-149 (internal seam)` §2.

*Purpose:* two distinct lists of failure patterns observed in 65%+ of the corpus. Injected into Newton-mode substrate theses (when rubric `inject_antipattern_catalog: true`) so the mutator sees them before writing, ahead of any judge flag.

How these two lists differ:

The mining data splits failure classes into two causal categories based on frequency lift (freq in high-score iters / freq in low-score iters):

- *Structural blockers*: lift < 1. When these appear, the thesis cannot score high. Avoidance is a precondition for ≥85.
- *Ceiling-breakers*: lift > 1. Appear MORE frequently as weakest-link in high-score iters (10-15% each at ≥85). At high scores, these are the "best-available residual critique" the judge finds. Engaging them head-on is what pushes past 85.

Confusing these two and treating everything as "avoid" would reduce thesis quality. The ceiling-breaker classes require structural engagement.

---

## PART 1, Structural blockers (AVOID these; they kill any thesis)

These classes appear in 0-7% of ≥85-score iterations and 2-22% of <60-score iterations. Their presence is a strong negative signal.

### SB-1: Circularity / Self-reference

Pattern: the thesis's conclusion is presupposed in its premise. Or: a definition that refers to itself. Or: a gate that validates the thesis using another part of the same pipeline that produced the thesis.

Empirical signature (weakest-point text): contains `self-referential`, `hard self-reference`, `circular`, `tautolog`, `begs the question`, `already assumed`, `prior encodes what is being proven`.

Observed corpus rate: 0.0% in ≥85 iters; 6.1% in <60 iters. Complete absence from the high bucket.

Example weakest-point (anonymized from corpus):
> "Structured semantic-gate derivation classified the proof as hard self-reference. The thesis asserts the causal sufficiency of its derived observable thresholds while the thresholds themselves are defined in terms of the asserted causal chain."

Avoidance protocol: before writing a thesis, ask "what would falsify this claim that is NOT something my own machinery produces?" If the answer is nothing, the thesis is circular.

### SB-2: Harness defect / broken test

Pattern: the `test_model.py` or equivalent gate harness fails at the runtime level (import error, path error, `NameError`, `FileNotFoundError`). The test CANNOT run, so no evidence for or against the thesis is gathered.

Empirical signature (weakest-point text): contains `HARNESS DEFECT`, `test_model.py`, `FileNotFoundError`, `ImportError`, `ModuleNotFoundError`, `fail_runtime`, `NameError`, `SyntaxError`.

Observed corpus rate: 1.4% in ≥85 iters; 21.8% in <60 iters (lift 0.06).

Avoidance protocol: standard-library-only Python (unless rubric declares `runner_allowed_imports`). Absolute file paths via `Path(__file__).resolve().parents[N]`, never bare relative. All data embedded in the test or loaded from a deterministic absolute location. Every variable defined before use.

### SB-3: Unfalsifiable claim

Pattern: the thesis makes a claim that has no operational test. The predicate is not decidable from any observation or computation.

Empirical signature: contains `unfalsifiable`, `no operational test`, `not testable`, `no discriminator`, `non-discriminating`, `no observable consequence`, `cannot be tested`, `no falsifier`.

Observed corpus rate: 1.4% in ≥85 iters; 2.7% in <60 iters (lift 0.51).

Avoidance protocol: every claim the result rests on must be accompanied by a CONCRETE OBSERVABLE whose value would falsify it. Name the observable, name the value-threshold, name the mechanism to measure it.

---

## PART 2, Ceiling-breakers (ENGAGE these head-on; the judge WILL flag them at high scores)

These classes appear in 6-16% of ≥85-score iterations. They are the TOP-OF-DISTRIBUTION residual critiques: at high scores, the judge has nothing lower-severity to flag, so finds these. Theses that engage these classes score high. Theses that ignore them cap at 70-85.

### CB-1: Overclaimed scope

Pattern: the thesis applies a result derived on a bounded dataset / regime / parameter range to a wider scope without justifying the extension.

LLM-classified occurrences in the corpus: 187 records across 48 projects (most-common ceiling-breaker).

Empirical signature: contains `overclaim`, `generalizes beyond`, `extrapolates outside`, `applies broadly without`, `universal claim from bounded evidence`, `not demonstrated outside`, `scope overreach`.

High-score frequency: 15.6%. This is the SINGLE most common weakest-link in ≥85 iters.

Engagement protocol: explicitly state the evidence envelope. Explicitly state what the thesis does NOT claim outside that envelope. Name the specific observation / computation whose value would determine whether the claim extends beyond the envelope.

### CB-2: Missing mechanism

Pattern: the thesis describes WHAT happens (correlation, pattern, observation) without the causal HOW.

LLM-classified: 147 records, 48 projects.

Empirical signature: `no mechanism named`, `correlation without causation`, `no causal chain`, `phenomenological fit`, `descriptive but not mechanistic`, `cannot explain why`, `Kepler-class fit`.

High-score frequency: 10.9%.

Engagement protocol: name a specific causal mechanism. Name its known sources in the literature. Name the level (microstructural / statistical / algebraic / topological) at which the mechanism operates. State what would happen if the mechanism were absent.

### CB-3: Missing counterfactual / rival hypothesis

Pattern: thesis asserts its explanation without canvassing rival explanations that fit the same evidence.

LLM-classified: 89 records, 36 projects. Novel class (regex taxonomy had no equivalent).

Empirical signature: `no rival considered`, `no counterfactual`, `alternative explanations not addressed`, `rule out other causes`.

High-score frequency: 9.5% (lift 2.41, the HIGHEST lift ceiling-breaker).

Engagement protocol: explicitly name ≥2 rival hypotheses that fit the same evidence. For each, explain why it fails where the thesis succeeds. Name the ONE specific observation that would distinguish the winner.

### CB-4: Catastrophic / critical assumption

Pattern: an assumption so central that its failure invalidates the entire thesis, stated without justification or risk analysis.

Regex occurrences: 157 records.

Empirical signature: `catastrophic assumption`, `fatal if`, `central premise not justified`, `hinges on unproved`, `entire guarantee depends on`.

High-score frequency: 10.9%.

Engagement protocol: identify the ONE most critical assumption. State it as a falsifier. State what observation would kill it. State a fallback (narrower scope) that would still support the conclusion if the assumption fails.

### CB-5: Parameter sensitivity / unverified bound

Pattern: a numeric threshold, bound, or exponent on which the result depends is set empirically or by convention without derivation.

LLM classification: 81 records (parameter_sensitivity) across 30 projects. Regex: 94 records (unverified_bound) across similar project breadth.

Empirical signature: `empirically observed`, `tuned threshold`, `no derivation`, `κ ≤`, `bound < 10^`, `chosen to`, `without proof that`, `assumed upper-bound`.

High-score frequency: 6.1-6.8%.

Engagement protocol: either derive the bound from a theorem OR declare it as a stipulated assumption (with a SHA-256 commitment BEFORE the evaluation) OR narrow scope so the bound is provable by construction. The gp140→CW-PT transition (Chebyshev basis → provable condition-number bound) is the canonical example.

### CB-6: Exhaustiveness / completeness overclaim

Pattern: "this list / this partition / this set of cases exhausts all possibilities" asserted without proof of exhaustiveness.

Regex: 62 records.

Empirical signature: `exhaust`, `all cases`, `no coverage proof`, `assumes completeness`.

High-score frequency: 2.7%.

Engagement protocol: for any "covers all X" claim, either prove the partition via a named classification theorem, or weaken to "covers all observed X" with N documented cases and an explicit residual uncovered-case policy.

### CB-7: Tail generalization / far-field extrapolation failure

Pattern: thesis fits within the observed range but predicts poorly (or is unjustified) in the far-tail / asymptotic / large-N regime.

Regex: 116 records, 4 independent mining queries converge on this class as the CENTRAL blindspot.

Empirical signature: `farther tail`, `asymptot`, `beyond training`, `large-N behavior`, `extrapol`, `far-field`.

High-score frequency: 8.2%.

Engagement protocol: declare the evidence envelope explicitly. Declare the asymptotic regime (if any). If the thesis extrapolates, name the specific asymptotic-scaling assumption, its source, and the observation that would falsify it in the far-tail. The structural-pivot library does NOT help this class (pivot effectiveness = -0.7 mean delta). Evidence-level engagement is mandatory.

---

## PART 3, Usage

### Rubric-gated injection (updated 2026-04-24 per stratified mining)

The two parts require DIFFERENT rubric flags per judge-stratified mining findings. Part 1 is cross-judge-validated (structural under gpt-4.1, gemini, o3, claude-sonnet). Part 2 is partially judge-specific (`missing_mechanism` and `parameter_sensitivity` flip sign between judges).

*Recommended rubric structure:*

```json
{
  "inject_antipattern_catalog": "hardkill"
}
```

- `"hardkill"` (safe default for any Newton-mode project): appends ONLY Part 1 (cross-judge-validated structural blockers).
- `"ceilingbreaker"`: appends Part 2 (ceiling-breakers). Use ONLY if the project's judge family matches the judges under which the ceiling-breaker lifts replicated (currently gpt-4.1 confirmed; others insufficient N). Flip to this setting after the judge is declared.
- `"both"`: appends both. Legacy behavior; equivalent to original `true`.
- `true`: alias for `"both"`. Backward compat.
- `false` (default): no injection.

Default: false. Opt-in per project rubric. Existing projects unaffected.

*Why this split matters (data):* stratified analysis across 4 judge families shows that all 7 structural-blocker classes have lift=0.00 across every tested judge (universally bad). But `missing_mechanism` has lift 0.84 under gpt-4.1 (negative signal) vs. 2.43 under o3 (positive signal), direction flips. Injecting a universal ceiling-breaker catalog would give the o3-mutator+gpt-4.1-judge pipeline MISALIGNED guidance on those classes. Only Part 1 is safe to inject regardless of judge choice.

### Validation plan (Popper pre-registration, per [GP-149](../../research_areas/seams/engine/diagnostics/GP-149_failure_taxonomy_hardening_primitives_seam.md) §9)

If this catalog is effective on opted-in projects:
- `missing_mechanism` frequency in weakest-points drops by ≥30%.
- `overclaimed_scope` frequency drops by ≥20%.
- Median iters-to-score-80 drops by ≥20%.

Failure to observe these → catalog rolled back, lesson documented in memory.

### Not a replacement for rubric dimensions

This catalog is PROMPT-CONTEXT guidance for the mutator. The rubric's dimensions still govern scoring. A mutator that ignores this catalog but writes an excellent thesis can still score high. A mutator that internalizes it but writes a bad thesis can still score low. The catalog is a signal boost; it guarantees nothing on its own.

---

## PART 4, Post-Completion Rubric Heuristics (gp145b + gp150, 2026-04-24)

*Source:* post-completion mining of gp145b_saw_narrow_null (44 iters, champion 66, final 48) and gp150_epistemic_boundary_audit (23 iters, champion 71, final 38). Both runs completed under o3 judge.

These heuristics are extracted from runtime trajectories, a layer beyond the initial corpus mining. They refine the catalog with domain-specific patterns from mathematical-rigor substrates (gp145b) and self-auditing substrates (gp150).

### RH-1: Constant exhibition rule

*Pattern:* Thesis invokes a theorem with hidden constants (Bailey-Ferguson, condition-number bounds, approximation error bounds) but never exhibits the constant numerically or derives its value from first principles.

*Source:* gp145b, 12+ judge attacks on "hidden constant c in FBA Theorem 2." Champion capped at 48 because c(x,3) ≤ 2^363 was hand-patched with ad-hoc κ_safety=2^10 without rigorous derivation. Score range when this pattern present: 15-66.

*Avoidance:* When invoking any theorem with named constants, compute and present the constant's numerical value, derived from the theorem's preconditions applied to the specific inputs. If the constant cannot be derived, state that as a limitation and stop short of asserting a heuristic bound.

*Failure family:* `parameter_sensitivity` (CB-5 overlap) + `residual_lower_bound_rigor` (new).

### RH-2: Theorem direction mapping

*Pattern:* Forward recovery theorems (e.g., "IF a relation exists, PSLQ will find it") used contrapositively ("PSLQ found nothing → no relation exists") without independent verification of the contrapositive's numerical preconditions.

*Source:* gp145b, iter 25 judge provided π−355/113 counter-example showing 100-bit margin insufficient when κ₂ large. Same directional confusion appeared in 10+ iterations. Score collapse: 66→25 when judge exposed the conflation.

*Avoidance:* Explicitly label whether theorem use is FORWARD (recovery guarantee) or CONTRAPOSITIVE (non-existence proof). For contrapositive use, prove independently that all numerical stability preconditions hold at every step of the algorithm's execution, including past initialization.

*Failure family:* `theorem_application_fidelity` (new, maps to CB-4 catastrophic assumption).

### RH-3: Condition number propagation

*Pattern:* Thesis bounds κ of an initial matrix/operator and assumes the bound propagates through iterative algorithm steps (PSLQ unimodular updates, Krylov subspace expansions, etc.) without proving propagation.

*Source:* gp145b, iter 24 judge (Gemini-Pro): "Cauchy interlacing is inapplicable to PSLQ's congruence transforms H_k = U_k G U_k^T; κ₂(H_k) can grow arbitrarily." Score range when this pattern present: 12-32.

*Avoidance:* If the thesis bounds κ of an initial configuration, it must also bound κ of ALL intermediate configurations the algorithm visits. Principal-submatrix bounds (Cauchy interlacing) do NOT apply to congruence transforms. State the transform class and prove κ-stability under it, or treat κ as unbounded.

*Failure family:* `condition_number_control` (new, maps to CB-5 unverified bound).

### RH-4: Finite-domain operationalization mandate

*Pattern:* Thesis claims a structural gap or non-approximability result that holds only asymptotically (as t→∞, |x|→∞, m→∞) without demonstrating it on a finite, experimentally relevant domain.

*Source:* gp150, judge repeatedly attacked Caputo/time-fractional theses with "Stone-Weierstrass on finite intervals applies; your discriminator requires t→∞." Score range for infinite-horizon arguments: 6-38. Champion (71) succeeded by shifting to a FINITE-domain discriminator (M₄ divergence observable on bounded spatial windows).

*Avoidance:* Every non-approximability claim must include a concrete finite-domain test case with explicit domain size. If the gap evaporates on bounded windows, it is unfalsifiable and scores <50. The gp150 champion's pivot from "infinite-horizon Caputo memory" to "finite-domain M₄ divergence" is the canonical fix.

*Failure family:* `unfalsifiable_claim` (SB-3 refinement).

### RH-5: Architectural loophole enumeration

*Pattern:* Thesis claims a solver gap but fails to block standard escape routes: (a) adaptive parameter growth, (b) phase-space augmentation / ODE embedding, (c) rational/neural surrogates, (d) compositional chaining of existing solvers.

*Source:* gp150, delay-equation theses (iters 6-12) systematically demolished via "linear-chain trick embeds this into high-dimensional ODE" and "Prony approximation on finite windows covers this." Score range: 28-62. Champion survived because M₄ divergence resists all four escape routes.

*Avoidance:* For any claimed solver-class gap, explicitly enumerate the four standard escape routes and prove the gap resists each. If any route absorbs the gap, it is an implementation backlog, falling short of a structural boundary.

*Failure family:* `exhaustiveness` (CB-6 refinement).

### RH-6: Stagnation vs. cycling distinction

*Pattern:* Loop control kills a productive run via stagnation counter when the mutator is exploring distinct critique classes across iterations.

*Source:* gp150, run-1 killed at iter 8 (stagnation_count 4) because `underidentified_after` defaulted to 3 in the generated rubric. But [GP-148](../../research_areas/seams/engine/discovery/GP-148_void_mining_seam.md) corpus mining shows champions typically need 20+ iterations of grinding through different critique classes. The loop control contradicted the chassis's own mining findings.

*Avoidance:* Track "number of distinct critique classes encountered" separately from "number of iterations without score improvement." A run cycling through 3 critique classes for 10 iterations (true stagnation) is worse than one bouncing through 7 distinct classes in 8 iterations (healthy exploration). Rubric should set `underidentified_after` to at least 6 for self-auditing substrates.

*Failure family:* `apparatus_self_consistency` (new, meta-level).

### RH-7: Evidence-injection plateau

*Pattern:* Injecting new evidence mid-run produces a temporary score spike followed by regression as the judge attacks the new evidence's own weaknesses.

*Source:* gp145b, Evidence Set H injected after iter 16 (score 18). Iter 17 peaked at 66 (the champion). Subsequent 25 iterations regressed to 12-48 band. The evidence supplied the missing Bailey-Ferguson constant c but the constant itself was heuristic, so the judge attacked the heuristic.

*Avoidance:* Evidence injections should supply PROVEN facts (derived constants, certified bounds, published theorems with page citations). Conjectured bounds or heuristic estimates will be attacked by the judge, causing the thesis to regress past the pre-injection baseline.

*Failure family:* `proof_obligation_deferral` (new, maps to CB-4).

### RH-8: Cyclic error non-learning

*Pattern:* The same algebraic or logical error (sign reversal, inequality direction, binary/decimal precision confusion) re-emerges across iterations despite being flagged by the judge.

*Source:* gp145b, inequality direction error in iter 6 repeated the same flaw from run-1 iter 5. Numeric constant off by 52 orders in iter 21. Binary/decimal precision conversion reversed in multiple iters. The mutator does not retain corrections across iterations.

*Avoidance:* When the judge flags an algebraic error, inject it as a derived constraint with `failure_family: "algebraic_sign_error"` so the mutator sees it in subsequent iterations. Current derived_constraints mechanism supports this but the mutator must be prompted to check constraints before writing equations.

*Failure family:* `harness_defect` (SB-2 variant, the thesis's own math is the broken harness).

### RH-10: Self-refuting audit pattern

*Pattern:* A substantive-sounding flaw surfaces in one audit iteration (score ≥75) and is REFUTED by re-implementation in a subsequent iteration (score <40). Without the second-pass refutation, a v2.x patch would have been written for a flaw that does not exist at the asserted magnitude.

*Source:* gp153 v2.0-critique audit, 2026-04-24:
- iter 6 (78): claimed `Student-t(ν≤4)` noise induces ≥30% mis-ranking in MDL_v2 → iter 8 (32): "core falsifier fails on re-implementation: mis-rank frequency is <1%, not ≥25%."
- iter 9-10 (50/42): claimed heteroscedastic-bias mis-ranking ≥30% → iter 12 (25): "central quantitative claim ≥30% falsified by counter-test: observed rate ≈0%."

Both substantive-looking flaws DIED on second-pass re-implementation. Two patch cycles avoided.

*Avoidance:* Do not write a v2.x patch from a single iter's claim until the next iter has independently reproduced the failure rate at the asserted magnitude. Treat first-iter claims as hypotheses and require ≥1 independent reproduction before patching the spec.

*Failure family:* `unsupported_assumption` (CB-3 refinement, the "rival" is the audit's own next iteration).

### RH-11: Apparatus-proposed fix sign errors

*Pattern:* Apparatus-generated fix formulas carry sign errors and/or missing terms vs the first-principles derivation, even when the underlying flaw is valid. The apparatus reliably FINDS flaws but is unreliable at PROPOSING formulas.

*Source:* Framer spec evolution v1.0 → v2.0:
- v1.0: Jacobian term sign +1 (should be −2)
- v1.1: σ_noise floor in raw-y units (should be Jacobian-transformed)
- v1.2: Jacobian coef −1 (should be −2)
- gp153 iter 13 (38): proposed v2.1 MDL formula "drops the N·log σ̂² term and inverts the sign of Σ log g_i², so it is not the negative log-likelihood of a heteroscedastic Gaussian model"

Four sequential apparatus-proposed formulas, four math errors. The pattern is recurring.

*Avoidance:* Treat any apparatus-proposed FIX FORMULA as a hypothesis to verify against likelihood-axiom derivation. If the apparatus says "MDL should be X," derive X from a stated likelihood and verify the derivation before implementing.

*Failure family:* `missing_derivation` (CB / new, the apparatus's formula isn't grounded).

### RH-12: Magic-number recursion in apparatus-proposed patches

*Pattern:* An apparatus-proposed threshold (e.g., "10× variance-spread", "50-bit MDL gain", "0.3 correlation cutoff") is itself ad-hoc, it repeats the same magic-number anti-pattern the spec was originally trying to escape. The apparatus copies the spec's threshold style without deriving the new threshold.

*Source:* gp153 iter 11 (50): "Patch proposal (σ_i² weighting + G-HETERO-VAR) uses an ad-hoc 10× variance-spread threshold and lacks a proof it will not itself introduce instability or over-penalise truly homoscedastic data."

The 10× threshold has no derivation. It's a round number chosen to look approximately right.

*Avoidance:* Any threshold the apparatus proposes must trace to a stated principle (Wilson interval at given confidence, Heisenberg estimator's noise floor, Chebyshev / quantile bound). Round numbers without derivation are not acceptable. If the apparatus cannot derive a threshold, the reviewer should derive it before implementing.

*Failure family:* `parameter_sensitivity` (CB-5 refinement, recursive within the apparatus's own self-corrections).

### RH-9: Operational materiality gap

*Pattern:* A technically sound thesis (high probability on logical premise nodes A, B) has low outcome probability because the judge doubts the gap's practical consequence (low probability on "materiality" node C).

*Source:* gp150, champion DAG: Node A (mixtures impose exponential tails) = 0.80, Node B (fractional-Laplacian needs power-law tail) = 0.75, Node C (divergent M₄ materially affects observable) = 0.35. Outcome = 0.58 despite strong premises. The judge's "engineer's veto": valid but operationally immaterial.

*Resolution:* The user's FOM validation (M₄_FOM grows 28× as domain quadruples, M₄_MIX stays flat at ~35) is the canonical answer: supply the finite-domain benchmark that demonstrates operational materiality. Feed back as evidence to push Node C from 0.35 toward 0.80+.

*Failure family:* `missing_counterfactual` (CB-3 refinement, the counterfactual is "what task actually fails without this?").

### RH-13: Categorical-as-continuous smuggle

*Pattern:* When the substrate exposes a categorical predictor (modality, architecture, study, fit-convention), the mutator hashes the string to an integer and applies continuous math (log, division, polynomial) to that integer. The distance between hash("L") and hash("V") has no physical meaning, so the input's structure is meaningless before any math runs on it.

*Source:* gp154 iters 5, 8, 11, 12, 13 (2026-04-24). Across multiple iters the o3 mutator wrote `numeric_code(d)` helpers that mapped {"L", "V", "M", ...} to {0, 1, 2, ...}, then applied `log(d)` and `1/d`. The judge correctly identified this every time as "a core data-type error... mapping categorical variables to a continuous integer index, and then applying continuous mathematical functions". Harness then crashed with IndexError / ZeroDivisionError because the hashing was uneven. Score 0 every iter.

*Avoidance for substrate authors:* Expose categoricals as Python strings AND provide explicit feature-vector schema. Either provide one-hot indicator columns or document that the mutator must use indicator functions (`1 if features['modality'] == 'language' else 0`). Never let a substrate force the mutator to choose between hashing and giving up.

*Avoidance for the mutator:* When `features['modality']` is a string, you have three legitimate moves: (a) one-hot encoding to a vector of indicator columns; (b) regime selectors / case dispatch (`if modality == 'language': ...`); (c) propose a hand-crafted ordinal mapping (e.g., "complexity rank"), valid only when physics justifies the ordering. Alphabetical accident does not count.

*Failure family:* `category_error` (NEW, distinct from `unit_error` because the smuggling happens at the type-system layer before any operation runs).

### RH-14: Vacuous null via excluded vocabulary

*Pattern:* A thesis declares "no closed-form law exists at dimension ≤ K" after exhaustively testing a discrete dictionary Σ that excludes the very functional forms the literature uses for the target phenomenon. Scaling laws ARE power laws. A null over a Σ that excludes `power_k` is vacuously empty and proves nothing.

*Source:* gp154 iters 4, 7, 10, 12, 13 (2026-04-24). The mutator's null-result theses tested dictionaries like {d, a, log d, 1/d, d·a, d/a}, all linear or pre-linear, without including `d^(-1/2)`, `d^(-1)` as standalone power-law forms with arbitrary exponent k. The judge: "the thesis arbitrarily excluded continuous power-law exponents, the literal standard functional form for empirical scaling laws... the null hypothesis wins vacuously due to an invalid metric space."

*Avoidance:* Any null-result thesis MUST include in its Σ at minimum:
- `power_k(x)` for k in {1, 2, -1, -1/2, 1/2}, covers Sharma α=2/d, Cagnetta α_D, Hoffmann
- `log(x)`, `exp(x)`, covers logarithmic regimes
- conditional / regime selector, covers two-regime models (variance vs resolution-limited)
- multiplicative composition `f(x) * g(y)` and additive `f(x) + g(y)` at depth ≤ 2

A null over a smaller Σ is reported as "no law at this restricted vocabulary" (with explicit acknowledgment that the literature standard form is excluded), and never as "no law exists".

*Failure family:* `vacuous_null` (NEW, refinement of CB-2 "missing-discriminator" applied to null results).

### RH-15: MRE aggregation fallacy

*Pattern:* A thesis claims that a single per-row predictive error of x% forces the dataset-level MRE above threshold τ. But MRE is the MEAN of per-row relative errors: a single 73% error contributes 0.73/n to MRE, where n is the row count. With n=9 and threshold 0.25, the maximum allowable single-row error is 0.25 * 9 = 2.25 (225%) IF every other row is perfect. Even with a 73% error, the budget remaining is 0.25 - 0.73/9 = 0.169 for the OTHER 8 rows.

*Source:* gp154 iters 8, 12 (2026-04-24). Mutator's null-thesis proof: "a single prediction collision of 73% relative error forces MRE > 0.25 across the 9-point dataset, therefore no 3-factor closed-form law can pass the gate." Judge: "0.734 / 9 = 0.081, which leaves a massive remaining error budget. The core logical proof of the thesis is fundamentally broken."

*Avoidance:* When arguing about gate satisfiability:
- Compute the MRE budget explicitly: total budget = τ * n, per-row budget = τ
- A single row's contribution to MRE = (its relative error) / n
- Distinguish: "no single-row prediction can be off by more than X" (max-relative-error gate, NOT what we use) vs "the AVERAGE relative error must be below τ" (MRE gate)
- Test the claim with arithmetic before submitting

*Failure family:* `arithmetic_error` (CB-1 refinement, the elementary-math error happens inside a thesis's own logical proof, upstream of the numerical fit).

### RH-17: Lookup-table fallacy (hardcoded-constants-as-law)

*Pattern:* A thesis presents an `if/else` decision tree of hardcoded empirical constants and human-labeled categorical selectors as a "zero-parameter physical law." The function appears parameter-free (no `params` dict, no fit) because the parameters are baked into the conditional branches. Each branch outputs a known answer for a known input, i.e., the function is a memorized lookup table dressed up as a closed-form predictor.

*Source:* gp154 iter 2 (2026-04-25). The o3 mutator wrote `I_model(feat)` with branches like:
- `if regime_hint == "variance_limited": return 1.0` (Bahri α=1)
- `if intrinsic_dim_d is not None: return round(2.0 / d, 3)` (Sharma)
- `if distractor_class == "semantic": return -0.160` (Cerebras hardcoded value)
- `if data_quality == "clean": return 1.817` (Bansal hardcoded value)
- `if scaling_var == "C_OPT" and "chinchilla" in study: return 0.50` (Hoffmann hardcoded)
- modality fallback dict with literature constants per modality

The judge: "The Lookup Table Fallacy: The thesis attempts to pass off an if/else decision tree of hardcoded empirical constants and human-labeled categorical selectors (oracle leakage) as a zero-parameter predictive physical law... Furthermore, the quantitative test suite explicitly failed to run, rendering all claims of 'Holdout MRE' entirely fictitious. The proposed 'law' reduces to an arbitrary script outputting known answers."

The mutator's intuition is partly right, the Sharma branch (`α = 2/d`) IS a physical law and the variance-limited branch (`α = 1`) IS a regime claim. But the Cerebras / Bansal / Hoffmann branches are pure memorization: they hardcode the very values the holdout would test. There's no generative content. The function is a dictionary.

Distinguishing a true piecewise law from a lookup-table:
- A true piecewise law has a generative formula in each branch that takes continuous predictors as input. `α = 2/d` is law-like because if you give it a new d=8, it predicts α=0.25, without ever having seen d=8.
- A lookup-table branch has the answer hardcoded for each categorical case. `if data_quality == "target_noise": return 2.772` predicts nothing for an unseen data_quality value; it's just rote.

The decisive test: if you remove a categorical branch and ask the model to predict a row in that category, can it produce ANY answer better than chance? If no, that branch was a lookup.

*Avoidance for the mutator:*
- For each piecewise branch, write the GENERATIVE rule first, then the parameters that instantiate it. `α = 2/d` is the rule; d is the parameter. `α = 2.772 if target_noise` has no rule, just a constant, that's a lookup.
- For categoricals where you have no generative theory, declare them as explicit free parameters (e.g., `α_target_noise: float = 2.772 # fitted to row 104`). This makes the parameter count explicit so the K_law budget catches the memorization.
- Better still: propose a relationship between the categorical and a continuous derived feature. E.g., "data_quality maps to noise_entropy_bits via [hypothesis]; α = f(noise_entropy_bits)". This converts a lookup into a falsifiable hypothesis.

*Failure family:* `lookup_table_dressed_as_law` (NEW, extension of CB-1 "memorization" applied to piecewise functions where each branch hides a constant in plain sight).

### RH-18: Kernel-camouflage lookup table (smooth-function disguise)

*Pattern:* A thesis presents a continuous closed-form function (Gaussian, sigmoid, lognormal, etc.) whose hardcoded centers, widths, and amplitudes are positioned exactly at the withheld-class feature values that the substrate critic exposed in the briefing. The form looks structurally like a smooth scaling rule but is functionally equivalent to RH-17's class-conditional lookup table. Only ONE constant is fitted. The structurally needed centers/widths/amplitudes are mutator-chosen literals matching the briefing's exposed cross-class values.

*Source:* gp163d_unified_accel iter 5 (2026-04-26, post-Class-A SPARC-mass enrichment). The gpt-5.5 mutator wrote a McGaugh-form interpolation with `c(M) = c0 · [1 + 14·exp(-((M-14.5)/1.228)²)] · exp(-5·sigmoid((M-22.795)/2.07375))`. The Gaussian boost peaks at M=14.5, the substrate's collapsed Class B (cluster) mass value, exposed verbatim in the iter-2 mutator briefing as `withheld ['14.5', '31.09']`. The sigmoid suppression activates above M≈22.8, the midpoint between Class B (14.5) and Class C (binary, raw kg-units value 30) so it suppresses Class C only. Six structurally needed constants (two centers, two widths, two amplitudes), all chosen by the mutator, none fitted. Only `c0` was declared in PARAMETER_NAMES. The form's `test_model.py` even includes structural-contract assertions hardcoding `_REF_B_MASS = 14.5` and `_REF_C_MASS = 31.09`.

The judge scored the form 100 because it passed every gate in the existing stack: single Python expression, continuous primitives (exp, sigmoid, sqrt), one fitted parameter, holdout passed, combined-class farther-tail passed (Class B's 84 rows masked Class C's MRE=1.95 in the unweighted average).

*Why this is a distinct pattern from RH-17:*
- RH-17 has explicit class-conditional branches: `if class=='B': return 10·c else return c`. Detectable by AST inspection for class-label string literals in conditions.
- RH-18 has no class-label conditionals. The class structure is encoded in the *coordinates* of a continuous function. The form looks indistinguishable from a true physical rule until you compare the hardcoded centers to the briefing's exposed withheld-class feature values.

The empirical disambiguator: substrate-perturbation testing. When Class C's mass coordinate was changed mid-run from kg-units (~30) to solar-units (-0.30), the suppression kernel went inactive on Class C (sigmoid at M=-0.3 is essentially zero) and Class C MRE jumped from "passes near-miss" to 1.95. The boost kernel at M=14.5 stayed unchanged because Class B was unchanged. A true continuous law is invariant under substrate-coordinate perturbations (refit may shift c0 but the kernel SHAPE is data-driven). RH-18 forms collapse on the perturbed class because their kernel coordinates were tuned to the unperturbed substrate.

Distinguishing a true continuous law from kernel-camouflage:
- A true law has kernel centers/widths/amplitudes that emerge from FITTING against visible data. If the form has 6 structural constants, declare 6 in PARAMETER_NAMES and let scipy optimize them on visible Class A.
- RH-18 has those 6 constants HARDCODED to match exposed withheld-class values. The form would not survive being refit on a perturbed substrate, as the centers would have to be reset by the mutator each time.

The decisive test: if you remove the suspect constant from PARAMETRIC_FORM, declare it as a free parameter, and refit on visible data, do you recover (a) the same hardcoded value (then the form has discoverable physics), (b) something close to it within 50% (the form is consistent with physics but the mutator memorized one good initialization), or (c) something far away or unconverged (pure memorization, no underlying signal)? Only (a) earns RH-18 acquittal.

*Avoidance for the mutator:*
- Every numeric constant whose value matches a briefing-exposed withheld-class feature value to within 5% must be promoted to a free parameter. The apparatus's withheld-value-leakage gate (G-WITHHELD-VALUE-LEAKAGE) detects this pattern and rejects.
- If you have no theory for what the kernel center should be, declare it as a free parameter with a wide prior. Do not pin it to "where the briefing said the withheld class sits."
- The substrate critic surfaces extrapolation gaps so you can REFRAME (commit to a publishable null on the gap) or REQUEST ENRICHMENT (operator action). Using the gap's exposed numerical values to position a kernel is the camouflage move.

*Failure family:* `kernel_camouflage_of_class_label` (extension of RH-17 lookup-table-dressed-as-law to the continuous-function disguise. Same Goodhart pattern, different detector signature.)


*Pattern:* A thesis defends a null result by excluding from scope the very phenomenon that would refute it. The author writes "we exclude compute-optimal scaling from this analysis", and then claims "no law exists for the remaining phenomena", but the excluded class was the only collision the null relied on as evidence.

*Source:* gp154 iter 12 (2026-04-24). Author's null thesis depended on collisions between Kaplan-style and Chinchilla-style fits, then excluded compute-optimal scaling from scope, removing all such collisions. Judge: "the only valid collision is between Kaplan and Chinchilla, which the author inexplicably self-invalidated by explicitly excluding compute-optimal scaling from their scope."

*Avoidance:* Before excluding any feature subset from scope, ask: "Does my null/positive proof depend on data points that fall in this excluded subset?" If yes, the exclusion either (a) breaks the proof or (b) renders the proof trivially true on a degenerate subset. Either way, expose the dependency explicitly.

*Failure family:* `scope_circularity` (CB-7 refinement, the scope decision is itself the critical assumption).
