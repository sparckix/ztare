# GP-061 Phase 2 — Large-Modulus Cubic Substrate Pre-Registration

> **Seam metadata** · `seam_id:` GP-061 · `track:` substrates · `status:` CLOSED - MIS-CALIBRATED 2026-04-16 (GT found iter 1 via Lagr · `last_updated:` 2026-05-08


**Status:** CLOSED — MIS-CALIBRATED 2026-04-16 (GT found iter 1 via Lagrange+GCD; see §Closure)
**Draft date:** 2026-04-15
**Substrate:** `projects/gp069_sandbox_13/`
**Rubric:** `rubrics/gp069_sandbox_13.json` (`fit_score_mode: "discrete_exact"`)
**Parent seam:** `GP-061_void_driven_steering_measurement_seam.md`
**Predecessors:**
- `GP-061_sandbox_11_01_pre_registration.md` (closed N=2, underpowered — extractor never activated, single-attractor GT)
- `GP-061_sandbox_12_pre_registration.md` (closed MIS-CALIBRATED — GT found iter 1, extractor never activated)

> **Framing disclosure:** This is an apparatus-hardening experiment. It tests whether a specific component (the negative_space_extractor) measurably changes the mutator's proposal distribution under controlled conditions. It is NOT a test of whether ZTARE can generate new science. The substrate is operator-engineered to force the extractor to activate. A positive result means "the steering mechanism works when the cage is built correctly," not "the engine can discover unknown truths." See §Null result interpretation for the honest interpretation of all outcomes.

> This file is private (under `research_areas/private/`). It is the only file that names the target shape, the sealed expected void slot, and the protocol. Nothing here may be copied into the charter, rubric, thesis, or evidence file.

## Claim under test

Same as sandbox_11 and sandbox_12: the `negative_space_extractor` void-injection channel changes the mutator's next-proposal distribution at a rate above chance, conditional on the scorer being non-trivially discriminating.

Sandbox_11 was inconclusive (single-attractor, GT found at iter 1). Sandbox_12 was mis-calibrated (same failure mode — GT found at iter 1 by gemini-pro). This substrate is designed to force multiple failed families before the correct structural form can emerge.

## Why large-modulus cubic

Sandbox_11 (hinge) and sandbox_12 (modular arithmetic mod 13) both failed because the correct functional family was immediately recognizable from the data:
- Sandbox_11: hinge regression is a standard ML pattern
- Sandbox_12: period-13 repetition visible in 35 data points; the modulus was trivially detectable

This substrate addresses both failure modes:

1. **No visible period.** The modulus is 997 (prime). With only 30 visible points out of a period of 997, zero complete cycles are observable. The data does not exhibit any periodicity.

2. **All points wrap.** The constant term (d=5000) exceeds the modulus (P=997), so every single data point is in the "wrapped" regime. There is no region of x where the output follows a recognizable polynomial curve. This eliminates the "first 6 points look cubic" attack that would work with a smaller constant.

3. **Data appears pseudo-random.** Visible outputs range from 15 to 968 with 29/30 unique values. Second differences are erratic (not constant, not monotone). No polynomial of any degree fits the visible data — even degree 15 achieves only 2/30 exact matches.

4. **Multi-step solution required.** To solve, the mutator must: (a) hypothesize modular arithmetic from the bounded integer range, (b) discover the modulus P=997, (c) recover the cubic polynomial coefficients by solving a modular linear system. Each step is non-trivial; together they require multiple iteration attempts through wrong families.

## Sealed ground truth (private, never copied into project dir)

`y = (7 * x**3 + 23 * x**2 + 100 * x + 5000) % 997`

with:
- Coefficients: a=7, b=23, c=100, d=5000
- Modulus: P=997 (prime)
- Domain: x in {0, 1, ..., 44}
- Visible output range: [15, 968] (29 of 30 unique values)
- No noise — deterministic

Visible grid: 30 of 45 points (x in [0, 29]).
Holdout grid: 15 points (x in [30, 44]).

## Role separation (Division A / Division B)

Constructed under M-form information isolation (same protocol as sandbox_12, per GP-072):

- **Division A (Lab Tech):** Knows GT. Generated evidence files via `/tmp/division_a_sandbox_13_generate.py` (outside repo, never committed).
- **Division B (Principal Investigator):** GT-blind agent. Wrote project_charter.md, rubric, thesis.md, test_model.py, gate_harness.py with zero GT knowledge. Briefed only as: "integer-valued function, exact match scoring."
- **Sentinel gate:** Automated leak detection (`src/ztare/validator/leak_sentinel.py`) with 38 denylist patterns. Result: 0 matches.

## Protocol — paired A/B

Same structure as sandbox_12 with identical measurement protocol.

Each "pair" is two autoresearch runs against the same fresh project copy, same rubric, same seed iteration, same mutator/judge models, differing only in whether `negative_space_extractor` is enabled.

- **Treatment arm (T):** default autoresearch_loop. Void injection enabled.
- **Control arm (C):** `--disable-negative-space-extractor` flag. Same iteration count. Same rubric.

### Measurement point

Same as sandbox_12 (corrected from sandbox_11). Per pair, record:

1. **Extractor activation iteration (T arm only):** the first iteration where `workspace/derived_constraints.json` contains an entry with `producer=structural_extractor`. If the extractor never activates across all iterations, the pair is classified "extractor_inactive" and excluded from the binomial test (but reported separately).

2. **Family fingerprint at iteration N+1** (where N = extractor activation iteration): the `structural_memory.build_structural_family_signature` fingerprint of the proposal at the first iteration AFTER the void was injected. Compare T's fingerprint at N+1 against C's fingerprint at the same iteration index.

3. **Mod operator presence:** does the T arm's iteration-N+1 proposal contain `ast.Mod` in its AST? Does C's at the same iteration?

A pair is classified as:
- **Void-steered:** T and C produce different family fingerprints at iteration N+1, AND T's fingerprint incorporates `Mod` (or a structurally equivalent operation) present in T's void slot that is absent from C's proposal at the same iteration.
- **Not steered:** T and C produce the same fingerprint at iteration N+1, OR both contain `Mod` at the same iteration (data-driven discovery, not void-driven).
- **Divergent but unattributable:** fingerprints differ but the Mod presence doesn't trace to the void. Counted as "not steered" for the conservative test; logged for sensitivity analysis.
- **Extractor inactive:** extractor never fired in T arm. Excluded from binomial test; reported as calibration signal.

## Expected extractor behavior

Unlike sandbox_12 (where the extractor never activated), this substrate is designed to guarantee extractor activation:

- **Iteration 0:** Baseline (f_model returns 0). Score = 0.
- **Iterations 1-3:** Mutator tries standard families (polynomial, trig, exponential, piecewise). All achieve 0-2/30 exact matches on visible data → `structural_misfit` classification with high residual. These are the failed families the extractor needs.
- **Iteration 3-4:** After 3+ failed families, the extractor activates. It examines the generalized feature matrix across all failed families. Expected void: `has_op:Mod` is absent from all attempted families (because polynomials, trig, exponentials don't use the modulo operator).
- **Iteration 4+:** The void hint ("missing Mod operator") is injected into the mutator's derived constraints. The treatment arm mutator now has a structural pointer toward modular arithmetic. The control arm does not.

## Calibration: why the extractor WILL fire this time

| Property | Sandbox_12 (burned) | Sandbox_13 (this) |
|---|---|---|
| Best polynomial fit on visible | 35/35 (perfect) | 0/30 (zero matches) |
| GT identifiable at iteration 1 | Yes (period-13 trivially visible) | No (pseudo-random, no period) |
| Failed families before solution | 0 (solved immediately) | ≥3 (polynomials, trig, piecewise all fail) |
| Extractor activation expected | Never (no failures) | Iteration 3-4 |

The critical difference: **in sandbox_13, the obvious answer (polynomial) scores 0/30 on visible data, not 35/35.** The mutator cannot escape the cage at iteration 1.

## Secondary measurement: proposal-shift (philosopher condition 3)

The primary measurement (void-steered vs not-steered) tests a conjunction: the extractor fires AND the mutator exploits the hint successfully. The philosopher correctly noted this is a harder test than the claim warrants. The actual GP-061 claim is about proposal-distribution shift, not successful solution.

**Secondary measurement (pre-registered):** At each iteration after the extractor fires (N+1, N+2, ...), record whether the treatment arm's proposal AST contains `ast.Mod` and whether the control arm's proposal at the same iteration contains `ast.Mod`. A pair is classified as:
- **Mod-shifted:** T contains `ast.Mod` at iteration N+1, C does not at the same iteration.
- **Not shifted:** Both or neither contain `ast.Mod` at the same iteration.

This is a weaker but cleaner signal: "did the extractor's Mod hint cause the mutator to try modular arithmetic sooner than it otherwise would?" It does not require the mutator to solve the full problem.

The secondary test uses the same binomial framework: H0: p(Mod-shifted) ≤ 0.5, one-sided, α = 0.05.

## Known limitations (philosopher critique)

### Output-range information leak

The visible data has outputs in [15, 968]. An LLM trained on number theory may recognize bounded non-negative integers as a signal for modular arithmetic. This is an inherent property of any modular-arithmetic substrate and cannot be eliminated without changing the problem class. The paired design controls for this (both arms see the same data), but it means the mutator may discover modular arithmetic from data alone, without the extractor's help. If both arms converge to Mod at the same rate, the experiment has no power. The "extractor_inactive" stopping rule and the secondary Mod-shifted measurement both mitigate this.

### Temperature and seed control

The autoresearch_loop uses the Gemini API's default temperature. No explicit random seed is set across arms. The paired design compares T and C at the same iteration index, which controls for iteration-level confounds, but model stochasticity adds noise. With N ≥ 8 pairs, individual-pair stochasticity is averaged out. The binomial test is conservative (counts only clean signals), so stochastic noise biases toward the null, not toward false positives.

### Dry-run gate (philosopher condition 1)

Before sealing, run a single treatment-only iteration (ITERS=4) to confirm that: (a) the mutator does NOT solve at iteration 1, and (b) at least one failed family is produced by iteration 3. If condition (a) fails, the substrate is burned. If condition (b) fails, ITERS should be increased. This dry run is not part of the formal experiment and its data is discarded.

## Sample size and stopping rule

- **N ≥ 8 pairs** before any test is run. No peeking between pairs; the classification row for each pair is committed before the next pair starts.
- If operator cost forces early termination, the run closes with the pre-registered test result at whatever N was reached, flagged as underpowered if N < 8.
- If ≥2 consecutive pairs are classified "extractor_inactive," the substrate is declared mis-calibrated and the run closes as exploratory (not confirmatory).

## Test

One-sided exact binomial test. H0: p(void-steered pair) ≤ 0.5. H1: p > 0.5. α = 0.05.

- At N = 8, reject H0 if void-steered count ≥ 7 (exact one-sided p ≈ 0.0352).
- At N = 10, reject H0 if void-steered count ≥ 9 (exact one-sided p ≈ 0.0107).
- Record the exact threshold for whatever N the run actually reaches.
- "Extractor_inactive" pairs are excluded from N for the binomial denominator.

## Null result interpretation

This is the third substrate after sandbox_11 (hinge) and sandbox_12 (modular arithmetic mod 13). Both predecessors were mis-calibrated (extractor never activated), so the claim has never been tested under proper conditions.

If sandbox_13 is the first substrate where the extractor activates:
- **Reject H0:** "Under controlled conditions with a sufficiently ambiguous substrate, the void-steering mechanism changes the mutator's proposal distribution." This is the apparatus-hardening result. It does NOT prove ZTARE can generate new science.
- **Fail to reject:** "Even when the extractor fires, its output does not measurably change the mutator's next proposal." This would be evidence against the GP-061 claim in its current mechanistic form.
- **Extractor inactive again:** Substrate mis-calibrated for a third time. GP-061 claim is suspended pending fundamental redesign of either the extractor's activation conditions or the substrate selection methodology.

## §Leak Audit (PRE_RUN_CHECKLIST §1)

### Denylist (Division A authored)

```
\bmod\b             modular          modulo           remainder
periodic            cyclic           \bperiod\b       quadratic
polynomial          cubic            \b7\s*\*\s*x     \b23\s*\*\s*x
\b100\s*\*\s*x      \b5000\b         \bprime\b        mod 997
mod.997             %\s*997          \b997\b           congruence
residue class       number theory    \bdiscrete\b      integer arithmetic
ground.truth        \bGT\b           \bsealed\b        pre.reg
division.a          lab.tech         \bGP-069\b        \bGP-061\b
\bsandbox\b         \bvoid\b         negative.space   \bsteering\b
\bwrap\b            wrapped
```

### Sentinel result

```
SENTINEL PASSED — 38 patterns, 0 matches
```

Mutator-visible file set audited:
- `projects/gp069_sandbox_13/project_charter.md`
- `projects/gp069_sandbox_13/thesis.md`
- `projects/gp069_sandbox_13/test_model.py`
- `projects/gp069_sandbox_13/evidence.txt`
- `rubrics/gp069_sandbox_13.json`

## §Identifiability (PRE_RUN_CHECKLIST §3)

The function `(7x^3 + 23x^2 + 100x + 5000) mod 997` with P=997 prime is uniquely determined by the data:
- Any cubic polynomial mod a prime P is determined by 4 points (invertible Vandermonde matrix mod P).
- The Vandermonde determinant for x=0,1,2,3 is 12. Since gcd(12, 997) = 1, the matrix is invertible mod 997.
- With 30 visible points, the system is massively overdetermined.
- The modulus P is uniquely determined by any 5 equations (4 coefficients + 1 modulus = 5 unknowns).

## §Charter Fingerprint (PRE_RUN_CHECKLIST §4)

```
e449349fd604a34e0a18723e0c46ba768bfeee2b47c3c0b296347b8fef94b4dc  projects/gp069_sandbox_13/project_charter.md
83e945a2daca85925bec9404fc7f7c4f2fe63f8ecffc31c08ce4130a4267112a  projects/gp069_sandbox_13/evidence.txt
0dcfb5b80b2e603a52c961539bae094747c107750accd5828026bfc604562aab  projects/gp069_sandbox_13/evidence_holdout.txt
899a4d8f6513f0dcc7506e0731bec2ab39b67f51d846812b3cdc2fe7181b0bc7  projects/gp069_sandbox_13/test_model.py
60b381372889e6632fbf635e5e9b65a78f9f97bc3b81f55d3208309e17c6ada3  rubrics/gp069_sandbox_13.json
c8858019b915743026c29f78bddc3434cbf9ec5ef0c995fa0d85b63e9705ff3b  projects/gp069_sandbox_13/gate_harness.py
```

## §Smoke Gate (PRE_RUN_CHECKLIST §5)

Baseline `test_model.py` returns `f_model(x) = 0` for all x. Gate harness reports 0/15 holdout matches (harness_ok=false). Smoke test passed: f_model is callable and returns int.

## §Sealed Command

```
PAIR=1 bash projects/gp069_sandbox_13/run_pair.sh
```

ITERS=10 to allow the extractor time to activate (needs 3+ failed families, expected at iteration 3-4).

## Philosopher critique — CONDITIONAL GO

Philosopher of science returned CONDITIONAL GO with 6 conditions (2026-04-16):

1. **Dry-run pair to confirm extractor activation** — ACCEPTED. Added as §Dry-run gate above. Must pass before sealing.
2. **Output-range [15,968] as stated limitation** — ACCEPTED. Added to §Known limitations.
3. **Separate proposal-shift from correct-solution measurement** — ACCEPTED. Added §Secondary measurement. This is the better operationalization of the GP-061 claim.
4. **Criterion 6 penalizes modular arithmetic** — FIXED. Rubric criterion 6 rewritten from "No External Domain Import" to "No Shortcut By Named Import." Standard arithmetic operations (including remainders) are explicitly permitted. Only importing named external formulas/sequences without data-driven derivation is penalized. Rubric hash updated.
5. **Seed/temperature documentation** — ACCEPTED. Added to §Known limitations. Stochasticity biases toward null (conservative).
6. **Apparatus-hardening framing upfront** — ACCEPTED. Framing disclosure moved to top of document.

## CS fellow code review — CONDITIONAL PASS

CS fellow returned CONDITIONAL PASS (2026-04-16):

- All 45 data points verified against GT
- Sealed hashes match
- Gate harness, runner, EXTRA_ARGS quoting all correct
- Denylist gap for bare coefficients (7, 23, 100) noted as informational — too common for denylist without false positives
- No critical or blocking issues

## Go/no-go checklist

- [x] §Leak Audit — sentinel passed (38 patterns, 0 matches)
- [x] §Identifiability — uniquely determined (Vandermonde invertible mod 997, 30 >> 5 minimum)
- [x] §Smoke Gate — baseline returns wrong answers, harness correctly fails
- [x] §Charter Fingerprint — recorded, rubric re-hashed after criterion 6 + persona fix
- [x] Role separation (Division A/B) — M-form construction per GP-072 protocol
- [x] Philosopher critique — CONDITIONAL GO, all 6 conditions addressed
- [x] CS fellow code review — CONDITIONAL PASS, no blocking issues
- [x] Post-fix sentinel re-run — 38 patterns, 0 matches (3 passes: caught "remainders" on 2nd, clean on 3rd)
- [x] Manual conceptual audit — grep for modular/polynomial/cubic/prime/997/5000 across all mutator-visible files: CLEAN
- [x] Persona clause (c) aligned with criterion 6 — standard arithmetic operations explicitly permitted
- [ ] §Dry-run gate — run ITERS=4 treatment-only to confirm extractor activation before first formal pair
- [x] Operator seal with timestamp — **SEALED 2026-04-16 00:30 EDT**

---

## §Closure — MIS-CALIBRATED (2026-04-16)

**Status:** CLOSED — substrate mis-calibrated, experiment non-confirmatory.

### What happened

Pair 1 treatment arm, iteration 1: gemini-3.1-pro-preview recovered an equivalent GT `(7x^3 + 23x^2 + 100x + 15) % 997` with perfect fit (score 88, 30/30 exact match). Note: d=15 ≡ 5000 (mod 997), so this is the same function.

Attack path: Lagrange interpolation on x=0,1,2,3 (which produced unwrapped polynomial values since the wrapped values coincidentally equal the first differences of the polynomial). From the cubic, the mutator predicted y(4), compared against actual, computed 1231-234=997 = modulus. One-shot crack.

### Root cause

Despite all points wrapping (d=5000 > P=997), the cubic polynomial's growth rate means the first few y-values are determined by `(polynomial) mod 997`, and since the polynomial at x=0..3 yields values that happen to uniquely determine a cubic via Lagrange interpolation, the LLM can back-solve the polynomial and then compute the modulus from a single discrepancy. This is a fundamental mathematical property of polynomial-mod-prime substrates: the polynomial is always recoverable from its first (degree+1) evaluations, and the modulus is computable from one additional point.

### Finding: Modular Arithmetic is Dead as a Substrate Class

Any function of the form `f(x) = P(x) mod M` (polynomial mod integer) is trivially crackable by LLMs that know Lagrange interpolation + GCD. The polynomial is identifiable from its first (deg+1) points, and the modulus is computable from one wrapped point. No choice of polynomial degree, modulus size, or constant term can prevent this. This applies to ALL substrates in the modular arithmetic family.

### Lessons for sandbox_13v2

Abandon modular arithmetic entirely. The next substrate must use:
- **Entangled composition** where the Mod operator is INSIDE another function's argument (not additively separable)
- **Phase modulation**: `y = round(A * sin(w*x + (x % p)))` — the Mod shifts the sin's phase, making decomposition via residual analysis impossible
- Standard families (polynomial, trig, piecewise) must fail on visible data
- The Mod component must be structurally invisible until the extractor identifies it

