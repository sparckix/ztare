---
description: "Coverage map for ZTARE review packets: what exists, what is partial, and which experiment packets are still missing."
---
# Packet Coverage

> **Up:** [Evidence Atlas](README.md)

This page answers a narrower question than the claim cards: do the public
claims have enough packet structure for an outside reviewer to inspect them
without reading the whole repo?

## Reviewer Verdict

The packet layer is usable for review, but not complete.

An outside reviewer can already inspect the main evidence routes: benchmark
evidence, public claim register, 38 project claim summaries, model-free demos,
public analytics receipts, papers, and selected workbench artifacts. The
strongest areas are ready to be read as evidence-linked claims, not as bare
repo volume.

The missing layer is uniformity. Some claims have excellent packets; some have
public summaries but no machine-checkable packet fields; some patterns are
named and implemented but do not yet have causal or ablation evidence. That is
acceptable for a research workbench, but it should stay explicit in any
external introduction.

## Packet Standard

An external-facing review packet should have:

1. a scoped claim;
2. evidence level and status tag;
3. primary source artifacts;
4. runnable or reproducible anchors when possible;
5. explicit non-claims;
6. next falsifier or external-validation step;
7. linkage to the public claim register or a project `public/CLAIM_SUMMARY.md`;
8. enough metadata for a cold reviewer to tell whether the packet is original,
   replicated, controlled, demoted, or externally checked.

The current repo has many artifacts and many public summaries. It does not yet
have every claim expressed as a uniform machine-readable packet.

Concrete packets assembled from existing public artifacts live under
[Review Packets](packets/README.md).

## Coverage Snapshot

| Area | Current packet status | What exists | Missing before "complete" |
|---|---|---|---|
| Evaluator hardening / self-certification failures | Strongest packetized area | Benchmark evidence, gaming behavior catalog, case studies, papers, `make hello`, `make demo`, `make benchmark-evidence` | Larger frozen claim-packet suite with ordinary LLM review, rubric-only review, deterministic gates, and gates-plus-precedent as separate conditions |
| Gaming catalog / hardening registry | Packetized with coherence audit | Public catalog, Cognitive Camouflage paper boundary, live 17-row registry, promotion evidence links, `make gaming-catalog-audit` | Row-level evidence tiers, minimal reproducers for every live vector, external reproduction, and a contribution protocol for candidate vectors |
| Public claim governance | Partially packetized with claim-card validation | Public claim register, 38 project `public/CLAIM_SUMMARY.md` files, experiment track record, claim-card required-field checks in `evidence_packet_check.py` | Machine-readable per-project/public-claim evidence rows beyond the curated claim cards |
| Scientific case studies / OEIS / sandbox recoveries | Many project-intake files, uneven external strength | Per-project summaries, register sections, benchmark evidence where applicable | Per-claim retest tags normalized across all summaries; external baseline packets for claims that currently rest on system-internal evidence |
| Navier-Stokes Track B | Rich residual packets, not closure packet | Public journey, public graph, Lean tree, residual manifest, PDE workbench packs | No theorem-closure packet. Needs target-axiom-specific packet with amnesia check, tool-depth receipt, formal/source receipt, and external mathematical review |
| Forecasting science / Law 1-3 | Public-packetized as a law-validation program, still system-internal | Public register section, project summary, methodology architecture, law validation matrix, findings-to-laws map, unifying law note, premium-channel report, channel-holdout report, cutoff Stage A audit, paper drafts, calibration commands | Law 1 anti-bias-collapse run, Law 2 prospective policy-cell validation or demotion, Law 3 matched pre/post cutoff corpus, external replication |
| LeanMill / formal audit | Governance/audit packet exists; performance packet incomplete | Architecture doc, APN public audit summary/receipts, F103 register entry, `lake build` | Public miniF2F or named-baseline benchmark; external proof artifact review; no public claim yet that planner memory improves natural Mathlib proof closure |
| Reflexive primitives | Seed packetized, not fully outcome-tested | Registry, primitive matrix, capability evidence contract ledger, self-report critic | At least five resolved capability-evidence-contract bets; synthetic controls for self-report critic; outcome tracking for pattern-action-contract closes |
| Autoresearch trace and state carrier | Technical reference only; not counted as a review packet | [Autoresearch state carrier reference](../reference/autoresearch_state_carrier.md), trace tests, hypothesis projection tests, real-project trace/projection smoke, action-intelligence link field | End-to-end fixed run producing route row, trace artifact, projection artifact, and action-impact row from one command before this becomes a review packet |
| Agentic engineering patterns | Catalogued, not uniformly packetized | Pattern catalog, anti-pattern catalog, implementation anchors, smoke tests | Per-pattern review packet: motivating failure, implementation artifact, validator/test, observed prevented failure, demotion criterion |
| Forecast pool / action intelligence | Mechanized smoke packet; calibration packet incomplete | Forecast pool implementation, action-intelligence smoke, analytics artifacts | Public calibration report with enough resolved contracts for per-agent calibration and decision-use lift estimates; keep separate from forecasting law-validation claims |
| Cross-domain methodology | Synthesis packet exists; external packet missing | Public claim register, multi-domain validation, experiment track record | Frozen cross-domain benchmark over claim artifacts with external baselines and independent labels |

