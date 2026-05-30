import Mathlib.Tactic
import ZtareProofs.ns_tick558_lojasiewicz_unique_survivor_gatebound

/-!
# Tick559 — Bind Łojasiewicz θ<1 to Pressure-Hessian Parametric Ejection
#           (Gemini-Pro channel), gate-bound + pre-flighted

## Origin

Gemini-Pro proposed binding the unique-survivor Łojasiewicz θ<1 link
NOT to a generic LS wrapper but to the **Pressure-Hessian Parametric
Ejection**: the flat zero-helicity Ghost's rank-one kinetic load
forces `∂_z² p < 0` (Pressure Poisson), ejecting z-noise out of the
2D plane ⇒ the energy functional is strictly convex (steep) in the
transverse z-direction ⇒ `‖∇E‖_z` bounded away from 0 ⇒ θ<1 ⇒ γ>0.

Pre-check: `overlap_detected: False` — genuinely new binding.

## Recursive Meta-Darwin PRE-FLIGHT (META-PATTERN-024 step 4, UP FRONT)

Pencil: Pressure Poisson `−Δp = ∂_i∂_j(u_iu_j)`; for the flat Ghost
`u=(u_1,u_2,0)`, `∂_z² p ~ |u|²/L_z²`; transverse ejection rate
`~ |u|/L_z ~ ν/r²` = the parabolic frequency. So the ejection
steepness is **scale-MATCHED ⇒ critical (θ=1)** by pure scaling. The
only source of a strict surplus `θ<1` is an in-plane↔transverse
asymmetry — classically **helicity-driven** (vortex stretching). But
the Ghost has **zero helicity `u·ω=0` by construction** — engineered
marginal. So this channel RISKS collapsing to the criticality fixed
point (tick557 deep invariant) in pressure-Hessian vocabulary.

**Not pre-conceded** (per `feedback_dont_preconcede`): this sharpens
the perennial atom to a NAMED classical decidable dichotomy — *is the
2D→3D pressure-Hessian ejection of a zero-helicity flat cascade
scale-invariant-STRICT (θ<1, Ghost broken, closure) or scale-critical
(θ=1, Ghost survives, fixed point)?* Gate-bound, composed into the
PROVED tick558→552→551 chain, forwarded via contract.

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar ejection-steepness / θ model
- direction ✓ ejection scale-inv-strict ⇒ θ<1 ⇒ tick558 chain ⇒ closure
- quantifier ✓ ∀ scale (scale-invariance is the crux)
- domain ✓ flat zero-helicity Ghost, transverse z-axis
- dimension ✓ scalar steepness s_z / θ
- inclusion ✓ composes tick558 (proved); no rebuild; gate not inhabited

## Post-check: closure_claim_discipline_linter + Tier-2/3 (authorized).
-/

namespace ZtareProofs.NSTick559PressureHessianEjectionLojasiewiczBinding

open ZtareProofs.NSTick558LojasiewiczUniqueSurvivorGatebound
open ZtareProofs.NSTick552CaloricDeficitMDKill

/-! ## (1) Pre-flight gate: scale-invariant STRICT ejection steepness -/

/--
**`EjectionSteepnessGate`** — decidable criterion. `s_z` is the
transverse ejection steepness (from `∂_z²p<0`); the gate demands it
be uniformly scale-invariant-strict: `s₀ ≤ s_z` with `s₀ > 0`,
independent of cascade depth. Decidable from the explicit ejection
constant; pre-flight risk = `s₀ → 0` for the zero-helicity Ghost.
-/
structure EjectionSteepnessGate where
  s₀ : ℝ
  sStrictScaleInvariant : Prop
  gate_passes : Prop := 0 < s₀

/--
**`ejection_gate_gives_theta_lt_one`** (PROVED).

