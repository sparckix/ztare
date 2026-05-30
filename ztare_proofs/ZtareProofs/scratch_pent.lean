import Mathlib

set_option maxHeartbeats 1000000

-- Helper-free: divisibility witness for k*(3k-1).
-- even k=2m: k*(3k-1) = 2*(m*(3k-1))
-- odd  k=2m+1: k*(3k-1) = (2m+1)*(6m+2) = 2*((2m+1)*(3m+1))

-- ROW 1
example : ((0:ℤ)*(3*0-1)/2).toNat = 0 := by decide

-- ROW 2
example : ((1:ℤ)*(3*1-1)/2).toNat = 1 := by decide

-- ROW 3
example : ∀ k : ℤ, (2:ℤ) ∣ k*(3*k-1) := by
  intro k
  rcases Int.even_or_odd k with ⟨m, hm⟩ | ⟨m, hm⟩
  · exact ⟨m*(3*k-1), by rw [hm]; ring⟩
  · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩

-- ROW 4
example : ∀ k : ℤ, 0 ≤ k*(3*k-1) := by
  intro k
  rcases lt_or_ge k 1 with h | h
  · have hk : k ≤ 0 := by omega
    nlinarith [hk, sq_nonneg k]
  · have h0 : 0 ≤ k := by linarith
    have : 0 ≤ 3*k-1 := by linarith
    positivity

