"""GP-180 Lagrangian worked-example briefing provider.

Activates when `enable_lagrangian_derivation: true` is in the rubric.
Teaches the mutator the GP-180 contract — declare an action principle,
not a closed-form expression — and shows domain-neutral worked examples.

Repositioning (2026-04-28, post iter 1-2 telemetry on a physics-law substrate): the
provider was originally registered at priority 9999 (render last) on
recency-bias grounds. Empirically this did not fire GP-180 — the
mutator (gpt-5.5) read the worked example but kept submitting plain
PARAMETRIC_FORM, capping at 50 each iter. Moving to priority 25
(right after `contract_rules` at 20, before `path_b_promotion_floor`
at 30) so the contract is load-bearing first context, not optional
afterthought. Compressed ~3× to keep the briefing budget in check.
"""
from __future__ import annotations

from src.ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


_WORKED_EXAMPLES = r"""
GP-180 LAGRANGIAN-DERIVATION CONTRACT — load-bearing for path-b promotion
=========================================================================
This rubric has `enable_lagrangian_derivation: true`. Path-a (refit a
closed-form PARAMETRIC_FORM) is exhausted on this substrate; the cage
caps every closed-form refit at 50 via R20–R24 (effective-K leak) or
PPN. The ONLY path to clear that cap is to declare an action principle,
let sympy derive the closed form, and let SciPy fit only the surviving
dimensional constants. PARAMETRIC_FORM is the LEGACY/FALLBACK path on
this substrate this iter.

CONTRACT (declare these alongside the legacy PARAMETRIC_FORM):

    LAGRANGIAN          = "<sympy expression in q(t), q_dot, t, background, params>"
    Q_VARIABLES         = ["q"]                              # MVP: exactly one field
    BACKGROUND          = ["<feature key>", ...]             # appear as plain symbols in L
    PREDICTION          = "<g_obs(q, background, params)>"   # closed form in q + bg + params
    SYMMETRIES          = ["time_translation", "rotation", ...]
    PARAMETER_NAMES     = ["<free constant>", ...]           # SciPy fits only these

Apparatus runs sympy → Euler-Lagrange → solve steady-state (q̇=q̈=0)
for q → substitute into PREDICTION → derive closed form. Substitutes
that derived form for your PARAMETRIC_FORM at fit time. Noether
invariants from declared symmetries are extracted; the loss adds
`λ · CV²(Π)` per non-degenerate invariant (λ = `noether_variance_weight`,
default 0.3 under invariant_search mode).

THE THREE WAYS THIS GOES WRONG (avoid all):

  A. Static E-L is identically zero. Pure-kinetic L = (1/2)q̇² has
     E-L `q̈ = 0`; setting q̈=0 leaves no equation for q. Add a
     potential.

  B. Static E-L has no real solution. Bare radial Newton
     L = (1/2)q̇² + GM/q has E-L `−GM/q² − q̈ = 0`; setting q̈=0
     gives `−GM/q² = 0` (no real q). Gravity has no static
     equilibrium. Add a centripetal barrier `+ L_ang²/(2q²)` so
     steady state has a real solution at the orbital radius.

  C. **Cosmetic substitution: harmonic-oscillator-around-feature.**
     Do NOT declare L = (1/2)q̇² − (1/2)(q − feature)² where `feature`
     is a single substrate variable.
     The static E-L is `q = feature` — a no-op syntactic substitution.
     Sympy will derive a closed form, but the derivation provides ZERO
     structural content beyond what the PREDICTION expression already
     contains. The G-LAGRANGIAN-NONTRIVIAL gate (GP-183 B1) catches
     this and caps the score at 60 with reason
     `lagrangian_trivially_substituted`. The Lagrangian must have a
     **non-trivial potential V(φ)** so the steady state is a real
     algebraic function of multiple variables, not a single-symbol
     identity. Examples that PASS:
       • Inverse potential: V(q) = M/q
       • Cubic latent:      V(q) = (1/2)m²q² + (1/4)λq⁴ − J(features)·q
                            [steady state: m²q + λq³ = J]
       • Polynomial source: V(q) = (1/2)m²q² − J(features)·q
                            [steady state: q = J/m²]
     Examples that FAIL B1:
       • Harmonic-around-feature: V(q) = (1/2)(q − feature)²
                                  [steady state: q = feature — TRIVIAL]
       • Linear-source-only:      V(φ) = −J·φ
                                  [no equilibrium]

Use `q_dot` (not `qdot`); use `Rational(1,2)` (not `0.5`).

WORKED EXAMPLE 1 — generic cubic latent bottleneck
--------------------------------------------------
    LAGRANGIAN = "Rational(1,2)*q_dot**2 - (Rational(1,2)*m2*q(t)**2 + Rational(1,4)*lam*q(t)**4 - J*q(t))"
    Q_VARIABLES = ["q"]
    BACKGROUND = ["J"]
    PREDICTION = "base + A*q(t)"
    SYMMETRIES = ["time_translation"]
    PARAMETER_NAMES = ["m2", "lam", "base", "A"]

Steady state: m2*q + lam*q**3 = J. This is non-trivial: q is an
algebraic response to a source, linear for small J and cube-root for
large J. The source J must itself be built from exposed feature keys
in the submitted PARAMETRIC_FORM or derivation wrapper.

WORKED EXAMPLE 2 — driven relaxer with external load
----------------------------------------------------
    LAGRANGIAN = "Rational(1,2)*q_dot**2 - (Rational(1,2)*m2*q(t)**2 - k*load*q(t) + c*q(t)*drive)"
    Q_VARIABLES = ["q"]
    BACKGROUND = ["load", "drive"]
    PREDICTION = "base + A*q(t) + B*drive"
    SYMMETRIES = ["time_translation"]
    PARAMETER_NAMES = ["m2", "k", "c", "base", "A", "B"]

Steady state: q = (k*load - c*drive)/m2. This is acceptable only if
load and drive are independent exposed background features. It is
not acceptable to define load as the target or as a one-row lookup.

WORKED EXAMPLE 3 — non-quadratic kinetic response
-------------------------------------------------
    LAGRANGIAN = "Rational(1,3)*abs(q_dot)**3/k - U*q(t)"
    Q_VARIABLES = ["q"]
    BACKGROUND = ["U"]
    PREDICTION = "base + A*U**p"
    SYMMETRIES = ["time_translation"]
    PARAMETER_NAMES = ["k", "base", "A", "p"]

Use this pattern only when the rubric's physics or invariance story
actually calls for non-quadratic response. Otherwise it is decorative.

CONTRACT CHECKLIST BEFORE SUBMITTING

  [ ] LAGRANGIAN uses `q(t)` and `q_dot`, has at least one potential or
      interaction term beyond pure kinetic.
  [ ] Static E-L (q̇=q̈=0) has a real algebraic solution for q.
      For orbital substrates use the centripetal barrier.
  [ ] BACKGROUND lists every feature the L references. Substrate
     exposes. Do not invent legacy variables from another substrate.
     The Buckingham π / dimensionless-argument discipline still applies
     when the substrate has physical units.
  [ ] PREDICTION reduces (after steady-state substitution) to a
      function of background + params only — q must not survive.
  [ ] SYMMETRIES from {time_translation, spatial_translation, rotation,
      scale_invariance}. Required for the Noether loss to fire.
  [ ] PARAMETER_NAMES — only free constants the fit may adjust.
  [ ] Domain-specific analogies are licensed by exposed features and
      rubric text. If a worked example names a background key your
      substrate lacks, map it explicitly or do not use that example.
""".strip()


