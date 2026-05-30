# GP-099 — Vocabulary Floor: Expanding the Primitive Library Without Combinatorial Death

> **Seam metadata** · `seam_id:` GP-099 · `track:` engine · `status:` open - opened 2026-04-19 09:45:00 EST · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-04-19 09:45:00 EST

## ID

GP-099

## Eigenquestion

Can ZTARE discover physical laws requiring special functions (Bessel, Error, Gamma) without adding them to _BASE_PRIMITIVES — by using a universal approximant primitive (Padé) that can *become* any special function through its coefficient matrix?

## Problem Statement

Component D's topology synthesizer is bottlenecked by the 32 functions hardcoded in `_BASE_PRIMITIVES` (topology_synthesizer.py:1060-1095). It can compose them to depth-2, but it cannot invent mathematical classes absent from the library.

If the true physical law requires a special function (Bessel J₀(x), error function erf(x), Gamma function Γ(x), Airy function Ai(x)) that cannot be cleanly approximated by depth-2 combinations of exp, log, power, and trig, the apparatus will:
1. Hit the Feynman Wall (library exhausted)
2. Spin up Component D (composition mode)
3. Fail to find a valid composition (the spanning set doesn't contain the target)
4. Permanently stall with WALL_LIBRARY_INSUFFICIENT

This is a genuine ceiling, not a solvable engineering problem. The Taylorist Cage proves whether a solution exists *within the spanning set*. It is not a universal solver.

## Scope

**Covers:**
- Whether Padé approximants [m,n] can serve as a universal primitive that subsumes special functions
- The tension between Padé universality and the Padé Trap (Weierstrass dominance on visible data)
- Whether named special functions should be added to the library instead (or in addition)
- How the holdout gate interacts with Padé approximants (no prior topology → no asymptotic prediction)
- Cost of expanding the library vs. adding a universal approximant

**Does not cover:**
- Evidence preprocessing (see GP-098)
- N-D compression (see GP-097)
- Changes to the synthesis loop or gate architecture
- Specific physical substrates requiring special functions

---

## Existing Codebase Evidence

### 1. The current primitive library

`topology_synthesizer.py:1060-1095`: 32 primitives spanning:
- Polynomials (linear, quadratic, cubic)
- Exponentials (exp, exp_decay, double_exp)
- Trigonometric (sin, cos, tan)
- Hyperbolic (sinh, cosh, tanh)
- Logarithmic (log, log2)
- Power (power, sqrt, reciprocal)
- Rational (rational, sqrt_reciprocal, log_reciprocal)
- Special composites (logistic, gaussian, gompertz, weibull, kww)

### 2. Depth-2 composition

`topology_synthesizer.py:739-850`: The depth-2 pass composes any two primitives via +, -, *, /. This gives O(32² × 4) ≈ 4,096 depth-2 candidates. With ratio probes, the search space is ~5,000 forms.

### 3. The Padé Trap (GP-078 Gap 11b)

The Padé Trap is the observation that rational approximants (Padé[m,n]) with enough parameters always beat the true physical law on visible data. This is a consequence of the Weierstrass approximation theorem: polynomials are universal approximators on compact intervals. Padé extends this to rational functions, which handle poles and asymptotes better than polynomials.

The holdout gate is the structural defense: rational approximants diverge on extrapolation because they have no physical prior constraining their asymptotic behavior. But this defense works precisely because named primitives (exp_decay, tanh) HAVE known asymptotics. A generic Padé[3,3] has no prior topology — it's a black box with 7 parameters. The holdout gate cannot distinguish a correct Padé from a wrong one by asymptotic behavior alone.

---

## Debate Log

### Turn 1 — Claude (2026-04-19 09:45:00 EST) — Opening: The Padé proposal has a fatal tension with the Padé Trap

Gemini proposes: instead of adding 40 named special functions, add one "universal" primitive — a Padé approximant [m,n] — and let the engine discover which special function it represents by finding the coefficient matrix that holds under extrapolation.

This is an elegant Odrzywołek-style compression: compress the space of special functions into a single parametric family, just as Odrzywołek compressed transcendental symmetries into eml(x,y).

**The fatal tension:** We just documented the Padé Trap (GP-078 Gap 11b). The trap says: rational approximants with enough parameters always beat the true law on visible data (Weierstrass guarantee), then diverge on extrapolation. Our defense is the farther-tail holdout, which works because named primitives have *known asymptotics* that the holdout can verify.

A generic Padé[3,3] has 7 free parameters and no asymptotic prior. If the true law is J₀(x) (Bessel), the Padé will fit the visible window perfectly — but so will any other Padé with 7 parameters. The holdout can only distinguish Padé approximants by how they behave at extrapolation distance. For Padé[3,3], the asymptotic behavior depends on the leading coefficients — it's either polynomial (if deg numerator > deg denominator) or approaches a constant (if equal) or goes to 0 (if less). None of these match J₀(x)'s actual asymptotics (oscillating decay ~ cos(x)/sqrt(x)).

**The consequence:** Adding a Padé primitive makes the holdout gate *weaker*, not stronger. Every Padé candidate will fit the visible window. The holdout can only reject Padé forms that have the wrong asymptotic class (polynomial vs. constant vs. zero). It cannot distinguish between multiple constant-asymptotic Padé forms, even though they approximate different special functions.

**An alternative approach: named special functions with known asymptotics.**

Instead of one universal approximant, add a small set of named special functions to `_BASE_PRIMITIVES`:

| Function | Asymptotics | Physics use cases |
|---|---|---|
| erf(x) | Saturates to ±1 | Diffusion, probability |
| J₀(x) | Oscillating decay | Wave propagation, cylindrical symmetry |
| Γ(x) | Factorial growth | Combinatorics, quantum mechanics |
| Ai(x) | Exponential decay | Quantum tunneling |
| Si(x) | Oscillating saturation | Signal processing |

Five functions. Library goes from 32 to 37. Depth-2 search space increases by ~30% (O(37² × 4) ≈ 5,500). Manageable.

Each named function has *known* asymptotic behavior. The holdout gate works exactly as before: verify that the candidate's extrapolation matches the function's known asymptotics.

**The trade-off:**
- Padé: Universal but holdout-weak. Can approximate *any* function but can't verify it.
- Named: Targeted but holdout-strong. Can only discover functions in the library but can verify them.

**My recommendation:** Named functions, not Padé. The holdout gate is ZTARE's fundamental defense. Weakening it for universality is the wrong trade.

**Requesting domain expert review on:**
- Is the Padé Trap truly fatal for the universal approximant approach?
- Is there a way to give Padé approximants asymptotic priors?
- Are 5 special functions enough, or is the long tail too long?
- Does SciPy even have stable implementations of these functions?

### Turn 2 — Munger Multidisciplinary (2026-04-19 09:45:00 EST) — Claude is right; the Padé proposal is self-defeating

**Inversion check on Gemini's proposal: failed.** The inversion "compress the math so it fits the existing vocabulary" sounds Mungerian, but it violates a decisive constraint: the holdout gate requires asymptotic priors.

Apply the Lollapalooza check: what happens when Padé is combined with the existing Depth-2 composition? You get Padé-of-Padé — a rational function composed with another rational function. The parameter space explodes. The Levenberg-Marquardt optimizer already struggles with 7-parameter Padé; at depth-2 you'd have 14 parameters. Optimizer death.

**The man-with-a-hammer diagnosis:** Gemini is pattern-matching to the Odrzywołek eml(x,y) success. But eml works because it has a *structural* prior (the interplay between exp and log creates transcendental symmetries). Padé[m,n] has no structural prior — it's the general-purpose tool that fits everything and predicts nothing. This is precisely the criticism we make of polynomial fits.

**My recommendation:** Named functions. But apply the circle-of-competence constraint: only add functions where SciPy has stable numerical implementations AND where the function's asymptotic behavior is known and testable. Don't add functions that are numerically unstable or whose asymptotics are complex (e.g., Gamma has poles at non-positive integers — the holdout might probe a pole).

**A middle path worth considering:** Add named functions as primitives AND add a single Padé[2,2] (5 parameters) as a "dark primitive" — a catch-all that the engine tries last, after all named primitives fail. If Padé[2,2] passes the holdout, it's flagged as "unidentified functional form" rather than claiming a specific law. The operator then inspects the coefficient matrix and identifies the special function manually.

This preserves the holdout gate's strength (named functions are tested first with full asymptotic verification) while adding a safety net for truly novel functions (Padé as a last resort, flagged for human review).

### Turn 3 — Symbolic Regression Expert (2026-04-19 09:45:00 EST) — The library size question is empirical, not theoretical

**On the library expansion cost:**

Adding 5 special functions to a 32-primitive library is computationally negligible. The depth-1 scan goes from O(32) to O(37) fits. The depth-2 scan goes from O(32² × 4) to O(37² × 4). The ratio is 1.34×. At current speeds (~0.01 sec/fit), the total depth-2 scan takes ~55 seconds instead of ~41. Irrelevant.

The real cost is not computational — it's **false positive rate.** Every new primitive is a new competitor in the visible-window tournament. If erf(x) and tanh(x) produce nearly identical fits in [0, 5] (they do — erf ≈ tanh on compact intervals), the engine must distinguish them by holdout behavior. erf(x) → ±1 as x → ±∞. tanh(x) → ±1 as x → ±∞. Same asymptotics. The holdout can't distinguish them.

This is a structural problem: erf and tanh are both saturating sigmoids. They differ in their approach rate (erf is faster), not their asymptotic values. The holdout gate tests asymptotic *values*, not *rates*. To distinguish erf from tanh, you'd need a rate-sensitive holdout — e.g., checking the derivative at the holdout point, not just the value.

**Recommendation:** Don't add erf. It's aliased with tanh in the holdout. Add only special functions whose asymptotics are topologically distinct from existing primitives:

| Function | Asymptotic class | Aliases existing? |
|---|---|---|
| erf(x) | Saturating sigmoid | YES (≈ tanh) — skip |
| J₀(x) | Oscillating decay | NO — unique |
| Γ(x) | Factorial growth | NO — unique (but poles) |
| Ai(x) | Exponential decay | YES (≈ exp_decay) — skip |
| Si(x) | Oscillating saturation | NO — unique |
| erfc(x) | Decaying complement | YES (≈ exp_decay) — skip |

Only J₀, Γ, and Si have topologically unique asymptotics. That's 3 additions, not 5. Library goes to 35.

**On Padé:** Agree with Claude and Munger. Padé is a universal *fitter*, not a universal *discoverer*. The distinction matters: fitting is matching visible data, discovering is identifying the correct functional form. ZTARE is a discovery engine, not a fitting engine. Padé helps fitting, hurts discovery.

### Turn 4 — Philosophy of Science (2026-04-19 09:45:00 EST) — The vocabulary question is about ontological commitment

**The deeper question:** Adding a primitive to the library is an ontological commitment. It says: "this functional form exists in the space of physical laws." ZTARE's library is its ontology of mathematical structures. Expanding it is a statement about what the universe might contain.

Padé is the "anything could be the law" ontology. Named functions are the "the universe uses these specific structures" ontology. The history of physics strongly favors the second: physical laws use a remarkably small vocabulary of mathematical functions. Bessel, Legendre, Hermite, Laguerre — these arise from separation of variables in specific coordinate systems. They're not arbitrary; they're consequences of symmetry.

**The pragmatic test:** How many real physics laws require special functions that can't be approximated by depth-2 compositions of the existing 32 primitives?

- Electromagnetic wave propagation: Bessel functions (cylindrical), spherical harmonics (angular). Can't be depth-2 approximated.
- Quantum mechanics: Hermite polynomials (harmonic oscillator), Laguerre (hydrogen atom). Polynomials are already in the library — these are specific instances.
- Diffusion: erf(x). Aliased with tanh (as SR expert noted).
- Airy functions: quantum tunneling. Aliased with exp_decay.

The honest answer: very few physics laws *require* special functions that are topologically distinct from the current library. Most special functions arise in the solutions of *specific boundary value problems*, not in the governing equations themselves.

**Recommendation:** This is a low-priority expansion. The vocabulary floor is real but distant. Most physics that ZTARE will encounter in the next 10 substrates will be expressible with the current 32 + cosh/sinh. Add J₀ and Si when a real substrate demands them. Don't build speculatively.

**The Lakatos test:** Is adding special functions a progressive or degenerating move? Progressive if it enables discovery of laws previously intractable. Degenerating if it merely expands the library without enabling new results. We have no substrate that requires J₀. Until we do, the expansion is degenerating.

### Turn 5 — Systems Engineering / ML (2026-04-19 09:45:00 EST) — SciPy implementation check and cost model

**SciPy stability check:**

| Function | SciPy module | Stable? | Edge cases |
|---|---|---|---|
| J₀(x) | `scipy.special.j0` | Yes | Oscillates forever; holdout at large x will see oscillation |
| Γ(x) | `scipy.special.gamma` | Yes | Poles at x = 0, -1, -2, ... — curve_fit may hit poles |
| Si(x) | `scipy.special.sici` | Yes | Returns (Si, Ci) tuple — need wrapper |
| erf(x) | `scipy.special.erf` | Yes | Aliased with tanh (skip per SR expert) |
| Ai(x) | `scipy.special.airy` | Yes | Returns (Ai, Ai', Bi, Bi') — need wrapper |

The pole problem for Γ(x) is real. If curve_fit proposes parameters that evaluate Γ at a non-positive integer, the fit crashes. This requires bounded parameter ranges in curve_fit, which the current fitting infrastructure doesn't support for arbitrary primitives.

**Cost model for library expansion:**

| Library size | Depth-1 fits | Depth-2 fits | Wall time (est.) |
|---|---|---|---|
| 32 (current) | 32 | 4,096 | ~41 sec |
| 35 (+3) | 35 | 4,900 | ~49 sec |
| 37 (+5) | 37 | 5,476 | ~55 sec |
| 42 (+10) | 42 | 7,056 | ~71 sec |

Even doubling the library (64 primitives) keeps depth-2 under 3 minutes. The cost ceiling is curve_fit convergence time per candidate, not library size. Library expansion is computationally free up to ~100 primitives.

**Recommendation:** The blocking constraint is not compute — it's *holdout aliasing* (SR expert's point). Only add primitives with topologically unique asymptotics. J₀ (oscillating decay) is the strongest candidate. Si (oscillating saturation) is second. Γ is third but has the pole problem.

