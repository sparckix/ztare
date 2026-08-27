import Mathlib.Tactic
import ZtareProofs.FormalAlgebraicEigenvectorDarbouxExclusion
import ZtareProofs.FormalDifferentialGermEvaluation

/-!
# Critical finite-prefix exclusion on an arbitrary differential germ

One initial nested relation, the exact visible and hidden ODEs, and finite
derivative-prefix membership force a nonzero visible polynomial to vanish at
the critical endpoint.  This constructs algebraicity of that endpoint.  The
critical irrational-residue Darboux theorem then excludes the nonzero scalar
eigenvector directly, without analytic continuation or a monodromy orbit.
-/

namespace FormalCriticalDifferentialGermEliminantExclusion

open Ideal Polynomial
open FormalAlgebraicEigenvectorDarbouxExclusion
open FormalBivariateDerivationSwap
open FormalCriticalConnectionRationalization
open FormalDerivativePrefixEvaluation
open FormalDifferentialGermEvaluation
open FormalFiniteDerivativeDarbouxAlternative

noncomputable section

abbrev CriticalRF := RatFunc ℝ

variable {E : Type*} [Field E] [Algebra CriticalRF E]

/-- A finite visible eliminant contradicts the critical scalar eigenvector on
any compatible differential field germ carrying one initial coupled
relation. -/
theorem critical_finite_prefix_differential_germ_impossible
    (dE : Derivation ℤ E E)
    (visible hidden : E) (velocity : CriticalRF[X])
    (initial : CriticalRF[X][X]) (bound : ℕ)
    (eliminant : CriticalRF[X])
    (hcoefficients : ∀ coefficient : CriticalRF,
      algebraMap CriticalRF E
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ) coefficient) =
        dE (algebraMap CriticalRF E coefficient))
    (hvisible :
      dE visible =
        algebraMap CriticalRF E explicitRationalDifferential * visible)
    (hhidden :
      dE hidden = velocity.eval₂ (algebraMap CriticalRF E) hidden)
    (hinitial :
      nestedEvalRingHom (algebraMap CriticalRF E) visible hidden initial = 0)
    (hmember :
      Polynomial.C eliminant ∈ derivativePrefixIdeal
        (storedBivariateDerivation
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ))
          velocity explicitRationalDifferential)
        initial bound)
    (heliminant : eliminant ≠ 0)
    (hvisibleNonzero : visible ≠ 0) : False := by
  have hevaluatedNested :
      nestedEvalRingHom (algebraMap CriticalRF E) visible hidden
          (Polynomial.C eliminant) = 0 := by
    exact nestedEval_eq_zero_of_mem_derivativePrefixIdeal
      (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
        (K := ℝ))
      dE (algebraMap CriticalRF E) velocity
      explicitRationalDifferential visible hidden hcoefficients hvisible
      hhidden initial hinitial bound (Polynomial.C eliminant) hmember
  have hevaluated :
      eliminant.eval₂ (algebraMap CriticalRF E) visible = 0 := by
    simpa [nestedEvalRingHom] using hevaluatedNested
  have halgebraic : IsAlgebraic CriticalRF visible := by
    refine ⟨eliminant, heliminant, ?_⟩
    simpa [Polynomial.aeval_def] using hevaluated
  exact no_nonzero_algebraic_critical_eigenvector
    dE visible hcoefficients hvisible halgebraic hvisibleNonzero

/-- Aggregated critical differential-germ eliminant certificate. -/
theorem critical_differential_germ_eliminant_exclusion_terminal_certificate :
    ∀ (dE : Derivation ℤ E E)
      (visible hidden : E) (velocity : CriticalRF[X])
      (initial : CriticalRF[X][X]) (bound : ℕ)
      (eliminant : CriticalRF[X]),
      (∀ coefficient : CriticalRF,
        algebraMap CriticalRF E
            (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
              (K := ℝ) coefficient) =
          dE (algebraMap CriticalRF E coefficient)) →
      dE visible =
        algebraMap CriticalRF E explicitRationalDifferential * visible →
      dE hidden = velocity.eval₂ (algebraMap CriticalRF E) hidden →
      nestedEvalRingHom (algebraMap CriticalRF E) visible hidden initial = 0 →
      Polynomial.C eliminant ∈ derivativePrefixIdeal
        (storedBivariateDerivation
          (FormalRationalFunctionDerivationLocalOrder.ratFuncDerivation
            (K := ℝ))
          velocity explicitRationalDifferential)
        initial bound →
      eliminant ≠ 0 → visible ≠ 0 → False := by
  intro dE visible hidden velocity initial bound eliminant
    hcoefficients hvisible hhidden hinitial hmember heliminant
    hvisibleNonzero
  exact critical_finite_prefix_differential_germ_impossible
    dE visible hidden velocity initial bound eliminant hcoefficients
    hvisible hhidden hinitial hmember heliminant hvisibleNonzero

end

end FormalCriticalDifferentialGermEliminantExclusion
