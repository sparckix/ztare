# ZTARE Priority Roadmap

**Last refreshed:** 2026-05-20
**Planning horizon:** next 2 weeks
**Owner:** ZTARE maintainers

This is the working roadmap for what ZTARE should make easier and more
reliable next. It is not the experiment ledger, the seam archive, or a claim
registry. It treats ZTARE as a socio-technical research system: human
principal, agentic operators, evidence, gates, workbench surfaces, forecasts,
ledgers, and publication boundaries. It answers one question:

```text
What should the system learn to do better next?
```

The current priority stack is:

1. Clarify and harden the socio-technical system boundary.
2. Work on genuinely hard problems without overclaiming.
3. Improve the discovery kernel from the failures it observes.
4. Turn repeated failures into reusable recursive-improvement machinery.
5. Build organizational memory so the research company compounds instead of
   rediscovering the same lessons.

Release hygiene still matters, but it is a gate around those priorities, not
the reason the repo exists.

## Current Thesis

ZTARE is a falsification-native research system. Its value is not only that it
can run adversarial searches on difficult substrates; it is that it can notice
why those searches fail, preserve the lesson, and route the next attempt more
intelligently.

The hard problems are the forcing function. The recursive and organizational
layers are how the system becomes better after each failure. The public
positioning layer matters because readers need to understand that this is not
only an AI tool; it is a governed human-agent research workbench with explicit
authority paths.

## Priority Tracks

| Track | Public name | What it is | Success condition |
|---|---|---|---|
| 1 | Socio-Technical System Position | Human operator, agentic operators, workbench surfaces, public/private membrane, related-system positioning, and authority boundaries. | A new reader can explain what ZTARE is without reducing it to math, dashboards, agent chat, or symbolic regression. |
| 2 | Hard Problem Campaigns | Navier-Stokes, neural scaling, modified gravity, theorem/prover work, and other bounded scientific campaigns. | Each campaign has a scoped claim, a live residual, and a next falsifier or source-design step. |
| 3 | Discovery Kernel | The validator, rubrics, substrate contracts, fit primitives, gates, proof bridges, and anti-Goodhart machinery. | A user can pressure-test a hypothesis and recover why it failed, survived, or became underidentified. |
| 4 | Recursive Self-Improvement | Trajectory mining, catch ledgers, anti-pattern catalogs, reflexive primitives, margin-of-safety gates, and source-health repair. | Repeated failure classes turn into tests, gates, source contracts, or explicit non-goals. |
| 5 | Organizational Learning | Forecast market, GP-233 yield decomposition, GP-244 intelligence surface, experiment ledger, action intelligence, and tenant-overlay governance. | The organization allocates attention from evidence and source readiness rather than chat memory or activity volume. |

The reusable organization-runtime kernel belongs in the sibling
`cognitive-firm` project. This repo keeps the ZTARE research tenant, the
discovery kernel, the scientific campaigns, and the private/public surfaces
needed to operate them.

## P0 Pulls

