import Mathlib

/-!
# Parity insertion and the binary even-kernel construction

This file contains the substrate-neutral theorem used by the binary-code
campaign.  It is independent of the computed automorphism group of the
frozen `[51,20,14]` code.
-/

namespace AxiomPackParityInsertion

open scoped BigOperators

/-- The binary field used throughout the construction. -/
abbrev F₂ := ZMod 2

/-- A binary word with `n` named coordinates. -/
abbrev Word (n : ℕ) := Fin n → F₂

/-- The finite support of a binary word. -/
def support {n : ℕ} (x : Word n) : Finset (Fin n) :=
  Finset.univ.filter fun i => x i ≠ 0

/-- Hamming weight. -/
def weight {n : ℕ} (x : Word n) : ℕ :=
  (support x).card

/-- Coordinate sum, i.e. binary parity. -/
def parity {n : ℕ} (x : Word n) : F₂ :=
  ∑ i, x i

lemma f₂_eq_zero_or_one (a : F₂) : a = 0 ∨ a = 1 := by
  exact (by decide : ∀ b : F₂, b = 0 ∨ b = 1) a

theorem parity_eq_weight_cast {n : ℕ} (x : Word n) :
    parity x = (weight x : F₂) := by
  classical
  calc
    parity x = ∑ i ∈ support x, x i := by
      unfold parity
      symm
      apply Finset.sum_subset (Finset.filter_subset _ _)
      intro i _ hi
      simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hi
      simpa using not_ne_iff.mp hi
    _ = ∑ _i ∈ support x, (1 : F₂) := by
      apply Finset.sum_congr rfl
      intro i hi
      have hxi : x i ≠ 0 := by simpa [support] using hi
      exact (f₂_eq_zero_or_one (x i)).resolve_left hxi
    _ = (weight x : F₂) := by simp [weight]

/-- Insert parity as a new leading coordinate. -/
def parityInsert {n : ℕ} (x : Word n) : Word (n + 1) :=
  Fin.cons (parity x) x

/-- Remove the leading coordinate. -/
def punctureHead {n : ℕ} (y : Word (n + 1)) : Word n :=
  fun i => y i.succ

@[simp]
theorem punctureHead_parityInsert {n : ℕ} (x : Word n) :
    punctureHead (parityInsert x) = x := by
  ext i
  simp [punctureHead, parityInsert]

theorem weight_parityInsert {n : ℕ} (x : Word n) :
    weight (parityInsert x) =
      if Odd (weight x) then weight x + 1 else weight x := by
  classical
  change
    (Finset.univ.filter fun i : Fin (n + 1) => parityInsert x i ≠ 0).card =
      if Odd (weight x) then weight x + 1 else weight x
  rw [Fin.card_filter_univ_succ]
  simp only [parityInsert, Fin.cons_zero, Fin.cons_succ]
  have hp : parity x ≠ 0 ↔ Odd (weight x) := by
    rw [parity_eq_weight_cast, ZMod.natCast_ne_zero_iff_odd]
  change
    (if parity x ≠ 0 then weight x + 1 else weight x) =
      if Odd (weight x) then weight x + 1 else weight x
  exact if_congr hp rfl rfl

theorem thirteen_iff_parityInsert_fourteen {n : ℕ} (x : Word n) :
    13 ≤ weight x ↔ 14 ≤ weight (parityInsert x) := by
  rw [weight_parityInsert]
  by_cases hodd : Odd (weight x)
  · rw [if_pos hodd]
    rcases hodd with ⟨k, hk⟩
    omega
  · rw [if_neg hodd]
    have heven : Even (weight x) := Nat.not_odd_iff_even.mp hodd
    rcases heven with ⟨k, hk⟩
    omega

/-- Parity as a linear functional. -/
def parityLinear (n : ℕ) : Word n →ₗ[F₂] F₂ where
  toFun := parity
  map_add' x y := by simp [parity, Finset.sum_add_distrib]
  map_smul' a x := by simp [parity, Finset.mul_sum]

/-- The linear parity-insertion map. -/
def parityInsertLinear (n : ℕ) : Word n →ₗ[F₂] Word (n + 1) where
  toFun := parityInsert
  map_add' x y := by
    ext i
    refine Fin.cases ?_ (fun j => ?_) i
    · simp [parityInsert, parity, Finset.sum_add_distrib]
    · simp [parityInsert]
  map_smul' a x := by
    ext i
    refine Fin.cases ?_ (fun j => ?_) i
    · simp [parityInsert, parity, Finset.mul_sum]
    · simp [parityInsert]

/-- The even-weight ambient subspace. -/
def evenAmbient (n : ℕ) : Submodule F₂ (Word n) :=
  LinearMap.ker (parityLinear n)

theorem parity_parityInsert {n : ℕ} (x : Word n) :
    parity (parityInsert x) = 0 := by
  simpa [parity, parityInsert, Fin.sum_univ_succ] using
    ZModModule.add_self (parity x)

