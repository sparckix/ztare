import Mathlib

open MeasureTheory Real

set_option maxHeartbeats 1000000

-- ROW 1
example : ((0:ℤ)*(3*0-1)/2).toNat = 0 := by decide

-- ROW 2
example : ((1:ℤ)*(3*1-1)/2).toNat = 1 := by decide

-- ROW 3
example : ∀ k : ℤ, (2:ℤ) ∣ k*(3*k-1) := by
  intro k
  rcases Int.even_or_odd k with ⟨m, hm⟩ | ⟨m, hm⟩
  · exact ⟨m * (3 * k - 1), by rw [hm]; ring⟩
  · exact ⟨k * (3*m+1), by rw [hm]; ring⟩

-- ROW 4
example : ∀ k : ℤ, 0 ≤ k*(3*k-1) := by
  intro k
  rcases le_or_gt 0 k with h | h
  · rcases eq_or_lt_of_le h with h0 | h0
    · simp [← h0]
    · have : (0:ℤ) ≤ 3*k-1 := by nlinarith
      positivity
  · have h1 : k ≤ -1 := by omega
    nlinarith

-- helper: for k ≥ 0, 2 * (toNat value) = k*(3k-1)
theorem pent_two_mul (k : ℤ) (hk : 0 ≤ k) :
    2 * (((k*(3*k-1)/2).toNat : ℕ) : ℤ) = k*(3*k-1) := by
  have hdvd : (2:ℤ) ∣ k*(3*k-1) := by
    rcases Int.even_or_odd k with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m * (3 * k - 1), by rw [hm]; ring⟩
    · exact ⟨k * (3*m+1), by rw [hm]; ring⟩
  have hnn : 0 ≤ k*(3*k-1) := by
    rcases eq_or_lt_of_le hk with h0 | h0
    · simp [← h0]
    · have : (0:ℤ) ≤ 3*k-1 := by nlinarith
      positivity
  have hqnn : 0 ≤ k*(3*k-1)/2 := Int.ediv_nonneg hnn (by norm_num)
  rw [Int.toNat_of_nonneg hqnn]
  rw [mul_comm]
  exact Int.ediv_mul_cancel hdvd

-- ROW 5
example : StrictMono (fun n : ℕ => (((n:ℤ))*(3*((n:ℤ))-1)/2).toNat) := by
  apply strictMono_nat_of_lt_succ
  intro n
  have h1 := pent_two_mul (n:ℤ) (by positivity)
  have h2 := pent_two_mul ((n:ℤ)+1) (by positivity)
  have hcast : ((n:ℤ)+1) = ((n+1 : ℕ) : ℤ) := by push_cast; ring
  rw [hcast] at h2
  have key : 2 * (((((n:ℤ))*(3*((n:ℤ))-1)/2).toNat : ℕ) : ℤ)
      < 2 * ((((((n+1:ℕ):ℤ))*(3*(((n+1:ℕ):ℤ))-1)/2).toNat : ℕ) : ℤ) := by
    rw [h1, h2]; push_cast; nlinarith [Nat.cast_nonneg (α := ℤ) n]
  have : (((((n:ℤ))*(3*((n:ℤ))-1)/2).toNat : ℕ) : ℤ)
      < ((((((n+1:ℕ):ℤ))*(3*(((n+1:ℕ):ℤ))-1)/2).toNat : ℕ) : ℤ) := by linarith
  exact_mod_cast this

-- ROW 6
example : ∀ k : ℤ, 1 ≤ k → 1 ≤ (k*(3*k-1)/2).toNat := by
  intro k hk
  have hpos : (1:ℤ) ≤ k*(3*k-1)/2 := by
    have : (2:ℤ) ≤ k*(3*k-1) := by nlinarith
    omega
  omega

-- ROW 7
example : StrictMonoOn (fun k : ℤ => (k * (3 * k - 1) / 2).toNat) (Set.Ici (1:ℤ)) := by
  intro a ha b hb hab
  simp only [Set.mem_Ici] at ha hb
  have ha0 : (0:ℤ) ≤ a := by linarith
  have hb0 : (0:ℤ) ≤ b := by linarith
  have h1 := pent_two_mul a ha0
  have h2 := pent_two_mul b hb0
  have key : 2 * (((a*(3*a-1)/2).toNat : ℕ) : ℤ) < 2 * (((b*(3*b-1)/2).toNat : ℕ) : ℤ) := by
    rw [h1, h2]; nlinarith
  have : (((a*(3*a-1)/2).toNat : ℕ) : ℤ) < (((b*(3*b-1)/2).toNat : ℕ) : ℤ) := by linarith
  exact_mod_cast this

