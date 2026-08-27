import Mathlib.Analysis.Normed.Field.Lemmas
import Mathlib.Tactic

/-!
# Reciprocal convergence at norm escape

Norm escape of a trajectory in a nontrivially normed field forces eventual
nonvanishing and sends the reciprocal trajectory to zero.  The source filter
is arbitrary, so the theorem applies to one-sided finite endpoints, paths,
sequences, and other continuation filters without changing its statement.
-/

namespace FormalNormEscapeReciprocalLimit

open Bornology Filter
open scoped Topology

/-- The exact output obtained by changing from an escaping affine coordinate
to its reciprocal coordinate. -/
def NormEscapeReciprocalOutcome
    {ι 𝕜 : Type*} [NontriviallyNormedField 𝕜]
    (source : Filter ι) (trajectory : ι → 𝕜) : Prop :=
  (∀ᶠ index in source, trajectory index ≠ 0) ∧
    Tendsto (fun index ↦ (trajectory index)⁻¹) source (𝓝 0)

/-- Norm escape alone constructs eventual nonvanishing and reciprocal
convergence to zero. -/
theorem normEscapeReciprocalOutcome
    {ι 𝕜 : Type*} [NontriviallyNormedField 𝕜]
    {source : Filter ι} {trajectory : ι → 𝕜}
    (hnorm : Tendsto (fun index ↦ ‖trajectory index‖) source atTop) :
    NormEscapeReciprocalOutcome source trajectory := by
  have hnonzero : ∀ᶠ index in source, trajectory index ≠ 0 := by
    have hlarge : ∀ᶠ index in source, (1 : ℝ) ≤ ‖trajectory index‖ :=
      hnorm.eventually_ge_atTop 1
    filter_upwards [hlarge] with index hindex
    intro hzero
    simp only [hzero, norm_zero] at hindex
    norm_num at hindex
  have hcobounded : Tendsto trajectory source (cobounded 𝕜) :=
    tendsto_norm_atTop_iff_cobounded.mp hnorm
  have hreciprocal :
      Tendsto (fun index ↦ (trajectory index)⁻¹) source (𝓝 0) := by
    simpa only [Function.comp_apply] using
      tendsto_inv₀_cobounded.comp hcobounded
  exact ⟨hnonzero, hreciprocal⟩

/-- Aggregated substrate-neutral reciprocal endpoint terminal. -/
theorem norm_escape_reciprocal_limit_terminal_certificate :
    ∀ {ι 𝕜 : Type*} [NontriviallyNormedField 𝕜]
      (source : Filter ι) (trajectory : ι → 𝕜),
      Tendsto (fun index ↦ ‖trajectory index‖) source atTop →
      NormEscapeReciprocalOutcome source trajectory := by
  intro ι 𝕜 _ source trajectory hnorm
  exact normEscapeReciprocalOutcome hnorm

end FormalNormEscapeReciprocalLimit
