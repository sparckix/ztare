# GP-023 Planck Sandbox 05, Stronger-Mutator Successor Pre-Registration

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` Drafted 2026-04-13 22:16:54 EDT as the post-`sandbox_04` str · `last_updated:` 2026-05-17


## Status

Drafted 2026-04-13 22:16:54 EDT as the post-`sandbox_04` stronger-mutator
successor. Unsealed.

This packet holds substrate, apparatus, rubric, and judge fixed and changes
only the mutator family and iteration budget.

## Purpose

`sandbox_04` showed that apparatus feedback changes search topology and enables
real primitive-cone escape, but it did not produce a better champion than the
score-50 farther-tail ceiling.

Sandbox 05 asks the next narrower question:

> once apparatus-blindness has been paid down, is the remaining bottleneck
> mutator/search capacity?

## Experiment Object

Inherited unchanged from Sandbox 04:

- hidden generator class
- visible slice
- hidden in-range holdout
- farther-tail holdout
- charter gates
- GP-046 asymptotic-claim contract
- GP-035 fit primitive
- cold residual successor mode
- GP-048 telemetry
- GP-048 primitive-cone stagnation injection
- sanitized farther-tail veto
- judge family

Changed for Sandbox 05:

- runtime mutator family: `gemini-pro`
- hard iteration cap: `10`

## Primary Hypothesis

With the full Sandbox 04 apparatus packet held fixed, a stronger mutator family
can produce a champion that improves on the repeated score-50 ceiling and
either clears `farther_tail_global_residual` or materially narrows it.

## Null Hypothesis

Even with the stronger mutator family, the run either stays near the same
farther-tail ceiling, oscillates between the same near-pass and collapse
families, or fails to produce a materially stronger champion within 10
iterations.

## Runtime Contract

Required flags:

- `--project gp023_planck_sandbox_05`
- `--rubric gp023_planck_sandbox_05`
- `--iters 10`
- `--mutator_model gemini-pro`
- `--judge_model gemini`
- `--deterministic_score_gates`
- `--underidentified_after 20`
- `--no_model_fallback`

Required pre-run command:

```bash
python projects/gp023_planck_sandbox_05/harness_smoke_gate.py
```

## Anti-Overfitting Rule

This packet is interpretable only if the mutator-family change is the sole
causal delta relative to Sandbox 04.

Forbidden:

- new prompt hints
- new rubric criteria
- new apparatus messages
- new charter directionality
- new grammar or primitive expansion
- carry-over of evolved Sandbox 04 thesis text or mutated `test_model.py`

## Success Band

Counts as positive support for the stronger-mutator hypothesis only if the
bound champion does at least one of:

1. scores `> 50`, or
2. keeps score `50` but lowers `farther_tail_global_residual` materially below
   the Sandbox 04 champion's `0.023578450731712275`

## Failure Band

Anything else under a valid run.

## Invalid / Non-Diagnostic Outcomes

- missing required runtime flag
- smoke-gate failure
- provider fallback to a forbidden family
- runtime silently resolving `gemini-pro` to a different family

## Seal

Not sealed yet.

### Draft run command

```bash
python projects/gp023_planck_sandbox_05/harness_smoke_gate.py
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_05 \
    --rubric gp023_planck_sandbox_05 \
    --iters 10 \
    --mutator_model gemini-pro \
    --judge_model gemini \
    --deterministic_score_gates \
    --underidentified_after 20 \
    --no_model_fallback
```
