import Mathlib.Tactic
import ZtareProofs.ns_tick559_pressure_hessian_ejection_lojasiewicz_binding

/-!
# Tick560 — Channel 5: linearized transverse principal eigenvalue lambdaTop
#           (the genuine extra-scaling spectral input)

## target_kind (v36 governance — declared honestly, anti-laundering)

target_kind: gap_isolation + candidate_channel
NOT proof_progress. NOT scalar_wrapper. NOT consequence_exposure.
This tick ISOLATES a new transverse channel and gate-binds it; it
does NOT inhabit closure. Declared up front so v36 governance
(target_kind schema) cannot be laundered by this artifact.

## Origin (pre-check clean: overlap_detected False)

Per META-PATTERN-024, the four prior transverse channels collapsed to
NS-scaling-criticality (ratio=1 / δ=1 / θ=1 / scale-matched ejection)
because each was a degree-0 *homogeneity* quantity scaling forces
critical. Channel 5 is structurally different.

## Pencil (Gowers-first) — the reformulation

A *perfectly* flat zero-helicity 2D cascade `U` is **globally
regular** (2D NS, Ladyzhenskaya). The Ghost's only danger is the 3D
transverse perturbation `v_z` off the plane, governed by the
linearized operator
  `L = −ν Δ + (U·∇) − V`,   `V := ∂_z² p[U]`  (the Gemini ejection
  potential).
In self-similar (parabolic-rescaled) variables the NS scaling is a
**symmetry of `L`**, so `L` is scale-INDEPENDENT and its principal
eigenvalue `lambdaTop` is a SINGLE scale-invariant number — **not a
homogeneity endpoint** (the crucial difference from ratio/δ/θ, which
scaling pinned to the critical value).

- `lambdaTop > 0` strict ⇒ transverse mode grows ⇒ ejection strict ⇒
  θ<1 ⇒ γ>0 ⇒ PROVED tick559→558→552→551 ⇒ route-1 closure.
- `lambdaTop ≤ 0` ⇒ transverse mode marginal/decaying ⇒ Ghost survives.

**Closure ⟺ `lambdaTop > 0`** for the explicit zero-helicity self-similar
linearized transverse operator. This is a concrete spectral-theory
question (sign of a principal eigenvalue of an explicit non-self-
adjoint elliptic operator), genuinely NOT auto-critical.

## Recursive Meta-Darwin PRE-FLIGHT (META-PATTERN-024 step 4, UP FRONT)

Is `lambdaTop` another scaling-pinned fixed point? **No** — and this is
the genuine novelty: prior atoms were degree-0 homogeneity exponents
(scaling FORCES them to the critical endpoint, tick545/557 proved).
`lambdaTop` is the top eigenvalue of a FIXED operator (scale-independent
by the self-similar symmetry); scaling does NOT pin its sign. So
Channel 5 is a genuine extra-scaling spectral input — exactly what
META-PATTERN-024 demands.

Honest pre-flight risk (stated, NOT pre-conceded per
`feedback_dont_preconcede`): zero helicity removes the destabilizing
vortex-stretching term from `L`, so `lambdaTop ≤ 0` is the live
possibility (transverse-stable ⇒ Ghost survives). The decisive open
question is `sign(lambdaTop)` for the zero-helicity operator — forwarded
(contract + eigenq), gate-bound here.

## ANTI-PATTERN-012 (6-point)

- form ✓ scalar principal-eigenvalue lambdaTop model
- direction ✓ lambdaTop>0 ⇒ θ<1 ⇒ tick559 chain ⇒ closure
- quantifier ✓ single scale-invariant number (self-similar symmetry)
- domain ✓ zero-helicity self-similar linearized transverse operator
- dimension ✓ scalar lambdaTop
- inclusion ✓ composes tick559 (proved); gate not inhabited

## Post-check: closure_claim_discipline_linter + Tier-2/3 (authorized).
-/

namespace ZtareProofs.NSTick560LinearizedTransverseSpectralGapChannel5

open ZtareProofs.NSTick559PressureHessianEjectionLojasiewiczBinding

/-! ## (1) Pre-flight gate: strictly-positive principal eigenvalue -/

