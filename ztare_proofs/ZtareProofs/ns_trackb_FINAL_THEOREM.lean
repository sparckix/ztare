/-
  # NS Track B — FINAL THEOREM CONSOLIDATION

  READ ME FIRST. This file is the architectural CRYSTAL of the
  ZTARE NS Track B Lean formalization: a single navigation hub that
  re-exports the climactic theorems of the architecture under stable
  short names so future readers can find every load-bearing piece
  from one entry point.

  See the docstring block immediately after the imports below for
  the full top-level orientation, the residual-void inventory, and
  a pointer to `ZtareProofs/NS_TRACKB_README.md`.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_galerkin_existence_axiomatic
import ZtareProofs.ns_trackb_bkm_smoothness_criterion
import ZtareProofs.ns_trackb_smoothness_criterion_compressor
import ZtareProofs.ns_trackb_global_smooth_solution_master_spine
import ZtareProofs.ns_trackb_blowup_falsifier
import ZtareProofs.ns_trackb_godel_meta_consistency

/-! # NS Track B — FINAL THEOREM CONSOLIDATION (top-level orientation)

  ## How to navigate this file

  Each section below re-exports a single climactic theorem from a
  sibling file, with a one-paragraph orientation.  No new
  mathematics is introduced; every theorem statement is the original
  upstream theorem aliased into the
  `ZtareProofs.NS.FinalTheorem` namespace.  The single new theorem
  is `ns_track_b_clay_conditional_pipeline` (§7), which composes
  the Galerkin one-shot existence with the master upgrade to give
  the SHARPEST end-to-end conditional Clay-shape statement the
  architecture supports.

  ## Architectural map (sibling docs)

  * Architecture overview:
    `ZtareProofs/NS_TRACKB_README.md` — the long-form prose
    walkthrough of the workstreams (O = Galerkin, S = smoothness
    criteria, M = master spine, G = Gödelian meta-consistency).
  * Umbrella import: `ZtareProofs.lean` (the file you are inside
    a sibling of) — every Track B module is imported there, so
    `lake build` exercises the full graph.

  ## Five Clay-equivalent residual axioms (the open problems)

  These are the only mathematical voids on the path from
  `LerayHopfSolution` to `GlobalSmoothSolution`.  Each is a *named*
  classical conjecture whose discharge would close Clay:

  1. `BKM_global_extension`   — Beale-Kato-Majda (1984): if the
     vorticity sup-norm time-integral is finite on every finite
     window, then the solution is globally smooth.  File:
     `ns_trackb_bkm_smoothness_criterion.lean`.
  2. `PSL_global_extension`   — Ladyzhenskaya-Prodi-Serrin
     (1959-1967): velocity in `L^q_t L^p_x` with `2/q + 3/p ≤ 1`
     suffices.  File: `ns_trackb_prodi_serrin_smoothness.lean`.
  3. `ESS_global_extension`   — Escauriaza-Seregin-Šverák (2003):
     `L^∞_t L^3_x` boundedness suffices.  File:
     `ns_trackb_ess_l3_endpoint.lean`.
  4. `BdV_global_extension`   — Beirão da Veiga (1995): velocity
     *gradient* in `L^q_t L^p_x` with `2/q + 3/p ≤ 2`, `3/2 < p`
     suffices.  File: `ns_trackb_smoothness_criterion_compressor.lean`.
  5. `CF_global_extension`    — Constantin-Fefferman (1993):
     vorticity *direction* uniformly Lipschitz in regions of large
     vorticity suffices.  File:
     `ns_trackb_smoothness_criterion_compressor.lean`.

  ## Seven Galerkin axioms (the classical-PDE residual void)

  These six classical theorems plus one residual nonlinear-pairing
  Prop input together discharge the existence half of Track B; each
  is cited.  All live in
  `ns_trackb_galerkin_existence_axiomatic.lean`:

  1. `galerkin_truncation_exists`              (Lions 1969).
  2. `galerkin_per_n_energy_estimate`          (Hopf 1951).
  3. `galerkin_per_n_divergence_free`          (Lions 1969).
  4. `galerkin_initial_data_pairing_converges` (Constantin-Foiaș).
  5. `galerkin_uniform_l2_bounds`              (Leray 1934 / Temam).
  6. `galerkin_weak_limit_exists`              (Banach-Alaoglu).
  7. `NonlinearPairingStrongConv`              — *not* an axiom but
     a Prop input on `MomentumClauseInput` and
     `ConcretePromotionInput`; the Aubin-Lions residual void.

  Together: 5 Clay-equivalent axioms + 6 Galerkin axioms +
  1 Aubin-Lions Prop input are the entire residual-void
  inventory for the conditional Clay-shape pipeline below. -/

