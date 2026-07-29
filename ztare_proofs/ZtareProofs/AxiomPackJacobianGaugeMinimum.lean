import Mathlib

/-!
Kernel certificate for the gauge-minimal second source jet of the normalized
Jacobian family.

The target coordinate `filteredC` gives a quadratic normal form over
`ℚ[P,C]`.  Its normal monomials have injective leading signatures, reducing
the arbitrary-degree Hamiltonian window to seven generators.  The final
section checks an eight-coordinate dual obstruction and the explicit
degree-five upper witness in exact bivariate polynomial arithmetic.
-/

namespace AxiomPackJacobianGaugeMinimum

section FilteredTargetCoordinate

def seedP (g w : ℚ) : ℚ := g + 2 * w - 3 * w^2
def seedQ (g w : ℚ) : ℚ := w * g + w^2 - 2 * w^3

def filteredC (P Q : ℚ) : ℚ :=
  4 * P^3 - P^2 - 18 * P * Q + 27 * Q^2 + 4 * Q

/-- The new target coordinate pulls back with filtered degree six. -/
theorem filtered_coordinate_pullback (g w : ℚ) :
    filteredC (seedP g w) (seedQ g w) =
      g^2 * (3 * seedP g w + g - 1) := by
  simp [filteredC, seedP, seedQ]
  ring

/-- The target ring is quadratic in `Q` over the coordinates `(P,C)`. -/
theorem quadratic_target_relation (P Q : ℚ) :
    27 * Q^2 =
      filteredC P Q + (18 * P - 4) * Q - 4 * P^3 + P^2 := by
  simp [filteredC]
  ring

/-- Monic form used by the abstract quadratic reduction theorem. -/
theorem monic_quadratic_target_relation (P Q : ℚ) :
    Q^2 =
      (filteredC P Q - 4 * P^3 + P^2) / 27 +
        ((18 * P - 4) / 27) * Q := by
  simp [filteredC]
  ring

/-- Exact scaling expansion that exposes the weight-four leading term. -/
theorem scaled_seedP (g w s : ℚ) :
    seedP (s * g) (s^2 * w) =
      -3 * w^2 * s^4 + 2 * w * s^2 + g * s := by
  simp [seedP]
  ring

/-- Exact scaling expansion that exposes the weight-six leading term. -/
theorem scaled_seedQ (g w s : ℚ) :
    seedQ (s * g) (s^2 * w) =
      -2 * w^3 * s^6 + w^2 * s^4 + g * w * s^3 := by
  simp [seedQ]
  ring

/-- The filtered coordinate has leading signature `gamma²*w²` and weight
six after the two cusp cancellations. -/
theorem scaled_filteredC (g w s : ℚ) :
    filteredC (seedP (s * g) (s^2 * w)) (seedQ (s * g) (s^2 * w)) =
      -9 * g^2 * w^2 * s^6 + 6 * g^2 * w * s^4 +
        4 * g^3 * s^3 - g^2 * s^2 := by
  simp [filteredC, seedP, seedQ]
  ring

end FilteredTargetCoordinate

section AbstractQuadraticNormalForm

variable {R : Type*} [CommRing R]

/-- Coefficients `(Aₙ,Bₙ)` for reducing `qⁿ` to `Aₙ+qBₙ` under a monic
quadratic relation `q²=a+bq`. -/
def quadraticPower (a b : R) : ℕ → R × R
  | 0 => (1, 0)
  | n + 1 =>
      let previous := quadraticPower a b n
      (a * previous.2, previous.1 + b * previous.2)

theorem quadratic_power_normal_form
    (q a b : R) (hq : q^2 = a + b * q) (n : ℕ) :
    q^n = (quadraticPower a b n).1 + q * (quadraticPower a b n).2 := by
  induction n with
  | zero =>
      simp [quadraticPower]
  | succ n ih =>
      rw [pow_succ, ih]
      simp only [quadraticPower]
      calc
        ((quadraticPower a b n).1 + q * (quadraticPower a b n).2) * q =
            (quadraticPower a b n).1 * q +
              q^2 * (quadraticPower a b n).2 := by ring
        _ = a * (quadraticPower a b n).2 +
              q * ((quadraticPower a b n).1 +
                b * (quadraticPower a b n).2) := by
              rw [hq]
              ring

def quadraticPolynomialA (a b : R) (f : Polynomial R) : R :=
  f.sum fun n coefficient => coefficient * (quadraticPower a b n).1

def quadraticPolynomialB (a b : R) (f : Polynomial R) : R :=
  f.sum fun n coefficient => coefficient * (quadraticPower a b n).2

/-- Every polynomial in a quadratic generator has a two-term normal form. -/
theorem quadratic_polynomial_normal_form
    (q a b : R) (hq : q^2 = a + b * q) (f : Polynomial R) :
    Polynomial.eval q f =
      quadraticPolynomialA a b f + q * quadraticPolynomialB a b f := by
  classical
  simp only [Polynomial.eval_eq_sum, quadraticPolynomialA,
    quadraticPolynomialB, Polynomial.sum_def]
  rw [Finset.mul_sum]
  rw [← Finset.sum_add_distrib]
  apply Finset.sum_congr rfl
  intro n hn
  rw [quadratic_power_normal_form q a b hq n]
  ring

variable {S : Type*} [CommRing S]

theorem quadratic_power_normal_form_map
    (mapRS : R →+* S) (q : S) (a b : R)
    (hq : q^2 = mapRS a + mapRS b * q) (n : ℕ) :
    q^n =
      mapRS (quadraticPower a b n).1 +
        q * mapRS (quadraticPower a b n).2 := by
  induction n with
  | zero =>
      simp [quadraticPower]
  | succ n ih =>
      rw [pow_succ, ih]
      simp only [quadraticPower]
      calc
        (mapRS (quadraticPower a b n).1 +
            q * mapRS (quadraticPower a b n).2) * q =
          mapRS (quadraticPower a b n).1 * q +
            q^2 * mapRS (quadraticPower a b n).2 := by ring
        _ = mapRS (a * (quadraticPower a b n).2) +
            q * mapRS ((quadraticPower a b n).1 +
              b * (quadraticPower a b n).2) := by
            rw [hq]
            simp
            ring

