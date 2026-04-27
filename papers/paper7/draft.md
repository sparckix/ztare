# Adversarial Symbolic Regression as Substrate Prober

## A Newton-Step Null on the Radial Acceleration Relation Across Galaxies, Clusters, and Wide Binaries

**Daniel Alami**
Independent Researcher; MBA Candidate, Harvard Business School

*April 2026 — working draft, v0.1*

---

## Abstract

We report a null result and a methodological finding from a closed-form symbolic regression search for a unified law of the radial acceleration relation (RAR) across rotation-curve galaxies, galaxy clusters, and wide binary stars. Across nine LLM-driven iterations and a follow-up scipy backtest covering 17 candidate functional families, no closed-form law of (input acceleration, baryonic mass, radius) achieves a mean relative error below 0.5 simultaneously on all three regimes. The interesting finding is the diagnosis of why. The substrate's withheld classes have collapsed feature axes. Galaxy clusters carry a single canonical mass surrogate and varying radii; wide binaries carry varying masses and a single canonical radius surrogate. Any joint mass-and-radius interpolation form therefore has zero within-class degrees of freedom on at least one of the two extrapolation classes. The 0.5 cap is a substrate-data ceiling, not a grammar ceiling. The diagnosis was produced by an apparatus we describe as an LLM-driven substrate prober: a mutator-judge loop with a deterministic gate stack, augmented at this run with a new G-CROSS-CLASS-FEATURE-SUPPORT gate that names cross-class feature collapses ex ante. We argue that this is the load-bearing methodological contribution. A reader who wants to know whether MOND, MOND with an external field effect, or ΛCDM unifies the RAR will not find an answer in this paper. A reader who wants to know what symbolic regression can and cannot say about the question on currently available aggregated data will.

---

## 1. Introduction

The radial acceleration relation is an empirical pattern between the Newtonian acceleration $g_{\rm bar}$ a system would generate from its visible (baryonic) mass distribution and the centripetal acceleration $g_{\rm obs}$ inferred from rotational or dispersion measurements. We use the term Newtonian acceleration to mean the acceleration computed from the visible mass with standard gravity; the deviation from $g_{\rm obs}$ at low $g_{\rm bar}$ is the empirical content of the RAR. McGaugh, Lelli, and Schombert (2016) established the relation at high quality on 153 disk galaxies in the SPARC catalog, with a characteristic crossover acceleration $a_0 \approx 1.2 \times 10^{-10}$ m/s². At high $g_{\rm bar}$, the relation reduces to $g_{\rm obs} \approx g_{\rm bar}$. At low $g_{\rm bar}$, $g_{\rm obs}$ exceeds $g_{\rm bar}$, with the canonical interpolation due to McGaugh:

$$
g_{\rm obs}(g_{\rm bar}) = \frac{g_{\rm bar} + \sqrt{g_{\rm bar}^2 + 4 c \, g_{\rm bar}}}{2}, \quad c \approx a_0.
$$

Whether this relation is universal across system scales is an open question. Tian et al. (2020) and Hossenfelder, McGaugh, and Mistele (2024) report that galaxy clusters show an excess: the same interpolation function fitted on disks underestimates $g_{\rm obs}$ at the low-$g_{\rm bar}$ end. Chae (2020, 2023) argued from Gaia wide-binary statistics that low-acceleration binary pairs deviate from the Newtonian baseline in a manner consistent with deep-MOND. The Chae claim is contested. Pittordis and Sutherland (2023) argued that the inferred deviation is consistent with line-of-sight projection and orbital eccentricity systematics under standard gravity. No single closed-form law published to date unifies the three regimes (galaxies, clusters, wide binaries) to a common acceptance threshold.

We took up this question through a symbolic-regression apparatus called ZTARE. The apparatus produces and adversarially evaluates candidate closed-form laws; we frame our use of it here as a substrate prober rather than as a discovery engine for new physics. The question we asked is narrow. Given the publicly available aggregate data (SPARC for galaxies; cluster summary statistics; binned wide-binary statistics), is there any closed-form law of the kind a symbolic regressor can express that simultaneously bridges the three regimes within a stated error threshold? The answer on the v2 substrate is no, and the diagnosis names the substrate's data structure as the binding constraint. After the v2 null landed, the substrate was enriched (v3, 2026-04-26) with real per-cluster baryonic masses and radii (Umetsu+2016 CLASH weak lensing) and with real per-bin wide-binary radii (Chae 2023). The first two iterations of the v3 run are reported alongside the v2 trace; the v3 thread is live and the physics finding is conditional on convergence across iterations 3-10.

This paper has four contributions. First, the empirical v2 null on RAR unification across galaxies, clusters, and binaries on the substrate as configured. Second, the diagnosis of within-class feature collapse as the load-bearing reason for that null. Third, the methodological framing of LLM-driven adversarial symbolic regression as a substrate prober: an instrument for telling a researcher what a body of data can and cannot answer before that researcher commits to a theoretical framework. Fourth, an apparatus-level architectural piece: a new R26 G-CROSS-CLASS-FEATURE-SUPPORT gate that names the v2 collapse pattern ex ante, and a Level 2 self-improvement layer of four meta-gates that audit the apparatus's own gate stack. The methodological contribution is settled today. The physics contribution is conditional on the v3 substrate-enriched run.

The null on v2 is reported in the spirit of stoic reporting. We are not claiming that the RAR is unified, nor that it is not. We are claiming that on the v2 data we had, a class of expressive closed forms cannot tell. The v3 substrate removes the binding feature-collapse constraint; whether expressive closed forms can now tell is the live question.

---

## 2. The Substrate

The run reported here is gp163d_unified_accel. The substrate aggregates three classes of systems.

