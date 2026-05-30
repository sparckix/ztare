# GP-245 Forecaster Skill Calibration — Public Claim Summary

> Public-evidence surface for the GP-245 Forecast Calibration Program
> (a forecaster-skill / multi-channel calibration subsystem of the
> ZTARE repo). Working directory private; cited by
> `docs/public_claim_register.md` under *GP-245 Forecast Calibration
> Program*. Last updated 2026-05-29 with F100–F104.

## Claim

Across 104 documented F-findings (F1–F104) on subscription-class LLM
forecasting with a 5-family panel (claude-opus-4.7, codex-gpt-5.5,
codex-gpt-5.4-mini, deepseek-chat, gemini-2.5-flash), the program
contributes a small set of specific instruments and operationalizations
and, in the latest stretch, a pre-registered inductive theory of LLM
bias inheritance that survives its own confirmatory smoke at the 8/10
bar. The full program shape:

1. **Tail-insurance-premium as a separately-elicited second-moment
   channel** that predicts per-row Brier across four pilots
   (F8/F10/F20/F32; pooled ρ ranges +0.32 to +0.47; F32 is the first
   pilot where all three agents agree in direction).
2. **LLM herding under exposure is robust to behavioral remediation**:
   slope(shift | prior_gap) ≈ +0.75 with or without a "be skeptical"
   instruction (F15 baseline + F33 negative; pooled N=240 + N=239).
   Combined with F19/F22 (rationale-exchange null), this establishes
   that independence must be enforced architecturally — no light-touch
   behavioral patch substitutes.
3. **Premium-as-abstention** rescues the negative threshold-shift
   wiring (F25 → F28, +22 utility lift on symmetric-loss regime).
4. **Closed-loop super-judge** re-decision on worried cases improves
   Brier dramatically without humans in the loop (F30, Brier 0.21 vs
   original 0.35; regime-dependent utility).
5. **Failure-mode atlas** with six honest negatives bounded by
   structural conditions (F12, F19/F22, F24, F33, and F14/F23 as
   diagnostic + reconciliation), drafted at
   `papers/failure_mode_atlas/paper_draft_v1.md`.
6. **Composed-routing recipe deployed at N=142** (F97/F99/F100).
   `confident_no_discount` (a single per-family shrinkage rule for
   `p_raw < 0.10`) improves Brier at p<0.05 on every panel member
   (claude Δ=−0.030 p=0.016, deepseek Δ=−0.052 **p=0.0008**, etc.) and
   is wired into `org/calibration/per_agent_prompt_policy.yaml`.
7. **Re-audit discipline** (F101): the Halawi 2024 forecasting
   dataset is structurally contaminated for the 2025+ LLM generation
   (resolve-year histogram has 0 entries past 2024; every panel
   knowledge cutoff postdates every resolution). A 30-call probe
   returned raw Brier 0.13 with perfect bin-calibration at p<0.10 —
   the memorization signature. The published filter
   `resolve_date > max(panel_cutoff)` empties the dataset for the
   current generation. Written into the working paper.
8. **Frequency-Inheritance Hypothesis with 3-axis taxonomy** (F104).
   Inducted from F100–F102: LLM bias inheritance partitions by
   (i) elicitation surface, (ii) bias-mechanism class (utility-grounded
   vs frequency-encoded vs systemic-motivational), (iii) alignment
   overlay — yielding ESCAPE / INHERIT / MIMIC cells. Pre-classified
   10 well-studied biases into the 3 cells; claude-subscription n=15
   confirmatory scored **8 of 10 correct** at the pre-registered ≥8/10
   bar (random-cell baseline 3.3/10). Confirmed: A/B/G ESCAPE,
   C/E/H/J INHERIT, F MIMIC. Two informative misses both predicted
   MIMIC: D sunk-cost and I in-group, both fully suppressed on
   subscription-RLHF claude, refining the MIMIC predicate to
   "systemic motivational + heavy case-study representation +
   survives alignment damping." Cross-panel confirmatory on codex /
   deepseek / gemini fired 2026-05-29 to distinguish "alignment damping"
   from "framework wrong"; result pending.
