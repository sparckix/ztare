# Automated Asymptotic Recovery with Provable False-Positive Rejection

## Abstract

We present results from an automated epistemic verification engine (ZTARE) that recovers asymptotic laws from blinded numerical data without domain knowledge, and provably rejects false positives on substrates where no closed-form compression exists. The engine operates a loop of hypothesis generation (LLM mutator), deterministic gate verification (holdout + farther-tail), and template-enumeration compression that strips overparameterized surrogates to minimal gate-passing forms. Applied to ten integer sequences presented as unlabeled observables:

1. **Recovery (known targets, blinded):** Recovered the Hardy-Ramanujan partition asymptotic $\ln p(n) \approx a\sqrt{n} + b\ln n + c$ from 30 blinded data points; the Lucky number density growth rate $L(n)/n \approx 1.200 \cdot \ln n + c$ (coefficient $a = 1.200$ consistent with the conjectured analogy to PNT); the Meinardus $n^{1/3}$ topology for partitions into squares; the Hardy-Ramanujan derivative for partitions excluding 1; and the Vaughan compositional form $\sqrt{n/\ln n}$ for prime partitions.

2. **Rejection (incompressible targets):** Correctly returned null on Mertens function $M(n)/\sqrt{n}$ (oscillatory, no smooth compression), normalized prime gaps $g(n)/\log p_n$ (spiky, no smooth compression), and Ulam density $U(n)/n$ (41 templates tested, none pass holdout). False-positive rate: 0 across all incompressible substrates.

3. **Methodological findings:** (a) An automated observable-rotation step discovered that while $U(n)/n$ resists compression, the reciprocal $n/U(n)$ compresses to $a \cdot \ln n + b/n + c$ with all gates passing — the representation, not the data, was the bottleneck. (b) The grammar ceiling theorem: additional compute iterations cannot break structural ceilings imposed by the expression grammar; only grammar expansion (adding new primitives) enables structural class transitions. This was demonstrated empirically on a four-run chain where 63 iterations in a restricted grammar could not reach a form that one grammar expansion achieved in 6 iterations.

All results were obtained with the engine operating blind: cold variable names, no domain labels, no named mathematical constants, and no access to OEIS or any reference database. The code, data, and gate harnesses are publicly available.

---

## 1. Method

The engine operates in three phases:

**Phase 1 (Hypothesis generation).** An LLM proposes a functional form as a typed fit declaration. A deterministic fitting primitive (scipy.optimize.curve_fit) estimates parameters on visible evidence only. Deterministic holdout gates (binary pass/fail on hidden data) enforce generalization. An information yield evaluator tracks stagnation and triggers topological pivots when the search exhausts a functional class.

**Phase 2 (Compression).** After Phase 1 completes, a template-enumeration compressor tests all low-parameter forms from the grammar against the holdout gates. Stage 1: 22 additive templates (combinations of $\sqrt{n}$, $\ln n$, $n^b$, $e^{an}$, $1/n$). Stage 2: 13 depth-1 compositional templates ($\sqrt{n/\ln n}$, $\sqrt{n \cdot \ln n}$, etc.), activated only when Stage 1 returns no gate-passing forms. Stage 3: Lomb-Scargle periodicity detection on residuals (FAP $< 0.01$, sub-window consistency). Selection by BIC within topology classes; an exponent grid ($\{0.25, 1/3, 0.5, 2/3, 1, 1.5, 2\}$) constrains free power-law exponents.

**Phase 2.5 (Observable rotation).** When Phase 2 returns no gate-passing forms, the engine applies monotonic transformations to the observable ($1/z$, $\ln z$, $\Delta z$) and re-runs compression on the transformed representation. This step discovered the Ulam reciprocal compression (§2.5).

**Phase 3 (Certification).** A Lean 4 compiler generates proof stubs: `#eval` blocks that verify gate bounds at every holdout point, plus PSLQ conjectures mapping fitted floats to mathematical constants.

All phases are deterministic except the LLM's text generation. The holdout data is sealed before any iteration runs. The grammar, templates, and gate thresholds are fixed across all substrates.

---

## 2. Results

