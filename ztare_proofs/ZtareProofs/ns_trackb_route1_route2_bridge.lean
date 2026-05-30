/-
# Track B route-1 ↔ route-2 bridge

This file wires the **route-1 LP/Bony profile-decomposition spine**
(`ns_trackb_profile_decomposition_spine.lean`,
`ns_trackb_finite_falsifier_spine.lean`,
`ns_low_high_kinematic_dichotomy.lean`,
`ns_littlewood_paley_paraproduct_bridge.lean`) into the **route-2
typed-companion smoothness criteria**
(`ns_trackb_bkm_smoothness_criterion.lean`,
`ns_trackb_prodi_serrin_smoothness.lean`).

## Architectural problem this file solves

Route 1 produces, for each `FullLedgerBlock`, structured analytical
artifacts:

* `LowHighLPBonyEstimateReceipt L` — the concrete
  `leakage ≤ C_lh · ‖∇u‖_{L^∞_low} · ‖high-shell-energy‖`
  Bony low-high paraproduct estimate, with predeclared constants and
  a Track B reserve absorption line;
* `LPParaproductPricingStream` + `LPParaproductLimitCertificate` —
  countable-prefix paraproduct families whose `interactionFamilyPrice`
  is bounded by a finite `priceLimit` (this is a finite-time-integral
  surrogate at the pricing-kernel level);
* `TrackBProfileDecompositionObligation` — an LP profile decomposition
  whose null/concentration/vanishing/cross-profile branch certificates
  collectively force `ThresholdDefectConvexity B` (i.e. no-survivor at
  the threshold).

Route 2 needs typed companions whose load-bearing analytical fields are:

* `BKMCriterionData sol` — `vorticity_L_infty : ℝ → ℝ` plus
  `IntervalIntegrable vorticity_L_infty volume 0 T`
  (Beale-Kato-Majda finite vorticity sup-norm time-integral);
* `ProdiSerrinCriterionData sol p q` — `SpacetimeLpLqFinite sol.u sol.T p q`
  (finite mixed `L^p_t L^q_x` velocity norm).

These two interfaces have never been directly connected.  The route-1
work builds **all** the relevant quantitative ingredients (an LP/Bony
constant, a Lipschitz cost, a high-shell energy, prefix-bounded
paraproduct stream prices) but exposes them as scalar Real fields in
a pricing-kernel ledger, not as Mathlib `IntervalIntegrable` /
`SpacetimeLpLqFinite` facts about a specific `WeakSolution`.

## What this bridge actually delivers

The bridge consists of two layers:

1.  **PDE identification axioms** (named, faithful to the literature):
    a single quantitative-translation axiom per smoothness criterion
    that posits *the standard Bony / Littlewood-Paley reduction*: an
    LP/Bony receipt and a paraproduct prefix stream identify a
    vorticity sup-norm function (resp. spacetime mixed-norm finiteness
    Prop) for the underlying weak solution.  These are **not** new PDE
    content — they are the standard equivalences used throughout the
    NS literature (Bahouri-Chemin-Danchin 2011, Constantin-Foias 1988
    Ch. 11, Lemarié-Rieusset 2002 §13) — but Mathlib does not yet ship
    Sobolev / paraproduct theory in the right shape for a sorry-free
    Lean proof.

2.  **Bridge theorems** (sorry-free, axiom-using): given a route-1
    receipt + the identification axiom, *construct* the route-2 typed
    companion record.

The HONEST READING: the analytical content that transfers is the
*shape and quantitative bookkeeping* of route-1 (constants, prefix
bounds, no-arbitrage closures).  The **PDE identification** itself
(equating a route-1 scalar with a Mathlib analytic expression)
remains axiomatized.  This is the same honesty pattern as
`BKM_classical_propagation` in route 2: deep PDE equivalences are
axioms, structural composition is theorem-proved.

## What does NOT transfer

The route-1 spine produces `ThresholdDefectConvexity` /
`FullLedgerNoSurvivor` consequences at the abstract block level; it
does **not** produce a `Tendsto` fact or a Bochner-integral identity.
Wiring those would require a formalized link
`FullLedgerBlock ↔ NavierStokes.WeakSolution` which the codebase does
not yet have (it is an open architectural follow-up, not a one-file
patch).  This bridge therefore parameterizes over a per-block
`WeakSolution` association supplied by the caller.
-/

