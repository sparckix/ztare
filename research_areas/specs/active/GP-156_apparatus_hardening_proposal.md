---
id: GP-156
status: shipped
summary: Proposals 1+2+3 + K_law BIC amendment all shipped 2026-04-25
---

# GP-156 — Apparatus Hardening Proposal (Prose-vs-Code Gap)

**Status:** PROPOSAL — pre-adversarial-review
**Owner:** Claude (manager)
**Visibility:** private (ZTARE architectural change; first-mover IP)
**Created:** 2026-04-25 (post gp154+gp155 mining pass)

## Empirical motivation

Mining of gp154 v3 substrate (8 iters) + gp155 synthetic dense substrate
(4 iters) showed **7 of 12 iters fail on CODE, not on conceptual
discovery**:

| Failure subtype | Count | Notes |
|----|----|----|
| code_crash_import | 5 | TypeError / AttributeError / NameError on module load |
| code_empty | 2 | thesis has no Python block; harness can't run |
| fabricated_visible | 2 | thesis claims visible-MRE the harness contradicts |
| mre_overshoot (substantive but constants wrong) | 3 | code runs, gates fail by ~10× |
| structural_form_ok (concept right) | 4 | regime crossover, logistic blend identified |

**Diagnostic:** the LLM mutator can identify the right STRUCTURE (regime
crossover, sigmoidal blend) at ~33% rate but ships working CODE at ~25%
rate. The gap between "I know what to write" and "I shipped working
Python with correct numerical constants" is the substrate-independent
bottleneck.

## What's already shipped (Proposal 1 — done 2026-04-25)

`validate_python_suite_imports` in `src/ztare/fit/mutation_suite_guard.py`,
wired into `_prepare_mutation_candidate` at autoresearch_loop.py:1730.
Catches at R1 reject time:
- SyntaxError (compile stage)
- TypeError / AttributeError / NameError / ImportError at module load
- Missing `I_model` definition

Validated against 6 scenarios incl. the gp155 iter-1 TypeError pattern
and the gp154 iter-3 AttributeError pattern. All correctly classified.

This intervention is structural — it applies to all current and future
runs without requiring rubric changes. Cost: 1 hr; ongoing benefit: every
import-crash iter is now caught at R1 instead of consuming an iteration.

## Proposal 2 — Visible-MRE attestation (~3 hrs)

### Problem

Mutator wrote "visible MRE = 0.23" in iter 6 of gp154. Harness reported
holdout MRE = 2.01 with the SAME code. The judge correctly called this
"either fabricated or measured on a different implementation than what
was submitted to the harness." But the judge's catch was downstream —
the iteration was already consumed.

### Mechanism

When the mutator's MutationDeclaration JSON header includes a
`visible_mre_claim: float` field (or the prose contains the pattern
`MRE_visible\s*=\s*([0-9.]+)`), the apparatus:

1. After R1 reject-or-accept gate, runs `test_model.evaluate_visible()`
   on the candidate's I_model
2. Compares claimed vs measured MRE
3. If `|claimed - measured| > 0.05` (absolute), R1 rejects with sharp
   message: *"You claimed visible MRE = X but evaluate_visible() returned
   Y. Either your formula doesn't match what you wrote in test_model.py,
   or you fabricated the number. Fix and resubmit."*

### Scope

- Applies only when the mutator makes a numerical claim about visible MRE
- Skipped if no claim is made
- Threshold (0.05 absolute) is conservative — designed to catch
  10×+ discrepancies (the actual failure mode), not penalise rounding

### Risks (for ZTARE-on-ZTARE review to scrutinise)

R1: **Mutator stops claiming visible MRE**, gaming around the
attestation. Mitigation: if no claim is made, judge's "Holdout
Validation Rigor" criterion penalises the absence of a pre-commit. The
mutator can game by silence but the rubric punishes silence.

R2: **Float precision / non-determinism** — what if the candidate uses a
random seed? Mitigation: enforce deterministic visible-set evaluation;
if mutator's I_model is non-deterministic, that's its own R1 failure
(the harness needs deterministic predictions).

R3: **Visible-MRE is not the right number to attest** — maybe the
mutator's claim is about a different metric (e.g. R²). Mitigation:
attestation only fires on the literal `MRE_visible` regex; if mutator
claims R², the regex doesn't match and no attestation runs.

### Implementation sketch

