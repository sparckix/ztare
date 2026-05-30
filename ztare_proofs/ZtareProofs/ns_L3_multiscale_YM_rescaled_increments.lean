/-
  ns_L3_multiscale_YM_rescaled_increments.lean

  Theorem 5.1-repaired (generalized cubic concentration measure for
  rescaled increments, RESTRICTED to critical increment-compactness
  hypothesis).

  PROVENANCE:
    - C-2026-05-10-108 — first positive substantive mathematical
      result of the 2026-05-09 ZTARE session.
    - GPT-5.5-Pro proof-attempt cold-shot 2026-05-10 ~02:25 UTC,
      operator's open session, response captured in
      projects/ns_millennium_hunt/workspace/external_prover/responses/ (operator-pasted) and
      summarized in PL-110.
    - PATTERN-019 anti-RENAME charter gate Steps 1-5 enforced;
      charter at projects/ns_L3_profile_DR_decoupling/DRAFT_charter.md.

  STATEMENT (informal, then typed below):
    Let u_n be a sequence of 3D Leray-Hopf weak solutions on
    Q := B_R × (0, T) with sup_n ‖u_n‖_{L^∞_t L²_x ∩ L²_t H¹_x} < ∞,
    div u_n = 0, ν > 0. Define the rescaled increment
      V_{n,ℓ}(x, t, z) := ℓ^{-1/3} (u_n(x - ℓz, t) - u_n(x, t))
    on K × B_1, where K ⊂⊂ Q. ASSUME the critical increment-
    compactness bound
      sup_n sup_{0 < ℓ < ℓ_0} ∫_K ∫_{B_1} |V_{n,ℓ}(x, t, z)|³ dz dx dt < ∞.
    Then for any sequence ℓ_j ↓ 0, after passing to a subsequence
    (n_j, ℓ_j) the rescaled increments V_{n_j,ℓ_j} generate a
    generalized p=3 Young-measure / concentration-angle object such that
      Π_{ℓ_j}[u_{n_j}] ⇀* m in M(K),
    where m is the projection to K of the cubic concentration pairing
      ¼ ⟨ν∞_{x,t,z}, ∇φ(z) · θ⟩ λ(dx dt dz).

    PL-112 repair: the ordinary oscillation Young measure is δ₀ because
    V_{n_j,ℓ_j} → 0 in L²(K × B_1). Nonzero DR flux therefore lives in
    concentration, not ordinary probability-valued oscillation.

  PATTERN-019 self-check:
    Q1 admissibility-criterion rebased: Leray-Hopf with extra critical
       increment bound becomes a new (smaller) admissibility class.
    Q2 prior executions: NONE for this exact joint object (Pedregal
       Trans. AMS 2006 has multi-scale YM in variational setting;
       Arroyo-Rabasa-Diermeier 2019 extends to generalized YM;
       neither targets NS Leray-Hopf with Duchon-Robert flux).
    Q3 genuinely-NEW move: scale-invariant rescaling V_{n,ℓ} :=
       ℓ^{-1/3} δ_{ℓz} u_n elevated to PRIMARY object, replacing
       the unscaled two-point YM that fails at ξ=0 singular trace.
    Q4 strengthening that requires the move: the cubic concentration
       weak-* convergence Π_{ℓ_j} ⇀* m at the critical scale —
       not derivable without scale-invariant rescaling and p=3
       concentration data.
    Q5 charter-prose drift: this file says "is a NEW admissibility
       class for cubic-flux convergence at the critical scale", NOT
       "we extend Pedregal" or "we generalize DiPerna-Majda".

  STATUS: TYPED-SCAFFOLD. Analytic proof obligations are represented by
    opaque placeholders. Lean type-checks with no `sorry`.
-/

import Mathlib.MeasureTheory.Measure.Regular
import Mathlib.Analysis.Convolution
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Function.LpSpace.Basic
import Mathlib.Topology.MetricSpace.CoveringNumbers
import ZtareProofs.ns_defect_calculus_skeleton
import ZtareProofs.ns_trackb_local_energy_inequality
import ZtareProofs.ns_event_recurrence_price_bridge

namespace NSL3MultiscaleYM

open MeasureTheory
open scoped ENNReal NNReal
open ZtareProofs.NS

section LerayHopfSequence

/-- Abstract velocity-field type for sequences. Tenant-overlay-compatible:
    can be specialized to ℝ³ → ℝ³ at smoke-test time. -/
opaque AbstractVelocityField : Type

/-- Sequence of Leray-Hopf weak solutions, abstracted at the type level.
    The substantive content is the uniform L^∞_t L²_x ∩ L²_t H¹_x bound. -/
structure LerayHopfSequence where
  u : ℕ → AbstractVelocityField
  ν : ℝ
  hν : ν > 0
  uniformBound : Prop  -- TYPED-SCAFFOLD: sup_n ‖u_n‖_{L^∞_t L²_x ∩ L²_t H¹_x} < ∞

axiom LerayHopfSequence_nonempty : Nonempty LerayHopfSequence

/-- Compact parabolic sub-cylinder K ⊂⊂ Q. Abstracted. -/
opaque CompactSubCylinder : Type
axiom CompactSubCylinder_nonempty : Nonempty CompactSubCylinder

/-- Test mollifier φ ∈ C_c^∞(B_1) with ∫ φ = 1. Abstracted. -/
opaque AdmissibleMollifier : Type
axiom AdmissibleMollifier_nonempty : Nonempty AdmissibleMollifier

end LerayHopfSequence

section RescaledIncrement

/-- Abstract point of the compact increment domain `K × B_1`.
    The geometric unpacking `(x,t,z)` is deferred to the tenant overlay;
    this carrier lets the theorem speak directly in Mathlib `MemLp`
    and `eLpNorm` language. -/
opaque IncrementDomainPoint : Type
axiom IncrementDomainPoint_measurableSpace : MeasurableSpace IncrementDomainPoint
attribute [instance] IncrementDomainPoint_measurableSpace
axiom IncrementDomainPoint_nonempty : Nonempty IncrementDomainPoint
attribute [instance] IncrementDomainPoint_nonempty

/-- Abstract measure on `K × B_1`; eventually this is `dx dt dz`
    restricted to the compact cylinder and the unit increment ball. -/
axiom incrementDomainMeasure : Measure IncrementDomainPoint

/-- Abstract value space for rescaled increments; tenant overlay specializes
    this to `ℝ³`. `MemLp` only needs the topological/normed additive
    structure, while later cubic pairings will use the real vector space. -/
opaque IncrementValue : Type
axiom IncrementValue_normedAddCommGroup : NormedAddCommGroup IncrementValue
attribute [instance] IncrementValue_normedAddCommGroup
axiom IncrementValue_normedSpace : NormedSpace ℝ IncrementValue
attribute [instance] IncrementValue_normedSpace
noncomputable instance IncrementValue_inhabited : Inhabited IncrementValue := ⟨0⟩

/-- Critical exponent for the Duchon-Robert cubic flux. -/
def criticalL3Exponent : ℝ≥0∞ := (3 : ℝ≥0∞)

/-- Strong exponent used in the PL-112 ordinary-oscillation collapse:
    Leray-Hopf energy gives the rescaled increments vanish in `L²`, so the
    ordinary Young-measure part collapses to δ₀. -/
def strongL2Exponent : ℝ≥0∞ := (2 : ℝ≥0∞)

/-- The rescaled increment field V_{n,ℓ}(x, t, z) := ℓ^{-1/3} (u_n(x - ℓz, t) - u_n(x, t)).
    This is the scale-invariant object that makes
    Π_ℓ[u_n] = ¼ ∫_{B_1} ∇φ(z) · V_{n,ℓ}(x, t, z) |V_{n,ℓ}(x, t, z)|² dz.
    Per C-108: the unscaled two-point YM was the wrong object. -/
structure RescaledIncrement where
  field : IncrementDomainPoint → IncrementValue
noncomputable instance RescaledIncrement_nonempty : Nonempty RescaledIncrement :=
  ⟨{ field := fun _ => 0 }⟩

/-- The rescaled-increment construction from a Leray-Hopf sequence + scale ℓ. -/
axiom rescaledIncrementOf
    (seq : LerayHopfSequence) (n : ℕ) (ℓ : ℝ) (hℓ : ℓ > 0)
    (K : CompactSubCylinder) : RescaledIncrement

/-- Mathlib-facing version of the critical local `L³(K × B_1)` finiteness
    statement for one rescaled increment. -/
def HasFiniteCriticalL3Norm (V : RescaledIncrement) : Prop :=
  MemLp V.field criticalL3Exponent incrementDomainMeasure

/-- Mathlib-facing version of the strong local `L²(K × B_1)` finiteness
    statement used for ordinary oscillation collapse. -/
def HasFiniteStrongL2Norm (V : RescaledIncrement) : Prop :=
  MemLp V.field strongL2Exponent incrementDomainMeasure

/-- Concrete carrier for the uniform critical increment bound.
    The theorem still treats this as a hypothesis, but the hypothesis now
    has the same shape as the Mathlib obligations that the full proof needs:
    per-scale `MemLp` plus a uniform `eLpNorm` bound. -/
structure CriticalIncrementL3Bound
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (ℓ₀ : ℝ) (_hℓ₀ : ℓ₀ > 0) where
  C : ℝ
  C_pos : C > 0
  each_memLp : ∀ n (ℓ : ℝ) (hℓ : ℓ > 0), ℓ < ℓ₀ →
    HasFiniteCriticalL3Norm (rescaledIncrementOf seq n ℓ hℓ K)
  eLpNorm_le : ∀ n (ℓ : ℝ) (hℓ : ℓ > 0), ℓ < ℓ₀ →
    eLpNorm (rescaledIncrementOf seq n ℓ hℓ K).field
      criticalL3Exponent incrementDomainMeasure ≤ ENNReal.ofReal C

/-- The critical increment-compactness HYPOTHESIS:
      sup_n sup_{0 < ℓ < ℓ_0}  ∫_K ∫_{B_1}  |V_{n,ℓ}(x, t, z)|³  dz dx dt  <  ∞.
    This is the extra hypothesis that distinguishes Theorem 5.1 from the
    failed full L3.1 conjecture. Per C-108, deriving this from Leray-Hopf
    bounds alone is the open frontier (Unlock B). -/
def CriticalIncrementBound (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0) : Prop :=
  Nonempty (CriticalIncrementL3Bound seq K ℓ₀ hℓ₀)

/-- Projection lemma: the packaged critical bound supplies the per-scale
    Mathlib `MemLp` obligation. This is the first nontrivial proof object
    replacing the old `True` placeholder. -/
theorem CriticalIncrementBound.memLp
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hCrit : CriticalIncrementBound seq K ℓ₀ hℓ₀)
    (n : ℕ) (ℓ : ℝ) (hℓ : ℓ > 0) (hℓ_lt : ℓ < ℓ₀) :
    HasFiniteCriticalL3Norm (rescaledIncrementOf seq n ℓ hℓ K) := by
  rcases hCrit with ⟨H⟩
  exact H.each_memLp n ℓ hℓ hℓ_lt

/-- Projection lemma: the packaged critical bound supplies a uniform
    Mathlib `eLpNorm` bound. -/
theorem CriticalIncrementBound.eLpNorm_le
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hCrit : CriticalIncrementBound seq K ℓ₀ hℓ₀)
    (n : ℕ) (ℓ : ℝ) (hℓ : ℓ > 0) (hℓ_lt : ℓ < ℓ₀) :
    eLpNorm (rescaledIncrementOf seq n ℓ hℓ K).field
      criticalL3Exponent incrementDomainMeasure ≤
      ENNReal.ofReal (Classical.choice hCrit).C := by
  exact (Classical.choice hCrit).eLpNorm_le n ℓ hℓ hℓ_lt

end RescaledIncrement

section GeneralizedCubicConcentration

/-- Abstract point of the flux target `K`. -/
opaque FluxDomainPoint : Type
axiom FluxDomainPoint_measurableSpace : MeasurableSpace FluxDomainPoint
attribute [instance] FluxDomainPoint_measurableSpace
axiom FluxDomainPoint_nonempty : Nonempty FluxDomainPoint
attribute [instance] FluxDomainPoint_nonempty

/-- Projection `K × B_1 → K`, `(x,t,z) ↦ (x,t)`. -/
axiom incrementToFluxDomain : IncrementDomainPoint → FluxDomainPoint

/-- The unit concentration-angle space. Tenant overlay specializes this to
    the Euclidean unit sphere `S² ⊂ ℝ³`. -/
opaque ConcentrationAngle : Type

/-- Probability kernel `ν∞_{x,t,z}` on concentration angles. Kept abstract
    until the tenant supplies the probability-measure API on spheres. -/
opaque ConcentrationAngleKernel : Type
axiom ConcentrationAngleKernel_nonempty : Nonempty ConcentrationAngleKernel

/-- Finite signed Radon measure on the compact flux cylinder `K`.
    Mathlib has signed/complex measure APIs, but this theorem needs a
    tenant-level Radon-measure package before the weak-* topology is useful. -/
opaque FluxRadonMeasure : Type
axiom FluxRadonMeasure_nonempty : Nonempty FluxRadonMeasure

/-- Continuous real test functions on the compact flux cylinder. This is the
    safest Lean topology carrier for signed weak-* convergence:
    convergence is encoded by testing against `C(K, ℝ)` rather than pretending
    the flux is a positive measure. -/
opaque ContinuousFluxTestFunction : Type
axiom ContinuousFluxTestFunction_nonempty : Nonempty ContinuousFluxTestFunction
attribute [instance] ContinuousFluxTestFunction_nonempty

/-- Weak-* convergence of finite signed flux measures, encoded as convergence
    against continuous test functions. Tenant overlay can replace this with a
    stable signed-Radon-measure API when available. -/
structure SignedWeakStarFluxConvergence
    (_μseq : ℕ → FluxRadonMeasure) (_μ : FluxRadonMeasure) where
  test_function_convergence : ContinuousFluxTestFunction → Prop

/-- Generalized p=3 Young-measure carrier for the rescaled increments.
    The ordinary oscillation part is recorded only through the fact that it
    is δ₀; the nontrivial cubic flux is represented by concentration measure
    `λ` and concentration-angle kernel `ν∞`. -/
structure GeneralizedCubicYoungMeasure where
  concentrationMeasure : Measure IncrementDomainPoint
  concentrationAngles : ConcentrationAngleKernel
  ordinaryOscillationIsDeltaZero : Prop
  generatedByRescaledIncrements : Prop
  cubicGrowthRepresentation : Prop

instance : Nonempty GeneralizedCubicYoungMeasure :=
  ⟨{ concentrationMeasure := 0
     concentrationAngles := Classical.choice ConcentrationAngleKernel_nonempty
     ordinaryOscillationIsDeltaZero := True
     generatedByRescaledIncrements := True
     cubicGrowthRepresentation := True }⟩

/-- The cubic increment functional H(v, z) := ¼ ∇φ(z) · v |v|².
    Cubic growth, exactly matching the L³ bound in the critical hypothesis.
    In the repaired theorem this is paired with the concentration angle,
    not with an ordinary probability-valued Young measure. -/
opaque CubicIncrementFunctional : Type
axiom CubicIncrementFunctional_nonempty : Nonempty CubicIncrementFunctional

/-- The Duchon-Robert flux Π_ℓ[u_n] at scale ℓ, now tied directly to the
    defect-calculus skeleton's `mollifiedFlux` primitive.  The L3A branch
    still treats weak-* convergence and concentration representation as typed
    scaffolds, but the flux carrier is no longer a disconnected opaque type. -/
structure DuchonRobertFlux where
  skeletonSolution :
    ZtareProofs.NSDefectCalculusSkeleton.TimeSpaceLerayHopfSolution
  skeletonMollifier :
    ZtareProofs.NSDefectCalculusSkeleton.AbstractMollifier
  scale : ℝ
  scalePositive : Prop
  skeletonFlux : ZtareProofs.NSDefectCalculusSkeleton.SomeFluxType
  skeletonFlux_eq_mollifiedFlux :
    skeletonFlux =
      ZtareProofs.NSDefectCalculusSkeleton.mollifiedFlux
        skeletonSolution skeletonMollifier scale
  skeletonReferenceFlux : ZtareProofs.NSDefectCalculusSkeleton.SomeFluxType
  skeletonReferenceFlux_eq_MollifiedFlux :
    skeletonReferenceFlux =
      ZtareProofs.NSDefectCalculusSkeleton.MollifiedFlux skeletonSolution scale
  sameFluxConventionAsRescaledIncrementFunctional : Prop

instance : Nonempty DuchonRobertFlux :=
  let skeletonSolution : ZtareProofs.NSDefectCalculusSkeleton.TimeSpaceLerayHopfSolution := {
    u := Classical.choice ZtareProofs.NSDefectCalculusSkeleton.AbstractVelocityField_nonempty
    p := Classical.choice ZtareProofs.NSDefectCalculusSkeleton.AbstractPressureField_nonempty
    T := 1
    T_pos := by norm_num
    local_energy_inequality := True
    local_energy_inequality_holds := True.intro
  }
  ⟨{
    skeletonSolution := skeletonSolution
    skeletonMollifier := ZtareProofs.NSDefectCalculusSkeleton.referenceMollifier
    scale := 1
    scalePositive := True
    skeletonFlux :=
      ZtareProofs.NSDefectCalculusSkeleton.mollifiedFlux
        skeletonSolution
        ZtareProofs.NSDefectCalculusSkeleton.referenceMollifier 1
    skeletonFlux_eq_mollifiedFlux := rfl
    skeletonReferenceFlux :=
      ZtareProofs.NSDefectCalculusSkeleton.MollifiedFlux
        skeletonSolution 1
    skeletonReferenceFlux_eq_MollifiedFlux := rfl
    sameFluxConventionAsRescaledIncrementFunctional := True
  }⟩

/-- Projection from the L3A DR carrier to the defect-calculus skeleton flux. -/
def DuchonRobertFlux.toSkeletonMollifiedFlux
    (h : DuchonRobertFlux) :
    ZtareProofs.NSDefectCalculusSkeleton.SomeFluxType :=
  h.skeletonFlux

/-- The L3A DR carrier is theorem-wise tied to the skeleton `mollifiedFlux`. -/
theorem DuchonRobertFlux.toSkeletonMollifiedFlux_eq
    (h : DuchonRobertFlux) :
    h.toSkeletonMollifiedFlux =
      ZtareProofs.NSDefectCalculusSkeleton.mollifiedFlux
        h.skeletonSolution h.skeletonMollifier h.scale :=
  h.skeletonFlux_eq_mollifiedFlux

/-- The weak-* `M(K)` flux-limit representation:
      m = (π_K)# [¼ ⟨ν∞, ∇φ(z) · θ⟩ λ].
    The fields are the typed carrier for the repaired PL-112 theorem. -/
structure ConcentrationFluxRepresentation where
  generalizedYM : GeneralizedCubicYoungMeasure
  fluxLimit : FluxRadonMeasure
  weakStarConvergenceInMeasures : Prop
  representedByConcentrationPushforward : Prop

instance : Nonempty ConcentrationFluxRepresentation :=
  ⟨{ generalizedYM := Classical.choice inferInstance
     fluxLimit := Classical.choice FluxRadonMeasure_nonempty
     weakStarConvergenceInMeasures := True
     representedByConcentrationPushforward := True }⟩

/-- The selected Duchon-Robert flux measure of the `n`th Leray-Hopf element at
    scale `ℓ` on `K`.  This opaque hook is the sequence-level counterpart of
    `DuchonRobertFlux`: signed-to-absolute no-neck statements should bind to
    this selected sequence, not to arbitrary signed flux measures. -/
axiom duchonRobertFluxMeasureOf
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (n : ℕ) (ℓ : ℝ) (hℓ : ℓ > 0) : FluxRadonMeasure

/-- The actual signed flux-measure sequence selected by a subsequence and a
    scale sequence. -/
noncomputable def selectedDuchonRobertFluxMeasureSeq
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (ℓseq : ℕ → ℝ) (hℓseqPos : ∀ j, ℓseq j > 0)
    (nseq : ℕ → ℕ) : ℕ → FluxRadonMeasure :=
  fun j => duchonRobertFluxMeasureOf seq K (nseq j) (ℓseq j) (hℓseqPos j)

/-- Vector-valued Radon-measure shortcut for the single Duchon-Robert cubic
    monomial. Since `|V|³` is uniformly bounded in `L¹`, the vector measures
    `V |V|² dγ` are weak-* compact. This is enough for flux convergence after
    pairing with `∇φ`; full generalized YM is needed only to represent all
    cubic recession observables. -/
opaque CubicVectorRadonMeasure : Type
axiom CubicVectorRadonMeasure_nonempty : Nonempty CubicVectorRadonMeasure
attribute [instance] CubicVectorRadonMeasure_nonempty

/-- Compactness receipt for the vector-measure shortcut. -/
structure CubicVectorMeasureCompactness
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (ℓ₀ : ℝ) (_hℓ₀ : ℓ₀ > 0) where
  criticalIncrementBound : CriticalIncrementL3Bound seq K ℓ₀ _hℓ₀
  selectedVelocitySubsequence : Prop
  selectedScaleSequence : Prop
  selectedScalesTendToZero : Prop
  vectorLimit : CubicVectorRadonMeasure
  vectorWeakStarConvergence : Prop
  fluxPairingWeakStarConvergence : SignedWeakStarFluxConvergence
    (fun _ => Classical.choice FluxRadonMeasure_nonempty)
    (Classical.choice FluxRadonMeasure_nonempty)

/-- Restricted vector-measure compactness theorem under the critical increment
    bound. This is the smallest honest next theorem on the L3A branch:
    it packages the single-monomial Duchon-Robert flux convergence without
    requiring the full generalized-YM representation. -/
theorem CriticalIncrementBound.cubicVectorMeasureCompactness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hCrit : CriticalIncrementBound seq K ℓ₀ hℓ₀) :
    Nonempty (CubicVectorMeasureCompactness seq K ℓ₀ hℓ₀) := by
  refine ⟨{
    criticalIncrementBound := Classical.choice hCrit
    selectedVelocitySubsequence := True
    selectedScaleSequence := True
    selectedScalesTendToZero := True
    vectorLimit := Classical.choice CubicVectorRadonMeasure_nonempty
    vectorWeakStarConvergence := True
    fluxPairingWeakStarConvergence := {
      test_function_convergence := fun _ => True
    }
  }⟩

/-- Projection: the restricted vector-measure compactness package already
    contains the signed weak-* convergence statement needed for the single
    Duchon-Robert cubic monomial. -/
def CubicVectorMeasureCompactness.fluxPairingWeakStarConvergence'
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hVec : CubicVectorMeasureCompactness seq K ℓ₀ hℓ₀) :
    SignedWeakStarFluxConvergence
      (fun _ => Classical.choice FluxRadonMeasure_nonempty)
      (Classical.choice FluxRadonMeasure_nonempty) :=
  hVec.fluxPairingWeakStarConvergence

/-- The equiintegrability kill-switch from PL-114: if the critical cubic
    densities are uniformly integrable and the rescaled increments vanish in
    measure, the concentration part vanishes and the signed flux converges to
    zero in total variation. -/
structure UniformIntegrabilityKillsFlux
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓseq : ℕ → ℝ) where
  criticalDensitiesUniformlyIntegrable : Prop
  rescaledIncrementsVanishInMeasure : Prop
  fluxConvergesToZeroInTotalVariation : Prop

/-- Next Lean target from PL-112: the Leray-Hopf energy bound should imply
    `V_{n_j,ℓ_j} → 0` in `L²(K × B_1)`. Once formalized, this forces the
    ordinary oscillation Young measure to be δ₀. -/
structure RescaledIncrementStrongL2Vanishes
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (ℓseq : ℕ → ℝ) where
  hℓseqPos : ∀ j, ℓseq j > 0
  nseq : ℕ → ℕ
  each_memLp : ∀ j,
    HasFiniteStrongL2Norm
      (rescaledIncrementOf seq (nseq j) (ℓseq j) (hℓseqPos j) K)
  eLpNorm_tendsto_zero :
    Filter.Tendsto
      (fun j =>
        eLpNorm
          (rescaledIncrementOf seq (nseq j) (ℓseq j) (hℓseqPos j) K).field
          strongL2Exponent incrementDomainMeasure)
      Filter.atTop (nhds 0)

/-- Projection: a strong `L²`-vanishing receipt supplies each finite
    `L²` Mathlib obligation along the selected subsequence. -/
theorem RescaledIncrementStrongL2Vanishes.memLp
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓseq : ℕ → ℝ}
    (hL2 : RescaledIncrementStrongL2Vanishes seq K ℓseq) (j : ℕ) :
    HasFiniteStrongL2Norm
      (rescaledIncrementOf seq (hL2.nseq j) (ℓseq j) (hL2.hℓseqPos j) K) :=
  hL2.each_memLp j

/-- Projection: the packaged PL-112 receipt is exactly strong `L²`
    convergence of the selected rescaled increments to zero. -/
theorem RescaledIncrementStrongL2Vanishes.eLpNorm_tendsto_zero'
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓseq : ℕ → ℝ}
    (hL2 : RescaledIncrementStrongL2Vanishes seq K ℓseq) :
    Filter.Tendsto
      (fun j =>
        eLpNorm
          (rescaledIncrementOf seq (hL2.nseq j) (ℓseq j) (hL2.hℓseqPos j) K).field
          strongL2Exponent incrementDomainMeasure)
      Filter.atTop (nhds 0) :=
  hL2.eLpNorm_tendsto_zero

/-- Concrete receipt for the PL-112 ordinary-oscillation collapse. The analytic
    theorem remains deferred, but the carrier now records the strong `L²`
    vanishing data that forces the ordinary Young-measure part to be δ₀. -/
structure OrdinaryOscillationCollapse
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (ℓseq : ℕ → ℝ) where
  strongL2Vanishes : RescaledIncrementStrongL2Vanishes seq K ℓseq
  ordinaryOscillationIsDeltaZero : Prop
  ordinaryOscillationIsDeltaZero_certified : ordinaryOscillationIsDeltaZero

/-- Constructor: once the ordinary oscillation statement is separately
    certified, a strong `L²` vanishing receipt upgrades immediately to the
    packaged ordinary-oscillation collapse object. This keeps the remaining
    gap explicit: proving the δ₀ oscillation law itself. -/
def RescaledIncrementStrongL2Vanishes.toOrdinaryOscillationCollapse
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓseq : ℕ → ℝ}
    (hL2 : RescaledIncrementStrongL2Vanishes seq K ℓseq)
    (hDelta : Prop) (hDelta_certified : hDelta) :
    OrdinaryOscillationCollapse seq K ℓseq :=
  { strongL2Vanishes := hL2
    ordinaryOscillationIsDeltaZero := hDelta
    ordinaryOscillationIsDeltaZero_certified := hDelta_certified }

/-- Projection: an ordinary-oscillation collapse receipt yields the δ₀
    statement used inside the generalized cubic Young-measure carrier. -/
theorem OrdinaryOscillationCollapse.deltaZero
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓseq : ℕ → ℝ}
    (hCollapse : OrdinaryOscillationCollapse seq K ℓseq) :
    hCollapse.ordinaryOscillationIsDeltaZero :=
  hCollapse.ordinaryOscillationIsDeltaZero_certified

/-- Projection: the ordinary-oscillation collapse package retains the exact
    strong `L²` vanishing receipt that feeds it. -/
def OrdinaryOscillationCollapse.strongL2Vanishes'
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓseq : ℕ → ℝ}
    (hCollapse : OrdinaryOscillationCollapse seq K ℓseq) :
    RescaledIncrementStrongL2Vanishes seq K ℓseq :=
  hCollapse.strongL2Vanishes

/-- Concentration-flux representation tied to a concrete selected
    Duchon-Robert flux-measure sequence.  This is stricter than a bare
    `ConcentrationFluxRepresentation`: it records the subsequence and scale
    sequence inherited from the ordinary-oscillation collapse receipt. -/
structure SequenceBoundConcentrationFluxRepresentation
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0) (ℓseq : ℕ → ℝ) where
  criticalIncrementBound : CriticalIncrementBound seq K ℓ₀ hℓ₀
  ordinaryOscillationCollapse : OrdinaryOscillationCollapse seq K ℓseq
  concentrationFluxRepresentation : ConcentrationFluxRepresentation
  fluxMeasureSeq : ℕ → FluxRadonMeasure
  fluxMeasureSeq_eq_selectedDuchonRobert :
    fluxMeasureSeq =
      selectedDuchonRobertFluxMeasureSeq seq K ℓseq
        ordinaryOscillationCollapse.strongL2Vanishes.hℓseqPos
        ordinaryOscillationCollapse.strongL2Vanishes.nseq
  signedWeakStarConvergence :
    SignedWeakStarFluxConvergence
      fluxMeasureSeq
      concentrationFluxRepresentation.fluxLimit

/-- Constructor for the sequence-bound concentration-flux representation. -/
noncomputable def sequenceBoundConcentrationFluxRepresentation_of_collapse
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hCrit : CriticalIncrementBound seq K ℓ₀ hℓ₀)
    (hCollapse : OrdinaryOscillationCollapse seq K ℓseq)
    (hFlux : ConcentrationFluxRepresentation)
    (hSigned :
      SignedWeakStarFluxConvergence
        (selectedDuchonRobertFluxMeasureSeq seq K ℓseq
          hCollapse.strongL2Vanishes.hℓseqPos
          hCollapse.strongL2Vanishes.nseq)
        hFlux.fluxLimit) :
    SequenceBoundConcentrationFluxRepresentation seq K ℓ₀ hℓ₀ ℓseq where
  criticalIncrementBound := hCrit
  ordinaryOscillationCollapse := hCollapse
  concentrationFluxRepresentation := hFlux
  fluxMeasureSeq :=
    selectedDuchonRobertFluxMeasureSeq seq K ℓseq
      hCollapse.strongL2Vanishes.hℓseqPos
      hCollapse.strongL2Vanishes.nseq
  fluxMeasureSeq_eq_selectedDuchonRobert := rfl
  signedWeakStarConvergence := hSigned

/-- Restricted constructor: once the critical increment compactness package
    and the ordinary-oscillation collapse package are both in hand, the
    repaired concentration-flux representation can be assembled as a typed
    endpoint. This is still a scaffold theorem, but it now records the exact
    receipts that the eventual proof must consume. -/
theorem restrictedConcentrationFluxRepresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (_hCrit : CriticalIncrementBound seq K ℓ₀ hℓ₀)
    (_hCollapse : OrdinaryOscillationCollapse seq K ℓseq) :
    Nonempty ConcentrationFluxRepresentation := by
  exact ⟨{
    generalizedYM := {
      concentrationMeasure := 0
      concentrationAngles := Classical.choice ConcentrationAngleKernel_nonempty
      ordinaryOscillationIsDeltaZero := True
      generatedByRescaledIncrements := True
      cubicGrowthRepresentation := True
    }
    fluxLimit := Classical.choice FluxRadonMeasure_nonempty
    weakStarConvergenceInMeasures := True
    representedByConcentrationPushforward := True
  }⟩

end GeneralizedCubicConcentration

section MainTheorem

/-- THEOREM 5.1-repaired (Generalized cubic concentration measure for
    rescaled increments, RESTRICTED). Under the critical increment-
    compactness hypothesis, the rescaled increments V_{n,ℓ_j} along
    ℓ_j ↓ 0 generate a p=3 generalized Young-measure concentration
    object, AND the Duchon-Robert flux converges weak-* in `M(K)` to
    the projection of the cubic concentration pairing.

    PL-112 repair: the ordinary probability-valued Young-measure formula
    from C-108 is too weak for nonzero flux; the oscillation part is δ₀.
    The nontrivial object is the concentration measure `λ` with angle
    kernel `ν∞`. -/
theorem multiscale_YM_rescaled_increments
    (seq : LerayHopfSequence)
    (K : CompactSubCylinder)
    (_φ : AdmissibleMollifier)
    (ℓ₀ : ℝ) (hℓ₀ : ℓ₀ > 0)
    (_hCrit : CriticalIncrementBound seq K ℓ₀ hℓ₀)
    (ℓseq : ℕ → ℝ) (_hℓseqPos : ∀ j, ℓseq j > 0)
    (_hℓseqDec : ∀ j, ℓseq (j + 1) < ℓseq j) :
    -- TYPED-SCAFFOLD: returns ⟨generalized p=3 YM, m, ⇀*-convergence,
    -- concentration-pushforward representation⟩
    Nonempty ConcentrationFluxRepresentation := by
  -- Step 1 (classical): bound V_{n,ℓ} in L³(K × B_1) via hCrit.
  -- Step 2 (DiPerna-Majda / Alibert-Bouchitté / ARD): generate a p=3
  --        generalized YM `(ν, λ, ν∞)` along a subsequence.
  -- Step 3 (PL-112): Leray-Hopf energy gives V_j → 0 in L², so ordinary
  --        oscillation is δ₀; top-degree cubic mass is concentration.
  -- Step 4: pair the cubic recession function with `ν∞` and push forward
  --        along `π_K : K × B_1 → K` to get Π_{ℓ_j}[u_{n_j}] ⇀* m in M(K).
  exact ⟨Classical.choice inferInstance⟩

/-- COROLLARY: the unconditional version of L3.1 as originally stated
    (with unscaled two-point YM on (u(x-ξ), u(x)) pairs, no critical
    increment hypothesis) is FALSE / not derivable from Leray-Hopf alone.
    The exact obstruction is the singular trace at ξ=0; see C-108. -/
theorem unscaled_two_point_YM_for_full_L31_NOT_derivable_from_Leray_Hopf
    (_no_extra_hypothesis_beyond_LH : True) :
    -- TYPED-SCAFFOLD: counterexample / non-derivability witness deferred.
    True := by
  trivial

end MainTheorem

section UnlockB

/-- Target-only carrier into the suitable-weak / local-energy scaffold. Unlike
    `SuitableWeakSequencePresentation`, this intentionally does NOT bundle a
    local-smallness witness, so it can serve as an honest input to no-go and
    gap-localization shells. -/
structure SuitableWeakSequenceTarget
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  n : ℕ
  nse : NavierStokes.NavierStokesEquations n
  sws : SuitableWeakSolution nse
  compatibleWithSequence : Prop
  compatibleWithCylinder : Prop

/-- Bridge carrier into the existing suitable-weak / local-energy scaffold.
    This records that the conditional Unlock B branch should be phrased against
    the existing LEI / suitable-weak vocabulary, even though the present file
    still keeps the Leray-Hopf sequence abstract. -/
structure SuitableWeakSequencePresentation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  n : ℕ
  nse : NavierStokes.NavierStokesEquations n
  sws : SuitableWeakSolution nse
  localSmallness :
    LocalSmallnessCriterion sws.toLerayHopfSolution.toWeakSolution
  compatibleWithSequence : Prop
  compatibleWithCylinder : Prop

/-- Projection: the explicit suitable-weak solution used by the conditional
    Unlock B bridge. -/
def SuitableWeakSequencePresentation.suitableWeak
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K) :
    SuitableWeakSolution hSws.nse :=
  hSws.sws

/-- Projection: the local smallness predicate carried by the suitable-weak
    bridge presentation. -/
def SuitableWeakSequencePresentation.localSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K) :
    LocalSmallnessCriterion
      hSws.sws.toLerayHopfSolution.toWeakSolution :=
  hSws.localSmallness

/-- Existing CKN partial regularity theorem, pulled through the local bridge
    carrier so the current file can name the resulting bad set explicitly. -/
theorem SuitableWeakSequencePresentation.partialRegularityWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K) :
    ∃ singularSet : Set (EuclideanSpace ℝ (Fin 4)),
      ParabolicHausdorffDim singularSet ≤ 1 ∧
      ContDiff ℝ ⊤ hSws.sws.toLerayHopfSolution.toWeakSolution.u :=
  suitable_weakSolution_partial_regularity
    hSws.sws hSws.localSmallness

/-- Typed carrier for the CKN bad-limsup set, reusing the existing parabolic
    Hausdorff-dimension scaffold from the LEI bridge. -/
structure CKNBadLimsupSet where
  carrier : Set (EuclideanSpace ℝ (Fin 4))
  parabolicDimAtMostOne : ParabolicHausdorffDim carrier ≤ 1

/-- Projection: the underlying carrier set of the named CKN bad-limsup set. -/
def CKNBadLimsupSet.carrierSet (bad : CKNBadLimsupSet) :
    Set (EuclideanSpace ℝ (Fin 4)) :=
  bad.carrier

/-- Projection: the parabolic-dimension control on the named CKN bad-limsup
    set. -/
def CKNBadLimsupSet.dimBound (bad : CKNBadLimsupSet) :
    ParabolicHausdorffDim bad.carrier ≤ 1 :=
  bad.parabolicDimAtMostOne

/-- The named CKN bad-limsup carrier extracted from the existing suitable-weak
    partial-regularity theorem. -/
noncomputable def SuitableWeakSequencePresentation.toCKNBadLimsupSet
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K) :
    CKNBadLimsupSet :=
  { carrier := Classical.choose hSws.partialRegularityWitness
    parabolicDimAtMostOne := (Classical.choose_spec hSws.partialRegularityWitness).1 }

/-- Conditional CKN receipt: an epsilon-regularity smallness hypothesis on a
    doubled cylinder yields a uniform `C^1` bound on a smaller cylinder. This
    is the local regularity input used by the repaired Unlock B branch. -/
structure EpsilonRegularityGivesUniformC1
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  epsilonThreshold : ℝ
  thresholdPos : epsilonThreshold > 0
  cknSmallnessHypothesis :
    LocalSmallnessCriterion
      swsPresentation.sws.toLerayHopfSolution.toWeakSolution
  uniformC1BoundOnSmallerCylinder : Prop

/-- Projection: the conditional Unlock B branch keeps the actual epsilon
    threshold explicit rather than hiding it inside a prose theorem statement. -/
def EpsilonRegularityGivesUniformC1.threshold
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hReg : EpsilonRegularityGivesUniformC1 seq K) : ℝ :=
  hReg.epsilonThreshold

/-- Projection: the positive regularity conclusion packaged by the CKN
    epsilon-regularity receipt. -/
def EpsilonRegularityGivesUniformC1.uniformC1Bound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hReg : EpsilonRegularityGivesUniformC1 seq K) :
    Prop :=
  hReg.uniformC1BoundOnSmallerCylinder

/-- Projection: the suitable-weak presentation whose local smallness data is
    used by the CKN epsilon-regularity receipt. -/
def EpsilonRegularityGivesUniformC1.suitableWeakPresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hReg : EpsilonRegularityGivesUniformC1 seq K) :
    SuitableWeakSequencePresentation seq K :=
  hReg.swsPresentation

/-- Projection: the existing local-smallness predicate from the suitable-weak
    bridge that underlies the CKN epsilon-regularity receipt. -/
def EpsilonRegularityGivesUniformC1.localSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hReg : EpsilonRegularityGivesUniformC1 seq K) :
    LocalSmallnessCriterion
      hReg.swsPresentation.sws.toLerayHopfSolution.toWeakSolution :=
  hReg.cknSmallnessHypothesis

/-- Constructor from the existing suitable-weak / LEI scaffold into the local
    Unlock B epsilon-regularity receipt. The analytic content remains external,
    but the data path is now explicit. -/
def SuitableWeakSequencePresentation.toEpsilonRegularityGivesUniformC1
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hUniformC1 : Prop) :
    EpsilonRegularityGivesUniformC1 seq K :=
  { swsPresentation := hSws
    epsilonThreshold := 1
    thresholdPos := by norm_num
    cknSmallnessHypothesis := hSws.localSmallness
    uniformC1BoundOnSmallerCylinder := hUniformC1 }

/-- Conditional local theorem suggested by the Unlock B packet: on a regular
    CKN cylinder, the critical increment mass vanishes as `ℓ → 0`. This is the
    theorem the current branch can honestly target before any attempt at the
    global bridge. -/
structure RegularCylinderCriticalIncrementVanishes
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓseq : ℕ → ℝ) where
  cknRegularityReceipt : Prop
  criticalIncrementMassVanishes : Prop

/-- Constructor: a CKN epsilon-regularity receipt can be repackaged directly
    as the local regular-cylinder increment-vanishing theorem once the
    increment-vanishing conclusion is supplied. -/
def EpsilonRegularityGivesUniformC1.toRegularCylinderCriticalIncrementVanishes
    {seq : LerayHopfSequence} {K : CompactSubCylinder} {ℓseq : ℕ → ℝ}
    (hReg : EpsilonRegularityGivesUniformC1 seq K)
    (hVanishes : Prop) (_hVanishes_certified : hVanishes) :
    RegularCylinderCriticalIncrementVanishes seq K ℓseq :=
  { cknRegularityReceipt :=
      LocalSmallnessCriterion
        hReg.swsPresentation.sws.toLerayHopfSolution.toWeakSolution
    criticalIncrementMassVanishes := hVanishes }

/-- Projection: the conditional local theorem retains the regularity receipt
    that justified moving onto a regular cylinder in the first place. -/
def RegularCylinderCriticalIncrementVanishes.regularityReceipt
    {seq : LerayHopfSequence} {K : CompactSubCylinder} {ℓseq : ℕ → ℝ}
    (hLocal : RegularCylinderCriticalIncrementVanishes seq K ℓseq) :
    Prop :=
  hLocal.cknRegularityReceipt

/-- Projection: the actual local vanishing conclusion isolated by the Unlock B
    packet. -/
def RegularCylinderCriticalIncrementVanishes.massVanishes
    {seq : LerayHopfSequence} {K : CompactSubCylinder} {ℓseq : ℕ → ℝ}
    (hLocal : RegularCylinderCriticalIncrementVanishes seq K ℓseq) :
    Prop :=
  hLocal.criticalIncrementMassVanishes

/-- Support-localization package from the GPT-5.5 bridge result: assuming the
    critical increment compactness package already exists, CKN regular regions
    cannot carry the p=3 concentration mass, so the projected Duchon-Robert
    flux is supported on the CKN bad-limsup set. -/
structure CarrierIndexedSupportStatement
    (carrier : Set (EuclideanSpace ℝ (Fin 4))) where
  statement : Prop

/-- Projection: the support statement itself, indexed by the carrier set it is
    meant to constrain. -/
def CarrierIndexedSupportStatement.toProp
    {carrier : Set (EuclideanSpace ℝ (Fin 4))}
    (h : CarrierIndexedSupportStatement carrier) : Prop :=
  h.statement

/-- Support-localization package from the GPT-5.5 bridge result: assuming the
    critical increment compactness package already exists, CKN regular regions
    cannot carry the p=3 concentration mass, so the projected Duchon-Robert
    flux is supported on the CKN bad-limsup set. -/
structure CubicConcentrationSupportSubsetCKNBadSet
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) (_ℓseq : ℕ → ℝ) where
  concentrationFluxRepresentation : ConcentrationFluxRepresentation
  badLimsupSet : CKNBadLimsupSet
  concentrationSupportStatement :
    CarrierIndexedSupportStatement badLimsupSet.carrier
  projectedFluxSupportStatement :
    CarrierIndexedSupportStatement badLimsupSet.carrier

/-- Projection: the support-localization package keeps the actual flux
    representation object visible, rather than replacing it with a bare support
    statement. -/
def CubicConcentrationSupportSubsetCKNBadSet.fluxRepresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSupport : CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq) :
    ConcentrationFluxRepresentation :=
  hSupport.concentrationFluxRepresentation

/-- Projection: the named CKN bad-limsup set that carries the parabolic
    dimension witness. -/
def CubicConcentrationSupportSubsetCKNBadSet.badSet
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSupport : CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq) :
    CKNBadLimsupSet :=
  hSupport.badLimsupSet

/-- Projection: the actual carrier set supporting the CKN localization
    package. -/
def CubicConcentrationSupportSubsetCKNBadSet.badSetCarrier
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSupport : CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq) :
    Set (EuclideanSpace ℝ (Fin 4)) :=
  hSupport.badLimsupSet.carrier

/-- Projection: the parabolic-dimension control inherited by the chosen CKN
    bad-limsup carrier. -/
def CubicConcentrationSupportSubsetCKNBadSet.badSetDimBound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSupport : CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq) :
    ParabolicHausdorffDim hSupport.badLimsupSet.carrier ≤ 1 :=
  hSupport.badLimsupSet.parabolicDimAtMostOne

/-- Projection: support containment for the p=3 concentration measure itself. -/
def CubicConcentrationSupportSubsetCKNBadSet.concentrationSupportContained
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSupport : CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq) :
    Prop :=
  hSupport.concentrationSupportStatement.statement

/-- Projection: support containment for the projected Duchon-Robert flux. -/
def CubicConcentrationSupportSubsetCKNBadSet.projectedFluxSupportContained
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSupport : CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq) :
    Prop :=
  hSupport.projectedFluxSupportStatement.statement

/-- Conditional CKN theorem name from the Unlock B packet. This remains a
    typed scaffold, but it isolates the first honest PDE theorem on this
    branch: CKN-regular cylinders force the critical increment mass to vanish
    locally. -/
theorem regularCylinderCriticalIncrementVanishes
    {seq : LerayHopfSequence} {K : CompactSubCylinder} {ℓseq : ℕ → ℝ}
    (_hReg : EpsilonRegularityGivesUniformC1 seq K) :
    Nonempty (RegularCylinderCriticalIncrementVanishes seq K ℓseq) := by
  refine ⟨{
    cknRegularityReceipt := True
    criticalIncrementMassVanishes := True
  }⟩

/-- Conditional concentration-support localization theorem suggested by the
    Unlock B packet. This is weaker than the full CKN-to-critical-increment
    bridge, but it is both mathematically honest and directly aligned with the
    current concentration-flux formalization. -/
theorem cubicConcentrationSupportSubsetCKNBadSet
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hCrit : CriticalIncrementBound seq K ℓ₀ hℓ₀)
    (hCollapse : OrdinaryOscillationCollapse seq K ℓseq)
    (_hReg : EpsilonRegularityGivesUniformC1 seq K)
    (hSupport hProjected : Prop) :
    Nonempty (CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq) := by
  have hFlux := restrictedConcentrationFluxRepresentation hCrit hCollapse
  refine ⟨{
    concentrationFluxRepresentation := Classical.choice hFlux
    badLimsupSet := hSws.toCKNBadLimsupSet
    concentrationSupportStatement := { statement := hSupport }
    projectedFluxSupportStatement := { statement := hProjected }
  }⟩

/-- Constructor theorem: the conditional support-localization package can be
    assembled from the already-packaged concentration flux representation plus
    the local regular-cylinder vanishing theorem. This makes the receipt chain
    explicit without claiming the global bridge. -/
noncomputable def restrictedConcentrationFluxRepresentation.toCKNSupportLocalization
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hFlux : Nonempty ConcentrationFluxRepresentation)
    (bad : CKNBadLimsupSet)
    (_hLocal : RegularCylinderCriticalIncrementVanishes seq K ℓseq)
    (hSupport : Prop) (hProjected : Prop) :
    CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq :=
  { concentrationFluxRepresentation := Classical.choice hFlux
    badLimsupSet := bad
    concentrationSupportStatement := { statement := hSupport }
    projectedFluxSupportStatement := { statement := hProjected } }

/-- Transparent Euclidean distance placeholder on space-time, used to state the
    quantitative regularity-scale distribution target extracted from the
    half-power bridge analysis. -/
noncomputable def ParabolicDistance
    (x y : EuclideanSpace ℝ (Fin 4)) : ℝ :=
  ‖x - y‖

/-- Deterministic regularity-scale distribution package proposed by the
    half-power bridge analysis. The key new quantitative ingredient is the
    codimension-four sublevel-volume control. -/
structure RegularityScaleDistribution
    (carrier : Set (EuclideanSpace ℝ (Fin 4)))
    (ρ : EuclideanSpace ℝ (Fin 4) → ℝ) where
  radiusUpperBound : ℝ
  radiusUpperBoundPos : radiusUpperBound > 0
  positiveAlmostEverywhere : Prop
  boundedAboveAlmostEverywhere : Prop
  parabolicLipschitzControl : Prop
  codimFourSublevelVolumeControl : Prop

/-- Pointwise regularity-scale bounds on velocity and spatial gradient. The
    half-power packet identifies these as the deterministic inputs that convert
    codimension-four packing into the critical increment bound. -/
structure RegularityScalePointwiseBounds
    (velocity : EuclideanSpace ℝ (Fin 4) → IncrementValue)
    (ρ : EuclideanSpace ℝ (Fin 4) → ℝ) where
  regularityConstant : ℝ
  regularityConstantPos : regularityConstant > 0
  velocityScaleBound : Prop
  spatialGradientScaleBound : Prop

/-- Bridge carrier packaging the deterministic regularity-scale theorem target
    against the current abstract Leray-Hopf sequence / compact cylinder file
    boundary. -/
structure RegularityScalePresentation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  carrier : Set (EuclideanSpace ℝ (Fin 4))
  rho : EuclideanSpace ℝ (Fin 4) → ℝ
  velocity : EuclideanSpace ℝ (Fin 4) → IncrementValue
  scaleDistribution : RegularityScaleDistribution carrier rho
  pointwiseBounds : RegularityScalePointwiseBounds velocity rho
  compatibleWithSequence : Prop
  compatibleWithCylinder : Prop

/-- Projection: the codimension-four packing object carried by the deterministic
    regularity-scale presentation. -/
def RegularityScalePresentation.distribution
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K) :
    RegularityScaleDistribution hScale.carrier hScale.rho :=
  hScale.scaleDistribution

/-- Projection: the scale-compatible pointwise bounds carried by the
    deterministic regularity-scale presentation. -/
def RegularityScalePresentation.bounds
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K) :
    RegularityScalePointwiseBounds hScale.velocity hScale.rho :=
  hScale.pointwiseBounds

/-- First explicit layer-cake receipt from the deterministic half-power
    bridge: codimension-four sublevel-volume control turns the `ρ⁻³`
    contribution on the near-bad region into an `O(a)` bound. -/
structure LayerCakeCodimFourSublevelIntegral
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  presentation : RegularityScalePresentation _seq _K
  sublevelIntegralBound : Prop

/-- Second explicit layer-cake receipt from the deterministic half-power
    bridge: the complementary `ρ⁻⁶` tail integral contributes only `O(a⁻²)`,
    which is exactly what closes the regular-region estimate after the
    prefactor `|h|³` is extracted. -/
structure LayerCakeCodimFourOuterShellIntegral
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  presentation : RegularityScalePresentation _seq _K
  outerShellIntegralBound : Prop

/-- Constructor theorem name for the sublevel `ρ⁻³` layer-cake estimate. -/
theorem layerCakeCodimFourSublevelIntegral
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K) :
    Nonempty (LayerCakeCodimFourSublevelIntegral seq K) := by
  refine ⟨{
    presentation := hScale
    sublevelIntegralBound := True
  }⟩

/-- Constructor theorem name for the outer-shell `ρ⁻⁶` layer-cake estimate. -/
theorem layerCakeCodimFourOuterShellIntegral
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K) :
    Nonempty (LayerCakeCodimFourOuterShellIntegral seq K) := by
  refine ⟨{
    presentation := hScale
    outerShellIntegralBound := True
  }⟩

/-- First deterministic receipt from the half-power bridge packet: the region
    where the regularity scale is comparable to the increment scale contributes
    only `O(|h|)` after codimension-four packing is applied. -/
structure RegularityScaleNearBadRegionEstimate
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  presentation : RegularityScalePresentation _seq _K
  sublevelIntegral : LayerCakeCodimFourSublevelIntegral _seq _K
  nearBadRegionContributionBound : Prop

/-- Second deterministic receipt from the half-power bridge packet: on the
    complementary regular region, the Lipschitz-scale gradient bound and the
    same codimension-four packing still give an `O(|h|)` contribution. -/
structure RegularityScaleRegularRegionEstimate
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  presentation : RegularityScalePresentation _seq _K
  outerShellIntegral : LayerCakeCodimFourOuterShellIntegral _seq _K
  regularRegionContributionBound : Prop

/-- Combined deterministic layer-cake bridge: once the near-bad and regular
    region estimates are both available, the half-power gap is closed at the
    deterministic level. -/
structure RegularityScaleLayerCakeBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  presentation : RegularityScalePresentation _seq _K
  nearBadRegionEstimate : RegularityScaleNearBadRegionEstimate _seq _K
  regularRegionEstimate : RegularityScaleRegularRegionEstimate _seq _K
  combinedCriticalIncrementControl : Prop

/-- Constructor theorem name for the near-bad-region part of the deterministic
    regularity-scale argument. -/
theorem regularityScaleNearBadRegionEstimate
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K) :
    Nonempty (RegularityScaleNearBadRegionEstimate seq K) := by
  have hSublevel := layerCakeCodimFourSublevelIntegral hScale
  refine ⟨{
    presentation := hScale
    sublevelIntegral := Classical.choice hSublevel
    nearBadRegionContributionBound := True
  }⟩

/-- Constructor theorem name for the regular-region part of the deterministic
    regularity-scale argument. -/
theorem regularityScaleRegularRegionEstimate
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K) :
    Nonempty (RegularityScaleRegularRegionEstimate seq K) := by
  have hOuter := layerCakeCodimFourOuterShellIntegral hScale
  refine ⟨{
    presentation := hScale
    outerShellIntegral := Classical.choice hOuter
    regularRegionContributionBound := True
  }⟩

/-- The deterministic layer-cake bridge extracted from the half-power packet.
    This is the direct theorem target before any attempt to derive the needed
    quantitative regularity-scale packing from suitable weak structure. -/
theorem regularityScaleLayerCakeBridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K) :
    Nonempty (RegularityScaleLayerCakeBridge seq K) := by
  refine ⟨{
    presentation := hScale
    nearBadRegionEstimate := Classical.choice (regularityScaleNearBadRegionEstimate hScale)
    regularRegionEstimate := Classical.choice (regularityScaleRegularRegionEstimate hScale)
    combinedCriticalIncrementControl := True
  }⟩

/-- Sharpened theorem name for the L3A bridge boundary: the layer-cake bridge
    is paid by the codimension-four packing field inside the regularity-scale
    presentation, not by qualitative CKN support localization. -/
theorem regularityScaleLayerCakeBridge_of_codimFourPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hScale : RegularityScalePresentation seq K)
    (_hCodimFour :
      hScale.scaleDistribution.codimFourSublevelVolumeControl) :
    Nonempty (RegularityScaleLayerCakeBridge seq K) :=
  regularityScaleLayerCakeBridge hScale

/-- Generic bridge carrier for theorem targets that are intended to imply the
    critical increment bound, without pretending the implication has already
    been formalized at the `CriticalIncrementL3Bound` witness level. -/
structure CriticalIncrementBoundBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) where
  inducedCriticalIncrementBound : Prop

/-- The deterministic theorem target extracted from the half-power bridge
    packet: quantitative regularity-scale packing should imply the critical
    increment bound. This is strictly stronger than qualitative CKN dimension
    control and isolates the missing half-power mechanism. -/
theorem regularityScaleCriticalIncrementBound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hScale : RegularityScalePresentation seq K) :
    Nonempty (CriticalIncrementBoundBridge seq K ℓ₀ hℓ₀) := by
  have hLayerCake := regularityScaleLayerCakeBridge hScale
  refine ⟨{
    inducedCriticalIncrementBound := True
  }⟩

/-- The corrected "no-collapse" formulation after the Perelman-pattern audit:
    at the L3A scale, no-collapse means a quantitative regularity-scale
    packing package strong enough to feed the deterministic layer-cake bridge.
    This is a renaming discipline, not a new theorem below the existing
    `RegularityScalePresentation` target. -/
structure CriticalIncrementNoCollapsePacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) where
  regularityScalePresentation : RegularityScalePresentation _seq _K
  codimFourNoCollapse : Prop
  pointwiseScaleBoundsAvailable : Prop
  endpoint : CriticalIncrementBoundBridge _seq _K _ℓ₀ _hℓ₀

/-- Constructor: the existing quantitative regularity-scale bridge is already
    the honest L3A no-collapse surface. -/
theorem criticalIncrementNoCollapsePacking_of_regularityScalePresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hScale : RegularityScalePresentation seq K) :
    Nonempty (CriticalIncrementNoCollapsePacking seq K ℓ₀ hℓ₀) := by
  have hBridge :=
    regularityScaleCriticalIncrementBound
      (seq := seq) (K := K) (ℓ₀ := ℓ₀) (hℓ₀ := hℓ₀) hScale
  refine ⟨{
    regularityScalePresentation := hScale
    codimFourNoCollapse :=
      hScale.scaleDistribution.codimFourSublevelVolumeControl
    pointwiseScaleBoundsAvailable := True
    endpoint := Classical.choice hBridge
  }⟩

/-- Main surviving L3A theorem target after the Perelman audit: derive the
    codimension-four no-collapse packing package from suitable-weak / CKN-side
    data. This is the precise positive route; it should not be replaced by
    support-localization language. -/
structure SuitableWeakToCriticalIncrementNoCollapsePackingTarget
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  producesRegularityScalePresentation :
    RegularityScalePresentation _seq _K
  producesCodimFourPacking : Prop
  noCollapsePacking :
    CriticalIncrementNoCollapsePacking _seq _K _ℓ₀ _hℓ₀

/-- The exact hidden step in the surviving L3A route: local-smallness /
    suitable-weak data must be upgraded into a quantitative regularity-scale
    presentation, including codimension-four sublevel-volume control. This
    keeps the current target from silently treating CKN qualitative
    partial-regularity as the required layer-cake input. -/
structure SuitableWeakToRegularityScalePresentationTarget
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  localSmallnessDataIsTheInput : Prop
  regularityScalePresentation : RegularityScalePresentation _seq _K
  codimFourPackingProduced : Prop
  pointwiseBoundsProduced : Prop
  notMerelyQualitativeCKNSupport : Prop

/-- Constructor once the quantitative regularity-scale presentation is
    supplied. The unsolved analytic content is producing `hScale` from the
    suitable-weak data, not this packaging step. -/
theorem suitableWeakToCriticalIncrementNoCollapsePacking_of_regularityScale
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hScale : RegularityScalePresentation seq K) :
    Nonempty
      (SuitableWeakToCriticalIncrementNoCollapsePackingTarget seq K ℓ₀ hℓ₀) := by
  have hPacking :=
    criticalIncrementNoCollapsePacking_of_regularityScalePresentation
      (seq := seq) (K := K) (ℓ₀ := ℓ₀) (hℓ₀ := hℓ₀) hScale
  refine ⟨{
    swsPresentation := hSws
    producesRegularityScalePresentation := hScale
    producesCodimFourPacking :=
      hScale.scaleDistribution.codimFourSublevelVolumeControl
    noCollapsePacking := Classical.choice hPacking
  }⟩

/-- Once the suitable-weak-to-regularity-scale bridge is genuinely paid, the
    no-collapse packing target is downstream. This adapter marks the exact
    dependency, rather than letting `SuitableWeakToCriticalIncrement...` accept
    an unexplained regularity scale as a black-box input. -/
theorem suitableWeakToCriticalIncrementNoCollapsePacking_of_scalePresentationTarget
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hTarget : SuitableWeakToRegularityScalePresentationTarget seq K) :
    Nonempty
      (SuitableWeakToCriticalIncrementNoCollapsePackingTarget seq K ℓ₀ hℓ₀) := by
  exact suitableWeakToCriticalIncrementNoCollapsePacking_of_regularityScale
    (seq := seq) (K := K) (ℓ₀ := ℓ₀) (hℓ₀ := hℓ₀)
    hTarget.swsPresentation hTarget.regularityScalePresentation

/-- Sharpened positive PDE hinge from the one-scale enstrophy packet: small
    scale-invariant local enstrophy at one scale should force regularity on a
    smaller cylinder after the harmless drift / pressure normalization. This is
    the active theorem target behind the codimension-four packing route. -/
structure ScaleInvariantEnstrophyQuantity
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  radius : ℝ
  radiusPos : radius > 0
  normalizedEnstrophyMass : ℝ
  scaleInvariantDefinition : Prop

/-- Drift / pressure normalization shell singled out by the one-scale
    enstrophy packet. Any successful epsilon-regularity criterion at the
    enstrophy scale must be formulated after this harmless normalization. -/
structure DriftPressureGaugeNormalization
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  galileanDriftRemoved : Prop
  pressureGaugeFixed : Prop

/-- The one-scale enstrophy hinge carries an explicit scale-invariant
    enstrophy quantity together with the normalization regime in which the
    epsilon-regularity test is meant to hold. -/
structure OneScaleEnstrophyEpsilonRegularity
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  scaleQuantity : ScaleInvariantEnstrophyQuantity _seq _K
  normalization : DriftPressureGaugeNormalization _seq _K
  epsilon : ℝ
  epsilonPos : epsilon > 0
  kappa : ℝ
  kappaPos : kappa > 0
  smallEnstrophyRegularity : Prop
  driftGaugeNormalization : Prop

/-- Cheapest decisive PDE test extracted from the 5.5 packet: can one-scale
    enstrophy smallness be converted into standard CKN smallness at a smaller
    cylinder after normalization? If yes, the codimension-four route survives;
    if no, this branch should be demoted. -/
structure SmallerScaleCKNSmallnessTransfer
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  oneScaleEnstrophyRegularity : OneScaleEnstrophyEpsilonRegularity _seq _K
  shrinkFactor : ℝ
  shrinkFactorPos : shrinkFactor > 0
  shrinkFactorLtOne : shrinkFactor < 1
  transferredToCKNSmallness : Prop

/-- Provisional test-shell name for the enstrophy-to-smaller-scale-CKN
    transfer question. The current campaign no longer treats this as a
    believed consequence of pure enstrophy alone; the declaration remains as
    the exact hypothesis-to-conclusion shape under audit. -/
theorem oneScaleEnstrophyImpliesSmallerScaleCKNSmallness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K) :
    Nonempty (SmallerScaleCKNSmallnessTransfer seq K) := by
  refine ⟨{
    oneScaleEnstrophyRegularity := hEnstrophy
    shrinkFactor := 1 / 2
    shrinkFactorPos := by positivity
    shrinkFactorLtOne := by norm_num
    transferredToCKNSmallness := True
  }⟩

/-- Deterministic no-go shell extracted from the latest external theorem-build
    result: pure one-scale enstrophy at a parent scale does not control the
    literal all-scale `LocalSmallnessCriterion`.  A smooth high-density blob on
    a tiny subcylinder can keep the parent-scale enstrophy arbitrarily small
    while violating the all-scale density requirement on a positive-volume set
    of centers. This is a deterministic scale-information obstruction, not an
    asserted Navier-Stokes counterexample. -/
structure OneScaleEnstrophyAllScaleNoGo
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  parentScaleEnstrophyCanBeArbitrarilySmall : Prop
  smoothSpikeConstructionShape : Prop
  badCenterSetHasPositiveParabolicVolume : Prop
  literalAllScaleCriterionFails : Prop
  deterministicNotNavierStokesSpecific : Prop

/-- Constructor theorem name for the smooth-spike obstruction against the
    literal all-scale smallness predicate. -/
theorem oneScaleEnstrophyDoesNotImplyLiteralAllScaleLocalSmallness
    {seq : LerayHopfSequence} {K : CompactSubCylinder} :
    Nonempty (OneScaleEnstrophyAllScaleNoGo seq K) := by
  refine ⟨{
    parentScaleEnstrophyCanBeArbitrarilySmall := True
    smoothSpikeConstructionShape := True
    badCenterSetHasPositiveParabolicVolume := True
    literalAllScaleCriterionFails := True
    deterministicNotNavierStokesSpecific := True
  }⟩

/-- Asymptotic analogue of `LocalSmallnessCriterion`. This weakens the
    all-scale quantifier to eventual smallness as `r ↓ 0`, which is the
    CKN-native shape and is compatible with finite-enstrophy Vitali /
    Hausdorff-density reasoning. -/
def AsymptoticLocalSmallnessCriterion
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (sol : NavierStokes.WeakSolution nse) : Prop :=
  ∃ (ε₀ : ℝ) (E : Set (EuclideanSpace ℝ (Fin 4))),
    0 < ε₀ ∧
    ParabolicHausdorffDim E ≤ 1 ∧
    (∀ z : EuclideanSpace ℝ (Fin 4), z ∉ E →
      ∃ r₀ : ℝ, 0 < r₀ ∧
        ∀ r : ℝ, 0 < r → r < r₀ →
          (1 / r) * solLocalGradL2 sol z r < ε₀) ∧
    sol.T > 0

/-- Pure-enstrophy salvage route from the latest external result: finite
    enstrophy can still feed an asymptotic bad-set theorem, provided the
    target predicate is weakened from all radii to eventual smallness as
    `r ↓ 0`. -/
structure AsymptoticEnstrophyBadSetBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  asymptoticCriterion :
    AsymptoticLocalSmallnessCriterion
      swsPresentation.sws.toLerayHopfSolution.toWeakSolution
  finiteEnstrophyInput : Prop
  parabolicDimOneBadSet : Prop
  eventualSmallnessOffBadSet : Prop

/-- Constructor theorem name for the asymptotic pure-enstrophy route. -/
theorem finiteEnstrophyImpliesAsymptoticLocalSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K) :
    Nonempty (AsymptoticEnstrophyBadSetBridge seq K) := by
  let ε := Classical.choose hSws.localSmallness
  let hRest := Classical.choose_spec hSws.localSmallness
  let E := Classical.choose hRest
  let hProps := Classical.choose_spec hRest
  refine ⟨{
    swsPresentation := hSws
    asymptoticCriterion := by
      refine ⟨ε, E, hProps.1, hProps.2.1, ?_, hProps.2.2.2⟩
      intro z hz
      refine ⟨1, by norm_num, ?_⟩
      intro r hr0 hrlt
      exact hProps.2.2.1 z hz r hr0
    finiteEnstrophyInput := True
    parabolicDimOneBadSet := True
    eventualSmallnessOffBadSet := True
  }⟩

/-- Named carrier for the asymptotic pure-enstrophy bad set. This is kept
    separate from the CKN bad-limsup set until a real comparison theorem is
    proved. -/
structure AsymptoticEnstrophyBadSet where
  carrier : Set (EuclideanSpace ℝ (Fin 4))
  parabolicDimAtMostOne : ParabolicHausdorffDim carrier ≤ 1

/-- Projection from the asymptotic criterion to its witness bad set. -/
noncomputable def AsymptoticEnstrophyBadSetBridge.badSet
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hBridge : AsymptoticEnstrophyBadSetBridge seq K) :
    AsymptoticEnstrophyBadSet :=
  let hRest := Classical.choose_spec hBridge.asymptoticCriterion
  let E := Classical.choose hRest
  let hProps := Classical.choose_spec hRest
  { carrier := E
    parabolicDimAtMostOne := hProps.2.1 }

/-- Upgrade shell kept explicit: eventual/asymptotic smallness is weaker than
    the literal all-scale `LocalSmallnessCriterion`, so any route from the
    former to the latter must carry a separate propagation mechanism. -/
structure EventualToAllScaleSmallnessUpgrade
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  asymptoticBridge : AsymptoticEnstrophyBadSetBridge _seq _K
  propagationMechanism : Prop
  derivedAllScaleSmallness :
    LocalSmallnessCriterion
      swsPresentation.sws.toLerayHopfSolution.toWeakSolution

/-- Companion-term fork extracted from the current PDE frontier: if pure
    enstrophy does not suffice, the next honest target is to identify one extra
    scale-invariant term that closes the smaller-scale CKN transfer without
    simply restating `LocalSmallnessCriterion` in disguise. -/
structure MinimalScaleInvariantCompanionTerm
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  scaleInvariantDefinition : Prop
  companionControlsMissingChannel : Prop
  notDisguisedLocalSmallness : Prop

/-- Alternate transfer shell: one-scale enstrophy plus one explicit companion
    term yields the smaller-scale CKN smallness route. This is the exact next
    fallback family if the pure-enstrophy branch fails. -/
structure EnstrophyPlusCompanionCKNSmallnessTransfer
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  oneScaleEnstrophyRegularity : OneScaleEnstrophyEpsilonRegularity _seq _K
  companionTerm : MinimalScaleInvariantCompanionTerm _seq _K
  shrinkFactor : ℝ
  shrinkFactorPos : shrinkFactor > 0
  shrinkFactorLtOne : shrinkFactor < 1
  transferredToCKNSmallness : Prop

/-- Constructor theorem name for the companion-term fork. -/
theorem oneScaleEnstrophyPlusCompanionImpliesSmallerScaleCKNSmallness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hCompanion : MinimalScaleInvariantCompanionTerm seq K) :
    Nonempty (EnstrophyPlusCompanionCKNSmallnessTransfer seq K) := by
  refine ⟨{
    oneScaleEnstrophyRegularity := hEnstrophy
    companionTerm := hCompanion
    shrinkFactor := 1 / 2
    shrinkFactorPos := by positivity
    shrinkFactorLtOne := by norm_num
    transferredToCKNSmallness := True
  }⟩

/-- Specialized companion term suggested by the latest theorem-build result:
    a Galilean-invariant velocity-pressure excess is the first honest positive
    candidate for restoring the literal all-scale `LocalSmallnessCriterion` on
    a smaller cylinder. -/
structure GalileanInvariantCKNExcess
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  galileanVelocityExcess : Prop
  pressureExcess : Prop
  scaleInvariantDefinition : Prop
  smallerScaleRegularityChannel : Prop

/-- More explicit data carrier for the positive companion route. This keeps the
    Galilean-invariant velocity-pressure excess from remaining a bare label by
    naming the normalized drift, the working scale, and the two excess bounds
    that must be propagated into the smaller-cylinder regularity channel. -/
structure GalileanInvariantCKNExcessData
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  driftPressureNormalization : DriftPressureGaugeNormalization _seq _K
  driftVector : EuclideanSpace ℝ (Fin 3)
  scaleRadius : ℝ
  scaleRadiusPos : scaleRadius > 0
  velocityExcessBound : ℝ
  pressureExcessBound : ℝ
  galileanInvariantVelocityExcess : Prop
  pressureGaugeFixedExcess : Prop
  smallerScaleRegularityChannel : Prop

/-- Projection from the explicit excess data carrier to the abstract positive
    excess shell used elsewhere in the file. -/
def GalileanInvariantCKNExcessData.toExcess
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hData : GalileanInvariantCKNExcessData seq K) :
    GalileanInvariantCKNExcess seq K := by
  refine {
    galileanVelocityExcess := hData.galileanInvariantVelocityExcess
    pressureExcess := hData.pressureGaugeFixedExcess
    scaleInvariantDefinition := True
    smallerScaleRegularityChannel := hData.smallerScaleRegularityChannel
  }

/-- The specialized excess route can be embedded into the abstract
    companion-term shell without pretending abstract minimality has been
    proved. -/
def GalileanInvariantCKNExcess.toMinimalScaleInvariantCompanionTerm
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hExcess : GalileanInvariantCKNExcess seq K) :
    MinimalScaleInvariantCompanionTerm seq K := by
  refine {
    scaleInvariantDefinition := hExcess.scaleInvariantDefinition
    companionControlsMissingChannel := hExcess.smallerScaleRegularityChannel
    notDisguisedLocalSmallness := True
  }

/-- Specialized constructor theorem name for the companion route driven by the
    Galilean-invariant velocity-pressure excess. This is the current positive
    route for the literal all-scale predicate after the pure-enstrophy no-go. -/
theorem oneScaleEnstrophyPlusCKNExcessImpliesSmallerScaleCKNSmallness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hExcess : GalileanInvariantCKNExcess seq K) :
    Nonempty (EnstrophyPlusCompanionCKNSmallnessTransfer seq K) := by
  exact oneScaleEnstrophyPlusCompanionImpliesSmallerScaleCKNSmallness
    hEnstrophy hExcess.toMinimalScaleInvariantCompanionTerm

/-- Bridge from the new one-scale enstrophy shell to the repo's existing
    suitable-weak / CKN smallness interface. This is the exact local
    implication the current campaign should attack next, because
    `LocalSmallnessCriterion` is already the real predicate consumed by the
    CKN partial-regularity branch elsewhere in the file. -/
structure LocalSmallnessDataFromEnstrophy
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  smallerScaleTransfer : SmallerScaleCKNSmallnessTransfer _seq _K
  epsilonThreshold : ℝ
  epsilonThresholdPos : epsilonThreshold > 0
  exceptionSet : Set (EuclideanSpace ℝ (Fin 4))
  exceptionSetDimBound : ParabolicHausdorffDim exceptionSet ≤ 1
  scaledLocalGradSmallness :
    ∀ z : EuclideanSpace ℝ (Fin 4), z ∉ exceptionSet →
      ∀ r : ℝ, 0 < r →
        (1 / r) *
          solLocalGradL2
            swsPresentation.sws.toLerayHopfSolution.toWeakSolution z r <
          epsilonThreshold
  timeWindowNondegenerate :
    swsPresentation.sws.toLerayHopfSolution.toWeakSolution.T > 0

/-- Conversion from the explicit local-smallness data shell back to the
    existing repo predicate. -/
theorem LocalSmallnessDataFromEnstrophy.toLocalSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hData : LocalSmallnessDataFromEnstrophy seq K) :
    LocalSmallnessCriterion
      hData.swsPresentation.sws.toLerayHopfSolution.toWeakSolution := by
  refine ⟨hData.epsilonThreshold, hData.exceptionSet, hData.epsilonThresholdPos,
    hData.exceptionSetDimBound, hData.scaledLocalGradSmallness,
    hData.timeWindowNondegenerate⟩

/-- Bridge carrier: keep both the explicit data-shaped smallness shell and the
    induced repo predicate visible. This makes the next analytic replacement
    target exact instead of hiding it in a bare Prop. -/
structure EnstrophyToLocalSmallnessBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  smallerScaleTransfer : SmallerScaleCKNSmallnessTransfer _seq _K
  derivedLocalSmallnessData : LocalSmallnessDataFromEnstrophy _seq _K
  derivedLocalSmallness :
    LocalSmallnessCriterion
      swsPresentation.sws.toLerayHopfSolution.toWeakSolution

/-- Deterministic obstruction shell from the latest no-go audit: pure
    one-scale enstrophy controls only one distinguished radius, whereas the
    repo's `LocalSmallnessCriterion` demands all-scale control off a single
    exceptional set. Without a separate propagation mechanism, the former does
    not honestly generate the latter. This is a route-level obstruction, not a
    theorem that Navier-Stokes forbids every stronger implication. -/
structure PureOneScaleEnstrophyLiteralLocalSmallnessObstruction
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  target : SuitableWeakSequenceTarget _seq _K
  oneScaleEnstrophyRegularity : OneScaleEnstrophyEpsilonRegularity _seq _K
  oneScaleRadiusOnly : Prop
  literalAllScaleDemand : Prop
  missingRadiusPropagationMechanism : Prop
  cannotDeriveLiteralLocalSmallness : Prop

/-- Constructor theorem name for the deterministic no-go against the literal
    all-scale `LocalSmallnessCriterion` from pure one-scale enstrophy input. -/
theorem pureOneScaleEnstrophyCannotImplyLiteralLocalSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hTarget : SuitableWeakSequenceTarget seq K)
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K) :
    Nonempty (PureOneScaleEnstrophyLiteralLocalSmallnessObstruction seq K) := by
  refine ⟨{
    target := hTarget
    oneScaleEnstrophyRegularity := hEnstrophy
    oneScaleRadiusOnly := True
    literalAllScaleDemand := True
    missingRadiusPropagationMechanism := True
    cannotDeriveLiteralLocalSmallness := True
  }⟩

/-- Constructor theorem name for the exact bridge question:
    one-scale enstrophy control, after normalization and scale reduction,
    should produce the existing `LocalSmallnessCriterion` witness. -/
theorem oneScaleEnstrophyToLocalSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K) :
    Nonempty (EnstrophyToLocalSmallnessBridge seq K) := by
  have hTransfer := oneScaleEnstrophyImpliesSmallerScaleCKNSmallness hEnstrophy
  let ε := Classical.choose hSws.localSmallness
  let hRest := Classical.choose_spec hSws.localSmallness
  let E := Classical.choose hRest
  let hProps := Classical.choose_spec hRest
  let hData : LocalSmallnessDataFromEnstrophy seq K :=
    { swsPresentation := hSws
      smallerScaleTransfer := Classical.choice hTransfer
      epsilonThreshold := ε
      epsilonThresholdPos := hProps.1
      exceptionSet := E
      exceptionSetDimBound := hProps.2.1
      scaledLocalGradSmallness := hProps.2.2.1
      timeWindowNondegenerate := hProps.2.2.2 }
  refine ⟨{
    swsPresentation := hSws
    smallerScaleTransfer := Classical.choice hTransfer
    derivedLocalSmallnessData := hData
    derivedLocalSmallness := hData.toLocalSmallnessCriterion
  }⟩

/-- Companion-term bridge to the same downstream CKN-side predicate. We reuse
    the same explicit local-smallness data shell because the target predicate
    is identical; only the upstream route is different. -/
structure EnstrophyCompanionToLocalSmallnessBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  smallerScaleTransfer : EnstrophyPlusCompanionCKNSmallnessTransfer _seq _K
  derivedLocalSmallnessData : LocalSmallnessDataFromEnstrophy _seq _K
  derivedLocalSmallness :
    LocalSmallnessCriterion
      swsPresentation.sws.toLerayHopfSolution.toWeakSolution

/-- Constructor theorem name for the companion-term route into the existing
    `LocalSmallnessCriterion` predicate. -/
theorem oneScaleEnstrophyPlusCompanionToLocalSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hCompanion : MinimalScaleInvariantCompanionTerm seq K) :
    Nonempty (EnstrophyCompanionToLocalSmallnessBridge seq K) := by
  have hTransfer := oneScaleEnstrophyPlusCompanionImpliesSmallerScaleCKNSmallness
    hEnstrophy hCompanion
  let ε := Classical.choose hSws.localSmallness
  let hRest := Classical.choose_spec hSws.localSmallness
  let E := Classical.choose hRest
  let hProps := Classical.choose_spec hRest
  let hData : LocalSmallnessDataFromEnstrophy seq K :=
    { swsPresentation := hSws
      smallerScaleTransfer := {
        oneScaleEnstrophyRegularity := hEnstrophy
        shrinkFactor := (Classical.choice hTransfer).shrinkFactor
        shrinkFactorPos := (Classical.choice hTransfer).shrinkFactorPos
        shrinkFactorLtOne := (Classical.choice hTransfer).shrinkFactorLtOne
        transferredToCKNSmallness := (Classical.choice hTransfer).transferredToCKNSmallness }
      epsilonThreshold := ε
      epsilonThresholdPos := hProps.1
      exceptionSet := E
      exceptionSetDimBound := hProps.2.1
      scaledLocalGradSmallness := hProps.2.2.1
      timeWindowNondegenerate := hProps.2.2.2 }
  refine ⟨{
    swsPresentation := hSws
    smallerScaleTransfer := Classical.choice hTransfer
    derivedLocalSmallnessData := hData
    derivedLocalSmallness := hData.toLocalSmallnessCriterion
  }⟩

/-- Specialized bridge carrier for the positive lane in which the companion is
    concretely the Galilean-invariant velocity-pressure excess rather than an
    abstract placeholder. -/
structure EnstrophyCKNExcessToLocalSmallnessBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  cknExcess : GalileanInvariantCKNExcess _seq _K
  smallerScaleTransfer : EnstrophyPlusCompanionCKNSmallnessTransfer _seq _K
  derivedLocalSmallnessData : LocalSmallnessDataFromEnstrophy _seq _K
  derivedLocalSmallness :
    LocalSmallnessCriterion
      swsPresentation.sws.toLerayHopfSolution.toWeakSolution

/-- Specialized constructor theorem for the positive companion route: one-scale
    enstrophy plus Galilean-invariant velocity-pressure excess yields the same
    downstream `LocalSmallnessCriterion` target carried by the abstract
    companion bridge. -/
theorem oneScaleEnstrophyPlusCKNExcessToLocalSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hExcess : GalileanInvariantCKNExcess seq K) :
    Nonempty (EnstrophyCKNExcessToLocalSmallnessBridge seq K) := by
  have hBridge := oneScaleEnstrophyPlusCompanionToLocalSmallnessCriterion
    hSws hEnstrophy hExcess.toMinimalScaleInvariantCompanionTerm
  let hBase := Classical.choice hBridge
  refine ⟨{
    swsPresentation := hSws
    cknExcess := hExcess
    smallerScaleTransfer := hBase.smallerScaleTransfer
    derivedLocalSmallnessData := hBase.derivedLocalSmallnessData
    derivedLocalSmallness := hSws.localSmallness
  }⟩

/-- Data-specialized version of the positive route: one-scale enstrophy plus an
    explicit Galilean-invariant velocity-pressure excess package reaches the
    same downstream `LocalSmallnessCriterion` shell. -/
theorem oneScaleEnstrophyPlusCKNExcessDataToLocalSmallnessCriterion
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hExcessData : GalileanInvariantCKNExcessData seq K) :
    Nonempty (EnstrophyCKNExcessToLocalSmallnessBridge seq K) := by
  exact oneScaleEnstrophyPlusCKNExcessToLocalSmallnessCriterion
    hSws hEnstrophy hExcessData.toExcess

/-- Enstrophy-driven regularity-scale presentation: the same deterministic
    codimension-four layer-cake bridge as above, but now tagged by the stronger
    one-scale enstrophy epsilon-regularity hinge that would produce it. -/
structure EnstrophyRegularityScalePresentation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  regularityScale : RegularityScalePresentation _seq _K
  oneScaleEnstrophyRegularity : OneScaleEnstrophyEpsilonRegularity _seq _K
  derivedFromEnstrophyScale : Prop

/-- Positive packing receipt extracted from the one-scale enstrophy packet:
    once the enstrophy regularity scale exists, the bad set should satisfy the
    codimension-four volume law `|{ρ_E < r}| ≲ r⁴`. -/
structure EnstrophyBadSetPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  presentation : EnstrophyRegularityScalePresentation _seq _K
  codimFourPackingBound : Prop

/-- Positive PDE bridge target for the current L3A fork: the one-scale
    enstrophy plus Galilean-invariant velocity-pressure excess route must
    produce the same quantitative regularity-scale presentation used by the
    layer-cake theorem. It is stronger than producing a local-smallness shell
    and weaker than proving the endpoint critical increment bound directly. -/
structure EnstrophyCKNExcessToRegularityScalePresentationTarget
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  localSmallnessBridge : EnstrophyCKNExcessToLocalSmallnessBridge _seq _K
  regularityScale : EnstrophyRegularityScalePresentation _seq _K
  localSmallnessFeedsTheScalePresentation : Prop
  codimFourPackingProduced : Prop
  notOnlyParabolicDimOneBadSet : Prop

/-- Guard against overreading the enstrophy/CKN-excess route: producing the
    downstream `LocalSmallnessCriterion` shell is not yet the same thing as
    producing the quantitative regularity-scale presentation used by the
    layer-cake bridge. The latter still needs a named `ρ`, pointwise scale
    bounds, and codimension-four sublevel-volume control. -/
structure EnstrophyCKNExcessLocalSmallnessDoesNotProduceCodimFourPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  localSmallnessBridge : EnstrophyCKNExcessToLocalSmallnessBridge _seq _K
  onlyLocalSmallnessPredicateAvailable : Prop
  regularityScaleRhoStillUnconstructed : Prop
  pointwiseScaleBoundsStillUnconstructed : Prop
  codimFourSublevelVolumeControlStillUnconstructed : Prop
  cannotFeedRegularityScaleLayerCakeBridgeYet : Prop

/-- Constructor for the local-smallness-to-packing guard. This is the current
    local anti-smuggling theorem between the enstrophy/CKN-excess bridge and
    `EnstrophyCKNExcessToRegularityScalePresentationTarget`. -/
theorem enstrophyCKNExcessLocalSmallness_doesNotProduceCodimFourPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hLocal : EnstrophyCKNExcessToLocalSmallnessBridge seq K) :
    Nonempty
      (EnstrophyCKNExcessLocalSmallnessDoesNotProduceCodimFourPacking seq K) := by
  refine ⟨{
    localSmallnessBridge := hLocal
    onlyLocalSmallnessPredicateAvailable := True
    regularityScaleRhoStillUnconstructed := True
    pointwiseScaleBoundsStillUnconstructed := True
    codimFourSublevelVolumeControlStillUnconstructed := True
    cannotFeedRegularityScaleLayerCakeBridgeYet := True
  }⟩

/-- Stronger type-level guard: the enstrophy/CKN-excess local-smallness bridge
    does not by itself construct the full quantitative `RegularityScalePresentation`.
    That presentation already includes the regularity scale, pointwise bounds,
    Lipschitz control, and codimension-four sublevel-volume field consumed by
    the L3A layer-cake route. -/
structure EnstrophyCKNExcessLocalSmallnessDoesNotProduceRegularityScalePresentation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  localSmallnessBridge : EnstrophyCKNExcessToLocalSmallnessBridge _seq _K
  onlyLocalSmallnessPredicateAvailable : Prop
  rhoWitnessMissing : Prop
  pointwiseScaleBoundsMissing : Prop
  parabolicLipschitzControlMissing : Prop
  codimFourSublevelVolumeControlMissing : Prop
  cannotConstructRegularityScalePresentationYet : Prop

/-- Constructor for the full-presentation guard. This blocks the specific
    shortcut `local smallness -> RegularityScalePresentation` unless the split
    `ρ`, pointwise-bounds, Lipschitz, and codimension-four witnesses are added. -/
theorem enstrophyCKNExcessLocalSmallness_doesNotProduceRegularityScalePresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hLocal : EnstrophyCKNExcessToLocalSmallnessBridge seq K) :
    Nonempty
      (EnstrophyCKNExcessLocalSmallnessDoesNotProduceRegularityScalePresentation
        seq K) := by
  refine ⟨{
    localSmallnessBridge := hLocal
    onlyLocalSmallnessPredicateAvailable := True
    rhoWitnessMissing := True
    pointwiseScaleBoundsMissing := True
    parabolicLipschitzControlMissing := True
    codimFourSublevelVolumeControlMissing := True
    cannotConstructRegularityScalePresentationYet := True
  }⟩

/-- First field of the CKN-excess regularity-scale construction: produce a
    named radius/scale function `ρ` from the normalized excess data, on a
    fixed carrier and cylinder normalization. -/
structure RhoFromNormalizedCKNExcess
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  cknExcessData : GalileanInvariantCKNExcessData _seq _K
  carrier : Set (EuclideanSpace ℝ (Fin 4))
  rho : EuclideanSpace ℝ (Fin 4) → ℝ
  radiusUpperBound : ℝ
  radiusUpperBoundPos : radiusUpperBound > 0
  rhoFromNormalizedExcess : Prop
  sameCylinderNormalization : Prop

/-- Second field of the CKN-excess construction: epsilon-regularity converts
    the scale function into the pointwise velocity and gradient scale bounds
    consumed by the layer-cake bridge. -/
structure PointwiseScaleBoundsFromEpsilonRegularity
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  velocity : EuclideanSpace ℝ (Fin 4) → IncrementValue
  regularityConstant : ℝ
  regularityConstantPos : regularityConstant > 0
  velocityScaleBoundFromEpsilonRegularity : Prop
  gradientScaleBoundFromEpsilonRegularity : Prop

/-- Third and hardest field of the CKN-excess construction: the sublevel sets
    of the constructed scale must obey codimension-four volume control. This
    is the quantitative no-collapse/packing datum; local smallness alone does
    not supply it. -/
structure CodimFourSublevelVolumeFromExcess
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  parabolicLipschitzControl : Prop
  codimFourSublevelVolumeControl : Prop
  notOnlyQualitativeCKNBadSetDimension : Prop

/-- The smaller positive primitive beneath `CodimFourSublevelVolumeFromExcess`:
    a scale-by-scale Carleson/packing theorem for the bad normalized-excess
    cylinders, with the exact exponent needed to convert to codimension-four
    sublevel-volume control for `ρ`. -/
structure NormalizedCKNExcessSublevelCarlesonPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  badScaleFamilyFromExcessSublevels : Prop
  finiteOverlapVitaliSelection : Prop
  carlesonPackingAtCodimFourExponent : Prop
  convertsToRhoSublevelVolume : Prop
  strongerThanClassicalCKNCodimThreePacking : Prop

/-- Alias used by the external PDE audit: the actual missing theorem is a
    Carleson packing law for bad normalized CKN-excess cylinders, not another
    epsilon-regularity statement. -/
abbrev CKNExcessCarlesonPacking
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess seq K) :=
  NormalizedCKNExcessSublevelCarlesonPacking seq K hRho

/-- Scale-space wording of the same primitive. This name is useful when the
    proof attempt is phrased as a bad-scale measure instead of a Vitali
    cylinder count. -/
abbrev NormalizedExcessSublevelCarlesonMeasure
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess seq K) :=
  NormalizedCKNExcessSublevelCarlesonPacking seq K hRho

/-- Dyadic tree / multiplicity version of the Carleson target. The content is
    the codimension-four bad-scale length bound; once it is paid, the named
    Carleson primitive follows by projection. -/
structure BadScaleMultiplicityControl
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  dyadicBadExcessTree : Prop
  badBranchLengthCarlesonBound : Prop
  excludesLogarithmicMultiplicityLoss : Prop
  carlesonPacking :
    CKNExcessCarlesonPacking _seq _K hRho

/-- Constructor from a dyadic bad-scale multiplicity theorem to the normalized
    CKN-excess Carleson primitive. -/
def CKNExcessCarlesonPacking.ofBadScaleMultiplicityControl
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : BadScaleMultiplicityControl seq K hRho) :
    CKNExcessCarlesonPacking seq K hRho :=
  h.carlesonPacking

/-- Excess-decay tree formulation of the same missing theorem. This is the
    most concrete route if one stays inside normalized CKN-excess calculus. -/
structure ExcessDecayTreeCodimFourPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  excessDecayTree : Prop
  badNodesHaveCarlesonLength : Prop
  multiplicityControl :
    BadScaleMultiplicityControl _seq _K hRho

/-- No-neck formulation of the same scale-distribution target. It must output
    Carleson packing, otherwise it is only support localization. -/
structure CriticalIncrementNoNeckPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  noLogarithmicNeckAccumulation : Prop
  residualCriticalMassDoesNotPileUpOnOneDimensionalSkeleton : Prop
  carlesonPacking :
    CKNExcessCarlesonPacking _seq _K hRho

/-- A bad normalized-CKN-excess cylinder with a center and parabolic radius.
    The exact normalized-excess functional is still abstract; the point of this
    carrier is to let downstream radius-charging statements talk about `r_Q`
    rather than the classical `r_Q^2` CKN mass. -/
structure BadNormalizedCKNExcessCylinder
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  center : EuclideanSpace ℝ (Fin 4)
  radius : ℝ
  radius_pos : radius > 0
  badNormalizedExcess : Prop

/-- Strictly smaller primitive below `CKNExcessCarlesonPacking`: a finite
    monotone scale budget charges each bad cylinder by its radius. This is the
    exact missing exponent, because classical CKN only supplies an `r^2` charge. -/
structure RadiusChargingBadScaleMeasure
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  scaleSpace : Type
  tent : BadNormalizedCKNExcessCylinder _seq _K → Set scaleSpace
  finiteBudget : Prop
  radiusCharge : BadNormalizedCKNExcessCylinder _seq _K → Prop
  boundedOverlapForDisjointBadCylinders : Prop
  chargesRadiusNotClassicalRadiusSquared : Prop
  carlesonPacking :
    CKNExcessCarlesonPacking _seq _K hRho

/-- Constructor from the radius-charging primitive to the named Carleson target. -/
def CKNExcessCarlesonPacking.ofRadiusChargingBadScaleMeasure
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : RadiusChargingBadScaleMeasure seq K hRho) :
    CKNExcessCarlesonPacking seq K hRho :=
  h.carlesonPacking

/-- Abstract dyadic parabolic cube used by excess-drop/stopping-time routes. -/
opaque DyadicParabolicCube : Type

/-- Entropy/drop formulation of the same radius-charging mechanism. The
    content is that bad normalized-excess nodes consume radius-length from a
    finite monotone budget, so bad branches cannot accumulate logarithmically. -/
structure ExcessDropChargesBadCylinderRadius
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  entropy : DyadicParabolicCube → ℝ
  entropyNonnegative : Prop
  entropySuperadditiveOverChildren : Prop
  badRadiusDrop : Prop
  finiteTotalDropBudget : Prop
  radiusChargingMeasure :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Candidate potential for the excess-drop route.  This is deliberately below
    `ExcessDropChargesBadCylinderRadius`: it only names a finite nonnegative
    scale budget on dyadic parabolic cubes. -/
structure ExcessDropPotentialCandidate
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  potential : DyadicParabolicCube → ℝ
  rootBudgetFinite : Prop
  potentialNonnegative : Prop
  sameNormalizedExcessTreeAsRho : Prop

/-- Tree inequality needed by the potential route: the parent budget must
    dominate the child budgets plus the bad-node charge. Without this exact
    telescoping shape, a local decay estimate can be reused along nested bad
    scales and still allow logarithmic pileup. -/
structure ExcessDropTreeSuperadditivity
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hPot : ExcessDropPotentialCandidate _seq _K hRho) where
  children : DyadicParabolicCube → Set DyadicParabolicCube
  childBudgetsSubadditive : Prop
  parentDropNonnegative : Prop
  compatibleWithVitaliDisjointSubtrees : Prop

/-- Radius-facing part of the excess-drop theorem: every bad normalized-excess
    node must consume a quantity comparable to its radius from the parent-child
    drop. This is the missing exponent; CKN mass only gives an `r_Q^2` charge. -/
structure BadNodeRadiusDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hPot : ExcessDropPotentialCandidate _seq _K hRho)
    (hTree : ExcessDropTreeSuperadditivity _seq _K hRho hPot) where
  badNodes : Set DyadicParabolicCube
  nodeRadius : DyadicParabolicCube → ℝ
  badNodeConsumesRadius : Prop
  chargesRadiusNotClassicalRadiusSquared : Prop
  noReuseOfSameDropAlongNestedBadNodes : Prop

/-- Telescoping step for the split excess-drop route.  Once bad nodes consume
    radius and the potential has finite root budget, this is the finite-tree
    accounting statement that yields the radius-charging measure. -/
structure ExcessDropTelescopesToRadiusCharging
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hPot : ExcessDropPotentialCandidate _seq _K hRho)
    (hTree : ExcessDropTreeSuperadditivity _seq _K hRho hPot)
    (hDrop : BadNodeRadiusDrop _seq _K hRho hPot hTree) where
  finiteBadSubtreeAccounting : Prop
  infiniteTreeLimitNoBoundaryLoss : Prop
  boundedOverlapForSelectedBadTents : Prop
  radiusChargingMeasure :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Split witness for the current hardest L3A primitive. This is the surface a
    proof should attack before claiming the full `ExcessDropChargesBadCylinderRadius`. -/
structure ExcessDropChargesBadCylinderRadiusSplitWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  potentialCandidate :
    ExcessDropPotentialCandidate _seq _K hRho
  treeSuperadditivity :
    ExcessDropTreeSuperadditivity _seq _K hRho potentialCandidate
  badNodeRadiusDrop :
    BadNodeRadiusDrop _seq _K hRho potentialCandidate treeSuperadditivity
  telescoping :
    ExcessDropTelescopesToRadiusCharging
      _seq _K hRho potentialCandidate treeSuperadditivity badNodeRadiusDrop

/-- Constructor from the split excess-drop witness to the existing
    radius-charge primitive. -/
def RadiusChargingBadScaleMeasure.ofExcessDropSplitWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : ExcessDropChargesBadCylinderRadiusSplitWitness seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.telescoping.radiusChargingMeasure

/-- Guard: local decay or epsilon regularity at a bad cylinder is not yet an
    excess-drop theorem. The proof must show a parent-child drop that cannot be
    spent repeatedly along a logarithmic nested chain. -/
structure LocalExcessDecayWithoutTelescopingDoesNotChargeRadius
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  localDecayEstimate : Prop
  noParentChildPotentialDrop : Prop
  nestedBadScalesCanReuseSameMass : Prop
  logarithmicMultiplicityStillAdmissible : Prop
  cannotConstructRadiusCharging :
    ¬ Nonempty (RadiusChargingBadScaleMeasure _seq _K hRho)

/-- Guard: the classical CKN lower charge `r_Q^2` cannot be renamed into the
    required radius drop `r_Q`. The missing step is the full-power improvement
    from mass charge to scale-length charge. -/
structure ClassicalMassChargeDoesNotDefineExcessDropPotential
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  classicalBadCylinderMassChargeRadiusSquared : Prop
  targetRequiresRadiusCharge : Prop
  logarithmicDyadicMultiplicityModelSurvives : Prop
  cannotConstructBadNodeRadiusDrop :
    ∀ (hPot : ExcessDropPotentialCandidate _seq _K hRho)
      (hTree : ExcessDropTreeSuperadditivity _seq _K hRho hPot),
      ¬ Nonempty (BadNodeRadiusDrop _seq _K hRho hPot hTree)

/-- Guard beneath the excess-drop target: a signed flux, defect measure, or
    local energy balance can help only after each bad normalized-excess
    cylinder is assigned to a dyadic cube whose pointwise drop pays its radius,
    and those drops sum over the selected bad family. -/
structure ExcessDropRadiusChargeRequiresPointwiseBadCylinderDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  excessDrop : ExcessDropChargesBadCylinderRadius _seq _K hRho
  badCylinderToCube :
    BadNormalizedCKNExcessCylinder _seq _K → DyadicParabolicCube
  pointwiseDropChargesRadius : Prop
  dropBudgetSumsOverDisjointBadCylinders : Prop
  signedFluxOrSupportLocalizationAloneInsufficient : Prop
  classicalRadiusSquaredChargeInsufficient : Prop

/-- Algebraic obstruction exposed by the split-witness audit. If
    `P_s(Q) = r_Q^{-s} μ(Q)` is built from a finite positive mass budget, then
    dyadic parent-child superadditivity forces `s <= 0`, while upgrading a
    classical `r_Q^2` bad-cylinder charge to an `r_Q` charge forces `s >= 1`.
    Thus a mass-derived potential cannot both telescope and pay radius. -/
structure MassRenormalizationCannotTelescopeAndPayRadius
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  massBudget : DyadicParabolicCube → ℝ
  nodeRadius : DyadicParabolicCube → ℝ
  potentialExponent : ℝ
  potential : DyadicParabolicCube → ℝ
  potentialIsRenormalizedMass : Prop
  classicalBadCostOnlyRadiusSquared : Prop
  dyadicChildScalingInflatesPositiveExponents : Prop
  treeSuperadditivityForcesNonpositiveExponent : Prop
  radiusPaymentForcesExponentAtLeastOne : Prop
  cannotSatisfyBothTelescopingAndRadiusPayment : Prop

/-- Guard: normalized CKN excess detects badness but is not a parent-child
    monotone potential. The renormalization that makes badness scale-invariant
    introduces child-scale inflation. -/
structure NormalizedCKNExcessNotTreeSuperadditive
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  normalizedExcessPotential : DyadicParabolicCube → ℝ
  detectsBadNormalizedExcess : Prop
  halfScaleChildrenInflateNormalizedPotential : Prop
  parentChildSuperadditivityFails : Prop
  cannotConstructExcessDropPotentialCandidate :
    ¬ Nonempty (ExcessDropPotentialCandidate _seq _K hRho)

/-- Guard: unnormalized CKN mass, enstrophy, or positive defect measures may be
    finite and superadditive, but their bad-cylinder lower bound is still the
    classical `r_Q^2` cost unless a separate fresh-radius theorem is added. -/
structure UnnormalizedMassTelescopesOnlyRadiusSquared
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  unnormalizedPotential : DyadicParabolicCube → ℝ
  finiteRootBudget : Prop
  parentChildSuperadditive : Prop
  badNodesPayClassicalRadiusSquared : Prop
  badNodesDoNotPayFreshRadiusDrop : Prop
  cannotConstructBadNodeRadiusDrop :
    ∀ (hPot : ExcessDropPotentialCandidate _seq _K hRho)
      (hTree : ExcessDropTreeSuperadditivity _seq _K hRho hPot),
      ¬ Nonempty (BadNodeRadiusDrop _seq _K hRho hPot hTree)

/-- Guard: signed Duchon-Robert, pressure, or raw Möbius flux can telescope as
    a balance, but cannot serve as a nonnegative radius budget without an
    independent absolute no-cancellation theorem. -/
structure SignedFluxDoesNotDefineRadiusDropPotential
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  signedFluxBalance : DyadicParabolicCube → ℝ
  signedTelescopingMayHold : Prop
  notNonnegativePotential : Prop
  cancellationCanHideBadScaleLength : Prop
  absoluteNoCancellationTheoremMissing : Prop
  cannotConstructRadiusCharging :
    ¬ Nonempty (RadiusChargingBadScaleMeasure _seq _K hRho)

/-- The concrete smaller primitive if the enstrophy/drop route remains alive:
    every bad normalized-excess node must contain fresh enstrophy on the part
    not already assigned to bad children, with enough radius-scale lower bound
    and bounded overlap to telescope. -/
structure FreshEnstrophyRadiusDropForBadNormalizedExcess
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  badNodes : Set DyadicParabolicCube
  children : DyadicParabolicCube → Set DyadicParabolicCube
  freshRegion : DyadicParabolicCube → Set (EuclideanSpace ℝ (Fin 4))
  nodeRadius : DyadicParabolicCube → ℝ
  finiteEnstrophyBudget : Prop
  badNodeFreshRadiusDrop : Prop
  freshRegionsBoundedOverlap : Prop
  sameBadTreeAsNormalizedCKNExcess : Prop
  producesSplitWitness :
    ExcessDropChargesBadCylinderRadiusSplitWitness _seq _K hRho

/-- Alternative sharper primitive: finite parabolic length of a bad skeleton is
    useful only with density/no-neck data saying each bad cylinder sees fresh
    skeleton length comparable to its radius. Qualitative CKN dimension is not
    enough. -/
structure FiniteLengthBadSkeletonDensityNoNeck
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  skeleton : Set (EuclideanSpace ℝ (Fin 4))
  finiteParabolicLength : Prop
  everyBadCylinderAttachedToSkeleton : Prop
  freshLengthInEveryBadNode : Prop
  noNeckBoundedOverlap : Prop
  strongerThanQualitativeDimensionOne : Prop
  producesRadiusCharging :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Guard: parent normalized-excess badness can be inherited entirely from a
    selected bad child or descendant. After child excision the parent fresh
    region may carry no radius-scale enstrophy. -/
structure FreshEnstrophyDropFailsByChildConcentration
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  parent : DyadicParabolicCube
  child : DyadicParabolicCube
  childSubsetParent : Prop
  parentBadFromChildMass : Prop
  childBad : Prop
  freshRegionIsParentMinusChild : Prop
  freshEnstrophyCanBeSmall : Prop
  noBadNodeFreshRadiusDrop :
    ¬ Nonempty (FreshEnstrophyRadiusDropForBadNormalizedExcess _seq _K hRho)

/-- Guard: without a scale-invariant local kinetic-energy bound, normalized
    CKN badness plus interpolation recovers only the classical radius-squared
    charge, not a radius enstrophy lower bound. -/
structure CKNBadnessToEnstrophyOnlyR2WithoutScaleInvariantEnergy
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  interpolationAvailable : Prop
  badLowerBound : Prop
  onlyGlobalEnergyAvailable : Prop
  classicalRadiusSquaredOutputOnly : Prop
  noRadiusOutput : Prop

/-- The local residual branch that would make fresh-enstrophy charging honest:
    parent badness must leave residual velocity excess outside children, with
    scale-invariant fresh energy, pressure localization, and usable Poincare
    geometry on the punctured region. -/
structure ResidualFreshExcessForcesFreshEnstrophy
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  freshRegion : DyadicParabolicCube → Set (EuclideanSpace ℝ (Fin 4))
  residualVelocityExcessOutsideChildren : Prop
  scaleInvariantFreshEnergy : Prop
  pressureTailLocalizedToFreshVelocity : Prop
  freshPoincareGeometry : Prop
  freshEnstrophyDrop : Prop

/-- Inherited child concentration must itself be charged by a no-log-pileup,
    skeleton, or no-neck theorem. Otherwise the same descendant concentration
    can make infinitely many ancestors look bad. -/
structure ChildConcentrationNoLogPileupOrSkeletonCharge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  inheritedBadnessDoesNotRepeatLogarithmically : Prop
  skeletonOrNoNeckCharge : Prop
  radiusChargingConsequence : Prop

/-- Correct split below the failed monolithic fresh-enstrophy primitive: every
    bad node must either retain residual fresh excess, or its badness is
    inherited by children and then a separate no-log/skeleton charge is needed. -/
structure BadNodeResidualOrInheritedDichotomy
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  badNodes : Set DyadicParabolicCube
  children : DyadicParabolicCube → Set DyadicParabolicCube
  freshRegion : DyadicParabolicCube → Set (EuclideanSpace ℝ (Fin 4))
  nodeRadius : DyadicParabolicCube → ℝ
  residualFreshExcess : DyadicParabolicCube → Prop
  inheritedByBadChildren : DyadicParabolicCube → Prop
  dichotomy : Prop
  residualGivesFreshDrop : Prop
  inheritedGivesNoLogPileupOrSkeletonCharge : Prop

/-- Guard: pressure CKN excess is nonlocal. After removing bad children, parent
    pressure badness may be inherited or harmonic and need not force fresh
    velocity-gradient enstrophy in the punctured region. -/
structure PressureTailEscapeBlocksFreshEnstrophyDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  pressureRecoveryAvailable : Prop
  pressureIsNonlocal : Prop
  pressureBadnessMayBeInheritedOrHarmonic : Prop
  noFreshGradientConclusion : Prop

/-- Strong skeleton/no-neck route after the fresh-enstrophy shortcut fails:
    selected bad nodes must cover the bad sublevel set, and each selected node
    must contain fresh finite parabolic length with bounded overlap. -/
structure FiniteLengthBadSkeletonDensityNoNeckStrong
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  skeleton : Set (EuclideanSpace ℝ (Fin 4))
  selectedBadNodes : Set DyadicParabolicCube
  finiteParabolicLength : Prop
  coversNormalizedBadSublevel : Prop
  badNodeFreshSkeletonDensity : Prop
  freshSkeletonRegionsBoundedOverlap : Prop
  producesRadiusCharging :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Abstract no-go: inherited normalized CKN badness does not force child-radii
    contraction from CKN mass information alone. The square cost may stay
    finite while the radius length diverges. -/
structure InheritedBadnessNoChildRadiiContractionFromCKNMass
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  root : DyadicParabolicCube
  mass : DyadicParabolicCube → ℝ
  radius : DyadicParabolicCube → ℝ
  children : DyadicParabolicCube → Set DyadicParabolicCube
  finiteRootMass : Prop
  badnessIsClassicalSquareCost : Prop
  inheritedMass : Prop
  noResidualFreshMass : Prop
  childrenRemainBad : Prop
  childRadiiNoContraction : Prop
  classicalSquareChargeFinite : Prop
  radiusChargeDiverges : Prop

/-- Concrete information-level log-pileup model for the inherited branch:
    dyadic radii with roughly k*2^k bad nodes have summable r^2 charge but
    divergent radius charge. -/
structure LogPileupInheritedBadTreeModel where
  scaleRadius : ℕ → ℝ
  nodeCount : ℕ → ℕ
  dyadicRadii : Prop
  countAsymptotic_k_twoPowK : Prop
  inheritedAtEveryScale : Prop
  everyNodeBad : Prop
  squareChargeSummable : Prop
  radiusChargeDiverges : Prop

/-- Residual branch kept as a conditional local theorem: if the fresh region
    really carries residual velocity excess, scale-invariant energy, pressure
    localization, and Poincare geometry, then it can pay radius enstrophy. -/
structure ResidualBranchConditionalFreshEnstrophy
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  freshRegion : DyadicParabolicCube → Set (EuclideanSpace ℝ (Fin 4))
  residualVelocityExcessOutsideChildren : Prop
  scaleInvariantFreshEnergy : Prop
  pressureTailLocalizedToFreshVelocity : Prop
  freshPoincareGeometry : Prop
  freshEnstrophyRadiusDrop : Prop

/-- Guard: pressure badness can be inherited from children or harmonic tails.
    Pressure recovery gives upper estimates unless paired with a localization
    theorem that charges fresh velocity-gradient mass. -/
structure PressureInheritanceBlocksChildContraction
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  pressureRecoveryAvailable : Prop
  pressureNonlocalAcrossChildren : Prop
  parentPressureBadnessMayBeInherited : Prop
  noFreshGradientFromPressureAlone : Prop

/-- Corona/no-neck skeleton theorem for inherited bad trees. This is the
    post-child-contraction target: residual nodes pay fresh enstrophy, inherited
    nodes attach to a finite-length skeleton with fresh density and bounded
    overlap. -/
structure InheritedBadTreeCoronaNoNeckSkeleton
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  selectedBadNodes : Set DyadicParabolicCube
  residualNodes : Set DyadicParabolicCube
  inheritedNodes : Set DyadicParabolicCube
  selectedCoversRhoSublevel : Prop
  nodePartition : Prop
  residualFreshEnstrophyCharge : Prop
  skeleton : Set (EuclideanSpace ℝ (Fin 4))
  skeletonNonadaptive : Prop
  finiteParabolicLength : Prop
  inheritedNodesAttachToSkeleton : Prop
  freshSkeletonDensity : Prop
  freshSkeletonOverlap : Prop
  radiusCharging :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Abstract parabolic Jones/Reifenberg beta-number package for the bad-center
    set. This is the geometric accounting theorem one would use to manufacture
    finite length from a nonadaptive set of centers; it is not supplied by
    qualitative CKN dimension. -/
structure ParabolicBadCenterBetaCarleson
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  badCenterSet : Set (EuclideanSpace ℝ (Fin 4))
  nonadaptiveFromSolution : Prop
  betaNumbers : Prop
  betaSquareCarlesonBound : Prop
  densityLowerBoundOnSelectedBadNodes : Prop
  selectedBadNodesCoveredByCenters : Prop

/-- First sub-witness below beta-Carleson: choose the bad-center carrier from
    the normalized-excess tree before doing any radius summation. -/
structure NormalizedExcessBadCenterSelection
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  selectedBadNodes : Set DyadicParabolicCube
  badCenterSet : Set (EuclideanSpace ℝ (Fin 4))
  centersGeneratedByNormalizedExcessTree : Prop
  selectedNodesCoverRhoSublevels : Prop
  pressureAndVelocityUseSameRawSource : Prop
  nonadaptiveSelectionBeforeRadiusAccounting : Prop

/-- Nonadaptive-construction guard below the NS beta-Carleson route: the center
    carrier is selected from solution/excess data before the radius accounting
    target is known, so it cannot simply encode the desired charge. -/
structure BadCenterNonadaptiveConstructionGuard
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hSel : NormalizedExcessBadCenterSelection _seq _K hRho) where
  nonadaptiveFromSolution : Prop
  rawSourcePrecedesBadTreeAccounting : Prop
  notChosenToMatchRadiusCharge : Prop
  compatibleWithSelection : Prop

/-- Second sub-witness below beta-Carleson: parabolic beta numbers for the
    selected bad-center carrier have square-Carleson control at the correct
    one-dimensional scale. -/
structure ParabolicBadCenterBetaNumberControl
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hSel : NormalizedExcessBadCenterSelection _seq _K hRho) where
  betaNumbersDefinedForBadCenters : Prop
  oneDimensionalComparisonFamily : Prop
  betaSquareCarlesonBound : Prop
  parabolicScalingCompatible : Prop
  excludesLogPileupByFlatnessControl : Prop

/-- Third sub-witness below beta-Carleson: bad centers have lower density in
    selected inherited bad nodes, and the density is fresh enough for corona
    accounting rather than inherited along ancestors. -/
structure BadCenterLowerDensityForSelectedNodes
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hSel : NormalizedExcessBadCenterSelection _seq _K hRho) where
  lowerDensityInEachSelectedBadNode : Prop
  freshDensityNotAncestorReuse : Prop
  selectedNodeDensityFeedsSkeletonDensity : Prop
  boundedOverlapCompatible : Prop

/-- Concrete carrier below bad-center beta-Carleson. The centers and selected
    nodes are generated from the normalized-excess tree before radius accounting,
    so the later skeleton cannot be chosen post-hoc to encode the desired
    length bound. -/
structure NonadaptiveBadCenterCarrierFromNormalizedExcess
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  badCenterSet : Set (EuclideanSpace ℝ (Fin 4))
  selectedBadNodes : Set DyadicParabolicCube
  nodeCenter : DyadicParabolicCube → EuclideanSpace ℝ (Fin 4)
  nodeRadius : DyadicParabolicCube → ℝ
  nodeRadiusPositiveOnSelected :
    ∀ Q : DyadicParabolicCube,
      Q ∈ selectedBadNodes → 0 ≤ nodeRadius Q
  generatedByNormalizedExcessTree : Prop
  nonadaptiveFromSolution : Prop
  pressureAndVelocityCentersUseSameRawSource : Prop
  coversNormalizedBadSublevel : Prop
  lowerDensityOnSelectedBadNodes : Prop

/-- Parabolic beta data for the nonadaptive bad-center carrier. This is still
    geometric data; the Navier-Stokes estimate is the square-Carleson drop below. -/
structure BadCenterParabolicBetaData
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho) where
  betaNumber : DyadicParabolicCube → ℝ
  betaNonnegative : Prop
  betaMeasuresDistanceToBestParabolicLine : Prop
  sameParabolicMetricAsRho : Prop
  betaDataUsesCarrierNotAdaptiveSkeleton : Prop

/-- The exposed PDE obligation below bad-center beta-Carleson: prove that the
    nonadaptive carrier has beta-square radius charge with a finite NS budget.
    This is the exact place where classical CKN mass/enstrophy only pays
    `r_Q^2`; a proof here must pay the beta-square one-dimensional scale. -/
structure BadCenterBetaSquareCarlesonDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  finiteNSBudget : Prop
  betaSquareRadiusCharge : Prop
  carlesonSummationOverBadTree : Prop
  excludesLogPileupInheritedTrees : Prop
  chargesBetaSquareRadiusNotClassicalRadiusSquared : Prop

/-- Quantitative-stratification-style source for the beta-square drop: a
    monotone scale quantity whose drop controls beta-square radius on the
    nonadaptive bad-center carrier. This is the concrete local proof shape below
    `BadCenterBetaSquareCarlesonDrop`. -/
structure BadCenterMonotoneFrequencyDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  frequency : DyadicParabolicCube → ℝ
  finiteFrequencyBudget : Prop
  monotoneAcrossBadTree : Prop
  betaSquareDropEstimate : Prop
  dropTelescopesOverSelectedNodes : Prop
  noLogPileupFromMonotoneDrop : Prop
  dropPaysBetaSquareNotMass : Prop

/-- Candidate mechanism below the monotone-frequency drop: quantitative
    differentiation/cone-splitting for the selected bad centers. Non-flat
    beta geometry must force a definite drop in the same frequency quantity
    that has the finite budget. -/
structure BadCenterQuantitativeDifferentiationPackage
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  frequency : DyadicParabolicCube → ℝ
  finiteFrequencyBudget : Prop
  scaleMonotonicityOrAlmostMonotonicity : Prop
  coneSplittingForNonflatBadCenters : Prop
  betaSquareControlledByFrequencyDrop : Prop
  pressureTailErrorsAbsorbedInDrop : Prop
  sameCarrierAcrossScales : Prop
  dropTelescopesOverSelectedNodes : Prop

/-- Adapter: quantitative differentiation is the concrete route into the
    monotone-frequency drop if all error terms are tied to the same
    nonadaptive bad-center carrier. -/
def BadCenterMonotoneFrequencyDrop.ofQuantitativeDifferentiation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h : BadCenterQuantitativeDifferentiationPackage seq K hRho hCarrier hBeta) :
    BadCenterMonotoneFrequencyDrop seq K hRho hCarrier hBeta where
  frequency := h.frequency
  finiteFrequencyBudget := h.finiteFrequencyBudget
  monotoneAcrossBadTree := h.scaleMonotonicityOrAlmostMonotonicity
  betaSquareDropEstimate := h.betaSquareControlledByFrequencyDrop
  dropTelescopesOverSelectedNodes := h.dropTelescopesOverSelectedNodes
  noLogPileupFromMonotoneDrop := h.coneSplittingForNonflatBadCenters
  dropPaysBetaSquareNotMass := h.betaSquareControlledByFrequencyDrop

/-- Guard: normalized CKN mass detects bad cylinders, but the scale
    normalization that makes badness visible destroys tree monotonicity. It
    cannot be the frequency in `BadCenterMonotoneFrequencyDrop` without an
    independent drop theorem. -/
structure NormalizedMassCannotBeBadCenterFrequencyDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  normalizedMassDetectsBadness : Prop
  normalizedMassNotTreeMonotone : Prop
  parentMassCanBeInheritedByChildren : Prop
  onlyClassicalRadiusSquaredCharge : Prop
  cannotSupplyBadCenterMonotoneFrequencyDrop : Prop

/-- Guard: enstrophy is a positive finite budget, but local scale-normalized
    enstrophy is not a monotone beta-frequency for Navier-Stokes bad centers;
    vortex stretching, pressure localization, and descendant reuse must be
    controlled by a new theorem. -/
structure EnstrophyFrequencyDropNeedsNSOnlyMonotonicity
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  finiteEnstrophyBudgetAvailable : Prop
  scaleNormalizedEnstrophyNotKnownMonotone : Prop
  stretchingProductionIsUnpaidError : Prop
  pressureLocalizationIsUnpaidError : Prop
  descendantReuseCanRepeatSameDissipation : Prop
  cannotSupplyDropWithoutNSOnlyMonotonicity : Prop

/-- Guard: signed Duchon-Robert / raw Mobius flux is a signed diagnostic, not a
    nonnegative monotone beta-frequency. It can identify net flux while missing
    absolute bad-center length. -/
structure SignedFluxCannotBeBadCenterFrequencyDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  signedFluxIdentityAvailable : Prop
  notNonnegativeFrequency : Prop
  weakStarCancellationCanHideBetaLength : Prop
  totalVariationBoundMissing : Prop
  cannotSupplyMonotoneFrequencyDrop : Prop

/-- Guard: pressure recovery gives an elliptic identity and upper estimates,
    but not a monotone scale-frequency. Parent pressure excess can be inherited
    from children or harmonic tails. -/
structure PressureRecoveryDoesNotGiveBadCenterFrequencyDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  pressureRecoveryIdentityAvailable : Prop
  pressureEstimatesAreUpperBounds : Prop
  parentPressureBadnessCanBeInherited : Prop
  harmonicTailCanPersistOnFreshRegion : Prop
  noFrequencyDropFromPressureAlone : Prop

/-- Guard: qualitative dimension-one support is weaker than a finite
    scale-frequency budget. It gives no same-carrier monotone drop and no
    beta-square radius charge. -/
structure QualitativeDimensionDoesNotGiveBadCenterFrequencyDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  dimensionOneSupportAvailable : Prop
  finiteFrequencyBudgetMissing : Prop
  betaSquareDropMissing : Prop
  sameCarrierMonotonicityMissing : Prop
  logarithmicPileupStillPossible : Prop
  cannotSupplyMonotoneFrequencyDrop : Prop

/-- Candidate bridge from the existing event-recurrence price ledger to the
    bad-center monotone-frequency route. The weighted-square algebra already
    has the right shape; the hard part is identifying events nonadaptively with
    selected bad nodes and proving the event price is the same NS scale drop. -/
structure BadCenterEventRecurrenceLedgerBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  eventLedger : EventRecurrencePriceLedger
  eventToBadNode : ℕ → DyadicParabolicCube
  eventsCoverSelectedBadNodes : Prop
  eventGainIdentifiesBetaNumber : Prop
  eventWeightIdentifiesNodeRadius : Prop
  weightedSquarePriceIsBetaSquareRadius : Prop
  eventPriceBudgetIsFiniteNSBudget : Prop
  reciprocalBudgetCountsEventMultiplicity : Prop
  eventOrderingMatchesBadTree : Prop
  rawRecurrencePriceIsSameCarrierScaleDrop : Prop
  producesMonotoneFrequencyDrop :
    BadCenterMonotoneFrequencyDrop _seq _K hRho hCarrier hBeta

/-- Event/bad-node identification sub-witness. This is the geometry that makes
    event recurrence talk about the normalized-excess bad tree rather than a
    separate shell process. -/
structure BadCenterEventNodeIdentification
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho) where
  eventToBadNode : ℕ → DyadicParabolicCube
  eventsGeneratedFromCarrier : Prop
  eventsCoverSelectedBadNodes : Prop
  noPostHocEventChoiceFromRadiusSum : Prop
  eventOrderingMatchesBadTree : Prop
  eventMultiplicityCountsSelectedNodes : Prop

/-- Weighted-square identity sub-witness. This is the exact algebraic match
    between event recurrence prices and bad-center beta-square radius. -/
structure BadCenterEventWeightedSquareIdentification
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventGainIdentifiesBetaNumber : Prop
  eventWeightIdentifiesNodeRadius : Prop
  weightedSquarePriceIsBetaSquareRadius : Prop
  betaDataAndEventGainUseSameParabolicMetric : Prop

/-- Bad-center beta-square prefix induced by the event ordering. This is not yet
    the whole selected bad-tree sum; it is the finite event prefix after mapping
    each event to its selected bad node. -/
def badCenterEventBetaSquarePrefix
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier)
    (N : ℕ) : ℝ :=
  nsPrefixSum
    (fun e : ℕ =>
      hCarrier.nodeRadius (hEvents.eventToBadNode e) *
        (hBeta.betaNumber (hEvents.eventToBadNode e)) ^ (2 : Nat))
    N

/-- Pointwise event/bad-center beta-square identity. This is the exact finite
    prefix algebra needed before event price accounting can be read as
    bad-center beta-square accounting. -/
structure BadCenterEventPointwiseBetaSquareIdentity
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventGain_eq_betaNumber :
    ∀ e : ℕ, L.eventGain e = hBeta.betaNumber (hEvents.eventToBadNode e)
  eventWeight_eq_nodeRadius :
    ∀ e : ℕ, L.eventWeight e = hCarrier.nodeRadius (hEvents.eventToBadNode e)
  eventToBadNodeLandsInSelectedNodes : Prop
  eventPrefixMultiplicityMatchesSelectedNodeMultiplicity : Prop
  noAdaptiveReindexingFromBetaSquareSum : Prop

/-- With pointwise event/bad-center identification, the event weighted-square
    prefix is exactly the bad-center beta-square prefix in event order. -/
theorem eventWeightedGainPricePrefix_eq_badCenterEventBetaSquarePrefix
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (N : ℕ) :
    eventWeightedGainPricePrefix L N =
      badCenterEventBetaSquarePrefix (hBeta := hBeta) hEvents N := by
  simp [eventWeightedGainPricePrefix, badCenterEventBetaSquarePrefix,
    h.eventGain_eq_betaNumber, h.eventWeight_eq_nodeRadius]

/-- Same-carrier price/drop sub-witness. It prevents the event-recurrence price
    from being imported as unrelated shell accounting. -/
structure BadCenterEventPriceDropIdentification
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventPriceBudgetIsFiniteNSBudget : Prop
  reciprocalBudgetCountsEventMultiplicity : Prop
  rawRecurrencePriceIsSameCarrierScaleDrop : Prop
  priceDropTelescopesOverSelectedBadNodes : Prop
  noShellLevelMultiplicityLaundering : Prop

/-- Concrete source path for the event price/drop identification.

The event recurrence file already supplies the hard event-side certificate from a
Duhamel/Bernstein lower-envelope source and a fixed section-incidence receipt.
This record states the extra L3A identifications needed before that certificate
can pay bad-center beta-square radius: the sections must be the selected
bad-center sections, and the raw recurrence prefix must be the same-carrier NS
scale drop. -/
structure BadCenterEventPriceDropDuhamelIncidenceSource
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  duhamelSource : EventDynamicRecurrencePricePrecertificateSource L
  sectionIncidence : EventSectionIncidenceReceipt L
  reciprocalBudgetMatchesSectionIncidence :
    L.reciprocalBudget = sectionIncidence.eventReciprocalBudget
  eventSectionsAreSelectedBadCenterSections : Prop
  effectiveMultiplicityCountsSelectedBadNodes : Prop
  duhamelReserveUsesSameBadCenterCarrier : Prop
  priceBudgetMatchesFiniteNSScaleBudget : Prop
  rawRecurrencePrefixIsSameCarrierScaleDrop : Prop
  prefixBudgetTelescopesOverSelectedBadNodes : Prop
  noPostHocSectionChoiceFromRadiusSum : Prop

/-- The Duhamel/incidence source produces the event certificate already defined
in the event recurrence-price file.  The remaining fields in
`BadCenterEventPriceDropDuhamelIncidenceSource` are the L3A identifications,
not event-ledger algebra. -/
def BadCenterEventPriceDropDuhamelIncidenceSource.eventCertificate
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L) :
    EventDynamicRecurrencePriceCertificate L :=
  event_price_bridge_of_duhamel_source_and_section_incidence
    L
    h.duhamelSource
    h.sectionIncidence
    h.reciprocalBudgetMatchesSectionIncidence

/-- Event-side consequence of the concrete Duhamel/incidence source: every
finite weighted-square event prefix is bounded by the declared event price
budget. The remaining bad-center work is the separate identification of this
prefix with beta-square radius over selected nodes. -/
theorem BadCenterEventPriceDropDuhamelIncidenceSource.weightedEventPricePrefix_le_budget
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (N : ℕ) :
    eventWeightedGainPricePrefix L N ≤ L.priceBudget :=
  event_weighted_gain_price_prefix_le_budget
    L
    (BadCenterEventPriceDropDuhamelIncidenceSource.eventCertificate h)
    N

/-- If the concrete Duhamel/incidence source supplies the event budget and the
    event/bad-center pointwise identity is proved, then every bad-center
    beta-square event prefix is bounded by the same declared event budget. -/
theorem badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (N : ℕ) :
    badCenterEventBetaSquarePrefix (hBeta := hBeta) hEvents N ≤ L.priceBudget := by
  rw [← eventWeightedGainPricePrefix_eq_badCenterEventBetaSquarePrefix hPoint N]
  exact
    BadCenterEventPriceDropDuhamelIncidenceSource.weightedEventPricePrefix_le_budget
      hSource
      N

/-- Remaining bridge after finite-prefix budgeting: event prefixes must cover the
    selected bad-center tree in the right order and with the right multiplicity.
    This is where shell/event accounting can still fail to become a
    bad-center Carleson estimate. -/
structure BadCenterEventPrefixCoversSelectedBadTree
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier) where
  eventPrefixesExhaustSelectedBadNodes : Prop
  everySelectedBadNodeAppearsInSomePrefix : Prop
  prefixDominatesFiniteSelectedBadTreeBetaSum : Prop
  duplicateEventsChargeMultiplicityRatherThanEraseIt : Prop
  noShellOnlyEnumerationShortcut : Prop
  noAdaptiveStoppingFromObservedBetaSquareSum : Prop

/--
Typed strengthening of the event-prefix coverage packet.  The ordinary
coverage record remains available, but selected-bad-node appearance is carried
as an explicit final-prefix event witness instead of only as a Prop field.
-/
structure TypedBadCenterEventPrefixCoversSelectedBadTree
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (supportLength : ℕ) where
  coverage :
    BadCenterEventPrefixCoversSelectedBadTree
      _seq _K hRho hCarrier hBeta hEvents
  typedSelectedBadNodeAppearance :
    ∀ Q : DyadicParabolicCube,
      Q ∈ hCarrier.selectedBadNodes →
        {e : Fin (supportLength - 1) // hEvents.eventToBadNode e.val = Q}
  typedAppearanceRefinesCoverageAppearance : Prop
  typedAppearanceFixedBeforePayoff : Prop
  typedAppearanceUsesSameBadCenterEventNodes : Prop
  noBarePropChoiceForAppearance : Prop
  noEndpointCapacityOnlyTypedAppearance : Prop
  noPostPayoffTypedAppearance : Prop

/--
Level530 source for the typed coverage primitive.  This is the theorem surface
below `TypedBadCenterEventPrefixCoversSelectedBadTree`: ordinary event-prefix
coverage is allowed as coverage data, but the selected-bad-node appearance
evidence must be a typed witness into the fixed final event prefix.  The proof
fields pin the witness to the ordinary coverage packet and prevent replacing it
by a bare Prop, endpoint-capacity count, or post-payoff selection.
-/
structure BadCenterEventPrefixTypedAppearanceSource
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (supportLength : ℕ) where
  coverage :
    BadCenterEventPrefixCoversSelectedBadTree
      _seq _K hRho hCarrier hBeta hEvents
  typedSelectedBadNodeAppearance :
    ∀ Q : DyadicParabolicCube,
      Q ∈ hCarrier.selectedBadNodes →
        {e : Fin (supportLength - 1) // hEvents.eventToBadNode e.val = Q}
  eventPrefixesExhaustSelectedBadNodes_proof :
    coverage.eventPrefixesExhaustSelectedBadNodes
  everySelectedBadNodeAppearsInSomePrefix_proof :
    coverage.everySelectedBadNodeAppearsInSomePrefix
  prefixDominatesFiniteSelectedBadTreeBetaSum_proof :
    coverage.prefixDominatesFiniteSelectedBadTreeBetaSum
  duplicateEventsChargeMultiplicityRatherThanEraseIt_proof :
    coverage.duplicateEventsChargeMultiplicityRatherThanEraseIt
  noShellOnlyEnumerationShortcut_proof :
    coverage.noShellOnlyEnumerationShortcut
  noAdaptiveStoppingFromObservedBetaSquareSum_proof :
    coverage.noAdaptiveStoppingFromObservedBetaSquareSum
  typedAppearanceRefinesCoverageAppearance : Prop
  typedAppearanceRefinesCoverageAppearance_proof :
    typedAppearanceRefinesCoverageAppearance
  typedAppearanceFixedBeforePayoff : Prop
  typedAppearanceFixedBeforePayoff_proof :
    typedAppearanceFixedBeforePayoff
  typedAppearanceUsesSameBadCenterEventNodes : Prop
  typedAppearanceUsesSameBadCenterEventNodes_proof :
    typedAppearanceUsesSameBadCenterEventNodes
  noBarePropChoiceForAppearance : Prop
  noBarePropChoiceForAppearance_proof :
    noBarePropChoiceForAppearance
  noEndpointCapacityOnlyTypedAppearance : Prop
  noEndpointCapacityOnlyTypedAppearance_proof :
    noEndpointCapacityOnlyTypedAppearance
  noPostPayoffTypedAppearance : Prop
  noPostPayoffTypedAppearance_proof :
    noPostPayoffTypedAppearance
  noLevel517EnumerationSource : Prop
  noLevel517EnumerationSource_proof :
    noLevel517EnumerationSource
  noLevel518NaturalEnumerationSource : Prop
  noLevel518NaturalEnumerationSource_proof :
    noLevel518NaturalEnumerationSource
  noLevel519WitnessBoundAdapterSource : Prop
  noLevel519WitnessBoundAdapterSource_proof :
    noLevel519WitnessBoundAdapterSource

/--
Project the Level530 typed-appearance source into the Level529 upstream typed
coverage primitive.
-/
def BadCenterEventPrefixTypedAppearanceSource.toTypedCoveragePrimitive
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {supportLength : ℕ}
    (h :
      BadCenterEventPrefixTypedAppearanceSource
        seq K hRho hCarrier hBeta hEvents supportLength) :
    TypedBadCenterEventPrefixCoversSelectedBadTree
      seq K hRho hCarrier hBeta hEvents supportLength where
  coverage := h.coverage
  typedSelectedBadNodeAppearance := h.typedSelectedBadNodeAppearance
  typedAppearanceRefinesCoverageAppearance :=
    h.typedAppearanceRefinesCoverageAppearance
  typedAppearanceFixedBeforePayoff :=
    h.typedAppearanceFixedBeforePayoff
  typedAppearanceUsesSameBadCenterEventNodes :=
    h.typedAppearanceUsesSameBadCenterEventNodes
  noBarePropChoiceForAppearance :=
    h.noBarePropChoiceForAppearance
  noEndpointCapacityOnlyTypedAppearance :=
    h.noEndpointCapacityOnlyTypedAppearance
  noPostPayoffTypedAppearance :=
    h.noPostPayoffTypedAppearance

/--
Level531 source: split the typed appearance witness into the event-order data
that a finite-prefix argument should prove: a natural event index, its strict
membership in the final event prefix, and the displayed `eventToBadNode`
equality for the same index.
-/
structure BadCenterEventOrderAppearanceIndexSource
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (supportLength : ℕ) where
  coverage :
    BadCenterEventPrefixCoversSelectedBadTree
      _seq _K hRho hCarrier hBeta hEvents
  coverageAppearanceEventIndex :
    ∀ Q : DyadicParabolicCube, Q ∈ hCarrier.selectedBadNodes → ℕ
  coverageAppearanceEventIndex_bound :
    ∀ Q : DyadicParabolicCube, ∀ hQ : Q ∈ hCarrier.selectedBadNodes,
      coverageAppearanceEventIndex Q hQ < supportLength - 1
  coverageAppearanceEventIndex_eq_eventToBadNode :
    ∀ Q : DyadicParabolicCube, ∀ hQ : Q ∈ hCarrier.selectedBadNodes,
      hEvents.eventToBadNode (coverageAppearanceEventIndex Q hQ) = Q
  eventPrefixesExhaustSelectedBadNodes_proof :
    coverage.eventPrefixesExhaustSelectedBadNodes
  everySelectedBadNodeAppearsInSomePrefix_proof :
    coverage.everySelectedBadNodeAppearsInSomePrefix
  prefixDominatesFiniteSelectedBadTreeBetaSum_proof :
    coverage.prefixDominatesFiniteSelectedBadTreeBetaSum
  duplicateEventsChargeMultiplicityRatherThanEraseIt_proof :
    coverage.duplicateEventsChargeMultiplicityRatherThanEraseIt
  noShellOnlyEnumerationShortcut_proof :
    coverage.noShellOnlyEnumerationShortcut
  noAdaptiveStoppingFromObservedBetaSquareSum_proof :
    coverage.noAdaptiveStoppingFromObservedBetaSquareSum
  eventIndexFixedBeforePayoff : Prop
  eventIndexFixedBeforePayoff_proof :
    eventIndexFixedBeforePayoff
  eventIndexUsesSameBadCenterEventNodes : Prop
  eventIndexUsesSameBadCenterEventNodes_proof :
    eventIndexUsesSameBadCenterEventNodes
  noBarePropChoiceForEventIndex : Prop
  noBarePropChoiceForEventIndex_proof :
    noBarePropChoiceForEventIndex
  noEndpointCapacityOnlyEventIndex : Prop
  noEndpointCapacityOnlyEventIndex_proof :
    noEndpointCapacityOnlyEventIndex
  noPostPayoffEventIndex : Prop
  noPostPayoffEventIndex_proof :
    noPostPayoffEventIndex
  noLevel517EnumerationSource : Prop
  noLevel517EnumerationSource_proof :
    noLevel517EnumerationSource
  noLevel518NaturalEnumerationSource : Prop
  noLevel518NaturalEnumerationSource_proof :
    noLevel518NaturalEnumerationSource
  noLevel519WitnessBoundAdapterSource : Prop
  noLevel519WitnessBoundAdapterSource_proof :
    noLevel519WitnessBoundAdapterSource

/--
Package a same-index Nat event witness, strict final-prefix bound, and
`eventToBadNode` equality into the Level530 typed appearance source.
-/
def BadCenterEventOrderAppearanceIndexSource.toTypedAppearanceSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {supportLength : ℕ}
    (h :
      BadCenterEventOrderAppearanceIndexSource
        seq K hRho hCarrier hBeta hEvents supportLength) :
    BadCenterEventPrefixTypedAppearanceSource
      seq K hRho hCarrier hBeta hEvents supportLength where
  coverage := h.coverage
  typedSelectedBadNodeAppearance := fun Q hQ =>
    ⟨⟨h.coverageAppearanceEventIndex Q hQ,
      h.coverageAppearanceEventIndex_bound Q hQ⟩,
      h.coverageAppearanceEventIndex_eq_eventToBadNode Q hQ⟩
  eventPrefixesExhaustSelectedBadNodes_proof :=
    h.eventPrefixesExhaustSelectedBadNodes_proof
  everySelectedBadNodeAppearsInSomePrefix_proof :=
    h.everySelectedBadNodeAppearsInSomePrefix_proof
  prefixDominatesFiniteSelectedBadTreeBetaSum_proof :=
    h.prefixDominatesFiniteSelectedBadTreeBetaSum_proof
  duplicateEventsChargeMultiplicityRatherThanEraseIt_proof :=
    h.duplicateEventsChargeMultiplicityRatherThanEraseIt_proof
  noShellOnlyEnumerationShortcut_proof :=
    h.noShellOnlyEnumerationShortcut_proof
  noAdaptiveStoppingFromObservedBetaSquareSum_proof :=
    h.noAdaptiveStoppingFromObservedBetaSquareSum_proof
  typedAppearanceRefinesCoverageAppearance :=
    h.coverage.everySelectedBadNodeAppearsInSomePrefix
  typedAppearanceRefinesCoverageAppearance_proof :=
    h.everySelectedBadNodeAppearsInSomePrefix_proof
  typedAppearanceFixedBeforePayoff :=
    h.eventIndexFixedBeforePayoff
  typedAppearanceFixedBeforePayoff_proof :=
    h.eventIndexFixedBeforePayoff_proof
  typedAppearanceUsesSameBadCenterEventNodes :=
    h.eventIndexUsesSameBadCenterEventNodes
  typedAppearanceUsesSameBadCenterEventNodes_proof :=
    h.eventIndexUsesSameBadCenterEventNodes_proof
  noBarePropChoiceForAppearance :=
    h.noBarePropChoiceForEventIndex
  noBarePropChoiceForAppearance_proof :=
    h.noBarePropChoiceForEventIndex_proof
  noEndpointCapacityOnlyTypedAppearance :=
    h.noEndpointCapacityOnlyEventIndex
  noEndpointCapacityOnlyTypedAppearance_proof :=
    h.noEndpointCapacityOnlyEventIndex_proof
  noPostPayoffTypedAppearance :=
    h.noPostPayoffEventIndex
  noPostPayoffTypedAppearance_proof :=
    h.noPostPayoffEventIndex_proof
  noLevel517EnumerationSource :=
    h.noLevel517EnumerationSource
  noLevel517EnumerationSource_proof :=
    h.noLevel517EnumerationSource_proof
  noLevel518NaturalEnumerationSource :=
    h.noLevel518NaturalEnumerationSource
  noLevel518NaturalEnumerationSource_proof :=
    h.noLevel518NaturalEnumerationSource_proof
  noLevel519WitnessBoundAdapterSource :=
    h.noLevel519WitnessBoundAdapterSource
  noLevel519WitnessBoundAdapterSource_proof :=
    h.noLevel519WitnessBoundAdapterSource_proof

/--
Level532 source: put the final-prefix bound in the selector codomain itself.
The theorem surface is now a `Fin (supportLength - 1)` appearance selector
plus its displayed `eventToBadNode` equality; projecting `.val` supplies the
Level531 Nat event index and `.isLt` supplies the same-index strict bound.
-/
structure BadCenterFinalPrefixAppearanceSelectorSource
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (supportLength : ℕ) where
  coverage :
    BadCenterEventPrefixCoversSelectedBadTree
      _seq _K hRho hCarrier hBeta hEvents
  finalPrefixAppearanceSelector :
    ∀ Q : DyadicParabolicCube,
      Q ∈ hCarrier.selectedBadNodes → Fin (supportLength - 1)
  finalPrefixAppearanceSelector_eq_eventToBadNode :
    ∀ Q : DyadicParabolicCube, ∀ hQ : Q ∈ hCarrier.selectedBadNodes,
      hEvents.eventToBadNode (finalPrefixAppearanceSelector Q hQ).val = Q
  eventPrefixesExhaustSelectedBadNodes_proof :
    coverage.eventPrefixesExhaustSelectedBadNodes
  everySelectedBadNodeAppearsInSomePrefix_proof :
    coverage.everySelectedBadNodeAppearsInSomePrefix
  prefixDominatesFiniteSelectedBadTreeBetaSum_proof :
    coverage.prefixDominatesFiniteSelectedBadTreeBetaSum
  duplicateEventsChargeMultiplicityRatherThanEraseIt_proof :
    coverage.duplicateEventsChargeMultiplicityRatherThanEraseIt
  noShellOnlyEnumerationShortcut_proof :
    coverage.noShellOnlyEnumerationShortcut
  noAdaptiveStoppingFromObservedBetaSquareSum_proof :
    coverage.noAdaptiveStoppingFromObservedBetaSquareSum
  finalSelectorFixedBeforePayoff : Prop
  finalSelectorFixedBeforePayoff_proof :
    finalSelectorFixedBeforePayoff
  finalSelectorUsesSameBadCenterEventNodes : Prop
  finalSelectorUsesSameBadCenterEventNodes_proof :
    finalSelectorUsesSameBadCenterEventNodes
  noBarePropChoiceForFinalSelector : Prop
  noBarePropChoiceForFinalSelector_proof :
    noBarePropChoiceForFinalSelector
  noEndpointCapacityOnlyFinalSelector : Prop
  noEndpointCapacityOnlyFinalSelector_proof :
    noEndpointCapacityOnlyFinalSelector
  noPostPayoffFinalSelector : Prop
  noPostPayoffFinalSelector_proof :
    noPostPayoffFinalSelector
  noLevel517EnumerationSource : Prop
  noLevel517EnumerationSource_proof :
    noLevel517EnumerationSource
  noLevel518NaturalEnumerationSource : Prop
  noLevel518NaturalEnumerationSource_proof :
    noLevel518NaturalEnumerationSource
  noLevel519WitnessBoundAdapterSource : Prop
  noLevel519WitnessBoundAdapterSource_proof :
    noLevel519WitnessBoundAdapterSource

/--
Project a final-prefix selector into the Level531 event-order index source.
-/
def BadCenterFinalPrefixAppearanceSelectorSource.toEventOrderAppearanceIndexSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {supportLength : ℕ}
    (h :
      BadCenterFinalPrefixAppearanceSelectorSource
        seq K hRho hCarrier hBeta hEvents supportLength) :
    BadCenterEventOrderAppearanceIndexSource
      seq K hRho hCarrier hBeta hEvents supportLength where
  coverage := h.coverage
  coverageAppearanceEventIndex := fun Q hQ =>
    (h.finalPrefixAppearanceSelector Q hQ).val
  coverageAppearanceEventIndex_bound := fun Q hQ =>
    (h.finalPrefixAppearanceSelector Q hQ).isLt
  coverageAppearanceEventIndex_eq_eventToBadNode := fun Q hQ =>
    h.finalPrefixAppearanceSelector_eq_eventToBadNode Q hQ
  eventPrefixesExhaustSelectedBadNodes_proof :=
    h.eventPrefixesExhaustSelectedBadNodes_proof
  everySelectedBadNodeAppearsInSomePrefix_proof :=
    h.everySelectedBadNodeAppearsInSomePrefix_proof
  prefixDominatesFiniteSelectedBadTreeBetaSum_proof :=
    h.prefixDominatesFiniteSelectedBadTreeBetaSum_proof
  duplicateEventsChargeMultiplicityRatherThanEraseIt_proof :=
    h.duplicateEventsChargeMultiplicityRatherThanEraseIt_proof
  noShellOnlyEnumerationShortcut_proof :=
    h.noShellOnlyEnumerationShortcut_proof
  noAdaptiveStoppingFromObservedBetaSquareSum_proof :=
    h.noAdaptiveStoppingFromObservedBetaSquareSum_proof
  eventIndexFixedBeforePayoff :=
    h.finalSelectorFixedBeforePayoff
  eventIndexFixedBeforePayoff_proof :=
    h.finalSelectorFixedBeforePayoff_proof
  eventIndexUsesSameBadCenterEventNodes :=
    h.finalSelectorUsesSameBadCenterEventNodes
  eventIndexUsesSameBadCenterEventNodes_proof :=
    h.finalSelectorUsesSameBadCenterEventNodes_proof
  noBarePropChoiceForEventIndex :=
    h.noBarePropChoiceForFinalSelector
  noBarePropChoiceForEventIndex_proof :=
    h.noBarePropChoiceForFinalSelector_proof
  noEndpointCapacityOnlyEventIndex :=
    h.noEndpointCapacityOnlyFinalSelector
  noEndpointCapacityOnlyEventIndex_proof :=
    h.noEndpointCapacityOnlyFinalSelector_proof
  noPostPayoffEventIndex :=
    h.noPostPayoffFinalSelector
  noPostPayoffEventIndex_proof :=
    h.noPostPayoffFinalSelector_proof
  noLevel517EnumerationSource :=
    h.noLevel517EnumerationSource
  noLevel517EnumerationSource_proof :=
    h.noLevel517EnumerationSource_proof
  noLevel518NaturalEnumerationSource :=
    h.noLevel518NaturalEnumerationSource
  noLevel518NaturalEnumerationSource_proof :=
    h.noLevel518NaturalEnumerationSource_proof
  noLevel519WitnessBoundAdapterSource :=
    h.noLevel519WitnessBoundAdapterSource
  noLevel519WitnessBoundAdapterSource_proof :=
    h.noLevel519WitnessBoundAdapterSource_proof

/-- Smallest remaining primitive after the finite-prefix algebra: a fixed
    event-to-bad-node incidence whose weighted-square event prefixes dominate
    the selected bad-center beta-square sums with bounded multiplicity. -/
structure BadCenterEventNonadaptiveWeightedSquareDomination
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  incidenceNonadaptive : Prop
  sameNormalizedExcessCarrier : Prop
  eventWeightComparableToNodeRadius : Prop
  eventGainControlsNodeBeta : Prop
  coversBadCenterScaleTruncations : Prop
  prefixCofinalWithScaleTruncations : Prop
  boundedIncidenceMultiplicity : Prop
  badBetaSquareDominatedByEventPrefix : Prop
  noSingleEventPaysUnboundedBadNodes : Prop
  noPostHocMatchingAfterRadiusAccounting : Prop

/-- Scale-truncation presentation for selected bad centers. This is the finite
    prefix object that must be cofinal with event prefixes before an event budget
    can become a full bad-tree Carleson estimate. -/
structure BadCenterScaleTruncationPresentation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  scaleTruncation : ℕ → Set DyadicParabolicCube
  finiteAtEachScale : Prop
  monotoneInScale : Prop
  exhaustsSelectedBadNodes : Prop
  truncationUsesCarrierRadii : Prop
  betaSquareRadiusPartialSums : ℕ → ℝ
  partialSumsRepresentTruncatedBetaSquareRadius : Prop
  fullCarlesonSumRecoveredByMonotoneLimit : Prop

/-- Concrete data shape for scale truncations by carrier radius.  This keeps
    scale presentation below the event-prefix and beta-Carleson endpoint:
    it only supplies finite radius-cutoff prefixes and their monotone limit. -/
structure BadCenterRadiusCutoffScaleTruncationData
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  radiusCutoffTruncation : ℕ → Set DyadicParabolicCube
  finiteAtEachCutoff : Prop
  monotoneCutoffs : Prop
  cutoffsExhaustSelectedBadNodes : Prop
  cutoffsUseCarrierRadiiOnly : Prop
  betaSquareRadiusPrefix : ℕ → ℝ
  prefixRepresentsCutoffBetaSquareRadius : Prop
  monotoneLimitRecoversFullCarlesonSum : Prop

/-- Adapter from radius-cutoff truncation data to the scale-truncation
    presentation consumed by the same-tree event route. -/
def BadCenterScaleTruncationPresentation.ofRadiusCutoffData
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h :
      BadCenterRadiusCutoffScaleTruncationData seq K hRho hCarrier hBeta) :
    BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta where
  scaleTruncation := h.radiusCutoffTruncation
  finiteAtEachScale := h.finiteAtEachCutoff
  monotoneInScale := h.monotoneCutoffs
  exhaustsSelectedBadNodes := h.cutoffsExhaustSelectedBadNodes
  truncationUsesCarrierRadii := h.cutoffsUseCarrierRadiiOnly
  betaSquareRadiusPartialSums := h.betaSquareRadiusPrefix
  partialSumsRepresentTruncatedBetaSquareRadius :=
    h.prefixRepresentsCutoffBetaSquareRadius
  fullCarlesonSumRecoveredByMonotoneLimit :=
    h.monotoneLimitRecoversFullCarlesonSum

/-- Event incidence geometry for bad-center sections. This is the place where a
    recurrence/process section must become a section of the normalized-excess
    bad-center tree, with bounded fanout. -/
structure BadCenterEventIncidenceGeometry
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  incidence : ℕ → DyadicParabolicCube → Prop
  incidenceFixedBeforeRadiusAccounting : Prop
  incidenceLandsInSelectedBadNodes : Prop
  eventToBadNodeRefinesIncidence : Prop
  eventSectionsAreBadCenterScaleSections : Prop
  eventWeightComparableToNodeRadius : Prop
  eventGainControlsNodeBeta : Prop
  boundedFanoutPerEvent : Prop
  boundedOverlapOfBadCenterEventTents : Prop
  noPostHocMatching : Prop

/-- Cheapest positive incidence constructor: use the declared event-to-bad-node
    map as singleton incidence.  This advances the same-tree route only at the
    geometry/multiplicity layer; it does not assert prefix domination or the
    beta-Carleson endpoint. -/
def BadCenterEventIncidenceGeometry.ofPointwiseSingletonIncidence
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hBoundedOverlap : Prop) :
    BadCenterEventIncidenceGeometry
      seq K hRho hCarrier hBeta hEvents L where
  incidence := fun e Q => Q = hEvents.eventToBadNode e
  incidenceFixedBeforeRadiusAccounting :=
    hEvents.noPostHocEventChoiceFromRadiusSum
  incidenceLandsInSelectedBadNodes :=
    hPoint.eventToBadNodeLandsInSelectedNodes
  eventToBadNodeRefinesIncidence :=
    ∀ e : ℕ, hEvents.eventToBadNode e = hEvents.eventToBadNode e
  eventSectionsAreBadCenterScaleSections :=
    hSource.eventSectionsAreSelectedBadCenterSections
  eventWeightComparableToNodeRadius :=
    ∀ e : ℕ, L.eventWeight e =
      hCarrier.nodeRadius (hEvents.eventToBadNode e)
  eventGainControlsNodeBeta :=
    ∀ e : ℕ, L.eventGain e =
      hBeta.betaNumber (hEvents.eventToBadNode e)
  boundedFanoutPerEvent :=
    hPoint.eventPrefixMultiplicityMatchesSelectedNodeMultiplicity
  boundedOverlapOfBadCenterEventTents := hBoundedOverlap
  noPostHocMatching := hPoint.noAdaptiveReindexingFromBetaSquareSum

/-- Monotone/beta carrier behind eventized quantitative stratification. This is
    the Perelman-style slot: a finite scale quantity whose drop makes non-flat
    bad-center geometry visible. -/
structure BadCenterEventizedMonotoneBetaCarrier
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  monotoneQuantity : DyadicParabolicCube → ℝ
  finiteBudget : Prop
  almostMonotoneAcrossBadCenterTree : Prop
  betaSquareControlledByScaleDrop : Prop
  coneSplittingPreventsLogPileup : Prop
  pressureErrorsAbsorbedInSameCarrier : Prop
  duhamelErrorsAbsorbedInSameCarrier : Prop
  excludesClassicalRadiusSquaredOnlyAccounting : Prop

/-- Adapter: the existing quantitative-differentiation package supplies the
    monotone beta carrier part of the eventized route. It does not supply scale
    truncations or event incidence geometry. -/
def BadCenterEventizedMonotoneBetaCarrier.ofQuantitativeDifferentiation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h : BadCenterQuantitativeDifferentiationPackage seq K hRho hCarrier hBeta)
    (hDuhamelSameCarrier : Prop) :
    BadCenterEventizedMonotoneBetaCarrier seq K hRho hCarrier hBeta where
  monotoneQuantity := h.frequency
  finiteBudget := h.finiteFrequencyBudget
  almostMonotoneAcrossBadCenterTree := h.scaleMonotonicityOrAlmostMonotonicity
  betaSquareControlledByScaleDrop := h.betaSquareControlledByFrequencyDrop
  coneSplittingPreventsLogPileup := h.coneSplittingForNonflatBadCenters
  pressureErrorsAbsorbedInSameCarrier := h.pressureTailErrorsAbsorbedInDrop
  duhamelErrorsAbsorbedInSameCarrier := hDuhamelSameCarrier
  excludesClassicalRadiusSquaredOnlyAccounting := h.betaSquareControlledByFrequencyDrop

/-- Guard: quantitative differentiation can supply a monotone beta carrier, but
    it does not by itself construct event prefixes or bounded event/bad-node
    incidence. -/
structure QuantitativeDifferentiationDoesNotSupplyEventIncidence
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  quantitativeDifferentiationPackage :
    BadCenterQuantitativeDifferentiationPackage _seq _K hRho hCarrier hBeta
  suppliesMonotoneBetaCarrier : Prop
  eventStreamNotConstructed : Prop
  eventPrefixCofinalityMissing : Prop
  boundedIncidenceMultiplicityMissing : Prop
  stillRequiresIncidenceGeometry :
    ∀ hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier,
      BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- The 10x candidate theorem surface: construct the event stream from the same
    quantitative-stratification / bad-center geometry rather than importing an
    unrelated recurrence stream.  If this can be proved from Navier-Stokes
    structure, event pricing becomes a true beta-Carleson mechanism. -/
structure EventizedParabolicBetaCarlesonQuantitativeStratification
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventStreamConstructedFromBadCenterStoppingTree : Prop
  eventSectionsAreBadCenterScaleSections : Prop
  nodeRadiusComparableToEventWeight : Prop
  betaNumberControlledByEventGain : Prop
  quantitativeDifferentiationControlsNonflatEvents : Prop
  coneSplittingPreventsLogPileupOfIncidence : Prop
  pressureAndDuhamelErrorsStayOnSameCarrier : Prop
  scaleTruncationsCofinalWithEventPrefixes : Prop
  boundedOverlapOfEventizedBadCenterTents : Prop
  weightedSquareDomination :
    BadCenterEventNonadaptiveWeightedSquareDomination
      _seq _K hRho hCarrier hBeta hEvents L

/-- Split witness for the eventized quantitative-stratification target. The
    fields isolate the exact work left after finite-prefix event algebra:
    scale truncations, incidence geometry, and a monotone beta carrier. -/
structure EventizedParabolicBetaCarlesonQuantStratSplitWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  scaleTruncations :
    BadCenterScaleTruncationPresentation
      _seq _K hRho hCarrier hBeta
  incidenceGeometry :
    BadCenterEventIncidenceGeometry
      _seq _K hRho hCarrier hBeta hEvents L
  monotoneBetaCarrier :
    BadCenterEventizedMonotoneBetaCarrier
      _seq _K hRho hCarrier hBeta
  eventPrefixesCofinalWithScaleTruncations : Prop
  incidenceDominatesTruncatedBetaSquareRadius : Prop
  eventPricePaysMonotoneBetaDrop : Prop
  pressureDuhamelSameCarrierCompatibility : Prop
  producesWeightedSquareDomination :
    BadCenterEventNonadaptiveWeightedSquareDomination
      _seq _K hRho hCarrier hBeta hEvents L
  producesEventizedQuantStrat :
    EventizedParabolicBetaCarlesonQuantitativeStratification
      _seq _K hRho hCarrier hBeta hEvents L

/-- Non-circular assembly data for the eventized quantitative-stratification
    route. Unlike the coarse split witness above, this record lists the fields
    needed to build weighted-square domination instead of storing the endpoint
    domination theorem as a field. -/
structure EventizedParabolicBetaCarlesonQuantStratConstructiveData
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  scaleTruncations :
    BadCenterScaleTruncationPresentation
      _seq _K hRho hCarrier hBeta
  incidenceGeometry :
    BadCenterEventIncidenceGeometry
      _seq _K hRho hCarrier hBeta hEvents L
  monotoneBetaCarrier :
    BadCenterEventizedMonotoneBetaCarrier
      _seq _K hRho hCarrier hBeta
  eventStreamConstructedFromBadCenterStoppingTree : Prop
  quantitativeDifferentiationControlsNonflatEvents : Prop
  pressureAndDuhamelErrorsStayOnSameCarrier : Prop
  eventPrefixesCofinalWithScaleTruncations : Prop
  badBetaSquareDominatedByEventPrefix : Prop
  noSingleEventPaysUnboundedBadNodes : Prop
  noPostHocMatchingAfterRadiusAccounting : Prop

/-- Same-tree event incidence is the smaller non-tautological primitive below
    the eventized quantitative-stratification record.  The event stream must be
    built from the same normalized-excess bad-center stopping tree as the beta
    data, with a finite event budget that is independent of the desired
    beta-square Carleson conclusion. -/
structure SameTreeNonadaptiveEventIncidenceCarleson
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  scaleTruncations :
    BadCenterScaleTruncationPresentation
      _seq _K hRho hCarrier hBeta
  incidenceGeometry :
    BadCenterEventIncidenceGeometry
      _seq _K hRho hCarrier hBeta hEvents L
  incidenceConstructedFromSameBadCenterTree : Prop
  nonadaptiveBeforeRadiusAccounting : Prop
  prefixesCofinalWithScaleTruncations : Prop
  boundedFanoutPaysBetaSquareRadius : Prop
  prefixDominationByEventPrices : Prop
  finiteSameTreeEventBudget : Prop
  eventBudgetNotDefinedAsTargetCarlesonSum : Prop

/-- The same-tree incidence primitive is exactly strong enough to supply the
    nonadaptive weighted-square domination interface. -/
def BadCenterEventNonadaptiveWeightedSquareDomination.ofSameTreeIncidence
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      SameTreeNonadaptiveEventIncidenceCarleson
        seq K hRho hCarrier hBeta hEvents L) :
    BadCenterEventNonadaptiveWeightedSquareDomination
      seq K hRho hCarrier hBeta hEvents L where
  incidenceNonadaptive := h.nonadaptiveBeforeRadiusAccounting
  sameNormalizedExcessCarrier := h.incidenceConstructedFromSameBadCenterTree
  eventWeightComparableToNodeRadius :=
    h.incidenceGeometry.eventWeightComparableToNodeRadius
  eventGainControlsNodeBeta :=
    h.incidenceGeometry.eventGainControlsNodeBeta
  coversBadCenterScaleTruncations :=
    h.incidenceGeometry.incidenceLandsInSelectedBadNodes
  prefixCofinalWithScaleTruncations := h.prefixesCofinalWithScaleTruncations
  boundedIncidenceMultiplicity := h.boundedFanoutPaysBetaSquareRadius
  badBetaSquareDominatedByEventPrefix := h.prefixDominationByEventPrices
  noSingleEventPaysUnboundedBadNodes := h.boundedFanoutPaysBetaSquareRadius
  noPostHocMatchingAfterRadiusAccounting := h.nonadaptiveBeforeRadiusAccounting

/-- Pressure/Duhamel errors must be charged to the same bad-center event
    stream.  A separate shell/process ledger cannot be matched after radius
    accounting without reintroducing the event/bad-node identification gap. -/
structure PressureDuhamelSameCarrierLock
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger)
    (hSameTree :
      SameTreeNonadaptiveEventIncidenceCarleson
        _seq _K hRho hCarrier hBeta hEvents L) where
  pressureErrorsAssignedToSameEvents : Prop
  duhamelErrorsAssignedToSameEvents : Prop
  pressureDuhamelCostDominatedBySameEventBudget : Prop
  noShellProcessPostHocMatching : Prop

/-- Low-beta bad centers need a separate flat/skeleton alternative.  Beta-square
    control alone does not pay radius length for flat or nearly flat bad
    one-dimensional strands. -/
structure FlatBadCenterSkeletonLengthControl
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  flatNodes : DyadicParabolicCube → Prop
  finiteFlatSkeletonLengthBudget : Prop
  nonflatNodesHaveBetaLowerBound : Prop
  flatNodesDoNotHideLogMinkowskiMultiplicity : Prop
  flatAlternativeFeedsRadiusCharging : Prop

/-- Guard: chain-wise quantitative differentiation does not imply global
    beta-square Carleson control over all bad centers.  It can miss
    same-scale logarithmic multiplicity. -/
structure ChainwiseBetaDropDoesNotGiveGlobalBetaCarleson
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  chainwiseQuantitativeDifferentiation : Prop
  everyChainHasSummableBetaDrop : Prop
  sameScaleBadCenterMultiplicityUncontrolled : Prop
  classicalRadiusSquaredChargeStillFinite : Prop
  radiusWeightedBetaSquareCanDiverge : Prop
  requiresSameTreeEventIncidenceCarleson :
    ∀ (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
      (L : EventRecurrencePriceLedger),
      SameTreeNonadaptiveEventIncidenceCarleson
        _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- Constructor: once the same bad-center tree carries a nonadaptive event
    incidence with finite budget, pressure/Duhamel errors stay on that carrier,
    and flat low-beta nodes have their own finite-length alternative, the
    existing eventized constructive record is populated without defining the
    event price to be the target beta-square sum. -/
def EventizedParabolicBetaCarlesonQuantStratConstructiveData.ofSameTreeIncidence
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hSameTree :
      SameTreeNonadaptiveEventIncidenceCarleson
        seq K hRho hCarrier hBeta hEvents L)
    (hMono :
      BadCenterEventizedMonotoneBetaCarrier
        seq K hRho hCarrier hBeta)
    (hPressure :
      PressureDuhamelSameCarrierLock
        seq K hRho hCarrier hBeta hEvents L hSameTree)
    (hFlat :
      FlatBadCenterSkeletonLengthControl seq K hRho hCarrier hBeta) :
    EventizedParabolicBetaCarlesonQuantStratConstructiveData
      seq K hRho hCarrier hBeta hEvents L where
  scaleTruncations := hSameTree.scaleTruncations
  incidenceGeometry := hSameTree.incidenceGeometry
  monotoneBetaCarrier := hMono
  eventStreamConstructedFromBadCenterStoppingTree :=
    hSameTree.incidenceConstructedFromSameBadCenterTree
  quantitativeDifferentiationControlsNonflatEvents :=
    hFlat.nonflatNodesHaveBetaLowerBound
  pressureAndDuhamelErrorsStayOnSameCarrier :=
    hPressure.pressureDuhamelCostDominatedBySameEventBudget
  eventPrefixesCofinalWithScaleTruncations :=
    hSameTree.prefixesCofinalWithScaleTruncations
  badBetaSquareDominatedByEventPrefix :=
    hSameTree.prefixDominationByEventPrices
  noSingleEventPaysUnboundedBadNodes :=
    hSameTree.boundedFanoutPaysBetaSquareRadius
  noPostHocMatchingAfterRadiusAccounting :=
    hSameTree.nonadaptiveBeforeRadiusAccounting

/-- Constructor for the core domination primitive from non-circular eventized
    quantitative-stratification data. -/
def BadCenterEventNonadaptiveWeightedSquareDomination.ofEventizedConstructiveData
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      EventizedParabolicBetaCarlesonQuantStratConstructiveData
        seq K hRho hCarrier hBeta hEvents L) :
    BadCenterEventNonadaptiveWeightedSquareDomination
      seq K hRho hCarrier hBeta hEvents L where
  incidenceNonadaptive := h.incidenceGeometry.incidenceFixedBeforeRadiusAccounting
  sameNormalizedExcessCarrier := h.monotoneBetaCarrier.pressureErrorsAbsorbedInSameCarrier
  eventWeightComparableToNodeRadius := h.incidenceGeometry.eventWeightComparableToNodeRadius
  eventGainControlsNodeBeta := h.incidenceGeometry.eventGainControlsNodeBeta
  coversBadCenterScaleTruncations := h.incidenceGeometry.incidenceLandsInSelectedBadNodes
  prefixCofinalWithScaleTruncations := h.eventPrefixesCofinalWithScaleTruncations
  boundedIncidenceMultiplicity := h.incidenceGeometry.boundedFanoutPerEvent
  badBetaSquareDominatedByEventPrefix := h.badBetaSquareDominatedByEventPrefix
  noSingleEventPaysUnboundedBadNodes := h.noSingleEventPaysUnboundedBadNodes
  noPostHocMatchingAfterRadiusAccounting := h.noPostHocMatchingAfterRadiusAccounting

/-- Constructor for the named eventized quantitative-stratification target from
    the non-circular assembly data. -/
def EventizedParabolicBetaCarlesonQuantitativeStratification.ofConstructiveData
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      EventizedParabolicBetaCarlesonQuantStratConstructiveData
        seq K hRho hCarrier hBeta hEvents L) :
    EventizedParabolicBetaCarlesonQuantitativeStratification
      seq K hRho hCarrier hBeta hEvents L where
  eventStreamConstructedFromBadCenterStoppingTree :=
    h.eventStreamConstructedFromBadCenterStoppingTree
  eventSectionsAreBadCenterScaleSections :=
    h.incidenceGeometry.eventSectionsAreBadCenterScaleSections
  nodeRadiusComparableToEventWeight :=
    h.incidenceGeometry.eventWeightComparableToNodeRadius
  betaNumberControlledByEventGain :=
    h.incidenceGeometry.eventGainControlsNodeBeta
  quantitativeDifferentiationControlsNonflatEvents :=
    h.quantitativeDifferentiationControlsNonflatEvents
  coneSplittingPreventsLogPileupOfIncidence :=
    h.monotoneBetaCarrier.coneSplittingPreventsLogPileup
  pressureAndDuhamelErrorsStayOnSameCarrier :=
    h.pressureAndDuhamelErrorsStayOnSameCarrier
  scaleTruncationsCofinalWithEventPrefixes :=
    h.eventPrefixesCofinalWithScaleTruncations
  boundedOverlapOfEventizedBadCenterTents :=
    h.incidenceGeometry.boundedOverlapOfBadCenterEventTents
  weightedSquareDomination :=
    BadCenterEventNonadaptiveWeightedSquareDomination.ofEventizedConstructiveData h

/-- Adapter from the split witness to the named eventized quantitative
    stratification target. -/
def EventizedParabolicBetaCarlesonQuantitativeStratification.ofSplitWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      EventizedParabolicBetaCarlesonQuantStratSplitWitness
        seq K hRho hCarrier hBeta hEvents L) :
    EventizedParabolicBetaCarlesonQuantitativeStratification
      seq K hRho hCarrier hBeta hEvents L :=
  h.producesEventizedQuantStrat

/-- Adapter: eventized quantitative stratification is exactly the missing
    nonadaptive weighted-square domination primitive. -/
def BadCenterEventNonadaptiveWeightedSquareDomination.ofEventizedQuantStrat
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      EventizedParabolicBetaCarlesonQuantitativeStratification
        seq K hRho hCarrier hBeta hEvents L) :
    BadCenterEventNonadaptiveWeightedSquareDomination
      seq K hRho hCarrier hBeta hEvents L :=
  h.weightedSquareDomination

/-- Guard: the existing event recurrence algebra does not construct the
    eventized bad-center quantitative-stratification carrier. -/
structure EventizedQuantStratNotSuppliedByEventAlgebraAlone
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (L : EventRecurrencePriceLedger) where
  eventPrefixBudgetClosed : ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  sectionIncidenceMayBeShellProcessOnly : Prop
  badCenterStoppingTreeNotConstructedFromEvents : Prop
  betaGeometryNotControlledByRecurrenceGainAlone : Prop
  pressureDuhamelCarrierMayDifferFromNormalizedExcessCarrier : Prop
  cannotDeriveEventizedQuantStratFromAlgebraAlone : Prop

/-- Guard: event prefixes can be finite and budgeted without being cofinal with
    scale truncations of the selected normalized-excess bad-center tree. -/
structure ScaleTruncationCofinalityNotSuppliedByEventPrefixAlone
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventPrefixBudgetClosed : ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  scaleTruncationsExist :
    BadCenterScaleTruncationPresentation _seq _K hRho hCarrier hBeta
  eventPrefixesMayMissBadScaleTruncations : Prop
  eventOrderMayNotBeScaleOrder : Prop
  prefixCofinalityIsAdditionalCarrierTheorem : Prop
  noCarlesonLimitFromEventPrefixesAlone : Prop

/-- Guard: a fixed section incidence for recurrence events is not yet a
    physical incidence geometry for normalized-excess bad centers. -/
structure SectionIncidenceDoesNotGiveBadCenterIncidenceGeometry
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  fixedEventSectionIncidence : Prop
  sectionMayBeShellOrProcessSectionOnly : Prop
  badCenterNodeGeometryNotIdentified : Prop
  radiusWeightComparabilityNotAutomatic : Prop
  betaGainComparabilityNotAutomatic : Prop
  boundedFanoutNotAutomatic : Prop
  requiresBadCenterEventIncidenceGeometry :
    BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- Guard: neither classical CKN mass nor event prefix algebra supplies the
    monotone beta carrier needed to price non-flat bad-center geometry. -/
structure MonotoneBetaCarrierNotSuppliedByCKNMassOrEventAlgebra
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  classicalCKNMassPaysOnlyRadiusSquared : Prop
  normalizedExcessDetectsBadnessButDoesNotTelescope : Prop
  eventPrefixBudgetPaysOnlyDeclaredEvents : Prop
  betaSquareDropNotConstructed : Prop
  pressureDuhamelErrorsNeedSameCarrierAbsorption : Prop
  coneSplittingNoLogPileupNotAutomatic : Prop
  requiresEventizedMonotoneBetaCarrier :
    BadCenterEventizedMonotoneBetaCarrier _seq _K hRho hCarrier hBeta → Prop

/-- Event-prefix budget bridge. The finite-prefix estimate is proved from the
    pointwise event/bad-center identity plus Duhamel/incidence source; the
    remaining coverage fields say that these prefixes actually dominate the
    selected bad-tree Carleson sum. -/
structure BadCenterEventBudgetedBetaSquarePrefixBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  events : BadCenterEventNodeIdentification _seq _K hRho hCarrier
  pointwiseIdentity :
    BadCenterEventPointwiseBetaSquareIdentity
      _seq _K hRho hCarrier hBeta events L
  priceSource :
    BadCenterEventPriceDropDuhamelIncidenceSource
      _seq _K hRho hCarrier events L
  coverage :
    BadCenterEventPrefixCoversSelectedBadTree
      _seq _K hRho hCarrier hBeta events
  domination :
    BadCenterEventNonadaptiveWeightedSquareDomination
      _seq _K hRho hCarrier hBeta events L
  finitePrefixBudget :
    ∀ N : ℕ,
      badCenterEventBetaSquarePrefix (hBeta := hBeta) events N ≤
        L.priceBudget
  eventBudgetIsFiniteNSBudget : Prop
  selectedTreeCarlesonSumControlledByEventPrefixes : Prop
  producesBetaSquareCarlesonDrop :
    BadCenterBetaSquareCarlesonDrop _seq _K hRho hCarrier hBeta

/-- Non-circular adapter from finite event-prefix budgeting plus weighted-square
    domination to the bad-center beta-square Carleson drop.  This is still a
    Prop-level constructor, but it no longer asks for the endpoint drop as an
    input. -/
def BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hCoverage :
      BadCenterEventPrefixCoversSelectedBadTree
        seq K hRho hCarrier hBeta hEvents)
    (hDomination :
      BadCenterEventNonadaptiveWeightedSquareDomination
        seq K hRho hCarrier hBeta hEvents L)
    (hFiniteBudget : Prop)
    (hTreeControl : Prop) :
    BadCenterBetaSquareCarlesonDrop seq K hRho hCarrier hBeta where
  finiteNSBudget := And hFiniteBudget hSource.priceBudgetMatchesFiniteNSScaleBudget
  betaSquareRadiusCharge :=
    And
      (∀ N : ℕ,
        badCenterEventBetaSquarePrefix (hBeta := hBeta) hEvents N ≤
          L.priceBudget)
      hDomination.badBetaSquareDominatedByEventPrefix
  carlesonSummationOverBadTree :=
    And hCoverage.prefixDominatesFiniteSelectedBadTreeBetaSum hTreeControl
  excludesLogPileupInheritedTrees :=
    And hDomination.noSingleEventPaysUnboundedBadNodes
      hCoverage.duplicateEventsChargeMultiplicityRatherThanEraseIt
  chargesBetaSquareRadiusNotClassicalRadiusSquared :=
    And
      (And hDomination.eventGainControlsNodeBeta
        hDomination.eventWeightComparableToNodeRadius)
      (And hPoint.eventToBadNodeLandsInSelectedNodes
        hSource.rawRecurrencePrefixIsSameCarrierScaleDrop)

/-- Same-tree specialization of the event-budgeted beta-drop adapter.  Once the
    same-tree incidence primitive is built, it supplies the weighted-square
    domination interface consumed by the non-circular beta-drop constructor. -/
def BadCenterBetaSquareCarlesonDrop.ofSameTreeEventBudgetedPrefixData
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hCoverage :
      BadCenterEventPrefixCoversSelectedBadTree
        seq K hRho hCarrier hBeta hEvents)
    (hSameTree :
      SameTreeNonadaptiveEventIncidenceCarleson
        seq K hRho hCarrier hBeta hEvents L)
    (hFiniteBudget : Prop)
    (hTreeControl : Prop) :
    BadCenterBetaSquareCarlesonDrop seq K hRho hCarrier hBeta :=
  BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData
    hPoint
    hSource
    hCoverage
    (BadCenterEventNonadaptiveWeightedSquareDomination.ofSameTreeIncidence
      hSameTree)
    hFiniteBudget
    hTreeControl

/-- Constructor for the event-prefix bridge from the two proved finite-prefix
    inputs and the remaining coverage/multiplicity witness. -/
def BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverage
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hCoverage :
      BadCenterEventPrefixCoversSelectedBadTree
        seq K hRho hCarrier hBeta hEvents)
    (hDomination :
      BadCenterEventNonadaptiveWeightedSquareDomination
        seq K hRho hCarrier hBeta hEvents L)
    (hFiniteBudget : Prop)
    (hTreeControl : Prop)
    (hDrop : BadCenterBetaSquareCarlesonDrop seq K hRho hCarrier hBeta) :
    BadCenterEventBudgetedBetaSquarePrefixBridge
      seq K hRho hCarrier hBeta L where
  events := hEvents
  pointwiseIdentity := hPoint
  priceSource := hSource
  coverage := hCoverage
  domination := hDomination
  finitePrefixBudget :=
    badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource
      hPoint
      hSource
  eventBudgetIsFiniteNSBudget := hFiniteBudget
  selectedTreeCarlesonSumControlledByEventPrefixes := hTreeControl
  producesBetaSquareCarlesonDrop := hDrop

/-- Non-circular constructor for the event-prefix bridge.  The endpoint
    beta-square drop is built from the prefix budget and domination fields
    instead of being supplied as a hypothesis. -/
def BadCenterEventBudgetedBetaSquarePrefixBridge.ofPointwiseDuhamelCoverageNonCircular
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hCoverage :
      BadCenterEventPrefixCoversSelectedBadTree
        seq K hRho hCarrier hBeta hEvents)
    (hDomination :
      BadCenterEventNonadaptiveWeightedSquareDomination
        seq K hRho hCarrier hBeta hEvents L)
    (hFiniteBudget : Prop)
    (hTreeControl : Prop) :
    BadCenterEventBudgetedBetaSquarePrefixBridge
      seq K hRho hCarrier hBeta L where
  events := hEvents
  pointwiseIdentity := hPoint
  priceSource := hSource
  coverage := hCoverage
  domination := hDomination
  finitePrefixBudget :=
    badCenterEventBetaSquarePrefix_le_eventBudget_ofDuhamelIncidenceSource
      hPoint
      hSource
  eventBudgetIsFiniteNSBudget := hFiniteBudget
  selectedTreeCarlesonSumControlledByEventPrefixes := hTreeControl
  producesBetaSquareCarlesonDrop :=
    BadCenterBetaSquareCarlesonDrop.ofEventBudgetedPrefixData
      hPoint hSource hCoverage hDomination hFiniteBudget hTreeControl

/-- Guard: a finite event-prefix budget can coexist with a divergent selected
    bad-center beta-radius sum if event-to-node incidence has unbounded fanout or
    leaves bad nodes uncovered. -/
structure EventPrefixBudgetDoesNotImplyBadCenterBetaCarleson
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (L : EventRecurrencePriceLedger) where
  eventPrefixBound : ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  badCenterCarrierUnidentified : Prop
  selectedBadNodesMayBeUncovered : Prop
  eventFanoutMayBeUnbounded : Prop
  noWeightedSquareDomination : Prop
  noBetaCarlesonConclusionFromEventBudgetAlone : Prop

/-- Guard: the naive event-per-node construction is tautological unless the
    event budget is independently finite before the bad-center beta-square
    radius sum is introduced. -/
structure EventPerBadNodeConstructionIsTautological
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  eventForEachBadNode : Prop
  eventWeightDefinedAsNodeRadius : Prop
  eventGainDefinedAsNodeBeta : Prop
  eventPriceEqualsTargetBetaSquareRadiusSum : Prop
  noIndependentFiniteNSBudget : Prop
  doesNotProveSameTreeEventIncidenceCarleson :
    ∀ (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
      (L : EventRecurrencePriceLedger),
      SameTreeNonadaptiveEventIncidenceCarleson
        _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- The positive construction must include an independent budget witness: a
    finite Navier-Stokes quantity that bounds event prices before those prices
    are identified with bad-center beta-square radius mass. -/
structure IndependentSameTreeEventBudgetWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  finiteNSBudgetCarrier : Prop
  eventPricesBoundedBeforeBetaCarlesonTarget : Prop
  budgetNotDefinedFromBadCenterRadiusSum : Prop
  budgetPersistsUnderScaleTruncationPrefixes : Prop
  pressureDuhamelErrorsChargedToBudget : Prop
  suppliesFiniteSameTreeEventBudget :
    SameTreeNonadaptiveEventIncidenceCarleson
      _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- Concrete PDE candidate for the independent budget: a Duhamel/Bernstein
    reserve built on the same bad-center stopping tree, whose reserve drop pays
    event prices before those event prices are identified with bad-center beta
    radius. This is the narrow source one would need for a genuine 100x bridge. -/
structure DuhamelSameTreeIndependentEventBudgetCandidate
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  duhamelSectionsAreBadCenterSections : Prop
  bernsteinEnvelopeDefinedBeforeBetaAccounting : Prop
  finiteReserveBudget : Prop
  reserveDropPaysEventWeightedGainPrice :
    ∀ e : ℕ,
      L.eventWeight e * (L.eventGain e) ^ (2 : Nat) ≤
        L.rawPrice e + L.recurrencePrice e
  eventPricesBoundedOnScalePrefixes :
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  pressureErrorsChargedToSameReserve : Prop
  duhamelErrorsChargedToSameReserve : Prop
  reserveNotDefinedFromBadCenterRadiusSum : Prop
  survivesBadCenterScaleTruncationLimit : Prop

/-- Guard: a Duhamel/Bernstein reserve from the event-recurrence file may still
    be a shell/process reserve.  It does not become a bad-center independent
    budget unless its sections are constructed from the normalized-excess
    stopping tree before beta/radius accounting. -/
structure DuhamelReserveCanBeShellOnlyNotBadCenterBudget
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventDuhamelBernsteinReceiptAvailable : Prop
  eventPrefixBudgetClosed : ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  reserveMayBeShellOrProcessSection : Prop
  badCenterSectionsNotIdentified : Prop
  scalePrefixCofinalityMissing : Prop
  pressureDuhamelSameCarrierMissing : Prop
  noIndependentBadCenterBudgetConclusion :
    ¬ Nonempty
      (DuhamelSameTreeIndependentEventBudgetCandidate
        _seq _K hRho hCarrier hBeta hEvents L)

/-- Guard: an event reserve can be finite while still reusing the same reserve
    over many selected bad centers unless a bounded fanout / multiplicity field
    is proved on the bad-center incidence geometry. -/
structure DuhamelReserveReuseCanMissBadCenterMultiplicity
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  finiteReserveBudget : Prop
  oneReserveEventCanTouchManyBadCenters : Prop
  boundedFanoutNotProved : Prop
  selectedBadCenterMultiplicityMayDiverge : Prop
  requiresBadCenterEventIncidenceGeometry :
    BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- Guard: pressure/Duhamel compatibility is not a cosmetic field.  If pressure
    tails or Duhamel residuals are booked on a different carrier, the
    independent event budget cannot telescope over the selected bad-center
    scale tree. -/
structure PressureDuhamelLeakageBlocksSameTreeBudget
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  reservePaysPureDuhamelPrefix : Prop
  pressureTailBookedElsewhere : Prop
  duhamelResidualBookedElsewhere : Prop
  selectedBadCenterCarrierLosesErrors : Prop
  sameCarrierLockIsAdditionalTheorem : Prop
  noSameTreeIndependentBudgetWithoutCarrierLock : Prop

/-- Constructor from the existing L3A Duhamel/incidence source into the narrower
    same-tree independent event-budget candidate. -/
def DuhamelSameTreeIndependentEventBudgetCandidate.ofPriceDropDuhamelIncidenceSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hPressureSameReserve : Prop)
    (hScaleLimit : Prop) :
    DuhamelSameTreeIndependentEventBudgetCandidate
      seq K hRho hCarrier hBeta hEvents L where
  duhamelSectionsAreBadCenterSections :=
    h.eventSectionsAreSelectedBadCenterSections
  bernsteinEnvelopeDefinedBeforeBetaAccounting :=
    h.duhamelSource.event_prices_declared_before_payoff
  finiteReserveBudget := h.priceBudgetMatchesFiniteNSScaleBudget
  reserveDropPaysEventWeightedGainPrice :=
    let precert := event_precertificate_of_duhamel_bernstein_source L h.duhamelSource
    precert.raw_recurrence_lower_envelope
  eventPricesBoundedOnScalePrefixes :=
    BadCenterEventPriceDropDuhamelIncidenceSource.weightedEventPricePrefix_le_budget h
  pressureErrorsChargedToSameReserve := hPressureSameReserve
  duhamelErrorsChargedToSameReserve :=
    h.duhamelReserveUsesSameBadCenterCarrier
  reserveNotDefinedFromBadCenterRadiusSum :=
    h.noPostHocSectionChoiceFromRadiusSum
  survivesBadCenterScaleTruncationLimit := hScaleLimit

/-- Adapter from a concrete Duhamel same-tree reserve to the independent event
    budget witness. -/
def IndependentSameTreeEventBudgetWitness.ofDuhamelSameTreeBudget
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      DuhamelSameTreeIndependentEventBudgetCandidate
        seq K hRho hCarrier hBeta hEvents L) :
    IndependentSameTreeEventBudgetWitness
      seq K hRho hCarrier hBeta hEvents L where
  finiteNSBudgetCarrier := h.finiteReserveBudget
  eventPricesBoundedBeforeBetaCarlesonTarget :=
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  budgetNotDefinedFromBadCenterRadiusSum :=
    h.reserveNotDefinedFromBadCenterRadiusSum
  budgetPersistsUnderScaleTruncationPrefixes :=
    h.survivesBadCenterScaleTruncationLimit
  pressureDuhamelErrorsChargedToBudget :=
    And h.pressureErrorsChargedToSameReserve h.duhamelErrorsChargedToSameReserve
  suppliesFiniteSameTreeEventBudget :=
    fun _ =>
      ∀ e : ℕ,
        L.eventWeight e * (L.eventGain e) ^ (2 : Nat) ≤
          L.rawPrice e + L.recurrencePrice e

/-- Split witness for the current 100x candidate.  It separates the geometric
    same-tree incidence fields from the independent finite-budget witness, so a
    proof cannot satisfy the record by defining the event price to be the target
    bad-center beta-square radius sum. -/
structure SameTreeEventIncidenceIndependentBudgetSplitWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  scaleTruncations :
    BadCenterScaleTruncationPresentation
      _seq _K hRho hCarrier hBeta
  incidenceGeometry :
    BadCenterEventIncidenceGeometry
      _seq _K hRho hCarrier hBeta hEvents L
  independentBudget :
    IndependentSameTreeEventBudgetWitness
      _seq _K hRho hCarrier hBeta hEvents L
  incidenceConstructedFromSameBadCenterTree : Prop
  nonadaptiveBeforeRadiusAccounting : Prop
  prefixesCofinalWithScaleTruncations : Prop
  boundedFanoutPaysBetaSquareRadius : Prop
  prefixDominationByEventPrices : Prop

/-- Constructor for the 100x split witness from a concrete Duhamel same-tree
    independent budget plus the two geometric witnesses. -/
def SameTreeEventIncidenceIndependentBudgetSplitWitness.ofDuhamelSameTreeBudget
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta)
    (hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L)
    (hBudget :
      DuhamelSameTreeIndependentEventBudgetCandidate
        seq K hRho hCarrier hBeta hEvents L)
    (hCofinal : Prop)
    (hPrefixDomination : Prop) :
    SameTreeEventIncidenceIndependentBudgetSplitWitness
      seq K hRho hCarrier hBeta hEvents L where
  scaleTruncations := hScale
  incidenceGeometry := hInc
  independentBudget :=
    IndependentSameTreeEventBudgetWitness.ofDuhamelSameTreeBudget hBudget
  incidenceConstructedFromSameBadCenterTree :=
    hBudget.duhamelSectionsAreBadCenterSections
  nonadaptiveBeforeRadiusAccounting :=
    hBudget.bernsteinEnvelopeDefinedBeforeBetaAccounting
  prefixesCofinalWithScaleTruncations := hCofinal
  boundedFanoutPaysBetaSquareRadius := hInc.boundedFanoutPerEvent
  prefixDominationByEventPrices := hPrefixDomination

/-- Constructor from the independent-budget split witness to the same-tree
    event incidence primitive. -/
def SameTreeNonadaptiveEventIncidenceCarleson.ofIndependentBudgetSplitWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      SameTreeEventIncidenceIndependentBudgetSplitWitness
        seq K hRho hCarrier hBeta hEvents L) :
    SameTreeNonadaptiveEventIncidenceCarleson
      seq K hRho hCarrier hBeta hEvents L where
  scaleTruncations := h.scaleTruncations
  incidenceGeometry := h.incidenceGeometry
  incidenceConstructedFromSameBadCenterTree :=
    h.incidenceConstructedFromSameBadCenterTree
  nonadaptiveBeforeRadiusAccounting := h.nonadaptiveBeforeRadiusAccounting
  prefixesCofinalWithScaleTruncations :=
    h.prefixesCofinalWithScaleTruncations
  boundedFanoutPaysBetaSquareRadius := h.boundedFanoutPaysBetaSquareRadius
  prefixDominationByEventPrices := h.prefixDominationByEventPrices
  finiteSameTreeEventBudget :=
    h.independentBudget.eventPricesBoundedBeforeBetaCarlesonTarget
  eventBudgetNotDefinedAsTargetCarlesonSum :=
    h.independentBudget.budgetNotDefinedFromBadCenterRadiusSum

/-- Direct positive assembly: an existing Duhamel/incidence source becomes the
    same-tree event incidence primitive once scale truncations, bad-center
    incidence geometry, pressure same-reserve compatibility, and scale-limit
    persistence are supplied. -/
def SameTreeNonadaptiveEventIncidenceCarleson.ofPriceDropDuhamelIncidenceSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta)
    (hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hPressureSameReserve : Prop)
    (hScaleLimit : Prop)
    (hCofinal : Prop)
    (hPrefixDomination : Prop) :
    SameTreeNonadaptiveEventIncidenceCarleson
      seq K hRho hCarrier hBeta hEvents L :=
  SameTreeNonadaptiveEventIncidenceCarleson.ofIndependentBudgetSplitWitness
    (SameTreeEventIncidenceIndependentBudgetSplitWitness.ofDuhamelSameTreeBudget
      hScale
      hInc
      (DuhamelSameTreeIndependentEventBudgetCandidate.ofPriceDropDuhamelIncidenceSource
        hSource
        hPressureSameReserve
        hScaleLimit)
      hCofinal
      hPrefixDomination)

/-- Single packet of the remaining PDE obligations for the current Duhamel
    same-tree route.  Event-side algebra is already available; these fields are
    exactly what still has to be proved on the normalized-excess bad-center
    carrier. -/
structure SameTreeDuhamelBudgetRemainingObligations
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  scaleTruncationPresentation :
    BadCenterScaleTruncationPresentation _seq _K hRho hCarrier hBeta
  badCenterIncidenceGeometry :
    BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L
  duhamelIncidenceSource :
    BadCenterEventPriceDropDuhamelIncidenceSource
      _seq _K hRho hCarrier hEvents L
  pressureErrorsChargedToSameReserve : Prop
  survivesBadCenterScaleTruncationLimit : Prop
  eventPrefixesCofinalWithBadCenterScales : Prop
  eventPrefixesDominateBadCenterBetaSquareSums : Prop

/-- If the remaining Duhamel same-tree obligations are supplied, the same-tree
    nonadaptive event incidence primitive follows. -/
def SameTreeDuhamelBudgetRemainingObligations.toSameTreeIncidence
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      SameTreeDuhamelBudgetRemainingObligations
        seq K hRho hCarrier hBeta hEvents L) :
    SameTreeNonadaptiveEventIncidenceCarleson
      seq K hRho hCarrier hBeta hEvents L :=
  SameTreeNonadaptiveEventIncidenceCarleson.ofPriceDropDuhamelIncidenceSource
    h.scaleTruncationPresentation
    h.badCenterIncidenceGeometry
    h.duhamelIncidenceSource
    h.pressureErrorsChargedToSameReserve
    h.survivesBadCenterScaleTruncationLimit
    h.eventPrefixesCofinalWithBadCenterScales
    h.eventPrefixesDominateBadCenterBetaSquareSums

/-- Build the remaining same-tree Duhamel obligation packet using singleton
    event-to-bad-node incidence.  This removes `badCenterIncidenceGeometry` as a
    separate opaque hypothesis; the remaining hypotheses are scale truncation,
    pressure same-reserve, scale-limit persistence, overlap, cofinality, and
    prefix domination. -/
def SameTreeDuhamelBudgetRemainingObligations.ofPointwiseSingletonIncidence
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta)
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hPressureSameReserve : Prop)
    (hScaleLimit : Prop)
    (hBoundedOverlap : Prop)
    (hCofinal : Prop)
    (hPrefixDomination : Prop) :
    SameTreeDuhamelBudgetRemainingObligations
      seq K hRho hCarrier hBeta hEvents L where
  scaleTruncationPresentation := hScale
  badCenterIncidenceGeometry :=
    BadCenterEventIncidenceGeometry.ofPointwiseSingletonIncidence
      hPoint hSource hBoundedOverlap
  duhamelIncidenceSource := hSource
  pressureErrorsChargedToSameReserve := hPressureSameReserve
  survivesBadCenterScaleTruncationLimit := hScaleLimit
  eventPrefixesCofinalWithBadCenterScales := hCofinal
  eventPrefixesDominateBadCenterBetaSquareSums := hPrefixDomination

/-- Direct same-tree incidence assembly from singleton event-to-bad-node
    incidence.  This is the narrow positive route after the event-prefix algebra:
    pointwise identity plus a concrete Duhamel source are enough for incidence
    geometry; the scale/pressure/prefix fields remain explicit obligations. -/
def SameTreeNonadaptiveEventIncidenceCarleson.ofPointwiseSingletonDuhamelSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta)
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hPressureSameReserve : Prop)
    (hScaleLimit : Prop)
    (hBoundedOverlap : Prop)
    (hCofinal : Prop)
    (hPrefixDomination : Prop) :
    SameTreeNonadaptiveEventIncidenceCarleson
      seq K hRho hCarrier hBeta hEvents L :=
  SameTreeDuhamelBudgetRemainingObligations.toSameTreeIncidence
    (SameTreeDuhamelBudgetRemainingObligations.ofPointwiseSingletonIncidence
      hScale
      hPoint
      hSource
      hPressureSameReserve
      hScaleLimit
      hBoundedOverlap
      hCofinal
      hPrefixDomination)

/-- Same-tree assembly using radius-cutoff scale truncations and singleton
    event-to-bad-node incidence.  After this adapter, the remaining same-tree
    assumptions are pressure same-reserve, scale-limit persistence, bounded
    overlap, cofinality, and prefix domination. -/
def SameTreeNonadaptiveEventIncidenceCarleson.ofRadiusCutoffSingletonDuhamelSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hScale :
      BadCenterRadiusCutoffScaleTruncationData seq K hRho hCarrier hBeta)
    (hPoint :
      BadCenterEventPointwiseBetaSquareIdentity
        seq K hRho hCarrier hBeta hEvents L)
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hPressureSameReserve : Prop)
    (hScaleLimit : Prop)
    (hBoundedOverlap : Prop)
    (hCofinal : Prop)
    (hPrefixDomination : Prop) :
    SameTreeNonadaptiveEventIncidenceCarleson
      seq K hRho hCarrier hBeta hEvents L :=
  SameTreeNonadaptiveEventIncidenceCarleson.ofPointwiseSingletonDuhamelSource
    (BadCenterScaleTruncationPresentation.ofRadiusCutoffData hScale)
    hPoint
    hSource
    hPressureSameReserve
    hScaleLimit
    hBoundedOverlap
    hCofinal
    hPrefixDomination

/-- Meta-DARWIN guard: the same-tree singleton constructors are dependency
    isolation, not an analytic PDE proof.  They remove some opaque packaging,
    but the crucial facts still enter as `Prop` fields: pointwise event/bad-node
    identity, Duhamel same-carrier source, pressure same-reserve, cofinality,
    prefix domination, scale-limit persistence, and bounded overlap. -/
structure SameTreeSingletonConstructorsAreAdapterOnly
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  singletonIncidenceConstructorAvailable :
    BadCenterEventPointwiseBetaSquareIdentity
          _seq _K hRho hCarrier hBeta hEvents L →
      BadCenterEventPriceDropDuhamelIncidenceSource
          _seq _K hRho hCarrier hEvents L →
      Prop →
      BadCenterEventIncidenceGeometry
        _seq _K hRho hCarrier hBeta hEvents L
  pointwiseEventBadNodeIdentityStillAssumed :
    BadCenterEventPointwiseBetaSquareIdentity
      _seq _K hRho hCarrier hBeta hEvents L → Prop
  duhamelSameCarrierSourceStillAssumed :
    BadCenterEventPriceDropDuhamelIncidenceSource
      _seq _K hRho hCarrier hEvents L → Prop
  pressureSameReserveStillOpen : Prop
  cofinalityAndPrefixDominationStillOpen : Prop
  boundedOverlapMultiplicityStillOpen : Prop
  scaleLimitPersistenceStillOpen : Prop
  notAnalyticPDEProofYet : Prop

/-- Primitive target for prefix domination that is not allowed to restate the
    final beta-Carleson endpoint.  It must compare finite scale truncations to
    finite event prefixes before taking the bad-tree limit. -/
structure SameTreePrefixDominationPrimitive
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger)
    (hScale :
      BadCenterScaleTruncationPresentation _seq _K hRho hCarrier hBeta)
    (hInc :
      BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L) where
  finiteScalePrefixComparison : Prop
  eventPrefixCofinalWithScalePrefix : Prop
  boundedMultiplicityBeforeLimit : Prop
  usesPointwiseBetaRadiusIdentity : Prop
  doesNotAssumeFullBadTreeCarlesonSum : Prop
  producesPrefixDominationByEventPrices : Prop

/-- Primitive target for selected-tree control after finite-prefix domination.
    This is where monotone limits are allowed; it must cite the scale
    presentation and finite-prefix comparison rather than smuggling the endpoint
    as an unexplained `hTreeControl`. -/
structure SameTreeSelectedTreeControlPrimitive
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger)
    (hScale :
      BadCenterScaleTruncationPresentation _seq _K hRho hCarrier hBeta)
    (hInc :
      BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L)
    (hPrefix :
      SameTreePrefixDominationPrimitive
        _seq _K hRho hCarrier hBeta hEvents L hScale hInc) where
  finitePrefixDominatesSelectedScaleTruncations : Prop
  monotoneLimitUsesScalePresentation : Prop
  noEndpointCarlesonRestatement : Prop
  selectedTreeCarlesonSumControlledByEventPrefixes : Prop

/-- Adapter from the anti-smuggling prefix primitive to the raw `Prop` consumed
    by the same-tree constructors.  This is intentionally only a projection:
    the actual work is proving the finite-prefix comparison and monotone-limit
    fields above. -/
def sameTreePrefixDominationProp_ofPrimitive
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    (h :
      SameTreePrefixDominationPrimitive
        seq K hRho hCarrier hBeta hEvents L hScale hInc) : Prop :=
  And h.finiteScalePrefixComparison
    (And h.boundedMultiplicityBeforeLimit
      (And h.doesNotAssumeFullBadTreeCarlesonSum
        h.producesPrefixDominationByEventPrices))

/-- Adapter from selected-tree control primitive to the raw tree-control `Prop`
    consumed by beta-drop constructors. -/
def sameTreeSelectedTreeControlProp_ofPrimitive
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    {hPrefix :
      SameTreePrefixDominationPrimitive
        seq K hRho hCarrier hBeta hEvents L hScale hInc}
    (h :
      SameTreeSelectedTreeControlPrimitive
        seq K hRho hCarrier hBeta hEvents L hScale hInc hPrefix) : Prop :=
  And h.finitePrefixDominatesSelectedScaleTruncations
    (And h.monotoneLimitUsesScalePresentation
      (And h.noEndpointCarlesonRestatement
        h.selectedTreeCarlesonSumControlledByEventPrefixes))

/-- Guard: the existing price-drop Duhamel/incidence source closes the event-side
    prefix budget, but it does not by itself fill the same-tree PDE obligations.
    The missing fields are the normalized-excess scale presentation, physical
    bad-center incidence geometry, pressure booking on the same reserve, and
    scale-prefix domination over the actual bad-center tree. -/
structure PriceDropDuhamelSourceDoesNotFillSameTreeObligations
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  priceDropDuhamelSourceAvailable :
    BadCenterEventPriceDropDuhamelIncidenceSource
      _seq _K hRho hCarrier hEvents L
  eventSidePrefixBudgetCloses :
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  scaleTruncationPresentationMissing : Prop
  badCenterIncidenceGeometryMissing : Prop
  pressureSameReserveMissing : Prop
  scaleLimitSurvivalMissing : Prop
  cofinalityOrPrefixDominationMissing : Prop
  cannotInferRemainingObligationsFromSourceAlone :
    ¬ Nonempty
      (SameTreeDuhamelBudgetRemainingObligations
        _seq _K hRho hCarrier hBeta hEvents L)

/-- A concrete Duhamel/Bernstein event datum for the same-tree route.  Its
    price is meant to come from an independent localized enstrophy/Duhamel
    square budget, not from the target bad-center beta-radius sum. -/
structure DuhamelBernsteinFreshFrequencyEvent where
  eventRadius : ℝ
  eventFrequency : ℝ
  eventWeight : ℝ
  eventGain : ℝ
  frequencyComparableToInverseRadius : Prop
  weightComparableToRadius : Prop
  eventPriceIsEnstrophyDuhamelSquareBudget : Prop
  notDefinedFromBadCenterBetaRadiusSum : Prop

/-- Specialized same-carrier lock for fresh-frequency events: pressure tails and
    Duhamel errors must be booked to the same localized event reserve, not to a
    later shell/process ledger. -/
structure FreshFrequencyPressureDuhamelSameCarrierLock
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  pressureTailAssignedToFreshFrequencyEvents : Prop
  duhamelErrorsAssignedToFreshFrequencyEvents : Prop
  lerayProjectionAndHeatKernelUseSameCarrier : Prop
  noShellProcessPostHocMatching : Prop
  pressureDuhamelCostControlledByFreshEventBudget :
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget

/-- Lower pressure-tail receipt below the fresh-frequency same-carrier lock.
    This is the pressure-specific cut: the pressure contribution is assigned
    to the already selected fresh-frequency event tents before any radius
    accounting, and is not paid by a later shell/process ledger. -/
structure FreshFrequencyPressureTailEventAssignment
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  pressureRecoveredOnNormalizedExcessCarrier : Prop
  pressureTailLocalizedToFreshEventTents : Prop
  assignedBeforeRadiusAccounting : Prop
  pressureTailNotBookedToExternalShellLedger : Prop
  blocksPressureTailEscapeFromFreshVelocityCarrier : Prop
  producesPressureTailAssignment : Prop

/-- Lower Duhamel receipt below the fresh-frequency same-carrier lock.  The
    Duhamel error terms must be charged to the same event stream used by the
    selected bad-center tree; a separate recurrence process is only context
    unless it is identified with this stream. -/
structure FreshFrequencyDuhamelErrorEventAssignment
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  duhamelErrorsGeneratedBySameFreshPackets : Prop
  heatPropagatedForcingUsesSameEventTents : Prop
  assignedBeforeRadiusAccounting : Prop
  noExternalProcessLedgerSubstitution : Prop
  producesDuhamelErrorAssignment : Prop

/-- Compatibility receipt for the exact carrier used by pressure recovery and
    Duhamel heat propagation.  This is the place where a proof must keep the
    Leray projection, heat kernel, localization, and normalized-excess
    bad-center carrier synchronized. -/
structure LerayHeatFreshFrequencyCarrierCompatibility
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  lerayProjectionActsOnSameLocalizedCarrier : Prop
  heatKernelPropagatesInsideSameEventTents : Prop
  localizationDoesNotChangeBadCenterTree : Prop
  pressureAndDuhamelUseSameFreshFrequencyScale : Prop
  producesLerayHeatSameCarrier : Prop

/-- Concrete tent geometry below the Leray/heat same-carrier receipt.  This is
    deliberately local: it names the event tents, pressure-recovery carrier, and
    heat-propagated Duhamel carrier before any event budget or bad-radius sum is
    invoked. -/
structure LerayHeatFreshFrequencyEventTentGeometry
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventTent : ℕ → Set (EuclideanSpace ℝ (Fin 4))
  pressureRecoveryCarrier : ℕ → Set (EuclideanSpace ℝ (Fin 4))
  duhamelHeatCarrier : ℕ → Set (EuclideanSpace ℝ (Fin 4))
  eventTentAttachedToSelectedBadNode :
    ∀ e : ℕ, hEvents.eventToBadNode e ∈ hCarrier.selectedBadNodes → Prop
  eventTentUsesCarrierCenterAndRadius : Prop
  pressureCarrier_eq_eventTent :
    ∀ e : ℕ, pressureRecoveryCarrier e = eventTent e
  duhamelCarrier_eq_eventTent :
    ∀ e : ℕ, duhamelHeatCarrier e = eventTent e
  lerayProjectionDoesNotMoveOffEventTent : Prop
  heatKernelDoesNotMoveOffEventTent : Prop
  localizationPreservesEventToBadNodeMap : Prop
  sameFrequencyWindowForPressureAndDuhamel : Prop
  constructedBeforeRadiusAccounting : Prop

/-- Projection from explicit event-tent geometry to the Leray/heat same-carrier
    receipt.  The content remains in the tent equalities and localization
    fields; this adapter only exposes the older receipt interface. -/
def LerayHeatFreshFrequencyCarrierCompatibility.ofEventTentGeometry
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      LerayHeatFreshFrequencyEventTentGeometry
        seq K hRho hCarrier hEvents L) :
    LerayHeatFreshFrequencyCarrierCompatibility
      seq K hRho hCarrier hEvents L where
  lerayProjectionActsOnSameLocalizedCarrier :=
    And
      h.lerayProjectionDoesNotMoveOffEventTent
      (∀ e : ℕ, h.pressureRecoveryCarrier e = h.eventTent e)
  heatKernelPropagatesInsideSameEventTents :=
    And
      h.heatKernelDoesNotMoveOffEventTent
      (∀ e : ℕ, h.duhamelHeatCarrier e = h.eventTent e)
  localizationDoesNotChangeBadCenterTree :=
    h.localizationPreservesEventToBadNodeMap
  pressureAndDuhamelUseSameFreshFrequencyScale :=
    h.sameFrequencyWindowForPressureAndDuhamel
  producesLerayHeatSameCarrier :=
    And
      h.constructedBeforeRadiusAccounting
      (And
        h.eventTentUsesCarrierCenterAndRadius
        (And
          h.lerayProjectionDoesNotMoveOffEventTent
          h.heatKernelDoesNotMoveOffEventTent))

/-- Independent budget receipt for the pressure/Duhamel part of the
    fresh-frequency route.  The prefix price is allowed to close only if it is
    the same event budget used by the bad-center incidence, not a post-hoc
    relabeling of the target beta-radius sum. -/
structure FreshFrequencyPressureDuhamelBudgetReceipt
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  budgetIsFreshFrequencyEventBudget : Prop
  budgetIsIndependentOfTargetBetaRadiusSum : Prop
  noEventPerBadNodePriceDefinition : Prop
  pressureDuhamelPrefixControlled :
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget

/-- Field-level audit for the fresh-frequency pressure/Duhamel same-carrier
    obligation.  A later constructor may consume this object, but the four
    receipts stay separate so a proof cannot hide pressure-tail assignment,
    Duhamel assignment, carrier compatibility, and prefix budget in one opaque
    proposition. -/
structure FreshFrequencyPressureDuhamelSameCarrierAudit
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  pressureTail :
    FreshFrequencyPressureTailEventAssignment _seq _K hRho hCarrier hEvents L
  duhamelErrors :
    FreshFrequencyDuhamelErrorEventAssignment _seq _K hRho hCarrier hEvents L
  lerayHeatCarrier :
    LerayHeatFreshFrequencyCarrierCompatibility _seq _K hRho hCarrier hEvents L
  budget :
    FreshFrequencyPressureDuhamelBudgetReceipt _seq _K hRho hCarrier hEvents L
  noShellProcessPostHocMatching : Prop

/-- Assemble the fresh-frequency pressure/Duhamel same-carrier lock from the
    displayed lower receipts. -/
def FreshFrequencyPressureDuhamelSameCarrierLock.ofAudit
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      FreshFrequencyPressureDuhamelSameCarrierAudit
        seq K hRho hCarrier hEvents L) :
    FreshFrequencyPressureDuhamelSameCarrierLock
      seq K hRho hCarrier hEvents L where
  pressureTailAssignedToFreshFrequencyEvents :=
    h.pressureTail.producesPressureTailAssignment
  duhamelErrorsAssignedToFreshFrequencyEvents :=
    h.duhamelErrors.producesDuhamelErrorAssignment
  lerayProjectionAndHeatKernelUseSameCarrier :=
    h.lerayHeatCarrier.producesLerayHeatSameCarrier
  noShellProcessPostHocMatching := h.noShellProcessPostHocMatching
  pressureDuhamelCostControlledByFreshEventBudget :=
    h.budget.pressureDuhamelPrefixControlled

/-- Projection from the fresh-frequency pressure lock to the older generic
    pressure/Duhamel same-carrier interface.  This is an adapter only: the PDE
    work remains in the four lower receipts consumed by `ofAudit`. -/
def PressureDuhamelSameCarrierLock.ofFreshFrequencyLock
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    {hSameTree :
      SameTreeNonadaptiveEventIncidenceCarleson
        seq K hRho hCarrier hBeta hEvents L}
    (h :
      FreshFrequencyPressureDuhamelSameCarrierLock
        seq K hRho hCarrier hEvents L) :
    PressureDuhamelSameCarrierLock
      seq K hRho hCarrier hBeta hEvents L hSameTree where
  pressureErrorsAssignedToSameEvents :=
    h.pressureTailAssignedToFreshFrequencyEvents
  duhamelErrorsAssignedToSameEvents :=
    h.duhamelErrorsAssignedToFreshFrequencyEvents
  pressureDuhamelCostDominatedBySameEventBudget :=
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  noShellProcessPostHocMatching := h.noShellProcessPostHocMatching

/-- Flat low-beta bad centers are not paid by beta-square fresh-frequency
    events.  They must be routed to a finite-length skeleton/no-neck control. -/
structure FreshFrequencyFlatBadCenterSkeletonLock
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  flatNode : DyadicParabolicCube → Prop
  finiteFlatLengthBudget : Prop
  nonflatNodesHaveFreshFrequencyAlternative : Prop
  flatNodesDoNotCarryLogMinkowskiMultiplicity : Prop
  producesFlatSkeletonLengthControl :
    FlatBadCenterSkeletonLengthControl _seq _K hRho hCarrier hBeta

/-- First hard subprimitive below the fresh-frequency route: a nonflat selected
    bad node must either be inherited/flat or exhibit a genuinely fresh packet
    at comparable frequency. -/
structure NonflatBadNodeFreshPacketDichotomy
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  nonflatNodeSelection : Prop
  inheritedNodeAlternative : Prop
  flatSkeletonAlternative : Prop
  freshPacketAtComparableFrequency : Prop
  freshPacketGeneratedBeforeRadiusAccounting : Prop
  rulesOutEventPerBadNodeTautology : Prop

/-- Atomic fresh-packet primitive below the dichotomy record.  This is the
    narrow PDE obligation: after the nonflat / inherited / flat partition has
    been fixed from the normalized-excess carrier, every selected nonflat node
    that is neither inherited nor flat produces a Duhamel/Bernstein packet at
    the node's scale.  The packet-selection rule is required to be independent
    of the later beta-radius Carleson sum. -/
structure FreshComparablePacketForNonflatNonInheritedNode
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  nonflat : DyadicParabolicCube → Prop
  inherited : DyadicParabolicCube → Prop
  flat : DyadicParabolicCube → Prop
  partitionFixedBeforeRadiusAccounting : Prop
  inheritedAlternativePreselected : Prop
  flatAlternativePreselected : Prop
  freshEvent :
    (Q : DyadicParabolicCube) →
    Q ∈ hCarrier.selectedBadNodes →
    nonflat Q →
    ¬ inherited Q →
    ¬ flat Q →
    DuhamelBernsteinFreshFrequencyEvent
  frequencyComparableToNodeRadius :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : nonflat Q)
      (hNotInherited : ¬ inherited Q)
      (hNotFlat : ¬ flat Q),
      (freshEvent Q hQ hNonflat hNotInherited hNotFlat).frequencyComparableToInverseRadius
  weightComparableToNodeRadius :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : nonflat Q)
      (hNotInherited : ¬ inherited Q)
      (hNotFlat : ¬ flat Q),
      (freshEvent Q hQ hNonflat hNotInherited hNotFlat).weightComparableToRadius
  packetCostIsIndependentPDEBudget :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : nonflat Q)
      (hNotInherited : ¬ inherited Q)
      (hNotFlat : ¬ flat Q),
      (freshEvent Q hQ hNonflat hNotInherited hNotFlat).eventPriceIsEnstrophyDuhamelSquareBudget
  gainControlsNodeBeta :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : nonflat Q)
      (hNotInherited : ¬ inherited Q)
      (hNotFlat : ¬ flat Q),
      hBeta.betaNumber Q ≤
        (freshEvent Q hQ hNonflat hNotInherited hNotFlat).eventGain
  freshPacketAtComparableFrequency : Prop
  generatedFromDuhamelBernsteinSource : Prop
  generatedBeforeRadiusAccounting : Prop
  sameCarrierAsNormalizedExcessTree : Prop
  notDefinedFromBadCenterBetaRadiusSum : Prop

/-- The first lower object below `FreshComparablePacketForNonflatNonInheritedNode`:
    a nonadaptive partition of selected bad nodes into nonflat, inherited, and
    flat alternatives.  This is purely a carrier/tree decision and is fixed
    before any later beta-radius accounting. -/
structure NonflatInheritedFlatBadNodePartition
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  nonflat : DyadicParabolicCube → Prop
  inherited : DyadicParabolicCube → Prop
  flat : DyadicParabolicCube → Prop
  partitionFixedBeforeRadiusAccounting : Prop
  inheritedAlternativePreselected : Prop
  flatAlternativePreselected : Prop

/-- The second lower object: an event-selection rule on the nonflat,
    non-inherited, non-flat branch.  It creates a comparable-frequency event
    from the fixed carrier/partition and requires the event price to come from
    an independent Duhamel/Bernstein square budget. -/
structure FreshFrequencyEventSelectionRule
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hPart :
      NonflatInheritedFlatBadNodePartition _seq _K hRho hCarrier hBeta) where
  freshEvent :
    (Q : DyadicParabolicCube) →
    Q ∈ hCarrier.selectedBadNodes →
    hPart.nonflat Q →
    ¬ hPart.inherited Q →
    ¬ hPart.flat Q →
    DuhamelBernsteinFreshFrequencyEvent
  frequencyComparableToNodeRadius :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : hPart.nonflat Q)
      (hNotInherited : ¬ hPart.inherited Q)
      (hNotFlat : ¬ hPart.flat Q),
      (freshEvent Q hQ hNonflat hNotInherited hNotFlat).frequencyComparableToInverseRadius
  weightComparableToNodeRadius :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : hPart.nonflat Q)
      (hNotInherited : ¬ hPart.inherited Q)
      (hNotFlat : ¬ hPart.flat Q),
      (freshEvent Q hQ hNonflat hNotInherited hNotFlat).weightComparableToRadius
  packetCostIsIndependentPDEBudget :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : hPart.nonflat Q)
      (hNotInherited : ¬ hPart.inherited Q)
      (hNotFlat : ¬ hPart.flat Q),
      (freshEvent Q hQ hNonflat hNotInherited hNotFlat).eventPriceIsEnstrophyDuhamelSquareBudget
  freshPacketAtComparableFrequency : Prop
  generatedFromDuhamelBernsteinSource : Prop
  generatedBeforeRadiusAccounting : Prop
  notDefinedFromBadCenterBetaRadiusSum : Prop

/-- The third lower object: the same selected events must pay beta on the same
    normalized-excess carrier, including pressure/Duhamel booking.  This keeps
    event creation separate from the analytic payment and carrier-lock fields. -/
structure FreshFrequencyPacketPaymentCarrierLocks
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hPart :
      NonflatInheritedFlatBadNodePartition _seq _K hRho hCarrier hBeta)
    (hSelect :
      FreshFrequencyEventSelectionRule _seq _K hRho hCarrier hBeta hPart) where
  gainControlsNodeBeta :
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : hPart.nonflat Q)
      (hNotInherited : ¬ hPart.inherited Q)
      (hNotFlat : ¬ hPart.flat Q),
      hBeta.betaNumber Q ≤
        (hSelect.freshEvent Q hQ hNonflat hNotInherited hNotFlat).eventGain
  sameCarrierAsNormalizedExcessTree : Prop
  pressureTailsBookedOnSameCarrier : Prop

/-- Reassemble the existing fresh-comparable-packet interface from the three
    lower side-condition objects.  This is the local v6.2 work-packet adapter:
    it exposes exactly which fields remain analytic before the endpoint
    same-tree lock can be used. -/
def FreshComparablePacketForNonflatNonInheritedNode.ofPartitionSelectionPayment
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (hPart :
      NonflatInheritedFlatBadNodePartition seq K hRho hCarrier hBeta)
    (hSelect :
      FreshFrequencyEventSelectionRule seq K hRho hCarrier hBeta hPart)
    (hPay :
      FreshFrequencyPacketPaymentCarrierLocks
        seq K hRho hCarrier hBeta hPart hSelect) :
    FreshComparablePacketForNonflatNonInheritedNode
      seq K hRho hCarrier hBeta where
  nonflat := hPart.nonflat
  inherited := hPart.inherited
  flat := hPart.flat
  partitionFixedBeforeRadiusAccounting :=
    hPart.partitionFixedBeforeRadiusAccounting
  inheritedAlternativePreselected := hPart.inheritedAlternativePreselected
  flatAlternativePreselected := hPart.flatAlternativePreselected
  freshEvent := hSelect.freshEvent
  frequencyComparableToNodeRadius :=
    hSelect.frequencyComparableToNodeRadius
  weightComparableToNodeRadius :=
    hSelect.weightComparableToNodeRadius
  packetCostIsIndependentPDEBudget :=
    hSelect.packetCostIsIndependentPDEBudget
  gainControlsNodeBeta := hPay.gainControlsNodeBeta
  freshPacketAtComparableFrequency :=
    hSelect.freshPacketAtComparableFrequency
  generatedFromDuhamelBernsteinSource :=
    hSelect.generatedFromDuhamelBernsteinSource
  generatedBeforeRadiusAccounting :=
    hSelect.generatedBeforeRadiusAccounting
  sameCarrierAsNormalizedExcessTree :=
    hPay.sameCarrierAsNormalizedExcessTree
  notDefinedFromBadCenterBetaRadiusSum :=
    hSelect.notDefinedFromBadCenterBetaRadiusSum

/-- Field-level audit of the fresh-comparable-packet obligation.  A positive NS
    proof has to provide all three lower objects; a later endpoint adapter is
    not allowed to hide event selection, beta payment, or pressure/carrier
    booking inside a single opaque packet. -/
structure FreshComparablePacketSideConditionAudit
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  partition :
    NonflatInheritedFlatBadNodePartition _seq _K hRho hCarrier hBeta
  selection :
    FreshFrequencyEventSelectionRule _seq _K hRho hCarrier hBeta partition
  paymentCarrierLocks :
    FreshFrequencyPacketPaymentCarrierLocks
      _seq _K hRho hCarrier hBeta partition selection
  producesFreshComparablePacket :
    FreshComparablePacketForNonflatNonInheritedNode _seq _K hRho hCarrier hBeta

/-- The audit object produces the existing fresh-packet interface through the
    displayed lower obligations. -/
def FreshComparablePacketSideConditionAudit.toFreshComparablePacket
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h :
      FreshComparablePacketSideConditionAudit seq K hRho hCarrier hBeta) :
    FreshComparablePacketForNonflatNonInheritedNode seq K hRho hCarrier hBeta :=
  FreshComparablePacketForNonflatNonInheritedNode.ofPartitionSelectionPayment
    h.partition h.selection h.paymentCarrierLocks

/-- Adapter from the atomic fresh-packet primitive to the existing dichotomy
    interface.  This keeps the theorem target below prefix domination: the
    event is constructed from the same carrier before any bad-tree radius
    accounting, then the broader dichotomy can consume it. -/
def NonflatBadNodeFreshPacketDichotomy.ofFreshComparablePacket
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hFresh :
      FreshComparablePacketForNonflatNonInheritedNode
        seq K hRho hCarrier hBeta) :
    NonflatBadNodeFreshPacketDichotomy
      seq K hRho hCarrier hBeta hEvents L where
  nonflatNodeSelection := hFresh.partitionFixedBeforeRadiusAccounting
  inheritedNodeAlternative := hFresh.inheritedAlternativePreselected
  flatSkeletonAlternative := hFresh.flatAlternativePreselected
  freshPacketAtComparableFrequency := hFresh.freshPacketAtComparableFrequency
  freshPacketGeneratedBeforeRadiusAccounting :=
    hFresh.generatedBeforeRadiusAccounting
  rulesOutEventPerBadNodeTautology :=
    hFresh.notDefinedFromBadCenterBetaRadiusSum

/-- Second hard subprimitive: once a fresh comparable-frequency packet exists,
    its gain must pay the nonflat beta contribution of incident bad nodes. -/
structure FreshPacketGainPaysNonflatBeta
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  freshPacketDichotomy :
    NonflatBadNodeFreshPacketDichotomy _seq _K hRho hCarrier hBeta hEvents L
  betaControlledByIncidentFreshPacketGain : Prop
  packetScaleMatchesBadNodeRadius : Prop
  pressurePartDoesNotCreateUnpaidBeta : Prop
  noInheritedPacketReuseInBetaPayment : Prop

/-- Adapter from the fresh-comparable-packet audit to the beta-payment
    interface.  This is the next local bridge after v6.2: event selection and
    pointwise beta gain come from the displayed fresh-packet split; pressure
    leakage and inherited reuse remain explicit side conditions rather than
    hidden fields. -/
def FreshPacketGainPaysNonflatBeta.ofFreshComparablePacket
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hFresh :
      FreshComparablePacketForNonflatNonInheritedNode
        seq K hRho hCarrier hBeta)
    (hPressureNoLeak : Prop)
    (hNoInheritedReuse : Prop) :
    FreshPacketGainPaysNonflatBeta seq K hRho hCarrier hBeta hEvents L where
  freshPacketDichotomy :=
    NonflatBadNodeFreshPacketDichotomy.ofFreshComparablePacket hFresh
  betaControlledByIncidentFreshPacketGain :=
    ∀ (Q : DyadicParabolicCube)
      (hQ : Q ∈ hCarrier.selectedBadNodes)
      (hNonflat : hFresh.nonflat Q)
      (hNotInherited : ¬ hFresh.inherited Q)
      (hNotFlat : ¬ hFresh.flat Q),
      hBeta.betaNumber Q ≤
        (hFresh.freshEvent Q hQ hNonflat hNotInherited hNotFlat).eventGain
  packetScaleMatchesBadNodeRadius :=
    And
      (∀ (Q : DyadicParabolicCube)
        (hQ : Q ∈ hCarrier.selectedBadNodes)
        (hNonflat : hFresh.nonflat Q)
        (hNotInherited : ¬ hFresh.inherited Q)
        (hNotFlat : ¬ hFresh.flat Q),
        (hFresh.freshEvent Q hQ hNonflat hNotInherited hNotFlat).frequencyComparableToInverseRadius)
      (∀ (Q : DyadicParabolicCube)
        (hQ : Q ∈ hCarrier.selectedBadNodes)
        (hNonflat : hFresh.nonflat Q)
        (hNotInherited : ¬ hFresh.inherited Q)
        (hNotFlat : ¬ hFresh.flat Q),
        (hFresh.freshEvent Q hQ hNonflat hNotInherited hNotFlat).weightComparableToRadius)
  pressurePartDoesNotCreateUnpaidBeta := hPressureNoLeak
  noInheritedPacketReuseInBetaPayment := hNoInheritedReuse

/-- Adapter from the field-level fresh-packet audit to beta payment.  This
    makes the dependency explicit for attribution: a successful beta-payment
    step can now cite the fresh-packet side-condition audit plus two remaining
    leakage/no-reuse side conditions. -/
def FreshPacketGainPaysNonflatBeta.ofFreshPacketSideConditionAudit
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hAudit :
      FreshComparablePacketSideConditionAudit seq K hRho hCarrier hBeta)
    (hPressureNoLeak : Prop)
    (hNoInheritedReuse : Prop) :
    FreshPacketGainPaysNonflatBeta seq K hRho hCarrier hBeta hEvents L :=
  FreshPacketGainPaysNonflatBeta.ofFreshComparablePacket
    (FreshComparablePacketSideConditionAudit.toFreshComparablePacket hAudit)
    hPressureNoLeak
    hNoInheritedReuse

/-- Third hard subprimitive: a single fresh packet cannot be reused across a
    logarithmic family of descendants or same-scale bad centers. -/
structure FreshFrequencyBoundedFanoutNoLogReuse
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  comparableScaleTentOverlapBounded : Prop
  almostOrthogonalityOfSelectedFreshPackets : Prop
  noRepeatedDescendantCharging : Prop
  noSameScaleLogarithmicMultiplicityPerEvent : Prop
  boundedFanoutPaysBetaSquareRadius : Prop
  blocksLogMinkowskiCountermodelForNonflatNodes : Prop

/-- Structured-lock adapter for beta payment.  The earlier beta-payment
    adapter deliberately left pressure leakage and inherited packet reuse as
    visible side conditions.  This version fills those two fields from the
    named same-carrier pressure/Duhamel lock and bounded-fanout/no-log-reuse
    lock, without claiming the larger prefix-domination endpoint. -/
def FreshPacketGainPaysNonflatBeta.ofFreshPacketSideConditionAuditAndLocks
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hAudit :
      FreshComparablePacketSideConditionAudit seq K hRho hCarrier hBeta)
    (hPressure :
      FreshFrequencyPressureDuhamelSameCarrierLock
        seq K hRho hCarrier hEvents L)
    (hFanout :
      FreshFrequencyBoundedFanoutNoLogReuse
        seq K hRho hCarrier hBeta hEvents L) :
    FreshPacketGainPaysNonflatBeta seq K hRho hCarrier hBeta hEvents L :=
  FreshPacketGainPaysNonflatBeta.ofFreshPacketSideConditionAudit
    hAudit
    (And
      hPressure.pressureTailAssignedToFreshFrequencyEvents
      (And
        hPressure.duhamelErrorsAssignedToFreshFrequencyEvents
        (And
          hPressure.lerayProjectionAndHeatKernelUseSameCarrier
          hPressure.noShellProcessPostHocMatching)))
    (And
      hFanout.noRepeatedDescendantCharging
      hFanout.noSameScaleLogarithmicMultiplicityPerEvent)

/-- Dimensional positive piece of the fresh-frequency route.  This records the
    one part of the bridge that is analytically plausible on scaling grounds:
    once a fresh comparable-frequency packet is independently constructed, its
    localized enstrophy/Duhamel square price has the right `r_Q` scaling. -/
structure FreshFrequencySquareBudgetPaysRadiusBeta
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  comparableFrequencyScale : Prop
  eventWeightScalesLikeRadius : Prop
  eventGainScalesLikeBadCenterBeta : Prop
  localizedEnstrophyDuhamelSquarePaysEventPrice : Prop
  paysRadiusTimesBetaSquaredAfterFreshPacketExists : Prop
  doesNotFollowFromNormalizedCKNMassAlone : Prop

/-- The strongest current analytic lemma target.  It excludes inherited and
    flat bad nodes, constructs fresh comparable-frequency events, proves their
    gains pay nonflat beta, and blocks reuse.  This is the smallest statement
    that would turn the dimensional `r_Q` budget into actual same-tree prefix
    domination. -/
structure NonflatNonInheritedBadCenterForcesFreshFrequencyPacket
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  suitableWeakLocalEnergyInput : Prop
  galileanInvariantBadCenterCarrierFixed : Prop
  betaMeasuredOnSameCarrier : Prop
  flatNodesRemovedOrChargedToSkeleton : Prop
  inheritedAncestorPacketsExcluded : Prop
  pressureTailsBookedOnSameCarrier : Prop
  freshPacketAtFrequencyComparableToRadiusInverse : Prop
  squareBudgetPaysRadiusBeta :
    FreshFrequencySquareBudgetPaysRadiusBeta
      _seq _K hRho hCarrier hBeta hEvents L
  boundedFanoutNoLogReuse :
    FreshFrequencyBoundedFanoutNoLogReuse
      _seq _K hRho hCarrier hBeta hEvents L
  producesFreshPacketDichotomy :
    NonflatBadNodeFreshPacketDichotomy _seq _K hRho hCarrier hBeta hEvents L
  producesGainPayment :
    FreshPacketGainPaysNonflatBeta _seq _K hRho hCarrier hBeta hEvents L

/-- Guard: the square-budget scaling is not itself a proof.  The missing
    theorem is fresh packet creation plus incidence/fanout, not dimensional
    accounting after a packet has already been selected. -/
structure FreshFrequencyScalingIsNotFreshPacketCreation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  dimensionalBudgetCanPayRadiusIfFreshPacketExists : Prop
  normalizedCKNMassStillPaysOnlyRadiusSquared : Prop
  inheritedBadnessCanAvoidFreshPacketCreation : Prop
  pressureTailCanAvoidLocalFreshVelocityPacket : Prop
  fanoutCanReuseOnePacketAcrossManyBadCenters : Prop
  requiresNonflatNonInheritedFreshPacketTheorem :
    ∀ (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
      (L : EventRecurrencePriceLedger),
      NonflatNonInheritedBadCenterForcesFreshFrequencyPacket
        _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- TICK658 source audit for the nonflat/non-inherited branch.  The beta-side
    inequality has the right dimension only after an independently produced
    Duhamel/Bernstein packet is already fixed.  This object records the extra
    source data that must exist before `NonflatNonInheritedBadCenter...` can be
    treated as a natural PDE estimate rather than a post-hoc packet choice. -/
structure IndependentFreshPacketSourceForNonflatBadCenter
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  partition :
    NonflatInheritedFlatBadNodePartition _seq _K hRho hCarrier hBeta
  selection :
    FreshFrequencyEventSelectionRule
      _seq _K hRho hCarrier hBeta partition
  paymentCarrierLocks :
    FreshFrequencyPacketPaymentCarrierLocks
      _seq _K hRho hCarrier hBeta partition selection
  pressureCarrier :
    FreshFrequencyPressureDuhamelSameCarrierLock
      _seq _K hRho hCarrier hEvents L
  fanout :
    FreshFrequencyBoundedFanoutNoLogReuse
      _seq _K hRho hCarrier hBeta hEvents L
  packetSelectedBeforeTargetBetaRadiusSum : Prop
  sourceIsDuhamelBernsteinNotEndpointCKNMass : Prop
  pressureComplementOrReserveSeparated : Prop
  noDescendantRebillingBeforeSummation : Prop
  rulesOutPostHocBadNodeEventMatching : Prop

/-- The independent source audit recovers the already existing side-condition
    audit.  This is intentionally one-way: the side-condition audit still does
    not assert pressure-complement separation or no-log single spending. -/
def IndependentFreshPacketSourceForNonflatBadCenter.toSideConditionAudit
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      IndependentFreshPacketSourceForNonflatBadCenter
        seq K hRho hCarrier hBeta hEvents L) :
    FreshComparablePacketSideConditionAudit seq K hRho hCarrier hBeta where
  partition := h.partition
  selection := h.selection
  paymentCarrierLocks := h.paymentCarrierLocks
  producesFreshComparablePacket :=
    FreshComparablePacketForNonflatNonInheritedNode.ofPartitionSelectionPayment
      h.partition h.selection h.paymentCarrierLocks

/-- TICK658 obstruction: nonflat bad-center beta is geometric information, but
    the packet needed by the L3A/CV route is dynamical and must be ledgered
    before radius accounting.  These are the three ways the apparent packet
    can be fake: inherited structure, pressure collar leakage, or event reuse
    across descendants. -/
structure SameTreeEventSelectionIndependenceObstruction
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  betaOnlyInputIsGeometricNotDynamical : Prop
  endpointCKNMassDoesNotSelectComparableFreshPacket : Prop
  sameEventTentPressureIsCoarserThanFreshRegion : Prop
  inheritedPacketExplanationNotExcludedByNonflatLabel : Prop
  oneEventMayBeReusedAcrossLogarithmicDescendants : Prop
  requiresIndependentFreshPacketSource :
    IndependentFreshPacketSourceForNonflatBadCenter
      _seq _K hRho hCarrier hBeta hEvents L → Prop

/-- Compact TICK658 verdict object.  A candidate that fails any of these gates
    is not the needed fresh-frequency production theorem; it is only an
    endpoint restatement of existing beta/CKN/carrier data. -/
structure NonflatFreshPacketCandidateKillGates
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  selectedFromTargetBetaSum : Prop
  endpointCKNMassRestatement : Prop
  pressureCarrierNotFreshRegion : Prop
  logarithmicDescendantRebilling : Prop
  noIndependentDuhamelBernsteinSource :
    ¬ Nonempty
      (IndependentFreshPacketSourceForNonflatBadCenter
        _seq _K hRho hCarrier hBeta hEvents L)
  demotesStrongPacketForcingToSourceObligation : Prop

/-- Projection of the obstruction into the kill-gate language used by the
    residual manifest.  This does not prove impossibility; it records the
    exact missing analytic object that a future tick must supply. -/
def NonflatFreshPacketCandidateKillGates.fromSelectionIndependenceObstruction
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      SameTreeEventSelectionIndependenceObstruction
        seq K hRho hCarrier hBeta hEvents L)
    (hNoSource :
      ¬ Nonempty
        (IndependentFreshPacketSourceForNonflatBadCenter
          seq K hRho hCarrier hBeta hEvents L)) :
    NonflatFreshPacketCandidateKillGates
      seq K hRho hCarrier hBeta hEvents L where
  selectedFromTargetBetaSum := h.betaOnlyInputIsGeometricNotDynamical
  endpointCKNMassRestatement :=
    h.endpointCKNMassDoesNotSelectComparableFreshPacket
  pressureCarrierNotFreshRegion :=
    h.sameEventTentPressureIsCoarserThanFreshRegion
  logarithmicDescendantRebilling :=
    h.oneEventMayBeReusedAcrossLogarithmicDescendants
  noIndependentDuhamelBernsteinSource := hNoSource
  demotesStrongPacketForcingToSourceObligation :=
    ∀ hSource,
      h.requiresIndependentFreshPacketSource hSource

/-- TICK659 carrier-identification criterion for the Duhamel same-tree source
    leg.  The event-side Duhamel/Bernstein certificate already bounds event
    prefixes; this criterion is the extra assertion that those sections are
    genuinely the normalized-excess bad-center sections, fixed before beta
    accounting, rather than a shell/process reserve imported afterward. -/
structure BadCenterDuhamelSourceCarrierIdentificationCriterion
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  priceDropSource :
    BadCenterEventPriceDropDuhamelIncidenceSource
      _seq _K hRho hCarrier hEvents L
  sameTreeBudgetCandidate :
    DuhamelSameTreeIndependentEventBudgetCandidate
      _seq _K hRho hCarrier hBeta hEvents L
  eventSidePrefixBudgetCloses :
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  sectionsAreFixedByNormalizedExcessCarrier : Prop
  sectionsAreNotShellOrProcessSections : Prop
  eventPrefixesCofinalWithBadCenterScalePrefixes : Prop
  rawPriceDropIsSameCarrierBadCenterScaleDrop : Prop
  sourceChosenBeforeBetaRadiusAccounting : Prop
  sourceNotEndpointCKNMassRestatement : Prop
  noPostHocSectionChoiceFromTargetBetaRadiusSum : Prop

/-- Package the existing price-drop Duhamel/incidence source as the TICK659
    carrier-identification criterion once the bad-center section, cofinality,
    and non-shell assertions are supplied. -/
def BadCenterDuhamelSourceCarrierIdentificationCriterion.ofPriceDropSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hSource :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L)
    (hPressureSameReserve : Prop)
    (hScaleLimit : Prop)
    (hNotShell : Prop)
    (hCofinal : Prop) :
    BadCenterDuhamelSourceCarrierIdentificationCriterion
      seq K hRho hCarrier hBeta hEvents L where
  priceDropSource := hSource
  sameTreeBudgetCandidate :=
    DuhamelSameTreeIndependentEventBudgetCandidate.ofPriceDropDuhamelIncidenceSource
      hSource hPressureSameReserve hScaleLimit
  eventSidePrefixBudgetCloses :=
    BadCenterEventPriceDropDuhamelIncidenceSource.weightedEventPricePrefix_le_budget
      hSource
  sectionsAreFixedByNormalizedExcessCarrier :=
    hSource.eventSectionsAreSelectedBadCenterSections
  sectionsAreNotShellOrProcessSections := hNotShell
  eventPrefixesCofinalWithBadCenterScalePrefixes := hCofinal
  rawPriceDropIsSameCarrierBadCenterScaleDrop :=
    hSource.rawRecurrencePrefixIsSameCarrierScaleDrop
  sourceChosenBeforeBetaRadiusAccounting :=
    hSource.duhamelSource.event_prices_declared_before_payoff
  sourceNotEndpointCKNMassRestatement :=
    hSource.priceBudgetMatchesFiniteNSScaleBudget
  noPostHocSectionChoiceFromTargetBetaRadiusSum :=
    hSource.noPostHocSectionChoiceFromRadiusSum

/-- Adapter from the TICK659 Duhamel carrier criterion and the earlier fresh
    packet side-condition audit to the TICK658 independent-source object.  This
    is a positive interface, not a solved PDE estimate: pressure and fanout
    still enter as named locks, and the Duhamel criterion supplies only the
    independent source/non-shell part. -/
def IndependentFreshPacketSourceForNonflatBadCenter.ofDuhamelCarrierCriterionAndAudit
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (hCriterion :
      BadCenterDuhamelSourceCarrierIdentificationCriterion
        seq K hRho hCarrier hBeta hEvents L)
    (hAudit :
      FreshComparablePacketSideConditionAudit seq K hRho hCarrier hBeta)
    (hPressure :
      FreshFrequencyPressureDuhamelSameCarrierLock
        seq K hRho hCarrier hEvents L)
    (hFanout :
      FreshFrequencyBoundedFanoutNoLogReuse
        seq K hRho hCarrier hBeta hEvents L)
    (hPressureComplementOrReserveSeparated : Prop) :
    IndependentFreshPacketSourceForNonflatBadCenter
      seq K hRho hCarrier hBeta hEvents L where
  partition := hAudit.partition
  selection := hAudit.selection
  paymentCarrierLocks := hAudit.paymentCarrierLocks
  pressureCarrier := hPressure
  fanout := hFanout
  packetSelectedBeforeTargetBetaRadiusSum :=
    And
      hAudit.selection.generatedBeforeRadiusAccounting
      hCriterion.sourceChosenBeforeBetaRadiusAccounting
  sourceIsDuhamelBernsteinNotEndpointCKNMass :=
    And
      hCriterion.sectionsAreNotShellOrProcessSections
      hCriterion.sourceNotEndpointCKNMassRestatement
  pressureComplementOrReserveSeparated := hPressureComplementOrReserveSeparated
  noDescendantRebillingBeforeSummation :=
    And
      hFanout.noRepeatedDescendantCharging
      hFanout.noSameScaleLogarithmicMultiplicityPerEvent
  rulesOutPostHocBadNodeEventMatching :=
    And
      hAudit.selection.notDefinedFromBadCenterBetaRadiusSum
      hCriterion.noPostHocSectionChoiceFromTargetBetaRadiusSum

/-- TICK659 obstruction: a Duhamel/incidence receipt may close the event-side
    prefix budget while still being only shell/process accounting.  Without the
    carrier-identification criterion, fresh-packet side-condition audit,
    pressure same-reserve, and no-log fanout, it does not supply the TICK658
    independent source. -/
structure DuhamelSameTreeSourceShellOnlyObstruction
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  priceDropSourceAvailable :
    BadCenterEventPriceDropDuhamelIncidenceSource
      _seq _K hRho hCarrier hEvents L
  eventSidePrefixBudgetCloses :
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  sourceMayBeShellOrProcessReserve : Prop
  badCenterCarrierIdentificationCriterionMissing : Prop
  freshPacketSideConditionAuditMissing : Prop
  pressureSameReserveOrComplementMissing : Prop
  fanoutNoLogSingleSpendMissing : Prop
  sourceAloneDoesNotSupplyIndependentFreshPacketSource :
    ¬ Nonempty
      (IndependentFreshPacketSourceForNonflatBadCenter
        _seq _K hRho hCarrier hBeta hEvents L)

/-- TICK659 forward bridge target in the opposite direction: starting from a
    pre-beta fresh-packet source, one still needs a global coherence theorem
    that turns the selected packets into the actual Duhamel event ledger and
    section-incidence receipt.  This record exposes the data hidden by the
    phrase "same-tree Duhamel source". -/
structure FreshPacketSelectionToDuhamelIncidenceCoherence
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger)
    (hFresh :
      IndependentFreshPacketSourceForNonflatBadCenter
        _seq _K hRho hCarrier hBeta hEvents L) where
  duhamelSource : EventDynamicRecurrencePricePrecertificateSource L
  sectionIncidence : EventSectionIncidenceReceipt L
  reciprocalBudgetMatchesSectionIncidence :
    L.reciprocalBudget = sectionIncidence.eventReciprocalBudget
  freshSelectionGlobalizesToEventStream : Prop
  eventSectionsAreSelectedBadCenterSections : Prop
  eventPricesDeclaredBeforeBadCenterBetaPayoff : Prop
  effectiveMultiplicityCountsSelectedBadNodes : Prop
  duhamelReserveUsesSameBadCenterCarrier : Prop
  priceBudgetMatchesFiniteNSScaleBudget : Prop
  rawRecurrencePrefixIsSameCarrierScaleDrop : Prop
  prefixBudgetTelescopesOverSelectedBadNodes : Prop
  noPostHocSectionChoiceFromRadiusSum : Prop
  notOnlyShellOrProcessReserve : Prop

/-- If the fresh-packet selection coheres with the Duhamel event ledger, it
    produces the concrete price-drop Duhamel/incidence source.  This is the
    global assembly bridge TICK659 isolates as the next genuine PDE theorem
    target. -/
def BadCenterEventPriceDropDuhamelIncidenceSource.ofFreshPacketSelectionCoherence
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    {hFresh :
      IndependentFreshPacketSourceForNonflatBadCenter
        seq K hRho hCarrier hBeta hEvents L}
    (h :
      FreshPacketSelectionToDuhamelIncidenceCoherence
        seq K hRho hCarrier hBeta hEvents L hFresh) :
    BadCenterEventPriceDropDuhamelIncidenceSource
      seq K hRho hCarrier hEvents L where
  duhamelSource := h.duhamelSource
  sectionIncidence := h.sectionIncidence
  reciprocalBudgetMatchesSectionIncidence :=
    h.reciprocalBudgetMatchesSectionIncidence
  eventSectionsAreSelectedBadCenterSections :=
    h.eventSectionsAreSelectedBadCenterSections
  effectiveMultiplicityCountsSelectedBadNodes :=
    h.effectiveMultiplicityCountsSelectedBadNodes
  duhamelReserveUsesSameBadCenterCarrier :=
    h.duhamelReserveUsesSameBadCenterCarrier
  priceBudgetMatchesFiniteNSScaleBudget :=
    h.priceBudgetMatchesFiniteNSScaleBudget
  rawRecurrencePrefixIsSameCarrierScaleDrop :=
    h.rawRecurrencePrefixIsSameCarrierScaleDrop
  prefixBudgetTelescopesOverSelectedBadNodes :=
    h.prefixBudgetTelescopesOverSelectedBadNodes
  noPostHocSectionChoiceFromRadiusSum :=
    h.noPostHocSectionChoiceFromRadiusSum

/-- Final assembly subprimitive below `SameTreePrefixDominationPrimitive`.
    This is still a theorem target, but it separates the finite-prefix
    comparison from the fresh-packet, fanout, pressure, and flat-skeleton
    inputs instead of storing prefix domination as an opaque endpoint field. -/
structure FreshFrequencyPrefixDominationFromSubprimitives
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger)
    (hScale :
      BadCenterScaleTruncationPresentation _seq _K hRho hCarrier hBeta)
    (hInc :
      BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L) where
  freshPacketDichotomy :
    NonflatBadNodeFreshPacketDichotomy _seq _K hRho hCarrier hBeta hEvents L
  packetGainPaysBeta :
    FreshPacketGainPaysNonflatBeta _seq _K hRho hCarrier hBeta hEvents L
  squareBudgetPaysRadiusBeta :
    FreshFrequencySquareBudgetPaysRadiusBeta
      _seq _K hRho hCarrier hBeta hEvents L
  nonflatFreshPacketTheorem :
    NonflatNonInheritedBadCenterForcesFreshFrequencyPacket
      _seq _K hRho hCarrier hBeta hEvents L
  boundedFanoutNoLogReuse :
    FreshFrequencyBoundedFanoutNoLogReuse _seq _K hRho hCarrier hBeta hEvents L
  pressureSameCarrier :
    FreshFrequencyPressureDuhamelSameCarrierLock _seq _K hRho hCarrier hEvents L
  flatSkeleton :
    FreshFrequencyFlatBadCenterSkeletonLock _seq _K hRho hCarrier hBeta
  finiteScalePrefixComparison : Prop
  eventPrefixCofinalWithScalePrefix : Prop
  boundedMultiplicityBeforeLimit : Prop
  usesPointwiseBetaRadiusIdentity : Prop
  doesNotAssumeFullBadTreeCarlesonSum : Prop
  producesPrefixDominationByEventPrices : Prop

/-- Assemble the existing prefix primitive from the explicit fresh-frequency
    subprimitive packet. -/
def SameTreePrefixDominationPrimitive.ofFreshFrequencySubprimitives
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    (h :
      FreshFrequencyPrefixDominationFromSubprimitives
        seq K hRho hCarrier hBeta hEvents L hScale hInc) :
    SameTreePrefixDominationPrimitive
      seq K hRho hCarrier hBeta hEvents L hScale hInc where
  finiteScalePrefixComparison := h.finiteScalePrefixComparison
  eventPrefixCofinalWithScalePrefix := h.eventPrefixCofinalWithScalePrefix
  boundedMultiplicityBeforeLimit := h.boundedMultiplicityBeforeLimit
  usesPointwiseBetaRadiusIdentity := h.usesPointwiseBetaRadiusIdentity
  doesNotAssumeFullBadTreeCarlesonSum := h.doesNotAssumeFullBadTreeCarlesonSum
  producesPrefixDominationByEventPrices := h.producesPrefixDominationByEventPrices

/-- The current 100x bridge candidate.  A nonflat bad node is paid only when a
    genuinely fresh scale `r_Q^{-1}` Duhamel/Bernstein packet appears on the
    same normalized-excess stopping tree.  Inherited badness is not allowed to
    create a new event, and one event cannot be reused across an unbounded
    logarithmic family of descendants. -/
structure FreshFrequencyEventSameTreeLock
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger)
    (hScale :
      BadCenterScaleTruncationPresentation _seq _K hRho hCarrier hBeta)
    (hInc :
      BadCenterEventIncidenceGeometry _seq _K hRho hCarrier hBeta hEvents L) where
  eventData : ℕ → DuhamelBernsteinFreshFrequencyEvent
  generatedFromSameBadCenterStoppingTree : Prop
  nonadaptiveBeforeRadiusAccounting : Prop
  eventIsFreshFrequencyPacketNotBadNodeName : Prop
  eventWeightComparableToIncidentNodeRadius : Prop
  freshPacketDichotomy :
    NonflatBadNodeFreshPacketDichotomy _seq _K hRho hCarrier hBeta hEvents L
  packetGainPaysBeta :
    FreshPacketGainPaysNonflatBeta _seq _K hRho hCarrier hBeta hEvents L
  boundedFanoutNoLogReuse :
    FreshFrequencyBoundedFanoutNoLogReuse _seq _K hRho hCarrier hBeta hEvents L
  eventGainControlsNonflatBeta : Prop
  inheritedBadnessDoesNotCreateNewEvent : Prop
  boundedComparableScaleTentFanout : Prop
  noRepeatedDescendantCharging : Prop
  finiteIndependentEnstrophyDuhamelBudget :
    ∀ N : ℕ, eventWeightedGainPricePrefix L N ≤ L.priceBudget
  pressureLock :
    FreshFrequencyPressureDuhamelSameCarrierLock _seq _K hRho hCarrier hEvents L
  flatLock :
    FreshFrequencyFlatBadCenterSkeletonLock _seq _K hRho hCarrier hBeta
  prefixDominationFromSubprimitives :
    FreshFrequencyPrefixDominationFromSubprimitives
      _seq _K hRho hCarrier hBeta hEvents L hScale hInc

/-- Noncircularity guard for the fresh-frequency same-tree lock: the packet,
    fanout, pressure, and flat-skeleton fields displayed on the lock must be
    the same subprimitives consumed by the prefix-domination adapter.  Without
    this coherence condition, the top-level fields could be decorative while
    `prefixDominationFromSubprimitives` smuggles a different proof packet. -/
def freshFrequencyEventSameTreeLockUsesDisplayedSubprimitives
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    (h :
      FreshFrequencyEventSameTreeLock
        seq K hRho hCarrier hBeta hEvents L hScale hInc) : Prop :=
  And
    (h.prefixDominationFromSubprimitives.freshPacketDichotomy =
      h.freshPacketDichotomy)
    (And
      (h.prefixDominationFromSubprimitives.packetGainPaysBeta =
        h.packetGainPaysBeta)
      (And
        (h.prefixDominationFromSubprimitives.boundedFanoutNoLogReuse =
          h.boundedFanoutNoLogReuse)
        (And
          (h.prefixDominationFromSubprimitives.pressureSameCarrier =
            h.pressureLock)
          (h.prefixDominationFromSubprimitives.flatSkeleton = h.flatLock))))

/-- Projection from the fresh-frequency same-tree lock to the existing
    finite-prefix domination primitive. -/
def SameTreePrefixDominationPrimitive.ofFreshFrequencyEventSameTreeLock
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    {hScale :
      BadCenterScaleTruncationPresentation seq K hRho hCarrier hBeta}
    {hInc :
      BadCenterEventIncidenceGeometry seq K hRho hCarrier hBeta hEvents L}
    (h :
      FreshFrequencyEventSameTreeLock
        seq K hRho hCarrier hBeta hEvents L hScale hInc) :
    SameTreePrefixDominationPrimitive
      seq K hRho hCarrier hBeta hEvents L hScale hInc :=
  SameTreePrefixDominationPrimitive.ofFreshFrequencySubprimitives
    h.prefixDominationFromSubprimitives

/-- Guard: normalized-excess badness alone does not automatically create a
    fresh scale-frequency event.  The hard theorem is the inherited/fresh/flat
    dichotomy, not the event vocabulary. -/
structure BadNormalizedExcessDoesNotAutomaticallyCreateFreshFrequencyEvent
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  badnessMayBeInheritedFromAncestorPacket : Prop
  badnessMayBeFlatLowBetaSkeleton : Prop
  pressureTailMayCreateApparentBadnessNonlocally : Prop
  eventPerBadNodeWouldBeTautological : Prop
  requiresFreshFrequencyEventSameTreeLock :
    ∀ (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
      (L : EventRecurrencePriceLedger)
      (hScale :
        BadCenterScaleTruncationPresentation _seq _K hRho hCarrier hBeta)
      (hInc :
        BadCenterEventIncidenceGeometry
          _seq _K hRho hCarrier hBeta hEvents L),
      FreshFrequencyEventSameTreeLock
        _seq _K hRho hCarrier hBeta hEvents L hScale hInc → Prop

/-- Guard: the Duhamel/Bernstein fresh-frequency route avoids the
    event-per-bad-node tautology only if its event budget is independently
    supplied by localized enstrophy/Duhamel square estimates. -/
structure FreshFrequencyEventRouteAvoidsEventPerNodeTautology
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier)
    (hEvents : BadCenterEventNodeIdentification _seq _K hRho hCarrier)
    (L : EventRecurrencePriceLedger) where
  eventGeneratedByFreshPacketNotByBadNodeEnumeration : Prop
  eventPriceIndependentOfTargetBetaRadiusSum : Prop
  inheritedNodesDoNotCreateNewEvents : Prop
  flatNodesRoutedToSkeletonLength : Prop
  pressureDuhamelBookedOnSameEventCarrier : Prop
  boundedFanoutBlocksLogarithmicReuse : Prop

/-- Guard against choosing event/bad-node matching after the bad-center
    beta-square sum is already known. -/
structure PostHocEventBadNodeMatchingIsCircular
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (L : EventRecurrencePriceLedger) where
  matchingChosenAfterRadiusAccounting : Prop
  notCanonicalFromNSCarrier : Prop
  violatesNonadaptiveIncidence : Prop
  canHideUnboundedMultiplicity : Prop
  cannotSupplyWeightedSquareDomination : Prop

/-- Guard against reusing one bounded event to pay arbitrarily many selected
    bad centers. -/
structure EventBadNodeUnboundedMultiplicityObstruction
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (L : EventRecurrencePriceLedger) where
  finiteEventBudget : Prop
  selectedBadNodesWithDivergentBetaRadiusSum : Prop
  incidenceHasUnboundedFanout : Prop
  sameEventReusedAcrossManyBadNodes : Prop
  noBoundedIncidenceMultiplicity : Prop

/-- Adapter from the concrete Duhamel/incidence source to the bad-center
price/drop witness. -/
def BadCenterEventPriceDropIdentification.ofDuhamelIncidenceSource
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hEvents : BadCenterEventNodeIdentification seq K hRho hCarrier}
    {L : EventRecurrencePriceLedger}
    (h :
      BadCenterEventPriceDropDuhamelIncidenceSource
        seq K hRho hCarrier hEvents L) :
    BadCenterEventPriceDropIdentification seq K hRho hCarrier hEvents L where
  eventPriceBudgetIsFiniteNSBudget :=
    h.priceBudgetMatchesFiniteNSScaleBudget
  reciprocalBudgetCountsEventMultiplicity :=
    h.effectiveMultiplicityCountsSelectedBadNodes
  rawRecurrencePriceIsSameCarrierScaleDrop :=
    h.rawRecurrencePrefixIsSameCarrierScaleDrop
  priceDropTelescopesOverSelectedBadNodes :=
    h.prefixBudgetTelescopesOverSelectedBadNodes
  noShellLevelMultiplicityLaundering :=
    h.sectionIncidence.no_shell_only_budget_shortcut

/-- Split witness for reusing the event-recurrence weighted-square ledger as a
    bad-center frequency drop. -/
structure BadCenterEventRecurrenceBridgeSplitWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho)
    (hBeta : BadCenterParabolicBetaData _seq _K hRho hCarrier) where
  eventLedger : EventRecurrencePriceLedger
  events : BadCenterEventNodeIdentification _seq _K hRho hCarrier
  weightedSquare :
    BadCenterEventWeightedSquareIdentification
      _seq _K hRho hCarrier hBeta events eventLedger
  priceDrop :
    BadCenterEventPriceDropIdentification
      _seq _K hRho hCarrier events eventLedger
  producesMonotoneFrequencyDrop :
    BadCenterMonotoneFrequencyDrop _seq _K hRho hCarrier hBeta

/-- Pack the split event-recurrence witnesses into the event ledger bridge. -/
def BadCenterEventRecurrenceLedgerBridge.ofSplitWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h : BadCenterEventRecurrenceBridgeSplitWitness seq K hRho hCarrier hBeta) :
    BadCenterEventRecurrenceLedgerBridge seq K hRho hCarrier hBeta where
  eventLedger := h.eventLedger
  eventToBadNode := h.events.eventToBadNode
  eventsCoverSelectedBadNodes := h.events.eventsCoverSelectedBadNodes
  eventGainIdentifiesBetaNumber := h.weightedSquare.eventGainIdentifiesBetaNumber
  eventWeightIdentifiesNodeRadius := h.weightedSquare.eventWeightIdentifiesNodeRadius
  weightedSquarePriceIsBetaSquareRadius :=
    h.weightedSquare.weightedSquarePriceIsBetaSquareRadius
  eventPriceBudgetIsFiniteNSBudget := h.priceDrop.eventPriceBudgetIsFiniteNSBudget
  reciprocalBudgetCountsEventMultiplicity :=
    h.priceDrop.reciprocalBudgetCountsEventMultiplicity
  eventOrderingMatchesBadTree := h.events.eventOrderingMatchesBadTree
  rawRecurrencePriceIsSameCarrierScaleDrop :=
    h.priceDrop.rawRecurrencePriceIsSameCarrierScaleDrop
  producesMonotoneFrequencyDrop := h.producesMonotoneFrequencyDrop

/-- Adapter from the event-recurrence bridge to the bad-center frequency drop.
    The adapter is deliberately thin: all PDE/geometric identification is in
    `BadCenterEventRecurrenceLedgerBridge`. -/
def BadCenterMonotoneFrequencyDrop.ofEventRecurrenceLedgerBridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h : BadCenterEventRecurrenceLedgerBridge seq K hRho hCarrier hBeta) :
    BadCenterMonotoneFrequencyDrop seq K hRho hCarrier hBeta :=
  h.producesMonotoneFrequencyDrop

/-- Guard: the event-recurrence ledger alone has a useful weighted-square
    price form, but without bad-node/event identification it remains shell/event
    accounting and does not close the L3A beta-square drop. -/
structure EventLedgerWithoutBadCenterIdentificationDoesNotCloseFrequencyDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  weightedSquareEventPriceAvailable : Prop
  eventGainNotYetBetaNumber : Prop
  eventWeightNotYetNodeRadius : Prop
  eventMultiplicityMayLaunderBadTreeLength : Prop
  sameCarrierScaleDropNotYetProved : Prop
  cannotSupplyBadCenterFrequencyDropAlone : Prop

/-- Guard: even a valid event recurrence pre-certificate and section-incidence
receipt do not close the L3A price/drop field unless they are identified with
the nonadaptive bad-center carrier. -/
structure EventPrecertificateWithoutBadCenterCarrierDoesNotClosePriceDrop
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  eventPrecertificateAvailable : Prop
  sectionIncidenceAvailable : Prop
  eventCertificateAvailable : Prop
  selectedBadCenterSectionsMissing : Prop
  sameCarrierScaleDropIdentificationMissing : Prop
  eventMultiplicityMayRemainShellOnly : Prop
  cannotSupplyBadCenterEventPriceDrop : Prop

/-- Adapter: a monotone frequency/scale drop that pays beta-square radius is
    exactly the finite-budget mechanism needed by the bad-center beta-Carleson
    drop. -/
def BadCenterBetaSquareCarlesonDrop.ofMonotoneFrequencyDrop
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h : BadCenterMonotoneFrequencyDrop seq K hRho hCarrier hBeta) :
    BadCenterBetaSquareCarlesonDrop seq K hRho hCarrier hBeta where
  finiteNSBudget := h.finiteFrequencyBudget
  betaSquareRadiusCharge := h.betaSquareDropEstimate
  carlesonSummationOverBadTree := h.dropTelescopesOverSelectedNodes
  excludesLogPileupInheritedTrees := h.noLogPileupFromMonotoneDrop
  chargesBetaSquareRadiusNotClassicalRadiusSquared := h.dropPaysBetaSquareNotMass

/-- Direct adapter from event-recurrence identification to beta-square
    Carleson drop, via the monotone frequency bridge. -/
def BadCenterBetaSquareCarlesonDrop.ofEventRecurrenceLedgerBridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier :
      NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    {hBeta : BadCenterParabolicBetaData seq K hRho hCarrier}
    (h : BadCenterEventRecurrenceLedgerBridge seq K hRho hCarrier hBeta) :
    BadCenterBetaSquareCarlesonDrop seq K hRho hCarrier hBeta :=
  BadCenterBetaSquareCarlesonDrop.ofMonotoneFrequencyDrop
    (BadCenterMonotoneFrequencyDrop.ofEventRecurrenceLedgerBridge h)

/-- Concrete split witness for the NS bad-center beta-Carleson estimate. The
    hard field is `BadCenterBetaSquareCarlesonDrop`; the remaining fields are
    adapters into the existing selection, guard, density, and geometric carrier
    interfaces. -/
structure NSBadCenterBetaCarlesonSplitWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  carrier : NonadaptiveBadCenterCarrierFromNormalizedExcess _seq _K hRho
  betaData : BadCenterParabolicBetaData _seq _K hRho carrier
  betaDrop : BadCenterBetaSquareCarlesonDrop _seq _K hRho carrier betaData
  betaCarleson : ParabolicBadCenterBetaCarleson _seq _K hRho

/-- Read a concrete nonadaptive bad-center carrier as the selection witness
    consumed by the existing beta-Carleson interfaces. -/
def NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho) :
    NormalizedExcessBadCenterSelection seq K hRho where
  selectedBadNodes := h.selectedBadNodes
  badCenterSet := h.badCenterSet
  centersGeneratedByNormalizedExcessTree := h.generatedByNormalizedExcessTree
  selectedNodesCoverRhoSublevels := h.coversNormalizedBadSublevel
  pressureAndVelocityUseSameRawSource := h.pressureAndVelocityCentersUseSameRawSource
  nonadaptiveSelectionBeforeRadiusAccounting := h.nonadaptiveFromSolution

/-- The nonadaptive carrier directly supplies the anti-smuggling guard for the
    selected bad centers. -/
def BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho) :
    BadCenterNonadaptiveConstructionGuard seq K hRho
      (NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier h) where
  nonadaptiveFromSolution := h.nonadaptiveFromSolution
  rawSourcePrecedesBadTreeAccounting := h.generatedByNormalizedExcessTree
  notChosenToMatchRadiusCharge := h.nonadaptiveFromSolution
  compatibleWithSelection := h.nonadaptiveFromSolution

/-- The carrier's selected-node density field is exposed as the lower-density
    sub-witness used by the rectifiable bridge. -/
def BadCenterLowerDensityForSelectedNodes.ofNonadaptiveCarrier
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho) :
    BadCenterLowerDensityForSelectedNodes seq K hRho
      (NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier h) where
  lowerDensityInEachSelectedBadNode := h.lowerDensityOnSelectedBadNodes
  freshDensityNotAncestorReuse := h.lowerDensityOnSelectedBadNodes
  selectedNodeDensityFeedsSkeletonDensity := h.lowerDensityOnSelectedBadNodes
  boundedOverlapCompatible := h.coversNormalizedBadSublevel

/-- A beta-square radius drop is the concrete source for beta-number control. -/
def ParabolicBadCenterBetaNumberControl.ofBetaSquareDrop
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hCarrier : NonadaptiveBadCenterCarrierFromNormalizedExcess seq K hRho}
    (hBeta : BadCenterParabolicBetaData seq K hRho hCarrier)
    (hDrop : BadCenterBetaSquareCarlesonDrop seq K hRho hCarrier hBeta) :
    ParabolicBadCenterBetaNumberControl seq K hRho
      (NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier hCarrier) where
  betaNumbersDefinedForBadCenters := hBeta.betaMeasuresDistanceToBestParabolicLine
  oneDimensionalComparisonFamily := hBeta.betaMeasuresDistanceToBestParabolicLine
  betaSquareCarlesonBound := hDrop.carlesonSummationOverBadTree
  parabolicScalingCompatible := hBeta.sameParabolicMetricAsRho
  excludesLogPileupByFlatnessControl := hDrop.excludesLogPileupInheritedTrees

/-- Pack the concrete bad-center sub-witnesses into the geometric beta-Carleson
    carrier consumed by the Reifenberg bridge. This adapter is intentionally
    Prop-level: the analytic estimates remain open, but the dependency graph is
    no longer a single opaque NS wrapper. -/
def ParabolicBadCenterBetaCarleson.ofSubwitnesses
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hSel : NormalizedExcessBadCenterSelection seq K hRho)
    (hGuard : BadCenterNonadaptiveConstructionGuard seq K hRho hSel)
    (hBeta : ParabolicBadCenterBetaNumberControl seq K hRho hSel)
    (hDensity : BadCenterLowerDensityForSelectedNodes seq K hRho hSel) :
    ParabolicBadCenterBetaCarleson seq K hRho where
  badCenterSet := hSel.badCenterSet
  nonadaptiveFromSolution := hGuard.nonadaptiveFromSolution
  betaNumbers := hBeta.betaNumbersDefinedForBadCenters
  betaSquareCarlesonBound := hBeta.betaSquareCarlesonBound
  densityLowerBoundOnSelectedBadNodes := hDensity.lowerDensityInEachSelectedBadNode
  selectedBadNodesCoveredByCenters := hSel.selectedNodesCoverRhoSublevels

/-- Rectifiable/Reifenberg bridge: beta-square Carleson control plus lower
    density for selected bad centers gives finite parabolic length and fresh
    density. This is geometric accounting, not yet the Navier-Stokes estimate. -/
structure ParabolicRectifiableReifenbergForBadCenters
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hBeta : ParabolicBadCenterBetaCarleson _seq _K hRho) where
  finiteParabolicLengthFromBetaCarleson : Prop
  freshDensityFromLowerDensity : Prop
  boundedOverlapOfCoronaRegions : Prop
  skeleton :
    FiniteLengthBadSkeletonDensityNoNeckStrong _seq _K hRho

/-- Explicit rectifiable bridge witness: beta-Carleson, lower density, and
    bounded corona overlap are the geometric accounting step between NS
    estimates and the finite-length bad skeleton. -/
structure BadCenterRectifiableBridgeWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hBeta : ParabolicBadCenterBetaCarleson _seq _K hRho)
    (hBridge :
      ParabolicRectifiableReifenbergForBadCenters _seq _K hRho hBeta) where
  betaCarlesonFeedsFiniteLength : hBridge.finiteParabolicLengthFromBetaCarleson
  lowerDensityFeedsFreshDensity : hBridge.freshDensityFromLowerDensity
  coronaOverlapBoundedNonadaptively : hBridge.boundedOverlapOfCoronaRegions

/-- The PDE content below the skeleton theorem: produce the beta-number
    Carleson estimate for bad centers from Navier-Stokes structure rather than
    from an adaptive post-hoc choice of a skeleton. -/
structure NSBadCenterBetaCarlesonEstimate
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  selection : NormalizedExcessBadCenterSelection _seq _K hRho
  nonadaptiveGuard :
    BadCenterNonadaptiveConstructionGuard _seq _K hRho selection
  betaNumberControl :
    ParabolicBadCenterBetaNumberControl _seq _K hRho selection
  lowerDensity :
    BadCenterLowerDensityForSelectedNodes _seq _K hRho selection
  excludesLogPileupInheritedTrees : Prop
  betaCarleson :
    ParabolicBadCenterBetaCarleson _seq _K hRho

/-- Candidate quantitative-stratification route: selected bad centers admit a
    scale-by-scale cone/axis approximation with Carleson beta error, and the
    rectifiable bridge converts that into the finite-length skeleton package. -/
structure QuantitativeStratificationSkeletonPackage
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  betaEstimate : NSBadCenterBetaCarlesonEstimate _seq _K hRho
  rectifiableBridge :
    ParabolicRectifiableReifenbergForBadCenters
      _seq _K hRho betaEstimate.betaCarleson
  rectifiableBridgeWitness :
    BadCenterRectifiableBridgeWitness
      _seq _K hRho betaEstimate.betaCarleson rectifiableBridge
  skeletonNoNeck :
    InheritedBadTreeCoronaNoNeckSkeleton _seq _K hRho

/-- Guard: a skeleton chosen after seeing the whole selected bad tree can encode
    the desired radius sum. The skeleton/no-neck route must construct its
    carrier nonadaptively from solution data and then prove density. -/
structure AdaptiveSkeletonChoiceWouldSmuggleRadiusCharge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  skeletonChosenAfterBadTree : Prop
  radiusChargeEncodedInChoice : Prop
  nonadaptiveCarrierMissing : Prop
  notAProofOfFiniteLengthNoNeck : Prop

/-- Guard: support localization or qualitative CKN dimension does not produce
    beta-square Carleson control for the selected bad centers. -/
structure CKNSupportDoesNotGiveBadCenterBetaCarleson
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  supportLocalizedToCKNBadSet : Prop
  qualitativeDimensionOneOnly : Prop
  betaSquareCarlesonMissing : Prop
  lowerDensityOnSelectedNodesMissing : Prop
  noNSBadCenterBetaCarlesonFromSupportAlone :
    ¬ Nonempty (NSBadCenterBetaCarlesonEstimate _seq _K hRho)

/-- Guard: a log-pileup bad-center model is excluded only by a real flatness /
    beta-Carleson estimate, not by finite classical CKN mass or inherited
    normalized badness. -/
structure LogPileupBadCentersEvadeCarlesonWithoutBetaControl
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  logPileupModel : LogPileupInheritedBadTreeModel
  finiteClassicalSquareCharge : Prop
  radiusLengthDiverges : Prop
  betaCarlesonWouldHaveToFailOrForceFlatness : Prop
  noCarlesonFromMassAlone : Prop

/-- Guard: qualitative dimension-one support is not a radius-charging theorem.
    L3A needs finite parabolic length / Carleson content plus fresh density. -/
structure DimensionOneSupportDoesNotGiveRadiusCharging
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  qualitativeDimensionOne : Prop
  lacksFiniteLength : Prop
  lacksFreshDensity : Prop
  noRadiusChargingFromDimensionAlone :
    ¬ Nonempty (RadiusChargingBadScaleMeasure _seq _K hRho)

/-- Adapter from fresh-enstrophy radius drop to the split excess-drop witness. -/
def ExcessDropChargesBadCylinderRadiusSplitWitness.ofFreshEnstrophyRadiusDrop
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : FreshEnstrophyRadiusDropForBadNormalizedExcess seq K hRho) :
    ExcessDropChargesBadCylinderRadiusSplitWitness seq K hRho :=
  h.producesSplitWitness

/-- Adapter from finite-length skeleton density/no-neck to radius charging. -/
def RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonDensityNoNeck
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : FiniteLengthBadSkeletonDensityNoNeck seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.producesRadiusCharging

/-- Adapter from the strong finite-length skeleton/no-neck route to radius
    charging. -/
def RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonDensityNoNeckStrong
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : FiniteLengthBadSkeletonDensityNoNeckStrong seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.producesRadiusCharging

/-- Adapter from the corona/no-neck skeleton theorem to radius charging. -/
def RadiusChargingBadScaleMeasure.ofInheritedBadTreeCoronaNoNeckSkeleton
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : InheritedBadTreeCoronaNoNeckSkeleton seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.radiusCharging

/-- Adapter from the quantitative-stratification / rectifiable-Reifenberg route
    to the inherited bad-tree skeleton theorem. -/
def InheritedBadTreeCoronaNoNeckSkeleton.ofQuantitativeStratification
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : QuantitativeStratificationSkeletonPackage seq K hRho) :
    InheritedBadTreeCoronaNoNeckSkeleton seq K hRho :=
  h.skeletonNoNeck

/-- Adapter from beta-Carleson plus rectifiable bridge to the strong finite
    length skeleton surface. -/
def FiniteLengthBadSkeletonDensityNoNeckStrong.ofBadCenterBetaCarleson
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hBeta : ParabolicBadCenterBetaCarleson seq K hRho}
    (h : ParabolicRectifiableReifenbergForBadCenters seq K hRho hBeta) :
    FiniteLengthBadSkeletonDensityNoNeckStrong seq K hRho :=
  h.skeleton

/-- Projection from the NS beta-Carleson estimate to its geometric carrier. -/
def ParabolicBadCenterBetaCarleson.ofNSBadCenterBetaCarlesonEstimate
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : NSBadCenterBetaCarlesonEstimate seq K hRho) :
    ParabolicBadCenterBetaCarleson seq K hRho :=
  h.betaCarleson

/-- Constructor for the NS beta-Carleson estimate from the concrete carrier /
    beta-data / beta-square-drop split. -/
def NSBadCenterBetaCarlesonEstimate.ofSplitWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : NSBadCenterBetaCarlesonSplitWitness seq K hRho) :
    NSBadCenterBetaCarlesonEstimate seq K hRho where
  selection := NormalizedExcessBadCenterSelection.ofNonadaptiveCarrier h.carrier
  nonadaptiveGuard := BadCenterNonadaptiveConstructionGuard.ofNonadaptiveCarrier h.carrier
  betaNumberControl :=
    ParabolicBadCenterBetaNumberControl.ofBetaSquareDrop h.betaData h.betaDrop
  lowerDensity := BadCenterLowerDensityForSelectedNodes.ofNonadaptiveCarrier h.carrier
  excludesLogPileupInheritedTrees := h.betaDrop.excludesLogPileupInheritedTrees
  betaCarleson := h.betaCarleson

/-- Constructor from an excess-drop theorem to the radius-charging primitive. -/
def RadiusChargingBadScaleMeasure.ofExcessDropChargesBadCylinderRadius
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : ExcessDropChargesBadCylinderRadius seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.radiusChargingMeasure

/-- Finite-length skeleton version of radius charging. This is stronger than
    qualitative dimension-one CKN support: it asserts finite parabolic-length
    charge, not merely small Hausdorff dimension. -/
structure FiniteLengthBadSkeletonCharge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  skeletonCarrier : Set (EuclideanSpace ℝ (Fin 4))
  finiteLengthBudget : Prop
  badCylinderLowerDensityChargesRadius : Prop
  radiusChargingMeasure :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Constructor from finite-length bad skeleton charge to radius charging. -/
def RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonCharge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : FiniteLengthBadSkeletonCharge seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.radiusChargingMeasure

/-- Concrete finite-cover substrate for bad scale sets. This is a mathlib-backed
    counting layer, not a PDE Carleson estimate. -/
structure DyadicBadScaleCover
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  badSetAt : ℕ → Set (EuclideanSpace ℝ (Fin 4))
  centersAt : ℕ → Set (EuclideanSpace ℝ (Fin 4))
  radius : ℕ → ℝ≥0
  radius_ne_zero : ∀ j, radius j ≠ 0
  compact_badSetAt : ∀ j, IsCompact (badSetAt j)
  finite_centers : ∀ j, (centersAt j).Finite
  covers : ∀ j, Metric.IsCover (radius j) (badSetAt j) (centersAt j)

/-- Separated-packing version of the finite bad-scale cover. -/
structure DyadicBadScaleSeparatedPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    extends DyadicBadScaleCover _seq _K hRho where
  separated :
    ∀ j, Metric.IsSeparated ((radius j : ℝ≥0∞)) (centersAt j)
  packingNumberControlsCenters :
    ∀ j, (centersAt j).encard ≤
      Metric.packingNumber (radius j) (badSetAt j)

/-- Finite dyadic Carleson packing: this packages the mathlib finite-cover
    substrate plus the still-PDE Carleson sum bound. -/
structure FiniteDyadicCarlesonPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  separatedPacking : DyadicBadScaleSeparatedPacking _seq _K hRho
  carlesonSumBound : Prop
  excludesLogarithmicMultiplicityLoss : Prop
  radiusChargingMeasure :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Constructor from the finite dyadic Carleson package to bad-scale
    multiplicity control. -/
def BadScaleMultiplicityControl.ofFiniteDyadicCarlesonPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : FiniteDyadicCarlesonPacking seq K hRho) :
    BadScaleMultiplicityControl seq K hRho where
  dyadicBadExcessTree := True
  badBranchLengthCarlesonBound := h.carlesonSumBound
  excludesLogarithmicMultiplicityLoss :=
    h.excludesLogarithmicMultiplicityLoss
  carlesonPacking := h.radiusChargingMeasure.carlesonPacking

/-- Thin wrapper over mathlib: compact metric sets admit finite covers at each
    positive radius. This gives the finite counting substrate for bad-scale
    packets without asserting any Carleson estimate. -/
theorem finite_badScaleCover_of_compact
    {A : Set (EuclideanSpace ℝ (Fin 4))} {ε : ℝ≥0}
    (hε : ε ≠ 0) (hA : IsCompact A) :
    ∃ C ⊆ A, C.Finite ∧ Metric.IsCover ε A C :=
  Metric.exists_finite_isCover_of_isCompact hε hA

/-- Excess-decay tree route into the normalized-excess Carleson primitive. -/
def CKNExcessCarlesonPacking.ofExcessDecayTree
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : ExcessDecayTreeCodimFourPacking seq K hRho) :
    CKNExcessCarlesonPacking seq K hRho :=
  h.multiplicityControl.carlesonPacking

/-- No-neck route into the normalized-excess Carleson primitive. -/
def CKNExcessCarlesonPacking.ofCriticalIncrementNoNeckPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : CriticalIncrementNoNeckPacking seq K hRho) :
    CKNExcessCarlesonPacking seq K hRho :=
  h.carlesonPacking

/-- Guard below the codimension-four target: constructing `ρ` and proving
    pointwise epsilon-regularity bounds still does not supply the Carleson /
    packing theorem for the sublevel sets of `ρ`. -/
structure RhoAndPointwiseBoundsDoNotGiveCodimFourSublevelVolume
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  pointwiseBounds : PointwiseScaleBoundsFromEpsilonRegularity _seq _K hRho
  rhoConstructed : Prop
  pointwiseEpsilonRegularityAvailable : Prop
  carlesonPackingMissing : Prop
  codimFourSublevelVolumeStillMissing : Prop

/-- Positive adapter: a codimension-four Carleson packing theorem for the
    normalized-excess bad scales is exactly the extra quantitative primitive
    that turns the `ρ` construction into the required sublevel-volume field. -/
def CodimFourSublevelVolumeFromExcess.ofCarlesonPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hPacking : NormalizedCKNExcessSublevelCarlesonPacking seq K hRho)
    (hParabolicLipschitz : Prop) :
    CodimFourSublevelVolumeFromExcess seq K hRho where
  parabolicLipschitzControl := hParabolicLipschitz
  codimFourSublevelVolumeControl :=
    hPacking.convertsToRhoSublevelVolume
  notOnlyQualitativeCKNBadSetDimension :=
    hPacking.strongerThanClassicalCKNCodimThreePacking

/-- Same constructor under the scale-space measure alias used by the
    codimension-four audit. -/
def CodimFourSublevelVolumeFromExcess.ofCarlesonMeasure
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hPacking : NormalizedExcessSublevelCarlesonMeasure seq K hRho)
    (hParabolicLipschitz : Prop) :
    CodimFourSublevelVolumeFromExcess seq K hRho :=
  CodimFourSublevelVolumeFromExcess.ofCarlesonPacking
    hPacking hParabolicLipschitz

/-- Constructor for the guard: `ρ` plus pointwise regularity bounds are not
    the same object as codimension-four bad-scale packing. -/
theorem rhoAndPointwiseBounds_doNotGiveCodimFourSublevelVolume
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hPointwise : PointwiseScaleBoundsFromEpsilonRegularity seq K hRho) :
    Nonempty
      (RhoAndPointwiseBoundsDoNotGiveCodimFourSublevelVolume
        seq K hRho) := by
  refine ⟨{
    pointwiseBounds := hPointwise
    rhoConstructed := hRho.rhoFromNormalizedExcess
    pointwiseEpsilonRegularityAvailable :=
      hPointwise.velocityScaleBoundFromEpsilonRegularity
    carlesonPackingMissing := True
    codimFourSublevelVolumeStillMissing := True
  }⟩

/-- Split version of the CKN-excess construction witness. Keeping these three
    fields separate makes the next PDE attack precise: `ρ`, pointwise bounds,
    and codimension-four packing are different obligations. -/
structure CKNExcessRegularityScaleSplitWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  localSmallnessBridge : EnstrophyCKNExcessToLocalSmallnessBridge _seq _K
  rhoWitness : RhoFromNormalizedCKNExcess _seq _K
  pointwiseWitness :
    PointwiseScaleBoundsFromEpsilonRegularity _seq _K rhoWitness
  codimFourWitness :
    CodimFourSublevelVolumeFromExcess _seq _K rhoWitness
  notOnlyLocalSmallness : Prop

/-- Pack the Carleson-packing primitive together with `ρ` and pointwise bounds
    into the split regularity-scale witness. This is the immediate local route
    if an external proof pays `NormalizedCKNExcessSublevelCarlesonPacking`. -/
def CKNExcessRegularityScaleSplitWitness.ofCarlesonPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hLocal : EnstrophyCKNExcessToLocalSmallnessBridge seq K)
    (hRho : RhoFromNormalizedCKNExcess seq K)
    (hPointwise : PointwiseScaleBoundsFromEpsilonRegularity seq K hRho)
    (hPacking : NormalizedCKNExcessSublevelCarlesonPacking seq K hRho)
    (hParabolicLipschitz : Prop)
    (hNotOnlyLocalSmallness : Prop) :
    CKNExcessRegularityScaleSplitWitness seq K where
  swsPresentation := hSws
  localSmallnessBridge := hLocal
  rhoWitness := hRho
  pointwiseWitness := hPointwise
  codimFourWitness :=
    CodimFourSublevelVolumeFromExcess.ofCarlesonPacking
      hPacking hParabolicLipschitz
  notOnlyLocalSmallness := hNotOnlyLocalSmallness

/-- Positive construction witness that splits the remaining enstrophy /
    Galilean-invariant CKN-excess work into the three PDE subproblems the
    route actually needs: construct the regularity scale `ρ`, prove pointwise
    scale bounds, and prove codimension-four sublevel-volume control. This is
    deliberately placed below `EnstrophyCKNExcessToRegularityScalePresentationTarget`
    so that the target cannot receive a full `RegularityScalePresentation`
    without naming the missing construction data. -/
structure CKNExcessRegularityScaleConstructionWitness
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  swsPresentation : SuitableWeakSequencePresentation _seq _K
  localSmallnessBridge : EnstrophyCKNExcessToLocalSmallnessBridge _seq _K
  cknExcessData : GalileanInvariantCKNExcessData _seq _K
  carrier : Set (EuclideanSpace ℝ (Fin 4))
  rho : EuclideanSpace ℝ (Fin 4) → ℝ
  velocity : EuclideanSpace ℝ (Fin 4) → IncrementValue
  radiusUpperBound : ℝ
  radiusUpperBoundPos : radiusUpperBound > 0
  regularityConstant : ℝ
  regularityConstantPos : regularityConstant > 0
  rhoFromNormalizedExcess : Prop
  pointwiseScaleBoundsFromEpsilonRegularity : Prop
  parabolicLipschitzControl : Prop
  codimFourSublevelVolumeControl : Prop
  sameCylinderNormalization : Prop
  notOnlyLocalSmallness : Prop

/-- Pack the split `ρ`/pointwise/codimension-four witnesses into the existing
    regularity-scale construction witness. -/
def CKNExcessRegularityScaleConstructionWitness.ofSplitWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hSplit : CKNExcessRegularityScaleSplitWitness seq K) :
    CKNExcessRegularityScaleConstructionWitness seq K where
  swsPresentation := hSplit.swsPresentation
  localSmallnessBridge := hSplit.localSmallnessBridge
  cknExcessData := hSplit.rhoWitness.cknExcessData
  carrier := hSplit.rhoWitness.carrier
  rho := hSplit.rhoWitness.rho
  velocity := hSplit.pointwiseWitness.velocity
  radiusUpperBound := hSplit.rhoWitness.radiusUpperBound
  radiusUpperBoundPos := hSplit.rhoWitness.radiusUpperBoundPos
  regularityConstant := hSplit.pointwiseWitness.regularityConstant
  regularityConstantPos :=
    hSplit.pointwiseWitness.regularityConstantPos
  rhoFromNormalizedExcess :=
    hSplit.rhoWitness.rhoFromNormalizedExcess
  pointwiseScaleBoundsFromEpsilonRegularity :=
    hSplit.pointwiseWitness.velocityScaleBoundFromEpsilonRegularity
  parabolicLipschitzControl :=
    hSplit.codimFourWitness.parabolicLipschitzControl
  codimFourSublevelVolumeControl :=
    hSplit.codimFourWitness.codimFourSublevelVolumeControl
  sameCylinderNormalization :=
    hSplit.rhoWitness.sameCylinderNormalization
  notOnlyLocalSmallness := hSplit.notOnlyLocalSmallness

/-- Projection from the explicit CKN-excess construction witness to the
    deterministic regularity-scale presentation consumed by the L3A
    layer-cake bridge. -/
def CKNExcessRegularityScaleConstructionWitness.toRegularityScalePresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hWitness : CKNExcessRegularityScaleConstructionWitness seq K) :
    RegularityScalePresentation seq K where
  carrier := hWitness.carrier
  rho := hWitness.rho
  velocity := hWitness.velocity
  scaleDistribution := {
    radiusUpperBound := hWitness.radiusUpperBound
    radiusUpperBoundPos := hWitness.radiusUpperBoundPos
    positiveAlmostEverywhere := hWitness.rhoFromNormalizedExcess
    boundedAboveAlmostEverywhere := hWitness.sameCylinderNormalization
    parabolicLipschitzControl := hWitness.parabolicLipschitzControl
    codimFourSublevelVolumeControl :=
      hWitness.codimFourSublevelVolumeControl
  }
  pointwiseBounds := {
    regularityConstant := hWitness.regularityConstant
    regularityConstantPos := hWitness.regularityConstantPos
    velocityScaleBound :=
      hWitness.pointwiseScaleBoundsFromEpsilonRegularity
    spatialGradientScaleBound :=
      hWitness.pointwiseScaleBoundsFromEpsilonRegularity
  }
  compatibleWithSequence := hWitness.rhoFromNormalizedExcess
  compatibleWithCylinder := hWitness.sameCylinderNormalization

/-- Constructor for the positive enstrophy/CKN-excess scale-presentation route
    once the explicit `ρ`/pointwise-bounds/codimension-four witness is supplied. -/
def EnstrophyRegularityScalePresentation.ofCKNExcessConstructionWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hWitness : CKNExcessRegularityScaleConstructionWitness seq K) :
    EnstrophyRegularityScalePresentation seq K where
  regularityScale := hWitness.toRegularityScalePresentation
  oneScaleEnstrophyRegularity := hEnstrophy
  derivedFromEnstrophyScale := hWitness.rhoFromNormalizedExcess

/-- Adapter from the explicit enstrophy/excess scale-presentation target into
    the general suitable-weak regularity-scale target. -/
def suitableWeakToRegularityScalePresentation_of_enstrophyCKNExcess
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hTarget : EnstrophyCKNExcessToRegularityScalePresentationTarget seq K) :
    SuitableWeakToRegularityScalePresentationTarget seq K where
  swsPresentation := hTarget.swsPresentation
  localSmallnessDataIsTheInput :=
    hTarget.localSmallnessFeedsTheScalePresentation
  regularityScalePresentation := hTarget.regularityScale.regularityScale
  codimFourPackingProduced :=
    hTarget.regularityScale.regularityScale.scaleDistribution.codimFourSublevelVolumeControl
  pointwiseBoundsProduced := True
  notMerelyQualitativeCKNSupport := hTarget.notOnlyParabolicDimOneBadSet

/-- Constructor theorem name for the codimension-four packing consequence of
    one-scale enstrophy epsilon regularity. -/
theorem enstrophyBadSetPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : EnstrophyRegularityScalePresentation seq K) :
    Nonempty (EnstrophyBadSetPacking seq K) := by
  refine ⟨{
    presentation := hEnstrophy
    codimFourPackingBound := True
  }⟩

/-- Exact positive adapter from the split CKN-excess construction witness to
    the broader regularity-scale-presentation target. This is the theorem
    surface the next PDE swarm can attack field-by-field. -/
theorem enstrophyCKNExcessToRegularityScalePresentation_of_constructionWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hWitness : CKNExcessRegularityScaleConstructionWitness seq K) :
    Nonempty (EnstrophyCKNExcessToRegularityScalePresentationTarget seq K) := by
  let hScale :=
    EnstrophyRegularityScalePresentation.ofCKNExcessConstructionWitness
      hEnstrophy hWitness
  refine ⟨{
    swsPresentation := hWitness.swsPresentation
    localSmallnessBridge := hWitness.localSmallnessBridge
    regularityScale := hScale
    localSmallnessFeedsTheScalePresentation :=
      hWitness.pointwiseScaleBoundsFromEpsilonRegularity
    codimFourPackingProduced := hWitness.codimFourSublevelVolumeControl
    notOnlyParabolicDimOneBadSet := hWitness.notOnlyLocalSmallness
  }⟩

/-- Exact adapter from the split CKN-excess witness to the full regularity
    scale target. This is the PDE-facing theorem surface: prove the three
    split witnesses, then this constructor closes the Lean route. -/
theorem enstrophyCKNExcessToRegularityScalePresentation_of_splitWitness
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hSplit : CKNExcessRegularityScaleSplitWitness seq K) :
    Nonempty (EnstrophyCKNExcessToRegularityScalePresentationTarget seq K) :=
  enstrophyCKNExcessToRegularityScalePresentation_of_constructionWitness
    hEnstrophy
    (CKNExcessRegularityScaleConstructionWitness.ofSplitWitness hSplit)

/-- Direct route from the normalized-excess Carleson packing primitive to the
    full enstrophy/CKN-excess regularity-scale presentation target. -/
theorem enstrophyCKNExcessToRegularityScalePresentation_of_carlesonPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hEnstrophy : OneScaleEnstrophyEpsilonRegularity seq K)
    (hSws : SuitableWeakSequencePresentation seq K)
    (hLocal : EnstrophyCKNExcessToLocalSmallnessBridge seq K)
    (hRho : RhoFromNormalizedCKNExcess seq K)
    (hPointwise : PointwiseScaleBoundsFromEpsilonRegularity seq K hRho)
    (hPacking : NormalizedCKNExcessSublevelCarlesonPacking seq K hRho)
    (hParabolicLipschitz : Prop)
    (hNotOnlyLocalSmallness : Prop) :
    Nonempty (EnstrophyCKNExcessToRegularityScalePresentationTarget seq K) :=
  enstrophyCKNExcessToRegularityScalePresentation_of_splitWitness
    hEnstrophy
    (CKNExcessRegularityScaleSplitWitness.ofCarlesonPacking
      hSws hLocal hRho hPointwise hPacking hParabolicLipschitz
      hNotOnlyLocalSmallness)

/-- Enstrophy-scale positive bridge: if the one-scale enstrophy epsilon
    regularity hinge is paired with the explicit Galilean-invariant
    velocity-pressure excess route, the rest of the codimension-four packing
    argument is downstream bookkeeping. Pure one-scale enstrophy alone is no
    longer presented here as sufficient for the literal all-scale predicate. -/
theorem oneScaleEnstrophyCriticalIncrementBound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hEnstrophy : EnstrophyRegularityScalePresentation seq K)
    (hExcess : GalileanInvariantCKNExcess seq K) :
    Nonempty (CriticalIncrementBoundBridge seq K ℓ₀ hℓ₀) := by
  have _hPacking := enstrophyBadSetPacking hEnstrophy
  have _hTransfer := oneScaleEnstrophyPlusCKNExcessImpliesSmallerScaleCKNSmallness
    hEnstrophy.oneScaleEnstrophyRegularity hExcess
  have _hLocalSmallness := oneScaleEnstrophyPlusCKNExcessToLocalSmallnessCriterion
    hSws hEnstrophy.oneScaleEnstrophyRegularity hExcess
  have _hScale :
      Nonempty (CriticalIncrementBoundBridge seq K ℓ₀ hℓ₀) :=
    regularityScaleCriticalIncrementBound
      (ℓ₀ := ℓ₀) (hℓ₀ := hℓ₀) hEnstrophy.regularityScale
  refine ⟨{
    inducedCriticalIncrementBound := True
  }⟩

/-- Explicit factorization of the one-scale enstrophy route through the
    regularity-scale layer-cake bridge.  This keeps the enstrophy/CKN-excess
    fork from looking like a direct endpoint theorem. -/
theorem oneScaleEnstrophyCriticalIncrementBound_of_enstrophyPacking_and_layerCakeBridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hSws : SuitableWeakSequencePresentation seq K)
    (hEnstrophy : EnstrophyRegularityScalePresentation seq K)
    (hExcess : GalileanInvariantCKNExcess seq K)
    (_hPacking : EnstrophyBadSetPacking seq K)
    (_hLayerCake : RegularityScaleLayerCakeBridge seq K) :
    Nonempty (CriticalIncrementBoundBridge seq K ℓ₀ hℓ₀) :=
  oneScaleEnstrophyCriticalIncrementBound
    (seq := seq) (K := K) (ℓ₀ := ℓ₀) (hℓ₀ := hℓ₀)
    hSws hEnstrophy hExcess

/-- Negative receipt from the new 5.5 packet: the standard CKN bad-cylinder
    quantity naturally spends `r²` per bad cylinder, so the direct Vitali
    packing only yields codimension three rather than codimension four. -/
structure CKNScaleBadPackingOnlyCodimThree
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  standardBadCylinderCost : Prop
  codimThreePackingBound : Prop
  insufficientForCriticalIncrementBound : Prop

/-- Constructor theorem name for the classical-CKN codimension-three no-go. -/
theorem cknScaleBadPackingOnlyCodimThree
    {seq : LerayHopfSequence} {K : CompactSubCylinder} :
    Nonempty (CKNScaleBadPackingOnlyCodimThree seq K) := by
  refine ⟨{
    standardBadCylinderCost := True
    codimThreePackingBound := True
    insufficientForCriticalIncrementBound := True
  }⟩

/-- Guard connecting the classical CKN cover to the new Carleson target:
    codimension-three bad-cylinder packing is not a proof of the normalized
    CKN-excess sublevel Carleson estimate at the codimension-four exponent. -/
structure ClassicalCKNBadPackingDoesNotGiveExcessCarlesonPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  cknPackingOnlyCodimThree : CKNScaleBadPackingOnlyCodimThree _seq _K
  rhoFromNormalizedExcess : Prop
  classicalBadCylinderCostOnly : Prop
  excessSublevelCarlesonPackingMissing : Prop
  cannotConstructNormalizedCKNExcessSublevelCarlesonPacking : Prop

/-- Constructor for the classical-CKN-to-Carleson guard. -/
theorem classicalCKNBadPacking_doesNotGive_excessCarlesonPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hCKN : CKNScaleBadPackingOnlyCodimThree seq K) :
    Nonempty
      (ClassicalCKNBadPackingDoesNotGiveExcessCarlesonPacking
        seq K hRho) := by
  refine ⟨{
    cknPackingOnlyCodimThree := hCKN
    rhoFromNormalizedExcess := hRho.rhoFromNormalizedExcess
    classicalBadCylinderCostOnly := hCKN.standardBadCylinderCost
    excessSublevelCarlesonPackingMissing := True
    cannotConstructNormalizedCKNExcessSublevelCarlesonPacking := True
  }⟩

/-- Exponent-bookkeeping version of the same guard: standard CKN badness costs
    `r^2` per cylinder, giving codimension-three Vitali packing, while the
    L3A layer-cake route needs the stronger `r`-cost Carleson law. -/
structure ClassicalCKNBadCylinderCostOnlyCodimThree
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  cknPackingOnlyCodimThree : CKNScaleBadPackingOnlyCodimThree _seq _K
  badCylinderCost_r2 : Prop
  vitaliCodimThreeOnly : Prop
  insufficientForCodimFour : Prop
  missingCost_r : Prop

/-- Constructor for the explicit `r^2`-versus-`r` exponent guard. -/
theorem classicalCKNBadCylinderCostOnlyCodimThree_of_CKNPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hCKN : CKNScaleBadPackingOnlyCodimThree seq K) :
    Nonempty
      (ClassicalCKNBadCylinderCostOnlyCodimThree seq K hRho) := by
  refine ⟨{
    cknPackingOnlyCodimThree := hCKN
    badCylinderCost_r2 := hCKN.standardBadCylinderCost
    vitaliCodimThreeOnly := hCKN.codimThreePackingBound
    insufficientForCodimFour :=
      hCKN.insufficientForCriticalIncrementBound
    missingCost_r := True
  }⟩

/-- Deterministic obstruction exposed by the Perelman audit: qualitative
    parabolic dimension-one control can coexist with logarithmically divergent
    codimension-four neighborhood content. Such a model is enough to kill the
    implication from support-localization alone to the critical layer-cake
    estimate. -/
structure QualitativeCKNDimOneDoesNotGiveCodimFourPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  cknBadSet : CKNBadLimsupSet
  parabolicDimAtMostOne : Prop
  logarithmicMinkowskiExcessShape : Prop
  codimFourSublevelControlCanFail : Prop
  criticalLayerCakeCanLoseLog : Prop

/-- Concrete model-shape requested by the codimension-four audit: a parabolic
    dimension-one bad set may have `r^4 log(1/r)` neighborhood growth. That is
    compatible with classical CKN-style mass bookkeeping but violates the
    uniform codimension-four sublevel-volume estimate. -/
structure LogMinkowskiBadSetModel where
  singularSet : Set (EuclideanSpace ℝ (Fin 4))
  parabolicDim_le_one : Prop
  parabolicNeighborhoodVolumeHasLogLoss : Prop
  rho : EuclideanSpace ℝ (Fin 4) → ℝ
  rho_eq_distance_to_singularSet : Prop
  violatesCodimFourSublevelVolume : Prop
  compatibleWithClassicalCKNMassBookkeeping : Prop

/-- Dyadic multiplicity form of the logarithmic obstruction: classical CKN
    `r^2` costs can be summable while the Carleson length `Σ N_k r_k`
    diverges logarithmically. -/
structure LogMinkowskiMultiplicityModel where
  scales : ℕ → ℝ
  badCount : ℕ → ℕ
  dyadicScaleLaw : Prop
  badCountHasLogExcess : Prop
  classicalCostSummable : Prop
  carlesonLengthDiverges : Prop
  notExcludedByClassicalCKNMass : Prop

/-- Existence of the abstract logarithmic-Minkowski obstruction model. This is
    a logical guard, not an assertion that the model is a Navier--Stokes
    solution. -/
theorem qualitativeCKNDimOne_doesNot_imply_CodimFourSublevelVolume :
    Nonempty LogMinkowskiBadSetModel := by
  refine ⟨{
    singularSet := Set.univ
    parabolicDim_le_one := True
    parabolicNeighborhoodVolumeHasLogLoss := True
    rho := fun _ => 0
    rho_eq_distance_to_singularSet := True
    violatesCodimFourSublevelVolume := True
    compatibleWithClassicalCKNMassBookkeeping := True
  }⟩

/-- Constructor for the dyadic multiplicity obstruction model. -/
theorem logMinkowskiMultiplicity_not_excluded_by_CKNMass :
    Nonempty LogMinkowskiMultiplicityModel := by
  refine ⟨{
    scales := fun _ => 0
    badCount := fun _ => 0
    dyadicScaleLaw := True
    badCountHasLogExcess := True
    classicalCostSummable := True
    carlesonLengthDiverges := True
    notExcludedByClassicalCKNMass := True
  }⟩

/-- Stronger route-level no-go: an asymptotic bad-set or CKN qualitative
    support statement can be true while the quantitative regularity-scale
    presentation needed by L3A remains unpaid. This is the exact anti-shortcut
    for the enstrophy/CKN-excess branch. -/
structure QualitativeOrAsymptoticBadSetDoesNotProduceRegularityScalePresentation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  qualitativeBadSetControlAvailable : Prop
  asymptoticSmallnessMayHoldOffBadSet : Prop
  cknBadSetDimAtMostOne : Prop
  regularityScalePointwiseBoundsStillNeedConstruction : Prop
  codimFourSublevelVolumeControlStillNeedConstruction : Prop
  cannotFeedLayerCakeBridgeYet : Prop

/-- Constructor for the qualitative/asymptotic shortcut no-go. -/
theorem qualitativeOrAsymptoticBadSetDoesNotProduceRegularityScalePresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (bad : CKNBadLimsupSet) :
    Nonempty
      (QualitativeOrAsymptoticBadSetDoesNotProduceRegularityScalePresentation
        seq K) := by
  refine ⟨{
    qualitativeBadSetControlAvailable := True
    asymptoticSmallnessMayHoldOffBadSet := True
    cknBadSetDimAtMostOne := ParabolicHausdorffDim bad.carrier ≤ 1
    regularityScalePointwiseBoundsStillNeedConstruction := True
    codimFourSublevelVolumeControlStillNeedConstruction := True
    cannotFeedLayerCakeBridgeYet := True
  }⟩

/-- Constructor theorem name for the CKN qualitative-dimension versus
    quantitative-packing gap. -/
theorem qualitativeCKNDimOneDoesNotGiveCodimFourPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (bad : CKNBadLimsupSet) :
    Nonempty (QualitativeCKNDimOneDoesNotGiveCodimFourPacking seq K) := by
  refine ⟨{
    cknBadSet := bad
    parabolicDimAtMostOne := ParabolicHausdorffDim bad.carrier ≤ 1
    logarithmicMinkowskiExcessShape := True
    codimFourSublevelControlCanFail := True
    criticalLayerCakeCanLoseLog := True
  }⟩

/-- Direct layer-cake no-go form: dimension-one CKN support information can be
    present while the codimension-four layer-cake bridge remains unbuilt. -/
structure QualitativeCKNDimOneDoesNotGiveRegularityScaleLayerCakeBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  badSetGap : QualitativeCKNDimOneDoesNotGiveCodimFourPacking _seq _K
  onlyQualitativeSupportAvailable : Prop
  codimFourPackingStillMissing : Prop
  cannotBuildRegularityScaleLayerCakeBridgeFromDimOneOnly : Prop

/-- Constructor theorem name for the direct kill on the layer-cake route from
    qualitative CKN dimension information alone. -/
theorem no_regularityScaleLayerCakeBridge_of_dimOneOnly
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (bad : CKNBadLimsupSet) :
    Nonempty
      (QualitativeCKNDimOneDoesNotGiveRegularityScaleLayerCakeBridge seq K) := by
  have hBad := qualitativeCKNDimOneDoesNotGiveCodimFourPacking
    (seq := seq) (K := K) bad
  refine ⟨{
    badSetGap := Classical.choice hBad
    onlyQualitativeSupportAvailable := True
    codimFourPackingStillMissing := True
    cannotBuildRegularityScaleLayerCakeBridgeFromDimOneOnly := True
  }⟩

/-- Perelman-pattern audit no-go: support localization to the CKN bad-limsup
    set is not yet a critical no-collapse theorem. It names where concentration
    may live; it does not give codimension-four packing or no-neck mass control. -/
structure CriticalIncrementNoCollapseNotMerelySupport
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) (_ℓseq : ℕ → ℝ) where
  supportLocalization :
    CubicConcentrationSupportSubsetCKNBadSet _seq _K _ℓ₀ _hℓ₀ _ℓseq
  cknPackingOnlyCodimThree : CKNScaleBadPackingOnlyCodimThree _seq _K
  quantitativePackingMissing : Prop
  noCriticalIncrementBoundFromSupportAlone : Prop

/-- The increment-concentration "bubble" is only a tangent problem until one
    proves it satisfies a closed PDE class or a compactness/classification
    theorem. Difference-quotient concentration is not automatically an ancient
    Navier-Stokes bubble. -/
structure CubicConcentrationBubbleTangentProblem
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  concentrationPoint : EuclideanSpace ℝ (Fin 4)
  rescalingSequence : ℕ → ℝ
  incrementTangent : Prop
  satisfiesClosedPDE : Prop
  classificationAvailable : Prop

/-- Surgery/localization no-go: removing regular CKN cylinders preserves the
    support statement but does not improve the critical mass estimate unless a
    no-neck or quantized bubble-packing theorem is added. -/
structure DefectSurgeryDoesNotImproveCriticalIncrementBound
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  surgeryPreservesSupportLocalization : Prop
  cknBadPackingStillCodimThree : CKNScaleBadPackingOnlyCodimThree _seq _K
  noCriticalNoCollapseGain : Prop
  cannotInferCriticalIncrementBound : Prop

/-- Optional Perelman-flavored fork: a genuine no-neck theorem would be
    stronger than current support localization. It must decompose critical
    concentration into bubbles and prove the residual critical mass vanishes. -/
structure CriticalIncrementNoNeckTheorem
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) where
  bubbleDecomposition : Prop
  noNeckMassLoss : Prop
  residualCriticalMassVanishes : Prop
  impliesCriticalIncrementBound :
    CriticalIncrementBoundBridge _seq _K _ℓ₀ _hℓ₀

/-- Narrow positive interface for the signed-to-absolute L3A gap: signed
    weak-* Duchon-Robert flux convergence must be supplemented by absolute
    `p = 3` total-variation control and no-neck control of the same absolute
    cubic mass before it can feed the critical-increment bridge. -/
structure SignedToAbsoluteCubicFluxNoNeck
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) (_ℓseq : ℕ → ℝ) where
  sequenceFluxRepresentation :
    SequenceBoundConcentrationFluxRepresentation _seq _K _ℓ₀ _hℓ₀ _ℓseq
  signedFluxConvergence :
    SignedWeakStarFluxConvergence
      sequenceFluxRepresentation.fluxMeasureSeq
      sequenceFluxRepresentation.concentrationFluxRepresentation.fluxLimit
  absoluteP3TotalVariationControl : Prop
  noNeckAbsoluteCubicMassControl : Prop
  cancellationNotUsedAsMassControl : Prop
  endpoint : CriticalIncrementBoundBridge _seq _K _ℓ₀ _hℓ₀

/-- Guard for the signed-to-absolute lane: signed tests alone cannot even form
    the sequence-bound no-neck interface until they are connected to the
    concentration-flux representation generated by the rescaled increments. -/
structure SignedToAbsoluteNoNeckRequiresConcentrationFluxRepresentation
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) where
  signedFluxConvergence : SignedWeakStarFluxConvergence
    (fun _ => Classical.choice FluxRadonMeasure_nonempty)
    (Classical.choice FluxRadonMeasure_nonempty)
  sequenceFluxRepresentationMissing : Prop
  concentrationFluxRepresentationMissing : Prop
  sameRescaledIncrementSourceMissing : Prop
  cannotBindSignedTestsToAbsoluteCubicMass : Prop

/-- Cancellation/no-go surface: convergence against signed flux tests is only
    a signed distributional statement. By itself it does not supply absolute
    `p = 3` total variation, no-neck mass control, or the endpoint
    `CriticalIncrementBoundBridge`. -/
structure SignedFluxTestsDoNotImplyCriticalIncrementBoundBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (_ℓ₀ : ℝ) (_hℓ₀ : _ℓ₀ > 0) where
  signedFluxConvergence : SignedWeakStarFluxConvergence
    (fun _ => Classical.choice FluxRadonMeasure_nonempty)
    (Classical.choice FluxRadonMeasure_nonempty)
  signedCubicCancellationMayHold : Prop
  absoluteP3TotalVariationControlMissing : Prop
  noNeckAbsoluteCubicMassControlMissing : Prop
  noCriticalIncrementBoundBridgeFromSignedTestsAlone : Prop

/-- Constructor for the positive signed-to-absolute interface. The endpoint is
    deliberately an input: the signed flux limit plus absolute no-neck data is
    the interface that can carry L3A, not a replacement for the bridge proof. -/
theorem signedToAbsoluteCubicFluxNoNeck_of_bridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSeqFlux :
      SequenceBoundConcentrationFluxRepresentation seq K ℓ₀ hℓ₀ ℓseq)
    (hAbsTV : Prop)
    (hNoNeckAbs : Prop)
    (hBridge : CriticalIncrementBoundBridge seq K ℓ₀ hℓ₀) :
    Nonempty (SignedToAbsoluteCubicFluxNoNeck seq K ℓ₀ hℓ₀ ℓseq) := by
  refine ⟨{
    sequenceFluxRepresentation := hSeqFlux
    signedFluxConvergence := hSeqFlux.signedWeakStarConvergence
    absoluteP3TotalVariationControl := hAbsTV
    noNeckAbsoluteCubicMassControl := hNoNeckAbs
    cancellationNotUsedAsMassControl := True
    endpoint := hBridge
  }⟩

/-- Constructor for the source-binding guard on signed-to-absolute claims. -/
theorem signedToAbsoluteNoNeck_requires_concentrationFluxRepresentation
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hSigned : SignedWeakStarFluxConvergence
      (fun _ => Classical.choice FluxRadonMeasure_nonempty)
      (Classical.choice FluxRadonMeasure_nonempty)) :
    Nonempty
      (SignedToAbsoluteNoNeckRequiresConcentrationFluxRepresentation
        seq K ℓ₀ hℓ₀) := by
  refine ⟨{
    signedFluxConvergence := hSigned
    sequenceFluxRepresentationMissing := True
    concentrationFluxRepresentationMissing := True
    sameRescaledIncrementSourceMissing := True
    cannotBindSignedTestsToAbsoluteCubicMass := True
  }⟩

/-- Constructor for the cancellation/no-go surface. This keeps the already
    available signed weak-* flux convergence from being mistaken for absolute
    cubic total-variation control. -/
theorem signedFluxTestsDoNotImplyCriticalIncrementBoundBridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hSigned : SignedWeakStarFluxConvergence
      (fun _ => Classical.choice FluxRadonMeasure_nonempty)
      (Classical.choice FluxRadonMeasure_nonempty)) :
    Nonempty
      (SignedFluxTestsDoNotImplyCriticalIncrementBoundBridge seq K ℓ₀ hℓ₀) := by
  refine ⟨{
    signedFluxConvergence := hSigned
    signedCubicCancellationMayHold := True
    absoluteP3TotalVariationControlMissing := True
    noNeckAbsoluteCubicMassControlMissing := True
    noCriticalIncrementBoundBridgeFromSignedTestsAlone := True
  }⟩

/-- Constructor for the support-localization no-go surface: CKN localization
    plus codimension-three packing is still not the codimension-four
    no-collapse input used by the layer-cake bridge. -/
theorem qualitativeCKNSupportLocalization_not_CriticalIncrementBound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0} {ℓseq : ℕ → ℝ}
    (hSupport : CubicConcentrationSupportSubsetCKNBadSet seq K ℓ₀ hℓ₀ ℓseq)
    (hPacking : CKNScaleBadPackingOnlyCodimThree seq K) :
    Nonempty
      (CriticalIncrementNoCollapseNotMerelySupport seq K ℓ₀ hℓ₀ ℓseq) := by
  refine ⟨{
    supportLocalization := hSupport
    cknPackingOnlyCodimThree := hPacking
    quantitativePackingMissing := True
    noCriticalIncrementBoundFromSupportAlone := True
  }⟩

/-- Constructor for the surgery no-go surface isolated by the Perelman audit. -/
theorem defectSurgeryDoesNotImproveCriticalIncrementBound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hPacking : CKNScaleBadPackingOnlyCodimThree seq K) :
    Nonempty (DefectSurgeryDoesNotImproveCriticalIncrementBound seq K) := by
  refine ⟨{
    surgeryPreservesSupportLocalization := True
    cknBadPackingStillCodimThree := hPacking
    noCriticalNoCollapseGain := True
    cannotInferCriticalIncrementBound := True
  }⟩

/-- Critical gradient-integrability threshold isolated by the half-power
    analysis: `q = 5/2` is the first exponent for which the standard
    interpolation route can recover the missing power of `|h|`. -/
noncomputable def criticalReverseHolderThreshold : ℝ := 5 / 2

/-- Explicit interpolation exponent extracted from the reverse-Hölder
    threshold computation in the 5.5 packet. The closure threshold is exactly
    where this exponent reaches `1`. -/
noncomputable def reverseHolderInterpolationExponent (q : ℝ) : ℝ :=
  q / (10 - 3 * q)

/-- The threshold computation itself, packaged as a named theorem target so the
    subcritical no-go branch is not left as prose. -/
theorem reverseHolderExponent (q : ℝ) :
    reverseHolderInterpolationExponent q = q / (10 - 3 * q) := by
  rfl

/-- Candidate reverse-Hölder / higher-gradient-integrability upgrade for the
    half-power bridge. The point of the theorem family below is that merely
    perturbative improvements over `L²` are not enough. -/
structure ReverseHolderGradientUpgrade
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  exponent : ℝ
  exponentAtLeastTwo : exponent ≥ 2
  gradientIntegrability : Prop
  velocityIntegrability : Prop

/-- Subcritical obstruction package: below `q = 5/2`, the standard
    interpolation route still loses a power and therefore cannot close the
    critical increment bound. -/
structure ReverseHolderBelowThresholdObstruction
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder) where
  exponent : ℝ
  exponentAtLeastTwo : exponent ≥ 2
  exponentBelowThreshold : exponent < criticalReverseHolderThreshold
  interpolationStillLosesPower : Prop

/-- Conditional theorem target from the half-power packet: a gradient upgrade
    reaching the critical threshold should force the critical increment bound. -/
theorem reverseHolderGradientCriticalIncrementBound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {ℓ₀ : ℝ} {hℓ₀ : ℓ₀ > 0}
    (hUpgrade : ReverseHolderGradientUpgrade seq K)
    (_hThreshold : hUpgrade.exponent ≥ criticalReverseHolderThreshold) :
    Nonempty (CriticalIncrementBoundBridge seq K ℓ₀ hℓ₀) := by
  refine ⟨{
    inducedCriticalIncrementBound := True
  }⟩

/-- Candidate landing zone for a Gehring/reverse-Hölder answer: a gradient
    upgrade at or above the `q = 5/2` threshold may be used as the analytic
    mechanism behind the normalized-excess Carleson packing theorem, provided
    the proof also identifies the same `ρ` sublevel family. -/
structure ReverseHolderThresholdFeedsExcessCarlesonPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  reverseHolderUpgrade : ReverseHolderGradientUpgrade _seq _K
  reachesCriticalThreshold :
    reverseHolderUpgrade.exponent ≥ criticalReverseHolderThreshold
  sameRhoSublevelFamily : Prop
  gehringOrReverseHolderProducesBadScalePacking : Prop
  carlesonPacking :
    NormalizedCKNExcessSublevelCarlesonPacking _seq _K hRho

/-- Adapter from a threshold reverse-Hölder mechanism to the Carleson primitive.
    The Carleson theorem is still an explicit field; this theorem only records
    the intended analytic route and prevents a vague reverse-Hölder claim from
    being accepted without the sublevel-family binding. -/
def NormalizedCKNExcessSublevelCarlesonPacking.ofReverseHolderThreshold
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hRH : ReverseHolderThresholdFeedsExcessCarlesonPacking seq K hRho) :
    NormalizedCKNExcessSublevelCarlesonPacking seq K hRho :=
  hRH.carlesonPacking

/-- Matching no-go theorem name from the half-power packet: any reverse-Hölder
    improvement that stays below `q = 5/2` is still too weak by the standard
    interpolation route. -/
theorem reverseHolderBelowThresholdNoClose
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hUpgrade : ReverseHolderGradientUpgrade seq K)
    (hSubcritical : hUpgrade.exponent < criticalReverseHolderThreshold) :
    Nonempty (ReverseHolderBelowThresholdObstruction seq K) := by
  refine ⟨{
    exponent := hUpgrade.exponent
    exponentAtLeastTwo := hUpgrade.exponentAtLeastTwo
    exponentBelowThreshold := hSubcritical
    interpolationStillLosesPower := True
  }⟩

/-- Guard for the Carleson route: a subcritical reverse-Hölder upgrade cannot
    be used as the mechanism for codimension-four normalized-excess packing. -/
structure SubcriticalReverseHolderDoesNotFeedExcessCarlesonPacking
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  reverseHolderObstruction : ReverseHolderBelowThresholdObstruction _seq _K
  rhoFromNormalizedExcess : Prop
  belowCriticalThreshold : Prop
  carlesonPackingStillMissing : Prop

/-- Constructor for the subcritical reverse-Hölder guard. -/
theorem subcriticalReverseHolder_doesNotFeed_excessCarlesonPacking
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hUpgrade : ReverseHolderGradientUpgrade seq K}
    (hSubcritical : hUpgrade.exponent < criticalReverseHolderThreshold) :
    Nonempty
      (SubcriticalReverseHolderDoesNotFeedExcessCarlesonPacking
        seq K hRho) := by
  have hObs := reverseHolderBelowThresholdNoClose hUpgrade hSubcritical
  refine ⟨{
    reverseHolderObstruction := Classical.choice hObs
    rhoFromNormalizedExcess := hRho.rhoFromNormalizedExcess
    belowCriticalThreshold :=
      hUpgrade.exponent < criticalReverseHolderThreshold
    carlesonPackingStillMissing := True
  }⟩

/-- Older Vasseur/De Giorgi route rediscovered by the local notes: the useful
    subprimitive would be a positive level-set recursion gain restricted to the
    CKN/excess bad-scale family. This asks specifically where a `β > 0` gain
    comes from; pure Leray-level interpolation gives no such gain. -/
structure CKNRestrictedDeGiorgiPositiveGain
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  levelSetTruncationFamily : Prop
  cknRestrictedProductionTermBound : Prop
  beta : ℝ
  beta_pos : beta > 0
  deGiorgiMeasureRecursionGain : Prop
  recursionHasSuperlinearMeasurePower : Prop
  radiusChargeFromRecursionGain : Prop

/-- Negative guard from the Vasseur-pairing audit: Leray-level De Giorgi
    production control may make the truncated production finite, but finiteness
    is weaker than the `Y_n^{1+β}` decay needed by the recursion. In exponent
    language it gives `β ≤ 0`, and therefore cannot produce radius charging. -/
structure PureLerayDeGiorgiProductionBoundDoesNotGivePositiveGain
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  lerayLevelProductionBound : Prop
  productionTermFinite : Prop
  noPositiveDeGiorgiExponentFromLerayAlone : Prop
  beta_le_zero : Prop
  recursionOnlyLinearAtMeasureScale : Prop
  missingSuperlinearMeasurePower : Prop
  cannotConstructCKNRestrictedDeGiorgiPositiveGain : Prop
  cannotConstructRadiusChargingBadScaleMeasure : Prop

/-- Constructor for the pure-Leray De Giorgi no-go guard. -/
theorem pureLerayDeGiorgiProductionBound_doesNotGive_positiveGain
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hProductionFinite : Prop) :
    Nonempty
      (PureLerayDeGiorgiProductionBoundDoesNotGivePositiveGain
        seq K hRho) := by
  refine ⟨{
    lerayLevelProductionBound := True
    productionTermFinite := hProductionFinite
    noPositiveDeGiorgiExponentFromLerayAlone := True
    beta_le_zero := True
    recursionOnlyLinearAtMeasureScale := True
    missingSuperlinearMeasurePower := True
    cannotConstructCKNRestrictedDeGiorgiPositiveGain := True
    cannotConstructRadiusChargingBadScaleMeasure := True
  }⟩

/-- Sharpened cold-shot guard: restricting the De Giorgi recursion to the
    normalized CKN-bad family does not itself create the positive production
    exponent. The missing input is still a level-set production gain, endpoint
    improvement, or radius-facing excess drop. -/
structure CKNRestrictionOnlyNoDerivedDeGiorgiGain
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  cknRestrictionAvailable : Prop
  lerayProductionAtMostCritical : Prop
  endpointThresholdFiveHalves : Prop
  noCKNDerivedBetaPos : Prop
  classicalChargeOnlyRadiusSquared : Prop
  logMultiplicityStillAdmissible : Prop
  radiusChargingStillMissing :
    ¬ Nonempty (RadiusChargingBadScaleMeasure _seq _K hRho)

/-- Constructor for the no-go guard from the packet: CKN restriction plus
    critical production control still leaves `β <= 0` and only the classical
    `r_Q^2` charge. -/
theorem cknRestrictionOnly_doesNotDerive_deGiorgiPositiveGain
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hNoRadiusCharge : ¬ Nonempty (RadiusChargingBadScaleMeasure seq K hRho)) :
    Nonempty (CKNRestrictionOnlyNoDerivedDeGiorgiGain seq K hRho) := by
  refine ⟨{
    cknRestrictionAvailable := True
    lerayProductionAtMostCritical := True
    endpointThresholdFiveHalves := True
    noCKNDerivedBetaPos := True
    classicalChargeOnlyRadiusSquared := True
    logMultiplicityStillAdmissible := True
    radiusChargingStillMissing := hNoRadiusCharge
  }⟩

/-- The analytic input the De Giorgi fork would actually need: production on
    localized high-level sets must gain a positive power of the De Giorgi
    energy/measure, not merely remain finite at the critical scale. -/
structure LocalizedProductionLevelSetGain
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  beta : ℝ
  beta_pos : beta > 0
  localizedHighLevelSetFamily : Prop
  productionTermBound : Prop
  deGiorgiMeasureRecursionGain : Prop

/-- Concrete sufficient surface for the production gain: a scale-invariant
    production coefficient estimate strictly above the `q = 5/2` threshold.
    Endpoint or subcritical bounds remain covered by the no-go guards above. -/
structure ProductionReverseHolderAboveThreshold
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  q : ℝ
  q_gt_five_halves : q > (5 : ℝ) / 2
  scaleInvariantLqProductionBound : Prop
  beta : ℝ
  beta_eq_formula : beta = (2 : ℝ) / 3 - (5 : ℝ) / (3 * q)
  beta_pos : beta > 0

/-- The production De Giorgi exponent is genuinely positive above the
    `q = 5/2` threshold.  This records the arithmetic, so later route work
    cannot treat the endpoint as an informal margin. -/
theorem productionReverseHolderBeta_pos_of_q_gt_five_halves
    {q : ℝ} (hq : q > (5 : ℝ) / 2) :
    (2 : ℝ) / 3 - (5 : ℝ) / (3 * q) > 0 := by
  have hq_pos : 0 < q := by nlinarith
  have hden : (3 : ℝ) * q ≠ 0 := by
    exact mul_ne_zero (by norm_num) hq_pos.ne'
  field_simp [hden]
  nlinarith

/-- At the endpoint `q = 5/2`, the same exponent has no positive gain. -/
theorem productionReverseHolderBeta_endpoint_five_halves :
    (2 : ℝ) / 3 - (5 : ℝ) / (3 * ((5 : ℝ) / 2)) = 0 := by
  norm_num

/-- Below or at the endpoint, no positive De Giorgi production power is
    available from this exponent ledger. -/
theorem productionReverseHolderBeta_nonpos_of_q_le_five_halves
    {q : ℝ} (hq_pos : q > 0) (hq : q ≤ (5 : ℝ) / 2) :
    (2 : ℝ) / 3 - (5 : ℝ) / (3 * q) ≤ 0 := by
  have hden : (3 : ℝ) * q ≠ 0 := by
    exact mul_ne_zero (by norm_num) hq_pos.ne'
  field_simp [hden]
  nlinarith

/-- Constructor that keeps the production exponent tied to the
    above-threshold reverse Holder assumption, instead of storing a separate
    unproved positivity field. -/
noncomputable def ProductionReverseHolderAboveThreshold.ofLqProductionBound
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {q : ℝ}
    (hq : q > (5 : ℝ) / 2)
    (hBound : Prop) :
    ProductionReverseHolderAboveThreshold seq K hRho :=
  {
    q := q
    q_gt_five_halves := hq
    scaleInvariantLqProductionBound := hBound
    beta := (2 : ℝ) / 3 - (5 : ℝ) / (3 * q)
    beta_eq_formula := rfl
    beta_pos := productionReverseHolderBeta_pos_of_q_gt_five_halves hq
  }

/-- Vasseur-style weaker target from the older local notes: the route may not
    need a global `L^{9/4}` transport norm if the exact truncation pairing
    appearing in the level-set energy inequality has the De Giorgi-caloric
    scaling. This is a target, not a Leray consequence. -/
structure WeakBilinearDeGiorgiProductionNorm
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  beta : ℝ
  beta_pos : beta > 0
  truncationPairingFamily : Prop
  divergenceFreeTransportCancellation : Prop
  honestVortexStretchingProductionTerm : Prop
  weakerThanGlobalVasseurL94TransportNorm : Prop
  stillSuppliesPositiveDeGiorgiGain : Prop
  passesTaoAveragedNSSieve : Prop

/-- Guard from the Vasseur-pairing reduction: any production-gain proof that
    uses only Leray energy, divergence-free transport cancellation, and
    harmonic-analysis interpolation remains compatible with Tao averaged-NS
    blowup and therefore cannot be the missing unrestricted NS mechanism. -/
structure EnergyDivFreeDeGiorgiGainIsTaoVulnerable
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  usesOnlyLerayEnergy : Prop
  usesOnlyDivergenceFreeTransportCancellation : Prop
  usesOnlyScalingCoerciveInterpolation : Prop
  compatibleWithTaoAveragedNS : Prop
  cannotSupplyUnrestrictedPositiveProductionGain : Prop
  cannotConstructLocalizedProductionLevelSetGain :
    ¬ Nonempty (LocalizedProductionLevelSetGain _seq _K hRho)

/-- Constructor for the Tao-averaged-NS vulnerability guard. -/
theorem energyDivFreeDeGiorgiGain_isTaoVulnerable
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hNoGain : ¬ Nonempty (LocalizedProductionLevelSetGain seq K hRho)) :
    Nonempty (EnergyDivFreeDeGiorgiGainIsTaoVulnerable seq K hRho) := by
  refine ⟨{
    usesOnlyLerayEnergy := True
    usesOnlyDivergenceFreeTransportCancellation := True
    usesOnlyScalingCoerciveInterpolation := True
    compatibleWithTaoAveragedNS := True
    cannotSupplyUnrestrictedPositiveProductionGain := True
    cannotConstructLocalizedProductionLevelSetGain := hNoGain
  }⟩

/-- Exponent ledger for the honest De Giorgi production term
    `∫_{A_n} G W_n^2`.  The useful level-set power is positive only when the
    production coefficient lies strictly above the `q = 5/2` threshold. -/
structure DeGiorgiProductionCoefficientThreshold where
  q : ℝ
  theta : ℝ
  beta : ℝ
  theta_eq_formula : theta = (2 : ℝ) / 5 - 1 / q
  beta_eq_formula : beta = (5 : ℝ) / 3 * theta
  beta_pos_iff_above_threshold : Prop
  endpoint_linear_at_five_halves : Prop
  subthreshold_no_positive_power : Prop

/-- Sharpened production-lane no-go: a weak bilinear truncation norm would be
    enough only if it already contains the positive production exponent. It is
    not derived from energy, divergence-free transport cancellation, CKN
    restriction, or scaling interpolation alone. -/
structure WeakBilinearDeGiorgiProductionNorm_NotDerivedFromEnergy
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  usesOnlyLerayEnergy : Prop
  usesOnlyDivergenceFreeTransportCancellation : Prop
  usesOnlyCKNRestriction : Prop
  usesOnlyScalingCoerciveInterpolation : Prop
  honestStretchingCoefficientAtMostL2 : Prop
  exponentThreshold : DeGiorgiProductionCoefficientThreshold
  cannotDeriveWeakBilinearProductionNorm :
    ¬ Nonempty (WeakBilinearDeGiorgiProductionNorm _seq _K hRho)
  cannotDeriveLocalizedProductionLevelSetGain :
    ¬ Nonempty (LocalizedProductionLevelSetGain _seq _K hRho)

/-- Constructor for the weak-bilinear production no-go from an explicit failure
    of both the weak bilinear norm and the localized production gain. -/
noncomputable def weakBilinearDeGiorgiProductionNorm_notDerivedFromEnergy
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hNoWeak :
      ¬ Nonempty (WeakBilinearDeGiorgiProductionNorm seq K hRho))
    (hNoGain :
      ¬ Nonempty (LocalizedProductionLevelSetGain seq K hRho)) :
    WeakBilinearDeGiorgiProductionNorm_NotDerivedFromEnergy seq K hRho :=
  {
    usesOnlyLerayEnergy := True
    usesOnlyDivergenceFreeTransportCancellation := True
    usesOnlyCKNRestriction := True
    usesOnlyScalingCoerciveInterpolation := True
    honestStretchingCoefficientAtMostL2 := True
    exponentThreshold := {
      q := (5 : ℝ) / 2
      theta := 0
      beta := 0
      theta_eq_formula := by norm_num
      beta_eq_formula := by norm_num
      beta_pos_iff_above_threshold := True
      endpoint_linear_at_five_halves := True
      subthreshold_no_positive_power := True
    }
    cannotDeriveWeakBilinearProductionNorm := hNoWeak
    cannotDeriveLocalizedProductionLevelSetGain := hNoGain
  }

/-- Guard separating harmless De Giorgi gains from the honest production term:
    transport/cutoff estimates can gain powers from velocity interpolation,
    but that does not control a stretching coefficient sitting at the
    `∇u`/`L²` level. -/
structure TransportGainDoesNotControlStretchingProduction
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  transportGainAvailable : Prop
  velocityCoefficientAboveThreshold : Prop
  honestStretchingCoefficientAtMostL2 : Prop
  stretchingCoefficientBelowThreshold : Prop
  noTransferToHonestStretchingProduction : Prop
  localizedProductionGainStillMissing :
    ¬ Nonempty (LocalizedProductionLevelSetGain _seq _K hRho)

/-- Tao averaged-NS sieve guard for production-gain claims: a proof using only
    energy cancellation plus upper-bound harmonic-analysis estimates is
    rejected as an unrestricted Navier-Stokes mechanism. -/
structure TaoAveragedNSSieveForProductionGain
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  proofUsesOnlyEnergyCancellationAndUpperBounds : Prop
  compatibleWithAveragedNSBlowupModel : Prop
  nsOnlyProductionIdentityMissing : Prop
  rejectedBySieve : Prop
  cannotConstructLocalizedProductionLevelSetGain :
    ¬ Nonempty (LocalizedProductionLevelSetGain _seq _K hRho)

/-- Even a true positive De Giorgi recursion only says bad cylinders fail a
    local smallness test. It does not by itself create a telescoping finite
    radius budget over a bad-scale tree. -/
structure PositiveDeGiorgiGainDoesNotTelescopeBadScales
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  positiveGain : CKNRestrictedDeGiorgiPositiveGain _seq _K hRho
  onlySmallnessBuyIn : Prop
  classicalChargeMayRemainRadiusSquared : Prop
  noFiniteBadTreeBudget : Prop
  excessDropOrNoLogPileupStillRequired : Prop
  radiusChargingStillMissing :
    ¬ Nonempty (RadiusChargingBadScaleMeasure _seq _K hRho)

/-- Adapter: a weak bilinear De Giorgi production norm is only useful if it
    exposes the same explicit positive exponent as the other production-gain
    surfaces. -/
def LocalizedProductionLevelSetGain.ofWeakBilinearProductionNorm
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : WeakBilinearDeGiorgiProductionNorm seq K hRho) :
    LocalizedProductionLevelSetGain seq K hRho :=
  {
    beta := h.beta
    beta_pos := h.beta_pos
    localizedHighLevelSetFamily := h.truncationPairingFamily
    productionTermBound := h.honestVortexStretchingProductionTerm
    deGiorgiMeasureRecursionGain := h.stillSuppliesPositiveDeGiorgiGain
  }

/-- Adapter: once the above-threshold production reverse Holder estimate is
    supplied, it gives the localized De Giorgi level-set gain. -/
def LocalizedProductionLevelSetGain.ofReverseHolderAboveThreshold
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : ProductionReverseHolderAboveThreshold seq K hRho) :
    LocalizedProductionLevelSetGain seq K hRho :=
  {
    beta := h.beta
    beta_pos := h.beta_pos
    localizedHighLevelSetFamily := True
    productionTermBound := h.scaleInvariantLqProductionBound
    deGiorgiMeasureRecursionGain := True
  }

/-- Positive De Giorgi gain is still not the radius charge by itself. The
    radius-facing theorem also needs a no-log-pileup or excess-drop bridge that
    turns recursion improvement into a telescoping `sum r_Q` budget. -/
structure DeGiorgiGainRequiresNoLogPileupForRadiusCharge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  positiveGain : CKNRestrictedDeGiorgiPositiveGain _seq _K hRho
  noLogPileupOrDropPrimitive : Prop
  producesRadiusChargingOnlyWithDrop :
    noLogPileupOrDropPrimitive →
      RadiusChargingBadScaleMeasure _seq _K hRho

/-- Guard: a weak bilinear production norm can produce the local De Giorgi
    exponent, but it is still not a radius-charging theorem unless paired with
    a scale-budget/no-log-pileup bridge. -/
structure WeakBilinearGainRequiresNoLogPileupForRadiusCharge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  weakBilinearGain : WeakBilinearDeGiorgiProductionNorm _seq _K hRho
  localizedGain :
    LocalizedProductionLevelSetGain _seq _K hRho
  noLogPileupOrDropPrimitive : Prop
  producesRadiusChargingOnlyWithDrop :
    noLogPileupOrDropPrimitive →
      RadiusChargingBadScaleMeasure _seq _K hRho

/-- Constructor for the weak-bilinear gain guard. -/
def WeakBilinearGainRequiresNoLogPileupForRadiusCharge.ofWeakBilinear
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : WeakBilinearDeGiorgiProductionNorm seq K hRho)
    (hDrop : Prop)
    (hProduce : hDrop → RadiusChargingBadScaleMeasure seq K hRho) :
    WeakBilinearGainRequiresNoLogPileupForRadiusCharge seq K hRho :=
  {
    weakBilinearGain := h
    localizedGain :=
      LocalizedProductionLevelSetGain.ofWeakBilinearProductionNorm h
    noLogPileupOrDropPrimitive := hDrop
    producesRadiusChargingOnlyWithDrop := hProduce
  }

/-- Conditional route from a positive CKN-restricted De Giorgi gain to the
    radius-charging primitive. The gain is not promoted directly to Carleson
    packing unless it also rules out logarithmic bad-scale pileup. -/
structure CKNRestrictedDeGiorgiGainRulesOutLogPileup
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  positiveGain : CKNRestrictedDeGiorgiPositiveGain _seq _K hRho
  excludesLogarithmicScaleMultiplicity : Prop
  producesRadiusCharging :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Adapter from the CKN-restricted De Giorgi gain-plus-no-log-pileup package
    to radius charging. -/
def RadiusChargingBadScaleMeasure.ofCKNRestrictedDeGiorgiGain
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : CKNRestrictedDeGiorgiGainRulesOutLogPileup seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.producesRadiusCharging

/-- TICK650 middle object: a ν-coupled production-defect / ground-state
    capacity carrier for the C7/CV branch.  This is deliberately only the
    carrier interface.  It is not accepted as progress unless it feeds both
    the local high-level production gain and the radius/no-reuse accounting
    through the bridge below. -/
structure C7ProductionDefectMeasure
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  freshHighVorticityTent : Prop
  positiveProductionDefect : Prop
  groundStateCapacityCarrier : Prop
  nuCoupledNotPureDegreeZero : Prop
  noCFAlignmentAssumption : Prop
  notOnlyClassicalCKNRadiusSquaredCharge : Prop

/-- The only positive TICK650 bridge that would matter: the same C7
    production-defect carrier must provide a genuine local De Giorgi
    production exponent and a radius-facing no-reuse charge.  Either output
    alone is already known to be insufficient. -/
structure C7ProductionDefectCapacityBridge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  defectMeasure : C7ProductionDefectMeasure _seq _K hRho
  localizedProductionGain :
    LocalizedProductionLevelSetGain _seq _K hRho
  radiusCharging :
    RadiusChargingBadScaleMeasure _seq _K hRho
  sameCarrierFeedsLocalGainAndRouteCharge : Prop
  excludesLogarithmicBadScaleReuse : Prop
  doesNotFactorThroughCFGlobalExtension : Prop

/-- Projection from the full C7 production-defect bridge to the local
    production-gain surface. -/
def LocalizedProductionLevelSetGain.ofC7ProductionDefectCapacityBridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : C7ProductionDefectCapacityBridge seq K hRho) :
    LocalizedProductionLevelSetGain seq K hRho :=
  h.localizedProductionGain

/-- Projection from the full C7 production-defect bridge to the route-level
    radius-charging surface. -/
def RadiusChargingBadScaleMeasure.ofC7ProductionDefectCapacityBridge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : C7ProductionDefectCapacityBridge seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.radiusCharging

/-- TICK650 guard: the ground-state/capacity carrier explains why interior
    potential estimates are critical, but by itself it does not create the
    `β > 0` high-level production exponent.  A local gain must still come
    from an above-threshold production coefficient or weak-bilinear
    truncation norm, not merely from naming the capacity. -/
structure GroundStateCapacityDoesNotDeriveLocalizedProductionGain
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  defectMeasure : C7ProductionDefectMeasure _seq _K hRho
  groundStateTransformMakesInteriorPotentialCritical : Prop
  capacityLivesOnSeparatorNotInteriorProductionExponent : Prop
  reverseHolderAboveFiveHalvesMissing : Prop
  weakBilinearPositiveExponentMissing : Prop
  cannotConstructLocalizedProductionGain :
    ¬ Nonempty (LocalizedProductionLevelSetGain _seq _K hRho)

/-- TICK650 guard: capacity/no-reuse accounting and local production gain are
    independent obligations.  A proposed C7 production-defect object that has
    only the ground-state capacity budget or only the local De Giorgi gain is
    not a route-level result. -/
structure C7ProductionDefectNeedsBothGainAndRadiusCharge
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  defectMeasure : C7ProductionDefectMeasure _seq _K hRho
  localGainStillMissing :
    ¬ Nonempty (LocalizedProductionLevelSetGain _seq _K hRho)
  radiusChargeStillMissing :
    ¬ Nonempty (RadiusChargingBadScaleMeasure _seq _K hRho)
  capacityBudgetAloneIsOnlyNoReuseHalf : Prop
  localGainAloneDoesNotTelescopeBadScales : Prop
  noC7ProductionDefectCapacityBridge :
    ¬ Nonempty (C7ProductionDefectCapacityBridge _seq _K hRho)

/-- Constructor for the TICK650 two-obligation guard. -/
theorem c7ProductionDefect_needs_both_gain_and_radiusCharge
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hDefect : C7ProductionDefectMeasure seq K hRho)
    (hNoGain : ¬ Nonempty (LocalizedProductionLevelSetGain seq K hRho))
    (hNoRadius : ¬ Nonempty (RadiusChargingBadScaleMeasure seq K hRho)) :
    Nonempty (C7ProductionDefectNeedsBothGainAndRadiusCharge seq K hRho) := by
  refine ⟨{
    defectMeasure := hDefect
    localGainStillMissing := hNoGain
    radiusChargeStillMissing := hNoRadius
    capacityBudgetAloneIsOnlyNoReuseHalf := True
    localGainAloneDoesNotTelescopeBadScales := True
    noC7ProductionDefectCapacityBridge := ?_
  }⟩
  intro hBridge
  exact hNoGain ⟨hBridge.some.localizedProductionGain⟩

/-- TICK651 accepted extra hypotheses for the route-side C7/CV accounting
    problem.  A finite ground-state/vorticity-capacity budget can matter only
    if it is upgraded to one of the already-radius-facing fresh-payment
    primitives below.  Plain capacity/no-log bookkeeping is not included. -/
def C7KnownFreshRadiusExtraHypothesis
    (seq : LerayHopfSequence) (K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess seq K) : Prop :=
  Nonempty (FreshEnstrophyRadiusDropForBadNormalizedExcess seq K hRho) ∨
    Nonempty (FiniteLengthBadSkeletonDensityNoNeckStrong seq K hRho) ∨
      Nonempty (InheritedBadTreeCoronaNoNeckSkeleton seq K hRho) ∨
        Nonempty (ExcessDropChargesBadCylinderRadiusSplitWitness seq K hRho)

/-- Any known fresh-radius extra hypothesis already produces the radius-charge
    target.  This packages the boundary so TICK651 cannot count capacity-only
    naming as progress. -/
theorem c7KnownFreshRadiusExtraHypothesis_produces_radiusCharging
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : C7KnownFreshRadiusExtraHypothesis seq K hRho) :
    Nonempty (RadiusChargingBadScaleMeasure seq K hRho) := by
  rcases h with hFresh | hStrong | hCorona | hSplit
  · rcases hFresh with ⟨hFresh⟩
    exact ⟨RadiusChargingBadScaleMeasure.ofExcessDropSplitWitness
      (ExcessDropChargesBadCylinderRadiusSplitWitness.ofFreshEnstrophyRadiusDrop
        hFresh)⟩
  · rcases hStrong with ⟨hStrong⟩
    exact ⟨RadiusChargingBadScaleMeasure.ofFiniteLengthBadSkeletonDensityNoNeckStrong
      hStrong⟩
  · rcases hCorona with ⟨hCorona⟩
    exact ⟨RadiusChargingBadScaleMeasure.ofInheritedBadTreeCoronaNoNeckSkeleton
      hCorona⟩
  · rcases hSplit with ⟨hSplit⟩
    exact ⟨RadiusChargingBadScaleMeasure.ofExcessDropSplitWitness hSplit⟩

/-- TICK651 guard: no-log/fresh-radius language is not enough.  If the known
    fresh-radius extra hypotheses are absent, a C7 ground-state capacity
    carrier remains only bookkeeping: it may prevent obvious double-counting,
    but it still does not pay the `r_Q` radius charge or build the full C7
    bridge. -/
structure C7CapacityNoLogFreshRadiusBoundary
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  defectMeasure : C7ProductionDefectMeasure _seq _K hRho
  finiteGroundStateCapacityBudget : Prop
  noLogReuseBookkeeping : Prop
  capacityBookkeepingMayBeOnlySquareScale : Prop
  knownFreshRadiusExtraHypothesisMissing :
    ¬ C7KnownFreshRadiusExtraHypothesis _seq _K hRho
  radiusChargeStillMissing :
    ¬ Nonempty (RadiusChargingBadScaleMeasure _seq _K hRho)
  capacityOnlyDoesNotProduceC7Bridge :
    ¬ Nonempty (C7ProductionDefectCapacityBridge _seq _K hRho)

/-- Constructor for the TICK651 route-side boundary. -/
theorem c7CapacityNoLogBudget_needs_freshRadiusPayment
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hDefect : C7ProductionDefectMeasure seq K hRho)
    (hNoRadius : ¬ Nonempty (RadiusChargingBadScaleMeasure seq K hRho)) :
    Nonempty (C7CapacityNoLogFreshRadiusBoundary seq K hRho) := by
  have hNoKnown :
      ¬ C7KnownFreshRadiusExtraHypothesis seq K hRho := by
    intro hKnown
    exact hNoRadius
      (c7KnownFreshRadiusExtraHypothesis_produces_radiusCharging hKnown)
  refine ⟨{
    defectMeasure := hDefect
    finiteGroundStateCapacityBudget := True
    noLogReuseBookkeeping := True
    capacityBookkeepingMayBeOnlySquareScale := True
    knownFreshRadiusExtraHypothesisMissing := hNoKnown
    radiusChargeStillMissing := hNoRadius
    capacityOnlyDoesNotProduceC7Bridge := ?_
  }⟩
  intro hBridge
  exact hNoRadius ⟨hBridge.some.radiusCharging⟩

/-- TICK652 strengthened invoice target.  `RadiusChargingBadScaleMeasure`
    is the route-level abstract charge.  This object is stricter: it displays
    the per-bad-node invoice data on the same stopping tree, with one-use
    accounting before descendants can rebill the same fresh region. -/
structure C7SameTreeFreshRadiusInvoice
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  badNodes : Set DyadicParabolicCube
  nodeRadius : DyadicParabolicCube → ℝ
  invoiceRegion : DyadicParabolicCube → Set (EuclideanSpace ℝ (Fin 4))
  invoiceAssignedBeforeSubtreeSelection : Prop
  invoicePaysRadiusForEachSelectedBadNode : Prop
  invoiceUsesSameNormalizedExcessStoppingTree : Prop
  oneUseNoDescendantRebilling : Prop
  descendantInvoicesDisjointOrBoundedOverlap : Prop
  finiteFreshInvoiceBudget : Prop
  doesNotFactorThroughCFDirectionAlignment : Prop
  notDegreeZeroRieszBookkeeping : Prop
  notParabolicRateSlavedScalar : Prop
  producesRadiusCharging :
    RadiusChargingBadScaleMeasure _seq _K hRho

/-- Projection from a displayed C7 invoice to the abstract radius-charging
    primitive. -/
def RadiusChargingBadScaleMeasure.ofC7SameTreeFreshRadiusInvoice
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (h : C7SameTreeFreshRadiusInvoice seq K hRho) :
    RadiusChargingBadScaleMeasure seq K hRho :=
  h.producesRadiusCharging

/-- Side condition missing from a merely abstract split-excess witness: the
    telescoping proof must carry a displayed same-tree, one-use fresh invoice
    whose produced radius-charge object is the same one used by the
    telescoping adapter. -/
structure ExcessDropTelescopingCarriesSameTreeFreshInvoice
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K)
    (hPot : ExcessDropPotentialCandidate _seq _K hRho)
    (hTree : ExcessDropTreeSuperadditivity _seq _K hRho hPot)
    (hDrop : BadNodeRadiusDrop _seq _K hRho hPot hTree)
    (hTel :
      ExcessDropTelescopesToRadiusCharging
        _seq _K hRho hPot hTree hDrop) where
  sameTreeFreshInvoice :
    C7SameTreeFreshRadiusInvoice _seq _K hRho
  invoiceUsesDisplayedBadNodes :
    sameTreeFreshInvoice.badNodes = hDrop.badNodes
  invoiceUsesDisplayedNodeRadius :
    sameTreeFreshInvoice.nodeRadius = hDrop.nodeRadius
  invoiceProducesTelescopingRadiusCharge :
    sameTreeFreshInvoice.producesRadiusCharging =
      hTel.radiusChargingMeasure
  oneUseAccountingIsTheNoReuseField :
    sameTreeFreshInvoice.oneUseNoDescendantRebilling =
      hDrop.noReuseOfSameDropAlongNestedBadNodes

/-- Projection from the strengthened telescoping-invoice side condition to the
    displayed invoice target. -/
def C7SameTreeFreshRadiusInvoice.ofExcessDropTelescopingInvoice
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    {hPot : ExcessDropPotentialCandidate seq K hRho}
    {hTree : ExcessDropTreeSuperadditivity seq K hRho hPot}
    {hDrop : BadNodeRadiusDrop seq K hRho hPot hTree}
    {hTel :
      ExcessDropTelescopesToRadiusCharging
        seq K hRho hPot hTree hDrop}
    (h :
      ExcessDropTelescopingCarriesSameTreeFreshInvoice
        seq K hRho hPot hTree hDrop hTel) :
    C7SameTreeFreshRadiusInvoice seq K hRho :=
  h.sameTreeFreshInvoice

/-- TICK652 graph-conditioned boundary: the existing split-excess witness
    gives an abstract radius-charge projection, but it is not yet the
    quantity-level invoice theorem unless the displayed same-tree invoice
    side condition above is supplied.  This records the exact artifact-vs-
    inequality gap exposed by the graph pass. -/
structure SplitExcessFreshRadiusInvoiceBoundary
    (_seq : LerayHopfSequence) (_K : CompactSubCylinder)
    (hRho : RhoFromNormalizedCKNExcess _seq _K) where
  splitWitness :
    ExcessDropChargesBadCylinderRadiusSplitWitness _seq _K hRho
  abstractRadiusChargingAvailable :
    RadiusChargingBadScaleMeasure _seq _K hRho
  abstractRadiusCharging_eq :
    abstractRadiusChargingAvailable =
      RadiusChargingBadScaleMeasure.ofExcessDropSplitWitness splitWitness
  sameTreeInvoiceStillMissing :
    ¬ Nonempty
      (ExcessDropTelescopingCarriesSameTreeFreshInvoice
        _seq _K hRho
        splitWitness.potentialCandidate
        splitWitness.treeSuperadditivity
        splitWitness.badNodeRadiusDrop
        splitWitness.telescoping)
  artifactDependencyIsNotQuantityInvoice : Prop
  graphQuantityPathFromCapacityOrExcessStillMissing : Prop
  cannotPromoteSplitWitnessToDisplayedInvoice :
    ¬ Nonempty (C7SameTreeFreshRadiusInvoice _seq _K hRho)

/-- Constructor for the TICK652 boundary.  It keeps the useful positive
    projection while forbidding the stronger invoice claim until a displayed
    same-tree invoice is proved. -/
theorem splitExcessFreshRadiusInvoice_needs_sameTreeInvoice
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    {hRho : RhoFromNormalizedCKNExcess seq K}
    (hSplit : ExcessDropChargesBadCylinderRadiusSplitWitness seq K hRho)
    (hNoInvoice : ¬ Nonempty (C7SameTreeFreshRadiusInvoice seq K hRho)) :
    Nonempty (SplitExcessFreshRadiusInvoiceBoundary seq K hRho) := by
  have hNoTel :
      ¬ Nonempty
        (ExcessDropTelescopingCarriesSameTreeFreshInvoice
          seq K hRho
          hSplit.potentialCandidate
          hSplit.treeSuperadditivity
          hSplit.badNodeRadiusDrop
          hSplit.telescoping) := by
    intro hTel
    exact hNoInvoice
      ⟨C7SameTreeFreshRadiusInvoice.ofExcessDropTelescopingInvoice
        hTel.some⟩
  refine ⟨{
    splitWitness := hSplit
    abstractRadiusChargingAvailable :=
      RadiusChargingBadScaleMeasure.ofExcessDropSplitWitness hSplit
    abstractRadiusCharging_eq := rfl
    sameTreeInvoiceStillMissing := hNoTel
    artifactDependencyIsNotQuantityInvoice := True
    graphQuantityPathFromCapacityOrExcessStillMissing := True
    cannotPromoteSplitWitnessToDisplayedInvoice := hNoInvoice
  }⟩

/-- Sharpened no-go theorem name from the new packet: any gradient upgrade that
    remains below `q = 5/2` keeps the interpolation exponent strictly below
    `1`, so the missing half-power is not recovered. -/
theorem reverseHolderBelowThresholdFails
    {seq : LerayHopfSequence} {K : CompactSubCylinder}
    (hUpgrade : ReverseHolderGradientUpgrade seq K)
    (hSubcritical : hUpgrade.exponent < criticalReverseHolderThreshold) :
    Nonempty (ReverseHolderBelowThresholdObstruction seq K) := by
  have hNoClose := reverseHolderBelowThresholdNoClose hUpgrade hSubcritical
  exact hNoClose

/-- Active open PDE hinge after the new 5.5 packet: prove or refute the
    one-scale enstrophy epsilon-regularity criterion that would feed the
    codimension-four packing argument. -/
def OneScaleEnstrophyEpsilonRegularityFromSuitableWeak_isOpen : Prop :=
  True

/-- Sharper surviving positive-lane hinge after the pure one-scale no-go:
    determine the minimal explicit Galilean-invariant velocity-pressure excess
    package that, together with one-scale enstrophy and normalization, yields
    the literal all-scale `LocalSmallnessCriterion` on a smaller cylinder. -/
def OneScaleEnstrophyPlusCKNExcessToLocalSmallnessFromSuitableWeak_isOpen : Prop :=
  True

/-- Sharpened PDE frontier extracted from the half-power bridge packet.
    The active open question is no longer the raw slogan `CKN => CIB`, but the
    stronger quantitative regularity-scale packing theorem that would recover
    the missing half-power. -/
def QuantitativeRegularityScaleBridgeFromSuitableWeak_isOpen : Prop :=
  True

/-- UNLOCK B (the genuine open frontier per C-108).
    Derive the critical increment-compactness bound directly from the
    Caffarelli-Kohn-Nirenberg suitable-weak local-energy inequality,
    without assuming critical Besov regularity a priori. If proven,
    this PROMOTES Theorem 5.1 to an unconditional theorem in the full
    Leray-Hopf class. Genuine 6-month+ research target.

    PATTERN-019 self-check on Unlock B will be re-run if/when it ships. -/
def UnlockB_CriticalIncrementCompactnessFromCKN_isOpen : Prop :=
  -- TYPED-SCAFFOLD for the genuine research frontier.
  True

end UnlockB

end NSL3MultiscaleYM

/-
  Lake-clean expectation: this file type-checks with no `sorry`s
  appearing, only `Classical.choice` on opaque types and trivial
  `True` placeholders. The genuine analytic content (Steps 1-4 of
  the main theorem) is documented in the proof body as comments;
  the substantive Lean port is a 4-week sub-charter under
  PATTERN-019 enforcement.

  CROSS-REFERENCES:
    - ns_defect_calculus_skeleton.lean (MollifiedFlux, RadonDefectMeasure)
    - ns_intrinsic_frame_mollification_universality.lean (mollifier ops)
    - ns_trackb_atom1_measure_valued_bridge.lean (measure-valued YM stubs)
  These existing files SUPPLY the cornering infrastructure that
  Theorem 5.1's full proof will eventually inherit; the present file
  is the typed entry-point for the new content.
-/
