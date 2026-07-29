import ZtareProofs.AxiomPackJacobianGaugeMinimum
import ZtareProofs.AxiomPackJacobianRootVolumeRectifier

/-!
Arithmetic aggregation for the all-prefix contact-complexity result.

The family-specific algebra is carried by the imported second-jet and
root-cover certificates. This file records the two discrete implications
used in the minimax synthesis:

* a prefix strictly below slope two has first degree at most two and second
  degree at most four;
* substitution words built from coefficients of degree at most `2 * n + 1`
  remain in the same triangular filtration.

The completed formal-contact group and the existence of the all-order
root-cover rectifier remain the mathematical construction documented with
the source artifact. This terminal is therefore an arithmetic and carried-
certificate endpoint, not a replacement formalization of that completed
group.
-/

namespace AxiomPackJacobianAllPrefixContactComplexity

open AxiomPackJacobianGaugeMinimum

def sourceExcess (degree : ℕ) : ℕ := degree - 1

/-!
The slope lower bound needs only the source-degree-two order-one window.
After the filtered target reduction, it has nine liftable source monomials
and six Hamiltonian target columns.  The following exact coefficient minor
is a compact independence certificate for that complete low window.
-/

def orderOneColumn : Fin 15 → CPair :=
  ![
    sourceUColumn (0, 1),
    sourceUColumn (1, 0),
    sourceUColumn (0, 2),
    sourceUColumn (1, 1),
    sourceUColumn (2, 0),
    sourceVColumn (0, 1),
    sourceVColumn (0, 2),
    sourceVColumn (1, 1),
    sourceVColumn (2, 0),
    (1, 0),
    (seedQPoly, 0),
    (0, 1),
    (-seedPPoly, seedQPoly),
    (0, seedPPoly),
    (0, seedPPoly ^ 2)
  ]

def orderOneRow : Fin 15 → CPair → ℚ :=
  ![
    fun pair => coeffVT pair.1 0 0,
    fun pair => coeffVT pair.1 0 1,
    fun pair => coeffVT pair.1 0 2,
    fun pair => coeffVT pair.1 0 3,
    fun pair => coeffVT pair.1 0 4,
    fun pair => coeffVT pair.1 1 0,
    fun pair => coeffVT pair.1 1 1,
    fun pair => coeffVT pair.1 1 2,
    fun pair => coeffVT pair.1 1 3,
    fun pair => coeffVT pair.1 2 0,
    fun pair => coeffVT pair.1 2 1,
    fun pair => coeffVT pair.1 2 2,
    fun pair => coeffVT pair.2 0 0,
    fun pair => coeffVT pair.2 0 1,
    fun pair => coeffVT pair.2 0 2
  ]

def orderOneMinor : Matrix (Fin 15) (Fin 15) ℚ :=
  fun row column => orderOneRow row (orderOneColumn column)

