import Mathlib.Tactic
import ZtareProofs.ns_matrix_block_sos_bossfight

/-!
# Finite PSD certificate witnesses

Lean-side witnesses exported from the finite Track B PSD audits.  These are
finite operator certificates, not global Navier-Stokes estimates.  Their role
is to turn a passing numerical PSD row into an auditable operator object before
any future threshold-gap identity is claimed.
-/

namespace ZtareProofs.NS

noncomputable section

/-- Exact diagonal slack from
`phase5fa_sparse_psd_pricing_certificate_exact_witnesses.json`, top row
`low_high_cluster_K2`, generator `leray_full_PE10P`.

The exact Fourier replay computes the finite pricing slack `(2/3)G - H` as a
diagonal rational matrix with the entries below. -/
def phase5faLowHighK2LerayFullPE10PSlackDiag (i : Fin 5) : ℝ :=
  match i.val with
  | 0 => (23 : ℝ) / 210
  | 1 => (125 : ℝ) / 6
  | 2 => (48 : ℝ) / 5
  | 3 => (1492 : ℝ) / 105
  | _ => (6347009 : ℝ) / 465885

theorem phase5faLowHighK2LerayFullPE10PSlackDiag_nonnegative :
    ∀ i : Fin 5, 0 ≤ phase5faLowHighK2LerayFullPE10PSlackDiag i := by
  intro i
  fin_cases i <;> norm_num [phase5faLowHighK2LerayFullPE10PSlackDiag]

/-- Checked finite PSD operator for the exported Phase 5FA top-row slack. -/
def phase5faLowHighK2LerayFullPE10PSlackPSDOperator :
    FinitePSDOperator 5 :=
  finiteDiagonalPSDOperator
    phase5faLowHighK2LerayFullPE10PSlackDiag
    phase5faLowHighK2LerayFullPE10PSlackDiag_nonnegative

/-- Exact diagonal slack from
`phase5fa_sparse_psd_pricing_certificate_exact_witnesses.json`, row
`low_high_cluster_K2`, generator `leray_coordinate_PE00P`. -/
def phase5faLowHighK2LerayCoordinatePE00PSlackDiag (i : Fin 5) : ℝ :=
  match i.val with
  | 0 => (23 : ℝ) / 210
  | 1 => (125 : ℝ) / 6
  | 2 => (48 : ℝ) / 5
  | 3 => (14 : ℝ)
  | _ => (4518931 : ℝ) / 332775

theorem phase5faLowHighK2LerayCoordinatePE00PSlackDiag_nonnegative :
    ∀ i : Fin 5, 0 ≤ phase5faLowHighK2LerayCoordinatePE00PSlackDiag i := by
  intro i
  fin_cases i <;> norm_num
    [phase5faLowHighK2LerayCoordinatePE00PSlackDiag]

/-- Checked finite PSD operator for the second exported Phase 5FA K2 slack. -/
def phase5faLowHighK2LerayCoordinatePE00PSlackPSDOperator :
    FinitePSDOperator 5 :=
  finiteDiagonalPSDOperator
    phase5faLowHighK2LerayCoordinatePE00PSlackDiag
    phase5faLowHighK2LerayCoordinatePE00PSlackDiag_nonnegative

/-- Symbolic Phase 5FA low-high cluster slack, generator
`leray_full_PE10P`.

This is the Lean-side finite-kernel witness for the SymPy symbolic replay in
`phase5fa_symbolic_low_high_psd_replay.py`.  It is parameterized by the shell
integer `K` and proves only that the replayed diagonal slack `(2/3)G - H` is
PSD for this fixed five-dimensional low-high stencil.  It is not a continuum
limit theorem. -/
def phase5faLowHighClusterKLerayFullPE10PSymbolicSlackDiag
    (K : ℕ) (i : Fin 5) : ℝ :=
  let k : ℝ := K
  match i.val with
  | 0 => (23 : ℝ) / 210
  | 1 => ((k ^ 2 + 1) ^ 3) / 6
  | 2 =>
      (k ^ 2 * (k + 1) ^ 2 * (k + 2) ^ 2) /
        (6 * (k ^ 2 + 2 * k + 2))
  | 3 =>
      (k ^ 2 *
          (4 * k ^ 8 + 12 * k ^ 6 + 21 * k ^ 4 +
            23 * k ^ 2 + 18)) /
        (6 * ((2 * k ^ 2 - 2 * k + 3) *
          (2 * k ^ 2 + 2 * k + 3)))
  | _ =>
      (16 * k ^ 20 + 320 * k ^ 19 + 3296 * k ^ 18 +
          22848 * k ^ 17 + 118712 * k ^ 16 +
          489344 * k ^ 15 + 1656852 * k ^ 14 +
          4713496 * k ^ 13 + 11441017 * k ^ 12 +
          23939276 * k ^ 11 + 43457935 * k ^ 10 +
          68652574 * k ^ 9 + 94362581 * k ^ 8 +
          112438296 * k ^ 7 + 115263888 * k ^ 6 +
          100365040 * k ^ 5 + 72767964 * k ^ 4 +
          42565104 * k ^ 3 + 19059024 * k ^ 2 +
          5896512 * k + 972000) /
        (6 * ((k ^ 2 + 2) * (k ^ 2 + 2 * k + 2) *
          (k ^ 2 + 2 * k + 6) * (k ^ 2 + 4 * k + 6) *
          (2 * k ^ 2 + 2 * k + 5) *
          (2 * k ^ 2 + 4 * k + 5) *
          (2 * k ^ 2 + 4 * k + 9) *
          (2 * k ^ 2 + 6 * k + 9)))

