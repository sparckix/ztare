import ZtareProofs.ns_trackb_krf_master_assembly
import ZtareProofs.ns_trackb_krf_mollifier_rate

/-!
# KRF Phase-A source bridge

This file connects the actual KRF Phase-A companion theorem
`mollifier_rate_uniform` to the row-20 source currency used by
`ns_trackb_krf_master_assembly`.

The master assembly remains generic over a two-index `smoothAt` family.  This
module specializes that family to the concrete Nat-indexed mollifier family
`Φ.kernel volume k ⋆ f n`, then routes the ambient-volume one-sided estimate
through the checked restricted-interval adapter.
-/

namespace ZtareProofs.NS.KRFMaster

open ZtareProofs.NS.KRFMollifierRate
open MeasureTheory
open scoped Convolution

/-- The actual Nat/`atTop` `mollifier_rate_uniform` source theorem supplies the
row-20 real-epsilon uniform scale approximation source for the concrete
convolution family, once the restricted measurability of the convolution error
is available. -/
theorem UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_nat_atTop
    {T : ℝ} (Φ : MollifierFamily ℝ ℕ Filter.atTop)
    {f : ℕ → ℝ → ℝ}
    (hf_meas : ∀ n, AEStronglyMeasurable (f n) MeasureTheory.volume)
    (hf_memLp : ∀ n, MemLp (f n) 2 MeasureTheory.volume)
    (hf_unif : TranslationEquicontinuousL2 ℝ MeasureTheory.volume f)
    (hRestrictMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            (Φ.kernel MeasureTheory.volume k ⋆[
              ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t - f n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T))) :
    UniformScaleApproximationELpNormRealOutput T f
      (fun k n t =>
        (Φ.kernel MeasureTheory.volume k ⋆[
          ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t) := by
  have hGlobalRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in Filter.atTop,
          ∀ n,
            eLpNorm
              (fun t =>
                (Φ.kernel MeasureTheory.volume k ⋆[
                  ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t - f n t)
              2 MeasureTheory.volume <
              ENNReal.ofReal ε := by
    intro ε hε
    simpa [Filter.eventually_atTop] using
      mollifier_rate_uniform Φ hf_meas hf_memLp hf_unif ε hε
  exact UniformScaleApproximationELpNormRealOutput_of_one_sided_global_rate
    hRestrictMeas
    hGlobalRate

/-- Variant of
`UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_nat_atTop`
whose measurability source is paid on the ambient measure.  The restricted
interval measurability required by the row-20 source contract is then supplied
by `AEStronglyMeasurable.restrict`. -/
theorem UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_nat_atTop_global_meas
    {T : ℝ} (Φ : MollifierFamily ℝ ℕ Filter.atTop)
    {f : ℕ → ℝ → ℝ}
    (hf_meas : ∀ n, AEStronglyMeasurable (f n) MeasureTheory.volume)
    (hf_memLp : ∀ n, MemLp (f n) 2 MeasureTheory.volume)
    (hf_unif : TranslationEquicontinuousL2 ℝ MeasureTheory.volume f)
    (hGlobalErrorMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            (Φ.kernel MeasureTheory.volume k ⋆[
              ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t - f n t)
          MeasureTheory.volume) :
    UniformScaleApproximationELpNormRealOutput T f
      (fun k n t =>
        (Φ.kernel MeasureTheory.volume k ⋆[
          ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t) := by
  exact UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_nat_atTop
    Φ
    hf_meas
    hf_memLp
    hf_unif
    (fun k n => (hGlobalErrorMeas k n).restrict)

/-- The concrete mollifier convolution term is ambient-measurable when the
unsmoothed function is locally integrable.  This uses the Mathlib theorem that a
compactly supported continuous left factor convolved with a locally integrable
right factor is continuous. -/
theorem aestronglyMeasurable_mollifier_convolution_of_locallyIntegrable
    (Φ : MollifierFamily ℝ ℕ Filter.atTop)
    {f : ℕ → ℝ → ℝ}
    (hf_loc : ∀ n, LocallyIntegrable (f n) MeasureTheory.volume) :
    ∀ k n : ℕ,
      AEStronglyMeasurable
        (fun t =>
          (Φ.kernel MeasureTheory.volume k ⋆[
            ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t)
        MeasureTheory.volume := by
  intro k n
  have hKernelCompact :
      HasCompactSupport (Φ.kernel MeasureTheory.volume k) := by
    simpa [MollifierFamily.kernel] using
      (Φ.bump k).hasCompactSupport_normed (μ := MeasureTheory.volume)
  have hKernelContinuous :
      Continuous (Φ.kernel MeasureTheory.volume k) := by
    simpa [MollifierFamily.kernel] using
      (Φ.bump k).continuous_normed (μ := MeasureTheory.volume)
  exact
    (hKernelCompact.continuous_convolution_left
      (L := ContinuousLinearMap.lsmul ℝ ℝ)
      hKernelContinuous
      (hf_loc n)).aestronglyMeasurable

/-- Ambient measurability of the concrete convolution error follows from
ambient measurability of the convolution term and of the unsmoothed function. -/
theorem aestronglyMeasurable_mollifier_convolution_error_of_convolution
    (Φ : MollifierFamily ℝ ℕ Filter.atTop)
    {f : ℕ → ℝ → ℝ}
    (hf_meas : ∀ n, AEStronglyMeasurable (f n) MeasureTheory.volume)
    (hConvMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            (Φ.kernel MeasureTheory.volume k ⋆[
              ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t)
          MeasureTheory.volume) :
    ∀ k n : ℕ,
      AEStronglyMeasurable
        (fun t =>
          (Φ.kernel MeasureTheory.volume k ⋆[
            ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t - f n t)
        MeasureTheory.volume := by
  intro k n
  exact (hConvMeas k n).sub (hf_meas n)

/-- The existing selected-family `MemLp` source at exponent two supplies the
local integrability required by the convolution-continuity theorem. -/
theorem locallyIntegrable_of_memLp_two_volume
    {f : ℕ → ℝ → ℝ}
    (hf_memLp : ∀ n, MemLp (f n) 2 MeasureTheory.volume) :
    ∀ n, LocallyIntegrable (f n) MeasureTheory.volume := by
  intro n
  exact (hf_memLp n).locallyIntegrable (by norm_num)

/-- Local integrability of the unsmoothed family supplies the global
convolution-error measurability source needed by the Nat/`atTop` mollifier-rate
bridge. -/
theorem UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_locallyIntegrable
    {T : ℝ} (Φ : MollifierFamily ℝ ℕ Filter.atTop)
    {f : ℕ → ℝ → ℝ}
    (hf_meas : ∀ n, AEStronglyMeasurable (f n) MeasureTheory.volume)
    (hf_memLp : ∀ n, MemLp (f n) 2 MeasureTheory.volume)
    (hf_unif : TranslationEquicontinuousL2 ℝ MeasureTheory.volume f)
    (hf_loc : ∀ n, LocallyIntegrable (f n) MeasureTheory.volume) :
    UniformScaleApproximationELpNormRealOutput T f
      (fun k n t =>
        (Φ.kernel MeasureTheory.volume k ⋆[
          ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t) := by
  have hConvMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            (Φ.kernel MeasureTheory.volume k ⋆[
              ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t)
          MeasureTheory.volume :=
    aestronglyMeasurable_mollifier_convolution_of_locallyIntegrable
      Φ
      hf_loc
  have hGlobalErrorMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            (Φ.kernel MeasureTheory.volume k ⋆[
              ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t - f n t)
          MeasureTheory.volume :=
    aestronglyMeasurable_mollifier_convolution_error_of_convolution
      Φ
      hf_meas
      hConvMeas
  exact UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_nat_atTop_global_meas
    Φ
    hf_meas
    hf_memLp
    hf_unif
    hGlobalErrorMeas

/-- The selected-family `MemLp` hypothesis already pays the local integrability
source needed for concrete mollifier convolution-error measurability. -/
theorem UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_memLp
    {T : ℝ} (Φ : MollifierFamily ℝ ℕ Filter.atTop)
    {f : ℕ → ℝ → ℝ}
    (hf_meas : ∀ n, AEStronglyMeasurable (f n) MeasureTheory.volume)
    (hf_memLp : ∀ n, MemLp (f n) 2 MeasureTheory.volume)
    (hf_unif : TranslationEquicontinuousL2 ℝ MeasureTheory.volume f) :
    UniformScaleApproximationELpNormRealOutput T f
      (fun k n t =>
        (Φ.kernel MeasureTheory.volume k ⋆[
          ContinuousLinearMap.lsmul ℝ ℝ, MeasureTheory.volume] f n) t) := by
  exact UniformScaleApproximationELpNormRealOutput_of_mollifier_rate_uniform_locallyIntegrable
    Φ
    hf_meas
    hf_memLp
    hf_unif
    (locallyIntegrable_of_memLp_two_volume hf_memLp)

end ZtareProofs.NS.KRFMaster
