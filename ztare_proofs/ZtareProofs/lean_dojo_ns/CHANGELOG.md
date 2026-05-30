# lean_dojo_ns vendoring CHANGELOG

This directory contains files vendored from
[lean-dojo/LeanMillenniumPrizeProblems](https://github.com/lean-dojo/LeanMillenniumPrizeProblems)
under the Apache License, Version 2.0 (see `./LICENSE`).

Source commit: `540da94826f70f3edf4d4fc66ce6cda20e903f61`
Vendored on: 2026-05-07

## Files vendored

| Local path                              | Source path                              |
|-----------------------------------------|------------------------------------------|
| `Imports.lean`                          | `Problems/NavierStokes/Imports.lean`     |
| `Definitions.lean`                      | `Problems/NavierStokes/Definitions.lean` |
| `Navierstokes.lean`                     | `Problems/NavierStokes/Navierstokes.lean`|
| `LICENSE`                               | `LICENSE` (top-level Apache 2.0)         |

## Modifications applied

The only modifications to vendored Lean source files are import-path
retargets so the modules resolve inside the `ZtareProofs` Lake library:

- `Definitions.lean`: `import Problems.NavierStokes.Imports`
  → `import ZtareProofs.lean_dojo_ns.Imports`
- `Navierstokes.lean`: `import Problems.NavierStokes.Imports`
  → `import ZtareProofs.lean_dojo_ns.Imports`
- `Navierstokes.lean`: `import Problems.NavierStokes.Definitions`
  → `import ZtareProofs.lean_dojo_ns.Definitions`

Each modified file carries a prominent attribution header that records
the modification.

## Files explicitly NOT vendored

- `MillenniumRDomain.lean` and `MillenniumBoundedDomain.lean` are
  orthogonal to the energy-inequality bridge and may carry heavier
  dependencies; they are out of scope for this integration.
- `Millennium.lean`, `Torus.lean`, `AdjointSpace.lean` similarly out of
  scope.

## Toolchain note

lean-dojo upstream pins `leanprover/lean4:v4.26.0` and Mathlib
`v4.26.0`. ZtareProofs pins `leanprover/lean4:v4.30.0-rc2` and Mathlib
`v4.30.0-rc2`. Vendored files compile against Mathlib v4.30.0-rc2; if a
future Mathlib API drift breaks them, fixes go in the `ZtareProofs/`
copies (NEVER edit the upstream repo) and are documented here.
