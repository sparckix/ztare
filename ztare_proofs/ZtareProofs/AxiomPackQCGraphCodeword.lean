import ZtareProofs.AxiomPackQCTransversalObstruction

/-!
# Binary graph-codeword codec for the cyclic-transversal obstruction

This file connects the support theorem to an explicit binary row-span word.
The rows are pairs of length-`25` supports and binary addition is symmetric
difference.  Rank is deliberately outside this theorem: the obstruction only
needs one nonzero word of weight at most `10`.
-/

namespace AxiomPackQCTransversalObstruction

open scoped symmDiff

/-- A binary length-`50` word, split into its two disjoint length-`25` blocks. -/
structure BinaryTwoBlockWord where
  leftSupport : Finset Position
  rightSupport : Finset Position
deriving DecidableEq

namespace BinaryTwoBlockWord

/-- Binary addition, represented by symmetric difference in each block. -/
def xor (u v : BinaryTwoBlockWord) : BinaryTwoBlockWord where
  leftSupport := u.leftSupport ∆ v.leftSupport
  rightSupport := u.rightSupport ∆ v.rightSupport

/-- The all-zero two-block word. -/
def zero : BinaryTwoBlockWord where
  leftSupport := ∅
  rightSupport := ∅

/-- Hamming weight; the two blocks occupy disjoint coordinate ranges. -/
def weight (w : BinaryTwoBlockWord) : ℕ :=
  w.leftSupport.card + w.rightSupport.card

@[simp]
theorem xor_zero (w : BinaryTwoBlockWord) : xor w zero = w := by
  cases w
  simp [xor, zero]

end BinaryTwoBlockWord

/-- The second seed support, expressed as the complement of a residue
transversal.  For the oracle phase `φ`, this transversal phase is `φ + 4`. -/
def graphSecondSeedSupport (φ : Phase) : Finset Position :=
  Finset.univ \ transversal φ

/-- Generator row `i` of the binary two-block graph presentation. -/
def graphRow (φ : Phase) (i : Fin 20) : BinaryTwoBlockWord where
  leftSupport := translate (i.val : Position) generatorSupport
  rightSupport := translate (i.val : Position) (graphSecondSeedSupport φ)

/-- XOR a finite list of generator rows.  Lists give a small, literal
row-span presentation; repeated indices cancel by binary addition. -/
def xorGraphRows (φ : Phase) : List (Fin 20) → BinaryTwoBlockWord
  | [] => BinaryTwoBlockWord.zero
  | i :: is => BinaryTwoBlockWord.xor (graphRow φ i) (xorGraphRows φ is)

/-- Membership in the binary span of the 20 displayed rows. -/
def InGraphRowSpan (φ : Phase) (w : BinaryTwoBlockWord) : Prop :=
  ∃ is : List (Fin 20), xorGraphRows φ is = w

theorem translate_zero (S : Finset Position) : translate 0 S = S := by
  ext x
  simp [translate]

theorem translate_symmDiff (d : Position) (S T : Finset Position) :
    translate d (S ∆ T) = translate d S ∆ translate d T := by
  exact Finset.image_symmDiff S T (Equiv.addRight d).injective

theorem translate_sdiff (d : Position) (S T : Finset Position) :
    translate d (S \ T) = translate d S \ translate d T := by
  exact Finset.image_sdiff S T (Equiv.addRight d).injective

theorem translate_univ (d : Position) :
    translate d (Finset.univ : Finset Position) = Finset.univ := by
  exact Finset.image_univ_equiv (Equiv.addRight d)

theorem translate_translate (d e : Position) (S : Finset Position) :
    translate d (translate e S) = translate (e + d) S := by
  ext x
  simp only [translate, Finset.mem_image]
  constructor
  · rintro ⟨y, ⟨z, hz, rfl⟩, rfl⟩
    exact ⟨z, hz, by simp [add_assoc]⟩
  · rintro ⟨z, hz, rfl⟩
    exact ⟨z + e, ⟨z, hz, rfl⟩, by simp [add_assoc]⟩

