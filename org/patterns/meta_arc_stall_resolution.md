---
id: PATTERN-020
name: meta_arc_stall_resolution
version: 1
status: active
discovered: 2026-05-09
discovered_reason: |
  META-DARWIN audit on pattern architecture (2026-05-09 evening) found
  this primitive at src/ztare/research_director/meta_arc_matcher.py
  (GP-215) was missing from the catalog. Direct addressing of the
  "operator manually scrolls through prior arcs to find applicable
  meta-move" bottleneck — exactly the recency-bias structural defect
  that prompted PATTERN-013 (pattern_deployment_ledger).
triggers:
  lexical: [stall, stuck, meta-move, arc, bottleneck, "no progress"]
  structural:
    - K consecutive iterations with no score movement
    - free-form stall description authored by RD or operator
    - need to select a meta-move that has historically resolved similar stalls
  problem_classes: [orchestration_meta_architecture, recency_bias_correction]
spawn:
  mode: kernel_call
  module: src.ztare.research_director.meta_arc_matcher
  inputs:
    - free_form_stall_description: str
    - cycle_catalogue_files:
        - gp215_cycles_filled.json  # NS substrate
        - gp215_cluster6_subdivision.json  # NS sub-clusters
        - gp215_results.json  # singleton clusters
        - gp215_cycles_aqual.json  # AQUAL substrate
        - gp215_cycles_neural.json  # neural-scaling substrate
  outputs:
    - top_K_meta_moves: ranked by cosine embedding score, source-attributed
    - adversary_move: highest-ranked move from a DIFFERENT cluster (monoculture guard)
related_patterns:
  - id: PATTERN-013
    relation: complement  # pattern-deployment-ledger flags monoculture; this provides the corrective meta-move
  - id: PATTERN-002
    relation: secondary  # adversary_move is darwin-style cross-cluster check
  - id: PATTERN-019
    relation: feeds  # adaptive eigenquestion generation can use the stall description
references:
  - existing kernel: src/ztare/research_director/meta_arc_matcher.py
  - cycle catalogues: analytics/public/gp215_cycles_*.json
  - GP-215 (NASA-LLIS bottleneck artifact, embedding-ranked stall→move match)
falsifiable_test: |
  Once routed on the K=3-no-movement stall trigger, over N>=12 stalls where
  PATTERN-020's top-K or adversary_move was deployed within 1 iteration, median
  time-to-next-score-movement must be <=0.6x the median for matched stalls resolved
  by RD free-recall meta-move selection. If catalogue-ranked meta-moves do not cut
  time-to-unstick to at most 0.6x the free-recall baseline, the ranking apparatus
  adds no measurable lift and demotes.
  metric_source: agent_telemetry.jsonl (meta_arc_matcher dispatches tagged
  PATTERN-020) joined to substrate score-progression telemetry; matched free-recall
  control stalls drawn from the same substrates' pre-wiring history.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-020 — Meta-Arc Stall Resolution

## What this pattern is

A **meta-move ranking apparatus** that takes a substrate's free-form
stall description and returns ranked candidate meta-moves drawn from
a curated cycle catalogue (GP-215; NASA-LLIS-style bottleneck artifact
ranking). Cosine embedding score over the catalogue's clustered
prior-arc descriptions. Plus a **monoculture-guard adversary move**:
the highest-ranked move from a *different* cluster than the top-K,
enforced as a structural anti-anchoring check.

## When to deploy

* **K consecutive iterations with no score movement** (default K=3 on
  any substrate): fire PATTERN-020 to rank candidate meta-moves.
* **Operator-typed "we are stuck"** signal: convert to free-form stall
  description and dispatch.
* **PATTERN-013 monoculture flag fires**: PATTERN-020 is one of the
  structural corrections — get a candidate cross-cluster meta-move
  from the catalogue.
* **Pre-cold-shot**: before a paid PATTERN-014 dispatch, run
  PATTERN-020 to surface candidate meta-moves the RD has not tried
  yet; the cold-shot can then be eigenquestion-shaped around
  evaluating the candidate move rather than open-ended exploration.

## Anti-anchoring discipline: the adversary move

The kernel-level meta_arc_matcher.py emits not only the top-K matched
moves but also an `adversary_move`: the highest-ranked move from a
cluster DIFFERENT from the top-K's clusters. This is a structural
anti-anchoring guard — even if the cosine ranking concentrates within
one cluster, the operator/RD always sees one cross-cluster candidate.

**Always include the adversary_move in any decision-doc derived from
PATTERN-020.** Discarding it without justification is a defect.

## Falsifiable-asymmetry test (per PATTERN-005)

The pattern is "working" iff: substrates where PATTERN-020's top-K
output (or adversary_move) was deployed within 1 iteration of the
stall signal have a shorter time-to-next-score-movement than
substrates where the RD picked a meta-move via free recall.
Empirically testable from `analytics/public/telemetry/agent_telemetry.jsonl` joined
with substrate score-progression telemetry.

## Anti-laundering catches

* **Cosine-only-laundering**: ranking by cosine score alone over a
  catalogue with hidden bias (e.g. an over-represented prior cluster)
  produces a biased top-K. The adversary_move guard is the structural
  defense; if discarded the laundering re-enters.
* **Catalogue staleness**: gp215_cycles_*.json is a snapshot; if not
  refreshed when new clusters emerge, the apparatus blinds itself to
  recent meta-moves. Refresh cadence: per major architectural shift
  (new substrate, new failure-class promotion).
* **Free-recall laundering**: the RD or operator describes the stall
  in language that matches a familiar cluster, biasing cosine ranking.
  Mitigation: include the raw substrate context in the dispatch, not
  just the natural-language stall description.
