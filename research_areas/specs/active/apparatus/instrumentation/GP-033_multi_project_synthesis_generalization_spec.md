# GP-033 Multi-Project Synthesis Generalization Spec

## Status

`implemented` — spec written 2026-04-11 16:19:55, implementation landed 2026-04-11 16:19:55, hardened 2026-04-11 17:20:31, live-verified 2026-04-11 17:27:05.

## Objective

Generalize synthesis so several projects can be rendered into one report artifact through explicit renderer types, not just `field_manual`.

## Slice

Support:

- `python -m src.ztare.synthesis.synthesize --projects p1,p2 --renderer-type research_note`
- `python -m src.ztare.synthesis.synthesize --projects p1,p2 --renderer-type decision_brief`

Keep:

- `field_manual` on its specialized multi-project path
- single-project behavior unchanged

Do not support in slice 1:

- `--pack` with `--projects`
- implicit renderer selection for multi-project mode
- merged synthetic project directories

## Slice 2 Hardening

The first live EU render exposed two generic shortcomings that this spec now treats as part of the same seam:

1. multi-project report synthesis must preserve bounded quantitative priors even when the top-line forecast remains unresolved
2. multi-project report synthesis must not quietly reuse stale full-history summaries or prompt-mismatched caches after the operator changes history mode or extraction prompts

So the generic contract is extended as follows:

- multi-project `research_note` runs default to `focused` history unless the operator explicitly passes `--history-mode full`
- `summarize_history` cache reuse requires matching:
  - `history_mode`
  - `source_paths`
  - prompt hash
- malformed cached ledger reuse requires matching prompt hash as well as prior path/digest checks
- ledger extraction prompts must expose:
  - `forecast_status`
  - `quantitative_anchors`
  - `working_priors`
- `research_note` must render a compact `Working Ranges` section whenever those fields exist

## Contract

### Inputs

- explicit `--projects`
- explicit `--renderer-type`
- optional `--history-mode`

### Aggregation

For each project:

1. sniff context
2. ensure `history_summary.json`
3. ensure `ledger.json`
4. assemble compact per-project payload

Combined multi-project mode then:

1. writes `aggregated_corpus.*.json`
2. writes `history_summary.*.json`
3. extracts one combined ledger through a dedicated multi-project prompt
4. derives one combined brief
5. renders and QA-checks one combined report

### Output Scoping

Multi-project artifacts must be fully scoped by:

- renderer type
- project-list hash

This applies to:

- context
- ledger
- brief
- history summary
- aggregated corpus
- QA artifact
- candidate report
- final report

No shared single-project synthesis artifact may be overwritten by a multi-project run.

## Verifier

1. fixture regression for scoped paths / merged history summary / ledger cache matching
2. live render on a real multi-project pair, starting with:
   - `eu_union_decisive_pillars`
   - `eu_union_failure_probability_2035`
3. confirm that the combined report preserves:
   - the distinction between `component_only` and a fully earned top-line forecast
   - the EU failure project's bounded working ranges

Verifier outcome:

- passed on `eu_union_decisive_pillars + eu_union_failure_probability_2035`
- final report written
- QA score `98`

## Shipped Files

- `src/ztare/synthesis/synthesize.py`
- `config/prompts/extract_ledger_multi_project.md`
- `config/prompts/extract_ledger.md`
- `config/renderers/research_note.md`
- `src/ztare/synthesis/synthesize_multi_project_fixture_regression.py`
