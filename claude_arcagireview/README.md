# claude_arcagireview

Full-apparatus review of the ARC-AGI-3 worldmodel system (GP-250), 2026-07-15/16.
Six parallel code reviews (~50k LOC read, findings verified against live receipts and runnable probes) + campaign forensics + consolidated verdict.

| File | Scope |
|---|---|
| [00_campaign_forensics.md](00_campaign_forensics.md) | Measured campaign evidence: LOC, weakness-receipt stream, phase timings, adapter width, outcomes |
| [01_leaf_workbench_retry_review.md](01_leaf_workbench_retry_review.md) | leaf_workbench (+3,355 lines), retry surface, carrier contracts, briefing pack |
| [02_meta_governance_review.md](02_meta_governance_review.md) | engine router, k-lines, trace auditor, weakness-receipt loop, proposal funnel (106→0) |
| [03_dsl_carrier_lean_review.md](03_dsl_carrier_lean_review.md) | grid DSL, candidate pool, carrier loader, Lean bridge/equivalence, dead-code inventory |
| [04_planning_search_review.md](04_planning_search_review.md) | planner, reachability, factored search, frontier codec, goal abduction |
| [05_gates_evaluation_review.md](05_gates_evaluation_review.md) | replay/holdout gates, evidence consolidation, episode log, p0 metrics (authority path) |
| [06_abduction_synthesis_review.md](06_abduction_synthesis_review.md) | spec abduction, version space, catalog, nogoods, grammar reflex/extension |
| [07_verdict_iatrogenics_remediation.md](07_verdict_iatrogenics_remediation.md) | **Consolidated verdict: iatrogenics answer, docs assessment, prioritized remediation P0–P3, what remains for the general-purpose engine** |

Reviews are raw per-cluster reports (not merged); 07 is the synthesis.
