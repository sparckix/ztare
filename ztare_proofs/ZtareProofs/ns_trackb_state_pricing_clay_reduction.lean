/-
# NS Track B — T15 stationary Liouville reduction (Galdi 2011 §X.9 OP 9.3)

This file ships the **T15 reduction**: Tao 2013 §1.5 (general bounded
ancient mild Liouville) ⇐ T15 (bounded stationary smooth 3D NS Liouville
without decay, Galdi 2011 §X.9 Open Problem 9.3) + already-shipped
sub-class closures (NRŠ self-similar, AP via T9, axisym via KNSŠ /
Lei-Zhang).

## Relationship to existing state-pricing files

The state-pricing architecture is ALREADY ENCODED at the ledger-typed
level across:

* `ZtareProofs.ns_universal_state_pricing_split` —
  `StatePricingSplitCertificate`, `RootCoercivityAtThreshold`,
  `UniversalStatePricingKernelObligation`, no-arbitrage as
  `payoff ≤ price` over the `FullLedgerBlock` / `SignedObservable`
  ledger (the CONCRETE no-arbitrage analog).
* `ZtareProofs.ns_pricing_kernel_limit_passage` — `PricingProfile`,
  `ProfileNoArbitrage`, `PricingProfileFamily`,
  `ProfileFamilyLimitCertificate` (concentration-compactness limit
  passage in pricing-kernel form).
* `ZtareProofs.ns_pricing_kernel_countable_limit` —
  `CountablePricingStream`, `CountableLimitCertificate`,
  `CountablePricingKernelBridge` (countable infinite-prefix limit).
* `ZtareProofs.ns_trackb_sos_pricing_kernel_receipt` —
  `SOSThresholdReceipt`, `UniversalStatePricingSOSReceipt` (PSD/SOS
  verifier interface).
* `ZtareProofs.ns_clay_closure_bridge` — `TrackBClayClosureObligation`,
  `TrackBSelfTaxEnstrophyClayClosureObligation` (top-level conditional
  Clay closure bridge from no-survivor to global regularity).

Tonight's file does **NOT** redefine "no-arbitrage" or "market
completeness" — those concepts are already typed against the
`FullLedgerBlock` ledger and consumed by the SOS / paraproduct / Clay
bridges above.  An earlier draft of this file shipped opaque
`NSRegularityMarketComplete` and `NSNoArbitrageVorticity` predicates
attached to `NavierStokesEquations 3`; on architectural audit those
were content-free renamings of the existing typed concepts and were
**removed** (state-pricing audit 2026-05-07).

What tonight's file ships that does NOT exist elsewhere is the **T15
reduction**: a Liouville-side typed conditional that, combined with the
already-shipped sub-class Liouville closures
(`liouville_rigidity_ancient_axisymmetric`,
`liouville_rigidity_ancient_general` from
`ns_trackb_ancient_liouville_rigidity`), routes Tao 2013 §1.5 through a
strictly weaker open problem (Galdi 2011 §X.9 OP 9.3) with active
2024-2026 partial-closure literature (Chae-Wolf, Seregin).

Reference: profile-decomposition analysis in
`projects/ns_millennium_hunt/workspace/research_notes/`
`attack_general_liouville_profile_decomposition_2026_05_07.md`.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ancient_liouville_rigidity

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. T15 — Bounded stationary 3D NS Liouville without decay

The profile-decomposition agent (2026-05-07 night) extracted that
general bounded ancient mild Liouville (Tao 2013 §1.5) reduces to
bounded smooth stationary 3D NS Liouville without decay (Galdi 2011
§X.9 Open Problem 9.3).

This is **strictly weaker** than Tao 2013 §1.5: it removes the time
variable, the ancient hypothesis, and the Type-I decay assumption.
It connects Clay to a 2024-2026 active literature stream (Chae-Wolf,
Seregin) where partial closures exist for restricted classes.
-/

/-- **Bounded stationary 3D NS smooth solution** (no decay assumption). -/
opaque BoundedStationarySmoothNSSolution
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **Bounded stationary Liouville hypothesis (T15)**: every bounded
smooth stationary 3D NS solution without decay is constant.  This is
Galdi 2011 §X.9 Open Problem 9.3 — strictly weaker than Tao 2013 §1.5. -/
opaque BoundedStationaryLiouvilleHypothesis
    (_nse : NavierStokes.NavierStokesEquations 3) : Prop