## Direct Answer

The experiments are not all done in the packet sense.

What exists is substantial: public claim register, 38 project summaries,
benchmark evidence, smoke commands, case-study reproducers, public analytics
receipts, and many project/workbench artifacts. That is enough to support a
serious reviewer route.

What is missing is uniformity and externalization:

- not every claim has a machine-readable packet, though curated claim cards now
  have required-field validation;
- not every named primitive has causal or ablation evidence;
- several strong-looking areas are still system-internal;
- some links and paths still need normalization;
- external validation is sparse by design and should not be implied.

The next build step is not more prose volume. It is a packet validator plus a
small number of frozen, reviewer-runnable packet suites.

## Do We Need Additional Benchmarks Or Packets?

Yes, but selectively.

The repo does not need dozens of new benchmarks before it is legible. It needs
a small external-review set that converts the most important claims into
reviewer-runnable packets. The priority order should be:

| Priority | Packet or benchmark | Why it matters | Minimum useful version |
|---|---|---|---|
| P0 | Claim-card schema + validator | Prevents the atlas from becoming another prose index | Required fields, file-existence checks, evidence-level enum, non-claim and next-falsifier checks |
| P0 | Evaluator-hardening claim-packet benchmark | This is the most externally legible result, and it lacks a frozen comparison suite | Frozen suite comparing ordinary LLM review, rubric-only review, deterministic gates, and gates-plus-precedent |
| P0 | Gaming-catalog row evidence tiers | Turns the strongest public hook into a reusable field guide rather than a prose list | Per-row evidence tier, minimal reproducer pointer, gate owner, promotion receipt, and demotion condition |
| P1 | Agentic-pattern review packets | Gives reusable engineering patterns evidence another team can check, instead of catalog entries | Five packets for highest-transfer patterns, each with motivating failure, implementation, test, observed prevented failure, demotion criterion |
| P1 | Forecast calibration report | The forecasting/action-intelligence surface is strong but currently sprawling | Resolved contracts, per-agent calibration, decision-use rows, uncertainty intervals, contamination caveats |
| P1 | LeanMill public benchmark or proof-review packet | Prevents proof/governance claims from being confused with theorem-prover performance claims | One named-baseline benchmark or one externally reviewed proof artifact |
| P2 | NS residual-frontier packet | Makes the NS campaign inspectable without implying theorem closure | One named residual frontier with killed siblings, target axiom, tool-depth artifacts, Lean/source receipts, next mathematical falsifier |
| P2 | Cross-domain methodology benchmark | Tests the broadest methodology claim | Frozen claim artifacts, external baselines, independent labels, demotion/null outcomes |

Do not build benchmark volume for its own sake. A benchmark is worth adding
only when it changes an evidence level, discriminates a confuser, or makes a
claim inspectable by someone outside the repo.

Current runnable packet and claim-card check:

```bash
./venv/bin/python scripts/public/control/evidence_packet_check.py
```

It validates concrete packet files under `docs/evidence_atlas/packets/` for
required reviewer-facing sections, evidence-level values, and local link
existence. It also validates `docs/evidence_atlas/claim_cards.md` for the
minimum public fields: claim, evidence level, primary sources, runnable anchor,
non-claim, and next falsifier. It is included in `make benchmark-evidence`.

## Where New Work Belongs

Use the smallest durable surface that matches the work:

| Work type | Best home | Reason |
|---|---|---|
| Retrospective packaging of significant public evidence | `docs/evidence_atlas/packets/` | It is synthesis over existing public artifacts, not a new experiment; read-model references stay in `docs/reference/` until they support a public claim. |
| Campaign-specific new experiment | `projects/<campaign>/...` plus `projects/<campaign>/public/CLAIM_SUMMARY.md` | The current public pattern is project-first with a public summary surface. |
| Reusable cross-claim benchmark | `benchmarks/` | Use this only when the task is a frozen benchmark suite with reusable baselines and metrics. |
| Active or private pre-registration / sealed material | private or gitignored project workspace until closure | Public packets should not expose hidden GT, private sources, or active strategy. |
| Public claim status | `docs/public_claim_register.md` | This remains the canonical public claim-status surface. |

## Suggested Next Packets

1. **Public claim packet schema.** JSON or YAML beside each claim card with
   claim, evidence level, sources, commands, non-claims, next falsifier, and
   status.
2. **Per-project claim summary validator.** Extend the current claim-card
   validator to project `public/CLAIM_SUMMARY.md` files once their format is
   normalized enough to avoid false precision.
3. **Pattern review packets.** One packet per agentic engineering pattern,
   starting with the highest-transfer patterns: pre-flight assertion battery,
   fallback provenance telemetry, structural contract gating, forecast-pool
   control, and result-bound success claims.
4. **Forecast calibration packet.** One public calibration bundle with
   resolved contracts, per-agent calibration, decision-use rows, and caveats.
5. **LeanMill external packet.** Either a public benchmark packet or one
   externally reviewed proof artifact. Until then, keep performance claims
   scoped to governance/audit discipline.
6. **NS residual-frontier packet.** Pick one named residual frontier and
   package target axiom, killed siblings, tool-depth evidence, Lean/source
   receipt, and the next mathematical falsifier.
