# GP-141 Seam — Continuous A+B reference implementation lineage

> **Seam metadata** · `seam_id:` GP-141 · `track:` mission · `status:` open, 2026-04-24 very late. · `last_updated:` 2026-05-08


**Status:** open, 2026-04-24 very late.
**Parent seam:** GP-140 ztare_discovery (hybrid A/B charter).
**Parallel lineage:** INS-046 (CA-bridge discrete A+B), INS-047 (adaptive-threshold gaming), INS-048 (judge-capacity decisive), INS-049 (mutator-diversity decisive — this seam).

## Eigenquestion

Is the A+B pattern (Method A = behavioral-fit solver; Method B = argmin/Pareto ranker + orthogonal physical-invariant prior) stable enough across substrate classes to be embedded as a first-class reference implementation in the mutator's prompt surface, rather than re-derived per-iter?

## Empirical lineage

### 2026-04-23 (CA-bridge, INS-046)

- Substrate: deterministic radius-2 binary CA, 2^32 rule space
- Cold LLM tool-less: failed at step 2 (0.02 confidence)
- Apparatus Method A (constraint propagation, 80 LOC): 2-candidate behavioral-equivalence class in 0.6s
- Apparatus Method A experimental-design (IC library): correct rule pinned in 0.06s
- Verdict: A+B pattern works on discrete bounded state-space; Method B's orthogonal-prior role is structural (distinguish law from coincidence)
- Code: `projects/ca_bridge_test/apparatus_candidate/apparatus_v1.py` + `apparatus_v2_framer.py`
- Insight: separation of theoretical intervention-design (LLM competence) from computational intervention-execution (apparatus competence)

### 2026-04-24 mid (gp140 v2 iter-9 GAMED, INS-047)

- Substrate: radius-3 binary CA
- Thesis: adaptive τ = 1.25 × NDLC_min (rank statistic dressed as MDL)
- Loop score gpt-4.1: 87; three-panel blind review: 57; empirical falsification: 20/20 trials of HW=16 random rules certify non-empty
- Verdict: self-referential threshold construction is a Newton-mode gaming pattern
- Fix: charter v2.1 bans thresholds defined as functions of candidate-set statistics
- Meta-runner queue item 7 (adaptive_threshold_gaming_prevention_contract_stub) captures this for future hardening

### 2026-04-24 late (gp140 v2.1 iter-2 NML admit-gate misuse)

- Substrate: noisy Lorenz-96 proposed by thesis
- Thesis: Takens-SINDy + Shtarkov NML regret bound as absolute admit gate
- Score o3 judge: 68; lorenz_bridge_test empirical falsification on chaotic holdout: NML gate admits 22/25 overfit candidates because NLL term dominates penalty
- Verdict: regret bounds are minimax ceilings, NOT admission thresholds
- Fix: charter v2.2 bans admit-gate misuse; mandates argmin_L or Pareto ranking; requires orthogonal physical-invariant prior
- Code: `projects/lorenz_bridge_test/apparatus_candidate/apparatus_v2b_nml_full.py` (faithful thesis impl; admits all 22)

### 2026-04-24 late (operator v3 combined, reference pattern emerges)

- Substrate: bespoke chaotic perturbed-Lorenz family
- Apparatus v3 = argmin_L (NML stochastic complexity) + Liouville dissipativity (orthogonal) + Kaplan-Yorke dim (second orthogonal) + Pareto front over (L, k)
- On chaotic substrate with derivative-residual metric: v3 argmin picks the SINDy candidate with exact k=10 (matching truth), matrix distance 0.18 from true generator
- v3 argmin's L lower than true rule's L (finite-sample fit beats generator on this window)
- Side-by-side: v2 over-permissive (K_MAX trivial admits all 25), v2b now discriminates correctly (2/25 admitted), v3 picks one answer with full ranking context
- Code: `projects/lorenz_bridge_test/apparatus_candidate/apparatus_v3_combined.py` + `ode_generator.py::sample_nontrivial_chaotic_ode`

### 2026-04-24 very late (gp140 v2.2 iter-1 CAGE, partial compliance)

- Mutator: o3
- Thesis: MILP branch-and-bound over integer coefficient box `|c| ≤ 3` (COMPLETE enumeration within the box) + BIC + Liouville + K-Y
- Score gpt-4.1: 92; score o3: 62
- Partial compliance: uses absolute `L ≤ 150 bits` alongside invariants — residual admit-gate pattern despite v2.2 ban
- Blind-panel equivalent: N1 vulnerability (true generator might be outside the `|c| ≤ 3` box) unaddressed; gemini-pro's iter-1 exploited this exactly

### 2026-04-24 very late (gp140 v2.2 iter-1 LATTICE, gemini-pro mutator, reference-pattern candidate)

