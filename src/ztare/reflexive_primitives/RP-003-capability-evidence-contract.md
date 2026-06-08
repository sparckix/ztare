---
id: RP-003
name: capability_evidence_contract
version: 1
status: active
leg_applied: "Invert + Adversarial Disagreement"
target: "The apparatus's own choice of which new internal capability to build next"
verdict: "B (PARTIALLY NOVEL)"
literature_scout: "novel SHAPE (a carrier-bound capability preflight contract bound to a FROZEN yield-decomposition snapshot); cite-and-adopt components: Theory of Constraints / bottleneck-gating (Goldratt 1984), pre-registration / evidence-contract discipline, and the in-repo master-discriminator (exogenous-carrier-or-nothing)."
dependencies:
  - research_areas/seams/apparatus/instrumentation/GP-247_capability_evidence_contract_seam.md
  - research_areas/seams/apparatus/instrumentation/GP-233_research_yield_decomposition_seam.md
  - research_areas/seams/engine/lean/GP-246_governed_dag_proof_search_seam.md
  - research_areas/seams/apparatus/instrumentation/GP-244_research_operations_intelligence_cockpit_seam.md
falsifier:
  test: "Of the next K>=5 capability bets posted as CEC contracts: (a) any capability adopted whose declared exogenous_carrier is later shown to be proposer-chooseable (i.e. the proposer could select its own evidence distribution), OR (b) the contract fields (exogenous-carrier present, bottleneck pinned to a frozen snapshot) do NOT separate adopted-and-validated bets from abandoned ones better than the proposer's pre-stated p_success. Either ⇒ CEC is ceremony, demote."
  monitoring_artifact: "analytics/public/ledgers/capability_evidence_contracts/ (one row per posted CEC bet + its resolution)"
  period: "2026-05-31 .. 2026-08-31"
anti_laundering_commitments:
  - "Emit NO scalar capability-priority score until >=N resolved bets show the contract fields predict realized capability yield. Until then it is a review table, not a ranker."
  - "CA (constraint alignment) must resolve against a FROZEN yield-decomposition snapshot hash + a declared causal path; a live re-estimate or soft 0.6 is rejected (CA-gaming is the documented highest-leverage failure)."
  - "If a plain review table without the contract scaffold chooses capabilities as well, demote this entry."
  - "Provenance: the predecessor scalar formula (CEP) was killed by a cold cross-provider pre-flight as a sophistication ladder; do not silently reintroduce a scalar score."
---

# RP-003 — Capability Evidence Contract

## What It Is

A carrier-bound preflight contract for deciding which new internal capability
the apparatus should build next. A capability is **rankable only if** it posts:
a bottleneck stage **pinned to a frozen yield-decomposition snapshot**
(GP-233 lanes / GP-246 lean-closure) with a declared causal path; an
**exogenous evidence carrier** (kernel / hidden test / downstream decision the
proposer cannot narrate around); a kill criterion; the downstream decision it
would change; a cost ceiling; and a reuse surface. No qualifying carrier ⇒ not
rankable.

## Why This Is Reflexive

It uses the architecture's own yield-decomposition (its self-measurement of
where it is bottlenecked) as the central context for the architecture's own
decision about what to build. The engine prioritizes its own growth against its
own measured constraint.

## Provenance (anti-laundering)

The first design was a scalar ranker `CEP = (EIY × CA × TR)/(C × (1+GR))`. A
cold cross-provider adversarial pre-flight killed it: every factor is a
launderable judgment slot, the Goodhart-risk discount is itself Goodhartable,
and a multiplicative constraint-alignment term is the highest-leverage gaming
surface. The contract form is the salvage: carrier-bound, frozen-snapshot, no
scalar until calibrated. The kill is recorded so the scalar is not reintroduced.

## Self-reference verification

`grep CAPABILITY-EVIDENCE-CONTRACT analytics/public/index/architecture_index.jsonl`
returns this primitive's row; this entry documents a primitive that is in the
index it is registered in.
