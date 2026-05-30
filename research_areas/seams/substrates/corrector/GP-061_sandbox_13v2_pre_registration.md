# GP-061 Phase 2 — Phase-Modulated Sin Substrate Pre-Registration (v2)

> **Seam metadata** · `seam_id:` GP-061 · `track:` substrates · `status:` OPENED 2026-04-16 (dry-run findings). RESEALED 2026-04-16. · `last_updated:` 2026-05-08


**Status:** OPENED 2026-04-16 (dry-run findings). RESEALED 2026-04-16.
**Draft date:** 2026-04-16
**Substrate:** `projects/gp069_sandbox_13/`
**Rubric:** `rubrics/gp069_sandbox_13.json` (`fit_score_mode: "discrete_exact"`)
**Parent seam:** `GP-061_void_driven_steering_measurement_seam.md`
**Predecessors:**
- `GP-061_sandbox_11_01_pre_registration.md` (closed N=2, underpowered — extractor never activated, single-attractor GT)
- `GP-061_sandbox_12_pre_registration.md` (closed MIS-CALIBRATED — GT found iter 1, extractor never activated)
- `GP-061_sandbox_13_pre_registration.md` (closed MIS-CALIBRATED — v1 cubic-mod-997 cracked iter 1 via Lagrange+GCD)

> **Framing disclosure:** This is an apparatus-hardening experiment. It tests whether a specific component (the negative_space_extractor) measurably changes the mutator's proposal distribution under controlled conditions. It is NOT a test of whether ZTARE can generate new science. The substrate is operator-engineered to force the extractor to activate. A positive result means "the steering mechanism works when the cage is built correctly," not "the engine can discover unknown truths." See §Null result interpretation for the honest interpretation of all outcomes.

> This file is private (under `research_areas/private/`). It is the only file that names the target shape, the sealed expected void slot, and the protocol. Nothing here may be copied into the charter, rubric, thesis, or evidence file.

## Claim under test

Same as all prior sandbox iterations: the `negative_space_extractor` void-injection channel changes the mutator's next-proposal distribution at a rate above chance, conditional on the scorer being non-trivially discriminating.

Sandbox_11 was inconclusive (single-attractor). Sandbox_12 and sandbox_13v1 were both mis-calibrated (GT found at iteration 1). This substrate is designed to prevent iteration-1 solves through entangled composition that defeats both pattern recognition and algebraic decomposition.

## Why phase-modulated sin

Three prior substrates burned because the correct functional family was immediately recognizable:
- Sandbox_11 (hinge): standard ML pattern
- Sandbox_12 (mod 13): period visible in data
- Sandbox_13v1 (cubic mod 997): Lagrange+GCD one-shot crack — ANY polynomial-mod-integer is trivially solvable

**Finding from v1:** Modular arithmetic as a substrate class is dead. Polynomial mod integer is always crackable via Lagrange interpolation on the first (degree+1) points, then modulus from one discrepancy.

This substrate addresses the failure mode fundamentally:

1. **Entangled composition.** The Mod operator is INSIDE the sin argument: `sin(0.3*x + (x % 7))`. This is not additively separable — subtracting the best sin fit does NOT reveal a clean `(x%7)` sawtooth. Residual analysis fails because the mod shifts the sin's phase, not its amplitude.

2. **No standard family fits.** Best polynomial fit on visible data: 0/30 (any degree). Best `A*sin(w*x+phi)` fit: 7/30. No combination of standard families achieves meaningful exact matches.

3. **Output range hints at trig but not mod.** Values span [-100, 100] — consistent with `A*sin(...)` with A=100. A mutator may try trig early, but pure trig with constant phase cannot fit the data. The phase modulation by `(x%7)` is invisible until mod is tried inside the sin argument.

4. **Multi-step solution required.** The mutator must: (a) recognize trig-like output range, (b) try standard sin fits and fail, (c) hypothesize a non-constant phase term, (d) discover the phase is `(x % 7)` specifically. Steps (c) and (d) are non-trivial and require structural insight the extractor can provide.

## Sealed ground truth (private, never copied into project dir)

`y = round(100 * sin(0.3 * x + (x % 7)))`

with:
- Amplitude: A = 100
- Angular frequency: w = 0.3
- Phase modulus: P = 7
- Domain: x in {0, 1, ..., 44}
- Visible output range: [-100, 100] (25 of 30 unique values)
- 13 of 30 visible points are negative
- No noise — deterministic (rounded to nearest integer)

Visible grid: 30 of 45 points (x in [0, 29]).
Holdout grid: 15 points (x in [30, 44]).

