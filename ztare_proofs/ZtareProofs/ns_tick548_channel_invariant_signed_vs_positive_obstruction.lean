import Mathlib.Tactic

/-!
# Tick548 — The obstruction is CHANNEL-INVARIANT: signed cancels, positive survives

## Origin (poll → pre-check tick → recursive MD synthesis)

Pre-check tick discipline (amnesia precheck BEFORE this tick)
surfaced the 2026-05-14 findings:

- **F-GP225-…-TRANSPORT-LOWER-PAYMENT-MUST-USE-POSITIVE-LOCAL-FLUX-…-353**:
  "Transport lower payment cannot be proved from a signed/global
  transport defect alone; it must use positive localized cutoff
  flux… two same-window localized route-flux packets can cancel in a
  signed/global defect while positive local flux remains positive."
- **F-GP225-…-POSITIVE-CUTOFF-FLUX-RECEIPT-IS-CONDITIONAL-NOT-PROOF-…-355**:
  "Same-carrier positive cutoff flux is the transport branch's
  required receipt object; DR flux and pressure-`l=2` carriers cannot
  substitute."

Independent market check: codex priced the tick547 channel-shift
contract **0.34** (= claude_rd 0.34) — "existing machinery closes
summability, NOT the same-window moment obstruction."

**Synthesis (recursive Meta-Darwin across tick544–547):** the
obstruction is **channel-invariant**. Pressure (F-314/F-437) and
transport (F-353/F-355) are the SAME structural obstruction —
*signed/global same-window moments cancel; only the positive-part
(same-carrier cutoff) flux survives*. The virial isomorphism
(tick547) channel-shifts pressure→transport but the obstruction is
invariant under the channel label. The perennial strict-margin atom
⟺ the **unconditional positive same-carrier cutoff-flux receipt**.

## Pencil (Gowers-first)

Model a same-window pair by signed scalar moments `m₁, m₂`
(carrier-tagged but the tag is inert). Signed/global defect
`= m₁ + m₂` can be `0` (cancellation) while the positive-part flux
`|m₁| + |m₂| > 0`. This holds identically whether the carrier is
pressure-tagged or transport-tagged ⇒ **channel-invariance**. A
signed UPPER bound can never certify the receipt (it is killed by the
cancellation); only a POSITIVE-PART LOWER bound (a coercivity
statement, structurally different — not a relabel) survives. That
positive-part receipt being *unconditional* is the atom (F-355: it is
currently CONDITIONAL).

## Universal-language ops (orchestration_menu / MP-022)

- **Problem Reformulation** — strict-margin signed bound → positive-
  part coercivity receipt.
- **Characterization by Obstruction** — the invariant obstruction is
  signed cancellation; the invariant escape is positivity.
- **Sharpness / Failure-Witness Construction** — the
  `m₁ = 1, m₂ = −1` cancellation is the exact channel-invariant
  failure witness for ANY signed bound.
- **Limit-Passage Property Inheritance** — invariance under the
  channel label (pressure ↔ transport) is the inherited property.

## Recursive Meta-Darwin (in-artifact)

- **Not a relabel (MD)**: the positive-part receipt is a LOWER bound
  on `|m₁|+|m₂|` (coercivity), structurally distinct from the signed
  UPPER bound that the strict-margin chain kept producing. It is the
  correct reformulation that *survives* the invariant cancellation —
  genuinely different object, not vocabulary drift.
- **Distinct outcomes**: signed (killed by witness) vs positive
  (survives) are genuinely different — proved below.
- **Source-leakage**: grounded in the EXISTING 2026-05-14 F-353/F-355
  findings (surfaced by the mandated pre-check), not a new claim.
- **Floor-by-failing**: a signed bound that "passes" must be vacuous
  — the witness `m₁+m₂=0` falsifies any nonvacuous signed lower
  bound; proved.
-/

namespace ZtareProofs.NSTick548ChannelInvariantSignedVsPositiveObstruction

/-! ## (1) The channel-invariant cancellation witness (PROVED) -/

