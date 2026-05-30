# GP-112 — Margin of Safety Gate (Post-Discovery Stress Testing)

> **Seam metadata** · `seam_id:` GP-112 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening
Opened: 2026-04-21

## Eigenquestion

> When the compression primitive certifies a form, how much margin does the
> certification have? Can the apparatus automatically stress-test the finding
> before the operator publishes?

## Motivation

The Lucky number result (a=1.200) passed all gates at 50K. A manual 500K
stability test revealed: (1) the coefficient drifts 2% under 100x scale
expansion, (2) the template library was missing a loglog correction term
that improves far-tail residuals by 3x, (3) the "certified constant" was
actually a window-dependent estimate absorbing an unresolved correction.

The stability test was run by the operator, not by the apparatus. The
apparatus happily certified a=1.200 and would have done so indefinitely.
The Margin of Safety gate automates what the operator had to do manually.

This is the Buffett/Munger margin of safety applied to scientific claims:
a bridge rated for 10 tons that carries 10 tons has zero margin. A bridge
rated for 10 tons that carries 6 tons has 40% margin. The gate measures
the margin, not just the pass/fail.

## Proposed Tests (Phase 2.5 Extension)

The existing GP-111 Phase 2.5 handles rival exclusion. GP-112 extends it
with three additional stress tests that fire automatically after any
gate-passing compression result:

### 1. Coefficient Stability Under Scale Expansion

Refit the champion template at multiple scales (2x, 5x, 10x of the
visible window, using holdout + farther-tail as extended evidence).
Report the coefficient drift as a percentage per decade of scale.

**Decision rule:** If the leading coefficient drifts more than 1% per
decade of scale expansion, flag "MARGIN_THIN" and recommend extending
the evidence window before publishing a point estimate.

### 2. Grammar Completeness Probe

For each gate-passing template, generate the "natural extension" by
adding one structural term from a curated list:
- If template has log(n): try adding loglog(n)
- If template has n^b: try adding n^(b/2)
- If template has sqrt(n): try adding log(n)
- If template has exp(-bn): try adding exp(-cn^d)

Fit the extended template on the full available evidence. If the
extended template improves far-tail residuals by more than 2x with
acceptable BIC penalty, flag "GRAMMAR_GAP" and name the missing term.

**Decision rule:** If GRAMMAR_GAP fires, the compressed form is a
local approximation, not the asymptotic law. Report the bracket, not
the point estimate.

### 3. Extrapolation Stress Test

Fit on the visible window only. Predict at 10x, 50x, 100x beyond
visible. Report the extrapolation residual at each scale.

**Decision rule:** If 10x extrapolation passes but 100x fails, report
the effective prediction horizon. The claim is "the form generalizes
to Nx" where N is the largest scale at which the gate passes.

## Implementation

```python
# src/ztare/fit/margin_of_safety.py

def margin_of_safety_tests(
    project_dir: Path,
    compression_results: list[dict],
    evidence_visible: list[tuple],
    evidence_holdout: list[tuple],
    evidence_farther: list[tuple],
) -> dict:
    passing = [r for r in compression_results if r["gates_passed"]]
    if not passing:
        return {"status": "no_gate_passing_forms", "tests": []}

    best = passing[0]
    tests = []

    # 1. Coefficient stability at multiple scales
    for scale_name, data in [("2x", holdout), ("5x", farther[:len(farther)//2]),
                              ("10x", farther)]:
        extended = visible + data
        refit = fit_template(best, extended)
        drift = abs(refit["a"] - best["params"]["a"]) / abs(best["params"]["a"])
        tests.append({"type": "coefficient_stability", "scale": scale_name,
                       "drift_pct": drift * 100, "margin_ok": drift < 0.01})

    # 2. Grammar completeness probe
    extensions = generate_natural_extensions(best)
    for ext in extensions:
        ext_fit = fit_template(ext, all_evidence)
        improvement = best["far_res"] / max(ext_fit["far_res"], 1e-10)
        if improvement > 2.0:
            tests.append({"type": "grammar_gap", "missing_term": ext["name"],
                           "improvement": improvement})

    # 3. Extrapolation stress test
    for scale in [10, 50, 100]:
        pred_start = visible[-1][0] * scale
        # ... predict and measure residual

    return {"status": "margin_assessed", "tests": tests}
```

## Integration

