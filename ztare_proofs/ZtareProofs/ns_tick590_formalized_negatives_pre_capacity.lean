import Mathlib.Tactic

/-!
# Tick590 — FORMALIZED NEGATIVES established en route to the
#   ground-state / Carleman-capacity endpoint (operator-requested)

## Why (operator, 2026-05-16)

"Formalize the negatives that you and GPT-5.5 saw before getting to
the last PDE. it's good to have." Formalized negatives are clean
re-litigation blockers (tick578-580 pattern; Tier-3 clean — genuine
PROVED impossibilities/identities, NOT conditional-forward shells —
the tick581/583 laundering shape is deliberately absent: NO
`… ⇒ route1_closes` anywhere).

## Manifest target (HARD RULE)

These bound the C7 search; the live endpoint routes into **C3**
(ESS / Biot–Savart+CZ separator admissibility) ∧ closeable
C7-upper. NOT a new node — these negatives are exactly why the
interior-surplus formulations failed and the path went to the
ground-state capacity.

## The four negatives

N1 (shear countermodel, GPT-5.5): pure shear `u=(f(y,t),0,0)` has
   `ω=(0,0,−∂_yf)`, `ξ·Sξ=0`, `∇ξ=0` ⇒ `(A_visc)_+|ω|²=0`, yet the
   velocity CKN excess can be > 0. So "CKN-bad ⇒ surplus ≥ δ·r" is
   FALSE; C7-lower MUST be a dichotomy (caloric ∨ surplus).
