# ZTARE Novelty Audit vs Cold-LLM Null

> **Seam metadata** · `seam_id:` 2026_04_25_novelty_audit_vs_cold_llm · `track:` audits · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

**Question:** Is ZTARE producing genuinely novel science, or is it rigor-wrapping outputs that a zero-shot cold LLM could produce immediately?
**Date:** 2026-04-25 (night)
**Auditor:** subagent (general-purpose, full read access to repo)
**Scope:** every claimed empirical finding in `EXPERIMENT_TRACK_RECORD.md`, `ZTARE_BOARD.md`, `cognitive_gym.md` Part 5, README "Engine Track Record," `papers/experimental_math_letter/main.tex`, papers 1–6 abstracts/claims.
**Method:** for each finding, ask "what would a cold zero-shot LLM with cold variables and scipy output?" Categorize into A (pure recital) / B (recital + rigor) / C (apparatus-only) / D (indeterminate). Strip the apparatus, assess publishability.

---

## Verdict (Executive Summary)

The honest split, after auditing every finding row in the four
canonical surfaces, is approximately:

- **Bucket A (pure recital, cold LLM gets it in one shot): ~10–15%** of claimed findings.
- **Bucket B (recital + rigor, the apparatus contributes reproducibility, holdout discipline, cold-variable cage, cross-family pairing, but the *answer* is in published literature or trivially derivable): ~55–60%** of claimed findings.
- **Bucket C (apparatus-original, a cold LLM cannot produce these): ~25–30%** — concentrated in (a) the Lucky-number validity-horizon and (ln n)² correction, (b) Ulam reciprocal-rotation density estimate matching Steinerberger to 0.07%, (c) the cross-family matched-pair convergence on gp159, (d) the gp154 K≤7 negative result with form-class robustness, (e) the apparatus-meta-findings (grammar ceiling H-COMPUTE-01/H-GRAMMAR-01 chain, sandbox_06 forced vocabulary escape, gaming taxonomy from Paper 1, the M-form governance evidence in Paper 4), and (f) the BOS-contamination + cancellation-invariance findings in Paper 6.
- **Bucket D (indeterminate, would need actual cold-LLM run): ~5%** — primarily the partition-family substrates where I cannot, without running a cold call, perfectly settle whether the LLM emits the right-formula-and-coefficient or just the right-topology-and-wrong-coefficient.

**Net answer to the operator's question:** The apparatus is not pure rigor-wrapping. There is a real, ~25–30% core of findings a cold LLM would not produce. But the public framing of the science track over-weights the partition-family recoveries (Bucket B) and under-weights the genuinely apparatus-original findings (Bucket C). The Hardy–Ramanujan-style recoveries should be presented as **calibration of the instrument**, not as discoveries. The Lucky-number (ln n)² correction, the Ulam reciprocal-rotation Steinerberger match, the gp154 bounded null, the cross-family matched pair, the grammar-ceiling chain (crucial_01 → 02 → 02_ext → 03), and the cognitive-camouflage gaming taxonomy are the apparatus-original results. Papers 1, 4, 5, and 6 are largely Bucket C. The experimental-math letter mixes B and C and currently presents some B claims with too much apparatus-credit attached.