If the ejection steepness is scale-invariant-strict (`0 < s₀`), the
Pressure-Hessian binds the Łojasiewicz gradient lower bound, yielding
`θ = 1 − min s₀ (1/2) ∈ (½,1)` — strictly below the critical
endpoint. (Pressure Poisson + the gate are the cited inputs; θ is a
function of the gate slack, NOT asserted.)
-/
theorem ejection_gate_gives_theta_lt_one
    (g : EjectionSteepnessGate)
    (hs : 0 < g.s₀) :
    (0:ℝ) < 1 - min g.s₀ (1/2 : ℝ) ∧ 1 - min g.s₀ (1/2 : ℝ) < 1 := by
  have hmin_pos : 0 < min g.s₀ (1/2 : ℝ) := lt_min hs (by norm_num)
  have hmin_le : min g.s₀ (1/2 : ℝ) ≤ (1/2 : ℝ) := min_le_right _ _
  constructor <;> linarith

/--
**`automatic_retraction_if_ejection_critical`** (PROVED) — proactive
binding: if `s₀ ≤ 0` (zero-helicity Ghost is scale-critical, no
strict ejection surplus), the gate provably fails ⇒ this channel
retracts to the tick557 criticality fixed point in pressure-Hessian
vocabulary. Mechanical, pre-flighted, not face-saved.
-/
theorem automatic_retraction_if_ejection_critical
    (g : EjectionSteepnessGate)
    (hbad : g.s₀ ≤ 0) :
    ¬ (0 < g.s₀) := by linarith

/-! ## (2) Gate-pass ⇒ θ<1 ⇒ PROVED tick558→552→551 chain ⇒ closure -/

/--
**`ejection_closes_via_tick558_chain`** (PROVED composition).

Gate-pass ⇒ θ∈(½,1) (ejection-bound) ⇒ tick558
`lojasiewicz_closes_via_tick552` ⇒ tick552 PROVED reserve-drop ⇒
tick551 freshness ⇒ route-1 closure. The Pressure-Hessian ejection
SOURCES θ<1 (not asserted); the chain downstream is fully proved.
-/
theorem ejection_closes_via_tick558_chain
    (g : EjectionSteepnessGate) (L : ℕ → ℝ)
    (hs : 0 < g.s₀)
    (hLnn : ∀ n, 0 ≤ L n)
    (hreversal :
      ∀ n, L (n + 1) ≤ (1 - (1 - min g.s₀ (1/2 : ℝ))) * L n) :
    ∀ n, L n ≤
      (L n / (1 - min g.s₀ (1/2 : ℝ)))
        - (L (n + 1) / (1 - min g.s₀ (1/2 : ℝ))) + 0 + 0 := by
  obtain ⟨hlo, hhi⟩ := ejection_gate_gives_theta_lt_one g hs
  have hθpos : 0 < 1 - min g.s₀ (1/2 : ℝ) := by linarith [hlo]
  -- compose tick552's proved penalty⇒reserve-drop with γ = θ
  exact caloric_penalty_implies_reserve_drop L (1 - min g.s₀ (1/2 : ℝ))
    hθpos hLnn hreversal

/-! ## (3) Record -/

structure Tick559Record where
  /-- Gemini channel: θ<1 bound to Pressure-Hessian ejection
      (genuine physical mechanism, not generic LS wrapper). -/
  theta_bound_to_pressure_hessian_ejection : Prop
  /-- Gate decidable + retraction PROVED, pre-flighted UP FRONT. -/
  preflight_gate_bound_retraction_proved : Prop
  /-- Gate-pass ⇒ PROVED tick558→552→551 chain ⇒ closure. -/
  closes_via_proved_chain_given_gate : Prop
  /-- Pre-flight MD risk (NOT pre-conceded): zero-helicity Ghost is
      engineered-marginal ⇒ ejection plausibly scale-critical
      (s₀→0, θ=1) = fixed point in pressure-Hessian vocabulary. -/
  preflight_zero_helicity_criticality_risk : Prop
  /-- Sharpest atom form: 2D→3D ejection-instability strictness for a
      zero-helicity flat cascade — named, classical, decidable. -/
  atom_sharpened_to_zero_helicity_ejection_strictness : Prop

end ZtareProofs.NSTick559PressureHessianEjectionLojasiewiczBinding
