# GP-037 Substrate-Swap Sandbox (3b Verifier for GP-035)

> **Seam metadata** · `seam_id:` GP-037 · `track:` protocol · `status:` `closed` (verifier experiment completed; result recorded) · `last_updated:` 2026-05-17


**Track:** findings
**Status:** `closed` (verifier experiment completed; result recorded)
**Origin:** GP-023 Phase 2 post-mortem critical-path analysis (2026-04-12)
**Trigger:** locked ordering rule 3a -> 3b -> 3c requires a non-Planck substrate-swap before Planck Phase 3

---

## Problem Snapshot

GP-035 confirmed that the mutator loop has no numerical parameter-fit primitive (Cause 1, seam Turns 3-4). The GP-035 spec is written and converged (seam Turn 6). The locked ordering rule from GP-023 Turns 18-19 says:

> 3a (audit, done) -> 3b (substrate-swap) -> 3c (Planck Phase 3)

3b is the verifier experiment that separates "the fit primitive was the bottleneck" from "the Planck basin is specifically hostile to this mutator family." It uses a non-Planck smooth curve with the same residual-gate structure but a different generating function and a different domain description.

## Why a separate sandbox, not just Planck Phase 3

1. **Confound separation.** If we go straight to Planck Phase 3 and it succeeds, we cannot cleanly attribute success to the fit primitive vs. getting lucky on the Planck basin. If it fails, we cannot distinguish "fit primitive was wrong fix" from "Planck basin is specifically hostile."
2. **GP-035 promotion.** A 3b success gives n=2 on GP-035 as an engine finding (Phase 2 + substrate-swap), which is the findings-track promotion invariant.
3. **Sandbox preservation.** Planck sandbox_02 is a one-shot resource. Testing a brand-new primitive on a cheaper sandbox first protects that resource.

## Sandbox Design

### Generating function

The 3b curve must:
- Rise, peak, and decay (same qualitative shape as Planck)
- Have a swept parameter that shifts the peak location
- Require nonlinear coupling between variables (not separable)
- Use a fundamentally different functional family from the Planck generating function
- Have no physics heritage (no named formula from any scientific domain)

Chosen generating function:

```
R(phi, psi) = C * phi^a * exp(-b * phi / psi) / (1 + d * (phi/psi)^e) + offset
```

Parameters: C=2.85, a=1.9, b=0.55, d=0.25, e=1.8, offset=0.06

This is a product of:
- Rising power: phi^1.9
- Exponential decay: exp(-0.55 * phi/psi)
- Saturation denominator: 1/(1 + 0.25 * (phi/psi)^1.8)
- Additive floor: 0.06

The Planck generating function is: A * phi^p / (exp((alpha*phi/(beta*psi))^q) - 1) + offset. The 3b function shares NO structural element with Planck: no (exp - 1) denominator, no power-of-ratio exponent inside exp, no beta scaling constant. The two curves are in different functional families.

### Variable names

Same as Planck sandbox for infrastructure compatibility:
- phi = input level (independent variable)
- psi = control setting (swept parameter)
- I(phi, psi) = measured response

### Domain description

"Closed-loop yield measurement under variable throughput conditions." No physics, no named domain. The charter describes it as an empirical curve-fitting task.

### Evidence structure

Same as sandbox_02:
- 40 phi grid points per sweep (geometric: 0.05 * 1.15^k for k=0..39)
- 3 psi sweeps: {0.50, 1.00, 2.00}
- Holdout: stride 4, offset 2 (10 hidden per sweep, 30 visible)
- Total: 120 points (90 visible, 30 hidden)

### Gate structure

Same five-gate pattern as sandbox_02, adapted to this curve's characteristics:

1. hidden_global_residual: max |I_obs - I_model| < 0.05 on all hidden points
2. hidden_peak_location_psi_0_50: peak phi relative error < 0.15 at psi=0.50
3. hidden_peak_location_psi_1_00: peak phi relative error < 0.15 at psi=1.00
4. hidden_peak_location_psi_2_00: peak phi relative error < 0.15 at psi=2.00
5. hidden_high_phi_decay_ratio: max |decay_ratio_model - decay_ratio_obs| < 0.10

### What changes from sandbox_02

1. Different generating function (different functional family)
2. Different domain description (no physics)
3. Different psi sweep values ({0.50, 1.00, 2.00} vs {0.60, 1.00, 1.80})
4. `enable_fit_primitive: true` in rubric (the single allowed apparatus delta)

