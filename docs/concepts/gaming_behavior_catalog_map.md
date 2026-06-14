---
description: "Source-of-truth map for gaming behavior lifecycle: incident catalog, vector registry, promotion governance, runtime gates, and primitive precedents."
---

# Gaming Behavior Catalog Map

> **Up:** [Documentation map](../README.md)

This is the routing page for gaming-vector files, status, promotion, and
kernel-hardening operations. If another document needs mechanics, it should link
here instead of restating counts, file precedence, or promotion steps.

There are several files because the repo tracks a lifecycle, not one object. A
bad behavior starts as an incident or mined candidate. It only becomes a live
gate after the repo records what happened, decides whether the vector is real,
and verifies that the fix catches it.

```text
incident / behavior observed
  -> bounty / honeypot report or mined candidate
  -> reusable public explanation
  -> mined vector row with status
  -> promotion receipt / hardening board
  -> runtime enforcement in code or rubric
  -> reusable primitive precedent
```

The confusing part was documentation drift: the public catalog,
[GP-086](../../research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md)
seam, V4 board, and new vector registry were all describing adjacent layers.
This page says which layer owns which fact.

## Current Status

As of 2026-06-07, the live registry has 17 rows: 17 `gated`, 0 `open`.

Open rows:

None.

Intermediate notes such as "11 vectors, 8 gated, 3 open" or "9 gated, 8 open" are stale snapshots.

## Literature Positioning

Do not present the 17 live rows as a complete taxonomy of reward hacking. The
claim is narrower:

```text
paper lineage: original 9 benchmarked strategies
live registry: empirical engineering registry of observed or mined vectors
public literature: broader reward-hacking / specification-gaming family
```

The broad phenomenon is already public: objective misspecification, reward hacking, specification gaming,
Goodhart pressure, and reward-model overoptimization. The ZTARE contribution is operational and empirical:
rows are tied to concrete incidents, reproductions, promotion receipts, or runtime gates. Some rows are
plain variants of known families; some formal-substrate rows, especially Lean proof-context vectors, are
more specific than the public taxonomies usually name.

Relevant public anchors:

| Work | Why it matters here |
|---|---|
| [Specification Gaming Examples in AI](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/) / [examples list](https://docs.google.com/spreadsheets/d/e/2PACX-1vRkofjz0pB4RupYtFy87Te2F_U2GLaQmBvkUVCV4B5j3NQ00rV9FbI1fzcD1OBkFhQ/pubhtml) | Classic collection showing agents satisfy the literal objective while violating the intended task. |
| [Scaling Laws for Reward Model Overoptimization](https://arxiv.org/abs/2210.10760) | Measures Goodhart pressure when optimizing an imperfect proxy reward model. |
| [Recent Frontier Models Are Reward Hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking/) | Empirical frontier-model examples on agentic software / AI R&D tasks; closest public neighbor to live evaluator gaming. |
| [SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents](https://arxiv.org/abs/2605.21384) | Coding-agent benchmark framing for reward hacking in long-horizon tasks. |
| [Hack-Verifiable Environments](https://arxiv.org/abs/2605.20744) | Environment design where task success and hackability can be studied together. |

Use this wording publicly:

> The catalog is not a complete ontology. It is a lower-bounded, empirical registry of gaming mechanisms
> observed or mined in ZTARE runs. The original paper freezes the first nine benchmarked strategies. Later
> rows extend the operational registry and are grouped by enforcement surface rather than claimed as
> mutually exclusive theoretical kinds.

## What To Open

| Question | Open this |
|---|---|
| What is the current status of a vector? | `analytics/public/queries/gaming_vector_catalog.jsonl` |
| What does the behavior mean in plain English? | `docs/cheating_catalog.md` |
| Where is the gate actually enforced? | `src/ztare/gates/`, `src/ztare/validator/*`, `src/ztare/leanmill/solver/*` |
| How did a vector get promoted? | `analytics/public/queries/gaming_vector_promotion_evidence/*.json` |
| What was the old V4 hardening-board state? | `projects/epistemic_engine_v4/meta_runner_state.json`, `projects/epistemic_engine_v4/README.md` |
| What governed old staged evaluator hardening? | `src/ztare/validator/v4_meta_runner.py` |
| What governs current per-vector promotion? | `src/ztare/validator/gaming_vector_meta_runner.py`; its default board queue is generated from the live registry |
| Is the materialized hardening board current? | Run `make gaming-vector-hardening-check-plan`; it compares the board projection with registry-open rows. |
| What is the current promotion queue? | Run `make gaming-vector-hardening-show`; an empty queue means no currently-open autoresearch rows, not that the registry is empty. |
| How are new autoresearch vectors intentionally searched for? | `research_areas/seams/gaming/GP-058_bug_bounty_factory_integration_seam.md`, `rubrics/honeypot_minimal.json`, `docs/reference/make_targets.md` |
| How do standard (`factory`) and honeypot modes run? | `docs/reference/make_targets.md`, `src/ztare/validator/autoresearch_loop.py` |
| What is the historical [GP-086](../../research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md) rationale? | `research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md` |
| What seams track gaming-vector discovery and promotion? | `research_areas/seams/gaming/README.md`, `research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md` |
| What are reusable incident-derived templates? | `global_primitives/` |

Precedence when files disagree:

1. Registry JSONL for current vector status.
2. Runtime gate code for what is enforced.
3. Promotion evidence JSON for why a status flipped.
4. `gaming_vector_hardening_board/meta_runner_plan.json` for the current promotion queue only; it is a generated projection over open registry rows.
5. Public catalog for explanation.
6. [GP-086](../../research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md) seam/spec and V4 board files for provenance.
7. `global_primitives/` for reusable patterns, not live status.

## Current Coverage Snapshot

This checkout currently has 17 registry rows: 11 autoresearch rows and 6 LeanMill/proof-kernel rows. All 17 are marked `gated`, so the generated gaming-vector hardening board has an empty queue. Verify that instead of trusting this prose:

```bash
make gaming-vector-hardening-check-plan
make gaming-vector-hardening-show
```

If either command reports drift, refresh the materialized queue with:

```bash
make gaming-vector-hardening-sync-plan
```

Do not edit the materialized board to change status. The registry row plus promotion evidence owns status; the board is only the operator-facing queue for still-open rows.

## Layer Ownership

| Layer | Purpose | Canonical files |
|---|---|---|
| Public incident catalog | Explains named behaviors and audit patterns. | `docs/cheating_catalog.md` |
| Live vector registry | One row per vector; owns `open` / `gated` / `wontfix`. | `analytics/public/queries/gaming_vector_catalog.jsonl` |
| Discovery modes | Standard (`factory`) mode is tight evaluation; honeypot/bounty is red-team search for missed vectors. | `research_areas/seams/gaming/GP-058_bug_bounty_factory_integration_seam.md`, `rubrics/honeypot_minimal.json`, `docs/reference/make_targets.md` |
| Mining/checkpoint | Finds candidate vectors and avoids re-mining unchanged artifacts. | `src/ztare/common/kernel_hardener.py`, `analytics/public/queries/gaming_mine_manifest.jsonl` |
| Substrate miners | Convert artifacts into candidate `GamingVector`s. | `src/ztare/validator/autoresearch_hardener.py`, `src/ztare/leanmill/solver/leanmill_hardener.py`, `src/ztare/validator/sandbox_gaming_extractor.py` |
| Promotion governance | Validates that a fix blocks a named vector before registry status changes. The default board queue is a generated view of registry-open autoresearch rows. | `src/ztare/validator/gaming_vector_meta_runner.py`, promotion evidence JSON |
| Historical hardening board | Governed staged V4 evaluator-hardening projects. | `src/ztare/validator/v4_meta_runner.py`, `projects/epistemic_engine_v4/*benchmark_evidence.json` |
| Runtime enforcement | Gates that affect future autoresearch / leanmill runs. | `src/ztare/gates/global_gates.py`, `src/ztare/gates/autoresearch_gaming_gates.py`, `src/ztare/gates/semantic_gaming_carrier.py`, leanmill organs |
| Reusable precedents | Attack/failure/test templates derived from incidents. | `global_primitives/` |

## File Contract

| File or surface | Input | Output | Owner role |
|---|---|---|---|
| `docs/cheating_catalog.md` | Stable, human-readable behavior classes and public audit patterns | Explanations, examples, and citations | Public explanation only; no live status authority |
| `analytics/public/queries/gaming_vector_catalog.jsonl` | Accepted mined vectors | One row per vector with status, lineage, substrate, current gate/proposed action | Live status authority |
| `analytics/public/queries/gaming_vector_promotion_evidence/*.json` | Promotion receipt for one open vector | Evidence that the fix blocks the vector and passes controls | Status-change evidence |
| `analytics/public/queries/gaming_vector_hardening_board/meta_runner_plan.json` | Generated from registry-open autoresearch rows | Operator queue for pending promotion contracts | Projection only |
| `analytics/public/queries/gaming_mine_manifest.jsonl` | Artifact path, content hash, miner version | Incremental mining checkpoint | Mining cache; not status |
| `src/ztare/common/kernel_hardener.py` | Substrate hardener implementation | Shared mine-record-reproduce-promote contract | Cross-substrate interface |
| `src/ztare/validator/autoresearch_hardener.py` | Debate logs, code fixtures, project artifacts | Autoresearch `GamingVector` candidates | Autoresearch miner |
| `src/ztare/gates/autoresearch_gaming_gates.py` | `test_model.py` AST/source | Deterministic global-gate results for syntactic vectors | Autoresearch runtime enforcement |
| `src/ztare/gates/semantic_gaming_carrier.py` | Thesis/evidence/test-model text | Deterministic carrier selection for semantic review | Autoresearch runtime enforcement |
| LeanMill hardener/gates | Lean proof-context artifacts | LeanMill/proof-kernel gaming vectors and runtime checks | LeanMill runtime enforcement |

## SOP

1. **Discover a candidate vector.** Source may be honeypot/bounty output, sandbox debate logs, closure certificates, or a targeted audit. If it is only an idea, keep it out of the live registry until there is an exposing artifact or accepted review record.
2. **Mine or record the candidate.** Use the substrate hardener (`AutoresearchHardener` for autoresearch, the LeanMill hardener for proof-context vectors) so the row has a `GamingVector` shape. Mining may be neural, lexical, or manual-review assisted; the promoted gate must still be deterministic or receipt-backed.
3. **Add or update the registry row.** The row in `gaming_vector_catalog.jsonl` owns `status`, `already_gated_by`, `proposed_gate`, `substrate`, and lineage fields. Do not encode live status in the public catalog prose.
4. **Refresh/check the promotion queue.** Run `make gaming-vector-hardening-sync-plan` after adding open autoresearch rows, then `make gaming-vector-hardening-check-plan`. The board should be treated as generated output over open rows.
5. **Implement enforcement.** Add the narrow deterministic gate, config fix, or semantic carrier. Runtime opt-outs must be auditable: a disable flag needs a non-empty reason and must leave a visible gate payload.
6. **Write promotion evidence.** Add `gaming_vector_promotion_evidence/<vector>.json` with exposing artifacts, hashes, runtime-enforcement fields, regression controls, scoped vector-only claim, test result, and promotion recommendation.
7. **Run the promotion contract.** Use `make gaming-vector-hardening-run-vector VECTOR=<name> [SUBSTRATE=autoresearch]`. A PASS permits an explicit registry status change; it does not edit the registry for you.
8. **Verify the surfaces.** Run the targeted gate tests, `make gaming-vector-hardening-check-plan`, and docs checks if any public docs changed.
9. **Update public explanation only when needed.** Add or edit `docs/cheating_catalog.md` only when the vector introduces a stable behavior class or public-facing explanation. Link back to this SOP for operational mechanics.

## Discovery Modes

Autoresearch has two relevant run modes:

| Mode | Purpose | Surfaces |
|---|---|---|
| `factory` | Standard evaluator path: tight rubric, pre-run preparation, short iteration budget, synthesis output. | `docs/reference/make_targets.md`, `src/ztare/validator/autoresearch_loop.py` |
| `honeypot` | Bug-bounty path: loose rubric, no pre-run, long budget, debate log as the output. It is meant to reveal missed evaluator failures. | `docs/reference/make_targets.md`, `rubrics/honeypot_minimal.json`, `research_areas/seams/gaming/GP-058_bug_bounty_factory_integration_seam.md` |

The bounty lifecycle is:

```text
standard-run champion
  -> honeypot red-team on the same charter
  -> bounty report naming the exploit and missing gate
  -> operator accept/reject
  -> accepted candidate enters the vector registry
  -> promotion receipt
  -> runtime gate or config fix
```

[GP-058](../../research_areas/seams/gaming/GP-058_bug_bounty_factory_integration_seam.md) owns this discovery bridge. Honeypot output is a candidate source, not a gate spec and not an automatic promotion. The registry and promotion receipt still decide whether the candidate becomes live enforcement.

## Related Seams

| Seam | Role in this map |
|---|---|
| `research_areas/seams/gaming/GP-058_bug_bounty_factory_integration_seam.md` | Standard/honeypot bug-bounty discovery loop for new autoresearch vectors. |
| `research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md` | Promotion path from gaming pattern to cage/kernel gate lineage. |
| `research_areas/seams/gaming/README.md` | Index of gaming seams. |

## Runtime Enforcement Snapshot

| Vector class | Enforced by |
|---|---|
| [GP-086](../../research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md) recurring autoresearch signals | `global_gates.py`: `global_evidence_fit`, `global_uniqueness_gap`, `global_parsimony_violation`, `global_extrapolation_gap` |
| Autoresearch deterministic vectors | `autoresearch_gaming_gates.py`: structural-param smuggling, self-confirming metric, fabricated calibration, assumption-as-evidence |
| Audit-partition config vector | `holdout_audit.py` + `autoresearch_loop.py`: per-run audit partition salt with post-run replay material |
| Semantic scope/rigor vectors | `semantic_gaming_carrier.py`: scope overclaim, abstraction-transfer laundering, selective-rigor displacement |
| LeanMill proof-context vectors | `statement_integrity`, `canonical_reelaboration`, `leanmill_hardener.py` |

The semantic carrier is not a string-only proof of semantic failure. It is a deterministic router that fails closed when the artifact matches a scope/transfer/rigor risk and requires the appropriate review carrier.

Autoresearch runtime opt-outs are deliberately auditable. `disable_autoresearch_gaming_gates` and `disable_semantic_gaming_carrier` require a non-empty companion reason field; a reasonless disable hard-fails. A reasoned disable still appears in the global-gate payload as `actual="disabled"` so later audits can distinguish "no vector found" from "operator disabled this gate for a declared reason."

## V4 Board Versus Gaming Registry

The old V4 hardening board and the current gaming-vector registry are related but distinct.

| Mechanism | Unit | Role |
|---|---|---|
| `v4_meta_runner.py` | staged hardening project | Freezes candidate artifacts, checks typed contracts, runs fixture regressions, validates benchmark evidence, then marks a stage pass/fail/blocked. |
| `gaming_vector_meta_runner.py` | individual gaming vector | Generates the default queue from registry-open rows, checks a promotion receipt for one vector, then permits a registry status flip. |
| `gaming_vector_catalog.jsonl` | vector row | Records current status and lineage. |
| runtime gate code | executable enforcement | Catches future projects/runs. |

`analytics/public/queries/gaming_vector_hardening_board/meta_runner_plan.json` is a materialized view for operator readability. It is not authority. Regenerate it with:

```bash
make gaming-vector-hardening-sync-plan
```

Check projection drift with:

```bash
make gaming-vector-hardening-check-plan
```

Current V4 board status: `projects/epistemic_engine_v4/meta_runner_state.json` marks the original six stages complete. The project-local plan includes a queued stage 7, `adaptive_threshold_gaming_prevention`, but that stage is not part of `v4_meta_runner.py`'s default queue yet.

## Initial Hardening-Board Path

The initial V4 board stages were promoted through staged contracts, not direct vector rows. The shape was:

```text
candidate hardening thesis / test model
  -> frozen stage artifact
  -> fixture regression
  -> benchmark evidence JSON
  -> v4_meta_runner PASS
  -> runtime code/rubric already present
```

That is the same governance discipline now used for vectors, but the unit changed from "V4 stage" to "one catalog row."

The original nine public cheat patterns were also separate from the V4 board. They are field-documented numeric self-certification strategies and primitive precedents. [GP-086](../../research_areas/seams/apparatus/cage/GP-086_cage_kernel_hardening_seam.md) mined recurring debate-log signals from that broader evidence base and promoted a smaller set into runtime enforcement. The older route was:

```text
catalog incidents
  -> mine recurring signal
  -> choose CAGE / KERNEL / RUBRIC channel
  -> wire code or rubric
  -> validate with hardening-board-style contract
```

## MECE Frame

The registry rows are engineering units, not a perfect ontology. They are not MECE. Use three axes:

| Axis | Values |
|---|---|
| Substrate | `autoresearch`, `leanmill`, future substrates |
| Gamed surface | statement/context, evidence/data, metric/test, scope/transfer, complexity/accounting, rigor allocation |
| Enforcement channel | deterministic gate, config fix, semantic carrier, primitive precedent, documentation-only |

Current mechanism classes:

| Class | Registry rows |
|---|---|
| Proof-context integrity | `proof_instance_shadowing`, `decidable_fintype_instance_shadow`, `subsingleton_proofirrel_collapse`, `abbrev_def_shadows_mathlib_name`, `added_axiom_dependence`, `open_scoped_instance_hijack` |
| Declared-complexity/accounting | `structural_param_smuggle_body`, `parsimony_violation`, `uniqueness_gap`, `extrapolation_gap` |
| Evidence/provenance | `fabricated_calibration_set_threshold_laundering`, `assumption_as_evidence_relabeling`, `audit_partition_seed_fingerprint` |
| Metric/test self-confirmation | `definitional_tautology_self_confirming_metric` |
| Scope/transfer | `scope_overclaim_local_to_systemic`, `abstraction_stripping_invariance_laundering` |
| Rigor allocation | `selective_rigor_displacement` |

Known overlaps:

- Lean `category_type_smuggle` and `semantic_degeneracy` both sit under proof-context integrity.
- `scope_overclaim_local_to_systemic` and `abstraction_stripping_invariance_laundering` both sit under scope/transfer.
- `fabricated_calibration_set_threshold_laundering` is related to the original Gravity Constant cheat, but the constant is laundered through a calibration procedure.
- `audit_partition_seed_fingerprint` is a config/process vulnerability, not a Cage gate; it is closed by per-run audit-partition salting.

Implication: do not count the 17 rows as 17 mutually exclusive scientific kinds. Count them as 17 registry
rows with lineage and enforcement status.

## Current Next Step

No catalog rows are currently open. The next hardening work should enter through a new bounty/honeypot report, re-mine result, or recovered incident artifact, then get a registry row before promotion.

Promotion receipt requirements:

1. The exposing fixture or artifact is named.
2. The deterministic detector, config fix, or semantic carrier is named.
3. The fix blocks the exposing artifact.
4. Existing gated controls still pass.
5. The evidence surface is scoped, so one vector cannot claim another vector's fix.

## Non-Exhaustiveness

The catalog is lower-bounded. It records observed or mined vectors with lineage and current gate status. It is not a proof that every gaming route has been named.
