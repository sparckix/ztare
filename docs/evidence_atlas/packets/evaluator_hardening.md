---
description: "Review packet for ZTARE evaluator hardening and self-certification failure claims."
---
# Evaluator Hardening Packet

> **Up:** [Review Packets](README.md)

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
- [Gaming behavior catalog](../../gaming_behavior_catalog.md)
- [Cognitive Camouflage draft](../../../papers/cognitive-camouflage/draft.md)
- [Adversarial Precedent Memory draft](../../../papers/adversarial-precedent-memory/draft.md)

## Runnable Anchors

```bash
make hello
make evaluator-hardening-frozen-check
make benchmark-evidence
make demo
```

Expected `make hello` output:

- ready project-intake file: accepted;
- malformed project-intake file: blocked before in-loop routing because
  `evidence_refs` is empty;
- verdict: `demote_to_bounded_wording`;
- `claim_allowed: False`;
- machine summary reports blocked source count, failed check count, and
  `writes_persistent_runtime_state: false`;
- next falsifier: a named external-baseline benchmark with a pre-registered
  metric and comparison population.

Expected `make evaluator-hardening-frozen-check` output:

- `ok: true`;
- `artifact_backed_arms: 3`;
- `complete_four_arm_suite: false`;
- baseline false accepts are nonzero;
- deterministic gates and gates plus primitives reduce false accepts to zero;
- gates plus primitives restore good controls;
- `D_ordinary_review` is listed as the required future arm before the packet can
  be upgraded to a completed four-arm comparison.
- `ordinary_review_status: blocked_not_run`;
- ordinary-review contract and blocker artifacts are named;
- ordinary-review prompt export is verified against the frozen source-run
  specimen set;
- ordinary-review import preflight is verified model-free on a synthetic
  prompt-bound row packet.

## Evidence Summary

The constraint-memory benchmark compares rubric-only review, deterministic
gates, and gates plus primitives. The representative public run shows
deterministic gates removing false accepts in that suite, while gates plus
primitives recover good controls that deterministic gates alone over-reject.

The hello demo shows two current first-run surfaces: project intake blocks a
malformed project boundary before in-loop routing, and claim discipline demotes
an overbroad public claim before it becomes release wording. The model-free
demo and case studies show small self-certification and evaluation-design
failures where a plausible pass is insufficient. The value of the review
packet is false-positive discipline, not broad discovery performance.

## Current Proof Point Boundary

This packet is the current public proof point for evaluator hardening and claim
demotion. The boundary is deliberately narrow: the runnable checks support a
bounded false-positive and claim-discipline claim, not a broad autonomous
research benchmark.

Current requirements:

- keep `make hello` as the first command in README, quickstart, and review
  pack;
- keep `make first-run` green over `make hello`, gaming-catalog audit,
  benchmark-evidence check, frozen evaluator-hardening check,
  claim-boundary audit, terminology audit, public smoke, and docs checks;
- keep the frozen evaluator-hardening check runnable over the three
  artifact-backed arms;
- publish expected outputs and demotion criteria beside benchmark results.

Upgrade criterion:

- upgrade only if the frozen comparison shows gates or gates-plus-precedent
  catching false accepts that the weaker arms admit, while preserving named
  good controls.
- run and freeze the missing ordinary-review arm before any four-arm upgrade.

## Non-Claims

- Not a global best-system claim.
- Not evidence that ZTARE beats all symbolic-regression or proof systems.
- Not evidence that the current full research-operations stack is benchmarked
  end to end.
- Not evidence that gates alone are sufficient for scientific discovery.

## Missing Upgrade

A stronger packet would complete the public claim-packet benchmark with
separate conditions:

- ordinary LLM review;
- rubric-only review;
- deterministic gates;
- deterministic gates plus mined precedent.

The current frozen suite lives at
[`benchmarks/evaluator_hardening_frozen/`](../../../benchmarks/evaluator_hardening_frozen/).
It verifies the three artifact-backed arms and keeps the ordinary-review arm as
an explicit upgrade gap. The predeclared ordinary-review contract is
[`ordinary_review_arm_contract.json`](../../../benchmarks/evaluator_hardening_frozen/ordinary_review_arm_contract.json).
The current blocker is
[`D_ordinary_review_blocker.json`](../../../benchmarks/evaluator_hardening_frozen/D_ordinary_review_blocker.json):
there is no frozen ordinary-review output for the source run. The benchmark
runner exposes `D_ordinary_review` as an opt-in condition and can import
externally supplied row-level review outputs. The ordinary-review command is
bound to the frozen source-run specimen set with `--match-source-run`, so later
additions to the broader benchmark suite do not silently change the comparison
population. Imported rows must carry model, timestamp, prompt, and
provider/runtime provenance; prompt provenance must bind to the exact
runner-generated prompt for that specimen. Relative prompt paths resolve from
the import JSON file directory first. The runner fails closed on missing rows,
missing provenance, or prompt-hash mismatch rather than mixing imported and live
review evidence. A model-free preflight command validates imported rows before a
benchmark run: `make benchmark-ordinary-review-validate-import
BENCH_ORDINARY_IMPORT=path/to/ordinary_review_rows.json`. When the arm runs, the
runner writes `ordinary_review_freeze_manifest.json` beside `results.json` and
`metrics_summary.json`; the packet does not upgrade until that manifest reports
`can_promote_to_frozen_suite: true` over the same specimen set. The promotion
preflight is `make benchmark-ordinary-review-freeze-check
BENCH_ORDINARY_RUN=benchmarks/constraint_memory/runs/<run_id>`.

Demote the packet if the frozen comparison suite does not separate
deterministic gates or gates-plus-precedent from weaker review arms, or if it
cannot preserve good controls while removing false accepts.