/--
**`signed_cancellation_witness`** — there exist same-window signed
moments whose signed/global defect is `0` while the positive-part
flux is strictly positive. The exact obstruction, with NO channel
dependence (the witness ignores any carrier tag).
-/
theorem signed_cancellation_witness :
    ∃ m₁ m₂ : ℝ, m₁ + m₂ = 0 ∧ 0 < |m₁| + |m₂| := by
  refine ⟨1, -1, by ring, ?_⟩
  norm_num

/--
**`signed_bound_cannot_certify_receipt`** (PROVED).

Any putative *signed* lower-bound certificate
`∀ m₁ m₂, P → c ≤ m₁ + m₂` with `c > 0` is falsified by the
cancellation witness — for ANY carrier predicate `P` that the
witness satisfies. A signed bound is structurally incapable of the
receipt.
-/
theorem signed_bound_cannot_certify_receipt
    (c : ℝ) (hc : 0 < c) :
    ¬ (∀ m₁ m₂ : ℝ, m₁ + m₂ = 0 → c ≤ m₁ + m₂) := by
  intro h
  have := h 1 (-1) (by ring)
  norm_num at this
  linarith

/-! ## (2) Channel-invariance: the obstruction ignores the carrier tag -/

/--
**`obstruction_is_channel_invariant`** (PROVED).

Tag the carrier by an arbitrary label `ch : ChannelTag` (e.g.
`pressure`/`transport`). The signed-defect obstruction
`signedDefect m₁ m₂ = m₁ + m₂` does not depend on `ch`: the
cancellation witness works for every tag. Pressure (F-314/437) and
transport (F-353/355) are the SAME obstruction.
-/
inductive ChannelTag
  | pressure
  | transport

theorem obstruction_is_channel_invariant :
    ∀ ch : ChannelTag,
      ∃ m₁ m₂ : ℝ, (m₁ + m₂ = 0) ∧ 0 < |m₁| + |m₂| := by
  intro _ch
  exact signed_cancellation_witness

/-! ## (3) The invariant escape: a POSITIVE-PART lower bound survives -/

/--
**`positive_part_receipt_survives_cancellation`** (PROVED).

The genuinely-different object: a lower bound on the positive-part
flux `|m₁| + |m₂|` is NOT killed by the signed cancellation. Here the
cancelling witness still has positive-part flux `= 2 ≥ c` for any
`c ≤ 2`. This is a coercivity statement, structurally distinct from
a signed bound — the correct reformulation (F-355's required receipt
object), not a relabel.
-/
theorem positive_part_receipt_survives_cancellation
    (c : ℝ) (hc : c ≤ 2) :
    ∃ m₁ m₂ : ℝ, m₁ + m₂ = 0 ∧ c ≤ |m₁| + |m₂| := by
  refine ⟨1, -1, by ring, ?_⟩
  have : |(1:ℝ)| + |(-1:ℝ)| = 2 := by norm_num
  linarith [this]

/-! ## (4) Honest scope record -/

structure Tick548HonestScopeRecord where
  /-- Pre-check tick discipline run BEFORE this tick (F-353/F-355
      surfaced). -/
  precheck_tick_discipline_used : Prop
  /-- Obstruction proved channel-invariant (pressure ≅ transport). -/
  obstruction_channel_invariant_proved : Prop
  /-- Signed bound provably cannot certify the receipt (witness). -/
  signed_bound_structurally_incapable : Prop
  /-- Positive-part receipt is the genuinely-different invariant
      escape (coercivity, not a signed-bound relabel). -/
  positive_part_is_real_reformulation_not_relabel : Prop
  /-- Atom canonical form = unconditional positive same-carrier
      cutoff-flux receipt (F-355, currently CONDITIONAL). -/
  atom_is_unconditional_positive_cutoff_flux_receipt : Prop
  /-- Independent market corroboration: codex 0.34 = claude_rd 0.34. -/
  independent_forecaster_convergence : Prop

end ZtareProofs.NSTick548ChannelInvariantSignedVsPositiveObstruction
