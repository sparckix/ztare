import Mathlib

/-!
Kernel-checkable linear and quadratic certificates for the same-degree
equivariant deformation calculation around the public dimension-three
Jacobian counterexample.

The coefficient order is

`b30, b21, b20, b11, b02, b01, c40, c31, c30, c21, c20, c12,
 c11, c03, c02, c01`.

The source- and target-scaling coordinates have already been fixed.  The
first theorem classifies the kernel of the exact coefficient linearization.
The second theorem proves that its remaining direction has no second-order
lift.  The surrounding formal-arc and equivariant-coordinate interpretation
is deliberately outside this finite certificate.
-/

namespace AxiomPackJacobianEquivariantRigidity

/-- Fifteen independent rows of the 39-equation Keller linearization. -/
def TangentSystem (x : Fin 16 → ℚ) : Prop :=
  2 * x 0 + 3 * x 1 - 2 * x 6 - 3 * x 7 = 0 ∧
  6 * x 0 + x 1 + 2 * x 2 + 6 * x 3 - 4 * x 6 + 5 * x 7 -
      2 * x 8 - 6 * x 9 = 0 ∧
  26 * x 0 + 9 * x 1 + 18 * x 11 + 6 * x 2 + 21 * x 3 -
      18 * x 4 - 20 * x 6 + 12 * x 7 - 6 * x 8 - 21 * x 9 = 0 ∧
  52 * x 0 + 78 * x 1 + 54 * x 12 - 36 * x 2 - 9 * x 3 -
      54 * x 5 - 88 * x 6 - 33 * x 7 + 36 * x 8 - 45 * x 9 = 0 ∧
  68 * x 0 + 18 * x 1 + 135 * x 11 - 81 * x 13 + 12 * x 2 +
      54 * x 3 - 135 * x 4 - 56 * x 6 + 36 * x 7 - 12 * x 8 -
      54 * x 9 = 0 ∧
  8 * x 0 + 156 * x 1 + 135 * x 11 + 216 * x 12 - 162 * x 14 -
      144 * x 2 - 108 * x 3 + 27 * x 4 - 216 * x 5 - 152 * x 6 -
      48 * x 7 + 144 * x 8 - 108 * x 9 = 0 ∧
  172 * x 0 - 36 * x 1 + 108 * x 10 - 135 * x 12 + 162 * x 15 +
      78 * x 2 + 234 * x 3 - 27 * x 5 + 8 * x 6 + 117 * x 7 -
      186 * x 8 - 99 * x 9 = 0 ∧
  56 * x 0 - 20 * x 1 + 378 * x 11 - 621 * x 13 + 8 * x 2 +
      60 * x 3 - 378 * x 4 - 48 * x 6 + 80 * x 7 - 8 * x 8 -
      60 * x 9 = 0 ∧
  590 * x 0 + 9 * x 1 + 324 * x 10 + 297 * x 11 - 324 * x 12 +
      405 * x 14 + 729 * x 15 - 42 * x 2 + 585 * x 3 - 702 * x 4 -
      405 * x 5 - 320 * x 6 + 207 * x 7 - 282 * x 8 - 261 * x 9 = 0 ∧
  308 * x 0 + 216 * x 1 + 324 * x 10 + 297 * x 12 + 405 * x 15 -
      366 * x 2 + 108 * x 3 - 702 * x 5 - 320 * x 6 + 72 * x 7 +
      42 * x 8 - 351 * x 9 = 0 ∧
  384 * x 0 - 272 * x 1 + 432 * x 10 + 1602 * x 11 - 216 * x 12 -
      891 * x 13 + 972 * x 14 + 1620 * x 15 - 520 * x 2 +
      588 * x 3 - 2574 * x 4 - 1404 * x 5 - 480 * x 6 +
      596 * x 7 + 88 * x 8 - 372 * x 9 = 0 ∧
  48 * x 0 - 64 * x 1 - 108 * x 10 - 351 * x 11 - 378 * x 12 +
      297 * x 14 - 324 * x 15 + 376 * x 2 + 84 * x 3 + 108 * x 4 +
      702 * x 5 + 192 * x 6 - 128 * x 7 - 268 * x 8 + 240 * x 9 = 0 ∧
  96 * x 0 - 64 * x 1 + 108 * x 10 - 351 * x 12 + 297 * x 15 +
      184 * x 2 + 216 * x 3 + 108 * x 5 + 96 * x 6 + 4 * x 7 -
      256 * x 8 + 72 * x 9 = 0 ∧
  40 * x 0 - 12 * x 1 + 72 * x 10 - 24 * x 11 - 91 * x 12 +
      117 * x 14 + 165 * x 15 - 16 * x 2 + 42 * x 3 - 72 * x 4 -
      53 * x 5 - 12 * x 7 - 48 * x 8 + 32 * x 9 = 0 ∧
  48 * x 0 + 192 * x 10 - 72 * x 12 + 351 * x 15 - 72 * x 2 +
      64 * x 3 - 216 * x 5 - 72 * x 8 - 4 * x 9 = 0