- Mutator: gemini-2.5-pro
- Thesis: **LLL lattice basis reduction** (Lenstra-Lenstra-Lovász 1982) as Method A — unbounded integer lattice search, polynomial-time in data precision (NOT coefficient magnitude); Method B = **Pareto front over (Fit Error, BIC Complexity) + Liouville dissipativity + Persistent Homology Betti (β₀=1, β₁=2)** — explicit "no absolute threshold gate"
- Score o3: **83**
- Compliance: v2.2-clean. Named algorithm (LLL) with polynomial bound, two orthogonal priors (Liouville + Persistent Homology), Pareto ranking not gate, non-prior-sufficient substrate (bespoke BFractal-3D), edge-case reporting, explicit falsifiable forward observable
- Architectural novelty: LLL moves Method A from *search* to *structural extraction* of integer relations from the observation matrix. N1 vulnerability (true generator outside search box) is structurally bypassed — lattice reduction has no a-priori coefficient bound

## The reference pattern (distilled)

A Newton-class generative primitive for continuous dynamical substrates composes:

### Method A (behavioral solver)
Primitive must EMIT the complete behavioral-equivalence class consistent with observations up to a stated fit tolerance. Preferred forms in ascending order of structural completeness:
- SINDy sparse regression across λ-grid (bounded, grid-dependent) — apparatus_v3_combined baseline
- MILP branch-and-bound over bounded coefficient box (complete-in-box but N1-vulnerable) — CAGE class
- **LLL lattice basis reduction over integer-relation space (unbounded, structurally complete)** — LATTICE class

### Method B (ranker + orthogonal priors)
Primitive must EMIT a ranking (argmin_L or Pareto front), NOT an absolute admit gate. Must include at least one orthogonal physical-invariant prior. Preferred prior stack:
- **BIC or Rissanen stochastic complexity** (compressibility)
- **Liouville dissipativity** `tr(J) < threshold` on dissipative substrates
- **Kaplan-Yorke fractal dimension** bound for chaotic attractors
- **Persistent Homology Betti numbers** (β₀, β₁) for topological attractor constraints
- (For integer-arithmetic substrates: PSLQ integer-relation certification)

### Metric discipline
For chaotic continuous substrates, evaluate fit quality via **derivative-residual RMSE at observed states**, NOT full trajectory re-integration. Butterfly effect invalidates trajectory-matching over horizons longer than Lyapunov time.

### Substrate discipline
- Must be non-prior-sufficient per Evidence Set B (INS-045): not textbook arithmetic, not OEIS-indexed, not canonical ODE family
- For chaotic substrates: verify genuine chaos via finite-time Lyapunov > threshold (0.1-0.5 range). Random sparse-polynomial ODE without this filter admits dissipative-fixed-point systems that are trivial

## Implementation artifacts

### Operator reference code
- `projects/ca_bridge_test/apparatus_candidate/apparatus_v1.py` — discrete constraint propagation
- `projects/ca_bridge_test/apparatus_candidate/apparatus_v2_framer.py` — experimental-design disambiguation
- `projects/lorenz_bridge_test/apparatus_candidate/apparatus_v1_sindy.py` — SINDy Method A with derivative-residual
- `projects/lorenz_bridge_test/apparatus_candidate/apparatus_v3_combined.py` — argmin_L + Liouville + KY + Pareto Method B
- `projects/lorenz_bridge_test/ode_generator.py::sample_nontrivial_chaotic_ode` — substrate generator with genuine chaos enforcement

### Mutator-emitted reference (LATTICE, gemini-pro, 2026-04-24)
- Source: `projects/gp140_ztare_discovery/history/1777000664_iter1_score_83_gp140_ztare_discovery.md`
- Pattern: LLL + Pareto + Liouville + Persistent Homology
- Score: 83 under o3 judge (honest ceiling estimate: 90-95 if Millennium-nudge added)

## 2026-04-25 update — Weak-form LLL locked + Constant-Trace anti-pattern

### Iter-2 LATTICE-v2 (gemini-pro mutator, score 42 under o3)

- **Method A extension (KEEP):** Weak-form LLL via integration by parts. Observation is integrated against a library of smooth compactly-supported test functions ψ_k(t), with the derivative transferred onto the known-smooth test function via IBP. Low-pass filter in operator form. Extends LLL's noise tolerance from σ < 0.001 (pointwise) to σ ≥ 0.01 (weak-form). Origin: gemini-2.5-pro, 2026-04-25.
- **Method B regression (ANTI-PATTERN):** Constant Jacobian Trace filter (`tr(J) = C`, state-independent). Two fatal flaws:
    - False negative: rejects Rössler-class chaos whose trace `a + x - c` is state-dependent. A universal scientific instrument cannot refuse textbook chaos (Rössler, Chua, Duffing, double pendulum).
    - False positive: constant trace is invariant under volume-preserving diffeomorphisms. An adversarial Method A can construct non-physical rational-fraction warps whose trace is still constant; Method B admits them as "law-certified."
- **Lesson:** Method B priors must be **coordinate-invariant under the substrate's admissible diffeomorphism class**. For chaotic continuous dynamics: Lyapunov spectral properties (one zero exponent for flow; negative sum for dissipation), Persistent Homology Betti numbers, Kaplan-Yorke fractal dimension — all invariant by construction. Sign of Liouville divergence is also invariant (but magnitude under diffeomorphism is not).
- **Charter update:** v2.4 adds an explicit coordinate-invariance requirement with a blacklist of banned forms (Constant Trace, specific eigenvalues, pointwise state bounds, frame-specific symmetry).

