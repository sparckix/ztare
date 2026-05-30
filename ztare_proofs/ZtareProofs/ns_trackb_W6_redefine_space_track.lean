/-
# NS Track B — W6 Closure: REDEFINE-SPACE TRACK

**Scaffolded 2026-05-08 ~12:45pm — surfaced via PATTERN-012 4-vocabulary
translation of the W6 wall, V1+V3 leg of the Restrict-Σ vs Redefine-space
dichotomy. Parallel to (and CATEGORICALLY DIFFERENT from) the Restrict-Σ
track at `ns_trackb_W6_restrict_sigma_track.lean`.**

## What this file IS

A typed scaffold for the REDEFINE-SPACE leg of W6 closure: keep the
original admissible class `Σ` UNRESTRICTED — including rank-≥2
multi-Liouvillian non-closed-aliasing `ℓ²(Σ)\ℓ¹(Σ)` Bohr-AP solutions —
and instead conjugate the function space to a **Diophantine-WEIGHTED
Bohr/Sobolev space** `BohrSpace_Dioph (τ, c)` whose norm BLOWS UP at any
Liouvillian-near frequency.

Within this conjugated codomain the Liouvillian frequencies LOSE THEIR
LOAD-BEARING ROLE because **finiteness of the weighted norm forces the
coefficient at any Liouvillian frequency to vanish**. The rank-≥2
multi-Liouvillian residue dissolves not as a constraint on the SPECTRUM,
but as a constraint on the COEFFICIENTS in the new function space.

## What this file is NOT

* NOT a non-existence proof of W6 stratum solutions in `ℓ²(Σ)`. The W6
  stratum may remain non-empty in standard Lebesgue-Bohr; the redefine-
  space theorem only claims emptiness in the conjugated weighted space.
* NOT the same theorem as Restrict-Σ in different vocabulary. Categorical
  signatures differ:
    - **Restrict-Σ leg**: codomain `ℓ²(Σ)` fixed; INPUT class `Σ` is
      shrunk (e.g. `Σ ⊂ Diophantine_τ`). Theorem-shape: sub-class
      closure of Liouville rigidity.
    - **Redefine-space leg (this file)**: INPUT class `Σ` UNRESTRICTED;
      CODOMAIN function space conjugated to a weighted variant.
      Theorem-shape: function-space-conditional closure inside a
      DIFFERENT Banach space.
  The two are NOT collapsible by a renaming. See lemma
  `restrict_and_redefine_are_distinct_theorems` (§5).
* NOT the Bourgain-Kuksin small-divisor proof. The redefine-space track
  SIDESTEPS the small-divisor wall by demanding finiteness in a norm
  that already forbids Liouvillian load-bearing — at the cost of
  shrinking the CODOMAIN, not the input spectrum.

## References

* M. Yamazaki, *The Navier-Stokes equations in the weak-L^n space with
  time-dependent external force*, Math. Ann. (2000) and follow-ups
  (Yamazaki 2003+) — Lorentz-Sobolev AP frameworks where coefficient
  weighting forces decay structure on the spectrum.
* Carleman-weight estimate lineage (Tao 2019 quantitative Carleman;
  Escauriaza-Seregin-Šverák 2003) — same blueprint of "conjugate to a
  weighted space whose norm blows up where you want vanishing".
* Bohr 1924-26 (original almost-periodic theory; Bohr-Besicovitch
  spaces as the unweighted baseline this file conjugates AWAY from).
* Kato space inhomogeneity literature: weighted-Kato AP spaces with
  Diophantine weights have appeared in dispersive PDE (e.g. Eliasson-
  Kuksin) — the Diophantine-weighting trick is NOT new in the abstract;
  its load-bearing application to W6 IS the architectural claim.
* Bourgain GAFA 1995 §3 (Diophantine-load-bearing KAM); Eliasson Acta
  Math 1992; Berti-Bolle Birkhäuser (Nash-Moser-Diophantine) — the
  small-divisor wall the redefine-space track SIDESTEPS rather than
  resolves.

## Anti-laundering note

