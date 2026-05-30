import Mathlib.Tactic
import ZtareProofs.ns_gp216_bridge_composition_receipt

/-!
# GP216 Millennium endpoint

This file is the current Track B/GP216 Clay-facing endpoint.

It does not assert that the Navier-Stokes PDE estimates have been proved.
Instead, it states the exact receipt-family theorem: once the analytic work
constructs a `GP216BridgeCompositionReceipt` for each smooth finite-energy
initial datum, with the receipt tied to that datum, global regularity and
declared-candidate exclusion follow mechanically.
-/

namespace ZtareProofs.NS

noncomputable section

/-- The global-regularity statement delivered by a GP216 receipt family. -/
def GP216ClayRegularityStatement
    (P : GP216ClayProblemReceipt) : Prop :=
  ∀ u0 : SmoothNSInitialData,
    (((P.receipt_of_initial_data u0).profileLipschitzObligation)
      |>.evolution_of_initial_data u0).globalRegular

/-- Declared survivor/global-bridge candidates are excluded for every datum
covered by the GP216 receipt family. -/
def GP216ClayNoDeclaredCandidateStatement
    (P : GP216ClayProblemReceipt) : Prop :=
  ∀ u0 : SmoothNSInitialData,
    ¬ GP216GlobalBridgeCandidateWithinDeclaredScope
      (P.receipt_of_initial_data u0)

/-- A GP216 receipt family closes the formal global-regularity endpoint. -/
theorem gp216_receipt_family_closes_clay_regular_endpoint
    (P : GP216ClayProblemReceipt) :
    GP216ClayRegularityStatement P := by
  intro u0
  exact global_regular_of_gp216_clay_problem_receipt P u0

/-- A GP216 receipt family excludes every declared bridge-candidate escape. -/
theorem gp216_receipt_family_excludes_declared_candidates
    (P : GP216ClayProblemReceipt) :
    GP216ClayNoDeclaredCandidateStatement P := by
  intro u0
  exact no_gp216_global_bridge_candidate_of_composition_receipt
    (P.receipt_of_initial_data u0)

/-- Current top endpoint: global regularity plus declared-candidate exclusion,
conditional only on the GP216 receipt family. -/
theorem gp216_receipt_family_closes_regularity_and_declared_candidates
    (P : GP216ClayProblemReceipt) :
    GP216ClayRegularityStatement P ∧
      GP216ClayNoDeclaredCandidateStatement P := by
  exact
    ⟨gp216_receipt_family_closes_clay_regular_endpoint P,
      gp216_receipt_family_excludes_declared_candidates P⟩

end

end ZtareProofs.NS
