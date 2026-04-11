# GP-021 Topological Pivot Heuristics Spec

## Status

Active

## Scope

- how the legacy topological-pivot prompt should be reused going forward
- how its useful heuristics should be exposed as bounded profiles
- how profile selection should work across non-V4 and V4 projects

Does not cover:

- exploration memory / heuristic replay avoidance
- large-scale prompt-learning infrastructure
- a repo-wide migration of historical prompt traces

## Decision

Do not restore the legacy pivot monolith and do not retire it. Preserve its useful heuristic repertoire by exposing reusable modules and assembling them into bounded profiles selected by project family, falsification mode, and stagnation state.

## Problem

The old topological-pivot prompt had real search power, but it was trapped inside a single hardcoded prompt block.

That made it too broad for narrow kernel tracks, too opaque to tune, and too all-or-nothing to reuse safely.

## Why It Matters

ZTARE needs exploratory pressure, but not the same kind of exploratory pressure everywhere.

Broad non-V4 projects may need strong basin-escape heuristics. Narrow kernel tracks need a much tighter subset. Without a profile system, the runner oscillates between overbroad mutation and full suppression.

## Constraints

- preserve non-V4 access to strong exploratory pressure
- preserve V4 suppression of the generic monolith
- keep the first slice auditable and prompt-local
- avoid reintroducing symbolic theater or ontology reset into narrow tracks

## Options

### Option A — Keep The Monolith

**Description**

Leave the old prompt as-is for non-V4 projects.

**Pros**

- zero extra code
- preserves historical behavior

**Cons**

- keeps the all-or-nothing problem
- prevents bounded reuse in V4/kernel tracks
- remains hard to reason about

**Verdict**

Too blunt.

### Option B — Retire The Pivot Entirely

**Description**

Remove the pivot path and rely only on narrow mutation discipline.

**Pros**

- simpler prompt surface
- less symbolic-overreach risk

**Cons**

- throws away real exploratory capability
- loses a mechanism that previously opened viable basins

**Verdict**

Wrong.

### Option C — Reusable Heuristic Profiles

**Description**

Split the old pivot into named heuristic modules and assemble profile bundles:

- `legacy_generic`
- `bounded_discriminator`
- `kernel_bounded`

**Pros**

- preserves the real search asset
- lets narrow tracks reuse the safe subset
- creates an auditable architecture for exploratory pressure

**Cons**

- adds prompt-assembly logic
- still needs live verification

**Verdict**

Recommended.

## Recommendation

Adopt reusable heuristic profiles.

Current first-slice implementation:

- `src/ztare/validator/pivot_heuristics.py`
- profile selection in `src/ztare/validator/autoresearch_loop.py`
- stdout visibility for the active profile/modules

Not recommended:

- restoring the legacy monolith unchanged
- deleting pivoting entirely

## Implementation Sketch

Phase 1:

- define heuristic modules
- expose profile bundles
- wire runner selection
- print profile/module visibility to stdout

Phase 1.5 (2026-04-10 optimization-overshoot correction):

- `bounded_discriminator` expanded from 5 modules to 9 after GP-023 scoping surfaced that the first-slice trim had dropped three load-bearing heuristics and was missing the `interface_discipline` guardrail
- new `bounded_discriminator` profile (canonical order):
  - `state_incompatibility` (restored — basin-escape under hard constraint)
  - `primary_degree_of_freedom`
  - `failure_topology`
  - `entropy_stripping` (restored — aligned with bounded-disc goal)
  - `dimensional_shift` (restored — orthogonal shock; GP-023 hinge)
  - `reciprocal_variable`
  - `success_liability`
  - `back_pressure`
  - `interface_discipline` (added as guardrail)
- `adversarial_stress_test` and `coercive_leverage` stay out (correctly dropped — domain-specific)
- the genius pairing: `dimensional_shift` + `interface_discipline` together force paradigm-exploration without ontology drift
- full reasoning in seam Debate Log Turn 6

Phase 2:

- live-verify profile behavior in:
  - a non-V4 bounded-discriminator stagnation case (now using the expanded 9-module profile)
  - a V4 stagnation case (`kernel_bounded` unchanged)

Phase 3:

- only if needed later, add heuristic-reuse memory

## Open Questions

- should profile selection eventually use failure-family tags too?
- should `bounded_discriminator` and `kernel_bounded` share one module vocabulary long-term?
- when is heuristic-reuse memory worth the complexity?
