import Mathlib.Topology.Algebra.InfiniteSum.Real
import Mathlib.Analysis.MeanInequalities
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity

/-!
# HL maximal-function dual-load closure (tick492)

**Ex-post Lean formalization** of the HL-maximal-function paper-and-pencil
attack on `FlatKineticLoadNoReuse`.

**Three-way convergent finding** (GPT-5.5 + codex_rd + claude_rd):
the dual-load Schur envelope fails at the **sup-time vs common-time
obstruction**:
* `L_n = Σ_Q sup_t ∫_{B_Q} |u-u_Q|²` uses INDEPENDENT sup times per Q.
* Leray-Hopf only controls `sup_t Σ_Q ∫` (common time).
* Scalar countermodel: time-disjoint bumps defeat naive bound.

**Repair (per GPT-5.5)**: replace free sup with local-energy variation:
* `sup_t E_Q ≤ avg + Var_{I_Q}(E_Q)`
* `Var ≤ route + pressure + commutator + defect variation charges`
* `FlatKineticLoadNoReuse` = independent sup-times ⇒ summable variation charges

**codex_rd posterior** (real codex via pub/sub): `p_success = 0.41`,
`p_needs_new_lemma = 0.86`, top failure mode
`maximal_function_bridge_insufficient = 0.36`.

## What this file ships (real Lean content)

Composition: from a carrier field asserting the weighted kinetic-load
bound holds, derive `Summable A` via tick491's dual-load Cauchy-Schwarz
+ tick470's weighted L² ⇒ Summable A.

The PDE content is in the carrier's `L_weighted_summable` field —
the genuine open obligation per GPT-5.5 + codex_rd convergence.
-/

namespace ZtareProofs.NSHLMaximalDualLoadClosure

/--
**`FlatKineticLoadNoReuseCarrier`** — packages the post-GPT-5.5 repaired
formulation.

Fields:
* `A n`, `D n`, `L n` per-generation sums (as in tick491).
* `interpolation_inequality`: `A_n² ≤ D_n · L_n` (CKN-bad + Gagliardo-Nirenberg).
* `D_summable`: Leray-Hopf enstrophy budget.
* `L_summable`: **THE OPEN PDE CONTENT** — weighted kinetic-load no-reuse,
  per GPT-5.5: `Σ_n L_n < ∞` requires variation-charge summability,
  not just Leray energy.
-/
structure FlatKineticLoadNoReuseCarrier where
  A : ℕ → ℝ
  A_nonneg : ∀ n : ℕ, 0 ≤ A n
  D : ℕ → ℝ
  D_nonneg : ∀ n : ℕ, 0 ≤ D n
  L : ℕ → ℝ
  L_nonneg : ∀ n : ℕ, 0 ≤ L n
  /-- CKN-bad Gagliardo-Nirenberg interpolation. -/
  interpolation_inequality : ∀ n : ℕ, (A n)^2 ≤ D n * L n
  /-- Leray-Hopf dissipation budget (standard). -/
  D_summable : Summable D
  /-- **Open PDE content**: kinetic-load no-reuse via variation charges. -/
  L_summable : Summable L

/--
**Tick492 main theorem: FlatKineticLoadNoReuse ⇒ Summable A.**

Real Lean composition via Cauchy-Schwarz on Finset partial sums.

For each `N`:
  `(Σ_{n<N} A_n)² ≤ (Σ A_n²) · 1`     [Cauchy-Schwarz, trivial]
                  ≤ (Σ D_n · L_n) · 1  [interpolation]
                  ≤ (Σ D_n) · (Σ L_n) · 1  [Cauchy-Schwarz again]
                  ≤ tsum D · tsum L
