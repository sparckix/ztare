# GP-043 Post-Escape Semantic Cleanup Seam

> **Seam metadata** · `seam_id:` GP-043 · `track:` substrates · `status:` Active, 2026-04-12 17:39:48 EDT · `last_updated:` 2026-05-17


## Status

Active, 2026-04-12 17:39:48 EDT

## Problem

GP-042 produced a materially better escaped family at iter 8, but the run still ended at score `0`. The strongest candidate passed the hidden deterministic gates at that iteration while simultaneously carrying:

- hard self-reference
- bad global-floor overclaim
- a discriminator built from internal fitted parameter thresholds

So the next eigenquestion is narrower:

> once the escaped family is restated without semantic contamination, does the family remain a viable candidate, or does it still fail on the substance?

## Turn 1, Codex (2026-04-12 17:39:48 EDT), Freeze family, strip semantic contamination, test baseline directly

The correct first slice is not another mutator loop and not a model-family matrix.

It is:

1. freeze the GP-042 iter-8 escaped family
2. remove the contaminated wrapper
3. baseline-test the cleaned object on the unchanged substrate

That is what `GP-043` is for.

The family is held fixed as:

`P_floor_global + P_amplitude * psi^P_psi_power_A * phi^P_phi_power_N * exp(-(P_decay_coeff * psi^P_psi_power_B) * phi^P_phi_power_M)`

What is deliberately removed:

- treating `P_phi_power_M` thresholds as a decisive discriminator
- treating `P_floor_global` as independently confirmed global floor invariance
- any thesis-authored claim that internal fitted parameters are themselves the current observable

What remains as current observables:

- visible peak locations
- visible high-phi ordering
- hidden deterministic gates for real generalization

So GP-043 is a direct falsification object for the post-GP-042 frontier:

- if the cleaned seed lifts materially, the blocker was mainly semantic contamination
- if it still fails cleanly, the family itself remains inadequate

## Turn 2, Codex (2026-04-12 17:44:59 EDT), GP-043 says semantic contamination was real, but not the whole blocker

The sealed GP-043 baseline is complete.

Command executed:

```bash
python -m src.ztare.validator.test_thesis \
  --project gp043_post_escape_cleanup_01 \
  --rubric gp043_post_escape_cleanup_01 \
  --judge_model gemini \
  --mutator_model gemini \
  --deterministic_score_gates
```

Observed result:

- final score: `0`
- self-reference: **cleared**
- hidden deterministic gates: **all passed**
- remaining failure: visible-slice `fail_assert` at `phi=11.6462, psi=2.0`

This gives a clean split:

1. Semantic contamination was real.
- the hard self-reference is gone
- the internal-parameter discriminator is gone
- the global-floor overclaim is gone

2. But semantic contamination was not the whole blocker.
- the family still fails the visible residual contract on substance
- the miss is narrow but real:
  - `I_obs=1.82642`
  - `I_model=1.764319118173269`
  - `abs residual ≈ 0.0621 > 0.05`

3. The family is still decisive.
- all hidden deterministic gates passed on the cleaned seed
- so this is not junk-family collapse
- it is a serious near-pass family

So the next eigenquestion changes again:

> can a narrowly extended version of the escaped generalized-decay family clear the visible residual contract without losing the holdout pass?

That points to a structural next slice, not more wrapper cleanup. The most plausible next bounded extension is a psi-dependent floor term on top of the escaped generalized-decay family.

## Closure

**Closed 2026-04-12.**

**What the verifier answered:**

Semantic contamination in the GP-042 iter-8 thesis was real, self-reference, internal-parameter discriminators, and global-floor overclaim all cleared once the wrapper was stripped. But the family still fails the visible residual contract on substance: `abs residual ≈ 0.0621 > 0.05` at `phi=11.6462, psi=2.0`. The miss is narrow and localized. Hidden holdout gates remain fully passed, which means the family is decisive, not junk.

**What the verifier did not answer:**

Whether a structurally minimal extension of the escaped family, specifically a psi-dependent floor term replacing the global floor constant, can close the visible residual gap without losing the holdout pass.

**Handoff:**

GP-044 opens a single-extension bounded verifier: same substrate, same gates, same Gemini/Gemini family, one-shot baseline first. The only structural change is replacing `P_floor_global` with `f(psi)`. If that extension closes the gap, the family is confirmed. If it still misses, the decay parameterization itself is the next candidate.
