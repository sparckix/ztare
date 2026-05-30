# analytics/public/

The public analytics surface. Almost all of it is pipeline output or
regenerable cache; only 3 files under `analytics/` are git-tracked
(see `../README.md`). Every subdirectory is listed here; the
data-heavy ones are documented at this level and by their own README
rather than per generated file.

| Subdir | What it holds |
|---|---|
| `ledgers/` | The append-only record layer (catch, prediction, reflexive, trajectory, forward_evidence, pattern_deployment, external_prover, research_yield_decomposition). See its README + `../../LEDGERS.md`. |
| `queries/` | Mining + experiment query outputs (~24 child trees: trajectory, taste, classification, lean, gp215, gp216, novelty, scientific_amnesia, …). See its README. |
| `forecast_pool/` | Prediction / forecast layer (contracts, outcomes, scores, aggregates, consumer_state, …). See its README. |
| `index/` | Architecture index + the gitignored 243 MB `mathlib_graph`. |
| `gnn/` | ~19 GB ML sandboxes + pinned Lean prover builds. **Gitignored** (regenerable; includes the pinned v4.29.0 Carleson baseline GP-225 needs). |
| `dashboard/` | The React dashboard; built only via the operator `safe-build.sh`. |
| `closure_metric_specs/` | Declarative closure-metric specs. |
| `telemetry/` | Run telemetry (agent activity, insight yield, sorry counts). |
| `gflownet/` | GFlowNet baseline artifacts (GP-225). |
| `control/` | Tick-lifecycle control state. |

Generated child directories (e.g. `forecast_pool/outcomes/`,
`queries/gp216/`) are not given their own README: that would recreate
the sprawl removed on 2026-05-17. Their parent README enumerates and
explains them.
