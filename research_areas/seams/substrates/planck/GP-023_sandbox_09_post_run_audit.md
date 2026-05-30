# Sandbox_09 v2 — Post-Run Audit

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` CLOSED 2026-04-15 - · `last_updated:` 2026-05-08


**Status:** CLOSED 2026-04-15 — **Outcome D (apparatus — harvest under-convergence)**.
**Pre-reg:** `GP-023_sandbox_09_pre_registration.md` (v2, §A1 amendment).
**Operator-stop:** iter 3, run_id 1776258959.

**Revision note (2026-04-15 late):** First closure draft labeled this Outcome C. Corrected to D after re-reading §7 verdict tree: §D triggers on harvest under-convergence, which is exactly what happened (3 families at operator-stop, below the §5 threshold of 5 by iter 15). §C requires the cold-run to surface a bad void slot, which never fired because the cold step was never reached. §D is the cleaner label. §A is unreachable because its second conjunct (cold-run void surfacing) cannot be satisfied when the harvest is empty, even though the first conjunct (gate clearance) holds. The correction does not change the follow-up actions — Component B returns to open, sandbox_10 is next — but it maps to the sealed decision tree correctly.

---

## 1. Run timeline

| Run | Iter | Score | Gate fails | Disposition |
|---|---|---|---|---|
| 1776257539 | 1 | 50 | 3 (farther_tail_global, farther_tail_R_mid, farther_tail_R_max) | operator_stop |
| 1776258959 | 1 | 100 | 0 | champion_promoted |
| 1776258959 | 2 | 75 | 0 | not promoted |
| 1776258959 | 3 | 0 | 0 (self-reference) | not promoted, operator_stop |

Only 3 distinct structural-memory families harvested. Far below the §5 harvest-stress threshold of 5 families by iter 15, but the run was stopped early and the replay rule never engaged.

---

## 2. Champion analysis — the iter-1 score-100 artifact

**Declared form (champion_eval_results.json):**

```
V(t,R) = 0.14
       + Amplitude_ref * exp( (base + factor*log R) * log R )
       * ( 1 - exp( -Rate_ref * exp(rate_exp * log R) * t ) )
```

**Fitted parameters:**

| Parameter | Fitted | Symbolic meaning if ≈ null | Sealed GT value |
|---|---|---|---|
| `Amplitude_ref` | 0.94995 | = V_inf if base=factor=0 | V_inf = 0.95 |
| `R_amplitude_exp_base` | 2.28e-05 | → 0 | — |
| `R_amplitude_exp_factor` | -2.06e-06 | → 0 | — |
| `Rate_ref` | 1219.43 | = 1/C if rate_exp = -1 | 1/C = 1219.51 |
| `R_rate_exponent` | -0.99999 | → -1 | — |

**Numerical collapse.** Under the fitted parameters, the R-dependent amplitude multiplier `exp((base+factor·log R)·log R)` reduces to `exp(≈0)` = 1 for every R in the sweep, and the R-dependent rate `Rate_ref · exp(rate_exp · log R)` reduces to `1219.43 / R`. Substituting:

```
V(t,R) ≈ 0.14 + 0.9500 * 1 * (1 - exp(-1219.43 * t / R))
       ≈ 0.14 + 0.95 * (1 - exp(-t / (R * 0.00082)))
       = sealed GT.