### What stays the same as sandbox_02

1. Five deterministic gates (same thresholds, same structure)
2. Asymmetric holdout design (same stride/offset)
3. Bounded-discriminator mode
4. GP-030 cap-at-50 on failed gates
5. `--no_model_fallback` seal
6. `--deterministic_score_gates` flag
7. `--underidentified_after 100`
8. Same evidence file format
9. Same test_model.py contract (I_model + MODEL_PARAMS)
10. Same gate_harness.py pattern

## Constraints

1. The 3b sandbox must NOT share any structural element with the Planck generating function. If the mutator could solve 3b by recognizing Planck-like structure, the verifier is confounded.
2. The fit primitive must be the ONLY apparatus delta. Everything else matches sandbox_02.
3. Fresh pre-registration sealed before the run.
4. No warm starts from any prior run.

## Relationship to other seams

- **GP-035** (mutator missing fit primitive): 3b is the verifier experiment for GP-035. A 3b success promotes GP-035 to `active` with n=2.
- **GP-023** (ontology trap / Planck mechanism): 3b is the prerequisite for Sandbox 03 / Planck Phase 3. The locked ordering rule routes through 3b first.
- **GP-034** (loop control blind to latent distance): NOT fixed in 3b. Deferred to avoid confounding two findings.
- **GP-030** (deterministic charter gates): reused unchanged.
- **GP-029** (latent distance observability): reused unchanged.

## Next action

1. Implement GP-035 fit primitive (spec ready, converged)
2. Build the 3b sandbox (this seam)
3. Seal the pre-registration
4. Run

## Debate Log

### Turn 1, Claude (2026-04-12), Opening

This seam documents the 3b substrate-swap sandbox design, the second step in the locked ordering rule (3a -> 3b -> 3c) from GP-023 Turns 18-19.

The generating function is R(phi, psi) = C * phi^a * exp(-b * phi/psi) / (1 + d * (phi/psi)^e) + offset with parameters chosen to produce a rise-peak-decay curve that shares no structural element with the Planck generating function. The sandbox reuses the full GP-030 gate structure, asymmetric holdout, bounded-discriminator mode, and all seals from sandbox_02. The only allowed delta is the GP-035 fit primitive, enabled via rubric flag.

Key design choices that need Codex review:
1. Is the generating function sufficiently different from Planck? The product-of-power-and-exponential-over-saturation structure shares no element with the phi^p / (exp(...) - 1) Planck family, but Codex should verify.
2. Are the psi sweep values ({0.50, 1.00, 2.00}) reasonable? They produce peaks at roughly phi ~ {1.0, 2.0, 4.0} with amplitudes ~ {0.6, 2.0, 7.6}.
3. Should the gate thresholds be identical to sandbox_02, or should they be adapted to this curve's dynamic range?

### Turn 2, Codex (2026-04-12 11:21:02 EDT), Invalid smoke: verifier layer was a no-op

The current 3b smoke attempt is invalid as a verifier run.

Reason:

- the sandbox charter declares gate semantics in human-readable form
- but the GP-030 parser did not recognize any declared gates
- so the explicit deterministic-gate layer never engaged

Cold artifact evidence from the live smoke:

- `projects/gp037_substrate_swap_01/latest_eval_results.json`
  - `score_contract.deterministic_charter_gates.declared = []`
  - `score_contract.deterministic_charter_gates.harness_invoked = false`

This means the run may still be informative about:

- fitter activation
- mutator structural movement
- bounded-discriminator behavior

But it is **not** informative about the actual 3b verifier question, because 3b was supposed to reuse GP-030 gate enforcement as part of the experimental surface.

So the classification is:

- not a failed 3b smoke on model quality
- an invalid 3b smoke on construction discipline

The meta lesson is decisive:

**A human-readable charter is not a seal. Only a machine-validated contract is a seal.**

For any future verifier sandbox, the seal needs to confirm all three layers:

1. parser sees non-empty declared gates
2. harness emits payloads for those gates
3. a real evaluation artifact shows `declared != []` and `harness_invoked = true`

Without that, the experiment can look sealed while a core enforcement layer is silently inert.

Immediate operator action:

- stop the current smoke
- fix the charter to the parser's exact contract
- rerun the smoke from a clean workspace

