---
seam_id: layer3-evaluation-2026-05-06
status: closed
discovered: 2026-05-06
closed: 2026-05-06
owner: PM-of-ZTARE
relates_to: [#173, GP-216 v5 ops, GP-220 reflexive ROI audit]
resolution: no-new-primitives-today
---

# Layer 3 Self-Improvement — 2026-05-06 Evaluation

> **Seam metadata** · `seam_id:` layer3_evaluation_2026_05_06 · `track:` reflexive · `status:` closed · `last_updated:` 2026-05-09


## TL;DR

Today's Layer 3 closure-pattern miner output **does NOT support shipping
new primitive gates**. The apparent primitive candidates
(`broad_inversion`, `core_03_decomposition`, `core_04_local_to_global`)
were artifacts of LLM over-tagging of uncategorized governance/
architecture axioms in Lane B (verified-axiom corpus), not real Layer
3 signal about gaps in the cage.

The investigation produced two real outputs:

  1. A **lane-separated verdict logic** in `mine_closure_patterns.py`
     that requires ≥1 Lane A (F-row) attestation before declaring a
     `primitive_candidate`. Without it, Lane B governance noise
     drowned out the real Layer A research-closure signal.
  2. A **calibration finding**: the LLM tagger over-applies on
     governance prose. Use the `axiom_only_candidate` verdict to
     surface low-confidence candidates instead of ignoring them.

## What I expected vs. what happened

**Expected:** Layer 3 mining would surface 1-3 high-confidence
primitive candidates that recur across multiple substrate classes
without existing cage coverage. Author Gate(name=...) wrappers for
each.

**Found:** Lane A (F-row closures from real research) has only **9
events total** across the entire corpus (8 verified + 1
falsified_with_finding) — too few to triangulate primitive candidates.
Lane B (verified-axiom corpus, 2,606 records, 1,605 LLM-tagged) has
much higher counts but is dominated by 1,291 uncategorized governance
axioms whose meta-operations the LLM over-matched on surface
keywords.

## Concrete examples of LLM over-tagging

Sampled axioms tagged with `broad_inversion`:
  - "No infallible aggregator or absolute veto node inside the proof"
    → tagged broad_inversion + broad_falsification. Reading: this is
    a NEGATIVE EXISTENCE claim about governance, not an inversion /
    contrapositive / adjoint operation.
  - "Exogenous memory must remain outside the validator kernel" →
    tagged broad_inversion + core_03_decomposition. Reading: this is
    a separation/boundary architectural principle, not an
    inversion or decomposition meta-operation.

Sampled axioms tagged with `core_03_decomposition`:
  - "Architectural proofs must use minimal simulation complexity" →
    tagged broad_compression + core_03_decomposition. Reading: this
    is a complexity-bound principle, no decomposition is happening.

The LLM is surface-matching keywords ("must use", "no X") against op
definitions when no real meta-operation is present. This is a
prompt-engineering issue, not a fundamental flaw in the approach.

## Verdict-by-verdict status

| v5 op | Verdict | F-row | Axiom | Reading |
|---|---|---:|---:|---|
| `core_03_decomposition` | `primitive_candidate` | 1 | 246 | Borderline. 1 F-row attestation is weak; treat as a watch-item, not a build-item. |
| `broad_inversion` | `axiom_only_candidate` | 0 | 238 | LLM noise. Spot-check axioms before treating as real. |
| `core_04_local_to_global` | `axiom_only_candidate` | 0 | 9 | Same caveat. |
| `subfield_residual_chasing` | `covered_load_bearing` | 3 | 46 | Real signal — already covered by per_class_farther_tail. |
| All other ops | various | 0-1 | various | Either covered or below threshold. |

Only **`subfield_residual_chasing`** has meaningful Lane A signal (3
F-row closures), and that op is already covered. No new gate to
build.

## What stays valuable

  - **LLM enrichment script** (`scripts/public/mining/llm_enrich_v5_op_tags.py`):
    works, persists, idempotent. Will be decisive later when:
      - F-row count grows large enough that Lane A becomes
        statistically meaningful on its own (~50+ closures per op)
      - The substrate-class derivation classifies projects more
        granularly so Lane B isn't dominated by "uncategorized"
      - The LLM prompt is tightened to refuse-to-tag governance prose

  - **Lane-separated verdict logic** in `mine_closure_patterns.py`:
    correctly distinguishes high-confidence (Lane A attested) from
    low-confidence (axiom-only) candidates. Carries forward.

  - **The meta-finding itself**: Layer 3 self-improvement requires a
    minimum density of REAL closures in the F-row corpus. Today's
    density is 9 closures across 404 F-rows = 2.2%. Need to raise
    the closure rate (more iters running to closure) before Layer 3
    becomes decisive.

## What I'm NOT shipping

  - No new Gate authoring for broad_inversion (insufficient real
    signal)
  - No new Gate authoring for core_03_decomposition (1 F-row
    attestation is too weak)
  - No mutator-side "tactic palette" addition (same)

## Follow-up

If F-row closure rate grows to ≥50 events per op for any
axiom_only_candidate op, re-evaluate. Until then, today's verdict
holds: cage covers what's needed, gaps are noise.