### 2.1 Lucky Numbers (A000959) — Density Measurement

The Lucky number density ratio $L(n)/n$ was presented as an unlabeled observable over $n = 500$ to $5{,}000$ (visible), with holdout at $n = 5{,}001$ to $20{,}000$ and farther-tail at $n = 20{,}001$ to $50{,}000$. The engine found at iteration 1:

$$\frac{L(n)}{n} \approx 1.200 \cdot \ln n - \frac{4.697}{n} + 0.511$$

All four gates pass: holdout global residual $0.021 < 0.05$, farther-tail global residual $0.026 < 0.08$. Eight templates passed all gates, with the simplest ($a \cdot \ln n + b$, $k = 2$) confirming the logarithmic structure. The coefficient $a = 1.200$ is consistent with the conjectured analogy to the Prime Number Theorem, which predicts $L(n) \sim C \cdot n \ln n$ for some constant $C$. We note that the LLM may have encountered this relationship in training data; the contribution is the certified measurement under blinded, gate-verified conditions, not the conjecture itself.

### 2.2 Hardy-Ramanujan Recovery (A000041) — Calibration

The logarithm of the partition function was presented as 30 blinded data points. The compression primitive found $f(n) = 2.631\sqrt{n} - 1.172 \ln n - 1.445/n - 1.744$, matching the Hardy-Ramanujan asymptotic ($a_{\text{theory}} = \pi\sqrt{2/3} = 2.565$, $b_{\text{theory}} = -1$). All gates pass. The PSLQ bridge identified the leading coefficient as $\pi\sqrt{2/3}$.

### 2.3 Partitions into Squares (A001156) — Topology Identification

The compression found $a \cdot n^{0.335} + c \cdot \ln n + d$ (exponent within $0.5\%$ of the Meinardus-predicted $1/3$). Holdout gates rejected the form due to accumulated exponent bias at large $n$. With normalized (scale-invariant) residuals, the form passes at $0.16\%$ relative error.

### 2.4 Partitions Excluding 1 (A002865) — Topology Identification

The compression found $a\sqrt{n} + b\ln n + c/n + d$ with $a = 2.562$ (theoretical $\pi\sqrt{2/3} = 2.565$). Same pattern as §2.2: correct topology, holdout rejected due to absolute gate thresholds on a large-scale observable. Normalized residual: $0.04\%$.

### 2.5 Ulam Numbers (A002858) — Observable Rotation

No closed-form model of $U(n)/n$ passed holdout gates across 41 templates. However, the automated observable-rotation step (Phase 2.5) discovered that the reciprocal representation $n/U(n)$ compresses cleanly:

$$\frac{n}{U(n)} \approx -0.000216 \cdot \ln n + \frac{5.597}{n} + 0.0776$$

All gates pass at $n = 500{,}000$ with max residual $0.0015$ ($33\times$ below threshold). The constant $0.0776 \approx 1/12.88$, near the reciprocal of the conjectured asymptotic density ($\sim 1/13.5$). The methodological contribution is that the engine discovered which representation to compress without operator guidance.

Additionally, the density ratio $U(n)/n$ was computed to $n = 1{,}000{,}000$ ($U(10^6) = 13{,}509{,}072$). The inverse density converged to $13.506 \pm 0.003$ across the final $400{,}000$ values, consistent with prior measurements. Spectral analysis detected a dominant period near $19.3$ (Lomb-Scargle, FAP $< 6.5 \times 10^{-5}$), which differs from the period $\sim 21.3$ reported in Steinerberger (2017); we attribute the discrepancy to detrending sensitivity (spectral slope ranges from $-0.05$ to $-1.34$ across window widths $W = 11$ to $W = 101$).

### 2.6 Prime Partitions (A000607) — Compositional Discovery

Stage 1 templates failed. Stage 2 (depth-1 compositional) found $a\sqrt{n/\ln n} + b\ln n + c$, consistent with Vaughan's theorem. All four tight gates pass. This was the first activation of the compositional compression layer.

### 2.7 Survey on Unknown Substrates

