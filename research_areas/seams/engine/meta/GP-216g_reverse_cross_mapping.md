# GP-216g — Reverse Cross-Mapping: v5 op → all apparatus

> **Seam metadata** · `seam_id:` GP-216 · `track:` engine · `status:` active · `last_updated:` 2026-05-14


**Status:** active *(inferred 2026-05-08 — needs operator review)*

*2026-05-05. Item 3 of GP-216f's missing-pieces list. Operational discipline tool: for each universal op, list all apparatus across all 7 ZTARE scales that enforces it. Useful for impact analysis when changing an op's apparatus.*

**2026-05-14 consistency note:** this reverse map was written against the earlier v4/v5 hybrid ID surface. The canonical registry now exports the 8-subfield v5 vocabulary in `src/ztare/research_director/universal_research_ops.py` and the rendered surface in `docs/concepts/structural_language_catalog.md`. Treat the apparatus rows below as a legacy impact map until the reverse map is fully remapped from old `core_02/core_06/core_07` meanings to current `core_02/broad_01/core_06` meanings.

## Why this exists

GP-216e maps reflexive primitives → v5 ops (one direction). For day-to-day apparatus work, the more useful direction is the reverse: given a v5 op, what apparatus across ZTARE's 7 scales currently enforces or instantiates it?

If the apparatus for `core_07 Generalization` changes (e.g., a new framer transform is added), this table tells you the 5+ places that need cross-checking. Without it, the change rolls out and 4 of 5 places drift silently.

## The reverse-mapping table

For each shared-core v5 op, all apparatus instances:

### core_01 — Problem Reformulation & Reduction

| Scale | Apparatus | Specific instance |
|---|---|---|
| Coordinate | Framer SIGMA | `log` / `signed_log` / `arctan` (h_in transforms that re-coordinate) |
| Iteration | pivot_heuristics | `coordinate_compression` (module 13) — change coordinate system explicitly |
| Iteration | pivot_heuristics | `dimensional_shift` (module 5, partial — overlaps core_07) |
| Research arc | universal_research_ops.py | core_01 entry (canonical) |
| Verification | (n/a) | (no paper-5 verification op directly maps; closest is op3 topological_pivot_recognition) |
| Reflexive | reflexive_primitives doc | "Residual Isomorphism" (Compress + Invert) |
| Engineering | agentic_patterns | (n/a directly; Pattern 9 self-modeling is meta-application) |

**Impact analysis:** changing core_01's mechanism affects 3+ touchpoints (framer.py, pivot_heuristics.py, universal_research_ops.py). Test sites: framer round-trip tests; pivot_heuristics fixture regression; v5 vocabulary self-test.

### core_02 — Iterative Refinement Loop

| Scale | Apparatus | Specific instance |
|---|---|---|
| Coordinate | (n/a) | iteration is not a coordinate-scale primitive |
| Iteration | autoresearch_loop | the loop ITSELF instantiates this op at meta-scale |
| Iteration | StagnationSpecialCaseHintGate | mechanizes `core_02 + core_05` at runtime |
| Iteration | PotentialFunctionMonotonicityGate | mechanizes `core_02` directly (potential function discipline) |
| Research arc | universal_research_ops.py | core_02 entry (canonical) |
| Verification | paper 5 | op6 basin_search (within-frame iteration) |
| Reflexive | reflexive_primitives doc | "Reflexive Orchestration" |
| Engineering | agentic_patterns | Pattern 2 Pre-Flight Assertion Battery (iterate against battery) |

**Impact analysis:** changing core_02's mechanism affects 6+ touchpoints. Highest-risk: PotentialFunctionMonotonicityGate logic (runtime fail-closed gate). Test sites: gate self-tests; loop fixture regression.

### core_03 — Decomposition & Recomposition

| Scale | Apparatus | Specific instance |
|---|---|---|
| Coordinate | Framer SIGMA | `power_2` / `power_0.5` (split magnitude + phase) |
| Iteration | pivot_heuristics | `entropy_stripping` (module 4 — peel narrative to observables) |
| Iteration | pivot_heuristics | `failure_topology` (module 3 — name 3 failure nodes) |
| Research arc | universal_research_ops.py | core_03 entry (canonical) |
| Verification | (n/a) | (no direct paper-5 op; gluing-discipline is ambient) |
| Reflexive | reflexive_primitives doc | "Hybrid Persona Router" (decompose review by failure family) |
| Engineering | agentic_patterns | Pattern 6 Decomposed Wire-In with Single Entry Point |

**Impact analysis:** changing core_03 affects 4+ touchpoints. Highest-risk: pivot_heuristics module text (consumed in mutator prompts).

### core_04 — Local-to-Global Assembly

| Scale | Apparatus | Specific instance |
|---|---|---|
| Coordinate | (n/a) | not a coordinate-scale primitive |
| Iteration | (partial via failure_topology, but not direct) | weak coverage at iteration scale |
| Research arc | universal_research_ops.py | core_04 entry (canonical) |
| Verification | (n/a) | (gluing discipline is ambient in paper 5; no direct op) |
| NS Track B | ns_profile_limit_lsc_bossfight.lean | LSC limit-passage = literal local→global assembly |
| Reflexive | reflexive_primitives doc | (no direct primitive; verification-side at micro scale) |
| Engineering | agentic_patterns | (n/a directly) |

