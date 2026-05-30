# GP-133 — Meta-Law Hypothesis (MLH) Protocol: Perturbation-Invariance Across Number-Theoretic Substrates

## Status

Draft — awaiting principal sign-off and seam debate review

## Seam

research_areas/private/seams/mission/GP-133_multidisciplinary_discovery_panel_seam.md

## Scope

- Pre-registered protocol for testing whether perturbation-surviving forms share a common meta-law across diverse number-theoretic substrates
- Standard perturbation battery definition (which perturbations, applied how)
- Range-stability and coefficient-stability requirements per substrate
- Identification-horizon precondition (per-substrate gate before perturbation battery runs)
- Kill level for the meta-law claim
- g-function candidate families pre-committed before any substrate is run
- Substrate selection criteria and initial 5-substrate shortlist

**Out of scope:**
- Implementation of perturbation-as-gate in compress_champion (separate engineering task, GP-133 seam item 3)
- Phase C dark-data application (blocked on this protocol passing first)
- Changes to the existing gate harness or compress_champion scoring
- Formal proof / Lean lift of any discovered meta-law (Phase D, GP-088)

---

## Decision

Before claiming that ZTARE's perturbation battery can discover structural laws, the apparatus must pass a pre-registered validation: across 5 number-theoretic substrates with diverse multiplicative structures, the perturbation-surviving correction form F_S must be expressible as g(prime-density-signature of S) for a fixed simple g with parameter set of size ≤ 3. Each substrate must independently pass an identification-horizon check, a range-stability check, and a coefficient-stability check before its perturbation result contributes to the meta-law verdict. If the protocol fails, the apparatus is reclassified as a sophisticated rediscovery tool and the "close to discovery" claim is retired.

---

## Problem

The abundant-density perturbation experiment (2026-04-23) initially appeared to discriminate 1/log(n) from 1/n by showing a winner flip under the strip-p=2 perturbation. Subsequent range-sensitivity analysis revealed the flip was a small-n transient (vanishes at n ≥ 5000) and the Mertens coefficient ratio was wildly unstable (4.09 to −4.57 depending on fitting range). The substrate was below its identification horizon at n ≤ 10^5.

Without a pre-registered protocol specifying stability requirements, the positive result would have been published as a finding. The GP-133 panel unanimously rejected the claim and demanded a tightened protocol before any further interpretation.

**Root cause:** no pre-registration of what "structural invariance" requires beyond "the winner flips." The perturbation methodology is sound; the acceptance criteria were too loose.

---

## Why It Matters

If MLH passes: ZTARE has demonstrated meta-law-recovery capability — the ability to identify a shared generative mechanism across substrates, not just fit individual curves. This unlocks Phase C (prospective discovery on unknown-answer substrates) and transforms the apparatus from a curve-fitter into a candidate scientific instrument.

