---
description: "Evidence packet for ZTARE evaluator hardening and self-certification failure claims."
---
# Evaluator Hardening Packet

> **Up:** [Evidence Packets](README.md)

## Scoped Claim

ZTARE has public, bounded evidence that deterministic gates and mined
adversarial precedent reduce self-certifying evaluator failures on the tested
benchmark families.

## Evidence Level

L4: controlled or ablated evidence on bounded public benchmark families.

## Primary Sources

- [Benchmark evidence](../../../benchmarks/benchmark_evidence.md)
- [Constraint-memory benchmark](../../../benchmarks/constraint_memory/README.md)
- [Constraint-memory metrics summary](../../../benchmarks/constraint_memory/runs/20260404_195100/metrics_summary.json)
- [Cheating catalog](../../cheating_catalog.md)
- [Cognitive Camouflage draft](../../../papers/cognitive-camouflage/draft.md)
- [Adversarial Precedent Memory draft](../../../papers/adversarial-precedent-memory/draft.md)

## Runnable Anchors

```bash
make benchmark-evidence
make demo
```

## Evidence Summary

The constraint-memory benchmark compares rubric-only review, deterministic
gates, and gates plus primitives. The representative public run shows
deterministic gates removing false accepts in that suite, while gates plus
primitives recover good controls that deterministic gates alone over-reject.

The model-free demo and case studies show small self-certification and
evaluation-design failures where a plausible pass is not enough. The value of
the packet is false-positive discipline, not broad discovery performance.

## Non-Claims

- Not a global SOTA claim.
- Not evidence that ZTARE beats all symbolic-regression or proof systems.
- Not evidence that the current full research-operations stack is benchmarked
  end to end.
- Not evidence that gates alone are sufficient for scientific discovery.

## Missing Upgrade

A stronger packet would freeze a public claim-packet benchmark with separate
conditions:

- ordinary LLM review;
- rubric-only review;
- deterministic gates;
- deterministic gates plus mined precedent.

That benchmark belongs under `benchmarks/` because it would be a reusable
cross-claim evaluation suite rather than a single project campaign.

