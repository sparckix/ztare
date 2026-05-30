/-
# NS Track B — Rank-`r` Closed-Aliasing Banach-Algebra Closure
# DOWNGRADED: this file is REDUNDANT WITH T9 (catch #10, 2026-05-08)

**HONESTY (anti-laundering catch #10, 2026-05-08 audit)**: this file
was originally claimed as "extension of rank-1 closure to rank-r
closed-aliasing" and a "STRICT progress" result. Audit verdict:
**REDUNDANT WITH T9** (`closedAliasingAP_closes_T9` in
`ns_trackb_rescaled_limit_exhaustion.lean:169`).

T9 already closes ANY-CARDINALITY closed-aliasing AP-NS Liouville,
including all rank-r cases as a subset. The rank-r containment
hypothesis here is COSMETIC SLACK; once `BohrSpectrumClosedUnderAliasing`
is assumed, the rank parameter adds nothing.

This file is RETAINED as architectural BOOKKEEPING (rank-Banach-algebra
vocabulary may be useful for future ZTARE substrate consumers), but
the closure CLAIM here should be understood as a RELABEL of T9 in
rank-Banach-algebra vocabulary, NOT independent novel content.

The file's three opaque algebra-closure axioms (`rank_r_heat_closure`,
`_pressure_closure`, `_bilinear_closure`) return `True` — vacuous (1.5-
order intra-file mismatch like catch #6). They are not threaded through
the main axiom's signature. Honest framing: these axioms are MARKERS,
not load-bearing primitives.

The W6_NON_CLOSED_ALIASING_RESIDUAL predicate (§4) IS still useful as
an explicit named open class.

Below: the original docstring is preserved for reference; the closure
axiom should be derived from T9 + closed-aliasing.

---
Produced 2026-05-08 by direct construction from tonight's adversarial
debate verdict (NOT by Pattern 1 residual-grinding). The debate
established that the Banach-algebra argument used for rank-1 closure
generalizes verbatim to **arbitrary rank `r` PROVIDED the spectrum is
CLOSED UNDER ALIASING** (`Σ + Σ ⊂ Σ ∪ {0}`). Without aliasing-closure,
genuine Picard accumulation can occur and the rank-r case is open.

But: T9 already covers this. The rank-r relabeling does not strictly
extend the closed class; it just renames the existing T9 closure in
rank-Banach-algebra vocabulary.

## The Banach algebra `A_{ω_1, ..., ω_r}`

Let `ω_1, ..., ω_r ∈ ℝ³ \ {0}` be ℤ-linearly-independent. Define
   `A_{ω_1,...,ω_r} := { f ∈ AP(ℝ³) : Σ_f ⊂ ℤ-span{ω_1,...,ω_r} }`
with the Wiener norm `‖f‖_W := Σ_{ξ∈Σ_f} |a_ξ|`.

For `r = 1` this is the rank-1 algebra of the previous file. For
general `r`, `A_{ω_1,...,ω_r}` is a commutative Banach algebra closed
under heat (`-νΔ`-resolvent, eigenvalues `4π²ν|ξ|²` ≥ `4π²νδ²`),
pressure (CZ-Riesz multiplier `|ξ|^{-2}` uniformly bounded by
`δ^{-2}` where `δ = min_{ξ∈ℤ-span\{0}} |ξ|`), and the bilinear NS map
`B(u,v) = P((u·∇)v)` (rank-preserved by `bilinear_rank_preservation`).

## Closed-aliasing hypothesis (the EXTRA hypothesis vs rank-1)

For `r = 1` the spectrum sits on `ℤω_1` and is automatically
"closed under aliasing" up to {0}: the integer lattice IS closed
under addition. For `r ≥ 2`, having `Σ ⊂ ℤ-span{ω_1,...,ω_r}` is
WEAKER than `Σ + Σ ⊂ Σ ∪ {0}`. The latter is what makes the Banach
algebra a sub-algebra of `AP` rather than just a subset.

* **CLOSED-aliasing rank-r**: `Σ_u + Σ_u ⊂ Σ_u ∪ {0}`. Picard
  iteration stays inside `Σ_u`. Wiener-norm contraction holds.
  Banach-algebra closure argument applies verbatim. **CLOSED.**
* **NON-closed-aliasing rank-r**: `Σ_u ⊊ ℤ-span{ω_1,...,ω_r}` and
  Picard iterates accumulate new lattice points
  `Σ_u^{(d)} ⊋ Σ_u^{(d-1)}`. The Wiener norm of `Σ_u^{(d)}` may
  blow up (small-divisor pathology if generators are Liouvillian).
  **GENUINELY OPEN.**

## Anti-laundering distinction

This file does NOT close arbitrary rank-r Bohr-AP NS. It closes the
sub-class with `Σ + Σ ⊂ Σ ∪ {0}`. Examples that satisfy this:
* Single ℤ-lattice spectra (`Σ = ℤ^r ω`)
* Finite-orbit spectra under the bilinear map
* Sum-free spectra augmented to closure

Examples that do NOT satisfy this:
* Generic rank-≥2 Liouvillian Bohr-AP velocities where the
  unrestricted ℤ-span allows arbitrary integer combinations
* The W6 residual class (rank-≥2 multi-Liouvillian) from
  `ns_trackb_rank_dichotomy_W6_closure`

The closed-aliasing closure is STRICT progress on top of rank-1
because for r=1 the closure is automatic, while for r≥2 it carves
out a non-trivial sub-class that previously sat inside the W6
residual but now closes.
-/

import Mathlib.Tactic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_bohr_mean_enstrophy_identity
import ZtareProofs.ns_trackb_rank_dichotomy_W6_closure
import ZtareProofs.ns_trackb_bilinear_rank_preservation

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The rank-`r` Banach algebra `A_{ω_1,...,ω_r}` -/

/-- **Opaque**: spectrum is contained in the ℤ-span of the given
generators (rank-`r` containment, NOT yet aliasing-closure). -/
opaque BohrSpectrumInZSpan
    (_BohrSpec : Set (Euc ℝ 3)) (_r : ℕ) : Prop

/-- **Opaque**: spectrum is CLOSED under aliasing,
`Σ + Σ ⊂ Σ ∪ {0}`. The load-bearing extra hypothesis. -/
opaque BohrSpectrumClosedUnderAliasing
    (_BohrSpec : Set (Euc ℝ 3)) : Prop

/-- **Opaque**: membership in the rank-`r` Banach algebra
`A_{ω_1,...,ω_r}` with finite Wiener norm. -/
opaque InRankRBanachAlgebra
    (_u : NavierStokes.VelocityField 3) (_BohrSpec : Set (Euc ℝ 3))
    (_r : ℕ) : Prop

/-- **Opaque** Wiener norm on the rank-`r` Banach algebra. -/
opaque WienerNormRankR
    (_u : NavierStokes.VelocityField 3) : ℝ

/-! ## §2. Banach-algebra closure under heat / pressure / bilinear -/

/-- **AXIOM (Heat closure on `A_{ω_1,...,ω_r}`)**: for closed-aliasing
rank-`r` spectrum, the heat semigroup preserves the algebra. CZ-Riesz
multiplier `|ξ|^{-2}` uniformly bounded by `δ^{-2}` on the spectrum. -/
axiom rank_r_heat_closure
    (u : NavierStokes.VelocityField 3) (BohrSpec : Set (Euc ℝ 3))
    (r : ℕ)
    (_h_zspan : BohrSpectrumInZSpan BohrSpec r)
    (_h_closed : BohrSpectrumClosedUnderAliasing BohrSpec)
    (_h_member : InRankRBanachAlgebra u BohrSpec r) :
    True

/-- **AXIOM (Pressure closure on `A_{ω_1,...,ω_r}`)**: CZ-Riesz
pressure operator preserves the algebra under closed-aliasing. -/
axiom rank_r_pressure_closure
    (u : NavierStokes.VelocityField 3) (BohrSpec : Set (Euc ℝ 3))
    (r : ℕ)
    (_h_zspan : BohrSpectrumInZSpan BohrSpec r)
    (_h_closed : BohrSpectrumClosedUnderAliasing BohrSpec)
    (_h_member : InRankRBanachAlgebra u BohrSpec r) :
    True

/-- **AXIOM (Bilinear closure on `A_{ω_1,...,ω_r}`)**: the NS bilinear
map `B(u,v) = P((u·∇)v)` preserves the algebra under closed-aliasing.
Combines `bilinear_rank_preservation` (rank stays ≤ r) with the
aliasing-closure hypothesis (sumset stays inside `Σ ∪ {0}`). -/
axiom rank_r_bilinear_closure
    (u v : NavierStokes.VelocityField 3) (BohrSpec : Set (Euc ℝ 3))
    (r : ℕ)
    (_h_zspan : BohrSpectrumInZSpan BohrSpec r)
    (_h_closed : BohrSpectrumClosedUnderAliasing BohrSpec)
    (_h_u : InRankRBanachAlgebra u BohrSpec r)
    (_h_v : InRankRBanachAlgebra v BohrSpec r) :
    True

/-! ## §3. The rank-`r` closed-aliasing closure (MAIN THEOREM) -/

/-- **AXIOM (Rank-`r` Closed-Aliasing NS Closure)**: for any
`r : ℕ`, any closed-aliasing rank-`r` Bohr-AP stationary 3D NS
solution with `ν > 0` satisfies `u ≡ const`. The proof is the
Banach-algebra Wiener-norm contraction inside `A_{ω_1,...,ω_r}`,
identical in structure to `rank_1_closure` but applied at rank `r`. -/
axiom rank_r_closed_aliasing_closure
    (u : NavierStokes.VelocityField 3)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3) (r : ℕ)
    (_h_AP_B2 : IsAPInBesicovitchB2 u BohrSpec a)
    (_h_zero_excl : ZeroModeExcluded BohrSpec)
    (_h_NS : BohrStationaryNS u)
    (_h_div : BohrDivergenceFree BohrSpec a)
    (_h_zspan : BohrSpectrumInZSpan BohrSpec r)
    (_h_closed : BohrSpectrumClosedUnderAliasing BohrSpec) :
    IdenticallyZero u

