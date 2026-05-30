import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Analysis.MeanInequalities
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity

/-!
# Helicity dichotomy on flat-radius branches (tick503, 2026-05-15)

## Origin

Operator + GPT-5.5 collaboration after tick501 KILL. tick501's
naive helicity pigeonhole failed because flat-stopping produces
NESTED cylinders, not disjoint. The corrected bound (this file)
uses the radius-charge formulation:

  if  `|H_Q| ≥ c · r_Q`  on a disjoint/bounded-overlap family
       (achievable via Vitali extraction from nested),
  then  `Σ_Q r_Q ≤ B / c`  (where `B` is the Cauchy-Schwarz
        budget `≤ √(T·E_0) · √(enstrophy)`).

This closes the HIGH-HELICITY sub-branch.

## The dichotomy

  flat branch  ⇒  high-helicity (radius-charge bound closes)
                  ∨  helicity-dark (sharpened residual)

The sharpened obstruction `NoHelicityDarkTangentialReynoldsDefect`
is STRICTLY SHARPER than the prior `NoTangentialLineReynoldsDefect`
but does NOT close NS Clay.

## Why helicity-dark is open: GPT-5.5's countermodel

Plane-wave packet
  `u_N(x) = a · τ · φ(x) · cos(N · k · x)`,  with `τ · k = 0`
has:
  * `ω_N ≈ -aN(τ × k) φ(x) sin(N k · x)`
  * `u_N · ω_N ≈ 0`  pointwise (orthogonal at high frequency)
  * `u_N ⊗ u_N ⇀ (a²/2) τ ⊗ τ · φ²`  rank-one tangential Reynolds
    stress in the weak limit

So tangential rank-one Reynolds defects can have zero helicity
pointwise. Helicity cannot rule them out.

## Honest scope of this file

* The bound `Σ r_Q ≤ B/c` is, mathematically, the elementary
  Markov inequality `Σ a_n ≤ B AND ∀n, c·a_n ≤ b_n AND Σ b_n ≤ B`
  ⇒ `c · Σ a_n ≤ B`. Strip NS vocabulary → 2-line classical
  analysis. **The mathematical content is elementary.**
* The VALUE is **structural for the proof-campaign DAG**:
  helicity becomes a typed branch FILTER in the residual
  taxonomy, removing high-helicity flat cascades from the
  remaining obstruction.
* The new obstruction `NoHelicityDarkTangentialReynoldsDefect`
  is encoded as a Prop signature; its discharge is OPEN.
* Carriers admit all-zero inhabitants (e.g., `radius ≡ 0`);
  the value is in TYPED PLACEMENT in the DAG, not in the
  inhabitant.

This is encoded with explicit anti-laundering guards per the
`feedback_be_meta_darwin_to_self` discipline.
-/

namespace ZtareProofs.NSHelicityDichotomyDAGNode

/-! ## (1) High-helicity radius-charge bound (closes that sub-branch) -/

/-- **`HighHelicityRadiusCharge`**: typed data for the high-helicity
sub-branch closure.

Given a disjoint/bounded-overlap family of selected bad cylinders
with `|helicity Q| ≥ c · radius Q` and Cauchy-Schwarz budget
`Σ |helicity Q| ≤ B`, the radius sum is bounded:
`Σ radius Q ≤ B / c`. -/
structure HighHelicityRadiusCharge where
  /-- Per-cylinder radius (nonneg). -/
  radius : ℕ → ℝ
  radius_nonneg : ∀ n, 0 ≤ radius n
  /-- Per-cylinder local helicity (absolute value). -/
  helicity : ℕ → ℝ
  helicity_nonneg : ∀ n, 0 ≤ helicity n
  /-- Cauchy-Schwarz budget constant. -/
  B : ℝ
  B_nonneg : 0 ≤ B
  /-- Radius-charge constant. -/
  c : ℝ
  c_pos : 0 < c
  /-- Cauchy-Schwarz: Σ helicity ≤ B (over the disjoint family). -/
  helicity_finite_budget :
    ∀ I : Finset ℕ, (I.sum helicity) ≤ B
  /-- Radius-scale lower bound: c · radius ≤ helicity. -/
  radius_scale_helicity :
    ∀ n, c * radius n ≤ helicity n

