# GP-061 Phase 2 — Hinge Substrate Pre-Registration

> **Seam metadata** · `seam_id:` GP-061 · `track:` substrates · `status:` SEALED 2026-04-15 20:27 EDT (re-sealed after pre-launch catc · `last_updated:` 2026-05-08


**Status:** SEALED 2026-04-15 20:27 EDT (re-sealed after pre-launch catch: model pin corrected from `gemini` (flash) to `gemini-pro` to match parent GP-061 steering-AB precedent and all GP-023 sandbox precedents. No decisive data was recorded under the flash pin; the pair-1 flash launch was aborted at iter-0 completion before any pair classification row was written.). Any change to this document, the sealed-hash set, or the pair runner after this point invalidates the α=0.05 claim and reopens the run as exploratory.
**Draft date:** 2026-04-15
**Substrate:** `projects/gp061_sandbox_11_01/`
**Rubric:** `rubrics/gp061_sandbox_11_01.json` (`complexity_penalty_enabled: true`)
**Parent seam:** `GP-061_void_driven_steering_measurement_seam.md`
**Dependency cleared:** task #65 (BIC wired through `structural_memory.py` cross-family ranking, flag-gated)

> This file is private (under `research_areas/private/`) and is not mutator-visible. It is the only file that names the target shape, the sealed expected void slot, and the protocol. Nothing here may be copied into the charter, rubric, thesis, or evidence file.

## Claim under test

The `negative_space_extractor` void-injection channel changes the mutator's next-proposal distribution at a rate above chance, conditional on the scorer being non-trivially discriminating (here: BIC-penalized cross-family ranking under a hinge substrate).

This is the GP-061 core claim. Substrate has changed (GP-045 was criterion-driven and never exercised the measurement surface). The claim has not.

## Sealed ground truth (private, never copied into project dir)

`V_GT(t, R) = A * max(0, t - (t0 + t1 * R)) + B`

with
- `A = 2.0`
- `t0 = 0.30`
- `t1 = 0.40`
- `B = 0.50`
- noise σ = 0.005 additive, zero-mean

Visible grid: uniform `t` in [0, 1] at 21 points per sweep, R in {0.10, 0.30, 0.50, 0.70, 0.90}.
Holdout grid: 8 off-grid t-points per sweep at the same R values.

The piecewise-linear form is expressible in the default fit-primitive grammar via `(fabs(t - t_kink) + (t - t_kink))/2`. The mutator must discover this; it is not stated anywhere in any mutator-visible file.

## Protocol — paired A/B

Each "pair" is two autoresearch runs against the same fresh project copy, same rubric, same seed iteration, same mutator/judge models, differing only in whether `negative_space_extractor` is enabled.

- **Treatment arm (T):** default autoresearch_loop. Void injection enabled. Command in `run_treatment_run1.sh`.
- **Control arm (C):** `--disable-negative-space-extractor` flag passed. Same iteration count. Same rubric.

Per pair we record the **family fingerprint of the iteration-1 proposal** (first mutator output after the iteration-0 baseline is consumed and the residual surface + structural memory + extractor output are visible). Fingerprint comes from `structural_memory.build_structural_family_signature`, read from `workspace/structural_memory.json` after iteration 1 closes.

A pair is classified as:
- **Void-steered:** T and C produce different family fingerprints at iteration 1, AND T's fingerprint incorporates a primitive present in T's iteration-0 `workspace/derived_constraints.json` entry authored by `producer=negative_space_extractor` that is absent from iteration-0 residual cues alone.
- **Not steered:** T and C produce the same fingerprint at iteration 1.
- **Divergent but unattributable:** fingerprints differ but T's primitive does not trace back to the void ledger entry. Counted as "not steered" for the conservative one-sided test; separately logged for sensitivity analysis.

### Void artifact location — corrected

The `negative_space_extractor` does NOT write a standalone `void_proposal_iter_0.json`. It writes into the shared derived-constraints ledger at `workspace/derived_constraints.json` via `update_derived_constraints_ledger`, tagged with `producer=negative_space_extractor`. Pair classification reads from that ledger, filtering by producer and iteration.

## Pair classification — manual audit for pair 1, harness later

**No automated classifier exists yet.** For pair 1, classification is a manual operator audit:
1. After T run closes, read `projects/gp061_sandbox_11_01/workspace/structural_memory.json` and record the family fingerprint from the iteration-1 entry.
2. Read the iteration-1 `producer=negative_space_extractor` entry in `workspace/derived_constraints.json` and extract the void slot payload.
3. Read the iteration-1 mutator output for T (fit_declaration expression and thesis prose).
4. After C run closes (against a fresh copy), repeat step 1 for C.
5. Fill one row in `projects/gp061_sandbox_11_01/phase2_ab_results.jsonl` by hand with: pair_index, T fingerprint, C fingerprint, void slot payload, did T incorporate the void slot (yes/no/ambiguous), classification (void-steered / not steered / unattributable).

The jsonl file is operator-written. An automated classifier can be added after pair 1 once we see what the iter-1 artifacts actually look like; building it blind is premature.

## Sample size and stopping rule

- **N ≥ 10 pairs** before any test is run. No peeking between pairs; the classification row for each pair is committed before the next pair starts.
- If operator cost forces early termination, the run closes with the pre-registered test result at whatever N was reached, flagged as underpowered if N < 10. No continuation after looking.

## Test

One-sided exact binomial test. H0: p(void-steered pair) ≤ 0.5. H1: p > 0.5. α = 0.05.

- At N = 10, reject H0 if void-steered count ≥ 9 (exact one-sided p ≈ 0.0107).
- At N = 15, reject H0 if void-steered count ≥ 12 (exact one-sided p ≈ 0.0176).
- Record the exact threshold for whatever N the run actually reaches.

## Null result interpretation

Failure to reject is **not** "void injection does nothing." It is "under this substrate and this scorer, the proposal-distribution channel is not detectable at α = 0.05 with the power available." The extractor can still be useful as a debug instrument in the null case. A null result on this substrate triggers one more substrate attempt under a discrete-grader pilot (GP-069 seam §§ 127+), not another BIC patch. Two consecutive null substrates would be taken as weak falsifying evidence against the GP-061 claim in its current form.

## What this run is NOT

- Not a champion-search run. No promotion path matters; the binomial test is the only summary.
- Not a test of GP-069 tier-3 clearance. The substrate is only GP-069 level-1 cleared — the complexity-penalized scorer is sufficient to prevent the nesting-collapse pathology from hijacking the measurement surface at this level.
- Not a paper-4 claim on its own. Phase 2 resolves the "does void injection steer proposals above chance" question; any paper framing waits on the measurement outcome.

## Non-hidden out-of-scope

- Smuggled-parameter attacks (grid-scale smoothing floors, bandwidth constants, any constant that acts like a parameter but is not counted in `k`) are known BIC-blind-spots. If phase 2 closes positively but smooth-closure families dominate via smuggled parameters, the positive reading is preserved — we are measuring steering, not GP-069 tier-3. Smuggled-parameter detection remains a separate GP-069 track.
- Retroactive sandbox_09/10 audit is deferred as non-informative (winning families at residual ≈ 0; SSE dominates BIC regardless).

## §Leak Audit (PRE_RUN_CHECKLIST §1)

Target-specific denylist (applied in addition to the generic layer):

```
hinge            kink             piecewise        fabs
sigmoid          threshold        first.derivative ramp
max\(0           t_kink           t0.*t1           piecewise.linear
void             negative.space   GP-061           GP-045
GP-069           sandbox          phase.?2         void.steering
complexity.penalt BIC
```

Mutator-visible file set audited:

- `projects/gp061_sandbox_11_01/project_charter.md`
- `projects/gp061_sandbox_11_01/thesis.md`
- `projects/gp061_sandbox_11_01/test_model.py`
- `projects/gp061_sandbox_11_01/evidence.txt`
- `projects/gp061_sandbox_11_01/evidence_holdout.txt`
- `rubrics/gp061_sandbox_11_01.json`

**Grep output (2026-04-15, post-neutralization sweep):**

```
rubrics/gp061_sandbox_11_01.json:5:  "complexity_penalty_enabled": true,
rubrics/gp061_sandbox_11_01.json:15:    "7_No_External_Domain_Import": "... avoid importing ANY named model ..."
```

Two hits, both explained:
1. Line 5 — `complexity_penalty_enabled` is the rubric config key consumed by the scorer. Key name is generic ("penalize complexity"), does not encode GT form or family class. Required by the scorer loader; cannot be renamed without breaking the runtime.
2. Line 15 — benign substring: "a**void**" inside the word "avoid". No semantic leak.

Zero unexplained matches. §Leak Audit PASSED.

**Slug and rubric filename:** renamed 2026-04-15 from `gp061_hinge_phase2_01` → `gp061_sandbox_11_01` to comply with PRE_RUN_CHECKLIST §1 naming-leak rules. The original slug encoded the answer class (`hinge`) and framework meta-talk (`phase2`). The new slug is opaque and follows the `gp023_sandbox_NN` precedent. Both the project directory and the rubric filename were renamed; launch scripts and this pre-registration were updated accordingly.

## §Identifiability (PRE_RUN_CHECKLIST §3)

**Run 2026-04-15.** Script at `/tmp/identifiability_and_smoke_gp061_sandbox_11_01.py` (private, outside project dir). Parses `evidence.txt` (105 points, 5 sweeps × 21 t-points). Tolerance: 2% max relative error per parameter.

**1. Multi-start fit (25 random seeds, box A∈[0.1,5], t0∈[0,0.5], t1∈[0,1], B∈[0,1]):**
```
25/25 starts converged to within 2% rel of GT
best max-relative-error across all starts: 0.008773
best fit: A=2.0014 t0=0.3024 t1=0.3965 B=0.5012
GT      : A=2.0    t0=0.3    t1=0.4    B=0.5
```

**2. Pairwise bowl check (sweep each param around GT, others fixed):**
```
OK A : argmin=2.0000 gt=2.0
OK t0: argmin=0.3000 gt=0.3
OK t1: argmin=0.4000 gt=0.4
OK B : argmin=0.5000 gt=0.5
```
All four parameters have unique minima at GT.

**3. Jacobian column rank at GT:**
```
rank=4 (expected 4)
singular values: [17.77, 6.574, 3.662, 1.139]
```
Full column rank; smallest singular value 1.139, ratio to largest ≈ 0.064 — well-conditioned, no parameter collapse.

**4. Bootstrap (200 resamples with replacement):**
```
200/200 resamples converged
A : 95% CI = [1.9953, 2.0076], GT=2.0, GT_in_own_CI=True
t0: 95% CI = [0.3007, 0.3041], GT=0.3, GT_in_own_CI=False
t1: 95% CI = [0.3950, 0.3981], GT=0.4, GT_in_own_CI=False
B : 95% CI = [0.4998, 0.5028], GT=0.5, GT_in_own_CI=True
```
**No CI contains any neighbor parameter's GT value** — the checklist rule is satisfied. t0 and t1 own-CIs miss their own GT by 0.02% and 0.5% respectively, which is a small noise-induced point-estimate bias from the σ=0.005 noise concentrated in the kink transition region; it is not an identifiability failure.

**Verdict:** PASSED. Sealed hinge GT is uniquely recoverable from the visible slice.

## §Smoke Gate (PRE_RUN_CHECKLIST §5)

**Run 2026-04-15.** The charter has no deterministic gate block; smoke-gate analog is: baseline `test_model.V_model` produces finite predictions across the visible grid with visibly non-zero residuals on every sweep.

```
finite_ok: true
global_max_abs_residual: 1.81646
per-sweep max_abs_residual:
  R=0.1: 1.81646  (n=21, mean_abs=0.9448)
  R=0.3: 1.65695  (n=21, mean_abs=0.8475)
  R=0.5: 1.50093  (n=21, mean_abs=0.7639)
  R=0.7: 1.33477  (n=21, mean_abs=0.6888)
  R=0.9: 1.18732  (n=21, mean_abs=0.6298)
```
Baseline is `V_model(t, R) = 0.0` (neutral constant placeholder, no parameters, no form hint). Residuals are finite and large on every sweep; the iter-1 residual surface will therefore be informative.

**Verdict:** PASSED.

## §Charter Fingerprint (PRE_RUN_CHECKLIST §4)

**Recorded 2026-04-15 (post-neutralization).** SHA256 of all mutator-visible artifacts:

```
a292ec356d611fd9eea01b8e81115acc1dcd9e790e6de8273af9883a4721f360  projects/gp061_sandbox_11_01/project_charter.md
a51963448d467868eecf1e453ab6f5bee5cff6cf7e232214d451bb51d1a54642  projects/gp061_sandbox_11_01/evidence.txt
aecb8726f6d7314d25c0fcf0ab80a278cc5d637feb0242da3b3333b38f4632bc  projects/gp061_sandbox_11_01/evidence_holdout.txt
204499abc881f62f8eef89ebe225bbddeb15d5a42574dee74a028ba65b4a7708  projects/gp061_sandbox_11_01/thesis.md
3b9cca54f100963bbb5aef30c469f1a82eea43aab4ed0b8f5e6b608ff641dcc9  projects/gp061_sandbox_11_01/test_model.py
b922a678668634746d7be00e09686221b978a5fb45bb90f2205c38eaa7b25301  rubrics/gp061_sandbox_11_01.json
```

Any drift from these hashes at operator-seal time invalidates the pre-registration.

## §Sealed Command Dry-Run (PRE_RUN_CHECKLIST §6)

**Sealed command** (note: rubric argument is the stem, not a path — initial script draft used `rubrics/<name>.json` which `autoresearch_loop.py` would double-suffix):
```
make loop PROJECT=gp061_sandbox_11_01 RUBRIC=gp061_sandbox_11_01 ITERS=5 MODE=factory MUTATOR_MODEL=gemini-pro JUDGE_MODEL=gemini-pro
```

**Dry-run attempt 2026-04-15 — finding:** `ITERS=0` is NOT a free short-circuit. `autoresearch_loop.py:2508` is `for i in range(ITERATIONS)` — the post-loop is skipped, but iteration 0 (the baseline mutator proposal + judge cycle) runs unconditionally before the loop. An `ITERS=0` invocation therefore performs one full gemini mutator call + one full gemini judge call, writes `latest_eval_results`, `champion_eval_results`, `debate_log_iter_*.md`, `workspace/*.json`, and `history/`, and costs ≈ $0.006. This was executed once and the resulting artifacts have been purged; sealed hashes re-verified post-purge.

**Substitute dry-run check (accepted as §6 analog):** the identifiability + smoke-gate script at `/tmp/identifiability_and_smoke_gp061_sandbox_11_01.py` already exercises the rubric loader path (reads `evidence.txt`, confirms baseline `test_model.V_model` is importable and finite, verifies the sealed GT is recoverable from the visible slice). That covers everything a dry run would have caught short of a live gemini call, at zero API cost. Running `make loop ITERS=0` a second time would re-burn $0.006 and re-contaminate the project dir for no incremental signal.

**Incidental content signal from the destroyed iter-0 artifacts:** the dry-run's iteration-0 mutator proposal (seen only in the log; not pasted into any mutator-visible file) reached for a two-regime decomposition using `max(0, x)` with *quadratic* accumulation. This is in the hinge family but with wrong curvature relative to the sealed linear GT — reassuring that (a) the clean charter+evidence surface is solvable without any form leak, and (b) the exact GT form is not trivially obvious, so mid-run convergence remains a non-trivial measurement. No iter-0 content is carried forward; the reset between arms restores the canonical neutral `thesis.md` from `.baseline_thesis.md`.

**§6 verdict:** PASSED via substitute check. Any further "dry run" before pair 1 is wasteful; pair 1 itself is the next legitimate run.

## Go/no-go checklist

- [x] §Leak Audit grep executed with zero unexplained matches
- [x] §Identifiability protocol passed
- [x] §Smoke Gate equivalent passed
- [x] §Charter Fingerprint recorded
- [x] §Sealed Command dry-run passed (substitute: identifiability + smoke-gate script covers the loader path without burning a gemini call; see §Sealed Command Dry-Run note)
- [x] Slug rename executed (`gp061_sandbox_11_01`)
- [x] Strip test performed on charter, thesis, rubric persona (bounded B5 agent, 2026-04-15 — triggered thesis/test_model neutralization)
- [x] Operator seal with timestamp — **SEALED 2026-04-15 20:27 EDT (re-sealed after pre-launch catch: model pin corrected from `gemini` (flash) to `gemini-pro` to match parent GP-061 steering-AB precedent and all GP-023 sandbox precedents. No decisive data was recorded under the flash pin; the pair-1 flash launch was aborted at iter-0 completion before any pair classification row was written.)**

**All 8 checklist boxes PASSED. Pre-registration SEALED 2026-04-15 20:27 EDT (re-sealed after pre-launch catch: model pin corrected from `gemini` (flash) to `gemini-pro` to match parent GP-061 steering-AB precedent and all GP-023 sandbox precedents. No decisive data was recorded under the flash pin; the pair-1 flash launch was aborted at iter-0 completion before any pair classification row was written.).**

## Governance

- Any deviation from this document during the run is logged in the seam's "deviations" section and forfeits the α = 0.05 claim; the run re-closes as exploratory.
- Results land in `projects/gp061_sandbox_11_01/phase2_ab_results.jsonl` (at project dir root, NOT inside `workspace/` — the pair runner wipes `workspace/` between arms, so the results file must live where resets won't touch it). One row per pair, operator-written for pair 1, aggregated into a single summary commit at close.

## Early termination — 2026-04-16

**Closed at N=2 pairs. Flagged as underpowered per §Sample size and stopping rule.**

**Reason: substrate too well-determined for steering measurement.** Both pairs produced identical results: T and C converge to the same smooth-hinge family (V_base + slope/2 * (z + sqrt(z^2)), 4 parameters, rmse ~0.00492) at iteration 1. The negative_space_extractor ran in both treatment arms but emitted zero void slots — there are no failed families to mine because the evidence surface has a single dominant attractor that gemini-pro finds immediately. With no void signal produced, the steering mechanism has nothing to inject, and the experiment cannot distinguish T from C.

**Results:**

| Pair | T fp | C fp | Void entries | Classification |
|---|---|---|---|---|
| 1 | sfam:81bb03ce | sfam:4bee3876 | 0 | divergent but unattributable |
| 2 | sfam:4bee3876 | sfam:128fa52a | 0 | divergent but unattributable |

Both classified "divergent but unattributable" (fingerprints differ due to canonicalization aliasing in `build_structural_family_signature`, not real structural differences). Both count as "not steered" for the binomial test. Void-steered count: 0/2.

**Binomial test at N=2:** cannot reject H0 at any threshold. Result is uninformative, not negative — the instrument (negative_space_extractor) never activated, so the channel was never tested.

**Subsidiary findings:**
1. **Fingerprint canonicalization bug:** `build_structural_family_signature` does not normalize commutative constant placement (`P1 * CONST * expr` vs `P1 * expr / CONST` hash differently despite identical topology). This produces spurious fingerprint divergence. Not a steering finding — an instrumentation bug.
2. **Extractor activation condition:** the negative_space_extractor requires failed families in structural_memory.json to mine void slots from. On substrates where the GT family is found at iteration 1, no families fail, and the extractor returns None. The extractor's activation condition is "ambiguous family selection at iteration 1" — this substrate does not meet it.
3. **F-ATTACKER-EXFIL-01:** gemini-pro attacker filesystem scraping via execute_python_code discovered during pair-1 pre-launch and patched mid-session (tempdir sandbox + --disable_attacker_tools). Not a steering finding; documented separately in GP-049 Turn 16.

**Per §Null result interpretation:** this is the first null substrate. One more substrate attempt under a discrete-grader pilot (GP-069 seam) is warranted before taking weak falsifying evidence against the GP-061 claim. The next substrate must have ambiguous family selection at iteration 1 — a harder GT where multiple families compete.

**Total experiment cost:** ~$1.78 (2 pairs × ~$0.89/pair).
