# When the discriminator gets outrun: evidence enrichment and hypothesis-pair specificity

**A short case study in discriminator calibration.**

*Origin: this failure was observed in two successive pre-registered symbolic regression
experiments on the same two-variable law. The first experiment (24 visible points) found
a Wien approximation that failed a farther-tail gate. Evidence was enriched to 33 points
and the experiment was re-run. The second champion — a stretched-exponential form — passed
the same farther-tail gate with comfortable margin. It was structurally different from the
ground truth. The gate, calibrated for the Wien-vs-Planck hypothesis pair, did not
discriminate the new hypothesis pair. This prompted the recognition that discriminators
are hypothesis-pair-specific and must be redesigned when the operative competitor changes.*

---

## Abstract

We exhibit a failure mode in sequential symbolic regression evaluation where evidence
enrichment changes the competitor hypothesis without updating the discriminator. In the
first experiment, 24 visible points produce a Wien approximation as the champion form.
A farther-tail discriminator — relative error above 200% at six probe points — correctly
flags it as the wrong structural class. Evidence is enriched to 33 points and the
experiment is re-run. The new champion is a stretched-exponential (Weibull-like) form
that achieves score 88/100 on the rubric and passes the same farther-tail gate at all
six probe points (maximum 98% relative error). Yet the form is structurally distinct from
the generating law (Planck) and cannot converge to it under any parameter adjustment.

The gate correctly eliminated Wien. It was calibrated for the Wien-vs-Planck hypothesis
pair. After enrichment, the operative pair became Weibull-vs-Planck, and the existing
gate had not been redesigned for this finer distinction. The gate passed because Weibull
and Planck are both in the exponential decay class, and the discriminator's probe regime
had been calibrated to separate the exponential class from the non-exponential class.
Separating two members of the exponential class from each other requires a different
discriminator — one calibrated for the new hypothesis pair.

A self-contained reproducer is provided: `evidence_enrichment_saturation_reproducer.py`
(numpy + scipy only, ~130 lines).

---

## 1. Setup

The ground-truth generating law is the Planck spectral form:

$$
z(x_1, x_2) = \frac{x_1^3}{\exp(x_1 / x_2) - 1}
$$

**Experiment 1 (24 visible points)**

- `x1 ∈ {0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0}` — eight values
- `x2 ∈ {0.5, 1.0, 2.0}` — three values
- Farther-tail discriminator: relative error > 200% at any of
  `(x1, x2) ∈ {5, 6, 8} × {0.5, 1.0}` → form is NOT exponential class

Champion found: **Wien form**
`z = p0 · x1^p2 · x2^p1 · exp(−p3 · x1/x2)`, fitted values
`p0=1.208, p1=0.862, p2=2.160, p3=0.739`. Score 97/100 on rubric. RMSE = 0.021.

Gate verdict: **is_exponential_class = False** (Wien fails at (6.0, 0.5), 238%
relative error — the Planck denominator's `−1` correction becomes controlling in
this regime and Wien cannot express it in its functional class).

**Experiment 2 (33 visible points — enriched)**

Evidence enriched by adding the former farther-tail probe points to the visible set:
- Nine new points: `x1 ∈ {5.0, 6.0, 8.0}` × `x2 ∈ {0.5, 1.0, 2.0}`
- Farther-tail discriminator updated to use `x1 ∈ {10, 12, 15}` × `x2 ∈ {0.5, 1.0}` —
  beyond the new visible maximum

Champion found: **stretched-exponential (Weibull-like) form**

$$
z = A \cdot x_1^{\alpha} \cdot x_2^{\beta - \alpha} \cdot \exp\!\left(-\frac{\alpha}{\delta \cdot r_0^\delta} \cdot \left(\frac{x_1}{x_2}\right)^\delta\right)
$$

with fitted values `A=0.885, α=1.948, δ=1.259, β=2.999, r0=2.822`.
Score 88/100 on rubric. RMSE = 0.043 on enriched visible set.

Gate verdict: **is_exponential_class = True** (passes all six farther-tail checks).

---

## 2. The check that passes

The farther-tail discriminator tests six probe points:

| x1   | x2  | GT (Planck) | Wien prediction | Wien rel. err | Weibull prediction | Weibull rel. err |
|------|-----|-------------|-----------------|---------------|--------------------|------------------|
| 10.0 | 0.5 | 2.00e-6     | 3.62e-5         | **1710%**     | 4.80e-7            | 76%              |
| 12.0 | 0.5 | 6.53e-8     | 2.80e-6         | **4180%**     | 6.82e-9            | 90%              |
| 15.0 | 0.5 | 3.16e-10    | 1.84e-7         | **58100%**    | 5.59e-12           | 98%              |
| 10.0 | 1.0 | 4.54e-2     | 1.07e-1         | 135%          | 3.86e-2            | 15%              |
| 12.0 | 1.0 | 1.06e-2     | 2.99e-2         | 182%          | 7.91e-3            | 26%              |
| 15.0 | 1.0 | 1.03e-3     | 8.26e-3         | **701%**      | 5.26e-4            | 49%              |

Threshold: 200% relative error on any pair → is_exponential_class = False.

Wien fails on four of the six pairs. The form's pure-exponential tail
(`exp(−p3 · x1/x2)`) overestimates Planck at high `x1/x2` because it cannot
express the `−1` correction in the Planck denominator. This correction becomes
negligible for small `x1/x2` (the visible training regime) but controlling in
the tail.