/-- **Tick503 main lemma**: from the carrier, radius sums are
bounded by `B/c` on every finite subfamily. -/
theorem high_helicity_radius_packing
    (h : HighHelicityRadiusCharge) (I : Finset ℕ) :
    (I.sum h.radius) ≤ h.B / h.c := by
  have hc_pos := h.c_pos
  have hsum_le : h.c * (I.sum h.radius) ≤ I.sum h.helicity := by
    calc h.c * (I.sum h.radius)
        = I.sum (fun n => h.c * h.radius n) := by
          rw [Finset.mul_sum]
      _ ≤ I.sum h.helicity :=
          Finset.sum_le_sum (fun n _ => h.radius_scale_helicity n)
  have hbudget := h.helicity_finite_budget I
  have hsum_le_B : h.c * (I.sum h.radius) ≤ h.B :=
    le_trans hsum_le hbudget
  exact (le_div_iff₀ hc_pos).mpr (by linarith)

/-! ## (2) Helicity-dark flat cascade residual (new sharpened obstruction) -/

/-- **`HelicityDarkFlatCascadeResidual`**: typed signature for the
sharpened residual obstruction.

A flat cascade is "helicity-dark" if `|H_Q|/r_Q → 0` along the
cascade. Per GPT-5.5's analysis (after tick503's high-helicity
branch is removed), the surviving obstruction is supported on such
helicity-dark cascades — specifically the tangential rank-one
Reynolds defects produced by plane-wave packets with `τ·k = 0`.

Fields here are typed signatures, not derived theorems. The
discharge of this residual is OPEN. -/
structure HelicityDarkFlatCascadeResidual where
  /-- Per-generation radius. -/
  radius : ℕ → ℝ
  radius_nonneg : ∀ n, 0 ≤ radius n
  /-- Per-generation absolute helicity. -/
  helicity : ℕ → ℝ
  helicity_nonneg : ∀ n, 0 ≤ helicity n
  /-- Σ radius diverges (flat cascade survives). -/
  radius_not_summable : ¬ Summable radius
  /-- Σ helicity converges (helicity-dark). -/
  helicity_summable : Summable helicity
  /-- Tangentiality constraint: typed signature only. -/
  tangential_rank_one_reynolds_defect_supported : Prop
  /-- Pressure-invisible: typed signature. -/
  pressure_invisible : Prop
  /-- Beta-flat: typed signature. -/
  beta_invisible : Prop
  /-- Defect-fresh-invisible: typed signature. -/
  defect_fresh_invisible : Prop

/-! ## (3) The dichotomy theorem statement (signature) -/

/-- **Typed signature of the dichotomy**: every flat-radius branch
is EITHER closed by high-helicity radius-charge OR is a helicity-
dark cascade. This signature is the typed placement in the DAG;
its CONSTRUCTION on a given Leray-Hopf solution is open.

Discharging this Prop requires either:
* exhibiting a `HighHelicityRadiusCharge` instance for the branch
  (closes), OR
* exhibiting a `HelicityDarkFlatCascadeResidual` instance
  (sharpens to new residual).
-/
structure FlatBranchHelicityDichotomy where
  high_helicity_branch_closed_via_radius_charge : Prop
  helicity_dark_cascade_residual_open : Prop
  /-- The dichotomy: at least one alternative holds. -/
  dichotomy :
    high_helicity_branch_closed_via_radius_charge ∨
    helicity_dark_cascade_residual_open

/-! ## (4) GPT-5.5 countermodel: tangential plane-wave packet -/

/-- **GPT-5.5 plane-wave countermodel signature.**