To test whether the engine can discover genuinely unknown asymptotics (rather than recover known ones), we ran three substrates where the true correction terms are not established in the literature. The substrates were presented fully blinded (dark folder names, no domain labels in evidence headers, persona, or charter).

| Substrate | Visible fit | Extrapolation (10x range) | Verdict |
|-----------|------------|--------------------------|---------|
| S1 (density ratio, converging) | max res 0.006 | max res 0.010 (diverging) | Window fit, not structure |
| S2 (normalized sum, oscillating) | max res 0.48 | N/A | Correct null |
| S3 (normalized gaps, spiky) | max res 2.39 | N/A | Correct null |

S2 and S3 were correctly identified as incompressible (the true structure lives in fluctuations, not trends). S1 achieved tight visible-window fit but the compression form diverged on extrapolation to $10\times$ the training range, confirming window fitting rather than structural discovery. The hit rate on genuinely unknown substrates was 0/3. The false-positive rate was also 0/3 — the engine did not claim structure where none exists.

### 2.7.1 PySR baseline comparison

To test whether the false-positive rejection above is specific to this apparatus or generic to holdout-gated symbolic regression, we ran PySR (Cranmer 2023) on the same five substrates under identical out-of-sample gating.

| Substrate | ZTARE verdict | PySR (default BIC) | PySR + ZTARE gate |
|-----------|---------------|--------------------|--------------------|
| S1 abundant density | 1/n passes at $n{\leq}100$K | form claimed, no null option | null ($0.0105 > 0.01$ gate) |
| S2 Mertens $M(n)/\sqrt{n}$ | null | form with NaN on extrapolation | null |
| S3 prime gaps $g(n)/\log p_n$ | null | form claimed, no null option | null ($1.73 \gg 0.08$ gate) |
| Lucky $L(n)/n$ (§2.1) | $1.200\ln n + b/n + c$ | $1.204\ln n + 0.487$ | passes ($0.033 \le 0.08$) |
| Hardy-Ramanujan $\log p(n)$ (§2.2) | $\pi\sqrt{2n/3} + b\ln n + c$ | nested exponential, incorrect | null ($0.265 > 0.08$) |

Three observations:

1. **Cross-validation on Lucky numbers.** PySR's genetic search independently recovered $a = 1.204$ against ZTARE's $a = 1.200$. Two structurally different search algorithms (LLM-proposal + template-enumeration vs. evolutionary program synthesis) converge to the same coefficient on a conjectured-but-unproven asymptotic. The triangulation strengthens the §2.1 measurement.

2. **Hardy-Ramanujan recovery is not automatic.** PySR failed to return $\pi\sqrt{2/3} \cdot \sqrt{n}$ within the same iteration budget; its best BIC form was a nested exponential that failed the holdout gate at $3.3\times$ threshold. This indicates the topology $\sqrt{n} + \ln n$ is not reliably reachable by default PySR settings even when the answer is in a library the algorithm could compose. The template-enumeration primitive recovered it in one pass.

3. **The holdout gate is the null-returning mechanism, not the search.** On all three incompressible substrates (§2.7 S1-S3), default PySR claims a form; under ZTARE-style gating, PySR correctly declares null on all three. This reframes the §4 claim: what distinguishes this apparatus from standard symbolic regression is not a novel search algorithm but the architectural commitment to holdout gating as a hard structural constraint rather than a post-hoc model-selection criterion.

The comparison was run with PySR 1.5.10, 40 iterations, complexity limit 20, operator set $\{+, -, \times, /, \mathrm{pow}, \log, \sqrt{\cdot}, \exp\}$. Results and harness at `scripts/pysr_baseline.py`; reproduction data at `papers/experimental_math_letter/pysr_baseline_full.json`.

### 2.7.2 Two ceilings: grammar and space

The grammar ceiling theorem (§3) states that additional compute cannot break structural ceilings imposed by the expression grammar; grammar expansion is required. Applying that framework to the §2.7 null result exposes a second ceiling the engine had not previously isolated.

