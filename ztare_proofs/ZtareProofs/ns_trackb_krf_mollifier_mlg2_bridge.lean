import Mathlib.MeasureTheory.Function.LpSeminorm.LpNorm
import ZtareProofs.SQ3.MLG_2_eLpNorm_convolution_sub_le
import ZtareProofs.ns_trackb_krf_arzela_ascoli_step
import ZtareProofs.ns_trackb_krf_master_assembly
import ZtareProofs.ns_trackb_krf_mollifier_rate

/-!
# KRF mollifier bridge through paid MLG-2 Phase-A infrastructure

This file connects the concrete KRF `MollifierFamily` surface to the checked
p=2 real-line mollifier theorem in `SQ3.MLG_2_eLpNorm_convolution_sub_le`.

It pays the pointwise approximate-identity theorem for any single `L²`
function.  It does not claim the uniform-in-family KRF Phase-A rate needed by
the full Kolmogorov--Riesz--Frechet compactness theorem; that remains the
next Clay-facing uniformity gap.
-/

open MeasureTheory Filter Topology
open scoped Convolution

namespace ZtareProofs.NS.KRFMollifierMLG2Bridge

noncomputable section

open ZtareProofs.SQ3.MLG2
open ZtareProofs.NS.AubinLions
open ZtareProofs.NS.KRFMollifierRate
open ZtareProofs.NS.KRFMaster

universe v

/-- Uniform near/far concentration for a family of translation moduli.

This is the uniform-family analogue of
`mollifier_concentration_near_far_enorm_real`: the small-shift hypothesis is
uniform in `n`, and the far-field bound is a single finite `M` for every
`n,y`.  It is the source lemma needed before a KRF Phase-A uniform mollifier
rate can be obtained from the paid pointwise MLG-2 machinery. -/
theorem mollifier_concentration_near_far_enorm_real_uniform
    {ι : Type*} {l : Filter ι} {w : ι → ℝ → ENNReal}
    {ω : ℕ → ℝ → ENNReal} {M B : ENNReal}
    (hω_small :
      ∀ η : ENNReal, 0 < η →
        ∃ δ : ℝ, 0 < δ ∧ ∀ n y, ‖y‖ < δ → ω n y ≤ η)
    (hω_bound : ∀ (n : ℕ) (y : ℝ), ω n y ≤ M)
    (hM_ne_top : M ≠ ⊤)
    (h_mass_bound : ∀ᶠ i in l, (∫⁻ y : ℝ, w i y ∂volume) ≤ B)
    (hB_ne_top : B ≠ ⊤)
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, w i y ∂volume)
          l (𝓝 0)) :
    ∀ ε : ℝ, 0 < ε →
      ∀ᶠ i in l,
        ∀ n,
          (∫⁻ y : ℝ, w i y * ω n y ∂volume) < ENNReal.ofReal ε := by
  intro ε hε
  let ε₀ : ENNReal := ENNReal.ofReal (ε / 2)
  have hε₀_pos : 0 < ε₀ := by
    exact ENNReal.ofReal_pos.mpr (half_pos hε)
  have hε₀_ne_top : ε₀ ≠ ⊤ := by
    exact ENNReal.ofReal_ne_top
  have hε₀_ne_zero : ε₀ ≠ 0 := ne_of_gt hε₀_pos
  let C : ℝ := max B.toReal M.toReal + 1
  have hC_pos : 0 < C := by
    dsimp [C]
    linarith [(ENNReal.toReal_nonneg : 0 ≤ B.toReal),
      le_max_left B.toReal M.toReal]
  have hε₀_toReal_pos : 0 < ε₀.toReal :=
    ENNReal.toReal_pos hε₀_ne_zero hε₀_ne_top
  let ηR : ℝ := ε₀.toReal / (2 * C)
  let η : ENNReal := ENNReal.ofReal ηR
  let q : ENNReal := ENNReal.ofReal (ε₀.toReal / 2)
  have hηR_pos : 0 < ηR := by
    dsimp [ηR]
    exact div_pos hε₀_toReal_pos (mul_pos (by norm_num) hC_pos)
  have hη_pos : 0 < η := by
    exact ENNReal.ofReal_pos.mpr hηR_pos
  have hη_ne_top : η ≠ ⊤ := by
    exact ENNReal.ofReal_ne_top
  have hB_le_C : B ≤ ENNReal.ofReal C := by
    calc
      B = ENNReal.ofReal B.toReal := (ENNReal.ofReal_toReal hB_ne_top).symm
      _ ≤ ENNReal.ofReal C := by
        apply ENNReal.ofReal_le_ofReal
        dsimp [C]
        exact le_trans (le_max_left _ _) (by linarith)
  have hM_le_C : M ≤ ENNReal.ofReal C := by
    calc
      M = ENNReal.ofReal M.toReal := (ENNReal.ofReal_toReal hM_ne_top).symm
      _ ≤ ENNReal.ofReal C := by
        apply ENNReal.ofReal_le_ofReal
        dsimp [C]
        exact le_trans (le_max_right _ _) (by linarith)
  have hη_mul_C : η * ENNReal.ofReal C = q := by
    rw [← ENNReal.ofReal_mul (le_of_lt hηR_pos)]
    congr 1
    dsimp [ηR, q]
    field_simp [ne_of_gt hC_pos]
  have hBη_le_q : B * η ≤ q := by
    calc
      B * η ≤ ENNReal.ofReal C * η := mul_le_mul_left hB_le_C η
      _ = η * ENNReal.ofReal C := by rw [mul_comm]
      _ = q := hη_mul_C
  have hηM_le_q : η * M ≤ q := by
    calc
      η * M ≤ η * ENNReal.ofReal C := mul_le_mul_right hM_le_C η
      _ = q := hη_mul_C
  have hq_add_q_le : q + q ≤ ε₀ := by
    have hq_add :
        q + q = ENNReal.ofReal ε₀.toReal := by
      dsimp [q]
      rw [← ENNReal.ofReal_add (by positivity : 0 ≤ ε₀.toReal / 2)
        (by positivity : 0 ≤ ε₀.toReal / 2)]
      congr 1
      ring
    rw [hq_add, ENNReal.ofReal_toReal hε₀_ne_top]
  have hε₀_lt : ε₀ < ENNReal.ofReal ε := by
    dsimp [ε₀]
    exact (ENNReal.ofReal_lt_ofReal_iff hε).2 (half_lt_self hε)
  rcases hω_small η hη_pos with ⟨δ, hδ_pos, hδ_small⟩
  let far : Set ℝ := {y : ℝ | δ ≤ ‖y‖}
  have hfar_meas : MeasurableSet far := by
    dsimp [far]
    exact (isClosed_le continuous_const continuous_norm).measurableSet
  have hnear_small : ∀ n y, y ∈ farᶜ → ω n y ≤ η := by
    intro n y hy
    have hy_lt : ‖y‖ < δ := by
      simpa [far] using hy
    exact hδ_small n y hy_lt
  have htail_eventually :
      ∀ᶠ i in l, (∫⁻ y in far, w i y ∂volume) ≤ η := by
    have htailη :=
      (ENNReal.tendsto_nhds_zero.1 (h_tail δ hδ_pos)) η hη_pos
    simpa [far] using htailη
  filter_upwards [h_mass_bound, htail_eventually] with i hmass htail_i n
  have hnear_bound :
      (∫⁻ y in farᶜ, w i y * ω n y ∂volume) ≤ q := by
    calc
      (∫⁻ y in farᶜ, w i y * ω n y ∂volume)
          ≤ ∫⁻ y in farᶜ, w i y * η ∂volume := by
            exact setLIntegral_mono' hfar_meas.compl
              (fun y hy => mul_le_mul_right (hnear_small n y hy) (w i y))
      _ ≤ ∫⁻ y : ℝ, w i y * η ∂volume := setLIntegral_le_lintegral farᶜ _
      _ = (∫⁻ y : ℝ, w i y ∂volume) * η := by
            rw [lintegral_mul_const' η (fun y : ℝ => w i y) hη_ne_top]
      _ ≤ B * η := mul_le_mul_left hmass η
      _ ≤ q := hBη_le_q
  have hfar_bound :
      (∫⁻ y in far, w i y * ω n y ∂volume) ≤ q := by
    have htailM_le : (∫⁻ y in far, w i y ∂volume) * M ≤ η * M :=
      mul_le_mul_left htail_i M
    calc
      (∫⁻ y in far, w i y * ω n y ∂volume)
          ≤ ∫⁻ y in far, w i y * M ∂volume := by
            exact setLIntegral_mono' hfar_meas
              (fun y _hy => mul_le_mul_right (hω_bound n y) (w i y))
      _ = (∫⁻ y in far, w i y ∂volume) * M := by
            rw [lintegral_mul_const' M (fun y : ℝ => w i y) hM_ne_top]
      _ ≤ η * M := htailM_le
      _ ≤ q := hηM_le_q
  have hsum :
      (∫⁻ y : ℝ, w i y * ω n y ∂volume) ≤ ε₀ := by
    calc
      (∫⁻ y : ℝ, w i y * ω n y ∂volume)
          = (∫⁻ y in far, w i y * ω n y ∂volume) +
              (∫⁻ y in farᶜ, w i y * ω n y ∂volume) := by
            exact (lintegral_add_compl (fun y : ℝ => w i y * ω n y)
              hfar_meas).symm
      _ ≤ q + q := add_le_add hfar_bound hnear_bound
      _ ≤ ε₀ := hq_add_q_le
  exact lt_of_le_of_lt hsum hε₀_lt

/-- Uniform RHS convergence from KRF-style translation equicontinuity.

This turns `TranslationEquicontinuousL2` plus a finite uniform far-field bound
into the exact real-epsilon RHS estimate used by the p=2 MLG-2 convolution
rate theorem.  The bound hypothesis is intentionally explicit: pointwise
`MemLp` alone is not enough to control the far field uniformly in `n`. -/
theorem eLpNorm_two_real_mollifier_rhs_uniform_of_near_far
    {ι : Type*} {l : Filter ι} {ρ : ι → ℝ → ℝ}
    {f : ℕ → ℝ → ℝ} {M B : ENNReal}
    (hf_unif : TranslationEquicontinuousL2 ℝ (volume : Measure ℝ) f)
    (h_bound :
      ∀ (n : ℕ) (y : ℝ),
        eLpNorm (fun x : ℝ => f n (x - y) - f n x)
          p2 (volume : Measure ℝ) ≤ M)
    (hM_ne_top : M ≠ ⊤)
    (h_mass_bound :
      ∀ᶠ i in l, (∫⁻ y : ℝ, ‖ρ i y‖ₑ ∂volume) ≤ B)
    (hB_ne_top : B ≠ ⊤)
    (h_tail :
      ∀ δ : ℝ, 0 < δ →
        Tendsto
          (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
          l (𝓝 0)) :
    ∀ ε : ℝ, 0 < ε →
      ∀ᶠ i in l,
        ∀ n,
          (∫⁻ y : ℝ, ‖ρ i y‖ₑ *
            eLpNorm (fun x : ℝ => f n (x - y) - f n x)
              p2 (volume : Measure ℝ) ∂volume) < ENNReal.ofReal ε := by
  refine mollifier_concentration_near_far_enorm_real_uniform
    (w := fun i y => ‖ρ i y‖ₑ)
    (ω := fun n y =>
      eLpNorm (fun x : ℝ => f n (x - y) - f n x)
        p2 (volume : Measure ℝ))
    ?small h_bound hM_ne_top h_mass_bound hB_ne_top h_tail
  intro η hη
  by_cases hη_top : η = ⊤
  · refine ⟨1, by norm_num, ?_⟩
    intro n y _hy
    simp [hη_top]
  · have hη_ne_zero : η ≠ 0 := ne_of_gt hη
    let εR : ℝ := η.toReal / 2
    have hεR_pos : 0 < εR := by
      exact half_pos (ENNReal.toReal_pos hη_ne_zero hη_top)
    rcases hf_unif εR hεR_pos with ⟨U, hU_nhds, hU⟩
    rcases Metric.mem_nhds_iff.1 hU_nhds with ⟨δ, hδ_pos, hδ_subset⟩
    refine ⟨δ, hδ_pos, ?_⟩
    intro n y hy
    have hneg_mem : -y ∈ U := by
      apply hδ_subset
      simpa [Metric.mem_ball, dist_eq_norm] using hy
    have hsmall := hU n (-y) hneg_mem
    have htarget :
        eLpNorm (fun x : ℝ => f n (x - y) - f n x)
          p2 (volume : Measure ℝ) < ENNReal.ofReal εR := by
      simpa [p2, sub_eq_add_neg] using hsmall
    exact le_trans (le_of_lt htarget) (by
      have hεR_le : ENNReal.ofReal εR ≤ η := by
        have hlt : ENNReal.ofReal εR < ENNReal.ofReal η.toReal := by
          rw [ENNReal.ofReal_lt_ofReal_iff
            (ENNReal.toReal_pos hη_ne_zero hη_top)]
          exact half_lt_self (ENNReal.toReal_pos hη_ne_zero hη_top)
        exact le_of_lt (by
          simpa [εR, ENNReal.ofReal_toReal hη_top] using hlt)
      exact hεR_le)

/-- A uniform `L²` envelope gives the far-field bound required by the uniform
near/far split. -/
theorem eLpNorm_two_translate_diff_le_real_of_uniform_eLpNorm_bound
    {f : ℕ → ℝ → ℝ} {A : ENNReal}
    (hf_memLp : ∀ n, MemLp (f n) p2 (volume : Measure ℝ))
    (hA : ∀ n, eLpNorm (f n) p2 (volume : Measure ℝ) ≤ A) :
    ∀ (n : ℕ) (y : ℝ),
      eLpNorm (fun x : ℝ => f n (x - y) - f n x)
        p2 (volume : Measure ℝ) ≤ A + A := by
  intro n y
  calc
    eLpNorm (fun x : ℝ => f n (x - y) - f n x)
        p2 (volume : Measure ℝ)
        ≤ eLpNorm (f n) p2 (volume : Measure ℝ) +
          eLpNorm (f n) p2 (volume : Measure ℝ) := by
          simpa [p2] using
            eLpNorm_two_translate_diff_le_real_of_memLp_two (hf_memLp n) y
    _ ≤ A + A := add_le_add (hA n) (hA n)

/-- Support-radius convergence supplies tail concentration for scalar kernels.

This is the small measure-theoretic bridge from the KRF `ContDiffBump` support
radius to the near/far concentration hypothesis used by the paid p=2 MLG-2
mollifier theorem. -/
theorem tail_concentration_of_support_radius_tendsto
    {ι : Type*} {l : Filter ι} {ρ : ι → ℝ → ℝ} {r : ι → ℝ}
    (hr : Tendsto r l (𝓝 0))
    (hsupp : ∀ i, Function.support (ρ i) ⊆ Metric.ball (0 : ℝ) (r i)) :
    ∀ δ : ℝ, 0 < δ →
      Tendsto
        (fun i : ι => ∫⁻ y in {y : ℝ | δ ≤ ‖y‖}, ‖ρ i y‖ₑ ∂volume)
        l (𝓝 0) := by
  intro δ hδ
  have h_eventually_r : ∀ᶠ i in l, r i < δ := by
    exact hr.eventually (eventually_lt_nhds hδ)
  refine tendsto_const_nhds.congr' ?_
  filter_upwards [h_eventually_r] with i hi
  have hfar_meas : MeasurableSet {y : ℝ | δ ≤ ‖y‖} := by
    exact (isClosed_le continuous_const continuous_norm).measurableSet
  exact (setLIntegral_eq_zero (μ := (volume : Measure ℝ))
    (f := fun y : ℝ => ‖ρ i y‖ₑ) hfar_meas (fun y hy => by
    have hynot : y ∉ Metric.ball (0 : ℝ) (r i) := by
      intro hyball
      have hnorm_lt : ‖y‖ < r i := by
        simpa [Metric.mem_ball, dist_eq_norm] using hyball
      exact not_lt_of_ge hy (lt_trans hnorm_lt hi)
    have hρ_zero : ρ i y = 0 := by
      by_contra hne
      exact hynot (hsupp i hne)
    simp [hρ_zero])).symm

/-- Every real-line KRF `MollifierFamily` has ENNReal tail mass tending to zero
outside every fixed ball. -/
theorem tail_concentration_krf_mollifierFamily_real
    {ι : Type*} {l : Filter ι}
    (Φ : MollifierFamily ℝ ι l) :
    ∀ δ : ℝ, 0 < δ →
      Tendsto
        (fun i : ι =>
          ∫⁻ y in {y : ℝ | δ ≤ ‖y‖},
            ‖Φ.kernel (volume : Measure ℝ) i y‖ₑ ∂volume)
        l (𝓝 0) := by
  refine tail_concentration_of_support_radius_tendsto
    (ρ := fun i => Φ.kernel (volume : Measure ℝ) i)
    (r := fun i => (Φ.bump i).rOut)
    Φ.rOut_tendsto ?_
  intro i
  simpa [MollifierFamily.kernel] using
    (Φ.bump i).support_normed_eq (μ := (volume : Measure ℝ)).subset

/-- Uniform RHS convergence for a real-line KRF `MollifierFamily`.

This is the KRF-kernel specialization of the uniform near/far source.  It is
still an RHS estimate; the following theorem consumes the checked MLG-2
convolution inequality to bound the actual mollifier error. -/
theorem eLpNorm_two_real_mollifier_rhs_uniform_of_krf_mollifierFamily
    {ι : Type*} {l : Filter ι}
    (Φ : MollifierFamily ℝ ι l)
    {f : ℕ → ℝ → ℝ} {A : ENNReal}
    (hf_memLp : ∀ n, MemLp (f n) p2 (volume : Measure ℝ))
    (hf_unif : TranslationEquicontinuousL2 ℝ (volume : Measure ℝ) f)
    (hA : ∀ n, eLpNorm (f n) p2 (volume : Measure ℝ) ≤ A)
    (hA_ne_top : A ≠ ⊤) :
    ∀ ε : ℝ, 0 < ε →
      ∀ᶠ i in l,
        ∀ n,
          (∫⁻ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) i y‖ₑ *
            eLpNorm (fun x : ℝ => f n (x - y) - f n x)
              p2 (volume : Measure ℝ) ∂volume) < ENNReal.ofReal ε := by
  refine eLpNorm_two_real_mollifier_rhs_uniform_of_near_far
    (ρ := fun i => Φ.kernel (volume : Measure ℝ) i)
    (M := A + A) (B := 1)
    hf_unif
    (eLpNorm_two_translate_diff_le_real_of_uniform_eLpNorm_bound
      hf_memLp hA)
    ?hM_ne_top ?hmass ?hB_ne_top
    (tail_concentration_krf_mollifierFamily_real Φ)
  · exact ENNReal.add_ne_top.2 ⟨hA_ne_top, hA_ne_top⟩
  · exact mollifier_total_mass_bound_one_of_nonneg_unit
      (hρ_int := fun i =>
        (Φ.bump i).integrable_normed (μ := (volume : Measure ℝ)))
      (hρ_nonneg := fun i y =>
        (Φ.bump i).nonneg_normed (μ := (volume : Measure ℝ)) y)
      (hρ_one := fun i =>
        (Φ.bump i).integral_normed (μ := (volume : Measure ℝ)))
  · simp

/-- Uniform real-line KRF Phase-A approximation in p=2 `eLpNorm`.

This is the paid uniform-family analogue of the pointwise theorem below, under
the explicit KRF sources that make the near/far proof valid: translation
equicontinuity and a finite uniform `L²` envelope for the family. -/
theorem eLpNorm_two_real_mollifier_error_uniform_of_krf_mollifierFamily
    {ι : Type*} {l : Filter ι}
    (Φ : MollifierFamily ℝ ι l)
    {f : ℕ → ℝ → ℝ} {A : ENNReal}
    (hf_memLp : ∀ n, MemLp (f n) p2 (volume : Measure ℝ))
    (hf_unif : TranslationEquicontinuousL2 ℝ (volume : Measure ℝ) f)
    (hA : ∀ n, eLpNorm (f n) p2 (volume : Measure ℝ) ≤ A)
    (hA_ne_top : A ≠ ⊤) :
    ∀ ε : ℝ, 0 < ε →
      ∀ᶠ i in l,
        ∀ n,
          eLpNorm
            (fun x : ℝ =>
              (∫ y, Φ.kernel (volume : Measure ℝ) i y • f n (x - y) ∂volume)
                - f n x)
            p2 (volume : Measure ℝ) < ENNReal.ofReal ε := by
  intro ε hε
  filter_upwards
    [eLpNorm_two_real_mollifier_rhs_uniform_of_krf_mollifierFamily
      Φ hf_memLp hf_unif hA hA_ne_top ε hε] with i hi n
  exact lt_of_le_of_lt
    (eLpNorm_two_convolution_sub_le_lintegral_translate_diff_real
      ((Φ.bump i).continuous_normed (μ := (volume : Measure ℝ)))
      ((Φ.bump i).hasCompactSupport_normed (μ := (volume : Measure ℝ)))
      ((Φ.bump i).integrable_normed (μ := (volume : Measure ℝ)))
      ((Φ.bump i).integral_normed (μ := (volume : Measure ℝ)))
      (hf_memLp n))
    (hi n)

/-- The paid MLG-2 uniform Phase-A theorem supplies the KRF master real-epsilon
uniform scale contract for the integral-form smoothing family.

The only remaining side condition is the restricted measurability of the
smoothed error, kept explicit because downstream KRF files already isolate that
as a separate source obligation. -/
theorem UniformScaleApproximationELpNormRealOutput_of_mlg2_krf_mollifierFamily
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {f : ℕ → ℝ → ℝ} {A : ENNReal}
    (hMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            (∫ y, Φ.kernel (volume : Measure ℝ) k y • f n (t - y) ∂volume) -
              f n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hf_memLp : ∀ n, MemLp (f n) p2 (volume : Measure ℝ))
    (hf_unif : TranslationEquicontinuousL2 ℝ (volume : Measure ℝ) f)
    (hA : ∀ n, eLpNorm (f n) p2 (volume : Measure ℝ) ≤ A)
    (hA_ne_top : A ≠ ⊤) :
    UniformScaleApproximationELpNormRealOutput T f
      (fun k n t =>
        ∫ y, Φ.kernel (volume : Measure ℝ) k y • f n (t - y) ∂volume) := by
  refine UniformScaleApproximationELpNormRealOutput_of_one_sided_global_rate
    (u := f)
    (smoothAt := fun k n t =>
      ∫ y, Φ.kernel (volume : Measure ℝ) k y • f n (t - y) ∂volume)
    hMeas ?_
  intro ε hε
  simpa [p2] using
    eLpNorm_two_real_mollifier_error_uniform_of_krf_mollifierFamily
      Φ hf_memLp hf_unif hA hA_ne_top ε hε

/-- Concrete `MollifierFamily` smoothing on the real line, in the integral
form consumed by the KRF Phase-A and Arzelà/Cantor source contracts. -/
def mollifierFamilySmoothAt
    {B : Type v} [NormedAddCommGroup B] [NormedSpace ℝ B]
    [CompleteSpace B]
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → B)
    (k n : ℕ) (t : ℝ) : B :=
  ∫ y, Φ.kernel (volume : Measure ℝ) k y • u n (t - y) ∂volume

/-- Fixed-scale continuity of the concrete real-valued KRF mollifier integral
from local integrability of the unsmoothed function.

This is the API bridge from Mathlib's convolution-continuity theorem to the
integral form `mollifierFamilySmoothAt` used by the KRF/Arzelà source
contracts. -/
theorem continuous_mollifierFamilySmoothAt_of_locallyIntegrable
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (hu_loc : ∀ n, LocallyIntegrable (u n) volume) :
    ∀ k n : ℕ,
      Continuous (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) := by
  intro k n
  have hKernelCompact :
      HasCompactSupport (Φ.kernel (volume : Measure ℝ) k) := by
    simpa [MollifierFamily.kernel] using
      (Φ.bump k).hasCompactSupport_normed (μ := volume)
  have hKernelContinuous :
      Continuous (Φ.kernel (volume : Measure ℝ) k) := by
    simpa [MollifierFamily.kernel] using
      (Φ.bump k).continuous_normed (μ := volume)
  have hConv :
      Continuous
        ((Φ.kernel (volume : Measure ℝ) k) ⋆[
          ContinuousLinearMap.lsmul ℝ ℝ, volume] u n) :=
    hKernelCompact.continuous_convolution_left
      (L := ContinuousLinearMap.lsmul ℝ ℝ)
      hKernelContinuous
      (hu_loc n)
  simpa [mollifierFamilySmoothAt, convolution_lsmul] using hConv

/-- Fixed-scale continuity of the concrete KRF mollifier integral from the
selected-family `L²` source. -/
theorem continuous_mollifierFamilySmoothAt_of_memLp_two_volume
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ)) :
    ∀ k n : ℕ,
      Continuous (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) := by
  exact continuous_mollifierFamilySmoothAt_of_locallyIntegrable
    Φ
    (fun n => (hu_memLp n).locallyIntegrable (by norm_num [p2]))