```python
# In _prepare_mutation_candidate, after R1 import-time exec:
if python_code is not None and visible_mre_claim is not None:
    measured = run_visible_evaluation(python_code, project_dir=PROJECT_DIR)
    if abs(measured - visible_mre_claim) > 0.05:
        raise ValueError(
            f"Visible MRE attestation failed: claimed={visible_mre_claim:.4f} "
            f"but evaluate_visible() returned {measured:.4f}. Discrepancy "
            f"{abs(measured-visible_mre_claim):.4f} exceeds 0.05 tolerance. "
            f"Fix the prose-vs-code gap before resubmission."
        )
```

## Proposal 3 — Feature-vector fit primitive (~1-2 days)

### Problem

LLMs are bad at numerical constant optimization. gp155 iter 1 wrote a
"three-parameter logistic blend" which is the correct conceptual answer
— but the implementation crashed because the mutator tried to manually
construct fit parameters and got the type wrong. ZTARE's existing
`fit_primitive` (`src/ztare/fit/fit_primitive.py`) uses
`scipy.optimize.curve_fit` to nail constants given a parametric form
— but it requires 1D paired (x, y) data and is gated by the rubric's
`enable_fit_primitive` flag.

For substrates whose I_model takes a feature DICT (gp154, gp155),
fit_primitive doesn't engage. The mutator is forced to guess constants
manually. They fail.

### Mechanism

A new primitive: `fit_primitive_features` in
`src/ztare/fit/fit_primitive_features.py` (parallel to fit_primitive.py).

Inputs:
- `parametric_form`: a Python expression string with named parameters
  (e.g. `"a + b * sigmoid((c - features['log10_N_params']) / s)"`)
- `parameter_names`: list of free parameters to fit (e.g. `["a", "b", "c", "s"]`)
- `feature_keys`: the feature dict keys the form references
- Visible data: `[(features_dict_i, y_observed_i) for i in 0..n]`

Fit logic:
1. Parse the parametric form into a callable taking
   `(features_dict, params)` and returning a scalar.
2. Construct an objective: sum of squared (or absolute) residuals over
   the visible set.
3. `scipy.optimize.minimize` with multi-start (3 starts default; 5 if
   stagnation_count >= 3).
4. Return `FitSuccess(fitted_params, max_abs_residual,
   convergence_classification)` analogous to existing fit_primitive.

Mutator interface:

```python
# In thesis.md / test_model.py:
PARAMETRIC_FORM = "a + b * sigmoid((c - features['log10_N_params']) / s)"
PARAMETER_NAMES = ["a", "b", "c", "s"]

def I_model(features, params=MODEL_PARAMS):
    a, b, c, s = params["a"], params["b"], params["c"], params["s"]
    return a + b * (1.0 / (1.0 + math.exp(-(c - features['log10_N_params']) / s)))
```

The apparatus reads `PARAMETRIC_FORM` + `PARAMETER_NAMES`, fits via
fit_primitive_features, substitutes `MODEL_PARAMS = {fitted_dict}`,
re-runs the harness with fitted constants.

### Why this unblocks the substrate ceiling

For gp155: the ground-truth law is
`α = 1 + (2/d - 1) * sigmoid((0.5*d + 3 - log10_N) / 0.5)`. Five free
parameters: the `2`, the `0.5` slope, the `3` intercept, the `0.5`
smoothness, and the `1` baseline. A mutator who proposes the FORM
without fitting the constants would currently fail the gate. With
fit_primitive_features, scipy nails the constants and the gate passes.

For gp154: similar — mutator declares regime selector + per-modality
constants, scipy fits the constants from visible data. Hardcoded
"oracle" values that the iter-2 judge correctly criticised become
data-derived constants.

### Risks (for ZTARE-on-ZTARE review to scrutinise)

R4: **Overfit on visible** → fails on holdout. Mitigation: fit_primitive
already has K_law parameter-count budget. fit_primitive_features
inherits it. Holdout gate is the safety net.

R5: **Parametric form expressiveness** — if the form is wrong, no
fitting will save it. Mitigation: this is correct behaviour — wrong
form should fail the gate. The primitive doesn't promise discovery, it
promises that GIVEN a correct form, the constants are fittable.

R6: **Eval injection risk** — the parametric form is a string parsed by
the apparatus. Could the mutator inject arbitrary code? Mitigation:
parse via `ast.parse` + whitelist (allowed nodes: BinOp, UnaryOp, Call,
Name, Constant, Subscript, Attribute on math/numpy). Reject any other
AST node. Same pattern as existing fit_primitive's expression parser.

R7: **Multi-start cost** — 3-5 scipy.optimize calls per fit could be
slow. Mitigation: scipy.optimize.minimize on 100-row visible set is
~milliseconds. Negligible vs API call cost.

R8: **Feature dict ordering** — different features.py implementations
might iterate the dict in different orders, leading to fit non-
determinism. Mitigation: enforce sorted feature key access via the
rubric's `feature_keys()` canonical order.