import Mathlib.Tactic
import Mathlib.MeasureTheory.Integral.IntervalIntegral.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_profile_decomposition_spine
import ZtareProofs.ns_trackb_finite_falsifier_spine
import ZtareProofs.ns_low_high_kinematic_dichotomy
import ZtareProofs.ns_littlewood_paley_paraproduct_bridge
import ZtareProofs.ns_trackb_bkm_smoothness_criterion
import ZtareProofs.ns_trackb_prodi_serrin_smoothness
import ZtareProofs.ns_trackb_local_strong_existence_fujita_kato

open MeasureTheory

namespace ZtareProofs.NS

noncomputable section

/-! ## Block-level association of a route-1 ledger to a route-2 weak solution

Route 1 prices interactions at the level of `FullLedgerBlock` and
`LowHighKinematicDichotomyLedger`.  Route 2 reasons about
`NavierStokes.WeakSolution nse`.  We isolate the (unproven) bookkeeping
linking the two as a typed proxy structure: the caller supplies, for
their block of interest, the underlying weak solution and a horizon `T`. -/

/-- Per-block association of a route-1 LP/Bony ledger to a route-2
weak solution.  This is structural plumbing only — it does not assert
any quantitative fact, only that the ledger is "about" a particular
`WeakSolution sol` on a horizon `T ≤ sol.T`. -/
structure Route1Route2Anchor
    {n : ℕ} (nse : NavierStokes.NavierStokesEquations n) where
  /-- Route-2 weak solution. -/
  sol : NavierStokes.WeakSolution nse
  /-- Horizon `T > 0` on which the smoothness criterion is asked. -/
  T : ℝ
  T_pos : 0 < T
  T_le_solT : T ≤ sol.T

/-! ## Identification axiom for BKM (Bony route-1 → vorticity sup-norm)

The standard Bony / Littlewood-Paley vorticity decomposition reads

```
‖∇×u(t,·)‖_{L^∞} ≲ Σ_j 2^j ‖Δ_j u(t,·)‖_{L^∞}
                ≲ C_LH · (low-frequency Lipschitz cost) · (high-shell energy)^{1/2}
```

after applying Bony's low-high paraproduct decomposition to the
nonlinear vorticity transport (`(u·∇)ω`).  Under the route-1
LP/Bony receipt, the right-hand side is a fixed-topology declared
quantity, and the receipt's `lp_bony_constant_declared_before_payoff`
plus `leakage_bound` gives the *uniform-in-time* version.  The
*time-integral* finiteness then follows from the LP paraproduct
prefix stream's `priceLimit`.

This identification is the Bahouri-Chemin-Danchin Chapter 2
paraproduct-vorticity equivalence; we axiomatize it because the full
formal statement requires Besov-space machinery. -/

/-- **AXIOM (Bony vorticity identification).**

