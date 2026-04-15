# GP-045 Cold Residual Successor 01 — Pre-Registration

## Status

Sealed 2026-04-12 19:24:26 EDT.
Executed 2026-04-12 19:27:28 EDT to 2026-04-12 19:47:21 EDT.
Run complete.

## Purpose

This exploratory verifier tests a cold residual-mode successor search under the Option B admissibility rule.

The central question is:

> can the mutator produce a materially better successor structure from cold artifacts alone, without the operator naming the next repair family?

This is not pre-registered as a clean deductive-discovery proof. It is a sealed exploratory verifier on whether the cold residual surface is rich enough to generate non-steered family movement.

## Fixed Inputs

- project: `gp045_cold_residual_01`
- rubric: `gp045_cold_residual_01`
- mutator family: `gemini`
- judge family: `gemini`
- same substrate / holdout / deterministic gates as GP-043
- cold residual successor mode enabled
- fit primitive enabled

## Cold Artifact Surface

The run starts from seeded project-local artifacts:

- `workspace/fit_result.json` — GP-042 iter-8 fitted base family and full residual map
- `workspace/structural_memory.json` — GP-042 family trace
- `latest_eval_results.json` — GP-043 clean-family gate surface

These are read-only starting artifacts. They do not authorize any named successor family.

## Admissibility Boundary

Allowed:

- full residual matrix
- gate pass/fail surface
- structural-memory trace
- generic kernel diagnostics emitted automatically

Forbidden:

- named repair-family steering in charter/thesis/rubric
- operator-supplied topological diagnosis implying the next family
- fixed recombination rule in advance

## Success Condition

1. the run produces at least one structurally distinct successor candidate beyond the seeded base family
2. the candidate materially improves visible residual over the seeded base approximation
3. hidden deterministic gates remain passed or improve
4. no self-reference / internal-parameter discriminator / named external import returns

## Failure Condition

- collapse back into known families with no material improvement
- visible improvement only by breaking hidden gates
- no meaningful successor-family movement from the cold residual surface

Any of these is still informative.

## Run Outcome

Run executed to the sealed 10-iteration budget under:

- run id: `1776036404`
- mutator: `gemini-2.5-flash`
- judge: `gemini-2.5-flash`
- exit reason: `budget_exhausted`
- no model fallback observed

Champion / latest split:

- **champion:** [1776036404_iter7_score_100_gp045_cold_residual_01.md](/Users/daalami/figs_activist_loop/projects/gp045_cold_residual_01/history/1776036404_iter7_score_100_gp045_cold_residual_01.md) with [champion_eval_results.json](/Users/daalami/figs_activist_loop/projects/gp045_cold_residual_01/champion_eval_results.json)
- **latest final evaluated attempt:** `iter 10`, score `0`, preserved in [latest_eval_results.json](/Users/daalami/figs_activist_loop/projects/gp045_cold_residual_01/latest_eval_results.json)

What the run established:

1. a structurally distinct successor family beyond the seeded base approximation did emerge
2. the winning family materially improved visible fit and passed all hidden deterministic gates
3. the best passing artifact achieved:
   - `hidden_global_residual = 0.033232 < 0.05`
   - all hidden peak-location gates passed
   - `hidden_high_phi_decay_ratio = 0.026302 < 0.10`

What the run did **not** establish:

- a clean deductive-discovery proof of the underlying mechanism
- uniqueness of additive recombination as the right causal interpretation
- independent causal evidence for the physical meaning of the fitted exponents

Interpretation:

- this pre-registration succeeded as an **exploratory cold residual successor verifier**
- the honest claim is narrower than "deductive discovery proved"
- the load-bearing next step is an admissibility / claim-scope audit of the iter-7 champion, not blind continuation of this same run

## Pre-Seal Audit

Verified locally before seal:

- [project_charter.md](/Users/daalami/figs_activist_loop/projects/gp045_cold_residual_01/project_charter.md): no named successor repair family
- [thesis.md](/Users/daalami/figs_activist_loop/projects/gp045_cold_residual_01/thesis.md): no named successor repair family
- [current_iteration.md](/Users/daalami/figs_activist_loop/projects/gp045_cold_residual_01/current_iteration.md): no named successor repair family
- [gp045_cold_residual_01.json](/Users/daalami/figs_activist_loop/rubrics/gp045_cold_residual_01.json): `cold_residual_successor_mode = true`
- [test_model.py](/Users/daalami/figs_activist_loop/projects/gp045_cold_residual_01/test_model.py): current base family only; no preselected extension
- `python -m py_compile projects/gp045_cold_residual_01/test_model.py projects/gp045_cold_residual_01/gate_harness.py` passed
- `python projects/gp045_cold_residual_01/test_model.py` passed

## Sealed Command

```bash
python -m src.ztare.validator.autoresearch_loop \
  --project gp045_cold_residual_01 \
  --rubric gp045_cold_residual_01 \
  --iters 10 \
  --mutator_model gemini \
  --judge_model gemini \
  --deterministic_score_gates \
  --underidentified_after 100 \
  --no_model_fallback
```