Generator: `/tmp/division_a_sandbox_13v2_generate.py` (outside repo, never committed).

## Calibration analysis

| Family | Best exact match on visible (30 pts) | Notes |
|---|---|---|
| Polynomial (any degree) | 0-1/30 | Even deg-15 gets ≤1 match |
| sin(w*x + phi) | 7/30 | Best at w=1.3, phi=-2.15. Far from GT w=0.3 |
| Piecewise linear | 0-2/30 | Non-monotone, no clean breakpoints |
| Exponential | 0/30 | Negatives in data rule out simple exp |
| Lookup table | 30/30 | But fails holdout (no generalization) |

The critical property: **best sin fit achieves only 7/30**, well below the 23% threshold. The mutator will try trig (output range [-100,100] suggests it) but pure trig fails. The path from "it looks like sin" to "sin with modular phase" requires multiple failed attempts and structural insight.

## Extractor expected void

The `_GENERALIZED_OPS` vocabulary: `{Pow, Mult, Div, Add, Sub, USub, Mod}`.

After 3+ failed families (polynomial, simple trig, piecewise), all will use subsets of `{Pow, Mult, Add, Sub, USub}`. None will use `Mod`. The extractor will identify `has_op:Mod` as absent from all attempted families — the void.

## Role separation (Division A / Division B)

Constructed under M-form information isolation (same protocol as sandbox_12, per GP-072):

- **Division A (Lab Tech):** Knows GT. Generated evidence files via `/tmp/division_a_sandbox_13v2_generate.py` (outside repo, never committed).
- **Division B (Principal Investigator):** GT-blind agent. Wrote project_charter.md, rubric, thesis.md, test_model.py, gate_harness.py with zero GT knowledge. Briefed only as: "integer-valued function, exact match scoring."
- **Sentinel gate:** Automated leak detection (`src/ztare/validator/leak_sentinel.py`) with 31 denylist patterns. Result: 0 matches.

## Protocol — paired A/B

Each "pair" is two autoresearch runs against the same fresh project copy, same rubric, same seed iteration, same mutator/judge models, differing only in whether `negative_space_extractor` is enabled.

- **Treatment arm (T):** default autoresearch_loop. Void injection enabled.
- **Control arm (C):** `--disable-negative-space-extractor` flag. Same iteration count. Same rubric.

### Measurement point

Per pair, record:

1. **Extractor activation iteration (T arm only):** the first iteration where `workspace/derived_constraints.json` contains an entry with `producer=structural_extractor`. If the extractor never activates across all iterations, the pair is classified "extractor_inactive" and excluded from the binomial test (but reported separately).

2. **Family fingerprint at iteration N+1** (where N = extractor activation iteration): the `structural_memory.build_structural_family_signature` fingerprint of the proposal at the first iteration AFTER the void was injected. Compare T's fingerprint at N+1 against C's fingerprint at the same iteration index.

3. **Mod operator presence:** does the T arm's iteration-N+1 proposal contain `ast.Mod` in its AST? Does C's at the same iteration?

A pair is classified as:
- **Void-steered:** T and C produce different family fingerprints at iteration N+1, AND T's fingerprint incorporates `Mod` (or a structurally equivalent operation) present in T's void slot that is absent from C's proposal at the same iteration.
- **Not steered:** T and C produce the same fingerprint at iteration N+1, OR both contain `Mod` at the same iteration (data-driven discovery, not void-driven).
- **Divergent but unattributable:** fingerprints differ but the Mod presence doesn't trace to the void. Counted as "not steered" for the conservative test; logged for sensitivity analysis.
- **Extractor inactive:** extractor never fired in T arm. Excluded from binomial test; reported as calibration signal.

## Secondary measurement: proposal-shift

At each iteration after the extractor fires (N+1, N+2, ...), record whether the treatment arm's proposal AST contains `ast.Mod` and whether the control arm's proposal at the same iteration contains `ast.Mod`. A pair is classified as:
- **Mod-shifted:** T contains `ast.Mod` at iteration N+1, C does not at the same iteration.
- **Not shifted:** Both or neither contain `ast.Mod` at the same iteration.

One-sided exact binomial test on Mod-shifted rate. H0: p(Mod-shifted) ≤ 0.5. α = 0.05.

## Known limitations

### Output-range information leak

The visible data has outputs in [-100, 100]. An LLM may recognize this as consistent with `A*sin(...)` with A=100. This could lead both arms to try trig early. The paired design controls for this (both arms see the same data), but it means the mutator may attempt trig from data alone, without the extractor's help. The key: even if both arms try trig, pure `sin(w*x+phi)` gets only 7/30. The void-steered advantage is in discovering *modular phase*, not trig itself.