/-- Translating a complemented transversal and adding it to itself cancels
the two all-one supports. -/
theorem graphSecondSeed_binomial_support (φ : Phase) (d : Position) :
    graphSecondSeedSupport φ ∆ translate d (graphSecondSeedSupport φ) =
      transversal φ ∆ translate d (transversal φ) := by
  rw [graphSecondSeedSupport, translate_sdiff, translate_univ]
  change (transversal φ)ᶜ ∆ (translate d (transversal φ))ᶜ =
    transversal φ ∆ translate d (transversal φ)
  exact compl_symmDiff_compl (a := transversal φ) (b := translate d (transversal φ))

/-- Reversing a cyclic binomial shift preserves its support cardinality. -/
theorem symmDiff_translate_neg_card_eq (S : Finset Position) (d : Position) :
    (S ∆ translate (-d) S).card = (S ∆ translate d S).card := by
  calc
    (S ∆ translate (-d) S).card =
        (translate d (S ∆ translate (-d) S)).card :=
      (translate_card d (S ∆ translate (-d) S)).symm
    _ = (translate d S ∆ S).card := by
      rw [translate_symmDiff, translate_translate]
      simp [translate_zero]
    _ = (S ∆ translate d S).card := by rw [symmDiff_comm]

/-- A two-row word is visibly in the displayed binary row span. -/
theorem xor_two_graphRows_mem (φ : Phase) (i j : Fin 20) :
    InGraphRowSpan φ (BinaryTwoBlockWord.xor (graphRow φ i) (graphRow φ j)) := by
  refine ⟨[i, j], ?_⟩
  simp [xorGraphRows]

/-- Literal binary-codeword form of the cyclic-transversal obstruction.

