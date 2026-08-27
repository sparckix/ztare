---
description: "A task-typed market where deterministic programs, frontier reasoning, model-authored programs, and verified hybrids compete under one evidence and authority contract."
---

# Capability-Adaptive Execution

ZTARE should not freeze an agent-versus-code boundary from an old benchmark.
Model capability changes with the task family, runtime, model, prompt contract,
tool surface, reasoning budget, and date. The stable layer is the work contract
and its settlement rule. Producers are replaceable.

The common kernel lives in
[`src/ztare/common/execution_market.py`](../../src/ztare/common/execution_market.py).
JaggedThoughts Capital supplies the first operating adapter in
[`src/ztare/investment/adaptive_execution.py`](../../src/ztare/investment/adaptive_execution.py).

## Governing identities

| Object | Job | Equality boundary |
|---|---|---|
| `ExecutionTask` | Freeze inputs, evidence hashes, output type, verifier, tolerance, consequence class, and authority ceiling | Exact task hash |
| `ExecutorIdentity` | Name one producer implementation and capability epoch | Implementation hash + runtime + model + reasoning configuration + epoch |
| `ExecutionReceipt` | Record carrier status, output hash, independent verification, residual, cost, latency, and granted authority | Task hash + executor identity + attempt |
| `CapabilitySnapshot` | Project same-family, same-epoch evidence for routing | Executor identity + task family |
| `ExecutionMarketPlan` | Select a primary and bounded shadow probes | Exact offers, receipts, and task |

The capability epoch includes the runtime version, model selector, reasoning
effort, response schema, and prompt-contract hash. A changed model or contract
starts a distinct evidence population.

## Operating transaction

```text
source-bound problem
  -> frozen ExecutionTask
  -> deterministic baseline + current executor offers
  -> bounded attempts
  -> independent verifier per output
  -> immutable receipts
  -> same-family capability snapshots
  -> primary route + shadow probes
```

Four execution modes are live in the investment adapter:

1. `deterministic_program`: the typed valuation interpreter;
2. `direct_agent`: a frontier model derives the answer directly;
3. `agent_authored_program`: the model writes a reusable `solve(case)` program,
   which runs in the shared guarded Python carrier;
4. `verified_hybrid`: the direct answer and authored-program suite must both
   pass and agree within tolerance.

The model may search outside the valuation grammar. It can reason directly or
compose a new algorithm. The task hash, evidence hashes, answer type, numeric
residual, and authority ceiling do not move with it.

## Promotion rule

An unmeasured executor runs as a shadow beside exactly one declared baseline.
Primary-route eligibility currently requires, within one task family and
capability epoch:

- at least 20 independently verified attempts;
- at least five distinct frozen task identities;
- an observed verifier pass rate of at least 98%;
- a live output carrier and an independent verifier.

Twenty retries of one equation cannot satisfy the diversity gate. Among
eligible executors, the planner exposes the cost/latency Pareto frontier and
uses a transparent cost, latency, then identity ordering. Consequence and
capital authority remain properties of the task; performance cannot enlarge
them.

This is intentionally a typed routing rule rather than a universal capability
score. Evidence for implied-growth root solving says nothing by itself about
industry analysis, earnings normalization, portfolio construction, or order
execution.

## Authored-program holdouts

A model could emit the right number while writing a useless program. The
investment adapter therefore creates three numeric counterfactuals only after
the provider returns. It executes the returned `solve(case)` function on each
unseen case and applies the same DCF residual and canonical-root verifier. The
program receipt passes only when the primary case and all three holdouts pass.

The hybrid adds a separate condition: direct reasoning and the reusable
program must agree. Direct, authored-program, and hybrid receipts from one
provider call are marked as a shared call; they are distinct execution-mode
observations, not three independent model invocations.

## First operating evidence

On 2026-08-10, the current subscription runtime (`codex-cli 0.146.0`, account
default model, high reasoning effort) attempted one IBM implied-growth task
bound to its stored decision and valuation-result hashes:

| Mode | Implied growth | Verification |
|---|---:|---|
| Valuation interpreter | 7.1128857805% | passed |
| Direct agent | 7.1128857805% | passed |
| Agent-authored program | 7.1128857805% | primary + 3/3 unseen cases passed |
| Verified hybrid | 7.1128857805% | both paths passed; agreement delta `1.25e-16` |