/-- Fixed-scale scalar pointwise bound for the KRF mollifier integral from
explicit `L²` hypotheses on the kernel and shifted source.

This is the Cauchy--Schwarz/Hölder source lemma needed before the analytic
KRF hypotheses can supply a uniform pointwise envelope. -/
theorem abs_mollifierFamilySmoothAt_le_l2_norm_integrals
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (k n : ℕ) (t : ℝ)
    (hρ : MemLp (Φ.kernel (volume : Measure ℝ) k) p2 (volume : Measure ℝ))
    (hu : MemLp (fun y : ℝ => u n (t - y)) p2 (volume : Measure ℝ)) :
    |mollifierFamilySmoothAt Φ u k n t| ≤
      (∫ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) k y‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) *
        (∫ y : ℝ, ‖u n (t - y)‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) := by
  calc
    |mollifierFamilySmoothAt Φ u k n t|
        = ‖∫ y : ℝ, Φ.kernel (volume : Measure ℝ) k y • u n (t - y) ∂volume‖ := by
          simp [mollifierFamilySmoothAt, Real.norm_eq_abs]
    _ ≤ ∫ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) k y • u n (t - y)‖ ∂volume :=
          norm_integral_le_integral_norm
            (fun y : ℝ => Φ.kernel (volume : Measure ℝ) k y • u n (t - y))
    _ = ∫ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) k y‖ * ‖u n (t - y)‖ ∂volume := by
          simp
    _ ≤ (∫ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) k y‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) *
          (∫ y : ℝ, ‖u n (t - y)‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) := by
          simpa [p2] using
            (integral_mul_norm_le_Lp_mul_Lq
              (μ := (volume : Measure ℝ))
              Real.HolderConjugate.two_two hρ hu)

/-- The fixed KRF mollifier kernel is in `L²`, since it is continuous with
compact support. -/
theorem mollifierFamily_kernel_memLp_two_volume
    (Φ : MollifierFamily ℝ ℕ atTop) (k : ℕ) :
    MemLp (Φ.kernel (volume : Measure ℝ) k) p2 (volume : Measure ℝ) := by
  simpa [MollifierFamily.kernel] using
    ((Φ.bump k).continuous_normed (μ := (volume : Measure ℝ))).memLp_of_hasCompactSupport
      ((Φ.bump k).hasCompactSupport_normed (μ := (volume : Measure ℝ)))

/-- Real-line subtraction preserves the `L²` source hypothesis used by the
fixed-scale pointwise mollifier bound. -/
theorem shifted_memLp_two_volume_of_memLp_two_volume
    {u : ℝ → ℝ} (hu : MemLp u p2 (volume : Measure ℝ)) (t : ℝ) :
    MemLp (fun y : ℝ => u (t - y)) p2 (volume : Measure ℝ) := by
  simpa [Function.comp_def] using
    hu.comp_measurePreserving (volume.measurePreserving_sub_left t)

/-- Fixed-scale scalar pointwise bound with the KRF kernel and shifted-source
`L²` hypotheses instantiated from the `MollifierFamily` structure and one
source `MemLp p=2` hypothesis. -/
theorem abs_mollifierFamilySmoothAt_le_l2_norm_integrals_of_memLp_two_volume
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (k n : ℕ) (t : ℝ)
    (hu_memLp : MemLp (u n) p2 (volume : Measure ℝ)) :
    |mollifierFamilySmoothAt Φ u k n t| ≤
      (∫ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) k y‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) *
        (∫ y : ℝ, ‖u n (t - y)‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) :=
  abs_mollifierFamilySmoothAt_le_l2_norm_integrals
    Φ u k n t
    (mollifierFamily_kernel_memLp_two_volume Φ k)
    (shifted_memLp_two_volume_of_memLp_two_volume hu_memLp t)

/-- Fixed-scale derivative formula for the concrete KRF mollifier integral.

This is the Mathlib convolution-derivative bridge for the actual
`mollifierFamilySmoothAt` API: for a fixed KRF mollifier scale, differentiating
the smoothed function differentiates the compactly supported kernel. -/
theorem hasDerivAt_mollifierFamilySmoothAt_of_locallyIntegrable
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (hu_loc : ∀ n, LocallyIntegrable (u n) volume) :
    ∀ k n : ℕ, ∀ x : ℝ,
      HasDerivAt
        (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
        (∫ y : ℝ,
          deriv (Φ.kernel (volume : Measure ℝ) k) y • u n (x - y) ∂volume)
        x := by
  intro k n x
  have hKernelCompact :
      HasCompactSupport (Φ.kernel (volume : Measure ℝ) k) := by
    simpa [MollifierFamily.kernel] using
      (Φ.bump k).hasCompactSupport_normed (μ := volume)
  have hKernelContDiff :
      ContDiff ℝ (1 : ℕ∞) (Φ.kernel (volume : Measure ℝ) k) := by
    simpa [MollifierFamily.kernel] using
      ((Φ.bump k).contDiff_normed
        (μ := (volume : Measure ℝ)) (n := (1 : ℕ∞)))
  have hConv :
      HasDerivAt
        ((Φ.kernel (volume : Measure ℝ) k) ⋆[
          ContinuousLinearMap.lsmul ℝ ℝ, volume] u n)
        (((deriv (Φ.kernel (volume : Measure ℝ) k)) ⋆[
          ContinuousLinearMap.lsmul ℝ ℝ, volume] u n) x)
        x :=
    hKernelCompact.hasDerivAt_convolution_left
      (L := ContinuousLinearMap.lsmul ℝ ℝ)
      hKernelContDiff
      (hu_loc n)
      x
  simpa [mollifierFamilySmoothAt, convolution_lsmul] using hConv

/-- Fixed-scale differentiability of the concrete KRF mollifier integral. -/
theorem differentiableAt_mollifierFamilySmoothAt_of_locallyIntegrable
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (hu_loc : ∀ n, LocallyIntegrable (u n) volume) :
    ∀ k n : ℕ, ∀ x : ℝ,
      DifferentiableAt ℝ
        (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) x := by
  intro k n x
  exact
    (hasDerivAt_mollifierFamilySmoothAt_of_locallyIntegrable
      Φ hu_loc k n x).differentiableAt

/-- The derivative of a fixed KRF mollifier kernel is in `L²`.

This uses compact support of the KRF bump and Mathlib's
`ContDiff.continuous_deriv_one`; no uniform-in-scale bound is claimed. -/
theorem mollifierFamily_deriv_kernel_memLp_two_volume
    (Φ : MollifierFamily ℝ ℕ atTop) (k : ℕ) :
    MemLp (deriv (Φ.kernel (volume : Measure ℝ) k)) p2
      (volume : Measure ℝ) := by
  have hKernelCompact :
      HasCompactSupport (Φ.kernel (volume : Measure ℝ) k) := by
    simpa [MollifierFamily.kernel] using
      (Φ.bump k).hasCompactSupport_normed (μ := volume)
  have hKernelContDiff :
      ContDiff ℝ (1 : ℕ∞) (Φ.kernel (volume : Measure ℝ) k) := by
    simpa [MollifierFamily.kernel] using
      ((Φ.bump k).contDiff_normed
        (μ := (volume : Measure ℝ)) (n := (1 : ℕ∞)))
  exact
    (hKernelContDiff.continuous_deriv_one).memLp_of_hasCompactSupport
      hKernelCompact.deriv

/-- Pointwise derivative identity for the fixed-scale KRF mollifier integral. -/
theorem deriv_mollifierFamilySmoothAt_eq_integral_deriv_kernel
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (hu_loc : ∀ n, LocallyIntegrable (u n) volume)
    (k n : ℕ) (t : ℝ) :
    deriv (fun s : ℝ => mollifierFamilySmoothAt Φ u k n s) t =
      ∫ y : ℝ,
        deriv (Φ.kernel (volume : Measure ℝ) k) y • u n (t - y) ∂volume := by
  exact
    (hasDerivAt_mollifierFamilySmoothAt_of_locallyIntegrable
      Φ hu_loc k n t).deriv

/-- Fixed-scale derivative pointwise bound from explicit `L²` hypotheses on
the derivative kernel and shifted source. -/
theorem abs_deriv_mollifierFamilySmoothAt_le_l2_norm_integrals
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_loc : ∀ n, LocallyIntegrable (u n) volume)
    (k n : ℕ) (t : ℝ)
    (hρ : MemLp (deriv (Φ.kernel (volume : Measure ℝ) k)) p2
      (volume : Measure ℝ))
    (hu : MemLp (fun y : ℝ => u n (t - y)) p2
      (volume : Measure ℝ)) :
    |deriv (fun s : ℝ => mollifierFamilySmoothAt Φ u k n s) t| ≤
      (∫ y : ℝ,
        ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) *
        (∫ y : ℝ, ‖u n (t - y)‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) := by
  calc
    |deriv (fun s : ℝ => mollifierFamilySmoothAt Φ u k n s) t|
        = ‖∫ y : ℝ,
            deriv (Φ.kernel (volume : Measure ℝ) k) y • u n (t - y) ∂volume‖ := by
          rw [deriv_mollifierFamilySmoothAt_eq_integral_deriv_kernel
            Φ hu_loc k n t]
          simp [Real.norm_eq_abs]
    _ ≤ ∫ y : ℝ,
          ‖deriv (Φ.kernel (volume : Measure ℝ) k) y • u n (t - y)‖ ∂volume :=
          norm_integral_le_integral_norm
            (fun y : ℝ =>
              deriv (Φ.kernel (volume : Measure ℝ) k) y • u n (t - y))
    _ = ∫ y : ℝ,
          ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ *
            ‖u n (t - y)‖ ∂volume := by
          simp
    _ ≤ (∫ y : ℝ,
            ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) *
          (∫ y : ℝ, ‖u n (t - y)‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) := by
          simpa [p2] using
            (integral_mul_norm_le_Lp_mul_Lq
              (μ := (volume : Measure ℝ))
              Real.HolderConjugate.two_two hρ hu)

/-- Fixed-scale derivative pointwise bound with the derivative kernel and
shifted-source `L²` fields instantiated from the KRF `MollifierFamily` and
one source `MemLp p=2` hypothesis. -/
theorem abs_deriv_mollifierFamilySmoothAt_le_l2_norm_integrals_of_memLp_two_volume
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k n : ℕ) (t : ℝ) :
    |deriv (fun s : ℝ => mollifierFamilySmoothAt Φ u k n s) t| ≤
      (∫ y : ℝ,
        ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) *
        (∫ y : ℝ, ‖u n (t - y)‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2) :=
  abs_deriv_mollifierFamilySmoothAt_le_l2_norm_integrals
    Φ u
    (fun n => (hu_memLp n).locallyIntegrable (by norm_num [p2]))
    k n t
    (mollifierFamily_deriv_kernel_memLp_two_volume Φ k)
    (shifted_memLp_two_volume_of_memLp_two_volume (hu_memLp n) t)

/-- Linear lower envelope for sampled derivative costs.

This is an anti-laundering model, not a claim about the concrete
`MollifierFamily` scaling law: it isolates the elementary obstruction that a
positive-growth sampled derivative-cost source cannot be repackaged as a
single fixed-scale Lipschitz constant. -/
def sampledDerivativeCostLowerEnvelope (c : ℝ) (n : ℕ) : ℝ :=
  c * ((n : ℝ) + 1)

/-- A sampled derivative-cost source with positive linear lower growth has no
uniform upper bound.

This guards the fixed-scale derivative bridge above: a proof that pays only
the fixed `k` derivative-kernel constant cannot be silently reused for a
shrinking sampled family whose derivative cost grows along the sample index. -/
theorem not_exists_uniform_bound_of_linear_sampled_derivative_growth
    {a : ℕ → ℝ} {c : ℝ} (hc : 0 < c)
    (hgrowth : ∀ n : ℕ, c * ((n : ℝ) + 1) ≤ a n) :
    ¬ ∃ L : ℝ, ∀ n, a n ≤ L := by
  rintro ⟨L, hL⟩
  obtain ⟨n, hn⟩ := exists_nat_gt (L / c)
  have hn' : L / c < (n : ℝ) + 1 := by
    nlinarith
  have hlt : L < c * ((n : ℝ) + 1) := by
    simpa [mul_comm] using (div_lt_iff₀ hc).mp hn'
  have hchain : c * ((n : ℝ) + 1) ≤ L := le_trans (hgrowth n) (hL n)
  exact not_lt_of_ge hchain hlt

/-- The explicit linear lower envelope itself is not uniformly bounded above
when its slope is positive. -/
theorem sampledDerivativeCostLowerEnvelope_not_exists_uniform_bound
    {c : ℝ} (hc : 0 < c) :
    ¬ ∃ L : ℝ, ∀ n, sampledDerivativeCostLowerEnvelope c n ≤ L :=
  not_exists_uniform_bound_of_linear_sampled_derivative_growth
    (a := sampledDerivativeCostLowerEnvelope c)
    hc
    (fun _ => le_rfl)

/-- Convert a real absolute-value derivative bound into the `NNReal`
derivative-bound shape expected by Mathlib's Lipschitz-on-convex theorem. -/
theorem nnnorm_le_toNNReal_of_abs_le {x C : ℝ} (hx : |x| ≤ C) :
    ‖x‖₊ ≤ Real.toNNReal C := by
  simpa [nnnorm, Real.norm_eq_abs] using Real.toNNReal_le_toNNReal hx

/-- Fixed-scale interval Lipschitz source from a uniform derivative bound.

This is the Mathlib mean-value-theorem bridge for the KRF smoothing surface:
once the analytic argument supplies differentiability and a common derivative
bound on an interval, the fixed-scale mollified family is Lipschitz there with
the same constant. -/
theorem mollifierFamilySmoothAt_fixedScale_lipschitzOnWith_Icc_of_deriv_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (k : ℕ) {a b : ℝ} {L : NNReal}
    (hdiff :
      ∀ n x, x ∈ Set.Icc a b →
        DifferentiableAt ℝ
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) x)
    (hderiv :
      ∀ n x, x ∈ Set.Icc a b →
        ‖deriv (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) x‖₊ ≤ L) :
    ∀ n,
      LipschitzOnWith L
        (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
        (Set.Icc a b) := by
  intro n
  exact (convex_Icc a b).lipschitzOnWith_of_nnnorm_deriv_le
    (fun x hx => hdiff n x hx)
    (fun x hx => hderiv n x hx)

/-- Compact-wise fixed-scale Lipschitz source from interval derivative bounds.

The Arzelà contract asks for every compact `K`; on the real line it is enough
to enclose each compact in an interval and prove the common derivative bound
on that interval.  This theorem keeps the remaining source obligation explicit
and reusable. -/
theorem mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_Icc_deriv_bounds
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b : ℝ) (L : NNReal),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            DifferentiableAt ℝ
              (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) x) ∧
          (∀ n x, x ∈ Set.Icc a b →
            ‖deriv (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) x‖₊ ≤ L)) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
          K := by
  intro K hK
  rcases hsource K hK with ⟨a, b, L, hK_sub, hdiff, hderiv⟩
  refine ⟨L, fun n => ?_⟩
  exact
    (mollifierFamilySmoothAt_fixedScale_lipschitzOnWith_Icc_of_deriv_bound
      Φ u k hdiff hderiv n).mono hK_sub

