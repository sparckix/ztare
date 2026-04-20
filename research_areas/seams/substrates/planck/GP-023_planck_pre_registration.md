# GP-023 Planck Mechanism Pre-Registration

## Status

Drafted 2026-04-10. Freeze before sandbox construction begins.

**Sealed 2026-04-10** after contamination audit 01 passed.
- Sandbox: `projects/gp023_planck_sandbox_01/` (construction record at `projects/gp023_planck_sandbox_01/sandbox_construction_record.md`)
- Rubric: `rubrics/gp023_planck_sandbox_01.json`, `falsification_mode: bounded_discriminator`
- Independent contamination checker: **gpt-4o (OpenAI family)**; audit log at `research_areas/private/gp023_contamination_audit_01.md`; verdict PASS (checker's top guess was "driven harmonic oscillator / RLC resonance", 95% confidence on the forensic probe — wrong retrieval basin, perturbations held).
- **Runtime mutator family (sealed):** Gemini (`gemini-2.5-flash` via `MODEL_MAP["gemini"]`)
- **Runtime judge family (sealed):** Gemini (`gemini-2.5-flash`)
- **Forbidden as runtime for this experiment:** gpt-4o / OpenAI family (burned as contamination checker, independence would be violated)
- **UNDERIDENTIFIED exit suppression:** the run MUST be invoked with `--underidentified_after 20` (smoke run) or `--underidentified_after 100` (main run). Without this flag, the UNDERIDENTIFIED gate fires after just 3 consecutive catastrophic iterations in bounded_discriminator mode and breaks the loop — preempting the pivot entirely. GP-023's seed is deliberately designed to produce catastrophic failures until the pivot forces a structural break, so the default threshold of 3 is invalid for this experiment. The threshold must be at least equal to the iteration budget. Discovered 2026-04-10 during the smoke run at iteration 4. Fix: new `--underidentified_after` flag in `autoresearch_loop.py`; `information_yield.py:evaluate_information_yield` now accepts a separate `underidentified_after` param decoupled from `pivot_after`.
- **Model-fallback lock:** the run MUST be invoked with `--no_model_fallback`. Without that flag, `llm_runtime.FALLBACK_MODEL_CHAINS` silently cascades Gemini → `claude-sonnet-4-6` → `gpt-4o` on transient provider errors, which would (a) break the sealed runtime family and (b) in the worst case hand the run to the burned contamination checker. Added 2026-04-10 as a direct response to a pre-kickoff audit of the runtime code path. Enforcement is via the env var `ZTARE_DISABLE_MODEL_FALLBACK=1` which the flag sets at startup; `call_text` reads the env var on every call, so the lock applies to mutator, judge, and any helper path without kwarg threading. A valid GP-023 run must show the `🔒 Model fallback DISABLED` banner in the run log.
- Pivot profile sealed: `bounded_discriminator` (9-module expanded set per GP-021 Turn 6 fix, verified in `src/ztare/validator/pivot_heuristics.py`)
- Execution plan: 20-iteration smoke run first (gate before full 100), then 100-iteration main run on operator go-ahead. The 20-iter smoke run exists only to verify that the pivot fires, the seed is falsified in logs, and no contamination surfaces in the runtime's own text. Its result does not count toward or against the primary hypothesis.

## Purpose

This document freezes the first-run evaluation contract for GP-023 before any ontology-trap sandbox is constructed or executed.

It exists to prevent the exact failure mode this seam is about:

- post-hoc reinterpretation
- moving success criteria after seeing a trace
- mistaking retrieval theater for discovery

This file is intentionally narrower than the seam and narrower than the implementation spec.

## Experiment Object

Test whether ZTARE can generate a structurally novel primitive through:

- sustained adversarial blockade
- starvation under repeated failure
- orthogonal-shock prompt pressure
- anchor-proxy filtering

without retrieving the historical answer directly from pretraining.

The source inspiration is the Planck-style pattern:

- old vocabulary fails under hard empirical constraint
- a previously illegal composition appears
- the composition survives because it anchors to the curve

The experiment is not “did the model rediscover Planck.”
The experiment is “can the mechanism fire at all under an isomorphic but contamination-controlled setup.”

## Primary Hypothesis

Under a contamination-controlled isomorphic sandbox, a ZTARE run with sustained blockade plus repeated `bounded_discriminator` pivot pressure can produce a structurally novel composite primitive that:

1. was not explicitly present in the seed artifact
2. is argued into existence through renamed-variable reasoning
3. survives anchor-proxy demand against the perturbed target curve

## Null Hypothesis

Under the same conditions, the run will do one of:

- retrieve the historical solution shape directly
- cycle through existing failure families
- produce only ad hoc patches that do not survive anchor-proxy demand
- fail to produce a structurally novel composite primitive at all

## Pre-Registered Controls

### 1. Semantic Retrieval Control

- no physics vocabulary in the seed
- no terms like `energy`, `frequency`, `temperature`, `black-body`, `quantum`, `radiation`, `Planck`, `ultraviolet`
- variables are renamed to neutral tokens

### 2. Mathematical-Form Control

- perturb the functional form so it is not a clean black-body template match
- add irrelevant covariates or reshaped divergence behavior if needed

### 3. Data-Shape Control

- rescale and offset all curve data
- remove recognizable units
- no historically identifiable temperature or wavelength labels

### 4. Prompt Telegraphing Control

- use only generic GP-021 orthogonal-shock language
- do not hint at discreteness, quantization, packets, or frequency-energy coupling

### 5. Operator Contamination Control

- score only against the criteria below
- do not allow “this feels Planck-like” as evidence
- do not use human plausibility judgments as a positive criterion

## Independent Contamination Check

Before execution, query a separate model family with the perturbed seed and ask:

- “What historical scientific or physical phenomenon does this most resemble?”

Pre-registered handling:

- if the verifier identifies black-body radiation, Planck, or a materially equivalent historical case, the sandbox is contaminated
- contaminated sandbox is invalid and must be rebuilt before any GP-023 run begins
- contaminated sandbox does not count as success, failure, or partial result

## Pre-Registered Runtime

First-run budget:

- 100 iterations minimum
- do not stop on the first `0`
- do not stop on early stagnation unless the run becomes technically invalid

Mutator/judge family:

- default: Gemini or Claude may be used
- the exact family used must be recorded before the run starts
- same-family contamination checker is forbidden

Pivot regime:

- `bounded_discriminator` profile
- GP-021 Phase 1.5 expanded module set must be used
- no domain-specific heuristic hints beyond the registered profile

## Success Criteria

The run counts as a positive GP-023 result only if all three hold:

1. **Novel composite primitive**
   - a surviving thesis depends on a composite primitive not explicitly named in the seed artifacts

2. **Anchor-proxy bridge**
   - the primitive is tied to observable structure in the perturbed target curve
   - the bridge is load-bearing, not decorative

3. **Trace emergence**
   - the debate/thesis trace shows the primitive emerging from multi-step reasoning over renamed variables
   - not as a single unexplained leap

## Failure Criteria

The run counts as a negative GP-023 result if:

- 100 iterations complete
- the sandbox is uncontaminated
- and no candidate satisfies all three success criteria

## Invalid / Non-Diagnostic Outcomes

These do not count as clean success or clean failure:

- contaminated sandbox
- provider instability that prevents the run from meaningfully completing
- trace corruption or missing logs
- partial novelty with no anchor-proxy bridge
- anchor-proxy bridge with no structurally novel primitive

Handling rule:

- classify as `invalid` or `partial`
- do not silently upgrade a partial to success

## Mechanical Trace Rule

To satisfy “trace emergence,” the winning candidate must show at least:

- 3 explicit intermediate reasoning steps
- each step references renamed variables or renamed observables from the seed
- the final primitive is derivable from those steps without an unexplained jump

This rule is pre-registered specifically to reduce operator contamination.

## Output Record

A valid GP-023 run must preserve:

- full debate logs
- final thesis
- final falsification suite
- contamination-check record
- scoring sheet against this pre-registration

## What This Pre-Registration Does Not Decide

- the final sandbox parameterization
- whether one or two historical structures should be composed
- whether 100 iterations is enough in future runs
- whether a positive result generalizes beyond one instance

Those are spec-level or post-run interpretation questions, not things to improvise mid-run.

