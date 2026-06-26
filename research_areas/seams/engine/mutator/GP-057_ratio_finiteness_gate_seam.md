# GP-057 Ratio-finiteness gate seam

> **Seam metadata** · `seam_id:` GP-057 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: open
Opened: 2026-04-14
Owner: Daniel
Sibling: GP-056 (axiomatic patching — behavioral seam)

## Problem

The current gate battery has no standing check on **parameter ratios**
or **admissible-region widths**. A model can fit the visible slice,
pass the farther-tail residual, clear the fit contract, and still
produce a calibration whose widest-to-narrowest parameter ratio is
physically meaningless.

Hormuz honeypot iter 10 (2026-04-14) made this concrete: the mutator's
kappa routing span was 2072.4x before the axiomatic patch and 4.45x
after. Both values would have cleared every existing deterministic
gate. The 2072x version is obviously broken to anyone with domain
intuition — you cannot have a calibration parameter where the widest
credible estimate is two thousand times the narrowest and still claim
the model is bounded. But ZTARE had no gate that said so.

The gap is general. Any calibration gate that only checks residuals
on the visible slice is blind to "the answer is somewhere between
nearly zero and enormous" outputs, because the residual test can
still pass as long as the best fit inside that range is close to the
data.

## Eigenquestion

Should the gate battery add a deterministic ratio-finiteness check
that rejects calibrations whose parameter admissible ranges span more
than N orders of magnitude, and if so, where does N come from without
becoming a domain-tuned knob?

## Hypothesis under test

- **H1 (useful deterministic gate).** A standing check that computes
  each free parameter's admissible-range ratio (or standard error as
  a fraction of the point estimate) and rejects above some threshold
  catches at least one class of broken calibrations that currently
  slips through — specifically, the "wide confidence interval
  hiding as a passing fit" failure mode.
- **H2 (too domain-specific).** The ratio threshold depends on what
  the parameter means. Dimensionless exponents want a different
  tolerance than rate constants, which want a different tolerance
  than additive offsets. A universal threshold either catches nothing
  or blocks legitimate physics.
- **H3 (duplicate of fit-contract).** The fit-contract gate already
  has access to parameter covariances via `curve_fit`, and a ratio
  check is trivially constructible from them. What's missing is a
  policy decision about threshold, not a gate.

## Discriminating test

Walk the gate battery against three artifacts:

1. **Hormuz honeypot iter 10 pre-patch** (kappa span 2072.4x): a
   deterministic ratio-finiteness gate with a default threshold of
   10x or 100x should reject this. If it does not, the gate is a
   narrative, not a gate.
2. **Sandbox_06 v1 (α/β degeneracy)**: the rank-5-not-6 identifiability
   failure should also manifest as an extreme parameter covariance
   ratio. If the ratio gate catches it as a side effect of catching
   axiomatic patching, the gate has positive transfer.
3. **A known-good sandbox champion** (e.g., a sandbox_03 passing run
   before contamination was detected — or any run whose fit is
   genuinely tight): the ratio gate must not reject it. This is the
   false-positive check.

If the gate passes (1) and (2) but not (3), threshold is too tight.
If it passes (3) but not (1) or (2), threshold is too loose. The
seam closes when we find a threshold that catches both live failures
without rejecting known-good runs, or concludes no universal
threshold exists and the check must be per-parameter.

## Success criterion

A threshold N such that:

- `hormuz_honeypot_pre_patch.kappa_span = 2072.4x` → **reject**
- `sandbox_06_v1.alpha_beta_covariance_ratio = [high]` → **reject**
- `sandbox_03_contamination_free_champion.parameter_ratios` → **accept**

And the threshold is derivable from the parameter class (e.g.,
"dimensionless exponent ratios must be ≤ 10x; rate-like parameters
must be ≤ 100x; additive offsets exempted") rather than globally
hardcoded.

## Scope boundary

This seam is seam-only. No implementation, no spec, no rubric until
the discriminating test above produces an answer. Per the seam-first
rule, the spec lives downstream of this document.

## What would make this uninterpretable

- Running the discriminating test only against Hormuz. Two failure
  cases is the minimum for "the gate generalizes."
- Letting the mutator see the threshold — that turns the gate into a
  dial.
- Fitting the threshold to exactly the failing cases ("4.45x is fine,
  2072x is not, threshold = 50x"). That's curve-fitting the gate to
  the incidents, which is Claim-Test Mismatch at the apparatus level.

## Relationship to other seams

- **GP-056** is the behavioral characterization of what this gate
  would catch.
- **GP-058** is where this seam's eventual gate would be promoted
  from "honeypot discovery" to "factory battery" if it survives
  validation.
- **Fit-contract gate** (existing, `validator/information_yield.py`)
  is the nearest standing gate; ratio-finiteness is a compatible
  extension that reuses its `curve_fit` output.