/-- Compact-wise fixed-scale Lipschitz source after the KRF derivative formula
pays differentiability, leaving only the common derivative bound as an
analytic source obligation. -/
theorem mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k : ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b : ℝ) (L : NNReal),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            ‖deriv (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) x‖₊ ≤ L)) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
          K := by
  refine
    mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_Icc_deriv_bounds
      Φ u k ?_
  intro K hK
  rcases hsource K hK with ⟨a, b, L, hK_sub, hderiv⟩
  refine ⟨a, b, L, hK_sub, ?_, hderiv⟩
  intro n x _hx
  exact
    differentiableAt_mollifierFamilySmoothAt_of_locallyIntegrable
      Φ
      (fun m => (hu_memLp m).locallyIntegrable (by norm_num [p2]))
      k n x

/-- Compact-wise fixed-scale Lipschitz source from real absolute-value
derivative bounds.

This packages the analytic estimate form produced by the derivative Hölder
bound, `|deriv ...| ≤ C`, into the `NNReal` derivative-bound form required by
the checked fixed-scale Lipschitz bridge. -/
theorem mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k : ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b C : ℝ),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            |deriv (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t) x| ≤ C)) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
          K := by
  refine
    mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_bound
      Φ u hu_memLp k ?_
  intro K hK
  rcases hsource K hK with ⟨a, b, C, hK_sub, hderiv_abs⟩
  refine ⟨a, b, Real.toNNReal C, hK_sub, ?_⟩
  intro n x hx
  exact nnnorm_le_toNNReal_of_abs_le (hderiv_abs n x hx)

/-- Compact-wise fixed-scale Lipschitz source from bounds on the derivative
Hölder RHS.

This is the final formal packaging layer before a numerical envelope: if the
product of the fixed-scale derivative-kernel `L²` factor and the shifted source
`L²` factor is bounded by `C` on an enclosing interval, then the checked
derivative formula and Hölder estimate pay the compact Lipschitz source. -/
theorem mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_l2_rhs_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k : ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b C : ℝ),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            (∫ y : ℝ,
              ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume) ^
                ((1 : ℝ) / 2) *
              (∫ y : ℝ, ‖u n (x - y)‖ ^ (2 : ℝ) ∂volume) ^
                ((1 : ℝ) / 2) ≤ C)) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
          K := by
  refine
    mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_abs_bound
      Φ u hu_memLp k ?_
  intro K hK
  rcases hsource K hK with ⟨a, b, C, hK_sub, hbound⟩
  refine ⟨a, b, C, hK_sub, ?_⟩
  intro n x hx
  exact
    le_trans
      (abs_deriv_mollifierFamilySmoothAt_le_l2_norm_integrals_of_memLp_two_volume
        Φ u hu_memLp k n x)
      (hbound n x hx)

/-- Compact-wise fixed-scale Lipschitz source from separate bounds on the two
derivative Hölder factors.

The caller supplies an interval-wise bound on the fixed derivative-kernel
factor and the shifted-source factor.  This theorem only performs the
nonnegative product packaging and then invokes the checked RHS-bound wrapper;
it does not prove either numerical factor bound. -/
theorem mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_l2_factor_bounds
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k : ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b : ℝ) (A B : NNReal),
          K ⊆ Set.Icc a b ∧
          (∀ (n : ℕ) (x : ℝ), x ∈ Set.Icc a b →
            0 ≤
              (∫ y : ℝ, ‖u n (x - y)‖ ^ (2 : ℝ) ∂volume) ^
                ((1 : ℝ) / 2)) ∧
          (∀ x : ℝ, x ∈ Set.Icc a b →
            (∫ y : ℝ,
              ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume) ^
                ((1 : ℝ) / 2) ≤ (A : ℝ)) ∧
          (∀ (n : ℕ) (x : ℝ), x ∈ Set.Icc a b →
            (∫ y : ℝ, ‖u n (x - y)‖ ^ (2 : ℝ) ∂volume) ^
                ((1 : ℝ) / 2) ≤ (B : ℝ))) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
          K := by
  refine
    mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_l2_rhs_bound
      Φ u hu_memLp k ?_
  intro K hK
  rcases hsource K hK with ⟨a, b, A, B, hK_sub, hsrc_nonneg, hker, hsrc⟩
  refine ⟨a, b, (A : ℝ) * (B : ℝ), hK_sub, ?_⟩
  intro n x hx
  exact
    mul_le_mul
      (hker x hx)
      (hsrc n x hx)
      (hsrc_nonneg n x hx)
      (NNReal.coe_nonneg A)

/-- Nonnegativity of the fixed derivative-kernel `L²` factor. -/
theorem mollifierFamily_deriv_kernel_l2_factor_nonneg
    (Φ : MollifierFamily ℝ ℕ atTop) (k : ℕ) :
    0 ≤
      (∫ y : ℝ,
        ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume) ^
          ((1 : ℝ) / 2) := by
  have hbase :
      0 ≤ ∫ y : ℝ,
        ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume := by
    exact integral_nonneg (fun y => by positivity)
  exact Real.rpow_nonneg hbase _

/-- Nonnegativity of the shifted-source `L²` factor. -/
theorem shifted_source_l2_factor_nonneg
    (u : ℕ → ℝ → ℝ) (n : ℕ) (x : ℝ) :
    0 ≤
      (∫ y : ℝ, ‖u n (x - y)‖ ^ (2 : ℝ) ∂volume) ^
        ((1 : ℝ) / 2) := by
  have hbase :
      0 ≤ ∫ y : ℝ, ‖u n (x - y)‖ ^ (2 : ℝ) ∂volume := by
    exact integral_nonneg (fun y => by positivity)
  exact Real.rpow_nonneg hbase _

/-- Compact-wise fixed-scale Lipschitz source after the fixed derivative-kernel
factor is packaged as its own constant.

The only analytic source input left here is a uniform bound on the shifted
source `L²` factor over each enclosing interval.  The fixed derivative-kernel
factor is absorbed into a `NNReal` constant using nonnegativity. -/
theorem mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_source_l2_factor_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k : ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b : ℝ) (B : NNReal),
          K ⊆ Set.Icc a b ∧
          (∀ (n : ℕ) (x : ℝ), x ∈ Set.Icc a b →
            (∫ y : ℝ, ‖u n (x - y)‖ ^ (2 : ℝ) ∂volume) ^
                ((1 : ℝ) / 2) ≤ (B : ℝ))) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
          K := by
  refine
    mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_l2_factor_bounds
      Φ u hu_memLp k ?_
  intro K hK
  rcases hsource K hK with ⟨a, b, B, hK_sub, hsrc⟩
  let A : NNReal :=
    Real.toNNReal
      ((∫ y : ℝ,
        ‖deriv (Φ.kernel (volume : Measure ℝ) k) y‖ ^ (2 : ℝ) ∂volume) ^
          ((1 : ℝ) / 2))
  refine ⟨a, b, A, B, hK_sub, ?_, ?_, hsrc⟩
  · intro n x _hx
    exact shifted_source_l2_factor_nonneg u n x
  · intro x _hx
    have hnonneg := mollifierFamily_deriv_kernel_l2_factor_nonneg Φ k
    simp [A, Real.toNNReal_of_nonneg hnonneg]

/-- Translation invariance of the squared-norm source integral on the real
line, in the exact shifted form used by the derivative Hölder factor. -/
theorem shifted_source_l2_integral_eq_source_l2_integral
    (u : ℕ → ℝ → ℝ) (n : ℕ) (x : ℝ) :
    (∫ y : ℝ, ‖u n (x - y)‖ ^ (2 : ℝ) ∂volume) =
      ∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume := by
  have hmp := volume.measurePreserving_sub_left x
  have hme : MeasurableEmbedding (fun y : ℝ => x - y) := by
    exact (Homeomorph.subLeft x).measurableEmbedding
  simpa [Function.comp_def] using
    (MeasurePreserving.integral_comp (μ := volume) (ν := volume)
      hmp hme (fun y : ℝ => ‖u n y‖ ^ (2 : ℝ)))

/-- Compact-wise fixed-scale Lipschitz source from a uniform unshifted source
`L²` factor envelope.

This consumes the real-line translation invariance of volume to turn the
source envelope for `u n` into the shifted-source factor bound needed by the
checked fixed-scale compact Lipschitz theorem. -/
theorem mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_source_l2_envelope
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k : ℕ)
    (hsource :
      ∃ B : NNReal, ∀ n : ℕ,
        (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
            ((1 : ℝ) / 2) ≤ (B : ℝ)) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ => mollifierFamilySmoothAt Φ u k n t)
          K := by
  refine
    mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_source_l2_factor_bound
      Φ u hu_memLp k ?_
  rcases hsource with ⟨B, hB⟩
  intro K hK
  refine ⟨sInf K, sSup K, B, ?_, ?_⟩
  · exact subset_Icc_csInf_csSup hK.bddBelow hK.bddAbove
  intro n x _hx
  rw [shifted_source_l2_integral_eq_source_l2_integral u n x]
  exact hB n

/-- Fixed-scale scalar pointwise envelope from a uniform unshifted source `L²`
factor envelope.

The fixed kernel `L²` factor is constant in `n` and `t`; the source factor is
transported back to the unshifted source envelope by real-line translation
invariance of volume. -/
theorem mollifierFamilySmoothAt_fixedScale_pointwise_abs_bound_of_source_l2_envelope
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (k : ℕ)
    (hsource :
      ∃ B : NNReal, ∀ n : ℕ,
        (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
            ((1 : ℝ) / 2) ≤ (B : ℝ)) :
    ∀ t : ℝ, ∃ C : ℝ, ∀ n,
      |mollifierFamilySmoothAt Φ u k n t| ≤ C := by
  rcases hsource with ⟨B, hB⟩
  intro t
  let A : ℝ :=
    (∫ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) k y‖ ^ (2 : ℝ) ∂volume) ^
      ((1 : ℝ) / 2)
  refine ⟨A * (B : ℝ), ?_⟩
  intro n
  have hA_nonneg : 0 ≤ A := by
    have hbase :
        0 ≤ ∫ y : ℝ, ‖Φ.kernel (volume : Measure ℝ) k y‖ ^ (2 : ℝ) ∂volume := by
      exact integral_nonneg (fun y => by positivity)
    exact Real.rpow_nonneg hbase _
  have hpoint :=
    abs_mollifierFamilySmoothAt_le_l2_norm_integrals_of_memLp_two_volume
      Φ u k n t (hu_memLp n)
  calc
    |mollifierFamilySmoothAt Φ u k n t|
        ≤ A *
            (∫ y : ℝ, ‖u n (t - y)‖ ^ (2 : ℝ) ∂volume) ^
              ((1 : ℝ) / 2) := by
          simpa [A] using hpoint
    _ = A *
            (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
              ((1 : ℝ) / 2) := by
          rw [shifted_source_l2_integral_eq_source_l2_integral u n t]
    _ ≤ A * (B : ℝ) := by
          exact mul_le_mul_of_nonneg_left (hB n) hA_nonneg

/-- Concrete sampled `MollifierFamily` source for the Arzelà-Ascoli
`MollifiedFamilyHypotheses` contract, from continuity, compact-wise
equicontinuity, and scalar pointwise bounds.

This wrapper keeps the analytic estimates visible while aligning the exact
sampled family with the row-20 endpoint below:
`mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n))`. -/
theorem mollifierFamilySmoothAt_mollifiedFamilyHypotheses_of_pointwise_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (φ0 σ : ℕ → ℕ)
    (hcont :
      ∀ n,
        Continuous
          (fun t : ℝ =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t))
    (heq :
      ∀ K : Set ℝ, IsCompact K →
        EquicontinuousOn
          (fun (n : ℕ) (t : ℝ) =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
          K)
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t| ≤ C) :
    KRFArzelaAscoliStep.MollifiedFamilyHypotheses
      (fun (n : ℕ) (t : ℝ) =>
        mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t) :=
  KRFArzelaAscoliStep.mollifiedFamilyHypotheses_of_pointwise_abs_bound
    hcont heq hbound

/-- Concrete sampled `MollifierFamily` source for the Arzelà-Ascoli contract
from compact-wise common Lipschitz bounds and scalar pointwise bounds. -/
theorem mollifierFamilySmoothAt_mollifiedFamilyHypotheses_of_lipschitzOnWith_pointwise_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (φ0 σ : ℕ → ℕ)
    (hcont :
      ∀ n,
        Continuous
          (fun t : ℝ =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t))
    (hlip :
      ∀ K : Set ℝ, IsCompact K →
        ∃ L : NNReal, ∀ n,
          LipschitzOnWith L
            (fun t : ℝ =>
              mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
            K)
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t| ≤ C) :
    KRFArzelaAscoliStep.MollifiedFamilyHypotheses
      (fun (n : ℕ) (t : ℝ) =>
        mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t) :=
  KRFArzelaAscoliStep.mollifiedFamilyHypotheses_of_lipschitzOnWith_pointwise_abs_bound
    hcont hlip hbound

/-- Concrete Arzelà subsequence source for the sampled real-valued KRF
`MollifierFamily` family.

Mathlib supplies the remaining topological side conditions for `ℝ`, so after
the analytic step proves continuity, compact-wise common Lipschitz bounds, and
scalar pointwise bounds, the sampled family has a subsequence converging
uniformly on every compact set. -/
theorem mollifierFamilySmoothAt_arzela_subseq_of_lipschitzOnWith_pointwise_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (φ0 σ : ℕ → ℕ)
    (hcont :
      ∀ n,
        Continuous
          (fun t : ℝ =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t))
    (hlip :
      ∀ K : Set ℝ, IsCompact K →
        ∃ L : NNReal, ∀ n,
          LipschitzOnWith L
            (fun t : ℝ =>
              mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
            K)
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t| ≤ C) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ u (σ (ψ n)) (φ0 (σ (ψ n))) t)
          g atTop K := by
  simpa using
    (KRFArzelaAscoliStep.mollifiedFamily_subseq_tendstoUniformlyOn_of_ascoli
      (mollifierFamilySmoothAt_mollifiedFamilyHypotheses_of_lipschitzOnWith_pointwise_abs_bound
        Φ u φ0 σ hcont hlip hbound))

/-- Sampled compact-wise Lipschitz source from interval derivative bounds.

This is the varying-scale analogue of
`mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_deriv_bound`.
It does not claim any uniform-in-scale derivative estimate; it only packages
such an estimate, once supplied, into the exact sampled family consumed by the
row-20 Arzelà source. -/
theorem mollifierFamilySmoothAt_sampled_compact_lipschitzOnWith_of_deriv_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (φ0 σ : ℕ → ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b : ℝ) (L : NNReal),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            ‖deriv
              (fun t : ℝ =>
                mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t) x‖₊ ≤ L)) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
          K := by
  intro K hK
  rcases hsource K hK with ⟨a, b, L, hK_sub, hderiv⟩
  refine ⟨L, fun n => ?_⟩
  have hLipIcc :
      LipschitzOnWith L
        (fun t : ℝ =>
          mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
        (Set.Icc a b) :=
    (convex_Icc a b).lipschitzOnWith_of_nnnorm_deriv_le
      (fun x _hx =>
        differentiableAt_mollifierFamilySmoothAt_of_locallyIntegrable
          Φ
          (fun m => (hu_memLp m).locallyIntegrable (by norm_num [p2]))
          (σ n) (φ0 (σ n)) x)
      (fun x hx => hderiv n x hx)
  exact hLipIcc.mono hK_sub

/-- Sampled compact-wise Lipschitz source from real absolute-value derivative
bounds.

The theorem converts the scalar estimate form usually produced by analysis,
`|deriv ...| ≤ C`, into the `NNReal` Lipschitz source needed by Mathlib's
Arzelà-Ascoli wrapper. -/
theorem mollifierFamilySmoothAt_sampled_compact_lipschitzOnWith_of_deriv_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (φ0 σ : ℕ → ℕ)
    (hsource :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b C : ℝ),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            |deriv
              (fun t : ℝ =>
                mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t) x| ≤ C)) :
    ∀ K : Set ℝ, IsCompact K →
      ∃ L : NNReal, ∀ n,
        LipschitzOnWith L
          (fun t : ℝ =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
          K := by
  refine
    mollifierFamilySmoothAt_sampled_compact_lipschitzOnWith_of_deriv_bound
      Φ u hu_memLp φ0 σ ?_
  intro K hK
  rcases hsource K hK with ⟨a, b, C, hK_sub, hderiv_abs⟩
  refine ⟨a, b, Real.toNNReal C, hK_sub, ?_⟩
  intro n x hx
  exact nnnorm_le_toNNReal_of_abs_le (hderiv_abs n x hx)

/-- Sampled Arzelà subsequence source from explicit sampled derivative and
pointwise bounds.

This is a source-packaging closure: it proves that the sampled KRF mollifier
family has a compact-uniformly convergent subsequence once the analytic step
has supplied common compact derivative bounds and scalar pointwise bounds. It
does not prove those analytic sampled bounds. -/
theorem mollifierFamilySmoothAt_sampled_arzela_subseq_of_deriv_abs_bound_pointwise_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop) (u : ℕ → ℝ → ℝ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (φ0 σ : ℕ → ℕ)
    (hderiv :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b C : ℝ),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            |deriv
              (fun t : ℝ =>
                mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t) x| ≤ C))
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t| ≤ C) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ u (σ (ψ n)) (φ0 (σ (ψ n))) t)
          g atTop K := by
  exact
    mollifierFamilySmoothAt_arzela_subseq_of_lipschitzOnWith_pointwise_abs_bound
      Φ u φ0 σ
      (fun n =>
        continuous_mollifierFamilySmoothAt_of_memLp_two_volume
          Φ hu_memLp (σ n) (φ0 (σ n)))
      (mollifierFamilySmoothAt_sampled_compact_lipschitzOnWith_of_deriv_abs_bound
        Φ u hu_memLp φ0 σ hderiv)
      hbound

/-- Sampled Arzelà source for the KRF zero-extended indicator family from
explicit sampled derivative and pointwise bounds.

This is the row-20 family-specific version of
`mollifierFamilySmoothAt_sampled_arzela_subseq_of_deriv_abs_bound_pointwise_abs_bound`:
KRF data pays the ambient `L²` side condition for
`Set.indicator (Set.Icc 0 T) (u n)`, while the genuinely analytic sampled
derivative and pointwise bounds remain explicit assumptions. -/
theorem indicator_sampled_arzela_subseq_of_deriv_abs_bound_pointwise_abs_bound
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (D : KolmogorovRieszFrechetData ℝ T u)
    (φ0 σ : ℕ → ℕ)
    (hderiv :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b C : ℝ),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            |deriv
              (fun t : ℝ =>
                mollifierFamilySmoothAt Φ
                  (fun m => Set.indicator (Set.Icc 0 T) (u m))
                  (σ n) (φ0 (σ n)) t) x| ≤ C))
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ
            (fun m => Set.indicator (Set.Icc 0 T) (u m))
            (σ n) (φ0 (σ n)) t| ≤ C) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ (ψ n)) (φ0 (σ (ψ n))) t)
          g atTop K := by
  have hMemTwo :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2
        (volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq D D.integrable_norm_sq
  have hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) p2
        (volume : Measure ℝ) := by
    intro n
    simpa [p2] using hMemTwo n
  exact
    mollifierFamilySmoothAt_sampled_arzela_subseq_of_deriv_abs_bound_pointwise_abs_bound
      Φ (fun m => Set.indicator (Set.Icc 0 T) (u m)) hMem
      φ0 σ hderiv hbound

/-- Fixed-scale Arzelà subsequence source for the real-valued KRF
`MollifierFamily` family.

