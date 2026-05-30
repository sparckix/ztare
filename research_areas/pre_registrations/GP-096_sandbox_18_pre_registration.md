# Pre-Registration — GP-096 Sandbox 18 (Division A, SEALED)

**Status**: Division A sealed artifact. Division B agents must not read this file.
**Date**: 2026-04-19
**Protocol**: GP-072 M-form information isolation

---

## 1. Ground Truth System

### Equation of Motion

```
x''(t) + alpha * |x'(t)|^beta * sign(x'(t)) + omega^2 * x(t) + mu * x(t)^3 = 0
```

**System class**: Strengthened Duffing oscillator with fractional (sub-linear) power-law damping  
**Shorthand**: DFDO (Duffing + Fractional Damping Oscillator)

### Exact GT Parameters

| Parameter | Value | Role |
|-----------|-------|------|
| alpha     | 0.03  | Damping coefficient |
| beta      | 0.73  | Damping exponent (fractional, sub-linear: beta < 1) |
| omega     | 1.0   | Linear stiffness (angular frequency) |
| mu        | 0.18  | Cubic (Duffing) stiffness coefficient |
| x(0)      | 3.2   | Initial displacement |
| x'(0)     | 0.0   | Initial velocity |

**Parameter correction note**: The originally drafted spec listed alpha=0.41 with x(0)=3.2. Numerical integration of those parameters yields only 3 positive peaks before the trajectory damps to near-zero (sub-machine-precision). Alpha was corrected to 0.03 — same physics class, same beta, same omega and mu — to sustain 45+ peaks as required by the evidence plan. The GT is alpha=0.03.

### Integration Protocol

- Solver: `scipy.integrate.solve_ivp`, method RK45
- max_step: 0.005
- rtol: 1e-8, atol: 1e-10
- t_span: [0, 600]
- t_eval: np.arange(0, 600, 0.001)
- Peak detection: `scipy.signal.argrelmax` with order=5; positive peaks only

---

## 2. Observable and Evidence Plan

**Observable**: Positive local maxima of x(t). Peak n is defined as the n-th time x(t) achieves a local maximum with x > 0. The pair (u, v) = (t_n, x(t_n)).

| File | Peaks | t range | v range | Visibility |
|------|-------|---------|---------|------------|
| evidence.txt | 1–30 | [4.14, 160.66] | [3.091, 0.370] | Division B visible |
| evidence_holdout.txt | 31–40 | [166.89, 223.31] | [0.325, 0.075] | Hidden (Division A only) |
| evidence_farther_tail.txt | 41–45 | [229.60, 254.74] | [0.061, 0.023] | Hidden (Division A only) |

---

## 3. Theoretical Expectations

### Energy-Balance Approximation

For the pure fractional damping equation `x'' + alpha |x'|^beta sign(x') + omega^2 x = 0`, an energy-balance argument gives:

```
A(t) ~ C * (1 + c*t)^(-1/(1-beta))
```

where C, c are constants depending on alpha, omega, beta. For beta=0.73 this gives exponent -1/0.27 ≈ -3.70.

The Duffing coupling (mu * x^3 term) breaks clean separability. At high amplitude the effective frequency is amplitude-dependent:

```
omega_eff(A) ≈ sqrt(omega^2 + (3/4)*mu*A^2)
```

At low amplitude (peaks 30+, A < 0.5) the Duffing correction becomes negligible and the pure fractional damping envelope dominates.

**Exact closed form: unknown.** The system is not integrable in the classical sense. The envelope is power-law-like but with an amplitude-dependent period that makes simple analytical inversion to (n → A_n) non-trivial.

### Expected decay shape (rough)

- Early peaks (1–10): faster apparent decay rate (Duffing contribution active)
- Mid peaks (10–30): transition to asymptotic power-law regime
- Late peaks (30–45): dominantly power-law, period slowly increasing
- Far tail (41–45): power-law envelope most clearly exposed; exponential approximation will predict too-fast decay here

---

## 4. Pre-Registered Outcome Types

**Outcome A — Correct topology, all gates passed**
- Synthesized form correctly captures power-law envelope (or approximation that handles the far-tail accurately)
- Passes evidence.txt fit, evidence_holdout.txt, AND evidence_farther_tail.txt within tolerance
- May not recover exact GT equation form; functional equivalence on observable suffices
- This is the success outcome

**Outcome B — Wrong topology, passes visible window**
- Synthesized form fits evidence.txt well (exponential, stretched exponential, or polynomial fit)
- Fails on holdout and/or farther_tail because exponential decays too fast relative to power-law
- This is the primary gaming/ceiling outcome expected for naive grammar trees
- Diagnostic: holdout residual >> visible-window residual

**Outcome C — Stagnation**
- Validator rejects all candidates; score plateaus below threshold
- Root cause: grammar too restrictive, or fitness landscape too flat near zero amplitude
- Diagnostic: top score unchanging for many iterations

**Outcome D — Grammar ceiling**
- Grammar generates candidates that fit visible peaks but lacks primitives to express power-law envelope
- Similar to Outcome B but with less evidence of gaming; more a vocabulary limitation
- Diagnostic: best-of-run formula is exponential with no power-law component

---

## 5. Discriminator Design Criteria

### Primary discriminator: far-tail gate (peaks 41–45)

The far-tail is the strongest discriminator between power-law and exponential envelope:

| Peak | u | v (GT) | Exponential extrapolation (rough) |
|------|---|--------|-----------------------------------|
| 41 | 229.60 | 0.0612 | ~0.0150 (under-predicts) |
| 42 | 235.88 | 0.0492 | ~0.0110 |
| 43 | 242.17 | 0.0391 | ~0.0080 |
| 44 | 248.45 | 0.0305 | ~0.0058 |
| 45 | 254.74 | 0.0234 | ~0.0042 |

An exponential fit to peaks 1–30 will under-predict far-tail amplitudes by roughly 4x. A power-law fit will extrapolate correctly.

### Secondary discriminator: holdout residual ratio

- Compute: `holdout_RMSE / visible_RMSE`
- Healthy model: ratio ≈ 1.0–1.5 (generalizes)
- Gaming/exponential fit: ratio > 3.0 (collapses in holdout)

### Tertiary discriminator: period-amplitude relationship

The inter-peak spacing (u_{n+1} - u_n) increases as amplitude decreases. This is consistent with a nonlinear restoring force. A model that captures only amplitude decay without period drift will fail on u-coordinates of holdout peaks.

---

## 6. Division A Seal

This file contains GT parameters, derivation notes, and discriminator design. It must not be injected into mutator or judge prompts. Division B sees only `evidence.txt` and the rubric.

**Sealed by**: Division A agent, GP-072 protocol
**Date**: 2026-04-19
