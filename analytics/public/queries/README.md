# analytics/public/queries/

Mining + experiment query outputs (~62 code references). The miners
under `scripts/public/mining/` and the GP-2xx experiment drivers write
here; the dashboard and P0 page read from here. Almost all of it is
regenerable by re-running the relevant miner. Every child tree is
listed; individual generated files are not (re-run is the source of
truth).

## Reflexive-mining outputs

- `trajectory/` - volume + outcome curves, inflections, consequential
  artifacts (the sprint image + dashboard read these).
- `taste/` - per-artifact contextualized ratings + the weekly-stats
  roll-up (always the contextualized rater).
- `reflexive/` - reflexive-primitive ROI + recursive-gain candidates.
- `process/` - process-loop vs one-shot classification.
- `rd/` - Research-Director decision-history / calibration outputs.
- `classification/` - cross-provider classifier agreement outputs.
- `graphs/` - rendered reference-graph artifacts.

## Experiment-line outputs

- `gp215/`, `gp216/` - GP-215/216 experiment query outputs.
- `lean/` (+ `lean/gap_typed_outputs/`) - Lean prover query results +
  gap-typed prompter outputs.
- `neural_hunt/` - neural-hunt run outputs.
- `scientific_amnesia/` - amnesia-precheck history-overlap outputs.
- `surgical_swarm/` - bounded swarm-panel results.
- `curriculum_variants/` - generated toy-case obligation variants.
- `formalization_sequence/` - formalization-sequencing precheck.
- `closed_loop/` - LLM theorem closed-loop results.
- `batched_runs/`, `lambda_runs/` - batched / Lambda-GPU run outputs.
- `novelty/` (`cross_llm_nominations/`, `idea_feliz/`,
  `novelty_nominations/`) - novelty-nomination outputs.
- `openmath/` - OpenMath general-Liouville run outputs.
- `c7upper_wb/` - NS C7-upper viscous-alignment run outputs.
- `audits/` - per-run audit query outputs.
- `_regr_surface/`, `pattern_bank_redacted/` - regression-surface +
  redacted pattern-bank snapshots.

Dated one-shot query batches that are superseded are moved to
`analytics/_archive/` (the 2026-04-24 batch already was). Read
`docs/concepts/reflexive_mining_methodology.md` before trusting any
file here.
