# When a bootstrap-under-noise identifiability check lies to you

**A short case study in pre-commit verifier design.**

*Origin: this failure was first observed when designing a ground-truth
substrate for a law-recovery experiment. A six-parameter family was
declared as ground truth, but two of the parameters were unidentifiable
— a pre-commit check that should have caught this did not. The finding
prompted a change to adversarial multi-start as the standard
identifiability check for all subsequent experiment design.*

---

## Abstract

We exhibit a six-parameter nonlinear regression target whose declared family
is secretly rank five: two of the parameters enter only through a single
ratio. A common pre-commit identifiability check — *fit the clean target,
perturb it with small Gaussian noise, bootstrap, assert the recovered
parameters are stable* — passes the degenerate family cleanly. A different
check — *fit the clean target from multiple adversarial starting points,
assert the recovered parameters agree across starts* — catches the
degeneracy immediately: the two unidentifiable parameters disagree by
**>150% across starts** while their ratio agrees to **machine precision**.

The bootstrap-under-noise check is satisfying the *form* of an
identifiability test while missing the *intent*. This note explains why,
and what to use instead.

A self-contained reproducer is provided: `rank_deficient_reproducer.py`
(numpy + scipy only, ~150 lines).

---

## 1. Setup

The declared ground-truth family is

$$
I(\varphi, \psi) \;=\; A \cdot \frac{\varphi^{p}}{\exp\!\big((\alpha\varphi/(\beta\psi))^{q}\big) - 1} \;+\; \text{offset}
$$

with six declared parameters: `A, p, alpha, beta, q, offset`.

Ground-truth values: `A=0.95, p=2.30, alpha=0.72, beta=1.00, q=1.30,
offset=0.06`.

Evaluation grid: `phi ∈ geomspace(0.1, 15, 50)` at three values of
`psi ∈ {0.60, 1.00, 1.80}`, giving 150 points.

Fit is by least squares with physically plausible box bounds. No tuning,
no regularizer.

**The hidden structure.** Inside the exponential, `alpha` and `beta` appear
only as the ratio `alpha/beta`. Any joint rescaling `(alpha, beta) →
(c·alpha, c·beta)` for `c > 0` leaves the curve unchanged at every point
in the input domain. The declared six-parameter family is therefore
rank five on this input grid — and on *any* input grid, because the
degeneracy is algebraic, not numerical.

---

## 2. The check that passes

The pre-commit test specification was:

> Fit the clean target. Then perturb it with small Gaussian noise and
> refit, 30 bootstrap replicates. Assert that the recovered parameters
> are stable across replicates (per-parameter spread below tolerance).

Implemented as `check1_bootstrap_under_noise` in the reproducer.
`sigma = 5e-4`, `TOL = 1e-2`, fixed default start at the ground truth.

Result:

```
  A        bootstrap spread = 2.11e-03
  p        bootstrap spread = 5.60e-04
  alpha    bootstrap spread = 2.33e-03
  beta     bootstrap spread = 3.57e-03
  q        bootstrap spread = 7.95e-04
  offset   bootstrap spread = 2.85e-04
  VERDICT: PASSED
```

Every parameter, including the two unidentifiable ones, is stable to
three decimals across noise replicates. The test passes.

**Why it passes.** The optimizer's default start is the ground truth
itself. Small noise perturbs the landscape slightly but not enough to
push the optimizer out of the starting basin. The fit falls back into
the same local point each replicate — *which is a basin stability
property, not an identifiability property*. A rank-deficient family
with a strong default basin satisfies bootstrap-under-noise trivially,
because the check never actually explores the flat direction.

The form of the check is "are recovered parameters stable under a
perturbation?" The intent is "are the parameters recoverable from the
functional form of the generating model?" Those are not the same
question, and on a rank-deficient family the form question can answer
*yes* while the intent question answers *no*.

---

## 3. The check that catches

The replacement check:

> Fit the clean target (no noise) from several deliberately varied
> starting points. Assert that the recovered parameters agree across
> starts.

"Deliberately varied" is operationalized as five starts that are not
the optimizer's default and that exercise the feasible region away
from the truth on multiple parameter axes. Implemented as
`check2_adversarial_multistart`. `TOL_REL = 1%`.

Result:

```
  A       : spread=0.0000  rel=0.0%
  p       : spread=0.0000  rel=0.0%
  alpha   : min=1.0049  max=3.7789  spread=2.7740  rel=152.6%
  beta    : min=1.3957  max=5.2485  spread=3.8528  rel=152.6%
  q       : spread=0.0000  rel=0.0%
  offset  : spread=0.0000  rel=0.0%

  alpha/beta ratio (identifiable combination):
      cross-start spread = 7.98e-11
  cross-start fit losses: ~1e-20 to 1e-29  (all starts converge to machine zero)
```

