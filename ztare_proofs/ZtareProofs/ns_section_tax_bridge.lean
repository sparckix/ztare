import Mathlib.Tactic
import ZtareProofs.ns_eigenframe_poincare_section
import ZtareProofs.ns_marginal_tax_rate
import ZtareProofs.ns_section_dichotomy

namespace ZtareProofs

/-!
`ns_section_tax_bridge` connects the clean scalar compression

  m(E) = L(E) / G(E)

back to the eigenframe return section and the live dichotomy. This is the
cheapest way to keep tightening the branch without inventing new geometry.
-/

/-- Scalar tax dominance on a section witness. -/
def witnessTaxDominance (C : EigenframeCycleWitness) : Prop :=
  C.dangerGain < C.resetLoss

/-- Scalar non-dominance on a section witness. -/
def witnessTaxNonDominance (C : EigenframeCycleWitness) : Prop :=
  C.resetLoss ≤ C.dangerGain

/--
If the witness-level marginal tax rate exceeds `1`, then the witness is
loss-dominant.
-/
theorem witness_loss_dominance_of_tax_rate
    {C : EigenframeCycleWitness}
    (hgain : 0 < C.dangerGain)
    (htax : 1 < marginalTaxRate (fun _ => C.dangerGain) (fun _ => C.resetLoss) C.entry.peak) :
    witnessTaxDominance C := by
  unfold witnessTaxDominance
  exact loss_gt_gain_of_marginal_tax_gt_one hgain htax

/--
If the witness-level marginal tax rate is at most `1`, the witness stays
non-dominant.
-/
theorem witness_non_dominance_of_tax_rate
    {C : EigenframeCycleWitness}
    (hgain : 0 < C.dangerGain)
    (htax : marginalTaxRate (fun _ => C.dangerGain) (fun _ => C.resetLoss) C.entry.peak ≤ 1) :
    witnessTaxNonDominance C := by
  unfold witnessTaxNonDominance
  exact loss_le_gain_of_marginal_tax_le_one hgain htax

/--
Section-level tax dominance route.

If every sufficiently intense return has witness-level tax rate above `1`, then
the section resolves on the loss-dominant side.
-/
theorem eventual_loss_dominance_of_section_tax_rate
    {S : EigenframeSection} {EStar : Real}
    (htax :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        1 < marginalTaxRate (fun _ => C.dangerGain) (fun _ => C.resetLoss) C.entry.peak)
    (hgain :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak → 0 < C.dangerGain) :
    eventualLossDominanceOnSection S (highIntensityEntry EStar) := by
  intro C hhigh
  exact le_of_lt (witness_loss_dominance_of_tax_rate (hgain C hhigh) (htax C hhigh))

/--
Rival side from a witness-level non-dominant subsequence.
-/
def witnessNonDominantSubsequence (Seq : CycleSeq) : Prop :=
  ∀ n : Nat, witnessTaxNonDominance (Seq n)

/--
If a sequence is both profitable-shrinking and tax-non-dominant at every step,
it is a fully live scalar rival to the exhaust-horizon route.
-/
def scalarFractalRival (Seq : CycleSeq) : Prop :=
  profitableShrinkingSubsequence Seq ∧ witnessNonDominantSubsequence Seq

/--
Target shape for the scalar bridge.
-/
theorem section_tax_bridge_target_shape
    {S : EigenframeSection} {EStar : Real} {_Seq : CycleSeq}
    (hleft :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak →
        1 < marginalTaxRate (fun _ => C.dangerGain) (fun _ => C.resetLoss) C.entry.peak)
    (hgain :
      ∀ C : EigenframeCycleWitness, EStar ≤ C.entry.peak → 0 < C.dangerGain) :
    eventualLossDominanceOnSection S (highIntensityEntry EStar) := by
  exact eventual_loss_dominance_of_section_tax_rate hleft hgain

end ZtareProofs
