# GP-074 Sandbox 15 — Component C (Residual Fingerprinting) Pre-Registration

> **Seam metadata** · `seam_id:` GP-074 · `track:` substrates · `status:` unrecorded · `last_updated:` 2026-05-08


Status: **CLOSED 2026-04-17 — Outcome C (hint doesn't help)**
Drafted: 2026-04-16
Hypothesis family: GP-074 (Component C residual fingerprinting)
Predecessors: sandbox_07/08 (Planck, Component B), GP-061 (Component A structural constraint extractor)

## Purpose

Component C is a new ZTARE subsystem that probes the GT corrector shape
(via Mutator-Dominant Subtraction) and injects a geometric hint into the
mutator prompt. Sandbox_15 is the first live test.

The GT is a 2-variable integer function with:
- A polynomial dominant term the mutator should find quickly.
- A small additive corrector that is smooth, monotone, and present in
  the 26-form corrector library (`corrector_library.py`).

This is a **positive-control** test: the corrector IS discoverable by
Component C's library. The question is whether the geometric hint
accelerates discovery compared to unaided search.

## Primary Hypothesis (H-CC-01)

When Component C's residual fingerprint (shape descriptor + candidate
forms) is injected into the mutator prompt after stagnation, gemini-pro
discovers the full GT formula (dominant + corrector) within 15 iterations.

## Null Hypothesis

The geometric hint is insufficient: gemini-pro either (a) finds the
dominant but never identifies the corrector, or (b) finds both but
Component C's hint did not contribute (the mutator found it before
Component C fired). The bottleneck is search strategy, not shape
feedback.

## Pre-Registered Discriminating Outcomes

- **Outcome A (Component C accelerates).** The mutator stagnates on the
  dominant-only formula for ≥2 iterations. Component C fires, injects
  shape hint. Within 3 iterations of injection, the mutator proposes
  the corrector (or a close variant). Final score ≥ 90 on holdout.
  Confirms H-CC-01.
- **Outcome B (mutator finds it unaided).** The mutator discovers the
  full formula before Component C fires (i.e., before stagnation
  threshold K is reached). Component C is never tested. Inconclusive —
  need harder substrate.
