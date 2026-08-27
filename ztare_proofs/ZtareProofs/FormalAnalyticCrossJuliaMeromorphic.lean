import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Tactic
import ZtareProofs.FormalAnalyticPolynomialRootSelection
import ZtareProofs.FormalPolynomialCrossJuliaElimination

/-!
# Meromorphic hidden endpoint from the cross-Julia identity

The cross-Julia eliminant becomes an analytic polynomial family after pullback
to any analytic parameter germ.  A nonzero coefficient determinant and one
nonvanishing outer-generator value force at least one coefficient germ to be
active.  Finite coefficient selection and scaled-monic normalization then
make the hidden endpoint meromorphic.
-/

namespace FormalAnalyticCrossJuliaMeromorphic

open Filter Polynomial
open scoped Topology
open FormalPolynomialCrossJuliaElimination
open FormalAnalyticPolynomialRootSelection

/-- Analytic pullback data for a cross-Julia relation.  Meromorphicity of the
hidden endpoint and an active polynomial coefficient are deliberately absent. -/
structure AnalyticCrossJuliaCarrier where
  center : ℂ
  firstGenerator : ℂ[X]
  secondGenerator : ℂ[X]
  firstIndex : ℕ
  secondIndex : ℕ
  endpointValue : ℂ → ℂ
  endpointDerivative : ℂ → ℂ
  sourceValue : ℂ → ℂ
  hiddenEndpoint : ℂ → ℂ
  endpoint_analytic : AnalyticAt ℂ endpointValue center
  endpointDerivative_analytic : AnalyticAt ℂ endpointDerivative center
  source_analytic : AnalyticAt ℂ sourceValue center
  hidden_differentiable : ∀ᶠ t in 𝓝[≠] center,
    DifferentiableAt ℂ hiddenEndpoint t
  cross_identity : ∀ᶠ t in 𝓝[≠] center,
    Polynomial.eval (endpointValue t) secondGenerator *
        Polynomial.eval (hiddenEndpoint t) firstGenerator =
      endpointDerivative t * Polynomial.eval (sourceValue t) firstGenerator *
        Polynomial.eval (hiddenEndpoint t) secondGenerator
  coefficient_determinant :
    Polynomial.coeff firstGenerator firstIndex *
        Polynomial.coeff secondGenerator secondIndex -
      Polynomial.coeff firstGenerator secondIndex *
        Polynomial.coeff secondGenerator firstIndex ≠ 0
  endpoint_nonzero : ∀ᶠ t in 𝓝[≠] center,
    Polynomial.eval (endpointValue t) secondGenerator ≠ 0

/-- The pulled-back cross-Julia polynomial family. -/
noncomputable def AnalyticCrossJuliaCarrier.polynomialFamily
    (carrier : AnalyticCrossJuliaCarrier) : ℂ → ℂ[X] := fun t ↦
  crossJuliaPolynomial carrier.firstGenerator carrier.secondGenerator
    (carrier.endpointValue t) (carrier.endpointDerivative t)
    (carrier.sourceValue t)

/-- A finite degree bound that also contains both determinant indices. -/
def AnalyticCrossJuliaCarrier.degreeBound
    (carrier : AnalyticCrossJuliaCarrier) : ℕ :=
  max (max carrier.firstGenerator.natDegree
      carrier.secondGenerator.natDegree)
    (max carrier.firstIndex carrier.secondIndex)

theorem AnalyticCrossJuliaCarrier.polynomialFamily_coefficient_analytic
    (carrier : AnalyticCrossJuliaCarrier) (i : ℕ) :
    AnalyticAt ℂ (fun t ↦ (carrier.polynomialFamily t).coeff i)
      carrier.center := by
  have hsecondEval : AnalyticAt ℂ
      (fun t ↦ carrier.secondGenerator.eval (carrier.endpointValue t))
      carrier.center :=
    carrier.endpoint_analytic.aeval_polynomial carrier.secondGenerator
  have hfirstEval : AnalyticAt ℂ
      (fun t ↦ carrier.firstGenerator.eval (carrier.sourceValue t))
      carrier.center :=
    carrier.source_analytic.aeval_polynomial carrier.firstGenerator
  have hleft : AnalyticAt ℂ
      (fun t ↦ carrier.secondGenerator.eval (carrier.endpointValue t) *
        carrier.firstGenerator.coeff i) carrier.center :=
    hsecondEval.mul analyticAt_const
  have hright : AnalyticAt ℂ
      (fun t ↦
        (carrier.endpointDerivative t *
          carrier.firstGenerator.eval (carrier.sourceValue t)) *
            carrier.secondGenerator.coeff i) carrier.center :=
    (carrier.endpointDerivative_analytic.mul hfirstEval).mul analyticAt_const
  simpa only [AnalyticCrossJuliaCarrier.polynomialFamily,
    crossJuliaPolynomial, coeff_sub, coeff_C_mul, Pi.sub_apply,
    Pi.mul_apply] using hleft.sub hright

