---
description: "As-built lifecycle diagrams for the ARC-AGI-3 science loop, grammar reflex, and related control flows."
---

# Flows

This file records the as-built flow surfaces referenced by the ARC-AGI-3 system doc. Each diagram uses the current code names and the prose stays short so the lifecycle is easy to scan.

## 1. Science Turn Lifecycle

```mermaid
sequenceDiagram
    participant LC as live champion provider (tier 0)
    participant M as mutator leaf
    participant W as visible workbench tools
    participant C as carrier
    participant G as pre-judge deterministic gates
    participant B as compiler-bounce strikes
    participant E as structured exits
    participant R as R1 retry (visible_workbench)

    LC->>M: mandatory patch-base directive from champion_materialization.jsonl
    M->>W: inspect visible evidence and bounded probes
    W-->>M: receipts and query outputs
    M->>W: run evidence probe (DISCOVERY only, zero-credit)
    W-->>M: probe receipt
    M->>C: submit candidate carrier
    C->>G: observed-tier gates (must-pass) + heldout-tier gates (non-regression)
    G-->>M: dominance receipt (observed pass + strict improvement) or fail receipt
    G->>B: compiler-bounce on carrier or contract mismatch
    B-->>R: R1 retry in visible_workbench mode (instruments retained)
    R-->>M: kernel-derived declaration reattached
    B-->>M: strike receipt (science-content failures only)
    M->>E: candidate / investigated / lowerability-blocked / stuck
```

The science turn starts in the mutator leaf, uses only visible workbench affordances, and ends on one of the structured exits. The live-champion provider (tier 0, priority 18) renders the mandatory patch-base directive as the first directive the leaf sees. Deterministic gates own carrier admission and enforce tiered promotion: every observed-tier gate must pass absolutely, while heldout-tier gates require non-regression against the champion's recorded value. A turn may also close as `INVESTIGATED` — a credited first-class science outcome — when the leaf eliminates a new hypothesis class from visible evidence (K=3 stagnation bound before escalation pressure fires). Compiler-bounce is the early reject path when the surface is malformed or underspecified; R1 retries run in `visible_workbench` mode so instruments are retained. Envelope faults (`UNDECLARED_ARTIFACT_BREADTH`, `INVALID_PRIMITIVE_DECLARATION`) are kernel-normalized without consuming strikes.

## 2. Grammar Reflex

```mermaid
sequenceDiagram
    participant S as ceiling
    participant R as card
    participant L as sealed leaf
    participant H as harness
    participant A as adopt-or-checkpoint

    S->>R: emit operator proposal card
    R->>L: dispatch sealed leaf
    L->>H: propose planted synthetic + seeded improvement
    H-->>L: receipt or counterexample
    H->>A: adopt if strict improvement holds
    A-->>S: write-back or checkpoint
```

The reflex is a ceiling-to-card loop, not a free-form rewrite loop. A sealed leaf may plant a synthetic test and a seeded improvement, but the harness still disposes the candidate before any write-back.

## 3. Proposal Lifecycle

```mermaid
sequenceDiagram
    participant Z as zero-credit rider
    participant L as leaf_proposals ledger
    participant R as RefutedExperimentsLedger
    participant O as office batch
    participant D as dual-LLM committee
    participant P as disposition
    participant K as case-law digest
    participant F as future scratchpads

    Z->>L: append proposal row
    L->>R: check against killed failure families
    R-->>O: rejected_refuted receipt (machine-blocked families skip committee)
    L->>O: remaining rows, batched with dedup and free-kill
    O->>D: submit adjudication membrane
    D-->>D: sealed adjudicator leaf (primary verdict)
    D-->>D: sealed dissent leaf (adversarial counter)
    D-->>P: approve / reject / escalate-on-parse-failure
    P->>K: record case-law digest with effective_model_id attestation
    K->>F: seed future scratchpads
```

The proposal path is a ledgered side channel. A killed failure family is machine-blocked before the committee sees it: the RefutedExperimentsLedger checks the proposal's failure-family signature against prior `killed` dispositions and writes a `rejected_refuted` receipt; revised carriers with a new family signature pass through normally. Proposals that reach the committee are adjudicated by two sealed leaves — one primary, one adversarial dissent — with escalation when either verdict lacks a concrete reason or rule citation. The zero-credit rider can inform later work, but the committee decision and disposition decide whether a row becomes case-law or stays backlog.