### Temperature and seed control

The autoresearch_loop uses the Gemini API's default temperature. No explicit random seed is set across arms. Stochasticity adds noise but biases toward the null, not toward false positives.

### Substrate difficulty uncertainty

This is the fourth substrate attempt. Phase-modulated sin is harder than all predecessors, but we cannot guarantee it won't be solved at iteration 1. If both arms solve at iteration 1 again, the substrate class choice needs fundamental rethinking. The dry-run gate (below) mitigates this.

## Sample size and stopping rule

- **N ≥ 8 pairs** before any test is run. No peeking between pairs; the classification row for each pair is committed before the next pair starts.
- If operator cost forces early termination, the run closes with the pre-registered test result at whatever N was reached, flagged as underpowered if N < 8.
- If ≥2 consecutive pairs are classified "extractor_inactive," the substrate is declared mis-calibrated and the run closes as exploratory (not confirmatory).

## Test

One-sided exact binomial test. H0: p(void-steered pair) ≤ 0.5. H1: p > 0.5. α = 0.05.

- At N = 8, reject H0 if void-steered count ≥ 7 (exact one-sided p ≈ 0.0352).
- At N = 10, reject H0 if void-steered count ≥ 9 (exact one-sided p ≈ 0.0107).

## §Leak Audit

### Denylist (Division A authored, 31 patterns)

```
\bmod\b             modular          modulo           remainder
periodic            cyclic           \bperiod\b       \bphase\b
sinusoidal          oscillat         \bsin\b          \bcos\b
trigonometric       \btrig\b         ground.truth     \bGT\b
\bsealed\b          pre.reg          division.a       lab.tech
\bGP-069\b          \bGP-061\b       \bsandbox\b      \bvoid\b
negative.space      \bsteering\b     \bwrap\b         wrapped
\b0\.3\b            \b100\s*\*       entangle
```

### Sentinel result

```
SENTINEL PASSED — 31 patterns, 0 matches
```

Mutator-visible file set audited:
- `projects/gp069_sandbox_13/project_charter.md`
- `projects/gp069_sandbox_13/thesis.md`
- `projects/gp069_sandbox_13/test_model.py`
- `projects/gp069_sandbox_13/evidence.txt`
- `rubrics/gp069_sandbox_13.json`

## §Identifiability

The function `round(100 * sin(0.3*x + (x % 7)))` with 3 parameters (A=100, w=0.3, P=7) is uniquely determined by the data:
- The parameter space is finite and small (A, w, P are all small integers/rationals).
- 30 visible points massively overdetermine 3 unknowns.
- No degenerate solutions exist: the entangled phase modulation produces a unique pattern.

## §Charter Fingerprint

```
6171ba99e0f7385d98321107837cc06951a999b5a61d1c931b1e1e3565e55bea  projects/gp069_sandbox_13/project_charter.md
de8da07c4f08f0f2dfeb36caedba2e75bf44c05b0fcef8c9eb1b673152b01263  projects/gp069_sandbox_13/evidence.txt
a333b6c12b457ad6fc56cb77c56344d6221aabe1025b600fec496c8f8f550e35  projects/gp069_sandbox_13/evidence_holdout.txt
899a4d8f6513f0dcc7506e0731bec2ab39b67f51d846812b3cdc2fe7181b0bc7  projects/gp069_sandbox_13/test_model.py
60b381372889e6632fbf635e5e9b65a78f9f97bc3b81f55d3208309e17c6ada3  rubrics/gp069_sandbox_13.json
c8858019b915743026c29f78bddc3434cbf9ec5ef0c995fa0d85b63e9705ff3b  projects/gp069_sandbox_13/gate_harness.py
```

## §Smoke Gate

Baseline `test_model.py` returns `f_model(x) = 0` for all x. Gate harness reports 0/15 holdout matches (harness_ok=false). Smoke test passed: f_model is callable and returns int.

## §Sealed Command

```
PAIR=1 bash projects/gp069_sandbox_13/run_pair.sh
```

ITERS=12, MUTATOR_MODEL=gemini-pro, JUDGE_MODEL=gpt4.1.

Judge model updated from `gemini` to `gpt4.1` after dry-run: Gemini judge produced zombie TCP connections on 2 of 3 long Gemini Pro iterations (>300s). GPT-4.1 judge averaged 17s with equivalent scoring quality. ITERS raised from 10 to 12 based on finding that PC-008 void injection requires additional iterations for Gemini Pro to act on the hint.

## §Dry-Run Findings (2026-04-16)

