# Scripts Reorg Triage — 2026-05-09

## Current state

The root contract is now enforced:

- `scripts/` contains only `public/` and `private/`
- `scripts/public/` now contains bucket directories plus the two policy docs
- the main cleanup target has shifted from root-file sprawl to internal bucket
  consistency

Established buckets:

- `scripts/public/control/`
- `scripts/public/analytics_shared/`
- `scripts/public/validators/`
- `scripts/public/lean/`
- `scripts/public/models/`
- `scripts/public/projects/ns/`
- `scripts/public/projects/riemann/`
- `scripts/public/projects/neural_hunt/`
- `scripts/public/projects/ztare_on_ztare/`

## First moves completed

Moved out of root:

- ZTARE-on-ZTARE:
  - `score_external_corpus_coverage.py`
  - `joint_cross_walk.py`
  - `gp219_phase3_crosswalk.py`
- Riemann:
  - `riemann_operator_search_gpu.py`
  - `riemann_multiplicative_search.py`
- Model family:
  - all `gnn_*`
  - all `gflownet_*`
  - `lora_dataset_prep.py`

These moves were path-rewritten and `py_compile`-checked.

## Root census by class

### Clear NS tranche

`35` files are obvious NS/Clay-campaign scripts and should move next to
`scripts/public/projects/ns/`.

Examples:

- `ns_*`
- `W6_*`
- `A8*`
- `EQ_*`
- `verify_4mode_stationary_NS_collapse.py`
- `verify_helicity_IBP_factor.py`

### Clear control-plane tranche

`24` files are repo-wide control / validator / preflight entrypoints.
These should ultimately be the small set that remain at root or move into
`scripts/public/control/` and `scripts/public/validators/`.

Examples:

- `agent_daemon.py`
- `rd_tick_brief.py`
- `predispatch_check.py`
- `primitive_tick_surface.py`
- `query_graph.py`
- `render_architecture_index.py`
- `validate_*`
- `org_*`

### Clear Lean/proof-tooling tranche

`22` files are shared theorem/proof tooling and should move next into
`scripts/public/lean/`.

Examples:

- `lean_decl_index.py`
- `lean_fast_compile.py`
- `lean_tactic_hammer.py`
- `llm_lean_prover.py`
- `mathlib_lemma_scout.py`
- `typed_endpoint_*`
- `typed_patch_proposer.py`
- `auto_prover_harness.py`

### Mixed remainder

`93` files still need a sharper call. They are not all truly mixed; they are
just under-foldered.

The main sub-buckets inside this remainder are:

1. analytics/public/reporting helpers
2. substrate/gameable eval harnesses
3. one-off mathematical probes
4. model-family orchestration wrappers
5. historical experiment drivers

## Placement criteria

### Put under `scripts/public/projects/<project>/` if:

- the script hardcodes one project workspace
- the script's outputs are only meaningful for one project
- the name already exposes one substrate or project family

### Put under `scripts/public/lean/` if:

- it operates on Lean files, declarations, proof search, stubs, or theorem
  obligations across projects

### Put under `scripts/public/models/` if:

- it trains, scores, evaluates, or prepares data for reusable model families

### Put under `scripts/public/control/` if:

- it is part of the repo-wide control plane, predispatch, agent runtime,
  bootstrap, or orchestration path

### Put under `scripts/public/validators/` if:

- its only job is to validate a ledger, map, rubric, or contract

### Leave at root only if:

- it is a stable public entrypoint used across multiple buckets
- moving it would create more indirection than clarity

## Next tranches

1. tighten bucket boundaries inside `scripts/public/`
2. decide whether `cold_llm_null/`, `framer/`, `gp154_diagnostics/`, and
   `substrate_management/` should remain top-level buckets or fold deeper
3. keep new additions out of `scripts/public/` root unless they are docs or
   true top-level bucket directories

## Anti-drift rule

Do not add a new root script if:

- it is project-specific
- it is a one-off experiment driver
- its name needs a substrate prefix to be understandable

That script already belongs in a subtree.
