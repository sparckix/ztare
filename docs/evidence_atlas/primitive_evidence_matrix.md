---
description: "Evidence matrix for ZTARE agentic engineering patterns, anti-patterns, and reflexive primitives."
---
# Primitive Evidence Matrix

> **Up:** [Evidence Atlas](README.md)

This matrix separates three things that are easy to conflate:

- a construct being named in a catalog;
- a construct being implemented or wired into the apparatus;
- a construct having evidence that it changed outcomes.

## Reflexive Primitives Registry

The machine-readable registry is [src/ztare/reflexive_primitives/INDEX.md](../../src/ztare/reflexive_primitives/INDEX.md).

| ID | Name | Current evidence level | Primary evidence | Atlas reading |
|---|---|---:|---|---|
| RP-001 | architecture_index_meta_graph | L2-L3 | architecture index rows, mandate wiring, catch-ledger impact weighting | Strong as a navigation/control primitive; needs current drift/frequency falsifier monitoring to avoid becoming a self-importance map. |
| RP-002 | pattern_action_contract | L2-L3 | `src/ztare/research_director/pattern_action_contract.py`, RD tick brief, close-payload contracts | Strong direction: turns patterns into required carrier slots. Needs outcome tracking across depth-sensitive closes. |
| RP-003 | capability_evidence_contract | L2 seed | [GP-247](../../research_areas/seams/apparatus/instrumentation/GP-247_capability_evidence_contract_seam.md) seam, `cec_ledger.jsonl` with CEC-001 resolved Kepler-alive | Correctly refuses scalar priority scoring. Needs >=5 resolved bets before it can support capability-ranking claims. |
| RP-004 | self_report_epistemology_critic | L2 seed | script plus disclosed public-claim caveat | Useful as a disclosure mechanism. Needs synthetic controls and wording cleanup around small-N catch-ledger interpretation. |

## Philosophical Reflexive Primitives

[Reflexive engineering](../concepts/reflexive_engineering.md) lists nine
philosophical primitives. Some have machine-readable RP entries; others are
still conceptual or partially mechanized.

| Primitive | Evidence status | Primary pointer |
|---|---|---|
| Token-Optimized Self-Modeling | Implemented pattern family; machine registry via RP-001 sibling map | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-1-token-optimized-self-modeling), [agentic pattern 9](../concepts/agentic_engineering_patterns.md#pattern-9-token-optimized-self-modeling) |
| Inception / environment model | Documented, partially instantiated through architecture maps and gates | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-2-inception-machine-readable-environment-model) |
| Hybrid Persona Router | Documented, evidence depends on specific review loops | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-3-hybrid-persona-router-cache-route-generate-promote) |
| Residual Isomorphism | Documented, historically linked to grammar expansion and farther-tail residuals | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-4-residual-isomorphism-solving-for-the-shape-of-ignorance) |
| Reflexive Orchestration | Conceptual in the public doc | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-5-reflexive-orchestration-orchestration-isomorphism) |
| Procedural Self-Audit | Implemented discipline validator surface | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-6-procedural-self-audit-discipline-isomorphism) |
| Operator-Replay Mechanization | Implemented in orchestration modules, evidence depends on recovered discriminator queues | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-7-operator-replay-mechanization) |
| Research Taste Router | Implemented preference/router surface, not truth evidence | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-8-research-taste-router) |
| Reflexive Forecast Market | Implemented as forecast-pool/action-routing infrastructure | [reflexive engineering](../concepts/reflexive_engineering.md#primitive-9-reflexive-forecast-market), [forecast pool](../../scripts/public/control/forecast/pool.py) |

## Agentic Engineering Patterns

[Agentic engineering patterns](../concepts/agentic_engineering_patterns.md)
is a public portable catalog. This table records evidence posture, not a
claim that every pattern has causal lift evidence.

| Pattern | Name | Evidence posture |
|---|---|---|
| 1 | Stub-Replay Integration Testing | Documented pattern with concrete motivating examples; look for per-module stub tests before claiming implementation coverage. |
| 2 | Pre-Flight Assertion Battery | Implemented broadly as smoke/gate targets; causal lift is per-target. |
| 3 | Eligibility Pre-Filter for Position-Biased Selection | Documented orchestration pattern; implementation evidence should be traced per pipeline. |
| 4 | Fallback Chain with Provenance Telemetry | Implemented in several control surfaces by origin/provenance fields; needs per-surface audit for coverage. |
| 5 | Inverted Hash for Adversarial-Resistant Equality | Implemented in multiple hash/fingerprint utilities; claim strength is mechanism-level unless paired with a prevented-failure row. |
| 6 | Decomposed Wire-In with Single Entry Point | Strong implementation pattern across `src/ztare` and `scripts/public/control`; evidence is code-organization and tests, not benchmark lift. |
| 7 | Canonical Hash + Operator Multiset | Documented novelty discipline; use claim-card evidence before treating as deployed across all symbolic tasks. |
| 8 | Bloat-Cap Calibration via Real Telemetry | Documented; evidence depends on telemetry-backed cap rows. |
| 9 | Token-Optimized Self-Modeling | Strong conceptual and implementation evidence through architecture maps and validators. |
| 10 | Cross-Reference Knowledge Graph | Implemented in analytics/index/query surfaces; needs drift checks for external trust. |
| 11 | Cross-Scale Fractal Map | Documented; evidence should be linked to concrete cross-scale maps before public promotion. |
| 12 | Sealed Forecast Pool for Execution Control | Implemented; see forecast pool smoke and forecast artifacts. |
| 13 | Result-Bound Success Claims | Strongly reflected in public claim register and non-claim discipline. |
| 14 | Adversary-Authored Apparatus With Forced Out-of-Loop Judge | Implemented in membrane/judge design; production hardening depends on VPS/store separation. |
| 15 | Structural Contract Gating | Implemented in gates and contract surfaces; evidence should be measured per gate family. |
| 16 | Reasoning Contract Compiler | Documented; needs implementation pointers per compiler surface before public lift claim. |
| 17 | Shadow-First Controller Promotion | Documented; use only where shadow/live rows exist. |
| 18 | Typed Obstruction Basin | Documented and visible in NS/Lean surfaces; not a proof-closure claim. |

## Operational Patterns And Anti-Patterns

The source tables are [pattern catalog](../../org/patterns/INDEX.md) and
[anti-pattern catalog](../../org/anti-patterns/INDEX.md).

| Surface | Count in source index | Evidence posture |
|---|---:|---|
| Patterns | 12 canonical IDs in `org/patterns/INDEX.md` | Catalog-backed. Usage evidence must be traced through deployment logs, claim cards, or experiment rows. |
| Anti-patterns | 17 file-backed IDs plus reserved gaps in `org/anti-patterns/INDEX.md` | Stronger provenance than ordinary patterns because the catalog records catch clusters and detection/mitigation pairs. Still, each mitigation's causal effect needs local evidence. |
| Catch ledger | 147 ratified catches in the current self-report critic input window | Useful but bursty; do not report as an independent sustained rate without caveat. |

## What The Matrix Makes Visible

The repo has many constructs. The portfolio problem is evidence
stratification:

- Some constructs are only named or philosophical.
- Some are implemented but not ablated.
- Some have decision-changing evidence.
- A smaller set has controlled benchmark evidence.
- Almost none yet has second-lab external validation.

That distribution is normal for a research repo of this size, but it should be
visible in public claims.

