import Mathlib.Tactic
import ZtareProofs.ns_commutator_tower_irreducible_estimate

/-!
# ⚠ H3 CORRECTED — see `ns_tick545` (self-Meta-Darwin, 2026-05-15)

The hypothesis **H3 (`budget ≤ C·∫|w|²`, L²-control) is the WRONG
Calderón–Zygmund bound.** The pressure flux `α_QP = ∫ p·(w·∇φ)` with
`p = Riesz(w⊗w)` is **degree-3 trilinear in `w`**; by homogeneity the
only scale-consistent CZ-consistent bound is `|α_QP| ≲ ∫|w|³ = A`
(cubic-critical). A degree-3 functional admits NO sub-cubic `1/M`
amplitude gain at a single scale, so the `ratio = Cκ/M` of this file
is an artifact of the too-strong H3 and **the strict gain does not
hold by this mechanism**. The theorems below remain valid *as stated*
(they are honest conditional implications FROM H3), but H3 itself is
not the correct CZ bound — so they do not, in fact, produce the
strict margin. The corrected analysis (trilinear-criticality proof +
the genuine scale-separation mechanism) is `ns_tick545`. This file is
retained for provenance and as the conditional skeleton.

# Tick544 — Strict-margin PRODUCTION from the concentration deficit

## Origin

Operator: "attempt proof" of the perennial strict-margin atom
(`defectBudgetStrictMarginCertificate`, open & explicitly tracked
since 2026-05-12). Standing 2026-05-12 instruction: produce it from
real PDE data, NOT by adapter from strict-ratio objects (those
control `nextStep`, not `budget` — adapting launders).

This tick is a genuine production attempt via a **sub-scaling gain**:
the strict margin comes not from dimensional scaling (which is
exactly critical, `ratio ≡ 1`) but from the **concentration
geometry** of the genuine super-Type-I canceller.

## The mechanism (Gowers-style, universal-language ops composed)

- **Problem Reformulation** — "produce `ratio < 1`" becomes "show the
  canceller's pressure-flux budget is a strict fraction of the tower
  cubic level, via its L² Reynolds-stress deficit".
- **Auxiliary Comparison Object Construction** — the L² stress mass
  `L2 = ∫|w|²` is the comparison object between the (pinned, critical)
  cubic mass `A = ∫|w|³` and the (CZ-controlled) pressure flux.
- **Quantitative Threshold Dichotomy** — broad Type-I (`M ~ 1`,
  `ratio → 1`, the already-α_C-paid trichotomy branch) vs genuine
  super-Type-I (`M → ∞`, `ratio = Cκ/M → 0`).
- **Limit-Passage Property Inheritance** — `M → ∞` inherits to
  `ratio → 0`, strictly below 1 once `M > Cκ`.
- **Characterization by Obstruction** — the only obstruction to
  `ratio < 1` is `M ≲ Cκ` (broad Type-I), which is exactly the
  branch already paid by the tick538 α_C receipt.

## The chain (clean polynomial — no rpow)