### Turn 6 — Validator Hardening (2026-04-19 09:45:00 EST) — The holdout aliasing problem needs a structural fix

**The core issue isn't the library — it's the holdout's discrimination power.**

The holdout gate tests: "does the candidate's value at extrapolation distance match the expected asymptotic behavior?" This works for functions with distinct asymptotic *values* (exp → ∞, tanh → 1, reciprocal → 0). It fails for functions with the same asymptotic values but different approach rates (erf vs tanh both → 1).

Adding special functions amplifies this problem. J₀(x) oscillates as x → ∞ with decaying amplitude ~ cos(x)/sqrt(x). The holdout at a single point might catch it (if the holdout point happens to be near a zero of J₀) or miss it (if the holdout point is near a peak). Oscillating functions make single-point holdout unreliable.

**Proposal: multi-point holdout for oscillating functions.** If a candidate uses J₀ (or sin, cos, or any oscillating primitive), evaluate the holdout at multiple extrapolation distances (e.g., 1.5×, 2×, 3× the domain) and check for oscillation consistency. Non-oscillating functions (exp, tanh) should produce monotone holdout values. Oscillating functions should produce non-monotone holdout values. The pattern, not the point, is the discriminator.

This is a general improvement to the holdout gate, not specific to special functions. It would also improve discrimination between sin(x) and polynomial fits on the current 32-primitive library.

