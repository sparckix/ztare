# GP-042 Structural Memory Verifier 01 — Pre-Registration

> **Seam metadata** · `seam_id:` GP-042 · `track:` substrates · `status:` Drafted 2026-04-12 16:30:05 EDT. Launch observed 2026-04-12  · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Status

Drafted 2026-04-12 16:30:05 EDT. Launch observed 2026-04-12 16:57:41 EDT. Recorded 2026-04-12 16:59:42 EDT. **Not pre-sealed; current run started before formal seal.**

## Launch Record

The current live run cannot be honestly described as "sealed before launch." The exact launch was observed while the run was already in progress.

Observed from cold artifacts:

- run id: `1776027402`
- `workspace/iteration_telemetry.jsonl` shows `run_start` at `2026-04-12T20:57:41.179558+00:00`
- live process command:

```bash
python -m src.ztare.validator.autoresearch_loop \
  --project gp042_structural_memory_01 \
  --rubric gp042_structural_memory_01 \
  --iters 10 \
  --mutator_model gemini \
  --judge_model gemini \
  --deterministic_score_gates \
  --underidentified_after 100 \
  --no_model_fallback
```

Protocol classification for the current run:

- command pinned: yes
- runtime family pinned: yes
- recorded contemporaneously during iter 1: yes
- formally sealed before launch: **no**

So this run should be treated as a **started-unsealed verifier run**. It is still useful, but if strict pre-registration discipline is required for external reporting, the clean claim would require a fresh rerun under a true pre-seal.

## Purpose

Fresh verifier on the frozen GP-037 substrate. The substrate is intentionally reused unchanged so the experiment isolates one question:

> does preserved structural-family memory reduce reversion after an escape, or was the prior reversion legitimate evidential rejection all along?

This is a GP-042 verifier, not a continuation of GP-037 and not a model-family comparison.

## Substrate

- project: `projects/gp042_structural_memory_01`
- rubric: `rubrics/gp042_structural_memory_01.json`
- generating function / visible slice / holdout slice: identical to frozen GP-037 substrate
- deterministic gates: identical to frozen GP-037 substrate
- seed thesis: identical deliberately-wrong seed

## Apparatus

Current runtime surface for this verifier:

- GP-035 fit primitive: enabled
- GP-034 latent-motion veto: live
- GP-042 structural memory: live

The experimental object is GP-042. GP-034 is treated as landed confound reduction, not the question under test.

## Runtime Plan

Single bounded verifier run:

- `10` iterations
- `bounded_discriminator`
- `--deterministic_score_gates`
- `--underidentified_after 100`
- `--no_model_fallback`

## Model Family

Pinned to Gemini / Gemini for isolation.

Reason:
- GP-037 used Gemini / Gemini
- widening into Claude or cross-family comparison would change the question
- this verifier is about structural-memory carry-forward, not model-family ranking

If this run is interesting and the principal later wants the model-family question, open a separate verifier packet.

## Success Criteria

This verifier is **not** judged primarily by top-line score.

A positive GP-042 read requires all of:

1. `workspace/structural_memory.json` records at least two distinct structural families during the run
2. the later mutator prompt includes the read-only structural-memory block
3. an escaped family survives at least one unsupervised pivot boundary as persistent run state
4. a later iteration re-engages that family without it being reintroduced as a fresh kernel-supplied answer

## Negative Result

A negative GP-042 read is:

- the structural-memory substrate is present and auditable
- but reversion still occurs in essentially the same pattern as frozen GP-037

That weakens the memory-loss framing and redirects the frontier toward structural scoring / family discrimination.

## Output Record Requirements

- `workspace/structural_memory.json`
- `last_prompt_debug.txt`
- `workspace/latent_distance.jsonl`
- `workspace/latest_information_yield.json`
- `workspace/iteration_telemetry.jsonl`
- full debate logs

## Planned / Observed Command

```bash
python -m src.ztare.validator.autoresearch_loop \
  --project gp042_structural_memory_01 \
  --rubric gp042_structural_memory_01 \
  --iters 10 \
  --mutator_model gemini \
  --judge_model gemini \
  --deterministic_score_gates \
  --underidentified_after 100 \
  --no_model_fallback
```

## Execution Outcome

Recorded 2026-04-12 17:26:39 EDT.

- run id: `1776027402`
- status: completed
- exit: `budget_exhausted`
- final iteration: `10`
- final score: `0`

Cold-artifact summary:

- GP-042 substrate was active:
  - [structural_memory.json](/projects/gp042_structural_memory_01/workspace/structural_memory.json) recorded `4` distinct structural families
- GP-034 was active:
  - [latest_information_yield.json](/projects/gp042_structural_memory_01/workspace/latest_information_yield.json) shows repeated latent-motion veto of `REFRESH_SPECIALISTS`
- strongest family appeared at iter `8`:
  - visible `max_abs_residual = 0.062100881826731014`
  - hidden global residual passed at `0.03716749697106714`

Interpretation:

- this was a **started-unsealed exploratory verifier**, not a strict pre-sealed run
- it produced a real structural improvement over frozen GP-037
- but it did **not** produce a passing thesis or a positive final score

Protocol result:

- useful as internal verifier evidence: **yes**
- sufficient for strongest external pre-registration claim: **no**