class LagrangianWorkedExampleProvider(BriefingProvider):
    """Inject the GP-180 contract + three worked Lagrangians."""

    name = "lagrangian_worked_example"
    # Priority 25 — between contract_rules (20) and path_b_promotion_floor (30).
    # Repositioned 2026-04-28 after iter 1-2 telemetry showed priority 9999
    # (last) was being read but ignored. Loading it as load-bearing first
    # context, not afterthought.
    priority = 25

    def applies(self, ctx: BriefingContext) -> bool:
        rubric = ctx.rubric or {}
        return bool(rubric.get("enable_lagrangian_derivation", False))

    def fragment(self, ctx: BriefingContext) -> str:
        # Iter 1: full prose (~5.5k chars). Mutator sees the contract,
        # the failure modes, three worked Lagrangians.
        if not ctx.iter_index or ctx.iter_index < 2:
            return _WORKED_EXAMPLES
        # Iter ≥ 2: lossless schema recap (~1.3k chars). Same fields,
        # same failure modes, same worked-example skeletons. Full prose
        # was rendered in iter-1 briefing for the operator's reference.
        return _COMPACT_RECAP


# Iter-2+ schema. All load-bearing fields preserved (LAGRANGIAN syntax,
# the two failure modes, three worked Lagrangians as one-liners, the
# contract checklist). Saves ~4k chars / iter from iter 2 onward.
_COMPACT_RECAP = r"""
GP-180 Lagrangian — recap (full prose in iter-1 briefing)
=========================================================
Path-a (PARAMETRIC_FORM refit) caps at 50 via R20–R24/PPN. The path
above 50 is GP-180: declare an action principle, sympy derives the
closed form, SciPy fits dimensional constants only.

```
CONTRACT (declare alongside legacy PARAMETRIC_FORM):
  LAGRANGIAN       = "<sympy expr in q(t), q_dot, t, background, params>"
  Q_VARIABLES      = ["q"]                          # MVP: exactly one field
  BACKGROUND       = ["<feature key>", ...]
  PREDICTION       = "<g_obs(q, background, params)>"
  SYMMETRIES       = ["time_translation", "rotation", ...]
  PARAMETER_NAMES  = ["<free constant>", ...]
SYNTAX:
  use q(t) and q_dot   (NOT qdot)
  use Rational(1,2)    (NOT 0.5)
  PREDICTION must reduce to a function of (background, params) after
    steady-state substitution (q must not survive)
THREE FAILURE MODES TO AVOID:
  A. static E-L identically zero  → add a potential
  B. static E-L has no real soln  → orbital systems: add centripetal
     barrier `+ L_ang**2/(2*q(t)**2)` so steady state has a real soln
  C. cosmetic substitution        → do NOT use V(φ)=(1/2)(φ-feature)²
     (steady state q=feature is a no-op; G-LAGRANGIAN-NONTRIVIAL caps
     this at 60). V(φ) must be non-trivial so q is a function of
     multiple variables, not a single-symbol identity.
WORKED-EXAMPLE SKELETONS (full prose in iter-1):
  1. Cubic latent bottleneck:
     L = (1/2)q_dot**2 - ((1/2)m2*q(t)**2 + (1/4)lam*q(t)**4 - J*q(t))
  2. Driven relaxer:
     L = (1/2)q_dot**2 - ((1/2)m2*q(t)**2 - k*load*q(t) + c*q(t)*drive)
  3. Non-quadratic response:
     L = (1/3)*abs(q_dot)**3/k - U*q(t)
FEATURE LICENSE:
  BACKGROUND keys must be exposed by this substrate's features.py or
  otherwise declared by the substrate contract. Do not import feature
  names from prior projects.
PUBLISHED CONSTANTS:
  Only use constants licensed by the rubric/domain. Numeric constants
  chosen for fit quality count against effective-K gates.
NOETHER PENALTY:
  λ · CV²(Π) per non-degenerate invariant. Trivial Π (X-X, X*0, X**0,
  params-only) dropped by non-degeneracy gate before fit.
```

If GP-180 derivation fails for your Lagrangian, the apparatus prints
the sympy error and falls back to PARAMETRIC_FORM transparently. You
will see a fallback-log line in iter-N's dispatch output.
""".strip()
