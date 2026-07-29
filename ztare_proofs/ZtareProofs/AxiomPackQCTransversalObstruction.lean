import Mathlib.Tactic

/-!
# Cyclic-transversal obstruction for the `[50,20,14]` QC graph family

This file isolates the combinatorial core of the obstruction.  A transversal
of the five residue classes modulo `5` is encoded by an arbitrary phase
function `Fin 5 → ZMod 5`.  The five cyclic edge differences cannot all be
different: their quotient heights sum to `-1`, whereas a permutation of
`ZMod 5` sums to `0`.
-/

namespace AxiomPackQCTransversalObstruction

open scoped BigOperators symmDiff

abbrev Residue := Fin 5
abbrev Phase := Residue → ZMod 5
abbrev Position := ZMod 25

/-- Cyclic successor on the five residue classes. -/
def nextResidue (r : Residue) : Residue :=
  ⟨(r.val + 1) % 5, Nat.mod_lt _ (by norm_num)⟩

/-- The carry introduced when the chosen representatives cycle from `4` to `0`. -/
def carry (r : Residue) : ZMod 5 :=
  if r.val = 4 then 1 else 0

/-- Quotient height of the cyclic difference between consecutive transversal points. -/
def quotientDifference (φ : Phase) (r : Residue) : ZMod 5 :=
  φ (nextResidue r) - φ r - carry r

/-- Integer multiplication by `5`, viewed additively in `ZMod 25`. -/
def integerTimesFive : ℤ →+ Position where
  toFun z := (z : Position) * 5
  map_zero' := by simp
  map_add' x y := by push_cast; ring

theorem integerTimesFive_five : integerTimesFive 5 = 0 := by
  decide

/-- The additive embedding of quotient heights into the `5`-torsion subgroup
of `ZMod 25`. -/
def liftHeightHom : ZMod 5 →+ Position :=
  ZMod.lift 5 ⟨integerTimesFive, integerTimesFive_five⟩

/-- Multiplication by `5` lifts a quotient height into the kernel of reduction
modulo `5`. -/
def liftHeight (q : ZMod 5) : Position :=
  liftHeightHom q

theorem liftHeight_eq_five_mul_val (q : ZMod 5) :
    liftHeight q = 5 * (q.val : Position) := by
  calc
    liftHeight q = liftHeight (((q.val : ℤ) : ZMod 5)) := by
      congr 1
      change q = (q.val : ZMod 5)
      exact q.natCast_zmod_val.symm
    _ = integerTimesFive (q.val : ℤ) := by
      exact ZMod.lift_coe 5 ⟨integerTimesFive, integerTimesFive_five⟩ (q.val : ℤ)
    _ = 5 * (q.val : Position) := by
      simp [integerTimesFive, mul_comm]

@[simp]
theorem liftHeight_sub (q₁ q₂ : ZMod 5) :
    liftHeight (q₁ - q₂) = liftHeight q₁ - liftHeight q₂ :=
  liftHeightHom.map_sub q₁ q₂

@[simp]
theorem liftHeight_one : liftHeight (1 : ZMod 5) = (5 : Position) := by
  change ZMod.lift 5 ⟨integerTimesFive, integerTimesFive_five⟩ ((1 : ℤ) : ZMod 5) = 5
  rw [ZMod.lift_coe]
  norm_num [integerTimesFive]

/-- Reduction from positions modulo `25` to residues modulo `5`. -/
def reduceModFive : Position →+* ZMod 5 :=
  ZMod.castHom (by norm_num : 5 ∣ 25) (ZMod 5)

@[simp]
theorem reduce_liftHeight (q : ZMod 5) : reduceModFive (liftHeight q) = 0 := by
  rw [liftHeight_eq_five_mul_val]
  rw [map_mul]
  have hfive : reduceModFive (5 : Position) = 0 := by decide
  rw [hfive, zero_mul]

/-- The point in `ZMod 25` selected by residue `r` and phase `φ r`. -/
def transversalPoint (φ : Phase) (r : Residue) : Position :=
  (r.val : Position) + liftHeight (φ r)

@[simp]
theorem reduce_transversalPoint (φ : Phase) (r : Residue) :
    reduceModFive (transversalPoint φ r) = (r.val : ZMod 5) := by
  simp only [transversalPoint, map_add, map_natCast, reduce_liftHeight, add_zero]

/-- Cyclic edge difference between consecutive selected points. -/
def cyclicDifference (φ : Phase) (r : Residue) : Position :=
  transversalPoint φ (nextResidue r) - transversalPoint φ r

theorem cyclicDifference_eq (φ : Phase) (r : Residue) :
    cyclicDifference φ r = 1 + liftHeight (quotientDifference φ r) := by
  fin_cases r <;>
    simp [cyclicDifference, transversalPoint, nextResidue, quotientDifference, carry,
      liftHeight_sub, liftHeight_one] <;> ring