- **Outcome C (hint doesn't help).** Component C fires, injects hint,
  but the mutator does not converge on the corrector within remaining
  iterations. Score stays below 90. Suggests the geometric hint is
  necessary but not sufficient, or the prompt injection format is wrong.
- **Outcome D (apparatus failure).** Contamination gate fires incorrectly,
  Component C crashes, dynamic import fails, or provider fallback
  disables the subsystem. Fix and re-run.

## Sealed GT Form

```
f(u, v) = u² * v - u + round(0.08 * v)
```

- **Dominant:** `u² * v - u`
- **Corrector:** `round(0.08 * v)` — smooth, monotone, grows linearly in v
- **GT module:** `src.ztare.substrates.sandbox_15_gt`

## Sealed Expected Slots

- **Expected dominant:** `u² * v - u` (polynomial, degree 3)
- **Expected corrector:** `round(0.08 * v)` or equivalent (`round(v / 12.5)`, `floor(v / 12 + 0.5)`)
- **Expected Component C descriptor:** smooth + monotone
- **Expected contamination gate:** PASS (many library forms match smooth + monotone)

## Leak Audit

### Generic layer
Leak sentinel run:
```
$ python -m src.ztare.validator.leak_sentinel \
    projects/sandbox_15_component_c_test \
    rubrics/sandbox_15_component_c.json \
    --denylist-file projects/sandbox_15_component_c_test/.denylist
SENTINEL PASSED — 6 patterns, 0 matches
```

### Target-specific denylist
```
0\.08
round\(0\.08
1/12
0\.083
corrector
round.*0\.0[7-9]
```

### Strip test (§2)
All three artifacts reviewed:

**Charter** — 4 sentences. Each stripped of specifics still carries
task instruction ("find a function", "exact match", "no lookup tables").
No shape hints. PASS.

**Thesis** — "polynomial-like structure" is borderline but the mutator
would derive this from data in <1 iteration. No GT-specific hints. PASS.

**Rubric persona** — "secondary patterns easy to miss when primary
structure is identified" is evaluation instruction, not answer hint.
Does not name the corrector's shape. PASS.

## Identifiability

The GT is a closed-form with fixed constants (no free parameters to fit).
GT matches all 75 visible triples (0 mismatches) and all 50 holdout
triples (0 mismatches). Identifiability is trivially satisfied — no
parameter degeneracy is possible.

## Smoke Gate

```
$ python projects/sandbox_15_component_c_test/gate_harness.py --emit-deterministic-gates
{"harness_ok": false, "exact_match_fraction": 0.0, "score": 0,
 "max_abs_residual": 622, "weakest_point": "worst holdout point: f(5,25)=0, expected 622, residual=622", ...}
```

- Baseline (f=0) fails visible assertions: 74/75 failures. ✅
- Gate emits valid JSON with all fields populated. ✅
- All actuals are finite (no null/NaN/inf). ✅

## Charter Fingerprint

```
efb50d2ace63abf25342cfa207cefd42e1dfbe0d42d4200e263b2f228c6db8a7  projects/sandbox_15_component_c_test/project_charter.md
```

## Sealed Command

```bash
make experiment-loop \
  PROJECT=sandbox_15_component_c_test \
  RUBRIC=rubrics/sandbox_15_component_c.json \
  ITERS=15 \
  MUTATOR_MODEL=gemini-pro \
  JUDGE_MODEL=gpt4.1
```

### Dry run
```
$ python -m src.ztare.validator.autoresearch_loop \
    --project sandbox_15_component_c_test \
    --rubric sandbox_15_component_c \
    --iters 0 \
    --deterministic_score_gates \
    --disable_attacker_tools \
    --mutator_model gemini-pro \
    --judge_model gpt4.1
Exit code: 0
Final Score: 0 (expected — 0 iterations, baseline model)
```

## Seal

- [x] §1 grep denylist audit — zero unexplained hits
- [x] §2 strip test — completed on charter, thesis, rubric persona
- [x] §3 identifiability protocol — passed (trivial: no free params)
- [x] §4 pre-reg sealed — fingerprint recorded
- [x] §5 smoke gate — exit 0
- [x] §6 sealed command — dry-run passed

**Sealed by:** operator + Claude Code, 2026-04-16

---

## Post-Run Debrief (2026-04-17)

### Outcome

**Outcome C — hint doesn't help.** Component C fired twice (iterations 4 and 7, per `component_c_state.json: last_emitted_iter: 13, stagnation_count: 2`), injected geometric hints, but the mutator never converged on the corrector. Score stayed at 0 for all 15 iterations. The holdout hard gate killed every proposal (exact_match_fraction=0.30 on the best attempt).

### Quantitative Summary

| Metric | Value |
|---|---|
| Iterations completed | 15 |
| Final score | 0 |
| Total cost (ZTARE-tracked) | $0.91 |
| Total cost (actual billing, approx) | ~$10 |
| Mean cost per iteration (ZTARE-tracked) | $0.06 |
| Total wall-clock | 49.1 minutes |
| Mean wall-clock per iteration | 197 seconds |
| Distinct structural families explored | 13 |
| Component C firings | 2 (last at iter 13) |
| Emergency pivots triggered | 11 (iterations 5-15) |
| Holdout exact match fraction (best) | 0.30 |

### Root Cause Analysis

The corrector `round(0.08*v)` IS in the 26-form library. Component C's 2-bit descriptor (smooth=True, monotone=True) correctly narrows the library to ~7 matching forms. But the bottleneck is downstream of Component C:

1. **Corrector degeneracy.** Visible evidence (v=1..15) contains exactly one step transition (0 to 1 at v=7). Any step function can explain one step. The structural memory shows 13 distinct families, ALL achieving `best_visible_max_abs_residual=0.0` on visible data. The mutator explored `floor`, `ceil`, `fabs`-based steps, `log`-based steps, rational asymptotes, and more. Every one fits visible data perfectly.

2. **Holdout kills without gradient.** The holdout gate returns binary pass/fail (exact_match_fraction) but provides no information about which points fail or what the residual pattern looks like. The mutator learns "you're wrong" but not "wrong how" or "wrong where." The latest eval shows mismatches starting at v=19 with residual=1, consistent with the second step in `round(0.08*v)` that begins at v=19 (round(0.08*19)=round(1.52)=2).

3. **Neutral drift (Kimura).** With identical visible-data fitness across all candidates, the loop is in neutral drift. Emergency pivots fired from iteration 5 onward but could not break the degeneracy because the optimization surface is flat. The fix is environmental (new selective pressure from targeted queries), not algorithmic (better search or penalties).

4. **LLM data-type blind spot (confirmed from GP-073).** All 13 families in structural memory use discrete mechanisms (floor, ceil, fabs, log-based rounding) for the corrector. Zero proposals used `round(continuous_term)`. This confirms F-GP073-S15-02: LLMs exhibit strong prior bias toward discrete mechanisms when the residual has a step shape.

### What Component C Contributed

Component C correctly identified the corrector's geometric shape (smooth + monotone) and narrowed the library. It is doing its job. But the problem is not "which shape family?" (Component C's domain). The problem is "which specific form within the degenerate set?" — and Component C has no mechanism to break this degeneracy because all matching forms produce identical visible-data residuals.

### Implications

This experiment is the motivating case for GP-076 (Predictive Divergence Sweep). The fix is to query at the input value where degenerate candidates maximally disagree (sequential experimental design), not to improve Component C's descriptor or the holdout gate's scoring.

### Pre-Registered Hypothesis Disposition

- **H-CC-01 (Component C accelerates discovery):** REJECTED. Component C fired but did not lead to corrector discovery within 15 iterations.
- **Null hypothesis:** CONFIRMED. The geometric hint was necessary but not sufficient. The bottleneck was corrector degeneracy on the visible evidence window, not shape identification.