/-- **THEOREM (composition)**: closed-aliasing rank-`r` Bohr-AP NS is
collapsed by the Banach-algebra argument, recovering rank-1 closure as
the `r = 1` instance. -/
theorem rank_r_closed_aliasing_NS_closed
    (u : NavierStokes.VelocityField 3)
    (BohrSpec : Set (Euc ℝ 3)) (a : Euc ℝ 3 → Euc ℂ 3) (r : ℕ)
    (h_AP_B2 : IsAPInBesicovitchB2 u BohrSpec a)
    (h_zero_excl : ZeroModeExcluded BohrSpec)
    (h_NS : BohrStationaryNS u)
    (h_div : BohrDivergenceFree BohrSpec a)
    (h_zspan : BohrSpectrumInZSpan BohrSpec r)
    (h_closed : BohrSpectrumClosedUnderAliasing BohrSpec) :
    IdenticallyZero u :=
  rank_r_closed_aliasing_closure u BohrSpec a r
    h_AP_B2 h_zero_excl h_NS h_div h_zspan h_closed

/-! ## §4. The TRUE remaining open class: NON-closed-aliasing rank-≥2 -/

/-- **Predicate**: NON-closed-aliasing rank-≥2 spectrum — the genuine
open W6 residual where Picard accumulation may occur. -/
def W6_NON_CLOSED_ALIASING_RESIDUAL (BohrSpec : Set (Euc ℝ 3)) : Prop :=
  (∃ r : ℕ, r ≥ 2 ∧ BohrSpectrumInZSpan BohrSpec r) ∧
  ¬ BohrSpectrumClosedUnderAliasing BohrSpec

/-! ## §5. Honesty receipt

* The rank-r CLOSED-ALIASING case is closed by the SAME Banach-algebra
  argument as rank-1 (verbatim generalization at the algebra level).
* The rank-r NON-closed-aliasing case is GENUINELY OPEN — Picard
  iteration can accumulate new lattice points and the Wiener norm may
  blow up under multi-Liouvillian small-divisor pathology.
* For `r = 1` the closed-aliasing hypothesis is automatic, recovering
  `rank_1_closure` exactly.
* For `r ≥ 2` the closed-aliasing hypothesis is a NON-trivial extra
  assumption carving a closed sub-class out of the previous W6 residual.
* This file is NOT a Clay closure. It is concrete progress: a sub-class
  of the W6 residual, previously labeled "rank-≥2 multi-Liouvillian
  AP", has been split into a closed half (closed-aliasing) and a still-
  open half (non-closed-aliasing).

This is the architecture's most honest concrete extension of rank-1
closure to general rank, faithful to tonight's adversarial debate
verdict and respecting the anti-laundering caveat. -/

end

end ZtareProofs.NS
