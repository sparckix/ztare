# GP-023 Planck Sandbox 04 — Apparatus-Feedback Verifier Pre-Registration

## Status

Drafted 2026-04-12 23:16:00 EDT as a stronger-mutator verifier. Re-scoped 2026-04-13 00:39:18 EDT as an **apparatus-feedback verifier** after the `sandbox_03` iter-40 debrief. Fresh farther-tail holdout authored at packet level during the re-scope. This packet is **not sealed** and is **not pre-seal ready** until the companion GP-048 `src/` changes land and are dry-run on the exact packet.

This packet no longer asks "does a stronger model escape first?" The cheaper live question is now apparatus-first:

> if the flash mutator is given explicit primitive-cone feedback at stagnation plus a sanitized global-tail veto signal, does it leave the repeated farther-tail-failing basin that `sandbox_03` reproduced four times?

## Purpose

The empirical anchor after `sandbox_03` is now:

- iter 13: score `50`
- iter 20: score `50`
- iter 26: score `50`
- iter 33: score `50`

All four were the same basin: good visible fit, hidden in-range pass, repeated failure of `farther_tail_global_residual`.

So `sandbox_04` is now the cheapest falsification of the **apparatus-blindness** hypothesis:

> the mutator is not being shown, in a sanitized and non-leaking way, that its current family class is globally disfavored outside the visible frontier, and stagnation pressure is not yet expressed at the primitive-cone level.

## Experiment Object

Same hidden generator class, same visible and hidden in-range contract, **fresh farther-tail holdout**, same flash mutator family, changed apparatus feedback.

Inherited unchanged from `sandbox_03`:

- hidden generating law
- rename map
- visible slice
- hidden in-range holdout
- charter gates
- GP-046 asymptotic-claim contract
- GP-035 fit primitive
- cold residual successor mode

Changed for `sandbox_04`:

- fresh farther-tail holdout file on the same hidden generator class
- runtime mutator family remains `gemini`
- runtime judge family remains `gemini`
- hard iteration cap: `20`
- `underidentified_after: 20`
- GP-048 telemetry is expected to be enabled
- GP-048 stagnation injection is expected to be active
- sanitized farther-tail veto block is expected to be active

## Primary Hypothesis

Under the carried-forward contamination controls and the fresh farther-tail surface, a `20`-iteration bounded-discriminator run with:

- `enable_fit_primitive: true`
- `cold_residual_successor_mode: true`
- `gp048_telemetry: true`
- `gp048_stagnation_injection_mode: "primitive_cone"`
- `gp048_farther_tail_veto_mode: "sanitized"`
- `--mutator_model gemini`
- `--judge_model gemini`

can produce a candidate family that leaves the repeated `sandbox_03` primitive cone and improves on the same farther-tail failure class without named external-domain import.

## Null Hypothesis

Under the same conditions, the flash mutator will still do one of:

- remain trapped in the same local late-tail / floor-family basin,
- oscillate between the same one-gate near-pass and broad collapse families,
- produce a numerically adequate local surrogate that still fails farther-tail scrutiny,
- or fail to produce a viable candidate within the capped budget.

## Runtime Contract

Single-stage run, 20 iterations, same flash-family model IDs as `sandbox_03`.

Required flags:

- `--project gp023_planck_sandbox_04`
- `--rubric gp023_planck_sandbox_04`
- `--iters 20`
- `--mutator_model gemini`
- `--judge_model gemini`
- `--deterministic_score_gates`
- `--underidentified_after 20`
- `--no_model_fallback`

Required pre-run command:

```bash
python projects/gp023_planck_sandbox_04/harness_smoke_gate.py
```

Any non-zero exit from the smoke gate invalidates launch.

## Launch Blockers

This packet is blocked on companion `src/` work owned outside the packet:

1. GP-048 telemetry must be wired behind the rubric flag.
2. GP-048 primitive-cone stagnation injection must render during `stagnation_pivot` / `emergency_pivot`.
3. The sanitized farther-tail veto block below must be wired into the prompt path without exposing hidden evidence values.
4. The exact packet must be dry-run after those changes land.

Until those are true, `sandbox_04` is packet-ready but not launch-ready.

## Claim Scope

`sandbox_04` is allowed to claim the same object as `sandbox_03` because the farther-tail contract is unchanged:

```yaml
asymptotic_claim: true
farther_tail_contract: true
```

So a passing global-tail claim is licensed only if the farther-tail gates pass. No local-tail laundering is permitted.

## Success Band

`sandbox_04` counts as a positive GP-023 datum only if the bound champion satisfies all of:

1. score `>= 85`
2. all nine deterministic gates pass
3. no named external-domain import
4. mechanical trace rule satisfied: at least 3 intermediate reasoning steps over renamed variables, with no unexplained leap into the final composite
5. asymptotic/global-tail language, if used, is licensed by the farther-tail gate surface rather than only by bounded-window fit

## Strong-Partial Band

Honest but negative result:

- score `>= 70`
- at least 7 of 9 deterministic gates pass
- mechanical trace rule satisfied

## Failure Band

Anything else under a valid run, including reproduction of the same single-gate farther-tail failure basin.

## Invalid / Non-Diagnostic Outcomes

- missing required runtime flag
- pre-run smoke-gate failure
- post-run smoke-gate failure
- no champion artifact
- non-finite `actual` values in any declared gate
- provider fallback to a forbidden family

Handling rule: classify as `invalid`, not partial.

## Carried-Forward Contamination Posture

`sandbox_04` inherits `sandbox_03`'s substrate and scorer surfaces by contract, but does **not** inherit prompt-visible seed artifacts blindly.

Fresh packet discipline for `sandbox_04`:

- `thesis.md`, `current_iteration.md`, and `test_model.py` are rebuilt from scratch rather than copied from the live `sandbox_03` workspace
- no `Planck` token in any mutator-visible file
- no `gp023_planck_sandbox_04` token in any mutator-visible file
- no hidden-generator constants (`A=1.37`, `p=2.7`, `offset=0.08`, etc.) in any mutator-visible file
- the farther-tail veto block may state only that the current family fails a sealed global-tail check beyond the visible frontier; it may not reveal hidden values, exact residuals, or point locations

## Output Record

A valid `sandbox_04` run must preserve:

- debate logs
- final `thesis.md`
- final `test_model.py`
- `champion_eval_results.json`
- `latest_eval_results.json`
- run log including startup banners
- pre-run and post-run smoke-gate output
- champion gate payload in the evaluation artifact

## Draft Sanitized Farther-Tail Veto Block

This is the exact prompt text proposed for review and later `src/` wiring:

> SANITIZED GLOBAL-TAIL VETO:
> Your recent candidate family has repeatedly survived the visible slice and much of the in-range hidden evaluation while failing a sealed farther-tail check beyond the observed frontier.
> Treat this as a failure-class signal only, not as new evidence:
> the current family's late-tail mechanism is not licensed globally.
> Do not infer hidden values, hidden coordinates, or the exact shape of the farther-tail surface.
> The only authorized conclusion is that continued re-parameterization inside the same primitive cone is disfavored.
> When stagnation pressure is active, prefer a candidate that crosses a primitive-set boundary rather than refining the same decay-floor topology.

## Pre-Seal Verification Requirements

Before this document can be promoted from draft to sealed, all of the following must be true on the exact packet that will be run:

1. the charter parser extracts all nine declared gates
2. the asymptotic-claim contract parser extracts `asymptotic_claim: true` and `farther_tail_contract: true`
3. the frozen harness smoke gate passes on the naive seed thesis
4. one real deterministic evaluation artifact shows `harness_invoked: true` with declared gate results present
5. the companion GP-048 rubric flags are wired in `src/` and observable in a dry run
6. the exact run command is fully pinned with no model-family ambiguity
7. a literal mutator-visible leak sweep finds no `Planck`, no project-path token, and no hidden-generator constants in the mutator-visible packet

## Seal

Not sealed yet.

This packet is now **drafted and re-scoped**, but **not pre-seal ready**. Operator seal should happen only after the companion GP-048 `src/` work lands and the dry-run checks above pass.

### Draft run command

```bash
python projects/gp023_planck_sandbox_04/harness_smoke_gate.py
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_04 \
    --rubric gp023_planck_sandbox_04 \
    --iters 20 \
    --mutator_model gemini \
    --judge_model gemini \
    --deterministic_score_gates \
    --underidentified_after 20 \
    --no_model_fallback
```