/-- Functorial form: coefficients stay in the declared base ring while the
quadratic generator lives in an arbitrary commutative extension. -/
theorem quadratic_polynomial_normal_form_map
    (mapRS : R →+* S) (q : S) (a b : R)
    (hq : q^2 = mapRS a + mapRS b * q) (f : Polynomial R) :
    Polynomial.eval₂ mapRS q f =
      mapRS (quadraticPolynomialA a b f) +
        q * mapRS (quadraticPolynomialB a b f) := by
  classical
  simp only [Polynomial.eval₂_eq_sum, quadraticPolynomialA,
    quadraticPolynomialB, Polynomial.sum_def, map_sum]
  rw [Finset.mul_sum]
  rw [← Finset.sum_add_distrib]
  apply Finset.sum_congr rfl
  intro n hn
  rw [quadratic_power_normal_form_map mapRS q a b hq n]
  simp
  ring

end AbstractQuadraticNormalForm

section FilteredNormalMonomials

/-- Leading signature `(gamma exponent, w exponent)` for the normal monomial
`P^a * Q^b * C^c`, where the quadratic normal form has `b ≤ 1`. -/
def normalSignature (a b c : ℕ) : ℕ × ℕ :=
  (2 * c, 2 * a + 3 * b + 2 * c)

def normalWeight (a b c : ℕ) : ℕ := 4 * a + 6 * b + 6 * c

/-- Coefficient of the leading `gamma,w` monomial in the normal term
`P^a * Q^b * C^c`.  The three factors come from the exact scaling
identities `scaled_seedP`, `scaled_seedQ`, and `scaled_filteredC`. -/
def normalLeadingCoefficient (a b c : ℕ) : ℚ :=
  (-3 : ℚ)^a * (-2 : ℚ)^b * (-9 : ℚ)^c

theorem normal_leading_coefficient_ne_zero (a b c : ℕ) :
    normalLeadingCoefficient a b c ≠ 0 := by
  simp [normalLeadingCoefficient]

