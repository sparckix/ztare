import Mathlib.Tactic
import ZtareProofs.ns_trackb_lean_dojo_energy_bridge
import ZtareProofs.ns_trackb_finite_galerkin_energy_estimate
import ZtareProofs.ns_trackb_galerkin_stream_construction

/-!
# NS Track B end-to-end spine

This file composes the four workstream artifacts into a single
end-to-end theorem skeleton showing the structural reduction from
Galerkin truncation to Leray-Hopf energy inequality:

  Workstream #3 (finite-N energy estimate) — `ns_trackb_finite_galerkin_energy_estimate.lean`
       ↓ supplies `energy_estimate` field of GalerkinStreamData
  Workstream #4 (Galerkin stream construction) — `ns_trackb_galerkin_stream_construction.lean`
       ↓ supplies typed companion + GalerkinEnergyInterpretation
  Bridge (this session) — `ns_trackb_lean_dojo_energy_bridge.lean`
       ↓ discharges Leray-Hopf energy_inequality clause given LSC + InitialEnergyMatch
  Workstream #1 (LSC primitive — IN PROGRESS) — `ns_trackb_l2_lsc_primitive.lean`
       ↓ supplies LSC hypothesis from weak-L² convergence
  ⇒ Leray-Hopf energy_inequality discharged for the limit solution

Until workstream #1 lands, the LSC and InitialEnergyMatch are taken
as explicit Prop hypotheses. The composition compiles without them
but produces only a conditional statement.

This file is the LOAD-BEARING ORGANIZATIONAL ARTIFACT. The
mathematical content is in the imported files; here we show that the
pieces wire correctly.
-/

namespace ZtareProofs.NS

noncomputable section

/-! ## End-to-end composition theorem

Given:
- Galerkin stream data G (workstream #4, requires finite-N energy estimate from #3)
- A typed bound data over the constructed stream (computed from a Tendsto fact)
- Galerkin sequence with initial energy E_0
- LSC hypothesis (workstream #1, future)
- InitialEnergyMatch hypothesis

Conclude: Leray-Hopf energy inequality at time T for the limit. -/

theorem energy_inequality_via_spine
    (G : GalerkinStreamData)
    [_hNeBot : (Filter.comap (id : ℕ → ℕ) Filter.atTop).NeBot]
    (M : LeraySelfTaxMeasureValuedOutputLimitSource
            (LeraySelfTaxProfilePriceStream.ofGalerkinData G))
    (boundData :
      LeraySelfTaxRelaxedOutputPriceLiminfBoundData M (id : ℕ → ℕ)
        (fun a =>
          (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixPriceForComponent
            LeraySelfTaxPriceComponent.selfTax a)
        (fun a =>
          (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixPriceForComponent
            LeraySelfTaxPriceComponent.crossDefect a)
        (fun a =>
          (LeraySelfTaxProfilePriceStream.ofGalerkinData G).prefixPriceForComponent
            LeraySelfTaxPriceComponent.coherence a))
    (uInf : VelocityFieldInterface 3)
    (interp_match :
      (LeraySelfTaxProfilePriceStream.ofGalerkinData G).selfTaxLimitPrice
        = (G.galerkinSeq 0).kineticEnergy 0)
    (lsc : GalerkinEnergyLSC G.galerkinSeq uInf G.nu G.T)
    (initEnergyMatch : InitialEnergyMatch G.galerkinSeq uInf) :
    uInf.kineticEnergy G.T + 2 * G.nu * uInf.cumulative_dissipation G.T
      ≤ uInf.kineticEnergy 0 := by
  -- Build the Galerkin energy interpretation from G + the limit-match hypothesis.
  have interp :
      GalerkinEnergyInterpretation
        (LeraySelfTaxProfilePriceStream.ofGalerkinData G)
        G.galerkinSeq G.nu G.T := {
    prefix_eq_galerkin_lhs := fun n => rfl
    limit_eq_initial_energy := fun n => by
      rw [interp_match]
      exact (initEnergyMatch 0).symm.trans (initEnergyMatch n)
  }
  -- Discharge via the bridge.
  exact energy_inequality_at_T_from_typed_companion
    boundData G.galerkinSeq uInf G.nu G.T interp lsc initEnergyMatch

/-! ## Diagnostic: count remaining open obligations

After composing all four workstreams, the obligations remaining as
explicit Prop inputs (not derivable from typed companions or
finite-N estimates) are:

1. `M : LeraySelfTaxMeasureValuedOutputLimitSource (ofGalerkinData G)`:
   the measure-valued output limit source instance over the stream.
   This requires building the defect source + relaxed prices for the
   actual Galerkin sequence — substantial PDE work tied to weak limits.

2. `boundData : LeraySelfTaxRelaxedOutputPriceLiminfBoundData ...`:
   the typed bound data, constructible from `fromTendsto` GIVEN
   convergence of prefix prices to the relaxed prices. This is the
   classical Galerkin → Leray-Hopf convergence step.

3. `lsc : GalerkinEnergyLSC ...`:
   LSC of the Galerkin energy LHS at the limit solution. WORKSTREAM #1
   target. Mathlib has `lintegral_enorm_le_liminf_of_tendsto` +
   Vitali/UnifTight which can substitute.

4. `initEnergyMatch : InitialEnergyMatch ...`:
   the limit's initial energy equals the truncations'. Trivial when
   the Galerkin truncation preserves initial data: the spectral
   projection P_n satisfies `‖P_n u_0 - u_0‖_L² → 0` and KE is
   continuous in L².

5. `interp_match` between `selfTaxLimitPrice` and `(galerkinSeq 0).kineticEnergy 0`:
   bookkeeping; trivial after fixing convention `E_0 := KE(u_0, 0)`.

Obligations #1, #2, #3 are the genuinely PDE content. The architecture
reduces an opaque "prove Leray-Hopf energy inequality" to these three
named obligations, each of which is independently formalizable. -/

end

end ZtareProofs.NS
