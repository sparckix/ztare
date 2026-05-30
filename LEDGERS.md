# Ledgers, the append-only record layer

ZTARE's machine-written ledgers are **not relocated** (47+ code paths
resolve them by path; moving them breaks the pipeline). This is the
single place to understand them, links point to each file in situ.
Public ledgers are private-ref-masked by `scripts/public/publish_mask.py`
(CI-gated). Internal ledgers stay gitignored.

| Ledger | What it records | Written by | Read by | Visibility |
|---|---|---|---|---|
| [research_areas/EXPERIMENT_TRACK_RECORD.md](research_areas/EXPERIMENT_TRACK_RECORD.md) | Canonical E/F-row experiment track record (~2.2k rows) | agents / RD | seam-health audit, NS graph stack, substrate recommender (36 refs) | public (masked) |
| [rubrics/goodhart_log.jsonl](rubrics/goodhart_log.jsonl) | Goodhart/rigging incidents per rubric | `mform_alignment_audit.py` | M-form alignment audit | public (masked) |
| [global_primitives/incidents/primitive_incidents.jsonl](global_primitives/incidents/primitive_incidents.jsonl) | Primitive-failure incidents | `extract_incidents.py`, `draft_primitives.py` | primitive drafting | public (masked) |
| [analytics/public/ledgers/catch/catch_ledger.jsonl](analytics/public/ledgers/catch/catch_ledger.jsonl) | SOX/PCAOB-style ratified catch ledger | agents (append-only) | catch validator, P0 catch-rate | internal |
| [analytics/public/ledgers/prediction/prediction_ledger.jsonl](analytics/public/ledgers/prediction/prediction_ledger.jsonl) | Pre-registered predictions + resolutions (Brier) | RD / forecast pool | calibration scorer, P0 | internal |
| [analytics/public/ledgers/reflexive/proof_health.json](analytics/public/ledgers/reflexive/proof_health.json) | GP-237 survivors: laundering tripwire + non-accumulation regression rate | `build_proof_health.py` | P0 §3.4, dashboard | internal |
| [analytics/public/ledgers/reflexive/p0_metrics.json](analytics/public/ledgers/reflexive/p0_metrics.json) | GP-236 P0 rollup (22 metrics) | `build_p0_metrics.py` | P0 dashboard | internal |
| [analytics/public/ledgers/reflexive/seam_lineage.jsonl](analytics/public/ledgers/reflexive/seam_lineage.jsonl) | GP-237 5-row curated lineage probe | reflexive mine | scope-evolution | internal |
| [analytics/public/ledgers/reflexive/bifurcation_report.json](analytics/public/ledgers/reflexive/bifurcation_report.json) | In-loop vs out-of-loop bifurcation | reflexive mine | dashboard | internal |
| [analytics/trajectory_archive.jsonl](analytics/trajectory_archive.jsonl) (+ `_enriched`) | Mined trajectory archive (volume/taste curves). Canonical path read by the mining pipeline (5+14 code refs); not moved. | reflexive mine | mine_trajectories_enrich, mine_miner_roi, pivot/ROI miners, trajectory dashboard | public (tracked, code-canonical) |
| [analytics/queries/meta_arc_acceptance_ledger.jsonl](analytics/queries/meta_arc_acceptance_ledger.jsonl) | Meta-arc acceptance decisions | research_director/meta_arc_acceptance | meta_arc_acceptance.py | public (tracked) |
| research_areas/insights_ledger.md | Mined insights ledger | reflexive mine, substrate recommender | substrate recommender | internal |
| research_areas/seams/mission/ztare_mission_hypothesis_ledger_seam.md | Mission hypothesis ledger | mission track | thesis test | internal |

**Why not consolidate physically:** the heavily-coupled ledgers
(EXPERIMENT_TRACK_RECORD alone has 36 code references) cannot move
without breaking the pipeline. This hub is the logical consolidation, 
one map, files untouched.