private theorem phase5fa_low_high_cluster_K_full_denom3_pos
    (K : ℕ) :
    0 < 2 * (K : ℝ) ^ 2 - 2 * (K : ℝ) + 3 := by
  nlinarith [sq_nonneg (K : ℝ), sq_nonneg ((K : ℝ) - 1)]

private def phase5fa_low_high_cluster_K_full_d4_num (K : ℕ) : ℝ :=
  let k : ℝ := K
  16 * k ^ 20 + 320 * k ^ 19 + 3296 * k ^ 18 +
    22848 * k ^ 17 + 118712 * k ^ 16 +
    489344 * k ^ 15 + 1656852 * k ^ 14 +
    4713496 * k ^ 13 + 11441017 * k ^ 12 +
    23939276 * k ^ 11 + 43457935 * k ^ 10 +
    68652574 * k ^ 9 + 94362581 * k ^ 8 +
    112438296 * k ^ 7 + 115263888 * k ^ 6 +
    100365040 * k ^ 5 + 72767964 * k ^ 4 +
    42565104 * k ^ 3 + 19059024 * k ^ 2 +
    5896512 * k + 972000

private def phase5fa_low_high_cluster_K_full_d4_den (K : ℕ) : ℝ :=
  let k : ℝ := K
  6 * ((k ^ 2 + 2) * (k ^ 2 + 2 * k + 2) *
    (k ^ 2 + 2 * k + 6) * (k ^ 2 + 4 * k + 6) *
    (2 * k ^ 2 + 2 * k + 5) *
    (2 * k ^ 2 + 4 * k + 5) *
    (2 * k ^ 2 + 4 * k + 9) *
    (2 * k ^ 2 + 6 * k + 9))

private theorem phase5fa_low_high_cluster_K_full_d4_num_nonnegative
    (K : ℕ) :
    0 ≤ phase5fa_low_high_cluster_K_full_d4_num K := by
  unfold phase5fa_low_high_cluster_K_full_d4_num
  positivity

private theorem phase5fa_low_high_cluster_K_full_d4_den_nonnegative
    (K : ℕ) :
    0 ≤ phase5fa_low_high_cluster_K_full_d4_den K := by
  unfold phase5fa_low_high_cluster_K_full_d4_den
  positivity

theorem phase5faLowHighClusterKLerayFullPE10PSymbolicSlackDiag_nonnegative
    (K : ℕ) :
    ∀ i : Fin 5,
      0 ≤ phase5faLowHighClusterKLerayFullPE10PSymbolicSlackDiag K i := by
  intro i
  fin_cases i
  · norm_num [phase5faLowHighClusterKLerayFullPE10PSymbolicSlackDiag]
  · change 0 ≤ (((K : ℝ) ^ 2 + 1) ^ 3) / 6
    exact div_nonneg (by positivity) (by norm_num)
  · change
      0 ≤
        ((K : ℝ) ^ 2 * ((K : ℝ) + 1) ^ 2 * ((K : ℝ) + 2) ^ 2) /
          (6 * ((K : ℝ) ^ 2 + 2 * (K : ℝ) + 2))
    exact div_nonneg (by positivity) (by positivity)
  · unfold phase5faLowHighClusterKLerayFullPE10PSymbolicSlackDiag
    have hdenA :
        0 < 2 * (K : ℝ) ^ 2 - 2 * (K : ℝ) + 3 :=
      phase5fa_low_high_cluster_K_full_denom3_pos K
    have hdenB :
        0 < 2 * (K : ℝ) ^ 2 + 2 * (K : ℝ) + 3 := by
      positivity
    have hnum :
        0 ≤
          (K : ℝ) ^ 2 *
            (4 * (K : ℝ) ^ 8 + 12 * (K : ℝ) ^ 6 +
              21 * (K : ℝ) ^ 4 + 23 * (K : ℝ) ^ 2 + 18) := by
      positivity
    have hden :
        0 ≤
          6 *
            ((2 * (K : ℝ) ^ 2 - 2 * (K : ℝ) + 3) *
              (2 * (K : ℝ) ^ 2 + 2 * (K : ℝ) + 3)) := by
      positivity
    exact div_nonneg hnum hden
  · change
      0 ≤
        phase5fa_low_high_cluster_K_full_d4_num K /
          phase5fa_low_high_cluster_K_full_d4_den K
    exact
      div_nonneg
        (phase5fa_low_high_cluster_K_full_d4_num_nonnegative K)
        (phase5fa_low_high_cluster_K_full_d4_den_nonnegative K)

