# lean_dojo_ns_torus vendoring CHANGELOG

This directory contains files vendored from
[lean-dojo/LeanMillenniumPrizeProblems](https://github.com/lean-dojo/LeanMillenniumPrizeProblems)
under the Apache License, Version 2.0 (see `./LICENSE`).

It supplies the **periodic-domain** (Fefferman B + D) Clay statements;
its companion `../lean_dojo_ns/` supplies the shared `WeakSolution` /
`LerayHopfSolution` machinery that is reused unchanged here.

Source commit: `540da94826f70f3edf4d4fc66ce6cda20e903f61`
Vendored on: 2026-05-07

## Files vendored

| Local path                  | Source path                                         |
|-----------------------------|-----------------------------------------------------|
| `Torus.lean`                | `Problems/NavierStokes/Torus.lean`                  |
| `MillenniumRDomain.lean`    | `Problems/NavierStokes/MillenniumRDomain.lean`      |
| `MillenniumBoundedDomain.lean` | `Problems/NavierStokes/MillenniumBoundedDomain.lean` |
| `LICENSE`                   | `LICENSE` (top-level Apache 2.0)                    |

## Modifications applied

Only `import` paths were retargeted so the modules resolve inside the
`ZtareProofs` Lake library:

- `Torus.lean`:
  - `import Problems.NavierStokes.Imports`
    → `import ZtareProofs.lean_dojo_ns.Imports`
  - `import Problems.NavierStokes.Definitions`
    → `import ZtareProofs.lean_dojo_ns.Definitions`
  - `import Problems.NavierStokes.Navierstokes`
    → `import ZtareProofs.lean_dojo_ns.Navierstokes`
  - `import Problems.NavierStokes.MillenniumRDomain`
    → `import ZtareProofs.lean_dojo_ns_torus.MillenniumRDomain`
- `MillenniumRDomain.lean`: same retarget pattern, all three imports.
- `MillenniumBoundedDomain.lean`: retarget pattern across four
  imports (`Imports`, `Definitions`, `Navierstokes`,
  `MillenniumRDomain`). Additionally, the unused upstream
  `import Problems.NavierStokes.Torus` line was DROPPED because that
  file registers a `MeasureSpace Torus3 := ⟨volume⟩` instance that —
  since `Torus3 := Euc ℝ 3` is a reducible abbreviation — collides
  with `measureSpaceOfInnerProductSpace` on `Euc ℝ 3` and breaks
  downstream integral-typeclass elaboration. The bounded-domain file
  itself does not reference `Torus3`, so removing the import is
  semantically vacuous. `Torus.lean` is still vendored as a separate
  module for callers that explicitly want the `Torus3` model.

No other content below the attribution header is changed.

## Why this is split from `lean_dojo_ns/`

`lean_dojo_ns/` deliberately scoped to the shared NS machinery (no Clay
problem statements). The Clay statements (R³ and periodic) carry
heavier definitional content (Fefferman conditions 4–11, decay
predicates, `nseR3` constructor, `IsPeriodic`, `IsSpatiallyPeriodicForce`)
and live here alongside the periodic-specific artifacts so that the
core machinery directory stays minimal.