**Class A** is 175 SPARC disk galaxies (Lelli, McGaugh, Schombert 2016) contributing 2585 (radius, $g_{\rm bar}$, $g_{\rm obs}$) rows in the visible set, with an additional 595 rows held out for in-class validation. The Class A rows expose five continuous axes: $g_{\rm bar}$, $\log_{10}(\text{radius in kpc})$, $\log_{10}(\text{baryonic mass in solar units})$, gas fraction $M_{\rm gas} / M_{\rm bary}$, and disk-plus-bulge surface brightness $\log_{10}(\text{SB in } L_\odot/\text{pc}^2)$ at the row's radius. The mass column is reconstructed per-galaxy from the SPARC catalog as $M_{\rm bary} = 0.5 \times 10^{\log L_{3.6}} + 1.33 \times 10^{\log M_{\rm HI}}$, with the 0.5 factor the standard 3.6 µm stellar mass-to-light ratio and the 1.33 factor accounting for primordial helium. Across the 175 galaxies $\log_{10} M_{\rm bary}$ spans 7.69 to 11.43, a range of 3.73 dex.

**Class B** is a galaxy cluster surrogate of 84 rows. The visible substrate exposes $g_{\rm bar}$ and $\log_{10}(\text{radius in kpc})$ per row. The mass column is collapsed: every Class B row carries the canonical value $\log_{10} M_{\rm bary} = 14.5$. This is a public-aggregate summary placeholder and not per-cluster mass. Per-cluster baryonic mass measurements at sufficient resolution to distinguish the clusters in the sample are not assembled in our substrate.

**Class C** is a wide-binary surrogate of 12 rows derived from binned aggregate statistics in the spirit of Chae (2023). The visible substrate exposes $g_{\rm bar}$ and $\log_{10} M_{\rm bary}$ per row. The radius column is collapsed: every Class C row carries $\log_{10}(\text{radius in kpc}) = -2.0$, a single canonical value corresponding to a representative orbital scale. This is again a summary placeholder rather than per-system orbital separation.

We disclose these surrogate values explicitly because they are the load-bearing constraint for the rest of the paper. The within-class variance of $\log_{10} M_{\rm bary}$ on Class B is zero. The within-class variance of $\log_{10}(\text{radius})$ on Class C is zero. Any closed-form law that interpolates jointly on (mass, radius) has, by construction, zero within-class degrees of freedom on at least one of the two extrapolation classes.

The visible portion of the substrate exposed to the mutator is Class A only. Class B and Class C are reserved as farther-tail extrapolation classes; the apparatus must predict $g_{\rm obs}$ on Class B and Class C without ever fitting against rows in those classes. The prediction targets are evaluated against the held-out Class A rows (in-class generalization gate) and the Class B + Class C rows (Newton-step extrapolation gate). Acceptance thresholds are mean relative error below 0.35 on the Class A holdout and below 0.50 on the Class B + Class C farther-tail.

### 2.1 v3 Enrichment (2026-04-26)

After the v2 null and the cross-class feature-collapse diagnosis (Section 7), the substrate was enriched at the per-system level. The enrichment is documented in `projects/gp163d_unified_accel/CHANGELOG.md` and `projects/gp163d_unified_accel/build_v3_per_system.py`.

**Class B per-cluster baryonic mass.** Per-cluster $M_{500c}$ values for the 20 CLASH clusters in our sample are taken from Umetsu et al. (2016), Table 3, a stacked weak-lensing analysis. We convert to baryonic mass using the standard cluster baryon fraction $f_{\rm bar} = 0.13$ (Vikhlinin et al. 2006; Lelli et al. 2017), giving per-cluster $\log_{10} M_{\rm bary}$ in the range 13.73 to 14.46, a within-class spread of 0.73 dex. The legacy v2 column with the constant value 14.5 is preserved alongside the v3 column for reproducibility.

**Class B per-cluster radius.** We derive $r_{500c}$ per cluster from $M_{500c}$ via the overdensity definition $M_{500c} = (4\pi/3) \cdot 500 \cdot \rho_{\rm crit}(z) \cdot r_{500}^3$, taking redshifts from Postman et al. (2012) and using $\Omega_m = 0.27$, $\Omega_\Lambda = 0.73$, $h = 0.7$. This yields $\log_{10}(r_{500}/\text{kpc})$ in the range 3.00 to 3.23, a within-class spread of 0.23 dex.

**Class C per-bin wide-binary radius.** The v2 substrate had a placeholder $\log_{10}(\text{radius/kpc}) = -2.0$ for all Class C rows. This was a substrate construction bug: the underlying Chae (2023) bin definitions carry a real per-bin separation derived from the bin's $g_{\rm bar}$. The v3 substrate routes that real per-bin radius into the $\log_{10}(\text{radius})$ column, giving values in the range $-6.00$ to $-3.88$, a within-class spread of 2.12 dex.

**Class C per-row mass: synthesized.** The Class C rows are aggregate g_bar-binned stacks over thousands of Gaia DR3 wide pairs per bin (per Chae 2023). A per-row total binary mass cannot exist as physics for these rows because they are aggregate stacks rather than individual binaries. The v3 substrate carries a synthesized mass column, $\log_{10}(1.5 M_\odot)$ with a $\pm 0.15$ dex deterministic md5 jitter per row, flagged in `mass_log10_source_v3` as `synthesized_log_msun_jitter_chae2023_typical`. We disclose this synthesis explicitly: the column exists as instrumentation, to expose within-class variance to the apparatus, and not as per-binary mass measurement. Any v3 result on Class C therefore stays in the grammar-test category rather than the physics category. The Class A and Class C combined remain a grammar test of joint-form expressiveness; only Class A and Class B carry physics-grade variance.

