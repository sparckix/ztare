---
id: REFLEXIVE-PRIMITIVE-001
short_id: RP-001
name: architecture_index_meta_graph
version: 1
status: shipped
shipped: 2026-05-08
verdict: B  # PARTIALLY NOVEL per literature scout 2026-05-08
literature_scout: projects/ns_millennium_hunt/workspace/research_notes/architecture_index_meta_graph_literature_scout_2026_05_08.md
class: reflexive_primitive  # third class beyond org/patterns/ + org/anti-patterns/
leg_applied: [Compress, Adversarial Disagreement]  # Compress=catalog the capability surface; AD=impact-rank disagrees with frequency-rank
target: The architecture's own capability surface (gates, ops, primitives, mining, scripts, patterns, anti-patterns)
operational_goal: |
  The architecture maintains a central index of its own primitives that is
  injected into every Director dispatch via mandate-wiring, with an ex-post
  impact factor computed from the catch ledger + climb-trigger mining + session
  usage. The index is self-referential: this entry IS in the index it documents.

description: |
  Capability index + meta-graph used by the architecture as central context
  for every dispatch. Three-level disclosure (top-10 / kind-table / full-catalog)
  pattern-matched by lexical+structural triggers. Impact-weighted from the catch
  ledger so the surfaced primitives are the ones that have actually fired in
  central ways recently — NOT just the most-called primitives.

novelty:
  honest_framing: |
    NOVEL SHAPE assembled from cite-and-adopt components + 3 genuinely novel pieces.
    DO NOT claim "fully novel"; Verdict B says PARTIALLY novel.
  cite_and_adopt:
    - work: RAG-MCP semantic retrieval over MCP-tool catalog
      citation: arXiv:2505.03275 (Gan & Sun, May 2025)
      adopted: lexical/semantic retrieval over capability catalog as the primary discoverability mechanism
    - work: Anthropic Agent Skills three-level progressive disclosure
      citation: Anthropic engineering blog 2025 + platform.claude.com docs
      adopted: file format (YAML frontmatter + markdown body) and three-level disclosure (name+description preloaded, full body on demand, nested files lazy)
    - work: Voyager skill library
      citation: arXiv:2305.16291 (Wang et al.)
      adopted: ever-growing executable-capability library with embedding-indexed top-K retrieval per task
  novel_pieces:
    - id: impact_factor_first_class
      claim: |
        Ex-post impact factor (per-capability outcome score from catch ledger +
        F-row score-deltas + closure-weight) surfaced as a first-class index
        feature visible to the dispatcher. Voyager uses success-frequency only;
        Online-Optimized RAG (arXiv:2509.20415) updates retrieval EMBEDDINGS
        from feedback but does not expose an impact rank.
      novelty_grade: PARTIALLY_NOVEL
    - id: meta_graph_edges
      claim: |
        Catalog edges to seam-graph + GP-index + OKR tree (the meta-graph layer
        — flat catalogs in Voyager / RAG-MCP / Agent Skills do not link to host-
        architecture knowledge graphs).
      novelty_grade: NOVEL_IN_SHAPE
    - id: self_referential_mandate_wiring
      claim: |
        Catalog auto-injected on every Director dispatch (not just startup) via
        mandate-wiring at org/mandates/research_director_mandate.md v1.50. Agent
        Skills preloads at startup; Gödel Agent (arXiv:2410.04444) self-modifies
        code at runtime; neither auto-injects a ranked catalog per dispatch.
      novelty_grade: NOVEL_IN_SHAPE

triggers:
  lexical: [discoverability, capability_index, primitive_catalog, mandate_injection, impact_factor, dispatch_briefing]
  structural:
    - new_session_start
    - principal_dispatching_director
    - dormant_capability_suspected_underused
    - retirement_review_seeking_zero_impact_primitives
  problem_classes: [agent_dispatch_briefing, capability_discoverability, architectural_debt_surfacing]

components:
  index_jsonl: analytics/public/index/architecture_index.jsonl
  schema: analytics/public/index/architecture_index_schema.md
  renderer: scripts/public/control/render_architecture_index.py
  rendered_view: src/ztare/architecture_index/INDEX.md
  mandate_wiring: org/mandates/research_director_mandate.md (v1.50)
  scoring_rubric: analytics/public/index/architecture_index_schema.md §"Impact factor scoring rubric"