**Run:** 6 iters, gemini-pro mutator / gpt4.1 judge, `rubrics/gp069_sandbox_13.json`.

### What worked
- **Extractor activated.** Structural memory populated with 5 families across 6 iters (2 polynomial, 3 trig). Extractor never fired in prior sandboxes — this is the first confirmed activation.
- **PC-008 void injection correct.** The negative_space_extractor generated `sin(arg0|has_op:Mod)` as the unexplored structural slot. This is exactly the GT component (`x % 7` inside the sin argument). The instrument identified the gap autonomously.
- **Family progression.** Mutator navigated from polynomial (iters 1, 3) to trig (iters 4, 5, 6) under judge pressure. Correct directional movement.
- **Judge quality.** GPT-4.1 judge correctly diagnosed each iteration's structural failure, including naming "modular pseudo-periodic functions" explicitly in iter 4 feedback.

### Instrument bugs found and fixed

**Bug 1 — Expression grammar rejected bare trig calls.**
`fit_primitive.py` `_ALLOWED_DIRECT_CALLS` only contained `{"eml"}`. Gemini Pro's iter 2 expression `100 * sin(A * x + B * floor(x / 7))` — structurally equivalent to the GT — was rejected with `"Direct call 'sin()' not allowed here."` The mutator regressed to polynomial in iter 3.
**Fix:** Added `sin, cos, tan, asin, acos, atan, atan2, sinh, cosh, tanh, exp, log, log10, log2, sqrt, floor, ceil, fabs, abs, round` to `_ALLOWED_DIRECT_CALLS`. Applied to `src/ztare/validator/fit_primitive.py`.

**Bug 2 — Lagrange interpolator held champion via unit test gaming.**
A degree-3 polynomial (exact Lagrange interpolation) scored 32 and held champion for all 6 iters, because it passes all unit tests by construction. Trig approaches (18-22) scored lower despite being structurally closer to the GT, because continuous trig without the `% 7` term fails exact integer matching. Champion score was not a quality signal — it was a memorization artifact.
**Fix:** Added explicit penalty to `rubrics/gp069_sandbox_13.json`: a polynomial of degree ≥ N-2 (where N = evidence count) scores 0 on criterion 4 (Generalization_To_Holdout) by definition.

### What the dry-run does not resolve
- **Gemini Pro did not act on PC-008.** The void hint (`sin(Mod)`) was injected but Gemini Pro explored wider Fourier families (more sin/cos terms) rather than adding the `Mod` operator. This may require more iterations or stronger void-injection prompt language. The formal pairs at 12 iters will test whether the additional iterations change this.
- **No control arm.** The dry-run had no `--disable-negative-space-extractor` arm. Cannot attribute any family shift to void injection vs. judge feedback vs. data alone. The paired A/B design in the formal protocol remains the only valid test.

### Calibration verdict
Substrate confirmed calibrated. Extractor activates. Grammar and scoring fixes applied. Proceed to formal pairs.

## Null result interpretation

If sandbox_13v2 is the first substrate where the extractor activates:
- **Reject H0:** "Under controlled conditions with a sufficiently ambiguous substrate, the void-steering mechanism changes the mutator's proposal distribution." Apparatus-hardening result only.
- **Fail to reject:** "Even when the extractor fires, its output does not measurably change the mutator's next proposal." Evidence against the GP-061 claim in its current form.
- **Extractor inactive again:** Fourth mis-calibration. GP-061 claim suspended pending fundamental redesign.
- **Solved at iteration 1 (both arms):** Phase-modulated sin is also too easy. Must escalate to higher-dimensional or non-analytic substrates.

## Go/no-go checklist

- [x] §Leak Audit — sentinel passed (31 patterns, 0 matches)
- [x] §Identifiability — uniquely determined (3 params, 30 data points)
- [x] §Smoke Gate — baseline returns wrong answers, harness correctly fails
- [x] §Charter Fingerprint — recorded with v2 charter hash (non-negative constraint removed)
- [x] Role separation (Division A/B) — M-form construction per GP-072 protocol
- [x] Charter factual accuracy — output range [-100, 100] consistent with "The output is always an integer"
- [x] Denylist covers v2 GT terms — sin, cos, trig, phase, 0.3, 100*, mod, entangle all denied
- [x] No stale v1 artifacts — workspace, history, debate logs, eval results all cleared
- [x] §Dry-run gate — COMPLETED 2026-04-16 (6-iter treatment-only run, gemini-pro/gpt4.1). See §Dry-Run Findings.
- [x] Operator seal with timestamp — **RESEALED 2026-04-16**