**Impact analysis:** core_04 has the WEAKEST apparatus coverage. Most enforcement is at the substrate level (NS Track B's LSC theorems). Codex's recent wiring of GP-216 op-class enrichment routes "local estimates don't glue globally" → core_04 at the pivot scale, partly closing this gap.

### core_05 — Canonical Form & Invariance / Extremal Case Analysis

| Scale | Apparatus | Specific instance |
|---|---|---|
| Coordinate | Framer SIGMA | `reciprocal` (inversion-to-extremes) |
| Iteration | pivot_heuristics | `fixed_point_scan` (module 15 — subset where f equals canonical) |
| Iteration | pivot_heuristics | `collision_exploit` (module 16 — f(a)=f(b) is structural identity) |
| Iteration | pivot_heuristics | `inversion` (module 12) |
| Iteration | StagnationSpecialCaseHintGate | mechanizes core_05 (special-case candidates) |
| Research arc | universal_research_ops.py | core_05 entry (canonical) |
| Verification | paper 5 | op7 failure_family_tagging (canonical-naming) |
| Reflexive | reflexive_primitives doc | "Inception Pattern" (extremal validator simulation) |
| Reflexive | reflexive_primitives doc | "Procedural Self-Audit" (canonical task structure) |
| Engineering | agentic_patterns | Pattern 5 Inverted Hash; Pattern 7 3-Axis Novelty |

**Impact analysis:** core_05 has the RICHEST apparatus coverage (8+ touchpoints). Changes ripple widely. Test surface: 3 pivot module fixtures + StagnationSpecialCaseHintGate self-tests + 2 reflexive primitives.

### core_06 — External Framework Importation

| Scale | Apparatus | Specific instance |
|---|---|---|
| Coordinate | Framer SIGMA | `arctan` / `sigmoid` (bounded-output transforms; Mathlib-style imports) |
| Iteration | pivot_heuristics | `interface_discipline` (module 11 — keep mutation at gate layer) |
| Iteration | BoundChainConsistencyGate | mechanizes core_06 + core_02 (chained external bounds with constants) |
| Research arc | universal_research_ops.py | core_06 entry (canonical) |
| Verification | paper 5 | op5 anchor_proxy_requirement (external observable binding) |
| Reflexive | reflexive_primitives doc | "Operator-Replay Mechanization" (operator's choices as external framework) |
| Engineering | agentic_patterns | Pattern 1 Stub-Replay Integration Testing (LLM as external oracle) |

**Impact analysis:** core_06 has 6+ touchpoints. Highest-risk: BoundChainConsistencyGate (runtime fail-closed gate on Lean theorem chains).

### core_07 — Generalization & Abstraction

| Scale | Apparatus | Specific instance |
|---|---|---|
| Coordinate | Framer SIGMA | `signed_log` / `softplus` (broaden domain of admissible inputs) |
| Iteration | pivot_heuristics | `dimensional_shift` (module 5 — higher-dimensional reframe) |
| Iteration | pivot_heuristics | `category_switch` (module 14 — different mathematical category) |
| Research arc | universal_research_ops.py | core_07 entry (canonical) |
| Verification | paper 5 | op2 controlling_claim_isolation (broaden the decisive claim) |
| Reflexive | reflexive_primitives doc | "Token-Optimized Self-Modeling" (codify tacit understanding into apparatus) |
| Reflexive | reflexive_primitives doc | "Research Taste Router" (preferences generalized into scoring) |
| Engineering | agentic_patterns | Pattern 9 Token-Optimized Self-Modeling |
| Engineering | agentic_patterns | Pattern 10 Cross-Reference Knowledge Graph |

**Impact analysis:** core_07 has the WIDEST cross-scale spread (9+ touchpoints), reflecting that generalization/abstraction is the most-used universal move. Changes here ripple widely. Test surface: 2 framer transforms + 2 pivot modules + 2 reflexive primitives + 2 agentic patterns.

## Reading the table

For impact analysis: when changing the apparatus enforcement of an op, **count the touchpoints in this table and add the test sites for each**.

For onboarding: this table provides the "where does this op live in the codebase?" answer. Each op's 4-9 apparatus touchpoints are the canonical view of how the op manifests in ZTARE's 7 scales.

For maintenance: an apparatus change in one row should trigger cross-check for the other rows of the same op. The auto-cross-reference linter (Item 4 of GP-216f) automates this check.

## Coverage gaps surfaced

The table reveals **uneven coverage across ops**:

- **Strongest coverage:** core_05 (8+ apparatus touchpoints), core_07 (9+)
- **Weakest coverage:** core_04 (3 touchpoints; mostly substrate-specific)

The weakest-coverage ops are the natural candidates for next apparatus work. Codex's recent wiring of "LSC → core_04" partly addresses core_04's weak coverage at the iteration scale.

## What this is NOT

- Not exhaustive: I may have missed apparatus instances. Should be cross-checked against the unified knowledge graph (`analytics/public/queries/graphs/ztare_knowledge_graph.json`).
- Not authoritative: the universal_research_ops.py module is the canonical source for op definitions; this table is a derived view.
- Not a directive: changing the apparatus is the operator's call; this table just makes the impact surface visible.
