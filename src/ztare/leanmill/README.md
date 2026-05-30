# `ztare.leanmill`

LeanMill engine — the importable surface for the GP-225 station factory.

This is the kernel-resident home for the LeanMill primitives that
passed the boundary tests in `scripts/README.md` (falsifier-survival,
cross-caller, stable contract). Operator scripts under
`scripts/public/control/leanmill_*` may import from here; this package
must never import from `scripts/`.

## Modules

| Module | Role |
|---|---|
| `common` | Canonical helpers (`read_json`, `write_json_atomic`, `run`, `sqlite_open`) consolidated from the duplicated worker primitives. |
| `paths` | Single source of truth for LeanMill path constants. |
| `policy` | Factory-policy loader (`read_policy`, `apply_profile_section`). |
| `work_queue` | SQLite WorkItem queue + append-only JSONL event ledger. The apparatus's durable bus. |
| `contracts/source_query` | Typed source-query contract — `schema: leanmill-source-query-contract-v1`. |
| `contracts/learning_feedback` | Typed non-credit learning-feedback contract — canonical exit precedence, malformed negative-control detection, and capped feedback entries. |

## Shims under `scripts/public/control/`

Five scripts at the operator surface re-export from this package so the
existing sibling-import patterns (`import leanmill_work_queue as work_queue`,
`from leanmill_paths import FACTORY_POLICY`, etc.) continue to resolve
without modification:

```
scripts/public/control/leanmill/work_queue.py            → ztare.leanmill.work_queue
scripts/public/control/leanmill/paths.py                 → ztare.leanmill.paths
scripts/public/control/leanmill/factory_config.py        → ztare.leanmill.policy
scripts/public/control/leanmill/source_query_contract.py → ztare.leanmill.contracts.source_query
scripts/public/control/leanmill/learning_feedback_contract.py → ztare.leanmill.contracts.learning_feedback
```

## Invariants

- Side-effect-free at import time.
- Stdlib + `ztare.leanmill.paths` only — no transitive script imports.
- Every public name is enumerated in each module's `__all__`.
- Every module ships a `_self_test()` (or, for the queue, a `self-test`
  CLI subcommand) that covers the happy path.

## Spec

Current process flow, lane topology, and operating picture:
`docs/concepts/leanmill_architecture.md`.

Durable decision/spec boundary:
`research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md`
and `research_areas/specs/active/engine/lean/GP-225_leanmill_vnext_station_factory_spec.md`.

The pre-registered four-arm Evaluation Harness contract lives at
`analytics/public/leanmill/dashboard_data/evaluation_harness_contract.json`.
