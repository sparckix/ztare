import Mathlib.Analysis.Meromorphic.Basic
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticMonicPolynomialRoot

/-!
# Meromorphic descent from a scaled monic analytic root

If a finite power of the puncture coordinate times a branch is the root of a
monic analytic polynomial family, the preceding Cauchy-bound kernel extends
the scaled root analytically.  Dividing by that finite coordinate power then
constructs a meromorphic germ for the original branch.
-/

namespace FormalScaledMonicMeromorphicRoot

open Filter
open scoped Topology
open FormalAnalyticMonicPolynomialRoot
open FormalAnalyticPuncturedExtension

/-- A branch together with a monic analytic root carrier for one finite
coordinate-power scaling of that branch. -/
structure ScaledMonicRootCarrier where
  branch : ℂ → ℂ
  scaleOrder : ℕ
  rootCarrier : AnalyticMonicRootCarrier
  scaled_identity : rootCarrier.branch = fun t ↦
    (t - rootCarrier.center) ^ scaleOrder * branch t

/-- The original branch is meromorphic at the carrier center. -/
theorem ScaledMonicRootCarrier.branch_meromorphicAt
    (carrier : ScaledMonicRootCarrier) :
    MeromorphicAt carrier.branch carrier.rootCarrier.center := by
  obtain ⟨extension, hscaledExtension, hextensionAnalytic⟩ :=
    carrier.rootCarrier.hasFiniteAnalyticExtension
  let coordinatePower : ℂ → ℂ := fun t ↦
    (t - carrier.rootCarrier.center) ^ carrier.scaleOrder
  have hcoordinateAnalytic : AnalyticAt ℂ coordinatePower
      carrier.rootCarrier.center := by
    dsimp [coordinatePower]
    fun_prop
  have hproductMeromorphic : MeromorphicAt
      (coordinatePower⁻¹ * extension) carrier.rootCarrier.center :=
    hcoordinateAnalytic.meromorphicAt.inv.mul
      hextensionAnalytic.meromorphicAt
  have hbranch : carrier.branch =ᶠ[𝓝[≠] carrier.rootCarrier.center]
      coordinatePower⁻¹ * extension := by
    filter_upwards [hscaledExtension, self_mem_nhdsWithin] with t ht htc
    have hne : coordinatePower t ≠ 0 := by
      apply pow_ne_zero
      exact sub_ne_zero.mpr htc
    have hscaled : coordinatePower t * carrier.branch t = extension t := by
      calc
        coordinatePower t * carrier.branch t = carrier.rootCarrier.branch t := by
          rw [carrier.scaled_identity]
        _ = extension t := ht
    change carrier.branch t = (coordinatePower t)⁻¹ * extension t
    rw [← hscaled]
    field_simp
  exact hproductMeromorphic.congr hbranch.symm

/-- Aggregated scaled-root meromorphicity surface. -/
theorem scaled_monic_meromorphic_root_terminal_certificate :
    ∀ carrier : ScaledMonicRootCarrier,
      MeromorphicAt carrier.branch carrier.rootCarrier.center := by
  intro carrier
  exact carrier.branch_meromorphicAt

end FormalScaledMonicMeromorphicRoot