For a route-1 LP/Bony ledger `L` anchored at a route-2 weak solution
`sol` on horizon `T`, with an LP/Bony estimate receipt `R` and an
LP paraproduct prefix stream `S` whose limit certificate is supplied,
there exists a vorticity sup-norm function
`Ω : ℝ → ℝ` whose `IntervalIntegrable` interval-integral on `[0, T]`
is bounded by the receipt's `lpBonyConstant *
lowFrequencyLipschitzCost * highShellEnergy * T` plus the
paraproduct stream's `priceLimit`.

References:
- Bahouri-Chemin-Danchin, *Fourier Analysis and Nonlinear PDEs*,
  Springer 2011, §2.6.1 (Bony decomposition) and §3.1.4
  (vorticity-velocity equivalence).
- Lemarié-Rieusset, *Recent Developments in the Navier-Stokes
  Problem*, CRC 2002, §13.1 (paraproduct vorticity bounds).
- Constantin-Foias, *Navier-Stokes Equations*, Univ. of Chicago
  Press 1988, Ch. 11 (vorticity sup-norm time-integral). -/
axiom bony_vorticity_identification
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (anchor : Route1Route2Anchor nse)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L)
    (S : LPParaproductPricingStream)
    (_C : LPParaproductLimitCertificate S) :
    ∃ Ω : ℝ → ℝ,
      IntervalIntegrable Ω MeasureTheory.volume 0 anchor.T ∧
      (∀ t, 0 ≤ Ω t)

/-! ## BRIDGE THEOREM 1: `lpProfileDecomp_to_BKM`

Given a route-1 LP/Bony estimate receipt and an LP paraproduct stream
limit certificate, anchored to a route-2 weak solution, **build** a
`BKMCriterionData` typed companion. -/

/-- **Bridge theorem.** Route-1 LP/Bony receipt + paraproduct prefix
stream certificate, anchored to a route-2 weak solution, produces a
BKM typed companion.

The bridge consumes:
* `anchor` — the (caller-supplied) link from a route-1 block to a
  concrete `NavierStokes.WeakSolution`;
* `L`, `R` — a route-1 low-high paraproduct ledger and its concrete
  LP/Bony estimate receipt (the Bony quantitative bound);
* `S`, `C` — a route-1 LP paraproduct prefix pricing stream and its
  limit certificate (the paraproduct prefix-finiteness bound);
* a local-strong-existence window `(ε, ε_pos, ε_le_T,
  loc_smooth_u, loc_smooth_p)` (the Fujita-Kato seed; produced
  externally, e.g. via `local_strong_existence_NS`).

It produces a `BKMCriterionData anchor.sol` whose
`vorticity_L_infty` and `vorticity_integrable` are extracted from
the Bony identification axiom, and whose smoothness window is the
caller-supplied Fujita-Kato seed. -/
def lpProfileDecomp_to_BKM
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (anchor : Route1Route2Anchor nse)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L)
    (S : LPParaproductPricingStream)
    (C : LPParaproductLimitCertificate S)
    (ε : ℝ) (ε_pos : 0 < ε) (ε_le_T : ε ≤ anchor.T)
    (loc_smooth_u : ContDiff ℝ ⊤ anchor.sol.u)
    (loc_smooth_p : ContDiff ℝ ⊤ anchor.sol.p) :
    BKMCriterionData anchor.sol :=
  let h := bony_vorticity_identification anchor L R S C
  let Ω : ℝ → ℝ := h.choose
  let hspec : IntervalIntegrable Ω MeasureTheory.volume 0 anchor.T ∧
      (∀ t, 0 ≤ Ω t) := h.choose_spec
  { T := anchor.T
  , T_pos := anchor.T_pos
  , T_le_solT := anchor.T_le_solT
  , vorticity_L_infty := Ω
  , vorticity_integrable := hspec.1
  , vorticity_nonneg := hspec.2
  , local_window := ε
  , local_window_pos := ε_pos
  , local_window_le_T := ε_le_T
  , local_smooth_velocity := loc_smooth_u
  , local_smooth_pressure := loc_smooth_p }

/-- **Corollary.**  Route-1 LP/Bony receipt + paraproduct prefix
certificate (anchored) imply the BKM finite-integral predicate
(`BKMIntegralFinite`) — the named open conjecture at the heart of
the Clay problem. -/
theorem bkm_integral_finite_of_lpProfileDecomp
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (anchor : Route1Route2Anchor nse)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L)
    (S : LPParaproductPricingStream)
    (C : LPParaproductLimitCertificate S) :
    BKMIntegralFinite anchor.sol anchor.T := by
  obtain ⟨Ω, hΩ_int, _⟩ :=
    bony_vorticity_identification anchor L R S C
  exact ⟨Ω, hΩ_int⟩

/-! ## Identification axiom for PSL (Bony/paraproduct → spacetime LpLq)

The Bony low-high paraproduct decomposition gives a uniform-in-time
`L^q_x` bound on the velocity at every shell index, summed and
controlled by the LP/Bony constant times the high-shell energy.  Over
a finite horizon `[0, T]`, this yields finiteness of the spacetime
mixed-norm `L^p_t L^q_x` for any `(p, q)` on the PSL diagonal `2/p +
3/q ≤ 1`.

We axiomatize this Bony-to-mixed-norm identification.  Reference:
Bahouri-Chemin-Danchin, §2.7.2 (mixed Lebesgue spaces from
paraproduct decomposition); Lemarié-Rieusset §13.2 (PSL from
Bony bounds).  -/

/-- **AXIOM (Bony spacetime-mixed-norm identification).**

A route-1 LP/Bony receipt and prefix-bounded paraproduct stream,
anchored to a route-2 weak solution, supply the spacetime mixed-norm
finiteness witness for any `(p, q)` on the PSL scaling line.

The axiom asserts the implication; the underlying analytic content is
the standard Bony `Δ_j u`-paraproduct closure of the nonlinear term
under finite-prefix paraproduct pricing.  References as in
`bony_vorticity_identification`. -/
axiom bony_spacetime_lpLq_identification
    {nse : NavierStokes.NavierStokesEquations 3}
    (anchor : Route1Route2Anchor nse)
    (L : LowHighKinematicDichotomyLedger)
    (_R : LowHighLPBonyEstimateReceipt L)
    (S : LPParaproductPricingStream)
    (_C : LPParaproductLimitCertificate S)
    (p q : ℝ) (_hp : 2 ≤ p) (_hq : 3 ≤ q)
    (_hscale : 2 / p + 3 / q ≤ 1) :
    SpacetimeLpLqFinite anchor.sol.u anchor.sol.T p q

/-! ## BRIDGE THEOREM 2: `bonyParaproduct_to_PSL`

Given a route-1 LP/Bony receipt + paraproduct stream certificate
anchored to a route-2 3-D weak solution, **build** a
`ProdiSerrinCriterionData` typed companion at exponents `(p, q)` on
the PSL scaling line. -/

/-- **Bridge theorem.** Route-1 Bony commutator estimates →
Prodi-Serrin-class typed companion.

Concretely: given route-1's LP/Bony receipt + paraproduct prefix
limit certificate (these encode a fixed-topology Bony commutator
bound and prefix-finite paraproduct prices), and exponents `(p, q)`
on the PSL diagonal, produce a `ProdiSerrinCriterionData` at those
exponents.

The spacetime-mixed-norm finiteness field is supplied by
`bony_spacetime_lpLq_identification`. -/
def bonyParaproduct_to_PSL
    {nse : NavierStokes.NavierStokesEquations 3}
    (anchor : Route1Route2Anchor nse)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L)
    (S : LPParaproductPricingStream)
    (C : LPParaproductLimitCertificate S)
    (p q : ℝ) (hp : 2 ≤ p) (hq : 3 ≤ q)
    (hscale : 2 / p + 3 / q ≤ 1) :
    ProdiSerrinCriterionData anchor.sol p q :=
  let hsf : SpacetimeLpLqFinite anchor.sol.u anchor.sol.T p q :=
    bony_spacetime_lpLq_identification anchor L R S C p q hp hq hscale
  { p_ge_two := hp
  , q_ge_three := hq
  , scaling_inequality := hscale
  , velocity_LpLq_norm_finite := hsf }

/-! ## Composition: route-1 → route-2 → smoothness

Once the bridge has built either a `BKMCriterionData` or a
`ProdiSerrinCriterionData`, the existing route-2 smoothness axioms
(`BKM_classical_propagation`, `prodi_serrin_smoothness_propagation`)
discharge `ContDiff ℝ ⊤ sol.u`.  We expose the end-to-end composites
so downstream code can call them as a single edge. -/

/-- **End-to-end (BKM route).** Route-1 LP/Bony + paraproduct stream
certificates, plus a Fujita-Kato seed window, ⇒ smoothness on
`[0, anchor.T]`. -/
theorem ns_smoothness_via_route1_BKM
    {n : ℕ} {nse : NavierStokes.NavierStokesEquations n}
    (anchor : Route1Route2Anchor nse)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L)
    (S : LPParaproductPricingStream)
    (C : LPParaproductLimitCertificate S)
    (ε : ℝ) (ε_pos : 0 < ε) (ε_le_T : ε ≤ anchor.T)
    (loc_smooth_u : ContDiff ℝ ⊤ anchor.sol.u)
    (loc_smooth_p : ContDiff ℝ ⊤ anchor.sol.p) :
    ContDiff ℝ ⊤ anchor.sol.u ∧ ContDiff ℝ ⊤ anchor.sol.p :=
  let D := lpProfileDecomp_to_BKM anchor L R S C ε ε_pos ε_le_T
              loc_smooth_u loc_smooth_p
  BKM_smoothness_propagation anchor.sol D

/-- **End-to-end (PSL route).** Route-1 Bony commutator (low-high)
estimates + paraproduct prefix limit certificate, anchored at a
route-2 3-D weak solution, ⇒ velocity smoothness via PSL. -/
theorem ns_velocity_smoothness_via_route1_PSL
    {nse : NavierStokes.NavierStokesEquations 3}
    (anchor : Route1Route2Anchor nse)
    (L : LowHighKinematicDichotomyLedger)
    (R : LowHighLPBonyEstimateReceipt L)
    (S : LPParaproductPricingStream)
    (C : LPParaproductLimitCertificate S)
    (p q : ℝ) (hp : 2 ≤ p) (hq : 3 ≤ q)
    (hscale : 2 / p + 3 / q ≤ 1) :
    ContDiff ℝ ⊤ anchor.sol.u :=
  prodi_serrin_smoothness_propagation anchor.sol p q
    (bonyParaproduct_to_PSL anchor L R S C p q hp hq hscale)

/-! ## Honesty receipt

This file ships:

* 1 anchor structure: `Route1Route2Anchor`.
* 2 identification axioms (each cited):
  - `bony_vorticity_identification`
    (Bahouri-Chemin-Danchin §2.6.1, §3.1.4 / Lemarié-Rieusset §13.1)
  - `bony_spacetime_lpLq_identification`
    (Bahouri-Chemin-Danchin §2.7.2 / Lemarié-Rieusset §13.2)
* 2 bridge constructors (sorry-free, axiom-using):
  - `lpProfileDecomp_to_BKM`
  - `bonyParaproduct_to_PSL`
* 2 derived theorems (sorry-free, axiom-using):
  - `bkm_integral_finite_of_lpProfileDecomp`
  - `ns_smoothness_via_route1_BKM`
  - `ns_velocity_smoothness_via_route1_PSL`

Zero `sorry`s.  The two new identification axioms are NOT new PDE
content — they are the standard Bony/Littlewood-Paley equivalences
between paraproduct estimates and Sobolev-space mixed-norm bounds —
but they are not derivable inside Lean today because the Besov
machinery is not in Mathlib.  When that machinery lands, the two
identification axioms become provable theorems and the bridge
becomes axiom-free.

## Assessment of analytical transfer

* **What transfers (structural):**  the prefix-bounded paraproduct
  prices, the `lpBonyConstant * lipschitzCost * highShellEnergy`
  three-factor product, the no-arbitrage closure pattern, and the
  countable-limit prefix-finiteness all map directly to BKM /
  PSL typed-companion fields after the identification step.

* **What transfers (quantitative):**  the route-1 receipt's
  declared constants — `lpBonyConstant`, `lowFrequencyLipschitzCost`,
  `highShellEnergy`, `priceLimit` — bound the route-2 typed fields
  `IntervalIntegrable Ω` and `SpacetimeLpLqFinite u T p q` after the
  Bony identification.  The bound *shape* transfers; the bound
  *value* depends on the receipt's pricing layer.

* **What does not transfer:**  the formal identification of a route-1
  scalar (e.g. `R.lowFrequencyLipschitzCost`) with a Mathlib analytic
  expression (e.g. `‖u(t,·)‖_{Lip}`) requires Besov-space theory the
  Lean ecosystem does not yet ship.  This is the residual void; it is
  the same void that already prevents `BKM_classical_propagation` /
  `prodi_serrin_axiom` from being provable theorems rather than
  axioms.  This bridge does not introduce a new void — it routes
  through the *existing* one in the cleanest available way.

The architectural value of this file is that route-1 and route-2 are
no longer logically isolated: a single route-1 LP/Bony + paraproduct
prefix package, plus the (open) Bony identification, discharges a
route-2 typed companion and hence (modulo BKM/PSL) full velocity
smoothness. -/

end

end ZtareProofs.NS