9. **F102 cross-corpus replication on diversified n=42 Metaculus+FRED**
   (landed 2026-05-29). Same A/F slate, 1050 calls, 1039 schema_ok.
   Loss-frame ESCAPE replicates across all five families (mean gap
   0.061–0.124, all below the 0.15 human floor). Status-quo MIMIC
   replicates even more strongly on the diversified corpus: codex_55
   mean 0.505, median 0.540 (codex_55 effectively flips its forecast
   sign about half the time when told the YES condition currently
   holds). F102 is **not** v28a-specific.

The channel-ordering claim of F20 (tail-premium strictly stronger
than verbal confidence) was scoped down by F32 to
**corpus-and-agent-dependent**, with the per-agent `codex_55`
verbal-confidence sign-flip reproducing on the new corpus. Tail
remains the channel that doesn't sign-flip across agents; it is not
always the strongest per-agent reader on every corpus.

## What this audits

LLM-forecasting calibration as an apparatus capability: which
channels carry signal, which interventions transfer across corpora,
which operationalizations turn raw signal into utility, and where
debate-style mechanisms work vs fail. The program treats
over-claiming novelty as itself a failure mode and reports a
WebSearch-grounded novelty self-rating of 3–4 novel instruments
(not 13 novel discoveries).

## Retest tags

- F8 (tail-premium predicts Brier): *Cross-mutator replicated*
  (claude + 2 codex variants same sign across v3 + v4); apparatus-
  internal verdict only on the specific instrument.
- F10 (decomposed channels predict Brier): *Enlarged-data confirmed*
  (n=590, different corpus from F8).
- F15 (herding magnitude): *Original-run-only (n=239 triples)*;
  phenomenon documented in arXiv:2505.21588, specific binary-forecast
  measurement is ours.
- F17 (per-agent heterogeneous memory-injection rescue): *Original-
  run-only*; behavioral finding likely novel.
- F20 (tail vs vconf comparison): *Cross-corpus on apparatus*;
  scoped to corpus-and-agent-dependent ordering by F32, per-agent
  codex_55 sign-flip reproduces.
- F28 (premium-as-abstention rescue): *Original-run-only*;
  operationalization-specific.
- F30 (closed-loop judge): *Original-run-only*; pure-LLM autonomy
  with regime-dependent utility.
- F32 (tail-premium fourth replication; first all-agent-same-sign;
  scopes F20): *Original-run-only on gp225 apparatus-replay corpus*;
  N=30 per agent, Spearman SE ≈ ±0.18.
- F33 (skeptical-framing does not reduce herding): *Original-run-
  only on apparatus-external + apparatus-internal NS contracts*;
  clean Δ-vs-v5-baseline null, 6/6 pairs slope +0.65 to +0.86,
  vindicates architectural-only fix for ensemble independence.
- F95–F100 (multi-pilot composed routing + per-family channel
  calibration at N=42 → N=142): *Cross-corpus enlarged-data*; routed_v1
  beats median-of-5 at p=0.0013 and mean-of-5 at p=0.0069 (N=142);
  best-single comparison is *inconclusive_underpowered* at Δ≥0.05.
  `confident_no_discount` is the only standalone rule that beats raw
  at p<0.05 on every panel member.
- F101 (Halawi contamination): *Original analytic*; deployable filter
  `resolve_date > max(panel_cutoff)`. Empties the dataset for the
  current generation; written into the working paper §Re-audit
  Discipline.
- F102 (ESCAPE / MIMIC / near-linear split): *Cross-corpus replicated*;
  v28a 5-family × n=30 plus n=42 diversified Metaculus+FRED. Loss-frame
  ESCAPE confirmed on diverse pool; status-quo MIMIC even stronger
  (codex_55 mean 0.505 / median 0.540 on Metaculus+FRED).
