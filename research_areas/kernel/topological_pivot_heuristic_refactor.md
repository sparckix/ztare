# Topological Pivot Heuristic Refactor

Legacy combined note:

- seam now lives at `research_areas/seams/GP-021_topological_pivot_heuristics_seam.md`
- spec now lives at `research_areas/specs/active/GP-021_topological_pivot_heuristics_spec.md`

## Status

Active private kernel spec.

## Scope

- whether the legacy topological-pivot prompt should be preserved, retired, or refactored
- how its useful heuristics should be reused across project families
- this spec does **not** implement the refactor yet

## Decision

Do not restore the legacy pivot monolith wholesale and do not retire it.
Refactor the useful search heuristics inside it into reusable heuristic modules, then assemble profile bundles by project family / falsification mode / stagnation state.

## Problem

The legacy topological-pivot prompt contains real search power.

It includes heuristics like:

- state incompatibility
- primary degree of freedom
- zero-trust autopsy
- entropy stripping
- dimensionality shift
- reciprocal operations
- adversarial stress-test
- systemic back-pressure
- coercive vectors
- coefficient of friction

Those heuristics helped broad, non-V4 projects escape local basins.

But the current implementation traps them inside one monolithic prompt that is:

- too broad for narrow kernel-hardening tracks
- too undifferentiated for repeated reuse
- too opaque to tune or reason about

## Why It Matters

Without a refactor, the system stays stuck in a bad binary:

- either use the whole legacy pivot prompt
- or ban it entirely

That is too coarse.

The actual architectural problem is:

- preserve high-value exploratory pressure
- without reintroducing symbolic theater, ontology drift, or grand-architecture overreach into narrow contracts

This matters because the old prompt was genuinely useful, but only in the right search regime.

## Constraints

- preserve the ability of non-V4 projects to use strong exploratory pressure
- preserve V4-family suppression of the generic pivot monolith
- do not widen V4/kernel scope with free-form ontology resets
- avoid turning this into a large new exploration engine
- keep the first slice auditable and prompt-local

## Clarification: What Is And Is Not V4

`eu_union_load_bearing_pillars` is **not** a V4-family project.

The V4-family gate is narrow:

- `epistemic_engine_v4`
- `epistemic_engine_v4_*`

Source:

- `src/ztare/validator/v4_family.py`

So:

- non-V4 projects can still use the generic pivot
- V4-family projects explicitly suppress it and substitute a bounded override

## Options

### Option A — Keep The Monolithic Pivot As-Is

**Description**

Keep the current legacy pivot for non-V4 projects and leave V4 suppression unchanged.

**Pros**

- no new work
- preserves historical behavior in broad non-V4 runs

**Cons**

- V4 still cannot reuse the useful pieces safely
- bounded-discriminator projects still get an overbroad exploration block
- same prompt is replayed identically
- no typed reuse or selective tuning

**Verdict**

Too blunt.

### Option B — Retire The Pivot Entirely

**Description**

Remove the legacy pivot path and rely only on narrower mutation discipline.

**Pros**

- simpler prompt surface
- removes symbolic overreach risk

**Cons**

- throws away real exploratory capability
- loses a mechanism that has opened viable basins in broad search

**Verdict**

Wrong.

### Option C — Factor The Pivot Into Reusable Heuristic Profiles

**Description**

Split the old prompt into named heuristic modules and assemble different profile bundles by project family / falsification mode / stagnation state.

Example modules:

- `failure_topology`
- `primary_degree_of_freedom`
- `reciprocal_variable`
- `success_liability`
- `back_pressure`
- `coercive_leverage`
- `dimensional_shift`
- `symbolic_mapping`

Proposed profile bundles:

- `legacy_generic`
  - broad non-V4 search
  - closest to the legacy prompt

- `bounded_discriminator`
  - keeps:
    - failure topology
    - reciprocal variable
    - success liability
    - back pressure
  - drops:
    - symbolic-mapping theater
    - unconstrained dimensional shift

- `kernel_bounded`
  - V4-safe subset
  - keeps:
    - failure topology
    - interface discipline
    - success-liability / failure-surface thinking
  - forbids:
    - ontology reset
    - grand-architecture substitution

**Pros**

- preserves the real search asset
- lets narrow tracks reuse the useful pieces safely
- creates an explicit architecture for exploratory pressure
- makes future tuning measurable and auditable

**Cons**

- adds prompt-assembly logic
- requires a small initial module vocabulary
- can be overengineered if expanded too early

**Verdict**

Recommended.

## Recommendation

Adopt Option C.

Specifically:

1. treat the heuristic repertoire as the reusable asset
2. split it into explicit modules
3. select profile bundles by:
   - project family
   - falsification mode
   - stagnation state
4. keep V4 suppression of the legacy monolith
5. let V4 reuse only the bounded-safe heuristic subset

Not recommended:

- restoring the legacy prompt unchanged
- deleting the pivot entirely
- building a large exploration-memory system in the first slice

## Implementation Sketch

### Phase 1 — Extract Heuristic Modules

Create a prompt-assembly helper, e.g.:

- `src/ztare/validator/pivot_heuristics.py`

Represent the old pivot as named fragments instead of one monolith.

### Phase 2 — Add Profile Selection

Selection inputs:

- project family
- falsification mode
- stagnation count

Initial profiles:

- `legacy_generic`
- `bounded_discriminator`
- `kernel_bounded`

### Phase 3 — Add Operator Visibility

Stdout should report:

- whether a pivot fired
- which profile fired
- which heuristic modules were injected

### Phase 4 — Optional Reuse Memory

Later only:

- record which heuristic families were already tried in this basin
- avoid replaying the exact same exploratory pressure forever

This is explicitly not required for the first implementation slice.

## Open Questions

1. Should profile selection be driven only by project family + falsification mode, or also by recent failure-family tags?
2. Should `bounded_discriminator` and `kernel_bounded` share one module vocabulary or maintain separate allowed lists?
3. When should heuristic-reuse memory become worth the complexity?

## Debate Log

### Turn 1 — Codex

Initial concern: the old topological-pivot prompt clearly had real search value, but the current system only offers a bad binary between full reuse and full suppression.

### Turn 2 — Codex

Clarified the scope boundary:

- the prompt is still live for non-V4 projects
- V4-family suppression is narrow and intentional
- `eu_union_load_bearing_pillars` is not V4

This shifted the seam from "restore the pivot" to "refactor the reusable heuristics inside it."

### Turn 3 — Codex

Recommendation stabilized:

- preserve the heuristic repertoire
- split it into reusable modules
- assemble bounded profiles instead of reusing the monolith

### Turn 4 — Codex

Implemented the first slice:

- added `src/ztare/validator/pivot_heuristics.py`
- extracted named heuristic modules
- introduced profile selection:
  - `legacy_generic`
  - `bounded_discriminator`
  - `kernel_bounded`
- wired `autoresearch_loop.py` to inject profiles instead of a hardcoded monolith
- stdout now reports which profile and modules fired

This is still a first slice, not a final closure. What remains is live verification that the new profile path preserves useful exploration pressure without reintroducing drift.