The maximum program-suite relative residual was `6.79e-16`. The route remains
`baseline_with_shadow_probes`: one task cannot qualify a task family. The run
is stored as an immutable execution-market artifact and a golden-store leaf;
it has analytical-shadow authority and cannot activate a paper decision,
change a portfolio, or route an order.

The residual is equation misfit: on this task it corresponds to roughly
`$0.00019` against a `$279.29B` target operating-equity value. The agreement
delta compares two answer producers. Both are precision checks; neither is a
return forecast or evidence that the valuation premise will make money. The
separate prospective performance path is
[`ztare.investment.closed_book`](../../src/ztare/investment/closed_book.py).

## JaggedThoughts boundary audit

The execution market does not imply that every investment operation should use
the same producer mix. Each family needs a settlement carrier before routing
can adapt.

| Task family | Current production path | Settlement carrier | Adaptive state |
|---|---|---|---|
| Public-source transport | Provider adapters and source policy | response hash, availability time, schema, point-in-time checks | Keep transport bounded; models may propose source plans later |
| Open-theme translation | Subscription agent | strict intent schema plus complete-catalog receipt | Already agent-produced and kernel-admitted; downstream yield remains uncalibrated |
| Filing fact normalization | Typed SEC fact compiler | units, periods, filing dates, accession lineage | Candidate for agent extraction only when checked against filing facts |
| Durable-earnings analysis | Company-quality program | source coverage, accounting identities, declared residuals | Numeric derivation can enter a market; normalization judgment lacks a complete verifier |
| Industry/strategy options | Research agent authors choices; grammar enumerates | evidence references, compatibility, bounded closure, representation residual | Agent generation is live; consequence scoring needs prospective calibration |
| Implied-growth valuation | Four-mode execution market | DCF residual, canonical root, post-generation holdouts | Implemented; shadow evidence only |
| Valuation-envelope compilation | Typed valuation grammar | units, assumption identity, mechanism compatibility, replay | Strong next adapter for model-authored programs |
| Fund factor decomposition | Factor-analysis program | source chronology, regression diagnostics, benchmark identity | Needs multiple public-data tasks and holdout windows |
| Portfolio assembly | Exact bounded enumerator | capital, turnover, exposure, compatibility, objective replay | Agents may propose candidates; constraint admission can be deterministic |
| World-model proposals | Versioned mechanism candidates | common episode matrix, linked losses, paired controls | Producer-open today; survivor authority remains evaluation-owned |
| Research dossiers | Subscription research agent | request/candidate identity, source minimums, evidence refs, lineage | Schema admission is live; factual and decision-yield calibration remains open |
| Paper activation and orders | Operator; brokerage absent | explicit confirmation and later settlement | Outside capability routing |

This audit moves only implied-growth production in the first slice. The other
rows identify a verifier or state why one is insufficient; they are not dormant
executor branches.

## Why this split compounds

Formal grammars remain useful as typed intermediate representations,
enumerators, provenance carriers, and verification oracles. They do not need
to monopolize production. As frontier models improve, a new executor can enter
the same market and earn current-epoch receipts without rewriting investment
state transitions. When a model becomes cheaper or more reliable for a task
family, routing can change from evidence. When capability regresses, the new
epoch loses the old eligibility automatically.

The pattern follows execution-backed reasoning in
[PAL](https://arxiv.org/abs/2211.10435) and
[LEVER](https://arxiv.org/abs/2302.08468), dynamic routing in
[RouteLLM](https://arxiv.org/abs/2406.18665), and verifier-backed test-time
sampling in [Large Language Monkeys](https://arxiv.org/abs/2407.21787).
Finance-specific benchmark snapshots such as
[Finance Agent Benchmark](https://arxiv.org/abs/2508.00828),
[FinToolBench](https://arxiv.org/abs/2603.08262), and
[Fin-RATE](https://arxiv.org/abs/2602.07294) inform priors and failure classes;
local task receipts determine the operating route.

## Current boundary

Only source-bound implied-growth solving has this adapter. Strategy option
generation, quality-of-earnings normalization, factor inference, portfolio
assembly, and qualitative thesis work still need their own task types and
verifiers before they can participate. The next useful extensions are those
with a sharp settlement carrier: source-grounded extraction against filing
facts, valuation-program compilation against unit and lineage checks, and
portfolio proposals against exact constraint and replay gates.
