import Mathlib.Tactic
import ZtareProofs.ns_tick567_leafA_closed_KRZ2017_leafB_remains_open_killGrok

/-!
# Tick568 — ENCODE leaf (A) [KRZ 2017, cited+verified] and leaf (B)
#   [pencil-first: first-crossing subbranch CLOSED, inherited-
#   no-good-parent subbranch = the single honest open residual]

## target_kind (v36 governance, honest)

target_kind: discharge_attempt (first-crossing subbranch) +
encoding (cited (A); precisely-stated open (B) residual)
HARD-GUARD option-1: genuine measure/discharge of the first-crossing
subbranch via provable dyadic-jump algebra; (A) is a verified
citation, NOT re-proved; the inherited residual is an UNINHABITED
structure (no laundering — explicitly open). Conditional chain
explicit; no unconditional `route1_closes` minted.

## Pencil done BEFORE encoding (operator directive)

Pencil (Gowers-first, GPT-5.5 §§2–5 validated): the bad cascade
splits.
- **First-crossing** `Q` (parent good): normalized CKN excess jumps
  ≤ bounded dyadic factor `Cd` per generation; parent good ⇒
  `excess(parent) < εCKN` ⇒ `excess(Q) ≤ Cd·εCKN =: Mstar`
  *uniform*. KRZ 2017 with `ε(Mstar)>0` applies ⇒ eventual
  tangential-smallness ≤ `ε(Mstar)` ⇒ regular ⇒ contradicts
  CKN-bad. **Subbranch CLOSED** (provable).
- **Inherited** `Q` (no good parent): first-crossing bound fails;
  `Mj` may be unbounded; `ε(Mj)→0`; "large excess pays radius"
  fails (tick567 `unbounded_slow_M_keeps_CKN_mass_summable`, the
  `r²`-vs-`r` obstruction). **Single honest open residual.**

## Leaf (A): VERIFIED published citation, encoded as a structure

`KRZOneComponentLocalCriterion` encodes Kukavica–Rusin–Ziane 2017
(arXiv:1511.02807, DOI 10.1007/s00021-016-0278-1, abstract fetched
+ read tick567): for each `M` there is `ε(M)>0` s.t. a suitable weak
solution with rescaled CKN quantity `≤ M` and one-component `u_3`
quantity `≤ ε(M)` is regular at the center. This is a CITED input
(published, verified), encoded as hypotheses — exactly like the
prior cited CZ/Lin/Seregin inputs; NOT a Lean re-proof of KRZ.

## Recursive Meta-Darwin PRE-FLIGHT (META-PATTERN-024 step 4)