dependencies:
  required:
    - analytics/public/ledgers/catch/catch_ledger.jsonl  # source of impact-factor signal
    - climb_trigger_mining          # nightly job feeds impact_factor recomputation
    - GP-227_dashboard              # downstream-citation-count component of impact
  related_primitives:
    - id: RP-INCEPTION  # Inception Pattern — pre-computed model of validation pipeline injected into context
      relation: sibling  # both inject central context into agents pre-dispatch
    - id: RP-TOKEN-OPTIMIZED-SELF-MODELING  # token-budget structural cache
      relation: sibling  # both compress capability surface for narrow-context agents

falsifier:
  description: |
    Weekly Spearman rank correlation between impact-factor ranking (this
    primitive's claim) and frequency-of-invocation ranking (Voyager-style
    baseline). If ρ > 0.9 for 4 consecutive weeks, the impact-factor claim
    DEMOTES — the proposal collapses to a re-skin of Voyager / Agent Skills
    + retrieval, and the "impact_factor first-class" novelty piece is
    withdrawn from the recording.
  binary_check: |
    spearman_rho(impact_rank, frequency_rank) > 0.9 for 4 consecutive ISO weeks
    starting 2026-05-08.
  monitoring_period: 2026-05-08 .. 2026-06-05 (4 weeks)
  monitoring_owner: principal + RD daemon
  monitoring_artifact: analytics/public/queries/reflexive/architecture_index_falsifier_2026_05_08.json (TODO: ship before end of week)
  not_trivial: |
    On the 2026-05-08 snapshot, ranking by impact_factor_expost surfaces
    UNIVERSAL-RESEARCH-OPS / PDE-ESTIMATE-CRAFT-OPS (impact 4, last_used
    2026-05-08, central in the W6/T9 work) at the top, while a
    frequency-only ranking would surface gates that fire on every cage run
    regardless of whether they catch anything. The two rankings ARE
    different at t=0; the falsifier tests whether they CONVERGE over 4
    weeks. If they converge, impact_factor was a renaming.

falsifiable_test:
  type: machine_checkable
  binary_check: spearman_rho_over_4_weeks > 0.9
  on_failure: |
    Demote `impact_factor_expost` to `frequency_of_invocation_30d`. Update
    `analytics/public/index/architecture_index_schema.md` to acknowledge the collapse.
    Update this entry's `novel_pieces[0]` to `novelty_grade: WITHDRAWN`.
    Catch is logged to analytics/public/ledgers/catch/catch_ledger.jsonl with kind:
    `false_novelty_claim` and pointer to this primitive id.

anti_laundering_commitments:
  - Verdict B → recorded as PARTIALLY NOVEL, not "fully novel"
  - RAG-MCP / Anthropic Agent Skills / Voyager explicitly attributed in
    `novelty.cite_and_adopt`, NOT buried in a footnote
  - Falsifier wired with date range, owner, monitoring artifact — not
    aspirational
  - Catch #34 vigilance: Spearman falsifier IS the "if-this-then-demote"
    commitment that makes the impact-factor claim falsifiable

self_reference:
  index_row_id: REFLEXIVE-PRIMITIVE-001-architecture-index-meta-graph
  index_row_kind: reflexive_primitive  # NEW kind added to schema 2026-05-08
  verification: |
    The architecture-index now contains a row whose `path` points at THIS
    file. The index documents the index. Run
    `python scripts/public/control/render_architecture_index.py --grep reflexive-primitive`
    to verify.

discoverability:
  injected_into:
    - org/mandates/research_director_mandate.md (v1.50 mandate-wiring)
    - src/ztare/reflexive_primitives/INDEX.md (this catalog)
    - src/ztare/architecture_index/INDEX.md (rendered view)
  bidirectional_crosslinks:
    - org/patterns/INDEX.md         # sibling: orchestration patterns
    - org/anti-patterns/INDEX.md    # sibling: catch-backed failure modes
    - docs/concepts/reflexive_engineering.md  # philosophical parent

