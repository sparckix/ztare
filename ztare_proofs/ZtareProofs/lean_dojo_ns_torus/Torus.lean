/-
================================================================================
ATTRIBUTION
================================================================================

Source repository: https://github.com/lean-dojo/LeanMillenniumPrizeProblems
Source path:       Problems/NavierStokes/Torus.lean
Source commit:     540da94826f70f3edf4d4fc66ce6cda20e903f61
License:           Apache License, Version 2.0
                   See ./LICENSE in this directory for the full license text.
Copyright:         Copyright (c) 2025 Robert Joseph George

Copied from lean-dojo/LeanMillenniumPrizeProblems for the periodic-domain
typed-companion bridge integration. MODIFICATION: only the `import`
lines were retargeted from `Problems.NavierStokes.{Imports,Definitions,
Navierstokes,MillenniumRDomain}` to the corresponding `ZtareProofs.*`
paths so the file resolves inside the `ZtareProofs` Lake library. No
other content below this header is changed. See ./CHANGELOG.md for
vendoring notes.

================================================================================
-/

import ZtareProofs.lean_dojo_ns.Imports
import ZtareProofs.lean_dojo_ns.Definitions
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.lean_dojo_ns_torus.MillenniumRDomain
import Mathlib.Analysis.InnerProductSpace.PiL2

open EuclideanSpace MeasureTheory Order NavierStokes

/-!
`Torus3` is currently modeled as `ℝ³` (`Euc ℝ 3`) together with the *intended interpretation*
that points are identified modulo `ℤ³`.

This is enough for a clean statement of "periodic" Navier–Stokes on a bounded domain without
introducing additional quotient / Haar-measure infrastructure.
-/

/-- A lightweight model of the 3-torus, implemented as `ℝ³` with "periodic" interpretation. -/
abbrev Torus3 : Type := Euc ℝ 3

/-- Use the Borel σ-algebra on the `Torus3` model. -/
noncomputable instance : MeasurableSpace Torus3 := borel Torus3

/-- `Torus3` is a Borel space (by definition of the model). -/
noncomputable instance : BorelSpace Torus3 := ⟨rfl⟩

/-- Use Lebesgue measure (`volume`) on the `Torus3` model. -/
noncomputable instance : MeasureSpace Torus3 := ⟨volume⟩