The packet `u_N = a τ φ cos(N k · x)` with `τ · k = 0` has
`u_N · ω_N ≈ 0` pointwise but produces tangential rank-one
Reynolds stress in the weak limit. This signature records the
countermodel's existence; the actual u_N construction is in PDE
literature, not Lean. -/
structure PlaneWavePacketCountermodel where
  /-- Amplitude. -/
  a : ℝ
  /-- Frequency. -/
  N : ℝ
  /-- Tangential vector τ (1D representative). -/
  tau : ℝ
  /-- Wave vector k (1D representative). -/
  k : ℝ
  /-- Orthogonality `τ · k = 0` (1D: tau * k = 0). -/
  tangential : tau * k = 0
  /-- The packet has zero local helicity in the high-frequency
      limit (signature only). -/
  helicity_zero_pointwise : Prop
  /-- The packet produces tangential rank-one Reynolds stress
      in the weak limit (signature only). -/
  weak_limit_tangential_rank_one : Prop

/-! ## (5) Honest scope -/

/-- What this file ships and what it does not. -/
structure Tick503ScopeGuard where
  /-- (1) is real arithmetic (`high_helicity_radius_packing`):
      proved in Lean with no `Prop := True` placeholder. -/
  high_helicity_radius_charge_proved : Bool
  /-- The math content of (1) is elementary Markov. The value is
      structural placement in the proof campaign DAG. -/
  math_content_is_elementary_markov : Bool
  /-- (2) `HelicityDarkFlatCascadeResidual` has Prop signature
      fields — those are HONEST OPEN obligations, not closure. -/
  helicity_dark_residual_is_open_obligation : Bool
  /-- (3) Dichotomy is a typed signature; its construction is
      open. -/
  dichotomy_construction_is_open : Bool
  /-- (4) Plane-wave countermodel signature is a literature
      reference, NOT a Lean construction. -/
  plane_wave_countermodel_is_signature_only : Bool
  /-- Carriers admit all-zero inhabitants; the value is in DAG
      placement, not non-vacuity. -/
  carriers_admit_zero_inhabitants : Bool
  /-- This file does NOT close NS Clay. -/
  does_not_close_NS_clay : Bool

def tick503_scope : Tick503ScopeGuard :=
  { high_helicity_radius_charge_proved := true
    math_content_is_elementary_markov := true
    helicity_dark_residual_is_open_obligation := true
    dichotomy_construction_is_open := true
    plane_wave_countermodel_is_signature_only := true
    carriers_admit_zero_inhabitants := true
    does_not_close_NS_clay := true }

/-! ## Sanity-check theorems (real Lean content) -/

/-- The high-helicity carrier with c = 1, B = 1, all sequences zero
satisfies all constraints; the radius-packing bound `0 ≤ 1` is
trivial. This DEMONSTRATES the carrier admits zero inhabitants —
the value is structural placement, not non-vacuity. -/
def trivial_inhabitant : HighHelicityRadiusCharge :=
  { radius := fun _ => 0
    radius_nonneg := fun _ => le_refl 0
    helicity := fun _ => 0
    helicity_nonneg := fun _ => le_refl 0
    B := 1
    B_nonneg := by norm_num
    c := 1
    c_pos := by norm_num
    helicity_finite_budget := fun I => by
      simp [Finset.sum_const_zero]
    radius_scale_helicity := fun n => by norm_num }

/-- On the trivial inhabitant, the radius-packing bound trivially
holds: `0 ≤ 1/1 = 1`. This confirms the carrier's vacuous-
inhabit risk; the discipline acknowledges this in scope. -/
theorem trivial_inhabitant_packing_trivial :
    ∀ I : Finset ℕ, (I.sum trivial_inhabitant.radius) ≤
      trivial_inhabitant.B / trivial_inhabitant.c := by
  intro I
  exact high_helicity_radius_packing trivial_inhabitant I

end ZtareProofs.NSHelicityDichotomyDAGNode