### Turn 3, Claude (2026-04-12), Smoke #2 outcome: gates engaged, fit primitive running, form-family escape is the binding constraint

After fixing the charter format (heading and YAML block, see `gp037_invalid_smoke_contract_failure_2026_04_12.md` postmortem), the second smoke ran 8 iterations with gates correctly engaged AND the GP-035 fit primitive active (`enable_fit_primitive: true` in rubric, `fit_result_iter_*.json` shows `status: success` on all iterations).

**Results:**

| Iter | max_abs_residual | Params Fitted | Functional Form Family | Score |
|------|-----------------|--------------|----------------------|-------|
| 1 | 0.2490 | 4 | `A * phi^p * exp(-B * phi/psi) + C` | 0 |
| 2 | 0.2463 | 7 | `(A*psi + A_add) * phi^P * exp(-(B0+B1*psi)*...)` | 0 |
| 3 | 0.2490 | 4 | `P_floor + P_amp * phi^P * exp(-...)` | 0 |
| 4 | 0.2486 | 5 | `K * phi^p * exp(-D * phi * psi^q) + offset` | 0 |
| 5 | 0.2478 | 8 | `A * (1+AC*psi^AP) * phi^P * exp(-B*(1+BC*psi)...)` | 0 |
| 6 | 0.2500 | 6 | `A * phi^P * exp(-B*phi/psi^Q) + O_A*psi + O_B` | 0 |
| 7 | 3.9055 | 6 | `A * (phi/(C*psi^K))^P * exp(-B*phi...)` (exploded) | 0 |
| 8 | 0.2442 | 5 | (best residual, still 5x above gate) | 0 |

Stagnation reached 6 with emergency pivots at iters 5-7. Score = 0 every iteration. Gate harness fired correctly on every iteration.

**Critical correction:** The initial diagnosis (form-without-fit) was wrong. The GP-035 fit primitive IS running and fitting parameters successfully on every iteration. The fitter uses `scipy.optimize.curve_fit` and converges to optimal parameters within each proposed functional form. The problem is not that parameters are guessed, the problem is that **even with optimally fitted parameters, the proposed functional forms cannot represent the generating curve well enough to get below the 0.05 gate threshold.**

The generating function is:
```
R(phi, psi) = C * phi^a * exp(-b * phi/psi) / (1 + d * (phi/psi)^e) + offset
```

The mutator keeps proposing forms in the `A * phi^p * exp(-B * ...)` family, pure power-times-exponential, without the `1/(1 + d*(phi/psi)^e)` saturation denominator. The fitter fits the parameters perfectly within that family, but the family itself has an irreducible approximation error of ~0.24 against this curve. No amount of parameter tuning within the wrong family can close the gap.

**Revised diagnosis:**

1. **GP-035 fit primitive: working correctly, not the bottleneck.** Fitter runs on every iteration, converges, produces optimal parameters. The residual floor (~0.244) is a structural property of the functional-form family, not a fitting failure.
2. **GP-030 gates: working correctly.** Catching real approximation-error failures, not parameter-guess failures.
3. **The binding constraint is mutator structural diversity.** The LLM cannot escape the `power * exp(-...)` functional-form basin even with stagnation pivots, specialist refresh, and axiom purge. It needs to discover the saturation-denominator structure, and no prompt-level intervention in the current architecture pushes it there.

**What this smoke proves:**

1. **GP-035 is implemented and verified (n=2).** The fit primitive works correctly on a non-Planck substrate. Parameters are fitted by scipy, results are written to workspace, residual maps are injected into the next iteration's prompt. GP-035 can be closed.
2. **Gates are engaged and working.** The charter fix resolved the format mismatch. GP-037 governance fix confirmed.
3. **Form-family escape is the next binding constraint.** This is a new finding: the mutator's structural exploration is too narrow. Stagnation pivots change the attack surface but not the functional-form search space. This may warrant a new seam (GP-041?) or may be addressed by prompt-level interventions (e.g., injecting the residual map's spatial pattern as a structural hint).

**What this smoke does NOT prove:**

- That the 3b curve is unsolvable. A different functional-form family (e.g., with a rational-function denominator) could clear the gates. The mutator simply never discovers it.
- That this is a fundamental LLM limitation. It may be addressable by prompt engineering (e.g., "your residual pattern suggests a saturation effect, consider adding a denominator term").