theorem transversalPoint_injective (φ : Phase) :
    Function.Injective (transversalPoint φ) := by
  intro r s hrs
  have hreduce := congrArg reduceModFive hrs
  rw [reduce_transversalPoint, reduce_transversalPoint] at hreduce
  apply Fin.ext
  have hval := congrArg ZMod.val hreduce
  simpa [ZMod.val_natCast, Nat.mod_eq_of_lt r.isLt, Nat.mod_eq_of_lt s.isLt] using hval

@[simp]
theorem reduce_cyclicDifference (φ : Phase) (r : Residue) :
    reduceModFive (cyclicDifference φ r) = 1 := by
  rw [cyclicDifference_eq]
  simp only [map_add, map_one, reduce_liftHeight, add_zero]

theorem nextResidue_bijective : Function.Bijective nextResidue := by
  decide

theorem sum_carry : ∑ r : Residue, carry r = (1 : ZMod 5) := by
  decide

theorem sum_all_zmod_five : ∑ q : ZMod 5, q = 0 := by
  decide

theorem sum_quotientDifference (φ : Phase) :
    ∑ r : Residue, quotientDifference φ r = (-1 : ZMod 5) := by
  have hshift : (∑ r : Residue, φ (nextResidue r)) = ∑ r : Residue, φ r :=
    nextResidue_bijective.sum_comp φ
  simp only [quotientDifference, Finset.sum_sub_distrib]
  rw [hshift, sum_carry]
  abel

/-- Two distinct cyclic edges of every residue transversal have the same
quotient height.  This is the non-enumerative pigeonhole at the center of the
QC-family obstruction. -/
theorem exists_distinct_equal_quotientDifference (φ : Phase) :
    ∃ r s : Residue, r ≠ s ∧ quotientDifference φ r = quotientDifference φ s := by
  have hnot : ¬ Function.Injective (quotientDifference φ) := by
    intro hinj
    have hbij : Function.Bijective (quotientDifference φ) :=
      (Fintype.bijective_iff_injective_and_card _).2 ⟨hinj, by simp⟩
    have hperm : (∑ r : Residue, quotientDifference φ r) = ∑ q : ZMod 5, q :=
      hbij.sum_comp (fun q : ZMod 5 ↦ q)
    rw [sum_quotientDifference, sum_all_zmod_five] at hperm
    have hminus : (-1 : ZMod 5) ≠ 0 := by decide
    exact hminus hperm
  rw [Function.not_injective_iff] at hnot
  obtain ⟨r, s, hrs, hne⟩ := hnot
  exact ⟨r, s, hne, hrs⟩

/-- The repetition of quotient heights is a repetition of the corresponding
nonzero, non-`5ℤ` shifts in `ZMod 25`. -/
theorem exists_distinct_equal_cyclicDifference (φ : Phase) :
    ∃ r s : Residue, r ≠ s ∧ cyclicDifference φ r = cyclicDifference φ s := by
  obtain ⟨r, s, hne, hquot⟩ := exists_distinct_equal_quotientDifference φ
  refine ⟨r, s, hne, ?_⟩
  rw [cyclicDifference_eq, cyclicDifference_eq, hquot]

/-- The five selected points of a phase transversal. -/
def transversal (φ : Phase) : Finset Position :=
  Finset.univ.image (transversalPoint φ)

/-- Translate a finite set of positions by a shift. -/
def translate (d : Position) (S : Finset Position) : Finset Position :=
  S.image (fun x ↦ x + d)

theorem transversalPoint_mem (φ : Phase) (r : Residue) :
    transversalPoint φ r ∈ transversal φ := by
  exact Finset.mem_image.mpr ⟨r, Finset.mem_univ r, rfl⟩

theorem transversal_card (φ : Phase) : (transversal φ).card = 5 := by
  rw [transversal, Finset.card_image_of_injective _ (transversalPoint_injective φ),
    Finset.card_univ, Fintype.card_fin]

theorem translate_card (d : Position) (S : Finset Position) :
    (translate d S).card = S.card := by
  rw [translate, Finset.card_image_of_injective]
  intro x y hxy
  exact add_right_cancel hxy

theorem card_symmDiff_le_six_of_five_of_two_inter
    (S T : Finset Position)
    (hS : S.card = 5)
    (hT : T.card = 5)
    (hinter : 2 ≤ (S ∩ T).card) :
    (S ∆ T).card ≤ 6 := by
  have hdisj : Disjoint (S \ T) (T \ S) := by
    rw [Finset.disjoint_left]
    intro x hxS hxT
    exact (Finset.mem_sdiff.mp hxT).2 (Finset.mem_sdiff.mp hxS).1
  change ((S \ T) ∪ (T \ S)).card ≤ 6
  rw [Finset.card_union_of_disjoint hdisj, Finset.card_sdiff,
    Finset.card_sdiff]
  have hinter_comm : (T ∩ S).card = (S ∩ T).card := by
    rw [Finset.inter_comm]
  rw [hS, hT, hinter_comm]
  omega