The "10 substrates, zero false positives" framing is technically true but selection-conditioned. The cold-LLM null is not "would the LLM hallucinate something" but "would the LLM produce the same answer." On the partition substrates, it would produce the same *topology* roughly 50–87% of the time (the apparatus's own internal data, see exp-math letter §2.1 final paragraph). The apparatus contribution is *parsimony* (compressing 6–7 param proposals to k=3), holdout enforcement, and cold variable names. That is real. It is not a discovery engine on those substrates; it is a *recovery-under-discipline* engine.

---

## Per-finding audit

| Finding (with source) | Bucket | Cold-LLM test result (predicted) | Apparatus contribution | Publishable as-is? |
|---|---|---|---|---|
| GP-088 / A000041 partition function `2.631·sqrt(n) − 1.172·log(n) − 1.445/n − 1.744`; coeff matches π·sqrt(2/3) to 2.6%. (exp-math letter §2.2, cognitive_gym Part 5 row 1, README Engine Track Record) | **B** | Cold LLM given (n, log p(n)) pairs in cold form will propose `a·sqrt(n) + b·log(n) + c` ≥50% of the time (Hardy–Ramanujan is in training data; the LLM's own composition log shows 11/15 sqrt+log proposals per exp-math letter §2.1). It will likely emit a 5–7 param overparameterized form rather than k=3, but the topology is recital. | Cold variables, holdout split, automated parsimony compression that strips overparameterization, deterministic gate enforcement. The recovery itself is recital; the **forced parsimony** is the apparatus contribution. | As calibration target ✓. As a discovery ✗. |
| A000009 / Q(n) `1.813·sqrt(n) − 0.737·log(n) − 1.735`; coeff matches π/sqrt(3) to 0.04%. (exp-math letter §2.3, cognitive_gym row 2) | **B** | Same as above. The π/sqrt(3) leading coefficient and −3/4 subleading are in any analytic combinatorics textbook. A cold LLM emits the topology directly. | Cold variables; rival-exclusion at 100–3900× margin tested deterministically; pinning a=π/sqrt(3) reduced farther-tail residual to within gate. The rival-exclusion margin is the apparatus addition. | As calibration ✓. The "6 rivals ruled out at 100–3900× margin" is a real apparatus output, but it is not new science. |
| A000607 prime partitions `sqrt(n/log n)` topology recovered Stage 2. (exp-math letter §2.6, cognitive_gym row 4) | **B** | This is closer to the boundary. The Vaughan-style asymptotic for prime-partitions has the form `exp(C·sqrt(n/log n))`, so on log-data the topology is `sqrt(n/log n) + log(n)`. A cold LLM would likely propose `sqrt(n)`, fail, then iterate. It is published, so it is recital, but it is not first-shot recital. The compression-stage hit was Stage-2 (compositional), Stage-1 (additive) failed — the engine itself reports this. | Stage-1→Stage-2 compositional grammar expansion; the depth-1 composition was the decisive apparatus contribution. **This is the closest partition-substrate to Bucket C.** | As discovery ✗ (Vaughan published). As methodology demonstration of compositional templates ✓. |
| A001156 / square partitions `n^(1/3) + log(n)`, exponent within 0.5% of Meinardus 1/3. (exp-math letter §2.4) | **B** | Meinardus' theorem gives 1/3 directly; published 1954. Cold LLM likely emits the n^(1/3) topology if given hints; with truly cold variables it might emit a power-law family and find ≈0.33. Not first-shot but well-supported. | Cold variables; deterministic-gate-rejected at absolute residual; correctly reported as topology-ID-not-certification. The honesty about the exponent bias being a finite-window artifact is apparatus-original framing. | The honesty about the gate failure is the publishable bit. The recovery itself is recital. |
| A002865 partitions excluding 1 `sqrt(n) + log(n)`, coeff π·sqrt(2/3). (exp-math letter §2.5) | **B** | Same as A000009 (same Hardy–Ramanujan family modulo (1−q) factor). | Cold variables; absolute-vs-normalized-residual finding (same pattern as A001156). | Calibration ✓; not discovery. |
| A002858 / Ulam UNDERIDENTIFIED, then reciprocal-rotation `n/U(n)`, fitted constant 13.50 vs Steinerberger 13.52. (exp-math letter §2.7) | **C** | Steinerberger's 2017 conjectured density (≈13.5) is published, so the *number* is recital. But the **observable rotation** (compress fails on z; try 1/z; 1/z compresses trivially) is an automated apparatus move. A cold LLM asked "find a closed form for U(n)/n" would produce one; it would not emit "no closed form, try the reciprocal observable." The 0.07% agreement at n=770K is also a scale that a cold LLM cannot produce without sieve compute. | Automated post-no-gate-passing-form transform pipeline; the rotation is documented as apparatus-original. The Steinerberger constant itself is recital, but recovering it via *automatic representation rotation* is the novelty. | The methodological move ("observable rotation") is the publishable kernel. The constant value is corroboration of Steinerberger. |
| A000959 / Lucky numbers, `a·log(n) + b/n + c`, leading coeff 1.200 at 50K; **drift to 1.177 at 500K**, log-quadratic correction `−0.00267·(log n)²` recovered, b_eff converging toward Hawkins limit 1.0 at n~10^17. (exp-math letter §2.1, cognitive_gym row 3) | **C** | Hawkins (1957) gave the asymptotic L(n)~n·log(n) (coefficient 1). The *finite-n approach rate* and the specific (log n)² correction topology are **not in training data** (verified by the apparatus's own bibliography survey; see paper §2.1 "to our knowledge, no published result gives a specific sub-leading correction topology for the Lucky number counting function"). The 2% drift over a decade and the validity horizon are apparatus measurements, not retrievals. | The full margin-of-safety pipeline: detect drift, exhaust additive extensions, force compositor injection, recover non-additive correction, extend grammar permanently with regression test. **This is the strongest single Bucket C result in the science track.** | ✓ Yes — the validity-horizon framing and the (log n)² correction with effective-coefficient extrapolation to the Hawkins limit are apparatus-original. |
| KWW polymer `a·exp(−b·t^c) + d`, c=0.630 (cognitive_gym row 8, exp-math letter §2 implicit) | **A/B** | KWW (Williams–Watts 1970) is textbook. Any LLM given (t,v) decay data will propose `exp(−(t/τ)^β) + offset` immediately. Score 98 ceiling explicitly attributed to the **Prony-series objection**, which is a 100-year-old literature objection. | Cold variable names, score-ceiling behavior demonstrates the apparatus's epistemic discipline (reaches the right form, then refuses to push past the correct epistemological limit). The discipline is apparatus-original; the answer is textbook. | As a *cage validation* (proves the apparatus reaches the correct form when the form is reachable) ✓. As discovery ✗. |
| sandbox_20 real polymer `t^(−B)·exp(−C·t)`, B=0.433 vs theory 2/5; **externally validated by domain practitioner**. (cognitive_gym row 10) | **B** | Power-law × exponential cutoff is a standard rheology family (Kapnistos et al. 2008 cited). The form is published. Cold LLM with sparse log-log data likely emits this family. | Cold variables, normalized RMSE gate, external validation — the external validation is rare and worth highlighting; without it the result would be a noisy fit to a textbook form. | As reproducibility-under-discipline ✓. As discovery ✗ (Kapnistos already published). |
| DFDO sandbox_18 / GP-103 — engine found 12-param ratio-of-exp surrogate (score 95) but never proposed the true 6-param two-regime additive. **Correct refusal of single-regime fit followed by topology-induction-gap diagnosis.** (cognitive_gym row 9, EXP TRACK F-GP096-DFDO-01, F-GP103-01) | **C** | Cold LLM given a two-regime substrate would propose either component and stop. The diagnosis "engine explored each component in isolation but never the additive composition; this is a structural blind spot called the topology induction gap" is meta-finding about LLM mutator search behavior under adversarial pressure. No cold LLM produces this self-diagnosis. | The entire apparatus structure (failure-family naming, structural memory, negative-space extractor) produced this finding. | ✓ Yes. The finding is "LLMs under composition pressure don't try A+B when A and B individually fail" — a documented mutator blind spot. |
| sandbox_06 Planck recovery — sealed GT `A·phi^p / (exp((γ·phi/ψ)^q)−1) + offset` recovered to machine precision in ≤10 iters from naive power-law seed (E-GP023-S06-01, F-GP023-S06-01). | **C** for the apparatus claim, **B** for the math | The functional form (Planck/Bose–Einstein occupancy) is textbook physics. A cold LLM given the data with full physics labels gets it instantly. The apparatus claim is *not* "we found Planck"; it is "the apparatus forced a general-purpose mutator with naive power-law seed to escape its regression-toolbox prior and converge on a non-elementary transcendental form under sealed gates." That second claim is calibration-of-cage and is not something a cold LLM can demonstrate (it requires the cage). The track-record row F-GP023-S06-01 explicitly scopes this as "recovery under guided constraint, not discovery." | The cage itself is the apparatus contribution. | ✓ As calibration of the cage. F-MISSION-01 correctly notes: this is the precondition for discovery, not discovery. |
| crucial_01 → 02 → 02_extended → 03 chain: **grammar ceiling H-COMPUTE-01 + H-GRAMMAR-01.** Same evidence, same model, same iters; doubling compute gains 5 points; adding one primitive (UNIVERSAL_DENOMINATOR) recovers Planck. (E-GP083-CRUCIAL-01..03, F-INS021/022) | **C** | Cold LLM cannot produce a controlled experiment proving "compute does not break grammar ceiling; one new primitive does." This is an apparatus-on-itself finding. | The entire infrastructure for sealed evidence + sealed grammars + matched runs. | ✓ Strong, publishable methodology finding. The grammar-ceiling claim is the central methodological contribution of the experimental-math letter §2 "two ceilings." |
| gp159 retrieval-trap: cross-family matched pair, gemini-pro 93 vs claude-opus 90 on synthetic α=C1/(d+C2) with **non-standard** constants C1=3.71, C2=0.89. (EXP TRACK E-GP159-01, F-GP159-01) | **C** | This is *by construction* a Bucket C finding. The non-standard constants are not in literature. The matched-pair convergence requires two independent mutator families and the same apparatus to score them. A cold LLM call cannot produce a "cross-family matched pair." | Everything. Mutator separation, judge separation, anti-retrieval gate, identical sandbox. | ✓ The strongest single piece of cross-family-stability evidence in the repo. Should be the headline of any "the apparatus is reproducible" claim. |
| gp160 asymptotic-wall: synthetic exp+power decay, score 90, asymptotic wall gate prevents polynomial-trap extrapolation. (E-GP160-01) | **C** (synthetic, scoped) | Cold LLM with cold variables would still likely propose exp+power. But the **asymptotic-wall gate** that catches polynomial extrapolation to negative values at d=100,150,200 is an apparatus-original test. | The gate. | ✓ As gate-validation evidence. |
| gp161 MDL anti-Goodhart: synthetic K=10 oscillatory truth, score 90. **Apparatus did not force K≤5.** (E-GP161-01) | **C** | Tests whether the apparatus's parsimony pressure causes Goodharting; this is a test the apparatus designed for itself. Cold LLM cannot run this test. | The MDL-as-rubric-metric design and its anti-Goodhart probe. | ✓ As MDL-rubric-validation evidence. |
| gp154 / Pythia neural scaling: K≤7 wall **form-class robust** across 13 forms × 6 hypothesis families. Bounded null with structural justification. (cognitive_gym addition; EXP TRACK F-GP154-CLASS-K-AS-DIST-SHIFT) | **C with caveats** | A cold LLM cannot produce "the wall is form-class robust to multiplicative N×D, convention-conditioned, log-link, sigmoid crossover, negative-coefficient, loss-type-aware augmentation" without the apparatus running the matched comparisons. **However**, the v4 charter itself flags that the diagnostic priors were derived from the same dataset the holdout draws from, so a Nature MI panel ruled this **exploratory not confirmatory**. The bounded-null claim downgrades from "confirmed" to "candidate hypothesis to test on independent data." | Stratified 5-fold CV on hand-authored forms; the scoping is apparatus-original. | ✓ As a methodology paper (ZTARE as ontological diagnostic tool, distinguishing form-class insufficiency from feature insufficiency from distribution shift). Not as a "we proved Class-K is impossible" claim. The repo's own README (Engine Track Record bounded-null row) currently presents the strong version; should be tempered. |
| Paper 1 (Cognitive Camouflage): 9 gaming strategies cataloged across 453 debate logs, 6 domains, 3 mutator families. Cross-mutator replication. | **C** | A cold LLM does not produce a taxonomy of LLM gaming strategies under recursive optimization pressure. This is observation of a system in operation, not retrieval of a known taxonomy. The strategies (Blame Shield, Float Masking, Fake AutoDiff, Cooked Book RNG, etc.) are named primitives extracted from telemetry. | The whole apparatus is the experimental setup. | ✓ Already published on SSRN. Clearly Bucket C. |
| Paper 2 (Adversarial Precedent Memory): primitive-ordering effects, evaluator-hardening via mined precedents. | **C** | Benchmark methodology + ablation results from a real evaluator-hardening run. Not retrievable. | The benchmark, the precedent schema, the crux-first ablation. | ✓ Bucket C. |
| Paper 3 (Contract-Governed Hardening): meta-runner with deterministic Python promotion contracts; 6 stages over 4 months; 1 sloppy promotion blocked. | **C** | The 6-stage history is empirical from one operated system. Not retrievable. | The architecture of the meta-runner is novel-as-engineering, even if the conceptual lineage (CI/CD + process supervision + Constitutional AI) is acknowledged. | ✓ Bucket C, scoped to single-system N=1 as the paper itself states. |
| Paper 4 (Cognitive Firm): M-form governance, write-scope-guard, two unauthorized-write incidents caught and archived, 24 governed self-improvements, fractal-Goodhart at 5+ layers. | **C** | The 4-month operational evidence (specific incidents, specific archives, fractal-Goodhart instances at evaluator/kernel/supervisor layers) is empirical and unique. Cannot be retrieved. | Everything is the apparatus running on itself. | ✓ Bucket C, scoped N=1. |
| Paper 5 (Principles of Epistemic Verification): 10-operation decomposition of "judgment," 7 structural principles, 3-tier ledger, residual of 3 commitments that resist decomposition. | **C** with **abductive** caveat | The paper itself flags (Front Matter §4) that the decomposition is *abductively proposed* on one corpus, not empirically established. A cold LLM does not produce "ten named operations of epistemic verification with named pathologies derived from telemetry." | The corpus and the abductive extraction. | ✓ Bucket C **only** at the scope the paper states (proposed-from-one-corpus, awaiting holdout replication). The repo's framing of this as "the foundational treatise" is appropriate; presenting the 10 ops as established science is not. |
| Paper 6 (Neural Scaling): BOS-contamination artifact in transformer rank measurements, cancellation invariance (~70% architectural floor, training-invariant in some families and learnable in others), cross-architecture replication including Mamba SSM. | **C** | The BOS norm (35× regular tokens at layer 12 in Pythia-410M) and the trained-vs-untrained cancellation comparison (70.2% vs 72.2% in Pythia, 76.0% vs 62.0% in Mamba) are direct empirical measurements. Cold LLM cannot produce these. The U-shaped ablation curve and the YES/NO alignment-learning split across 7 model families are also direct measurements. | Most of the empirical content is independent of ZTARE-as-validator; this is more a standalone neural scaling paper. The ZTARE connection (template-enumeration finding `sqrt(n/log n)` beats power-law on Pythia loss) is real but minor relative to the BOS and cancellation findings. | ✓ Bucket C. The paper's own §7.2 list of 5 claims is well-scoped. |
| "Marginal cost ~$1 per insight at gpt-4.1 + gemini-flash" (F-INS019-01) | **C** | Empirical cost from one run. Not retrievable. | The cost-tracking telemetry. | ✓ as an apparatus-economics datapoint, scoped to one substrate one model pair. |
| Topology induction gap, structural blocker vs ceiling-breaker dichotomy, tail_generalization as convergent blindspot (GP-149 mining, F-TAIL-GEN-CONVERGENT-01) | **C** | Mining 1825 records across 84 projects to find that "tail_generalization meta-critique kills any impossibility-thesis substrate" is empirical apparatus-on-itself work. Not retrievable. | The entire mining infrastructure. | ✓ Bucket C, methodology-paper material. |
| H-GP073-S15-01/02/03 (Component B = topological pruner not semantic injector; LLM corrector-degeneracy on integer-output substrates; Component C = residual fingerprinting architectural gap) | **C** | These are component-level findings extracted from sandbox runs. Cold LLM cannot produce "Component B operates on AST syntax not semantics; here is the ratio of pruned to total space that bounds its effectiveness." | The runs. | ✓ Bucket C. |
| Connes/Hilbert–Pólya (GP-125): Riemann zero spacing CV 0.293 vs target 0.465; **bimodal phase transition** in operator space across 28 generator families; polynomial-confinement structural ceiling. (E-GP125-01, F-GP125-BIMODAL-GAP, F-GP125-A10-DENSE-01) | **C** | The bimodal gap (no operator family hits sv ∈ [0.37, 0.54]) and the negative result on dense-arithmetic operators at N=800 are empirical. Specific spacing-CV measurements not in literature. | The infrastructure; the SFF-L1 metric application; the matched generator sweeps. | ✓ Bucket C, but the result is null (failed to find Hilbert–Pólya operator), so publishability is "informative null in operator space" — appropriate scoping per the row. |
| GP-148 mining findings: 1825-record archive, pivot-effectiveness disambiguated by weakest-link class, persistence-and-cycling champion profile, tail_generalization as central blindspot (refuted Lollapalooza hypothesis) | **C** | Empirical mining of one operated system. | The archive itself, the enrichment pipeline, the failure taxonomy. | ✓ Bucket C, methodology-paper material. |
| GP-150 FOM (fractional spatial operators) self-identified as v3.0 substrate gap by the apparatus auditing its own architecture. Primitive shipped, 4/4 unit tests pass, unwired pending GP-146 validation. | **C** | The apparatus-self-audit producing a concrete feature request is novel methodological pattern. | Everything. | ✓ Bucket C as apparatus-recursive-design instance. |
| GP-097 N-D Manifold Compressor / Topological Coordinate Descent | **C/B-borderline** | The general idea (compress N-D to 1D via slicing) is in the dimensionality-reduction literature; the specific WALL_ENTANGLEMENT exit and library-sweep slicer are apparatus-design choices. | The integration with the rest of the pipeline. | as engineering ✓; as new science the borderline is unclear without the cold-LLM run. |
| F-CAP-FLASH-RC-01 (gemini-2.5-flash recovers RC time constant from transient-only grid in 1 iter) | **B** | The form `V_inf · (1 − exp(−t/τ)) + V_offset` is textbook circuit theory. The capability claim is narrow and explicitly called out as "incidental observation, narrow scope, flash-only." | The blinded grid and fit-collapse instrumentation. | as a narrow capability datapoint ✓. |
| sopfr / A001414 ("Multiplicative-to-Additive Homomorphism with Empirical Base Identity") under cage with named_import_check (cognitive_gym Forced Abduction section, exp-math letter §2.7 / "Two Ceilings") | **C** | The forced articulation under hard-zero score gate is apparatus-original. The cold LLM given (n, sopfr(n)) pairs would simply call `factorint` and produce `sum(p*v for p,v in factorint(n).items())`; that is the *recital* path. The Bucket C content is the *Space ceiling* finding: even with the primitive available, the LLM categorically fails to switch from continuous-function-space to prime-space without prompting. | The denylist + named_import_check gate; the Space-ceiling diagnosis. | ✓ Bucket C, methodology paper material (the "Two Ceilings" section of the experimental math letter is the apparatus-original framing). |
| F-GP145-01, F-GP150-RUN-01 (impossibility-thesis substrates rate-limited by tail_generalization meta-critique) | **C** | Empirical observation across multiple substrates of a convergent failure pattern. Not retrievable. | The substrates, the apparatus, the cross-run analysis. | ✓ Bucket C. |
| 11 substrates, zero false positives (cognitive_gym row count + exp-math letter §2.8) | **B** | "Zero false positives" on a hand-curated 11-substrate benchmark designed by the operator who knows the answers. The selection conditioning matters. The PySR comparison (exp-math letter §2.9) provides a real cross-algorithm baseline and is more compelling: under the same holdout gates, PySR also declares null on Mertens, prime gaps, abundant density, and matches ZTARE's coefficient on Lucky to within noise. | Holdout gates as the decisive apparatus piece, demonstrated to be algorithm-interchangeable. | ✓ in the *PySR-baseline framing* (the gate is the mechanism, the search is interchangeable). The "zero false positives" framing alone is over-claimed for an N=11 designed benchmark. |

**Total rows audited:** ~32 distinct findings (de-duplicated across surfaces). Several E-rows in the track record that are infrastructure-only (apparatus bug fixes, primitive shipments) are not graded — they are engineering, not findings.

---

## Bucket-by-bucket analysis

### Bucket A — Pure recital (cold LLM gets it in one shot, apparatus rigor adds nothing the LLM couldn't do alone in 5 minutes)

Strictly, **no finding is pure-pure Bucket A** in the corpus. Even
the partition-family recoveries get a cold-variable cage and a
parsimony compressor that strips overparameterization — neither of
which a one-shot cold LLM call would produce. The closest entries
to A are:

- **KWW polymer** — the form `exp(−(t/τ)^β)` is so foundational that
  any LLM emits it given decay data. The score-98 ceiling discipline
  is apparatus-original framing, but the *answer* is recital.
- **F-CAP-FLASH-RC-01** (RC step response) — textbook circuit
  theory. Narrow scope is acknowledged in the finding row.

**Honest count: ~5–10% of substrate findings are A-leaning.**

### Bucket B — Recital + rigor (answer in literature, but apparatus adds decisive reproducibility)

This is the dominant bucket on the science track. The pattern:

1. **GP-088 / A000041 (Hardy–Ramanujan).** Cold LLM proposes
   sqrt+log topology ~50–87% of the time per the apparatus's own
   composition-log statistics. The apparatus contributes:
   parsimony compression (forces k=3 from k=6–7 LLM proposals),
   cold variable names, deterministic holdout gate, and rival
   exclusion at 100–3900× margin.
2. **A000009, A001156, A002865** — same pattern as above.
   Different leading coefficients, same Hardy–Ramanujan family
   structure.
3. **A000607** — borderline B/C. The compositional-template
   activation (Stage 2) is the apparatus contribution; the answer
   (Vaughan-style sqrt(n/log n)) is published.
4. **KWW** — recital with disciplined ceiling.
5. **sandbox_20 polymer** — published rheology family
   (Kapnistos 2008), apparatus contribution is the cold-variable
   cage and external practitioner validation.
6. **sandbox_06 Planck recovery** — recital of a textbook form
   under sealed gates; the apparatus claim (forced vocabulary
   escape under cage pressure) is itself Bucket C, but the
   *answer* (Planck/Bose–Einstein) is Bucket A.
7. **F-CAP-FLASH-RC-01** — narrow capability datapoint.

**The rigor is real:**

- Cold variable names (no `n`-as-partition-index, no `t`-as-time, no
  `phi`-as-photon-momentum). The contamination gate documented in
  cognitive_gym is the apparatus-side enforcement.
- Sealed evidence/holdout/farther-tail splits with hashes.
- Deterministic holdout gates with pass/fail thresholds set
  pre-iteration.
- Parsimony compression that strips 6–7 param LLM proposals to
  k=3 minimal forms (the experimental math letter §2.1 explicitly
  attributes this to the compression phase, not to the LLM).
- Cross-family pairing (gp159).
- Rival exclusion at quantified margins.
- PySR comparison (exp-math letter §2.9) is a real adversarial
  baseline.

**Honest count: ~55–60% of substrate findings are B.** Most of the
public Engine Track Record is B. This is OK — recovery under
discipline is a real contribution — but it is not discovery.

### Bucket C — Apparatus-only (a cold LLM cannot produce these)

The genuinely apparatus-original findings are:

**Substrate-level Bucket C:**

1. **Lucky number A000959 validity-horizon and (log n)² correction.**
   The 2% drift over a decade, the loglog-detection-by-margin-gate, the
   automated grammar extension to include `c/(n+d)` shifted reciprocal,
   and the effective-coefficient extrapolation toward Hawkins limit
   1.0 at n~10^17 — none of these are in literature. The apparatus's
   own bibliography survey (paper §2.1) confirms no published sub-leading
   correction topology for Lucky-number counting.
2. **Ulam reciprocal-rotation Steinerberger match (13.50 vs 13.52).**
   The number itself is in literature; the *automated rotation
   discovery* and the 0.07% agreement at n=770K is apparatus-original.
3. **Lucky/Ulam detrending sensitivity table (slope range 1.7).** The
   methodological finding that spectral slopes are
   detrending-method-dependent is apparatus-original.
4. **DFDO topology-induction-gap diagnosis** (engine explores A and
   B in isolation, never tries A+B even when both individually fail).
5. **gp154 K≤7 form-class-robust bounded null** — but downgraded to
   exploratory by the v4 charter's own panel-detected leakage.

**Methodological Bucket C (the strongest):**

6. **gp159 cross-family matched pair (93/90).** Two LLM families
   agree within 3 points on a non-standard-constant synthetic
   substrate. By construction, no cold LLM produces this.
7. **Grammar-ceiling chain crucial_01 → 02 → 02_extended → 03**
   (H-COMPUTE-01 + H-GRAMMAR-01). The controlled experiment proves
   "compute does not break grammar ceiling; one new primitive
   does." This is apparatus-on-itself science.
8. **Forced abduction on sopfr** — under hard-zero name denylist,
   the engine articulated "Multiplicative-to-Additive Homomorphism
   with Empirical Base Identity" rather than retrieve `factorint`.
   The forcing is the finding.
9. **Two-ceilings framing (Grammar + Space).** The apparatus-derived
   distinction between "the grammar can express the form but the
   LLM does not category-switch into prime-space" is
   apparatus-original.

**Paper-level Bucket C:**

10. **Paper 1 gaming taxonomy (9 strategies, 453 debate logs, 3
    mutator families).**
11. **Paper 2 evaluator-hardening benchmark** with primitive-ordering
    ablations.
12. **Paper 3 meta-runner architecture** with one blocked sloppy
    promotion documented.
13. **Paper 4 M-form governance** with two unauthorized-write
    incidents, 24 governed self-improvements, fractal-Goodhart at
    5+ layers.
14. **Paper 5 ten-operation decomposition** (scoped as abductively
    proposed, awaiting holdout).
15. **Paper 6 BOS-contamination artifact + cancellation invariance
    + alignment-learning split** across 7 model families.

**Mining-level Bucket C:**

16. **GP-148/149 mining results** — pivot-effectiveness by failure
    class, persistence-and-cycling champion profile,
    tail_generalization as convergent blindspot, Lollapalooza
    refuted.
17. **GP-103 topology-induction gap.**
18. **GP-073/074 Component-B-as-pruner-not-injector;
    Component-C-residual-fingerprinting architectural gap.**
19. **GP-085 grammar-ceiling hypothesis** confirmed both legs
    (compute does not break, one primitive does).
20. **GP-125 Riemann bimodal phase transition in operator
    space** (informative null).

**Honest count: ~25–30% of findings are genuinely Bucket C.**

### Bucket D — Indeterminate (would need a cold-LLM run to settle)

- **Whether the cold LLM produces the *exact* leading coefficient
  to the same precision as the apparatus on the partition family.**
  My prediction: it gets the topology and a reasonable coefficient
  but not the apparatus's compressed form's parsimony. Without
  running it, I cannot rule out the LLM matching coefficient
  precision.
- **Whether the cold LLM proposes the reciprocal rotation
  spontaneously on Ulam.** My prediction: no, but unproven.
- **Whether GPT-4 / Claude / Gemini differ in their cold-LLM null
  emissions on these substrates.** Important for any "X% of
  Bucket B" claim.
- **Whether the tail-generalization meta-critique is a property of
  o3-as-judge or of any judge.** GP-148 found it cross-judge but
  the sample is small.

---

## Implications for paper claims

### Paper 1 — Cognitive Camouflage

**Survives:** the gaming taxonomy (Bucket C). The cross-mutator
matrix (Gemini converges, Claude converges with Suite Omission,
GPT-4o oscillates) is empirical apparatus-on-system data. The judge
baselines (Gemini fooled 4/5, Claude 0/5; Firing Squad caught all)
are apparatus-original.

**Does not need any walking back.** The paper's contribution is the
taxonomy and the detection-gap result. Both are clean Bucket C.

### Paper 2 — Adversarial Precedent Memory

**Survives:** the four claims, all scoped to one system, one
benchmark. Bucket C.

**Does not need walking back.** The paper itself caveats the OOD
generalization claim explicitly.

### Paper 3 — Contract-Governed Hardening

**Survives:** the meta-runner architecture and the 6-stage history
with one blocked sloppy promotion. Bucket C.

**Does not need walking back.** Single-system N=1 is stated upfront.

### Paper 4 — Cognitive Firm

**Survives:** M-form architecture, write-scope-guard evidence, two
unauthorized-write incidents, 24 governed self-improvements,
fractal-Goodhart at 5+ layers. All Bucket C.

**Does not need walking back.** The paper explicitly disclaims
multi-principal governance and concurrent-program-oversight.

### Paper 5 — Principles of Epistemic Verification

**Survives:** the 10-operation decomposition **as an abductive
proposal from one corpus**, awaiting holdout replication. The paper
itself flags this in Front Matter §4.

**Watch the framing:** any external presentation must reproduce the
abductive caveat. The 10 operations are not yet established science;
they are a hypothesis. The repo's existing scoping is correct.

### Paper 6 — Neural Scaling

**Survives:** BOS-contamination artifact (clean Bucket C, replicable),
cancellation invariance (Bucket C with the trained-vs-untrained null
test), cross-architecture orthogonality (Bucket C), U-shaped ablation
curve (Bucket C). The "training teaches coordination not alignment"
framing is apparatus-original.

**Does not need walking back.** The paper itself disclaims the YES/NO
alignment-learning causal variable as unknown.

### Experimental Math Letter (submitted to Experimental Mathematics)

**Survives at the right scope:**
- §2.1 Lucky number: **the Bucket C content** (validity horizon,
  (log n)² correction, b_eff → Hawkins) is the strongest result.
  Should be the headline.
- §2.2 / §2.3 / §2.4 / §2.5 partition-family recoveries:
  **Bucket B**, should be presented as **calibration of the
  instrument**, not as discoveries.
- §2.6 prime partitions: **Bucket B with apparatus-original
  Stage-1→Stage-2 compositional-template activation**. The
  methodological note is publishable.
- §2.7 Ulam reciprocal-rotation: **Bucket C** (the rotation move),
  Bucket B (the Steinerberger constant value).
- §2.8 11-substrate / zero-false-positive: framing is over-claimed
  for N=11 designed benchmark. **The PySR comparison §2.9 is the
  decisive rigor evidence**, not the substrate count.
- §2.9 PySR baseline: **Bucket C as a methodology contribution**
  (the gate is the mechanism, the search is interchangeable).
- §2.10 two-ceilings (sopfr Space ceiling): **Bucket C**, the
  category-switch-as-orthogonal-bound is apparatus-original.

**Recommended reframe before submission revision:** lead with the
two ceilings, the validity-horizon, and the PySR comparison.
Move partition-family recoveries to a "calibration" subsection.
Drop or temper the "zero false positives" framing in favor of
the PySR-cross-algorithm comparison.

### README "Engine Track Record"

**Survives at the right scope:**
- "Recoveries on dark domains" table: **Bucket B**. The
  partition family is recovery-under-discipline, not discovery
  on dark domains. The phrase "dark domain" is over-claimed for
  Hardy–Ramanujan-family substrates that are textbook.
  Suggested edit: rename the section to **"Recovery under cage
  pressure"** or **"Calibration substrates."**
- External validation (sandbox_20 polymer): **Bucket B but
  external-validated**. Keep, but mark as published-form +
  external-validated.
- Correct refusals (Ulam, DFDO, Lucky validity-horizon):
  **Bucket C, the strongest part of the table.** Keep as-is.
- Apparatus-reproducibility (gp159 matched pair): **Bucket C,
  the headline of the apparatus-reproducibility framing.** Keep.
- Bounded null (gp154): **Bucket C with the panel-detected
  leakage caveat.** The current README phrasing ("statistically
  indistinguishable from the constant predictor") is technically
  accurate but presents the v3 result without the v4 charter's
  own downgrade to exploratory. Should be tempered to match
  the v4 charter scoping.

---

## What this audit DOES NOT cover

1. **No cold-LLM call was actually run** during this audit. All
   "cold LLM would emit X" predictions are based on training-data
   priors (Hardy–Ramanujan in textbooks, KWW textbook, Steinerberger
   2017, Hawkins 1957, etc.). The Bucket A vs B boundary on the
   partition family in particular would be tightened by an actual
   cold-LLM call against the same evidence files. **Recommended
   future work: run gpt-5 / opus-4 / gemini-2.5-pro one-shot on the
   five partition-family `evidence.txt` files with cold variable
   names and compare to the apparatus's compressed champion.**
2. **No assessment of the supervisor / cognitive-firm operational
   evidence beyond what is documented in Paper 4.** The
   24-governed-self-improvements claim is stated; I did not verify
   each of 24 by reading every supervisor log.
3. **No assessment of the gaming-taxonomy code-level evidence.**
   Paper 1 cites debate-log line numbers; I did not pull each one.
4. **No recursive meta-audit** on whether *this audit* itself
   exhibits any of the 11 overreach patterns from the automated
   skeptic persona memory file.
5. **No handling of the Hardening Board** items that have not yet
   produced findings.
6. **No commentary on the engineering quality of the apparatus
   itself** (the 24 bugs in the GP-156 session, the rubric defects,
   etc.) — these are real but they are not "findings" in the
   science sense.
7. **No quantitative effect-size analysis** comparing the
   distribution of mutator-proposed forms with vs without the
   contamination gate, which would be the cleanest evidence for the
   apparatus contribution on Bucket B substrates.

---

## Top recommendations

1. **Reframe the partition-family substrates as calibration, not
   discovery.** The current README, the experimental-math letter,
   and the cognitive_gym Part 5 table all present GP-088 / A000009
   / A000607 / A001156 / A002865 as "recoveries on dark domains."
   They are not dark; they are textbook. Renaming the section to
   "Calibration substrates" (or "Recovery under cage pressure") and
   moving these *below* the Lucky-number / Ulam / cross-family /
   bounded-null findings in any external presentation will make the
   apparatus-original content visible. **The apparatus is real but
   the public surface currently buries its strongest evidence
   under its weakest.**

2. **Make the gp159 cross-family matched pair the headline of any
   "the apparatus is reproducible" claim.** It is the only finding
   in the repo where two independent LLM families converge to
   within-noise scores on the same non-standard-constant substrate.
   Without the apparatus, the same two models do not converge to
   similar answers. This is the cleanest single piece of evidence
   for the apparatus contribution and it is currently buried in
   the README under "Apparatus-reproducibility evidence."

3. **Run an actual cold-LLM null test on three substrates before
   the experimental-math letter revision.** Specifically: cold
   gpt-5 / opus / gemini-pro one-shot on (a) GP-088 partition
   evidence, (b) A000959 Lucky-number evidence at 50K, (c)
   A002858 Ulam evidence. Time-box: 1 hour, 9 calls total. This
   tightens the Bucket A vs B boundary on the partition family
   from "predicted recital" to "demonstrated recital." It also
   directly tests the Lucky-number Bucket C claim by giving the
   cold LLM the same 50K data and seeing if it emits the
   (log n)² correction or stops at simple `a·log(n) + b/n + c`
   (the apparatus's own iter-1 form before the margin-of-safety
   loop). My prediction: the cold LLM stops at simple log; the
   apparatus's recursive margin-of-safety loop is the
   decisive piece.

4. **Temper the gp154 bounded-null framing to match the v4
   charter's panel-corrected scope.** The README currently
   presents the K≤7 wall as "form-class robust." The v4 charter
   itself flags that the diagnostic priors were derived from
   the same dataset the holdout draws from, so the result is
   exploratory not confirmatory under Nature MI panel review.
   The README should match. Suggested README edit: replace
   "form-class robust" with "form-class robust on the available
   holdout, pending external sealed holdout validation per
   panel-prescribed work item T14."

5. **Consider splitting the experimental-math letter into two
   submissions.** (a) A short methodology letter focused on the
   apparatus-original Bucket C content: validity horizons (Lucky),
   observable rotation (Ulam), grammar-ceiling chain
   (crucial_01..03), two-ceilings (sopfr Space ceiling), PySR
   gate-not-search comparison. (b) A separate, more conservative
   submission on the partition-family recoveries framed as
   *calibration of cold-variable cages with deterministic holdout
   gates*, which is a real methodology paper but does not need to
   coexist with the apparatus-original content. Mixing them
   currently causes the partition recoveries to look more
   discovery-like than they are and the apparatus-original content
   to look more incremental than it is.

---

**Final note to the operator:** the apparatus is real. The ~25–30%
Bucket C content is genuinely original and not retrievable from a
cold LLM. The gaming taxonomy (Paper 1), the M-form governance
evidence (Paper 4), the BOS / cancellation / alignment-learning
findings (Paper 6), the Lucky validity-horizon and (log n)²
correction, the cross-family matched pair, and the grammar-ceiling
chain are the pieces that survive the cold-LLM null cleanly. The
partition-family recoveries are recovery-under-discipline, which is
a real contribution but is not discovery and should not be presented
as such. The pace anxiety in the memory file is real but the
positioning fix is to *highlight what the apparatus actually does*
(forced parsimony, validity horizons, cross-family stability, refusal
discipline) rather than to add more substrates to the recovery count.
