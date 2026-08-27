import Mathlib.Algebra.Field.ZMod
import Mathlib.RingTheory.Polynomial.RationalRoot

/-!
# Rational-root obstruction by one prime reduction

This kernel turns a root-free prime reduction into a no-rational-root theorem.
The rational-root theorem first clears the canonical denominator with
`scaleRoots`; survival of the leading coefficient keeps that denominator
nonzero modulo the selected prime.
-/

namespace FormalRationalRootModPrime

open IsFractionRing Polynomial

variable {modulus : ℕ} [Fact (Nat.Prime modulus)]

/-- If the leading coefficient survives modulo a prime and the reduced
polynomial has no root, then the integer polynomial has no rational root. -/
theorem rat_no_root_of_mod_prime_no_root
    (p : ℤ[X])
    (hlead : Int.castRingHom (ZMod modulus) p.leadingCoeff ≠ 0)
    (hnoRoot :
      ∀ x : ZMod modulus,
        (p.map (Int.castRingHom (ZMod modulus))).eval x ≠ 0)
    (q : ℚ) :
    (p.map (Int.castRingHom ℚ)).eval q ≠ 0 := by
  intro hq
  have hqAeval : aeval q p = 0 := by
    simpa [aeval_def, eval_map] using hq
  have hscaled :=
    num_isRoot_scaleRoots_of_aeval_eq_zero (A := ℤ) hqAeval
  let d : ℤ := den ℤ q
  let n : ℤ := num ℤ q
  have hdDvd : d ∣ p.leadingCoeff := by
    simpa [d] using den_dvd_of_is_root (A := ℤ) hqAeval
  have hdMod : Int.castRingHom (ZMod modulus) d ≠ 0 := by
    intro hd
    obtain ⟨c, hc⟩ := hdDvd
    have hcMod := congrArg (Int.castRingHom (ZMod modulus)) hc
    apply hlead
    simpa [map_mul, hd] using hcMod
  have hscaledInt : (p.scaleRoots d).eval n = 0 := by
    simpa [d, n, IsRoot] using hscaled
  have hscaledMod :
      ((p.scaleRoots d).map
          (Int.castRingHom (ZMod modulus))).eval
        (Int.castRingHom (ZMod modulus) n) = 0 := by
    simpa using
      congrArg (Int.castRingHom (ZMod modulus)) hscaledInt
  rw [map_scaleRoots p d
      (Int.castRingHom (ZMod modulus)) hlead] at hscaledMod
  let nMod : ZMod modulus := Int.castRingHom (ZMod modulus) n
  let dMod : ZMod modulus := Int.castRingHom (ZMod modulus) d
  let pMod : (ZMod modulus)[X] :=
    p.map (Int.castRingHom (ZMod modulus))
  have hscale := scaleRoots_eval_mul pMod (nMod / dMod) dMod
  have hcancel : dMod * (nMod / dMod) = nMod := by
    calc
      dMod * (nMod / dMod) = dMod * nMod / dMod := by
        rw [mul_div_assoc]
      _ = nMod := mul_div_cancel_left₀ nMod hdMod
  rw [hcancel, hscaledMod] at hscale
  have hpow : dMod ^ pMod.natDegree ≠ 0 := pow_ne_zero _ hdMod
  have hpMod : pMod.eval (nMod / dMod) = 0 := by
    exact (mul_eq_zero.mp hscale.symm).resolve_left hpow
  exact hnoRoot (nMod / dMod) hpMod

end FormalRationalRootModPrime
