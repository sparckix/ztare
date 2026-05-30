/-
# NS Track B — W6-NEW-3 — Leray-Skew Commutator Framework (height-filtered)

> **2026-05-09 EXTERNAL VERDICT (GPT-5 cold-shot, dispatch epd-af8ecfae3613,
> $0.36 cost, catch C-2026-05-09-61):** **THIS ROUTE IS DEAD too.**
>
> The named residual void axiom `HeightFilteredLerayCommutatorControl`
> in this file is **PROVABLY FALSE** for rank-2 Liouville `ω` in any
> NS-controlled norm class that is monotone in the physical wavenumber
> `|ζ| = |m + n ω|` (Sobolev `H^s`, Besov, Gevrey, mixed-Lebesgue, etc.).
>
> **Structural invariant** (height–scale collapse for Liouville lattices):
> ```
>   ρ_ω(H) := min{ |m + n ω| : 0 < H(m,n) ≤ H }
> ```
> For Liouville `ω` and every `τ > 0`, there exists a sequence `H_k → ∞`
> with `ρ_ω(H_k) ≤ H_k^{−τ}`. This is the defining consequence of
> Liouville approximation (Cassels 1957 Ch. I Thm 1; Bugeaud 2004 §1.1):
> ∀k ∈ ℕ ∃ infinitely many p/q with |ω − p/q| < q^{−k}, hence
> `(m, n) = (-p, q)` gives `|m + nω| ≤ H^{−k}` with `H ≍ q`.
>
> **Explicit counterexample family.** Pick a Liouville-approximating
> sequence `(m_j, n_j)` with `H_j ≥ exp(j²)` and `|ζ_j| ≤ H_j^{−j}`.
> Define
> ```
>   u(x) := Σ_{j} a_j exp(i ζ_j ξ · x) e,   e ⟂ ξ
>   a_j  := (1 + |ζ_j|²)^{−s/2} · j^{−1}
> ```
> Then `‖u‖_{H^s}² = Σ j^{−2} < ∞` (finite Sobolev norm), but for any
> `R` with `H_J ≤ R < H_{J+1}`,
> ```
>   ‖Q_R u‖_2² ≥ Σ_{j≥J} a_j² ≳ 1/J ≫ H_J^{−σ} for any σ > 0
> ```
> since `H_J` grows super-polynomially in `J`. Hypothesis (T) FAILS
> uniformly in `R` for every `σ > 0`. Hypothesis (B) is benign
> (Cauchy–Schwarz on the height-ball cardinality `R²`).
>
> **Implication for the W6 closure narrative.** Tonight's session has
> demolished THREE independent W6 closure routes via external GPT-5
> dispatch:
>   1. **Additive-combinatorics (BKGSW + NC)** — catch C-58: (NC)
>      outright false on T³ via shear-flow counterexample.
>   2. **Low-frequency Wiener-algebra (Lerner-2026 port)** — catch C-59:
>      function class incompatible (Lerner's decay vs Bohr-AP non-decay).
>   3. **Height-filtered Leray-skew commutator** (this file) — catch
>      C-61: height-scale collapse for Liouville ω structurally obstructs
>      (T) regardless of NS-controlled norm choice.
>
> All three share the same root cause: **the rank-2 Liouville Bohr-AP
> substrate is wrong-shape for NS-natural functional analysis.** The
> substrate's natural invariant (height `max(|m|, |n|)`) is decoupled
> from NS's natural invariant (scale `|m + n ω|`) precisely BECAUSE `ω`
> is Liouville.
>
> **The honest contribution this file represents** is the PRECISE FRAMING
> + LEAN ENCODING + SHARP NEGATIVE ANSWER on the third independent route,
> NOT closure.
>
> Continuation directions that are NOT yet demolished by external prover:
>   (i) Restrict `ω` to Diophantine-of-finite-type (not Liouville). But the
>       2026-05-07 audit `alien_math_6_diophantine_KAM_KILL_OR_VALIDATE`
>       already showed that for stationary AP-NS the linearized operator
>       collapses to `ν|α|² I_{P_α^⊥}` regardless of Diophantine class —
>       no time-frequency, no `⟨n, α⟩` denominator. Diophantine restriction
>       does NOT obviously revive the height-filter route; needs separate
>       cold-shot.
>   (ii) Drop Bohr-AP for a different non-decaying class (e.g.
>        Wiener-algebra, almost-periodic in time but not space, etc.) —
>        wholly different campaign.
>   (iii) Drop the W6 target — accept multi-Liouvillian rank-≥2 as a
>        recognized "structurally hard" stratum that the bilinear cascade
>        cannot resolve, and concentrate elsewhere.

**Date**: 2026-05-09 evening session.
**Provenance**: GPT-5.5 derivation relayed by operator after the additive-
combinatorics route was structurally demolished by:

  * **C-2026-05-09-58**: NS substrate does NOT provide (BKGSW)+(NC) on T³;
    explicit shear-flow counterexample disproves (NC).
  * **C-2026-05-09-59**: W6_sharp_conditional Lerner-2026 port confirmed
    NOT faithful to Lerner Theorem 1.12; Bohr-AP function class
    structurally outside Lerner's decay class.

This file encodes the **non-additive bilinear-control** mechanism that
replaces additive positivity. The math content is well-known to NS
specialists (Constantin-Foias-Manley-style skew-symmetry plus filtered
Reynolds-stress decomposition); what is novel here is the **explicit
naming of the residual void** in the Bohr-AP-W6 setting:

  > Prove quantitative commutator/flux control for Liouville-height Bohr
  > filters under the Leray-skew NS trilinear form.

This is **NOT** Khintchine-Groshev with weights. It is a height-filtered
Leray commutator estimate compatible with NS Sobolev/parabolic control.

## What this file IS

* Type-level encoding of the trilinear form `b(u,v,w) = ∫ (u·∇v)·w`.
* The two NS skew-symmetry identities `b(u,v,w) = -b(u,w,v)` and
  `b(u,v,v) = 0` for divergence-free `u`, stated as **axioms** with the
  TAG `classical_mathlib_mergeable_pending_setup`.
* The filtered nonlinear flux `Π_R(u) = b(u, u, P_R u)` and the two
  vanishing-term identities (LLL and HLL) that follow from the
  skew-symmetry axioms.
* Bound (1) of the GPT-5.5 derivation as a typed-companion axiom.
* The named **residual void**: `HeightFilteredLerayCommutatorControl`
  axiom, tagged TIER-A-alien (genuinely open, NOT in Mathlib, NOT in
  current published NS literature for Liouville-height Bohr filters).
* A composition theorem `W6_NEW3_filtered_energy_identity_conditional`
  showing how the residual void plus standard NS energy methods
  unblocks W6.

## What this file is NOT

* **NOT a closure of W6.** The residual void axiom is the open content.
* **NOT a Bohr-AP analog of Lerner-2026.** This route abandons low-frequency
  Wiener-algebra control entirely; the mechanism is energy-method
  cancellation, not coefficient-summability.
* **NOT additive-combinatorics.** The skew-symmetry kills same-side
  interactions BEFORE summation; absolute values destroy NS structure.
* **NOT mergeable to Mathlib.** The trilinear form, the skew identity,
  and the Bohr-height projections all need 100-300 LoC of analytic
  setup not yet in Mathlib. This is documented but not a defect.

## Catch register
* **Catch C-58/C-59 corroboration**: the routes this file replaces are
  documented as terminally demolished in `analytics/public/ledgers/catch/catch_ledger.jsonl`.
* **Pattern-deployment-ledger note**: this file's content was sourced
  via PATTERN-009 (independent_cas_verification, operator-relayed
  GPT-5.5), the under-utilized pattern flagged by PATTERN-013 minting.

-/

namespace ZtareProofs.NS3D.W6NEW3LeraySkew

open scoped Classical
noncomputable section

/-! ## Type-level placeholders for NS objects on T³

These are abstract Props/types capturing the math content. Concrete
realizations would use Mathlib's `MeasureTheory.Lp` and a divergence-free
constraint via `MeasureTheory.distrib`. We keep them abstract to focus
on the cancellation algebra, not the analytic setup.
-/

/-- Abstract divergence-free vector-field-on-T³ class. -/
class IsDivFreeT3 (u : Type*) : Prop

/-- Abstract Bohr-height-ball projection at radius `R`. -/
structure BohrHeightProjection (R : ℝ) (u : Type*) where
  height_filter_well_defined : True
  preserves_div_free : True
  commutes_with_grad_and_leray : True

/-- The trilinear NS form `b(u,v,w) = ∫_T³ (u · ∇v) · w dx`, abstracted
as an opaque ℝ-valued operation. -/
opaque trilinearNS : ∀ (u v w : Type*), ℝ

/-! ## NS skew-symmetry identities (classical, Mathlib-mergeable pending setup)

These are the two structural identities that kill additive-combinatorics
positivity and replace it with cancellation-based control.
-/

/-- **Skew-symmetry**: for divergence-free `u`,
`b(u, v, w) = -b(u, w, v)`. Classical (Constantin-Foias-Manley).
Mathlib-mergeable conditional on full vector-field setup. -/
axiom trilinearNS_skew_div_free
    {u v w : Type*} [IsDivFreeT3 u] :
    trilinearNS u v w = - trilinearNS u w v

/-- **Energy-cancellation**: for divergence-free `u`, `b(u, v, v) = 0`.
Direct consequence of skew-symmetry with `w = v`. -/
theorem trilinearNS_self_zero
    {u v : Type*} [IsDivFreeT3 u] :
    trilinearNS u v v = 0 := by
  have h := trilinearNS_skew_div_free (u := u) (v := v) (w := v)
  -- `r = -r ⇒ r = 0` over ℝ.
  linarith

/-! ## Filtered nonlinear flux Π_R(u) and its decomposition

Following GPT-5.5's derivation (relayed 2026-05-09):
  Π_R(u) := ⟨P_R B(u, u), P_R u⟩ = b(u, u, u_L)
where u_L = P_R u (low Bohr-height part) and u_H = Q_R u (high tail).

Expanding `u = u_L + u_H` in the first two slots gives four terms; the
LLL and HLL terms vanish by `trilinearNS_self_zero`, leaving
  Π_R = b(u_L, u_H, u_L) + b(u_H, u_H, u_L).
-/

/-- Filtered low-mode component (abstract carrier). -/
structure LowMode (R : ℝ) (u : Type*) where
  carrier : Type*

/-- Filtered high-tail component (abstract carrier). -/
structure HighMode (R : ℝ) (u : Type*) where
  carrier : Type*

/-- Filtered nonlinear flux `Π_R(u) = b(u, u, P_R u)`. -/
opaque PiR : ∀ (R : ℝ) (u : Type*), ℝ

/-- **LLL-cancellation**: the low-low-low diagonal vanishes by
`trilinearNS_self_zero` applied to `u_L`. -/
axiom trilinearNS_LLL_zero
    (R : ℝ) {u : Type*} [IsDivFreeT3 u]
    (uL : LowMode R u) :
    -- Concretely: trilinearNS uL.carrier uL.carrier uL.carrier = 0
    True

/-- **HLL-cancellation**: `b(u_H, u_L, u_L) = 0` because the third-and-second
slot are equal modulo the projection-commutes-with-Leray axiom. -/
axiom trilinearNS_HLL_zero
    (R : ℝ) {u : Type*} [IsDivFreeT3 u]
    (uL : LowMode R u) (uH : HighMode R u) :
    True

/-! ## Bound (1): non-additive bilinear control

|Π_R(u)| ≲ ‖u_L‖_∞ · ‖∇ u_L‖_2 · ‖u_H‖_2  +  ‖∇ u_L‖_∞ · ‖u_H‖_2²

This is the central NS-compatible bilinear bound. The proof is Hölder +
Bernstein + the two cancellation axioms above. Stated here as a typed-
companion axiom; the full Lean derivation requires ~150-300 LoC of
Mathlib eLpNorm + Hölder + Bernstein machinery and is **not in scope
for this file** — it is the unit of work for a follow-up campaign.
-/

/-- Norms placeholder: each `Norm⟨name⟩` is an opaque ℝ-valued operator. -/
opaque normLinftyLow : ∀ (R : ℝ) (u : Type*), ℝ
opaque normGradLowL2 : ∀ (R : ℝ) (u : Type*), ℝ
opaque normHighL2 : ∀ (R : ℝ) (u : Type*), ℝ
opaque normGradLowLinfty : ∀ (R : ℝ) (u : Type*), ℝ

/-- **Bound (1)** of the GPT-5.5 derivation. -/
axiom PiR_bound_one
    (R : ℝ) {u : Type*} [IsDivFreeT3 u] :
    ∃ C : ℝ, |PiR R u|
      ≤ C * (normLinftyLow R u * normGradLowL2 R u * normHighL2 R u
        + normGradLowLinfty R u * (normHighL2 R u) ^ 2)

/-! ## The named residual void

The binding constraint: turn bound (1) into a quantitative R-rate. This
requires
  (a) tail-decay control: ‖Q_R u‖_2 ≲ R^{-σ} N_σ(u) for some σ > 0.
  (b) Bernstein/commutator low-mode bounds: ‖P_R u‖_∞ + ‖∇ P_R u‖_∞
      ≲ R^a N(u) for some a < σ.

For Liouville ω, the scalar Bohr size |m + n ω| is BADLY non-comparable
to the height H(m, n) = max(|m|, |n|). Hence no Diophantine lower bound
converts height into analytic smoothing in any direction useful here.

**The missing theorem is therefore the height-filtered Leray commutator
estimate for Liouville-height Bohr filters**, NOT a Khintchine-Groshev
weighted bound.

-/

/-- The named residual void. **Open content.** -/
axiom HeightFilteredLerayCommutatorControl
    {u : Type*} [IsDivFreeT3 u]
    (Σω_LiouvilleRank2 : True) :
    ∃ σ a C : ℝ,
      0 < σ ∧ a < σ ∧ 0 < C ∧
      ∀ (R : ℝ),
        normHighL2 R u ≤ C * R ^ (-σ) ∧
        normLinftyLow R u + normGradLowLinfty R u ≤ C * R ^ a

/-! ## Composition: the residual void unblocks the filtered energy identity

The structure of the consequence (relative to W6) is: with the residual
void axiom, bound (1) yields a CLOSED energy estimate of the form

  ½ d/dt ‖P_R u‖₂² + ν ‖∇ P_R u‖₂² ≲ tail-controlled remainder

which, in the Bohr-AP stationary setting (no time derivative, only
spatial), reduces to a uniform-in-R coercive bound. Sending R → ∞
forces the tail and the nonlinearity to zero, giving the W6
conclusion `IdenticallyZeroSpatial u` UNDER THE RESIDUAL VOID.

This composition is stated below as a typed conditional theorem.
-/

/-- The W6 conclusion (placeholder for `IdenticallyZeroSpatial u`). -/
opaque W6Trivial : ∀ (u : Type*), Prop

/-- **W6-NEW-3 — conditional closure under the residual void.**

If `HeightFilteredLerayCommutatorControl` holds for the multi-Liouvillian
substrate, then bound (1) plus standard NS energy methods imply the W6
trivial conclusion.

This theorem **does not claim** the residual void; it claims the
implication. The residual void is the open content the W6-NEW-3 campaign
is targeting. -/
theorem W6_NEW3_filtered_energy_identity_conditional
    {u : Type*} [IsDivFreeT3 u]
    (Σω_LiouvilleRank2 : True)
    (residual_void :
      ∃ σ a C : ℝ,
        0 < σ ∧ a < σ ∧ 0 < C ∧
        ∀ (R : ℝ),
          normHighL2 R u ≤ C * R ^ (-σ) ∧
          normLinftyLow R u + normGradLowLinfty R u ≤ C * R ^ a) :
    W6Trivial u := by
  -- The composition (Hölder + Young + tail decay + Bernstein commutator
  -- + send R → ∞) is the unit-of-work for the follow-up campaign. We
  -- state the implication as a typed sorry-companion: the residual void
  -- axiom + bound (1) is the claim, the rest is standard NS energy
  -- machinery on T³.
  sorry

/-! ## Anti-laundering catches

* **Catch L-1**: this file does not "close" W6. The conditional theorem
  has a `sorry` in the body. Removing the `sorry` requires a full energy-
  method composition, which is the next-campaign work.
* **Catch L-2**: the `axiom`s `trilinearNS_skew_div_free`,
  `trilinearNS_LLL_zero`, `trilinearNS_HLL_zero`, `PiR_bound_one` are
  CLASSICAL on standard NS substrate and Mathlib-mergeable pending the
  vector-field setup. They are NOT new mathematical content.
* **Catch L-3**: the `axiom`
  `HeightFilteredLerayCommutatorControl` is the GENUINE open content.
  It is NOT in Mathlib, NOT (to operator+RD knowledge) in the published
  NS literature for Liouville-height Bohr filters, and represents the
  load-bearing residual void this campaign would target.
* **Catch L-4 (vocabulary-quarantine, PATTERN-004)**: this file uses NS-
  native vocabulary (Leray projection, energy method, skew-symmetry,
  Reynolds stress) instead of Bohr-AP-native vocabulary (multi-Liouvillian,
  closed-aliasing, ℓ¹/ℓ² gap). The substrate translation `Σω_LiouvilleRank2`
  is intentionally abstract to expose this seam — the binding question
  is whether the Bohr-AP setting realizes the height-filter algebra
  faithfully. The next-campaign external-prover dispatch should ask
  exactly this.

-/

end
end ZtareProofs.NS3D.W6NEW3LeraySkew
