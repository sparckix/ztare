# GP-111 — Proactive Closure: Automated Post-Discovery Test Generation

> **Seam metadata** · `seam_id:` GP-111 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: opening
Opened: 2026-04-21

## Eigenquestion

> When the compression primitive finds a gate-passing form, can the apparatus
> automatically generate and execute the tests that a hostile referee would
> demand — without waiting for the operator?

## Motivation

The Lucky number result (a=1.200) passed all gates at iteration 1. The LLM
judge immediately flagged: "no test excludes loglog, sqrt(log), or iterated
log rivals." The operator had to manually ask for the rival exclusion test.
The test took 10 lines of code and 5 seconds to run. The rivals were excluded
at 3-7x gate margin. This closure step should have been automatic.

Pattern: every gate-passing result generates a judge weakest-point that IS the
test specification. The apparatus already has the data, the templates, and the
gates. The only missing piece: a Phase 2.5 that reads the judge feedback and
emits the tests.

## Architecture: Phase 2.5 (Closure Tests)

```
Phase 1 (loop) → Phase 2 (compression) → Phase 2.5 (closure) → Phase 3 (Lean)
```

### Inputs
- `compression_results.json` — which templates passed, with what parameters
- `champion_eval_results.json` — judge's weakest point + probability DAG
- The passing template's fitted parameters
- Evidence files (visible, holdout, farther-tail)

### Outputs
- `closure_tests.json` — structured results of all tests run:
  - Rival exclusion table (all same-k templates, gate results)
  - Coefficient stability (refit at 2x, 5x, 10x if data available)
  - PSLQ identification (already in Lean compiler)
  - Extrapolation test (predict at 100x beyond visible if data available)

### Implementation

```python
# src/ztare/fit/closure_tests.py

def run_closure_tests(
    project_dir: Path,
    compression_results: list[dict],
    judge_weakest_point: str,
) -> dict:
    """Automated post-discovery closure tests.
    
    Reads the judge's weakest point, generates relevant tests,
    runs them deterministically, returns structured results.
    """
    
    passing = [r for r in compression_results if r["gates_passed"]]
    if not passing:
        return {"status": "no_gate_passing_forms", "tests": []}
    
    best = passing[0]
    tests = []
    
    # 1. Rival exclusion: fit ALL same-k templates and report gate results
    # The judge often says "rivals not excluded" — this answers it
    rivals = generate_rival_templates(best, grammar)
    for rival in rivals:
        result = fit_and_gate_test(rival, evidence, gates)
        tests.append({"type": "rival_exclusion", **result})
    
    # 2. Coefficient stability: refit on larger data ranges
    # Uses holdout + farther-tail as extended visible
    for scale in [2, 5, 10]:
        result = refit_at_scale(best, evidence, scale)
        tests.append({"type": "coefficient_stability", "scale": scale, **result})
    
    # 3. PSLQ constant identification
    for param, value in best["params"].items():
        exact = try_identify_constant(value)
        if exact:
            tests.append({"type": "pslq", "param": param, "value": value, "exact": exact})
    
    return {"status": "closure_complete", "tests": tests}
```

### Integration into `make discover`

```makefile
discover:
    # Phase 1: hypothesis loop
    # Phase 2: compression
    # Phase 2.5: closure tests (NEW)
    $(PYTHON) -m src.ztare.fit.closure_tests --project $(PROJECT)
    # Phase 3: Lean proofs
```

## Constraints

1. All tests are DETERMINISTIC — no LLM in the closure loop
2. The test plan is derived from the judge's weakest point + the compression results
3. No new templates are added (that would be grammar expansion, not closure)
4. The closure tests DO NOT change the champion or the gate results
5. The output is ANNOTATION — it strengthens or weakens the finding, doesn't alter it

## Backtest Prediction

| Substrate | Judge weakest point | Closure test needed | Expected result |
|-----------|-------------------|--------------------|----|
| GP-088 | "rivals not excluded" | Rival exclusion | All rivals fail (already verified) |
| Lucky | "loglog not excluded" | Rival exclusion | All rivals fail (verified: 3-7x margin) |
| A001156 | "gate rejected" | N/A (no gate pass) | — |
| A002865 | "gate rejected" | N/A (no gate pass) | — |
| A000607 | "structural reliance" | Rival exclusion | Stage 1 rivals fail |
| Ulam | UNDERIDENTIFIED | Statistical fingerprint (already done) | — |

## Next Actions

- [ ] Implement closure_tests.py
- [ ] Wire into make discover Makefile
- [ ] Backtest on all substrates
- [ ] Update architecture map
