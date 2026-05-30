# GP-163d Unified Accel — Run Postmortem (10-iter all-zero)

> **Seam metadata** · `seam_id:` GP-163 · `track:` audits · `status:` closed - three apparatus bugs identified, fixes in place · `last_updated:` 2026-05-08


**Status:** closed — three apparatus bugs identified, fixes in place
**Parent:** GP-156 apparatus hardening spec (this seam appends new bugs)
**Date:** 2026-04-25 night
**Substrate:** `projects/gp163d_unified_accel` (RAR/MOND interpolation, 3 system classes, Newton-step test)

---

## Outcome

11 iterations, all score 0. Mutator basin-locked on the canonical
simple-form `(x + sqrt(x² + 4cx))/2` with single fitted constant
`c = 1.3322676295501878e-15` — five orders of magnitude smaller than the
canonical disk a₀ ≈ 1.2e-10. HOLDOUT MRE = 0.58, FARTHER_TAIL MRE = 0.87.
6 of 9 substantive submissions resubmitted the identical form with the
same fitted value.

The fit primitive reported `✅ FIT SUCCESS: max|res|=0.00000,
mean|res|=0.00000` because the residuals (at scale ~1e-11) rounded to
zero in `%.5f` formatting. The display masked a fundamentally wrong fit.

---

## Three apparatus bugs identified

### Bug A — INIT-RANGE TRAP on dimensional constants

**Symptom:** `INIT_RANGE = (-2, 2)` (default) keeps scipy's gradient
descent confined to order(1). When the physical optimum is 5+ orders of
magnitude smaller (e.g. acceleration scale ~1e-10), scipy converges to a
degenerate near-zero basin. The objective is locally flat there because
high-x rows fit `y ≈ x` for any tiny `c`, while low-x rows have
relatively small absolute residuals at the physical y-scale.

**Detection signal:** fitted parameter magnitude is 5+ decades smaller
than `min(|y|)` on visible data, with default init range.

**Fix shipped:** `src/ztare/fit/fit_primitive_features.py` —
sub-physical-scale check added after the existing magnitude-pathology
check. Sets `pathological=True` and writes an actionable
`pathology_reason` pointing at `INIT_RANGE`.

**Sanity verified:** Replayed gp163d iter 1 form on visible subsample —
detector fires, message includes the remedy with concrete bounds.

### Bug B — JUDGE conflates "L3 in-test asserts" with "gate harness"

**Symptom:** judge writes weakest_point as *"harness defect, Level 3
unit tests didn't run"* even when `latest_eval_results.json` has real
gate values (HOLDOUT MRE = 0.58, FARTHER_TAIL MRE = 0.87). Mutator reads
the weakest_point as *"fix the suite, not the form"* and spends
subsequent iters tweaking the suite while the form stays wrong.

**Root cause:** the judge prompt template's "harness defect" language
is triggered by the `fail_other` flag from in-test asserts inside
`test_model.py`'s `__main__` block. The judge does not distinguish
between "in-test assert tripped" (suite-level) and "gate harness
produced numbers but failed thresholds" (gate-level). Both flow to the
same `fail_other` channel.

**Fix shipped (substrate-level):** `rubrics/gp163d_unified_accel.json`
persona updated to explicitly tell the judge that `p.get(name, default)`
is the apparatus-required idiom and that gate-harness numbers (when
present in latest_eval_results.json) take precedence over "harness
defect" rationale.

**Fix deferred (apparatus-level):** the universal judge prompt template
needs to enforce: *"if `latest_eval_results.json` has a numeric
`holdout.mean_relative_error` field, you MUST grade against that value.
Do not invoke 'harness defect' rationale unless the gate values are
absent or non-numeric."* Locating this template requires deeper code
search; logged as task #85, deferred.

### Bug C — 3 R1 strikes per iter on stdlib-only suite contract

**Symptom:** every iter (1, 2, 3, …) burned R1 strike 1 on *"Bounded-
discriminator suite imports non-standard dependencies (features). Use
standard-library-only Python and plain `assert` statements."* Mutator
recovered after 1-3 strikes but the same first-strike pattern repeated
across the run. ~30 wasted R1 calls.

**Root cause:** the existing mutator-prompt block lists "common R1
rejection patterns" but did not separately call out the
`if __name__ == "__main__":` falsification suite. The mutator
interpreted "use real data in tests" as a default behavior and kept
emitting `from features import visible_rows` inside the suite.

**Fix shipped:** `src/ztare/validator/autoresearch_loop.py` — added
explicit pattern #4 to "COMMON R1 REJECTION PATTERNS" block in the
fit_primitive_features context, with the gp163d failure mode named
("Bug C") and a concrete RIGHT/WRONG example. Also added pattern #5
covering Bug A (INIT_RANGE for dimensional constants) so the mutator
sees both fixes in the same prompt segment.

---

## Voids — what the mutator NEVER tried across 11 iters

For posterity, the form-class space the autonomous run did not enter:

1. **Hypothesis S** (c as a function of features). Charter authorized.
   Zero attempts.
2. **Different INIT_RANGE for c.** Mutator stayed at default (-2, 2).
   Zero attempts.
3. **Per-class branches in form** (`c if class=='A' else c·g(features)`).
   Charter explicitly invited. Zero attempts.
4. **Log-space fitting** (fit `log(y)` vs `log(x)`).
5. **Different functional families** (exponential interpolator,
   standard-form interpolator, sigmoid blend).
6. **Abandoning Hypothesis U** when it kept failing. 6 of 9 substantive
   iters were identical Hypothesis U with same `c=1.33e-15`. Basin lock.

The void map confirms: this run failed at the apparatus layer, not at
the mutator's structural-search layer. The structural-form proposal
(simple-form Hypothesis U) was correct and reasonable. The apparatus's
init-range trap + judge-conflation + iter-1 contract friction trapped
the run before structural diversity could emerge.

---

## What this run earned (despite the zero-score)

1. **Three apparatus bugs surfaced with concrete reproducers** — Bug A
   and Bug C have shipped fixes; Bug B has a substrate-level workaround.
2. **The fit-primitive's "max|res|=0.00000" display formatting bug** is
   now publicly documented (residuals at scale ~1e-11 round to zero in
   `%.5f`). Future telemetry should use `%.5g` or scientific notation.
3. **The mutator basin-lock pattern** was confirmed at the apparatus
   level: when the judge keeps reporting "harness defect," the mutator
   does not pivot the form. This is a closed loop only the operator
   could see — useful evidence for paper 5's "fractal Goodhart" thesis.

This run is not a science failure. It is a methodology failure with
clear repair paths. Once the Bug A detector fires and the mutator
reads the actionable `INIT_RANGE` hint, gp163d-class substrates should
converge in 2-3 iters under either Hypothesis U or S.

---

## Relaunch criteria

Before the next gp163d run:

1. ✅ Bug A detector live in `fit_primitive_features.py`.
2. ✅ Bug C prompt warning live in `autoresearch_loop.py`.
3. ✅ Bug B substrate workaround live in `rubrics/gp163d_unified_accel.json`.
4. (defer) Apparatus-level Bug B fix in universal judge prompt.

The mutator's iter 1 should now see the explicit warning that
`from features import …` is rejected inside the `__main__` block, and
should also see the INIT_RANGE pattern when proposing dimensional
constants. If the next run still triggers either bug on iter 1, the
prompt warnings need further hardening.