For every transversal phase there is an admissible nonzero row index
`1 ≤ s < 20` such that the XOR of rows `0` and `s` is a graph-codeword of
weight at most `10`.  The sign branch is the monomial normalization that
turns a possible shift of degree at least `20` into its negative shift. -/
theorem exists_two_row_graph_codeword_weight_le_ten (φ : Phase) :
    ∃ (s : Fin 20) (w : BinaryTwoBlockWord),
      s ≠ 0 ∧
      InGraphRowSpan φ w ∧
      w = BinaryTwoBlockWord.xor (graphRow φ 0) (graphRow φ s) ∧
      w.leftSupport.card = 4 ∧
      w.weight ≤ 10 := by
  obtain ⟨d, hd, hright⟩ := exists_shift_symmDiff_card_le_six φ
  have hdne : d ≠ 0 := by
    intro hzero
    subst d
    norm_num [reduceModFive] at hd
    exact (by decide : (0 : ZMod 5) ≠ 1) hd
  by_cases hsmall : d.val < 20
  · let s : Fin 20 := ⟨d.val, hsmall⟩
    have hspos : (s.val : Position) = d := by
      exact ZMod.natCast_zmod_val d
    let w := BinaryTwoBlockWord.xor (graphRow φ 0) (graphRow φ s)
    refine ⟨s, w, ?_, xor_two_graphRows_mem φ 0 s, rfl, ?_, ?_⟩
    · intro hs0
      have hsval : s.val = 0 := congrArg Fin.val hs0
      have hdval : d.val = 0 := by simpa [s] using hsval
      exact hdne ((ZMod.val_eq_zero d).mp hdval)
    · simp only [w, BinaryTwoBlockWord.xor, graphRow]
      rw [hspos]
      change (translate 0 generatorSupport ∆ translate d generatorSupport).card = 4
      rw [translate_zero]
      change (binomialGeneratorSupport d).card = 4
      exact binomialGeneratorSupport_card hd
    · simp only [w, BinaryTwoBlockWord.weight, BinaryTwoBlockWord.xor, graphRow]
      rw [hspos]
      change
        (translate 0 generatorSupport ∆ translate d generatorSupport).card +
            (translate 0 (graphSecondSeedSupport φ) ∆
              translate d (graphSecondSeedSupport φ)).card ≤ 10
      rw [translate_zero generatorSupport, translate_zero (graphSecondSeedSupport φ)]
      rw [graphSecondSeed_binomial_support]
      change (binomialGeneratorSupport d).card +
          (transversal φ ∆ translate d (transversal φ)).card ≤ 10
      rw [binomialGeneratorSupport_card hd]
      omega
  · have hnegsmall : (-d).val < 20 := by
      rw [ZMod.neg_val]
      simp only [if_neg hdne]
      have hdlt : d.val < 25 := d.val_lt
      omega
    let s : Fin 20 := ⟨(-d).val, hnegsmall⟩
    have hspos : (s.val : Position) = -d := by
      exact ZMod.natCast_zmod_val (-d)
    let w := BinaryTwoBlockWord.xor (graphRow φ 0) (graphRow φ s)
    refine ⟨s, w, ?_, xor_two_graphRows_mem φ 0 s, rfl, ?_, ?_⟩
    · intro hs0
      have hsval : s.val = 0 := congrArg Fin.val hs0
      have hnegval : (-d).val = 0 := by simpa [s] using hsval
      have hnegzero : -d = 0 := (ZMod.val_eq_zero (-d)).mp hnegval
      exact hdne (neg_eq_zero.mp hnegzero)
    · simp only [w, BinaryTwoBlockWord.xor, graphRow]
      rw [hspos]
      change (translate 0 generatorSupport ∆ translate (-d) generatorSupport).card = 4
      rw [translate_zero]
      rw [symmDiff_translate_neg_card_eq]
      change (binomialGeneratorSupport d).card = 4
      exact binomialGeneratorSupport_card hd
    · simp only [w, BinaryTwoBlockWord.weight, BinaryTwoBlockWord.xor, graphRow]
      rw [hspos]
      change
        (translate 0 generatorSupport ∆ translate (-d) generatorSupport).card +
            (translate 0 (graphSecondSeedSupport φ) ∆
              translate (-d) (graphSecondSeedSupport φ)).card ≤ 10
      rw [translate_zero generatorSupport, translate_zero (graphSecondSeedSupport φ)]
      rw [symmDiff_translate_neg_card_eq generatorSupport]
      rw [symmDiff_translate_neg_card_eq (graphSecondSeedSupport φ)]
      rw [graphSecondSeed_binomial_support]
      change (binomialGeneratorSupport d).card +
          (transversal φ ∆ translate d (transversal φ)).card ≤ 10
      rw [binomialGeneratorSupport_card hd]
      omega

/-- Add a constant quotient-height offset to every residue phase. -/
def phaseOffset (φ : Phase) (k : ZMod 5) : Phase :=
  fun r ↦ φ r + k

/-- Missing-transversal phase for the oracle multiplier whose two selected
heights in residue `r` are `φ r` and `φ r + 2`. -/
def selectedQCMissingPhase (φ : Phase) : Phase :=
  phaseOffset φ 4

/-- Multiplication by `5` embeds quotient heights into `ZMod 25`. -/
theorem liftHeight_injective : Function.Injective liftHeight := by
  intro q₁ q₂ h
  have hv := congrArg ZMod.val h
  rw [liftHeight_eq_five_mul_val, liftHeight_eq_five_mul_val] at hv
  have hval₁ : (5 * (q₁.val : Position)).val = 5 * q₁.val := by
    have hq := q₁.val_lt
    have hq25 : q₁.val < 25 := by omega
    have hprod : 5 * q₁.val < 25 := by omega
    have hfive : (5 : Position).val = 5 :=
      ZMod.val_natCast_of_lt (by norm_num)
    rw [ZMod.val_mul, ZMod.val_natCast_of_lt hq25, hfive,
      Nat.mod_eq_of_lt hprod]
  have hval₂ : (5 * (q₂.val : Position)).val = 5 * q₂.val := by
    have hq := q₂.val_lt
    have hq25 : q₂.val < 25 := by omega
    have hprod : 5 * q₂.val < 25 := by omega
    have hfive : (5 : Position).val = 5 :=
      ZMod.val_natCast_of_lt (by norm_num)
    rw [ZMod.val_mul, ZMod.val_natCast_of_lt hq25, hfive,
      Nat.mod_eq_of_lt hprod]
  rw [hval₁, hval₂] at hv
  apply ZMod.val_injective
  omega

