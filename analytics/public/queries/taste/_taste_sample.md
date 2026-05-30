# Taste Sample — Blind Rating Sheet

This batch has **14 samples** to rate. (62 additional samples were skipped because they're already in the taste_ledger from previous runs.)

Each sample below has a unique `SAMPLE_NNN` ID. Read each sample and rate it 0-5 on **insight density**:

  - **0** = boilerplate, scaffolding, or restated apparatus state
  - **1** = trivially observable; doesn't change downstream reasoning
  - **2** = useful but expected; consolidates known
  - **3** = non-obvious finding or sharp framing; would help a future reader
  - **4** = surprising / load-bearing / mechanism-revealing
  - **5** = paradigm-shifting; reframes the problem or apparatus

Output format:
```
SAMPLE_001 | score | one-line rationale
SAMPLE_002 | score | one-line rationale
...
```

**Bias warning to rater:** if you've worked on this codebase recently, you'll be tempted to score familiar / recent / self-authored content higher. Try to score on the artifact text alone, not on what you remember about it.

---

## SAMPLE_001 (project_workspace_md)

```
# Phase 5DS Candidate Cascade Intake Audit

Bounded exact-Fourier intake harness for independent cascade proposals. This
is not a search over phases or amplitudes: the candidate must be declared
first, then scored.

## Harness

- Script: `projects/ns_millennium_hunt/workspace/phase5ds_candidate_cascade_audit.py`
- Canonical packet: `W=(sin y, -sin x, 0)`
- Checks: realness, divergence-free defect, self projected residual,
  pressure-source norm, mixed projected residual against `W`, multiplier
  profit against `W`, and candidate self-profit
  `<u_B, P((u_B dot grad) W)>`.

## Iter 1 Generator Backtest

Generator declared by `ns_proofsearch_independent_multishell_cascade` iter 1:

- `k_m=(m,m,1)`, `1<=m<=B`
- `e_m=(1,-1,0)/sqrt(2)`
- `A_m=m^(-5/3)`
- `phi_m=(-1)^m*pi/4`
- real field formed by adding the complex conjugate modes.

Direct audit result:

| B | real defect | div defect | self residual | pressure source | mixed residual | candidate profit | packet profit ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 | 0 | 0 | 0 | 0 | 1.539676408 | 0 | 0 |
| 6 | 0 | 0 | 0 | 0 | 1.876990061 | 0 | 0 |
| 10 | 0 | 0 | 0 | 0 | 1.998372819 | 0 | 0 |
| 20 | 0 | 0 | 0 | 0 | 2.130600982 | 0 | 0 |
| 50 | 0 | 0 | 0 | 0 | 2.260108660 | 0 | 0 |
| 100 | 0 | 0 | 0 | 0 | 2.332550003 | 0 | 0 |

## Read

The iter 1 thesis satisfied the anti-tautology bar by declaring a generator,
but its claimed 
```

## SAMPLE_009 (project_workspace_md)

```
# H136 GPU Burst Synthesis and Architecture Status

Recorded: `2026-05-12`

GPU host: `129.146.108.52` (`A100-SXM4-40GB`)

Artifact directory:
`projects/neural_hunt/workspace/h121_remote_a100_2026_05_12/`

## Verdict

`gpu_burst_complete_no_more_gpu_needed_for_current_packet`

The corrected replay supports conditional residual write gating as a serious
architecture candidate, but it does not justify claiming a new Transformer
architecture yet. The evidence says the middle of the stack is not uniformly
dead. Some middle writes are harmful on local continuation / H75-like packets,
but those same write paths are needed on ICL, BoolQ, and other global-context
or format-sensitive tasks.

## What Changed

1. Corrected replay preserves the nonuniform-layer result.
   H115/H116 reproduce the pattern that layer `8` and parts of `8-10` can
   improve correct-continuation logprob when suppressed, while full middle-span
   deletion is damaging. The target is read/write asymmetry, not pruning.

2. Real-task validation blocks the naive architecture claim.
   H117/H124/H125/H128/H131 show that layer `8` suppression is often the least
   dangerous or modestly beneficial perturbation, but full `8-10` suppression
   hurts aggregate mixed real-task accuracy. Gentle throttling can preserve
   accuracy in some cells; blunt bypass cannot.

3. Distribution split is the main scientific result of the G
```

## SAMPLE_025 (project_workspace_md)

```
# Adversarial Debate: x_algo_goodhart_audit
<!-- rubric: x_algo_goodhart_audit | mutator: gpt4.1-mini | judge: gpt-4.1-mini -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: Negative candidate score: -2.6666666666666665
Zero candidate score: 10.0
Positive candidate score: 11.0


# Final Score: 85
**Weakest Point:** The critique's dependency on the unknown exact magnitudes of NEGATIVE_SCORES_OFFSET and the tuned real-time weights limits its quantification of impact severity, though the structural mechanism itself is firmly code-anchored.
**Rationale:** The critique's core claim is that the linear combination scoring with an asymmetric offset_score() normalization structurally biases against candidates with net negative predicted engagement factors due to the offset pulling negative combined scores further down—thereby disproportionately suppressing content with even moderate negative signals despite some positive actions. This is precisely anchored on ranking_scorer.rs's offset_score function and the delineation of positive_sum and negative_sum components. The critique identifies a vivid harm: the system overweightedly penalizes any candidate with negative calls, reducing diversity and reinforcing bubble effects by aggressively filtering or downranking borderline negatives. The dominant engineer rebuttal would be that Phoenix's t
```

## SAMPLE_027 (project_workspace_md)

```
# H158 Strict Holdout All-Layer Gentle Probe Plan

Recorded: `2026-05-12`

Status: `pre_registered / gpu_if_hot`

## Eigenquestion

Did H147 fail because the selected middle spans were wrong, or because simple
residual alpha-throttling has no state-preserving utility frontier on the
strict holdout?

## Rationale

H147/H156 close the H138 write-width rule on strict holdout:

- H140 fails with false allows.
- Corrected H156 finds no family/:mc state-preserving utility frontier.
- Aggressive broad-span throttles damage utility and drift.
- Gentle selected spans preserve state but have near-zero or negative utility.

The remaining cheap discriminator is an all-single-layer gentle map. It avoids
broad span deletion and asks whether any individual layer has a positive,
state-preserving frontier under the same strict packet.

## Command

Run on the already-bootstrapped GPU host:

```bash
./venv/bin/python projects/neural_hunt/workspace/run_h110_span_functional_probe.py \
  --packet projects/neural_hunt/workspace/h147_strict_write_width_holdout_packet_2026_05_12.jsonl \
  --steps 1600000,1800000 \
  --spans 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 \
  --alphas 0.75,0.9 \
  --docs-per-cell 12 \
  --device cuda \
  --trust-remote-code \
  --output-stem h158_strict_holdout_all_layer_gentle_probe_2026_05_12
```

## Success Criterion

H158 is positive only if corrected pair preservation finds 
```

## SAMPLE_045 (project_workspace_md)

```
# Adversarial Debate: x_algo_goodhart_audit
<!-- rubric: x_algo_goodhart_audit | mutator: gpt5.5 | judge: claude-sonnet-4-6 -->


## Level 3 Unit Test Results
✅ PASS: The thesis survived its own falsification suite.
Output: 

# Final Score: 62
**Weakest Point:** The thesis's central architectural claim — 'exposed ranking path is structurally blind' — performs an illicit inference from documentary absence to structural necessity. The verification panel's critique is correct and devastating: the logical form requires P2 (exposed code = production system) which is never established, only assumed by scope definition. The thesis acknowledges this in its own limitation list ('does not prove that production lacks undisclosed pre-delivery gates') but then continues to use 'structurally blind' as if the scope condition resolves into an architectural fact. This is the single most catastrophic load-bearing failure. A correctly scoped version would state 'the exposed code surface contains no pre-top-K independent quality channel; if this surface is representative of production, the ranking path is structurally blind' — but even that weaker form is not what the thesis delivers in its conclusion nodes. Additionally, Rival 6 ('Phoenix predictions are a sufficient statistic for healthy/relevant quality') is marked 'empirically unresolved' rather than falsified, which means the thesis cannot cl
```

## SAMPLE_047 (project_workspace_md)

```
# Eigenquestion: Asymptotic Super-Type-I Sparse Cascade — the real residual, two isolated gaps

**Date:** 2026-05-15
**Target model:** GPT-5.5 Pro
**Style requested:** Gowers-style theorem-surface audit. Verify/close the two isolated gaps, or give a countermodel. Do not re-derive the proved scaffolding. Do not return a polished essay.

## Why this eigenquestion exists (meta: is this the *right* eigenq?)

Your prior response closed the **literal** `SuperTypeIIntermittentCommutatorCascade` by a pure measure-theoretic contradiction — but **vacuously**: the `∀ θ η > 0` clause + CKN cube-mass floor is self-inconsistent, so the structure was empty. We independently caught the same vacuity in self-audit and already corrected the Lean encoding *before* your response (`ns_tick538` scale-indexed fix; `ns_tick541` `literal_cascade_false` proved).

You explicitly flagged the genuine residual (your §8, §9 caveat, P5):

> *"That weaker [asymptotic] version is not killed by the above proof... would require a new theorem."*

So we **know** the real eigenq. The meta-criterion for "this is the right eigenq" is encoded as a test below (M1–M3) so you can confirm we have correctly identified it and not produced another vacuous or laundered target. Then the substantive question is the two isolated gaps **G1, G2**.

## Proved scaffolding (DONE — do not re-derive)

| Result | Status | File |
|---|---|
```

## SAMPLE_050 (project_workspace_md)

```
# H99 H73 8-Step Residual Cell Feature Analysis

Recorded: `2026-05-11`

Verdict: `mechanics_signal_with_packet_diversity_caveat`

## Packet Diversity

- cells: `48`
- rows per cell: `[12]`
- unique docs per cell: `[3]`

## Strongest Schema Deltas

| step | family | abs PC2 residual | top feature | abs delta | eff-rank delta | cosine delta | cancellation delta |
|---:|---|---:|---|---:|---:|---:|---:|
| 400000 | `mmlu_professional_medicine` | 0.3891 | `residual_effective_rank_mean` | 0.6619 | -0.6619 | -0.0377 | -0.0148 |
| 800000 | `mmlu_professional_medicine` | 0.0046 | `residual_effective_rank_mean` | 0.6583 | -0.6583 | -0.0299 | -0.0180 |
| 200000 | `mmlu_professional_medicine` | 0.2695 | `residual_effective_rank_mean` | 0.6582 | -0.6582 | -0.0452 | -0.0018 |
| 1200000 | `mmlu_professional_medicine` | 0.1831 | `residual_effective_rank_mean` | 0.6544 | -0.6544 | -0.0205 | -0.0172 |
| 100000 | `mmlu_professional_medicine` | 0.3736 | `residual_effective_rank_mean` | 0.6519 | -0.6519 | -0.0611 | 0.0280 |
| 10000 | `mmlu_professional_medicine` | 0.9218 | `residual_effective_rank_mean` | 0.6514 | -0.6514 | -0.0963 | 0.0691 |
| 50000 | `mmlu_professional_medicine` | 0.3250 | `residual_effective_rank_mean` | 0.6464 | -0.6464 | -0.0838 | 0.0801 |
| 0 | `mmlu_professional_medicine` | 1.2780 | `residual_effective_rank_mean` | 0.6095 | -0.6095 | 0.0006 | -0.0007 |
| 10000 | `medmcqa` |
```

## SAMPLE_051 (concept_doc)

```
# Agentic Engineering Patterns

**Status:** public, stand-alone. No ZTARE prerequisites.
**Audience:** anyone building LLM-mediated pipelines (research apparatus, agent frameworks, RAG systems, multi-stage agentic workflows).
**Sister docs:** `docs/concepts/reflexive_engineering.md` (the meta-move applied to ZTARE specifically), `docs/guides/reflexive_audit_workflow.md` (workflow for discovering primitives).

---

## What this is

A pattern catalogue for engineering pipelines whose internals are LLM calls. Most software-testing literature assumes deterministic functions; LLM pipelines are non-deterministic at the call layer but deterministic at the orchestration layer. The patterns here target the orchestration layer — the dispatch logic, contract enforcement, candidate selection, telemetry — and treat the LLM calls themselves as oracles to be stubbed during integration testing.

Each pattern was discovered the same way: a specific bug shipped to production (or got close), an examination of why standard testing missed it, and a small reusable technique emerged that closes that class. The patterns are independent — adopt them à la carte.

---

## Pattern catalogue

### Pattern 1 — Stub-Replay Integration Testing

**Problem.** LLM pipelines pass non-deterministic generations through deterministic dispatch logic. Standard unit tests stub out the LLM call entirely, which means the 
```

## SAMPLE_052 (project_workspace_md)

```
# Phase 5n Stall-Law Audit

Verdict: `distributed_stall_law_supported`

The weak positive production surplus survives segmentation, but it does not belong to an identity-stable stretching winner. Across leader-identity, 99%-multiplicity, and chi-difference segmentations, the object behaves as distributed two-core churn: positive budget persists, leadership changes, and stretch-axis occupancy remains sparse.

## Candidate Law

The branch sustains weak net-positive local production by redistributing harvesting across competing identities and interaction states faster than it can consolidate that production into one persistent stretching-led, geometrically collapsing core.

## Overall

- leader chi budget: `{'net_integral': 0.009990646156675196, 'positive_integral': 0.022311798174850298, 'negative_integral': -0.012321152018175104, 'positive_to_negative_abs_ratio': 1.8108532499183398}`
- track A chi budget: `{'net_integral': 0.0046686506844822485, 'positive_integral': 0.026565092711673406, 'negative_integral': -0.02189644202719116, 'positive_to_negative_abs_ratio': 1.2132150364285066}`
- track B chi budget: `{'net_integral': 0.023349776025825646, 'positive_integral': 0.03004746274942199, 'negative_integral': -0.006697686723596344, 'positive_to_negative_abs_ratio': 4.48624487669198}`
- chi-diff budget (A-B): `{'net_integral': -0.018681125341343398, 'positive_integral': 0.02528834897
```

## SAMPLE_057 (project_workspace_md)

```
# Route-1 Active-Tail Singular Part Control

**Date:** 2026-05-14
**Track:** NS Hunt, route 1
**Status:** Lower lemma after active-carrier domination pull-forward

## Eigenquestion

Can the singular part of active route-source tail mass be controlled by the
profile/coherence residual visibility?

## Lemma

```text
ActiveTailSingularPartControlledByProfileResidual
```

Let the visible measure be:

```text
nu_vis = mu_T + mu_QP + mu_C
```

where:

- `mu_T` is same-cutoff positive transport visibility,
- `mu_QP` is pre-summed pressure/local-quadratic visibility,
- `mu_C` is positive commutator/Reynolds defect visibility.

For the active source-tail carrier `mu_A`, take the Lebesgue decomposition:

```text
mu_A = f dnu_vis + mu_A_perp
mu_A_perp singular to nu_vis
```

The missing theorem is:

```text
mu_A_perp(E) <= C * mu_I(E)
```

on each fixed event tent atom `E`, where `mu_I` is an independently defined
profile/coherence residual measure.

## Consequence

If the singular control theorem holds and the visible-density bound holds, then:

```text
mu_A(E) <= C' * (mu_T + mu_QP + mu_C + mu_I)(E)
```

This proves `ActiveTailCarrierVisibilityDomination`, which feeds
`NoNonzeroZeroVisibilityActiveProfile`, which feeds the route-1 visibility
cover.

## If It Fails

If `mu_A_perp` is not controlled by `mu_I`, then the current four-channel
visibility cover is incomplete. The route needs a
```

## SAMPLE_060 (project_workspace_md)

```
# N8 Inversion Packet: Non-Route Branches After Route-1 Pincer

**Date:** 2026-05-14  
**Tick:** 409  
**Status:** top-down inversion packet

## Verdict

Route-1 schedule closure should be isolated. The remaining branches should not
be forced through route 1 unless a concrete reduction is proved.

The top-down obstruction is:

```text
CriticalIncrementFailure
  -> Route1Failure
   or finiteMassResidual
   or CKNRadiusFailure
   or PressureConeFailure
   or BetaIncidenceFailure
   or UnfreshTailFailure
   or RecurrentReuseFailure.
```

Route 1 only closes the first disjunct.

## N8a. CKN / Radius

The obstruction is the scaling gap:

```text
sum r_Q^2 <= C
```

does not imply

```text
sum r_Q < infinity.
```

Microscopic bad cylinders can have finite square-radius budget and divergent
radius budget. Route-1 local energy accounting does not close this by itself.

Admissible next moves:

- prove a separate radius-charge theorem;
- prove CKN/radius failure generates route-1 schedule mass;
- import a stronger non-energy quantity such as an endpoint `L^3_x` mechanism;
- keep `CKNRadiusFailure` as an open branch.

## N8b. Pressure / Cone

The obstruction is nonlocal pressure and sign-indefinite projected kernels.
Same-window sheath cancellation can make final carrier magnitude vanish while
pre-summed stress remains nonzero.

Admissible next moves:

- use pre-summed pressure/local-quad
```

## SAMPLE_064 (project_workspace_md)

```
# NS Track B Numeric Liminf Divide-and-Conquer Packet

Recorded: 2026-05-07

Updated: 2026-05-07 after lane review, zero-defect falsifier, and Lean
hardening.

## Current Target

The live residual is:

```lean
GP216SelectedProjectedNumericCompactnessLiminfSource
```

The residual-void audit counts one source atom:

```text
selected_projected_numeric_compactness_liminf_source
```

This is not one mathematical task.  It is a decomposable source certificate
whose fields can be attacked independently, then synthesized.

## Eigenquestion

Can the selected projected GP216 branch be given compactness/liminf provenance
from one fixed cofinal approximation family, with the generated liminf prices
identified with the relaxed prices consumed by the measure-valued source?

If yes, the selected compactness source already feeds the compiled downstream
route.  If no, the failure should identify which field is over-strong or
missing.

## Lanes

### Lane A: Selected Stream And Approximation Family

Fields:

```lean
approximation_family
approximation_index_to_prefix
approximation_family_declared_before_payoff
approximation_family_cofinal_in_selected_prefixes
selected_projected_stream_fixed_before_payoff
```

Task: define the branch-local approximation family for
`GP216ContinuumProjectedSelectedBranchStream H n source branch_is_global`.

Pass condition: the family is declared before payoff and co
```

## SAMPLE_071 (project_workspace_md)

```
# Phase 5BR 5BQ Failure-Mode Audit

- `classification`: `mixed_mes_plus_tube_recovery_gap`
- `rows`: `72`

## Reasons

- No row at any N had positive net budget.
- Every high-N reduced-block row that exists is positive definite.
- High-N block rows are missing at N=[96, 128]; this is an optimizer/tube-recovery gap, not a negative block certificate.
- Negative reduced-block rows occur at N=[24].

## Per-N Summary

- N `24`: blocks `4`, positive blocks `1`, negative blocks `3`, strict `1`, near `4`, positive-net `0`, q_min `0.0011973`, net_max `-0.068737`
  eig `[ -15.2886, 15.2251 ]`, schur `[ -18.6456, 22.7229 ]`
- N `32`: blocks `0`, positive blocks `0`, negative blocks `0`, strict `0`, near `0`, positive-net `0`, q_min `0.167257`, net_max `-0.0515151`
- N `48`: blocks `11`, positive blocks `11`, negative blocks `0`, strict `11`, near `11`, positive-net `0`, q_min `0.000194349`, net_max `-0.122334`
  eig `[ 115.057, 165.512 ]`, schur `[ 117.086, 191.248 ]`
- N `64`: blocks `3`, positive blocks `3`, negative blocks `0`, strict `1`, near `3`, positive-net `0`, q_min `0.00351507`, net_max `-0.0868772`
  eig `[ 224.659, 271.012 ]`, schur `[ 239.362, 343.806 ]`
- N `96`: blocks `0`, positive blocks `0`, negative blocks `0`, strict `0`, near `0`, positive-net `0`, q_min `0.0506927`, net_max `-0.0951106`
- N `128`: blocks `0`, positive blocks `0`, negative blocks `0`, strict `0`, nea
```

## SAMPLE_076 (project_workspace_md)

```
# Direct attack on axisymmetric-with-swirl Liouville (unconditional)

**Date**: 2026-05-07
**Author**: Claude Opus 4.7 (1M context)
**Target**: every bounded ancient mild axisymmetric (possibly nonzero swirl) 3D NS solution is constant
**Verdict**: **OPEN-WITH-NEW-OBSTRUCTION (depth-3, isomorphic to C1 Prodi-Serrin barrier on the polar slice)**

## 1. Literature scan (2024-2026)

- Lei-Zhang 2011 (J. Funct. Anal. 261:2323): bounded axisymmetric ancient + `‖Γ‖_∞ ≤ K` + axis-decay ⇒ trivial.
- Lei-Zhang 2017 (Comm. PDE): axisymmetric small-swirl in critical norms; forward Cauchy.
- Pan-Zhang addendum to Tsai survey (arXiv 2101.04905, refreshed 2024): explicitly lists *unconditional* swirl Liouville as open; emphasizes that the conjecture is "beyond reach if no extra assumption is given."
- Chen-Hou 2022 / Hou 2025 PNAS: axisymmetric **Euler** boundary blow-up; the NS analog under viscosity without boundary is exactly the bounded-ancient class we attack.
- arXiv 2507.14964 (2025): Prodi-Serrin-type criterion on `u^θ` in `L_∞(0,T;L_p)` with `3/p < 1` (cylinder, IBVP) — **angular component**, not Γ. Confirms current frontier still bolts criteria onto `u^θ`.
- 2024 small-swirl critical-space results (Solving axisym-NS in critical spaces I, JDE 2022; follow-ups 2024) — all forward Cauchy with smallness, none unconditional Liouville.

No 2024-2026 paper closes unconditional axisymmetri
```

