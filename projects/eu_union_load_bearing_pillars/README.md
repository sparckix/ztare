# EU Union Load-Bearing Pillars

## Purpose

This project returns to the broader question that the earlier `eu_union_stability` project only partially answered:

- which missing integration pillars are actually load-bearing for a durable union?
- can the EU remain intact with partial integration?
- when does fragile survival become material union failure?

It is **not** only a Eurozone shock-mechanism project.

## Why This Is Separate From `eu_union_stability`

`eu_union_stability` narrowed into a specific mechanism claim:

- absent automatic fiscal transfers amplify asymmetric shocks beyond heterogeneity baseline

That was useful, but narrower than the original question.

This project is broader:

- rank missing pillars
- separate `durable equilibrium` from `fragile survival`
- include a secondary forecast subquestion:
  - is formal EU intactness through January 1, 2035 more likely than material union failure?

Forecast typing:

- this is a `directional_forecast` project, not a `%` forecast project
- the forecast output is a bounded tilt, not a point probability

## Evidence Priority

Use inherited materials in this order:

1. `projects/eu_union_stability/Report.md`
   - best reader-facing synthesis of what the earlier project supported
2. `projects/eu_union_stability/evidence.txt`
   - source-backed structured evidence and inherited constraints
3. `projects/eu_union_stability/verified_axioms.json`
   - compact factual anchors
4. raw debate logs
   - provenance only, not first-line evidence

Do **not** treat:

- the prior score
- the prior probability DAG

as a forecast probability for this project.

## Main Question

What is the minimum set of integration pillars required for the EU to remain in a durable equilibrium rather than a repeated pattern of costly improvised crisis management?

## Secondary Forecast Subquestion

Conditional on current institutions, is the more likely outcome through January 1, 2035:

- continued formal intactness with durable fragility
- or material union failure?

## Suggested Commands

Run the project directly against the seeded evidence:

```bash
python -m src.ztare.validator.autoresearch_loop \
  --project eu_union_load_bearing_pillars \
  --rubric eu_union_load_bearing_pillars \
  --iters 3 \
  --mutator_model gemini \
  --judge_model gemini \
  --deterministic_score_gates
```

If you want a fresh workspace/compiler pass first:

```bash
python -m src.ztare.workspace.update_workspace --project eu_union_load_bearing_pillars --model gemini
python -m src.ztare.workspace.compile_evidence --project eu_union_load_bearing_pillars --mode workspace
cp projects/eu_union_load_bearing_pillars/compiled_evidence.txt projects/eu_union_load_bearing_pillars/evidence.txt
```

## Working Rule

The thesis should be allowed to conclude:

- `fragile but intact`

without being forced into:

- `stable`
- `collapse`

That distinction is the point of this project.