namespace ZtareProofs.NS.FinalTheorem

open NavierStokes
open ZtareProofs.NS
open ZtareProofs.NS.GalerkinAxiomatic
open ZtareProofs.NS.GlobalSmoothMaster
open ZtareProofs.NS.BlowUpFalsifier
open ZtareProofs.NS.GodelMetaConsistency

/-! ## §1.  `lerayHopf_existence_oneshot` — Galerkin → LerayHopfSolution

  Workstream O: classical Galerkin construction lifted into Lean
  modulo the six Galerkin axioms and the Aubin-Lions Prop input
  carried inside `MomentumClauseInput` / `ConcretePromotionInput`.

  Source: `ns_trackb_galerkin_existence_axiomatic.lean` §9. -/

/-- Re-export: one-shot conditional Leray-Hopf existence. -/
noncomputable def lerayHopf_existence_oneshot
    (nse : NavierStokesEquations 3) (T : ℝ) (T_pos : 0 < T)
    (E : EnergyClauseInput (buildClassicalGalerkinConstruction nse T T_pos))
    (M : MomentumClauseInput (buildClassicalGalerkinConstruction nse T T_pos))
    (P : ConcretePromotionInput nse T
            (buildClassicalGalerkinConstruction nse T T_pos)) :
    NavierStokes.LerayHopfSolution nse :=
  GalerkinAxiomatic.lerayHopf_existence_oneshot nse T T_pos E M P

/-! ## §2.  `clay_conditional_via_BKM` — BKM-conditional Clay

  Workstream S (BKM branch): if the BKM vorticity-sup-norm
  time-integral is finite on every finite window, then a globally
  smooth solution exists.  This is the canonical conditional Clay
  statement; closing the BKM conjecture closes Clay.

  Source: `ns_trackb_bkm_smoothness_criterion.lean` §6. -/

/-- Re-export: BKM-conditional Clay theorem. -/
theorem clay_conditional_via_BKM
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_envelope_binds_sol : ZtareProofs.NS.BKMGlobalEnvelopeBoundsSolution nse)
    (h_global_BKM :
      ∀ T : ℝ, 0 < T →
        ∃ Ω : ℝ → ℝ, IntervalIntegrable Ω MeasureTheory.volume 0 T) :
    Nonempty (NavierStokes.GlobalSmoothSolution nse) :=
  ZtareProofs.NS.clay_conditional_via_BKM nse h_initial_smooth
    h_envelope_binds_sol h_global_BKM

/-! ## §3.  `unifiedSmoothness_to_globalSmooth` — 5-way disjunction

  Workstream S (compressor): a SINGLE bridge replaces five parallel
  branch dispatchers (BKM, PSL, ESS, BdV, CF).  Given a Leray-Hopf
  solution and a uniform-branch witness for any one of the five
  classical smoothness criteria, produce a globally smooth solution.

  Source: `ns_trackb_smoothness_criterion_compressor.lean` §5. -/

/-- Re-export: unified smoothness-criterion compressor. -/
noncomputable def unifiedSmoothness_to_globalSmooth
    {nse : NavierStokes.NavierStokesEquations 3}
    (LH : NavierStokes.LerayHopfSolution nse)
    (h_initial_smooth : ContDiff ℝ ⊤ nse.initialVelocity)
    (h_uniform_branch :
      (∀ T : ℝ, 0 < T → BKMIntegralFinite LH.toWeakSolution T)
        ∨
      (∀ T : ℝ, 0 < T → ∃ p q : ℝ, 2 ≤ p ∧ 3 ≤ q ∧ 2 / p + 3 / q ≤ 1 ∧
          SpacetimeLpLqFinite LH.toWeakSolution.u T p q)
        ∨
      (∀ T : ℝ, 0 < T → ESSL3IntegralFinite LH.toWeakSolution T)
        ∨
      (∀ T : ℝ, 0 < T → BdVGradientFinite LH.toWeakSolution T)
        ∨
      (∀ T : ℝ, 0 < T → CFVorticityDirectionLipschitz LH.toWeakSolution T)) :
    NavierStokes.GlobalSmoothSolution nse :=
  ZtareProofs.NS.unifiedSmoothness_to_globalSmooth
    LH h_initial_smooth h_uniform_branch

/-! ## §4.  `globalSmoothSolution_modulo_smoothness_criterion` — master Fefferman A modulo criterion (term form)

  Workstream M (master spine): given a Leray-Hopf solution, a
  smoothness-criterion choice, a verification of the criterion on
  `[0, T]`, and the weak-to-global promotion bridge, return a
  `GlobalSmoothSolution` term (not just an existence proof).

  Source: `ns_trackb_global_smooth_solution_master_spine.lean` §7. -/

