# GP-044 Psi-Dependent Floor Seam

## Status

Closed — 2026-04-12 18:18:04 EDT

## Problem

GP-043 showed that the escaped generalized-decay family is load-bearing but still fails the visible residual contract at `phi=11.6462, psi=2.0` by `≈ 0.062`. The miss is narrow and localized. All hidden holdout gates pass on the cleaned seed.

The GP-043 family uses a global floor constant `P_floor_global = 0.0706`. The localization of the residual failure — high phi, high psi — is the only reason to test a floor-side extension at all. But that does **not** yet prove a true asymptotic floor is psi-dependent. At most, the visible slice shows that the high-phi tail in the observed range differs strongly by psi, especially at `psi=2.0`.

The eigenquestion for GP-044:

> Can replacing the global floor with a psi-dependent floor term close the visible residual gap without losing the holdout pass?

## Family Under Test

GP-043 (frozen):

```
I_model = P_floor_global
        + P_amplitude * psi^A * phi^N * exp(-(P_decay_coeff * psi^B) * phi^M)
```

GP-044 extension (minimal structural change):

```
I_model = (P_floor_base + P_floor_scale * psi^P_floor_alpha)
        + P_amplitude * psi^A * phi^N * exp(-(P_decay_coeff * psi^B) * phi^M)
```

All decay-branch parameters (`P_amplitude`, `A`, `N`, `P_decay_coeff`, `B`, `M`) are initialized from the GP-043 iter-8 fitted values. The GP-035 fitter re-optimizes all parameters against visible evidence.

## Design Constraints

- **Same substrate.** Same evidence.txt, same evidence_holdout.txt, same gate definitions as GP-043.
- **Same gates.** `hidden_global_residual < 0.05`, peak location within 15%, high-phi decay ratio within 10%.
- **Same model family.** Gemini mutator, Gemini judge. No family branching yet.
- **One-shot baseline first.** Run `test_thesis.py` once with the cleaned seed and GP-035 fitting enabled. Do not open a 10-iter loop until the one-shot result is read.
- **No self-reference.** Discriminators must be evidence-grounded observables. No fitted-parameter thresholds as the decisive observable.

## Success Criterion

1. Visible residual clears `< 0.05` across all sweeps
2. Hidden holdout gates stay passed (all five)
3. No return to self-reference or internal-parameter discriminators

## Failure Criterion

- Visible residual still fails after psi-dependent floor fitting
- Or hidden gates collapse when the floor gains psi-dependence

Either outcome gives diagnostic information. Failure here would indicate the decay branch itself needs structural change, not just the floor.

## Turn 1 — 2026-04-12 — One-shot baseline pre-registration

Sealed command:

```bash
python -m src.ztare.validator.test_thesis \
  --project gp044_psi_dependent_floor_01 \
  --rubric gp044_psi_dependent_floor_01 \
  --judge_model gemini \
  --mutator_model gemini \
  --deterministic_score_gates
```

Seed: `projects/gp044_psi_dependent_floor_01/test_model.py` — GP-043 decay branch parameters frozen, psi-dependent floor initialized with `P_floor_base=0.04, P_floor_scale=0.04, P_floor_alpha=1.0`.

Expected result space:
- If GP-035 fitter finds params that close the gap → visible residual passes, hidden gates stay → family confirmed
- If fitter cannot close the gap on this form → floor parameterization is not the whole story → open decay-branch extension seam

## Turn 2 — Codex (2026-04-12 17:50:31 EDT) — Bounded ablation is fine; prompt-steered GP-044 is not

The GP-044 idea is **not** inherently overfitting, but the current implementation had one real contamination risk:

- the rubric persona was steering the mutator toward the answer:
  - “CRITICAL: starting point ... do NOT revert ... psi-dependent floor is the specific structural extension under test”

That is too strong for a verifier. It turns a bounded ablation into a partially coached search.

The clean version of GP-044 is:

1. treat it as a **single-extension ablation**
2. keep the family change fixed in the project seed / test model
3. keep the judge persona neutral
4. avoid claiming that a true asymptotic floor is already known to be psi-dependent

So the correct scientific claim is narrower:

> GP-044 tests whether a psi-dependent high-phi offset term can repair the localized visible miss without breaking holdout generalization.

That is acceptable. What would be overfitting is:

- broad prompt steering toward this family
- using the rubric to forbid alternatives
- narrating “psi-dependent floor” as already established fact rather than a bounded local hypothesis

## Turn 3 — Codex (2026-04-12 18:00:12 EDT) — This is not the GP-041 ablation again

This is a different ablation from the earlier replay work.

What GP-041 asked:

- if the escaped candidates are replayed with generic multistart / optimizer help, do they suddenly pass?

That was an **optimizer-side** ablation on already-proposed families, and it came back negative.

What GP-044 asks:

- if the strongest escaped family gets one narrowly justified structural extension, does the localized visible miss disappear while holdout performance survives?

That is a **family-structure** ablation, not a fitter ablation.

So GP-044 is methodologically legitimate as long as it stays bounded:

- one structural change only
- neutral judge persona
- no hypothesis-enforcing assertions in `test_model.py`
- explicit pre-reg and one-shot baseline first

I also removed the bad assertion that required the fitted offset term itself to be monotone in `psi`. That was enforcing the hypothesis rather than testing it.

## Turn 4 — Claude (2026-04-12) — Turn 3 confirmed the fix; assertion 5 is gone, substrate is clean

Turn 3 (Codex) removed the hypothesis-enforcing floor-monotonicity assertion from `test_model.py`. Confirmed: `test_model.py` no longer contains assertion 5. The remaining assertions (1–4) are all evidence-grounded observables — peak locations and high-phi tail ordering read directly from evidence.txt. That is the correct discriminator surface.

Substrate is clean. Ready for pre-registration seal.

## Turn 5 — Codex (2026-04-12 18:18:04 EDT) — Negative bounded result; floor repair is not the missing piece

The one-shot GP-044 baseline answered its question cleanly enough to close the seam.

Observed outcome:

- visible fail moved to `phi=0.05, psi=2.0`
- hidden global residual degraded to `0.08312080760556562 > 0.05`
- self-reference did **not** return

So the floor-side repair failed on both of the things that mattered:

1. it did **not** clear the visible contract
2. it did **not** preserve the hidden pass from GP-043

That means GP-044 is a useful negative result, not wasted effort. It rules out the tempting story that the GP-043 near-pass was mainly missing a more flexible additive offset.

The load-bearing implication is narrower:

> the remaining miss is not an offset problem first. The next admissible repair, if any, has to target the interior shape / decay core rather than the floor.

But there is a second implication that matters more for the discovery claim:

> if the operator keeps hand-selecting plausible repairs after each failure, a later pass may no longer support a deductive-science claim even if it numerically succeeds.

So GP-044 closes with a double lesson:

- substantive: floor extension is the wrong repair
- methodological: the next seam must define an admissibility rule for successor structural extensions, or the later claim stops looking deductive and starts looking operator-steered

## Closure

**Closed 2026-04-12 18:18:04 EDT.**

**What GP-044 ruled out:**

- that the GP-043 miss was mainly a single global-floor rigidity problem
- that a psi-dependent offset term is the minimal successful repair

**What GP-044 did not answer:**

- whether an admissible interior-shape / decay-core extension can clear the visible miss without contaminating the deductive-science claim

**Handoff:**

Open GP-045 on the successor question, but do not jump straight into another verifier run without first locking the admissibility rule for structural extensions.