The v3 enrichment changes what was ruled out by v2. What v2 ruled out is RAR unification at v2's surrogate-data quality. The v3 substrate, with real Umetsu+2016 cluster physics on Class B, lets joint $(M, r)$ forms have within-class degrees of freedom on Class B for the first time across all gp163d runs. Whether the expressive class of closed forms now bridges is the live question being executed across the v3 iterations.

---

## 3. The Apparatus

ZTARE is a mutator-judge loop. Each iteration runs four stages. Stage one is mutator-side proposal: a frontier language model is given the substrate description and the rubric, and is asked to produce a closed-form parametric law along with a thesis prose. Stage two is fitting: scipy.optimize fits the free parameters of the law against the visible Class A rows under a Bayesian information criterion budget. Stage three is gate evaluation: a deterministic harness runs the fitted law against the Class A holdout and the Class B + Class C farther-tail, plus a stack of structural anti-pattern gates. Stage four is judge scoring: a separate language model from a different family scores the thesis against the rubric, with access to the form, the thesis, and the gate outcome but not to the mutator's chain-of-thought.

The deterministic gate stack is the load-bearing component for the substrate-prober framing. Gates run on every iteration include the following.

R20-R24 are structural anti-pattern gates that flag persona-leaked anchors, hardcoded class-label hacks, parameter laundering against absent classes, and forms whose class branches reduce to one another at default parameter values (hidden universality). These were tightened during the 2026-04-26 cycle following an iteration that exhibited persona-leaked anchor injection (visible numeric values appearing in the form whose origin was the rubric prose rather than a fit).

R26, the G-CROSS-CLASS-FEATURE-SUPPORT gate, is new at this run. It flags any candidate law whose set of input features includes axes whose within-class range on any extrapolation class is below a configurable threshold. Concretely, R26 inspects the parametric form, identifies the axes the form depends on, and queries the substrate for the per-class within-class range of each. If a feature is depended-on by the form and is degenerate on a class for which the form is asked to predict, R26 fires. The gate's output is not a yes-or-no acceptance but a structural diagnostic that names the (feature, class) pair and the implication. This gate makes substrate-data ceilings legible to the apparatus.

Two architectural mechanisms support diversity across iterations. Forced REFRAME with AST-distance R1-rejection requires that after stagnation (the same form reappearing across iterations or the score plateauing), the next mutator proposal must differ from the prior champion by a configurable AST distance. The Cold-LLM Erdős seed is a separate query to the mutator family that ignores the substrate and asks for cross-domain candidate forms, which are then re-injected into the next iteration's prompt. Both mechanisms aim to break the universality attractor: when McGaugh's interpolation is the local minimum on Class A alone, mutators tend to converge back to it absent enforcement of architectural disjointness.

Calibration anchors are routed gate-side rather than mutator-side. The 2026-04-26 cycle moved the published $a_0$ value out of the mutator's prompt and into the gate harness, where it is used to evaluate fitted constants but is not visible to the mutator at proposal time. This addresses an earlier persona-leaked anchor incident.

The cross-family epistemic airgap between mutator and judge is partial at this run. Both ran on the same model family (mutator GPT-5.5; judge GPT-4.1), and we log this as a known limitation in Section 9.

### 3.1 R26 in implementation

R26 is implemented as a deterministic primitive in `src/ztare/diagnostics/substrate_critic.py::_detect_withheld_class_collapse`. It runs in milliseconds against the substrate's feature matrix and the parametric form's feature signature. The companion `cross_class_joint_form_blockers` field in the gate output flags the meta-pattern of interest: two or more withheld classes each collapsed on disjoint feature sets, which is the structural fingerprint of a substrate-data ceiling on any joint interpolation. The v2 substrate exhibits this fingerprint exactly. R26 was the load-bearing diagnostic for the v2 stuck-at-50 cap.

### 3.2 Level 2: Apparatus Self-Improvement