This is the classical KRF shape: fix the mollifier scale first, prove the
fixed-scale family is continuous, compact-wise commonly Lipschitz, and
pointwise bounded, then extract a subsequence converging uniformly on every
compact set.  The later `δ → 0`/scale-selection step is intentionally separate
from this Arzelà source. -/
theorem mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_lipschitzOnWith_pointwise_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (hcont :
      ∀ n,
        Continuous
          (fun t : ℝ =>
            mollifierFamilySmoothAt Φ u k n t))
    (hlip :
      ∀ K : Set ℝ, IsCompact K →
        ∃ L : NNReal, ∀ n,
          LipschitzOnWith L
            (fun t : ℝ =>
              mollifierFamilySmoothAt Φ u k n t)
            K)
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ u k n t| ≤ C) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ u k (ψ n) t)
          g atTop K := by
  simpa using
    (KRFArzelaAscoliStep.mollifiedFamily_subseq_tendstoUniformlyOn_of_ascoli
      (KRFArzelaAscoliStep.mollifiedFamilyHypotheses_of_lipschitzOnWith_pointwise_abs_bound
        (f := fun n t => mollifierFamilySmoothAt Φ u k n t)
        hcont hlip hbound))

/-- Fixed-scale Arzelà source with the continuity field paid by the selected
`L²` source.  The remaining analytic obligations are exactly the scalar
pointwise bound and compact-wise common Lipschitz bound. -/
theorem
    mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_memLp_lipschitzOnWith_pointwise_abs_bound
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (hlip :
      ∀ K : Set ℝ, IsCompact K →
        ∃ L : NNReal, ∀ n,
          LipschitzOnWith L
            (fun t : ℝ =>
              mollifierFamilySmoothAt Φ u k n t)
            K)
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ u k n t| ≤ C) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ u k (ψ n) t)
          g atTop K := by
  exact
    mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_lipschitzOnWith_pointwise_abs_bound
      Φ u k
      (fun n => continuous_mollifierFamilySmoothAt_of_memLp_two_volume Φ hu_memLp k n)
      hlip
      hbound

/-- Fixed-scale Arzelà source from one uniform source `L²` envelope.

This packages the fixed-scale path completely once the selected source family
has a uniform `L²` envelope.  It deliberately leaves the actual source-envelope
estimate and the later shrinking-scale/diagonal step outside the statement. -/
theorem mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_source_l2_envelope
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (hsource :
      ∃ B : NNReal, ∀ n : ℕ,
        (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
            ((1 : ℝ) / 2) ≤ (B : ℝ)) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ u k (ψ n) t)
          g atTop K := by
  exact
    mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_memLp_lipschitzOnWith_pointwise_abs_bound
      Φ u k hu_memLp
      (mollifierFamilySmoothAt_fixedScale_compact_lipschitzOnWith_of_source_l2_envelope
        Φ u hu_memLp k hsource)
      (mollifierFamilySmoothAt_fixedScale_pointwise_abs_bound_of_source_l2_envelope
        Φ u hu_memLp k hsource)

/-- An ambient uniform `eLpNorm` cap at `p = 2` supplies the real source
`L²` envelope used by the fixed-scale Arzelà bridge.

This is deliberately an ambient `volume` statement on `ℝ`; it does not convert
the restricted KRF interval field `∫_[0,T] ‖u n t‖^2` into an all-real-line
bound. -/
theorem source_l2_envelope_of_uniform_eLpNorm_bound
    {u : ℕ → ℝ → ℝ} {A : ENNReal}
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (hA : ∀ n, eLpNorm (u n) p2 (volume : Measure ℝ) ≤ A)
    (hA_ne_top : A ≠ ⊤) :
    ∃ B : NNReal, ∀ n : ℕ,
      (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
          ((1 : ℝ) / 2) ≤ (B : ℝ) := by
  refine ⟨A.toNNReal, ?_⟩
  intro n
  have h_toReal :
      (eLpNorm (u n) p2 (volume : Measure ℝ)).toReal ≤ A.toReal :=
    ENNReal.toReal_mono hA_ne_top (hA n)
  have h_lp :
      (eLpNorm (u n) p2 (volume : Measure ℝ)).toReal =
        (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
          ((1 : ℝ) / 2) := by
    have hp_two : (2 : NNReal) ≠ 0 := by
      norm_num
    rw [MeasureTheory.toReal_eLpNorm (hu_memLp n).aestronglyMeasurable]
    simpa [p2, one_div] using
      (MeasureTheory.lpNorm_nnreal_eq_integral_norm_rpow
        (μ := (volume : Measure ℝ))
        (f := u n)
        (p := (2 : NNReal))
        hp_two
        (hu_memLp n).aestronglyMeasurable)
  calc
    (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^ ((1 : ℝ) / 2)
        = (eLpNorm (u n) p2 (volume : Measure ℝ)).toReal := h_lp.symm
    _ ≤ A.toReal := h_toReal
    _ = (A.toNNReal : ℝ) := by
          exact (ENNReal.coe_toNNReal_eq_toReal A).symm

/-- Fixed-scale Arzelà source from an ambient uniform `eLpNorm` bound.

The theorem composes the currency bridge
`source_l2_envelope_of_uniform_eLpNorm_bound` with the existing fixed-scale
source-envelope Arzelà step. -/
theorem mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_uniform_eLpNorm_bound
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    {A : ENNReal}
    (hu_memLp : ∀ n, MemLp (u n) p2 (volume : Measure ℝ))
    (hA : ∀ n, eLpNorm (u n) p2 (volume : Measure ℝ) ≤ A)
    (hA_ne_top : A ≠ ⊤) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ u k (ψ n) t)
          g atTop K := by
  exact
    mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_source_l2_envelope
      Φ u k hu_memLp
      (source_l2_envelope_of_uniform_eLpNorm_bound
        hu_memLp hA hA_ne_top)

/-- Restricted interval `L²` control alone does not imply the ambient
all-real-line `MemLp p = 2` source needed by the Phase-A bridge.

The constant-one family has a finite `L²` integral on `[0,1]`, but the same
constant-one function is not in ambient `L²(volume)` on `ℝ`.  This is the
formal source-shape guard against treating
`KolmogorovRieszFrechetData.unif_l2_bound` as an all-real-line source without
support or extension data. -/
theorem restricted_interval_l2_bound_not_ambient_memLp_constant_one :
    (∃ M : ℝ, 0 ≤ M ∧
      ∀ _n : ℕ,
        ∫ _t in Set.Icc (0 : ℝ) 1, ‖(1 : ℝ)‖ ^ (2 : ℝ) ≤ M) ∧
    ¬ MemLp (fun _ : ℝ => (1 : ℝ)) p2 (volume : Measure ℝ) := by
  constructor
  · refine ⟨1, by norm_num, ?_⟩
    intro _n
    simp
  · intro hmem
    have hfinite :
        eLpNorm (fun _ : ℝ => (1 : ℝ)) p2 (volume : Measure ℝ) < ⊤ :=
      hmem.eLpNorm_lt_top
    have hp0 : p2 ≠ 0 := by
      simp [p2]
    have hptop : p2 ≠ ⊤ := by
      simp [p2]
    have hiff :=
      (MeasureTheory.eLpNorm_const_lt_top_iff
        (μ := (volume : Measure ℝ))
        (p := p2)
        (c := (1 : ℝ))
        hp0 hptop)
    have hbad := hiff.mp hfinite
    simp at hbad

/-- Restricted `MemLp` upgrades to ambient `MemLp` when the source is supported
on the interval.

This is the positive counterpart to
`restricted_interval_l2_bound_not_ambient_memLp_constant_one`: the interval
source can be used only after the zero-extension/support hypothesis is stated. -/
theorem ambient_memLp_of_restricted_memLp_support
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (hu_restrict :
      ∀ n, MemLp (u n) p2 (volume.restrict (Set.Icc 0 T)))
    (hsupport : ∀ n x, x ∉ Set.Icc 0 T → u n x = 0) :
    ∀ n, MemLp (u n) p2 (volume : Measure ℝ) := by
  intro n
  have hIndicator :
      Set.indicator (Set.Icc 0 T) (u n) = u n := by
    funext x
    by_cases hx : x ∈ Set.Icc 0 T
    · simp [Set.indicator_of_mem, hx]
    · simp [Set.indicator_of_notMem, hx, hsupport n x hx]
  have hi :
      MemLp (Set.indicator (Set.Icc 0 T) (u n)) p2
        (volume : Measure ℝ) := by
    exact
      (MeasureTheory.memLp_indicator_iff_restrict
        (μ := (volume : Measure ℝ))
        (p := p2)
        (f := u n)
        (hs := (measurableSet_Icc : MeasurableSet (Set.Icc 0 T)))).2
        (hu_restrict n)
  simpa [hIndicator] using hi

/-- A restricted interval source `L²` envelope upgrades to the ambient source
envelope when the source is supported on the interval. -/
theorem source_l2_envelope_of_restricted_l2_envelope_support
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (hsource :
      ∃ B : NNReal, ∀ n : ℕ,
        (∫ y in Set.Icc 0 T, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
            ((1 : ℝ) / 2) ≤ (B : ℝ))
    (hsupport : ∀ n x, x ∉ Set.Icc 0 T → u n x = 0) :
    ∃ B : NNReal, ∀ n : ℕ,
      (∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
          ((1 : ℝ) / 2) ≤ (B : ℝ) := by
  rcases hsource with ⟨B, hB⟩
  refine ⟨B, ?_⟩
  intro n
  have hIntegral :
      ∫ y in Set.Icc 0 T, ‖u n y‖ ^ (2 : ℝ) ∂volume =
        ∫ y : ℝ, ‖u n y‖ ^ (2 : ℝ) ∂volume := by
    exact
      MeasureTheory.setIntegral_eq_integral_of_forall_compl_eq_zero
        (μ := (volume : Measure ℝ))
        (s := Set.Icc 0 T)
        (f := fun y : ℝ => ‖u n y‖ ^ (2 : ℝ))
        (fun y hy => by simp [hsupport n y hy])
  rw [← hIntegral]
  exact hB n

/-- Fixed-scale Arzelà from restricted interval source data plus explicit
support outside the interval.

This is the honest support-extension route: it composes restricted `MemLp`,
restricted source envelope, and zero support outside `[0,T]` into the ambient
fixed-scale source theorem. -/
theorem mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_restricted_l2_support
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (hu_restrict :
      ∀ n, MemLp (u n) p2 (volume.restrict (Set.Icc 0 T)))
    (hsource :
      ∃ B : NNReal, ∀ n : ℕ,
        (∫ y in Set.Icc 0 T, ‖u n y‖ ^ (2 : ℝ) ∂volume) ^
            ((1 : ℝ) / 2) ≤ (B : ℝ))
    (hsupport : ∀ n x, x ∉ Set.Icc 0 T → u n x = 0) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ u k (ψ n) t)
          g atTop K := by
  exact
    mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_source_l2_envelope
      Φ u k
      (ambient_memLp_of_restricted_memLp_support
        hu_restrict hsupport)
      (source_l2_envelope_of_restricted_l2_envelope_support
        hsource hsupport)

/-- KRF data supplies the ambient source `L²` envelope for the zero-extended
indicator family.

This is the KRF-native support route: the original source need not be ambient
`L²`, but the KRF data already names the zero extension
`Set.indicator (Set.Icc 0 T) (u n)`. -/
theorem source_l2_envelope_of_krf_data_indicator
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∃ B : NNReal, ∀ n : ℕ,
      (∫ y : ℝ,
          ‖Set.indicator (Set.Icc 0 T) (u n) y‖ ^ (2 : ℝ) ∂volume) ^
          ((1 : ℝ) / 2) ≤ (B : ℝ) := by
  have hMemTwo :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2
        (volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq D D.integrable_norm_sq
  have hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) p2
        (volume : Measure ℝ) := by
    intro n
    simpa [p2] using hMemTwo n
  rcases indicator_eLpNorm_bound_of_krf_l2_bound_memLp D hMemTwo with
    ⟨A, hA_lt_top, hA⟩
  have hA' :
      ∀ n,
        eLpNorm (Set.indicator (Set.Icc 0 T) (u n)) p2
          (volume : Measure ℝ) ≤ A := by
    intro n
    simpa [p2] using hA n
  exact source_l2_envelope_of_uniform_eLpNorm_bound hMem hA' hA_lt_top.ne

/-- Fixed-scale Arzelà compactness for the KRF zero-extended indicator family.

The conclusion is intentionally about
`Set.indicator (Set.Icc 0 T) (u n)`, not the unextended source.  This is the
honest KRF/Mathlib currency for the ambient mollifier bridge. -/
theorem mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_krf_data_indicator
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∃ (ψ : ℕ → ℕ) (g : ℝ → ℝ),
      StrictMono ψ ∧ Continuous g ∧
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m)) k (ψ n) t)
          g atTop K := by
  have hMemTwo :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2
        (volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq D D.integrable_norm_sq
  have hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) p2
        (volume : Measure ℝ) := by
    intro n
    simpa [p2] using hMemTwo n
  exact
    mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_source_l2_envelope
      Φ (fun m => Set.indicator (Set.Icc 0 T) (u m)) k hMem
      (source_l2_envelope_of_krf_data_indicator D)

/-- A fixed mollifier scale cannot be smuggled into the row-20 sampled-scale
interface as a strict scale selector.

The row-20 consumers below require a `StrictMono σ`, hence `σ n → ∞`.  A
fixed-scale Arzelà theorem is therefore not directly a sampled-scale/diagonal
receipt. -/
theorem no_strictMono_constant_scale_selector
    {σ : ℕ → ℕ} {k : ℕ}
    (hσ : ∀ n : ℕ, σ n = k) :
    ¬ StrictMono σ := by
  intro hmono
  have hlt : σ 0 < σ 1 := hmono (Nat.zero_lt_succ 0)
  rw [hσ 0, hσ 1] at hlt
  exact (Nat.lt_irrefl k) hlt

/-- Fixed-scale KRF indicator Arzelà compactness in the row-20 smoothed-limit
`eLpNorm` currency.

This pays only the smoothed-limit side of the row-20 producer for the extracted
fixed-scale zero-extended indicator family.  It does not pay the Phase-A
approximation side, and by `no_strictMono_constant_scale_selector` it is not a
sampled-scale diagonal receipt. -/
theorem linkedSmoothedLimitELpNormRealOutput_of_krf_data_indicator_fixedScale_arzela
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∃ ψ : ℕ → ℕ,
      StrictMono ψ ∧
      LinkedSmoothedLimitELpNormRealOutput T
        (fun n t =>
          mollifierFamilySmoothAt Φ
            (fun m => Set.indicator (Set.Icc 0 T) (u m)) k (ψ n) t) := by
  rcases mollifierFamilySmoothAt_fixedScale_arzela_subseq_of_krf_data_indicator
    Φ u k D with ⟨ψ, g, hψ, hg, hUniformCompacts⟩
  have hMemTwo :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2
        (volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq D D.integrable_norm_sq
  have hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) p2
        (volume : Measure ℝ) := by
    intro n
    simpa [p2] using hMemTwo n
  have hSmoothContinuous :
      ∀ n : ℕ,
        Continuous
          (fun t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m)) k (ψ n) t) := by
    intro n
    exact
      continuous_mollifierFamilySmoothAt_of_memLp_two_volume
        Φ hMem k (ψ n)
  refine ⟨ψ, hψ, ?_⟩
  exact
    LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_compacts
      (T := T)
      (smooth := fun n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k (ψ n) t)
      (limit := g)
      (fun n => ((hSmoothContinuous n).sub hg).aestronglyMeasurable.restrict)
      (fun n => (hg.sub (hSmoothContinuous n)).aestronglyMeasurable.restrict)
      hUniformCompacts

/-- Tendsto-form version of
`linkedSmoothedLimitELpNormRealOutput_of_krf_data_indicator_fixedScale_arzela`.
-/
theorem linkedSmoothedLimitELpNormOutput_of_krf_data_indicator_fixedScale_arzela
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    (u : ℕ → ℝ → ℝ)
    (k : ℕ)
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∃ ψ : ℕ → ℕ,
      StrictMono ψ ∧
      LinkedSmoothedLimitELpNormOutput T
        (fun n t =>
          mollifierFamilySmoothAt Φ
            (fun m => Set.indicator (Set.Icc 0 T) (u m)) k (ψ n) t) := by
  rcases
    linkedSmoothedLimitELpNormRealOutput_of_krf_data_indicator_fixedScale_arzela
      Φ u k D with ⟨ψ, hψ, hReal⟩
  exact ⟨ψ, hψ, LinkedSmoothedLimitELpNormOutput_of_real hReal⟩

/-- KRF data pays the restricted measurability side condition for the
zero-extended indicator family's mollifier error.

This is a formalization-side receipt: the smoothed term is continuous from the
ambient indicator `L²` source, while the unsmoothed zero extension is
measurable from `D.meas_u`. -/
theorem aestronglyMeasurable_indicator_mollifier_error_of_krf_data
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∀ k n : ℕ,
      AEStronglyMeasurable
        (fun t =>
          mollifierFamilySmoothAt Φ
            (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t -
            Set.indicator (Set.Icc 0 T) (u n) t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T)) := by
  intro k n
  have hMemTwo :
      ∀ m, MemLp (Set.indicator (Set.Icc 0 T) (u m)) 2
        (volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq D D.integrable_norm_sq
  have hMem :
      ∀ m, MemLp (Set.indicator (Set.Icc 0 T) (u m)) p2
        (volume : Measure ℝ) := by
    intro m
    simpa [p2] using hMemTwo m
  have hSmooth :
      AEStronglyMeasurable
        (fun t =>
          mollifierFamilySmoothAt Φ
            (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T)) :=
    ((continuous_mollifierFamilySmoothAt_of_memLp_two_volume
        Φ hMem k n).aestronglyMeasurable).restrict
  have hIndicator :
      AEStronglyMeasurable
        (fun t => Set.indicator (Set.Icc 0 T) (u n) t)
        (MeasureTheory.volume.restrict (Set.Icc 0 T)) :=
    (((D.meas_u n).indicator
      (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))).aestronglyMeasurable).restrict
  exact hSmooth.sub hIndicator

/-- KRF data pays the MLG-2 Phase-A uniform-scale approximation for the
zero-extended indicator family once the genuinely missing ambient translation
equicontinuity source has been supplied.

This deliberately leaves the boundary-strip coercivity problem explicit:
`KolmogorovRieszFrechetData.unif_translation` is a restricted-interval real
integral statement, while this theorem consumes ambient
`TranslationEquicontinuousL2` for the zero extension. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_translation
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hIndicatorUnif :
      TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
        (fun n => Set.indicator (Set.Icc 0 T) (u n))) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) := by
  have hMemTwo :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2
        (volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq D D.integrable_norm_sq
  have hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) p2
        (volume : Measure ℝ) := by
    intro n
    simpa [p2] using hMemTwo n
  rcases indicator_eLpNorm_bound_of_krf_l2_bound_memLp D hMemTwo with
    ⟨A, hA_lt_top, hA⟩
  have hA' :
      ∀ n,
        eLpNorm (Set.indicator (Set.Icc 0 T) (u n)) p2
          (volume : Measure ℝ) ≤ A := by
    intro n
    simpa [p2] using hA n
  simpa [mollifierFamilySmoothAt] using
    (UniformScaleApproximationELpNormRealOutput_of_mlg2_krf_mollifierFamily
      (T := T)
      Φ
      (f := fun n => Set.indicator (Set.Icc 0 T) (u n))
      (A := A)
      (by
        intro k n
        simpa [mollifierFamilySmoothAt] using
          aestronglyMeasurable_indicator_mollifier_error_of_krf_data
            Φ D k n)
      hMem
      hIndicatorUnif
      hA'
      hA_lt_top.ne)

/-- Native KRF3 currency for the zero-extended interval family.

This is the Mathlib-friendly version of translation equicontinuity: it is
already stated as an ambient `eLpNorm` smallness assertion for the translated
zero extension, so it does not require a separate Bochner `IntegrableOn`
witness for a shifted-square integrand. -/
structure KRFIndicatorTranslationELpNormSource
    (T : ℝ) (u : ℕ → ℝ → ℝ) : Prop where
  unif_indicator_translation :
    ∀ ε : ℝ, 0 < ε → ∃ δ : ℝ, 0 < δ ∧
      ∀ n h, |h| < δ →
        eLpNorm
          (fun x =>
            Set.indicator (Set.Icc 0 T) (u n) (x + h) -
              Set.indicator (Set.Icc 0 T) (u n) x)
          2 (volume : Measure ℝ) < ENNReal.ofReal ε

