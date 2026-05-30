# `ztare.orchestrator`

The autoresearch-loop orchestrator. The largest single subpackage —
this is where iteration control, evidence handling, dispatch, and
post-iteration audit live.

GP-157 v5.0 extraction target: the loop logic moved out of
`autoresearch_loop` (the monolithic driver) into typed, separately
testable primitives here.

## Concerns

| Concern | Modules (examples) |
|---|---|
| **Iter context + state** | `iter_context`, `state`, `iter_state_machine`, `transition_log`, `best_state_persistence`, `champion_artifact_sync` |
| **Dispatch + control flow** | `blitz_dispatch`, `cage_authoritative`, `divergence_sweep_context`, `mutator_briefing`, `discriminator_queue` |
| **Cold-shot / seed primitives** | `cold_shot_seed`, `cold_shot_policy`, `cold_shot_discriminator`, `cold_llm_seed_requery`, `composition_seed` |
| **Contract + adherence** | `contract_adherence`, `contract_table`, `evidence_contract`, `derived_constraints_refresh`, `dynamic_rubric` |
| **Evidence + gap handling** | `evidence_gap_enrichment`, `evidence_gap_persistence`, `fitted_model`, `framer_provider`, `gen_provider` |
| **Briefings + provider plug-ins** | `briefing_compression`, `briefing_providers/` |
| **Charter critique + alien-seam loading** | `charter_critic`, `alien_math_seam_loader` |

## Conventions

- Most loop code reads `IterContext` (typed dataclass) rather than
  un-typed dict payloads.
- Fixture-regression files (suffix `_fixture_regression.py`) sit next
  to their primary modules so regressions are caught at import time.
- Side-effecting writes go through the transition log; pure functions
  are preferred for everything else.

## Relationship to neighbours

- `ztare.orchestration/` (separate subpackage) owns *cross-process*
  orchestration — agent-channel projection, A2A, task authorization.
  `ztare.orchestrator/` owns the *single autoresearch-loop iteration*.
- `ztare.research_director/` owns the science-side discipline that
  decides what the loop should attempt; this subpackage runs the attempt.
- `ztare.validator/` owns the proof-value gate that the loop's output
  must pass before promotion.

## Spec

`docs/concepts/architecture.md` and the GP-157 v5.0 / GP-216 / GP-241
seams under `research_areas/seams/`.