theorem transversalPoint_phaseOffset (φ : Phase) (k : ZMod 5) (r : Residue) :
    transversalPoint (phaseOffset φ k) r =
      transversalPoint φ r + liftHeight k := by
  simp only [transversalPoint, phaseOffset]
  change (r.val : Position) + liftHeightHom (φ r + k) =
    (r.val : Position) + liftHeightHom (φ r) + liftHeightHom k
  rw [map_add]
  abel

/-- A quotient-height phase offset is the corresponding translation of the
transversal inside `ZMod 25`. -/
theorem translate_transversal_liftHeight (φ : Phase) (k : ZMod 5) :
    translate (liftHeight k) (transversal φ) = transversal (phaseOffset φ k) := by
  rw [translate, transversal, transversal, Finset.image_image]
  apply Finset.image_congr
  intro r hr
  simp only [Function.comp_apply]
  exact (transversalPoint_phaseOffset φ k r).symm

theorem residue_eq_of_transversalPoint_eq
    (φ ψ : Phase) {r s : Residue}
    (h : transversalPoint φ r = transversalPoint ψ s) : r = s := by
  have hreduce := congrArg reduceModFive h
  rw [reduce_transversalPoint, reduce_transversalPoint] at hreduce
  apply Fin.ext
  have hval := congrArg ZMod.val hreduce
  simpa [ZMod.val_natCast, Nat.mod_eq_of_lt r.isLt, Nat.mod_eq_of_lt s.isLt] using hval

/-- Distinct height offsets give disjoint residue transversals. -/
theorem phaseOffset_transversal_disjoint (φ : Phase) {k l : ZMod 5}
    (hkl : k ≠ l) :
    Disjoint (transversal (phaseOffset φ k)) (transversal (phaseOffset φ l)) := by
  rw [Finset.disjoint_left]
  intro x hxk hxl
  obtain ⟨r, -, hrx⟩ := Finset.mem_image.mp hxk
  obtain ⟨s, -, hsx⟩ := Finset.mem_image.mp hxl
  have hrs : r = s := residue_eq_of_transversalPoint_eq
    (phaseOffset φ k) (phaseOffset φ l) (hrx.trans hsx.symm)
  subst s
  have hpoint :
      transversalPoint (phaseOffset φ k) r =
        transversalPoint (phaseOffset φ l) r := hrx.trans hsx.symm
  simp only [transversalPoint, phaseOffset] at hpoint
  have hlift : liftHeight (φ r + k) = liftHeight (φ r + l) :=
    add_left_cancel hpoint
  have hoffset : φ r + k = φ r + l := liftHeight_injective hlift
  exact hkl (add_left_cancel hoffset)

theorem translate_union (d : Position) (S T : Finset Position) :
    translate d (S ∪ T) = translate d S ∪ translate d T := by
  exact Finset.image_union S T

/-- Translating by `5` advances every phase height by one. -/
theorem translate_five_phaseOffset_transversal (φ : Phase) (k : ZMod 5) :
    translate 5 (transversal (phaseOffset φ k)) =
      transversal (phaseOffset φ (k + 1)) := by
  calc
    translate 5 (transversal (phaseOffset φ k)) =
        translate (liftHeight 1) (transversal (phaseOffset φ k)) := by
      rw [liftHeight_one]
    _ = transversal (phaseOffset (phaseOffset φ k) 1) :=
      translate_transversal_liftHeight (phaseOffset φ k) 1
    _ = transversal (phaseOffset φ (k + 1)) := by
      congr 1
      funext r
      simp only [phaseOffset]
      abel