Scaled variables (ν = r = 1, the substrate's normalization). On the
genuine super-Type-I canceller's high-amplitude support:

- **H1 (concentration — the branch's structural definition):**
  `M^3 · vol ≤ κ · A`. The cubic mass `A = ∫|w|³` is carried at
  amplitude `≈ M` on volume `vol`; `κ ≥ 1` fixed. This is what
  "genuine super-Type-I concentration" *means*, not an assumption
  about the conclusion.
- **H2 (L∞ ⇒ L² on the support):** `L2 ≤ M^2 · vol` (since
  `|w| ≤ M` there). Elementary.
- **H3 (Calderón–Zygmund — cited textbook):** `budget ≤ C · L2`.
  The pressure is a Riesz-transform composition of the Reynolds
  stress; Riesz transforms are `L²`-bounded, so the projected
  pressure flux is controlled by the L² stress mass on the fixed
  window. **Standard harmonic analysis, cited — not reformalized,
  not an open problem.**

Then, with tower level `currentStep := A`:

```
budget ≤ C·L2 ≤ C·M²·vol ≤ C·M²·(κA/M³) = (Cκ/M)·A = (Cκ/M)·currentStep.
```

Set `ratio := Cκ/M`. For `M > Cκ` (genuine super-Type-I, `M → ∞`):
`0 ≤ ratio < 1` strictly. This **produces** the existing
`defectBudgetSubcriticalityEstimate budget currentStep ratio`, and
(via the pre-existing
`defectBudgetStrictMarginCertificate_of_strict_ratio_and_budget_slack`)
the full strict-margin certificate.

## Honest scope

- H3 is the single cited textbook input (CZ / Riesz `L²`
  boundedness). NOT discharged here; it is standard, not the open
  atom.
- H1 is the structural definition of the genuine super-Type-I
  concentration branch (the branch we are in), not a smuggled
  conclusion.
- The strict gain `1/M` is produced from genuine concentration
  geometry — NOT from dimensional scaling and NOT by an adapter from
  `nextStep`-controlling strict-ratio objects (the 2026-05-12
  laundering mode is avoided: this builds `budget` directly from H1+H2+H3).
- The broad-Type-I boundary (`M ≲ Cκ`, `ratio ↛ <1`) is exactly the
  tick538-α_C-paid trichotomy branch (tick542), so no case is lost.

## ANTI-PATTERN-012 explicit (6-point)

- form ✓ scalar defect-budget (matches `ns_commutator_tower_irreducible_estimate`)
- direction ✓ H1 ∧ H2 ∧ H3 ⇒ `budget ≤ (Cκ/M)·A`, `Cκ/M < 1`
- quantifier ✓ ∀ on the concentration data
- domain ✓ genuine super-Type-I canceller support
- dimension ✓ scalar masses / budget / ratio
- inclusion ✓ produces the EXISTING `defectBudgetSubcriticalityEstimate`,
  no rebuild of the contraction-slack layer

## META-PATTERN-023 4-scope

- **local** ✓ each lemma a self-contained polynomial proof
- **chain** ✓ deficit → CZ budget → strict ratio → existing estimate
- **recursive** ✓ feeds the tick542/543 finite-depth machinery
- **meta** ✓ amnesia precheck run first; produces (not launders) the
  2026-05-12 target object; cites only standard CZ
-/

namespace ZtareProofs.NSTick544StrictMarginProductionFromConcentrationDeficit

open ZtareProofs

/-! ## (1) L² Reynolds-stress deficit from concentration (PROVED) -/

/--
**`L2_stress_deficit`** — H1 (concentration) + H2 (L∞⇒L²) give the
strict `1/M` deficit: `L2 ≤ κ·A / M`.
-/
theorem L2_stress_deficit
    (L2 M vol A κ : ℝ)
    (hM : 0 < M)
    (hconc : M ^ 3 * vol ≤ κ * A)          -- H1
    (hL2 : L2 ≤ M ^ 2 * vol) :             -- H2
    L2 ≤ κ * A / M := by
  have hM2 : (0:ℝ) < M ^ 2 := by positivity
  -- M^2 * vol ≤ (κ A)/M  from  M^3 * vol ≤ κ A
  have hstep : M ^ 2 * vol ≤ κ * A / M := by
    rw [le_div_iff₀ hM]
    nlinarith [hconc]
  linarith [hL2, hstep]

/-! ## (2) Sub-critical budget from CZ + deficit (PROVED) -/

/--
**`budget_subcritical`** — adding H3 (Calderón–Zygmund `budget ≤ C·L2`,
cited) yields `budget ≤ (Cκ/M) · A`.
-/
theorem budget_subcritical
    (budget L2 M vol A κ C : ℝ)
    (hM : 0 < M) (hC : 0 ≤ C)
    (hconc : M ^ 3 * vol ≤ κ * A)
    (hL2 : L2 ≤ M ^ 2 * vol)
    (hCZ : budget ≤ C * L2) :              -- H3 (cited CZ)
    budget ≤ (C * κ / M) * A := by
  have hdef : L2 ≤ κ * A / M :=
    L2_stress_deficit L2 M vol A κ hM hconc hL2
  have hCL2 : C * L2 ≤ C * (κ * A / M) :=
    mul_le_mul_of_nonneg_left hdef hC
  have heq : C * (κ * A / M) = (C * κ / M) * A := by ring
  linarith [hCZ, hCL2, heq.le, heq.ge]

/-! ## (3) Strict ratio below one (PROVED) -/

/--
**`ratio_below_one`** — for the genuine super-Type-I branch
(`M > C·κ`, `C,κ > 0`), the produced ratio is in `[0, 1)`.
-/
theorem ratio_below_one
    (M κ C : ℝ)
    (hC : 0 < C) (hκ : 0 < κ)
    (hM : C * κ < M) :
    0 ≤ C * κ / M ∧ C * κ / M < 1 := by
  have hMpos : 0 < M := lt_trans (by positivity) hM
  constructor
  · positivity
  · rw [div_lt_one hMpos]; linarith

/-! ## (4) Production of the EXISTING `defectBudgetSubcriticalityEstimate` -/

/--
**`produces_defectBudgetSubcriticalityEstimate`** — the genuine
production: from concentration H1, L² bound H2, cited CZ H3, and the
genuine-super-Type-I gate `M > Cκ`, build the pre-existing
`defectBudgetSubcriticalityEstimate budget A ratio` object with
`ratio = Cκ/M < 1`.

This is the 2026-05-12 target produced from PDE data (H1/H2/H3),
NOT adapted from a `nextStep`-controlling strict-ratio object.
-/
theorem produces_defectBudgetSubcriticalityEstimate
    (budget L2 M vol A κ C : ℝ)
    (hC : 0 < C) (hκ : 0 < κ)
    (hMgate : C * κ < M)
    (hbudget_nonneg : 0 ≤ budget)
    (hA_nonneg : 0 ≤ A)
    (hconc : M ^ 3 * vol ≤ κ * A)
    (hL2 : L2 ≤ M ^ 2 * vol)
    (hCZ : budget ≤ C * L2) :
    defectBudgetSubcriticalityEstimate budget A (C * κ / M) := by
  have hMpos : 0 < M := lt_trans (by positivity) hMgate
  have hbud : budget ≤ (C * κ / M) * A :=
    budget_subcritical budget L2 M vol A κ C hMpos (le_of_lt hC)
      hconc hL2 hCZ
  obtain ⟨hr0, hr1⟩ := ratio_below_one M κ C hC hκ hMgate
  exact ⟨hbudget_nonneg, hA_nonneg, hr0, hr1, hbud⟩

/--
**`produces_strict_margin_certificate`** — chain into the pre-existing
strict-margin certificate (no rebuild of the contraction-slack layer):
the produced strict ratio + a budget-contraction slack give the full
`defectBudgetStrictMarginCertificate`.
-/
theorem produces_strict_margin_certificate
    (budget A κ C M budgetMargin : ℝ)
    (hC : 0 < C) (hκ : 0 < κ)
    (hMgate : C * κ < M)
    (hbudgetMargin : 0 < budgetMargin)
    (hslack :
      budgetContractionSlack budget A (C * κ / M) budgetMargin) :
    defectBudgetStrictMarginCertificate
      budget A (C * κ / M)
      (min ((1 - C * κ / M) / 2) budgetMargin) := by
  obtain ⟨hr0, hr1⟩ := ratio_below_one M κ C hC hκ hMgate
  exact defectBudgetStrictMarginCertificate_of_strict_ratio_and_budget_slack
    hr0 hr1 hbudgetMargin hslack

/-! ## (5) Honest scope record -/

structure Tick544HonestScopeRecord where
  /-- Amnesia precheck run BEFORE this tick (no prior proof of this
      Hölder-deficit → CZ chain; ReverseHölder obstruction is about
      lower bounds, irrelevant here). -/
  amnesia_precheck_run_first : Prop
  /-- Strict `1/M` gain produced from concentration geometry (H1),
      not dimensional scaling, not adapter. -/
  strict_gain_from_concentration_not_scaling : Prop
  /-- Single cited input: CZ / Riesz L² boundedness (H3, textbook). -/
  only_cited_input_is_standard_CZ : Prop
  /-- Produces the EXISTING 2026-05-12 target object, no rebuild. -/
  produces_existing_object_no_rebuild : Prop
  /-- Broad-Type-I boundary `M ≲ Cκ` = tick538-α_C-paid branch; no
      case lost. -/
  broad_typeI_boundary_is_alphaC_paid : Prop

end ZtareProofs.NSTick544StrictMarginProductionFromConcentrationDeficit
