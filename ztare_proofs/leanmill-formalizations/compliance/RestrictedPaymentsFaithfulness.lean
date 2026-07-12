/-
Restricted-payments covenant — faithfulness certificate.

PROVENANCE: hand-authored, kernel-checked — NOT an autonomous closure. This is the adversarial companion to
`restricted_payments_covenant.lean` (which IS an autonomous LeanMill closure). Where that file proves the
covenant's safety invariants, this one shows why the faithful permission logic is load-carrying: for each
plausible MIS-reading of the covenant, it exhibits a concrete transaction the misreading PERMITS and the
faithful covenant FORBIDS — the distinguishing witness, mechanized rather than asserted. `#print axioms` on
each theorem is `[propext, Classical.choice, Quot.sound]`; no `sorry`.
-/
import Mathlib

-- Natural-language specification (blueprint): blueprints/restricted_payments_covenant_blueprint.md
-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English intent is argued, not proved.

/-!
The faithful covenant permits a Restricted Payment iff THREE conditions hold together: no Default (a), the
pro-forma coverage test passes (b), and the payment stays strictly under the builder basket (c). Each laundered
reading below is a misreading a human reviewer plausibly misses; each is refuted by a concrete distinguishing
scenario.
-/

namespace RestrictedPaymentsFaithfulness

/-- Faithful covenant permission: (a) ∧ (b) ∧ (c), with (c) a STRICT basket inequality. -/
def Permitted (noDefault fccrPass : Prop) (builderBasket cumulativeRP amount : ℝ) : Prop :=
  noDefault ∧ fccrPass ∧ (cumulativeRP + amount < builderBasket)

/-- Laundered `∧→∨`: permit on ANY one condition. -/
def Permitted_or (noDefault fccrPass : Prop) (builderBasket cumulativeRP amount : ℝ) : Prop :=
  noDefault ∨ fccrPass ∨ (cumulativeRP + amount < builderBasket)

/-- Laundered dropped-(c): omit the builder-basket cap entirely. -/
def Permitted_dropC (noDefault fccrPass : Prop) (_builderBasket _cumulativeRP _amount : ℝ) : Prop :=
  noDefault ∧ fccrPass

/-- Laundered `<→≤`: allow a payment landing exactly at the basket. -/
def Permitted_le (noDefault fccrPass : Prop) (builderBasket cumulativeRP amount : ℝ) : Prop :=
  noDefault ∧ fccrPass ∧ (cumulativeRP + amount ≤ builderBasket)

/-- `∧→∨` waves through a payment by a company IN DEFAULT.
Witness: `noDefault = False`, `fccrPass = True`, basket `1`, prior `0`, amount `0` — the ∨ reading permits
the distribution, the faithful covenant forbids it because condition (a) fails. -/
theorem or_permits_a_defaulted_payment :
    Permitted_or False True 1 0 0 ∧ ¬ Permitted False True 1 0 0 := by
  refine ⟨Or.inr (Or.inl trivial), ?_⟩
  rintro ⟨hnd, _, _⟩
  exact hnd

/-- Dropped-(c) waves through a payment that OVERSPENDS the builder basket.
Witness: (a) and (b) hold, basket `1`, prior `1`, amount `1` — the drop reading permits it, the faithful
covenant forbids it because `1 + 1 < 1` is false. -/
theorem dropC_permits_over_the_basket :
    Permitted_dropC True True 1 1 1 ∧ ¬ Permitted True True 1 1 1 := by
  refine ⟨⟨trivial, trivial⟩, ?_⟩
  rintro ⟨_, _, hlt⟩
  norm_num at hlt

/-- `<→≤` waves through a payment landing EXACTLY at the basket ceiling.
Witness: (a) and (b) hold, basket `1`, prior `0`, amount `1` — `0 + 1 ≤ 1` so the ≤ reading permits it,
`0 + 1 < 1` is false so the faithful covenant forbids it. -/
theorem le_permits_the_exact_boundary :
    Permitted_le True True 1 0 1 ∧ ¬ Permitted True True 1 0 1 := by
  refine ⟨⟨trivial, trivial, by norm_num⟩, ?_⟩
  rintro ⟨_, _, hlt⟩
  norm_num at hlt

end RestrictedPaymentsFaithfulness
