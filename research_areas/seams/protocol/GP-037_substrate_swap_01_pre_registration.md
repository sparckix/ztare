# GP-037 Substrate-Swap Sandbox 01, Pre-Registration

> **Seam metadata** · `seam_id:` GP-037 · `track:` protocol · `status:` Drafted 2026-04-12. **Sealed 2026-04-12. Frozen 2026-04-12 1 · `last_updated:` 2026-05-17


## Status

Drafted 2026-04-12. **Sealed 2026-04-12. Frozen 2026-04-12 16:08:11 EDT.**

## Execution Disposition

This file remains the sealed design artifact for the full registered `25 -> 100` verifier plan. That full registered plan was **not executed as written**.

What did execute:
- Invalid smoke attempt before the GP-030 gate-declaration contract was fixed
- Short follow-up smokes while GP-035 prompt-surface bugs were still being removed
- One clean exploratory verifier run: `run_id = 1776021031`, `10` iterations, gates engaged, fit primitive exercised, score remained `0`, no viable basin emerged

Cold-artifact outcome from the clean exploratory run:
- deterministic gates engaged: yes
- fit primitive exercised: yes
- semantic traversal observed: yes
- passing basin found: no
- result type: **negative capability result / completed exploratory verifier**

So GP-037 should be treated as **frozen and closed**, but **not** as a fully executed adjudication of the registered `Stage 1 (25)` and `Stage 2 (100)` plan. The carry-forward lesson is that GP-035 is no longer the binding bottleneck; mutator structural diversity / form-family escape is.

## Purpose

3b verifier for GP-035 (mutator missing fit primitive). Tests whether the GP-035 fit primitive closes the residual bottleneck on a non-Planck smooth curve with hidden-slice generalization gates. The single allowed apparatus delta from GP-023 Phase 2 is `enable_fit_primitive: true` in the rubric.

## Primary Hypothesis

A ZTARE mutator equipped with a post-LLM numerical fitting step (GP-035) can discover a composite functional form that clears residual, peak-location, and decay-ratio gates on a hidden holdout slice, the same gate structure that the GP-023 Phase 2 mutator failed to clear without the fit primitive.

## Null Hypothesis

The mutator with the fit primitive still fails to clear the gates. Possible causes:
- The fit primitive is not sufficient (structural proposals are also wrong)
- The bounded-discriminator style guide creates friction for quantitative curve-fit tasks (GP-010)
- The loop-control stagnation heuristic fires destructively (GP-034, known but deferred)

## Controls

- **Form separation:** generating function shares no structural element with Planck sandbox
- **Gate equivalence:** same five-gate pattern, same thresholds
- **Holdout equivalence:** same stride/offset split (30 visible, 10 hidden per sweep)
- **Single delta:** only `enable_fit_primitive` differs from GP-023 Phase 2 apparatus

## Pre-Registered Runtime

**Two-stage smoke + main** (same pattern as GP-023 Phase 2).

**Stage 1 (smoke, 25 iterations):**
- Verify `--deterministic_score_gates` exercises mid-run (at least one candidate evaluated against gates)
- Verify `--no_model_fallback` holds (no gpt-4o in run log)
- Verify GP-035 fit primitive activates (at least one `GP-035 fit primitive:` log line)
- Verify three startup banners: model fallback disabled, deterministic gates enabled, smoke gate pass

**Stage 1 exit checks** (all must hold for Stage 2):
1. Loop exited cleanly at 25 iterations
2. At least one gate evaluation occurred
3. At least one fit primitive invocation occurred (success or failure)
4. No OpenAI-family model in run log

**Stage 2 (main, 100 iterations):**
- Same configuration as Stage 1
- Early stop permitted only if champion passes all 5 gates AND score >= 85 AND >= 30 iterations completed
- Do not stop on early stagnation unless technically invalid

**Required flags:**
- `--deterministic_score_gates`
- `--underidentified_after 100`
- `--no_model_fallback`

**Rubric:** `rubrics/gp037_substrate_swap_01.json` with `enable_fit_primitive: true`

**Mutator/judge family:** Gemini `gemini-2.5-flash` (same as GP-023 Phase 2)

**Pivot regime:** `bounded_discriminator`, GP-021 Phase 1.5 expanded module set

## Harness Smoke Gate

Before main loop:

1. `python projects/gp037_substrate_swap_01/test_model.py` -> must exit non-zero (naive seed fails visible assertions)
2. `python projects/gp037_substrate_swap_01/gate_harness.py --emit-deterministic-gates` -> must exit zero with valid JSON, five gates, all `passed: false`, all `actual` values finite

## Run-State Binding

**Primary artifact:** `projects/gp037_substrate_swap_01/champion_eval_results.json`

**Bands:**
1. **Success:** score >= 85 AND all 5 gates pass AND Mechanical Trace Rule satisfied
2. **Strong-partial:** score >= 70 AND >= 4/5 gates pass AND Mechanical Trace Rule
3. **Failure:** anything else (including score >= 85 with failed gate)
4. **Invalid:** no champion file, harness collapse, smoke-gate failure, missing required flags

## Success Criteria (3b-specific)

The run counts as a positive 3b result if:
1. Champion binds to Success band
2. The champion's functional form contains nonlinear phi-psi coupling
3. The fit primitive produced the fitted parameters (not the LLM's guesses)

A positive 3b result:
- Promotes GP-035 to `active` with n=2
- Unlocks the 3c (Sandbox 03 / Planck Phase 3) decision

## Failure Criteria

The run counts as a negative 3b result if:
1. Run completes (100 iterations or valid early stop) AND
2. Sandbox is uncontaminated AND
3. Post-run harness smoke check passes AND
4. Champion does not bind to Success band

A negative 3b result:
- GP-035 stays at `note/n=1`
- Hypothesis space narrows: fit primitive alone is not sufficient
- Sandbox 03 decision is deferred pending further analysis

## Output Record Requirements

| Artifact | Required |
|---|---|
| Full debate logs | yes |
| Final thesis | yes |
| Final test_model.py | yes |
| Champion file | yes |
| workspace/fit_result.json (final) | yes |
| workspace/latent_distance.jsonl | yes |
| Post-run scoring sheet | yes |

## Seal

**Sealed run commands** (to be filled at seal time):

Stage 1 (smoke):
```bash
python -m src.ztare.validator.autoresearch_loop \
    --project gp037_substrate_swap_01 \
    --rubric gp037_substrate_swap_01 \
    --iters 25 \
    --deterministic_score_gates \
    --underidentified_after 100 \
    --no_model_fallback \
    --mutator_model gemini \
    --judge_model gemini
```

Stage 2 (main):
```bash
python -m src.ztare.validator.autoresearch_loop \
    --project gp037_substrate_swap_01 \
    --rubric gp037_substrate_swap_01 \
    --iters 100 \
    --deterministic_score_gates \
    --underidentified_after 100 \
    --no_model_fallback \
    --mutator_model gemini \
    --judge_model gemini
```

**Pre-run smoke gate verified:** yes, test_model.py exits 1 (naive seed fails visible assertions), gate_harness.py exits 0 with 5 gates all `passed: false` and all `actual` finite (re-verified 2026-04-12 after seed restoration)
**Operator seal timestamp:** 2026-04-12T22:30Z