-- ROW 9
example : Set.InjOn (fun k : ℤ => (k * (3 * k - 1) / 2).toNat) (Set.Ici (0:ℤ)) := by
  intro a ha b hb hab
  simp only [Set.mem_Ici] at ha hb
  simp only at hab
  have h1 := pent_two_mul a ha
  have h2 := pent_two_mul b hb
  have heq : a*(3*a-1) = b*(3*b-1) := by
    rw [← h1, ← h2, hab]
  nlinarith [sq_nonneg (a - b), sq_nonneg (a + b)]

-- ROW 10
example : ∀ k : ℤ, 1 ≤ k → (k*(3*k-1)/2).toNat + k ≤ ((k+1)*(3*(k+1)-1)/2).toNat := by
  intro k hk
  have hk0 : (0:ℤ) ≤ k := by linarith
  have hk1 : (0:ℤ) ≤ k+1 := by linarith
  have h1 := pent_two_mul k hk0
  have h2 := pent_two_mul (k+1) hk1
  have key : (((k*(3*k-1)/2).toNat : ℕ) : ℤ) + k ≤ ((((k+1)*(3*(k+1)-1)/2).toNat : ℕ) : ℤ) := by
    nlinarith [h1, h2]
  calc ((k*(3*k-1)/2).toNat + k : ℤ)
      = ((k*(3*k-1)/2).toNat : ℤ) + k := by ring
    _ ≤ (((k+1)*(3*(k+1)-1)/2).toNat : ℤ) := key


-- ROW 8
example : ∀ k : ℤ, 2 * ((((-k)*(3*(-k)-1)/2).toNat : ℕ) : ℤ) = (-k)*(3*(-k)-1) := by
  intro k
  have hdvd : (2:ℤ) ∣ (-k)*(3*(-k)-1) := by
    rcases Int.even_or_odd (-k) with ⟨m, hm⟩ | ⟨m, hm⟩
    · exact ⟨m * (3 * (-k) - 1), by rw [hm]; ring⟩
    · exact ⟨(-k) * (3*m+1), by rw [hm]; ring⟩
  have hnn : 0 ≤ (-k)*(3*(-k)-1) := by
    rcases le_or_gt 0 (-k) with h | h
    · rcases eq_or_lt_of_le h with h0 | h0
      · simp [← h0]
      · have : (0:ℤ) ≤ 3*(-k)-1 := by nlinarith
        positivity
    · nlinarith
  have hdiv : (-k)*(3*(-k)-1)/2 * 2 = (-k)*(3*(-k)-1) := Int.ediv_mul_cancel hdvd
  have hqnn : 0 ≤ (-k)*(3*(-k)-1)/2 := Int.ediv_nonneg hnn (by norm_num)
  rw [Int.toNat_of_nonneg hqnn]
  omega

-- ROW 11
example : ∀ {k : ℕ} {M c : ℝ}, 0 ≤ M → 0 < c → (∫ x in (0:ℝ)..M, x ^ k * Real.exp (-(c * x))) ≤ (Nat.factorial k : ℝ) / c ^ (k + 1) := by
  intro k M c hM hc
  exact intervalIntegral_pow_mul_exp_neg_le hM hc

-- ROW 12
example : ∀ {k M : ℕ} {c : ℝ}, 0 < c → (∑ i ∈ Finset.Ico 0 M, (i:ℝ) ^ k * Real.exp (-(c * i))) ≤ Real.exp c * (Nat.factorial k:ℝ) / c ^ (k+1) := by
  intro k M c hc
  have h := sum_Ico_pow_mul_exp_neg_le (k := k) (M := M) hc
  calc (∑ i ∈ Finset.Ico 0 M, (i:ℝ) ^ k * Real.exp (-(c * i)))
      = ∑ i ∈ Finset.Ico 0 M, (i:ℝ) ^ k * Real.exp (- (c * i)) := rfl
    _ ≤ Real.exp c * (Nat.factorial k:ℝ) / c ^ (k+1) := by
        simpa using h

-- ROW 13
example : ∀ {k M : ℕ} {c : ℝ}, 0 < c → (∑ i ∈ Finset.Iic M, (i:ℝ) ^ k * Real.exp (-(c * i))) ≤ Real.exp c * (Nat.factorial k:ℝ) / c ^ (k+1) := by
  intro k M c hc
  have h := sum_Iic_pow_mul_exp_neg_le (k := k) (M := M) hc
  simpa using h

-- ROW 14
example : ∀ {k M : ℕ} {c : ℝ}, 0 < c → (∑ i ∈ Finset.Iic M, (i:ℝ) ^ k * (2:ℝ) ^ (-(c * i))) ≤ (2:ℝ) ^ c * (Nat.factorial k:ℝ) / (Real.log 2 * c) ^ (k+1) := by
  intro k M c hc
  have h := sum_Iic_pow_mul_two_pow_neg_le (k := k) (M := M) hc
  simpa using h
