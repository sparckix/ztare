# scripts/public/analytics_shared/

> **Up:** [scripts/](../../README.md) · **Siblings:** [mining/](../mining/README.md) · [validators/](../validators/README.md) · [audits/](../audits/README.md)

Cross-cutting analytics used by more than one track: apparatus
meta-review, forecast-pool auditing, the per-axis scorers that feed the
P0 page, and the public judgment-primitive export bundle. If
[mining/](../mining/README.md) produces the weekly ledgers, this folder
audits and scores them and exports the substrate-agnostic parts.

## Meta-review and audit

| Script | What it does |
|---|---|
| `apparatus_level2_review.py` | Level-2 apparatus-on-apparatus meta-review with mandatory falsifier tests (the Level 0/1/2 cognitive-gym hierarchy). |
| `audit_forecast_pool_externalities.py` | Read-only audit of forecast-pool calibration, routing, and externalities. |
| `reflexive_primitive_roi_audit.py` | GP-220 per-primitive ROI scorecard over the R8-R16 reflexive-primitive catalog. |
| `diagnose_gate_telemetry.py` | Cage-engagement telemetry diagnostic (surfaced the 0% engagement for R8/R9/R10). |
| `synthesize_audit_dashboard.py` | Cross-audit synthesis: joins the 9 single-axis audit outputs into one dashboard. |

## Nomination and closure utility

| Script | What it does |
|---|---|
| `build_codex_nomination_panel.py` | TEST C: aggregates today's apparatus output into one CSV Codex can mark up. |
| `compute_closure_utility.py` | Computes the closure-utility metric from the Codex-marked nomination panel. |
| `llm_novelty_nomination.py` | LLM novelty-nomination test under closure-utility framing (standard nominations rediscover spine edges). |
| `llm_theorem_closed_loop.py` | Minimum viable theorem-writer loop: nominate, lake build, revise, verify. |
| `idea_feliz_generator.py` | Compressed structural insights for Codex instead of asking the LLM to ship a Lean patch directly. |

## Scoring (feeds P0)

| Script | What it does |
|---|---|
| `score_insight_yield_per_minute.py` | Operator-requested metric: insight yield per agent-minute over resolved prediction-ledger rows. |
| `score_pattern_deployment_diversity.py` | PATTERN-013: deployment-diversity score from the pattern-deployment ledger. |
| `score_prediction_ledger_calibration.py` | PATTERN-012 calibration analyzer (sibling to the prediction-ledger validator: this one scores, the validator enforces). |
| `count_real_sorries.py` | Deterministic Lean sorry counter that excludes docstring substring matches (catch C-2026-05-09-78). |

## Export / sync / cartography

| Script | What it does |
|---|---|
| `export_judgment_primitives.py` | Exports the public-safe judgment-primitive bundle (JSON + optional TypeScript mirrors). |
| `export_layered_knowledge_graph.py` | Role-separated subgraphs from the unified graph so downstream consumers cannot read across roles. |
| `sync_product_judgment_primitives.py` | Syncs generated judgment primitives into downstream product repos (ZTARE stays source of truth). |
| `search_space_cartography.py` | GP-218 R1: reusable analytic over any per-generator (loss, signal) parameter sweep. |

## Related

- Produces the ledgers this scores: [mining/](../mining/README.md)
- The exported bundle is consumed by the cognitive-firm kernel and downstream product repos.