theorem normal_signature_injective
    (a b c a' b' c' : ℕ)
    (hb : b ≤ 1) (hb' : b' ≤ 1)
    (h : normalSignature a b c = normalSignature a' b' c') :
    a = a' ∧ b = b' ∧ c = c' := by
  simp only [normalSignature, Prod.mk.injEq] at h
  omega

/-- Exact enumeration of the scalar filtered piece through degree eight. -/
theorem normal_terms_le_eight
    (a b c : ℕ) (hb : b ≤ 1) (hweight : normalWeight a b c ≤ 8) :
    (b = 0 ∧ c = 0 ∧ a ≤ 2) ∨
    (b = 1 ∧ c = 0 ∧ a = 0) ∨
    (b = 0 ∧ c = 1 ∧ a = 0) := by
  simp only [normalWeight] at hweight
  omega

/-- Exact enumeration of the scalar filtered piece through degree ten. -/
theorem normal_terms_le_ten
    (a b c : ℕ) (hb : b ≤ 1) (hweight : normalWeight a b c ≤ 10) :
    (b = 0 ∧ c = 0 ∧ a ≤ 2) ∨
    (b = 1 ∧ c = 0 ∧ a ≤ 1) ∨
    (b = 0 ∧ c = 1 ∧ a ≤ 1) := by
  simp only [normalWeight] at hweight
  omega

/-- Coefficient comparison removes the extra `C` direction from an
integrable Hamiltonian field in the `(8,10)` component window. -/
theorem filtered_hamiltonian_extra_direction_vanishes
    (c dC dPC : ℚ)
    (hPQ2 : 27 * dPC = 0)
    (hP2Q : 12 * c = -18 * dPC)
    (hQ2 : -9 * c = 27 * dC) :
    c = 0 ∧ dC = 0 ∧ dPC = 0 := by
  constructor
  · linarith
  constructor <;> linarith

def filteredWindowFirst
    (a0 aP aP2 aQ aC P Q : ℚ) : ℚ :=
  a0 + aP * P + aP2 * P^2 + aQ * Q + aC * filteredC P Q

def filteredWindowSecond
    (b0 bP bP2 bQ bPQ bC bPC P Q : ℚ) : ℚ :=
  b0 + bP * P + bP2 * P^2 + bQ * Q + bPQ * P * Q +
    bC * filteredC P Q + bPC * P * filteredC P Q

/-- Formal divergence of the two filtered scalar normal forms. The displayed
formula is obtained by differentiating `filteredWindowFirst` in `P` and
`filteredWindowSecond` in `Q`. -/
def filteredWindowDivergence
    (aP aP2 aC bQ bPQ bC bPC P Q : ℚ) : ℚ :=
  aP + 2 * aP2 * P + aC * (12 * P^2 - 2 * P - 18 * Q) +
    bQ + bPQ * P + bC * (-18 * P + 54 * Q + 4) +
    bPC * P * (-18 * P + 54 * Q + 4)

/-- Every divergence-free field in the two scalar filtered windows is a
linear combination of the Hamiltonian fields of
`P,Q,P²,PQ,Q²,P³,P²Q`. This is the exact coefficient bridge from the
quadratic target chart to the seven columns used by the dual certificate. -/
theorem filtered_hamiltonian_window_decomposition
    (a0 aP aP2 aQ aC : ℚ)
    (b0 bP bP2 bQ bPQ bC bPC : ℚ)
    (hdiv : ∀ P Q : ℚ,
      filteredWindowDivergence aP aP2 aC bQ bPQ bC bPC P Q = 0) :
    aC = 0 ∧ bC = 0 ∧ bPC = 0 ∧
    ∃ kP kQ kP2 kPQ kQ2 kP3 kP2Q : ℚ,
      ∀ P Q : ℚ,
        filteredWindowFirst a0 aP aP2 aQ aC P Q =
          kQ + kPQ * P + 2 * kQ2 * Q + kP2Q * P^2 ∧
        filteredWindowSecond b0 bP bP2 bQ bPQ bC bPC P Q =
          -kP - 2 * kP2 * P - kPQ * Q -
            3 * kP3 * P^2 - 2 * kP2Q * P * Q := by
  have h00 := hdiv 0 0
  have h10 := hdiv 1 0
  have hm10 := hdiv (-1) 0
  have h01 := hdiv 0 1
  have h11 := hdiv 1 1
  simp [filteredWindowDivergence] at h00 h10 hm10 h01 h11
  have hbPC : bPC = 0 := by linarith
  have haC : aC = 0 := by linarith
  have hbC : bC = 0 := by linarith
  have hbQ : bQ = -aP := by linarith
  have hbPQ : bPQ = -2 * aP2 := by linarith
  refine ⟨haC, hbC, hbPC, ?_⟩
  refine ⟨-b0, a0, -bP / 2, aP, aQ / 2, -bP2 / 3, aP2, ?_⟩
  intro P Q
  constructor
  · simp [filteredWindowFirst, haC]
    ring
  · simp [filteredWindowSecond, hbC, hbPC, hbQ, hbPQ]
    ring

/-- Terminal aggregation of the arbitrary-degree filtered target chart. -/
theorem filtered_target_coordinate_certificate :
    (∀ g w : ℚ,
      filteredC (seedP g w) (seedQ g w) =
        g^2 * (3 * seedP g w + g - 1)) ∧
    (∀ P Q : ℚ,
      Q^2 =
        (filteredC P Q - 4 * P^3 + P^2) / 27 +
          ((18 * P - 4) / 27) * Q) ∧
    (∀ a b c a' b' c' : ℕ,
      b ≤ 1 → b' ≤ 1 →
      normalSignature a b c = normalSignature a' b' c' →
      a = a' ∧ b = b' ∧ c = c') ∧
    (∀ a b c : ℕ,
      b ≤ 1 → normalWeight a b c ≤ 8 →
      (b = 0 ∧ c = 0 ∧ a ≤ 2) ∨
      (b = 1 ∧ c = 0 ∧ a = 0) ∨
      (b = 0 ∧ c = 1 ∧ a = 0)) ∧
    (∀ a b c : ℕ,
      b ≤ 1 → normalWeight a b c ≤ 10 →
      (b = 0 ∧ c = 0 ∧ a ≤ 2) ∨
      (b = 1 ∧ c = 0 ∧ a ≤ 1) ∨
      (b = 0 ∧ c = 1 ∧ a ≤ 1)) ∧
    (∀ (a0 aP aP2 aQ aC : ℚ)
        (b0 bP bP2 bQ bPQ bC bPC : ℚ),
      (∀ P Q : ℚ,
        filteredWindowDivergence aP aP2 aC bQ bPQ bC bPC P Q = 0) →
      aC = 0 ∧ bC = 0 ∧ bPC = 0 ∧
      ∃ kP kQ kP2 kPQ kQ2 kP3 kP2Q : ℚ,
        ∀ P Q : ℚ,
          filteredWindowFirst a0 aP aP2 aQ aC P Q =
            kQ + kPQ * P + 2 * kQ2 * Q + kP2Q * P^2 ∧
          filteredWindowSecond b0 bP bP2 bQ bPQ bC bPC P Q =
            -kP - 2 * kP2 * P - kPQ * Q -
              3 * kP3 * P^2 - 2 * kP2Q * P * Q) := by
  exact ⟨filtered_coordinate_pullback,
    monic_quadratic_target_relation,
    fun _ _ _ _ _ _ hb hb' h =>
      normal_signature_injective _ _ _ _ _ _ hb hb' h,
    normal_terms_le_eight,
    normal_terms_le_ten,
    filtered_hamiltonian_window_decomposition⟩

end FilteredNormalMonomials

section ExactDualCertificate

/- A computable coefficient presentation of `ℚ[[v,t]]`. All expressions below
are polynomials of total degree at most ten; the unbounded function type lets
the kernel query coefficients without trusting a parser or a truncated
multiplication table. -/
structure CPoly where
  coeff : ℕ → ℕ → ℚ

abbrev CPair := CPoly × CPoly

def cTerm (value : ℚ) (vDegree tDegree : ℕ) : CPoly :=
  ⟨fun i j =>
    if i = vDegree ∧ j = tDegree then value else 0⟩

def cConst (value : ℚ) : CPoly :=
  cTerm value 0 0

def cV : CPoly :=
  cTerm 1 1 0

def cT : CPoly :=
  cTerm 1 0 1

def cAdd (left right : CPoly) : CPoly :=
  ⟨fun i j => left.coeff i j + right.coeff i j⟩

def cNeg (value : CPoly) : CPoly :=
  ⟨fun i j => -value.coeff i j⟩

def cMul (left right : CPoly) : CPoly :=
  ⟨fun i j =>
    ∑ iv ∈ Finset.range (i + 1),
      ∑ jt ∈ Finset.range (j + 1),
        left.coeff iv jt * right.coeff (i - iv) (j - jt)⟩

instance instZeroCPoly : Zero CPoly := ⟨cConst 0⟩
instance instOneCPoly : One CPoly := ⟨cConst 1⟩
instance instOfNatCPoly (n : ℕ) : OfNat CPoly n := ⟨cConst n⟩
instance instAddCPoly : Add CPoly := ⟨cAdd⟩
instance instNegCPoly : Neg CPoly := ⟨cNeg⟩
instance instSubCPoly : Sub CPoly := ⟨fun left right => cAdd left (cNeg right)⟩
instance instMulCPoly : Mul CPoly := ⟨cMul⟩

@[simp] theorem cPoly_add_coeff (left right : CPoly) (i j : ℕ) :
    (left + right).coeff i j = left.coeff i j + right.coeff i j := rfl

@[simp] theorem cConst_coeff (value : ℚ) (i j : ℕ) :
    (cConst value).coeff i j =
      if i = 0 ∧ j = 0 then value else 0 := rfl

@[simp] theorem cTerm_coeff
    (value : ℚ) (vDegree tDegree i j : ℕ) :
    (cTerm value vDegree tDegree).coeff i j =
      if i = vDegree ∧ j = tDegree then value else 0 := rfl

@[simp] theorem cV_coeff (i j : ℕ) :
    cV.coeff i j = if i = 1 ∧ j = 0 then 1 else 0 := rfl

@[simp] theorem cT_coeff (i j : ℕ) :
    cT.coeff i j = if i = 0 ∧ j = 1 then 1 else 0 := rfl

@[simp] theorem cPoly_neg_coeff (value : CPoly) (i j : ℕ) :
    (-value).coeff i j = -value.coeff i j := rfl

@[simp] theorem cPoly_sub_coeff (left right : CPoly) (i j : ℕ) :
    (left - right).coeff i j = left.coeff i j - right.coeff i j := by
  change left.coeff i j + -right.coeff i j =
    left.coeff i j - right.coeff i j
  rw [sub_eq_add_neg]

@[simp] theorem cPoly_mul_coeff (left right : CPoly) (i j : ℕ) :
    (left * right).coeff i j =
      ∑ iv ∈ Finset.range (i + 1),
        ∑ jt ∈ Finset.range (j + 1),
          left.coeff iv jt * right.coeff (i - iv) (j - jt) := rfl

@[simp] theorem cPoly_zero_coeff (i j : ℕ) :
    (0 : CPoly).coeff i j = 0 := by
  change (if i = 0 ∧ j = 0 then 0 else 0) = 0
  split <;> rfl

@[simp] theorem cPoly_ofNat_coeff (n i j : ℕ) :
    (OfNat.ofNat n : CPoly).coeff i j =
      if i = 0 ∧ j = 0 then (n : ℚ) else 0 := rfl

@[simp] theorem cPoly_one_coeff (i j : ℕ) :
    (1 : CPoly).coeff i j =
      if i = 0 ∧ j = 0 then 1 else 0 := rfl

@[simp] theorem cPoly_two_coeff (i j : ℕ) :
    (2 : CPoly).coeff i j =
      if i = 0 ∧ j = 0 then 2 else 0 := rfl

@[simp] theorem cPoly_three_coeff (i j : ℕ) :
    (3 : CPoly).coeff i j =
      if i = 0 ∧ j = 0 then 3 else 0 := rfl

def cPow (value : CPoly) : ℕ → CPoly
  | 0 => 1
  | n + 1 => cMul (cPow value n) value

instance instPowCPoly : Pow CPoly ℕ := ⟨cPow⟩

@[simp] theorem cPoly_pow_zero (value : CPoly) :
    value^0 = 1 := rfl

@[simp] theorem cPoly_pow_succ (value : CPoly) (n : ℕ) :
    value^(n + 1) = cMul (value^n) value := rfl

def qPoly (value : ℚ) : CPoly := cConst value

def seedPPoly : CPoly :=
  cTerm (1 / 2) 1 0 +
    cTerm (-3) 0 1 +
    cTerm (21 / 4) 2 0 +
    cTerm (-1) 1 1 +
    cTerm (-3) 0 2 +
    cTerm (-9 / 2) 3 0 +
    cTerm 12 2 1 +
    cTerm (-6) 1 2 +
    cTerm (-27 / 4) 4 0 +
    cTerm 9 3 1 +
    cTerm (-3) 2 2

def seedQPoly : CPoly :=
  cTerm (-2) 0 1 +
    cTerm 4 2 0 +
    cTerm (-4) 0 2 +
    cTerm (-5) 3 0 +
    cTerm (31 / 2) 2 1 +
    cTerm (-6) 1 2 +
    cTerm (-2) 0 3 +
    cTerm (-9) 4 0 +
    cTerm (9 / 2) 3 1 +
    cTerm 10 2 2 +
    cTerm (-6) 1 3 +
    cTerm (27 / 4) 5 0 +
    cTerm (-45 / 2) 4 1 +
    cTerm 21 3 2 +
    cTerm (-6) 2 3 +
    cTerm (27 / 4) 6 0 +
    cTerm (-27 / 2) 5 1 +
    cTerm 9 4 2 +
    cTerm (-2) 3 3

def jacPV : CPoly :=
  cTerm (-6) 1 2 +
    cTerm (-6) 0 2 +
    cTerm 27 2 1 +
    cTerm 24 1 1 +
    cTerm (-1) 0 1 +
    cTerm (-27) 3 0 +
    cTerm (-27 / 2) 2 0 +
    cTerm (21 / 2) 1 0 +
    cTerm (1 / 2) 0 0

def jacPT : CPoly :=
  cTerm (-6) 2 1 +
    cTerm (-12) 1 1 +
    cTerm (-6) 0 1 +
    cTerm 9 3 0 +
    cTerm 12 2 0 +
    cTerm (-1) 1 0 +
    cTerm (-3) 0 0

def jacQV : CPoly :=
  cTerm (-6) 2 3 +
    cTerm (-12) 1 3 +
    cTerm (-6) 0 3 +
    cTerm 36 3 2 +
    cTerm 63 2 2 +
    cTerm 20 1 2 +
    cTerm (-6) 0 2 +
    cTerm (-135 / 2) 4 1 +
    cTerm (-90) 3 1 +
    cTerm (27 / 2) 2 1 +
    cTerm 31 1 1 +
    cTerm (81 / 2) 5 0 +
    cTerm (135 / 4) 4 0 +
    cTerm (-36) 3 0 +
    cTerm (-15) 2 0 +
    cTerm 8 1 0

def jacQT : CPoly :=
  cTerm (-6) 3 2 +
    cTerm (-18) 2 2 +
    cTerm (-18) 1 2 +
    cTerm (-6) 0 2 +
    cTerm 18 4 1 +
    cTerm 42 3 1 +
    cTerm 20 2 1 +
    cTerm (-12) 1 1 +
    cTerm (-8) 0 1 +
    cTerm (-27 / 2) 5 0 +
    cTerm (-45 / 2) 4 0 +
    cTerm (9 / 2) 3 0 +
    cTerm (31 / 2) 2 0 +
    cTerm (-2) 0 0

def monomial (index : ℕ × ℕ) : CPoly :=
  cTerm 1 index.1 index.2

@[simp] theorem monomial_coeff (index : ℕ × ℕ) (i j : ℕ) :
    (monomial index).coeff i j =
      if i = index.1 ∧ j = index.2 then 1 else 0 := rfl

/-- Exact coefficient action of multiplication by the basis monomial
`v^index.1 * t^index.2`. -/
def shiftByMonomial (value : CPoly) (index : ℕ × ℕ) : CPoly :=
  ⟨fun i j =>
    if index.1 ≤ i ∧ index.2 ≤ j then
      value.coeff (i - index.1) (j - index.2)
    else 0⟩

@[simp] theorem shiftByMonomial_coeff
    (value : CPoly) (index : ℕ × ℕ) (i j : ℕ) :
    (shiftByMonomial value index).coeff i j =
      if index.1 ≤ i ∧ index.2 ≤ j then
        value.coeff (i - index.1) (j - index.2)
      else 0 := rfl

def sourceUColumn (index : ℕ × ℕ) : CPair :=
  (shiftByMonomial jacPV index, shiftByMonomial jacQV index)

def sourceVColumn (index : ℕ × ℕ) : CPair :=
  (shiftByMonomial jacPT index, shiftByMonomial jacQT index)

def sourceUIndices : List (ℕ × ℕ) :=
  [(0, 1), (1, 0), (0, 2), (1, 1), (2, 0),
    (0, 3), (1, 2), (2, 1), (3, 0),
    (0, 4), (1, 3), (2, 2), (3, 1), (4, 0)]

def sourceVIndices : List (ℕ × ℕ) :=
  [(0, 1), (0, 2), (1, 1), (2, 0),
    (0, 3), (1, 2), (2, 1), (3, 0),
    (0, 4), (1, 3), (2, 2), (3, 1), (4, 0)]

def sourceColumns : List CPair :=
  sourceUIndices.map sourceUColumn ++ sourceVIndices.map sourceVColumn

/-- Hamiltonian fields for
`P,Q,P²,PQ,Q²,P³,P²Q`, evaluated at the seed. -/
def targetColumns : List CPair :=
  [(0, -1),
    (1, 0),
    (0, -2 * seedPPoly),
    (seedPPoly, -seedQPoly),
    (2 * seedQPoly, 0),
    (0, -3 * seedPPoly^2),
    (seedPPoly^2, -2 * seedPPoly * seedQPoly)]

def coeffVT (f : CPoly) (vDegree tDegree : ℕ) : ℚ :=
  f.coeff vDegree tDegree

/-- Primitive eight-coordinate functional extracted from the exact rational
left kernel. -/
def dualPair (pair : CPair) : ℚ :=
  -18 * coeffVT pair.1 0 4 +
    3 * coeffVT pair.1 0 5 -
    2 * coeffVT pair.1 0 6 +
    42 * coeffVT pair.1 4 4 -
    18 * coeffVT pair.2 0 1 +
    18 * coeffVT pair.2 0 2 -
    18 * coeffVT pair.2 0 3 +
    18 * coeffVT pair.2 0 4

def residualPPoly : CPoly :=
  cTerm (-1 / 6) 0 1 +
    cTerm (15 / 32) 2 0 +
    cTerm (-3 / 8) 1 1 +
    cTerm (-1 / 8) 0 2 +
    cTerm (-11 / 96) 3 0 +
    cTerm (21 / 16) 2 1 +
    cTerm (-11 / 8) 1 2 +
    cTerm (5 / 12) 0 3 +
    cTerm (-201 / 128) 4 0 +
    cTerm (59 / 16) 3 1 +
    cTerm (-45 / 16) 2 2 +
    cTerm (1 / 4) 1 3 +
    cTerm (3 / 8) 0 4 +
    cTerm (-9 / 8) 5 0 +
    cTerm (27 / 16) 4 1 +
    cTerm (13 / 8) 3 2 +
    cTerm (-15 / 4) 2 3 +
    cTerm (3 / 2) 1 4 +
    cTerm (45 / 64) 6 0 +
    cTerm (-45 / 8) 5 1 +
    cTerm (93 / 8) 4 2 +
    cTerm (-53 / 6) 3 3 +
    cTerm (9 / 4) 2 4 +
    cTerm (81 / 32) 7 0 +
    cTerm (-81 / 8) 6 1 +
    cTerm (27 / 2) 5 2 +
    cTerm (-15 / 2) 4 3 +
    cTerm (3 / 2) 3 4 +
    cTerm (243 / 128) 8 0 +
    cTerm (-81 / 16) 7 1 +
    cTerm (81 / 16) 6 2 +
    cTerm (-9 / 4) 5 3 +
    cTerm (3 / 8) 4 4

def residualQPoly : CPoly :=
  cTerm (13 / 96) 2 0 +
    cTerm (-13 / 24) 1 1 +
    cTerm (7 / 8) 0 2 +
    cTerm (19 / 32) 3 0 +
    cTerm (-107 / 48) 2 1 +
    cTerm (-25 / 24) 1 2 +
    cTerm (9 / 4) 0 3 +
    cTerm (301 / 384) 4 0 +
    cTerm (51 / 8) 3 1 +
    cTerm (-613 / 48) 2 2 +
    cTerm (19 / 6) 1 3 +
    cTerm (15 / 8) 0 4 +
    cTerm (-49 / 8) 5 0 +
    cTerm (1621 / 96) 4 1 +
    cTerm (-23 / 8) 3 2 +
    cTerm (-14) 2 3 +
    cTerm (37 / 6) 1 4 +
    cTerm (1 / 2) 0 5 +
    cTerm (-141 / 64) 6 0 +
    cTerm (-481 / 32) 5 1 +
    cTerm (173 / 4) 4 2 +
    cTerm (-61 / 2) 3 3 +
    cTerm (9 / 4) 2 4 +
    cTerm (5 / 2) 1 5 +
    cTerm (711 / 64) 7 0 +
    cTerm (-627 / 16) 6 1 +
    cTerm (295 / 8) 5 2 +
    cTerm (7 / 6) 4 3 +
    cTerm (-61 / 4) 3 4 +
    cTerm 5 2 5 +
    cTerm (621 / 128) 8 0 +
    cTerm (9 / 8) 7 1 +
    cTerm (-513 / 16) 6 2 +
    cTerm (187 / 4) 5 3 +
    cTerm (-617 / 24) 4 4 +
    cTerm 5 3 5 +
    cTerm (-405 / 64) 9 0 +
    cTerm (945 / 32) 8 1 +
    cTerm (-405 / 8) 7 2 +
    cTerm (165 / 4) 6 3 +
    cTerm (-65 / 4) 5 4 +
    cTerm (5 / 2) 4 5 +
    cTerm (-243 / 64) 10 0 +
    cTerm (405 / 32) 9 1 +
    cTerm (-135 / 8) 8 2 +
    cTerm (45 / 4) 7 3 +
    cTerm (-15 / 4) 6 4 +
    cTerm (1 / 2) 5 5

def residualPair : CPair := (residualPPoly, residualQPoly)

theorem dual_annihilates_source_basis :
    sourceColumns.map dualPair = List.replicate 27 0 := by
  norm_num [sourceColumns, sourceUIndices, sourceVIndices,
    sourceUColumn, sourceVColumn, shiftByMonomial, dualPair, coeffVT,
    jacPV, jacPT, jacQV, jacQT, List.replicate_succ]

set_option maxHeartbeats 5000000 in
theorem dual_annihilates_target_basis :
    targetColumns.map dualPair = List.replicate 7 0 := by
  norm_num [targetColumns, dualPair, coeffVT, seedPPoly, seedQPoly,
    cMul, cPow, qPoly, cConst, cV, cT, cAdd, cNeg,
    Finset.sum_range_succ, List.replicate_succ]

set_option maxHeartbeats 5000000 in
theorem dual_detects_residual : dualPair residualPair = 18 := by
  norm_num [dualPair, residualPair, residualPPoly, residualQPoly,
    coeffVT]

def addCPair (left right : CPair) : CPair :=
  (left.1 + right.1, left.2 + right.2)

def scaleCPoly (scalar : ℚ) (value : CPoly) : CPoly :=
  ⟨fun i j => scalar * value.coeff i j⟩

def scaleCPair (scalar : ℚ) (value : CPair) : CPair :=
  (scaleCPoly scalar value.1, scaleCPoly scalar value.2)

def combine : List (ℚ × CPair) → CPair
  | [] => (0, 0)
  | (scalar, value) :: rest =>
      addCPair (scaleCPair scalar value) (combine rest)

theorem dual_add (left right : CPair) :
    dualPair (addCPair left right) = dualPair left + dualPair right := by
  simp [dualPair, addCPair, coeffVT]
  ring

theorem dual_scale (scalar : ℚ) (value : CPair) :
    dualPair (scaleCPair scalar value) = scalar * dualPair value := by
  simp [dualPair, scaleCPair, scaleCPoly, coeffVT]
  ring

theorem dual_source_column
    (column : CPair) (hcolumn : column ∈ sourceColumns) :
    dualPair column = 0 := by
  have hmapped : dualPair column ∈ sourceColumns.map dualPair :=
    List.mem_map.mpr ⟨column, hcolumn, rfl⟩
  rw [dual_annihilates_source_basis] at hmapped
  simpa using hmapped

theorem dual_target_column
    (column : CPair) (hcolumn : column ∈ targetColumns) :
    dualPair column = 0 := by
  have hmapped : dualPair column ∈ targetColumns.map dualPair :=
    List.mem_map.mpr ⟨column, hcolumn, rfl⟩
  rw [dual_annihilates_target_basis] at hmapped
  simpa using hmapped

theorem dual_combine_zero
    (terms : List (ℚ × CPair))
    (hterms : ∀ term ∈ terms,
      term.2 ∈ sourceColumns ∨ term.2 ∈ targetColumns) :
    dualPair (combine terms) = 0 := by
  induction terms with
  | nil =>
      simp [combine, dualPair, coeffVT]
  | cons term rest ih =>
      rw [combine, dual_add, dual_scale]
      have hhead := hterms term (by simp)
      have hheadzero : dualPair term.2 = 0 := by
        rcases hhead with hsource | htarget
        · exact dual_source_column term.2 hsource
        · exact dual_target_column term.2 htarget
      rw [hheadzero, mul_zero, zero_add]
      apply ih
      intro other hother
      exact hterms other (by simp [hother])

def generatedBySourceAndTarget (value : CPair) : Prop :=
  ∃ terms : List (ℚ × CPair),
    (∀ term ∈ terms,
      term.2 ∈ sourceColumns ∨ term.2 ∈ targetColumns) ∧
    combine terms = value

/-- Exact lower bound: the residual is outside the span of every admissible
degree-four source generator and every arbitrary-degree target direction
surviving the filtered normal form. -/
theorem residual_not_generated :
    ¬ generatedBySourceAndTarget residualPair := by
  rintro ⟨terms, hterms, heq⟩
  have hzero := dual_combine_zero terms hterms
  rw [heq, dual_detects_residual] at hzero
  norm_num at hzero

def sourceWitnessU : CPoly :=
  cTerm (-5 / 28) 3 2 +
    cTerm (-15 / 28) 2 2 +
    cTerm (-15 / 28) 1 2 +
    cTerm (-5 / 28) 0 2 +
    cTerm (197 / 280) 4 1 +
    cTerm (269 / 140) 3 1 +
    cTerm (477 / 280) 2 1 +
    cTerm (13 / 30) 1 1 +
    cTerm (-11 / 210) 0 1 +
    cTerm (-183 / 280) 5 0 +
    cTerm (-169 / 112) 4 0 +
    cTerm (-767 / 840) 3 0 +
    cTerm (37 / 280) 2 0 +
    cTerm (179 / 1680) 1 0

def sourceWitnessV : CPoly :=
  cTerm (3 / 28) 2 3 +
    cTerm (3 / 14) 1 3 +
    cTerm (3 / 28) 0 3 +
    cTerm (-257 / 280) 3 2 +
    cTerm (-39 / 20) 2 2 +
    cTerm (-687 / 560) 1 2 +
    cTerm (-317 / 1680) 0 2 +
    cTerm (639 / 280) 4 1 +
    cTerm (1271 / 280) 3 1 +
    cTerm (4153 / 1680) 2 1 +
    cTerm (31 / 560) 1 1 +
    cTerm (-179 / 1680) 0 1 +
    cTerm (-963 / 560) 5 0 +
    cTerm (-81 / 28) 4 0 +
    cTerm (-263 / 320) 3 0 +
    cTerm (3841 / 6720) 2 0

theorem degree_five_witness_top_coefficients :
    sourceWitnessU.coeff 5 0 = -183 / 280 ∧
    sourceWitnessV.coeff 5 0 = -963 / 560 := by
  norm_num [sourceWitnessU, sourceWitnessV]

theorem degree_five_witness_lift_ideals :
    sourceWitnessU.coeff 0 0 = 0 ∧
    sourceWitnessV.coeff 0 0 = 0 ∧
    sourceWitnessV.coeff 1 0 = 0 := by
  norm_num [sourceWitnessU, sourceWitnessV]

def gammaValue (v t : ℚ) : ℚ := 1 - (3 / 2) * v + t
def wValue (v t : ℚ) : ℚ := (1 + v) * gammaValue v t
def seedPValue (v t : ℚ) : ℚ :=
  seedP (gammaValue v t) (wValue v t)
def seedQValue (v t : ℚ) : ℚ :=
  seedQ (gammaValue v t) (wValue v t)

def jacPVValue (v t : ℚ) : ℚ :=
  -6 * t^2 * v - 6 * t^2 + 27 * t * v^2 + 24 * t * v - t -
    27 * v^3 - (27 / 2) * v^2 + (21 / 2) * v + 1 / 2

def jacPTValue (v t : ℚ) : ℚ :=
  -6 * t * v^2 - 12 * t * v - 6 * t +
    9 * v^3 + 12 * v^2 - v - 3

def jacQVValue (v t : ℚ) : ℚ :=
  -6 * t^3 * v^2 - 12 * t^3 * v - 6 * t^3 +
    36 * t^2 * v^3 + 63 * t^2 * v^2 + 20 * t^2 * v - 6 * t^2 -
    (135 / 2) * t * v^4 - 90 * t * v^3 + (27 / 2) * t * v^2 +
    31 * t * v + (81 / 2) * v^5 + (135 / 4) * v^4 -
    36 * v^3 - 15 * v^2 + 8 * v

def jacQTValue (v t : ℚ) : ℚ :=
  -6 * t^2 * v^3 - 18 * t^2 * v^2 - 18 * t^2 * v - 6 * t^2 +
    18 * t * v^4 + 42 * t * v^3 + 20 * t * v^2 -
    12 * t * v - 8 * t - (27 / 2) * v^5 - (45 / 2) * v^4 +
    (9 / 2) * v^3 + (31 / 2) * v^2 - 2

def sourceWitnessUValue (v t : ℚ) : ℚ :=
  (-5 / 28) * t^2 * v^3 - (15 / 28) * t^2 * v^2 -
    (15 / 28) * t^2 * v - (5 / 28) * t^2 +
    (197 / 280) * t * v^4 + (269 / 140) * t * v^3 +
    (477 / 280) * t * v^2 + (13 / 30) * t * v -
    (11 / 210) * t - (183 / 280) * v^5 -
    (169 / 112) * v^4 - (767 / 840) * v^3 +
    (37 / 280) * v^2 + (179 / 1680) * v

def sourceWitnessVValue (v t : ℚ) : ℚ :=
  (3 / 28) * t^3 * v^2 + (3 / 14) * t^3 * v + (3 / 28) * t^3 -
    (257 / 280) * t^2 * v^3 - (39 / 20) * t^2 * v^2 -
    (687 / 560) * t^2 * v - (317 / 1680) * t^2 +
    (639 / 280) * t * v^4 + (1271 / 280) * t * v^3 +
    (4153 / 1680) * t * v^2 + (31 / 560) * t * v -
    (179 / 1680) * t - (963 / 560) * v^5 -
    (81 / 28) * v^4 - (263 / 320) * v^3 + (3841 / 6720) * v^2

def targetWitnessPValue (v t : ℚ) : ℚ :=
  -(seedPValue v t)^2 / 168 -
    179 * seedPValue v t / 1680 +
    131 * seedQValue v t / 336

def targetWitnessQValue (v t : ℚ) : ℚ :=
  seedPValue v t * seedQValue v t / 84 +
    179 * seedQValue v t / 1680

def residualPValue (v t : ℚ) : ℚ :=
  let g := gammaValue v t
  let w := wValue v t
  (6 * g * w^2 - 6 * g * w + 2 * g + 9 * w^4 -
    32 * w^3 + 27 * w^2 - 6 * w) / 24

def residualQValue (v t : ℚ) : ℚ :=
  let g := gammaValue v t
  let w := wValue v t
  (2 * g^2 + 2 * g * w^3 - 12 * g * w^2 + 6 * g * w +
    12 * w^5 - 17 * w^4 + 6 * w^3 + w^2) / 24

/-- The explicit degree-five source and cubic Hamiltonian target correction
solve the second-jet equation as polynomial functions. -/
theorem degree_five_witness_equation (v t : ℚ) :
    jacPVValue v t * sourceWitnessUValue v t +
        jacPTValue v t * sourceWitnessVValue v t +
        targetWitnessPValue v t = residualPValue v t ∧
    jacQVValue v t * sourceWitnessUValue v t +
        jacQTValue v t * sourceWitnessVValue v t +
        targetWitnessQValue v t = residualQValue v t := by
  constructor <;>
    simp [jacPVValue, jacPTValue, jacQVValue, jacQTValue,
      sourceWitnessUValue, sourceWitnessVValue, targetWitnessPValue,
      targetWitnessQValue, residualPValue, residualQValue, seedPValue,
      seedQValue, seedP, seedQ, gammaValue, wValue] <;>
    ring

def targetDivergenceP (P : ℚ) : ℚ := -P / 84 - 179 / 1680
def targetDivergenceQ (P : ℚ) : ℚ := P / 84 + 179 / 1680

theorem degree_five_target_is_divergence_free (P : ℚ) :
    targetDivergenceP P + targetDivergenceQ P = 0 := by
  simp [targetDivergenceP, targetDivergenceQ]
  ring

/-- Terminal two-sided certificate: the arbitrary polynomial target window
has seven normal generators, the dual separates the residual from every
degree-four source/target generator, and an admissible degree-five witness
solves the same residual. -/
theorem gauge_minimal_second_jet_certificate :
    (¬ generatedBySourceAndTarget residualPair) ∧
    (∀ v t : ℚ,
      jacPVValue v t * sourceWitnessUValue v t +
          jacPTValue v t * sourceWitnessVValue v t +
          targetWitnessPValue v t = residualPValue v t ∧
      jacQVValue v t * sourceWitnessUValue v t +
          jacQTValue v t * sourceWitnessVValue v t +
          targetWitnessQValue v t = residualQValue v t) ∧
    sourceWitnessU.coeff 0 0 = 0 ∧
    sourceWitnessV.coeff 0 0 = 0 ∧
    sourceWitnessV.coeff 1 0 = 0 ∧
    sourceWitnessU.coeff 5 0 = -183 / 280 ∧
    sourceWitnessV.coeff 5 0 = -963 / 560 ∧
    (∀ P : ℚ, targetDivergenceP P + targetDivergenceQ P = 0) := by
  exact ⟨residual_not_generated,
    degree_five_witness_equation,
    degree_five_witness_lift_ideals.1,
    degree_five_witness_lift_ideals.2.1,
    degree_five_witness_lift_ideals.2.2,
    degree_five_witness_top_coefficients.1,
    degree_five_witness_top_coefficients.2,
    degree_five_target_is_divergence_free⟩

/-- One carried proposition joining the filtered-coordinate reduction, the
noncancellation data, the seven-generator Hamiltonian window, the exact
degree-four obstruction, and the admissible degree-five witness. -/
theorem complete_gauge_minimal_second_jet_certificate :
    (∀ P Q : ℚ,
      Q^2 =
        (filteredC P Q - 4 * P^3 + P^2) / 27 +
          ((18 * P - 4) / 27) * Q) ∧
    (∀ a b c a' b' c' : ℕ,
      b ≤ 1 → b' ≤ 1 →
      normalSignature a b c = normalSignature a' b' c' →
      a = a' ∧ b = b' ∧ c = c') ∧
    (∀ a b c : ℕ, normalLeadingCoefficient a b c ≠ 0) ∧
    (∀ (a0 aP aP2 aQ aC : ℚ)
        (b0 bP bP2 bQ bPQ bC bPC : ℚ),
      (∀ P Q : ℚ,
        filteredWindowDivergence aP aP2 aC bQ bPQ bC bPC P Q = 0) →
      aC = 0 ∧ bC = 0 ∧ bPC = 0 ∧
      ∃ kP kQ kP2 kPQ kQ2 kP3 kP2Q : ℚ,
        ∀ P Q : ℚ,
          filteredWindowFirst a0 aP aP2 aQ aC P Q =
            kQ + kPQ * P + 2 * kQ2 * Q + kP2Q * P^2 ∧
          filteredWindowSecond b0 bP bP2 bQ bPQ bC bPC P Q =
            -kP - 2 * kP2 * P - kPQ * Q -
              3 * kP3 * P^2 - 2 * kP2Q * P * Q) ∧
    (¬ generatedBySourceAndTarget residualPair) ∧
    (∀ v t : ℚ,
      jacPVValue v t * sourceWitnessUValue v t +
          jacPTValue v t * sourceWitnessVValue v t +
          targetWitnessPValue v t = residualPValue v t ∧
      jacQVValue v t * sourceWitnessUValue v t +
          jacQTValue v t * sourceWitnessVValue v t +
          targetWitnessQValue v t = residualQValue v t) ∧
    sourceWitnessU.coeff 0 0 = 0 ∧
    sourceWitnessV.coeff 0 0 = 0 ∧
    sourceWitnessV.coeff 1 0 = 0 ∧
    sourceWitnessU.coeff 5 0 = -183 / 280 ∧
    sourceWitnessV.coeff 5 0 = -963 / 560 ∧
    (∀ P : ℚ, targetDivergenceP P + targetDivergenceQ P = 0) := by
  exact ⟨monic_quadratic_target_relation,
    fun _ _ _ _ _ _ hb hb' h =>
      normal_signature_injective _ _ _ _ _ _ hb hb' h,
    normal_leading_coefficient_ne_zero,
    filtered_hamiltonian_window_decomposition,
    residual_not_generated,
    degree_five_witness_equation,
    degree_five_witness_lift_ideals.1,
    degree_five_witness_lift_ideals.2.1,
    degree_five_witness_lift_ideals.2.2,
    degree_five_witness_top_coefficients.1,
    degree_five_witness_top_coefficients.2,
    degree_five_target_is_divergence_free⟩

end ExactDualCertificate

end AxiomPackJacobianGaugeMinimum
