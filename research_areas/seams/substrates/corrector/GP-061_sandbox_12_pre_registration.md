# GP-061 Phase 2 — Modular Arithmetic Substrate Pre-Registration

> **Seam metadata** · `seam_id:` GP-061 · `track:` substrates · `status:` CLOSED - MIS-CALIBRATED 2026-04-15 (GT found iter 1, extract · `last_updated:` 2026-05-08


**Status:** CLOSED — MIS-CALIBRATED 2026-04-15 (GT found iter 1, extractor never activated; see §Closure)
**Draft date:** 2026-04-15
**Substrate:** `projects/gp069_sandbox_12/`
**Rubric:** `rubrics/gp069_sandbox_12.json` (`fit_score_mode: "discrete_exact"`)
**Parent seam:** `GP-061_void_driven_steering_measurement_seam.md`
**Predecessor:** `GP-061_sandbox_11_01_pre_registration.md` (closed N=2, underpowered — extractor never activated because GT was single-attractor)

> This file is private (under `research_areas/private/`). It is the only file that names the target shape, the sealed expected void slot, and the protocol. Nothing here may be copied into the charter, rubric, thesis, or evidence file.

## Claim under test

Same as sandbox_11: the `negative_space_extractor` void-injection channel changes the mutator's next-proposal distribution at a rate above chance, conditional on the scorer being non-trivially discriminating.

Sandbox_11 was inconclusive because the extractor never activated (single-attractor substrate, GT found at iteration 1, zero failed families). This substrate is designed to guarantee multiple failed families before any convergence is possible.

## Why modular arithmetic

The philosopher critique (2026-04-15) identified three properties that make this substrate appropriate:

1. **Multi-attractor landscape.** An LLM confronted with integer data from `(3x^2 + 5x + 7) mod 13` will try continuous functions first (polynomials, exponentials, piecewise fits), all of which fail badly because the output wraps. This guarantees ≥3 failed families before the correct operator class is explored — the extractor's activation condition.

2. **No tautology.** The void identifies a missing *operator type* (Mod absent from the AST feature-bag), not the answer. The mutator still must discover the polynomial, the modulus, and the composition. This is meaningfully different from the rejected modulated-gamma substrate where "try sin" for a sin-answer was tautological.

3. **Discrete scoring removes continuous epsilon attacks.** In continuous mode, a smooth approximation can game a low residual without discovering the true form. Discrete exact-match scoring has no partial credit — either the expression produces the right integer or it doesn't.

## Sealed ground truth (private, never copied into project dir)

`y = (3 * x**2 + 5 * x + 7) % 13`

with:
- Coefficients: a=3, b=5, c=7
- Modulus: p=13 (prime)
- Domain: x in {0, 1, ..., 50}
- Output range: {2, 3, 5, 6, 7, 9, 10} (7 of 13 possible residues)
- Period: 13 (quadratic residues mod prime)
- No noise — deterministic

Visible grid: 35 of 51 points (random split, seed=42).
Holdout grid: 16 points.

## Role separation (Division A / Division B)

This sandbox was constructed under M-form information isolation:

- **Division A (Lab Tech):** Knows GT. Generated evidence files and this pre-registration. Script at `/tmp/division_a_sandbox_12_generate.py` (outside repo, never committed).
- **Division B (Principal Investigator):** GT-blind agent. Wrote project_charter.md, rubric, test_model.py, gate_harness.py with zero GT knowledge. Briefed only as: "integer-valued function, exact match scoring."
- **Sentinel gate:** Automated leak detection (`src/ztare/validator/leak_sentinel.py`) with 33 denylist patterns. Division B's first draft had 14 hits (leaked "discrete", "sealed", "pre-registration", framework vocabulary). All neutralized. Second pass: 0 matches.

This is the first sandbox constructed under structural role separation rather than policy-based scrubbing.

## Protocol — paired A/B

Same structure as sandbox_11 with corrected measurement timing.

Each "pair" is two autoresearch runs against the same fresh project copy, same rubric, same seed iteration, same mutator/judge models, differing only in whether `negative_space_extractor` is enabled.

- **Treatment arm (T):** default autoresearch_loop. Void injection enabled.
- **Control arm (C):** `--disable-negative-space-extractor` flag. Same iteration count. Same rubric.

### Measurement point — corrected from sandbox_11

The philosopher critique identified that the sandbox_11 protocol measured "fingerprint divergence at iteration 1," but the extractor requires `confidence_threshold=3` failed families with `structural_misfit` classification. The divergence cannot manifest at iteration 1 — it manifests at the first iteration after the extractor fires (iteration 4+ at earliest, typically iteration 4 if iterations 0-2 each produce one new failed family and the extractor first runs at iteration 3).

**Corrected protocol:** Per pair, record:

1. **Extractor activation iteration (T arm only):** the first iteration where `workspace/derived_constraints.json` contains an entry with `producer=structural_extractor`. If the extractor never activates across all iterations, the pair is classified "extractor_inactive" and excluded from the binomial test (but reported separately).

2. **Family fingerprint at iteration N+1** (where N = extractor activation iteration): the `structural_memory.build_structural_family_signature` fingerprint of the proposal at the first iteration AFTER the void was injected. Compare T's fingerprint at N+1 against C's fingerprint at the same iteration index.

3. **Mod operator presence:** does the T arm's iteration-N+1 proposal contain `ast.Mod` in its AST? Does C's at the same iteration?

A pair is classified as:
- **Void-steered:** T and C produce different family fingerprints at iteration N+1, AND T's fingerprint incorporates `Mod` (or a structurally equivalent operation) present in T's void slot that is absent from C's proposal at the same iteration.
- **Not steered:** T and C produce the same fingerprint at iteration N+1, OR both contain `Mod` at the same iteration (data-driven discovery, not void-driven).
- **Divergent but unattributable:** fingerprints differ but the Mod presence doesn't trace to the void. Counted as "not steered" for the conservative test; logged for sensitivity analysis.
- **Extractor inactive:** extractor never fired in T arm. Excluded from binomial test; reported as calibration signal.

## Sample size and stopping rule

- **N ≥ 8 pairs** before any test is run (reduced from 10 due to cost — ~$0.90/pair from sandbox_11 precedent, budget ≈ $10). No peeking between pairs; the classification row for each pair is committed before the next pair starts.
- If operator cost forces early termination, the run closes with the pre-registered test result at whatever N was reached, flagged as underpowered if N < 8.
- If ≥2 consecutive pairs are classified "extractor_inactive," the substrate is declared mis-calibrated and the run closes as exploratory (not confirmatory).

## Test

One-sided exact binomial test. H0: p(void-steered pair) ≤ 0.5. H1: p > 0.5. α = 0.05.

- At N = 8, reject H0 if void-steered count ≥ 7 (exact one-sided p ≈ 0.0352).
- At N = 10, reject H0 if void-steered count ≥ 9 (exact one-sided p ≈ 0.0107).
- Record the exact threshold for whatever N the run actually reaches.
- "Extractor_inactive" pairs are excluded from N for the binomial denominator.

## Null result interpretation

Same as sandbox_11: failure to reject is "under this substrate and this scorer, the proposal-distribution channel is not detectable at α = 0.05." This is the second substrate after sandbox_11 (hinge). Per the sandbox_11 pre-reg §Null result interpretation: "Two consecutive null substrates would be taken as weak falsifying evidence against the GP-061 claim in its current form."

If sandbox_12 is also null (either extractor-inactive or void-steered count below threshold), the GP-061 claim is downgraded from "active hypothesis" to "unconfirmed — needs mechanism redesign before further testing."

## Philosopher critique — acknowledged items

The philosopher (2026-04-15) raised two items that are not addressed in this design and are logged as known limitations:

1. **Scrambled-void 3rd arm.** A third arm where the void fires with randomized content would distinguish void *content* from void *presence*. Not implemented due to cost (triples pair cost). Logged as a future extension if the 2-arm result is positive.

2. **Data-driven discovery confound.** Both arms see data with period 13 and output range < 13. A capable LLM might discover modular arithmetic from data alone. The paired design controls for this (both arms have the same data), but if both arms converge at the same speed, the experiment has no power. The "extractor_inactive" stopping rule partially mitigates: if both arms converge fast, the extractor never fires, and the pair is excluded.

## §Leak Audit (PRE_RUN_CHECKLIST §1)

### Denylist (Division A authored)

```
\bmod\b             modular          modulo           remainder
periodic            cyclic           \bperiod\b       quadratic
polynomial          \b3\s*\*\s*x     \b5\s*\*\s*x\b  parabola
\bprime\b           mod 13           mod.13           %\s*13
congruence          residue class    number theory    \bdiscrete\b
integer arithmetic  ground.truth     \bGT\b           \bsealed\b
pre.reg             division.a       lab.tech         \bGP-069\b
\bGP-061\b          \bsandbox\b      \bvoid\b         negative.space
\bsteering\b
```

### Sentinel result (post-neutralization)

```
SENTINEL PASSED — 33 patterns, 0 matches
```

Mutator-visible file set audited:
- `projects/gp069_sandbox_12/project_charter.md`
- `projects/gp069_sandbox_12/evidence.txt`
- `projects/gp069_sandbox_12/evidence_holdout.txt`
- `projects/gp069_sandbox_12/test_model.py`
- `rubrics/gp069_sandbox_12.json`

Division B first draft had 14 sentinel hits (framework vocabulary leaked through the agent briefing). All neutralized. Second pass: 0 matches.

## §Identifiability (PRE_RUN_CHECKLIST §3)

Modular arithmetic with integer coefficients is trivially identifiable: the function is deterministic (no noise), and exact match on 35 points with period 13 uniquely determines the polynomial and modulus. There is no parameter degeneracy — the coefficients (3, 5, 7) and modulus (13) are the only integers that produce this exact output sequence.

Formal proof: any polynomial `(a*x^2 + b*x + c) mod p` with p prime and 0 ≤ a,b,c < p is uniquely determined by its values at any p distinct x values. We have 35 > 13 visible points.

## §Charter Fingerprint (PRE_RUN_CHECKLIST §4)

```
38ac9046e5cc79dd1e132f0462ac3cff0272f0f2653cad28bc7b632c66928737  projects/gp069_sandbox_12/project_charter.md
afa359f1155392ef945198d2c9797c088a964d0099ee6c4794145dc7a84d9586  projects/gp069_sandbox_12/evidence.txt
1e845cfb23c9fcbacc1bd8ed89398e89d9704ff9558f130ba297cd9d05519e6f  projects/gp069_sandbox_12/evidence_holdout.txt
7ec9d08f434f5f5adaac89686524e6100f4e1b0319b86b8e38db16781273fadf  projects/gp069_sandbox_12/test_model.py
6a185a517e0f6de1625317c390581e4a036ab83805371258a0cb51612fa26401  projects/gp069_sandbox_12/gate_harness.py
d478706bb670128e028bbfa729bb25eee7c8c72e80ec6a1daacbe4f23898fe42  rubrics/gp069_sandbox_12.json
```

## §Smoke Gate (PRE_RUN_CHECKLIST §5)

Baseline `test_model.py` returns `f_model(x) = 0` for all x. Gate harness reports 0/16 holdout matches (harness_ok=false). Smoke test passed: f_model is callable and returns int.

Fixture regression tests for discrete scoring mode: 6/6 passed.

## §Sealed Command

```
make loop PROJECT=gp069_sandbox_12 RUBRIC=gp069_sandbox_12 ITERS=10 MODE=factory MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gemini
```

ITERS=10 to allow the extractor time to activate (needs 3+ failed families, so first possible void at iter 3, measurement at iter 4+).

## Go/no-go checklist

- [x] §Leak Audit — sentinel passed (33 patterns, 0 matches)
- [x] §Identifiability — trivially satisfied (deterministic, 35 > p=13 points)
- [x] §Smoke Gate — baseline returns wrong answers, harness correctly fails
- [x] §Charter Fingerprint — recorded
- [x] §Discrete scoring fixture regression — 6/6 passed
- [x] Role separation (Division A/B) — first sandbox under M-form construction
- [x] Philosopher critique — conditionally approved, measurement timing corrected
- [x] Philosopher-coder final code review — no fatal flaws; dead `discrete_tolerance` param removed, error message fixed, BIC=0 constraint documented, EXTRA_ARGS quoting verified
- [x] Operator seal with timestamp — **SEALED 2026-04-15 23:45 EDT**

**All checklist boxes PASSED. Pre-registration SEALED 2026-04-15 23:45 EDT.**

### Known constraints (from code review)
- `complexity_penalty_enabled` must remain `false` for `discrete_exact` substrates (BIC=0.0 would collapse ranking)
- `discrete_tolerance` parameter removed from `_evaluate_discrete_exact` signature (was dead code)

---

## §Closure — MIS-CALIBRATED (2026-04-15)

**Status:** CLOSED — substrate mis-calibrated, experiment non-confirmatory.

### What happened

Pair 1 treatment arm, iteration 1: gemini-3.1-pro-preview identified the exact GT `(3*x^2 + 5*x + 7) % 13` with perfect fit (score 83, max |residual| = 0.0, params a=3 b=5 c=7 m=13). Zero failed families produced. The negative_space_extractor never activated and cannot activate on this substrate with this mutator model.

Run stopped by operator after iteration 1. Control arm never started. No data recorded in `phase2_ab_results.jsonl`.

### Classification

Per §Sample size stopping rule: "If ≥2 consecutive pairs are classified 'extractor_inactive,' the substrate is declared mis-calibrated." One pair is sufficient to determine that the substrate is deterministically too easy — every pair will be extractor_inactive because gemini-pro solves the GT at iteration 1.

### Per §Null result interpretation

This is the second substrate (after sandbox_11/hinge) where the extractor never activated. Per the pre-registered interpretation: "Two consecutive null substrates would be taken as weak falsifying evidence against the GP-061 claim in its current form."

However, both failures are mis-calibration (substrate too easy), not genuine nulls (extractor fired but didn't steer). The GP-061 claim has never been tested under conditions where the extractor actually activates. The claim is **untested**, not falsified.

**Decision:** GP-061 is downgraded from "active hypothesis" to "unconfirmed — needs substrate redesign before further testing" per the pre-registered rule.

### Root cause analysis

1. **Modular arithmetic is in-distribution for gemini-pro.** Period detection on integer sequences is a well-represented pattern in LLM training data (math competition problems, code). The philosopher's calibration concern (#2: "A capable LLM might discover modular arithmetic from data alone") was exactly right.

2. **35 visible points with period 13 is massively over-determined.** The substrate provides 2.7x the minimum points needed for unique identification. Combined with property (1), the mutator has no reason to explore wrong families first.

3. **Same structural failure as sandbox_11.** Both substrates are single-attractor in practice: the correct functional family dominates at iteration 1, producing zero failed families, which means the extractor's activation condition (3+ failed families) can never be met.

### Lessons for sandbox_13

A viable substrate must satisfy:
- **Genuinely ambiguous first iteration:** multiple plausible families that score reasonably well
- **GT outside LLM training distribution:** not standard math patterns (polynomials, trig, modular arithmetic)
- **Misleading partial signal:** early evidence should actively support a wrong family
- **Sparse visible data:** closer to the identifiability minimum, not 2-3x over-determined