/-- PSD operator for the symbolic Phase 5FA low-high cluster replay,
`leray_full_PE10P`. -/
def phase5faLowHighClusterKLerayFullPE10PSymbolicSlackPSDOperator
    (K : ℕ) :
    FinitePSDOperator 5 :=
  finiteDiagonalPSDOperator
    (phase5faLowHighClusterKLerayFullPE10PSymbolicSlackDiag K)
    (phase5faLowHighClusterKLerayFullPE10PSymbolicSlackDiag_nonnegative K)

private def phase5fa_low_high_cluster_K_coordinate_d4_num (K : ℕ) : ℝ :=
  let k : ℝ := K
  16 * k ^ 20 + 320 * k ^ 19 + 3296 * k ^ 18 +
    22848 * k ^ 17 + 118712 * k ^ 16 +
    489320 * k ^ 15 + 1656516 * k ^ 14 +
    4711060 * k ^ 13 + 11429065 * k ^ 12 +
    23894654 * k ^ 11 + 43323631 * k ^ 10 +
    68316925 * k ^ 9 + 93659897 * k ^ 8 +
    111210972 * k ^ 7 + 113498340 * k ^ 6 +
    98317684 * k ^ 5 + 70914060 * k ^ 4 +
    41326704 * k ^ 3 + 18506832 * k ^ 2 +
    5776128 * k + 972000

private theorem phase5fa_low_high_cluster_K_coordinate_d4_num_nonnegative
    (K : ℕ) :
    0 ≤ phase5fa_low_high_cluster_K_coordinate_d4_num K := by
  unfold phase5fa_low_high_cluster_K_coordinate_d4_num
  positivity

private theorem phase5fa_low_high_cluster_K_quad_minus_linear_nonnegative
    (K : ℕ) :
    0 ≤ (K : ℝ) ^ 2 - (K : ℝ) + 1 := by
  nlinarith [sq_nonneg (K : ℝ), sq_nonneg ((K : ℝ) - 1)]

/-- Symbolic Phase 5FA low-high cluster slack, generator
`leray_coordinate_PE00P`.

This is the second generator family emitted by
`phase5fa_symbolic_low_high_psd_replay.py`. -/
def phase5faLowHighClusterKLerayCoordinatePE00PSymbolicSlackDiag
    (K : ℕ) (i : Fin 5) : ℝ :=
  let k : ℝ := K
  match i.val with
  | 0 => (23 : ℝ) / 210
  | 1 => ((k ^ 2 + 1) ^ 3) / 6
  | 2 =>
      (k ^ 2 * (k + 1) ^ 2 * (k + 2) ^ 2) /
        (6 * (k ^ 2 + 2 * k + 2))
  | 3 =>
      (k ^ 2 * (k ^ 2 - k + 1) * (k ^ 2 + k + 1)) / 6
  | _ =>
      phase5fa_low_high_cluster_K_coordinate_d4_num K /
        phase5fa_low_high_cluster_K_full_d4_den K

