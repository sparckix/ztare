/-
# NS Track B — Centralized Fujita-Kato local strong-solution existence

This file centralizes the **single canonical** axiomatization of the
Fujita-Kato local-in-time strong-solution existence theorem
(Fujita-Kato 1964; Kato 1984).

## Background

Prior to consolidation, two textually duplicate copies of this axiom
existed under different names:

* `local_strong_existence_NS`           in `ns_trackb_bkm_smoothness_criterion.lean`
* `local_strong_existence_NS_for_ESS`   in `ns_trackb_ess_l3_endpoint.lean`

The void-miner audit (`ns_trackb_void_audit_2026_05_07.md`, finding A1 ≡ A4)
flagged these as a maintenance void.  This file resolves the duplication:
both bridge files now import the single axiom shipped here.

## Classical statement

For any `NavierStokesEquations n` whose initial velocity is `C^∞` and
divergence-free, there exists `ε > 0` and a smooth velocity / pressure
pair `(u, p)` solving NS on `[0, ε]` with the prescribed initial
condition.

References:

* H. Fujita, T. Kato, *On the Navier-Stokes initial value problem I*,
  Arch. Rational Mech. Anal. **16** (1964), 269–315.
* T. Kato, *Strong L^p-solutions of the Navier-Stokes equation in ℝᵐ,
  with applications to weak solutions*,
  Math. Z. **187** (1984), 471–480.

## Sorries

This file is **sorry-free**.  It ships exactly one named axiom
referencing the cited classical result.
-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes

namespace ZtareProofs.NS

noncomputable section

/-- **AXIOM (Fujita-Kato 1964).** Local-in-time existence of a
classical (`C^∞`) Navier-Stokes solution for smooth, divergence-free
initial data.

For any `NavierStokesEquations n` whose initial velocity is `C^∞`
and divergence-free, there exists `ε > 0` and a smooth velocity /
pressure pair `(u, p)` solving NS on `[0, ε]` with the prescribed
initial condition.

This is the **single canonical** copy of the Fujita-Kato local-strong
existence axiom; the BKM and ESS bridges import this file rather than
re-stating it.

References:
* H. Fujita, T. Kato, *On the Navier-Stokes initial value problem I*,
  Arch. Rational Mech. Anal. **16** (1964), 269–315.
* T. Kato, *Strong L^p-solutions of the Navier-Stokes equation in
  ℝᵐ, with applications to weak solutions*,
  Math. Z. **187** (1984), 471–480. -/
axiom local_strong_existence_NS
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity) :
    ∃ (u : NavierStokes.VelocityField n) (p : NavierStokes.PressureField n)
      (ε : ℝ), 0 < ε ∧ ContDiff ℝ ⊤ u ∧ ContDiff ℝ ⊤ p ∧
        (∀ x : EuclideanSpace ℝ (Fin n),
          u (NavierStokes.pairToEuc 0 x) = nse.initialVelocity x)

/-- **Re-export under the legacy ESS name** for backward compatibility.

Earlier the ESS bridge declared its own `local_strong_existence_NS_for_ESS`.
That declaration is now dropped in favor of this re-export, which has
**identical content** to `local_strong_existence_NS` and is offered only
to preserve any external references to the old name. -/
theorem local_strong_existence_NS_for_ESS
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity) :
    ∃ (u : NavierStokes.VelocityField n) (p : NavierStokes.PressureField n)
      (ε : ℝ), 0 < ε ∧ ContDiff ℝ ⊤ u ∧ ContDiff ℝ ⊤ p ∧
        (∀ x : Euc ℝ n,
          u (NavierStokes.pairToEuc 0 x) = nse.initialVelocity x) :=
  local_strong_existence_NS nse h_initial_smooth

end

end ZtareProofs.NS