/-- Parity insertion, with codomain restricted to the even ambient space. -/
def parityInsertIntoEven (n : ℕ) : Word n →ₗ[F₂] evenAmbient (n + 1) :=
  (parityInsertLinear n).codRestrict (evenAmbient (n + 1)) fun x => by
    exact parity_parityInsert x

theorem parityInsertIntoEven_injective (n : ℕ) :
    Function.Injective (parityInsertIntoEven n) := by
  intro x y hxy
  have hval : parityInsert x = parityInsert y := congrArg Subtype.val hxy
  apply congrArg punctureHead at hval
  simpa using hval

theorem parity_eq_head_add_tail {n : ℕ} (y : Word (n + 1)) :
    parity y = y 0 + parity (punctureHead y) := by
  simp [parity, punctureHead, Fin.sum_univ_succ]

theorem parityInsert_punctureHead_of_even {n : ℕ} (y : Word (n + 1))
    (hy : y ∈ evenAmbient (n + 1)) :
    parityInsert (punctureHead y) = y := by
  have hsum : y 0 + parity (punctureHead y) = 0 := by
    rw [← parity_eq_head_add_tail]
    exact hy
  have hhead : y 0 = parity (punctureHead y) := by
    calc
      y 0 = -parity (punctureHead y) := eq_neg_of_add_eq_zero_left hsum
      _ = parity (punctureHead y) := ZMod.neg_eq_self_mod_two _
  ext i
  refine Fin.cases ?_ (fun j => ?_) i
  · simpa [parityInsert] using hhead.symm
  · simp [parityInsert, punctureHead]

theorem parityInsertIntoEven_surjective (n : ℕ) :
    Function.Surjective (parityInsertIntoEven n) := by
  intro y
  refine ⟨punctureHead (y : Word (n + 1)), ?_⟩
  apply Subtype.ext
  exact parityInsert_punctureHead_of_even (y := (y : Word (n + 1))) y.property

/-- Parity insertion identifies length-`n` words with even length-`n+1`
words. -/
noncomputable def parityInsertEquivEven (n : ℕ) :
    Word n ≃ₗ[F₂] evenAmbient (n + 1) :=
  LinearEquiv.ofBijective (parityInsertIntoEven n)
    ⟨parityInsertIntoEven_injective n, parityInsertIntoEven_surjective n⟩

/-- The parity extension of a binary linear code, now viewed inside the even
ambient space. -/
def parityExtensionCode {n : ℕ} (C : Submodule F₂ (Word n)) :
    Submodule F₂ (evenAmbient (n + 1)) :=
  C.map (parityInsertIntoEven n)

/-- Parity insertion transports punctured cosets to cosets in the even
ambient quotient. -/
noncomputable def puncturedCosetEquivEven {n : ℕ} (C : Submodule F₂ (Word n)) :
    (Word n ⧸ C) ≃ₗ[F₂]
      (evenAmbient (n + 1) ⧸ parityExtensionCode C) :=
  Submodule.Quotient.equiv C (parityExtensionCode C)
    (parityInsertEquivEven n) rfl

@[simp]
theorem puncturedCosetEquivEven_mk {n : ℕ} (C : Submodule F₂ (Word n))
    (x : Word n) :
    puncturedCosetEquivEven C (Submodule.Quotient.mk x) =
      Submodule.Quotient.mk (parityInsertIntoEven n x) := by
  rfl

/-- The threshold used by the campaign is preserved pointwise on an entire
coset. -/
theorem coset_thirteen_iff_extended_fourteen {n : ℕ}
    (C : Submodule F₂ (Word n)) (x : Word n) :
    (∀ c, c ∈ C → 13 ≤ weight (x + c)) ↔
      (∀ c, c ∈ C → 14 ≤ weight (parityInsert x + parityInsert c)) := by
  constructor
  · intro h c hc
    have hadd : parityInsert (x + c) = parityInsert x + parityInsert c :=
      (parityInsertLinear n).map_add x c
    rw [← hadd]
    exact (thirteen_iff_parityInsert_fourteen (x + c)).mp (h c hc)
  · intro h c hc
    apply (thirteen_iff_parityInsert_fourteen (x + c)).mpr
    have hadd : parityInsert (x + c) = parityInsert x + parityInsert c :=
      (parityInsertLinear n).map_add x c
    rw [hadd]
    exact h c hc

/-- Adjoin one binary generator to a code. -/
def oneRowExtension {n : ℕ} (C : Submodule F₂ (Word n)) (v : Word n) :
    Submodule F₂ (Word n) :=
  C ⊔ F₂ ∙ v

theorem oneRowExtension_finrank_twenty_one {n : ℕ}
    (C : Submodule F₂ (Word n)) (v : Word n)
    (hCdim : Module.finrank F₂ C = 20) (hv : v ∉ C) :
    Module.finrank F₂ (oneRowExtension C v) = 21 := by
  rw [oneRowExtension, Submodule.finrank_sup_span_singleton hv, hCdim]

