# GP-121 — Cross-Entity Substrates: What Would It Take?

**Status:** OPEN
**Opened:** 2026-04-22
**Category:** Apparatus / Engine / Generalization
**Trigger:** GP-116 weight-norm → cancellation-delta substrate hit
`global_evidence_fit` and `global_extrapolation_gap` gates designed
for smooth curves. Ad-hoc threshold relaxation is not acceptable for
a general-purpose engine.

*All panelist names are fictitious personas used as adversarial reasoning
lenses, not real individuals or endorsements.*

## Eigenquestion

ZTARE was built for substrates of the form n → z(n) where n is an
integer index (1, 2, 3, ...) and z is a smooth numerical observable.
The template library, gate thresholds, holdout protocol, and
farther-tail contract all assume this substrate type.

GP-116 produced a different substrate type: **cross-entity comparison**
where each data point is a different model (Pythia, GPT-2, SmolLM, etc.)
and the observable is a measured property (cancellation delta) as a
function of another measured property (weight norm). The points are:
- Not integer-indexed (weight norms are 24.66, 43.77, 59.19, ...)
- Not smooth (scatter from measurement noise + model heterogeneity)
- Not extrapolatable (there is no "farther tail" — each point is a
  different entity, not the next value in a sequence)
- Small sample (6 points, not 30+)

The gates correctly identified this mismatch. The question is not
"how to silence the gates" but "how should ZTARE handle cross-entity
substrates natively?"

## The Two Substrate Types

### Type A: Sequential Observable (current, well-supported)
- **Examples:** OEIS sequences, sieve densities, training loss curves
- **Structure:** n = 1, 2, 3, ... → z(n) is a smooth function
- **Properties:** monotone or slowly varying, integer domain, 30+ points
- **Holdout:** later values in the sequence (farther tail)
- **Gates calibrated for:** max residual < 5% of data range
- **Template library:** designed for asymptotic forms (log, sqrt, exp, power)

### Type B: Cross-Entity Observable (new, not supported)
- **Examples:** cancellation_delta(weight_norm), loss(model_size),
  accuracy(dataset_size), performance(architecture_property)
- **Structure:** n = measured property → z(n) = measured outcome
- **Properties:** scattered, continuous domain, 5-20 points, noisy
- **Holdout:** held-out entities (different model family, not next value)
- **Gates calibrated for:** need higher tolerance (noise is real, not error)
- **Template library:** needs classification forms (sigmoid, threshold,
  piecewise constant) in addition to smooth forms

## What Needs to Change

### 1. Gate Calibration by Substrate Type

The rubric should declare `substrate_type: sequential | cross_entity`.
Gates auto-calibrate:

| Gate | Sequential | Cross-Entity |
|------|-----------|--------------|
| evidence_fit_threshold | 0.05-0.15 | 0.25-0.40 |
| farther_tail_contract | required | disabled (holdout is entity-based) |
| holdout protocol | last 15% of sequence | held-out entity families |
| min_evidence_points | 20 | 5 |

### 2. Template Library Extension

Cross-entity substrates need forms the current library lacks:
- **Sigmoid/logistic:** z = a / (1 + exp(-b*(n-c))) + d
  (threshold effect — alignment appears above a norm cutoff)
- **Piecewise constant:** z = a if n < c, z = b if n >= c
  (binary classification — two basins)
- **Linear with saturation:** z = max(a*n + b, floor)
  (linear relationship that floors at zero)

### 3. Holdout Protocol

For cross-entity substrates, the holdout should be:
- A different architecture FAMILY (not a different index in the same family)
- Example: fit on 5 transformers, holdout on 1 SSM
- The farther_tail_contract doesn't apply (no "tail")
- Instead: cross-family generalization gate

### 4. Noise Model

Sequential substrates assume the underlying function is exact and
residuals are measurement error. Cross-entity substrates have
INTRINSIC scatter — different training recipes, different init
schemes, different data produce different outcomes even for the
same architecture. The noise is part of the signal.

The gate should distinguish:
- Systematic residual (the form is wrong) — FAIL
- Scattered residual (entity heterogeneity) — PASS with caveat

### 5. Sample Size Awareness

With 6 points, any k=4 form passes by construction (Von Neumann's
elephant). The gate should enforce k < n/3 for cross-entity substrates
(max 2 parameters for 6 points). This prevents overfitting while
allowing the data to speak.

