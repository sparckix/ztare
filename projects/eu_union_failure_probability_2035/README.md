# EU Union Failure Probability 2035

## Purpose

This project is the explicit probabilistic follow-on to:

- [eu_union_load_bearing_pillars](../eu_union_load_bearing_pillars)

It is a different project object.

The load-bearing project asked:

- what state is the EU currently in?
- which missing pillars are load-bearing?
- what bounded directional forecast survives?

This project asks instead:

- what is the best-justified point estimate or bounded range for `P(material_union_failure by 2035-01-01)`?
- what complementary probability does that imply for continued formal intactness through the same horizon?

## Project Type

This is a `probabilistic_forecast` project.

That means:

- `%` claims are in-bounds
- but only if the event target, horizon, and modeling basis are explicit

It does **not** mean:

- the old directional project's probability DAG can simply be reinterpreted as a market-style forecast probability

## Inheritance

This project should inherit from:

- [eu_union_load_bearing_pillars](../eu_union_load_bearing_pillars)

Inherited use:

- current-state classification and pillar ranking
- verified axioms and compiled evidence
- direction of the bounded forecast

Not inherited unchanged:

- the old probability DAG as a point-probability forecast

## What This Project Needs

Before it can honestly emit a `%`, it needs:

1. explicit event ontology for `material_union_failure`
2. horizon discipline through `2035-01-01`
3. reference-class or scenario basis for the point estimate
4. calibration logic for how current-state/pillar evidence maps into event probability
5. explicit relation between `P(failure)` and `P(formal intactness)`

## Starter Workflow

1. finish the last EU load-bearing closure pass
2. use that result as inherited current-state input here
3. fill `raw/` with reference-class and scenario evidence
4. compile evidence
5. draft the first actual probabilistic thesis

## Commands

Compile future evidence once `raw/` has material:

```bash
python -m src.ztare.workspace.compile_evidence \
  --project eu_union_failure_probability_2035 \
  --mode raw
```

Then promote:

```bash
cp projects/eu_union_failure_probability_2035/compiled_evidence.txt \
   projects/eu_union_failure_probability_2035/evidence.txt
```

Then run the validator once a real thesis/test suite exists:

```bash
python -m src.ztare.validator.autoresearch_loop \
  --project eu_union_failure_probability_2035 \
  --rubric eu_union_failure_probability_2035 \
  --iters 1 \
  --mutator_model gemini \
  --judge_model gemini \
  --deterministic_score_gates
```