theorem phase5faLowHighClusterKLerayCoordinatePE00PSymbolicSlackDiag_nonnegative
    (K : ℕ) :
    ∀ i : Fin 5,
      0 ≤
        phase5faLowHighClusterKLerayCoordinatePE00PSymbolicSlackDiag K i := by
  intro i
  fin_cases i
  · norm_num [phase5faLowHighClusterKLerayCoordinatePE00PSymbolicSlackDiag]
  · change 0 ≤ (((K : ℝ) ^ 2 + 1) ^ 3) / 6
    exact div_nonneg (by positivity) (by norm_num)
  · change
      0 ≤
        ((K : ℝ) ^ 2 * ((K : ℝ) + 1) ^ 2 * ((K : ℝ) + 2) ^ 2) /
          (6 * ((K : ℝ) ^ 2 + 2 * (K : ℝ) + 2))
    exact div_nonneg (by positivity) (by positivity)
  · change
      0 ≤
        ((K : ℝ) ^ 2 *
          ((K : ℝ) ^ 2 - (K : ℝ) + 1) *
            ((K : ℝ) ^ 2 + (K : ℝ) + 1)) / 6
    have hmid :
        0 ≤ (K : ℝ) ^ 2 - (K : ℝ) + 1 :=
      phase5fa_low_high_cluster_K_quad_minus_linear_nonnegative K
    have hnum :
        0 ≤
          (K : ℝ) ^ 2 *
            ((K : ℝ) ^ 2 - (K : ℝ) + 1) *
              ((K : ℝ) ^ 2 + (K : ℝ) + 1) := by
      positivity
    exact div_nonneg hnum (by norm_num)
  · change
      0 ≤
        phase5fa_low_high_cluster_K_coordinate_d4_num K /
          phase5fa_low_high_cluster_K_full_d4_den K
    exact
      div_nonneg
        (phase5fa_low_high_cluster_K_coordinate_d4_num_nonnegative K)
        (phase5fa_low_high_cluster_K_full_d4_den_nonnegative K)

/-- PSD operator for the symbolic Phase 5FA low-high cluster replay,
`leray_coordinate_PE00P`. -/
def phase5faLowHighClusterKLerayCoordinatePE00PSymbolicSlackPSDOperator
    (K : ℕ) :
    FinitePSDOperator 5 :=
  finiteDiagonalPSDOperator
    (phase5faLowHighClusterKLerayCoordinatePE00PSymbolicSlackDiag K)
    (phase5faLowHighClusterKLerayCoordinatePE00PSymbolicSlackDiag_nonnegative K)

/-- Exact Phase 5FB lifted upper for the symbolic low-high cluster replay.

The SymPy replay
`phase5fb_symbolic_quartic_threshold_replay.py` proves that the strongest
`global_matrix`/`low_high_cluster_K` lifted threshold row has upper
`gamma/mixed = 38/63` for the intended `K >= 2` family.  This Lean theorem
records only the exact target gap; the replay artifact carries the symbolic
matrix derivation and coefficient-positivity check. -/
theorem phase5fbLowHighClusterKGlobalMatrixUpper_lt_two_thirds :
    (38 : ℝ) / 63 < (2 : ℝ) / 3 := by
  norm_num

/-- The Phase 5FB symbolic global-matrix upper is below the Track B sharp wall.

This is only the scalar certificate bound.  A generated block still needs a
separate source proof that its gamma channel is bounded by this finite upper. -/
theorem phase5fbLowHighClusterKGlobalMatrixUpper_le_sharpTarget :
    (38 : ℝ) / 63 ≤ sharpTarget := by
  norm_num [sharpTarget]

/-- Exact lifted-slack form of the same Phase 5FB source candidate. -/
theorem phase5fbLowHighClusterKGlobalMatrixLiftedSlack_eq :
    ((2 : ℝ) / 3) ^ 2 - ((38 : ℝ) / 63) ^ 2 =
      (320 : ℝ) / 3969 := by
  norm_num

/-- Nonnegative lifted slack for the Phase 5FB symbolic low-high cluster
threshold replay. -/
theorem phase5fbLowHighClusterKGlobalMatrixLiftedSlack_nonnegative :
    0 ≤ ((2 : ℝ) / 3) ^ 2 - ((38 : ℝ) / 63) ^ 2 := by
  rw [phase5fbLowHighClusterKGlobalMatrixLiftedSlack_eq]
  norm_num

/-- Exact lifted amplitude-square ratio from the Phase 5FB symbolic
`global_matrix`/`low_high_cluster_K` replay. -/
def phase5fbLowHighClusterKGlobalMatrixLiftedRatio : ℝ :=
  ((38 : ℝ) / 63) ^ (2 : Nat)

theorem phase5fbLowHighClusterKGlobalMatrixLiftedRatio_eq :
    phase5fbLowHighClusterKGlobalMatrixLiftedRatio =
      (1444 : ℝ) / 3969 := by
  norm_num [phase5fbLowHighClusterKGlobalMatrixLiftedRatio]