/-- Repaired KRF bundle surface using the preferred ambient `eLpNorm` KRF3
field for the zero-extended interval family. -/
structure KolmogorovRieszFrechetDataWithELpNormKRF3
    (T : ℝ) (u : ℕ → ℝ → ℝ) : Prop
    extends KolmogorovRieszFrechetData ℝ T u where
  indicator_translation_source : KRFIndicatorTranslationELpNormSource T u

/-- The `eLpNorm`-native KRF3 source is exactly the neighbourhood-form
translation equicontinuity consumed by MLG-2. -/
theorem translationEquicontinuousL2_indicator_of_krf_eLpNorm_source
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (S : KRFIndicatorTranslationELpNormSource T u) :
    TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) := by
  intro ε hε
  rcases S.unif_indicator_translation ε hε with ⟨δ, hδ_pos, hδ⟩
  refine ⟨Metric.ball (0 : ℝ) δ, Metric.ball_mem_nhds 0 hδ_pos, ?_⟩
  intro n h hh
  have hh_abs : |h| < δ := by
    simpa [Metric.mem_ball, Real.dist_eq, abs_sub_comm] using hh
  exact hδ n h hh_abs

/-- Neighbourhood-form translation equicontinuity also packages back into the
native `δ/|h|` source currency.  This lets all existing MLG-2 translation
routes feed the repaired KRF3 bundle without restating their proofs. -/
theorem krfIndicatorTranslationELpNormSource_of_translationEquicontinuousL2
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (hT :
      TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
        (fun n => Set.indicator (Set.Icc 0 T) (u n))) :
    KRFIndicatorTranslationELpNormSource T u := by
  refine ⟨?_⟩
  intro ε hε
  rcases hT ε hε with ⟨U, hU_mem, hU_small⟩
  rcases Metric.mem_nhds_iff.mp hU_mem with ⟨δ, hδ_pos, hδ_subset⟩
  refine ⟨δ, hδ_pos, ?_⟩
  intro n h hh_abs
  have hh_ball : h ∈ Metric.ball (0 : ℝ) δ := by
    simpa [Metric.mem_ball, Real.dist_eq, abs_sub_comm] using hh_abs
  exact hU_small n h (hδ_subset hh_ball)

/-- Phase-A closure from KRF data plus the preferred `eLpNorm`-native KRF3
currency. This route avoids the Bochner-integrability side debt entirely. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_eLpNorm_source
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (S : KRFIndicatorTranslationELpNormSource T u) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) :=
  UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_translation
    Φ D (translationEquicontinuousL2_indicator_of_krf_eLpNorm_source S)

/-- Phase-A closure from the repaired `eLpNorm` KRF3 bundle surface. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_eLpNormKRF3
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithELpNormKRF3 T u) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) :=
  UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_eLpNorm_source
    Φ D.toKolmogorovRieszFrechetData D.indicator_translation_source