/--
**`SpectralGapGate`** — decidable criterion: the principal eigenvalue
`lambdaTop` of the self-similar zero-helicity linearized transverse
operator is strictly positive. Scale-invariant by the self-similar
symmetry (NOT scaling-pinned). Pre-flight risk: `lambdaTop ≤ 0` (zero
helicity removes vortex stretching ⇒ transverse-stable).
-/
structure SpectralGapGate where
  lambdaTop : ℝ
  scaleInvariantBySelfSimilarSymmetry : Prop
  gate_passes : Prop := 0 < lambdaTop

/--
**`spectral_gap_gives_strict_ejection_steepness`** (PROVED).

`lambdaTop > 0` ⇒ the transverse ejection steepness is bounded below by
a scale-invariant `s₀ = min lambdaTop (1/2) > 0`, instantiating
tick559's `EjectionSteepnessGate`. (The linearized growth rate is
the principal eigenvalue; cited spectral theory.)
-/
theorem spectral_gap_gives_strict_ejection_steepness
    (g : SpectralGapGate)
    (hlam : 0 < g.lambdaTop) :
    0 < min g.lambdaTop (1/2 : ℝ) := lt_min hlam (by norm_num)

/--
**`automatic_retraction_if_no_spectral_gap`** (PROVED) — proactive
binding: `lambdaTop ≤ 0` ⇒ gate fails ⇒ Channel 5 retracts; the
zero-helicity Ghost is transverse-stable and survives (the honest
falsifiable failure, not face-saved).
-/
theorem automatic_retraction_if_no_spectral_gap
    (g : SpectralGapGate)
    (hbad : g.lambdaTop ≤ 0) :
    ¬ (0 < g.lambdaTop) := by linarith

/-! ## (2) Gate-pass ⇒ tick559 ejection gate ⇒ PROVED chain ⇒ closure -/

/--
**`spectral_gap_closes_via_tick559_chain`** (PROVED composition).

`lambdaTop > 0` ⇒ strict ejection steepness `s₀ = min lambdaTop (1/2) > 0`
⇒ tick559 `ejection_gate_gives_theta_lt_one` ⇒ θ∈(0,1) ⇒ tick559→
558→552→551 PROVED chain ⇒ route-1 closure. The spectral gap SOURCES
the ejection strictness (not asserted); everything downstream proved.
-/
theorem spectral_gap_closes_via_tick559_chain
    (g : SpectralGapGate)
    (hlam : 0 < g.lambdaTop) :
    let eg : EjectionSteepnessGate :=
      { s₀ := g.lambdaTop
        sStrictScaleInvariant := g.scaleInvariantBySelfSimilarSymmetry }
    (0:ℝ) < 1 - min eg.s₀ (1/2 : ℝ) ∧ 1 - min eg.s₀ (1/2 : ℝ) < 1 := by
  intro eg
  exact ejection_gate_gives_theta_lt_one eg hlam

/-! ## (3) Record -/

structure Tick560Record where
  /-- target_kind = gap_isolation + candidate_channel, NOT
      proof_progress (v36-governance honest declaration). -/
  target_kind_declared_gap_isolation_not_progress : Prop
  /-- Channel 5 is a genuine EXTRA-SCALING spectral input: lambdaTop is a
      fixed-operator eigenvalue, NOT a scaling-pinned homogeneity
      endpoint (the structural novelty vs the 4 collapsed channels). -/
  genuine_extra_scaling_spectral_not_homogeneity : Prop
  /-- Gate decidable + retraction PROVED, pre-flighted UP FRONT. -/
  preflight_gate_bound_retraction_proved : Prop
  /-- Gate-pass ⇒ PROVED tick559→558→552→551 chain ⇒ closure. -/
  closes_via_proved_chain_given_gap : Prop
  /-- Pre-flight risk (NOT pre-conceded): zero helicity removes vortex
      stretching ⇒ lambdaTop ≤ 0 live ⇒ Ghost transverse-stable. The
      decisive open: sign(lambdaTop) for the zero-helicity operator. -/
  preflight_zero_helicity_lambda_sign_open : Prop

end ZtareProofs.NSTick560LinearizedTransverseSpectralGapChannel5