```
Phase 1 (loop) → Phase 2 (compression) → Phase 2.5a (rival exclusion, GP-111)
                                        → Phase 2.5b (margin of safety, GP-112)
                                        → Phase 3 (Lean stubs)
```

Both 2.5a and 2.5b fire automatically. Neither changes the champion or
the gate results. Both produce ANNOTATIONS that strengthen or weaken the
finding.

## Backtest Prediction

| Substrate | Test 1 (stability) | Test 2 (grammar) | Test 3 (extrap) |
|-----------|--------------------|-------------------|-----------------|
| GP-088 | a=2.631 stable (known) | No gap expected | 10x PASS |
| Lucky | **a drifts 2%/decade** | **loglog gap detected** | **10x PASS, 100x FAIL** |
| A000009 | a=1.813 stable (known) | No gap expected | 10x PASS |
| A000607 | Stage 2, tight margin | No gap expected | 10x PASS |
| Ulam | UNDERIDENTIFIED | N/A | N/A |

## Relationship to GP-111

GP-111 (rival exclusion) answers: "is there a competing form that also
passes?" GP-112 (margin of safety) answers: "how much room does the
winner have before it breaks?" Both are Phase 2.5. Both are deterministic.
Both annotate without altering. GP-111 owns rival exclusion + PSLQ.
GP-112 owns margin and robustness. No overlap per panel verdict.

---

## Panel Debate (2026-04-21) — Buffett / Popper / Tukey / Taleb

### Round 1

**Buffett:** The three tests map to three failure modes. Coefficient stability from
GP-111 is redundant — give stability to GP-112, keep GP-111 on rival exclusion only.
The 1% drift threshold needs a monotonicity test: directional drift at 0.5% is more
dangerous than oscillatory drift at 1.5%. Never block publication — annotate loudly.
The operator is the underwriter.

**Popper:** The three tests address distinct epistemic concerns. Tests 1 and 3 measure
severity (how demanding were the conditions the form survived). Test 2 is a demarcation
test (is the form the simplest adequate description). Missing: does the form make a
NOVEL PREDICTION that could falsify it? For number-theoretic sequences, this means
predicting L(10^7) and checking.

**Tukey:** Add split-half stability — partition visible, fit separately, compare.
Highest-value addition, requires no new data, would have caught Lucky drift. Add
residual autocorrelation (lag-1 > 0.3 flags structured residuals). The grammar probe
is residual diagnosis by another name. Report quantitative annotations, not just flags.

**Taleb:** The tests assume the same generative process at different scales. Add
convexity: does error grow linearly or accelerate? Report extrapolation residuals as
numbers at 10x, 50x, 100x — not just pass/fail. GRAMMAR_GAP should BLOCK (not just
annotate) because you have positive evidence the form is incomplete.

### Round 2

**Buffett (responding to Taleb):** Blocking depends on a curated extension list that
may be wrong. Compromise: confirmation gate (operator types y/N) instead of hard block.
Not-publishing is the default. Agreed with Tukey on split-half.

**Popper:** GRAMMAR_GAP should block `make publish` but not `make discover`. Discovery
is finding a candidate. Publication is claiming it is true. The distinction matters.
The backtest (5 substrates) has low discriminative power. Need a controlled-misfit
substrate to validate GP-112 properly.

**Tukey:** Add a fourth test: residual autocorrelation. Catches unknown-unknowns the
grammar probe misses because the right extension is not in the curated list.

**Taleb:** Accepts Buffett's confirmation-gate compromise. The correct asymmetry: the
default requires action to override (not-publishing), not action to enforce.

### Consolidated Verdicts

| Q | Verdict |
|---|---------|
| Design | **Five tests, not three.** Add split-half (Tukey) and residual autocorrelation (Tukey). |
| Thresholds | Reasonable conventions. Add monotonicity test to drift. GRAMMAR_SOFT at 1.5x. Rubric-configurable. |
| Block or annotate | **Annotate with confirmation gate for GRAMMAR_GAP.** MARGIN_THIN and extrapolation: advisory. |
| Recursive story | Honest only as methodology refinement. The apparatus did not catch itself; the operator caught it. |
| Priority | **Unanimous: build before next `make discover` run.** |

### Implementation (built 2026-04-21)

Five tests in `src/ztare/fit/margin_of_safety.py`:

1. Split-half stability (Tukey)
2. Coefficient drift with monotonicity test (Buffett)
3. Grammar completeness probe with GRAMMAR_SOFT at 1.5x (Tukey)
4. Residual autocorrelation, lag-1 > 0.3 threshold (Tukey)
5. Extrapolation stress with numerical residuals (Taleb)

GRAMMAR_GAP triggers interactive confirmation gate (Buffett-Taleb compromise).
All other flags are advisory annotations.

---

## Panel Revision: One-Iteration Rule Replaced (2026-04-21)

The operator challenged: "PERSIST + unused candidates is the same report-and-stop
anti-pattern." The panel agreed unanimously.

**Revised rule: exhaust-the-curated-list.** Try all pre-registered extensions (up to 4
from the curated set), with BIC penalty accumulating per candidate (log(trial_idx+1)).
Stop when: (a) a candidate produces EXPLAINED (accept it), or (b) all candidates
exhausted (report PERSIST_ALL_EXHAUSTED as a finding). The curated list is sealed at
first invocation. No additions after observing any result.

**Buffett:** "Stopping mid-checklist because someone said 'one try' is the same as
a value investor screening one stock from a watchlist and going home."

**Popper:** "PERSIST is a falsification signal. Refusing to test remaining hypotheses
in a pre-registered battery abandons the protocol."

**Taleb:** "You applied a fat-tail precaution to a situation with exactly 4 outcomes.
That is superstition, not prudence."

**500K Lucky result (Tier 1):** All 3 curated extensions exhausted (loglog, sqrt,
1/n^2). All PERSIST. lag-1 autocorrelation stuck at 0.934.

**Tier 2 implemented (2026-04-21):** Grammar-derived extensions. For each structural
primitive not in the champion, try adding it. BIC with log(n_grammar_terms) penalty.
5 grammar terms tried (exp_decay, power, loglog, sqrt*log interaction, log^2). All
PERSIST. lag-1 unchanged at 0.934 across all 8 total attempts (3 Tier 1 + 5 Tier 2).

**Conclusion:** The structured residuals in L(n)/n at 500K are not addressable by
any single additive term from the grammar. 8 extensions tried (3 curated + 5
grammar-derived), zero movement in autocorrelation.

## Final Panel Review: Overfitting + Tier Compression (2026-04-21)

Panel: Buffett / Popper / Tukey / Taleb / Number Theorist (sieve specialist).

**Q1 (overfitting):** Unanimous no. Reporting 8 nulls is the opposite of overfitting.
The risk is in continuing past exhaustion, not in what was done.

**Q2 (Tier 3):** Unanimous no. The number theorist identified the mechanism: the
0.934 autocorrelation is a sieve correlation artifact. The lucky sieve's position-
dependent elimination creates short-range dependence in the surviving sequence.
Adjacent L(n)/n values are correlated because the sieve's elimination pattern is
locally periodic. No smooth additive term addresses this because the structure
is in the realization (specific sieve output), not the density function (expected
behavior).

**Q3 (collapse tiers):** Yes. Report as single bounded enumeration: "8 candidate
extensions, BIC-penalized, zero improvement." Provenance is a footnote.

**Q4 (number theorist):** The Hawkins random sieve model predicts density ~1/log(n).
The champion form sqrt(n/log(n)) is consistent with this for the count L(n). The
autocorrelation is from the sieve's correlated point process (analogous to pair
correlation in prime gaps). No closed-form density resolves it.

**Q5 (stop here):** Yes, with one diagnostic. Tukey's residuals-vs-gaps test
was run: U-shaped relationship confirmed. Small gaps (2-6) and large gaps (50+)
both produce large residual changes. Medium gaps (10-14) produce minimum
variation. Spearman rho = -0.07 (weak, because U-shape cancels). The gap
structure drives the residuals. This is a sieve property, not a model deficiency.

**Two publishable findings from the Lucky substrate:**
1. The smooth trend: the compositional form `a*sqrt(n/log(n))+b*log(n)+c/n+d`
   is the BIC-best gate-passing template at 500K. Consistent with Hawkins model.
2. The sieve correlation: residual lag-1 autocorrelation 0.934, driven by the
   gap structure of the sieve output. No smooth additive correction resolves it.
   This is a measured structural property of Lucky number density fluctuations.

**Verdicts enacted:**
- Tiers collapsed into single bounded enumeration in margin_of_safety.py
- No Tier 3 built (pairwise combinations would be curve-fitting, not science)
- Tukey diagnostic run and confirmed
- Letter updated with honest 500K result