theorem phase5fbLowHighClusterKGlobalMatrixLiftedRatio_nonnegative :
    0 ≤ phase5fbLowHighClusterKGlobalMatrixLiftedRatio := by
  rw [phase5fbLowHighClusterKGlobalMatrixLiftedRatio_eq]
  norm_num

theorem phase5fbLowHighClusterKGlobalMatrixLiftedRatio_le_one :
    phase5fbLowHighClusterKGlobalMatrixLiftedRatio ≤ 1 := by
  rw [phase5fbLowHighClusterKGlobalMatrixLiftedRatio_eq]
  norm_num

/-- Exact polynomial form of the first-polarization void-extraction boundary.

The SymPy void extractor found that the first low-high support mode has lifted
one-mode value

`1444*x^2*(x^2 + 2*y^2) / (441*(3*x^2 + 20*y^2)^2)`.

After clearing the positive common denominator
`3969*(3*x^2 + 20*y^2)^2`, the slack to the Phase 5FB boundary
`(38/63)^2` is exactly the nonnegative polynomial below.  This theorem records
only the finite Fourier algebra; it is not a continuum source theorem. -/
theorem phase5fbFirstPolarizationBoundarySlackPolynomial_eq
    (x y : ℝ) :
    (1444 : ℝ) * (3 * x ^ (2 : Nat) + 20 * y ^ (2 : Nat)) ^ (2 : Nat) -
        9 * (1444 : ℝ) * x ^ (2 : Nat) *
          (x ^ (2 : Nat) + 2 * y ^ (2 : Nat)) =
      (2888 : ℝ) * y ^ (2 : Nat) *
        (51 * x ^ (2 : Nat) + 200 * y ^ (2 : Nat)) := by
  ring

/-- The cleared first-polarization slack is nonnegative.  Sharpness occurs at
the algebraic void boundary `y = 0`; the theorem records only nonnegativity,
not a uniqueness or continuum optimality claim. -/
theorem phase5fbFirstPolarizationBoundarySlackPolynomial_nonnegative
    (x y : ℝ) :
    0 ≤ (2888 : ℝ) * y ^ (2 : Nat) *
        (51 * x ^ (2 : Nat) + 200 * y ^ (2 : Nat)) := by
  positivity

/-- First unit-defect root square from the Phase 5FB symbolic replay.

The replay reduces the normalized full-ledger defect polynomial to
`D(t) = t^2 + sigma * t^4`, with `sigma >= 0`.  This formula records the
first unit-defect amplitude-square selected by that polynomial. -/
noncomputable def phase5fbFirstUnitDefectRootSquare (sigma : ℝ) : ℝ :=
  (2 : ℝ) / (1 + Real.sqrt (1 + 4 * sigma))

/-- The symbolic first-root square cannot amplify the unit channel. -/
theorem phase5fbFirstUnitDefectRootSquare_le_one
    {sigma : ℝ} (hsigma : 0 ≤ sigma) :
    phase5fbFirstUnitDefectRootSquare sigma ≤ 1 := by
  unfold phase5fbFirstUnitDefectRootSquare
  have harg : 0 ≤ 1 + 4 * sigma := by nlinarith
  have hsqrt_sq :
      (Real.sqrt (1 + 4 * sigma)) ^ 2 = 1 + 4 * sigma :=
    Real.sq_sqrt harg
  have hsqrt_nonneg : 0 ≤ Real.sqrt (1 + 4 * sigma) :=
    Real.sqrt_nonneg (1 + 4 * sigma)
  have hsqrt_ge_one : 1 ≤ Real.sqrt (1 + 4 * sigma) := by
    nlinarith
  have hden_pos : 0 < 1 + Real.sqrt (1 + 4 * sigma) := by
    nlinarith
  rw [div_le_iff₀ hden_pos]
  nlinarith

/-- The symbolic first-root square is nonnegative. -/
theorem phase5fbFirstUnitDefectRootSquare_nonnegative
    {sigma : ℝ} (hsigma : 0 ≤ sigma) :
    0 ≤ phase5fbFirstUnitDefectRootSquare sigma := by
  unfold phase5fbFirstUnitDefectRootSquare
  have harg : 0 ≤ 1 + 4 * sigma := by nlinarith
  have hden_pos : 0 < 1 + Real.sqrt (1 + 4 * sigma) := by
    have hsqrt_nonneg : 0 ≤ Real.sqrt (1 + 4 * sigma) :=
      Real.sqrt_nonneg (1 + 4 * sigma)
    nlinarith
  positivity

end

end ZtareProofs.NS