If MLH fails: the apparatus is correctly reclassified. No resources are wasted on Phase C dark-data runs that would produce "persuasive mathematically invalid artifacts" (Gemini's exact warning). The failure itself is informative — it tells us where the architectural ceiling is.

Either outcome is valuable. Running without the protocol is not.

---

## Constraints

1. **Pre-registration is binding.** All substrate choices, g-function candidates, stability thresholds, and the kill level must be committed before the first substrate is run. No post-hoc adjustment.
2. **Identification-horizon gate is mandatory per substrate.** A substrate enters the meta-law battery only if its correction-form coefficients are range-stable at the available n. If the horizon check fails, the substrate is excluded (not counted as a meta-law failure).
3. **No oracle access for the meta-law fit.** The g-function is fitted across substrates using only the perturbation-surviving forms; it is not informed by known analytic derivations of those forms.
4. **Existing ZTARE apparatus only.** The perturbation battery uses the current gate harness + compress_champion pipeline. No new fitting infrastructure is introduced for this protocol.
5. **Honest nulls count.** A substrate where the horizon check fails is documented as "horizon-blocked at n=X" — not discarded silently.

---

## Options

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Full 5-substrate MLH with 4-gate acceptance** | Run perturbation battery on 5 substrates. Each must pass: (i) horizon check, (ii) range-stability, (iii) coefficient-stability, (iv) theoretical-coefficient match where available. Then fit g across survivors. | Most rigorous. Pre-registered kill level. Catches the abundant-density false positive. | Requires 5 substrates with accessible identification horizons — may not all be feasible at n ≤ 10^6. | **Selected.** |
| **B — 3-substrate pilot before full MLH** | Run 2-3 substrates first as a pilot. If ≥2 pass the 4-gate, extend to 5. | Cheaper initial cost. Catches showstopper failures early. | Weaker statistical base for meta-law claim. Pilot-to-full transition introduces selection bias risk. | Viable as Phase 1 of Option A. |
| **C — Skip MLH, go directly to Phase C dark-data** | Pick an unknown-answer substrate and run perturbation battery without validation. | Fastest path to a "discovery" headline. | Exactly the failure mode the panel rejected. Would produce persuasive artifacts without validity. | **Rejected.** |

---

## Recommendation

Implement **Option A** with Option B as its first phase. Run 3 substrates first (Phase 1). If ≥2 pass all 4 gates and the g-fit residual is within bounds, extend to the full 5 (Phase 2). If <2 pass in Phase 1, the MLH is provisionally falsified and Phase C is blocked pending architectural review.

---

## Implementation

### 1. Substrate Selection (5 candidates, diverse multiplicative structure)

Pre-committed shortlist (ordered by expected identification-horizon accessibility):

| # | Substrate | Observable | Multiplicative structure | Expected horizon | Source |
|---|---|---|---|---|---|
| S1 | Squarefree density | q(n) = #{k ≤ n : k squarefree} / n | Möbius function μ(k) | ~10^4 (fast convergence to 6/π²) | Sieve |
| S2 | Totient summatory | Φ(n) = Σ_{k≤n} φ(k) / n² | Euler totient φ | ~10^4 | Sieve |
| S3 | Abundant density | z(n) = #{k ≤ n : σ(k) > 2k} / n | Divisor sum σ(k) | >10^5 (known from E-SURVEY-S1-03) | Sieve |
| S4 | Liouville summatory | L(n) = Σ_{k≤n} λ(k) / √n | Liouville λ(k) = (−1)^Ω(k) | ~10^4 | Sieve |
| S5 | Prime-counting correction | π(n) − li(n) | Prime indicator | ~10^5 | Sieve |

**Diversity check (R3, Tao):** S1 uses μ² (Möbius square), S2 uses φ (Euler totient), S3 uses σ threshold (divisor sum), S4 uses λ (Liouville — completely multiplicative), S5 uses the prime indicator (non-multiplicative). Five distinct multiplicative kernels. No two share the same Euler product skeleton.

**Substitution policy (R5, Kuhn):** if a substrate fails the horizon check at accessible n, it is excluded and replaced with the next candidate from the reserve list: divisor sum average D(n)/(n log n), partition function density (A000041-derived). **Maximum 2 substitutions total.** If 4+ candidates fail the horizon check, that is itself an informative result about the apparatus's operational range — report it, do not paper over it.

### 2. Standard Perturbation Battery (per substrate)

For each substrate, compute the observable on 4 populations:

| Population | Definition | What it tests |
|---|---|---|
| Base | All integers k ≤ n | Baseline |
| Odd-only | k odd | Strip p=2 contribution |
| No-p5 | k not divisible by 5 | Strip p=5 contribution |
| Squarefree-only | k squarefree | Remove higher prime powers |

For each population: fit `a + b/log(n)`, `a + b/n`, `a + b*exp(-c*n)` using curve_fit on the observable. Record: winning form, SSE ratio, fitted coefficients.

### 2b. Causal Identifiability Pre-Check (Gate 0) — R7, Pearl

**Definition:** Before running the perturbation battery, verify that the substrate's perturbation set produces at least 3 distinct predicted coefficient ratios across the 4 populations (base, odd-only, no-p5, squarefree). If the Euler product predictions are degenerate (all ratios cluster within ±5%), the substrate cannot distinguish g-function candidates regardless of n.

**Kill:** If fewer than 3 distinct predicted ratios exist, the substrate is uninformative for g-function discrimination. Exclude and document as "causally uninformative."

**Note:** For substrates where no theoretical prediction exists (S3, S5), Gate 0 passes vacuously — the perturbation battery is exploratory on those substrates.

### 3. Prediction-Stability Check (Gate i) — R1, Socrates/Feynman

**Definition:** A substrate passes the prediction-stability check if:
- The winning form is fitted independently on 3 non-overlapping sub-ranges (by equal-count split of sorted x-data)
- All 3 fitted models are evaluated on the FULL x-grid
- The maximum pairwise prediction disagreement ≤ 10% of max|y_data|

This tests whether the MODEL is stable (predictions agree), not whether the PARAMETERIZATION is identifiable. Parameters may drift (correction-term rank deficiency, per Ramanujan R8) while predictions remain stable — that is acceptable and informative but not a gate failure.

**Kill:** If max prediction disagreement > 10% of signal, the substrate is below its identification horizon. Exclude from MLH battery; document as "horizon-blocked."

**Threshold lock (R10, Popper):** The 10% prediction-stability threshold is pre-registered and locked before Phase 1. No post-hoc adjustment.

### 4. Range-Stability Check (Gate ii)

**Definition:** The perturbation-surviving form must be the same winner (by SSE ratio) on all 3 sub-ranges.

**Kill:** If the winner changes across sub-ranges, the result is range-unstable. Flag but do not exclude — report the instability in the per-substrate result.

### 5. Coefficient-Stability Check (Gate iii)

**Definition:** For the perturbation-surviving form, the ratio b_base / b_perturbed must be stable across the 3 sub-ranges to within ±30%.

**Kill:** If the ratio drifts by > 30% across ranges (as the abundant-density ratio drifted from 4.09 to −4.57), the coefficient is not identified. The substrate contributes a null to the MLH battery.

**Note:** Parameter-level drift is reported as a diagnostic (rank deficiency count) even when predictions are stable. This information feeds Ramanujan's R8 and R9 analyses.

### 6. Theoretical-Coefficient Verification (Gate iv, where applicable)

**Definition (R4, Gauss):** For substrates where a theoretical prediction exists for the ratio b_base / b_perturbed (e.g., Euler product factor p/(p-1) or p²/(p²-1) depending on kernel), the observed ratio must match within ±5% at n ≥ 10⁶. The Euler product predictions are exact theorems, not approximations — generous tolerances mask failures.

**Kill:** If mismatch > 5%, the form is empirically correct but not derivationally confirmed. The substrate contributes to the MLH g-fit with a "non-derived" flag.

### 7. Meta-Law g-Fit (across substrates)

After all substrates are processed:

**Input:** For each substrate S_i that passed Gates i-iii: the surviving form F_i and its fitted coefficients under each perturbation.

**Pre-committed g-function candidates (R2, Tao/Gauss):**

| g family | Expression | Parameters | Applies to |
|---|---|---|---|
| g1 | b = α · log(p_stripped) | 1 (α) | General |
| g2 | b = α · p/(p−1) | 1 (α) | Totient-type (linear Euler factor) |
| g3 | b = α · p/(p−1) + β | 2 (α, β) | General with offset |
| g4 | b_ratio = p/(p−1) exactly | 0 (parameter-free) | Functions with (1−1/p)⁻¹ local factor |
| g5 | b_ratio = p²/(p²−1) exactly | 0 (parameter-free) | μ²-based (quadratic Euler factor) |
| g6 | b_ratio = p/(p+1) | 0 (parameter-free) | Composite φ·μ interaction |

**Fit:** For each g family, fit across the (substrate, perturbation) pairs. Report residual variance.

**Accept threshold:** Cross-substrate residual ≤ 15% of within-substrate residual for the best g family.

### 8. Prediction-Before-Observation Test (conditional on MLH pass)

If MLH passes on ≥3 substrates:
1. Select a 6th substrate not in the training set (e.g., an OEIS sequence from GP-077 with weak analytic prior)
2. Use the fitted g to PREDICT F_S6 before running the apparatus
3. Lock the prediction
4. Run the apparatus + perturbation battery on S6
5. Compare predicted vs observed F_S6

This is the Ramanujan/Kuhn criterion: prediction-before-observation is the test that converts "rediscovery" into "discovery."

---

### 9. Pre-Specified Euler Product Predictions (R9, Ramanujan)

Before running the perturbation battery, pre-specify the theoretical coefficient ratio for each (substrate, perturbation) pair based on the Euler product structure. The meta-law search targets the RESIDUAL from these predictions, not the predictions themselves.

| Substrate | Strip p=2 | Strip p=5 | Squarefree restriction |
|---|---|---|---|
| S1 (squarefree, μ²) | p²/(p²−1) = 4/3 | 25/24 | N/A (already squarefree) |
| S2 (totient, φ) | p/(p−1) = 2 | 5/4 | No closed form |
| S3 (abundant, σ threshold) | Unknown (non-linear threshold) | Unknown | Unknown |
| S4 (Liouville, λ) | Symmetric ±1 — ratio depends on parity structure | TBD | N/A |
| S5 (prime-counting) | Non-multiplicative — no Euler product prediction | N/A | N/A |

Substrates S3-S5 have no clean Euler product prediction. If the perturbation battery finds a stable ratio on these substrates that MATCHES a ratio from S1-S2, that is the Newtonian signal. If each substrate produces an idiosyncratic ratio, there is no meta-law.

---

## Kill Level (pre-registered)

> On the first 3 substrates that pass the prediction-stability check (Gate i): if the perturbation battery does NOT produce prediction-stable, coefficient-stable surviving forms on at least 2 of the 3, the MLH is falsified and the "close to discovery-class instrument" claim is retired. The perturbation-as-gate remains as instrument hygiene; the meta-law claim is dropped.
>
> **Escalation path (R6, Kuhn):** If Phase 1 fails, the principal may re-run once at 10× n. If it fails again, falsification is final and the claim is retired for 12 months.
>
> **Phase C time-bound (R6, Kuhn):** If MLH passes, the prediction-before-observation test (Section 8) must begin within 14 days. No further validation substrates. The telescope must be pointed at the sky.

---

## Open Questions

1. **Can S1 (squarefree density) serve as a positive control?** Its asymptotic correction is well-known (6/π² with explicit error terms). If the perturbation battery can't recover it cleanly, the protocol has a calibration failure.
2. **Is n = 10^6 computationally feasible for all 5 substrates?** Sieve computation for σ(k) at n = 10^6 takes ~minutes. At n = 10^7, ~hours. The protocol should run at n = 10^6 first and extend only if horizon checks require it.
3. **Should the LLM mutator be involved at all?** The perturbation battery is fully deterministic (sieve + curve_fit). The LLM adds value only if the surviving form is outside the pre-committed candidate set.
4. **How does this protocol interact with GP-096 Phase C?** Phase C substrate selection is blocked until MLH Phase 1 passes. If MLH fails, Phase C is redesigned.

---

## Timeline

- **Phase 1 (3 substrates):** 1-2 days. Sieve computation + perturbation battery + 4-gate checks. Principal reviews results.
- **Phase 2 (extend to 5):** 1 day conditional on Phase 1 passing.
- **Prediction test:** 1 day conditional on Phase 2 passing.
- **Total if all gates pass:** ~4 days.
- **Total if Phase 1 fails:** 1-2 days + architectural review.

---

<!-- SPEC_DRAFTED 2026-04-23 from GP-133 seam Round 3 convergence -->
<!-- SPEC_REVISED 2026-04-23 from GP-133 seam Round 4 debate (R1-R10):
     R1: prediction-stability replaces parameter-stability
     R2: g5 (p²/(p²-1)) and g6 (p/(p+1)) added
     R3: S4→Liouville, S5→prime-counting (independent kernels)
     R4: Gate iv tolerance ±20%→±5%
     R5: substitution cap = 2
     R6: Phase C time-bound = 14 days post-MLH-pass
     R7: Gate 0 (causal identifiability pre-check) added
     R9: Euler product predictions pre-specified per substrate
     R10: all thresholds locked before Phase 1
-->
