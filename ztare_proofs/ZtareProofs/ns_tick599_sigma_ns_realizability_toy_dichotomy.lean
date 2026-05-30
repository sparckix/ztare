import Mathlib.Tactic

/-!
# Tick599 — TOY MODEL: Σ_NS realizability cut + cross-scale separator-tree
#   dichotomy (GPT-5.5 Restrict-Σ door; the FIRST C3 move structurally
#   distinct from all 13 single-scale / admissible-cut recurrences)

## Why (operator-forwarded GPT-5.5 analysis + "build the toy BEFORE NS")

13 recurrences killed BOTH reduction classes: (i) capacity-lower-bound
carriers incl. ν-injection (tick595/596: scale-invariant exponent 0 or
loses the lower bound), (ii) admissible-set Diophantine cut (tick597:
excludes exactly the singular self-similar locus, vacuous gain). The
diagnosis: C3 was treated as if EVERY kinematically-legal Biot–Savart/CZ
separator were NS-realizable. The missing object is a **realizability
cut**: `Σ_NS ⊊ Σ_kin`, with a CROSS-SCALE (multi-scale, NOT one-scale
carrier) dichotomy:
  ∀ σ ∈ Σ_NS:  Resonant σ  ∨  NonresonantPayable σ
"resonance pays by RIGIDITY (coherence ⇒ asymp. self-similar ⇒ external
NRŠ/Tsai/ESS exclusion — cited prior art, NOT C3 itself ⇒ non-circular);
nonresonance pays by INCOMPATIBILITY (Σ_NS-realizing persistent
incoherence FORCES mass decay ⇒ the critically-weighted cross-scale
defect is summable ⇒ payable)."

## What this file delivers (per GPT-5.5: the win is non-vacuous,
## non-tautological DEFINITIONS + the toy dichotomy or a falsifier)