| Priority | Track | Bet | Status | Outcome | Proof of done | Next action |
|---|---|---|---|---|---|---|
| P0 | Hard Problem Campaigns | NS residual focus | Active | Stop repeating 0-degree/parabolic-slaving reductions and route effort to named residual estimates, proof-search gates, or source-design tests. | NS public journey, residual manifest, atlas, forecast rows, and research-output summaries agree on the live residual. | Keep GP-244 and forecast-market consumption observer-only until source readiness improves; no default RD disturbance. |
| P0 | Hard Problem Campaigns | Neural scaling source design | Active | Treat existing trajectory results as bounded; move effort to sealed per-instance checkpoint/eval packets rather than same-packet rescues. | Source admissibility and observability gates are explicit in the case-study record. | Preserve the bounded claim and next source-design step in the public case-study docs. |
| P0 | Discovery Kernel | Contract reliability | In progress | The loop rejects malformed rubrics, missing suites, broken substrate contracts, and future-observable laundering before wasting model calls. | Targeted tests cover contract validation, runner admission, and scoring caps. | Keep reducing deterministic failure modes into preflight checks. |
| P0 | Recursive Self-Improvement | Failure-to-primitive pipeline | Active | Mining, catches, and reflexive observations become candidate gates or source contracts only when they generalize. | Anti-pattern catalog, catch ledger, trajectory mining, and source-health rows connect to implemented changes or explicit observer-only status. | Use GP-244 source readiness to separate useful signals from allocation evidence. |
| P0 | Organizational Learning | GP-244 intelligence surface | Implemented; source gaps visible | Operator can see forecast use, yield bottlenecks, experiment state, catch risk, source readiness, and observer-only learning candidates without mutating official state. | JSON/markdown/private HTML compile from source ledgers and emit executive brief, ETL manifest, source map, and source-readiness rows. | Repair p0 source emitters before treating the market or dashboard as allocation evidence. |
| P0 | Public release gate | Entry path and source hygiene | In progress | A new reader can understand the repo without private chat, ignored working papers, or maintainer-only checks. | README, docs map, first-30-minutes guide, prompt sheet, roadmap, release checklist, `.gitignore`, and smoke canary agree. | Run the public-doc adoption review after each doc cleanup. |
| P0 | Socio-Technical System Position | Related-system and module map | Active | Position ZTARE as a governed human-agent research system rather than a math-agent comparison, dashboard bundle, or validator-only repo. | `docs/concepts/system_position_and_module_map.md`, README, docs map, and roadmap use the same frame and distinguish human operator from agentic operator. | Keep upleveling the module map as LeanMill, forecast pool, Orbit, supervisor, and public-claim surfaces mature. |

## P1 Pulls

| Priority | Track | Bet | Status | Outcome | Proof of done | Next action |
|---|---|---|---|---|---|---|
| P1 | Hard Problem Campaigns | Theorem/prover bridge | Active | Discovered candidates can become formal proof obligations without pretending proof stubs are proofs. | Lean sources, theorem-writer workflow, proof-search receipts, and falsifier gates carry explicit status. | Keep proof obligations scoped and source-backed. |
| P1 | Discovery Kernel | Substrate authoring guardrails | In progress | Substrate authors cannot accidentally launch untestable or leakage-prone runs. | Rubric validator, holdout checks, source-contract audit, and submission snapshots are documented and tested. | Add fixtures for failure modes already paid for. |
| P1 | Recursive Self-Improvement | Recurrence suppression | Partial | Repeated catch categories can be measured for later avoidance, not merely logged. | Catch rows have enough category, timing, and consumption labels to estimate recurrence suppression. | Improve emitters at the catch/action source, not downstream prose inference. |
| P1 | Organizational Learning | Decision-use accounting | Source blocked | Forecasts become allocation evidence only when decisions log what forecast changed, what action followed, and what happened. | Forecast aggregates join to decision-use rows and outcome rows. | Add or repair source-side decision-use emitters. |
| P1 | Organizational Learning | Action intelligence compatibility | Partial | Actions, forecasts, catches, and yield rows can support bandit-style or value-of-information analysis later without local reward hacking now. | Action-impact rows include context, actor, action, expected effect, observed effect, and externality notes. | Keep live control observer-only until metrics are stable and source gaps close. |
| P1 | Discovery Kernel | LeanMill / GP-225 lemma-relevance and station factory | Active | A GNN-backed lemma-relevance ranker and a Lean station-factory orchestrator let proof-search routes consume mathlib at scale without dragging the whole stack into hand-engineering. | Seam `research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md`, station-scheduler, source-worker, probe-worker, and post-probe triage scripts under `scripts/public/control/leanmill_*`; coverage and held-out receipt gates pass. | Keep paid swarms non-default; promote opt-in zero-spend agent panels as RD discriminators only. |
| P1 | Hard Problem Campaigns | Epistemic-generation as mechanization placement (papers/epistemic-generation) | Draft | A placement theory for *which* research moves should become deterministic gates and which should stay structural-language scaffolding. Operationalised on a 1214-move, 64-arc corpus; a layered structural language (six shared-core, eight broadly shared, four peripheral operations) shows partial out-of-distribution transfer; agent-facing primitive screens are honest negatives. | Paper draft `papers/epistemic-generation/draft.md`; the surviving spine is mechanism-named subset, categorical research-vs-rote distinction, residual boundaries, and mechanization placement. | Tighten the placement criteria, harden the PDE-stress finding, do not promote primitives to solver-uplift claims they did not earn. |