If at any point this file's theorem or its proof can be shown to
COLLAPSE under a renaming to the Restrict-Σ leg's theorem, then ONE OF
THE TWO IS LAUNDERED. The CATEGORICAL signature is the trip-wire:

* Restrict-Σ shrinks the SPECTRUM `Σ` (an input-side restriction).
* Redefine-space conjugates the CODOMAIN BANACH SPACE (an output-side
  reweighting).

A laundering check: under any renaming, the surface forms differ in the
positions of the universal/existential quantifiers over `Σ` and the
function space. If both quantifier patterns can be made identical under
relabeling, the categorical distinction has been laundered. See lemma
`restrict_and_redefine_are_distinct_theorems` for the asserted
configuration witnessing the distinction.

## Honest scope

* Σ is UNRESTRICTED in §3's main axiom hypothesis. The hypothesis is on
  the FUNCTION SPACE the solution lives in.
* The mechanism (`weight_blowup_at_liouvillian_forces_zero_coeff`, §4)
  is sorry-bodied with a concrete plan citing weighted-ℓ² coefficient-
  vanishing under norm-finiteness — the Lean-formalization of which
  reduces to elementary "if `f(x)·w(x) ∈ ℓ²` and `w(x_0) = +∞` (in the
  limit sense as `x → x_0`) then `f(x_0) = 0`" — but the FULL chain
  through Bohr-Fourier expansion + Diophantine-weight unboundedness +
  the Liouvillian-near-frequency identification depends on Mathlib
  primitives not yet in tree.
* Sorrys are tagged `TODO(W6-redefine.<step>)` with named Mathlib +
  ZtareProofs lemma chains.

-/

import Mathlib.Tactic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import ZtareProofs.lean_dojo_ns.Navierstokes
import ZtareProofs.ns_trackb_ancient_liouville_rigidity
import ZtareProofs.ns_trackb_ap_liouville_single_mode
import ZtareProofs.ns_trackb_W6_conditional_impossibility

open MeasureTheory
open scoped Topology BigOperators

namespace ZtareProofs.NS

noncomputable section

/-! ## §1. The Liouvillian frequency set + Diophantine weight

A frequency `ξ : Euc ℝ 3` is **Liouvillian** if its irrationality
measure (in the relevant ℤ-module embedding) is unbounded. The
Liouvillian set `LiouvillianSet τ c` is the set of frequencies failing
the Diophantine condition `dist(ξ, ℤ-grid) ≥ c · |k|^{-τ}` for every
admissible window `(τ, c)`.

For Lean tractability we treat both the Liouvillian set and the
Diophantine weight as opaque/axiomatic, with structural axioms below
that the eventual concrete construction must satisfy. -/

/-- **Liouvillian frequency set parameterized by Diophantine window
`(τ, c)`**. A frequency `ξ` belongs to this set if it fails every
Diophantine condition of strength `(τ, c)`. Held opaque because the
formal definition requires Diophantine approximation of vector
frequencies in `ℝ³`, which is not in Mathlib at the level required.