/-- The unique normalized infinitesimal direction. -/
def tangentDirection (s : ℚ) : Fin 16 → ℚ :=
  ![-3 * s, 2 * s, -(11 / 4) * s, 3 * s, 0, s,
    -(3 / 2) * s, s, -(9 / 4) * s, 2 * s, -(7 / 12) * s,
    0, s, 0, 0, 0]

/-- Every normalized first-order solution is a scalar multiple of the one
displayed tangent.  In particular all four coefficients absent from the
weighted-lift ansatz (`b02`, `c12`, `c03`, `c02`) vanish to first order. -/
theorem tangent_classification (x : Fin 16 → ℚ) (h : TangentSystem x) :
    x = tangentDirection (x 5) := by
  rcases h with
    ⟨h0, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14⟩
  funext i
  fin_cases i <;> simp [tangentDirection] <;> linarith

/-- Eight coefficient equations that any second-order correction to the
remaining tangent would have to satisfy. -/
def SecondOrderSystem (s : ℚ) (y : Fin 16 → ℚ) : Prop :=
  2 * y 0 + 3 * y 1 - 2 * y 6 - 3 * y 7 = 0 ∧
  -7 * s ^ 2 + 72 * y 0 + 12 * y 1 + 24 * y 2 + 72 * y 3 -
      48 * y 6 + 60 * y 7 - 24 * y 8 - 72 * y 9 = 0 ∧
  -9 * s ^ 2 + 104 * y 0 + 36 * y 1 + 72 * y 11 + 24 * y 2 +
      84 * y 3 - 72 * y 4 - 80 * y 6 + 48 * y 7 - 24 * y 8 -
      84 * y 9 = 0 ∧
  59 * s ^ 2 + 416 * y 0 + 624 * y 1 + 432 * y 12 - 288 * y 2 -
      72 * y 3 - 432 * y 5 - 704 * y 6 - 264 * y 7 + 288 * y 8 -
      360 * y 9 = 0 ∧
  -13 * s ^ 2 + 136 * y 0 + 36 * y 1 + 270 * y 11 - 162 * y 13 +
      24 * y 2 + 108 * y 3 - 270 * y 4 - 112 * y 6 + 72 * y 7 -
      24 * y 8 - 108 * y 9 = 0 ∧
  167 * s ^ 2 + 32 * y 0 + 624 * y 1 + 540 * y 11 + 864 * y 12 -
      648 * y 14 - 576 * y 2 - 432 * y 3 + 108 * y 4 - 864 * y 5 -
      608 * y 6 - 192 * y 7 + 576 * y 8 - 432 * y 9 = 0 ∧
  -25 * s ^ 2 + 168 * y 0 - 60 * y 1 + 1134 * y 11 -
      1863 * y 13 + 24 * y 2 + 180 * y 3 - 1134 * y 4 - 144 * y 6 +
      240 * y 7 - 24 * y 8 - 180 * y 9 = 0 ∧
  -y 11 + 9 * y 13 - 2 * y 14 + 3 * y 4 = 0

/-- The exact left-kernel combination of the eight equations is `s^2=0`.
Thus a nonzero tangent has no second-order lift. -/
theorem no_second_order_lift
    (s : ℚ) (y : Fin 16 → ℚ) (hs : s ≠ 0)
    (h : SecondOrderSystem s y) : False := by
  rcases h with ⟨h0, h1, h2, h3, h4, h5, h6, h7⟩
  have hsquare : s ^ 2 = 0 := by
    linear_combination
      -1328 * h0 - 240 * h1 + 384 * h2 - 2 * h3 - 156 * h4 +
      h5 + 12 * h6 - 324 * h7
  exact hs (sq_eq_zero_iff.mp hsquare)

/-!
The first omitted equivariant degree shell adds the coordinates
`b40, b12, c50, c22`.  Its new tangent is killed quadratically.  The old
tangent can use `b40` and `c50` as an order-two correction, so the decisive
finite certificate moves to order three.  The coordinate order below is

`b40, b30, b21, b20, b12, b11, b02, b01, c50, c40, c31, c30,
 c22, c21, c20, c12, c11, c03, c02, c01`.
-/

