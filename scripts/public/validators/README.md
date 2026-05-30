# scripts/public/validators/

> **Up:** [scripts/](../../README.md) · **Siblings:** [audits/](../audits/README.md) · [analytics_shared/](../analytics_shared/README.md) · [lean/](../lean/README.md) · [mining/](../mining/README.md) · [control/](../control/README.md)

Schema and discipline validators. Each one is a fail-closed gate: it
re-asserts that a durable artifact (an index, a ledger, an arch-map, a
rubric) still matches the contract a downstream consumer relies on, and
exits non-zero when it does not. These are wired into `make` targets and
the pre-tick / post-tick surfaces, so a broken contract stops the loop
instead of silently corrupting later runs.

## Drift validators (claim vs live source)

Re-derive a claim from its source and fail if the recorded map drifted.

| Script | What it does |
|---|---|
| `validate_autoresearch_arch_map.py` | GP-101 ex-ante and ex-post drift check: iterates (arch-map, source-file) pairs, asserts each map's claims against its live source. |
| `validate_knowledge_graph.py` | GP-216d knowledge-graph drift validator, the Pattern-10 sister of the arch-map check. |
| `validate_architecture_index.py` | Validates the `architecture_index.jsonl` schema so the hard-key render step cannot crash on a missing field. |
| `validate_forecast_contracts.py` | Validates `forecast_pool/contracts/*.json` against the required-field contract the pool daemon assumes. |

## Append-only ledger integrity (SOX-analog)

Independence-and-retention checks: the proposer of a row may not be its
sole attestor.

| Script | What it does |
|---|---|
| `validate_catch_ledger.py` | Catch-ledger integrity: concurring-partner independence (AS 1220) plus workpaper retention (AS 1215). |
| `validate_forward_evidence.py` | Same independence and retention pattern for the v35 forward clean-corpus accrual gate. |
| `validate_prediction_ledger.py` | Enforces the PATTERN-012 prediction-ledger logging contract (gate half; scorer half lives in [analytics_shared/](../analytics_shared/README.md)). |

## Surfacing / forcing-function gates

Close recurring "prescription surfaced but never used" failure classes
by making non-use a hard stop.

| Script | What it does |
|---|---|
| `validate_prescription_surfacing.py` | Closes the buried-prescription / point-fix treadmill class: prescriptions must be surfaced and promoted, not point-fixed. |
| `validate_primitives_considered.py` | Sibling forcing core for the surfaced-but-not-used primitive failure (the menu catch-22). |
| `validate_agent_task_discipline.py` | Reflexive Primitive 6: agent procedural self-audit, the task-discipline analogue of the arch-map validator. |
| `validate_genuinely_new.py` | Mechanized novelty-sourcing gate, born from the 2026-05-16 SIE false-escape bug (rows mis-sourced as escape-route). |

## Pre-flight validators

| Script | What it does |
|---|---|
| `validate_rubric.py` | Deterministic rubric + project pre-flight: enforces every rule in the rubric specification before a run starts. |
| `validate_evidence.py` | GP-162 / GP-157 evidence pre-flight: catches the substrate-construction issues that cause silent run failures. |

## Related

- Concepts: [epistemic principles](../../../docs/concepts/epistemic_principles.md), [anti-pattern catalog](../../../docs/concepts/anti_pattern_catalog.md)
- Ledger layer these guard: [LEDGERS.md](../../../LEDGERS.md)
- Dynamic counterpart (gates that run, not schemas that hold): [audits/](../audits/README.md)
- Operator-internal gates (publish-safety, prose, docs-freshness) live in `scripts/private/` and run via `make gates`.