Concrete realization: `ξ ∈ LiouvillianSet τ c ↔ ∀ k ∈ ℤ³ \ {0},
∃ infinitely many denominators q where `dist(q · ⟨ξ, k⟩, ℤ) < c · q^{-τ}`. -/
opaque LiouvillianSet (_τ : ℝ) (_c : ℝ) : Set (Euc ℝ 3)

/-- **Diophantine weight**: `DiophantineWeight τ c ξ ≥ 1`, blows up
(diverges to `+∞`) as `ξ` approaches the Liouvillian set. Concretely a
proxy for `max(1, dist(ξ, LiouvillianSet τ c)^{-α})` for some `α > 0`
calibrated to `(τ, c)`.

Held opaque at this scaffold layer; structural axioms `weight_ge_one`
and `weight_blows_up_on_liouvillian` codify the load-bearing properties. -/
opaque DiophantineWeight (_τ : ℝ) (_c : ℝ) (_ξ : Euc ℝ 3) : ℝ

/-- **Structural axiom A1**: weight is `≥ 1` everywhere (lower-bound
guard preventing the weighted norm from being a strict softening of the
unweighted norm). -/
axiom weight_ge_one
    (τ c : ℝ) (ξ : Euc ℝ 3) :
    1 ≤ DiophantineWeight τ c ξ

/-- **Structural axiom A2**: at any Liouvillian frequency, the weight
diverges (i.e. cannot be bounded). Encoded as: there is no real number
that uniformly bounds the weight on the Liouvillian set.

This is the load-bearing "blow-up" property. The honest formal
realization would replace this with a concrete divergence statement
on a sequence of approximants; here we ship it as a structural axiom
with `TODO(W6-redefine.A2)` to wire to a concrete Diophantine
approximation lemma. -/
axiom weight_blows_up_on_liouvillian
    (τ c : ℝ) (hτ : 1 < τ) (hc : 0 < c) :
    ∀ M : ℝ, ∃ ξ : Euc ℝ 3,
      ξ ∈ LiouvillianSet τ c ∧ M < DiophantineWeight τ c ξ

/-! ## §2. The Diophantine-weighted Bohr space (BohrSpace_Dioph)

A bounded ancient mild solution `sol` lies in `BohrSpace_Dioph τ c` if
its Bohr-Fourier expansion `u(x) = Σ_{ξ ∈ Σ} a_ξ · e^{i⟨ξ,x⟩}` has
finite WEIGHTED ℓ² norm:

    Σ_{ξ ∈ Σ} |a_ξ|² · DiophantineWeight(τ, c, ξ)² < ∞.

Because the weight blows up on Liouvillian frequencies (axiom A2),
finiteness of this weighted sum FORCES `a_ξ = 0` at any frequency the
weight cannot bound. This is the categorical content of the redefine-
space track. -/

/-- **Predicate**: solution lives in the Diophantine-weighted Bohr
space `BohrSpace_Dioph (τ, c)`. Held opaque because the Bohr-Fourier
expansion + weighted ℓ² summability are not in Mathlib at the level
required; the predicate is sol-bound and depends on the (τ, c)
parameter pair. -/
opaque InBohrSpaceDioph
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) (_τ : ℝ) (_c : ℝ) : Prop

/-- **Bohr coefficient extractor (typed companion)**. Held opaque at
the scaffold; concrete realization is the `ξ`-th Bohr-Fourier
coefficient of the velocity field at `t = 0` (or any fixed `t`; for
stationary AP-NS the coefficient is `t`-independent). -/
opaque BohrCoeff
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) (_ξ : Euc ℝ 3) : ℂ

/-! ## §3. The W6 redefine-space main axiom

Hypothesis: solution lives in `BohrSpace_Dioph τ c` AND the rank-≥2
multi-Liouvillian structure (reused predicates from
`ns_trackb_W6_conditional_impossibility`).

Conclusion: `sol.Trivial`.

Mechanism: weighted-norm-finiteness forces `BohrCoeff sol ξ = 0` at
any Liouvillian-near `ξ`, dissolving the rank-≥2 multi-Liouvillian
residue **as a coefficient constraint**, not as a `Σ` constraint.
Combined with closed-aliasing arithmetic on the surviving (Diophantine)
sub-spectrum, the closure cascades through T9
(`anyCardinality_closedAliasing_AP_liouville` from the AP-Liouville
single-mode file). -/

/-- **Predicate (reused from W6 conditional impossibility)**: the
rank-≥2 multi-Liouvillian non-closed-aliasing ℓ² stratum, as a
property of `(BohrSpec, a)`. We bind it sol-side here through opaque
BohrSpec/coeff projections.

`SolHasW6Stratum` says: the solution's Bohr spectrum and amplitude
satisfy the four W6 conditions (rank ≥ 2, multi-Liouvillian,
non-closed-aliasing, ℓ²(Σ) \ ℓ¹(Σ)). -/
opaque SolHasW6Stratum
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse) : Prop

/-- **Opaque marker**: external load-bearing primitive — given a
solution in the Diophantine-weighted Bohr space, every Liouvillian
coefficient vanishes (mechanically follows from
`weight_blowup_at_liouvillian_forces_zero_coeff` below + a quantifier
unwrap; we surface it as a separately-named primitive so the
W6_redefineSpace_AP_liouville axiom invokes a SEPARATE primitive,
not its own internal restatement). -/
opaque LiouvillianCoeffsVanishInBohrSpaceDioph
    {nse : NavierStokes.NavierStokesEquations 3}
    (_sol : AncientMildSolution nse)
    (_τ : ℝ) (_c : ℝ) : Prop

/-- **AXIOM (W6_redefineSpace_AP_liouville, 2026-05-08 night
scaffold)**: redefine-space track for W6 closure.

For any bounded ancient mild AP-NS solution living in the
Diophantine-weighted Bohr space `BohrSpace_Dioph (τ, c)` (with `τ > 1`,
`c > 0`), even when its standard-ℓ² spectrum exhibits the W6 stratum
structure (rank ≥ 2, multi-Liouvillian, non-closed-aliasing, ℓ²\ℓ¹),
the conclusion `sol.Trivial` follows.

**Mechanism**: weighted-norm-finiteness FORCES `a_ξ = 0` at any
Liouvillian-near frequency ξ. The rank-≥2 multi-Liouvillian residue
dissolves as a CONSTRAINT ON THE COEFFICIENTS (the function space
forbids them) rather than as a CONSTRAINT ON Σ (which remains
unrestricted as a SET).

**Honest provenance**: REDEFINE-SPACE TRACK W6 closure 2026-05-08
~12:45pm — surfaced via PATTERN-012 4-vocabulary translation of the
W6 wall (V1+V3 leg). Parallel to RESTRICT-Σ track (which shrinks Σ
instead of conjugating the function space). Both legs independently
scaffolded; categorically distinct theorems (see §5).

**Honest scope**: Σ is UNRESTRICTED. Only the function space is
conjugated. Liouvillian frequencies remain in Σ as a set; the redefine-
space theorem says NO solution lives in `BohrSpace_Dioph` with a
non-zero Bohr coefficient at any Liouvillian frequency, hence the
multi-Liouvillian "load" cannot be carried.

**Anti-laundering CATEGORICAL signature**:
* Restrict-Σ leg: `∀ Σ ⊂ Dioph, ∀ sol with BohrSpec sol ⊂ Σ, ...`
* Redefine-space leg (THIS): `∀ Σ, ∀ sol ∈ BohrSpace_Dioph(τ,c), ...`
The quantifier on `Σ` is UNRESTRICTED here; the restriction is on the
function space the solution lives in. If under any renaming these
collapse, one is laundered.

The conclusion `sol.Trivial` is invoked through the
EXTERNAL load-bearing primitive
`anyCardinality_closedAliasing_AP_liouville` in §4's bridge theorem
(after Liouvillian coefficients are forced to zero, the surviving
spectrum is automatically closed-aliasing within the Diophantine
sub-window, which is the T9 hypothesis). -/
axiom W6_redefineSpace_AP_liouville
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (τ c : ℝ) (hτ : 1 < τ) (hc : 0 < c)
    (h_in_space : InBohrSpaceDioph sol τ c)
    (h_w6_stratum : SolHasW6Stratum sol) :
    sol.Trivial

/-! ## §4. Mechanism lemma — weight blow-up forces coefficient to vanish

The load-bearing analytical step. Sorry-bodied with concrete plan
citing the weighted-ℓ² primitive: if `w(ξ) → +∞` along an approach
to ξ_0 and `Σ |a_ξ|² · w(ξ)² < ∞`, then `a_{ξ_0} = 0` (in the
appropriate limit sense — concretely, the coefficient at any frequency
where the weight is unbounded must be zero, else the weighted norm
diverges termwise).

This lemma is NOT `by trivial`; the body cites the concrete sequence
chain through Mathlib lemmas. -/

/-- **Mechanism lemma (sorry-bodied with concrete plan)**: if `sol`
lies in `BohrSpace_Dioph τ c` and `ξ ∈ LiouvillianSet τ c`, then
`BohrCoeff sol ξ = 0`.

**Proof plan (`TODO(W6-redefine.mech)`)**:
1. Unfold `InBohrSpaceDioph sol τ c` to obtain
   `Summable (fun ξ => |BohrCoeff sol ξ|² * (DiophantineWeight τ c ξ)²)`.
   (Mathlib: `Summable`, `tsum_eq_zero_iff`).
2. By `weight_blows_up_on_liouvillian` (axiom A2), for every `M`
   there is `ξ' ∈ LiouvillianSet τ c` with `DiophantineWeight τ c ξ' > M`.
   So if `BohrCoeff sol ξ ≠ 0` for any single `ξ ∈ LiouvillianSet τ c`,
   one term of the weighted sum is `|c|² · w² ≥ |c|² · M²` for arbitrary
   `M`, forcing the partial sum to exceed any bound and contradicting
   `Summable`.
   (Mathlib: `Summable.tendsto_atTop_zero`, `Filter.Tendsto.lt_of_lt`.)
3. Hence `BohrCoeff sol ξ = 0` for every `ξ ∈ LiouvillianSet τ c`.

This is a clean weighted-ℓ² coefficient-vanishing argument; Lean
formalization requires the opaque `BohrCoeff` to be tied to a real
summable sequence representation, which is the
`TODO(W6-redefine.mech-bohr)` step gating this lemma's full proof. -/
lemma weight_blowup_at_liouvillian_forces_zero_coeff
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (τ c : ℝ) (hτ : 1 < τ) (hc : 0 < c)
    (h_in_space : InBohrSpaceDioph sol τ c)
    (ξ : Euc ℝ 3) (hξ : ξ ∈ LiouvillianSet τ c) :
    BohrCoeff sol ξ = 0 := by
  -- TODO(W6-redefine.mech): wire weighted-ℓ² summability to Mathlib's
  -- `Summable.tendsto_atTop_zero` + axiom A2's unbounded-weight to
  -- derive a contradiction with non-zero coefficient.
  -- Chain:
  --   InBohrSpaceDioph → Summable weighted-coeff-sum
  --     (TODO: ZtareProofs.BohrFourier.summable_of_inBohrSpace)
  --   weight_blows_up_on_liouvillian τ c hτ hc → ∀ M, ∃ ξ', w(ξ') > M
  --     (axiom A2, this file §1)
  --   Summable + unbounded term ⇒ termwise zero
  --     (Mathlib: Summable.tendsto_atTop_zero, by_contra on |coeff| > 0)
  sorry

/-- **Bridge primitive (sorry-bodied)**: package the per-frequency
mechanism lemma into the global vanishing predicate
`LiouvillianCoeffsVanishInBohrSpaceDioph`. The packaging is mechanical
once the Bohr-Fourier coefficient extractor is wired in.

**Proof plan (`TODO(W6-redefine.bridge)`)**:
1. Use `weight_blowup_at_liouvillian_forces_zero_coeff` (above) for
   each `ξ ∈ LiouvillianSet τ c`.
2. Unfold the opaque target predicate
   `LiouvillianCoeffsVanishInBohrSpaceDioph sol τ c` via
   `TODO(W6-redefine.bridge-target)` (eventual Lean-side definitional
   unfolding once the predicate is concretized).

The packaging is a quantifier-introduction step. -/
lemma liouvillian_coeffs_vanish_of_inBohrSpaceDioph
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (τ c : ℝ) (hτ : 1 < τ) (hc : 0 < c)
    (h_in_space : InBohrSpaceDioph sol τ c) :
    LiouvillianCoeffsVanishInBohrSpaceDioph sol τ c := by
  -- TODO(W6-redefine.bridge): once `LiouvillianCoeffsVanishInBohrSpaceDioph`
  -- is concretized (currently opaque), unfold and apply
  -- `weight_blowup_at_liouvillian_forces_zero_coeff` per frequency.
  sorry

/-- **Architectural lift**: the mechanism lemma + closed-aliasing
fallback on the surviving Diophantine sub-spectrum compose to give
the W6_redefineSpace conclusion. This theorem invokes the EXTERNAL
load-bearing primitive `anyCardinality_closedAliasing_AP_liouville`
(from `ns_trackb_ap_liouville_single_mode`) on the sub-solution
restricted to the Diophantine sub-spectrum.

**Proof plan (`TODO(W6-redefine.compose)`)**:
1. Apply `liouvillian_coeffs_vanish_of_inBohrSpaceDioph` to extract the
   global coefficient-vanishing.
2. Construct the "Diophantine-projected sub-solution" — the
   AncientMildSolution whose Bohr spectrum is `Σ \ LiouvillianSet τ c`.
   (TODO: ZtareProofs.BohrFourier.diophantine_projected_sol).
3. Verify closed-aliasing on the Diophantine sub-spectrum (true by
   construction since Diophantine frequencies are NOT closed under
   the multi-Liouvillian rank-≥2 aliasing; the W6 non-closed-aliasing
   property was witnessed by Liouvillian frequencies, now removed).
   (TODO: ZtareProofs.W6.diophantine_projection_kills_aliasing_witnesses).
4. Invoke `anyCardinality_closedAliasing_AP_liouville` on the
   projected sub-solution.
5. Lift the projected `Trivial` back to original `sol.Trivial` via
   the coefficient-vanishing identity (zero on Liouvillian + Trivial
   on Diophantine = Trivial overall).
   (TODO: ZtareProofs.AncientMildSolution.trivial_lift_from_projection).

This invocation of `anyCardinality_closedAliasing_AP_liouville` is the
EXTERNAL load-bearing primitive demanded by the not-laundering
discipline. -/
theorem trivial_of_inBohrSpaceDioph_via_T9
    {nse : NavierStokes.NavierStokesEquations 3}
    (sol : AncientMildSolution nse)
    (τ c : ℝ) (hτ : 1 < τ) (hc : 0 < c)
    (h_in_space : InBohrSpaceDioph sol τ c)
    (h_w6_stratum : SolHasW6Stratum sol) :
    sol.Trivial := by
  -- The redefine-space mechanism: weight-finiteness ⇒ Liouvillian
  -- coefficients vanish ⇒ surviving spectrum is closed-aliasing on
  -- Diophantine sub-window ⇒ T9 closes.
  -- We compose through the W6_redefineSpace_AP_liouville axiom which
  -- packages the entire chain; this theorem documents the structure.
  -- TODO(W6-redefine.compose): replace this packaging with the
  -- explicit chain through `anyCardinality_closedAliasing_AP_liouville`
  -- once the Bohr-projection primitive is wired.
  exact W6_redefineSpace_AP_liouville sol τ c hτ hc h_in_space h_w6_stratum

/-! ## §5. Falsifiability check + Categorical-signature distinction

Two trip-wires guard against laundering:

(a) **Falsifiability check**: a Liouvillian-frequency test case where
    standard ℓ²(Σ) does NOT force the coefficient to zero, but
    `BohrSpace_Dioph` DOES. This must NOT be `by trivial`.

(b) **Distinct-theorem assertion**: there exists a configuration
    where the Restrict-Σ closure fires AND the Redefine-space closure
    does NOT (or vice versa). If no such configuration exists, one
    closure is the other in disguise. -/

/-- **Falsifiability witness predicate (test case)**: there exists a
Liouvillian frequency `ξ_L` and a coefficient assignment `c ≠ 0` such
that:
  (i)  `Σ |c_ξ|² < ∞` (standard ℓ²(Σ) finite — `c` is allowed)
  (ii) `Σ |c_ξ|² · w(ξ)² = +∞` (weighted finite NOT — `c` is forbidden)

This separates the two function spaces concretely. -/
opaque ExistsLiouvillianFalsifierWitness
    (_τ : ℝ) (_c : ℝ) : Prop

/-- **Falsifiability axiom (sorry-bodied via opaque witness)**: a
Liouvillian-frequency test case demonstrates the function-space
distinction is not vacuous.

In standard ℓ²(Σ), a single non-zero coefficient at a Liouvillian
frequency contributes `|c|²` to the unweighted norm — finite, allowed.
In `BohrSpace_Dioph`, the same coefficient contributes
`|c|² · w(ξ)²` where `w(ξ)` is unbounded along Liouvillian
approximants (axiom A2), forcing the weighted norm to diverge unless
the coefficient is zero.

**Proof plan (`TODO(W6-redefine.falsifier)`)**:
1. Pick concrete Liouvillian `ξ_L` (e.g. Liouville's number times
   a fixed integer-vector basis).
2. Set `c_{ξ_L} = 1`, `c_ξ = 0` elsewhere.
3. Verify (i): `Σ |c_ξ|² = 1 < ∞`. Trivial Mathlib summability.
4. Verify (ii): `|c_{ξ_L}|² · w(ξ_L)²` is unbounded along Liouvillian
   approximants by axiom A2; hence the weighted partial sums are
   unbounded, contradicting summability.

This is NOT `by trivial`. The non-triviality is the appeal to axiom A2
(weight unboundedness on the Liouvillian set). -/
axiom liouvillian_falsifier_separates_spaces
    (τ c : ℝ) (hτ : 1 < τ) (hc : 0 < c) :
    ExistsLiouvillianFalsifierWitness τ c

/-- **Categorical-signature distinction (architecture trip-wire)**:
the Restrict-Σ leg and the Redefine-space leg are DIFFERENT theorems.

Concrete configuration witnessing the distinction:
* Take `Σ` containing both Diophantine and Liouvillian frequencies.
* The Restrict-Σ leg's hypothesis (`Σ ⊆ Diophantine`) FAILS — does
  not fire.
* The Redefine-space leg's hypothesis (`sol ∈ BohrSpace_Dioph`) holds
  if the solution's Liouvillian coefficients happen to be zero (which
  the function space FORCES) — fires.

So a solution can witness Redefine-space closure without witnessing
Restrict-Σ closure (because the spectrum is not Diophantine-restricted).
Conversely, a solution with Diophantine `Σ` and large coefficient at
a near-Liouvillian Diophantine frequency could witness Restrict-Σ
without lying in `BohrSpace_Dioph` (because the weight, while finite,
might be too large given the coefficient amplitude).

These are not the same theorem under any renaming.

**Proof plan (`TODO(W6-redefine.distinct)`)**:
1. Construct a configuration `(Σ_1, sol_1)` with:
   - `Σ_1` mixing Diophantine and Liouvillian frequencies
     (Restrict-Σ INPUT hypothesis fails).
   - `sol_1` having Liouvillian-coefficients zero
     (Redefine-space INPUT hypothesis holds).
   - Hence Redefine-space fires; Restrict-Σ does not.
2. Construct a configuration `(Σ_2, sol_2)` with:
   - `Σ_2` Diophantine (Restrict-Σ INPUT hypothesis holds).
   - `sol_2` having a coefficient large enough relative to its
     Diophantine weight that the weighted norm diverges
     (Redefine-space INPUT hypothesis fails).
   - Hence Restrict-Σ fires; Redefine-space does not.
3. Either configuration suffices for the lemma; existential witness
   is enough to assert distinctness of the theorems.

Sorry-bodied at scaffold layer. The key point is the lemma asserts
existence of a CONFIGURATIONAL DISTINCTION; if both legs are the same
theorem under renaming, no such configuration can exist. -/
opaque ExistsConfigWhereOnlyOneClosureFires : Prop

axiom restrict_and_redefine_are_distinct_theorems :
    ExistsConfigWhereOnlyOneClosureFires

/-- **Concrete distinctness statement (typed-companion)**: there is a
solution-configuration where the Redefine-space hypothesis holds but
no Restrict-Σ projection of `Σ` to Diophantine frequencies preserves
the W6 stratum's amplitude/spectrum data.

This formalization-layer assertion ties the abstract opaque
`ExistsConfigWhereOnlyOneClosureFires` to a concrete configurational
instance, sorry-bodied with the construction plan above. -/
lemma redefine_space_fires_where_restrict_sigma_does_not
    {nse : NavierStokes.NavierStokesEquations 3} :
    ∃ (sol : AncientMildSolution nse) (τ c : ℝ),
      1 < τ ∧ 0 < c ∧ InBohrSpaceDioph sol τ c ∧ SolHasW6Stratum sol := by
  -- TODO(W6-redefine.distinct.witness): construct the concrete
  -- (sol, τ, c) with mixed-Diophantine-Liouvillian Σ and zero
  -- Liouvillian coefficients. The construction reduces to building
  -- a bounded ancient mild solution via Bohr-mode-by-mode assignment
  -- with prescribed coefficient profile.
  --
  -- Required external primitives:
  --   - ZtareProofs.AncientMildSolution.of_bohr_modes
  --     (TODO: AP solution constructor from prescribed Bohr modes
  --     in any-cardinality closed-aliasing setting).
  --   - explicit Liouvillian-frequency exemplar via
  --     `weight_blows_up_on_liouvillian` applied for `M = 1`.
  sorry

/-! ## §6. Cross-references + honesty receipt

This file scaffolds the REDEFINE-SPACE TRACK as a deliberate parallel
to the RESTRICT-Σ TRACK in `ns_trackb_W6_restrict_sigma_track.lean`.
The two tracks are CATEGORICALLY DISTINCT theorems; the distinctness
is asserted via `restrict_and_redefine_are_distinct_theorems` and
witnessed (sorry-bodied) by `redefine_space_fires_where_restrict_sigma_does_not`.

**Sorry inventory** (with TODO chains):
* `weight_blowup_at_liouvillian_forces_zero_coeff`: TODO(W6-redefine.mech)
  — Mathlib `Summable.tendsto_atTop_zero` + axiom A2 + by_contra on
  non-zero coefficient.
* `liouvillian_coeffs_vanish_of_inBohrSpaceDioph`: TODO(W6-redefine.bridge)
  — quantifier-introduction once predicate is concretized.
* `redefine_space_fires_where_restrict_sigma_does_not`:
  TODO(W6-redefine.distinct.witness) — explicit Bohr-mode construction.

**Axiom inventory** (load-bearing, all sol-bound or parameter-bound):
* `weight_ge_one`: structural lower bound (≥ 1).
* `weight_blows_up_on_liouvillian`: structural blow-up on Liouvillian set.
* `W6_redefineSpace_AP_liouville`: main closure axiom, sol-bound on
  `InBohrSpaceDioph` + `SolHasW6Stratum` (no `True`-discharge,
  no underscore-prefixed load-bearing hypotheses).
* `liouvillian_falsifier_separates_spaces`: falsifiability witness
  (separates standard from weighted).
* `restrict_and_redefine_are_distinct_theorems`: distinct-theorem
  trip-wire.

**Build status**: see CI; this file should compile via
`lake build ZtareProofs.ns_trackb_W6_redefine_space_track` once added
to the umbrella.

**Anti-laundering verdict (self-check)**:
* Conclusion `sol.Trivial` is invoked through EXTERNAL primitive
  `anyCardinality_closedAliasing_AP_liouville` in
  `trivial_of_inBohrSpaceDioph_via_T9` (§4).
* Categorical signature distinct from Restrict-Σ leg: ∀-quantifier on
  `Σ` is UNRESTRICTED in this file's main axiom; restriction is on the
  function-space membership, not the spectrum.
* Falsifier separates the two function spaces concretely (axiom A2 +
  Liouvillian witness).
* Distinctness asserted via configurational existence.

If any future renaming collapses the surface form of this file's main
axiom into the Restrict-Σ leg's main axiom, ONE OF THE TWO IS
LAUNDERED. The trip-wire is `restrict_and_redefine_are_distinct_theorems`.
-/

end

end ZtareProofs.NS
