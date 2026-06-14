---
description: "Apparatus-wide canonical primitives for chaotic/dynamical substrates."
---
# Chaos-Substrate Primitives, Apparatus-Wide Canonical Principles

> **Up:** [Documentation map](../README.md)

**Audience:** any agent (human or LLM) authoring a charter, rubric, or implementation for a continuous-chaotic substrate (positive Lyapunov exponent, strange attractor, dissipative flow).

**Purpose:** document controlling principles that prevent common failure modes when the mutator reasons about chaotic systems. These principles are ENFORCED at rubric/charter layer via mutator-visible evidence + GATE layer via deterministic checks when the gates are built (per [GP-144](../../research_areas/seams/engine/GP-144_new_science_claim_discipline_seam.md) seam).

---

## Principle 1, Never fit chaos via trajectory-level RMS over long windows

**Mathematical reality.** In a system with positive leading Lyapunov exponent λ, two copies of the same attractor started from initial conditions differing by ε diverge as δ(t) = ε·e^(λt). Even ε = 10⁻¹⁶ (float-precision limit) becomes e^(λT) after time T. For Lorenz at standard parameters (λ ≈ 0.9): T=20 → 7·10⁷ amplification; T=50 → 5·10¹⁹.

**Consequence.** Any fitness metric that compares simulated trajectory to observed trajectory POINT-WISE over a window T where T·λ_max > 5 will reject the TRUE generator with near-certainty. The metric is measuring the butterfly effect, not the ODE's correctness.

**Banned fitness forms for continuous-chaotic substrates:**
- RMS trajectory error over window T where T·λ_max > 5.
- L2 norm of (simulated state − observed state) at any specific time t > 1/λ_max.
- Any fitness rule that would penalize a provably-correct ODE with infinite error at long horizons.

**Correct fitness forms:**
- **One-step-ahead derivative residual** ‖ẋ_sim(t) − ẋ_obs(t)‖ at observed states. SINDy-native. Used by v5-correct Method A.
- **Weak-form integral residual** ∫ φ(x)[ẋ − f(x)] dt = 0 for test functions φ (Chebyshev, Legendre, compact bump). Derivatives transferred to test function; no point-wise trajectory comparison required.
- **Attractor-geometry metric**: Wasserstein-1 on persistence diagrams, Kaplan-Yorke dimension, Lyapunov spectrum. Coordinate-invariant; measures attractor SHAPE not trajectory.
- **Poincaré-section invariants**: cross-section first-return-map statistics.

**Origin:** gp140_ztare_discovery iter 10 (score 87), mutator proposed "trajectory-level RMS-error fit over a 50-unit window" as Class-A fitness for a perturbed Lorenz-Rössler hybrid (λ_max ≈ 0.9); judge correctly flagged as self-falsifying. Gemini-Pro adversarial analysis 2026-04-24 confirmed this as a general trap.

---

## Principle 2, Autocorrelation time, not FFT peak, for chaotic timescales

**Mathematical reality.** Strange attractors have BROADBAND continuous power spectra. FFT peaks are sampling-frequency aliases or noise, not physical characteristic frequencies.

**Banned for chaotic substrates:**
- FFT / Power Spectral Density peaks as the source for weak-form test-function support radii, Takens delay lags, or observation-window scales.

**Correct forms:**
- **Autocorrelation decorrelation time** τ_decorr = first Δt where normalized autocorrelation C(Δt) drops below 1/e.
- **Lyapunov time** λ_max⁻¹.

