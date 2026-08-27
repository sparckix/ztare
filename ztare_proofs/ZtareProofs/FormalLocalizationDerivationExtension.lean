import Mathlib.Algebra.TrivSqZeroExt.Basic
import Mathlib.RingTheory.LaurentSeries
import Mathlib.RingTheory.PowerSeries.Derivative
import Mathlib.Tactic

/-!
# Extending derivations across localization

A derivation is encoded by its square-zero graph `a ↦ (a, da)`.  The graph
maps every localization denominator to a unit, hence the universal property
of localization extends it without choosing fraction representatives.  The
second projection of the extended graph is the localized derivation; the
first projection is the identity by localization extensionality.
-/

namespace FormalLocalizationDerivationExtension

open PowerSeries
open scoped LaurentSeries

noncomputable section

variable {A S : Type*} [CommRing A] [CommRing S]
variable (M : Submonoid A) [Algebra A S] [IsLocalization M S]

/-- The square-zero graph of a derivation after mapping both coordinates to
the localization. -/
def derivationGraphRingHom (d : Derivation ℤ A A) :
    A →+* TrivSqZeroExt S S where
  toFun value :=
    (algebraMap A S value, algebraMap A S (d value))
  map_one' := by
    ext <;> simp
  map_mul' := by
    intro first second
    ext
    · simp
    · simp only [TrivSqZeroExt.snd_mk, map_mul,
        TrivSqZeroExt.snd_mul, TrivSqZeroExt.fst_mk]
      rw [d.leibniz]
      simp only [map_add]
      simp
      ring
  map_zero' := by
    ext <;> simp
  map_add' := by
    intro first second
    ext <;> simp

theorem derivationGraphRingHom_fst
    (d : Derivation ℤ A A) (value : A) :
    (derivationGraphRingHom d value).fst = algebraMap A S value := by
  rfl

theorem derivationGraphRingHom_snd
    (d : Derivation ℤ A A) (value : A) :
    (derivationGraphRingHom d value).snd = algebraMap A S (d value) := by
  rfl

/-- The graph extends through the localization because its first coordinate
is the localization map and therefore sends every denominator to a unit. -/
def localizationGraphLift (d : Derivation ℤ A A) :
    S →+* TrivSqZeroExt S S :=
  IsLocalization.lift (g := derivationGraphRingHom d)
    fun denominator : M ↦ by
    rw [TrivSqZeroExt.isUnit_iff_isUnit_fst]
    change IsUnit (algebraMap A S (denominator : A))
    exact IsLocalization.map_units S denominator

@[simp]
theorem localizationGraphLift_algebraMap
    (d : Derivation ℤ A A) (value : A) :
    localizationGraphLift M d (algebraMap A S value) =
      derivationGraphRingHom d value := by
  exact IsLocalization.lift_eq _ value

/-- The first projection of the lifted graph is the identity on the complete
localization. -/
theorem localizationGraphLift_fst
    (d : Derivation ℤ A A) (value : S) :
    (localizationGraphLift M d value).fst = value := by
  have hhom :
      (TrivSqZeroExt.fstHom S S S).toRingHom.comp
          (localizationGraphLift M d) =
        RingHom.id S := by
    apply IsLocalization.ringHom_ext M
    ext baseValue
    simp only [RingHom.comp_apply, RingHom.id_apply]
    rw [localizationGraphLift_algebraMap]
    rfl
  exact RingHom.congr_fun hhom value

/-- Additive second projection of the lifted square-zero graph. -/
def localizationDerivativeAddHom (d : Derivation ℤ A A) : S →+ S where
  toFun value := (localizationGraphLift M d value).snd
  map_zero' := by simp [localizationGraphLift]
  map_add' := by
    intro first second
    simp [localizationGraphLift]

/-- Canonical extension of a derivation across a commutative localization. -/
def localizationDerivation (d : Derivation ℤ A A) : Derivation ℤ S S :=
  Derivation.mk'
    (localizationDerivativeAddHom M d).toIntLinearMap
    (by
      intro first second
      change
        (localizationGraphLift M d (first * second)).snd =
          first • (localizationGraphLift M d second).snd +
            second • (localizationGraphLift M d first).snd
      rw [map_mul, TrivSqZeroExt.snd_mul,
        localizationGraphLift_fst M d,
        localizationGraphLift_fst M d]
      simp only [smul_eq_mul, op_smul_eq_mul]
      ring)

/-- The localized derivation has the exact prescribed value on every base
element. -/
@[simp]
theorem localizationDerivation_algebraMap
    (d : Derivation ℤ A A) (value : A) :
    localizationDerivation M d (algebraMap A S value) =
      algebraMap A S (d value) := by
  change (localizationGraphLift M d (algebraMap A S value)).snd = _
  rw [localizationGraphLift_algebraMap]
  rfl

