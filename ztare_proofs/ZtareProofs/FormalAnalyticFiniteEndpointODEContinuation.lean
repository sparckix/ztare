import Mathlib.Analysis.Analytic.Polynomial
import Mathlib.Analysis.Complex.RemovableSingularity
import Mathlib.Tactic

/-!
# Finite-endpoint continuation for controlled polynomial ODEs

A punctured holomorphic solution of `y' = c(z) * p(y)` that converges to a
finite state extends analytically through the missing endpoint.  The same ODE
holds on a full neighborhood of the filled point; this is stronger than a
bare removable-singularity conclusion.
-/

namespace FormalAnalyticFiniteEndpointODEContinuation

open Filter Polynomial Set
open scoped Topology

/-- Punctured controlled-polynomial trajectory data with a finite endpoint
limit.  No extension or derivative at the endpoint is stored. -/
structure FiniteEndpointODECarrier (p : ℂ[X]) where
  center : ℂ
  state : ℂ
  coefficient : ℂ → ℂ
  branch : ℂ → ℂ
  coefficient_analytic : AnalyticAt ℂ coefficient center
  branch_differentiable : ∀ᶠ z in 𝓝[≠] center,
    DifferentiableAt ℂ branch z
  branch_ode : ∀ᶠ z in 𝓝[≠] center,
    HasDerivAt branch (coefficient z * p.eval (branch z)) z
  branch_tendsto : Tendsto branch (𝓝[≠] center) (𝓝 state)

/-- Exact output of finite-endpoint continuation. -/
def FiniteEndpointODEOutcome {p : ℂ[X]}
    (carrier : FiniteEndpointODECarrier p) : Prop :=
  ∃ extension : ℂ → ℂ,
    carrier.branch =ᶠ[𝓝[≠] carrier.center] extension ∧
    AnalyticAt ℂ extension carrier.center ∧
    extension carrier.center = carrier.state ∧
    ∀ᶠ z in 𝓝 carrier.center,
      HasDerivAt extension
        (carrier.coefficient z * p.eval (extension z)) z

/-- Filling the finite endpoint constructs an analytic extension and the
controlled-polynomial ODE persists across the filled point. -/
theorem FiniteEndpointODECarrier.finiteEndpointODEOutcome
    {p : ℂ[X]} (carrier : FiniteEndpointODECarrier p) :
    FiniteEndpointODEOutcome carrier := by
  let extension : ℂ → ℂ :=
    Function.update carrier.branch carrier.center carrier.state
  have hextensionContinuous : ContinuousAt extension carrier.center := by
    exact continuousAt_update_same.mpr carrier.branch_tendsto
  have hoverlap : carrier.branch =ᶠ[𝓝[≠] carrier.center] extension := by
    filter_upwards [self_mem_nhdsWithin] with z hz
    have hzc : z ≠ carrier.center := by
      simpa only [mem_compl_iff, mem_singleton_iff] using hz
    exact (Function.update_of_ne hzc carrier.state carrier.branch).symm
  have hextensionDifferentiable :
      ∀ᶠ z in 𝓝[≠] carrier.center, DifferentiableAt ℂ extension z := by
    filter_upwards [carrier.branch_differentiable,
      self_mem_nhdsWithin] with z hdiff hz
    have hzc : z ≠ carrier.center := by
      simpa only [mem_compl_iff, mem_singleton_iff] using hz
    apply DifferentiableAt.congr_of_eventuallyEq hdiff
    filter_upwards [eventually_ne_nhds hzc] with w hw
    exact Function.update_of_ne hw carrier.state carrier.branch
  have hextensionAnalytic : AnalyticAt ℂ extension carrier.center :=
    Complex.analyticAt_of_differentiable_on_punctured_nhds_of_continuousAt
      hextensionDifferentiable hextensionContinuous
  have hpuncODE :
      (fun z ↦ deriv extension z) =ᶠ[𝓝[≠] carrier.center]
        (fun z ↦ carrier.coefficient z * p.eval (extension z)) := by
    filter_upwards [carrier.branch_ode, hoverlap,
      self_mem_nhdsWithin] with z hODE hvalue hz
    have hzc : z ≠ carrier.center := by
      simpa only [mem_compl_iff, mem_singleton_iff] using hz
    have hlocal : carrier.branch =ᶠ[𝓝 z] extension := by
      filter_upwards [eventually_ne_nhds hzc] with w hw
      exact (Function.update_of_ne hw carrier.state carrier.branch).symm
    have hderiv : deriv carrier.branch z = deriv extension z :=
      EventuallyEq.deriv_eq hlocal
    calc
      deriv extension z = deriv carrier.branch z := hderiv.symm
      _ = carrier.coefficient z * p.eval (carrier.branch z) := hODE.deriv
      _ = carrier.coefficient z * p.eval (extension z) := by rw [hvalue]
  have hderivAnalytic : AnalyticAt ℂ (deriv extension) carrier.center :=
    hextensionAnalytic.deriv
  have hrhsAnalytic : AnalyticAt ℂ
      (fun z ↦ carrier.coefficient z * p.eval (extension z))
      carrier.center :=
    carrier.coefficient_analytic.mul
      (hextensionAnalytic.aeval_polynomial p)
  have hfullODE :
      (fun z ↦ deriv extension z) =ᶠ[𝓝 carrier.center]
        (fun z ↦ carrier.coefficient z * p.eval (extension z)) :=
    (hderivAnalytic.continuousAt.eventuallyEq_nhds_iff_eventuallyEq_nhdsNE
      hrhsAnalytic.continuousAt).mp hpuncODE
  have hODE : ∀ᶠ z in 𝓝 carrier.center,
      HasDerivAt extension
        (carrier.coefficient z * p.eval (extension z)) z := by
    filter_upwards [hextensionAnalytic.eventually_analyticAt, hfullODE] with
        z hz hderiv
    exact hz.differentiableAt.hasDerivAt.congr_deriv hderiv
  refine ⟨extension, hoverlap, hextensionAnalytic, ?_, hODE⟩
  simp [extension]

/-- Aggregated finite-endpoint continuation terminal. -/
theorem analytic_finite_endpoint_ode_continuation_terminal_certificate :
    ∀ (p : ℂ[X]) (carrier : FiniteEndpointODECarrier p),
      FiniteEndpointODEOutcome carrier := by
  intro p carrier
  exact carrier.finiteEndpointODEOutcome

end FormalAnalyticFiniteEndpointODEContinuation