/-- Explicit ten-point support used by the oracle's phase mask. -/
def selectedQCPhaseMaskSupport (φ : Phase) : Finset Position :=
  transversal (phaseOffset φ 0) ∪ transversal (phaseOffset φ 2)

theorem selectedQCPhaseMaskSupport_card (φ : Phase) :
    (selectedQCPhaseMaskSupport φ).card = 10 := by
  have hdisjoint :
      Disjoint (transversal (phaseOffset φ 0)) (transversal (phaseOffset φ 2)) :=
    phaseOffset_transversal_disjoint φ (by decide)
  rw [selectedQCPhaseMaskSupport, Finset.card_union_of_disjoint hdisjoint,
    transversal_card, transversal_card]

/-- Binary cyclic support product by `generatorSupport = {0,5}`. -/
def productByGeneratorSupport (S : Finset Position) : Finset Position :=
  S ∆ translate 5 S

/-- Four phase-offset transversals fill exactly the complement of the fifth. -/
theorem four_phaseOffset_transversals_eq_complement (φ : Phase) :
    ((transversal (phaseOffset φ 0) ∪ transversal (phaseOffset φ 2)) ∪
        (transversal (phaseOffset φ 1) ∪ transversal (phaseOffset φ 3))) =
      Finset.univ \ transversal (phaseOffset φ 4) := by
  let M0 := transversal (phaseOffset φ 0)
  let M1 := transversal (phaseOffset φ 1)
  let M2 := transversal (phaseOffset φ 2)
  let M3 := transversal (phaseOffset φ 3)
  let M4 := transversal (phaseOffset φ 4)
  have h02 : Disjoint M0 M2 := by
    dsimp [M0, M2]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h13 : Disjoint M1 M3 := by
    dsimp [M1, M3]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h01 : Disjoint M0 M1 := by
    dsimp [M0, M1]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h03 : Disjoint M0 M3 := by
    dsimp [M0, M3]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h21 : Disjoint M2 M1 := by
    dsimp [M2, M1]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h23 : Disjoint M2 M3 := by
    dsimp [M2, M3]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h04 : Disjoint M0 M4 := by
    dsimp [M0, M4]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h24 : Disjoint M2 M4 := by
    dsimp [M2, M4]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h14 : Disjoint M1 M4 := by
    dsimp [M1, M4]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have h34 : Disjoint M3 M4 := by
    dsimp [M3, M4]
    exact phaseOffset_transversal_disjoint φ (by decide)
  have hAB : Disjoint (M0 ∪ M2) (M1 ∪ M3) := by
    rw [Finset.disjoint_union_left, Finset.disjoint_union_right,
      Finset.disjoint_union_right]
    exact ⟨⟨h01, h03⟩, h21, h23⟩
  have hU4 : Disjoint ((M0 ∪ M2) ∪ (M1 ∪ M3)) M4 := by
    rw [Finset.disjoint_union_left, Finset.disjoint_union_left,
      Finset.disjoint_union_left]
    exact ⟨⟨h04, h24⟩, h14, h34⟩
  have hAcard : (M0 ∪ M2).card = 10 := by
    rw [Finset.card_union_of_disjoint h02]
    dsimp [M0, M2]
    rw [transversal_card, transversal_card]
  have hBcard : (M1 ∪ M3).card = 10 := by
    rw [Finset.card_union_of_disjoint h13]
    dsimp [M1, M3]
    rw [transversal_card, transversal_card]
  have hUcard : ((M0 ∪ M2) ∪ (M1 ∪ M3)).card = 20 := by
    rw [Finset.card_union_of_disjoint hAB, hAcard, hBcard]
  have hM4card : M4.card = 5 := by
    dsimp [M4]
    exact transversal_card (phaseOffset φ 4)
  have hallcard : (((M0 ∪ M2) ∪ (M1 ∪ M3)) ∪ M4).card = 25 := by
    rw [Finset.card_union_of_disjoint hU4, hUcard, hM4card]
  have hpartition : ((M0 ∪ M2) ∪ (M1 ∪ M3)) ∪ M4 = Finset.univ := by
    apply Finset.eq_univ_of_card
    simpa using hallcard
  have hcomplement : ((M0 ∪ M2) ∪ (M1 ∪ M3)) = Finset.univ \ M4 := by
    ext x
    have hcover : x ∈ (M0 ∪ M2) ∪ (M1 ∪ M3) ∨ x ∈ M4 := by
      apply Finset.mem_union.mp
      rw [hpartition]
      exact Finset.mem_univ x
    constructor
    · intro hx
      refine Finset.mem_sdiff.mpr ⟨Finset.mem_univ x, ?_⟩
      exact Finset.disjoint_left.mp hU4 hx
    · intro hx
      have hxnot : x ∉ M4 := (Finset.mem_sdiff.mp hx).2
      rcases hcover with hU | h4
      · exact hU
      · exact False.elim (hxnot h4)
  simpa [M0, M1, M2, M3, M4] using hcomplement