def orderOneExpectedMinor : Matrix (Fin 15) (Fin 15) ℚ :=
  ![
    ![0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    ![1 / 2, 0, 0, 0, 0, -3, 0, 0, 0, 0, -2, 0, 3, 0, 0],
    ![-1, 0, 1 / 2, 0, 0, -6, -3, 0, 0, 0, -4, 0, 3, 0, 0],
    ![-6, 0, -1, 0, 0, 0, -6, 0, 0, 0, -2, 0, 0, 0, 0],
    ![0, 0, -6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ![0, 1 / 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1 / 2, 0, 0],
    ![21 / 2, -1, 0, 1 / 2, 0, -1, 0, -3, 0, 0, 0, 0, 1, 0, 0],
    ![24, -6, 21 / 2, -1, 0, -12, -1, -6, 0, 0, -6, 0, 6, 0, 0],
    ![-6, 0, 24, -6, 0, 0, -12, 0, 0, 0, -6, 0, 0, 0, 0],
    ![0, 21 / 2, 0, 0, 1 / 2, 0, 0, 0, -3, 0, 4, 0, -21 / 4, 0, 0],
    ![-27 / 2, 24, 0, 21 / 2, -1, 12, 0, -1, -6, 0,
      31 / 2, 0, -12, 0, 0],
    ![27, -6, -27 / 2, 24, -6, -6, 12, -12, 0, 0, 10, 0, 3, 0, 0],
    ![0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    ![0, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 0, -2, -3, 0],
    ![0, 0, 0, 0, 0, -8, -2, 0, 0, 0, 0, 0, -4, -3, 9]
  ]

def orderOneSystem (x : Fin 15 → ℚ) : Fin 15 → ℚ :=
  ![
    x 9,
    x 0 / 2 - 3 * x 5 - 2 * x 10 + 3 * x 12,
    -x 0 + x 2 / 2 - 6 * x 5 - 3 * x 6 - 4 * x 10 + 3 * x 12,
    -6 * x 0 - x 2 - 6 * x 6 - 2 * x 10,
    -6 * x 2,
    x 1 / 2 - x 12 / 2,
    21 * x 0 / 2 - x 1 + x 3 / 2 - x 5 - 3 * x 7 + x 12,
    24 * x 0 - 6 * x 1 + 21 * x 2 / 2 - x 3 -
      12 * x 5 - x 6 - 6 * x 7 - 6 * x 10 + 6 * x 12,
    -6 * x 0 + 24 * x 2 - 6 * x 3 - 12 * x 6 - 6 * x 10,
    21 * x 1 / 2 + x 4 / 2 - 3 * x 8 + 4 * x 10 - 21 * x 12 / 4,
    -27 * x 0 / 2 + 24 * x 1 + 21 * x 3 / 2 - x 4 +
      12 * x 5 - x 7 - 6 * x 8 + 31 * x 10 / 2 - 12 * x 12,
    27 * x 0 - 6 * x 1 - 27 * x 2 / 2 + 24 * x 3 -
      6 * x 4 - 6 * x 5 + 12 * x 6 - 12 * x 7 +
      10 * x 10 + 3 * x 12,
    x 11,
    -2 * x 5 - 2 * x 12 - 3 * x 13,
    -8 * x 5 - 2 * x 6 - 4 * x 12 - 3 * x 13 + 9 * x 14
  ]

set_option maxHeartbeats 3000000 in
-- Only the fifteen selected coefficient equations are normalized; this
-- avoids replaying every polynomial entry inside a determinant expansion.
theorem order_one_minor_mulVec_eq_expected (x : Fin 15 → ℚ) :
    orderOneMinor.mulVec x = orderOneExpectedMinor.mulVec x := by
  funext row
  fin_cases row <;>
    norm_num [Matrix.mulVec, dotProduct, orderOneMinor,
      orderOneExpectedMinor, orderOneRow, orderOneColumn,
      sourceUColumn, sourceVColumn, shiftByMonomial, coeffVT,
      jacPV, jacPT, jacQV, jacQT, seedPPoly, seedQPoly,
      cMul, cPow, qPoly, cConst, cV, cT, cAdd, cNeg,
      Finset.sum_range_succ, Fin.sum_univ_succ]

theorem order_one_expected_mulVec_eq_system (x : Fin 15 → ℚ) :
    orderOneExpectedMinor.mulVec x = orderOneSystem x := by
  funext row
  fin_cases row <;>
    norm_num [Matrix.mulVec, dotProduct, orderOneExpectedMinor,
      orderOneSystem, Fin.sum_univ_succ] <;>
    (try ring_nf) <;>
    congr

set_option linter.flexible false in
set_option maxHeartbeats 3000000 in
-- Exact Gaussian elimination of the displayed low-order system.
theorem order_one_expected_minor_kernel
    (x : Fin 15 → ℚ)
    (hzero : orderOneExpectedMinor.mulVec x = 0) :
    x = 0 := by
  have hsystem : orderOneSystem x = 0 := by
    rw [← order_one_expected_mulVec_eq_system]
    exact hzero
  have h0 := congrFun hsystem (0 : Fin 15)
  have h1 := congrFun hsystem (1 : Fin 15)
  have h2 := congrFun hsystem (2 : Fin 15)
  have h3 := congrFun hsystem (3 : Fin 15)
  have h4 := congrFun hsystem (4 : Fin 15)
  have h5 := congrFun hsystem (5 : Fin 15)
  have h6 := congrFun hsystem (6 : Fin 15)
  have h7 := congrFun hsystem (7 : Fin 15)
  have h8 := congrFun hsystem (8 : Fin 15)
  have h9 := congrFun hsystem (9 : Fin 15)
  have h10 := congrFun hsystem (10 : Fin 15)
  have h11 := congrFun hsystem (11 : Fin 15)
  have h12 := congrFun hsystem (12 : Fin 15)
  have h13 := congrFun hsystem (13 : Fin 15)
  have h14 := congrFun hsystem (14 : Fin 15)
  simp [orderOneSystem] at h0 h1 h2 h3 h4 h5 h6 h7 h8 h9 h10 h11 h12 h13 h14
  have hx0 : x 0 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx1 : x 1 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx2 : x 2 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx3 : x 3 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx4 : x 4 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx5 : x 5 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx6 : x 6 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx7 : x 7 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx8 : x 8 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx9 : x 9 = 0 := by exact h0
  have hx10 : x 10 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx11 : x 11 = 0 := by exact h12
  have hx12 : x 12 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx13 : x 13 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  have hx14 : x 14 = 0 := by linarith [h0, h1, h2, h3, h4, h5, h6,
    h7, h8, h9, h10, h11, h12, h13, h14]
  funext index
  fin_cases index
  · convert hx0 using 1
  · convert hx1 using 1
  · convert hx2 using 1
  · convert hx3 using 1
  · convert hx4 using 1
  · convert hx5 using 1
  · convert hx6 using 1
  · convert hx7 using 1
  · convert hx8 using 1
  · convert hx9 using 1
  · convert hx10 using 1
  · convert hx11 using 1
  · convert hx12 using 1
  · convert hx13 using 1
  · convert hx14 using 1

theorem order_one_minor_mulVec_injective :
    Function.Injective orderOneMinor.mulVec := by
  intro left right heq
  have hexpected :
      orderOneExpectedMinor.mulVec left =
        orderOneExpectedMinor.mulVec right := by
    rw [← order_one_minor_mulVec_eq_expected,
      ← order_one_minor_mulVec_eq_expected]
    exact heq
  have hkernel :
      orderOneExpectedMinor.mulVec (left - right) = 0 := by
    rw [Matrix.mulVec_sub, hexpected, sub_self]
  have hzero := order_one_expected_minor_kernel (left - right) hkernel
  exact sub_eq_zero.mp hzero

/-- Integrality turns a strict first-order slope-two inequality into the
degree-two window. -/
theorem first_degree_of_strictly_subcritical
    (degree : ℕ) (h : sourceExcess degree < 2) :
    degree ≤ 2 := by
  simp [sourceExcess] at h
  omega

/-- Integrality turns a strict second-order slope-two inequality into the
degree-four window. -/
theorem second_degree_of_strictly_subcritical
    (degree : ℕ) (h : sourceExcess degree < 4) :
    degree ≤ 4 := by
  simp [sourceExcess] at h
  omega

/-- If the low first-order contact fiber has zero source component and the
based second jet requires degree at least five, then every prefix containing
orders one and two reaches slope two. -/
theorem second_jet_forces_prefix_slope_two
    (firstDegree secondDegree : ℕ)
    (hfirst :
      firstDegree ≤ 2 → firstDegree = 0)
    (hsecond :
      firstDegree = 0 → 5 ≤ secondDegree) :
    2 ≤ sourceExcess firstDegree ∨
      4 ≤ sourceExcess secondDegree := by
  by_cases hcritical : 2 ≤ sourceExcess firstDegree
  · exact Or.inl hcritical
  · right
    have hfirstWindow : firstDegree ≤ 2 := by
      apply first_degree_of_strictly_subcritical
      omega
    have hfirstZero : firstDegree = 0 := hfirst hfirstWindow
    have hsecondSharp : 5 ≤ secondDegree := hsecond hfirstZero
    simp [sourceExcess]
    omega

/-- The exact composition/logarithm word envelope used by the all-order
root-cover upper construction. -/
theorem slope_two_logarithm_word
    (n r degreeSum : ℕ)
    (hr : 0 < r)
    (hdegree : degreeSum ≤ 2 * n + r) :
    degreeSum - (r - 1) ≤ 2 * n + 1 :=
  AxiomPackJacobianRootVolumeRectifier.slope_two_word_envelope
    n r degreeSum hr hdegree

/-- Terminal aggregation of the carried second-jet certificate and the two
discrete filtration implications. -/
theorem all_prefix_contact_complexity_arithmetic_terminal_certificate :
    Function.Injective orderOneMinor.mulVec ∧
      (¬ AxiomPackJacobianGaugeMinimum.generatedBySourceAndTarget
        AxiomPackJacobianGaugeMinimum.residualPair) ∧
      (∀ firstDegree secondDegree : ℕ,
        (firstDegree ≤ 2 → firstDegree = 0) →
        (firstDegree = 0 → 5 ≤ secondDegree) →
        (2 ≤ sourceExcess firstDegree ∨
          4 ≤ sourceExcess secondDegree)) ∧
      (∀ n r degreeSum : ℕ,
        0 < r →
        degreeSum ≤ 2 * n + r →
        degreeSum - (r - 1) ≤ 2 * n + 1) := by
  refine ⟨order_one_minor_mulVec_injective,
    AxiomPackJacobianGaugeMinimum.residual_not_generated, ?_, ?_⟩
  · exact second_jet_forces_prefix_slope_two
  · exact slope_two_logarithm_word

end AxiomPackJacobianAllPrefixContactComplexity