theorem oneRowExtension_distance_thirteen {n : ℕ}
    (C : Submodule F₂ (Word n)) (v : Word n)
    (hCdist : ∀ c, c ∈ C → c ≠ 0 → 13 ≤ weight c)
    (hcoset : ∀ c, c ∈ C → 13 ≤ weight (v + c)) :
    ∀ d, d ∈ oneRowExtension C v → d ≠ 0 → 13 ≤ weight d := by
  intro d hd hd0
  obtain ⟨c, hc, z, hz, hcz⟩ := Submodule.mem_sup.mp hd
  obtain ⟨a, ha⟩ := Submodule.mem_span_singleton.mp hz
  rcases f₂_eq_zero_or_one a with ha0 | ha1
  · subst a
    simp only [zero_smul] at ha
    subst z
    simp only [add_zero] at hcz
    subst d
    exact hCdist c hc hd0
  · subst a
    simp only [one_smul] at ha
    subst z
    subst d
    simpa [add_comm] using hcoset c hc

/-- The even-weight subcode of `D`, represented as the kernel of parity on
the subtype `D`. -/
def parityKernel {n : ℕ} (D : Submodule F₂ (Word n)) : Submodule F₂ D :=
  LinearMap.ker ((parityLinear n).domRestrict D)

theorem parityKernel_finrank_twenty {n : ℕ}
    (D : Submodule F₂ (Word n))
    (hDdim : Module.finrank F₂ D = 21)
    (hodd : ∃ d : D, parity (d : Word n) ≠ 0) :
    Module.finrank F₂ (parityKernel D) = 20 := by
  let f := (parityLinear n).domRestrict D
  obtain ⟨d, hd⟩ := hodd
  have hfd : f d = 1 := by
    exact (f₂_eq_zero_or_one (f d)).resolve_left hd
  have htop : LinearMap.range f = ⊤ := by
    apply top_unique
    intro z _
    have h1 : (1 : F₂) ∈ LinearMap.range f := ⟨d, hfd⟩
    simpa using (LinearMap.range f).smul_mem z h1
  have hrank := f.finrank_range_add_finrank_ker
  rw [htop] at hrank
  have hsum : 1 + Module.finrank F₂ (LinearMap.ker f) = 21 := by
    simpa [hDdim] using hrank
  change Module.finrank F₂ (LinearMap.ker f) = 20
  omega

theorem parityKernel_distance_fourteen {n : ℕ}
    (D : Submodule F₂ (Word n))
    (hDdist : ∀ d : D, d ≠ 0 → 13 ≤ weight (d : Word n)) :
    ∀ e : parityKernel D, e ≠ 0 → 14 ≤ weight (e : Word n) := by
  intro e he0
  have heD0 : (e : D) ≠ 0 := by
    intro h
    apply he0
    exact Subtype.ext h
  have h13 : 13 ≤ weight (e : Word n) := hDdist (e : D) heD0
  have hp0 : parity (e : Word n) = 0 := by
    exact e.property
  have hcast : (weight (e : Word n) : F₂) = 0 := by
    rw [← parity_eq_weight_cast]
    exact hp0
  have heven : Even (weight (e : Word n)) :=
    ZMod.natCast_eq_zero_iff_even.mp hcast
  rcases heven with ⟨k, hk⟩
  omega

/-- Main reusable construction theorem.  A rank-20 distance-13 code, an
independent coset representative at distance at least 13, and one odd source
word produce a dimension-20 even subcode whose nonzero words have weight at
least 14. -/
theorem representative_thirteen_yields_parity_kernel_code {n : ℕ}
    (C : Submodule F₂ (Word n)) (v : Word n)
    (hCdim : Module.finrank F₂ C = 20)
    (hv : v ∉ C)
    (hCdist : ∀ c, c ∈ C → c ≠ 0 → 13 ≤ weight c)
    (hcoset : ∀ c, c ∈ C → 13 ≤ weight (v + c))
    (hoddC : ∃ c, c ∈ C ∧ parity c ≠ 0) :
    let D := oneRowExtension C v
    let E := parityKernel D
    Module.finrank F₂ E = 20 ∧
      ∀ e : E, e ≠ 0 → 14 ≤ weight (e : Word n) := by
  dsimp only
  have hDdim : Module.finrank F₂ (oneRowExtension C v) = 21 :=
    oneRowExtension_finrank_twenty_one C v hCdim hv
  have hDdist : ∀ d : oneRowExtension C v, d ≠ 0 →
      13 ≤ weight (d : Word n) := by
    intro d hd0
    have hdval : (d : Word n) ≠ 0 := by
      intro h
      apply hd0
      exact Subtype.ext h
    exact oneRowExtension_distance_thirteen C v hCdist hcoset d d.property hdval
  have hoddD : ∃ d : oneRowExtension C v, parity (d : Word n) ≠ 0 := by
    obtain ⟨c, hc, hpc⟩ := hoddC
    exact ⟨⟨c, Submodule.mem_sup_left hc⟩, hpc⟩
  exact ⟨parityKernel_finrank_twenty (oneRowExtension C v) hDdim hoddD,
    parityKernel_distance_fourteen (oneRowExtension C v) hDdist⟩

end AxiomPackParityInsertion
