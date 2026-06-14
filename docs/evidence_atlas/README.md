---
description: "Reviewer-facing atlas that links public ZTARE claims, patterns, primitives, experiments, and runnable checks."
---
# ZTARE Evidence Atlas

> **Up:** [Documentation map](../README.md)

## Purpose

This atlas is the reviewer-facing layer over the existing evidence system. It
does not create new claims. It links the public claim register, project claim
summaries, pattern catalogs, reflexive primitives, experiments, scripts, and
known caveats into one traversable surface.

The problem it solves is simple: the repository already has evidence, but a
cold reader has to know where to look. The atlas makes the evidence graph
inspectable without asking the reader to absorb the whole apparatus first.

## Evidence Levels

Use these levels when reading any atlas card.

| Level | Name | Meaning |
|---|---|---|
| L0 | Named | The construct is named in docs or a registry, but evidence is not yet linked here. |
| L1 | Implemented | Code, script, Lean file, or durable artifact exists. |
| L2 | Experiment-linked | At least one project, experiment row, claim summary, or stored result links to it. |
| L3 | Decision-changing | The evidence changed a public claim, next action, demotion, or routing decision. |
| L4 | Controlled or ablated | A baseline, ablation, matched negative control, or benchmark comparison exists. |
| L5 | Externally checked | Independent second-lab replication, external adoption, upstream PR, peer-reviewed acceptance, or outside expert validation exists. |

Most of ZTARE's strongest current claims sit in L2-L4. L5 is intentionally
rare. Do not silently round L2-L4 into external validation.

These are atlas evidence levels. They are also defined in the
[glossary](../concepts/glossary.md#evidence-level-l0-l5). Do not confuse them
with LeanMill proof-audit L1/L2/L3 layers, which are local proof-checking
layers rather than general evidence levels.

## Reading The Evidence Through Five Questions

The public introduction uses five release questions. The atlas is where those
questions should be grounded. Read each answer through the source packets and
claim register, not through general repo scale.

| Question | Current public evidence | What is still missing |
|---|---|---|
| Can a bounded loop produce measurable research improvement under a hardened evaluator? | Claim-specific. Evaluator-hardening and self-certification failures have L4 controlled benchmark evidence; scientific and methodology campaigns have project summaries, retest tags, demotions, and packetized evidence where available. | No blanket system-level benchmark claim. Stronger external-facing work is a small number of frozen packet suites or benchmarks tied to specific claims. |
| Does the kernel make fake progress visible before it becomes a claim? | Strong public route: cheating catalog, evaluator-hardening packet, anti-laundering catches, public claim governance, demotion history, and non-claim fields. | Larger frozen comparison suites that separate ordinary review, rubric-only review, deterministic gates, and precedent/gate combinations. |
| Does research state survive across in-loop runs and out-of-loop agent work? | Partial public route: public claim register, experiment track record, action/forecast surfaces, primitive matrix, reflexive primitives, and operations-intelligence artifacts. | More packetized evidence that state reuse changes later routing or outcomes, not only that state is stored. |
| Can API calls, subscription agents, and local workers share the same typed artifact contract? | Implemented and testable in the kernel surfaces, with dispatch and subscription outcome audits. Treat this as implementation evidence unless a run packet links it to outcomes. | More matched API/subscription runs on substantive substrates before making transport-quality claims. |
| Can an outside reader reproduce the evidence path from command to artifact to gate? | Evidence packets, executable review pack, public claim register, benchmark evidence, and packet checker provide a review path for selected claims. | Uniform machine-readable claim packets and validators across all public claims. |

## Files

- [Claim Cards](claim_cards.md): curated high-signal claims and where the
  evidence lives.
- [Primitive Evidence Matrix](primitive_evidence_matrix.md): agentic patterns,
  anti-patterns, and reflexive primitives, with implementation and evidence
  status.
- [Packet Coverage](packet_coverage.md): what is already packetized, what is
  only partially packetized, and which external-facing experiment packets are
  still missing.
- [Evidence Packets](packets/README.md): concrete reviewer-facing packets
  assembled from existing public artifacts.
- [Executable Review Pack](executable_review_pack.md): commands a skeptical
  reader can run first, plus the current caveats observed in this checkout.

## Relation To Existing Ledgers

The atlas is an index and synthesis layer. The source layers remain:

- [Public claim register](../public_claim_register.md)
- [Experiment track record](../../research_areas/EXPERIMENT_TRACK_RECORD.md)
- Per-project `projects/*/public/CLAIM_SUMMARY.md`
- [Pattern catalog](../../org/patterns/INDEX.md)
- [Anti-pattern catalog](../../org/anti-patterns/INDEX.md)
- [Reflexive primitive registry](../../src/ztare/reflexive_primitives/INDEX.md)
- [Benchmark evidence](../../benchmarks/benchmark_evidence.md)
- [Papers index](../../papers/README.md)

If this atlas disagrees with a source layer, treat the source layer as
authoritative and patch the atlas.

## Non-Claims

This atlas does not claim:

- that every project under `projects/` is public-claim-ready;
- that every pattern or primitive has ablation evidence;
- that internal verdicts equal external replication;
- that ZTARE is a leaderboard-leading theorem prover, autonomous scientist, or
  general discovery engine;
- that a large evidence graph is the same thing as a small externally validated
  result.

The correct public posture is: ZTARE has a large evidence-linked apparatus for
falsification-native AI research, with explicit confidence levels, non-claims,
and demotion history across claims, patterns, primitives, and project
experiments.

<!-- AUTO-INDEX:START (auto-generated; edit prose OUTSIDE this block) -->

## Index

**Sub-folders**

- [`packets/`](packets/) - 6 file(s)

**Documents**

- [Claim Cards](claim_cards.md) - Curated claim cards linking ZTARE public claims to evidence sources, commands, non-claims, and next falsifiers.
- [Executable Review Pack](executable_review_pack.md) - Small command set for reviewing ZTARE evidence without traversing the whole repository.
- [Packet Coverage](packet_coverage.md) - Coverage map for ZTARE evidence packets: what exists, what is partial, and which experiment packets are still missing.
- [Primitive Evidence Matrix](primitive_evidence_matrix.md) - Evidence matrix for ZTARE agentic engineering patterns, anti-patterns, and reflexive primitives.

<sub>1 sub-folder(s), 4 document(s). Auto-generated; re-run `gen_folder_index.py` after adding files.</sub>
<!-- AUTO-INDEX:END -->
