import Mathlib

set_option maxHeartbeats 1000000

-- ROW ADV01
theorem adv01 (n : ℕ) : ∃ p, n < p ∧ Nat.Prime p := by
  obtain ⟨p, hp_ge, hp_prime⟩ := Nat.exists_infinite_primes (n + 1)
  exact ⟨p, lt_of_lt_of_le (Nat.lt_succ_self n) hp_ge, hp_prime⟩

-- ROW ADV02
theorem adv02 (a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) : 2 * (a * b) ≤ a ^ 2 + b ^ 2 := by
  have h : 0 ≤ (a - b) ^ 2 := sq_nonneg _
  have hexp : (a - b) ^ 2 = a ^ 2 + b ^ 2 - 2 * (a * b) := by ring
  linarith [hexp ▸ h]

-- ROW ADV03
theorem adv03 (n : ℕ) : (2 : ℕ) * (Finset.range (n + 1)).sum id = n * (n + 1) := by
  induction n with
  | zero => simp
  | succ k ih =>
      rw [Finset.sum_range_succ, Nat.mul_add, ih]
      simp only [id]
      ring

-- ROW ADV04
theorem adv04 (n : ℤ) : (2 : ℤ) ∣ (n ^ 2 - n) := by
  have h : n ^ 2 - n = n * (n - 1) := by ring
  rw [h]
  rcases Int.even_or_odd n with he | ho
  · obtain ⟨k, hk⟩ := he
    exact ⟨k * (n - 1), by rw [hk]; ring⟩
  · obtain ⟨k, hk⟩ := ho
    refine ⟨n * k, ?_⟩
    rw [hk]; ring

-- ROW ADV05
theorem adv05 (x y : ℝ) : |x| - |y| ≤ |x - y| := by
  have h : |(x - y) + y| ≤ |x - y| + |y| := abs_add_le (x - y) y
  have he : (x - y) + y = x := by ring
  rw [he] at h
  linarith

-- ROW ADV06
theorem adv06 (x : ℝ) (n : ℕ) :
    (1 - x) * (Finset.range n).sum (fun i => x ^ i) = 1 - x ^ n := by
  induction n with
  | zero => simp
  | succ k ih =>
      rw [Finset.sum_range_succ, mul_add, ih]
      ring

-- ROW ADV07
theorem adv07 : ¬ ∃ q : ℚ, q ^ 2 = 2 := by
  rintro ⟨q, hq⟩
  have hirr : Irrational (Real.sqrt 2) := irrational_sqrt_two
  have hpos : (0:ℝ) ≤ 2 := by norm_num
  have : ((|q| : ℚ) : ℝ) = Real.sqrt 2 := by
    have hqr : ((q : ℝ)) ^ 2 = 2 := by
      have := congrArg (fun t : ℚ => (t : ℝ)) hq
      push_cast at this
      linarith [this]
    rw [Rat.cast_abs]
    rw [← Real.sqrt_sq_eq_abs]
    rw [hqr]
  exact hirr ⟨|q|, this⟩

-- ROW ADV08
theorem adv08 (n : ℕ) (f : Fin (n + 1) → Fin n) : ∃ i j, i ≠ j ∧ f i = f j := by
  have hcard : Fintype.card (Fin n) < Fintype.card (Fin (n + 1)) := by
    simp
  obtain ⟨i, j, hij, hfij⟩ := Fintype.exists_ne_map_eq_of_card_lt f hcard
  exact ⟨i, j, hij, hfij⟩

-- ROW ADV09
theorem adv09 (x : ℝ) (hx : -1 ≤ x) (n : ℕ) : 1 + (n : ℝ) * x ≤ (1 + x) ^ n := by
  have hpos : (0:ℝ) ≤ 1 + x := by linarith
  induction n with
  | zero => simp
  | succ k ih =>
      have hstep : (1 + x) ^ (k + 1) = (1 + x) ^ k * (1 + x) := by ring
      have hquad : (1 + (k : ℝ) * x) * (1 + x)
          = 1 + ((k : ℝ) + 1) * x + (k : ℝ) * x ^ 2 := by ring
      have hsq : 0 ≤ (k : ℝ) * x ^ 2 := by positivity
      have hcast : ((k : ℕ) + 1 : ℝ) = ((k + 1 : ℕ) : ℝ) := by push_cast; ring
      rw [← hcast] at *
      calc 1 + ((k : ℝ) + 1) * x
          ≤ 1 + ((k : ℝ) + 1) * x + (k : ℝ) * x ^ 2 := by linarith
        _ = (1 + (k : ℝ) * x) * (1 + x) := by rw [hquad]
        _ ≤ (1 + x) ^ k * (1 + x) := by
              apply mul_le_mul_of_nonneg_right ih hpos
        _ = (1 + x) ^ (k + 1) := by rw [hstep]


-- ROW ADV10
theorem adv10 (p : ℕ) (hp : Nat.Prime p) (hmod : p % 4 = 1) :
    ∃ a b : ℕ, a ^ 2 + b ^ 2 = p := by
  haveI : Fact p.Prime := ⟨hp⟩
  have hne : p % 4 ≠ 3 := by omega
  exact Nat.Prime.sq_add_sq hne