/-- Interior contribution to translating the zero-extended indicator family. -/
def indicatorTranslationInteriorTerm
    (T : ℝ) (u : ℕ → ℝ → ℝ) (n : ℕ) (h : ℝ) : ℝ → ℝ :=
  Set.indicator
    {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
    (fun x => u n (x + h) - u n x)

/-- Entry-boundary contribution to translating the zero-extended indicator
family: points outside `[0,T]` whose translate lies inside. -/
def indicatorTranslationEnterTerm
    (T : ℝ) (u : ℕ → ℝ → ℝ) (n : ℕ) (h : ℝ) : ℝ → ℝ :=
  Set.indicator
    {x : ℝ | x ∉ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
    (fun x => u n (x + h))

/-- Exit-boundary contribution to translating the zero-extended indicator
family: points inside `[0,T]` whose translate leaves the interval. -/
def indicatorTranslationExitTerm
    (T : ℝ) (u : ℕ → ℝ → ℝ) (n : ℕ) (h : ℝ) : ℝ → ℝ :=
  Set.indicator
    {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T}
    (fun x => -u n x)

/-- Source contract for reducing ambient translation equicontinuity of the
zero-extended indicator family to three concrete payments: interior
translation, entry boundary strip, and exit boundary strip.

The boundary fields are the nontrivial KRF/UI work; this structure exists to
avoid hiding them inside a direct `TranslationEquicontinuousL2` hypothesis. -/
structure IndicatorTranslationDecompositionSources
    (T : ℝ) (u : ℕ → ℝ → ℝ) : Prop where
  interior_meas :
    ∀ n h,
      AEStronglyMeasurable
        (indicatorTranslationInteriorTerm T u n h)
        (volume : Measure ℝ)
  enter_meas :
    ∀ n h,
      AEStronglyMeasurable
        (indicatorTranslationEnterTerm T u n h)
        (volume : Measure ℝ)
  exit_meas :
    ∀ n h,
      AEStronglyMeasurable
        (indicatorTranslationExitTerm T u n h)
        (volume : Measure ℝ)
  interior_small :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε
  enter_small :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationEnterTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε
  exit_small :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationExitTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε

private lemma measurable_shift_add_right (h : ℝ) :
    Measurable (fun x : ℝ => x + h) := by
  exact (continuous_id.add continuous_const).measurable

private lemma measurableSet_indicatorTranslationInterior
    (T h : ℝ) :
    MeasurableSet {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
  exact
    (measurableSet_Icc : MeasurableSet (Set.Icc 0 T)).inter
      ((measurableSet_Icc : MeasurableSet (Set.Icc 0 T)).preimage
        (measurable_shift_add_right h))

private lemma measurableSet_indicatorTranslationEnter
    (T h : ℝ) :
    MeasurableSet {x : ℝ | x ∉ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
  exact
    (measurableSet_Icc : MeasurableSet (Set.Icc 0 T)).compl.inter
      ((measurableSet_Icc : MeasurableSet (Set.Icc 0 T)).preimage
        (measurable_shift_add_right h))

private lemma measurableSet_indicatorTranslationExit
    (T h : ℝ) :
    MeasurableSet {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T} := by
  exact
    (measurableSet_Icc : MeasurableSet (Set.Icc 0 T)).inter
      (((measurableSet_Icc : MeasurableSet (Set.Icc 0 T)).preimage
        (measurable_shift_add_right h)).compl)

/-- The interior translation indicator has no larger ambient `L²` seminorm
than the unrestricted difference measured on `[0,T]`. This is only a currency
bridge; any later conversion to a real restricted integral still has to pay
the corresponding integrability hypothesis. -/
theorem indicatorTranslationInteriorTerm_eLpNorm_le_restricted_translation
    {T : ℝ} {u : ℕ → ℝ → ℝ} {n : ℕ} {h : ℝ} :
    eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
        (volume : Measure ℝ)
      ≤ eLpNorm (fun x : ℝ => u n (x + h) - u n x) 2
        ((volume : Measure ℝ).restrict (Set.Icc 0 T)) := by
  let s : Set ℝ := {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
  have hs : MeasurableSet s := by
    dsimp [s]
    exact measurableSet_indicatorTranslationInterior T h
  have hs_subset : s ⊆ Set.Icc 0 T := by
    intro x hx
    exact hx.1
  rw [indicatorTranslationInteriorTerm,
    eLpNorm_indicator_eq_eLpNorm_restrict hs]
  exact
    eLpNorm_mono_measure
      (fun x : ℝ => u n (x + h) - u n x)
      ((volume : Measure ℝ).restrict_mono_set hs_subset)

/-- A real restricted square-integral bound gives the corresponding restricted
`eLpNorm` bound once the `MemLp` witness is supplied. -/
theorem restricted_eLpNorm_two_le_of_setIntegral_bound_memLp
    {s : Set ℝ} {f : ℝ → ℝ} {M : ℝ}
    (hs : MeasurableSet s)
    (hMem : MemLp f 2 ((volume : Measure ℝ).restrict s))
    (hBound : ∫ x in s, ‖f x‖ ^ 2 ∂volume ≤ M) :
    eLpNorm f 2 ((volume : Measure ℝ).restrict s)
      ≤ ENNReal.ofReal (M ^ ((1 : ℝ) / 2)) := by
  have hp0 : (2 : ENNReal) ≠ 0 := by norm_num
  have hpInf : (2 : ENNReal) ≠ ⊤ := by norm_num
  have hSqIntegralEq :
      (∫ x in s, f x ^ 2 ∂volume) =
        ∫ x in s, ‖f x‖ ^ 2 ∂volume := by
    congr
    funext x
    simp [Real.norm_eq_abs, sq_abs]
  have hBoundSq : ∫ x in s, f x ^ 2 ∂volume ≤ M := by
    rw [hSqIntegralEq]
    exact hBound
  have hIntNonneg : 0 ≤ ∫ x in s, f x ^ 2 ∂volume := by
    exact setIntegral_nonneg hs (fun x _hx => by positivity)
  have hPowLe :
      (∫ x in s, f x ^ 2 ∂volume) ^ ((1 : ℝ) / 2)
        ≤ M ^ ((1 : ℝ) / 2) := by
    exact Real.rpow_le_rpow hIntNonneg hBoundSq
      (by positivity : 0 ≤ ((1 : ℝ) / 2))
  rw [MemLp.eLpNorm_eq_integral_rpow_norm hp0 hpInf hMem]
  norm_num
  exact ENNReal.ofReal_le_ofReal hPowLe

/-- Specialized currency bridge for the KRF interior translation source:
restricted real integral control of the shifted difference bounds the ambient
interior indicator term, once the shifted difference has a restricted `MemLp`
witness. -/
theorem indicatorTranslationInteriorTerm_eLpNorm_le_of_restricted_translation_integral_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ} {n : ℕ} {h M : ℝ}
    (hMem : MemLp (fun x : ℝ => u n (x + h) - u n x) 2
        ((volume : Measure ℝ).restrict (Set.Icc 0 T)))
    (hBound :
      ∫ x in Set.Icc 0 T, ‖u n (x + h) - u n x‖ ^ 2 ∂volume ≤ M) :
    eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
        (volume : Measure ℝ)
      ≤ ENNReal.ofReal (M ^ ((1 : ℝ) / 2)) := by
  exact
    (indicatorTranslationInteriorTerm_eLpNorm_le_restricted_translation
      (T := T) (u := u) (n := n) (h := h)).trans
      (restricted_eLpNorm_two_le_of_setIntegral_bound_memLp
        (s := Set.Icc 0 T)
        (f := fun x : ℝ => u n (x + h) - u n x)
        (M := M)
        (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
        hMem hBound)

/-- Interior-set version of the translation currency bridge. Unlike the
`Icc 0 T` version, this asks for `MemLp` only where both `x` and `x+h` remain
inside the source interval. -/
theorem indicatorTranslationInteriorTerm_eLpNorm_le_of_interior_integral_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ} {n : ℕ} {h M : ℝ}
    (hMem : MemLp (fun x : ℝ => u n (x + h) - u n x) 2
        ((volume : Measure ℝ).restrict
          {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}))
    (hBound :
      ∫ x in {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T},
        ‖u n (x + h) - u n x‖ ^ 2 ∂volume ≤ M) :
    eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
        (volume : Measure ℝ)
      ≤ ENNReal.ofReal (M ^ ((1 : ℝ) / 2)) := by
  let s : Set ℝ := {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
  have hs : MeasurableSet s := by
    dsimp [s]
    exact measurableSet_indicatorTranslationInterior T h
  rw [indicatorTranslationInteriorTerm,
    eLpNorm_indicator_eq_eLpNorm_restrict hs]
  exact
    restricted_eLpNorm_two_le_of_setIntegral_bound_memLp
      (s := s)
      (f := fun x : ℝ => u n (x + h) - u n x)
      (M := M)
      hs
      (by simpa [s] using hMem)
      (by simpa [s] using hBound)

/-- Interior smallness from correctly localized real-integral sources. This is
the sharp source contract left after the indicator/restriction bookkeeping has
been paid: prove `MemLp` and square-integral smallness on the interior set
where both `x` and `x+h` lie in `[0,T]`. -/
theorem indicatorTranslationInteriorTerm_small_of_interior_integral_sources
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (hInteriorMem :
      ∀ n h,
        MemLp (fun x : ℝ => u n (x + h) - u n x) 2
          ((volume : Measure ℝ).restrict
            {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}))
    (hInteriorIntegralSmall :
      ∀ η : ℝ, 0 < η → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ n h, h ∈ U →
          ∫ x in {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T},
            ‖u n (x + h) - u n x‖ ^ 2 ∂volume < η) :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε := by
  intro ε hε
  let γ : ℝ := (ε / 2) ^ 2
  have hεhalf : 0 < ε / 2 := by positivity
  have hγ_pos : 0 < γ := by
    dsimp [γ]
    positivity
  rcases hInteriorIntegralSmall γ hγ_pos with ⟨U, hU, hSmall⟩
  refine ⟨U, hU, ?_⟩
  intro n h hh
  have hLe :
      eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
          (volume : Measure ℝ)
        ≤ ENNReal.ofReal (γ ^ ((1 : ℝ) / 2)) :=
    indicatorTranslationInteriorTerm_eLpNorm_le_of_interior_integral_memLp
      (T := T) (u := u) (n := n) (h := h) (M := γ)
      (hInteriorMem n h) (le_of_lt (hSmall n h hh))
  have hγ_root : γ ^ ((1 : ℝ) / 2) = ε / 2 := by
    dsimp [γ]
    rw [← Real.sqrt_eq_rpow, Real.sqrt_sq hεhalf.le]
  have hOfRealLt : ENNReal.ofReal (γ ^ ((1 : ℝ) / 2)) < ENNReal.ofReal ε := by
    rw [hγ_root]
    exact (ENNReal.ofReal_lt_ofReal_iff hε).2 (half_lt_self hε)
  exact lt_of_le_of_lt hLe hOfRealLt

/-- Conditional interior smallness from KRF translation control, once the
shifted difference is supplied as a restricted `MemLp` source on `[0,T]`.

The `MemLp` hypothesis is intentionally explicit: it is stronger than what the
current KRF data pays for arbitrary `h`, since `x + h` may leave `[0,T]`. The
honest next target is the same theorem over the interior set
`{x | x ∈ Icc 0 T ∧ x + h ∈ Icc 0 T}`. -/
theorem indicatorTranslationInteriorTerm_small_of_krf_data_and_shifted_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hShiftMem :
      ∀ n h,
        MemLp (fun x : ℝ => u n (x + h) - u n x) 2
          ((volume : Measure ℝ).restrict (Set.Icc 0 T))) :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε := by
  intro ε hε
  let γ : ℝ := (ε / 2) ^ 2
  have hεhalf : 0 < ε / 2 := by positivity
  have hγ_pos : 0 < γ := by
    dsimp [γ]
    positivity
  rcases D.unif_translation γ hγ_pos with ⟨δ, hδ_pos, hδ⟩
  refine ⟨Metric.ball (0 : ℝ) δ, Metric.ball_mem_nhds 0 hδ_pos, ?_⟩
  intro n h hh
  have hh_abs : |h| < δ := by
    simpa [Metric.mem_ball, Real.dist_eq, abs_sub_comm] using hh
  have hIntLt :
      ∫ x in Set.Icc 0 T, ‖u n (x + h) - u n x‖ ^ 2 ∂volume < γ :=
    hδ n h hh_abs
  have hLe :
      eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
          (volume : Measure ℝ)
        ≤ ENNReal.ofReal (γ ^ ((1 : ℝ) / 2)) :=
    indicatorTranslationInteriorTerm_eLpNorm_le_of_restricted_translation_integral_memLp
      (T := T) (u := u) (n := n) (h := h) (M := γ)
      (hShiftMem n h) (le_of_lt hIntLt)
  have hγ_root : γ ^ ((1 : ℝ) / 2) = ε / 2 := by
    dsimp [γ]
    rw [← Real.sqrt_eq_rpow, Real.sqrt_sq hεhalf.le]
  have hOfRealLt : ENNReal.ofReal (γ ^ ((1 : ℝ) / 2)) < ENNReal.ofReal ε := by
    rw [hγ_root]
    exact (ENNReal.ofReal_lt_ofReal_iff hε).2 (half_lt_self hε)
  exact lt_of_le_of_lt hLe hOfRealLt

/-- KRF data pays the measurability source for the interior translation term. -/
theorem indicatorTranslationInteriorTerm_aestronglyMeasurable_of_krf_data
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∀ n h,
      AEStronglyMeasurable
        (indicatorTranslationInteriorTerm T u n h)
        (volume : Measure ℝ) := by
  intro n h
  have hShift :
      StronglyMeasurable (fun x : ℝ => u n (x + h)) :=
    (D.meas_u n).comp_measurable (measurable_shift_add_right h)
  have hDiff :
      StronglyMeasurable (fun x : ℝ => u n (x + h) - u n x) :=
    hShift.sub (D.meas_u n)
  exact
    (hDiff.indicator
      (measurableSet_indicatorTranslationInterior T h)).aestronglyMeasurable

/-- KRF data pays the measurability source for the entry-boundary term. -/
theorem indicatorTranslationEnterTerm_aestronglyMeasurable_of_krf_data
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∀ n h,
      AEStronglyMeasurable
        (indicatorTranslationEnterTerm T u n h)
        (volume : Measure ℝ) := by
  intro n h
  have hShift :
      StronglyMeasurable (fun x : ℝ => u n (x + h)) :=
    (D.meas_u n).comp_measurable (measurable_shift_add_right h)
  exact
    (hShift.indicator
      (measurableSet_indicatorTranslationEnter T h)).aestronglyMeasurable

/-- KRF data pays the measurability source for the exit-boundary term. -/
theorem indicatorTranslationExitTerm_aestronglyMeasurable_of_krf_data
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∀ n h,
      AEStronglyMeasurable
        (indicatorTranslationExitTerm T u n h)
        (volume : Measure ℝ) := by
  intro n h
  have hNeg :
      StronglyMeasurable (fun x : ℝ => -u n x) :=
    (D.meas_u n).neg
  exact
    (hNeg.indicator
      (measurableSet_indicatorTranslationExit T h)).aestronglyMeasurable

/-- KRF data pays all formal measurability fields in the indicator-translation
source contract; callers must still prove the three smallness fields. -/
theorem indicatorTranslationDecompositionSources_of_krf_data_and_smallness
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hInteriorSmall :
      ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ n h, h ∈ U →
          eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
            (volume : Measure ℝ) < ENNReal.ofReal ε)
    (hEnterSmall :
      ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ n h, h ∈ U →
          eLpNorm (indicatorTranslationEnterTerm T u n h) 2
            (volume : Measure ℝ) < ENNReal.ofReal ε)
    (hExitSmall :
      ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ n h, h ∈ U →
          eLpNorm (indicatorTranslationExitTerm T u n h) 2
            (volume : Measure ℝ) < ENNReal.ofReal ε) :
    IndicatorTranslationDecompositionSources T u := by
  exact
    { interior_meas :=
        indicatorTranslationInteriorTerm_aestronglyMeasurable_of_krf_data D
      enter_meas :=
        indicatorTranslationEnterTerm_aestronglyMeasurable_of_krf_data D
      exit_meas :=
        indicatorTranslationExitTerm_aestronglyMeasurable_of_krf_data D
      interior_small := hInteriorSmall
      enter_small := hEnterSmall
      exit_small := hExitSmall }

/-- The right-exit set for translating the zero extension is trapped in the
two endpoint strips of width `|h|`. -/
private lemma indicatorTranslationExitSet_subset_boundaryIntervals
    (T h : ℝ) :
    {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T}
      ⊆ Set.Icc 0 |h| ∪ Set.Icc (T - |h|) T := by
  intro x hx
  rcases hx with ⟨hxI, hxExit⟩
  have hxBad : x + h < 0 ∨ T < x + h := by
    by_cases h0 : 0 ≤ x + h
    · have hTnot : ¬ (x + h ≤ T) := by
        intro hT
        exact hxExit ⟨h0, hT⟩
      exact Or.inr (lt_of_not_ge hTnot)
    · exact Or.inl (lt_of_not_ge h0)
  rcases hxBad with hLeft | hRight
  · left
    refine ⟨hxI.1, ?_⟩
    have hx_lt_neg : x < -h := by linarith
    exact le_trans (le_of_lt hx_lt_neg) (neg_le_abs h)
  · right
    refine ⟨?_, hxI.2⟩
    have hT_sub_h_lt : T - h < x := by linarith
    have hT_abs_le : T - |h| ≤ T - h := by
      linarith [le_abs_self h]
    exact le_trans hT_abs_le (le_of_lt hT_sub_h_lt)

/-- The one-dimensional exit strip for translating an interval has Lebesgue
measure tending to zero with the translation parameter. -/
theorem exit_strip_measure_small (T : ℝ) :
    ∀ η : ℝ, 0 < η → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ h, h ∈ U →
        (volume : Measure ℝ)
          {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T}
          ≤ ENNReal.ofReal η := by
  intro η hη
  refine ⟨Metric.ball (0 : ℝ) (η / 4),
    Metric.ball_mem_nhds (0 : ℝ) (by positivity), ?_⟩
  intro h hh
  have hh_abs : |h| < η / 4 := by
    simpa [Real.dist_eq] using hh
  have hMeasureLe :
      (volume : Measure ℝ)
          {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T}
        ≤ ENNReal.ofReal (2 * |h|) := by
    calc
      (volume : Measure ℝ)
          {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T}
          ≤ (volume : Measure ℝ)
              (Set.Icc 0 |h| ∪ Set.Icc (T - |h|) T) := by
            exact measure_mono
              (indicatorTranslationExitSet_subset_boundaryIntervals T h)
      _ ≤ (volume : Measure ℝ) (Set.Icc 0 |h|)
            + (volume : Measure ℝ) (Set.Icc (T - |h|) T) := by
            exact measure_union_le _ _
      _ = ENNReal.ofReal (2 * |h|) := by
            rw [Real.volume_Icc, Real.volume_Icc]
            have hsecond : T - (T - |h|) = |h| := by ring
            rw [sub_zero, hsecond]
            rw [← ENNReal.ofReal_add (abs_nonneg h) (abs_nonneg h)]
            congr 1
            ring
  exact hMeasureLe.trans
    (ENNReal.ofReal_le_ofReal (by nlinarith [abs_nonneg h, hh_abs]))

/-- The shifted entry-image strip has the same vanishing-volume receipt as
the exit strip, by applying `exit_strip_measure_small` to `-h`. -/
theorem shifted_entry_image_strip_measure_small (T : ℝ) :
    ∀ η : ℝ, 0 < η → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ h, h ∈ U →
        (volume : Measure ℝ)
          {x : ℝ | x ∈ Set.Icc 0 T ∧ x - h ∉ Set.Icc 0 T}
          ≤ ENNReal.ofReal η := by
  intro η hη
  rcases exit_strip_measure_small T η hη with ⟨U, hU, hUStrip⟩
  refine ⟨(fun h : ℝ => -h) ⁻¹' U, ?_, ?_⟩
  · have hneg :
        Tendsto (fun h : ℝ => -h) (𝓝 (0 : ℝ)) (𝓝 (0 : ℝ)) := by
      simpa using (continuous_neg.tendsto (0 : ℝ))
    exact hneg hU
  · intro h hh
    have hsmall := hUStrip (-h) hh
    simpa [sub_eq_add_neg] using hsmall

/-- Right translation by a real scalar preserves Lebesgue measure. -/
private lemma volume_measurePreserving_add_right (h : ℝ) :
    MeasurePreserving (fun x : ℝ => x + h)
      (volume : Measure ℝ) (volume : Measure ℝ) := by
  have hMP : MeasurePreserving (fun x : ℝ => h + x)
      (volume : Measure ℝ) (volume : Measure ℝ) :=
    measurePreserving_add_left (volume : Measure ℝ) h
  have hfun : (fun x : ℝ => h + x) = (fun x : ℝ => x + h) := by
    funext x
    exact add_comm h x
  exact hfun ▸ hMP

/-- Translating the true interior set
`{x | x ∈ [0,T] ∧ x+h ∈ [0,T]}` pushes its restricted Lebesgue measure
inside the `[0,T]`-restricted Lebesgue measure. -/
private lemma map_restrict_interior_add_right_le_restrict_Icc
    {T h : ℝ} :
    (((volume : Measure ℝ).restrict
      {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}).map
        (fun x : ℝ => x + h))
      ≤ (volume : Measure ℝ).restrict (Set.Icc 0 T) := by
  let s : Set ℝ := {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
  have hs : MeasurableSet s := by
    dsimp [s]
    exact measurableSet_indicatorTranslationInterior T h
  have hImageSubset : (fun x : ℝ => x + h) '' s ⊆ Set.Icc 0 T := by
    rintro y ⟨x, hx, rfl⟩
    exact hx.2
  let e : ℝ ≃ᵐ ℝ := (Homeomorph.addRight h).toMeasurableEquiv
  have hPreimageImage :
      (fun x : ℝ => x + h) ⁻¹' ((fun x : ℝ => x + h) '' s) = s := by
    exact Set.preimage_image_eq s (fun x y hxy => add_right_cancel hxy)
  have hRestrictMap :
      (((volume : Measure ℝ).restrict s).map (fun x : ℝ => x + h))
        =
      (((volume : Measure ℝ).map (fun x : ℝ => x + h)).restrict
        ((fun x : ℝ => x + h) '' s)) := by
    simpa [s, e, hPreimageImage] using
      (MeasurableEquiv.restrict_map e (volume : Measure ℝ)
        ((fun x : ℝ => x + h) '' s)).symm
  calc
    (((volume : Measure ℝ).restrict
      {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}).map
        (fun x : ℝ => x + h))
        = (((volume : Measure ℝ).map (fun x : ℝ => x + h)).restrict
            ((fun x : ℝ => x + h) '' s)) := by
          simpa [s] using hRestrictMap
    _ = (volume : Measure ℝ).restrict
          ((fun x : ℝ => x + h) '' s) := by
          rw [(volume_measurePreserving_add_right h).map_eq]
    _ ≤ (volume : Measure ℝ).restrict (Set.Icc 0 T) :=
          Measure.restrict_mono hImageSubset le_rfl

/-- KRF data itself supplies the localized restricted `MemLp` source for the
interior shifted difference. The shift is measured only on points whose source
and translate both remain in `[0,T]`, so the proof uses measure transport
rather than a full shifted-tail hypothesis on `[0,T]`. -/
theorem interior_shiftedDifference_memLp_of_krf_data
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∀ n h,
      MemLp (fun x : ℝ => u n (x + h) - u n x) 2
        ((volume : Measure ℝ).restrict
          {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}) := by
  intro n h
  let s : Set ℝ := {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
  have hsSubset : s ⊆ Set.Icc 0 T := by
    intro x hx
    exact hx.1
  have hUnshift :
      MemLp (u n) 2 ((volume : Measure ℝ).restrict s) :=
    (restrictedMemLp_of_krf_data D n).mono_measure
      (Measure.restrict_mono hsSubset le_rfl)
  have hMapLe :
      (((volume : Measure ℝ).restrict s).map (fun x : ℝ => x + h))
        ≤ (volume : Measure ℝ).restrict (Set.Icc 0 T) := by
    simpa [s] using
      (map_restrict_interior_add_right_le_restrict_Icc (T := T) (h := h))
  have hShiftBase :
      MemLp (u n) 2
        (((volume : Measure ℝ).restrict s).map (fun x : ℝ => x + h)) :=
    (restrictedMemLp_of_krf_data D n).mono_measure hMapLe
  have hShift :
      MemLp (fun x : ℝ => u n (x + h)) 2
        ((volume : Measure ℝ).restrict s) := by
    simpa [Function.comp_def] using
      hShiftBase.comp_of_map
        ((measurable_shift_add_right h).aemeasurable)
  exact hShift.sub hUnshift

/-- If the full-interval shifted square difference is integrable, its integral
over the true interior set is bounded by the `[0,T]` integral. The integrability
hypothesis is explicit because Mathlib's Bochner set-integral monotonicity
does not follow from a bare real integral bound. -/
theorem interior_translation_square_integral_le_interval_of_integrableOn
    {T : ℝ} {u : ℕ → ℝ → ℝ} {n : ℕ} {h : ℝ}
    (hIntegrable :
      IntegrableOn
        (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
        (Set.Icc 0 T) (volume : Measure ℝ)) :
    ∫ x in {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T},
        ‖u n (x + h) - u n x‖ ^ 2 ∂volume
      ≤
    ∫ x in Set.Icc 0 T, ‖u n (x + h) - u n x‖ ^ 2 ∂volume := by
  let s : Set ℝ := {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
  have hsSubsetAe : s ≤ᵐ[(volume : Measure ℝ)] Set.Icc 0 T :=
    ae_of_all (volume : Measure ℝ) (fun x hx => hx.1)
  have hNonneg :
      0 ≤ᵐ[((volume : Measure ℝ).restrict (Set.Icc 0 T))]
        (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2) :=
    Filter.Eventually.of_forall (fun x => by positivity)
  exact
    setIntegral_mono_set
      (μ := (volume : Measure ℝ))
      (f := fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
      (s := s)
      (t := Set.Icc 0 T)
      hIntegrable hNonneg hsSubsetAe

/-- Ambient `L²` membership is a sufficient source for the full-interval
shifted-square integrability receipt used by the KRF3 currency bridge. This is
not supplied by restricted KRF interval energy alone; it is a source adapter for
routes that already have ambient/support/zero-extension data. -/
theorem interval_shifted_square_integrable_of_ambient_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (hAmbientMem : ∀ n, MemLp (u n) 2 (volume : Measure ℝ)) :
    ∀ n h,
      IntegrableOn
        (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
        (Set.Icc 0 T) (volume : Measure ℝ) := by
  intro n h
  have hShift :
      MemLp (fun x : ℝ => u n (x + h)) 2 (volume : Measure ℝ) := by
    simpa [Function.comp_def] using
      (hAmbientMem n).comp_measurePreserving
        (volume_measurePreserving_add_right h)
  have hDiff :
      MemLp (fun x : ℝ => u n (x + h) - u n x) 2
        (volume : Measure ℝ) :=
    hShift.sub (hAmbientMem n)
  have hPow :
      Integrable
        (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
        (volume : Measure ℝ) := by
    simpa using hDiff.integrable_norm_pow (by norm_num : (2 : ℕ) ≠ 0)
  exact hPow.integrableOn

/-- Sidecar source needed when KRF3 is stated as a real Bochner integral over
`[0,T]`.

The current `KolmogorovRieszFrechetData.unif_translation` field gives the
small real integral bound but does not itself expose the `IntegrableOn`
certificate required by Mathlib's Bochner set-integral monotonicity theorem. -/
structure KRFTranslationIntegrabilitySource
    (T : ℝ) (u : ℕ → ℝ → ℝ) : Prop where
  interval_shifted_square_integrable :
    ∀ n h,
      IntegrableOn
        (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
        (Set.Icc 0 T) (volume : Measure ℝ)

/-- Repaired legacy KRF bundle surface: keep the current real-integral KRF3
field, but carry the missing shifted-square `IntegrableOn` witness explicitly. -/
structure KolmogorovRieszFrechetDataWithIntegrabilityKRF3
    (T : ℝ) (u : ℕ → ℝ → ℝ) : Prop
    extends KolmogorovRieszFrechetData ℝ T u where
  translation_integrability_source : KRFTranslationIntegrabilitySource T u

/-- Ambient `L²` membership supplies the sidecar integrability source for the
real-integral KRF3 route. -/
theorem krfTranslationIntegrabilitySource_of_ambient_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (hAmbientMem : ∀ n, MemLp (u n) 2 (volume : Measure ℝ)) :
    KRFTranslationIntegrabilitySource T u where
  interval_shifted_square_integrable :=
    interval_shifted_square_integrable_of_ambient_memLp hAmbientMem

/-- KRF data closes the interior smallness field once the full-interval shifted
square difference has the integrability witness needed to use Bochner
set-integral monotonicity. The localized `MemLp` witness itself is paid by
`interior_shiftedDifference_memLp_of_krf_data`. -/
theorem indicatorTranslationInteriorTerm_small_of_krf_data_and_interval_diff_integrable
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hIntervalDiffIntegrable :
      ∀ n h,
        IntegrableOn
          (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
          (Set.Icc 0 T) (volume : Measure ℝ)) :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε := by
  refine
    indicatorTranslationInteriorTerm_small_of_interior_integral_sources
      (T := T) (u := u)
      (interior_shiftedDifference_memLp_of_krf_data D) ?_
  intro η hη
  rcases D.unif_translation η hη with ⟨δ, hδ_pos, hδ⟩
  refine ⟨Metric.ball (0 : ℝ) δ, Metric.ball_mem_nhds 0 hδ_pos, ?_⟩
  intro n h hh
  have hh_abs : |h| < δ := by
    simpa [Metric.mem_ball, Real.dist_eq, abs_sub_comm] using hh
  exact lt_of_le_of_lt
    (interior_translation_square_integral_le_interval_of_integrableOn
      (T := T) (u := u) (n := n) (h := h)
      (hIntervalDiffIntegrable n h))
    (hδ n h hh_abs)

/-- KRF uniform integrability pays the exit-boundary smallness field once a
geometric receipt proves the exit strip has volume tending to zero. -/
theorem indicatorTranslationExitTerm_small_of_krf_data_and_exit_strip_measure
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hExitStripMeasure :
      ∀ η : ℝ, 0 < η → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ h, h ∈ U →
          (volume : Measure ℝ)
            {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T}
            ≤ ENNReal.ofReal η) :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationExitTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε := by
  intro ε hε
  have hεhalf : 0 < ε / 2 := by positivity
  rcases D.unif_integrable hεhalf with ⟨δ, hδ_pos, hδ⟩
  rcases hExitStripMeasure δ hδ_pos with ⟨U, hU, hUStrip⟩
  refine ⟨U, hU, ?_⟩
  intro n h hh
  let s : Set ℝ := {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T}
  have hs : MeasurableSet s := by
    simpa [s] using measurableSet_indicatorTranslationExit T h
  have hMeasureSmall : (volume : Measure ℝ) s ≤ ENNReal.ofReal δ := by
    simpa [s] using hUStrip h hh
  have hUI :
      eLpNorm
          (s.indicator
            ((fun n => Set.indicator (Set.Icc 0 T) (u n)) n))
          2 (volume : Measure ℝ)
        ≤ ENNReal.ofReal (ε / 2) :=
    hδ n s hs hMeasureSmall
  have hExitEq :
      indicatorTranslationExitTerm T u n h =
        (fun x : ℝ =>
          -s.indicator
            ((fun x : ℝ => Set.indicator (Set.Icc 0 T) (u n) x)) x) := by
    funext x
    by_cases hx : x ∈ s
    · have hxI : x ∈ Set.Icc 0 T := hx.1
      rw [indicatorTranslationExitTerm, Set.indicator_of_mem hx,
        Set.indicator_of_mem hx, Set.indicator_of_mem hxI]
    · rw [indicatorTranslationExitTerm, Set.indicator_of_notMem hx,
        Set.indicator_of_notMem hx]
      simp
  calc
    eLpNorm (indicatorTranslationExitTerm T u n h) 2
        (volume : Measure ℝ)
        =
      eLpNorm
        (s.indicator
          ((fun n => Set.indicator (Set.Icc 0 T) (u n)) n))
        2 (volume : Measure ℝ) := by
          rw [hExitEq]
          change
            eLpNorm
                (-(s.indicator
                  ((fun n => Set.indicator (Set.Icc 0 T) (u n)) n)))
                2 (volume : Measure ℝ)
              =
            eLpNorm
                (s.indicator
                  ((fun n => Set.indicator (Set.Icc 0 T) (u n)) n))
                2 (volume : Measure ℝ)
          rw [eLpNorm_neg]
    _ ≤ ENNReal.ofReal (ε / 2) := hUI
    _ < ENNReal.ofReal ε := by
          rw [ENNReal.ofReal_lt_ofReal_iff hε]
          linarith

/-- KRF uniform integrability alone pays the exit-boundary smallness field,
because the interval exit strip has vanishing one-dimensional volume. -/
theorem indicatorTranslationExitTerm_small_of_krf_data
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationExitTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε :=
  indicatorTranslationExitTerm_small_of_krf_data_and_exit_strip_measure D
    (exit_strip_measure_small T)

/-- KRF uniform integrability also pays the entry-boundary smallness field.
After the change of variables `y = x + h`, the entry term is a translated
indicator over the shifted entry-image strip, whose volume tends to zero. -/
theorem indicatorTranslationEnterTerm_small_of_krf_data
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u) :
    ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
      ∀ n h, h ∈ U →
        eLpNorm (indicatorTranslationEnterTerm T u n h) 2
          (volume : Measure ℝ) < ENNReal.ofReal ε := by
  intro ε hε
  have hεhalf : 0 < ε / 2 := by positivity
  rcases D.unif_integrable hεhalf with ⟨δ, hδ_pos, hδ⟩
  rcases shifted_entry_image_strip_measure_small T δ hδ_pos with
    ⟨U, hU, hUStrip⟩
  refine ⟨U, hU, ?_⟩
  intro n h hh
  let s : Set ℝ := {y : ℝ | y ∈ Set.Icc 0 T ∧ y - h ∉ Set.Icc 0 T}
  let g : ℝ → ℝ :=
    s.indicator ((fun n => Set.indicator (Set.Icc 0 T) (u n)) n)
  have hs : MeasurableSet s := by
    simpa [s, sub_eq_add_neg] using
      measurableSet_indicatorTranslationExit T (-h)
  have hMeasureSmall : (volume : Measure ℝ) s ≤ ENNReal.ofReal δ := by
    simpa [s] using hUStrip h hh
  have hBase :
      StronglyMeasurable
        ((fun n => Set.indicator (Set.Icc 0 T) (u n)) n) :=
    (D.meas_u n).indicator measurableSet_Icc
  have hgsm : AEStronglyMeasurable g (volume : Measure ℝ) := by
    exact (hBase.indicator hs).aestronglyMeasurable
  have hUI : eLpNorm g 2 (volume : Measure ℝ) ≤ ENNReal.ofReal (ε / 2) :=
    hδ n s hs hMeasureSmall
  have hEnterEq :
      indicatorTranslationEnterTerm T u n h =
        fun x : ℝ => g (x + h) := by
    funext x
    by_cases hx :
        x ∈ {x : ℝ | x ∉ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T}
    · have hyS : x + h ∈ s := by
        refine ⟨hx.2, ?_⟩
        intro hy
        have hxI : x ∈ Set.Icc 0 T := by
          simpa using hy
        exact hx.1 hxI
      rw [indicatorTranslationEnterTerm, Set.indicator_of_mem hx]
      change u n (x + h) = g (x + h)
      simp [g, hyS, hx.2]
    · have hyNot : x + h ∉ s := by
        intro hy
        have hxNot : x ∉ Set.Icc 0 T := by
          intro hxI
          exact hy.2 (by simpa using hxI)
        exact hx ⟨hxNot, hy.1⟩
      rw [indicatorTranslationEnterTerm, Set.indicator_of_notMem hx]
      change 0 = g (x + h)
      simp [g, hyNot]
  calc
    eLpNorm (indicatorTranslationEnterTerm T u n h) 2
        (volume : Measure ℝ)
        = eLpNorm (g ∘ fun x : ℝ => x + h) 2
            (volume : Measure ℝ) := by
          rw [hEnterEq]
          rfl
    _ = eLpNorm g 2 (volume : Measure ℝ) := by
          exact eLpNorm_comp_measurePreserving hgsm
            (volume_measurePreserving_add_right h)
    _ ≤ ENNReal.ofReal (ε / 2) := hUI
    _ < ENNReal.ofReal ε := by
          rw [ENNReal.ofReal_lt_ofReal_iff hε]
          linarith

/-- After the exit boundary is paid geometrically, the source contract only
needs interior and entry-boundary smallness as analytic inputs. -/
theorem indicatorTranslationDecompositionSources_of_krf_data_and_interior_enter
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hInteriorSmall :
      ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ n h, h ∈ U →
          eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
            (volume : Measure ℝ) < ENNReal.ofReal ε)
    (hEnterSmall :
      ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ n h, h ∈ U →
          eLpNorm (indicatorTranslationEnterTerm T u n h) 2
            (volume : Measure ℝ) < ENNReal.ofReal ε) :
    IndicatorTranslationDecompositionSources T u :=
  indicatorTranslationDecompositionSources_of_krf_data_and_smallness D
    hInteriorSmall hEnterSmall
    (indicatorTranslationExitTerm_small_of_krf_data D)

/-- After both boundary strips are paid by uniform integrability and interval
geometry, the source contract only needs the interior smallness input. -/
theorem indicatorTranslationDecompositionSources_of_krf_data_and_interior
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hInteriorSmall :
      ∀ ε : ℝ, 0 < ε → ∃ U ∈ 𝓝 (0 : ℝ),
        ∀ n h, h ∈ U →
          eLpNorm (indicatorTranslationInteriorTerm T u n h) 2
            (volume : Measure ℝ) < ENNReal.ofReal ε) :
    IndicatorTranslationDecompositionSources T u :=
  indicatorTranslationDecompositionSources_of_krf_data_and_interior_enter D
    hInteriorSmall
    (indicatorTranslationEnterTerm_small_of_krf_data D)

/-- KRF data pays the full indicator-translation source contract once the
remaining KRF3 currency debt is supplied as full-interval shifted-square
integrability. -/
theorem indicatorTranslationDecompositionSources_of_krf_data_and_interval_diff_integrable
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hIntervalDiffIntegrable :
      ∀ n h,
        IntegrableOn
          (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
          (Set.Icc 0 T) (volume : Measure ℝ)) :
    IndicatorTranslationDecompositionSources T u :=
  indicatorTranslationDecompositionSources_of_krf_data_and_interior D
    (indicatorTranslationInteriorTerm_small_of_krf_data_and_interval_diff_integrable
      D hIntervalDiffIntegrable)

/-- Named-source version of
`indicatorTranslationDecompositionSources_of_krf_data_and_interval_diff_integrable`.
It records the exact extra source needed by the real-integral KRF3 route. -/
theorem indicatorTranslationDecompositionSources_of_krf_data_and_translation_integrability_source
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (S : KRFTranslationIntegrabilitySource T u) :
    IndicatorTranslationDecompositionSources T u :=
  indicatorTranslationDecompositionSources_of_krf_data_and_interval_diff_integrable
    D S.interval_shifted_square_integrable

/-- Pointwise algebraic decomposition of the translated zero extension into
interior, entry-boundary, and exit-boundary terms. -/
theorem indicator_translation_decomposition_pointwise
    {T : ℝ} {u : ℕ → ℝ → ℝ} (n : ℕ) (h : ℝ) :
    (fun x =>
      Set.indicator (Set.Icc 0 T) (u n) (x + h) -
        Set.indicator (Set.Icc 0 T) (u n) x)
      =
    (fun x =>
      indicatorTranslationInteriorTerm T u n h x +
        indicatorTranslationEnterTerm T u n h x +
          indicatorTranslationExitTerm T u n h x) := by
  funext x
  by_cases hx : x ∈ Set.Icc 0 T
  · by_cases hxh : x + h ∈ Set.Icc 0 T
    · have hInteriorMem :
          x ∈ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} :=
        ⟨hx, hxh⟩
      have hEnterNot :
          x ∉ {x : ℝ | x ∉ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
        intro hxEnter
        exact hxEnter.1 hx
      have hExitNot :
          x ∉ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T} := by
        intro hxExit
        exact hxExit.2 hxh
      rw [Set.indicator_of_mem hxh, Set.indicator_of_mem hx,
        indicatorTranslationInteriorTerm, indicatorTranslationEnterTerm,
        indicatorTranslationExitTerm, Set.indicator_of_mem hInteriorMem,
        Set.indicator_of_notMem hEnterNot, Set.indicator_of_notMem hExitNot]
      simp
    · have hInteriorNot :
          x ∉ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
        intro hxInterior
        exact hxh hxInterior.2
      have hEnterNot :
          x ∉ {x : ℝ | x ∉ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
        intro hxEnter
        exact hxEnter.1 hx
      have hExitMem :
          x ∈ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T} :=
        ⟨hx, hxh⟩
      rw [Set.indicator_of_notMem hxh, Set.indicator_of_mem hx,
        indicatorTranslationInteriorTerm, indicatorTranslationEnterTerm,
        indicatorTranslationExitTerm, Set.indicator_of_notMem hInteriorNot,
        Set.indicator_of_notMem hEnterNot, Set.indicator_of_mem hExitMem]
      simp
  · by_cases hxh : x + h ∈ Set.Icc 0 T
    · have hInteriorNot :
          x ∉ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
        intro hxInterior
        exact hx hxInterior.1
      have hEnterMem :
          x ∈ {x : ℝ | x ∉ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} :=
        ⟨hx, hxh⟩
      have hExitNot :
          x ∉ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T} := by
        intro hxExit
        exact hx hxExit.1
      rw [Set.indicator_of_mem hxh, Set.indicator_of_notMem hx,
        indicatorTranslationInteriorTerm, indicatorTranslationEnterTerm,
        indicatorTranslationExitTerm, Set.indicator_of_notMem hInteriorNot,
        Set.indicator_of_mem hEnterMem, Set.indicator_of_notMem hExitNot]
      simp
    · have hInteriorNot :
          x ∉ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
        intro hxInterior
        exact hx hxInterior.1
      have hEnterNot :
          x ∉ {x : ℝ | x ∉ Set.Icc 0 T ∧ x + h ∈ Set.Icc 0 T} := by
        intro hxEnter
        exact hxh hxEnter.2
      have hExitNot :
          x ∉ {x : ℝ | x ∈ Set.Icc 0 T ∧ x + h ∉ Set.Icc 0 T} := by
        intro hxExit
        exact hx hxExit.1
      rw [Set.indicator_of_notMem hxh, Set.indicator_of_notMem hx,
        indicatorTranslationInteriorTerm, indicatorTranslationEnterTerm,
        indicatorTranslationExitTerm, Set.indicator_of_notMem hInteriorNot,
        Set.indicator_of_notMem hEnterNot, Set.indicator_of_notMem hExitNot]
      simp

/-- Interior plus boundary-strip sources imply ambient translation
equicontinuity for the zero-extended indicator family.

This is the precise reduction left by the KRF Phase-A attempt: prove the
three fields of `IndicatorTranslationDecompositionSources` from restricted
KRF translation and uniform integrability, or show which boundary field fails. -/
theorem translationEquicontinuousL2_indicator_of_decomposition_sources
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (hsrc : IndicatorTranslationDecompositionSources T u) :
    TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) := by
  intro ε hε
  have hεsixth : 0 < ε / 6 := by positivity
  rcases hsrc.interior_small (ε / 6) hεsixth with
    ⟨Uint, hUint, hIntSmall⟩
  rcases hsrc.enter_small (ε / 6) hεsixth with
    ⟨Uenter, hUenter, hEnterSmall⟩
  rcases hsrc.exit_small (ε / 6) hεsixth with
    ⟨Uexit, hUexit, hExitSmall⟩
  refine ⟨(Uint ∩ Uenter) ∩ Uexit,
    Filter.inter_mem (Filter.inter_mem hUint hUenter) hUexit, ?_⟩
  intro n h hh
  have hhInt : h ∈ Uint := hh.1.1
  have hhEnter : h ∈ Uenter := hh.1.2
  have hhExit : h ∈ Uexit := hh.2
  have hInt := hIntSmall n h hhInt
  have hEnter := hEnterSmall n h hhEnter
  have hExit := hExitSmall n h hhExit
  let interior := indicatorTranslationInteriorTerm T u n h
  let enter := indicatorTranslationEnterTerm T u n h
  let exit := indicatorTranslationExitTerm T u n h
  have hMainLe :
      eLpNorm
          (fun x =>
            Set.indicator (Set.Icc 0 T) (u n) (x + h) -
              Set.indicator (Set.Icc 0 T) (u n) x)
          2 (volume : Measure ℝ)
        ≤ eLpNorm interior 2 (volume : Measure ℝ) +
          eLpNorm enter 2 (volume : Measure ℝ) +
            eLpNorm exit 2 (volume : Measure ℝ) := by
    rw [indicator_translation_decomposition_pointwise (T := T) (u := u) n h]
    calc
      eLpNorm (fun x => interior x + enter x + exit x) 2
          (volume : Measure ℝ)
          ≤ eLpNorm (fun x => interior x + enter x) 2
              (volume : Measure ℝ) +
            eLpNorm exit 2 (volume : Measure ℝ) := by
              simpa [interior, enter, exit, Pi.add_apply, add_assoc] using
                eLpNorm_add_le
                  ((hsrc.interior_meas n h).add (hsrc.enter_meas n h))
                  (hsrc.exit_meas n h)
                  (by norm_num : 1 ≤ (2 : ENNReal))
      _ ≤ (eLpNorm interior 2 (volume : Measure ℝ) +
              eLpNorm enter 2 (volume : Measure ℝ)) +
            eLpNorm exit 2 (volume : Measure ℝ) := by
              simpa [interior, enter, add_comm, add_left_comm, add_assoc] using
                add_le_add_right
                  (eLpNorm_add_le
                    (hsrc.interior_meas n h)
                    (hsrc.enter_meas n h)
                    (by norm_num : 1 ≤ (2 : ENNReal)))
                  (eLpNorm exit 2 (volume : Measure ℝ))
      _ = eLpNorm interior 2 (volume : Measure ℝ) +
          eLpNorm enter 2 (volume : Measure ℝ) +
            eLpNorm exit 2 (volume : Measure ℝ) := by
            rw [add_assoc]
  have hSixthNonneg : 0 ≤ ε / 6 := le_of_lt hεsixth
  have hTwoSixthsNonneg : 0 ≤ ε / 6 + ε / 6 :=
    add_nonneg hSixthNonneg hSixthNonneg
  have hSixthSum :
      ENNReal.ofReal (ε / 6) + ENNReal.ofReal (ε / 6) +
          ENNReal.ofReal (ε / 6) =
        ENNReal.ofReal (ε / 2) := by
    calc
      ENNReal.ofReal (ε / 6) + ENNReal.ofReal (ε / 6) +
          ENNReal.ofReal (ε / 6)
          =
        ENNReal.ofReal (ε / 6 + ε / 6) +
          ENNReal.ofReal (ε / 6) := by
            rw [ENNReal.ofReal_add hSixthNonneg hSixthNonneg]
      _ = ENNReal.ofReal (ε / 6 + ε / 6 + ε / 6) := by
            rw [ENNReal.ofReal_add hTwoSixthsNonneg hSixthNonneg]
      _ = ENNReal.ofReal (ε / 2) := by
            congr 1
            ring
  simpa using lt_of_le_of_lt hMainLe (by
    calc
      eLpNorm interior 2 (volume : Measure ℝ) +
          eLpNorm enter 2 (volume : Measure ℝ) +
            eLpNorm exit 2 (volume : Measure ℝ)
          ≤
        ENNReal.ofReal (ε / 6) + ENNReal.ofReal (ε / 6) +
          ENNReal.ofReal (ε / 6) := by
            exact add_le_add (add_le_add hInt.le hEnter.le) hExit.le
      _ = ENNReal.ofReal (ε / 2) := hSixthSum
      _ < ENNReal.ofReal ε := by
            rw [ENNReal.ofReal_lt_ofReal_iff hε]
            linarith)

/-- KRF data plus the explicit shifted-square integrability receipt pays the
ambient `L²` translation equicontinuity of the zero-extended indicator family.
This is the exact source consumed by the MLG-2 Phase-A bridge. -/
theorem translationEquicontinuousL2_indicator_of_krf_data_and_interval_diff_integrable
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hIntervalDiffIntegrable :
      ∀ n h,
        IntegrableOn
          (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
          (Set.Icc 0 T) (volume : Measure ℝ)) :
    TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) :=
  translationEquicontinuousL2_indicator_of_decomposition_sources
    (indicatorTranslationDecompositionSources_of_krf_data_and_interval_diff_integrable
      D hIntervalDiffIntegrable)

/-- Named-source version of the real-integral KRF3 route to ambient
translation equicontinuity. -/
theorem translationEquicontinuousL2_indicator_of_krf_data_and_translation_integrability_source
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (S : KRFTranslationIntegrabilitySource T u) :
    TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) :=
  translationEquicontinuousL2_indicator_of_decomposition_sources
    (indicatorTranslationDecompositionSources_of_krf_data_and_translation_integrability_source
      D S)

/-- Ambient `L²` membership is a sufficient source for ambient translation
equicontinuity of the KRF zero-extension, once the restricted KRF data is
available. -/
theorem translationEquicontinuousL2_indicator_of_krf_data_and_ambient_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hAmbientMem : ∀ n, MemLp (u n) 2 (volume : Measure ℝ)) :
    TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) :=
  translationEquicontinuousL2_indicator_of_krf_data_and_interval_diff_integrable
    D (interval_shifted_square_integrable_of_ambient_memLp hAmbientMem)