## P2 Pulls

| Priority | Track | Bet | Status | Outcome | Proof of done | Next action |
|---|---|---|---|---|---|---|
| P2 | Organizational Learning | Tenant overlay boundary | Design | ZTARE demonstrates a research tenant without duplicating the reusable cognitive-firm kernel. | `org/` docs distinguish reusable primitives from ZTARE-specific overlays and link the sibling kernel. | Keep tenant-specific notification channels and mandates out of public ZTARE. |
| P2 | Recursive Self-Improvement | Synthetic panels as research method | Design | Multidisciplinary panels produce research directions and objections without becoming authority. | Panel outputs feed synthesis files or seams with clear status and adversarial review. | Keep generated panel payloads in ignored review/synthesis workspaces unless promoted. |
| P2 | Discovery Kernel | Enterprise backend compatibility | Design | Filesystem-first single-user runtime can later map to API/Postgres/RBAC/leases without rewriting the kernel. | Interfaces define source connectors, identity/actor attribution, leases, event outbox, and audit provenance. | Keep first-party scope to stable interfaces unless a real deployment forces backend work. |

## Operating Rules

- Hard problems set the agenda. Infrastructure exists to improve the next hard
  problem attempt, not to create dashboards for their own sake.
- ZTARE is a socio-technical system first. Do not describe it as only a model
  wrapper, proof tool, dashboard, or benchmark harness.
- Recursive improvements must name the repeated failure they prevent. If a
  lesson has not generalized, keep it as observer-only.
- Organizational learning requires source records. A dashboard or synthesis is
  useful only when it points back to source ledgers and shows source readiness.
- Forecasts are not allocation evidence until decision-use and outcomes are
  logged.
- The hardening board is public historical provenance as of 2026-05-20. Use
  the roadmap, experiment ledger, seams/specs, and GP-244 read model for
  current state.

## Public Release Gate

Before a public push:

1. Entry docs must explain the current four-track map without private
   dependencies.
2. Public docs must not rely on ignored working-paper paths or private seams.
3. Public quickstart must use first-user checks, not maintainer canaries.
4. Case-study claims must include scope, evidence pointer, and non-claim.
5. Private runtime state, overlays, generated dashboards, and source-health
   outputs stay ignored.

## Current Open Questions

| Question | Why it matters | Default until resolved |
|---|---|---|
| What is the right live residual for NS after the 0-degree recurrence? | Avoid another month of reduction ticks in a space already bounded by the apparatus's own obstruction. | Treat parabolic-slaving reductions as terminal; route to named non-taxonomic estimates or proof-search gates only when falsifiable. |
| When does GP-244 become allocation evidence? | Forecasts, catches, and yield rows can otherwise become a polished mirror of weak sources. | Use GP-244 for triage until source-readiness and decision-use rows are repaired. |
| Which recursive lessons deserve kernel code? | Too much reflexive machinery can overfit local failures; too little loses organizational memory. | Require repeated occurrence, a clear prevented failure, and a testable source contract before promotion. |
| What belongs in ZTARE vs. cognitive-firm? | Avoid duplicating the org-runtime kernel while still showing how a research tenant operates. | Reusable org primitives upstream; ZTARE-specific overlays and scientific research state here. |
| How should bandit/RL-style action learning enter? | Local reward optimization can create externalities or Goodhart pressure. | Keep compatibility in action-impact records; do not automate live control until source quality, externality checks, and decision-use accounting are stable. |