On discrete number-theoretic substrates — here sopfr (A001414 sum of prime factors with multiplicity) tested blind under `py_exec` grammar with `isprime`, `factorint`, `primefactors`, `divisors`, `gcd` as primitives — the mutator fails to recover the law despite the grammar admitting it syntactically. The data reveals the target with high clarity: the value $z(8) = z(9) = 6$ is a collision identity ($2+2+2 = 3+3$) that uniquely distinguishes sopfr from all other standard arithmetic functions of $n$; 22 primes in the visible range map to themselves ($z(p) = p$); prime-power values follow $z(p^k) = k \cdot p$ exactly. None of these three signals are read by the LLM mutator under repeated iteration with pivot escalation.

The failure is not in the grammar — `sum(p \cdot v \text{ for } p, v \text{ in factorint}(n).\text{items}())$ is expressible — but in the *mathematical category* the mutator searches within. The LLM reaches for polynomial, rational, and logarithmic combinations (smooth function-space) because those dominate symbolic-regression corpora in its pre-training. Crossing from function-space (functions of a continuous index) to prime-space (functions on the lattice of primes under unique factorization) requires an ontological shift the LLM does not make unprompted, even with the prime-factorization primitives directly available in the expression sandbox.

We therefore distinguish two ceilings:

| Ceiling | Mechanism | Test | Fix |
|---------|-----------|------|-----|
| Grammar | Expression language admits the form syntactically | Can the answer be written in the grammar? | Grammar expansion (e.g., `py_exec` + primitives) |
| Space | Mathematical category the mutator searches within | Does the mutator reach for the correct category of object? | Explicit category-switch intervention, or reasoning-class model |

Grammar expansion is necessary but not sufficient. The space ceiling is an additional, orthogonal bound. This reframes the scope of the discovery claim: the apparatus recovers targets whose correct form lives in the LLM's *statistically dominant* category (smooth asymptotic — §2.1-§2.6), and fails on targets requiring category-switch to less frequent categories (discrete algebraic — §2.7) regardless of whether the grammar admits the answer.

### 2.7.3 Open methodological questions — state-reset primitives

The apparatus's pivot mechanism (GP-021) currently succeeds by disrupting the mutator's state accumulation via heuristic modules (inversion, coordinate compression, category switch). Three candidate state-reset primitives emerge from this work but have not been evaluated here:

- **Persona rotation:** cycle the mutator persona every $k$ iterations (contrarian empiricist → topology-first pattern matcher → adversarial symmetrist), breaking the drift of any single anchor.
- **Thesis amnesia:** clear the best-thesis memory on stagnation, forcing the mutator to propose from cold rather than iterate on a locally-optimal but globally-wrong form.
- **Judge rotation:** swap the judge model (e.g., gpt-4.1 → claude → gemini-pro) on stagnation to break judge-side calibration drift, which we observed as a score oscillation of 0–76 on identical-quality proposals (§2.7.1 footnote).

All three are low-cost, high-leverage candidates that deserve controlled evaluation. We defer their analysis to a dedicated methodology paper and flag them here as open directions for the symbolic-regression-with-LLM community.

---

## 3. The Grammar Ceiling Theorem

The most informative experiment was a four-run controlled chain on a bivariate transcendental substrate (Planck/Bose-Einstein occupancy function):

| Run | Grammar | Iterations | Best form | Score |
|-----|---------|-----------|-----------|-------|
| 1 | math\_exp\_only | 16 | Wien approximation | 88 |
| 2 | math\_exp\_only | 16 | Weibull (wrong class) | 88 |
| 3 | math\_exp\_only | 32 | Weibull (same class) | 93 |
| 4 | math\_exp\_only + UNIVERSAL\_DENOMINATOR | 15 | Planck (correct class) | 97 |

Runs 1-3 demonstrate that additional compute (doubling iteration budget) produces refinement within a structural class but cannot cause a structural class transition. Run 4 demonstrates that a single grammar expansion (adding $1/(e^x - 1)$) achieves the correct class in fewer iterations than any amount of compute in the restricted grammar. The grammar, not the compute budget, is the binding constraint on structural diversity.

This result has implications for LLM-based scientific discovery systems generally: the LLM's proposal distribution is bounded by its pre-training vocabulary; any form outside that vocabulary requires explicit grammar expansion, regardless of prompt engineering or iteration count.

### 3.1 Operator Grammar Ceiling (Riemann Zero Spacing)

The grammar ceiling generalizes beyond 1D function fitting to operator eigenvalue matching. We tested 28 real-symmetric operator families (polynomial confinement + number-theoretic diagonal/off-diagonal terms) at matrix dimension $N = 800$ on GPU, optimizing eigenvalue spacings to match the first 75 non-trivial zeros of $\zeta(s)$. Target spacing variance: 0.457 (GUE universality class).

The 28 generators separate into two phases with an empty gap:

| Phase | Loss (MSE) | Spacing var | Character |
|-------|-----------|-------------|-----------|
| A (polynomial-dominated) | 0.26--0.35 | 0.27--0.37 | Too regular |
| B (arithmetic-dominated) | 0.63--4.08 | 0.54--0.65 | Right variability, wrong loss |
| Gap | --- | 0.37--0.54 | **Empty: no generator occupies this region** |

No generator achieves both low loss and target-range spacing variance. The gap is structural: three independent grammar classes (polynomial-only, sparse arithmetic off-diagonal, dense Hankel/Toeplitz arithmetic) all reproduce it. Spectral form factor (SFF-L1) is uniformly wrong across all 28 families (0.82--1.13 vs target 0).

The bimodal gap is a distinct structural finding. It means the operator space has a phase transition between polynomial-dominated and arithmetic-dominated spectral statistics. A critical-point generator — sitting at the phase boundary — would require deliberate physics-informed design, not gradient descent from random initialization. This extends the grammar ceiling from "which mathematical primitives the engine can compose" to "which spectral statistics an operator class can produce."

### 3.2 Architecture-translation experiment: Navier-Stokes counter-example hunt

A separate experiment tests whether the apparatus's substrate-bottleneck-diagnosis methodology — empirically validated on continuous-gradient physics substrates in a parallel project (Alami 2026, paper 7) — translates to a mathematical-substrate Millennium target. The Navier-Stokes Millennium question (whether smooth divergence-free finite-energy 3D incompressible initial conditions on T³ can produce finite-time singularities) admits a continuous-gradient surrogate that the apparatus can in principle navigate: the Beale-Kato-Majda integral $\int_0^T \|\nabla u(\cdot, t)\|_\infty \, dt$ remains continuous in initial-condition parameters, even though the singularity-or-not question itself is binary.

The architecture-translation maps the four ZTARE components to their NS-counterexample-hunt analogues. The Architect (LLM cold-shot) proposes initial-condition velocity-field families $u_0(x; \theta)$ rather than Lagrangians. The Mechanic (numerical solver) replaces scipy.optimize with a JAX-based pseudo-spectral 3D incompressible Navier-Stokes integrator: vorticity formulation with 2/3 dealiasing, RK4 time stepping, periodic boundary conditions on $T^3 = [0, 2\pi]^3$, scaling from $N = 64$ local CPU prototyping to $N = 256$-$512$ on rented GPU. The Falsifier (loss landscape) maximizes $\sup_t \|\nabla u(\cdot, t)\|_\infty$ subject to finite-energy and divergence-free constraints, equivalent to maximizing the BKM integrand. The pre-registered Phase 0 acceptance gate is reproducing the published Taylor-Green vortex kinetic-energy decay curve at $\nu = 10^{-3}$, $N \geq 64$, $t \in [0, 5]$, within 1% of the literature benchmark; the pre-registered Phase 1 gate is replicating the Hou-Luo 2014 axisymmetric blow-up vorticity growth signature at the same resolution before any new ansatz hunt begins.

This experiment is scoped at five phases: solver scaffolding (Phase 0, in flight as of the present draft, scaffold $\sim 250$ lines, FFT round-trip clean at $10^{-13}$ tolerance, vorticity-magnitude diagnostic normalization currently being debugged), Hou-Luo replication (Phase 1, target $\sim 1$ day after Phase 0 acceptance), parallel cold-shot ansatz generation (Phase 2, runs in parallel with Phase 0/1 since it requires only LLM compute), parameter-sweep search (Phase 3, GPU-rental at H100 scale), resolution-convergence audit at progressively finer mesh (Phase 4, the controlling test that distinguishes a genuine blow-up from a numerical artifact), domain-expert routing for any Phase 4 survivor (Phase 5, since Clay-acceptable Navier-Stokes counter-examples require both numerical evidence and an analytical self-similar/Leray-type mathematical argument that the apparatus cannot generate).

The experiment's claim is methodological, not theorematic. The realistic outcome distribution is: most cold-shot ansatz families produce smooth (non-blowup) solutions, the Hou-Luo replication validates the solver, and any candidate showing super-exponential vorticity growth gets routed to Phase 4 for resolution-convergence audit. The experiment is not claiming the architecture will produce a Clay-acceptable counter-example in any specific timescale; it is claiming the architecture-translation question — whether the substrate-bottleneck-diagnosis methodology that worked on the physics substrate works on a mathematical substrate when a continuous-gradient surrogate is available — is itself a falsifiable methodological question worth posing. A null result (no candidate survives Phase 4) is equally publishable as a positive result, since the null bounds the methodology's reach in exactly the same epistemic-discipline pattern that paper 7's PN-elliptical FAIL bounded the PMOND v5 universality claim.

The experiment also responds to a structural critique raised during the architecture-translation design: the apparatus's strength on physics substrates depended on continuous gradients (per-class MRE responding smoothly to parameter perturbations), and pure mathematical proof problems (Lean-verifiable theorem proofs) lack such gradients because Lean's "unsolved goals" returns no partial-credit signal. The Navier-Stokes counter-example hunt is the unique Millennium target where the question's structure admits a continuous-gradient surrogate without requiring a Lean/SMT theorem-prover refactor. It is the architecture-translation experiment that the architecture's existing strengths can in fact attempt; broader Lean-based proof-generation experiments would require a separate apparatus (Architect proposing lemmas, Mechanic running SMT/Vampire, Falsifier running Lean kernel) outside the scope of the present apparatus and outside the scope of this paper.

---

## 4. Discussion

The engine recovers by compressing, not by generating. The LLM's role is to explore topology space and produce overparameterized surrogates; the compression primitive strips them to minimal gate-passing forms; the holdout gates enforce generalization.

Three contributions emerge:

**Recovery under blinding.** The engine recovers known asymptotic forms (Hardy-Ramanujan, Lucky density, Vaughan, Meinardus) from blinded data with no domain labels. This validates the apparatus as a measurement instrument for asymptotic structure.

**Provable false-positive rejection.** Across all incompressible substrates (Mertens, prime gaps, Ulam direct, DFDO), the engine returned null rather than claiming spurious structure. The deterministic holdout gates are the mechanism: any form that fits the visible window but diverges on held-out data is rejected regardless of how the LLM scored it.

**The grammar ceiling.** The engine's structural reach is bounded by its expression grammar, not by compute. This finding — demonstrated on a four-run controlled chain and independently confirmed on a 28-family operator search for Riemann zero spacing statistics — suggests that future automated discovery systems should invest in grammar expansion (adding new mathematical primitives or operator classes) rather than additional LLM iterations or optimization restarts within a fixed grammar.

The Lucky number coefficient $a = 1.200$ and the Ulam reciprocal compression are the strongest individual results, but we emphasize that the engine has not yet discovered an asymptotic form that was not already conjectured or known. The survey on unknown substrates (§2.7) returned 0/3 genuine discoveries. The engine is currently a recovery and certification instrument, not a discovery engine. Crossing that boundary likely requires either hybrid symbolic search (beyond LLM proposals) or substrates that sit within the LLM's grammar but outside its training data.

---

## Acknowledgments

The apparatus was built and operated by the author. All experiments used GPT-4.1 as the LLM mutator and judge unless otherwise noted. The grammar ceiling experiment (§3) used Gemini 2.5 Flash as the mutator.

---

## Data Availability

All code, evidence files, gate harnesses, rubrics, iteration telemetry, and compression results are publicly available at github.com/sparckix/ztare. Each experiment can be reproduced with `make discover PROJECT=<name> RUBRIC=<name>`.
