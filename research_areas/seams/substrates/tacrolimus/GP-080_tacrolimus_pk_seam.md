# GP-080 — Tacrolimus Pharmacokinetics: Component D Test on a Continuous Clinical Domain

> **Seam metadata** · `seam_id:` GP-080 · `track:` substrates · `status:` **Closed - 2026-04-18** (Stage 2 complete; figshare crucible · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Status

**Closed — 2026-04-18** (Stage 2 complete; figshare crucible deferred to Stage 3)

## One-Line

Test whether ZTARE's topology synthesizer (Component D) can independently derive biexponential pharmacokinetic structure from concentration-time evidence, using only domain-agnostic mathematical primitives — no biological library.

---

## Why This Domain

GP-078 (cal_sigma_02) confirmed ZTARE can recover dark integer recurrences. But the core discovery claim — that the engine synthesizes laws from mathematical primitives without domain knowledge — has not been tested on a continuous, multi-compartment, clinically-grounded problem.

Tacrolimus (an immunosuppressant used post-transplant) is the right test for three reasons:

1. **The ground truth is mathematically complex but structurally discoverable.** Oral tacrolimus follows a two-compartment open model with first-order absorption and elimination. The closed-form solution is biexponential: `C(t) = A·exp(-α·t) + B·exp(-β·t)` where the parameters are functions of rate constants (ka, ke, k12, k21). This is genuinely hard to guess but derivable from concentration-time residuals under Component D's NEST/COMPOSE grammar.

2. **The primitives already exist.** The Gemini conversation (2026-04-17 inversion) correctly identified that `exp_decay`, `rational` (= Michaelis-Menten), and `logistic` are already in `_BASE_PRIMITIVES`. No domain-specific library needed. The zero-trust architecture is preserved: domain-agnostic primitives forced into clinical structure by residual pressure.

3. **The holdout gate is clinically meaningful.** Predicting concentration at unseen time-points for unseen doses is not a toy problem — it is the operational task of therapeutic drug monitoring. A law that passes the holdout gate has genuine predictive validity.

---

## Ground Truth Specification

**Model class**: Two-compartment oral absorption model (standard population PK).

**Closed-form solution** (post-dose, single compartment approximation for discovery):

```
C(t, dose) = (F · dose / V) · (ka / (ka - ke)) · (exp(-ke·t) - exp(-ka·t))
```

Where:
- `ka` = absorption rate constant (~1.5 h⁻¹, oral tacrolimus)
- `ke` = elimination rate constant (~0.07 h⁻¹, typical adult)
- `F` = bioavailability fraction (~0.25, tacrolimus is highly variable)
- `V` = volume of distribution per bioavailability (~300 L)
- `dose` = administered dose (mg)

**Parameter source**: Population PK estimates from published literature (Størset et al. 2019, or equivalent). Division A owns the exact parameter set. Division B never sees it.

**Why 1-compartment first**: The biexponential 2-compartment solution (`A·exp(-α·t) + B·exp(-β·t)`) has 4 free parameters and requires simultaneously fitting both phases. The 1-compartment approximation (`(ka/(ka-ke))·(exp(-ke·t) - exp(-ka·t))`) is structurally equivalent but more identifiable from sparse data. Start here; escalate to 2-compartment if the gate passes.

**Evidence design**:
- Visible: concentration-time pairs at `t ∈ {0.5, 1, 2, 4, 6, 8, 12, 24}` hours, `dose ∈ {1, 3, 5}` mg → 24 visible points
- Holdout: same time grid at `dose ∈ {2, 4}` mg + sparse `t ∈ {3, 10, 18}` at dose=3 → 22 holdout points
- Variable names: `t` (hours post-dose), `dose` (mg), `z` (concentration, ng/mL)

**Denylist (Division A)**: tacrolimus, FK506, ka, ke, bioavailability, pharmacokinetic, absorption, elimination, two-compartment, biexponential, Størset, clearance, half-life, volume of distribution, immunosuppressant

---

## Infrastructure Pivots (What Needs to Change)

### Pivot 1 (BLOCKING): Topology synthesizer variable name parameterization

**Current state**: All 32 `_BASE_PRIMITIVES` in `topology_synthesizer.py` hardcode `n` as the independent variable (e.g., `"a * math.exp(-b * n) + c"`). The composition grammar, prompt builder, and parameter substitution all assume `n`.

**Required change**: Make the independent variable name configurable at runtime. Two sub-options:

- **(a) String substitution at composition time**: pass `var_name="t"` to `build_composition_prompt()` and `compile_composition()`, substitute `n→t` in all primitive expressions before fitting. Minimal code change.
- **(b) Variable-agnostic primitives**: replace `n` with a placeholder `{x}` in `_BASE_PRIMITIVES`, substitute at composition time. Cleaner but more invasive.

**Recommended**: option (a) — targeted substitution in `_build_primitive_table()` and `compile_composition()`. ~20 lines.

**Scope**: `src/ztare/validator/topology_synthesizer.py` only.

### Pivot 2 (BLOCKING): Multivariate composition (t, dose → C)

**Current state**: The composition grammar is 1D — it composes `f(n)` primitives. PK concentration depends on both `t` and `dose`. The gate harness will receive `(t, dose, z)` triples.

**Required change**: The mutator's FIT_DECLARATION must declare `independent_vars: ["t", "dose"]`. The fit primitive already supports this (rubric `fit_required_vars: ["t", "dose"]`). But the topology synthesizer compositions only generate 1D functions. Component D needs to be extended to compose expressions in 2 variables.

**Simplest approach**: Allow linear dose scaling as a special composition form: `f(t, dose) = dose · g(t)`. This is biologically grounded (linear PK assumption) and only adds one outer multiplication. The mutator can discover dose-proportionality from the evidence without being told.

**Alternative**: Full 2D composition — treat dose as a second argument to NEST/COMPOSE. More general but much more complex.

**Recommended**: linear dose-scaling wrapper first. Adds one composition form: `DOSE_SCALED: dose · g(t)`.

**Scope**: `src/ztare/validator/topology_synthesizer.py`, `build_composition_prompt()`.

### Pivot 3 (NON-BLOCKING): Evidence generator for continuous PK

**Current state**: `generate_substrate.py` already supports `--gt-script` (callable GT) and 2-variable evidence via `--variables t,dose --visible-ranges "t:0.5:24,dose:1:5"`.

**Gap**: Range syntax assumes integer steps. PK time points are non-uniform (`{0.5, 1, 2, 4, 6, 8, 12, 24}` h). Need either:
- A `--visible-points` flag accepting explicit (t, dose) pairs, OR
- A GT script that generates its own evidence grid (bypassing the range generator)

**Recommended**: GT script (`gp080_tacrolimus_gt.py`) generates its own evidence grid internally; `generate_substrate.py` calls `f_true(t, dose)` for each point. This is already supported by the `--gt-script` path — the script just needs to expose `evidence_grid()` as well as `f_true()`.

**Scope**: `src/ztare/substrates/gp080_tacrolimus_gt.py` (new file). No changes to generate_substrate.py.

### Pivot 4 (NON-BLOCKING): Log-space fitting for heteroscedastic PK data

**Current state**: The fit primitive minimizes absolute residuals (L2 in concentration space). PK data is log-normal — errors are proportional to concentration, not additive. Fitting in log-space is standard practice.

**Gap**: The gate harness and fit primitive currently compare `z_predicted` vs `z_observed` in linear space. For sparse PK data (concentrations spanning 2 orders of magnitude), linear-space L2 will overweight peak concentrations and underweight trough.

**Required change**: Add `fit_log_transform: true` flag to rubric JSON. When set, evidence is log-transformed before fitting and the gate harness evaluates in log-space. `generate_substrate.py` already has `--transform log` support (built for OEIS).

**Scope**: rubric field + gate harness template (add log-transform path).

---

## What Does NOT Need to Change

- `bounded_discriminator` mode: already exists, already wired
- `fit_required_vars: ["t", "dose"]`: already supported in rubric and autoresearch_loop
- `exp_decay`, `rational`, `logistic` primitives: already in `_BASE_PRIMITIVES`, map directly to PK kinetics
- 2-variable gate harness template: already in `generate_substrate.py`
- `holdout_hard_gate`: already supported
- Persona registry: `domain/systems_ml` and `domain/philosophy_of_science` are the right reviewers

---

## Component D Connection

The biexponential PK structure (`A·exp(-α·t) + B·exp(-β·t)`) is a COMPOSE of two `exp_decay` primitives. Under Component D's grammar:

```
COMPOSE(exp_decay_1, exp_decay_2) → a·exp(-b·t) + c·exp(-d·t)
```

This is a **Depth-1 composition** — within the current engine's budget. The mutator does not need to know pharmacokinetics. It just needs to discover that the residual after fitting a single `exp_decay` has the shape of another `exp_decay`. That is exactly what the FailurePackager is designed to surface.

If Component D is working, iteration 3-4 should produce a biexponential without the mutator ever being told the model class. That is the discovery claim.

---

## Execution Plan

1. **Write `gp080_tacrolimus_gt.py`** — GT script with published parameters, evidence grid generator, `f_true(t, dose)` and `f_dominant(t, dose)`. Division A artifact.

2. **Implement Pivot 1** — variable name substitution in topology_synthesizer.py. ~20 lines.

3. **Implement Pivot 2 (minimal)** — DOSE_SCALED composition form. ~30 lines.

4. **Run `generate_substrate.py --gt-script gp080_tacrolimus_gt.py --slug gp080_tacrolimus_01 --variables t,dose`**

5. **Write rubric** — `fit_required_vars: ["t", "dose"]`, `reviewer_domains: ["systems_ml", "philosophy_of_science"]`, penalties against named PK models.

6. **Run `make seal`** — sentinel + integration tests.

7. **Run `make experiment-loop PROJECT=gp080_tacrolimus_01 ITERS=15`** — more iterations than gp078 because biexponential discovery requires Component D to fire (Feynman Wall must be hit first).

---

## Division A / B Information Isolation

| Artifact | Division | Content |
|---|---|---|
| `gp080_tacrolimus_gt.py` | A | Parameters (ka, ke, F, V), evidence grid |
| `evidence_holdout.txt` | A | Held-out (t, dose, conc) triples |
| `.denylist` | A | 14 GT-specific terms |
| `evidence.txt` | B | 24 visible (t, dose, conc) triples — looks like generic function recovery |
| `project_charter.md` | B | "Find a law governing concentration as a function of two inputs" |
| `rubric.json` | B | No mention of PK, biexponential, or drug names |
| `thesis.md` | B | Neutral seed |
| `gate_harness.py` | B | Evaluates L2 (or log-L2) between predicted and observed concentrations |

---

## Two-Stage Execution Strategy

### Stage 1 — Synthetic Smoke Test (infrastructure validation only)

Use synthetic data from published population PK parameters (Størset 2019 or equivalent). Goal: verify that the `n→t` infrastructure pivot works and `curve_fit` doesn't crash on continuous floats. Gate: exact precision (`fit_score_mode: discrete_exact` on rounded concentration integers, or continuous RMSE < 0.1 ng/mL).

**Epistemic scope**: This run does NOT claim Component D "discovers pharmacokinetics." It only claims the infrastructure can handle continuous multi-compartment data. The biexponential answer is guaranteed because the data was generated by biexponentials. That is the point — a clean signal with a known answer validates the pipes.

**Known tautology**: The data IS biexponential by construction. Component D composing `exp_decay + exp_decay` is not discovery — it is standard nonlinear regression on a pristine surface. Do not overclaim. Log it as `apparatus_verified`, not `discovery`.

### Stage 2 — Figshare Crucible (discovery test)

Use real patient tacrolimus concentration-time data (figshare dataset, individual-level PK measurements). The GT is genuinely unknown — clinical data contains structural noise from enterohepatic recirculation, variable gastric emptying lag phases, CYP3A5 genotype variability, and assay limitations. These are not white noise — they are structural residuals that carry biological information the FailurePackager can read.

**Gate**: Bounded discriminator with clinical tolerance. NOT exact match. Acceptable gate: MAPE < 15% on holdout (standard therapeutic drug monitoring accuracy criterion), or alternatively a `continuous_rmse` gate with threshold informed by the dataset's assay CV (~10% for tacrolimus immunoassay).

**What genuine discovery looks like**: ZTARE fits a single `exp_decay`, the FailurePackager reads a secondary absorption spike in the residuals, Component D proposes COMPOSE(exp_decay, shifted_power) or DOSE_SCALED(exp_decay) + lag_term, and the result passes the holdout gate with MAPE < 15% without the mutator ever being told the model structure.

**Pivot 5 (Stage 2 only)**: Continuous tolerance gate in the gate harness. Current harness does integer exact match. Stage 2 needs:
- `fit_score_mode: "continuous_mape"` in rubric
- Gate harness `--emit-deterministic-gates` outputs `mape_fraction` instead of `exact_match`
- Holdout gate threshold: MAPE < 0.15 (15%)

This is a new rubric field and a new gate harness mode. Scope: `generate_substrate.py` gate harness template + rubric schema.

---

## Debate Log

### Turn 1 — Operator (2026-04-17)

Seam opened following GP-078 cal_sigma_02 eureka result (dark sequence recovery in 2 iterations). Operator directive: open GP-080 seam for tacrolimus PK as the Component D test domain, using GP-072 Division A/B protocol. Four infrastructure pivots identified. Public data question: recommend synthetic from published parameters for first run.

### Turn 2 — External review (2026-04-17)

Lethal counterpoint accepted: synthetic data strategy is an epistemic trap — the data being biexponential by construction guarantees Component D finds `exp_decay + exp_decay`, which is not discovery, it is regression on a surface designed to match the answer key. Real figshare patient data is the true crucible because biological noise is structural (not Gaussian white noise), giving the FailurePackager genuine residual signal to read. Two-stage strategy adopted: Stage 1 = apparatus validation (synthetic, do not overclaim), Stage 2 = discovery test (figshare, MAPE gate). Gate question resolved: Stage 1 uses exact/tight RMSE; Stage 2 uses MAPE < 15% (clinical standard). Pivot 5 added: continuous MAPE gate mode.

<!-- FINDINGS_DEBATE: Stage 2 is the epistemically valid test. Stage 1 is engineering scaffolding. Do not publish Stage 1 results as discovery. Pivots 1+2 blocking for both stages. Pivot 5 blocking for Stage 2 only. -->

### Turn 3 — Stage 2 Closure (2026-04-18)

**Run**: `gp080_02` — synthetic bi-exponential data with 5% proportional Gaussian noise (seed=42), clean holdout. 8 iterations. Mutator: Gemini Pro. Judge: GPT-4.1 (adversarial).

**Note on Stage 2 design**: This run used noise-injection on synthetic data, not the figshare real-patient crucible described above. Reason: figshare Pivot 5 (MAPE gate) was deferred pending RMSE gate validation on noisy synthetic. This run is the intermediate stage; the original figshare crucible remains the Stage 3 target.

**Champion**: Rational form `f(x1, x2) = x2 / (p0*x1 + p1 + p2/x1)` with p0=11.84, p1=2.73, p2=2.23. Judge score: 94. Holdout RMSE: 0.068 (gate: < 0.25). Passed.

**Iteration arc**:
- Iter 4: rational form discovered, score 94. Judge independently named "exponential exclusion" as structural weakest point without GT access.
- Iter 5–7: attempts to justify or replace the rational form; all scored below 94, reverted.
- Iter 8: fractional power / diffusion-limited thesis, score 67. Reverted.
- Feynman library exhausted during iter 7–8: all named library forms tested, none beat 94.
- Composition mode (Component D): 5/20 rounds, WALL_LIBRARY_INSUFFICIENT. Found Wien approximation form `x2 * (a·x1^b·exp(c·x1) + d)` but not the full bi-exponential. Closest structural approach: single exponential arm, missing the difference-of-two-exponentials coupling. Confirms data grid is the bottleneck, not grammar.

**Farther-tail verdict** (run after close, `eval_farther_tail.py`):

| x1 | x2 | f_true | f_champ | rel_err |
|----|----|--------|---------|---------|
| 30 | 1 | 0.1070 | 0.1489 | 39.1% |
| 48 | 1 | 0.0304 | 0.0897 | 195% |
| 48 | 3 | 0.0911 | 0.2691 | 195% |
| 72 | 1 | 0.0057 | 0.0567 | 902% |
| 96 | 1 | 0.0011 | 0.0406 | 3754% |

Farther-tail RMSE: 0.1639. Max relative error: 3754% at x1=96. **RATIONAL BASIN CONFIRMED.**

Relative error is x2-independent (identical % across all x2 at each x1) — confirms both models share the same x2 structure (linear multiplier); divergence is purely in the x1 dynamics (rational 1/x vs exponential decay).

**Pre-reg verdict**: CLOSED — gate PASSED (holdout RMSE 0.068 < 0.25), but rational ≠ GT form. The pre-registered criterion was RMSE gate only; form recovery was not pre-registered. Result: apparatus validated on noisy continuous data; form recovery failed on this holdout grid.

**GP-083 implication**: Confirmed empirically — the holdout grid (x1 ≤ 24) cannot discriminate rational 1/x from bi-exponential exp(-kt). Stage 3 design (farther-tail holdout gate at x1=48) is the discriminator test.

**Next**: Run `gp023_crucial_01` (Planck crucial experiment) per GP-083 spec.

