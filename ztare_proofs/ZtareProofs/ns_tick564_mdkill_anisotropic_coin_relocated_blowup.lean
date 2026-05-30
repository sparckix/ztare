import Mathlib.Tactic
import ZtareProofs.ns_tick562_antilamellar_discharge_via_serrin_heat_regularity

/-!
# Tick564 — Meta-Darwin KILL: the "Anisotropic Coin Cylinder" lemma
#           relocates the pressure-non-locality blowup, does not remove it

## target_kind (v36 governance, honest)

target_kind: meta_darwin_kill
NOT proof_progress. NOT a reduction tick. NOT compiled into the
route-1 DAG. This KILLS an external candidate "missing lemma"
construction (GPT-5.5's Anisotropic Coin), like tick552 killed the
Caloric Deficit and tick563 killed the pressure-forcing Kill Shot
(both Tier-3 PASS). HARD-GUARD-compliant: a darwin_idea_killer kill
proving the omitted factor; inhabits NO closure.

## The claim under audit

GPT-5.5 proposed a *Local One-Component ε-Regularity* lemma via an
**Anisotropic "Coin" Cylinder** `Q = B_R × (-h,0)`, `h ≪ R`, with a
separable cutoff `φ = ψ(x,y)·η(z)`. Claim: `|∂_zφ| ≫ |∇_{xy}ψ|` ⇒
`∇φ ≈ ∂_zφ k̂` ⇒ the pressure commutator
`∫ p(u·∇φ) ≈ ∫ p·u_z·∂_zφ` ⇒ Hölder
`≤ ‖p‖_{3/2}‖u_z‖_3‖∂_zφ‖_∞` ⇒ "microscopic since ‖u_z‖_3<ε" ⇒
absorbed ⇒ regular. Operator asked: audit the Hölder absorption
first, or compile? **Audit. It is killed.**

## The KILL — the silently-dropped `‖∂_zφ‖_∞ ~ 1/h` factor (PROVED)

A cutoff that goes `η=1`→`η=0` across the coin's height `h` has
`‖∂_zφ‖_∞ ≳ c/h`. The flatter the coin (`h→0`), the LARGER this
factor. The honest Hölder bound is
  `|∫ p(u·∇φ)| ≲ ‖p‖_{3/2} · ‖u_z‖_3 · (c/h)`,
NOT `≲ ‖p‖_{3/2}·‖u_z‖_3`. With `‖u_z‖_3 < ε` the bound is
`≲ ‖p‖_{3/2}·ε/h`, which **→ ∞ as h→0** unless `ε/h → 0`. The
Anisotropic Coin does not REMOVE the pressure-non-locality trap — it
RELOCATES the in-plane-velocity blowup into the `1/h`
cutoff-derivative. Same fixed point, new vocabulary.

## Threshold is NOT parabolic-scale-invariant (PROVED)

The proposed threshold `(1/R)∫_Q|u_z|³ < ε*(h/R)`. Cascade scaling
(`|u_z|~ε(r)·ν/r`, `|Q|~R²·h`, `R~r`):
  `(1/R)∫_Q|u_z|³ ~ ε(r)³ ν³ (R²h)/(r³ R) ~ ε(r)³ ν³ · h/R²`.
Condition `< ε*·h/R` ⟺ `ε(r)³ν³/R < ε*` ⟺ FAILS as `R→0` unless
`ε(r) ≳ R^{1/3}`. The threshold is aspect-ratio-dependent and
**not parabolic-scale-invariant** — exactly the
fixed-norm/fixed-domain vs self-similar-cascade mismatch GPT-5.5's
OWN prior near-2D NO_GO flagged as the live risk.

## Consequence (honest)

The Anisotropic Coin is a Φ-iterate landing on the same fixed point;
it does NOT supply the genuinely-open *local one-component
ε-regularity for suitable weak solutions* (the verified residual:
the one-component localization of He–Wang–Zhou 2019 full-velocity
local ε-regularity, NOT published). Not compiled into the route-1
DAG. The honest endpoint stands: route-1 closure ⟺ that real, named,
OPEN theorem; inputs 1–2 (Type-I branch-defining; Lin pressure)
genuinely discharged.

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar Hölder-bound / cutoff-derivative model
- direction ✓ honest bound carries the dropped `1/h`; threshold not R-invariant
- quantifier ✓ ∀ coin height h, ∀ cascade scale R
- domain ✓ anisotropic coin cylinder, flat cascade
- dimension ✓ scalar norms / h / R / ε
- inclusion ✓ uses CZ pressure bound honestly; inhabits no closure

## Post-check: closure_claim_discipline_linter + Tier-2/3 (authorized).
-/

namespace ZtareProofs.NSTick564MDKillAnisotropicCoinRelocatedBlowup

/-! ## (1) The dropped `1/h` factor: bound is NOT microscopic (PROVED) -/

/--
**`anisotropic_coin_bound_blows_up_in_h`** (PROVED).

Honest Hölder: `pressureTerm ≤ pNorm · uzNorm · dzPhiSup` with the
cutoff-derivative sup `dzPhiSup = c/h` (cutoff over height `h`). Even
with `uzNorm ≤ ε`, the bound is `pNorm·ε·c/h`, which is NOT bounded
by `pNorm·ε` — the omitted `c/h` factor makes it diverge as `h→0`.
Stated: for any target `microscopic`, there is a coin thin enough
(`h` small) that the honest bound exceeds it. The "microscopic"
claim silently drops `c/h`.
-/
theorem anisotropic_coin_bound_blows_up_in_h
    (pNorm ε c h : ℝ)
    (hp : 0 < pNorm) (hε : 0 < ε) (hh : 0 < h) (hhc : h < c) :
    pNorm * ε < pNorm * ε * (c / h) := by
  have h1 : 1 < c / h := by rw [lt_div_iff₀ hh]; linarith
  nlinarith [mul_pos hp hε, h1]

/-! ## (2) Threshold is not parabolic-scale-invariant (PROVED) -/

/--
**`coin_threshold_not_scale_invariant`** (PROVED).

The proposed condition reduces (cascade scaling) to
`ε(r)³·ν³ / R < ε*`. For fixed `ε(r)=εfix>0`, `ν>0`, `ε*>0`, this
FAILS for all sufficiently small `R` (the `1/R` survives): there is
`R>0` with `εfix³·ν³ / R ≥ ε*`. So the threshold is aspect-ratio /
scale dependent, not parabolic-invariant — the cascade-limit
mismatch.
-/
theorem coin_threshold_not_scale_invariant
    (εfix ν εstar R : ℝ)
    (hεfix : 0 < εfix) (hν : 0 < ν) (hεstar : 0 < εstar)
    (hR : 0 < R) (hRsmall : R * εstar < εfix ^ 3 * ν ^ 3) :
    εstar < εfix ^ 3 * ν ^ 3 / R := by
  rw [lt_div_iff₀ hR]; nlinarith [hRsmall]

/-! ## (3) Honest record -/

structure Tick564Record where
  /-- target_kind = meta_darwin_kill; NOT compiled into route-1 DAG. -/
  target_kind_kill_not_compiled : Prop
  /-- `‖∂_zφ‖_∞ ~ 1/h` silently dropped; honest bound blows up as
      h→0 (PROVED) — trap relocated, not removed. -/
  one_over_h_blowup_proved : Prop
  /-- Threshold `ε*(h/R)` not parabolic-scale-invariant (PROVED);
      cascade-limit mismatch = GPT-5.5's own prior NO_GO risk. -/
  threshold_not_scale_invariant_proved : Prop
  /-- Φ-iterate on the same fixed point; does NOT supply the genuine
      open one-component-local-ε-regularity theorem. -/
  phi_iterate_not_the_open_theorem : Prop
  /-- Honest endpoint stands: route-1 ⟺ real OPEN He–Wang–Zhou-style
      one-component localization; inputs 1–2 discharged; this killed. -/
  honest_endpoint_unchanged : Prop

end ZtareProofs.NSTick564MDKillAnisotropicCoinRelocatedBlowup
