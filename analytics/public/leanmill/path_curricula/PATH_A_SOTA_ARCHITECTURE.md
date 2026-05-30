# Path A/B/C SOTA Architecture Bundle

**Status:** draft, 2026-05-19.

## Key Question

Can tool-orchestrated proof execution compound when every attempt is governed and converted into residual memory?

Use fixed vocabulary for the next 30 days:

- **Path A:** proof execution and tool orchestration.
- **Path B:** governance, target-kind discipline, and anti-laundering ratification.
- **Path C:** residual trajectory memory, curriculum, and next-lever policy.

No new path labels unless A/B/C fail to cover a concrete artifact.

## Literature-Derived Shape

The strongest relevant systems do not depend on shallow whole-row routing:

- LeanDojo/ReProver: Lean interaction plus accessible-premise retrieval and hard negatives.
- COPRA: stateful proof search with executed tactics, feedback, backtracking, and retrieved lemmas.
- Baldur/APRIL: failed proof plus compiler diagnostic becomes a repair input.
- DeepSeek-Prover-V1.5: proof-assistant feedback and search/exploration beat one-shot generation.
- OProver/APOLLO: verified-proof retrieval, failure isolation, automated solvers, and targeted repair calls.
- LeanHammer/Duper/LeanSearch: public substrates to wrap, not rebuild.

## Bundle

The full bundle is A+B+C:

1. **Path A candidate context source:** retrieve verified proof snippets, premise candidates, and local sibling examples.
2. **Path A execution layer:** run bounded proof attempts in Lean.
3. **Path B governance:** classify every output as proof closure, exact gap, valid falsifier, consequence exposure, invalid, or laundered.
4. **Path C feedback capture:** persist failed tactic/block, Lean error, goal state, gate verdict, and raw output.
5. **Path C residual-to-lever compiler:** classify into syntax/import, unknown identifier, type mismatch, unsolved goal, timeout/budget, composition error, carrier mismatch, missing lemma, exact-gap candidate, or falsifier.
6. **Path C action policy:** choose a repair family: simp/rewrite, automation, arithmetic, structure/refine, exact/apply, decompose, retrieve context, increase budget, or emit exact gap.
7. **Path C curriculum:** aggregate governed trajectories into reusable OOD rows; train only after deterministic policies saturate.

## First Pull-Forward Artifact

`scripts/public/control/lean_repair_trajectory_dataset.py`

It builds machine-safe APRIL/OProver-style rows from existing ledgers and future trace directories:

```text
failed attempt -> Lean/gate feedback -> diagnosis -> repair class -> outcome
```

The first cheap test is offline: on discriminative rows only, does repair-class / error-class policy beat always-static / always-feedback / always-defer utility before any new solver spend?

## Existing Path C Substrate

The residual/memory layer is not blank. Current useful inputs:

- `analytics/public/leanmill/results/v2061_public_union_next_source_discovery_queue.json` — four source-safe candidate rows already queued.
- `analytics/public/leanmill/results/v2019_context_theorem_source_discovery.json` — three context-hydration repair lanes with target-self quarantine already recorded.
- `analytics/public/ledgers/residual_to_lever/RUNG1_RESIDUAL_LEDGER.jsonl` and `RUNG1_RICH_LEDGER.jsonl` — governed residual-to-lever rows.
- `analytics/public/leanmill/results/v2106_witness_equality_strict_sub_bucket_on_non_closing_steps.json` and `v2108_typed_label_readiness_with_witness_equality_and_hard_negatives.json` — typed-label / hard-negative substrate for later learned policy diagnostics.
- `/tmp/rung1/lean_repair_trajectory_dataset_rich.jsonl` on the VPS — round-level repair traces from completed four-arm runs.

`scripts/public/control/path_c_curriculum_queue.py` consolidates those into:

- `analytics/public/leanmill/path_curricula/PATH_C_CURRICULUM_QUEUE.json`
- `analytics/public/leanmill/path_curricula/PATH_C_CURRICULUM_QUEUE.md`

Current queue build: 12 rows after excluding rows already consumed by `LATEST_META_SOLVER_CONSUMPTION_MANIFEST.json` and downgrading rows replay-blocked by v2063 = 3 source-safe candidate generation, 2 context-hydration repair, 6 governed residual-to-lever restatements, 1 typed-label contrast acquisition. This matters twice: the older v2061 top row `current_scale_0126` is already a strict/solver row via v2068, and `current_scale_0132` is replay-blocked by identifier/context hydration. The current top unconsumed replay-smoke row is `current_scale_0080`.

## Pass Bar For The Next Path A Smoke

- No heavy Lean until the dataset builder and scoring self-tests pass.
- Evaluate only on discriminative rows: static-only, feedback-only, external-only, and no-close.
- A repair/error-class policy must beat always-static and always-feedback utility on those rows.
- If it fails, shift from routing to verified-proof retrieval/context injection.

## Current Interpretation

The nearest-neighbor proof-state router failed because it used static similarity while the successful literature uses verifier-feedback trajectories. The A+B+C bundle makes the label denser: every failed attempt becomes a governed training/evaluation unit, not just a row-level win/loss.

Timeout is a confounder, not a repair class. Treat it as a separate C action: increase budget, decompose, or abstain. Do not count timeout-only labels as semantic proof repair signal.

VPS split scoring on the rich repair traces sharpened this:

- Non-timeout rows: `29` targets, `28` positive; first-observed and best policy both `0.955` utility/target. There is no semantic repair-policy lift after removing timeout.
- Timeout-only rows: `17` targets, `0` positive; always-abstain utility/target `0.350`, first-observed `-0.300`. Timeout rows should go to decompose/abstain/budget-control, not repair routing.

So the immediate Path C win is a regime classifier and curriculum queue, not a learned semantic repair selector yet. The next useful A experiment must pull a new action from the queue and static-check/smoke it; another broad A-vs-B1 run is premature.

First queue pull-forward result: `current_scale_0080` produced one compiling canary candidate on the VPS:

```lean
have hq : q ∈ affineSpan k (range b) := by
  rw [b.tot]
  trivial
classical
obtain ⟨w, hw, rfl⟩ := eq_affineCombination_of_mem_affineSpan_of_fintype hq
trans ∑ i, w i
· exact Finset.sum_congr rfl (fun i hi => b.coord_apply_combination_of_mem (Finset.mem_univ i) hw)
· exact hw
```

Resolved transport result: the direct injected `Lean.collectAxioms` audit is clean-STD-only, and after patching `PersistentLean` to resolve the `lake` executable explicitly in non-login VPS processes, `authoritative_axioms.govern` returns official `closure` with reason `axioms_subset_STD`. Persisted proof: `/tmp/rung1/ratified_proofs/gp225_v1795_v1800_current_scale_0080_20260519T205044.lean`. Treat this as a one-row Path-C promotion plus Path-B transport repair, not as a broad Path-A solver-lift claim.