/-- Every residue transversal has a shift outside `5ℤ` for which the
transversal and its translate meet in at least two points. -/
theorem exists_shift_two_le_intersection (φ : Phase) :
    ∃ d : Position,
      reduceModFive d = 1 ∧
        2 ≤ (transversal φ ∩ translate d (transversal φ)).card := by
  obtain ⟨r, s, hrs, hdiff⟩ := exists_distinct_equal_cyclicDifference φ
  let d := cyclicDifference φ r
  have hrd : transversalPoint φ (nextResidue r) ∈ translate d (transversal φ) := by
    refine Finset.mem_image.mpr ⟨transversalPoint φ r, transversalPoint_mem φ r, ?_⟩
    dsimp [d]
    simp only [cyclicDifference]
    abel
  have hsd : transversalPoint φ (nextResidue s) ∈ translate d (transversal φ) := by
    refine Finset.mem_image.mpr ⟨transversalPoint φ s, transversalPoint_mem φ s, ?_⟩
    dsimp [d]
    rw [hdiff]
    simp only [cyclicDifference]
    abel
  have hpoints :
      transversalPoint φ (nextResidue r) ≠ transversalPoint φ (nextResidue s) := by
    intro hpoint
    have hnext := transversalPoint_injective φ hpoint
    exact hrs (nextResidue_bijective.1 hnext)
  refine ⟨d, reduce_cyclicDifference φ r, ?_⟩
  exact Finset.one_lt_card_iff.mpr
    ⟨transversalPoint φ (nextResidue r), transversalPoint φ (nextResidue s),
      Finset.mem_inter.mpr ⟨transversalPoint_mem φ (nextResidue r), hrd⟩,
      Finset.mem_inter.mpr ⟨transversalPoint_mem φ (nextResidue s), hsd⟩,
      hpoints⟩

/-- The repeated shift makes the symmetric difference of the transversal and
its translate have size at most `6`. -/
theorem exists_shift_symmDiff_card_le_six (φ : Phase) :
    ∃ d : Position,
      reduceModFive d = 1 ∧
        (transversal φ ∆ translate d (transversal φ)).card ≤ 6 := by
  obtain ⟨d, hd, hinter⟩ := exists_shift_two_le_intersection φ
  refine ⟨d, hd, ?_⟩
  exact card_symmDiff_le_six_of_five_of_two_inter
    (transversal φ) (translate d (transversal φ))
    (transversal_card φ) ((translate_card d (transversal φ)).trans (transversal_card φ)) hinter

/-- Support of `g = 1 + x⁵` in the cyclic ring. -/
def generatorSupport : Finset Position :=
  {0, 5}

theorem generatorSupport_card : generatorSupport.card = 2 := by
  decide

theorem reduce_of_mem_generatorSupport {x : Position} (hx : x ∈ generatorSupport) :
    reduceModFive x = 0 := by
  have hx' : x = 0 ∨ x = 5 := by
    simpa [generatorSupport] using hx
  rcases hx' with rfl | rfl <;> decide

theorem generatorSupport_disjoint_translate {d : Position}
    (hd : reduceModFive d = 1) :
    Disjoint generatorSupport (translate d generatorSupport) := by
  rw [Finset.disjoint_left]
  intro x hx hxt
  obtain ⟨y, hy, hyx⟩ := Finset.mem_image.mp hxt
  have hxzero := reduce_of_mem_generatorSupport hx
  have hyzero := reduce_of_mem_generatorSupport hy
  have hxone : reduceModFive x = 1 := by
    rw [← hyx, map_add, hyzero, hd, zero_add]
  rw [hxzero] at hxone
  have hzeroone : (0 : ZMod 5) ≠ 1 := by decide
  exact hzeroone hxone

/-- Support of the first graph-code block `g(1+xᵈ)`. -/
def binomialGeneratorSupport (d : Position) : Finset Position :=
  generatorSupport ∆ translate d generatorSupport

theorem binomialGeneratorSupport_card {d : Position}
    (hd : reduceModFive d = 1) :
    (binomialGeneratorSupport d).card = 4 := by
  have hdisj := generatorSupport_disjoint_translate hd
  rw [binomialGeneratorSupport, Finset.symmDiff_eq_union hdisj,
    Finset.card_union_of_disjoint hdisj, translate_card,
    generatorSupport_card]

/-- Exact support-level form of the weight-`10` consequence.  The first
summand is the support of `g(1+xᵈ)`; the second is the support of
`b(1+xᵈ)` after replacing the complement-transversal support of `b` by its
symmetric difference. -/
theorem exists_graph_word_support_weight_le_ten (φ : Phase) :
    ∃ d : Position,
      reduceModFive d = 1 ∧
        (binomialGeneratorSupport d).card +
            (transversal φ ∆ translate d (transversal φ)).card ≤ 10 := by
  obtain ⟨d, hd, hright⟩ := exists_shift_symmDiff_card_le_six φ
  refine ⟨d, hd, ?_⟩
  rw [binomialGeneratorSupport_card hd]
  omega

end AxiomPackQCTransversalObstruction