/-- The oracle's literal ten-point phase mask, multiplied over `F₂` by the
support `{0,5}`, is exactly the complement-transversal second seed used by
the graph rows. -/
theorem product_selectedQCPhaseMaskSupport_eq_secondSeed (φ : Phase) :
    productByGeneratorSupport (selectedQCPhaseMaskSupport φ) =
      graphSecondSeedSupport (selectedQCMissingPhase φ) := by
  rw [productByGeneratorSupport, selectedQCPhaseMaskSupport, translate_union]
  rw [translate_five_phaseOffset_transversal φ 0,
    translate_five_phaseOffset_transversal φ 2]
  change
    ((transversal (phaseOffset φ 0) ∪ transversal (phaseOffset φ 2)) ∆
        (transversal (phaseOffset φ 1) ∪ transversal (phaseOffset φ 3))) =
      Finset.univ \ transversal (phaseOffset φ 4)
  have h01 :
      Disjoint (transversal (phaseOffset φ 0)) (transversal (phaseOffset φ 1)) :=
    phaseOffset_transversal_disjoint φ (by decide)
  have h03 :
      Disjoint (transversal (phaseOffset φ 0)) (transversal (phaseOffset φ 3)) :=
    phaseOffset_transversal_disjoint φ (by decide)
  have h21 :
      Disjoint (transversal (phaseOffset φ 2)) (transversal (phaseOffset φ 1)) :=
    phaseOffset_transversal_disjoint φ (by decide)
  have h23 :
      Disjoint (transversal (phaseOffset φ 2)) (transversal (phaseOffset φ 3)) :=
    phaseOffset_transversal_disjoint φ (by decide)
  have hdisjoint :
      Disjoint
        (transversal (phaseOffset φ 0) ∪ transversal (phaseOffset φ 2))
        (transversal (phaseOffset φ 1) ∪ transversal (phaseOffset φ 3)) := by
    rw [Finset.disjoint_union_left, Finset.disjoint_union_right,
      Finset.disjoint_union_right]
    exact ⟨⟨h01, h03⟩, h21, h23⟩
  rw [Finset.symmDiff_eq_union hdisjoint]
  exact four_phaseOffset_transversals_eq_complement φ

/-- The selected QC family's generator row, indexed directly by the oracle
phase rather than by the missing-transversal phase. -/
def selectedQCGraphRow (φ : Phase) (i : Fin 20) : BinaryTwoBlockWord :=
  graphRow (selectedQCMissingPhase φ) i

/-- Binary row-span of the selected QC graph presentation. -/
def InSelectedQCGraphRowSpan (φ : Phase) (w : BinaryTwoBlockWord) : Prop :=
  InGraphRowSpan (selectedQCMissingPhase φ) w