- F103 (Lane B canonical L1+L2+L3 audit of 8 published AlphaProof
  Nexus AICollaborator bare-Mathlib proofs): *Original-run; methodology
  claim plus per-target verdicts*; after the helper-vs-top-level
  status-rule fix, forced sidecar at v4.27 for non-drift compile_failed,
  and the orphan-lake process-group kill discipline (2026-05-29), the
  honest verdict is: **8/8 compile kernel-clean at the pinned v4.27
  toolchain** (no `sorry`/`admit`; only allowlisted kernel axioms) and
  **all 8 are top-level L3-clean** — no headline theorem is a vacuous
  restatement. The two substantive caveats are **toolchain-pinning**
  (5/8 fail native v4.30; P5's native run hit a harness
  `audit_invocation_failed` infra bug, not falsification) and
  **library-composition** (the proofs assemble existing Mathlib lemmas —
  limited novel-math content, normal for formalization). 7/8 also carry
  **advisory** helper-level `gold_name_verbatim` flags (P1 excepted):
  a helper citing a Mathlib lemma by name is normal library use, not a
  defect. Two earlier framings are retracted — "laundering caught / 7–8
  of 8 clean" overstated quality (an auditor Bug-4 conflated helper
  passes into "clean"); "1 clean, 7 carry blockers" overstated a defect
  by weighting helper-level L3. We do **NOT** claim DeepMind published
  anything fake.
- F104 (Frequency-Inheritance Hypothesis with 3-axis taxonomy and
  pre-registered ≥8/10 cell-classification bar): *Original-run;
  inductive theory + pre-registered confirmatory smoke*; claude-
  subscription n=15 confirmatory scored **8 of 10** at the pre-
  registered bar. Two informative misses (D sunk-cost, I in-group)
  sharpen the MIMIC predicate. Cross-panel n=15 D-and-I over codex /
  deepseek / gemini fired 2026-05-29; result pending.

Full per-finding table with strength labels and evidence pointers:
`projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`
(working-directory artifact, not in the public surface).

## Honest non-claims

- Does **not** claim LLMs cannot forecast in general — positive
  findings outnumber negatives in the same program.
- Does **not** claim five independent model families — the panel is
  1 claude + 2 codex variants + 1 deepseek + 1 gemini; codex errors
  are correlated; deepseek/gemini provide cross-family diversification
  but n=42 per arm is the program's current ceiling for power-aware
  comparisons.
- Does **not** claim reproducibility-grade methodology — internal-
  audit-grade with documented external-extension path; zero second-
  lab submissions to date.
- Does **not** solve corpus contamination, author-level GT-selection
  leakage, or estimate API token cost.
- Does **not** claim novel mechanisms — most findings are
  extensions or scoped replications of arXiv:2603.25052 (multi-
  channel readout), arXiv:2604.01457 (overconfidence circuits),
  arXiv:2509.25532 (suggestibility), arXiv:2505.21588 (multi-agent
  herd behavior), Schoenegger 2024 (independent-aggregation
  ensembles), and Tian 2023 (verbalized confidence). Novelty is in
  specific instruments and operationalizations.

## Cross-reference

- Public claim register entry:
  `docs/public_claim_register.md`, section *GP-245 Forecast
  Calibration Program*.
- Working directory (private):
  `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/`.
- Parent seam:
  `research_areas/seams/protocol/GP-230_forecast_pool_decision_market_seam.md`.
- Child seam:
  `research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md`.
- Operational patterns:
  `docs/concepts/agentic_engineering_patterns.md` Pattern 12
  (Sealed Forecast Pool for Execution Control);
  `docs/concepts/reflexive_engineering.md` Primitive 9
  (Reflexive Forecast Market).
- Role mandate:
  `org/mandates/forecasting_agent_mandate.md`.
- Canonical scorer:
  `scripts/public/control/forecast/pool.py` (F9 v2 second-moment-
  Spearman extension landed 2026-05-24).
- Paper drafts:
  `papers/failure_mode_atlas/paper_draft_v1.md`,
  `papers/apparatus_testbed/paper_draft_v1.md` (both flagged
  `do-not-cite` by initial adversarial review; v2 revisions
  integrate F32/F33 and address the five kills per paper).