**Exception:** substrates with provably discrete spectra (limit cycle, quasi-periodic, steady-state) may use FFT peaks, declare the regime and cite evidence (autocorrelation doesn't decay, or no positive Lyapunov exponent).

**Origin:** gp140 v2.7 charter correction, 2026-04-24.

---

## Principle 3, Coordinate-invariance for Method-B priors

**Mathematical reality.** A Method-B compressibility prior that rejects candidates must be invariant under the diffeomorphism class the substrate admits. A prior that depends on a specific coordinate frame can be defeated by an adversarial C¹ diffeomorphism that preserves the physics but breaks the prior.

**Acceptable Method-B priors for chaotic continuous dynamical substrates:**
- **Lyapunov spectral properties**: sum(λ_i) < 0 for dissipative; one zero exponent for continuous flow.
- **Persistent Homology Betti numbers or persistence diagrams**: topological, diffeomorphism-invariant.
- **Kaplan-Yorke fractal dimension**: derived from Lyapunov spectrum.
- **Sign of Liouville divergence**: tr(J) < 0 is coordinate-invariant in sign (magnitude changes).

**Banned for chaotic continuous substrates:**
- Constant Jacobian Trace (tr J = C with state-independence required). Fails on Rössler; admits volume-preserving adversarial warps.
- Specific eigenvalue values rather than topological eigenvalue class.
- Pointwise state-variable bounds (e.g. |x| ≤ K).
- Coordinate-frame-specific symmetries.

**Origin:** gp140 v2.4 charter, 2026-04-25. See the v2.4 section of `projects/gp140_ztare_discovery/project_charter.md`.

---

## Principle 4, Wasserstein / Bottleneck over exact Betti integers under noise

**Mathematical reality.** Under finite-sample noise and finite Vietoris-Rips filtration scale, topological persistence diagrams gain and lose spurious features. Exact integer Betti equality (β₀ = β₀_true, β₁ = β₁_true) is brittle, the true generator can fail by coincidence at a single filtration scale.

**Banned for chaotic substrates with observation noise:**
- Exact-integer topological gates (`β_cand == β_obs`) at a single filtration scale.

**Correct forms:**
- **Wasserstein-1 distance** W₁(PD_cand, PD_obs) on H₀ ⊕ H₁ persistence diagrams. Continuous metric; integrates over filtration scales.
- **Bottleneck distance** d_B(PD_cand, PD_obs). Continuous; max persistence-pair distance.
- **Admit threshold**: τ_W = admit_factor · 2σ·√T (Fasy et al. 2014 stability bound) OR calibrated noise floor from perturbed-IC simulations of the declared generator. Rubric-declared; candidate cannot influence threshold.

**Origin:** gp140 v2.7 charter correction + [GP-143](../../research_areas/seams/engine/GP-143_continuous_chaotic_kernel_integration_seam.md) kernel integration spec, 2026-04-24.

---

## Principle 5, Input-contract / filter compatibility audit

**Mathematical reality.** A Method A input transformation (Takens delay embedding, scalar-observable reconstruction, non-affine coordinate warp) injects correction terms into the reconstructed system (e.g. d/dt log|det J_φ|) that a Method B filter may then fail to accommodate. The TRUE generator, after the input transformation, may violate the filter's strict assumption by construction.

**Before proposing a Method A + Method B composition, the thesis MUST audit:**
- Does Method A transform the input (scalar → Takens, noisy → denoised, sparse → interpolated)?
- If yes: does Method B's filter class SURVIVE that transformation?
- Known incompatibility pairs:
  - Scalar observable + Takens reconstruction ↔ strict Liouville divergence bound
  - Noisy input ↔ exact algebraic filters (pointwise LLL)
  - Sparse sampling ↔ high-order derivative-residual metrics
  - Short observation window ↔ Lyapunov-spectrum priors requiring convergence

**Compatible alternatives:**
- Full-state observable + strict divergence = OK
- Scalar observable + Lyapunov-spectrum or Betti topological priors (both coordinate-invariant)
- Noisy input + weak-form integration + approximate bias-bounded filters

**Origin:** gp140 v2.6 charter correction, 2026-04-25.

---

## How to invoke these principles in a new substrate

- **Charter**: cite this doc (`see docs/concepts/chaos_substrate_primitives.md`) and enumerate which principles apply.
- **Rubric**: the persona text should reject theses that violate any of these principles; add a dedicated dimension scoring "chaos-substrate principle compliance" with weight ≥5.
- **Evidence surface**: include a terse section restating the principles for mutator-visibility.
- **Gate layer (future)**: when continuum_limit_gate / wasserstein_persistence_gate / coordinate_invariance_gate are implemented, they encode these principles at code level (see [GP-144](../../research_areas/seams/engine/GP-144_new_science_claim_discipline_seam.md) seam for the gate-stack design).

## Known failure modes if these principles are ignored

- **RMS chaos trap**: Class-A rejects true generator, Class-B empty, thesis collapses (gp140 iter 10 case).
- **Fourier trap**: weak-form radii pivot on numerical artifacts (gp140 iter-8 LATTICE-ST case).
- **Coordinate-dependent prior exploit**: adversarial Method A warps break Method B gate (gp140 iter 2 Constant Jacobian Trace case).
- **Exact-equality topological brittleness**: finite-sample noise causes false-negative on true generator (gp140 iter 5 case).
- **Filter-input incompatibility**: TRUE generator self-falsifies after Method A transform (gp140 iter 5 scalar+Liouville case).