/-- Ten independent order-two coefficient equations, followed by one
third-order cokernel compatibility equation, for the surviving adjacent-shell
tangent.  The constants are part of the affine order-two system. -/
def AdjacentThirdOrderSystem (y : Fin 20 → ℚ) : Prop :=
  243 * y 0 - 243 * y 8 = 0 ∧
  324 * y 0 + 162 * y 1 + 243 * y 2 - 162 * y 8 - 162 * y 9 -
      243 * y 10 = 0 ∧
  486 * y 0 + 162 * y 1 + 243 * y 2 - 243 * y 4 - 324 * y 8 -
      162 * y 9 - 243 * y 10 + 243 * y 12 = 0 ∧
  2808 * y 0 - 1944 * y 1 - 324 * y 2 - 648 * y 3 - 1944 * y 5 -
      4104 * y 8 + 1296 * y 9 - 1620 * y 10 + 648 * y 11 +
      1944 * y 13 + 189 = 0 ∧
  360 * y 0 - 2808 * y 1 - 972 * y 2 - 648 * y 3 + 324 * y 4 -
      2268 * y 5 + 1944 * y 6 - 2520 * y 8 + 2160 * y 9 -
      1296 * y 10 + 648 * y 11 + 1620 * y 12 + 2268 * y 13 -
      1944 * y 15 + 243 = 0 ∧
  5328 * y 0 + 3744 * y 1 + 5616 * y 2 - 2592 * y 3 - 648 * y 5 -
      3888 * y 7 + 720 * y 8 - 6336 * y 9 - 2376 * y 10 +
      2592 * y 11 - 3240 * y 13 + 3888 * y 16 + 531 = 0 ∧
  984 * y 0 + 1224 * y 1 + 324 * y 2 + 216 * y 3 - 1458 * y 4 +
      972 * y 5 - 2430 * y 6 + 24 * y 8 - 1008 * y 9 +
      648 * y 10 - 216 * y 11 - 972 * y 12 - 972 * y 13 +
      2430 * y 15 - 1458 * y 17 - 117 = 0 ∧
  3216 * y 0 + 96 * y 1 + 1872 * y 2 - 1728 * y 3 - 2808 * y 4 -
      1296 * y 5 + 324 * y 6 - 2592 * y 7 - 1488 * y 8 -
      1824 * y 9 - 576 * y 10 + 1728 * y 11 + 1188 * y 12 -
      1296 * y 13 + 1620 * y 15 + 2592 * y 16 - 1944 * y 18 +
      501 = 0 ∧
  264 * y 0 + 168 * y 1 - 60 * y 2 + 24 * y 3 - 1026 * y 4 +
      180 * y 5 - 1134 * y 6 - 120 * y 8 - 144 * y 9 +
      240 * y 10 - 24 * y 11 - 108 * y 12 - 180 * y 13 +
      1134 * y 15 - 1863 * y 17 - 25 = 0 ∧
  1104 * y 0 - 1504 * y 1 + 912 * y 2 - 1440 * y 3 - 4680 * y 4 -
      1728 * y 5 + 3240 * y 6 - 2592 * y 7 - 1200 * y 8 +
      64 * y 9 - 48 * y 10 + 1440 * y 11 + 2736 * y 12 -
      864 * y 13 + 1944 * y 15 + 2592 * y 16 - 2430 * y 17 -
      5184 * y 18 + 635 = 0 ∧
  15 * y 0 - 3 * y 8 = 0

/-- The surviving tangent has no order-three lift, even after allowing an
arbitrary order-two correction in all twenty adjacent-shell coordinates. -/
theorem no_adjacent_third_order_lift
    (y : Fin 20 → ℚ) (h : AdjacentThirdOrderSystem y) : False := by
  rcases h with ⟨h0, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10⟩
  have hbad : (-3 / 64 : ℚ) = 0 := by
    linear_combination
      (911 / 1944) * h0 + (115 / 108) * h1 - (77 / 108) * h2 -
      (35 / 144) * h3 + (61 / 144) * h4 + (5 / 288) * h5 +
      (55 / 96) * h6 - (1 / 24) * h7 - (15 / 32) * h8 +
      (1 / 64) * h9 + (1 / 8) * h10
  norm_num at hbad

/-- Closed negative-existence form of the adjacent-shell obstruction.  This
is the canonical theorem boundary for downstream ratification: the
inconsistent system is the object being excluded, rather than an inherited
premise of the target declaration. -/
theorem no_adjacent_third_order_solution :
    ¬ ∃ y : Fin 20 → ℚ, AdjacentThirdOrderSystem y := by
  rintro ⟨y, h⟩
  exact no_adjacent_third_order_lift y h

end AxiomPackJacobianEquivariantRigidity