/-- If the original KRF family is genuinely supported in `[0,T]`, then the
restricted KRF `MemLp` source upgrades to the ambient source needed by the
indicator-translation bridge. -/
theorem translationEquicontinuousL2_indicator_of_krf_data_and_support
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hsupport : ∀ n x, x ∉ Set.Icc 0 T → u n x = 0) :
    TranslationEquicontinuousL2 ℝ (volume : Measure ℝ)
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) := by
  have hRestrict :
      ∀ n, MemLp (u n) p2 (volume.restrict (Set.Icc 0 T)) := by
    intro n
    simpa [p2] using restrictedMemLp_of_krf_data D n
  have hAmbientP2 :
      ∀ n, MemLp (u n) p2 (volume : Measure ℝ) :=
    ambient_memLp_of_restricted_memLp_support hRestrict hsupport
  have hAmbient :
      ∀ n, MemLp (u n) 2 (volume : Measure ℝ) := by
    intro n
    simpa [p2] using hAmbientP2 n
  exact
    translationEquicontinuousL2_indicator_of_krf_data_and_ambient_memLp
      D hAmbient

/-- Full-interval shifted-square integrability packages the ambient
translation route into the native `eLpNorm` KRF3 source. -/
theorem krfIndicatorTranslationELpNormSource_of_krf_data_and_interval_diff_integrable
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hIntervalDiffIntegrable :
      ∀ n h,
        IntegrableOn
          (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
          (Set.Icc 0 T) (volume : Measure ℝ)) :
    KRFIndicatorTranslationELpNormSource T u :=
  krfIndicatorTranslationELpNormSource_of_translationEquicontinuousL2
    (translationEquicontinuousL2_indicator_of_krf_data_and_interval_diff_integrable
      D hIntervalDiffIntegrable)

/-- The named legacy integrability sidecar pays the native `eLpNorm` KRF3
source. -/
theorem krfIndicatorTranslationELpNormSource_of_krf_data_and_integrability_source
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (S : KRFTranslationIntegrabilitySource T u) :
    KRFIndicatorTranslationELpNormSource T u :=
  krfIndicatorTranslationELpNormSource_of_translationEquicontinuousL2
    (translationEquicontinuousL2_indicator_of_krf_data_and_translation_integrability_source
      D S)

/-- Ambient `L²` membership is a direct source for the native `eLpNorm` KRF3
currency once the restricted KRF data is present. -/
theorem krfIndicatorTranslationELpNormSource_of_krf_data_and_ambient_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hAmbientMem : ∀ n, MemLp (u n) 2 (volume : Measure ℝ)) :
    KRFIndicatorTranslationELpNormSource T u :=
  krfIndicatorTranslationELpNormSource_of_translationEquicontinuousL2
    (translationEquicontinuousL2_indicator_of_krf_data_and_ambient_memLp
      D hAmbientMem)

/-- If the original family is supported on `[0,T]`, the restricted KRF data
pays the preferred native `eLpNorm` KRF3 source. -/
theorem krfIndicatorTranslationELpNormSource_of_krf_data_and_support
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hsupport : ∀ n x, x ∉ Set.Icc 0 T → u n x = 0) :
    KRFIndicatorTranslationELpNormSource T u :=
  krfIndicatorTranslationELpNormSource_of_translationEquicontinuousL2
    (translationEquicontinuousL2_indicator_of_krf_data_and_support
      D hsupport)

/-- The legacy repaired bundle with an explicit shifted-square integrability
sidecar canonically upgrades to the preferred native `eLpNorm` KRF3 bundle. -/
theorem eLpNormKRF3_of_integrabilityKRF3
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithIntegrabilityKRF3 T u) :
    KolmogorovRieszFrechetDataWithELpNormKRF3 T u where
  toKolmogorovRieszFrechetData := D.toKolmogorovRieszFrechetData
  indicator_translation_source :=
    krfIndicatorTranslationELpNormSource_of_krf_data_and_integrability_source
      D.toKolmogorovRieszFrechetData D.translation_integrability_source

/-- Ambient `L²` membership upgrades ordinary KRF data to the preferred native
`eLpNorm` KRF3 bundle. -/
theorem eLpNormKRF3_of_krf_data_and_ambient_memLp
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hAmbientMem : ∀ n, MemLp (u n) 2 (volume : Measure ℝ)) :
    KolmogorovRieszFrechetDataWithELpNormKRF3 T u where
  toKolmogorovRieszFrechetData := D
  indicator_translation_source :=
    krfIndicatorTranslationELpNormSource_of_krf_data_and_ambient_memLp
      D hAmbientMem

/-- Support of the original family on `[0,T]` upgrades ordinary KRF data to
the preferred native `eLpNorm` KRF3 bundle. -/
theorem eLpNormKRF3_of_krf_data_and_support
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hsupport : ∀ n x, x ∉ Set.Icc 0 T → u n x = 0) :
    KolmogorovRieszFrechetDataWithELpNormKRF3 T u where
  toKolmogorovRieszFrechetData := D
  indicator_translation_source :=
    krfIndicatorTranslationELpNormSource_of_krf_data_and_support
      D hsupport

/-- Conditional KRF Phase-A closure for the zero-extended indicator family
under the now-isolated KRF3 integrability receipt. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_interval_diff_integrable
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hIntervalDiffIntegrable :
      ∀ n h,
        IntegrableOn
          (fun x : ℝ => ‖u n (x + h) - u n x‖ ^ 2)
          (Set.Icc 0 T) (volume : Measure ℝ)) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) :=
  UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_translation
    Φ D
    (translationEquicontinuousL2_indicator_of_krf_data_and_interval_diff_integrable
      D hIntervalDiffIntegrable)

/-- Conditional KRF Phase-A closure for the real-integral KRF3 route, with the
missing Bochner integrability witness named as a source object. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_integrability_source
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (S : KRFTranslationIntegrabilitySource T u) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) :=
  UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_translation
    Φ D
    (translationEquicontinuousL2_indicator_of_krf_data_and_translation_integrability_source
      D S)

/-- Phase-A closure from the repaired legacy KRF3 bundle surface. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_integrabilityKRF3
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithIntegrabilityKRF3 T u) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) :=
  UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_integrability_source
    Φ D.toKolmogorovRieszFrechetData D.translation_integrability_source

/-- Conditional KRF Phase-A closure for routes that supply ambient `L²`
membership of the source family. Restricted interval KRF energy alone does not
provide this hypothesis; support or zero-extension data must pay it. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_ambient_memLp
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hAmbientMem : ∀ n, MemLp (u n) 2 (volume : Measure ℝ)) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) :=
  UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_translation
    Φ D
    (translationEquicontinuousL2_indicator_of_krf_data_and_ambient_memLp
      D hAmbientMem)

/-- KRF Phase-A closure for the zero-extended indicator family when the
underlying source family is actually supported in `[0,T]`. -/
theorem UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_support
    {T : ℝ}
    (Φ : MollifierFamily ℝ ℕ atTop)
    {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T u)
    (hsupport : ∀ n x, x ∉ Set.Icc 0 T → u n x = 0) :
    UniformScaleApproximationELpNormRealOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n))
      (fun k n t =>
        mollifierFamilySmoothAt Φ
          (fun m => Set.indicator (Set.Icc 0 T) (u m)) k n t) :=
  UniformScaleApproximationELpNormRealOutput_of_krf_data_indicator_of_translation
    Φ D
    (translationEquicontinuousL2_indicator_of_krf_data_and_support D hsupport)