theorem AnalyticCrossJuliaCarrier.polynomialFamily_degree_le
    (carrier : AnalyticCrossJuliaCarrier) (t : ℂ) :
    (carrier.polynomialFamily t).natDegree ≤ carrier.degreeBound := by
  calc
    (carrier.polynomialFamily t).natDegree ≤
        max
          (natDegree
            (C (carrier.secondGenerator.eval (carrier.endpointValue t)) *
              carrier.firstGenerator))
          (natDegree
            (C (carrier.endpointDerivative t *
                carrier.firstGenerator.eval (carrier.sourceValue t)) *
              carrier.secondGenerator)) := by
        exact natDegree_sub_le _ _
    _ ≤ max carrier.firstGenerator.natDegree
          carrier.secondGenerator.natDegree :=
      max_le_max
        (natDegree_C_mul_le _ carrier.firstGenerator)
        (natDegree_C_mul_le _ carrier.secondGenerator)
    _ ≤ carrier.degreeBound := le_max_left _ _

theorem AnalyticCrossJuliaCarrier.polynomialFamily_root
    (carrier : AnalyticCrossJuliaCarrier) :
    ∀ᶠ t in 𝓝[≠] carrier.center,
      (carrier.polynomialFamily t).IsRoot (carrier.hiddenEndpoint t) := by
  filter_upwards [carrier.cross_identity] with t ht
  rw [Polynomial.IsRoot.def]
  simp only [AnalyticCrossJuliaCarrier.polynomialFamily,
    crossJuliaPolynomial, eval_sub, eval_mul, eval_C]
  exact sub_eq_zero.mpr ht

theorem AnalyticCrossJuliaCarrier.some_coefficient_active
    (carrier : AnalyticCrossJuliaCarrier) :
    ∃ i : ℕ, i ≤ carrier.degreeBound ∧
      ¬(fun t ↦ (carrier.polynomialFamily t).coeff i) =ᶠ[
        𝓝[≠] carrier.center] (fun _ ↦ 0) := by
  have hfirstBound : carrier.firstIndex ≤ carrier.degreeBound := by
    dsimp [AnalyticCrossJuliaCarrier.degreeBound]
    omega
  have hsecondBound : carrier.secondIndex ≤ carrier.degreeBound := by
    dsimp [AnalyticCrossJuliaCarrier.degreeBound]
    omega
  by_cases hfirst :
      (fun t ↦ (carrier.polynomialFamily t).coeff carrier.firstIndex) =ᶠ[
        𝓝[≠] carrier.center] (fun _ ↦ 0)
  · refine ⟨carrier.secondIndex, hsecondBound, ?_⟩
    intro hsecond
    have hfalse : ∀ᶠ _t in 𝓝[≠] carrier.center, False := by
      filter_upwards [hfirst, hsecond, carrier.endpoint_nonzero] with
          t htFirst htSecond htEndpoint
      have hdet := crossJuliaPolynomial_coefficient_determinant
        carrier.firstGenerator carrier.secondGenerator
        (carrier.endpointValue t) (carrier.endpointDerivative t)
        (carrier.sourceValue t) carrier.firstIndex carrier.secondIndex
      rw [show crossJuliaPolynomial carrier.firstGenerator
          carrier.secondGenerator (carrier.endpointValue t)
            (carrier.endpointDerivative t) (carrier.sourceValue t) =
          carrier.polynomialFamily t by rfl,
        htFirst, htSecond] at hdet
      simp only [zero_mul, sub_self] at hdet
      exact (mul_ne_zero htEndpoint carrier.coefficient_determinant) hdet.symm
    obtain ⟨_t, ht⟩ := Filter.Eventually.exists hfalse
    exact ht
  · exact ⟨carrier.firstIndex, hfirstBound, hfirst⟩

/-- The analytic cross-Julia data construct the generic degree-bounded root
carrier consumed by finite coefficient selection. -/
noncomputable def AnalyticCrossJuliaCarrier.toDegreeBoundedRootCarrier
    (carrier : AnalyticCrossJuliaCarrier) :
    DegreeBoundedAnalyticRootCarrier :=
  { center := carrier.center
    degreeBound := carrier.degreeBound
    polynomialFamily := carrier.polynomialFamily
    branch := carrier.hiddenEndpoint
    coefficient_analytic := fun i _ ↦
      carrier.polynomialFamily_coefficient_analytic i
    eventually_degree_le := by
      filter_upwards [] with t
      exact carrier.polynomialFamily_degree_le t
    branch_differentiable := carrier.hidden_differentiable
    root_identity := carrier.polynomialFamily_root
    some_coefficient_active := carrier.some_coefficient_active }

/-- The hidden endpoint in an analytic cross-Julia relation is meromorphic. -/
theorem AnalyticCrossJuliaCarrier.hiddenEndpoint_meromorphicAt
    (carrier : AnalyticCrossJuliaCarrier) :
    MeromorphicAt carrier.hiddenEndpoint carrier.center := by
  exact carrier.toDegreeBoundedRootCarrier.branch_meromorphicAt

/-- Aggregated cross-Julia meromorphicity surface. -/
theorem analytic_cross_julia_meromorphic_terminal_certificate :
    ∀ carrier : AnalyticCrossJuliaCarrier,
      MeromorphicAt carrier.hiddenEndpoint carrier.center := by
  intro carrier
  exact carrier.hiddenEndpoint_meromorphicAt

end FormalAnalyticCrossJuliaMeromorphic