-- ROW 5
example : StrictMono (fun n : ℕ => (((n:ℤ))*(3*((n:ℤ))-1)/2).toNat) := by
  intro a b hab
  have hab' : (a:ℤ) < (b:ℤ) := by exact_mod_cast hab
  have hann : (0:ℤ) ≤ (a:ℤ) := Int.ofNat_nonneg a
  have hbnn0 : (0:ℤ) ≤ (b:ℤ) := Int.ofNat_nonneg b
  simp only
  have ea : (2:ℤ) ∣ (a:ℤ)*(3*(a:ℤ)-1) := by
    rcases Int.even_or_odd (a:ℤ) with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*(a:ℤ)-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  have eb : (2:ℤ) ∣ (b:ℤ)*(3*(b:ℤ)-1) := by
    rcases Int.even_or_odd (b:ℤ) with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*(b:ℤ)-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  obtain ⟨qa, hqa⟩ := ea
  obtain ⟨qb, hqb⟩ := eb
  have key : ((a:ℤ))*(3*((a:ℤ))-1)/2 < ((b:ℤ))*(3*((b:ℤ))-1)/2 := by
    rw [hqa, hqb, Int.mul_ediv_cancel_left _ (by norm_num), Int.mul_ediv_cancel_left _ (by norm_num)]
    nlinarith [hab', hann, hbnn0, hqa, hqb]
  have hbnn : 0 ≤ ((b:ℤ))*(3*((b:ℤ))-1)/2 := by
    have hb2 : 0 ≤ ((b:ℤ))*(3*((b:ℤ))-1) := by
      rcases lt_or_ge (b:ℤ) 1 with h | h
      · have hk : (b:ℤ) ≤ 0 := by omega
        nlinarith [sq_nonneg (b:ℤ)]
      · have : 0 ≤ 3*(b:ℤ)-1 := by linarith
        positivity
    exact Int.ediv_nonneg hb2 (by norm_num)
  omega

-- ROW 6
example : ∀ k : ℤ, 1 ≤ k → 1 ≤ (k*(3*k-1)/2).toNat := by
  intro k hk
  have ev : (2:ℤ) ∣ k*(3*k-1) := by
    rcases Int.even_or_odd k with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*k-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  obtain ⟨q, hq⟩ := ev
  rw [hq, Int.mul_ediv_cancel_left _ (by norm_num)]
  have hqpos : 1 ≤ q := by nlinarith [hk, hq]
  omega

-- ROW 7
example : StrictMonoOn (fun k : ℤ => (k * (3 * k - 1) / 2).toNat) (Set.Ici (1:ℤ)) := by
  intro a ha b hb hab
  simp only [Set.mem_Ici] at ha hb
  simp only
  have ea : (2:ℤ) ∣ a*(3*a-1) := by
    rcases Int.even_or_odd a with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*a-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  have eb : (2:ℤ) ∣ b*(3*b-1) := by
    rcases Int.even_or_odd b with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*b-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  obtain ⟨qa, hqa⟩ := ea
  obtain ⟨qb, hqb⟩ := eb
  have key : a*(3*a-1)/2 < b*(3*b-1)/2 := by
    rw [hqa, hqb, Int.mul_ediv_cancel_left _ (by norm_num), Int.mul_ediv_cancel_left _ (by norm_num)]
    nlinarith [hab, ha, hb, hqa, hqb]
  have hbnn : 0 ≤ b*(3*b-1)/2 := by
    have : 0 ≤ b*(3*b-1) := by nlinarith [hb]
    exact Int.ediv_nonneg this (by norm_num)
  omega

-- ROW 8
example : ∀ k : ℤ, 2 * ((((-k)*(3*(-k)-1)/2).toNat : ℕ) : ℤ) = (-k)*(3*(-k)-1) := by
  intro k
  have ev : (2:ℤ) ∣ (-k)*(3*(-k)-1) := by
    rcases Int.even_or_odd (-k) with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*(-k)-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  have nn : 0 ≤ (-k)*(3*(-k)-1) := by
    rcases lt_or_ge (-k) 1 with h | h
    · have hk : (-k) ≤ 0 := by omega
      nlinarith [sq_nonneg (-k)]
    · have : 0 ≤ 3*(-k)-1 := by linarith
      positivity
  obtain ⟨q, hq⟩ := ev
  rw [hq, Int.mul_ediv_cancel_left _ (by norm_num)]
  have hqnn : 0 ≤ q := by nlinarith [nn, hq]
  rw [Int.toNat_of_nonneg hqnn, hq]

-- ROW 9
example : Set.InjOn (fun k : ℤ => (k * (3 * k - 1) / 2).toNat) (Set.Ici (0:ℤ)) := by
  intro a ha b hb hEq
  simp only [Set.mem_Ici] at ha hb
  simp only at hEq
  have ea : (2:ℤ) ∣ a*(3*a-1) := by
    rcases Int.even_or_odd a with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*a-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  have eb : (2:ℤ) ∣ b*(3*b-1) := by
    rcases Int.even_or_odd b with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*b-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  obtain ⟨qa, hqa⟩ := ea
  obtain ⟨qb, hqb⟩ := eb
  have nna : 0 ≤ a*(3*a-1) := by
    rcases lt_or_ge a 1 with h | h
    · have : a = 0 := by omega
      simp [this]
    · have : 0 ≤ 3*a-1 := by linarith
      positivity
  have nnb : 0 ≤ b*(3*b-1) := by
    rcases lt_or_ge b 1 with h | h
    · have : b = 0 := by omega
      simp [this]
    · have : 0 ≤ 3*b-1 := by linarith
      positivity
  have hqann : 0 ≤ qa := by nlinarith [nna, hqa]
  have hqbnn : 0 ≤ qb := by nlinarith [nnb, hqb]
  rw [hqa, hqb, Int.mul_ediv_cancel_left _ (by norm_num),
      Int.mul_ediv_cancel_left _ (by norm_num),
      Int.toNat_of_nonneg hqann, Int.toNat_of_nonneg hqbnn] at hEq
  subst hEq
  have heq2 : a*(3*a-1) = b*(3*b-1) := by rw [hqa, hqb]
  nlinarith [heq2, ha, hb, sq_nonneg (a-b), sq_nonneg (a+b)]

-- ROW 10
example : ∀ k : ℤ, 1 ≤ k → (k*(3*k-1)/2).toNat + k ≤ ((k+1)*(3*(k+1)-1)/2).toNat := by
  intro k hk
  have ek : (2:ℤ) ∣ k*(3*k-1) := by
    rcases Int.even_or_odd k with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*k-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  have ek1 : (2:ℤ) ∣ (k+1)*(3*(k+1)-1) := by
    rcases Int.even_or_odd (k+1) with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m*(3*(k+1)-1), by rw [hm]; ring⟩
    · exact ⟨(2*m+1)*(3*m+1), by rw [hm]; ring⟩
  obtain ⟨qk, hqk⟩ := ek
  obtain ⟨qk1, hqk1⟩ := ek1
  have hqknn : 0 ≤ qk := by nlinarith [hk, hqk]
  have hqk1nn : 0 ≤ qk1 := by nlinarith [hk, hqk1]
  rw [hqk, hqk1, Int.mul_ediv_cancel_left _ (by norm_num),
      Int.mul_ediv_cancel_left _ (by norm_num),
      Int.toNat_of_nonneg hqknn, Int.toNat_of_nonneg hqk1nn]
  have goalZ : qk + k ≤ qk1 := by nlinarith [hqk, hqk1, hk]
  omega

-- ROW 11
example : ∀ {k : ℕ} {M c : ℝ}, 0 ≤ M → 0 < c →
    (∫ x in (0:ℝ)..M, x ^ k * Real.exp (-(c * x))) ≤ (Nat.factorial k : ℝ) / c ^ (k + 1) := by
  intro k M c hM hc
  sorry

-- ROW 12
example : ∀ {k M : ℕ} {c : ℝ}, 0 < c →
    (∑ i ∈ Finset.Ico 0 M, (i:ℝ) ^ k * Real.exp (-(c * i))) ≤ Real.exp c * (Nat.factorial k:ℝ) / c ^ (k+1) := by
  intro k M c hc
  sorry

-- ROW 13
example : ∀ {k M : ℕ} {c : ℝ}, 0 < c →
    (∑ i ∈ Finset.Iic M, (i:ℝ) ^ k * Real.exp (-(c * i))) ≤ Real.exp c * (Nat.factorial k:ℝ) / c ^ (k+1) := by
  intro k M c hc
  sorry

-- ROW 14
example : ∀ {k M : ℕ} {c : ℝ}, 0 < c →
    (∑ i ∈ Finset.Iic M, (i:ℝ) ^ k * (2:ℝ) ^ (-(c * i))) ≤ (2:ℝ) ^ c * (Nat.factorial k:ℝ) / (Real.log 2 * c) ^ (k+1) := by
  intro k M c hc
  sorry