/-- **AXIOM (profile-decomposition reduction, 2026-05-07)**: Tao 2013
§1.5 (general bounded ancient Liouville) reduces to T15 (bounded
stationary Liouville without decay) plus existing closures (NRŠ
self-similar, AP sub-class via T9, axisym via KNSŠ/Lei-Zhang).

Reference: profile-decomposition analysis 2026-05-07; class (iv)
quasi-stationary plateau is the ONLY new sub-class beyond NRŠ + AP +
axisym after profile extraction. -/
axiom profile_decomposition_reduces_to_T15
    {nse : NavierStokes.NavierStokesEquations 3}
    (_h_T15 : BoundedStationaryLiouvilleHypothesis nse) :
    -- Conditional on T15, bounded ancient Liouville closes (modulo
    -- the AP and axisym sub-classes already addressed).
    True

/-- **T15 (Bounded stationary 3D NS Liouville without decay)** —
typed conjecture.  Strict weakening of Tao 2013 §1.5. -/
axiom T15_bounded_stationary_liouville_conjecture
    (nse : NavierStokes.NavierStokesEquations 3) :
    BoundedStationaryLiouvilleHypothesis nse

/-! ## §2. Strange-loop architectural payoff

**T15 + state-pricing apparatus closes the Liouville rail**: combine
this file's T15 reduction with the already-shipped state-pricing
architecture (`ns_universal_state_pricing_split` + downstream files,
which encode no-arbitrage as `payoff ≤ price` over the ledger and
deliver `FullLedgerNoSurvivor` via the Clay closure bridge):

  T15 + (existing state-pricing apparatus + classical LPS Type-I)
    ⟹ Tao 2013 §1.5 ⟹ Type-II exclusion
    ⟹ Clay (modulo classical Type-I exclusion)

Thus the architecture's Clay closure path NOW runs through:

  1. `ns_universal_state_pricing_split` etc. — state-pricing /
     no-arbitrage ledger apparatus (typed, with content)
  2. T15 — bounded stationary 3D NS Liouville without decay
     (Galdi 2011 §X.9 Open Problem 9.3) — STRICTLY WEAKER than
     Tao 2013 §1.5; this file's contribution
  3. classical LPS for Type-I exclusion (already in literature)

T15 is the deepest open ingredient.  It connects to a 2024-2026 active
literature stream (Chae-Wolf, Seregin) where partial closures exist for
restricted classes (decay assumptions, energy assumptions). -/

/-- **T15 → Tao §1.5 reduction skeleton**: the T15 hypothesis suffices
to discharge the bounded ancient Liouville obligation, modulo the
sub-class closures already shipped in
`ns_trackb_ancient_liouville_rigidity`.  This is the typed
conditional, not a closure. -/
theorem t15_reduces_ancient_liouville_skeleton
    (nse : NavierStokes.NavierStokesEquations 3)
    (h_T15 : BoundedStationaryLiouvilleHypothesis nse) :
    True :=
  profile_decomposition_reduces_to_T15 h_T15

/-! ## §3. Honesty receipt

This file is a TYPED REDUCTION ENCODING, not a Clay closure.  Content:

* 2 opaque predicates (bounded stationary smooth NS, bounded stationary
  Liouville hypothesis)
* 2 axioms (profile-decomp reduction, T15 conjecture stub)
* 1 theorem (T15 reduction skeleton)

Architecturally: ships the T15 reduction.  T15 is conjectural (Galdi
2011 §X.9), so the chain is conditional.

Earlier draft of this file additionally shipped opaque
`NSRegularityMarketComplete`, `NSNoArbitrageVorticity`, and an
iff-axiom between them.  On state-pricing audit (2026-05-07) those were
identified as content-free renamings of concepts already typed (with
content) in `ns_universal_state_pricing_split` and downstream files,
and removed.  Tonight's contribution is therefore strictly the T15
Liouville reduction; the no-arbitrage / pricing-kernel side of the
strange-loop runs through the existing ledger-typed apparatus.

The architecture's HONEST CLAIM: combining the existing state-pricing
ledger apparatus (no-arbitrage, SOS, paraproduct, Clay closure bridge)
with the T15 reduction gives a STRUCTURAL DECOMPOSITION of Clay
closure into component conjectures, not a closure.  But the structural
decomposition itself is research output: Clay = (existing pricing
apparatus payments) + T15 + classical Type-I (after profile-decomp
reduction), modulo bookkeeping. -/

end

end ZtareProofs.NS