-- ROW ADV11
theorem adv11 (n k : ℕ) (hk : 0 < k) (hn : 2 * k ≤ n)
    (𝒜 : Finset (Finset (Fin n)))
    (hsize : ∀ A ∈ 𝒜, A.card = k)
    (hint : ∀ A ∈ 𝒜, ∀ B ∈ 𝒜, (A ∩ B).Nonempty) :
    𝒜.card ≤ Nat.choose (n - 1) (k - 1) := by
  -- Translate the "intersecting" hypothesis into Mathlib's `Set.Intersecting`
  -- (every pair is non-disjoint).
  have hInt : (𝒜 : Set (Finset (Fin n))).Intersecting := by
    intro A hA B hB hdisj
    have hAmem : A ∈ 𝒜 := by simpa using hA
    have hBmem : B ∈ 𝒜 := by simpa using hB
    obtain ⟨x, hx⟩ := hint A hAmem B hBmem
    rw [Finset.mem_inter] at hx
    exact (Finset.disjoint_left.mp hdisj hx.1) hx.2
  -- Translate the card hypothesis into `Set.Sized`.
  have hSized : (𝒜 : Set (Finset (Fin n))).Sized k := by
    intro A hA
    have hAmem : A ∈ 𝒜 := by simpa using hA
    exact hsize A hAmem
  -- Arithmetic: 2*k ≤ n implies k ≤ n / 2.
  have hkn : k ≤ n / 2 := by
    rw [Nat.le_div_iff_mul_le (by norm_num)]
    omega
  exact Finset.erdos_ko_rado hInt hSized hkn

-- ROW ADV12
theorem adv12 (s : Finset ℕ) (f g : ℕ → ℝ) :
    (s.sum (fun i => f i * g i)) ^ 2
      ≤ (s.sum (fun i => f i ^ 2)) * (s.sum (fun i => g i ^ 2)) := by
  set A : ℝ := s.sum (fun i => f i ^ 2) with hA
  set B : ℝ := s.sum (fun i => f i * g i) with hB
  set C : ℝ := s.sum (fun i => g i ^ 2) with hC
  -- Nonnegativity of the quadratic form Σ (g i * x - f i)^2 = C x^2 - 2 B x + A.
  have hAnonneg : 0 ≤ A := by
    rw [hA]; apply Finset.sum_nonneg; intro i _; positivity
  have hCnonneg : 0 ≤ C := by
    rw [hC]; apply Finset.sum_nonneg; intro i _; positivity
  have hquad : ∀ x : ℝ, 0 ≤ C * x ^ 2 - 2 * B * x + A := by
    intro x
    have hsum : C * x ^ 2 - 2 * B * x + A
        = s.sum (fun i => (g i * x - f i) ^ 2) := by
      have hexpand : s.sum (fun i => (g i * x - f i) ^ 2)
          = s.sum (fun i => g i ^ 2 * x ^ 2 - 2 * (f i * g i) * x + f i ^ 2) := by
        apply Finset.sum_congr rfl; intro i _; ring
      rw [hexpand, Finset.sum_add_distrib, Finset.sum_sub_distrib,
        ← Finset.sum_mul, ← Finset.sum_mul, ← Finset.mul_sum, hA, hB, hC]
    rw [hsum]
    apply Finset.sum_nonneg
    intro i _
    positivity
  -- Nonnegativity gives B^2 ≤ A * C, the squared Cauchy–Schwarz inequality.
  rcases eq_or_lt_of_le hCnonneg with hC0 | hCpos
  · -- C = 0 forces B = 0.
    have hAnn : 0 ≤ A := by
      rw [hA]; apply Finset.sum_nonneg; intro i _; positivity
    have hBzero : B = 0 := by
      by_contra hBne
      have hlin : ∀ x : ℝ, 0 ≤ -2 * B * x + A := by
        intro x; have := hquad x; rw [← hC0] at this; linarith [this]
      have hwit := hlin ((A + 1) / (2 * B))
      have h2B : (2 : ℝ) * B ≠ 0 := by
        intro h; apply hBne; linarith [mul_eq_zero.mp h]
      have hsimp : -2 * B * ((A + 1) / (2 * B)) + A = -1 := by
        field_simp
        ring
      rw [hsimp] at hwit
      linarith
    rw [hBzero, ← hC0]; ring_nf; positivity
  · -- C > 0: evaluate quadratic at its vertex x = B / C.
    have hvertex := hquad (B / C)
    have hCne : C ≠ 0 := ne_of_gt hCpos
    have hkey : 0 ≤ A - B ^ 2 / C := by
      have hexp : C * (B / C) ^ 2 - 2 * B * (B / C) + A
          = A - B ^ 2 / C := by
        field_simp
        ring
      rw [hexp] at hvertex
      exact hvertex
    have : B ^ 2 / C ≤ A := by linarith
    have hmul : B ^ 2 ≤ A * C := by
      rw [div_le_iff₀ hCpos] at this
      linarith
    rw [hB] at hmul ⊢
    linarith [hmul]