references:
  - projects/ns_millennium_hunt/workspace/research_notes/architecture_index_meta_graph_literature_scout_2026_05_08.md
  - analytics/public/index/architecture_index.jsonl
  - analytics/public/index/architecture_index_schema.md
  - org/mandates/research_director_mandate.md
  - docs/concepts/reflexive_engineering.md
  - research_areas/private/philosophy/reflexive_engineering_primitives.md

chain_position: pre  # runs BEFORE any agent dispatch (mandate-injected), not after a failure
---

# Reflexive Primitive 001: Architecture Index Meta-Graph

## What

A capability index + meta-graph that the architecture uses as central
context for every Director dispatch. Three-level progressive disclosure
(TOP-10 + kind-table + full catalog), pattern-matched by lexical+structural
triggers, impact-weighted from the catch ledger.

## Why this is reflexive (not just a catalog)

The index is self-referential by construction. THIS entry is itself a row in
the index it documents (`REFLEXIVE-PRIMITIVE-001-architecture-index-meta-graph`,
`kind: reflexive_primitive`). The architecture uses its own capability graph
as central context for every dispatch — the engine eating its own tail
in a productive way (per `docs/concepts/reflexive_engineering.md`).

## Verdict B: PARTIALLY NOVEL — honest framing

The literature scout (agent a8865f99, 2026-05-08) verified Verdict B. The
SHAPE is novel. The COMPONENTS are mostly cite-and-adopt:

| Component | Source | Status |
|---|---|---|
| Semantic retrieval over capability catalog | RAG-MCP (arXiv:2505.03275) | ADOPT |
| Three-level progressive disclosure (YAML+md, name+desc preloaded, body on demand) | Anthropic Agent Skills (2025) | ADOPT |
| Ever-growing executable-capability library w/ top-K retrieval | Voyager (arXiv:2305.16291) | ADOPT |
| Ex-post impact factor as first-class index feature | (no analog: Voyager uses success-frequency only; Online-Opt RAG arXiv:2509.20415 updates embeddings, not exposed ranks) | NOVEL piece 1 |
| Meta-graph edges to seam-graph + GP-index + OKR tree | (no analog: Voyager / RAG-MCP / Agent Skills all use flat catalogs) | NOVEL piece 2 (in shape) |
| Auto-injected on every dispatch via mandate-wiring | (no analog: Agent Skills preloads at startup; Gödel Agent self-modifies code; neither auto-injects ranked catalog per dispatch) | NOVEL piece 3 (in shape) |

Three genuinely novel pieces composed with three cite-and-adopt components.
DO NOT claim "fully novel." The literature-scout verdict (B) is the load-
bearing label.

## Falsifier (catch #34 vigilance commitment)

Weekly Spearman ρ between impact-rank and frequency-rank. If ρ > 0.9 for 4
consecutive weeks (2026-05-08 .. 2026-06-05), the "impact_factor first-class"
novelty piece DEMOTES to a renaming of Voyager-style success-frequency. The
falsifier is binary, machine-checkable, and pre-registered with date range.

If demoted: `novelty.novel_pieces[0].novelty_grade` becomes `WITHDRAWN` and
the entry is amended with a catch ledger row of kind `false_novelty_claim`.

## Self-reference verification

```
$ python scripts/public/control/render_architecture_index.py --grep reflexive-primitive
REFLEXIVE-PRIMITIVE-001-architecture-index-meta-graph    impact=5  last=2026-05-08  kind=reflexive_primitive  src/ztare/reflexive_primitives/architecture_index_meta_graph.md

1 match(es).
```

The architecture-index documents the architecture-index. The reflexive move
is complete.

## Cross-references

- Philosophical parent: `docs/concepts/reflexive_engineering.md` + `research_areas/private/philosophy/reflexive_engineering_primitives.md` (8 primitives; this would be Primitive 9 if folded into the essay; recorded here instead as the first machine-readable per-primitive entry)
- Sibling pattern catalog: `org/patterns/INDEX.md`
- Sibling anti-pattern catalog: `org/anti-patterns/INDEX.md`
- Literature scout: `projects/ns_millennium_hunt/workspace/research_notes/architecture_index_meta_graph_literature_scout_2026_05_08.md`
