# scripts/public/mining/

> **Up:** [scripts/](../../README.md) · **Siblings:** [analytics_shared/](../analytics_shared/README.md) · [validators/](../validators/README.md) · [control/](../control/README.md)

The reflexive-mining pipeline: re-mine every authored artifact weekly,
score insight density with the contextualized rater, write the ledgers
the dashboard and P0 page read. Read
`docs/concepts/reflexive_mining_methodology.md` before any run.
Outputs land under `analytics/public/ledgers/` and
`analytics/public/queries/`.

## Layout

| Path | What lives there |
|---|---|
| `mining/` (this directory) | **Canonical pipeline.** Files invoked by `run_reflexive_mine.py` plus the helpers they share. |
| `mining/research_mode/` | **One-shot research analyses.** Each file answered a specific ticket (GP-148/149 weakest-link, closure/process miners, substrate audits). Not on the weekly path. |

Anything not present in either directory has been archived to
`scripts/public/_archive/mining_vestigial_20260523/`.

## Orchestration and canonical paths

| Script | What it does |
|---|---|
| `run_reflexive_mine.py` | The single canonical weekly entrypoint: runs every phase below in order. |
| `_canonical_paths.py` | Single source of truth for every mining path (the scripts-reorg stranded scripts at pre-reorg paths; import from here, never hardcode). |

## Stage 1: extract and enrich

| Script | What it does |
|---|---|
| `mine_trajectories.py` | Build the unified JSONL archive of ZTARE iteration trajectories across `projects/*/`. |
| `mine_trajectories_enrich.py` | GP-148 Stage-1.5: append the operator-required fields to the trajectory archive. |

## Curves, inflections, compounding

| Script | What it does |
|---|---|
| `mine_trajectory_curves.py` | GP-227 Phase 1: sophistication / insight / confound curves from the artifact-creation record. |
| `detect_inflections.py` | GP-227 step 2: MAD change-point + multi-metric convergence on those curves. |
| `mine_reference_graph.py` | Apparatus compounding via the cross-artifact citation graph (closes the compounding blind spot). |
| `build_consequential_artifacts.py` | Per-week consequential-artifact digest (joins sample, week, and taste). |
| `mine_recursive_gain_candidates.py` | Aggregates all mining scorecards into one ranked recursive-gain candidate list. |

## Taste (quality) rating

| Script | What it does |
|---|---|
| `sample_artifacts_for_taste.py` | Deterministic stratified sample across artifact kinds (volume is not quality). |
| `build_context_primer.py` | Build the contextualized rater's primer (the cold rater never gives 5 because it has no codebase context). |
| `rate_artifacts_for_taste.py` | The LLM taste rater over the sampled artifacts. |
| `aggregate_taste.py` | Roll ratings into weekly insight-quality curves (always pass `--rater-id`; contextualized is canonical). |

## Climb triggers and proof health

| Script | What it does |
|---|---|
| `mine_climb_triggers.py` | GP-148 Ticket E: isolate consecutive iteration pairs with a large positive score delta. |

## P0 / GP-236 / GP-237 builders

| Script | What it does |
|---|---|
| `build_p0_metrics.py` | GP-236 P0 rollup, deterministic and zero-token: the instrument documenting its own metrics (consumer, not recomputer). |
| `build_proof_health.py` | GP-237 survivors only: the laundering tripwire + non-accumulation regression rate (v1/v3/v4 sophistication scores were killed). |
| `build_graph_sowhat.py` | The per-graph "so what" freshness gate + numbers digest (not templated). |

## `research_mode/` — one-shot research analyses

These produced specific findings for a specific ticket; they are not
on the weekly path and are not part of `run_reflexive_mine.py`. Kept
for reproducibility and as a parts library when a new analysis needs
the same plumbing.

| Script | Ticket / purpose |
|---|---|
| `mine_weakest_link_taxonomy.py` | GP-148 Ticket A: cluster weakest-point strings into a failure taxonomy. |
| `mine_weakest_link_llm_classify.py` | GP-148 Stage-3 lite: LLM classifier for strings the keyword taxonomy left unclustered. |
| `mine_pivot_effectiveness.py` | GP-148 Ticket B: how topological pivot events affect score. |
| `mine_score_ceilings.py` | GP-148 Ticket D: max score achieved per (project, rubric, mutator) group. |
| `mine_lollapalooza_hypothesis.py` | GP-148 Ticket C: tests the pre-registered Lollapalooza hypothesis (Popper P1). |
| `mine_champion_trajectory_sequence.py` | GP-149 I-4: weakest-link class sequence for every group that reached score ≥ 90. |
| `mine_judge_stratified.py` | GP-149 oracle-illusion countermeasure: stratify by (mutator, judge) instead of pooling. |
| `mine_cross_provider_classifier_agreement.py` | GP-149: classify a stratified sample under three LLM providers and measure agreement. |
| `mine_closure_patterns.py` | Layer-3 substrate: when obligations close, what structural moves recur. |
| `mine_process_loops.py` | Auto-detect loop vs one-shot artifacts. |
| `mine_structural_analogies.py` | Pair one-shots with analogous loops. |
| `mine_cap_kind_distribution.py` | Cross-substrate cap-kind distribution from `cap_kind_iter_*.json`. |
| `mine_v2_substrate_outputs.py` | Mine the v2 substrate's run history ex-post for insights. |
| `mine_v5_op_temporal_ordering.py` | Temporal ordering of v5 ops applied during closure events. |
| `llm_enrich_v5_op_tags.py` | LLM-enriched v5-op tagging on the verified-axioms corpus (keyword tagger caught only ~4.2%). |
| `cross_source_divergence_audit.py` | Kernel of the ACRR/PECVP primitive: process-external cross-verification divergence. |
| `triangulate_per_target.py` | Per-target dossier joining the 4 most useful miner outputs by target name. |

## Related

- Audits + scorers that consume these ledgers: [analytics_shared/](../analytics_shared/README.md)
- Methodology (read first): `docs/concepts/reflexive_mining_methodology.md`
- Concept: [reflexive engineering](../../../docs/concepts/reflexive_engineering.md)
