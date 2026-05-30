# GP-043 Post-Escape Semantic Cleanup Verifier 01, Pre-Registration

> **Seam metadata** · `seam_id:` GP-043 · `track:` substrates · `status:` Sealed 2026-04-12 17:39:48 EDT. · `last_updated:` 2026-05-17


## Status

Sealed 2026-04-12 17:39:48 EDT.

## Purpose

This verifier isolates one question:

> did the GP-042 iter-8 escaped family fail mainly because of semantic contamination, or does the family still fail once the wrapper is cleaned up?

The substrate, hidden holdout, and deterministic gates are unchanged from GP-042 / GP-037.

## Fixed Family Under Test

The family is frozen from GP-042 iter 8:

`I_model(phi, psi) = P_floor_global + P_amplitude * psi^P_psi_power_A * phi^P_phi_power_N * exp(-(P_decay_coeff * psi^P_psi_power_B) * phi^P_phi_power_M)`

The baseline seed uses the GP-042 iter-8 fitted parameters directly.

## What Is Removed

- no discriminator built from authored thresholds on fitted parameters
- no claim that `P_floor_global` is a verified global floor across all psi
- no claim that the fitted parameter values themselves are the decisive current observable

## Current Observables

- visible peak locations at `phi = 0.9411`, `2.1768`, `3.8072`
- visible high-phi ordering at `phi = 11.6462`
- hidden deterministic gates for real generalization

## Success Condition

The baseline result materially lifts relative to GP-042’s iter-8 semantic failure surface:

1. no hard self-reference on internal parameter thresholds
2. visible current-observable assertions pass
3. hidden deterministic performance stays strong enough to keep the family credible

## Failure Condition

The cleaned seed still fails in essentially the same way, which would mean the family itself remains inadequate or the cleaned wrapper still does not fix the substantive error.

## Sealed Command

```bash
python -m src.ztare.validator.test_thesis \
  --project gp043_post_escape_cleanup_01 \
  --rubric gp043_post_escape_cleanup_01 \
  --judge_model gemini \
  --mutator_model gemini \
  --deterministic_score_gates
```

## Execution Outcome

Recorded 2026-04-12 17:44:59 EDT.

- status: completed
- final score: `0`
- self-reference: cleared
- hidden deterministic gates: all passed
- visible failure: `fail_assert` at `phi=11.6462, psi=2.0`

Cold-artifact summary:

- [latest_eval_results.json](projects/gp043_post_escape_cleanup_01/latest_eval_results.json) shows:
  - no hard self-reference
  - all hidden deterministic gates passed
  - remaining visible residual failure
- [debate_log_iter_1776029995.md](projects/gp043_post_escape_cleanup_01/debate_log_iter_1776029995.md) localizes the miss:
  - `I_obs=1.82642`
  - `I_model=1.764319118173269`

Interpretation:

- semantic contamination was real and the cleanup worked
- but the escaped family still misses the visible residual contract on substance
- the next bounded frontier should move to structural extension, not more wrapper cleanup
