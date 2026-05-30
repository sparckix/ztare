import Mathlib.Tactic
import ZtareProofs.ns_beat_backscatter_coherence_charge

/-!
# GP-216 positive coherence price kernel

This file isolates the algebra behind the Phase 5IM/5IH lesson:
branch prices alone do not glue profiles, but branch prices plus the positive
parts of every cross/coherence term dominate the assembled quadratic tax.

The statement is deliberately scalar.  A PDE proof still has to instantiate the
symbols as fixed LP/Bony/Leray profile components and prove lower
semicontinuity of the declared prices.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Three-component quadratic expansion of an assembled self-tax proxy. -/
def threeProfileAssembledTax
    (branchA branchB mixedC crossAB crossAC crossBC : Real) : Real :=
  branchA + branchB + mixedC + 2 * crossAB + 2 * crossAC + 2 * crossBC

/-- Declared price that charges only positive coherence; negative coherence is
not profitable and need not be priced as positive payoff. -/
def threeProfilePositiveCoherencePrice
    (branchA branchB mixedC crossAB crossAC crossBC : Real) : Real :=
  branchA + branchB + mixedC +
    2 * positivePart crossAB +
      2 * positivePart crossAC +
        2 * positivePart crossBC

lemma le_positivePart (x : Real) : x ≤ positivePart x := by
  unfold positivePart
  exact le_max_left x 0

/-- Charging the positive parts of all cross/coherence channels dominates the
full quadratic expansion, independent of signs of the cross terms. -/
theorem three_profile_tax_le_positive_coherence_price
    (branchA branchB mixedC crossAB crossAC crossBC : Real) :
    threeProfileAssembledTax
        branchA branchB mixedC crossAB crossAC crossBC ≤
      threeProfilePositiveCoherencePrice
        branchA branchB mixedC crossAB crossAC crossBC := by
  unfold threeProfileAssembledTax threeProfilePositiveCoherencePrice
  nlinarith [le_positivePart crossAB,
    le_positivePart crossAC,
    le_positivePart crossBC]

/-- The single-cross raw expansion is also charged by the positive-coherence
price.  This is the valid orientation of the graph-surfaced symmetry: the
positive-part ledger dominates the raw expansion, not conversely. -/
theorem three_profile_raw_cross_budget_le_positive_coherence_price
    (branchA branchB mixedC crossAB crossAC crossBC : Real) :
    branchA + branchB + mixedC + crossAB + crossAC + crossBC ≤
      threeProfilePositiveCoherencePrice
        branchA branchB mixedC crossAB crossAC crossBC := by
  unfold threeProfilePositiveCoherencePrice
  nlinarith [le_positivePart crossAB,
    le_positivePart crossAC,
    le_positivePart crossBC,
    positivePart_nonnegative crossAB,
    positivePart_nonnegative crossAC,
    positivePart_nonnegative crossBC]

/-- Raw cross terms are not a valid upper bound for the positive-coherence
price.  Any theorem with this orientation has smuggled away the factor-two
positive-part charge on profitable coherence channels. -/
theorem not_three_profile_positive_coherence_price_le_raw_cross_budget :
    ¬ ∀ branchA branchB mixedC crossAB crossAC crossBC : Real,
      threeProfilePositiveCoherencePrice
          branchA branchB mixedC crossAB crossAC crossBC ≤
        branchA + branchB + mixedC + crossAB + crossAC + crossBC := by
  intro h
  have hbad := h 0 0 0 1 0 0
  unfold threeProfilePositiveCoherencePrice positivePart at hbad
  norm_num at hbad

/-- A prefix stream for the positive-coherence kernel. -/
structure PositiveCoherenceKernelStream where
  branchA : ℕ → Real
  branchB : ℕ → Real
  mixedC : ℕ → Real
  crossAB : ℕ → Real
  crossAC : ℕ → Real
  crossBC : ℕ → Real

def positiveCoherencePrefixTax
    (S : PositiveCoherenceKernelStream) (n : ℕ) : Real :=
  threeProfileAssembledTax
    (S.branchA n) (S.branchB n) (S.mixedC n)
    (S.crossAB n) (S.crossAC n) (S.crossBC n)

def positiveCoherencePrefixPrice
    (S : PositiveCoherenceKernelStream) (n : ℕ) : Real :=
  threeProfilePositiveCoherencePrice
    (S.branchA n) (S.branchB n) (S.mixedC n)
    (S.crossAB n) (S.crossAC n) (S.crossBC n)

theorem positive_coherence_prefix_tax_le_price
    (S : PositiveCoherenceKernelStream) (n : ℕ) :
    positiveCoherencePrefixTax S n ≤ positiveCoherencePrefixPrice S n :=
  three_profile_tax_le_positive_coherence_price
    (S.branchA n) (S.branchB n) (S.mixedC n)
    (S.crossAB n) (S.crossAC n) (S.crossBC n)

/-- If the positive-coherence price prefixes are bounded, then the assembled
tax prefixes are bounded.  Therefore an unbounded assembled-tax sequence is a
falsifier of bounded full-price closure, not of the positive-coherence charge
itself. -/
theorem no_unbounded_tax_with_bounded_positive_coherence_price
    (S : PositiveCoherenceKernelStream)
    {priceBound : Real}
    (hbounded : ∀ n, positiveCoherencePrefixPrice S n ≤ priceBound)
    (hunboundedTax : ∀ B : Real, ∃ n, B < positiveCoherencePrefixTax S n) :
    False := by
  rcases hunboundedTax priceBound with ⟨n, hn⟩
  have htax_le : positiveCoherencePrefixTax S n ≤ priceBound :=
    le_trans (positive_coherence_prefix_tax_le_price S n) (hbounded n)
  exact not_lt_of_ge htax_le hn

end

end ZtareProofs.NS
