# analytics/

Generated analytics + the append-only ledgers. Hand-authored map (not
auto-generated). Almost everything here is pipeline output or
regenerable cache, so the question per item is "does code depend on it"
not "is it source."

## What is tracked vs not

Only **3 files** under `analytics/` are git-tracked, all code-canonical
(verified by reference count, not guessed):

| Tracked file | Code refs | Disposition |
|---|---:|---|
| `trajectory_archive.jsonl` | 5 | Canonical mining archive read by `mine_trajectories_enrich`, `mine_miner_roi`, ROI/pivot miners. Not moved (path is the contract). |
| `trajectory_archive_enriched.jsonl` | 14 | Same, enriched form. |
| `queries/meta_arc_acceptance_ledger.jsonl` | 1 | Read by `research_director/meta_arc_acceptance.py`. |

Everything else under `analytics/` is untracked and either gitignored
or simply not part of the publish surface. See [`../LEDGERS.md`](../LEDGERS.md)
for the canonical ledger map.

## Subdirectories (dependency-grounded)

| Subdir | Code refs | What it is |
|---|---:|---|
| `public/forecast_pool/` | 76 | Prediction/forecast contracts, calibration, consumer state. Heavily live. |
| `public/queries/` | 62 | Mining query outputs (trajectory, taste, classification, neural-hunt). Live pipeline I/O. |
| `public/ledgers/` | 33 | Catch / prediction / reflexive / trajectory ledgers. The record layer. |
| `public/index/` | 13 | Architecture index + the (gitignored, 243 MB) `mathlib_graph`. |
| `public/gflownet/`, `public/control/`, `public/telemetry/`, `public/closure_metric_specs/` | 1-2 each | Lightly referenced support outputs. Kept. |
| `public/gnn/` | gitignored | ~19 GB ML sandboxes / pinned Lean prover builds. Regenerable cache + the **pinned v4.29.0 Carleson baseline that GP-225 verification needs**. Not an archive target (data, not code). |
| `public/dashboard/` | gitignored build | The React dashboard; built only via the operator `safe-build.sh`. |
| `private/` | gitignored | Operator-internal analytics. Never published. |
| `_archive/` | gitignored | Retired, zero-dependency content (see its README). |

## Archive decision

Inspected every subdir for code dependency. Live pipeline I/O
(forecast_pool, queries, ledgers, index, …) is kept. Two subdirs had
**zero code references** and were dated session scratch:

- `public/notes/` (15 NS-Clay working notes, several Meta-Darwin-retracted)
- `public/audits/` (7 dated Meta-Darwin audit reports)

Both moved to `_archive/` (not deleted): superseded, no dependency, the
canonical findings live in `research_areas/seams/` + operator memory.
The 19 GB of `gnn/` build caches were **not** touched: they are
regenerable data, not dead code, and one is a needed pinned build.
