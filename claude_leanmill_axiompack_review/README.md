# claude_leanmill_axiompack_review

Full-apparatus review of LeanMill + AxiomPack, 2026-07-17. Companion to `claude_arcagireview/` (same method: parallel cluster reviews with execution-verified findings + campaign forensics + consolidated verdict), plus the STP self-play research program the operator requested.

| File | Scope |
|---|---|
| [00_campaign_forensics.md](00_campaign_forensics.md) | Scale, corpus/receipt state, pending STP tasks from memory, RCA classes to check |
| [01_solver_core_review.md](01_solver_core_review.md) | solver_core cascade, kernel boundary, caches, governance stamps (~38.7k LOC package) |
| [02_autoformalization_faithfulness_review.md](02_autoformalization_faithfulness_review.md) | Roundtrip gate, faithfulness store, certificate leg, training-corpus integrity |
| [03_axiompack_review.md](03_axiompack_review.md) | Independence witnesses, ratification funnel, morphism layer, novelty-from-mechanics |
| [04_campaign_layer_review.md](04_campaign_layer_review.md) | Closure gate, audit_external, campaign executors, receipt identity, timing |
| [05_selfplay_sft_review.md](05_selfplay_sft_review.md) | **The pending STP task**: conjecturer, exporter, holdout, pass@k harness — runnable-today verdict |
| [06_stp_research_program.md](06_stp_research_program.md) | **STP literature dive** + precise falsifiable questions Q1-Q11 + experiments E1-E5 + novelty positioning |
| [07_verdict_and_program.md](07_verdict_and_program.md) | **Consolidated verdict: soundness scoreboard, iatrogenics, P0-P3 remediation, direct answers on STP/AxiomPack novelty** |

Reviews are raw per-cluster reports (not merged); 07 is the synthesis.