-/
theorem fkln_no_reuse_implies_summable
    (h : FlatKineticLoadNoReuseCarrier) : Summable h.A := by
  set f : ℕ → ℝ := fun n => Real.sqrt (h.D n) with hf
  set g : ℕ → ℝ := fun n => Real.sqrt (h.L n) with hg
  have hf_nn : ∀ n, 0 ≤ f n := fun n => Real.sqrt_nonneg _
  have hg_nn : ∀ n, 0 ≤ g n := fun n => Real.sqrt_nonneg _
  -- A_n ≤ f_n · g_n via A_n² ≤ D_n · L_n
  have hA_le_fg : ∀ n, h.A n ≤ f n * g n := by
    intro n
    have h_sq := h.interpolation_inequality n
    have h_DL_nn : 0 ≤ h.D n * h.L n := mul_nonneg (h.D_nonneg n) (h.L_nonneg n)
    calc h.A n = Real.sqrt ((h.A n)^2) := (Real.sqrt_sq (h.A_nonneg n)).symm
      _ ≤ Real.sqrt (h.D n * h.L n) := Real.sqrt_le_sqrt h_sq
      _ = Real.sqrt (h.D n) * Real.sqrt (h.L n) := Real.sqrt_mul (h.D_nonneg n) _
  -- Bound partial sums of A by partial sums of f·g, then Cauchy-Schwarz to √(C_D)·√(C_L)
  let C_D := ∑' n, h.D n
  let C_L := ∑' n, h.L n
  have hCD_nn : 0 ≤ C_D := tsum_nonneg h.D_nonneg
  have hCL_nn : 0 ≤ C_L := tsum_nonneg h.L_nonneg
  apply summable_of_sum_range_le (c := Real.sqrt C_D * Real.sqrt C_L) h.A_nonneg
  intro N
  have h_partial_A_le_fg :
      ∑ n ∈ Finset.range N, h.A n ≤ ∑ n ∈ Finset.range N, f n * g n :=
    Finset.sum_le_sum (fun n _ => hA_le_fg n)
  have hCS : (∑ n ∈ Finset.range N, f n * g n)^2
           ≤ (∑ n ∈ Finset.range N, (f n)^2) * (∑ n ∈ Finset.range N, (g n)^2) :=
    Finset.sum_mul_sq_le_sq_mul_sq (Finset.range N) f g
  have hf_sq : ∀ n, (f n)^2 = h.D n := fun n => Real.sq_sqrt (h.D_nonneg n)
  have hg_sq : ∀ n, (g n)^2 = h.L n := fun n => Real.sq_sqrt (h.L_nonneg n)
  have hf_sq_sum : ∑ n ∈ Finset.range N, (f n)^2 = ∑ n ∈ Finset.range N, h.D n :=
    Finset.sum_congr rfl (fun n _ => hf_sq n)
  have hg_sq_sum : ∑ n ∈ Finset.range N, (g n)^2 = ∑ n ∈ Finset.range N, h.L n :=
    Finset.sum_congr rfl (fun n _ => hg_sq n)
  rw [hf_sq_sum, hg_sq_sum] at hCS
  have h_D_partial : ∑ n ∈ Finset.range N, h.D n ≤ C_D :=
    h.D_summable.sum_le_tsum (Finset.range N) (fun n _ => h.D_nonneg n)
  have h_L_partial : ∑ n ∈ Finset.range N, h.L n ≤ C_L :=
    h.L_summable.sum_le_tsum (Finset.range N) (fun n _ => h.L_nonneg n)
  have h_sumA_nn : 0 ≤ ∑ n ∈ Finset.range N, h.A n :=
    Finset.sum_nonneg (fun n _ => h.A_nonneg n)
  have h_sumA_sq_le : (∑ n ∈ Finset.range N, h.A n)^2 ≤ C_D * C_L := by
    calc (∑ n ∈ Finset.range N, h.A n)^2
        ≤ (∑ n ∈ Finset.range N, f n * g n)^2 := by
          apply sq_le_sq' _ h_partial_A_le_fg
          have h_fg_nn : 0 ≤ ∑ n ∈ Finset.range N, f n * g n :=
            Finset.sum_nonneg (fun n _ => mul_nonneg (hf_nn n) (hg_nn n))
          linarith
      _ ≤ (∑ n ∈ Finset.range N, h.D n) * (∑ n ∈ Finset.range N, h.L n) := hCS
      _ ≤ C_D * C_L := mul_le_mul h_D_partial h_L_partial
          (Finset.sum_nonneg (fun n _ => h.L_nonneg n)) hCD_nn
  calc ∑ n ∈ Finset.range N, h.A n
      = Real.sqrt ((∑ n ∈ Finset.range N, h.A n)^2) := (Real.sqrt_sq h_sumA_nn).symm
    _ ≤ Real.sqrt (C_D * C_L) := Real.sqrt_le_sqrt h_sumA_sq_le
    _ = Real.sqrt C_D * Real.sqrt C_L := Real.sqrt_mul hCD_nn _

/-! ## Honest scope guard -/

/-- **Tick492: HL maximal function attack's structural composition.**

What this file proves:
* From `FlatKineticLoadNoReuseCarrier`, `Summable A` follows via
  Cauchy-Schwarz on partial sums (real ℝ-arithmetic).

What this file does NOT prove:
* The `L_summable` field — the GENUINELY OPEN PDE content per
  three-way convergent finding (GPT-5.5 + codex_rd + claude_rd):
  - Sup-time vs common-time obstruction (Leray controls sup-t Σ but
    not Σ sup-t of independent times)
  - GPT-5.5 repair via local-energy variation: requires variation
    charges from route/pressure/commutator/defect to be summable
  - codex_rd p_success = 0.41 with maximal-function-bridge as top risk

The HL maximal function angle attempted closure but the same
obstruction surfaces: independent sup-times across the cascade
require NS variation-charge structure that Leray-Hopf alone doesn't
supply.

Per session's three-way convergence: `FlatKineticLoadNoReuse` is
the final equivalent formulation of NS Clay flat-radius closure. -/
structure Tick492IsHLDualLoadAttackedStructural where
  cauchy_schwarz_composition_proven : Prop
  L_summable_is_open_FlatKineticLoadNoReuse : Prop
  sup_time_vs_common_time_obstruction_confirmed : Prop
  three_way_convergence_gpt55_codexrd_clauderd : Prop

end ZtareProofs.NSHLMaximalDualLoadClosure