### Reference-pattern distilled (updated)

**Method A (Level 3, noise-robust):**
- Weak-form LLL: integration-by-parts + smooth test functions + scaled integer lattice
- Input: noisy scalar/vector trajectory
- Output: integer-relation behavioral equivalence class, basis form
- Complexity: poly-time in (data length, precision, polynomial degree)

**Method B (coordinate-invariant):**
- Ranker: argmin_L or Pareto front over (L, k)
- Orthogonal priors (at least one required, preferably two from different invariant classes):
    - Lyapunov spectral: one zero exponent + negative sum for dissipative
    - Topological: Persistent Homology Betti (β₀, β₁) of reconstructed attractor
    - Fractal-dimension: Kaplan-Yorke dim ∈ substrate-appropriate band
    - Sign-only Liouville: `sign(tr(J)) < 0` without constant-magnitude requirement
- BANNED forms: Constant Jacobian Trace, specific eigenvalue values, pointwise bounds, frame-specific symmetry

## 2026-04-25 iter-3 update — prior/substrate compatibility + LLL scope caveat

### Iter-3 (gemini-pro, score 68 under o3)

- **Self-correction signal:** mutator dropped Constant Trace from iter-2 before derived_constraints injection fully landed. Replaced with Dimensional Consistency. Score jumped 42 → 68 purely on avoiding the earlier banned pattern.
- **New weakest-point 1 — prior/substrate contradiction:** thesis paired Dimensional Consistency Method B prior with Rössler substrate. Rössler (like Lorenz, Chua, Duffing) is conventionally written in DIMENSIONLESS form; assigning units to state variables forces mismatched dimensional sums. The true generator would be rejected by its own audit. **Rule:** Method B prior must be valid on the committed substrate class. Dimensional-consistency priors ↔ dimensioned substrates; symmetry priors ↔ substrates exhibiting that symmetry; trace priors already banned per v2.4.
- **New weakest-point 2 — LLL on nonlinear weak-form:** o3 judge noted nonlinear basis terms (x·y, x·z, y·z, x²) when integrated against test functions inject non-zero-mean systematic bias that shatters exact algebraic lattice dependence. Weak-form LLL is rigorous ONLY for linear weak-form systems. On nonlinear ODEs (which most chaotic substrates are), exact integer recovery is impossible; best-case is approximate with explicit bias estimate.
- **Lesson:** the Weak-form LLL Method A reference pattern has a SCOPE RESTRICTION that must be stated. Proposals using WLLL on nonlinear substrates without addressing bias are scope-overreach.

### Charter v2.5 hardening

Added two hard constraints:
- **Prior/substrate compatibility audit** — thesis must show `"this prior is valid on this substrate class because [property]"`. Silent pairing = downgrade.
- **LLL scope caveat** — if substrate is nonlinear, thesis must (a) linearize around fixed points and handle nonlinearity separately, (b) use implicit SINDy-PI with rational priors, or (c) adaptive bias-correction weak-form. Primitive must report bias estimate.

### Reference-pattern update

Method B compatible-prior catalog (by substrate class):

| Substrate class | Acceptable priors | Banned priors |
|---|---|---|
| Dimensioned physical ODEs (N-S, EM, population dynamics) | Dimensional consistency, conservation laws, thermodynamic bounds, Lyapunov-spectrum properties | Frame-specific symmetry, state-variable bounds |
| Non-dimensionalized canonical chaos (Lorenz, Rössler, Chua, Duffing) | Lyapunov-spectrum properties, Persistent Homology Betti, Kaplan-Yorke dim, sign-only Liouville | Dimensional consistency, Constant Jacobian Trace, specific eigenvalues |
| Integer-coefficient / Diophantine dynamics | Integer-relation certification (PSLQ), lattice-minimum argmin | Dimensional consistency (unless integers carry units) |
| Discrete deterministic state-space (CA, Boolean networks) | Description-length bounds, symmetry-group analysis of the transition function | Continuous-dynamics priors |

## Open items

1. **Embed LATTICE pattern as mutator context** (this seam, evidence.txt Evidence Set I, charter v2.3 reference block).
2. **Implement LLL-based Method A** as a first-class primitive in `src/ztare/primitives/` (not yet done — gemini-pro specified but we haven't built).
3. **Implement Persistent Homology Betti prior** (requires `gudhi` library; not yet tested).
4. **Meta-runner queue item**: promote `adaptive_threshold_gaming_prevention_contract_stub` (queue #7) to include admit-gate-misuse as a second gaming pattern.
5. **Cross-substrate validation**: run LATTICE-pattern apparatus on at least one other substrate class (non-local recurrence, scale-dependent numerical) to confirm the pattern is substrate-class-general.

## Private / public posture

Private during gp140 closure. Promote relevant findings to paper5 once lineage is stable. LATTICE-specific claims need gemini-pro-authorship attribution in any public writeup.