## Debate Questions

1. Is the sequential/cross-entity distinction the right split, or
   are there more substrate types?
2. Should the template library change, or should the gates change,
   or both?
3. How should holdout work for cross-entity substrates when you
   have only 6 data points? Leave-one-out cross-validation?
4. Does the noise model need to be explicit in the rubric, or can
   it be inferred from the evidence statistics?
5. Is this a GP-121 implementation or a v2 architectural change?

## Connection to Other Seams

- **GP-116** (transformer architecture discovery): the motivating
  substrate. Weight-norm → cancellation-delta is the first cross-entity
  substrate ZTARE has encountered.
- **GP-117** (why only kills): the apparatus kills because it was
  calibrated for Type A substrates. Type B substrates need different
  calibration, not looser gates.
- **GP-119** (Inverter): the Inverter should propose cross-entity
  tests ("measure this on another model family") which requires
  understanding that the substrate IS cross-entity.

## Panel Debate Results (2026-04-22)

Panel: Knuth / Dijkstra / Karpathy / Popper / Munger

### Fix 1: Rotation Feedback Loop — IMPLEMENT (Priority 1)
- Unanimous: highest value, lowest risk
- Ulam 1/z residual 0.002 proves the engine finds the answer and ignores it
- Modifications: run full fitting pipeline (not just compress_champion),
  validate composed form on ORIGINAL holdout, Bonferroni correction (disputed by Knuth)
- **STATUS: IMPLEMENTED** in post_underidentified.py Strategy E

### Fix 2: Cross-Entity Substrate Support — DEFER (Priority 3)
- 4-1 defer (Karpathy dissents: ship hard-coded GP-116 override now)
- Single data point (GP-116 weight-norm); building general framework from one
  example is overfitting to the training set
- Ship k < n/3 as standalone constraint immediately
- When 3+ cross-entity substrates exist, build Dijkstra's parametric gate architecture
- Knuth: taxonomy should be smooth-deterministic / smooth-stochastic / sparse-cross-entity (3 types not 2)
- Munger: "what if the engine should NOT handle cross-entity substrates at all?"
- **STATUS: k < n/3 constraint to be shipped. Full framework deferred.**

### Fix 3: GP-115 Trigger Expansion — PARTIAL (Priority 2)
- Ship logging of all GP-115 activity (detectors, suggestions, ratios, rejections)
- Ship constraint-ledger wiring via diagnosis_feedback.py pattern
- DEFER trigger scope expansion (needs logging data first)
- REJECT 1.2x threshold (empirical question; get data from logging)
- Knuth: for 0/42 substrates, run GP-115 on best-FITTING template residuals
  (not champion residuals which don't exist)
- Munger: constraint injection should say "detected X pattern" not "suggests template Y"
- **STATUS: Logging + constraint wiring to be shipped.**

### Meta-Verdict: Architecture, Not Calibration
The root cause is missing feedback edges in the pipeline DAG. Information
flows forward and never flows back. Three edges needed:
1. Rotation results → fitting pipeline (Fix 1, DONE)
2. GP-115 suggestions → constraint ledger → LLM mutator (Fix 3, pending)
3. Gate failure diagnostics → substrate type calibration (Fix 2, deferred)

### Dissents
- Karpathy: ship hard-coded GP-116 override now (unblocks GP-116)
- Knuth: Bonferroni correction is inappropriate for coordinate transforms
  (rotations are not independent hypotheses)

## Checklist

- [x] Panel debate: Knuth/Dijkstra/Karpathy/Popper/Munger
- [x] Fix 1: Rotation feedback loop (IMPLEMENTED)
- [ ] Fix 2: k < n/3 constraint (standalone, not full framework)
- [ ] Fix 3: GP-115 logging + constraint wiring
- [ ] Design substrate_type field for rubric schema (deferred to 3+ substrates)
- [ ] Add sigmoid/threshold templates to template library
- [ ] Test rotation loop on Ulam substrate
- [ ] Backtest: would any prior substrate have been misclassified?

---

*This seam was triggered by an ad-hoc threshold relaxation that the
operator correctly rejected as duct tape. The principle: when the
apparatus doesn't fit the data, change the apparatus, not the
threshold.*
