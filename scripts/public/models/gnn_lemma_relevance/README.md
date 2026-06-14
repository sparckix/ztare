# scripts/public/models/gnn_lemma_relevance/

> **Up:** [models/](../README.md) · [scripts/](../../../README.md)

The GP-225 lemma-relevance / proof-repair-router experiment lineage
(about 600 files). This is a monotonic research version-series, not a
flat code package, so it is documented by its structure rather than
file by file: a per-file list of 600 numbered experiments would be
noise, and each file's own docstring already states what it tries and
what it fixes over the prior.

## Naming convention

`vNNN_<short_name>.py` (with `.sh` GPU-wait launchers). `NNN` is a
strictly increasing experiment index. Examples:
`v100_neighborhood_similarity_graph_backtest`,
`v103_nonbootstrap_interface_role_extractor`,
`v111_public_competitor_benchmark_matrix`,
`v116_action_selection_overfit_audit`.

## How to read it

- The **highest vNNN** for a given line is the current state; lower
  versions are the recorded trajectory, kept deliberately because the
  audit-of-the-audit needs the prior attempts to verify nothing was
  laundered.
- Files named `*_audit`, `*_falsifier`, `*_overfit_audit`,
  `*_tie_audit`, `*_competitor_*` are the Meta-Darwin / falsification
  checks on the immediately preceding version.
- `production_hit10_falsifier.py` and the `remote_v5x_gpu_wait_run.sh`
  launchers are the production-grade evaluation entrypoints.
- Compatibility wrappers in the parent [models/](../README.md)
  (`gnn_lemma_relevance_v21_rerank.py`, etc.) delegate here so older
  call-sites keep resolving after the move.

## Archive policy

Nothing here is archived: it is an active GP-225 line, recently
touched, and the version trajectory is itself the evidence. The
non-subsumed verdicts (what beat the LeanHammer baseline and what did
not) live in the GP-225 seams + operator memory, not in these files.
Checkpoints and large run output go under `analytics/public/gnn/`
(gitignored).

## Related

- Parent + compatibility wrappers: [models/](../README.md)
- Lean obligations these rank: [lean/](../../lean/README.md)