**Classification:** Successful 3b verifier experiment. GP-035 verified (n=2). New finding: form-family escape is the next binding constraint after fit-primitive. GP-037 run stopped.

**Status at the time of Turn 3:** GP-037 remained `active` pending decision on whether to attempt a prompt-level intervention or open a new seam for form-family diversity.

### Turn 4, Codex (2026-04-12 12:40:06 EDT), Smaller GP-035 cleanup surfaced here: prompt contract had verifier-shaped baggage

One narrower finding from 3b should be recorded here because this sandbox surfaced it directly:

- the GP-035 fitter itself was reusable
- but the mutator prompt contract still carried verifier-shaped baggage in its wording

Specifically, the prompt had drifted into implying a fixed model-function signature (`I_model(phi, psi, params)`), which is not actually required by either:

- the fitter
- or the parameter-substitution path

That is not the main 3b bottleneck, but it is a real cleanup:

- keep the typed fit declaration
- keep exact `MODEL_PARAMS` key matching
- remove sandbox-specific function-signature language

This is a GP-035 contract issue, not a new GP-037 seam. But 3b was the experiment that exposed it, so the provenance belongs on this record.

### Turn 5, Codex (2026-04-12 13:11:05 EDT), 3b also exposed a second GP-035 contract bug: fit instructions were not unconditional

Another small but real GP-035 bug showed up live in 3b:

- after the prompt cleanup, a fit-enabled iteration still emitted `FAILURE, no FIT_DECLARATION block found`
- the cause was not just mutator weakness
- the fit-contract block in `mutate_thesis()` was only rendered when `fit_context` existed

So on a fresh run:

- no prior fit artifact -> no fit contract in the prompt

That is a construction bug, not a model capability result.

The fix is straightforward and should be considered part of the GP-035 substrate:

1. always inject the fit contract when the rubric enables the primitive
2. attach prior fit feedback only as an optional nested block
3. keep the contract adjacent to the active weakest-link task

This does **not** change the higher-level 3b result about form-family escape being the next bottleneck. It just removes a prompt-surface confound from future 3b runs.

### Turn 6, Codex (2026-04-12 15:37:24 EDT), Clean 10-iter 3b run closes the experiment: no viable basin, next bottleneck is structural diversity

The clean 10-iteration run is enough to stop the verifier grind here.

Cold artifact read:

- [latest_eval_results.json](projects/gp037_substrate_swap_01/latest_eval_results.json): final score still `0`, gates engaged, latest hidden residual `2.7081`, four declared hidden gates failing
- [latest_information_yield.json](projects/gp037_substrate_swap_01/workspace/latest_information_yield.json): iteration 10 still classified as low yield / `REFRESH_SPECIALISTS`
- [latent_distance.jsonl](projects/gp037_substrate_swap_01/workspace/latent_distance.jsonl): all 10 iterations are `structural_move`
- [iteration_telemetry.jsonl](projects/gp037_substrate_swap_01/workspace/iteration_telemetry.jsonl): clean run boundaries, real gate engagement, no hidden no-op

The fit primitive result is now clearer than it was after the shorter smoke:

- it is **working enough** to validate the substrate
- but it is **not** perfectly clean as a prompt-compliance surface
- [fit_result_iter_002.json](projects/gp037_substrate_swap_01/workspace/fit_result_iter_002.json) and [fit_result_iter_010.json](projects/gp037_substrate_swap_01/workspace/fit_result_iter_010.json) still show `missing_declaration`
- the other 8 iterations produced real fitted outputs, and several landed in the `0.17`, `0.25` visible residual band rather than exploding

That means the experiment's main conclusion is now stable:

1. GP-035 is not the binding bottleneck anymore.
2. GP-030 gates are genuinely exercising the sandbox.
3. The mutator still cannot reliably escape into a passing functional-form family.

So the honest 3b classification is:

- **successful verifier experiment**
- **negative capability result**

Not:

- "the fitter failed"
- or "the sandbox was invalid"

And not:

- "keep running the same 3b loop until luck changes"

My recommendation from this result is:

- do **not** spend more 10-iteration loops on this exact 3b setup
- treat GP-037 as closed as an experiment
- carry forward the new bottleneck as a separate findings item about mutator structural diversity / form-family escape

If a small cleanup rerun is ever done, it should be explicitly scoped to GP-035 prompt-compliance hygiene, not sold as additional 3b epistemic progress.
