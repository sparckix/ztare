# When holdout generalisation cannot discriminate structural class

**A short case study in evidence grid design.**

*Origin: this failure was observed in a pre-registered symbolic regression
experiment where a language model was asked to recover an unknown two-variable
law from data. The model found a structurally different formula that passed
both visible fit (RMSE = 0.021) and holdout (RMSE = 0.021) with large margin,
and scored 97/100 from an independent judge — yet was structurally wrong.
The holdout tested generalisation to unseen values of one variable; the
correct discriminator required extending the other variable into a new regime.
The finding prompted the design of the farther-tail discriminator as a
standard post-run check for structural class identification.*

---

## Abstract

We exhibit two structurally distinct two-variable functions — a
simple exponential-decay form (the Wien approximation) and the
transcendental law it approximates (the Planck form with denominator
`exp(x1/x2) - 1`) — that are indistinguishable on a bounded evidence
grid. Both pass a standard RMSE threshold (0.15) on 24 visible points and
on a 16-point holdout drawn from unseen values of the second variable.
Wien achieves visible RMSE = 0.021 and holdout RMSE = 0.021; Planck
achieves visible RMSE ≈ 0 (exact generating law) and holdout RMSE ≈ 0.
A standard evaluation battery — visible RMSE + holdout RMSE + holdout
hard gate — correctly passes both forms.

A farther-tail discriminator — relative error at input pairs where the
two forms disagree most — surfaces the distinction immediately: the
Wien form exceeds 200% relative error at (x1=6, x2=0.5), while the
Planck form stays below 0.01% at every farther-tail pair.

The holdout check is satisfying the *form* of a generalization test
while missing the *intent*. Generalization to unseen values of one
variable does not imply structural correctness. A discriminator must
probe the input regime where the candidate structural classes actually
disagree — which is not always the same regime as the holdout.

A self-contained reproducer is provided: `evidence_grid_underdetermination_reproducer.py`
(numpy + scipy only, ~120 lines).

---

## 1. Setup

The ground-truth generating law is

$$
z(x_1, x_2) \;=\; \frac{x_1^3}{\exp(x_1 / x_2) - 1}
$$

with the guard `z = 0` when `x1/x2 > 500`.

The visible evidence grid is:

- `x1 ∈ {0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0}` — eight values
- `x2 ∈ {0.5, 1.0, 2.0}` — three values, all visible
- 24 points total, clean (no measurement noise)

The holdout grid uses the same `x1` values at two unseen `x2` values:
`x2 ∈ {0.75, 1.5}` — 16 points.

**The two candidate forms.**

*Form A (Wien approximation)*: `z = p0 · x2^p1 · x1^p2 · exp(−p3 · x1 / x2)`
with four free parameters. Best-fit values on the visible 24 points:
`p0=1.208, p1=0.862, p2=2.160, p3=0.739`.

*Form B (Planck)*: `z = x1^3 / (exp(x1/x2) − 1)` — no free parameters.

The Wien form is the large-argument limit of the Planck form: when
`x1/x2 >> 1`, `exp(x1/x2) − 1 ≈ exp(x1/x2)`, so the Planck denominator
reduces to a pure exponential. On the visible grid, `x1/x2` ranges from
`0.25` (at `x1=0.5, x2=2.0`) to `8.0` (at `x1=4.0, x2=0.5`). The
`exp(x1/x2) − 1 ≈ exp(x1/x2)` approximation is not yet accurate at
`x1/x2 = 8`, but the four-parameter Wien form compensates by adjusting
`p3` to absorb the residual.

---

## 2. The check that passes

**Visible RMSE:** Form A (Wien, fitted) achieves RMSE = 0.021 on the
24-point visible grid. Form B (Planck, no fit) achieves RMSE ≈ 0 (it
is the exact generating law). Both well below any reasonable threshold
(0.15 used in the original evaluation).

**Holdout RMSE:** Form A achieves holdout RMSE = 0.021. Form B achieves
holdout RMSE ≈ 0. Both pass a threshold of 0.15 with large margin.

**Holdout hard gate (pass/fail):** Both pass.

A standard evaluation battery reports both forms as viable. An automated
judge evaluating form A on the visible + holdout data, with no access to
the ground truth, has no structural signal to prefer form B.

---

## 3. The check that catches

The farther-tail discriminator evaluates relative error at input pairs
where the two forms disagree:

| x1  | x2  | GT (Planck) | Wien prediction | Relative error |
|-----|-----|-------------|-----------------|----------------|
| 5.0 | 0.5 | 0.005675    | 0.013263        | 134%           |
| 6.0 | 0.5 | 0.001327    | 0.004486        | **238%**       |
| 8.0 | 0.5 | 0.000058    | 0.000434        | **654%**       |
| 5.0 | 1.0 | 0.847957    | 0.969711        | 14%            |
| 6.0 | 1.0 | 0.536741    | 0.686636        | 28%            |
| 8.0 | 1.0 | 0.171815    | 0.291549        | 70%            |

Predicate: `is_exponential_class()` returns False if any farther-tail
pair exceeds 200% relative error. Wien fails at `(6.0, 0.5)` — 238%.

Form B (Planck) achieves relative error < 0.01% at every farther-tail
pair (it is the exact generating law).

The divergence pattern is `x2`-dependent: at small `x2`, `x1/x2` grows
rapidly with `x1`, pushing deep into the regime where
`exp(x1/x2) − 1` and `exp(x1/x2)` are no longer interchangeable. The
Planck denominator carries the `-1` correction that Wien cannot express
in its functional class. The four fitted Wien parameters have exhausted
their degrees of freedom fitting the visible range; there is no parameter
setting that makes Wien correct at `x1/x2 >> 8`.

---

## 4. Why the two checks disagree

| Check | What it varies | What it actually tests |
|---|---|---|
| Holdout RMSE (unseen x2) | second variable | does the functional form generalize across the scaling variable |
| Farther-tail relative error (unseen x1) | first variable, extended range | does the functional form belong to the correct structural class in the regime where classes diverge |

The holdout probes generalization across `x2` (the scaling variable).
Both Wien and Planck satisfy the axiomatic scaling constraint:
`z_peak ∝ x2^3` and `x1_peak ∝ x2`. A form that gets the scaling right
will hold out well regardless of whether it is structurally correct.

The farther-tail probes the `x1/x2` regime where the `-1` in the Planck
denominator is load-bearing. That regime is not present in the visible or
holdout grids. The holdout's choice of unseen `x2` values does not
automatically cover the regime needed to discriminate structural classes.

This is not a failure of the holdout as a statistical tool — it correctly
tests what it measures. It is a failure of the *evidence design* to
anticipate which regime is discriminative for the structural question
being asked.

---

## 5. The general lesson

**The discriminative power of an evidence grid is relative to the
structural classes in competition.** A holdout that covers unseen values
of one variable does not automatically cover the regime where candidate
structural classes disagree.

The designer of an evaluation battery must ask: *in what input regime do
the candidate forms produce the largest relative disagreement?* The
discriminator must probe that regime. For the Wien-vs-Planck pair, that
regime is high `x1/x2` — achievable by extending `x1` past the visible
maximum, not by varying `x2`.

**A one-line rule.** *If your holdout only varies what you left out of
the visible set, it tests generalization within the structural family the
visible data is consistent with. It does not test whether that structural
family is the correct one.*

The corollary for automated symbolic regression evaluations: the holdout
gate is a necessary but not sufficient condition for structural
correctness. A farther-tail discriminator — placed in the regime of
maximum disagreement between candidate structural classes — is the
check that makes the battery structurally complete.

---

## 6. Scope and caveats

- This is a single worked example. The claim is not "holdout evaluation
  is insufficient in general" — it is "holdout evaluation on unseen
  values of one variable does not, by itself, discriminate structural
  class when the discriminative regime requires extending a different
  variable beyond the training range."
- The farther-tail discriminator requires knowing, in advance, where the
  candidate structural classes diverge. This is a design-time decision,
  not an automatic one. It is an instance of the evidence grid design
  problem: which input points are most informative about the structural
  question being asked?
- When the competing forms are not known in advance (as in live symbolic
  regression), the discriminator can be set conservatively: probe the
  input corners and extremes of the physically plausible domain, not just
  the interpolation range of the training data.
- The Wien-Planck distinction arises specifically because the visible
  range sits in the regime where the Wien approximation is good to within
  a few percent. If the visible `x1` grid had extended to `x1=8` at
  `x2=0.5`, the training RMSE of the Wien form would already be elevated
  and the issue would surface earlier. Evidence grid design determines
  how early the structural question becomes answerable.

---

## Reproducer

`evidence_grid_underdetermination_reproducer.py` in this directory.
Dependencies: numpy, scipy. Run:

```
python evidence_grid_underdetermination_reproducer.py
```

No framework, no project-specific vocabulary, no hidden state. The
output matches Sections 2 and 3 above.