**Phasing:** Don't add special functions without upgrading the holdout for oscillation detection. The holdout in its current form cannot reliably distinguish J₀ from a polynomial that happens to hit the same value at the single holdout point. This is the cage-before-kernel rule: upgrade the gate before expanding the grammar.

### Turn 7 — Claude (2026-04-19 09:45:00 EST) — Convergence synthesis

**Consensus:**

1. **Padé as universal primitive: rejected.** Fatal tension with the Padé Trap. Padé fits everything on visible data, the holdout can't discriminate between different Padé coefficient matrices. This weakens the engine's core defense.

2. **Named special functions: accepted with constraints.** Only add functions with topologically unique asymptotics. Skip aliases (erf ≈ tanh, Ai ≈ exp_decay). Current candidates: J₀ (oscillating decay), Si (oscillating saturation), Γ (factorial growth, but pole problem).

3. **Low priority.** No current substrate requires special functions. Expansion is degenerating until a real substrate demands it. Build when needed, not speculatively.

4. **Holdout upgrade prerequisite.** Before adding oscillating functions (J₀, Si), the holdout gate needs multi-point evaluation for oscillation detection. Without this, J₀ and polynomial fits are indistinguishable at a single holdout point.

5. **Munger's "dark primitive" middle path.** A single Padé[2,2] as last-resort catch-all, flagged for human review if it passes holdout. Not a discovery claim — a detection mechanism for novel functional forms. Worth exploring after the named-function expansion if a substrate still stalls.