### Implementation scope

Files to ship:
- `src/ztare/fit/fit_primitive_features.py` (~250 LoC)
- `src/ztare/fit/tests/fit_primitive_features_fixture_regression.py`
- Wire-in at autoresearch_loop.py as a **SIBLING block** to the existing
  fit_primitive call (NOT nested inside `if rubric_data.get("enable_fit_primitive", ...)`).
  Wire-in must be at the iter-body scope, gated ONLY by rubric flag
  `enable_fit_primitive_features`. **CORRECTION 2026-04-25**: original
  spec said "near existing fit_primitive call (line ~4255)" — "near"
  was ambiguous and I implemented as a CHILD branch (nested inside the
  1D fit_primitive `if`-block). gp155 has `enable_fit_primitive=false`
  so the entire 1D branch was skipped, taking the wire-in with it.
  Result: 30+ iters with NO Proposal 3 engagement. Bug surfaced when
  user noticed verbose telemetry banner never printed despite shipped.
  Spec now corrected to require SIBLING placement explicitly.
- Documentation: extend `docs/concepts/architecture.md` Framer section
  with sibling-primitive description

## Sequencing

1. **Done now (Proposal 1)** — R1 import-time exec dry-run. Shipped.
2. **Subject to review** — Proposals 2 and 3 above, after ZTARE-on-ZTARE
   adversarial audit (gp156 review project).
3. **After review** — implement whatever survives, ship.

## ZTARE-on-ZTARE review (gp156)

This proposal is being submitted as the substrate for a recursive
self-improvement audit. The auditor (ZTARE itself, in Newton mode) will
look for:

- Inversion failures: ways Proposal 2/3 could DEGRADE the apparatus
  rather than improve it
- Risks not enumerated here (R-list above is the seed; auditor extends)
- Specification gaps that would let a mutator game around the new
  guards
- Compositional interactions with existing gates (G-CIRC, G-FALSIFY,
  Framer, holdout-hard-gate)
- Primitive-availability assumptions that aren't met today

Audit rubric: Newton-mode, 12 iters, K_law ≤ 5 for any
counter-proposed redesign.

## Related work

- GP-152 / GP-153: ZTARE-on-ZTARE Framer architectural audit (precedent
  for this recursive pattern)
- GP-148: Mining apparatus that surfaced the persistence-cycling
  champion profile
- RH-13/14/15/17 in `docs/concepts/anti_pattern_catalog.md`: failure
  modes this proposal addresses

## Decision log

- **2026-04-25** — Proposal 1 (R1 import-time exec) shipped after live
  diagnosis from gp154 iters 1-7 and gp155 iters 1-4. Proposals 2 and 3
  drafted same session for ZTARE-on-ZTARE review before code is
  written.

## Amendment 2026-04-25 — K_law budget moves from flat-5 to BIC-justified-8

### What changed

The original spec (Proposal 3, line 179) said *"fit_primitive already has
K_law parameter-count budget"* and inherited the flat `k_law_max=5`. The
audit project gp156 (line 243) ran with *"Newton-mode, 12 iters, K_law ≤
5 for any counter-proposed redesign"* — the same flat budget.

**Amendment:** the flat K_law=5 cap is replaced by BIC-justified K up
to a hard ceiling of 8. Implementation in
`src/ztare/fit/fit_primitive_features.py:fit_features`:

```
σ̂² = SSE / N        (mean squared residual on visible rows)
BIC = N · log(σ̂²) + K · log(N)
```

`FeatureFitResult` now carries `bic`, `sigma_sq`, `n_fit_rows`, `k_params`
fields. `fit_features_result.json` exposes them. The 🧮 dispatch banner
prints BIC alongside residual stats so the operator and the judge can
see whether each parameter earned its bits.

### Why the flat-5 cap was wrong

1. **gp152/153 ZTARE-on-ZTARE audit failed to validate it** (postmortem
   at `research_areas/private/postmortems/gp152_153_ztare_on_ztare_sycophancy_loop_2026_04_25.md:43`):
   *"the K_law claim of 5 hid 16+ hardcoded constants"*. The flat cap
   was rubber-stamped by an audit that itself was a sycophancy loop.

2. **gp154 substrate has 13 modalities × 5 architectures**. A real
   cross-domain scaling law might genuinely need 6-8 parameters
   (Chinchilla alone has 5; adding modality structure pushes to 6-7).
   The flat 5-cap forced gpt-4.1 to declare incomplete one-hot
   encodings (5 params for 5 of 13 modalities) which the K_law gate
   rejected — a false negative.

