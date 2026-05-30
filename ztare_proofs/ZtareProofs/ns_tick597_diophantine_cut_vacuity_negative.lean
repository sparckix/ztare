import Mathlib.Tactic
import Mathlib.Topology.Order.Basic
import Mathlib.Topology.MetricSpace.Basic

/-!
# Tick597 — FORMALIZED NEGATIVE: the Restrict-Σ Diophantine
#   admissible-class cut is VACUOUS on the singular locus (13th
#   recurrence)

## Why (operator: "formalize the negatives")

The Restrict-Σ door restricted admissible inherited-bad configs to
shell-ratio sequences that are Diophantine / badly-approximable
(`|ρ_{n+1}/ρ_n − λ| ≥ κ` infinitely / uniformly), aiming for an
arithmetic small-divisor gain. Adversarial kill: self-similar / DSS
singular profiles are BY DEFINITION frequency-resonant — their shell
ratio tends to `λ`. So the Diophantine cut excludes EXACTLY the
singular locus: the admissible part is singularity-empty and the
"gain" evaporates on the set that carries the problem. This file
formalizes that vacuity.

## What is PROVED

`selfsimilar_not_diophantine`: any shell-ratio sequence with
`qₙ → λ` (self-similar/DSS) canNOT satisfy a uniform Diophantine
separation `∀ n, κ ≤ |qₙ − λ|` for any `κ > 0`. Hence
`diophantine_admissible ∩ self_similar = ∅` — the cut removes the
singular configs themselves. 13th recurrence; NOT a closure.

## Post-check: Tier-1 + Tier-3. Expect NOT_APPLICABLE (a proved
## vacuity lemma; no closure claim).
-/

namespace ZtareProofs.NSTick597DiophantineCutVacuityNegative

/-- Shell-ratio sequence `qₙ = ρ_{n+1}/ρ_n`. Self-similar/DSS singular
profile ⟺ `qₙ → λ` (frequency-resonant by definition of self-similar).
Diophantine-admissible ⟺ a uniform separation `κ ≤ |qₙ − λ|`. -/
def SelfSimilar (q : ℕ → ℝ) (lam : ℝ) : Prop :=
  Filter.Tendsto q Filter.atTop (nhds lam)

def DiophantineAdmissible (q : ℕ → ℝ) (lam : ℝ) : Prop :=
  ∃ κ : ℝ, 0 < κ ∧ ∀ n, κ ≤ |q n - lam|

/-- **`selfsimilar_not_diophantine`** (PROVED — the vacuity).
A self-similar (resonant, `qₙ→λ`) profile is NOT Diophantine-
admissible: tending to `λ` forces `|qₙ−λ|` below any `κ>0`
eventually, contradicting a uniform lower separation. -/
theorem selfsimilar_not_diophantine (q : ℕ → ℝ) (lam : ℝ)
    (hss : SelfSimilar q lam) : ¬ DiophantineAdmissible q lam := by
  rintro ⟨κ, hκ, hsep⟩
  -- qₙ → λ ⇒ |qₙ − λ| → 0
  have h0 : Filter.Tendsto (fun n => |q n - lam|) Filter.atTop (nhds 0) := by
    have := (hss.sub_const lam)
    simpa using (this.abs)
  -- eventually |qₙ − λ| < κ
  have hev : ∀ᶠ n in Filter.atTop, |q n - lam| < κ := by
    have := h0.eventually (gt_mem_nhds hκ)
    simpa using this
  obtain ⟨n, hn⟩ := hev.exists
  exact (not_lt.mpr (hsep n)) hn

/-- **`diophantine_cut_is_vacuous_on_singular_locus`** (PROVED).
The Diophantine-admissible class contains NO self-similar singular
profile: their intersection is empty. The arithmetic gain therefore
lives entirely OFF the singular locus — the cut buys nothing for the
actual problem. 13th recurrence. -/
theorem diophantine_cut_is_vacuous_on_singular_locus
    (q : ℕ → ℝ) (lam : ℝ) :
    ¬ (SelfSimilar q lam ∧ DiophantineAdmissible q lam) := by
  rintro ⟨hss, hdio⟩
  exact selfsimilar_not_diophantine q lam hss hdio

/-- Non-vacuity: the self-similar class is inhabited (the constant
`λ`-ratio sequence is exactly self-similar) — so the vacuity is a real
exclusion of an inhabited singular class, not an empty-hypothesis
triviality. -/
theorem selfsimilar_inhabited (lam : ℝ) :
    SelfSimilar (fun _ => lam) lam := by
  simpa [SelfSimilar] using tendsto_const_nhds

/-! ## Honest record -/

structure Tick597Record where
  /-- PROVED: self-similar (resonant) ⇒ not Diophantine-admissible;
      the cut excludes exactly the singular locus. -/
  diophantine_vacuity_proved : Prop
  /-- The arithmetic gain lives off the singular locus ⇒ the cut buys
      nothing. 13th recurrence; NOT a closure, NOT an impossibility. -/
  thirteenth_recurrence_not_closure : Prop

end ZtareProofs.NSTick597DiophantineCutVacuityNegative
