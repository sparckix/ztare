# Reflexive Primitives Catalog Index

**Discovered as a class:** 2026-05-08, when the architecture-index meta-graph
shipped (RP-001) and the operator's classification logic produced a Verdict B
("PARTIALLY NOVEL") finding that did NOT belong in `org/patterns/`
(orchestration patterns) or `org/anti-patterns/` (failure modes).

**Architectural rule:** central self-referential architectural components
— components that use the architecture's own capability graph / state /
infrastructure as central context for the architecture's own decisions —
live here. This is a THIRD CLASS distinct from patterns + anti-patterns:

| Class | Lives in | What it catalogs |
|---|---|---|
| Orchestration patterns | `org/patterns/` | Composable workflows (friction debate, swarm dispatch, reducer, etc.) |
| Anti-patterns | `org/anti-patterns/` | Failure modes (catch-ledger-backed) |
| **Reflexive primitives** | `src/ztare/reflexive_primitives/` | **Self-referential architectural components — the engine using its own infrastructure as central context for itself** |

Catalog format mirrors `org/patterns/*.md` and `org/anti-patterns/*.md`
(YAML frontmatter + markdown body).

## Relationship to `docs/concepts/reflexive_engineering.md`

The philosophical parent essay at `docs/concepts/reflexive_engineering.md`
(public) and `research_areas/private/philosophy/reflexive_engineering_primitives.md`
(private companion) catalog 8 reflexive primitives as numbered sections inside
one essay. This directory is the **machine-readable, per-primitive registry**
parallel to the patterns + anti-patterns directories. The essay is the
narrative; this directory is the register.

When a reflexive primitive ships in a central way, record it here as
`RP-NNN-<name>.md` with full YAML frontmatter (id, leg_applied, target, novelty
audit, dependencies, falsifier, anti-laundering commitments).

## Entries

| ID | Name | One-line summary | Verdict | Falsifier monitoring |
|---|---|---|---|---|
| RP-001 | architecture_index_meta_graph | Capability index + meta-graph used as central context for every Director dispatch; impact-weighted from catch ledger; self-referentially mandate-wired. | B (PARTIALLY NOVEL) | Spearman ρ(impact, frequency) > 0.9 for 4 weeks → demote impact-factor claim. Period: 2026-05-08 .. 2026-06-05. |
| RP-002 | pattern_action_contract | Pattern/anti-pattern/menu evidence converted into required RD evidence-carrier slots and close-time validation. | B (PARTIALLY NOVEL) | Next 10 depth-sensitive closes: <7 contract-filled payloads or unchanged tool-underuse catch rate → demote. Period: 2026-05-20 .. 2026-06-20. |
| RP-003 | capability_evidence_contract | Carrier-bound preflight contract for choosing which capability to build: exogenous carrier + bottleneck pinned to a frozen yield-decomposition (GP-233/GP-246) + kill criterion. Replaces the cold-pre-flight-killed CEP scalar. | B (PARTIALLY NOVEL) | Next K≥5 CEC bets: a capability adopted on a proposer-chooseable carrier, or fields no better than prior p_success → demote. Period: 2026-05-31 .. 2026-08-31. |
| RP-004 | self_report_epistemology_critic | GP-166 noise-profile critic turned inward on the apparatus's own metric series; flags autocorrelation/heteroscedasticity/non-Gaussian/errors-in-X so untrustworthy self-numbers are disclosed. | B (PARTIALLY NOVEL) | Positive+negative synthetic control monthly: false-alarm on i.i.d. OR miss on AR(1) φ=0.6 → demote. Period: 2026-05-31 .. ongoing. |

## Classification logic (operator-defined 2026-05-08)

The classification rule that routed RP-001 here:

- **Verdict A (Fully novel):** record as new construct + spawn paper. Lives in `research_areas/private/seams/` until adoption.
- **Verdict B (Partially novel = novel SHAPE + cite-and-adopt components):**
  record as REFLEXIVE PRIMITIVE if the construct uses the architecture's own
  infrastructure as central context for the architecture's own decisions.
  Lives here in `src/ztare/reflexive_primitives/`.
- **Verdict C (Cite-and-adopt only):** record as memory entry / agentic
  engineering pattern. Lives in `docs/concepts/agentic_engineering_patterns.md`
  or in MEMORY.md.

Verdict B + self-referential = THIS class.

## Anti-laundering commitments at the catalog level

Every entry MUST:

1. State its verdict (A / B / C) explicitly with literature-scout pointer.
2. Attribute every cite-and-adopt component (no buried citations).
3. Wire a binary, machine-checkable falsifier with date range + monitoring
   owner + monitoring artifact pointer.
4. Provide self-reference verification (e.g. `grep architecture_index.jsonl`
   shows the entry IS in the index it documents).

If an entry's falsifier fires, append a catch ledger row of kind
`false_novelty_claim` and amend the entry's `novel_pieces[].novelty_grade`
to `WITHDRAWN` for the demoted piece. Do NOT silently delete.

## Discoverability

This catalog is wired into:

- `analytics/public/index/architecture_index.jsonl` — each entry has a row with
  `kind: reflexive_primitive` (new kind added 2026-05-08).
- `org/mandates/research_director_mandate.md` — v1.50+ references this
  catalog alongside `org/patterns/` and `org/anti-patterns/`.
- `docs/concepts/reflexive_engineering.md` — philosophical parent.

## Cross-reference map (reflexive primitive ↔ ZTARE leg ↔ target layer)

```
RP-001 architecture_index_meta_graph     ↔ Compress + Adversarial Disagreement
                                          target: architecture's own capability surface
                                          siblings (philosophical, not yet machine-recorded):
                                            - Token-Optimized Self-Modeling (Compress, agent cognition)
                                            - Inception Pattern (Invert, environment model)
                                            - Hybrid Persona Router (AD, review layer)
                                            - Residual Isomorphism (Compress + Invert, grammar)
                                            - Reflexive Orchestration (AD + Compress, lifecycle)
                                            - Reflexive Specification Audit (AD, rubric/charter)
                                            - Procedural Self-Audit (Compress + Invert, task discipline)
                                            - Operator-Replay Mechanization (Compress + Invert, discovery loop)
                                            - Research Taste Router (Compress, principal preferences)
```

The 9 philosophical-essay primitives above are candidates for promotion to
machine-readable RP-NNN entries when they next ship in central ways.

## Versioning

Each entry has `version: 1` in frontmatter. Bump on:

- **Patch:** prose-only update, falsifier-monitoring artifact attached.
- **Minor:** new sub-component added; verdict refined with new evidence.
- **Major:** verdict re-graded (e.g. B → C if falsifier fires); novelty
  piece withdrawn. ALWAYS append a catch ledger row on major bumps.
