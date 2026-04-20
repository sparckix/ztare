# GP-023 Planck Sandbox 03 — Phase 3 Pre-Registration

## Status

Drafted 2026-04-12 21:26:07 EDT. Machine-path pre-seal verification completed 2026-04-12 21:35:50 EDT. First seed-thesis leak patch applied 2026-04-12 21:49:19 EDT to `thesis.md` / `current_iteration.md`. A remaining mutator-visible leak in `test_model.py` was then discovered and patched at 2026-04-12 21:54:36 EDT (`MODEL_PARAMS["p"]: 2.7 -> 1.5`), with smoke gate re-verified PASS afterward. A further mutator-visible ontology leak in `project_charter.md` was then discovered and scrubbed at 2026-04-12 21:59:40 EDT (removed `Planck`/project-path header leakage), with parser and smoke checks re-verified PASS afterward. A final prompt-visible metadata leak in HTML comments inside `thesis.md` / `current_iteration.md` was then removed at 2026-04-12 22:04:40 EDT, with smoke gate re-verified PASS afterward. The earlier 2026-04-12 21:50:02 EDT seal, 2026-04-12 21:54:36 EDT reseal, and 2026-04-12 21:59:40 EDT reseal were therefore premature and are superseded. **Resealed 2026-04-12 22:04:40 EDT** pending operator invocation of the run command in §Seal. Correction log: `research_areas/private/postmortems/gp023_phase3_prompt_surface_contamination_2026_04_12.md`.

This document supersedes `research_areas/private/seams/GP-023_planck_sandbox_02_pre_registration.md` for any work touching `projects/gp023_planck_sandbox_03/`. Sandbox_02 remains frozen as the Phase 2 historical record.

## Purpose

Phase 3 tests the next live GP-023 question after GP-035, GP-037, GP-045, and GP-046:

> with the fit primitive shipped and structural-diversity pressure made explicit, can the Planck-style sandbox produce a candidate that clears visible fit, hidden in-range generalization, and farther-tail asymptotic scrutiny without importing the historical answer?

Sandbox_03 is not a rerun of sandbox_02 with one flag flipped. It changes the evaluation object in two explicit ways:

1. `enable_fit_primitive: true` is part of the sealed runtime contract.
2. A sealed farther-tail holdout is added so asymptotic/global-tail claims are licensed deterministically rather than inferred from bounded-window late-tail behavior.

## Experiment Object

Unchanged substrate, changed apparatus.

The hidden generating law, rename map, and contamination posture are inherited from sandbox_02. The Phase 3 deltas are:

- GP-035 fit primitive enabled in-rubric
- cold residual successor mode enabled as the explicit structural-diversity delta
- a second hidden farther-tail surface bound to charter-declared deterministic gates

This makes the experiment object:

> can ZTARE escape the failed local families on the contamination-controlled Planck-style sandbox and recover a structurally admissible candidate under both in-range and farther-tail scrutiny?

## Primary Hypothesis

Under the carried-forward contamination controls, a 100-iteration bounded-discriminator run with the fit primitive enabled and cold residual successor mode active can produce a single candidate family that:

1. fits the visible slice,
2. generalizes to the hidden in-range holdout,
3. survives the farther-tail holdout if it makes a floor / asymptotic / global-tail claim,
4. preserves the renamed-variable mechanical-trace discipline, and
5. does so without named external-domain import.

## Null Hypothesis

Under the same conditions, the run will do one of:

- remain trapped in previously failed local families even with the fitter available,
- generate only local late-tail surrogates that fail farther-tail scrutiny,
- recover a numerically adequate family without satisfying the mechanical-trace discipline,
- import or gesture toward the historical law rather than deriving over the renamed variables,
- or fail to produce a viable candidate at all.

## Carried-Forward Contamination Posture

Sandbox_03 inherits sandbox_02's contamination audit posture by contract.

Justification:

- same hidden generating law
- same rename map
- same perturbations
- same visible evidence surface
- only new data is the hidden farther-tail slice, which is never exposed to the mutator prompt

So no fresh external contamination audit is required for Sandbox_03 seal.

## Runtime Contract

Single-stage run, 100 iterations.

Required flags:

- `--project gp023_planck_sandbox_03`
- `--rubric gp023_planck_sandbox_03`
- `--iters 100`
- `--mutator_model gemini`
- `--judge_model gemini`
- `--deterministic_score_gates`
- `--underidentified_after 100`
- `--no_model_fallback`

Required pre-run command:

```
python projects/gp023_planck_sandbox_03/harness_smoke_gate.py
```

Any non-zero exit from the smoke gate invalidates launch.

## Structural-Diversity Delta

Phase 3 makes the structural-diversity delta explicit instead of smuggling it through prompt drift:

- rubric `cold_residual_successor_mode: true`
- rubric `enable_fit_primitive: true`

Interpretation:

- the fitter closes parameter-estimation as the primary bottleneck
- cold residual successor mode is the first explicit attempt to escape the failed family basin without operator-chosen repair menus

Cold residual successor mode is allowed to activate only through the generic shipped mechanism. No project-local family list, topological hint, or hand-authored rescue axis is permitted.

## Asymptotic Claim Contract

Sandbox_03 declares:

```yaml
asymptotic_claim: true
farther_tail_contract: true
```

This means:

- asymptotic / floor / global-tail credit is in scope
- but only because `evidence_farther_tail.txt` exists and the charter binds deterministic farther-tail gates to it

Without those gates, the same thesis would be downgraded by GP-046 minimal A to a local late-tail surrogate rather than a licensed asymptotic claim.

## Run-State Binding

Primary binding artifact:

`projects/gp023_planck_sandbox_03/champion_eval_results.json`

