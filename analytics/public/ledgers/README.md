# analytics/public/ledgers/

The append-only record layer (~33 code references). See the
repo-level [`LEDGERS.md`](../../../LEDGERS.md) for who writes/reads
each ledger and its visibility. All 8 child trees listed.

- `catch/` - SOX-style ratified catch ledger (append-only,
  concurring-agent gate) + its schema. Input to the P0 catch-rate.
- `prediction/` - pre-registered predictions + resolutions (Brier) +
  the prediction-ledger README.
- `reflexive/` - the GP-236/GP-237 reflexive outputs:
  `p0_metrics.json`, `proof_health.json`, `bifurcation_report.json`,
  `seam_lineage.jsonl`, `scope_evolution.json`, `artifact_index.jsonl`,
  `proof_fingerprints_prev.json`, plus the reflexive README.
- `trajectory/` - mined trajectory roll-ups.
- `forward_evidence/` - forward-evidence ledger + its schema.
- `pattern_deployment/` - PATTERN-deployment ledger (which patterns
  fired, when).
- `external_prover/` - external-prover dispatch ledger (cost-capped
  cross-family runs).
- `research_yield_decomposition/` - GP-233 scientific-yield evidence
  ledger.

Ledgers are appended by code by path; do not move or reformat them
(byte-stability is a contract for the validators and the masker).