---

## Panel Self-Correction: Bracket Retracted (2026-04-21)

The operator challenged the panel: "We fixed the instrument and have 10x more
data. Why report a bracket from the broken instrument?"

**Buffett:** "I confused epistemic humility with operational laziness. You do
not file an annual report using last year's accounting system after discovering
it miscounted inventory."

**Popper:** "I let 'be cautious' override 'be rigorous.' The falsificationist
move was to demand remeasurement, not to bracket the old result."

**Tukey:** "I should have caught this — my job is instrument calibration. I saw
the fix and the data and still endorsed the old run. Comfortable imprecision."

**Taleb:** "A wide interval from a broken instrument is not more honest than a
narrow interval from a working one. It performs the theater of rigor without
the substance."

**Unanimous verdict:** Bracket [1.05, 1.20] RETRACTED. Rerun with corrected
26-template grammar on 500K evidence is the only correct action. The 500K
compression + GP-112 margin of safety result replaces all prior Lucky estimates.

---

## Closed-Loop Remediation Panel (2026-04-21) — Buffett / Popper / Tukey / Taleb

### Question

GP-112 as built reports and stops. The operator asked: "can we feed the
diagnosis back into the discovery process?" Gemini Pro proposed GP-113 as
a separate seam for the remediation controller (auditor/controller
separation). The panel was asked: should the loop close automatically?

### Round 1 verdicts

**Buffett:** Close automatically. The remediation adds only templates the
grammar probe already evaluated. The human adds no information by reading
the JSON and deciding to try them. Preserve original; remediation produces
second candidate. Minimum 1.05x improvement to enter expanded set.

**Popper:** Permissible if diagnosis and test are separate operations.
Full audit trail mandatory (trigger, candidates, delta). One iteration
only: second iteration = compound hypothesis. Self-recursive claim is
Level 2 (grammar-derived self-knowledge), not Level 3 (open-ended).

**Tukey:** Close it. Add residual autocorrelation DELTA diagnostic:
if remediation reduces lag-1 by 50%, emit STRUCTURED_RESIDUALS_EXPLAINED;
otherwise PERSIST. BIC in remediation must use n=len(visible), not
n=len(all_evidence), because holdout/farther informed the extension
selection. Split-half (Test 1) catches drift on visible alone.

**Taleb:** Close it. Bounded downside (original preserved), unbounded
upside (correct asymptotic). One iteration only: two iterations = optimizer
= Goodhart. Grammar-derived extension list (not curated) earns the
self-recursive claim. Emit GRAMMAR_EXTENSION_SIGNAL for RAM layer.

### Round 2 refinements

**Buffett-Taleb compromise on grammar-derived extensions:** Two tiers.
Tier 1: curated (4 extensions), no BIC correction. Tier 2: grammar-derived
(up to 20), with log(n_tried) BIC correction. Build Tier 1 now, defer Tier 2.

**Tukey on promotion:** Extensions selected by remediation in 3+ substrates
should be promoted to permanent library. Deferred to RAM/wiki layer per
ALU principle.

**Popper on claim levels:** Level 1 = thermostat (curated list). Level 2 =
type checker (grammar-derived). Level 3 = scientist (invents primitives).
Honest claim for Tier 1: Level 1. For Tier 2: Level 2.

### Consolidated verdict (unanimous)

| Decision | Verdict |
|----------|---------|
| Auto-close? | YES. One iteration. Preserve original. |
| BIC in remediation | n=len(visible) per Tukey |
| Min improvement | 1.05x per Buffett |
| Tiers | Tier 1 (curated, 4 ext) now. Tier 2 (grammar-derived) deferred. |
| Iteration count | ONE. Second gap = finding, not repair. |
| Self-recursive claim | Level 1 (Tier 1) or Level 2 (Tier 2) |
| Audit trail | trigger, extensions_tried, remediated_champion, margin_delta |
| Residual diagnostic | EXPLAINED vs PERSIST (Tukey) |

### Implementation (2026-04-21)

Closed-loop remediation added to `margin_of_safety.py`:
- Fires when any flag detected
- Collects extensions above 1.05x from grammar probe
- Picks best, re-fits on all_evidence, BIC on n=len(visible)
- Re-runs 3 of 5 margin tests on remediated form
- Reports autocorrelation delta (EXPLAINED vs PERSIST)
- Original champion preserved; remediation is additive