```

`max_abs_residual = 4.3e-7`. The champion is, to 4 significant figures, the sealed RC step response.

**Reading.** The mutator did not propose the RC form symbolically. It proposed a strict five-parameter generalization that **nests** RC, and the fit primitive drove the two extra exponents to their null values. The generalization collapsed to the specialization as soon as the least-squares loss hit the identifiable minimum.

**This is a capability signal, not a gate miss.** The extra exponents did not drift to game the gates — `factor=-2e-6` and `base=2e-5` are numerical zeros, not adversarial values. The champion is, on fitted parameters, genuinely the sealed GT. `gemini-2.5-flash` (confirmed via `iteration_telemetry.jsonl` `mutator_model_id`) recovered the RC step response on a blinded grid where no sweep reaches the ceiling (`t_max < τ_min` by construction — see §A1.2 rise-fraction table: 1.0% to 62.3% of the way up across sweeps). The symbolic regression capability on first-order transient curvature is real and worth recording as an independent observation. **It is not, however, the claim the pre-reg was written to adjudicate.**

## 3. Why the v2 grid amendment did not prevent this

v1 was aborted because the mutator read `V_inf` directly off the plateau (`t=1.6` was in saturation for the fast-R sweeps). v2 amended the grid so `t_max < τ_min` — no sweep reaches the ceiling. The §A1.5 identifiability protocol confirmed `cond(J) = 4.76e3` and per-parameter SE < 10% under typical lab noise, which was the signal that the grid is still well-conditioned for the sealed parameters.

**That signal was the problem.** The v2 protocol's "grid is identifiable" verdict is logically equivalent to "any sufficiently expressive family that nests RC will have a fit_primitive capable of recovering the RC specialization within it." v2 fixed the *direct-read* leak (V_inf no longer visible on an asymptote) but did not — and could not — prevent the *fit-time* collapse.

The two design goals are in tension on this sandbox:

- **Identifiable grid.** Required so the `fit_contract` gate can discriminate; required so §A1.5 clears.
- **Failed-family harvest.** Required so the negative-space extractor has failed fingerprints to cold-run against.

On an identifiable grid, any nested generalization of the GT is fit-collapsible to the GT. On a non-identifiable grid, §A1.5 cannot pass.

## 4. Verdict under §7 decision tree

Mapping to the sealed verdict criterion (pre-reg §7):

- **Outcome A (clean capability)** requires champion clears all 9 gates **and** the cold-run void set contains `fn:exp|arg0|has_op:Div` **and** no Planck-vocabulary residue **and** every surfaced void is grep-verifiable. Champion clears gates (first conjunct) but the cold-run was never invoked (second conjunct unreachable — operator-stop at iter 3, harvest empty, cold step never fired). **Outcome A is therefore not satisfied on the sealed decision tree.** It would be a protocol violation to promote on the first conjunct alone; the cold-run conjunct is the decisive half of the sealed claim, and sealing it was the whole point of pre-registering §6 and §7 before the run.
- **Outcome B (failed harvest, honest voids)** requires champion does not clear gates. Champion cleared. Not B.
- **Outcome C (mixed verdict)** requires the cold-run to surface a non-grep-verifiable or Planck-residue slot. Cold-run never fired. **Not C.**
- **Outcome D (apparatus failure)** fires on harvest under-convergence. §5 harvest-stress rule: "if at iteration 15 fewer than 5 distinct failed families exist in harvested structural memory, tighten every gate threshold by 3× and replay. Max 2 replays. Third under-harvest → Outcome D (retire)." We stopped at iter 3 with 3 families — operator-stop short-circuited the §5 replay mechanism, but the trajectory was unambiguously under-converging (iter 1 scored 100, meaning the mutator had already recovered the GT structurally; subsequent iterations were thesis iterations against an already-correct champion, not re-exploration of wrong families). The replay-and-tighten mechanism would not have changed that: gate-tightening does not force a mutator that has already found the GT to abandon it. §5 prescribes D for this trajectory.

**Closure.** **Outcome D (apparatus — harvest under-convergence)**. Sandbox_09 retires as a harvest substrate for Component B. Sandbox_10 (Kepler) is promoted to the active test of GP-061 Component B cross-grammar generalization, per §7's two-run promotion gate language.

GP-061 Component B's cross-grammar cold-test claim is **neither confirmed nor falsified** by this run and returns to open. The protocol discipline is doing its job: a sealed decision tree with two-conjunct verdicts refuses to promote on half of the evidence, and the refusal is the feature, not the bug.

## 5. What this run did produce

- **Independent capability datapoint on gemini-2.5-flash (unrelated to the sealed Component B claim).** Flash recovered a first-order RC step response from a blinded transient-only grid (no sweep reaches the plateau) in a single iteration via a nested five-parameter wrapper that the least-squares fit collapsed to the sealed two-free-parameter specialization. `max_abs_residual = 4.3e-7`. The symbolic regression capability on transient-curvature-only RC is real and should be cited *as a mutator observation*, not as a GP-061 outcome. Worth a finding row in the public track record under a new ID (proposed: F-CAP-FLASH-RC-01) with scope limited to the narrow claim "flash recovers first-order RC from blinded transient data via nested-generalization fit-collapse." Do not inflate the scope to "flash does symbolic regression" — this is one family, one grid, one run.
- **Independent cross-check of sandbox_06's lesson.** The champion nested a 5-parameter generalization around a rank-3 sealed family. The two extra exponents (`base`, `factor`) are unidentifiable *in combination with a linear RC*; the fit drove them to ≈ 1e-5 without spread. This is an instance of the adversarial-multi-start pattern from `papers/case_studies/rank_deficient_bootstrap.md` in reverse — here the extra parameters did not disagree across starts because there was only one start (the default). A multi-start identifiability check on the champion's *own* functional form would have caught the over-parameterization at promotion time.
- **Negative result on the sandbox_09 design premise for Component B.** RC (or any 3-param well-identified GT on an identifiable grid) is a poor substrate for a failed-family harvest test. The physics is too direct — initial slope fixes the time constant, so a modern LLM mutator can back out `R·C` from the transient slope alone. Future sandboxes targeting Component B need a GT family where early-iteration failures are **structurally forced**, not just statistically plausible.
- **A concrete principle for Component B sandbox design.** *You cannot simultaneously require (i) a grid on which the sealed GT is identifiable (so `fit_contract` can fire and §A1.5 can pass) and (ii) a protocol that accumulates a failed-family harvest before the mutator discovers the GT.* Any nested family collapses under (i); any non-nested family is pre-disqualified by charter-level contamination rules. Some other axis — grammar restriction that forbids nesting (e.g., a grammar in which the mutator literally cannot write a wrapper around the sealed form), or a GT outside the nesting closure of the mutator's grammar, or a deliberately-ill-conditioned grid with explicit tolerance of cond(J) > 1e8 — is required. Sandbox_10 (Kepler) gets partial help from axis 1: `math_power_only` grammar, `T² ∝ a³`, no exponential nesting available. But sandbox_10 needs its own nesting-collapse audit before sealing, because fractional-power wrappers can still collapse to Kepler at null extra-param values.

## 6. Follow-ups filed

1. **GP-061 Component B → open.** The two-run promotion gate (sandbox_09 ∧ sandbox_10) is unmet. Component B stays unvalidated for non-Planck projects.
2. **Sandbox_10 (Kepler) — decision pending.** Is Kepler vulnerable to the same nested-collapse pathology? A Kepler GT (`a³ ∝ T²`) under `math_exp_only` is not trivially nest-collapsible by exponential wrappers, which is a point in its favor. Before running, repeat the audit: write down the space of 5-parameter nested generalizations a mutator might propose, and check whether any of them collapse to Kepler at null extra-parameter values. If yes, re-amend Kepler before sealing. New seam to open: `GP-023_sandbox_10_nesting_audit.md`.
3. **`fit_multistart_replay` on champion forms.** The champion's form should itself be run through the multi-start identifiability check before being promoted. That would surface over-parameterized nested families at promotion time. New seam candidate: `GP-069_champion_nesting_audit_seam.md` (or append to GP-057 ratio-finiteness seam which is the nearest existing gate-library entry). Cheaper alternative: a post-fit symbolic simplifier that flags `fitted_param ≈ 0` or `fitted_param ≈ -1` and asks "what does the form reduce to under these limits?"
4. **Sandbox_06 case study cross-reference.** This run is a second empirical anchor for the rank-deficiency lesson, from the opposite direction: sandbox_06 was "declared form is secretly rank-deficient"; sandbox_09 is "declared form is a rank-deficient wrapper around an identifiable core." Update `papers/case_studies/rank_deficient_bootstrap.md` §6 caveats to reference this case in a later revision (not urgent).

## 7. Housekeeping state at close

- Pre-reg `GP-023_sandbox_09_pre_registration.md` stays in `research_areas/private/seams/`. Closed-but-apparatus-failure is not a public-ready artifact until the design lesson is written up as a standalone seam. Promotion to `research_areas/seams/` deferred until GP-061 Component B gets a verdict (via sandbox_10 or a replacement sandbox).
- `research_areas/private/EXPERIMENT_TRACK_RECORD.md` — In-Flight row E-GP023-S09-02 moved to closed with Outcome C and a pointer to this file.
- `research_areas/private/specs/active/GP-061_component_b_generalization_target_spec.md` v3 — sandbox_09 cross-reference updated to "closed Outcome C — apparatus, sandbox design incompatible with harvest premise; Component B claim returns to open."

---

*Audit written 2026-04-15 at operator-stop. Pre-reg §7 decision tree did not anticipate early-stop-at-nested-collapse; §7 should be amended on the next sandbox in this line to include an explicit nesting-collapse branch.*
