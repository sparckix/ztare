# GP-044 Psi-Dependent Floor Verifier 01 — Pre-Registration

## Status

Sealed 2026-04-12 18:00:12 EDT.
Executed 2026-04-12 18:18:04 EDT.
Frozen 2026-04-12 18:18:04 EDT.

## Purpose

This verifier isolates one question:

> can a minimally extended version of the GP-043 escaped generalized-decay family, with a psi-dependent offset term replacing the single global constant, clear the localized visible residual miss without losing holdout generalization?

This is a bounded ablation, not a broad search and not a claim that the true asymptotic floor is already known to be psi-dependent.

## Fixed Structural Change Under Test

**GP-043 frozen family:**

`I_model(phi, psi) = P_floor_global + P_amplitude * psi^A * phi^N * exp(-(P_decay_coeff * psi^B) * phi^M)`

**GP-044 extension:**

`I_model(phi, psi) = (P_floor_base + P_floor_scale * psi^P_floor_alpha) + P_amplitude * psi^A * phi^N * exp(-(P_decay_coeff * psi^B) * phi^M)`

The only structural change is replacing the single global constant with a psi-dependent offset term.

## What Is Fixed

- same substrate as GP-043 / GP-042 / GP-037
- same evidence and holdout
- same deterministic gates
- same Gemini/Gemini family
- same generalized-decay branch warm start

## What Is Deliberately Not Claimed

- no claim that the true asymptotic floor is already proven psi-dependent
- no claim that authored thresholds on fitted parameters are decisive observables
- no model-family widening

## Current Observables

- visible peak locations at `phi = 0.9411`, `2.1768`, `3.8072`
- visible high-phi ordering at `phi = 11.6462`
- hidden deterministic gates for real generalization

## Success Condition

1. visible max residual clears `< 0.05`
2. all hidden deterministic gates remain passed
3. no hard self-reference or internal-parameter discriminator returns

## Failure Condition

- visible residual still fails after fitting the extended family
- or hidden gates collapse

Either outcome is diagnostic.

## Sealed Command

```bash
python -m src.ztare.validator.test_thesis \
  --project gp044_psi_dependent_floor_01 \
  --rubric gp044_psi_dependent_floor_01 \
  --judge_model gemini \
  --mutator_model gemini \
  --deterministic_score_gates
```

## Observed Outcome

- Final score: `0`
- Visible falsification: `fail_assert` at `phi=0.05, psi=2.0`
- Hidden deterministic gates:
  - `hidden_global_residual`: **fail** (`0.08312080760556562 > 0.05`)
  - other four gates: pass
- Self-reference: **not present**

## Interpretation

This one-shot baseline was sufficient because GP-044 was a bounded ablation, not a search packet.

The run answered the fixed question negatively:

- the psi-dependent floor extension did not repair the GP-043 miss
- it also degraded holdout generalization

So GP-044 is frozen as a negative bounded result. The next admissible successor, if any, must target the interior shape / decay core rather than additive offset flexibility.
