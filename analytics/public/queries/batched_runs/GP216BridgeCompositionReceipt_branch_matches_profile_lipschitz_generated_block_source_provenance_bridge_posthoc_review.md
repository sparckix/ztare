# GP216 Batched Candidate Pilot — Posthoc Review

Recorded: 2026-05-06 16:27:00 EDT

Target: `GP216BridgeCompositionReceipt.branch_matches_profile_lipschitz_generated_block`

Run artifact: `analytics/queries/batched_runs/GP216BridgeCompositionReceipt_branch_matches_profile_lipschitz_generated_block_source_provenance_bridge.json`

Budget estimate: `$0.1927` under hard cap `$0.50`.

Outcome: 2 candidates compiled, but both were tautological accessor wrappers:

- `idx=0`: proves the exact target equality by `exact R.branch_matches_profile_lipschitz_generated_block`
- `idx=1`: proves the symmetric equality by `exact R.branch_matches_profile_lipschitz_generated_block.symm`

Closure verdict: `0/2` useful proof-progress candidates.

Apparatus verdict: useful falsifier of the old anti-degeneracy metric. A compiled declaration is not enough; swarm hits that directly re-export the target structure field must be demoted before they count as verified closure progress.

Patch shipped: `scripts/lean/batched_candidate_generator.py` now marks one-line `exact`/`simpa using` wrappers over the requested target field as `degenerate_reason = "direct_target_field_accessor"`.

Utility classification: not 10x on this endpoint. The run was a cheap diagnostic that prevented future false positives, but it did not close a source constructor.
