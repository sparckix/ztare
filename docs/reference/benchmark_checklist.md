# Benchmark Checklist

Use this checklist before trusting a new benchmark result.

## 1. Artifact Type
- Is the system output symbolic/exact, or semantic/free-form?
- If semantic, do not rely only on exact keyword matching for core metrics.

## 2. Measurement Layer
- Does the metric faithfully capture the property we claim to measure?
- Could paraphrase, formatting drift, or wording variance create false negatives?
- If yes, add a semantic adjudication layer or manual gold review.

## 3. Separation Of Roles
- Builder question: does the harness run correctly and isolate outputs?
- Architect question: what second-order artifact could silently corrupt the claim even if the harness "works"?

## 4. Ground Truth
- For each specimen, is the expected exploit family or success condition explicit?
- Are positive controls genuinely clean under the same rubric?
- Are failures due to benchmark bugs clearly separated from substantive evaluator misses?

## 5. Score Semantics
- Are scores bounded and interpretable?
- Can text say "falsified" while the score remains high?
- If so, move score mapping into deterministic code.

## 6. Detection Semantics
- Are we measuring exact phrase hits, or semantic identification of the mechanism?
- If semantic identification matters, report both:
  - heuristic detection
  - adjudicated detection
- If taxonomy is part of the claim, separate:
  - exploit-family detection
  - acceptable fatal structural detection

## 7. Controls
- Does the suite contain both bad specimens and good controls?
- If all good controls fail, the benchmark cannot distinguish sensitivity from over-rejection.

## 8. Failure Modes
- Do benchmark crashes get logged separately from evaluator failures?
- Do tool-calling or harness-path bugs have a distinct status so they do not contaminate the metrics?

## 9. Ablations
- Are the compared conditions isolating the intended change?
- Avoid confounding rubric changes, scoring changes, memory changes, and prompt changes in one benchmark.

## 10. Interpretation Discipline
- Do not claim more than the benchmark can support.
- If gates help but primitives do not, say exactly that.
- If measurement is still weak, fix the benchmark before escalating the claim.

## Core Rule
- Unearned trust is the enemy.
- This applies to memory, scores, evidence, and benchmark measurements.