Conditional on:

1. loop exit under the declared runtime contract,
2. post-run harness smoke check against the champion passing,
3. all declared gate payloads containing finite `actual` values,
4. no missing required flag in the run log.

Rejected bindings:

- `latest_eval_results.json`
- any specific iteration number
- any post-hoc manually selected thesis

## Success Band

Phase 3 counts as a positive GP-023 datum only if the bound champion satisfies all of:

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

This band exists so a strong local or in-range discovery that fails farther-tail discipline is recorded honestly rather than inflated into success.

## Failure Band

Anything else under a valid run:

- score `>= 85` with one or more failed gates
- local-fit win that fails farther-tail scrutiny
- numerically good thesis with missing trace discipline
- explicit or implicit external-domain import

## Invalid / Non-Diagnostic Outcomes

- missing required runtime flag
- pre-run smoke-gate failure
- post-run smoke-gate failure
- no champion artifact
- non-finite `actual` values in any declared gate
- provider fallback to a forbidden family

Handling rule: classify as `invalid`, not partial.

## Mechanical Trace Rule

Unchanged:

- at least 3 explicit intermediate reasoning steps
- each step references renamed variables or renamed observables
- final primitive is derivable from those steps without an unexplained jump

## Output Record

A valid Sandbox_03 run must preserve:

- debate logs
- final `thesis.md`
- final `test_model.py`
- `champion_eval_results.json`
- `latest_eval_results.json`
- run log including startup banners
- pre-run and post-run smoke-gate output
- champion gate payload in the evaluation artifact
- post-run scoring sheet at `projects/gp023_planck_sandbox_03/post_run_scoring_sheet.md`

## Pre-Seal Verification Requirements

Before this document can be promoted from draft to sealed, all of the following must be true on the exact packet that will be run:

1. the charter parser extracts all nine declared gates
2. the asymptotic-claim contract parser extracts `asymptotic_claim: true` and `farther_tail_contract: true`
3. the frozen harness smoke gate passes on the seed thesis
4. one real deterministic evaluation artifact shows `harness_invoked: true` with declared gate results present
5. the sealed run command has been dry-run at the machine-path level before operator launch

Items 1-4 above were satisfied on the drafted packet as of 2026-04-12 21:35:50 EDT. The final prompt-facing leak patch set completed at 2026-04-12 22:04:40 EDT after the residual HTML-comment metadata leak was removed and the smoke gate was re-run successfully. The exact run command is now pinned below, so the packet is resealed and waiting only on operator invocation.

## Seal

**Resealed 2026-04-12 22:04:40 EDT.** The prior 2026-04-12 21:50:02 EDT seal, 2026-04-12 21:54:36 EDT reseal, and 2026-04-12 21:59:40 EDT reseal are superseded by the corrections recorded in `research_areas/private/postmortems/gp023_phase3_prompt_surface_contamination_2026_04_12.md`.

### Sealed values

- **Runtime mutator family:** Gemini `gemini-2.5-flash` via `--mutator_model gemini`
- **Runtime judge family:** Gemini `gemini-2.5-flash` via `--judge_model gemini`
- **Forbidden as runtime:** gpt-4o / OpenAI fallback and any model fallback chain, enforced by `--no_model_fallback`
- **Deterministic gate surface:** 9 gates exactly as declared in `project_charter.md`
- **Asymptotic claim posture:** `asymptotic_claim: true`, `farther_tail_contract: true`
- **Structural-diversity delta:** `cold_residual_successor_mode: true`
- **Fit primitive posture:** `enable_fit_primitive: true`, `fit_required_dimensionality: 2`
- **Final pre-seal contamination fixes:** seed-thesis deanchor in `thesis.md` / `current_iteration.md` at 2026-04-12 21:49:19 EDT, seed-code deanchor in `test_model.py` at 2026-04-12 21:54:36 EDT, charter ontology/path scrub in `project_charter.md` at 2026-04-12 21:59:40 EDT, then HTML-comment metadata scrub in `thesis.md` / `current_iteration.md` at 2026-04-12 22:04:40 EDT

### Seal-time verification

Verified before seal:

1. charter parser extracted all 9 declared gates
2. asymptotic-claim contract parser extracted `asymptotic_claim: true` and `farther_tail_contract: true`
3. frozen harness smoke gate passed on the seed thesis
4. deterministic gate evaluator returned `harness_invoked=true` with 9 real pass/fail results on the seed thesis
5. exact run command below is fully pinned with no implicit model-family defaults left unbound

### Sealed commands

Re-run the smoke gate immediately before launch:

```
python projects/gp023_planck_sandbox_03/harness_smoke_gate.py
```

Binding Phase 3 run:

```
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_03 \
    --rubric gp023_planck_sandbox_03 \
    --iters 100 \
    --mutator_model gemini \
    --judge_model gemini \
    --deterministic_score_gates \
    --underidentified_after 100 \
    --no_model_fallback
```

## Ready-To-Run Commands

Pre-run smoke gate:

```
python projects/gp023_planck_sandbox_03/harness_smoke_gate.py
```

Main run:

```
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_03 \
    --rubric gp023_planck_sandbox_03 \
    --iters 100 \
    --mutator_model gemini \
    --judge_model gemini \
    --deterministic_score_gates \
    --underidentified_after 100 \
    --no_model_fallback
```

## What This Pre-Registration Does Not Decide

- whether a positive Sandbox_03 run is enough to close GP-023 globally
- whether a later Planck slice should add a compression/parsimony objective
- whether cold residual successor mode is the final structural-diversity answer or only the first admissible slice

Those are post-run interpretation questions, not things to improvise into this run.