/-- A derivation on the localization is determined by its values on the base
ring. -/
theorem localizationDerivation_unique
    (d : Derivation ℤ A A) (candidate : Derivation ℤ S S)
    (hcandidate : ∀ value : A,
      candidate (algebraMap A S value) = algebraMap A S (d value)) :
    candidate = localizationDerivation M d := by
  have hgraph :
      derivationGraphRingHom (A := S) (S := S) candidate =
        localizationGraphLift M d := by
    apply IsLocalization.ringHom_ext M
    ext value
    · simp [derivationGraphRingHom]
    · simp [derivationGraphRingHom, hcandidate]
  ext value
  have hsnd := congrArg
    (fun graph : S →+* TrivSqZeroExt S S ↦ (graph value).snd) hgraph
  simpa [derivationGraphRingHom, localizationDerivation,
    localizationDerivativeAddHom] using hsnd

/-- Aggregated localization-extension certificate. -/
theorem localization_derivation_extension_terminal_certificate :
    ∀ d : Derivation ℤ A A,
      (∀ value : A,
        localizationDerivation M d (algebraMap A S value) =
          algebraMap A S (d value)) ∧
      ∀ candidate : Derivation ℤ S S,
        (∀ value : A,
          candidate (algebraMap A S value) = algebraMap A S (d value)) →
        candidate = localizationDerivation M d := by
  intro d
  exact ⟨localizationDerivation_algebraMap M d,
    fun candidate hcandidate =>
      localizationDerivation_unique M d candidate hcandidate⟩

/-- Formal Laurent differentiation is the canonical localization extension
of formal power-series differentiation. -/
noncomputable local instance powerSeriesCanonicalIntAlgebra
    (K : Type*) [Field K] : Algebra ℤ K⟦X⟧ :=
  Ring.toIntAlgebra K⟦X⟧

noncomputable local instance laurentSeriesCanonicalIntAlgebra
    (K : Type*) [Field K] : Algebra ℤ K⸨X⸩ :=
  Ring.toIntAlgebra K⸨X⸩

/-- Power-series differentiation packaged against the canonical integer
algebra used by the localization kernel. -/
def powerSeriesIntDerivation (K : Type*) [Field K] :
    Derivation ℤ K⟦X⟧ K⟦X⟧ :=
  Derivation.mk'
    (PowerSeries.derivative K).toLinearMap.toAddMonoidHom.toIntLinearMap
    (by
      intro first second
      simpa only [smul_eq_mul] using
        (PowerSeries.derivative K).leibniz first second)

@[simp]
theorem powerSeriesIntDerivation_apply
    (K : Type*) [Field K] (series : K⟦X⟧) :
    powerSeriesIntDerivation K series = PowerSeries.derivative K series := by
  rfl

def laurentSeriesDerivation (K : Type*) [Field K] :
    Derivation ℤ K⸨X⸩ K⸨X⸩ :=
  localizationDerivation
    (Submonoid.powers (PowerSeries.X : K⟦X⟧))
    (powerSeriesIntDerivation K)

@[simp]
theorem laurentSeriesDerivation_algebraMap
    (K : Type*) [Field K] (series : K⟦X⟧) :
    laurentSeriesDerivation K
        (algebraMap K⟦X⟧ K⸨X⸩ series) =
      algebraMap K⟦X⟧ K⸨X⸩ (PowerSeries.derivative K series) := by
  exact localizationDerivation_algebraMap
    (A := K⟦X⟧) (S := K⸨X⸩)
    (Submonoid.powers (PowerSeries.X : K⟦X⟧))
    (powerSeriesIntDerivation K) series

/-- The Laurent derivation is characterized by its action on embedded power
series. -/
theorem laurentSeriesDerivation_unique
    (K : Type*) [Field K] (candidate : Derivation ℤ K⸨X⸩ K⸨X⸩)
    (hcandidate : ∀ series : K⟦X⟧,
      candidate (algebraMap K⟦X⟧ K⸨X⸩ series) =
        algebraMap K⟦X⟧ K⸨X⸩ (PowerSeries.derivative K series)) :
    candidate = laurentSeriesDerivation K := by
  have hcandidate' : ∀ series : K⟦X⟧,
      candidate (algebraMap K⟦X⟧ K⸨X⸩ series) =
        algebraMap K⟦X⟧ K⸨X⸩ (powerSeriesIntDerivation K series) := by
    intro series
    simpa using hcandidate series
  exact localizationDerivation_unique
    (A := K⟦X⟧) (S := K⸨X⸩)
    (Submonoid.powers (PowerSeries.X : K⟦X⟧))
    (powerSeriesIntDerivation K) candidate hcandidate'

end

end FormalLocalizationDerivationExtension