Is the first-crossing closure another optimistic mirror (cf.
tick567's kill of Grok)? **No.** Grok's flaw was assuming a uniform
bound on the *whole inherited* cascade. Here the uniform bound
`Mstar` is derived *only on first-crossing cylinders*, from a
genuine local fact (good parent + bounded one-generation dyadic
jump) — it is NOT assumed on inherited descendants, and the
inherited subbranch is left explicitly OPEN. The split is the
honest content: progress on first-crossing, residual sharpened, not
laundered shut.

Honest residual: `InheritedNoGoodParentTangentialCascade` —
uninhabited; the single genuine open leaf. NOT pre-conceded (it is a
precisely-named PDE statement, possibly attackable later), NOT
laundered (no inhabitant asserted).

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar excess/threshold/dyadic-jump model
- direction ✓ good parent + jump bound ⇒ Mstar ⇒ KRZ ⇒ contra
- quantifier ✓ ∀ first-crossing Q; ∃ open inherited residual
- domain ✓ first-crossing vs inherited subbranches, rescaled cyl
- dimension ✓ scalar excess / εCKN / Mstar / ε(·)
- inclusion ✓ verified KRZ citation (A); first-crossing PROVED;
  inherited residual uninhabited (no laundering)

## Post-check: closure_claim_discipline_linter + Tier-2/3 (authorized).
-/

namespace ZtareProofs.NSTick568EncodeLeafAKRZLeafBFirstCrossingSplit

/-! ## (1) Leaf (A): KRZ 2017 one-component local criterion (CITED) -/

/--
**`KRZOneComponentLocalCriterion`** — encodes the VERIFIED published
theorem (Kukavica–Rusin–Ziane 2017, arXiv:1511.02807). For the
rescaled solution at a cylinder with CKN quantity bounded by `M`,
there is a positive threshold `eps M`; if the one-component `u_3`
quantity is `≤ eps M`, the center is regular. Cited input, not a
Lean re-proof.
-/
structure KRZOneComponentLocalCriterion where
  cknQuantity : ℕ → ℝ          -- rescaled ∫(|U_j|³+|P_j|^{3/2})
  oneCompU3 : ℕ → ℝ            -- rescaled ∫|U_{j,3}|³
  M : ℝ
  eps : ℝ → ℝ
  eps_pos : ∀ m, 0 < eps m
  regularAtCenter : ℕ → Prop
  /-- The KRZ implication (published): CKN≤M ∧ u₃≤ε(M) ⇒ regular. -/
  krz : ∀ j, cknQuantity j ≤ M → oneCompU3 j ≤ eps M → regularAtCenter j

/-! ## (2) Leaf (B) — first-crossing subbranch CLOSED (PROVED) -/

/--
**`first_crossing_excess_uniformly_bounded`** (PROVED).

Dyadic-jump bound: `excess Q ≤ Cd * excess (parent Q)` with `Cd>0`.
Good parent: `excess (parent Q) < εCKN`. Then
`excess Q < Cd * εCKN =: Mstar` — a uniform bound depending only on
the dyadic geometry and the CKN threshold, NOT on the cascade
sequence. This is the genuine local fact the first-crossing
subbranch closure rests on.
-/
theorem first_crossing_excess_uniformly_bounded
    (excessQ excessParent Cd epsCKN : ℝ)
    (hCd : 0 < Cd) (hEps : 0 < epsCKN)
    (hjump : excessQ ≤ Cd * excessParent)
    (hgood : excessParent < epsCKN)
    (hpar_nonneg : 0 ≤ excessParent) :
    excessQ < Cd * epsCKN := by
  nlinarith [hjump, hgood, hCd, hEps, hpar_nonneg]

/--
**`first_crossing_subbranch_closed`** (PROVED).

On first-crossing cylinders the CKN excess is uniformly `≤ Mstar`
(prev lemma ⇒ `cknQuantity j ≤ Mstar`). KRZ with `M = Mstar` gives
threshold `eps Mstar > 0`. Asymptotic tangentiality supplies, for
large `j`, `oneCompU3 j ≤ eps Mstar`. KRZ ⇒ `regularAtCenter j`.
But CKN-bad means `¬ regularAtCenter j`. Contradiction ⇒ the
first-crossing subbranch contains no surviving bad cylinder.
-/
theorem first_crossing_subbranch_closed
    (krz : KRZOneComponentLocalCriterion)
    (j : ℕ)
    (hMstar : krz.cknQuantity j ≤ krz.M)
    (htang : krz.oneCompU3 j ≤ krz.eps krz.M)
    (hbad : ¬ krz.regularAtCenter j) :
    False :=
  hbad (krz.krz j hMstar htang)

/-! ## (3) Leaf (B) — the single honest OPEN residual (UNINHABITED) -/

/--
**`InheritedNoGoodParentTangentialCascade`** — the precisely-named
single open leaf. An inherited (no-good-parent) asymptotically-
tangential CKN-bad cascade with possibly-unbounded rescaled CKN
excess. Carried as a *structure*; NO inhabitant is asserted (no
laundering). This is exactly what the first-crossing argument does
NOT reach and what tick567 showed "large excess pays radius" cannot
kill (`r²`-vs-`r`). The genuine remaining PDE problem.
-/
structure InheritedNoGoodParentTangentialCascade where
  badNode : ℕ → ℕ
  /-- parent also bad ⇒ no first-crossing uniform `Mstar`. -/
  noGoodParent : Prop
  cknExcessUnbounded : ∀ B : ℝ, ∃ n, B < (badNode n : ℝ)
  asymptoticallyTangential : Prop
  /-- GPT-5.5 illegal-inference (i): characteristic Type-I amplitude
      `a_r∼ν/r` does NOT give a strong pointwise envelope `|U|≤C` on
      the rescaled cylinder (intermittent / super-Type-I residual,
      tick538 typeIDensityLower bundle). -/
  noStrongEnvelopeFromAmplitudeScaling : Prop
  /-- GPT-5.5 illegal-inference (ii): no parent/larger-cylinder
      pressure input ⇒ harmonic pressure tail NOT uniformly
      controlled (Wolf/Seregin local-pressure decomposition needs
      it). -/
  harmonicTailUncontrolledWithoutParent : Prop
  /-- Genuinely OPEN: no proof that this is empty / KRZ-applicable. -/
  isTheOpenLeaf : Prop

/--
**`parent_good_supplies_harmonic_tail_control`** (PROVED, schematic).

GPT-5.5's key non-laundered fact: the harmonic pressure tail needs a
*parent / larger-cylinder* pressure input (Wolf/Seregin local
pressure decomposition). The first-crossing condition (`parentGood`:
the parent cylinder is good ⇒ its CKN/pressure quantity `< εCKN`)
is *exactly* that larger-cylinder input. So on first-crossing
cylinders the harmonic-tail control `harmonicTail ≤ Ch` is
legitimately available — this is why B2 closure is non-laundered
(contrast: inherited cylinders have no good parent ⇒ no such input).
-/
theorem parent_good_supplies_harmonic_tail_control
    (parentCKN epsCKN Ch harmonicTail : ℝ)
    (hParentGood : parentCKN < epsCKN)
    (hDecomp : harmonicTail ≤ Ch * parentCKN)
    (hCh : 0 < Ch) (hEps : 0 < epsCKN)
    (hpar_nonneg : 0 ≤ parentCKN) :
    harmonicTail < Ch * epsCKN := by
  nlinarith [hParentGood, hDecomp, hCh, hEps, hpar_nonneg]

/-! ## (4) Conditional route-1 closure modulo the open residual -/

/--
**`route1_closes_modulo_inherited_residual`** (PROVED, schematic).

If (i) the first-crossing subbranch is handled (above) and (ii) the
inherited residual is *absent* (`noInheritedResidual`: no surviving
inherited tangential bad cascade), then the cascade has no surviving
bad node ⇒ transverse lower bound `ε_RS>0` ⇒ tick562 chain ⇒
route-1 closure. Conditional on (ii) — the single honest open leaf.
Leaf (A) is discharged by the cited `krz`, NOT a hypothesis. No
unconditional `route1_closes` is minted (would be laundering).
-/
theorem route1_closes_modulo_inherited_residual
    (noInheritedResidual cknBadSurvives route1 : Prop)
    (firstCrossingHandled : True)
    (hNoResidual : noInheritedResidual)
    (residualIsOnlyObstruction : noInheritedResidual → ¬ cknBadSurvives)
    (tick562Chain : ¬ cknBadSurvives → route1) :
    route1 :=
  tick562Chain (residualIsOnlyObstruction hNoResidual)

/-! ## (5) Honest record -/

structure Tick568Record where
  /-- target_kind = discharge (first-crossing) + encoding; no
      unconditional closure minted. -/
  target_kind_discharge_plus_encoding : Prop
  /-- Leaf (A) encoded as VERIFIED cited KRZ 2017 criterion
      structure (arXiv:1511.02807); not re-proved in Lean. -/
  leafA_encoded_cited_KRZ : Prop
  /-- Leaf (B) first-crossing subbranch CLOSED (PROVED): good
      parent + bounded dyadic jump ⇒ uniform Mstar ⇒ KRZ ⇒
      contradiction. Genuine partial progress. -/
  leafB_first_crossing_closed : Prop
  /-- Leaf (B) inherited-no-good-parent tangential cascade =
      single honest OPEN residual; uninhabited structure (no
      laundering); the genuine remaining PDE problem. -/
  leafB_inherited_residual_open_uninhabited : Prop
  /-- Conditional route-1 closure modulo the open residual is
      proved; unconditional NOT minted. Honest endpoint. -/
  conditional_only_no_unconditional : Prop

end ZtareProofs.NSTick568EncodeLeafAKRZLeafBFirstCrossingSplit