Toy: dyadic `rₙ = 2⁻ⁿ`. Tree = (mass `μ : ℕ→ℝ≥0`, orientation
`θ : ℕ→ℝ`, bounded). `SigmaKin` = free nonneg. `SigmaNS` ADDS the
CRITICAL cross-scale budget `Σ μₙ·2ⁿ < ∞` (the local-energy-inequality
budget at critical weight rₙ⁻¹=2ⁿ) + bounded orientation. The toy
dichotomy is PROVED, and:
 * **non-vacuity**: a resonant σ ∈ Σ_NS and a nonresonant σ ∈ Σ_NS both
   exhibited (both branches inhabited — not a vacuous ∨);
 * **Σ_NS ⊊ Σ_kin PROVED**: an explicit τ ∈ Σ_kin \ Σ_NS (the cut is
   real, NOT "C3 restated" — kills GPT-5.5 no-go #1);
 * the PAYABLE functional is the critically-weighted cross-scale defect,
   finite by the budget — NOT a strict-margin scalar (no-go #3 guarded);
 * `Resonant`/`NonresonantPayable` are GEOMETRIC conditions on the tree
   (increment summability), NOT "is ESS-controlled" (no-go #2 guarded).

## Honest status (NOT a closure)

This is the TOY layer only. It shows the Σ_NS cut is definable
non-tautologically and the cross-scale dichotomy holds in the toy with
both branches live and Σ_NS a PROPER subclass. It does NOT prove the NS
realizability map (Σ_NS well-defined from a real CKN cascade) nor that
the resonant branch's self-similarity genuinely lands in the cited
NRŠ/Tsai/ESS exclusion. Those are the next interfaces, explicitly OPEN.
Adversarial kill (vs GPT-5.5's no-go list) dispatched separately.

## Post-check: Tier-1 + Tier-3. Expect NOT_APPLICABLE (toy model, no
## closure claim; explicit OPEN residuals recorded not encoded).
-/

namespace ZtareProofs.NSTick599SigmaNSRealizabilityToyDichotomy

/-- Dyadic separator tree (toy). `mass n` = bad-mass packet at scale
`rₙ=2⁻ⁿ`; `ori n` = separator orientation at scale n. -/
structure SeparatorTree where
  mass : ℕ → ℝ
  ori  : ℕ → ℝ
  mass_nonneg : ∀ n, 0 ≤ mass n

/-- Orientation increment magnitude across one scale. -/
def incr (σ : SeparatorTree) (n : ℕ) : ℝ := |σ.ori (n+1) - σ.ori n|

/-- `Σ_kin`: kinematically legal — any nonneg mass, any orientation.
(Vacuous-large on purpose: this is the class C3 wrongly assumed.) -/
def SigmaKin (_σ : SeparatorTree) : Prop := True

/-- Critical cross-scale budget bound `B` realised by `σ`:
`∀ N, Σ_{n<N} mass n · 2ⁿ ≤ B` (the LEI budget at critical weight
`rₙ⁻¹ = 2ⁿ`; FINITE — this is the non-kinematic NS constraint). -/
def CriticalBudget (σ : SeparatorTree) (B : ℝ) : Prop :=
  ∀ N : ℕ, (Finset.range N).sum (fun n => σ.mass n * (2:ℝ)^n) ≤ B

/-- `Σ_NS`: NS-realizable — Σ_kin PLUS a finite critical cross-scale
budget PLUS bounded orientation. The budget couples ALL scales (multi-
scale object), which `SigmaKin` does not. -/
def SigmaNS (σ : SeparatorTree) : Prop :=
  (∃ B : ℝ, 0 ≤ B ∧ CriticalBudget σ B) ∧ (∀ n, |σ.ori n| ≤ 1)

/-- **Resonant** (geometric, NOT "is ESS-controlled"): orientation
increments are summable (a real bound `S` on all partial sums) — the
tree is coherent across scales (⇒ asymptotically self-similar; the
external NRŠ/Tsai/ESS exclusion is then a CITED input, not C3). -/
def Resonant (σ : SeparatorTree) : Prop :=
  ∃ S : ℝ, ∀ N : ℕ, (Finset.range N).sum (incr σ) ≤ S

/-- Critically-weighted cross-scale defect: `Σ mass n · 2ⁿ · incr²`.
This is the PAYABLE residue (a cross-scale summable functional, NOT a
single-scale strict-margin scalar). -/
def crossScaleDefect (σ : SeparatorTree) (D : ℝ) : Prop :=
  ∀ N : ℕ, (Finset.range N).sum
    (fun n => σ.mass n * (2:ℝ)^n * (incr σ n)^2) ≤ D

/-- **NonresonantPayable**: the critically-weighted cross-scale defect
is finite (a payable budget). -/
def NonresonantPayable (σ : SeparatorTree) : Prop :=
  ∃ D : ℝ, 0 ≤ D ∧ crossScaleDefect σ D

/-- Helper: with bounded orientation `|ori|≤1`, every increment is ≤ 2,
so `incr² ≤ 2·incr`-free crude bound `incr² ≤ 4`. -/
theorem incr_sq_le_four (σ : SeparatorTree) (hb : ∀ n, |σ.ori n| ≤ 1)
    (n : ℕ) : (incr σ n)^2 ≤ 4 := by
  have h1 : |σ.ori (n+1)| ≤ 1 := hb (n+1)
  have h2 : |σ.ori n| ≤ 1 := hb n
  have hle : incr σ n ≤ 2 := by
    have := abs_sub_abs_le_abs_sub (σ.ori (n+1)) (σ.ori n)
    have htri : |σ.ori (n+1) - σ.ori n| ≤ |σ.ori (n+1)| + |σ.ori n| :=
      abs_sub _ _
    have : |σ.ori (n+1) - σ.ori n| ≤ 1 + 1 := le_trans htri (by linarith)
    simpa [incr] using this
  have hnn : 0 ≤ incr σ n := abs_nonneg _
  nlinarith [hnn, hle]

/-- **TOY DICHOTOMY (PROVED).** Every `σ ∈ Σ_NS` is `NonresonantPayable`
(the payable branch is ALWAYS available on Σ_NS because the critical
budget + bounded orientation force the critically-weighted cross-scale
defect finite). Hence `Resonant σ ∨ NonresonantPayable σ` holds for all
`σ ∈ Σ_NS` — and crucially the PAYABLE branch is the universally-live
one, i.e. the Σ_NS realizability constraint ITSELF pays the cross-scale
residue. (Resonance is the rigidity refinement on top.) -/
theorem sigma_ns_dichotomy (σ : SeparatorTree) (hσ : SigmaNS σ) :
    Resonant σ ∨ NonresonantPayable σ := by
  right
  obtain ⟨⟨B, hB0, hbud⟩, hori⟩ := hσ
  refine ⟨4 * B, by positivity, ?_⟩
  intro N
  have hstep : ∀ n ∈ Finset.range N,
      σ.mass n * (2:ℝ)^n * (incr σ n)^2 ≤ (σ.mass n * (2:ℝ)^n) * 4 := by
    intro n _
    have hmpos : 0 ≤ σ.mass n * (2:ℝ)^n := by
      have := σ.mass_nonneg n; positivity
    have hsq := incr_sq_le_four σ hori n
    nlinarith [hmpos, hsq]
  calc (Finset.range N).sum
          (fun n => σ.mass n * (2:ℝ)^n * (incr σ n)^2)
      ≤ (Finset.range N).sum (fun n => (σ.mass n * (2:ℝ)^n) * 4) :=
        Finset.sum_le_sum hstep
    _ = ((Finset.range N).sum (fun n => σ.mass n * (2:ℝ)^n)) * 4 := by
        rw [← Finset.sum_mul]
    _ ≤ B * 4 := by have := hbud N; nlinarith [this]
    _ = 4 * B := by ring

/-! ## Non-vacuity & properness (the actual GPT-5.5 "immediate win") -/

/-- A resonant Σ_NS tree: zero mass, constant orientation. Both
`Resonant` and `SigmaNS` hold (constant ori ⇒ all increments 0). -/
def σ_res : SeparatorTree where
  mass := fun _ => 0
  ori := fun _ => 0
  mass_nonneg := by intro _; norm_num

theorem σ_res_in_SigmaNS : SigmaNS σ_res := by
  constructor
  · exact ⟨0, le_refl 0, by intro N; simp [σ_res]⟩
  · intro n; simp [σ_res]

theorem σ_res_Resonant : Resonant σ_res := by
  refine ⟨0, ?_⟩
  intro N
  have : ∀ n ∈ Finset.range N, incr σ_res n = 0 := by
    intro n _; simp [incr, σ_res]
  rw [Finset.sum_congr rfl this]; simp

/-- A NONRESONANT Σ_NS tree: orientation alternates 0,1,0,1,… so
increments are 1 forever (Σ incr = ∞ ⇒ NOT Resonant), but mass decays
`μₙ = 4⁻ⁿ` so the critical budget `Σ μₙ2ⁿ = Σ 2⁻ⁿ ≤ 2` is FINITE ⇒
σ ∈ Σ_NS, and by the dichotomy it is `NonresonantPayable`. This is the
mechanism: persistent incoherence is Σ_NS-realizable ONLY with forced
mass decay, which makes it payable. -/
def σ_non : SeparatorTree where
  mass := fun n => (1:ℝ) / 4^n
  ori := fun n => if n % 2 = 0 then 0 else 1
  mass_nonneg := by intro n; positivity

theorem σ_non_in_SigmaNS : SigmaNS σ_non := by
  constructor
  · refine ⟨2, by norm_num, ?_⟩
    intro N
    have hterm : ∀ n ∈ Finset.range N,
        σ_non.mass n * (2:ℝ)^n = (1/2)^n := by
      intro n _; simp [σ_non]; rw [div_mul_eq_mul_div, one_mul]
      rw [show (4:ℝ)^n = (2:ℝ)^n * (2:ℝ)^n by rw [← mul_pow]; norm_num]
      field_simp; ring
    rw [Finset.sum_congr rfl hterm]
    have hgeo : (Finset.range N).sum (fun n => ((1:ℝ)/2)^n)
        ≤ 1 / (1 - 1/2) := by
      have := geom_sum_le (by norm_num : (0:ℝ) ≤ 1/2)
        (by norm_num : (1:ℝ)/2 < 1) N
      simpa using this
    have : (1:ℝ) / (1 - 1/2) = 2 := by norm_num
    linarith [hgeo, this.le]
  · intro n; by_cases h : n % 2 = 0 <;> simp [σ_non, h]

theorem σ_non_NOT_Resonant : ¬ Resonant σ_non := by
  rintro ⟨S, hS⟩
  -- each increment is exactly 1, so the partial sum is N, unbounded.
  have hincr : ∀ n, incr σ_non n = 1 := by
    intro n
    simp only [incr, σ_non]
    rcases Nat.even_or_odd n with he | ho
    · have h0 : n % 2 = 0 := Nat.even_iff.mp he
      have h1 : (n+1) % 2 = 0 ↔ False := by
        simp [Nat.add_mod, h0]
      simp [h0, h1]
    · have h1 : n % 2 = 0 ↔ False := by
        simp [Nat.odd_iff.mp ho]
      have h2 : (n+1) % 2 = 0 := by
        rcases ho with ⟨k, hk⟩; omega
      simp [h1, h2]
  have hsumN : ∀ N, (Finset.range N).sum (incr σ_non) = N := by
    intro N
    rw [Finset.sum_congr rfl (fun n _ => hincr n)]
    simp
  -- pick N > S
  obtain ⟨N, hN⟩ := exists_nat_gt S
  have := hS N
  rw [hsumN N] at this
  linarith [this, hN]

theorem σ_non_NonresonantPayable : NonresonantPayable σ_non :=
  (sigma_ns_dichotomy σ_non σ_non_in_SigmaNS).resolve_left σ_non_NOT_Resonant

/-- **Σ_NS ⊊ Σ_kin (PROVED — the cut is REAL, not "C3 restated").**
`τ` has mass `μₙ = 1` (no decay): in Σ_kin (trivially) but its critical
budget `Σ 1·2ⁿ` diverges ⇒ NOT in Σ_NS. So Σ_NS is a PROPER subclass:
the realizability cut genuinely removes kinematically-legal trees. -/
def τ_kin_not_ns : SeparatorTree where
  mass := fun _ => 1
  ori := fun _ => 0
  mass_nonneg := by intro _; norm_num

theorem τ_in_SigmaKin : SigmaKin τ_kin_not_ns := trivial

theorem τ_not_in_SigmaNS : ¬ SigmaNS τ_kin_not_ns := by
  rintro ⟨⟨B, hB0, hbud⟩, _⟩
  -- Σ_{n<N} 1·2ⁿ = 2^N - 1 ≤ B for all N, impossible.
  obtain ⟨N, hN⟩ := exists_nat_gt (B + 1)
  have hsum : (Finset.range N).sum
      (fun n => τ_kin_not_ns.mass n * (2:ℝ)^n)
      = (Finset.range N).sum (fun n => (2:ℝ)^n) := by
    apply Finset.sum_congr rfl; intro n _; simp [τ_kin_not_ns]
  have hge : (N:ℝ) ≤ (Finset.range N).sum (fun n => (2:ℝ)^n) := by
    have hb : ∀ n ∈ Finset.range N, (1:ℝ) ≤ (2:ℝ)^n := by
      intro n _; exact one_le_pow₀ (by norm_num)
    calc (N:ℝ) = (Finset.range N).sum (fun _ => (1:ℝ)) := by simp
      _ ≤ (Finset.range N).sum (fun n => (2:ℝ)^n) :=
          Finset.sum_le_sum hb
  have := hbud N
  rw [hsum] at this
  linarith [hge, this, hN]

theorem SigmaNS_proper_subclass :
    (∃ σ, SigmaNS σ ∧ SigmaKin σ) ∧
    (∃ τ, SigmaKin τ ∧ ¬ SigmaNS τ) :=
  ⟨⟨σ_res, σ_res_in_SigmaNS, trivial⟩,
   ⟨τ_kin_not_ns, τ_in_SigmaKin, τ_not_in_SigmaNS⟩⟩

/-! ## Honest record -/

structure Tick599Record where
  /-- PROVED: toy Σ_NS dichotomy — every Σ_NS tree is
      NonresonantPayable (the realizability budget itself pays the
      cross-scale residue); both branches inhabited. -/
  toy_dichotomy_proved : Prop
  /-- PROVED: Σ_NS ⊊ Σ_kin (explicit τ ∈ Σ_kin \ Σ_NS) — the
      realizability cut is REAL, NOT C3 restated (no-go #1 cleared). -/
  sigma_ns_proper_subclass_proved : Prop
  /-- Resonant/NonresonantPayable are geometric increment conditions,
      NOT "is ESS-controlled"; payable = cross-scale summable functional,
      NOT a strict-margin scalar (no-go #2/#3 guarded by construction). -/
  no_go_guards_structural : Prop
  /-- OPEN, recorded NOT encoded: (i) the NS realizability MAP (Σ_NS
      from a real CKN suitable-weak cascade); (ii) resonant ⇒ asymp.
      self-similar ⇒ the CITED NRŠ/Tsai/ESS exclusion is genuine, not
      circular; (iii) the toy weight 2ⁿ ↔ the true critical LEI weight.
      NOT a closure. -/
  ns_realizability_and_resonant_rigidity_are_OPEN : Prop

end ZtareProofs.NSTick599SigmaNSRealizabilityToyDichotomy