**Open questions (deferred — seam stays open):**

**Q1: Holdout oscillation gate.** Multi-point holdout for oscillating primitives. Design, threshold, false positive rate. Prerequisite for J₀/Si addition.

**Q2: Γ pole safety.** curve_fit parameter bounds to avoid non-positive integer arguments. Feasible? Or exclude Γ until bounded optimization is implemented?

**Q3: When to trigger.** This seam stays open. It re-activates when a real substrate hits WALL_LIBRARY_INSUFFICIENT and post-mortem analysis reveals that the true law requires a special function absent from the library.

**Seam status: open (parked).** Direction clear (named functions, not Padé), but no implementation urgency. Re-activate when a substrate demands it.

## Recommendation

**Do not expand the library now.** The vocabulary floor is real but distant. When a substrate hits WALL_LIBRARY_INSUFFICIENT and post-mortem reveals a special function gap:

1. Add the specific function needed (not a batch of speculative additions)
2. Verify its asymptotics are topologically unique from existing primitives
3. Upgrade the holdout gate for oscillation detection if the function oscillates
4. Add SciPy wrapper with pole/edge-case protection

**Key architectural decision: named functions over Padé.** The holdout gate requires asymptotic priors. Named functions have them. Padé does not. The holdout is the engine's fundamental defense. Don't weaken it for universality.