3. **BIC is the principled replacement**, derived in GP-152 framer
   spec v2.0 at section 2 (`MDL_v2 = N·log(σ̂²_raw) + K·log(N)`).
   That spec was specifically designed to replace flat K caps with
   a Bayesian-info-criterion-justified budget. Frame-invariance was
   proven; backtest at scripts/public/backtest_framer_mdl_v2_vs_v1.py shows
   0.000 bits drift.

### Citation

The BIC formula is identical to the framer spec v2.0 because it's
the same Bayesian Information Criterion in both contexts: the only
difference is that feature-vector fits have no h_in/h_out framing
transforms, so K_total = K_law (no K_h_in / K_h_out terms).

### Hard ceiling rationale (k_law_max=8)

A hard ceiling is preserved at K=8 to defend against a degenerate case:
on a small visible set (say N=20), a K=20 model fits perfectly via
memorization with σ̂² → 0, BIC → -∞. BIC alone won't catch this;
the hard ceiling will. K=8 is chosen because:
- Allows gp154 13-modality substrate room (modality + architecture
  could realistically need 6-7 effective parameters)
- Below the typical N/2 threshold where memorization risk dominates
  (gp154/gp155 visible sets have N ≥ 72)
- One above the largest published scaling law (Chinchilla = 5),
  giving the mutator room to find STRUCTURAL refinements

### Forward-compatibility with v5.0 Cage Orchestrator

The `bic` field on `FeatureFitResult` is the decisive fix.
v5.0 Cage Orchestrator (GP-157 seam) will inherit BIC as the
canonical K-justification metric across both 1D and N-D fitters,
unifying the framer spec's MDL formula with the feature-vector
fitter. The flat K_law=5 era ends here.


---

## Postmortem appendix — gp163d_unified_accel run (2026-04-25 night)

A 10-iteration run on `gp163d_unified_accel` (RAR/MOND interpolation, 3
system classes) produced score=0 on every iter despite a structurally-
correct simple-form Hypothesis U submission. Postmortem details in
`research_areas/private/seams/GP-163d_unified_accel_run_postmortem.md`.

Three bugs identified and recorded against this spec:

### Bug A — INIT-RANGE TRAP on dimensional constants

`fit_primitive_features` default INIT_RANGE = (-2, 2). When the physical
scale of a fitted constant is far from order(1) (e.g. an acceleration
constant ~1e-10), scipy's gradient descent cannot traverse the gap and
converges to a degenerate near-zero basin. On gp163d, c fitted to
1.33e-15 vs canonical 1.2e-10. The objective was locally flat near zero
because high-x rows fit `y ≈ x` for any tiny `c`, masking the wrong fit.

**Fix shipped (this spec):** sub-physical-scale detector added after the
existing magnitude-pathology check in `fit_primitive_features.py`. Sets
`pathological=True` and emits `pathology_reason` with concrete remedy
(declare INIT_RANGE bounds spanning the physical scale).

### Bug B — JUDGE conflates "L3 in-test asserts" with "gate harness"

Judge writes weakest_point as "harness defect, L3 didn't run" even when
gate harness produced real numbers (HOLDOUT/FARTHER MRE present in
`latest_eval_results.json`). Mutator interprets this as "fix the suite,
not the form" and basin-locks. Both signal-failure modes flow through
the same `fail_other` channel.

**Fix shipped (substrate-level):** rubric persona for gp163d explicitly
exempts `p.get(name, default)` (the apparatus-required idiom) and tells
the judge to grade against gate values when present.

**Fix deferred (apparatus-level):** universal judge prompt template
needs branch logic — *"if `latest_eval_results.json.holdout.mean_relative_error`
is numeric, grade against that; do not invoke 'harness defect' rationale
when gate values are present."* Logged for next apparatus pass.

### Bug C — 3 R1 strikes per iter on stdlib-only suite contract

Every iter burned R1 strike 1 on `import features` inside the
`if __name__ == "__main__":` falsification suite. Mutator recovered but
the same first-strike pattern repeated. ~30 wasted R1 calls across 11
iters.

**Fix shipped (this spec):** `autoresearch_loop.py` mutator-prompt
fit_primitive_features context now includes pattern #4 ("stdlib-only in
suite, do NOT `import features`") and pattern #5 ("INIT_RANGE for
dimensional constants") with concrete RIGHT/WRONG examples. References
the gp163d failure modes by name so the mutator sees the cost of
ignoring them.

### Forward-compatibility note