Every start converges to the same curve — the fit losses are at
machine precision — but `alpha` and `beta` individually disagree by
>150% across starts, while their ratio agrees to ~8e-11. Four
parameters recover exactly; two wander freely along a one-dimensional
flat direction whose shadow is the identifiable combination `alpha/beta`.

This is the direct signature of a rank-deficient family, and the
adversarial multi-start check surfaces it on the first run, on clean
data, with no noise model or statistical tuning.

---

## 4. Why the two checks disagree

Both checks exercise the *same optimizer* on the *same functional
form*. They disagree because they probe different properties:

| Check | What it varies | What it actually tests |
|---|---|---|
| Bootstrap under noise (fixed start) | the data | is the chosen optimum *locally stable* under perturbations of the data around the starting basin |
| Adversarial multi-start (clean data) | the initial guess | is the *functional form* identifiable from the evidence surface, independent of where you start |

A rank-deficient family has flat directions in parameter space. Those
flat directions are invisible to the first check if the fixed start
already sits on one of them — the optimizer has no reason to move.
They are impossible to hide from the second check because the starts
are, by construction, on different points of the flat direction, and
the optimizer's box bounds are the only thing stopping them from
sliding all the way.

The fixed start is controlling in the first check's failure. If
the bootstrap were *also* given varied starts, the two checks would
converge. But the bootstrap protocol that was actually written used a
fixed default start, because the check's author was thinking about
"measurement noise on the evidence" rather than "degrees of freedom
in the model."

---

## 5. The general lesson

**Identifiability is a property of the functional form relative to
the evidence surface.** It is not a property of the optimizer's
trajectory. A test that only perturbs the evidence around a fixed
optimum is asking "is this optimum stable?" — which is worth knowing,
but is not a test of identifiability.

A test that perturbs the *starting point* while holding the evidence
fixed is directly asking "do different approaches to this evidence
surface land on the same parameters?" — which is the identifiability
question verbatim.

The two kinds of perturbation are complementary. A clean pre-commit
battery should run both and label them as different properties.
Calling the first one "the identifiability check" is the failure
mode on display.

**A one-line rule.** *If your identifiability check does not vary the
starting point, it is not an identifiability check — it is a basin
stability check wearing the wrong label.*

A corollary: the symptom of rank deficiency under the multi-start
check is very specific and worth recognizing. You get *individual*
parameters with huge cross-start disagreement, but some *combination*
of those parameters — a ratio, a sum, a product — that agrees to
machine precision. That combination is the identifiable direction;
the disagreement axes are flat directions. Reparameterize: replace the
disagreeing parameters with the agreeing combination, delete the
redundant one, and the family is now rank-correct by construction.

In the worked example:

```python
# Before (rank 5 pretending to be rank 6):
def model(phi, psi, A, p, alpha, beta, q, offset):
    ratio = (alpha * phi) / (beta * psi)
    ...

# After:
def model(phi, psi, A, p, gamma, q, offset):
    ratio = (gamma * phi) / psi
    ...
```

The evidence surface is pointwise identical. The parameter space the
fitter sees is now fully identifiable. Both checks pass.

---

## 6. Scope and caveats

- This is a single worked example. The claim is not "bootstrap-under-noise
  is useless" — it is a legitimate stability check. The claim is
  "bootstrap-under-noise labeled as an identifiability check is a
  category error, and multi-start on clean data catches what it misses."
- The rank deficiency here is exact and algebraic. Numerically near-rank-
  deficient families (ill-conditioned but formally full-rank) will show
  the same qualitative pattern under multi-start — large cross-start
  disagreement on some parameters, tight agreement on combinations —
  but the combinations will be approximate rather than exact.
- The multi-start check requires genuinely varied starts. Starts that
  all sit in the same basin as the default will miss flat directions
  the same way the bootstrap does. Randomizing in a tiny ball around
  the default is not enough. Use box-bound-spanning starts.
- The check is not a substitute for analytic rank analysis when you
  can do it. If you can take the Jacobian of your model with respect
  to its parameters on a representative grid and inspect its rank
  symbolically or numerically, do that first — it is cheaper and
  definitive. The multi-start check is the tool for when you cannot.

---

## Reproducer

`rank_deficient_reproducer.py` in this directory. Dependencies: numpy,
scipy. Run:

```
python rank_deficient_reproducer.py
```

No framework, no project-specific vocabulary, no hidden state. The
output matches Sections 2 and 3 above.