## 4. Strategy Office Convene

```mermaid
sequenceDiagram
    participant A as audits dossier
    participant Q as sealed leaf queries
    participant C as experiment cards
    participant S as sealed reward disposes
    participant D as dictionary write-back

    A->>Q: render dossier and query menu
    Q-->>A: capped-round query responses
    A->>C: commission experiment cards
    C->>S: submit batch for disposition
    S-->>D: approved cards / reward receipt
    D-->>A: write back conjecture mode and history
```

Strategy Office reads a bounded dossier, allows only capped query rounds, then writes cards through the decision membrane. The downstream write-back updates the dictionary with the committed surface, including conjecture-mode outcomes.

## 5. Escalation Lattice

```mermaid
sequenceDiagram
    participant M as deterministic miner
    participant L as ladder
    participant R as reflex
    participant S as leaf strikes
    participant E as effort tier
    participant Q as on-demand checkpoint
    participant O as office

    M->>L: exhaust the deterministic miner
    L->>R: climb the ladder
    R->>S: trigger leaf strikes
    S->>E: raise effort tier
    E->>Q: request checkpoint
    Q->>O: escalate to office
```

The lattice is ordered by cost and visibility. A failed lower rung should promote only the next needed instrument, with office escalation reserved for the cases that survive the deterministic ladder.

## 6. Promotion + Learning Cascade

```mermaid
sequenceDiagram
    participant L as leaf submission
    participant G as pre_judge_gate
    participant J as judge
    participant DC as derived constraints
    participant CM as champion materialization
    participant B as LeanMill blueprint
    participant LM as async Lean campaign
    participant AR as absorb_ratification
    participant IC as invariant_certificates
    participant P as pruning consumers
    participant SP as scratchpad + spec_nogood ledger
    participant TFD as tried_failed_digest provider

    L->>G: candidate carrier
    G->>G: observed-tier gates must-pass
    G->>G: heldout-tier non-regression vs champion
    G-->>L: fail receipt with counterexample quotient
    G->>J: dominance-promotable candidate passes to judge
    J-->>DC: derived constraint proposals
    DC->>DC: confirm on (run_id, iteration) recurrence across distinct runs
    DC-->>J: confirmed constraints feed next briefing
    J-->>CM: gate payload + candidate memory
    CM->>CM: scan workspace candidates, run harness, observed-tier safety + dominance check
    CM-->>CM: backup live test_model.py
    CM->>B: promoted champion spec
    B->>LM: blueprint.md dispatched async
    LM-->>AR: Lean proof artifact
    AR->>AR: compile-verify proof audit
    AR->>IC: write invariant_certificates.jsonl (kernel-ratified)
    IC->>P: ProvenInvariantsProvider feeds reachability admissibility filter
    P-->>P: prunes next spec abduction and pursuit
    L->>SP: INVESTIGATED turns write to spec_visible_nogoods.jsonl
    SP-->>L: next turn fragment head: already-eliminated case law + scratchpad tail (2000 chars)
    L->>TFD: run artifacts accumulate harness_weakness_receipts, probe rows, REFUTED block
    TFD-->>L: tried-and-failed digest injected into next briefing
```

The cascade is fully deterministic below the judge call. Champion materialization runs at loop bootstrap from memory artifacts; it backs up the live model before installing a better candidate. The LeanMill campaign is asynchronous and non-blocking: the play loop continues without waiting for proof work. Ratified certificates constrain reachability sweeps and may prune candidate families the abductor proposes on subsequent iterations.

The scratchpad and eliminations paths close the self-learning loop: `workspace/leaf_scratchpad.md` is re-fed verbatim (tail 2000 chars) at each turn's fragment head, and credited `INVESTIGATED` eliminations accumulate in `workspace/spec_visible_nogoods.jsonl` and appear as "already eliminated" case law. The tried-and-failed digest provider (`tried_failed_digest`) also includes the `RefutedExperimentsLedger` `REFUTED (machine-blocked)` block and recent `harness_weakness_receipts.jsonl` and `strategy_experiment_probe_rows.jsonl` entries.