These three bugs co-firing produced an apparently substrate-failure
that was actually entirely apparatus-side. The structural-form proposal
(simple-form Hypothesis U) was correct on every iter; the run failed at
the layer below structural search. This is a class of failure the
fractal-Goodhart thesis (paper 5) predicts: optimization pressure at
one layer (the mutator) is short-circuited by an unrelated layer's
measurement instrument (the fit primitive's display formatting + the
judge's misclassification). Document as Cage gate candidate in v5.1:
detect "judge invokes 'harness defect' AND gate values present" as a
contract violation between the eval channel and the gate channel.

---

## Deferred follow-ups from 2026-04-25 deep audit (lower priority)

These are non-blocking apparatus-side hardenings logged for a future
GP-156 v2 pass. Reference: `research_areas/private/seams/2026_04_25_deep_audit_findings.md`.

### F2 — `substitute_fitted_model_params` brace handling
Regex at `fit_primitive_features.py:1403` matches `MODEL_PARAMS = {[^{}]*}`,
which rejects ANY nested-brace literal (e.g. mutator declares
`MODEL_PARAMS = {'cfg': {'a': 1.0}}`). Two fixes possible:
- (a) extend regex to permit one level of nesting: `\{(?:[^{}]|\{[^{}]*\})*\}`,
- (b) validate the mutator's MODEL_PARAMS literal at submission time
  with `ast.literal_eval`, reject anything that's not a flat
  `dict[str, float]` upfront. Option (b) is preferred — it gives an
  earlier, clearer error than a silent post-fit substitution miss.

### F3 — `auto_escalate` arithmetic widening
The init-range escalation widens additively around the midpoint, so
5× / 25× steps stay within the same decade. For dimensional constants
where the physical optimum is OOM-distant from the default range,
arithmetic widening cannot escape. Replace with **logarithmic
widening**: span the bounds geometrically (multiply by 10× / 100× /
1000×) instead of additively. Combine with the Bug A detector so the
escalation only triggers when sub-physical-scale is flagged.

### F4 — `convergence_classification` y-scale-relative
Current convergence classifier (`converged_clean` / `converged_marginal`
/ `no_convergence`) is computed from raw residuals against fixed
absolute thresholds, which is scale-dependent. Sub-physical-scale fits
trivially "converge" (residuals tiny in absolute terms); large-y-scale
fits never converge by the same threshold. Make the classifier read
`mean_abs_residual / max(|y|)` so the threshold is dimensionless. Pair
with `convergence_relative_threshold` rubric flag (default 0.05) for
substrate-specific tuning.

---

## 2026-04-26 morning — F3+F4 PULLED FORWARD AND SHIPPED

User pulled F3+F4 forward from "deferred follow-ups" because they
directly strengthen the kernel against the gp163d-class init-range trap.

**Status of F1-F5:**

- ✅ **F3** (logarithmic init-range escalation): SHIPPED in
  `fit_primitive_features.py` line ~1037. Replaces 5×/25× arithmetic
  widening with log-uniform sampling across decade bands (1e-6..1e3,
  1e-12..1e6, 1e-18..1e9). Decade-spanning exploration guaranteed for
  any dimensional constant.
- ✅ **F4** (y-scale-relative convergence): SHIPPED in same function,
  ~line 1037. Convergence threshold = (mean|y|)² × 0.01, not flat
  1e-3. Substrates with y ≪ 1 no longer get spurious "converged"
  reports that block escalation. Substrates with y ≫ 1 still need
  legitimate fits to converge.
- ⏸ **F1** (`validate_substrate_meta` at every Cage entry): logged in
  `GP-157_cage_orchestrator_substrate_agnostic_dispatch.md`. Not
  pulled forward — Cage-side concern, lower leverage than F3/F4.
- ⏸ **F2** (substitute_fitted_model_params nested-dict validation):
  logged but not shipped. Defensive harden, not blocking.
- ⏸ **F5** (typed `EngagementSentinel | GateVerdict`): logged in
  GP-157 seam. Defensive, blocked by Phase 3b Cage promotion.

**Verification (gp163d simple-form fit, full visible 2585 rows, n_starts=8):**

| Pre-fix | Post F3+F4 |
|---|---|
| c = 1.3322676295501878e-15 (5+ decades wrong) | c = 4.04e-11 (within 0.5 decades of canonical 1.2e-10) |
| classification: converged_clean (false positive) | classification: no_convergence (correct — fit is structurally bad) |
| pathological: True (Bug A detector) | pathological: False (B3 guard correctly recognizes the fit is now OK at this scale) |

The 10⁴× improvement in fit accuracy means the next gp163d-class
relaunch should produce a genuinely fitted form on iter 1 instead of
basin-locking on the init-range trap.