/-- Direct oracle-phase form: every selected phase presentation contains a
nonzero XOR of rows `0` and `s`, with `s < 20`, of weight at most `10`. -/
theorem exists_selectedQC_two_row_codeword_weight_le_ten (φ : Phase) :
    ∃ (s : Fin 20) (w : BinaryTwoBlockWord),
      s ≠ 0 ∧
      InSelectedQCGraphRowSpan φ w ∧
      w = BinaryTwoBlockWord.xor (selectedQCGraphRow φ 0) (selectedQCGraphRow φ s) ∧
      w.leftSupport.card = 4 ∧
      w.weight ≤ 10 := by
  simpa [selectedQCGraphRow, InSelectedQCGraphRowSpan] using
    exists_two_row_graph_codeword_weight_le_ten (selectedQCMissingPhase φ)

/-- Generator row built from the literal oracle mask and its binary support
product by `{0,5}`. -/
def literalSelectedQCGraphRow (φ : Phase) (i : Fin 20) : BinaryTwoBlockWord where
  leftSupport := translate (i.val : Position) generatorSupport
  rightSupport := translate (i.val : Position)
    (productByGeneratorSupport (selectedQCPhaseMaskSupport φ))

theorem literalSelectedQCGraphRow_eq (φ : Phase) (i : Fin 20) :
    literalSelectedQCGraphRow φ i = selectedQCGraphRow φ i := by
  rw [literalSelectedQCGraphRow, selectedQCGraphRow, graphRow,
    product_selectedQCPhaseMaskSupport_eq_secondSeed]

/-- XOR a finite list of the literal oracle rows. -/
def xorLiteralSelectedQCGraphRows (φ : Phase) : List (Fin 20) → BinaryTwoBlockWord
  | [] => BinaryTwoBlockWord.zero
  | i :: is => BinaryTwoBlockWord.xor
      (literalSelectedQCGraphRow φ i) (xorLiteralSelectedQCGraphRows φ is)

/-- Membership in the binary span of the literal oracle rows. -/
def InLiteralSelectedQCGraphRowSpan (φ : Phase) (w : BinaryTwoBlockWord) : Prop :=
  ∃ is : List (Fin 20), xorLiteralSelectedQCGraphRows φ is = w

theorem xor_two_literalSelectedQCGraphRows_mem (φ : Phase) (i j : Fin 20) :
    InLiteralSelectedQCGraphRowSpan φ
      (BinaryTwoBlockWord.xor
        (literalSelectedQCGraphRow φ i) (literalSelectedQCGraphRow φ j)) := by
  refine ⟨[i, j], ?_⟩
  simp [xorLiteralSelectedQCGraphRows]

/-- Terminal literal-oracle statement.  The right seed is computed as the
binary support product of the explicit ten-point phase mask by `{0,5}`. -/
theorem exists_literalSelectedQC_two_row_codeword_weight_le_ten (φ : Phase) :
    ∃ (s : Fin 20) (w : BinaryTwoBlockWord),
      s ≠ 0 ∧
      InLiteralSelectedQCGraphRowSpan φ w ∧
      w = BinaryTwoBlockWord.xor
        (literalSelectedQCGraphRow φ 0) (literalSelectedQCGraphRow φ s) ∧
      w.leftSupport.card = 4 ∧
      w.weight ≤ 10 := by
  obtain ⟨s, w, hs, -, hw, hleft, hweight⟩ :=
    exists_selectedQC_two_row_codeword_weight_le_ten φ
  have hwLiteral : w = BinaryTwoBlockWord.xor
      (literalSelectedQCGraphRow φ 0) (literalSelectedQCGraphRow φ s) := by
    simpa only [literalSelectedQCGraphRow_eq] using hw
  refine ⟨s, w, hs, ?_, hwLiteral, hleft, hweight⟩
  rw [hwLiteral]
  exact xor_two_literalSelectedQCGraphRows_mem φ 0 s

end AxiomPackQCTransversalObstruction