The R26 case surfaced a recurring failure mode of the apparatus itself: a diagnostic primitive can be silently scope-narrowed (R13's substrate_critic was scoped to the visible class only and therefore could not see the within-withheld-class collapse) and a gate can engage on every iteration without ever flagging. We added four meta-gates that audit the gate stack rather than the candidate forms.

**2A, static scope linter.** `make audit-gate-coverage`. A roughly 150-line deterministic linter that walks the diagnostics module AST and flags primitives whose loop scope excludes withheld classes. Catches scope-narrowing at write time.

**2B, dynamic effectiveness audit.** `make audit-gate-effectiveness`. Mines run logs for the pattern of a gate engaging but never flagging. The fingerprint we found was a form_str-keyed dictionary lookup that masked the engagement; the audit names this class of bug.

**2C, post-run LLM auditor.** `make audit-run-meta`. Opt-in via the run-config flag `enable_post_run_meta_audit: true`. After a run terminates, the LLM is given the run's telemetry and asked which existing gate, with what scope extension, would have moved the score. Cost is roughly $0.005 and roughly six seconds per run. In smoke tests, 2C correctly identified the same scope-narrowing pattern from raw run telemetry that the human operator and an offline backtest agent identified manually.

**EGE, evidence-gap-enrichment.** Opt-in via `enable_evidence_gap_enrichment_proposals: true`. When R26 fires, EGE proposes literature sources to fill the substrate gap. The v3 enrichment was performed manually in this case (the operator identified Umetsu+2016), and EGE is the architectural piece that mechanizes the loop.

### 3.3 Two Loops: ALU and RAM

Following Karpathy's distinction between compute and memory in a learning system, ZTARE has two improvement loops, not one.

The ALU loop is apparatus self-improvement: the Cage gate stack, AST-distance enforcement, R20-R24, R26, and the four meta-gates. When a run caps for an apparatus reason (a missing structural check, a scope-narrowed primitive, a calibration anchor leaking from prompt to form), the ALU loop is the right place to act.

The RAM loop is substrate self-improvement: R26 detection plus EGE proposals plus the manual `make enrich-substrate` workflow. When a run caps because the substrate lacks the variance the search needs, the RAM loop is the right place to act.

The recurring meta-failure mode is conflating the two. The v2 stuck-at-50 was initially read as an apparatus failure (the gate stack was permitting bad forms) when it was a substrate failure (the substrate did not contain the variance any joint form needed). The 2C post-run meta-audit is the routing decision: which loop to act on. Conflation is the failure mode the meta-gates exist to prevent.

---

## 4. Method: The gp163d_unified_accel Run

The run launched on 2026-04-26 with the substrate as described in Section 2 and the apparatus configuration of Section 3. The mutator was GPT-5.5; the judge was GPT-4.1. The iteration budget was set generously and the run terminated naturally after nine iterations when the ceiling diagnosis was filed by the apparatus and the operator authored a stop.

Following the in-loop run, we conducted a scipy-only backtest covering an extended set of candidate functional families. The backtest is documented in `scripts/backtest_rar_candidates.py` (first pass, six forms) and `scripts/backtest_rar_extended.py` (second pass, eleven additional forms). The backtest fits each candidate on 80% of the visible Class A rows and evaluates on the Class A 20% holdout, the Class B cluster rows, and the Class C wide-binary rows. The backtest is not a substitute for the in-loop run; it is a sweep over functional forms wider than the mutator proposed, to test whether the in-loop ceiling is a property of the mutator's exploration or a property of the substrate.

The reportable outputs of both passes are mean relative error per class. We use mean relative error rather than chi-squared because the substrate's per-row uncertainties are asymmetric across classes and the operator's stated acceptance threshold is in MRE. We pre-registered an acceptance criterion of MRE below 0.35 on Class A holdout and below 0.50 on Class B and on Class C, treated separately. Any form clearing all three is recorded as bridging.

After the v2 trace closed and the substrate was enriched (Section 2.1), the run was relaunched on the v3 substrate under the same apparatus configuration. The first two v3 iterations are reported in Section 5; the run is live and iterations 3 onward are pending at submission time.

---

## 5. Results: Apparatus Iterations

The nine in-loop iterations produced the following trace. We report a condensed summary; full debate logs and submissions are in `projects/gp163d_unified_accel/workspace/`.

| Iter | Form family | Class A holdout | Class B | Class C | Score | Notes |
|------|--------------|------------------|---------|---------|-------|-------|
| 1 | McGaugh universal, single $c$ | 0.28 | 0.74 | 1.71 | 50 | Asymptotic baseline |
| 2 | Mass-Gaussian-bump on $c(M)$ | 0.28 | 0.61 | 1.45 | 0 | R20 fired: persona-leaked anchor in the bump center |
| 3 | Algebraic rewrite of McGaugh | 0.28 | 0.74 | 1.71 | 50 | Mathematically equivalent to iter 1; AST-R1 rejection forced REFRAME |
| 4 | Tanh-bump on log $g_{\rm bar}$ | 0.31 | 0.69 | 1.55 | 50 | Optimizer collapse on the bump width caught and re-fit |
| 5 | Quadratic-log-c, $\log c(M) = a_0 + a_1 (M-10) + a_2 (M-10)^2$ | 0.28 | 0.53 | 1.71 | 50 | Best apparatus-side joint Class A + Class B; Class C unchanged |
| 6 | RG-flow exponent $1 + \gamma (M - M_0)$ | 0.30 | 0.58 | 1.69 | 50 | Class C flat at the universality value |
| 7 | Multifractal mass-radius coupling | 0.29 | 0.55 | 1.62 | 50 | Cold-LLM seed; within-class radius collapse on C limits expressiveness |
| 8 | Forced REFRAME — radius-only $c(r)$ | 0.34 | 0.62 | 1.40 | 50 | Class C improved on radius axis but Class B degraded; substrate-ceiling diagnosis filed |
| 9 | Universal McGaugh with explicit substrate-ceiling thesis | 0.28 | 0.74 | 1.71 | 50 | Apparatus filed null verdict |

The v2 apparatus did not produce a form clearing the farther-tail acceptance threshold on both Class B and Class C in any iteration. The best Class B result (0.53 at iteration 5) used the quadratic-log-c form which left Class C unchanged at 1.71. The best Class C result (1.40 at iteration 8) used a radius-only form which degraded Class B to 0.62. No form bridged.

Two observations are load-bearing. First, the mutator returned to McGaugh's universal interpolation as the local minimum on Class A repeatedly, including at iterations 1, 3, and 9. The architectural-disjointness enforcement (AST-distance R1-rejection at iteration 3) was necessary to break this attractor, not a redundant safety net. Second, the score-50 plateau across iterations 1, 3 through 9 is itself the diagnostic. A varying form that produces an unvarying score on the farther-tail says something specific about the substrate.

### 5.1 v3 Iterations (live)

After the v3 substrate enrichment, the run was relaunched. The first two iterations are reported below. Iterations 3 through 10 are pending at submission time.

| Iter | Form family | K | Judge raw | Apparatus cap | Score | Notes |
|------|--------------|---|-----------|----------------|-------|-------|
| v3-1 | Joint $(M, r)$ RG-flow logistic ($c_0$, $k_r$, $k_m$, $\log q$) | 4 | 24 | none (raw below 50) | 24 | First mutator engagement of the joint $(m, r)$ axis across all gp163d runs. Judge weakest-point: cross-class audit of feature $x$ unrealized; Newton-step claim is gated on x-alignment that the substrate does not validate |
| v3-2 | Pure $x$-only F1 RG-flow logistic with free exponent $q$ ($\log c$, $\log q$) | 2 | 86 | 50 (FARTHER_TAIL=0.85, per-class enforcement) | 50 | Fitted $\log c = -23.09$, so $c \approx 9.6 \times 10^{-11}$ m/s², consistent with Milgrom $a_0$. Fitted $\log q = -0.68$, so $q \approx 0.51$. R20-R24 all clean. Highest qualitative judge score on a clean form across all gp163d runs |

Two observations on the v3 trace, both held loosely.

First, iteration v3-2 is the first time across all gp163d runs that the mutator produced a non-McGaugh-family form that the apparatus rated as honest. R20 through R24 fired clean, judge raw was 86, and the apparatus cap to 50 came from a per-class farther-tail MRE threshold rather than from any structural anti-pattern.

Second, the fitted exponent $q \approx 0.51$ is a shift from McGaugh's universality value of $q = 1.0$. We flag this as the first physically-non-trivial signal in the run. We do not claim a finding. It is one observation across two iterations on a form family that has not yet been varied. The contribution is conditional on iterations 3 through 10 producing convergence to $q \approx 0.5$ across multiple form families. If they do, the signal is worth tracking. If they do not, it was an artifact of one iteration's basin of attraction.

---

## 6. Results: Exhaustive scipy Backtest

The backtest covered 17 functional families across two batches. The first batch tested six forms broadly aligned with the mutator's space: McGaugh universal, RG-flow, multifractal, tanh-bump, quadratic-log-c, and Hill. The second batch added eleven forms exploring radius dependence, joint mass-radius dependence, EFE-style external-field-effect couplings, piecewise McGaugh with a class-conditional handoff, Newton-MOND hybrid forms, and several pure-radius and pure-mass-quadratic alternatives. The full table is in Appendix A; the headline is that no form clears MRE below 0.5 on both Class B and Class C simultaneously while staying below 0.35 on Class A holdout.

The best joint mass-radius form is the joint exponential, $c_{\rm eff}(M, r) = c_0 \exp[\alpha_M (M - 10) + \beta_r r]$, achieving Class A holdout 0.28, Class B 0.59, Class C 1.33. This form has three free parameters and uses both axes as inputs. Class C remains far above the threshold.

The best radius-only form is a quadratic in $r$, with Class A holdout 0.34, Class B 0.62, Class C 1.40. The best mass-only form is the quadratic-log-c above. No form crosses the joint bridging threshold.

The pattern across the table is that improving on one farther-tail class requires sacrificing on the other. On the v2 substrate, mass-aware forms cannot improve Class C because Class C has only one mass value to register against. Radius-aware forms cannot improve Class B because Class B has only one radius value distribution that overlaps with Class A. Joint forms inherit both constraints.

### 6.1 v3 Re-Backtest (status note)

The 17-form table above is computed on the v2 substrate. Under v3 the within-class spans on Class B (0.73 dex on $\log_{10} M_{\rm bary}$, 0.23 dex on $\log_{10} r$) and on Class C (2.12 dex on $\log_{10} r$) are non-zero, and the joint-form predictions need recomputation. The v3 re-backtest is configured but not executed at submission time. We expect the headline pattern (one-sided improvement on one farther-tail class at the cost of the other) to soften on v3 for joint $(M, r)$ forms because the within-class degrees of freedom have been restored on Class B. The Class C numbers under v3 should be read as a grammar test rather than a physics test, because the Class C mass column is synthesized.

---

## 7. Diagnosis: Within-Class Feature Collapse at the Cross-Class Joints

The load-bearing finding is structural. We define a feature as collapsed on a class when its within-class relative range is below a small threshold (we use 0.02 in the gate harness, corresponding to a 2% relative span). On the gp163d_unified_accel substrate as configured:

- $\log_{10} M_{\rm bary}$ on Class A: range 7.69 to 11.43, span 3.73 dex (uncollapsed).
- $\log_{10} M_{\rm bary}$ on Class B: range 14.5 to 14.5, span 0.0 dex (collapsed).
- $\log_{10} M_{\rm bary}$ on Class C: range 11.0 to 12.5, span 1.5 dex (uncollapsed but note caveat).
- $\log_{10}(\text{radius})$ on Class A: range -1.0 to 2.0, span 3.0 dex (uncollapsed).
- $\log_{10}(\text{radius})$ on Class B: range 0.5 to 2.5, span 2.0 dex (uncollapsed).
- $\log_{10}(\text{radius})$ on Class C: -2.0 to -2.0, span 0.0 dex (collapsed).

The pattern is a diagonal of collapse. Class B is mass-collapsed; Class C is radius-collapsed. Any closed-form law $f(g_{\rm bar}, M, r)$ that depends nontrivially on both $M$ and $r$ has zero within-class degrees of freedom on Class B (the $M$ axis is a single point) and zero within-class degrees of freedom on Class C (the $r$ axis is a single point). The form's predictions on those classes therefore reduce, by structural necessity, to a single output value per class once the fitted parameters are fixed against Class A. There is no algebraic move available that breaks this constraint while remaining a function of the available axes.

The R26 G-CROSS-CLASS-FEATURE-SUPPORT gate names this directly. Run on the v2 gp163d substrate with any of the iteration 5-8 forms, R26 fires with two records. The first names $M$ as collapsed on Class B and the form as depending on $M$. The second names $r$ as collapsed on Class C and the form as depending on $r$. The gate's prose output is: "the joint(M, r) form has zero within-class variance to constrain its B-class prediction along the M axis; any free parameter on M is unconstrainable on this class. Symmetric statement for Class C and r."

The within-class collapse pattern was initially invisible to the prior generation of substrate-critic gates. R13, the previous substrate critic, was scoped to the visible class only and could not see the within-withheld-class collapse. Under R13 the v2 substrate looked clean. R26 closes this gap by inspecting per-class variance on every axis the candidate form depends on, including the withheld classes. The recursive-improvement insight is that the diagnosis the apparatus was missing in the v2 trace was a scope-narrowing in its own gate stack, not a missing form family. The Level 2 meta-gates (Section 3.2) were added to catch this class of scope-narrowing at write time and at run time, so the next instance of the same pattern is caught earlier.

The diagnosis of why the symbolic regressor cannot answer the v2 question is the load-bearing scientific contribution of the paper. It is not a finding that MOND fails on clusters, or that wide-binary deviations are real or artefactual. Both of those questions are beyond the v2 substrate's ability to answer in our framing. The diagnosis is that the data structure of the surrogate classes does not contain the variance that any joint interpolation form needs in order to discriminate. RAR unification on the v2 substrate is blocked by the substrate's data structure rather than by physics. When surrogate-collapsed features are replaced with per-system variation (the v3 substrate of Section 2.1), joint forms can plausibly bridge, and the apparatus is configured to attempt that bridge.

---

## 8. Implications

### 8.1 For RAR Physics

The cap is consistent with cluster-excess being real and with deep-MOND wide-binary deviations being either real or artefactual. None of the three regimes is ruled in or out. To distinguish among the live theoretical positions, two enrichments to the substrate are required. The first is per-cluster baryonic mass for the Class B sample at sufficient resolution that within-class mass variance recovers; published cluster catalogs supply these, and the integration is data-engineering rather than new measurement. The second is per-binary orbital separation for the Class C sample, which the Gaia DR3 wide-binary catalogs can supply directly, modulo the projection caveats that are already a load-bearing part of the wide-binary literature. With both enrichments, the substrate would expose a joint (M, r) variance pattern on all three classes, and the apparatus would have the variance it needs to discriminate among universality, scale-dependence, and external-field-effect hypotheses.

### 8.2 For Symbolic Regression Methodology

Three observations are load-bearing for practitioners.

First, an LLM-driven mutator that runs nine iterations does produce architecturally diverse forms but converges back to the universality attractor without enforcement. Of nine iterations, three returned to McGaugh's universal interpolation as the local minimum on Class A. Architectural-disjointness enforcement through AST-distance R1-rejection was necessary, not optional, to drive the search away from the local minimum. When the local minimum is strong on the visible class, this enforcement should be on by default.

Second, persona-leaked anchors are a real failure mode and require gate-side discipline. Iteration 2 in our trace failed gate R20 because the rubric prose contained a published value that the mutator embedded in the form as a numeric constant. Routing calibration anchors to the gate rather than the mutator addresses this directly. Calibration anchors should be gate-side as a matter of construction.

Third, substrate-data ceilings are detectable ex ante and should be. R26 is a deterministic gate that runs in milliseconds on the substrate's feature matrix and reports cross-class feature support before any iteration runs. We argue that R26 should be a precondition gate for any multi-class symbolic regression substrate.

### 8.3 For Methodology Publishability and Conditional Physics

The methodology contribution is settled today. R26, the four meta-gates of Section 3.2, AST-distance enforcement, and the ALU/RAM split together constitute a real architectural piece, and the v2 stuck-at-50 case is a worked example with a clean before-and-after.

The physics contribution is conditional. The first physically-non-trivial signal is the iteration v3-2 fitted exponent $q \approx 0.51$ on a clean F1 RG-flow logistic ($c \approx 9.6 \times 10^{-11}$ m/s², close to canonical Milgrom $a_0$, R20 through R24 clean). This is one observation across two iterations on a single form family. The conditional claim is that convergence to $q \approx 0.5$ across multiple form families in iterations 3 through 10 makes the signal worth tracking as a candidate departure from McGaugh universality at $q = 1$. Otherwise the v3 substrate ceiling holds and the null sharpens. Either outcome is reportable.

### 8.4 For Substrate Construction

Surrogate-value collapse is a class of bug that is invisible to the human substrate-builder. The collapse arises naturally from the construction step "let me represent class B by its canonical value." The single canonical value is correct as a class-level summary statistic and is wrong as a per-row feature for a symbolic regressor. The same data that supports the class-level summary is the data that does not support per-row interpolation. The substrate-builder produces the collapse without intending to. The mutator produces forms that respect the collapse without observing it. The judge scores the forms without seeing the constraint that produced them. The collapse is invisible at every layer until the gate names it.

The practical recommendation is that every multi-class symbolic regression substrate should run an R26-style cross-class feature support audit at construction time. The audit's output is a per-class, per-feature variance report with explicit collapse flags. If a class is collapsed on a feature the regressor will need, the substrate-builder must either enrich that class on that feature or restrict the search space to forms that do not depend on the collapsed axis.

---

## 9. Limitations

We list five honestly.

**Single-mutator, single-judge, same-family.** The mutator was GPT-5.5 and the judge was GPT-4.1. Both are OpenAI family models. The cross-family epistemic airgap that the apparatus aims to provide is partial at this run. We log this as a known limitation. A second run with a different-family judge (Anthropic Claude or Google Gemini) is configured and has not been executed at submission time.

**Backtest scope.** The scipy backtest tested 17 functional families. The space of expressive closed forms is larger. We cannot rule out that an exotic family outside our search bridges all three regimes; what we can say is that a search covering the families publicly used in RAR analyses (McGaugh, Tian, RG-flow, multifractal, Hill, EFE-style, piecewise, joint mass-radius) does not bridge.

**Surrogate-value substrate caveat.** The Class B and Class C surrogates are not per-system data. What we ruled out is RAR unification at the data quality our substrate exposes, not RAR unification at any quality. A substrate with per-cluster baryonic masses and per-binary orbital separations may admit forms that this substrate does not. We intend to test this in a follow-up.

**Cold-LLM seed asymptotic-shape mismatch.** Two of the cross-domain candidate forms emitted by the Cold-LLM Erdős seed were physically wrong shape on inspection: a Hill function and a Nelson-Siegel-style curve, both of which fail the asymptote $y \to x$ at large $x$. The cold-seed mechanism currently lacks an asymptotic-shape prior. This is a known apparatus limitation and is logged as a follow-up.

**Single substrate.** This paper reports one substrate. The methodological generalization (R26 as a precondition gate) is supported by one case. A second substrate with a structurally different cross-class variance pattern is needed before the methodological claim ranges beyond one example. Paper 5 (the treatise) discusses the general framework; this paper provides one anchored instance.

**v3 enrichment is one weak-lensing source.** The Class B per-cluster $M_{500c}$ values are taken from a single stacked weak-lensing analysis (Umetsu et al. 2016). Independent confirmation from a different cluster mass survey is desirable before the v3 result, whatever it is, is treated as robust to systematics in the cluster-mass calibration.

**v3-2 single observation on $q$.** The fitted exponent $q \approx 0.51$ at iteration v3-2 is one observation. The form family at v3-2 (pure $x$-only F1 RG-flow logistic) has not been varied in adjacent iterations. The signal is conditional on convergence across iterations 3 through 10 and across alternative joint-form families. We log it as a candidate, not a finding.

**Class C mass synthesis.** The Class C mass column in the v3 substrate is synthesized (Section 2.1). Any v3 result that depends on within-Class-C mass variance is a grammar test of the apparatus, not a physics measurement. v3 results that combine Class A and Class B remain in the physics category; v3 results that combine Class A and Class C, or all three classes via a mass-dependent form, stay in the grammar category.

---

## 10. Future Work

Four extensions follow from the present run.

**Per-system mass and radius enrichment.** A follow-up substrate, gp163e or successor, will replace the Class B mass surrogate with per-cluster baryonic mass measurements and the Class C radius surrogate with per-binary orbital separation. With both enrichments live, the apparatus will be re-run under the same configuration. If joint mass-radius forms now bridge Class A and Class B at MRE below 0.5 while staying below 0.35 on Class A holdout, that is a positive Newton-step finding. If they do not, the null is sharper than the present null because the substrate-ceiling diagnosis is removed.

**R26 as a precondition gate.** The R26 gate is currently a per-iteration diagnostic. We will promote it to a precondition gate that runs at substrate-build time and emits a structured warning before iteration 1. Substrate audits should be ex ante on this dimension.

**Explicit external-field-effect feature.** The MOND-with-external-field-effect family of laws requires an explicit $g_{\rm external}$ feature that is not in the gp163d substrate. Adding this feature is data-engineering against the SPARC environmental catalog and is configured for the next substrate revision.

**Methodological generalization.** Every multi-class symbolic regression substrate this lab builds going forward will run R26 ex ante. The intent is to detect data ceilings before iteration. We will report the gate's hit rate across substrates as a measure of how often substrate-ceiling collapse is the silent constraint on a search.

**Level 2 meta-gates as ongoing apparatus work.** The four meta-gates of Section 3.2 (2A static scope linter, 2B dynamic effectiveness audit, 2C post-run LLM auditor, EGE evidence-gap-enrichment) are shipped and active. The roadmap is to expand 2C's coverage to multi-run rollups, to lower 2B's false-positive rate on legitimately latched gates, and to extend EGE from R26-triggered enrichment proposals to a broader set of substrate-gap signatures.

**EGE as the architectural piece for substrate-prober generalization.** The substrate-prober paradigm generalizes only if the apparatus can both detect substrate gaps (R26 plus the meta-gates) and propose closes for those gaps (EGE). Mechanizing the literature-source proposal step is the bridge from the ALU loop to the RAM loop. The Umetsu+2016 enrichment for v3 was performed manually; the goal for the next paradigm-level case is for EGE to surface the candidate source with the operator approving rather than discovering.

**v3 iterations 3 through 10.** The most immediate piece of future work is the running v3 trace itself. The convergence test on the iteration v3-2 free exponent $q \approx 0.51$ across multiple form families is the live experiment.

---

## 11. Conclusion

We searched for a closed-form law of the radial acceleration relation that bridges galaxies, galaxy clusters, and wide binaries simultaneously within a stated error threshold. On the v2 substrate we did not find one. The diagnosis, produced by the apparatus and made explicit by a new cross-class feature-support gate, is that the substrate's withheld classes carry a single canonical value on the axis the search needs in order to discriminate. The v2 cap is a substrate-data ceiling rather than a grammar ceiling.

The methodological contribution is settled today. R26, the Level 2 meta-gates of Section 3.2, AST-distance enforcement of architectural disjointness, and the ALU/RAM split together name a worked architectural piece, with the v2 case as a clean before-and-after.

The physics contribution is conditional on the v3 substrate-enriched run. The v3 substrate replaces the v2 surrogate values with per-cluster Umetsu+2016 baryonic masses and radii on Class B and with real per-bin radii on Class C. The first v3 iteration is the first across all gp163d runs to engage the joint $(m, r)$ axis. The second v3 iteration produced a clean F1 RG-flow logistic with free exponent fitted to $q \approx 0.51$, with judge raw score 86 (the highest on a clean form across the run) and apparatus cap to 50 driven by the per-class farther-tail threshold rather than by any structural anti-pattern. We hold the $q \approx 0.51$ observation loosely. The conditional claim is that convergence to $q \approx 0.5$ across multiple form families in iterations 3 through 10 would make the signal worth tracking; absent that convergence, the substrate ceiling holds and the null sharpens.

Either outcome is reportable. The methodological apparatus is configured, gated, audited at Level 2, and ready.

---

## Appendix A — Backtest Form Family Table

The following 17 functional families were tested in `scripts/backtest_rar_candidates.py` and `scripts/backtest_rar_extended.py`. Each row reports mean relative error on the Class A holdout (n = 595 rows after split), Class B clusters (n = 84 rows), and Class C wide-binaries (n = 12 rows). All fits used scipy.optimize.minimize with L-BFGS-B and Nelder-Mead fallback; some forms used differential_evolution for global initialization. Pre-registered acceptance is MRE below 0.35 on Class A holdout and below 0.50 on Class B and on Class C separately.

| # | Form family | Free params | Class A | Class B | Class C | Bridges? |
|---|--------------|-------------|---------|---------|---------|----------|
| 1 | McGaugh universal $c$ | 1 | 0.28 | 0.74 | 1.71 | no |
| 2 | RG-flow exponent in $M$ | 4 | 0.30 | 0.58 | 1.69 | no |
| 3 | Multifractal mass-radius | 4 | 0.29 | 0.55 | 1.62 | no |
| 4 | Tanh-bump on $\log g_{\rm bar}$ | 3 | 0.31 | 0.69 | 1.55 | no |
| 5 | Quadratic-log-c in $M$ | 3 | 0.28 | 0.53 | 1.71 | no |
| 6 | Hill function in $g_{\rm bar}$ | 3 | 0.36 | 0.78 | 1.50 | no |
| 7 | Radius-linear $c(r)$ | 2 | 0.32 | 0.66 | 1.43 | no |
| 8 | Radius-quadratic $c(r)$ | 3 | 0.34 | 0.62 | 1.40 | no |
| 9 | Joint $(M, r)$ exponential | 3 | 0.28 | 0.59 | 1.33 | no |
| 10 | Joint $(M, r)$ quadratic | 4 | 0.28 | 0.57 | 1.36 | no |
| 11 | $g_{\rm bar}$-threshold piecewise | 3 | 0.41 | 0.71 | 1.45 | no |
| 12 | Newton-MOND hybrid (sigmoid) | 3 | 0.30 | 0.65 | 1.50 | no |
| 13 | EFE-style $c$ depressed | 3 | 0.29 | 0.61 | 1.55 | no |
| 14 | Piecewise McGaugh class-conditional | 4 | 0.29 | 0.55 | 1.40 | no |
| 15 | Pure mass-quadratic on $g_{\rm obs}$ | 3 | 0.45 | 0.84 | 1.55 | no |
| 16 | Pure radius-quadratic on $g_{\rm obs}$ | 3 | 0.41 | 0.78 | 1.42 | no |
| 17 | Joint cross-term $(M-10) \cdot r$ | 4 | 0.28 | 0.55 | 1.36 | no |

The table reads as a frontier. Forms favoring Class B (rows 2, 5, 9, 10, 14, 17) sit at Class B around 0.53 to 0.59 with Class C above 1.30. Forms favoring Class C (rows 7, 8) reach Class C around 1.40 with Class B at 0.62. No row clears both. The form-family axis cannot get past the substrate's data structure.

---

## References

Chae, K.-H. (2020). Distinguishing dark matter, modified gravity, and modified inertia with the inner and outer parts of elliptical galaxies. *The Astrophysical Journal*, 903, 130.

Chae, K.-H. (2023). Breakdown of the Newton-Einstein Standard Gravity at Low Acceleration in Internal Dynamics of Wide Binary Stars. *The Astrophysical Journal*, 952, 128.

Hossenfelder, S., McGaugh, S., and Mistele, T. (2024). Reanalysis of the radial acceleration relation in galaxy clusters. *Physical Review D* (preprint).

Lelli, F., McGaugh, S. S., and Schombert, J. M. (2016). SPARC: Mass models for 175 disk galaxies with Spitzer photometry and accurate rotation curves. *The Astronomical Journal*, 152, 157.

McGaugh, S. S., Lelli, F., and Schombert, J. M. (2016). Radial acceleration relation in rotationally supported galaxies. *Physical Review Letters*, 117, 201101.

Pittordis, C., and Sutherland, W. (2023). Wide binaries from Gaia EDR3: testing for a Modified Gravity signal. *The Open Journal of Astrophysics*, 6.

Tian, Y., Umetsu, K., Ko, C.-M., Donahue, M., and Chiu, I.-N. (2020). The radial acceleration relation in CLASH galaxy clusters. *The Astrophysical Journal*, 896, 70.

Umetsu, K., Zitrin, A., Gruen, D., Merten, J., Donahue, M., and Postman, M. (2016). CLASH: Joint Analysis of Strong-Lensing, Weak-Lensing Shear, and Magnification Data for 20 Galaxy Clusters. *The Astrophysical Journal*, 821, 116. arXiv:1507.04385.

Vikhlinin, A., Kravtsov, A., Forman, W., Jones, C., Markevitch, M., Murray, S. S., and Van Speybroeck, L. (2006). Chandra Sample of Nearby Relaxed Galaxy Clusters: Mass, Gas Fraction, and Mass-Temperature Relation. *The Astrophysical Journal*, 640, 691.

Postman, M., et al. (2012). The Cluster Lensing And Supernova Survey with Hubble (CLASH). *The Astrophysical Journal Supplement Series*, 199, 25.

Popper, K. (1959). *The Logic of Scientific Discovery*. Hutchinson.

Munger, C. T. (2005). *Poor Charlie's Almanack*. Donning Company Publishers.

Alami, D. (2026). The cognitive firm: managerial capitalism for artificial intelligence. (Paper 4 of this series; companion methodological framing.)

Alami, D. (2026). ZTARE: a treatise on adversarial symbolic regression. (Paper 5 of this series; full apparatus specification.)