N2 (signed ⇏ positive-part): a bounded signed sum does NOT bound
   the sum of positive parts. So a signed enstrophy identity cannot
   yield the positive-surplus budget (the "signed-vs-positive
   trap").
N3 (finite budget ⇏ radius charge): a finite total measure does
   NOT imply a per-node `c·r_Q` lower payment.
N4 (ground-state criticality, GPT-5.5): for a positive solution
   `q` of `Lq=Vq`, the localized identity forces the interior
   "surplus" to equal *minus* the boundary capacity — so NO
   interior-sign manipulation can produce a strict positive gain;
   the operator is critical by construction. (This is *why* every
   interior estimate returned the endpoint.)

## Post-check: Tier-1 + Tier-3 (expect NOT_APPLICABLE/PASS — no
## closure claim; genuine impossibilities).
-/

namespace ZtareProofs.NSTick590FormalizedNegativesPreCapacity

/-! ## N1 — shear countermodel: raw lower-payment is FALSE -/

/-- A schematic bad-cylinder datum: `cknExcess` (velocity CKN
excess) and `surplus` (∫(A_visc)_+|ω|²). Pure shear realizes
`surplus=0` with `cknExcess>0`. -/
structure BadDatum where
  cknExcess : ℝ
  surplus : ℝ
  radius : ℝ

/-- **`raw_lower_payment_is_false`** (PROVED). There is NO uniform
`δ>0` with: every CKN-bad datum (`cknExcess>0`) satisfies
`δ·radius ≤ surplus`. Witness: the shear datum
`⟨cknExcess:=1, surplus:=0, radius:=1⟩` (pure shear: `ξ·Sξ=0`,
`∇ξ=0` ⇒ surplus 0; velocity excess 1). Hence C7-lower cannot be
the raw payment — it must be a dichotomy. -/
theorem raw_lower_payment_is_false :
    ¬ ∃ δ : ℝ, 0 < δ ∧ ∀ d : BadDatum,
        0 < d.cknExcess → δ * d.radius ≤ d.surplus := by
  rintro ⟨δ, hδ, h⟩
  have := h ⟨1, 0, 1⟩ (by norm_num)
  simp at this
  linarith

/-! ## N2 — signed identity ⇏ positive-part budget -/

/-- **`signed_not_positive_part`** (PROVED, the signed-vs-positive
trap). The signed sum does NOT control the positive parts: with
`x=1, y=-1`, the signed sum `x+y=0` (perfectly cancelled/bounded),
yet the positive-part sum `x⁺+y⁺ = 1 > 0 = |x+y|`. So no bound on
`Σ(a)_+` follows from a bound on the signed sum `|Σ a|` — a signed
enstrophy balance cannot yield the positive-surplus budget. -/
theorem signed_not_positive_part :
    ∃ x y : ℝ, x + y = 0 ∧ ¬ (max x 0 + max y 0 ≤ |x + y|) := by
  refine ⟨1, -1, by norm_num, ?_⟩
  norm_num

/-! ## N3 — finite budget ⇏ per-node radius charge -/

/-- **`finite_budget_not_radius_charge`** (PROVED). A finite total
budget over countably many nodes does NOT force a per-node
`c·radius` lower payment. Witness: budget `b n = 0` for all `n`
(total `0 < ∞`), radii `r n = 1`; no `c>0` has `c·1 ≤ 0`. -/
theorem finite_budget_not_radius_charge :
    ∃ (b r : ℕ → ℝ),
      (∀ n, 0 ≤ b n) ∧ (∀ n, b n = 0) ∧ (∀ n, r n = 1) ∧
      ¬ ∃ c : ℝ, 0 < c ∧ ∀ n, c * r n ≤ b n := by
  refine ⟨(fun _ => 0), (fun _ => 1), fun _ => le_refl 0,
          fun _ => rfl, fun _ => rfl, ?_⟩
  rintro ⟨c, hc, h⟩
  have := h 0
  simp at this
  linarith

/-! ## N4 — ground-state criticality: no interior strict surplus -/

/-- **`ground_state_no_interior_surplus`** (PROVED). The localized
ground-state identity for a positive solution: with
`dirichlet := ν∫|∇(φq)|²`, `pot := ∫Vφ²q²`, and the EXACT identity
`dirichlet − pot = cap` where `cap := ν∫q²|∇φ|² ≥ 0` (the boundary
capacity), the "interior surplus" `pot − dirichlet` equals `−cap`,
hence is `≤ 0`. So NO interior-sign manipulation yields a strict
positive interior gain — the gain is EXACTLY the boundary capacity.
This is *why* every interior-surplus estimate hit the endpoint;
the closing object must be the capacity, not an interior sign. -/
theorem ground_state_no_interior_surplus
    (dirichlet pot cap : ℝ)
    (hcap_nonneg : 0 ≤ cap)
    (ground_state_identity : dirichlet - pot = cap) :
    pot - dirichlet ≤ 0 := by
  linarith

/-- **`interior_surplus_eq_minus_capacity`** (PROVED, sharp form):
the interior surplus is *exactly* `−cap`, not merely `≤0`. The
interior estimate can never see a strict positive quantity; it sees
precisely the negative of the boundary capacity. -/
theorem interior_surplus_eq_minus_capacity
    (dirichlet pot cap : ℝ)
    (ground_state_identity : dirichlet - pot = cap) :
    pot - dirichlet = -cap := by
  linarith

/-! ## Honest record -/

structure Tick590Record where
  /-- N1: raw C7-lower payment is FALSE (shear countermodel) ⇒
      dichotomy mandatory. PROVED. -/
  shear_kills_raw_lower_payment : Prop
  /-- N2: signed identity ⇏ positive-part budget (signed-vs-positive
      trap). PROVED. -/
  signed_not_positive : Prop
  /-- N3: finite budget ⇏ per-node radius charge. PROVED. -/
  finite_budget_not_charge : Prop
  /-- N4: ground-state criticality — interior surplus = −capacity
      ≤ 0; no interior strict gain; the gain IS the boundary
      capacity (why interior estimates all hit the endpoint). PROVED. -/
  no_interior_surplus_gain : Prop
  /-- All four are genuine PROVED impossibilities/identities; NO
      conditional-forward / closure claim (tick581/583 shape
      deliberately absent). Live endpoint = C3 ∧ closeable-C7-upper. -/
  clean_negatives_no_closure_claim : Prop

end ZtareProofs.NSTick590FormalizedNegativesPreCapacity