Weibull passes all six pairs. The stretched-exponential decay
(`exp(−K · (x1/x2)^1.259)`) falls off faster than Wien in the tail. At high
`x1/x2` it consistently underestimates Planck by less than 200%. The gate, which
was calibrated to catch tail *overestimation* by Wien, is not triggered by tail
*underestimation* by Weibull.

---

## 3. What the check misses

Weibull passes the gate — but Weibull is not Planck. The structural distinction
is irreducible: no choice of `(A, α, δ, β, r0)` makes the Weibull form converge
to the Planck form. The Planck denominator `exp(u) − 1` saturates to `exp(u)` at
large `u` but carries the correction term `−1` that makes it numerically distinct
from any stretched exponential at intermediate `u`.

The gate's 200% threshold was set by asking: *at what probe points does Wien
overestimate Planck by more than 200%?* That question has the wrong operand for
the new hypothesis pair. For Weibull-vs-Planck, the discriminative regime is not
where Weibull overestimates Planck (it rarely does), but where Weibull decays too
fast relative to Planck at a specific intermediate `x1/x2` regime. A discriminator
for this pair would need to probe a different regime and measure a different quantity
(e.g., the ratio of log-slopes at fixed `x2`, or the asymptotic decay rate).

The farther-tail gate correctly described the evidence boundary: *in the regime
tested, the Wien approximation exceeds 200% error; the Weibull form does not.* That
is a true statement. The error is in interpreting this as evidence that Weibull is
structurally correct.

---

## 4. Why the two checks disagree

| Gate version | Probe regime | Hypothesis pair it was calibrated for | What it actually tests |
|---|---|---|---|
| Farther-tail (x1∈{5,6,8}) | x1/x2 ∈ {5–16} | Wien vs Planck | Does the form overestimate Planck in the regime where Wien's pure exponential diverges? |
| Farther-tail (x1∈{10,12,15}) | x1/x2 ∈ {10–30} | Still Wien vs Planck | Same question, extended range |
| Weibull-vs-Planck discriminator (not yet built) | x1/x2 intermediate | Weibull vs Planck | Does the form's decay exponent match the Planck denominator's implicit exponent? |

The second farther-tail gate extended the probe range but not the hypothesis pair.
After evidence enrichment, the engine no longer produces Wien-class champions. The
gate's adversarial pressure succeeded: it eliminated Wien from the reachable solution
space. But the gate was not updated to ask the next-harder question.

---

## 5. The underlying mechanism

Wien overestimates Planck at high `x1/x2` because `exp(x1/x2) − 1 < exp(x1/x2)`,
making the Planck denominator *smaller* than Wien's fitted exponential decay implies.
In other words, Planck's z-value is *higher* than Wien predicts. The 200% gate catches
this upward divergence.

Weibull's stretched exponent (`δ = 1.259 > 1`) makes its decay faster than a pure
exponential. At high `x1/x2`, Weibull's z-value is *lower* than Planck's. The
divergence is downward. The 200% threshold — designed to catch upward divergence —
is not triggered by downward divergence below 200%. Weibull stays within 98% of
Planck at all tested probe points.

This is not an accidental pass. Evidence enrichment at `x1 ∈ {5,6,8}` gave the
optimizer empirical data that punished the pure-exponential tail. The Weibull form
found the best-fitting stretched exponent that accommodated those points — and that
exponent happened to produce tail behavior that stayed inside the existing gate's
tolerance. The gate and the enriched evidence jointly shaped the solution space;
Weibull is the form that satisfies both constraints simultaneously.

---

## 6. The general lesson

**Discriminator calibration is hypothesis-pair-specific.** A discriminator for
Wien-vs-Planck is not a discriminator for Weibull-vs-Planck. When evidence enrichment
changes the operative competitor hypothesis, the discriminator should be redesigned
for the new pair.

**Evidence enrichment can change the hypothesis pair.** Adding data from a regime where
the current champion struggles will force the optimizer toward forms that fit that regime
better. The better forms may belong to a different structural class — and the existing
discriminator, calibrated against the old class, may not discriminate within the new one.

**The "check" is not wrong — it is asking the wrong question.** The farther-tail gate
correctly establishes that Weibull is in the exponential decay class. It does not establish
that Weibull is the *correct* member of that class. The gate tests class membership, not
identity. Finer discrimination within a structural class requires a discriminator designed
for the intra-class question.

**One-line rule.** *After any evidence enrichment that changes the champion's structural
family, ask whether the existing discriminator was calibrated for the new hypothesis pair
or only for the pair that produced the previous champion. If the latter, redesign the
discriminator before interpreting gate passage as structural confirmation.*

---

## 7. Scope and caveats

- This case study reports one pair of experiments. The mechanism — gate calibration
  specificity — is structural and should generalize, but has been observed here in one
  domain on one apparatus.
- The 200% threshold is not inherently wrong. It was the correct threshold for the
  Wien-Planck pair. The problem is applying it unchanged to the Weibull-Planck pair.
- The Weibull form is a *better* approximation than Wien — it achieves lower relative
  error at the farther-tail probe points and has the correct `x2^3` amplitude scaling.
  Gate passage reflects a genuine improvement in structural class. The issue is that
  improvement within a class is not the same as identification of the correct class member.
- The fix is not to set a stricter threshold (that would retroactively block Weibull's
  real improvement). The fix is to redesign the discriminator for the Weibull-vs-Planck
  pair — to ask the question that Weibull cannot satisfy even with optimal parameters.

---

## Reproducer

`evidence_enrichment_saturation_reproducer.py` in this directory.
Dependencies: numpy, scipy. Run:

```
python evidence_enrichment_saturation_reproducer.py
```

No framework, no project-specific vocabulary, no hidden state. The output matches
Sections 2 and 3 above.
