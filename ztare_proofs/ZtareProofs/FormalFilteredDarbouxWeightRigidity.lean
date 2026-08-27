import Mathlib.Algebra.Polynomial.Degree.Monomial
import Mathlib.Tactic

/-!
# Filtered weight rigidity for Darboux coefficient rows

Let a derivation preserve a visible-weight filtration and act on weight `n`
by a common coefficient derivation plus `n * L`.  If a Darboux relation has a
weight-zero cofactor, then any two nonzero coefficients create an exact
cross-ratio eigenrow.  Excluding every nonzero weight resonance therefore
forces the Darboux polynomial to occupy one visible weight.

The theorem is substrate-neutral.  A caller may exclude the cross-ratio row
by residues, valuations, grading, or another exact invariant.
-/

namespace FormalFilteredDarbouxWeightRigidity

open Polynomial

variable {K : Type*} [CommRing K]

/-- The coefficient row of a filtered Darboux equation with a cofactor of
visible weight zero. -/
def darbouWeightRow
    (coefficientDerivative : K → K)
    (logarithmicWeight cofactor coefficient : K)
    (weight : ℕ) : Prop :=
  coefficientDerivative coefficient +
      (weight : K) * logarithmicWeight * coefficient =
    cofactor * coefficient

/-- Two occupied weights in the same Darboux row produce the cross-multiplied
eigenratio equation.  No division is used. -/
theorem cross_relation_of_two_darboux_weight_rows
    (coefficientDerivative : K → K)
    (logarithmicWeight cofactor first second : K)
    (firstWeight secondWeight : ℕ)
    (hfirst : darbouWeightRow coefficientDerivative logarithmicWeight
      cofactor first firstWeight)
    (hsecond : darbouWeightRow coefficientDerivative logarithmicWeight
      cofactor second secondWeight) :
    second * coefficientDerivative first -
        first * coefficientDerivative second =
      ((secondWeight : K) - (firstWeight : K)) *
        logarithmicWeight * first * second := by
  unfold darbouWeightRow at hfirst hsecond
  have hfirstDerivative :
      coefficientDerivative first =
        cofactor * first -
          (firstWeight : K) * logarithmicWeight * first := by
    linear_combination hfirst
  have hsecondDerivative :
      coefficientDerivative second =
        cofactor * second -
          (secondWeight : K) * logarithmicWeight * second := by
    linear_combination hsecond
  rw [hfirstDerivative, hsecondDerivative]
  ring

/-- If all nonzero-weight cross relations are excluded, the support of a
filtered Darboux polynomial has at most one member. -/
theorem support_card_le_one_of_no_weight_resonance
    (coefficientDerivative : K → K)
    (logarithmicWeight cofactor : K)
    (polynomial : K[X])
    (hrows : ∀ weight,
      darbouWeightRow coefficientDerivative logarithmicWeight cofactor
        (polynomial.coeff weight) weight)
    (hnoResonance : ∀ firstWeight secondWeight,
      firstWeight ≠ secondWeight →
      polynomial.coeff firstWeight ≠ 0 →
      polynomial.coeff secondWeight ≠ 0 →
      polynomial.coeff secondWeight *
            coefficientDerivative (polynomial.coeff firstWeight) -
          polynomial.coeff firstWeight *
            coefficientDerivative (polynomial.coeff secondWeight) ≠
        ((secondWeight : K) - (firstWeight : K)) *
          logarithmicWeight * polynomial.coeff firstWeight *
            polynomial.coeff secondWeight) :
    polynomial.support.card ≤ 1 := by
  rw [Finset.card_le_one]
  intro firstWeight hfirst secondWeight hsecond
  by_contra hne
  have hfirstNonzero : polynomial.coeff firstWeight ≠ 0 :=
    mem_support_iff.mp hfirst
  have hsecondNonzero : polynomial.coeff secondWeight ≠ 0 :=
    mem_support_iff.mp hsecond
  exact hnoResonance firstWeight secondWeight hne hfirstNonzero
    hsecondNonzero
    (cross_relation_of_two_darboux_weight_rows coefficientDerivative
      logarithmicWeight cofactor (polynomial.coeff firstWeight)
      (polynomial.coeff secondWeight) firstWeight secondWeight
      (hrows firstWeight) (hrows secondWeight))

/-- A nonzero filtered Darboux polynomial with no weight resonance is the
monomial in its unique surviving visible weight. -/
theorem eq_monomial_natDegree_of_no_weight_resonance
    (coefficientDerivative : K → K)
    (logarithmicWeight cofactor : K)
    (polynomial : K[X])
    (hrows : ∀ weight,
      darbouWeightRow coefficientDerivative logarithmicWeight cofactor
        (polynomial.coeff weight) weight)
    (hnoResonance : ∀ firstWeight secondWeight,
      firstWeight ≠ secondWeight →
      polynomial.coeff firstWeight ≠ 0 →
      polynomial.coeff secondWeight ≠ 0 →
      polynomial.coeff secondWeight *
            coefficientDerivative (polynomial.coeff firstWeight) -
          polynomial.coeff firstWeight *
            coefficientDerivative (polynomial.coeff secondWeight) ≠
        ((secondWeight : K) - (firstWeight : K)) *
          logarithmicWeight * polynomial.coeff firstWeight *
            polynomial.coeff secondWeight) :
    polynomial = monomial polynomial.natDegree polynomial.leadingCoeff := by
  symm
  exact monomial_natDegree_leadingCoeff_eq_self
    (support_card_le_one_of_no_weight_resonance coefficientDerivative
      logarithmicWeight cofactor polynomial hrows hnoResonance)

/-- Aggregated filtered Darboux-weight certificate. -/
theorem filtered_darboux_weight_rigidity_terminal_certificate :
    ∀ (coefficientDerivative : K → K)
      (logarithmicWeight cofactor : K) (polynomial : K[X]),
      (∀ weight,
        darbouWeightRow coefficientDerivative logarithmicWeight cofactor
          (polynomial.coeff weight) weight) →
      (∀ firstWeight secondWeight,
        firstWeight ≠ secondWeight →
        polynomial.coeff firstWeight ≠ 0 →
        polynomial.coeff secondWeight ≠ 0 →
        polynomial.coeff secondWeight *
              coefficientDerivative (polynomial.coeff firstWeight) -
            polynomial.coeff firstWeight *
              coefficientDerivative (polynomial.coeff secondWeight) ≠
          ((secondWeight : K) - (firstWeight : K)) *
            logarithmicWeight * polynomial.coeff firstWeight *
              polynomial.coeff secondWeight) →
      polynomial.support.card ≤ 1 ∧
        polynomial =
          monomial polynomial.natDegree polynomial.leadingCoeff := by
  intro coefficientDerivative logarithmicWeight cofactor polynomial
    hrows hnoResonance
  exact ⟨
    support_card_le_one_of_no_weight_resonance coefficientDerivative
      logarithmicWeight cofactor polynomial hrows hnoResonance,
    eq_monomial_natDegree_of_no_weight_resonance coefficientDerivative
      logarithmicWeight cofactor polynomial hrows hnoResonance⟩

end FormalFilteredDarbouxWeightRigidity
