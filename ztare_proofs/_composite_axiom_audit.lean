import Mathlib

open Polynomial

theorem iso_lemma_div_add_numerator_cancel
    {F : Type*} [Field F] (d p r : F) (hd : d ≠ 0) :
    (p * d + r) / d = p + r / d := by exact?

theorem iso_lemma_field_div_eq_add_div
    {F : Type*} [Field F] (x d p r : F)
    (h : x = p * d + r) (hd : d ≠ 0) :
    x / d = p + r / d := by
  rw [h]
  exact iso_lemma_div_add_numerator_cancel d p r hd
#print axioms iso_lemma_field_div_eq_add_div