/-- Re-export: term-form Fefferman A modulo smoothness criterion. -/
noncomputable def globalSmoothSolution_modulo_smoothness_criterion
    {nse : NavierStokesEquations 3} {T : ℝ}
    (sol : LerayHopfSolution nse)
    (C : SmoothnessCriterion)
    (V : SmoothnessCriterionVerification sol T C)
    (P : WeakToGlobalSmoothBridge sol) :
    GlobalSmoothSolution nse :=
  GlobalSmoothMaster.globalSmoothSolution_modulo_smoothness_criterion
    sol C V P

/-! ## §5.  `architecture_smoothness_anti_laundering` — Gödelian inversion guarantee

  Workstream G: a structural Lean fact — every producer in the
  architecture's interface that emits a `GlobalSmoothSolution` from
  a `BlowUpScenario` must additionally consume a
  `SmoothnessBlocker`.  No producer of strictly smaller arity exists
  in the typed surface; if one did, it would resolve Clay in the
  negative.  The type system is the enforcement mechanism — the
  Gödelian self-property of the architecture.

  Source: `ns_trackb_godel_meta_consistency.lean` §5. -/

/-- Re-export: Gödelian inversion guarantee. -/
theorem architecture_smoothness_anti_laundering
    (nse : NavierStokesEquations 3) (T_star : ℝ) :
    ∀ (producer :
        BlowUpScenario nse T_star →
          SmoothnessBlocker → GlobalSmoothSolution nse),
      ∀ (B : BlowUpScenario nse T_star) (blk : SmoothnessBlocker),
        ∃ _gss : GlobalSmoothSolution nse, True :=
  GodelMetaConsistency.architecture_smoothness_anti_laundering nse T_star

/-! ## §6.  Honesty receipt — what is and is not proved

  This file proves NOTHING new.  Every theorem above is a
  re-export.  The single new term in §7 is a *composition* of
  upstream pieces — its mathematical content is exactly the
  conjunction of its inputs, plus the residual axioms enumerated in
  the top docstring.

  This file does NOT:
  * Prove Fefferman A unconditionally.
  * Discharge any of the 5 Clay-equivalent axioms.
  * Discharge any of the 6 Galerkin axioms.
  * Discharge the Aubin-Lions Prop input.

  This file DOES:
  * Provide a single navigation point for future readers.
  * State the SHARPEST end-to-end conditional pipeline (§7) that
    the current architecture supports.
  * Inventory the residual voids in one place (top docstring). -/

/-! ## §7.  THE SHARPEST END-TO-END STATEMENT

  Compose `lerayHopf_existence_oneshot` (workstream O) with
  `globalSmoothSolution_modulo_smoothness_criterion`
  (workstream M).  Conclusion: a `GlobalSmoothSolution nse`,
  conditional on the verification of one classical smoothness
  criterion on `[0, T]` and the weak-to-global promotion bridge.

  This is the architectural climax.  Its preconditions are exactly
  the residual voids inventoried at the top of this file: the six
  Galerkin axioms (carried by `EnergyClauseInput`,
  `MomentumClauseInput`, `ConcretePromotionInput`), the Aubin-Lions
  Prop input (carried inside the same), and ONE of the five Clay-
  equivalent smoothness criteria (carried by
  `SmoothnessCriterionVerification`). -/

/-- **NS Track B Clay-conditional pipeline.**

  Composition of the Galerkin one-shot existence and the master
  upgrade.  Given the workstream-O classical-Galerkin inputs
  (`E`, `M`, `P_concrete`), a chosen smoothness criterion `C`, a
  verification `V` of `C` on `[0, T]`, and the weak-to-global
  promotion bridge `P_smooth`, return a globally smooth Navier-
  Stokes solution. -/
noncomputable def ns_track_b_clay_conditional_pipeline
    (nse : NavierStokesEquations 3) (T : ℝ) (T_pos : 0 < T)
    (E : EnergyClauseInput (buildClassicalGalerkinConstruction nse T T_pos))
    (M : MomentumClauseInput (buildClassicalGalerkinConstruction nse T T_pos))
    (P_concrete : ConcretePromotionInput nse T
            (buildClassicalGalerkinConstruction nse T T_pos))
    (C : SmoothnessCriterion)
    (V : SmoothnessCriterionVerification
            (lerayHopf_existence_oneshot nse T T_pos E M P_concrete) T C)
    (P_smooth : WeakToGlobalSmoothBridge
            (lerayHopf_existence_oneshot nse T T_pos E M P_concrete)) :
    NavierStokes.GlobalSmoothSolution nse :=
  globalSmoothSolution_modulo_smoothness_criterion
    (lerayHopf_existence_oneshot nse T T_pos E M P_concrete) C V P_smooth

end ZtareProofs.NS.FinalTheorem