/-- Concrete `MollifierFamily` route to the preferred upstream KRF/Cantor
source contract.

The selected row-20 family is `φ0 ∘ σ`; the Arzelà/Cantor smoothed family is
sampled at scale `σ n`, i.e. `mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n))`.
The theorem packages the handoff once the same-family uniform-on-compacts
source has been supplied. -/
theorem krfUnarySmoothedLimitSourceOutput_mollifierFamily_arzela_subseq
    {B : Type v} [NormedAddCommGroup B] [NormedSpace ℝ B] [CompleteSpace B]
    [MeasurableSpace B] [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => mollifierFamilySmoothAt Φ u k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm
              (fun t => mollifierFamilySmoothAt Φ u k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            limit t - mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t => mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
          limit atTop K) :
    KRFUnarySmoothedLimitSourceOutput T u :=
  KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_real_tendsto_and_smoothed_limit
    (φ0 ∘ σ) (hφ0.comp hσ)
    (selectedRestrictedMemLp_of_krf_data D (φ0 ∘ σ))
    (mollifierFamilySmoothAt Φ u) σ hσ.tendsto_atTop
    (UniformScaleApproximationELpNormRealOutput_of_one_sided
      hApproxMeas hApproxRate)
    (LinkedSmoothedLimitELpNormOutput_of_real
      (LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_compacts
        hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts))

/-- Row-20 a.e. extraction from the checked uniform Phase-A source and an
actual Arzelà/Cantor subsequence.

This is the Clay-facing endpoint of the Phase-A bridge in this file: callers
may now provide the single uniform-scale source contract instead of reopening
its measurability and one-sided rate fields.  The remaining analytic source
obligation is deliberately visible: uniform convergence on compacts for the
same smoothed family `smoothAt (σ n) (φ0 (σ n))`. -/
theorem ae_subsequence_of_krf_data_uniform_phaseA_arzela_subseq_krf_mem
    {B : Type v} [NormedAddCommGroup B] [MeasurableSpace B]
    [BorelSpace B] [SecondCountableTopology B] [CompleteSpace B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (smoothAt : ℕ → ℕ → ℝ → B)
    (hApprox : UniformScaleApproximationELpNormRealOutput T u smoothAt)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => smoothAt (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t => limit t - smoothAt (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t => smoothAt (σ n) (φ0 (σ n)) t) limit atTop K) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) := by
  rcases hApprox with ⟨_hLeftMeas, hRightMeas, _hLeftRate, hRightRate⟩
  exact ae_subsequence_of_krf_data_one_sided_rate_arzela_subseq_krf_mem
    D φ0 σ hφ0 hσ smoothAt hRightMeas hRightRate limit
    hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts

/-- Direct row-20 consumer for the concrete `MollifierFamily` smoothing and an
actual Arzelà/Cantor subsequence alignment.

This is the stable version of the LeanMill sidecar closure: after the one-sided
uniform Phase-A source and the same-family all-compact Arzelà/Cantor source are
paid for `mollifierFamilySmoothAt`, the row-20 a.e. subsequence conclusion is
already kernel-clean. -/
theorem ae_subsequence_of_krf_data_mollifierFamily_arzela_subseq_krf_mem
    {B : Type v} [NormedAddCommGroup B] [NormedSpace ℝ B] [CompleteSpace B]
    [MeasurableSpace B] [BorelSpace B] [SecondCountableTopology B]
    {T : ℝ} {u : ℕ → ℝ → B}
    (D : KolmogorovRieszFrechetData B T u)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => mollifierFamilySmoothAt Φ u k n t - u n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hApproxRate :
      ∀ ε : ℝ, 0 < ε →
        ∀ᶠ k in atTop,
          ∀ n,
            eLpNorm
              (fun t => mollifierFamilySmoothAt Φ u k n t - u n t)
              2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) <
              ENNReal.ofReal ε)
    (limit : ℝ → B)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            limit t - mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t => mollifierFamilySmoothAt Φ u (σ n) (φ0 (σ n)) t)
          limit atTop K) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → B),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_one_sided_rate_arzela_subseq_krf_mem
    D φ0 σ hφ0 hσ (mollifierFamilySmoothAt Φ u)
    hApproxMeas hApproxRate limit
    hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts

/-- Direct row-20 consumer for the checked MLG-2/KRF Phase-A theorem plus the
same-family Arzelà/Cantor source, specialized to real-valued families.

This is the concrete endpoint after the uniform Phase-A closure in this file:
translation equicontinuity and the finite uniform `L²` envelope pay the
`MollifierFamily` approximation source; the only remaining source hypotheses
are smoothed-limit measurability and all-compact uniform convergence for the
same sampled smoothing family. -/
theorem ae_subsequence_of_krf_data_mlg2_mollifierFamily_arzela_subseq_krf_mem
    {T : ℝ} {f : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetData ℝ T f)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (hApproxMeas :
      ∀ k n : ℕ,
        AEStronglyMeasurable
          (fun t => mollifierFamilySmoothAt Φ f k n t - f n t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    {A : ENNReal}
    (hf_memLp : ∀ n, MemLp (f n) p2 (volume : Measure ℝ))
    (hf_unif : TranslationEquicontinuousL2 ℝ (volume : Measure ℝ) f)
    (hA : ∀ n, eLpNorm (f n) p2 (volume : Measure ℝ) ≤ A)
    (hA_ne_top : A ≠ ⊤)
    (limit : ℝ → ℝ)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            mollifierFamilySmoothAt Φ f (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            limit t - mollifierFamilySmoothAt Φ f (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t => mollifierFamilySmoothAt Φ f (σ n) (φ0 (σ n)) t)
          limit atTop K) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → ℝ),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => f (ψ n) t) atTop (𝓝 (uInf t)) :=
  ae_subsequence_of_krf_data_uniform_phaseA_arzela_subseq_krf_mem
    D φ0 σ hφ0 hσ (mollifierFamilySmoothAt Φ f)
    (UniformScaleApproximationELpNormRealOutput_of_mlg2_krf_mollifierFamily
      Φ hApproxMeas hf_memLp hf_unif hA hA_ne_top)
    limit hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts

/-- Repaired KRF3 currency plus a same-family sampled Arzelà/Cantor source
assembles the preferred unary row-20 producer for the zero-extended interval
family.

This is deliberately stated for the exact zero-extension family used by the
`eLpNorm` KRF3 source.  It does not mix an original-family smoothed limit with
the indicator-family Phase-A theorem; callers that want an a.e. conclusion for
the original family still need the downstream same-family adapter. -/
theorem krfUnarySmoothedLimitSourceOutput_indicator_of_eLpNormKRF3_mollifierFamily_arzela_subseq
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithELpNormKRF3 T u)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (limit : ℝ → ℝ)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            limit t -
              mollifierFamilySmoothAt Φ
                (fun m => Set.indicator (Set.Icc 0 T) (u m))
                (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ n) (φ0 (σ n)) t)
          limit atTop K) :
    KRFUnarySmoothedLimitSourceOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) := by
  have hIndicatorMemAmbient :
      ∀ n,
        MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2
          (MeasureTheory.volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq
      D.toKolmogorovRieszFrechetData
      D.toKolmogorovRieszFrechetData.integrable_norm_sq
  have hIndicatorMemRestrict :
      ∀ n,
        MemLp
          ((fun m => Set.indicator (Set.Icc 0 T) (u m)) ((φ0 ∘ σ) n))
          2 (MeasureTheory.volume.restrict (Set.Icc 0 T)) := by
    intro n
    exact
      (hIndicatorMemAmbient ((φ0 ∘ σ) n)).mono_measure
        Measure.restrict_le_self
  exact
    KRFUnarySmoothedLimitSourceOutput_of_uniform_scale_real_tendsto_and_smoothed_limit
      (φ0 ∘ σ) (hφ0.comp hσ) hIndicatorMemRestrict
      (mollifierFamilySmoothAt Φ
        (fun m => Set.indicator (Set.Icc 0 T) (u m)))
      σ hσ.tendsto_atTop
      (UniformScaleApproximationELpNormRealOutput_of_krf_eLpNormKRF3 Φ D)
      (LinkedSmoothedLimitELpNormOutput_of_real
        (LinkedSmoothedLimitELpNormRealOutput_of_tendstoUniformlyOn_compacts
          hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts))

/-- Linked `eLpNorm` producer form of
`krfUnarySmoothedLimitSourceOutput_indicator_of_eLpNormKRF3_mollifierFamily_arzela_subseq`.

The output is still for the zero-extended family, making the same-family
currency boundary explicit for the final row-20 a.e. consumer. -/
theorem linkedKRFELpNormProducerOutput_indicator_of_eLpNormKRF3_mollifierFamily_arzela_subseq
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithELpNormKRF3 T u)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (limit : ℝ → ℝ)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            limit t -
              mollifierFamilySmoothAt Φ
                (fun m => Set.indicator (Set.Icc 0 T) (u m))
                (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ n) (φ0 (σ n)) t)
          limit atTop K) :
    LinkedKRFELpNormProducerOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) :=
  linkedKRFELpNormProducerOutput_of_unary_smoothed_limit_source_output
    (krfUnarySmoothedLimitSourceOutput_indicator_of_eLpNormKRF3_mollifierFamily_arzela_subseq
      D Φ φ0 σ hφ0 hσ limit
      hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts)

/-- Repaired KRF3 plus a same-family sampled Arzelà/Cantor source reaches the
row-20 a.e. subsequence endpoint on `[0,T]` for the original family.

The proof routes through the zero-extended indicator family, where the repaired
KRF3 Phase-A source lives, and then uses `ae_restrict_mem` to remove the
indicator on the restricted interval measure. -/
theorem ae_subsequence_of_krf_eLpNormKRF3_mollifierFamily_arzela_subseq
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithELpNormKRF3 T u)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (limit : ℝ → ℝ)
    (hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ n) (φ0 (σ n)) t - limit t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            limit t -
              mollifierFamilySmoothAt Φ
                (fun m => Set.indicator (Set.Icc 0 T) (u m))
                (σ n) (φ0 (σ n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)))
    (hSmoothUniformCompacts :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ n) (φ0 (σ n)) t)
          limit atTop K) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → ℝ),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) := by
  let v : ℕ → ℝ → ℝ :=
    fun n => Set.indicator (Set.Icc 0 T) (u n)
  have hLinked : LinkedKRFELpNormProducerOutput T v := by
    dsimp [v]
    exact
      linkedKRFELpNormProducerOutput_indicator_of_eLpNormKRF3_mollifierFamily_arzela_subseq
        D Φ φ0 σ hφ0 hσ limit
        hSmoothLeftMeas hSmoothRightMeas hSmoothUniformCompacts
  have hMeasV : ∀ n, StronglyMeasurable (v n) := by
    intro n
    dsimp [v]
    exact (D.toKolmogorovRieszFrechetData.meas_u n).indicator
      (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
  rcases ae_subsequence_of_linked_eLpNorm_producer_source_measurable
      hMeasV hLinked with
    ⟨ψ, hψ, uInf, hAE⟩
  refine ⟨ψ, hψ, uInf, ?_⟩
  filter_upwards [
    hAE,
    MeasureTheory.ae_restrict_mem
      (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
  ] with t htend ht_mem
  exact htend.congr' (Filter.Eventually.of_forall fun n => by
    dsimp [v]
    simp [Set.indicator_of_mem ht_mem])

/-- Repaired KRF3 plus explicit sampled derivative and pointwise budgets pays
the row-20 unary smoothed-limit source for the zero-extended indicator family.

This composes the sampled Arzelà source-packaging theorem with the existing
row-20 producer.  The analytic sampled derivative and pointwise bounds remain
the exposed hard source; this theorem removes the remaining formalization
assembly around that source. -/
theorem krfUnary_indicator_of_eLpNormKRF3_mollifierFamily_deriv_source
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithELpNormKRF3 T u)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (hderiv :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b C : ℝ),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            |deriv
              (fun t : ℝ =>
                mollifierFamilySmoothAt Φ
                  (fun m => Set.indicator (Set.Icc 0 T) (u m))
                  (σ n) (φ0 (σ n)) t) x| ≤ C))
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ
            (fun m => Set.indicator (Set.Icc 0 T) (u m))
            (σ n) (φ0 (σ n)) t| ≤ C) :
    KRFUnarySmoothedLimitSourceOutput T
      (fun n => Set.indicator (Set.Icc 0 T) (u n)) := by
  rcases
      indicator_sampled_arzela_subseq_of_deriv_abs_bound_pointwise_abs_bound
        Φ u D.toKolmogorovRieszFrechetData φ0 σ hderiv hbound with
    ⟨ψ, g, hψ, hg, hUniform⟩
  let σ' : ℕ → ℕ := fun n => σ (ψ n)
  have hσ' : StrictMono σ' := hσ.comp hψ
  have hMemTwo :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) 2
        (volume : Measure ℝ) :=
    indicator_memLp_of_krf_integrableOn_norm_sq
      D.toKolmogorovRieszFrechetData
      D.toKolmogorovRieszFrechetData.integrable_norm_sq
  have hMem :
      ∀ n, MemLp (Set.indicator (Set.Icc 0 T) (u n)) p2
        (volume : Measure ℝ) := by
    intro n
    simpa [p2] using hMemTwo n
  have hSmoothContinuous :
      ∀ n : ℕ,
        Continuous
          (fun t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ' n) (φ0 (σ' n)) t) := by
    intro n
    exact
      continuous_mollifierFamilySmoothAt_of_memLp_two_volume
        Φ hMem (σ' n) (φ0 (σ' n))
  have hSmoothLeftMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ' n) (φ0 (σ' n)) t - g t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)) := by
    intro n
    exact ((hSmoothContinuous n).sub hg).aestronglyMeasurable.restrict
  have hSmoothRightMeas :
      ∀ n : ℕ,
        AEStronglyMeasurable
          (fun t =>
            g t -
              mollifierFamilySmoothAt Φ
                (fun m => Set.indicator (Set.Icc 0 T) (u m))
                (σ' n) (φ0 (σ' n)) t)
          (MeasureTheory.volume.restrict (Set.Icc 0 T)) := by
    intro n
    exact (hg.sub (hSmoothContinuous n)).aestronglyMeasurable.restrict
  have hUniform' :
      ∀ K : Set ℝ, IsCompact K →
        TendstoUniformlyOn
          (fun n t =>
            mollifierFamilySmoothAt Φ
              (fun m => Set.indicator (Set.Icc 0 T) (u m))
              (σ' n) (φ0 (σ' n)) t)
          g atTop K := by
    intro K hK
    simpa [σ'] using hUniform K hK
  exact
    krfUnarySmoothedLimitSourceOutput_indicator_of_eLpNormKRF3_mollifierFamily_arzela_subseq
      D Φ φ0 σ' hφ0 hσ' g
      hSmoothLeftMeas hSmoothRightMeas hUniform'

/-- Repaired KRF3 plus explicit sampled derivative and pointwise budgets reaches
the row-20 a.e. subsequence endpoint on `[0,T]`.

The conclusion is still conditional on the hard analytic sampled derivative and
pointwise source bounds; those are now the only compactness-source assumptions
exposed by this formal assembly. -/
theorem ae_subsequence_of_krf_eLpNormKRF3_mollifierFamily_deriv_source
    {T : ℝ} {u : ℕ → ℝ → ℝ}
    (D : KolmogorovRieszFrechetDataWithELpNormKRF3 T u)
    (Φ : MollifierFamily ℝ ℕ atTop)
    (φ0 σ : ℕ → ℕ) (hφ0 : StrictMono φ0) (hσ : StrictMono σ)
    (hderiv :
      ∀ K : Set ℝ, IsCompact K →
        ∃ (a b C : ℝ),
          K ⊆ Set.Icc a b ∧
          (∀ n x, x ∈ Set.Icc a b →
            |deriv
              (fun t : ℝ =>
                mollifierFamilySmoothAt Φ
                  (fun m => Set.indicator (Set.Icc 0 T) (u m))
                  (σ n) (φ0 (σ n)) t) x| ≤ C))
    (hbound :
      ∀ t : ℝ, ∃ C : ℝ, ∀ n,
        |mollifierFamilySmoothAt Φ
            (fun m => Set.indicator (Set.Icc 0 T) (u m))
            (σ n) (φ0 (σ n)) t| ≤ C) :
    ∃ (ψ : ℕ → ℕ), StrictMono ψ ∧
    ∃ (uInf : ℝ → ℝ),
      ∀ᵐ t ∂(MeasureTheory.volume.restrict (Set.Icc 0 T)),
        Tendsto (fun n => u (ψ n) t) atTop (𝓝 (uInf t)) := by
  let v : ℕ → ℝ → ℝ :=
    fun n => Set.indicator (Set.Icc 0 T) (u n)
  have hLinked : LinkedKRFELpNormProducerOutput T v := by
    dsimp [v]
    exact
      linkedKRFELpNormProducerOutput_of_unary_smoothed_limit_source_output
        (krfUnary_indicator_of_eLpNormKRF3_mollifierFamily_deriv_source
          D Φ φ0 σ hφ0 hσ hderiv hbound)
  have hMeasV : ∀ n, StronglyMeasurable (v n) := by
    intro n
    dsimp [v]
    exact (D.toKolmogorovRieszFrechetData.meas_u n).indicator
      (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
  rcases ae_subsequence_of_linked_eLpNorm_producer_source_measurable
      hMeasV hLinked with
    ⟨ψ, hψ, uInf, hAE⟩
  refine ⟨ψ, hψ, uInf, ?_⟩
  filter_upwards [
    hAE,
    MeasureTheory.ae_restrict_mem
      (measurableSet_Icc : MeasurableSet (Set.Icc 0 T))
  ] with t htend ht_mem
  exact htend.congr' (Filter.Eventually.of_forall fun n => by
    dsimp [v]
    simp [Set.indicator_of_mem ht_mem])

/-- Pointwise KRF Phase-A approximate identity on the real line.

For any `L²` function, convolution against the KRF `MollifierFamily` kernel
converges to the original function in p=2 `eLpNorm`.  This is the paid
pointwise Phase-A theorem; the full KRF compactness chain still needs the
uniform-in-family version consumed by `UniformScaleApproximationELpNormRealOutput`.
-/
theorem eLpNorm_two_real_mollifier_limit_of_krf_mollifierFamily_memLp
    {ι E : Type*} {l : Filter ι}
    [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    [MeasurableSpace E] [BorelSpace E] [SecondCountableTopology E]
    (Φ : MollifierFamily ℝ ι l) {f : ℝ → E}
    (hf : MemLp f p2 (volume : Measure ℝ)) :
    Tendsto
      (fun i =>
        eLpNorm
          (fun x : ℝ =>
            (∫ y, Φ.kernel (volume : Measure ℝ) i y • f (x - y) ∂volume) - f x)
          p2 (volume : Measure ℝ))
      l (𝓝 0) := by
  refine eLpNorm_two_real_mollifier_limit_of_nonneg_unit_tail_memLp
    (ρ := fun i => Φ.kernel (volume : Measure ℝ) i)
    (f := f)
    ?hcont ?hcomp ?hint ?hnonneg ?hone hf
    (tail_concentration_krf_mollifierFamily_real Φ)
  · intro i
    exact (Φ.bump i).continuous_normed (μ := (volume : Measure ℝ))
  · intro i
    exact (Φ.bump i).hasCompactSupport_normed (μ := (volume : Measure ℝ))
  · intro i
    exact (Φ.bump i).integrable_normed (μ := (volume : Measure ℝ))
  · intro i y
    exact (Φ.bump i).nonneg_normed (μ := (volume : Measure ℝ)) y
  · intro i
    exact (Φ.bump i).integral_normed (μ := (volume : Measure ℝ))

end

end ZtareProofs.NS.KRFMollifierMLG2Bridge
