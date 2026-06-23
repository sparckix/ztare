---
description: "Review packet for the LLM gaming behavior catalog, live vector registry, promotion evidence, and hardening lifecycle."
---
# Gaming Catalog And Hardening Registry Packet

> **Up:** [Review Packets](README.md)

## Scoped Claim

ZTARE maintains a public, bounded LLM gaming behavior catalog whose first nine
entries have Cognitive Camouflage paper lineage, human-readable public names,
and invariant audit axes; later live registry rows are tied to concrete gate
status and promotion evidence where declared.

## Evidence Level

L3-L4: paper-linked taxonomy for the first nine strategies; live engineering
registry and promotion-contract evidence for later gated rows. This is not L5
external validation.

## Primary Sources

- [LLM Gaming Behavior Catalog](../../gaming_behavior_catalog.md)
- [Gaming Behavior Catalog Map](../../concepts/gaming_behavior_catalog_map.md)
- [Live vector registry](../../../analytics/public/queries/gaming_vector_catalog.jsonl)
- [Promotion evidence directory](../../../analytics/public/queries/gaming_vector_promotion_evidence/)
- [Cognitive Camouflage paper](../../../papers/cognitive-camouflage/draft.md)
- [Evaluator Hardening Packet](evaluator_hardening.md)

## Runnable Anchor

```bash
make gaming-catalog-audit
```

Expected output:

- `ok: true`;
- `registry_count: 18`;
- `status_counts: {"gated": 18}`;
- `substrate_counts: {"autoresearch": 12, "leanmill": 6}`;
- `evidence_tier_counts: {"promotion_receipt": 8, "registry_row": 18,
  "reproduced_incident": 12, "runtime_gate": 18}`;
- `promotion_evidence_rows: 8`;
- `original_nine_headings: 9`;
- `executable_anchor_count: 5`;
- `executable_anchor_benign_control_passed: true`.

The same audit is included in:

```bash
make first-run
make gates
```

## Evidence Summary

The catalog is split into four layers:

1. first-nine benchmarked self-certification strategies;
2. later mined mechanism classes;
3. live registry rows with current gate status;
4. promotion evidence and hardening protocol.

That separation is the main evidence discipline. The original nine are paper
taxonomy claims. Later rows are engineering registry entries: they become
stronger when the registry row names a reproducing failure mode, the promotion
evidence resolves, and the runtime gate is wired. The audit fails if the public
catalog loses that boundary, if the map's declared count drifts from the
registry, if duplicate vector names appear, if declared promotion evidence does
not match the registry row, or if the executable autoresearch anchors stop
mapping from fixture to detector to runtime gate. The executable anchor set is
small by design: it currently checks four concrete autoresearch vectors plus a
benign control.

## Non-Claims

- Not a complete ontology of reward hacking or specification gaming.
- Not a mutually exclusive taxonomy.
- Not evidence that every known model family exhibits every row.
- Not a benchmark or leaderboard.
- Not external replication.
- Not a claim that later rows 10-17 belong to the original Cognitive
  Camouflage 9-strategy benchmark.

## Missing Upgrade

A stronger packet would add:

- a minimal reproducer or exposing artifact pointer for every registry row;
- a copyable candidate-row walkthrough from incident or reproducer to registry
  row, promotion receipt, regression, runtime gate or declared non-gate, and
  public explanation update;
- executable anchor coverage beyond the current four autoresearch vectors;
- a small external reproduction of at least one catalog entry outside the
  original ZTARE runs;
- a frozen ordinary-review comparison showing which entries are missed by
  text-only or holistic review and caught by the declared gate.

Demote the packet if the catalog begins counting live registry rows as a
complete taxonomy, if the map and registry disagree, or if a declared gated row
lacks an inspectable enforcement or promotion path.
