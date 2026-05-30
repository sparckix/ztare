import Mathlib.Tactic

/-!
# Translation-Covariant Matrix-Block Exclusion

This file records the algebraic core of the Phase 5EW/Track B pivot.

It does **not** prove Navier-Stokes regularity.  It formalizes the narrow
admissibility fact suggested by the Stokes-natural Track B submission:
an observable block that is linear in `V` and commutes with all torus
translations cannot connect two Fourier characters that some translation
separates.

Important scope note: a mixed-gain observable around a fixed background `W`
can be translation-*equivariant* when the missing Fourier momentum is supplied
by a mode of `W`.  This file therefore excludes only W-independent off-diagonal
linear state-price blocks; it does not close the W-coupled matrix-block ledger.

Analytic/PDE obligations remain outside this file:

* defining the full Stokes-natural/background-covariant observable class;
* proving the remaining same-mode/diagonal exact-quartic coercivity lemma;
* proving the Navier-Stokes dynamics only need this admissible class.
-/

namespace ZtareProofs.NS

theorem translationCovariantBlock_zero_of_character_separation
    {F : Type*} [Field F] {χk χl C : F}
    (hcov : χk * C = C * χl) (hsep : χk ≠ χl) : C = 0 := by
  have hzero : (χk - χl) * C = 0 := by
    calc
      (χk - χl) * C = χk * C - χl * C := by ring
      _ = C * χl - χl * C := by rw [hcov]
      _ = 0 := by ring
  have hdiff : χk - χl ≠ 0 := sub_ne_zero.mpr hsep
  exact (mul_eq_zero.mp hzero).resolve_left hdiff

/-- A theorem-shaped statement of the remaining non-tautological split. -/
structure StokesNaturalTrackBObligations : Prop where
  offDiagonalBlocksExcluded :
    ∀ {F : Type*} [Field F] {χk χl C : F},
      χk * C = C * χl → χk ≠ χl → C = 0
  sameModeQuarticCoercivityOpen : True
  nullspaceGainLemmaOpen : True

theorem stokesNatural_offDiagonalExclusion_obligationPacket :
    StokesNaturalTrackBObligations := by
  refine ⟨?_, trivial, trivial⟩
  intro F _ χk χl C hcov hsep
  exact translationCovariantBlock_zero_of_character_separation hcov hsep

end ZtareProofs.NS
