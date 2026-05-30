# External-prover dispatch epd-5ceb830d9ac7

**Model**: deepseek-v4-flash
**Substrate**: F36-paper-v1.1-cross-family
**Dispatched**: 2026-05-26T16:26:58.888089+00:00
**Cost**: $0.0107
**Tokens**: 9964 in / 2372 out

## Question

# Per-Agent Calibration Inversion in LLM Forecasting Ensembles: A Three-Pilot Replicated Finding on Tail-Insurance Premium Signs

**Draft v1 — 2026-05-26**
**Status:** internal draft; replication-grade across 3 independent pilots; external cross-corpus replication (v23) pending
**Source program:** GP-245 Forecast Calibration Program — a forecaster-skill subsystem of the ZTARE research apparatus
**Provenance:** all empirical claims trace to F-IDs in `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`

---

## Abstract

We document a single, replicated finding in LLM-forecasting ensembles: the sign of the correlation between an agent's elicited tail-insurance premium and that agent's binary correctness on the same contract is **family-specific, not universal**. Across three independently-designed pilots (v21, v22b, v22d-in-flight; cumulative N = 264 premium-rowed calls), `claude-opus-4.7` consistently pays MORE premium on contracts it ends up RIGHT on (gap +5 to +10 across pilots — the inverted direction), while both Codex variants (`codex-gpt-5.5`, `codex-gpt-5.4-mini`) pay MORE premium on contracts they end up WRONG on (gap −4 to −19 — the well-calibrated direction). The global aggregate gap is flat (−3), because the population-level statistic is the AVERAGE of opposite within-family signals. Any deployment that uses elicited tail-insurance premium as a confidence-correction signal must apply a per-family sign rule; a uniform rule is wrong for one family or the other. We provide the per-pilot evidence, name the correlated-errors caveat explicitly (two of three agents share a Codex base model), bound the scope to apparatus-internal subscription-class agents on the ZTARE corpus class, and state precisely what this paper does NOT establish.

---

## 1. Single claim, single scope

### 1.1 The finding

In an LLM-forecasting ensemble eliciting an explicit second-moment channel (`tail_insurance_premium`, a 0–100 elicited concern-magnitude scalar), the sign of `corr(premium, correctness)` is **agent-family-specific** within the apparatus-internal trio:

- **claude family** — premium HIGHER on correct contracts than on incorrect contracts (inverted direction)
- **codex-gpt-5.5** — premium HIGHER on incorrect contracts than on correct contracts (direction-correct)
- **codex-gpt-5.4-mini** — premium HIGHER on incorrect contracts than on correct contracts (direction-correct)

The population-level statistic that pools these signals is empirically flat (gap ≈ −3 across 264 premium-rowed calls), because the inverted-claude pool of N≈95 is roughly balanced against the direction-correct-codex pool of N≈169. **A finding presented at the population level would report "no signal"; a finding stratified by agent family reports two opposite signals.**

### 1.2 Scope of the claim

This paper claims, and only claims:

1. The per-family **directional** sign pattern above is consistent across three pilots within one apparatus on one corpus class (DIRECTIONAL only — bootstrap 95% CIs in §4.0a include zero for claude and codex_55; only codex_mini's gap excludes zero at CI).
2. The gap magnitudes are stable within ±5 points across pilots for each family **directionally**, but the across-pilot point estimates fall within the bootstrap noise band for two of three families.
3. A deployment-time per-family **directional** sign rule is supported by the within-apparatus evidence as a prior; we ship one (`org/calibration/per_agent_premium_sign.yaml`). It should be treated as a Bayesian prior, not a statistically certified rule. R1 review labeled this "apparatus-internal-pilot-repeated", which is the correct grade — NOT "replication-grade" (replication-grade requires CI-excluding-zero on each pilot, which we do not have for claude/codex_55).

It does NOT claim:

1. External validity. The three pilots share the same corpus class (~15 contracts per pilot, balanced base-rate 0.500, ZTARE-internal mix of apparatus_RD + apparatus_binary + Lean_proof_completability targets). A cross-corpus replication (v23) is pre-registered but not yet run.
2. Three independent model families. **Two of the three agents are Codex variants sharing the underlying Codex training stack.** Sign-consistency between `codex-gpt-5.5` and `codex-gpt-5.4-mini` is therefore a within-family replication, not a between-family one. The claim "claude is inverted, codex is direction-correct" is a 2-family claim, not a 3-family claim.
3. An effect-size confidence interval. Per-pilot gaps are spreads in the ±5 range, but a bootstrapped CI requires the full cross-pilot row-level pool, which lives in the workspace and is not redistributed in this paper.
4. A mechanism beyond what §4 sketches. The "claude premium is tone-correlated, codex premium is content-correlated" mechanism is consistent with the data and with one separate within-pilot finding (F37, signed-tail cancels claude's tone confound under inverted framing) but is not directly tested.

### 1.3a Selection rule — why this finding and not the others (with honest post-hoc admission)

> **HONEST ADMISSION (added v1.1, 2026-05-26).** R1 review (DeepSeek-R1, third-vendor adversarial reviewer, 2026-05-26) correctly identified that the four-criterion selection rule below was *added in response to the 2026-05-24 Codex review* on the prior Failure Atlas and Apparatus Testbed drafts. It is therefore **post-hoc relative to F36/F40 entering this paper** — the rule was crafted after seeing that F36/F40 happened to satisfy each criterion. A truly pre-registered selection rule would have been written before any of the 41 findings were evaluated against it. We acknowledge this is a methodological weakness. The only path to fixing it cleanly is more pilots (especially v25 cross-corpus): if F36/F40 continues to satisfy the four criteria on independently-collected data not seen at rule-design time, the post-hoc nature becomes less load-bearing. Until then, the selection rule should be read as **a defense of why F36/F40 is internally consistent with the program's evidence-flow, not as a pre-registered filter that protected the paper from cherry-picking**.

The rule, post-hoc as noted above:

1. **Replication-grade.** The finding must replicate across at least 3 independently-designed pilots. F40 meets this (v21, v22b, v22d; gap direction stable per family).
2. **Deployment consequence.** The finding must imply a concrete operational rule small enough to ship. F36/F40 ship as a 4-line YAML at `org/calibration/per_agent_premium_sign.yaml`.
3. **Decomposes a published-literature null.** The finding must reframe an existing claim — here, F8's population-level positive correlation, which decomposes into opposite within-family signals.
4. **Not yet named in the published literature.** Per-family premium-sign stratification is not in the published verbalized-confidence or multi-agent-ensemble literature (Tian et al. 2023; Schoenegger 2024; AIA Forecaster 2025).

The 40 other findings in GP-245 either: (a) replicate fewer than 3 pilots, (b) lack a small deployment rule, (c) are honest negatives catalogued in the companion Failure Atlas draft (`workingpapers/failure-mode-atlas/`), or (d) are infrastructure / methodology notes catalogued in the companion Apparatus Testbed draft (`workingpapers/apparatus-testbed/`). Appendix C lists every F-ID with its decision-relevant status under this selection rule. The selection rule is the verifiable reply to Codex critique #3 ("no sampling protocol") from the 2026-05-24 adversarial review of the Failure Atlas + Apparatus Testbed drafts.

### 1.3 What was NOT done that a stronger paper would do

- No third-party blinded replication.
- No independent corpus (subscription-class operators only).
- No open-weight or reasoning-class agent in the trio.
- No prompt-stability ablation beyond the three pilot designs.
- No bootstrap CI on the cross-pilot pool.
- No formal multiple-comparison correction. The per-family signs were registered as the analysis target after the v21-mid-pilot directional read; the cross-pilot replication (v22b, v22d) was designed as confirmatory, not exploratory. **Replication ACROSS three pre-designed pilots is our substitute for formal multiple-comparison correction.** We acknowledge this is methodologically weaker than a pre-registered single-pilot test with explicit alpha control.

---

## 2. Background and prior work

LLM-forecasting calibration has converged on a recognizable positive template: pick a calibration mechanism (verbalized confidence — Tian et al. 2023, Lin et al. 2022; decomposed elicitation — Schoenegger 2024; multi-agent ensemble — AIA Forecaster 2025; rationale exchange — Du et al. 2024), pick a corpus (ForecastBench, GJP-style, internal benchmark), report a Brier improvement and an ablation. Anchors include the verbal-confidence mechanistic accounts of Closing-the-Confidence-Faithfulness-Gap (arXiv:2603.25052, 2026) and Wired-for-Overconfidence (arXiv:2604.01457, 2026); the AIA Forecaster (2025) multi-agent SOTA; and Future-Is-Unevenly-Distributed (arXiv:2511.18394) on context-dependent forecasting ability.

What is uncommon: a finding reported at the agent-family stratum that decomposes a population-level null into opposite within-family signals. Tian et al. (2023) report per-model verbalized-confidence calibration but stop at family granularity rather than within-program correlation sign. Schoenegger (2024) reports independent-aggregation ensembles assuming sign-consistent errors. The closest prior framing is the "model-specific calibration" thread, but the published literature treats this as a recommendation to fine-tune per-model thresholds rather than to deploy a sign-inversion rule on a second-moment channel.

The `tail_insurance_premium` channel itself was constructed as a second-moment elicitation primitive in the GP-245 program (F8, F10, F20, F32). The original finding (F8) reported a positive population-level correlation between premium and per-row Brier; F36 establishes that the population correlation is the average of opposite within-family signals, and F40 replicates the per-family decomposition across three pilots.

---

## 3. Method

### 3.1 Apparatus

The GP-245 forecaster-skill subsystem within ZTARE is a fixed forecast-pool + audit-discipline infrastructure. A pilot is a configuration of:
- a contract set (15 contracts, balanced base-rate 0.500)
- a per-agent prompt for each of the trio
- an elicitation schema that includes the second-moment fields (`tail_insurance_premium`, `tail_downside_worry`, `tail_upside_surprise`, plus verbal confidence and rationale)
- a dispatcher that calls the trio in parallel via subscription endpoints

All three pilots in this paper use the same apparatus binary, the same scorer, and the same pool schema. Pilots differ only in (a) contract roster, (b) prompt conditions, and (c) elicitation field set.

### 3.2 The three pilots

| Pilot | Date | N parsed / total | Conditions | Used for F40 |
|---|---|--:|---|---|
| **v21** | 2026-05-22 | 270 / 270 | C1 magnitude-only / C2 signed-tail-only / C3 combined | Yes — original derivation (F36) |
| **v22b** | 2026-05-23 | 85 / 90 | Inverted framing × signed-tail-elicited | Yes — first replication (F37 + F40 lift) |
| **v22d** | 2026-05-24 | 115 / 120 | 2×2×2 factorial (framing × tail_format × balance_instruction) | Yes — second replication |

Premium-rowed calls (N = 164 in v21, 85 in v22b, 115 in v22d; cross-pilot cumulative N = 264 after restricting to contracts where the agent emitted a non-null premium scalar).

### 3.3 The metric

For each (agent_family, pilot) cell:
- `right_med` = median of `tail_insurance_premium` over contracts where agent's binary answer agreed with ground truth
- `wrong_med` = median over contracts where the answer disagreed
- `gap` = `right_med − wrong_med`
- positive gap = INVERTED (pays more when right)
- negative gap = DIRECTION-CORRECT (pays more when wrong, which is the well-calibrated direction for a "tail-insurance" channel)

### 3.4 Pre-registration and analysis discipline

- The v21 mid-pilot directional read at N=155 (`right=55, wrong=46`, called the v21-novel signal) was reported as the INITIAL direction; this read later REVERSED at full N=270 (`right=45, wrong=54`).
- The reversal is documented in the F36 entry of `research_log.md`: at mid-pilot, claude's premium emissions dominated the premium-rowed pool while mini's parse failures suppressed its contribution. Once mini caught up, the global median pulled toward direction-correct.
- The PER-FAMILY analysis was the analysis frame BEFORE the v22b and v22d designs were committed. v22b and v22d are confirmatory, not exploratory.
- No multiple-comparison correction was applied beyond replication-across-pilots. This is acknowledged as a methodological weakness §1.3.

---

## 4. Results

### 4.0a Bootstrap CIs (added v1.1, addresses Codex+R1 review critique on statistical uncertainty)

> **Critical honest finding.** After the 2026-05-26 cross-reviewer pass (Codex GPT-5 + DeepSeek-R1), we computed 95% bootstrap confidence intervals (B=5000, resample within right/wrong pool per family, pooled across v21+v22b+v22d magnitude cells, N=223 premium-rowed observations). Result: **only codex_mini's gap is statistically supported at 95% CI**; the claude inverted and codex_55 direction-correct patterns have CIs that include zero.

| Family | n_R | n_W | point gap | **95% CI** | statistically supported (CI excludes 0)? |
|---|--:|--:|--:|---|---|
| claude | 56 | 24 | +5.0 | **[-4.5, +15.0]** | **NO** |
| codex_55 | 61 | 18 | -6.0 | **[-25.0, +4.0]** | **NO** |
| codex_mini | 57 | 7 | -19.0 | **[-47.0, -12.0]** | YES |

**Honest re-framing.** The per-family DIRECTIONAL pattern (claude +, codex −) is consistent across the three pilots, but only codex_mini's gap magnitude excludes zero at 95% CI. Claude's inverted gap is **directionally suggestive, not statistically established at N=80**. Codex_55's direction-correct gap is **directionally suggestive, not statistically established at N=79**. The decomposition (population correlation = average of opposite within-family signals) is qualitatively the right frame, but the quantitative magnitude for two of three families remains within bootstrap noise.

**What this means for §7 deployment consequence.** The 4-line YAML per-family sign rule at `org/calibration/per_agent_premium_sign.yaml` is **provisional**, not statistically certified. Operators applying the rule should treat claude-inverted and codex_55-direction-correct as expected-direction priors, not confirmed signals. Only codex_mini's pattern is statistically robust enough for unconditional deployment. v23 + v24 + a future v25 (cross-corpus + N≥30 per family) are required to upgrade claude / codex_55 from "directional" to "statistically robust" status.

### 4.1 Cross-pilot pooled evidence

| Family | N right | right_med | N wrong | wrong_med | gap | pattern |
|---|--:|--:|--:|--:|--:|---|
| **claude** | 65 | 40 | 30 | 35 | **+5 inverted** | F36 holds |
| **codex-gpt-5.5** | 71 | 54 | 23 | 62 | **−8 direction-correct** | F36 holds |
| **codex-gpt-5.4-mini** | 67 | 15 | 8 | 34 | **−19 direction-correct** | F36 holds |
| Global aggregate | 203 | 39 | 61 | 42 | **−3 ≈ flat** | structural claim confirmed |

The global aggregate is flat (gap = −3 against a per-family signal magnitude of 5–19), because the inverted-claude pool of N=95 partially cancels the direction-correct-codex pool of N=169.

### 4.2 Per-pilot evidence (replication)

| Family | v21 N=R/W | v22b N=R/W | v22d N=R/W | v21 gap | v22b gap | v22d gap |
|---|---|---|---|--:|--:|--:|
| claude | 41/19 | 9/6 | 15/5 | **+10** | **+5** | **+10** |
| codex-gpt-5.5 | 43/16 | 10/5 | 18/2 | **−4** | **−5** | **−4** |
| codex-gpt-5.4-mini | 38/7 | 11/1 | 18/0 | **−19** | **−17** | (N=0 wrong) |

Claude's gap is INVERTED in **3 of 3 pilots** (+10 / +5 / +10). Codex-gpt-5.5's gap is direction-correct in **3 of 3 pilots** (−4 / −5 / −4). Codex-gpt-5.4-mini's gap is direction-correct in **2 of 2 interpretable pilots** (−19 / −17; v22d's wrong-count is 0 due to mini's high accuracy on that pilot's contracts).

Three pilots, three independent designs, same direction for each family, magnitudes within ±5 points of each other for each family.

### 4.2a (RELOCATED — see §9.1 below)

> This section was moved out of Results into the pre-registration / exploratory section per R1 review critique #4 (cross-family extension was being used to make claims at N_wrong=1/2). See §9.1 for the v23 + v24 cross-family extension, now correctly labeled as exploratory.

### 4.2b (deleted in v1.1 — see §9.1 for v23/v24 exploratory cross-family data, correctly labeled)

### 4.3 Comparison to the F8 population-level claim

F8 (v6 pilot, 2026-05-12) reported a positive population-level correlation between premium and per-row Brier (ρ = +0.42, pooled across the three agents). F36 re-analyzed v21 per-agent and showed F8's ρ is the average of (claude inverted, codex direction-correct). F40 confirms the per-family decomposition holds on v22b and v22d.

Implication: F8 / F10 / F20 / F32 — all of which reported population-level correlation — should be re-analyzed per-agent before any deployment. F40 buys substantial confidence that the per-family decomposition is the right frame.

---

## 5. Why the population statistic is misleading

The population correlation between `premium` and `correctness` collapses to ≈ 0 because the apparatus runs three agents in parallel and pools their outputs. Two effects compound:

1. **Within-family signs are opposite.** Claude's positive gap and Codex's negative gap partially cancel.
2. **Pool-share drift is correlated with apparent direction.** When mini's parse-failure rate fluctuates (24/90 in v21), the apparent global direction shifts as mini's contribution to the pool moves.

A population-level finding is not just under-powered here — it is **structurally misleading**. The right analysis stratum is `agent_family × pilot`, not `pool × pilot`.

This is the operational lesson: any second-moment channel in an LLM ensemble should be analyzed and deployed with per-family stratification by default. Population-level findings on multi-family pools have a known bias toward "no signal" when within-family signs differ.

---

## 6. Mechanism sketch (consistent with data, not directly tested)

We sketch a hypothesis. It is not the main contribution of the paper.

- **Claude's premium is tone-correlated.** Claude appears to elicit higher tail-insurance premium when it produces a high-confidence-toned rationale, regardless of whether the rationale is correct on the contract. High-tone rationales tend to also be right (claude is calibrated on tone with content), which produces the INVERTED gap.
- **Codex's premium is content-correlated.** Codex's premium tracks the model's actual uncertainty about the answer, so it goes up when the model is going to be wrong. This produces the DIRECTION-CORRECT gap.

Two pieces of within-program evidence are consistent with this story:

- **F37 (v22b pilot).** Eliciting `tail_downside_worry` and `tail_upside_surprise` as SIGNED scalars under an inverted-framing prompt cancels claude's premium-tone confound (the claude gap drops from +10 to +5 on v22b, then back to +10 on v22d where the inverted framing is mixed with other factors).
- **F39 (v22c pilot, separate from this paper).** An availability-bias balance-instruction lift selectively rescues claude's tone-driven over-pessimism — only claude responds to the instruction, consistent with the "tone, not content" mechanism.

These observations support the hypothesis but do not prove it. A direct test would require eliciting the tone vs content components separately and showing each agent's premium tracks one but not the other. This is on the v23+ roadmap.

---

## 7. Operational consequences

If you deploy a multi-family LLM ensemble that elicits a second-moment confidence-correction channel:

1. **Stratify by agent family before computing the correlation between the channel and correctness.** Pooled correlation can be the average of opposite within-family signals.
2. **Apply a per-family sign rule when using the channel for confidence correction.** For the apparatus-internal trio, the rule is `claude → invert premium; codex → use as-stated`. We ship this rule at `org/calibration/per_agent_premium_sign.yaml`.
3. **Treat any "no signal" population-level finding as a candidate for per-family decomposition.** If the published positive-result literature reports a calibration mechanism that did not lift Brier on your ensemble, check whether your ensemble has multi-family within-it; if so, decompose before concluding the mechanism is dead.

---

## 8. What this paper does NOT establish (explicit)

- That the gap directions hold on corpora outside the GP-245 internal mix (apparatus_RD + apparatus_binary + Lean_proof_completability). v23 will test this.
- That claude in general is "inverted" — claude under THIS apparatus's prompts on THIS corpus is. Different prompts may move the sign.
- That codex in general is "direction-correct" — codex under THIS apparatus's prompts on THIS corpus is.
- That the result generalizes to non-subscription / open-weights / reasoning-class agents. Subscription-class only.
- A point-estimate effect size with CI. Replication direction and gap range are stated.
- That two Codex variants constitute two independent confirmations. They do not — they share base lineage. The cross-family claim is 2-family (claude vs codex), not 3-family.

---

### 9.1 v23 + v24 exploratory cross-family data (relocated from §4.2a per R1 critique #4)

> **HONEST EXPLORATORY LABEL** (added v1.1, 2026-05-26). The data below was originally inserted into §4 Results. R1 review correctly flagged that N_wrong=1/2 cells were too thin to bear a "materially weakens" claim in the Results section. The data is preserved here as **exploratory cross-family evidence**, not Results. Treat as motivating v25 with adequately powered N, not as confirming the per-family rule on gemini/deepseek.

The two-Codex-variants caveat in §1.2 motivated adding non-Claude / non-Codex families. v23 ran `gemini-2.5-flash` + `deepseek-chat` on the same 5 contracts as v22d, single condition `(positive, magnitude, balance_off)`. v24 ran the same two families across the full 2×3×2 factorial (12 cells × 5 contracts × 2 families = 119/120 parsed).

Cell-restricted (positive/magnitude/balance_off) preliminary table:

| Family | n_R | n_W | gap | exploratory direction (CI NOT computed at this N) |
|---|--:|--:|--:|---|
| gemini-2.5-flash | 3 | 2 | +5 | suggestive INVERTED — N too thin for CI |
| deepseek-chat | 4 | 1 | 0 | UNRESOLVED — N_wrong=1 |

**What this exploratory data is NOT.** It is not the basis for a 4-family or 5-family scope claim. With N_wrong as low as 1 (deepseek) and 2 (gemini), no inference about the cross-family direction is statistically supported. The bootstrap CI in §4.0a was deliberately NOT computed for gemini/deepseek because the small-N CIs would be wildly wide and uninformative.

**What v25 is pre-registered to do.** Run gemini + deepseek across N≥30 contracts each (vs the 5 in v23/v24) so the bootstrap CI can be computed and the cross-family direction is statistically establishable. Same factorial structure as v24. Estimated cost: ~$2-5 in API spend. Wall time: ~20-40 min.

**Why we report the exploratory data at all.** Transparency. The v23/v24 runs were executed; their data exists in `pilot_v23_calls.jsonl` and `pilot_v24_calls.jsonl`; omitting them would be selective. The honest framing is "exploratory, motivating v25, not confirming."

---

## 9. Pre-registration of v23 (the external replication)

A cross-corpus replication is pre-registered to test:

- **Same per-family sign rule** on a corpus from outside the GP-245 mix (candidates: ForecastBench frozen slice, GJP-style geopolitical pool).
- **Same trio** (claude-opus-4.7, codex-gpt-5.5, codex-gpt-5.4-mini) for direct comparability.
- **Same elicitation schema** with `tail_insurance_premium` + signed-tail fields.
- **Pre-registered analysis frame** before any data is collected: per-family gap signs, magnitudes within ±5 of the GP-245 values, replication count across at least 2 corpora.
- **Pass-gate.** All three families show the same gap sign as in F40. If any family flips sign across corpora, the per-family rule is corpus-dependent and the operational guidance §7 is narrowed.

---

## 10. Why we're publishing this now

Three reasons:

1. **The result is replication-grade within the apparatus.** Three independent pilot designs, same direction per family, magnitudes within ±5. That's stronger than most single-pilot LLM-forecasting findings in the published literature.
2. **The published positive-result literature is silent on this stratum.** Findings reported at the pool stratum are systematically subject to the same averaging-out bias documented here.
3. **The deployment consequence is concrete and small.** A 4-line YAML rule. If we're wrong, the cost of carrying it is one operator-decision-cycle to remove. If we're right, applying the rule fixes a calibration error that nobody else has named yet.

We publish at internal-audit-grade with the external-extension path (v23) explicitly pre-registered. This is one tier below citation-grade reproducibility (no third-party blinded replication, no independent corpus, no open-weights agent in the trio). We label it as such.

---

## 11. Related findings (program context)

For context, GP-245 has documented 41 findings (F1–F41) over ~13 pilots. The F-IDs cited in this paper:

- **F8** — Original population-level claim that tail-insurance premium predicts per-row Brier (positive ρ, pooled across agents). The claim this paper decomposes.
- **F32** — First pilot where all three agents agreed in direction on the tail-channel signal. F36 re-analysis showed the agreement is at population level only; per-family signs were already opposite.
- **F36** — Per-agent inverted-vs-direction-correct premium-correctness coupling (v21-only). The original derivation.
- **F37** — Signed-tail elicitation under inverted framing cancels claude's tone confound (v22b).
- **F39** — Availability-bias balance instruction selectively rescues claude (v22c).
- **F40** — Cross-pilot replication of F36 across v21 + v22b + v22d (N=264). The publication-grade evidence.
- **F41** — 2×2×2 factorial: balance instruction is the dominant lever, and only for claude. Consistent with the §6 mechanism sketch.

The full ledger is in `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`. The deployment artifact is `org/calibration/per_agent_premium_sign.yaml`.

---

## 12. Reproducibility statement (honest)

- **Within-apparatus replication:** YES — three independent pilots (v21, v22b, v22d) produce the same per-family direction with magnitudes within ±5 points.
- **Third-party blinded replication:** NO. The trio (claude-opus-4.7, codex-gpt-5.5, codex-gpt-5.4-mini) was dispatched under one operator's subscription accounts. No second operator has replicated.
- **External corpus:** NO. All three pilots use the GP-245-internal corpus class. v23 is pre-registered against an external corpus but has not been run.
- **Open-weights agent:** NO. The trio is subscription-class only. A reasoning-class or open-weights agent has not been added.
- **Prompt stability:** PARTIAL. v22b and v22d use different elicitation prompts from v21; the per-family signs survive. We have not done a fine-grained prompt-perturbation ablation.

The reproducibility grade we claim: **apparatus-internal, three-pilot-replicated, with documented external-extension path (v23).** This is one tier below citation-grade.

---

## 13. Citation

If you cite this finding:

```bibtex
@misc{ztare_per_agent_premium_inversion_2026,
  title = {Per-Agent Calibration Inversion in LLM Forecasting Ensembles:
           A Three-Pilot Replicated Finding on Tail-Insurance Premium Signs},
  author = {Alami, Daniel},
  year = {2026},
  howpublished = {\url{https://github.com/sparckix/ztare}},
  note = {GP-245 Forecast Calibration Program, internal draft v1, 2026-05-26}
}
```

---

## Appendix A — Per-pilot row counts (full disclosure)

The premium-rowed N per family per pilot includes only contracts where the agent emitted a parseable `tail_insurance_premium` scalar. Parse-failure rates were:

- **v21:** 270/270 calls returned; 164 emitted a parseable premium (60.7%). The 106 calls that did not emit a premium were either in the C2 condition (signed-tail-only, no unsigned premium field) or returned an unparseable schema. Per-family parse rates: claude 60/90, codex_55 59/90, codex_mini 45/90.
- **v22b:** 85/90 calls returned; all 85 emitted a parseable premium. The 5 missing calls were parse failures at the dispatcher level.
- **v22d:** 115/120 calls returned; all 115 emitted a parseable premium. 5 missing at dispatcher level.

The N=264 cross-pilot cumulative count is `164 + 85 + 115 = 364` minus 100 v21 C2-condition rows where the premium field was absent by design = 264.

## Appendix C — Complete GP-245 finding ledger (F1–F41) and selection-rule status

The table below lists every documented finding in the GP-245 program (the canonical ledger is `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`). Each row is tagged against the four selection-rule criteria in §1.3a. A row that satisfies all four enters this paper as a lead claim; rows that satisfy a subset are routed to the companion Failure Atlas draft (negatives) or Apparatus Testbed draft (infrastructure/methodology). The intent is to demonstrate that this paper is **one finding from a disciplined 41-finding program**, not a cherry-picked instance.

Legend: ✅ meets criterion, ❌ does not, — not applicable.

| F-ID | One-line headline | Replicates 3+ pilots | Small deployment rule | Decomposes a literature null | Unnamed in published lit | Routed to |
|---|---|:--:|:--:|:--:|:--:|---|
| F1 | Subscription-class trio is internally consistent on shared contracts | ❌ (single pilot) | ❌ | ❌ | — | testbed |
| F2 | Brier on apparatus_RD class is ~0.21 trio-aggregate | ❌ | ❌ | ❌ | — | testbed |
| F3 | Codex_mini parse-failure rate is 24/90 on tail-field schema | ❌ | partial (schema fix) | ❌ | — | testbed |
| F4 | Verbal-confidence channel sign-flips per agent on apparatus_binary | ✅ (v6/v9.1/v21) | partial | ❌ | partial | folded into F36 chain |
| F5 | Lean-proof-completability binary forecast is worse than constant baseline | ❌ (corpus-bounded) | ❌ | ✅ | partial | atlas (as F12) |
| F6 | Closed-loop super-judge ratifies Brier-improvement on worried cases | ❌ | partial | partial | partial | future paper |
| F7 | Self-vs-external prediction contrast confound (binary vs continuous task) | ❌ | ❌ | ❌ | — | atlas (as F14, downgraded) |
| F8 | Premium predicts per-row Brier at population level (ρ ≈ +0.42, v6) | ✅ (replicated to F32) | ❌ (decomposes per F36) | — | — | **this paper as the claim F36 decomposes** |
| F9 | Channel-ordering ablation: signed vs unsigned magnitude on small N | ❌ | ❌ | ❌ | — | testbed |
| F10 | Tail-premium predicts Brier on v9.1 injected-memory variant (ρ +0.39) | ❌ | ❌ | ❌ | — | F8 chain |
| F11 | Verbal confidence sign-flip is corpus-dependent (Lean vs apparatus_RD) | ❌ | ❌ | partial | partial | atlas |
| F12 | LLMs predict Lean-proof completability **worse than constant baseline** | ✅ (v6/v6.1/v9.1) | ✅ (do not deploy on Lean class) | ✅ | ✅ | **atlas — publishable as honest negative** |
| F13 | External forecast-meta-classifier baseline behaves OOD across pilots | ❌ | ❌ | ❌ | — | atlas (as F24) |
| F14 | Self-vs-external contrast downgraded to diagnostic-only | — | — | — | — | atlas (diagnostic entry) |
| F15 | Herding under exposure: slope(shift ∣ prior_gap) ≈ +0.75 | ✅ (v5/v5.1/v6.1) | partial | ✅ | ✅ | atlas (as F33 pair) |
| F16 | Honest non-claim density rises under adversarial framing | ❌ | ❌ | ❌ | — | testbed |
| F17 | Brier-CI widening rule fails on binary outcomes for claude (+0.034) | ❌ | partial | ❌ | partial | atlas |
| F18 | F-meta-classifier OOD broke; v2 restored 3/4 pilots; v10 still null | ❌ | ❌ | ❌ | — | atlas (as F24) |
| F19 | Rationale-only transfer does not improve receiver Brier (single-shot binary) | ✅ (paired with F22) | ✅ (do not deploy rationale-exchange) | ✅ | partial | **atlas — publishable as honest negative** |
| F20 | Tail-premium channel ordering: stronger than verbal confidence | ❌ | ❌ | partial | partial | folded into F8 chain |
| F21 | Codex_55 verbal-confidence sign-flip persists on cross-domain corpus | ❌ | ❌ | ❌ | — | testbed |
| F22 | Adversarial framing rescues only worst-case anchoring, not Brier | ✅ (paired with F19) | partial | ✅ | partial | atlas |
| F23 | Debate works on code/seam review; fails on single-shot binary forecasting | ❌ | partial | ✅ | ✅ | atlas (reconciliation entry) |
| F24 | Meta-classifier OOD: v1 broke, v2 restored 3/4, v10 still null | ❌ | ❌ | ❌ | — | **atlas — publishable as honest negative** |
| F25 | Per-cost effort divisor claude 4.36× OOB; codex_55 cost 4.12× | ❌ | ✅ (per-agent calibration) | partial | partial | folded into F28 |
| F26 | Per-agent cost-calibration coefficients live at `org/calibration/per_agent_cost_calibration.yaml` | ❌ | ✅ | ❌ | — | testbed |
| F27 | F-meta cross-domain benchmark rank-flip across corpora | ❌ | ❌ | partial | partial | atlas |
| F28 | Premium-as-abstention rescues F25 (utility +22 on symmetric loss) | ❌ | ✅ | partial | partial | future paper |
| F29 | Closed-loop super-judge re-decision: Brier 0.21 → original 0.35 on worried cases | ❌ | partial | partial | partial | future paper |
| F30 | Super-judge regime-dependent utility | ❌ | partial | ❌ | — | future paper |
| F31 | Decision-utility framework retrofit | ❌ | ❌ | ❌ | — | future paper |
| F32 | First pilot where all three agents agree in tail-channel direction at population | ✅ (paired with F36 decomposition) | — | ✅ | ✅ | **this paper (the population pre-decomposition)** |
| F33 | Skeptical-instruction framing does NOT reduce herding | ✅ (F15 baseline + F33 negative) | ✅ (do not behavioral-patch herding) | ✅ | ✅ | **atlas — publishable as honest negative** |
| F34 | Lit cross-walk for F1-F34 (no new evidence) | — | — | — | — | testbed |
| F35 | Signed-tail beats unsigned magnitude on v21 (C2 < C1, C3 = noise) | ❌ (v21 only) | ✅ (schema field) | partial | partial | **this paper as F36 lead-in** |
| F36 | Per-agent inverted-vs-direction-correct premium-correctness coupling | ✅ (v21 base; F40 replicates) | ✅ | ✅ | ✅ | **this paper — LEAD CLAIM** |
| F37 | Signed-tail under inverted framing cancels claude's tone confound | ❌ (v22b only) | partial | ✅ | partial | **this paper as F36 mechanism** |
| F38 | Question-form framing inversion: no Brier lift but 1.7-5× failure-mention | ❌ (v22 only) | ❌ | ✅ | ✅ | future paper |
| F39 | Availability-bias balance instruction lifts claude Brier −0.06 | ❌ (v22c only) | partial | ✅ | ✅ | future paper |
| F40 | F36 replicates across 3 independent pilots (N=264) | ✅ (definitional) | ✅ (definitional) | ✅ | ✅ | **this paper — REPLICATION EVIDENCE** |
| F41 | 2×2×2 factorial: balance instruction is dominant lever, claude only | ❌ (v22d only) | ✅ | ✅ | ✅ | **this paper as F36 mechanism confirmation** |

**Reading the table.** Of the 41 findings, **6 enter this paper** (F8 as the population claim, F32 as the population pre-decomposition, F35 as the schema lead-in, F36 as the lead claim, F37 + F41 as mechanism support, F40 as replication evidence). **5 route to the Failure Atlas** (F5/F12, F19, F22, F24, F33). **8 route to the Apparatus Testbed** (F1, F2, F3, F9, F16, F21, F26, F34). **6 enter the future-paper queue** (F6, F28, F29, F30, F31, F38, F39, with F28/F38/F39 most likely first since each has an operational rule). The remaining are intermediate diagnostics not currently planned for publication.

The selection rule from §1.3a is verifiable against this table: only F36 + F40 satisfy ALL FOUR criteria simultaneously (3-pilot replication AND deployment rule AND decomposes a literature null AND not yet named in published lit). The other findings drop out on at least one criterion.

If the reader believes this paper should include more findings, point at the table and identify which other F-ID(s) satisfy all four. If none do, this paper's narrow scope is correct. If some do, this paper should be widened. Either way the conversation is in terms of the verifiable table, not adjective-grade dispute about "cherry-picking."

---

## Appendix B — On the two-Codex-variants caveat

The most important methodological caveat: **two of the three agents in the trio share a Codex base.** This is not three independent model families; it is one Anthropic family (claude-opus-4.7) and two variants of one OpenAI family (codex-gpt-5.5 and codex-gpt-5.4-mini).

What this DOES NOT WEAKEN:
- The within-family replication for the Codex variants (the two Codex agents replicate each other's sign across all 3 pilots) is consistent with shared training. It's a within-family confirmation that the signal isn't artifact of one specific Codex variant.
- The CROSS-family pattern (claude inverted vs codex direction-correct) is observed once across two families.

What this DOES WEAKEN:
- Any claim that "3 model families" agree is wrong — only 2 do.
- Generalization to other Anthropic models, other OpenAI models, or other vendors (Google, Meta, DeepSeek, etc.) is not supported by this evidence.
- A future v23 design should include at least one additional family (Gemini, DeepSeek, or open-weights Mixtral / Llama / Qwen) to strengthen the cross-family claim.

We name this caveat in the abstract, in §1.2, and here in Appendix B. It is the single most important honest scope bound on the paper.


## Response

## PATTERN-014 — Cross-Family Verification Attack on Per-Agent Calibration Inversion Draft

### 1. Load-bearing Eigenclaims

| Claim | Type | Standard form required |
|---|---|---|
| C1 | Per-family sign pattern is consistent across 3 pilots | H: ∀p∈{v21,v22b,v22d}. sign(gap<sub>family</sub>) = sign(family) |
| C2 | Population aggregate is flat | H: global gap ∈ [-5,5] on 0–100 scale |
| C3 | Claude inverted, codex direction-correct | H: E[gap<sub>claude</sub>] > 0 ∧ E[gap<sub>codex_55</sub>] < 0 ∧ E[gap<sub>codex_mini</sub>] < 0 |
| C4 | Deployment rule “claude → invert premium, codex → use as-stated” is supported | H: under the rule, corrected premium improves Brier vs uncorrected |
| C5 | F8 population-level correlation ρ≈+0.42 is average of opposite within-family signals | H: ∃ weights w<sub>f</sub> such that ρ<sub>pop</sub> = Σ w<sub>f</sub>·corr<sub>f</sub>(premium, correctness) with corr<sub>claude</sub> < 0 and corr<sub>codex</sub> > 0 |

### 2. Divergences from Standard Evidentiary Form

**2.1 Precondition vs conclusion mismatch for C1**

- Precondition: “replication” requires that each pilot’s per-family gap sign be *statistically distinguishable from zero* (e.g., bootstrap 95% CI excludes zero). The paper’s own §4.0a reports that for claude (CI [-4.5, +15]) and codex_55 (CI [-25, +4]), the CIs include zero. Therefore C1’s precondition is **not met** for those two families.
- The claimed “consistent direction” is a point estimate that is not stable under sampling noise in 2/3 families. The only family with CI excluding zero is codex_mini, but that family has n_wrong=7 (aggregate) and n_wrong=0 on v22d, making its “replication” across pilots trivially non-existent on one pilot.
- **Counterexample regime**: suppose in a fourth pilot, claude’s gap flips to -2 (well within its CI). This would be consistent with the observed CIs and would break the “stable direction” claim. The paper provides no CI on the sign itself, only a point estimate.

**2.2 Quantifier scope ambiguity in C2**

- “Global aggregate gap is flat (−3)” — the metric is median difference. Under a null where per-family gaps are zero, the global gap would be zero. The reported −3 is not tested against a null. No standard error or CI is given for the global gap. Without quantifier bounds on “flat”, the claim is unfalsifiable.
- The paper’s own logic that population flatness is “structural” depends on the assumption that the sign decomposition is real. If the per-family gaps are within noise, the population gap is also within noise. C2 becomes a restatement of “we didn’t detect a significant effect,” which is not a positive claim.

**2.3 The “inverted vs direction-correct” dichotomy (C3) is not statistically supported for two families**

- Using the paper’s own bootstrap CIs, the hypotheses H_claude⁺ and H_codex_55⁻ are **not rejected** by the data at conventional α=0.05. The only family whose gap excludes zero is codex_mini, but its n_wrong=7 (pooled) raises concerns about small-sample bias.
- The paper’s “three-pilot replication” relies on raw median differences without confidence intervals. This is an exploratory pattern, not a confirmatory finding.
- **Mathematical weakness**: Let X<sub>f,p</sub> be the gap for family f in pilot p. The authors claim X<sub>claude, p</sub> > 0 for p=1,2,3. But the sampling distribution of X<sub>claude, p</sub> has large variance (CI width ~20 points). The probability that all three observed point estimates are positive under the null X<sub>claude</sub> = 0 is not small enough to be convincing. A simple sign test on three pilots with p₀=0.5 gives p = 0.125, well above significance.

**2.4 Deployment rule (C4) is proposed without evidence of Brier improvement**

- The paper claims the rule “fixes a calibration error” but provides no evaluation of the corrected premium’s performance on a held-out set. The rule could worsen calibration if the direction is noise. **Proof sketch for counterexample**: suppose claude’s inverted gap is artefactual (e.g., due to small wrong-pool). Then inverting premium would artificially increase the correlation with correctness on future data, but this increase could be spurious if the underlying relation is zero. The paper needs to show an out-of-sample Brier lift, which it does not.
- The rule’s statistical certification is limited to codex_mini; for the other two agents, the CI includes zero, so unconditionally applying an inversion or signing rule is unsupported.

**2.5 Decomposition of F8 (C5) is logically necessary but quantitatively unfounded**

- The claim that ρ<sub>pop</sub> = average of opposite within-family correlations is a mathematical identity *if* the within-family correlations are measured without error. But the reported correlations have wide CIs. The decomposition is true as a point estimate, but the CIs around the within-family correlations likely overlap zero, meaning the “opposite within-family pattern” is not a statistically distinct reversal.
- Without within-family standard errors, the “population null is structural” argument is a numerical coincidence, not a robust finding.

### 3. Additional Critical Observations

**3.1 Post-hoc selection rule (§1.3a) invalidates confirmatory framing**

- The authors admit the selection rule was crafted after seeing that F36/F40 satisfied it. This is p‑hacking by criterion construction. The rule is not equivalent to a pre-registered analysis plan; it merely post-rationalizes why one finding out of 41 was chosen for publication. The selection rule itself has no cross-validatory power because it was built on the same data.

**3.2 Two-Codex caveat kills the multi-family independence claim**

- The only cross-family contrast is claude vs codex (with two correlated variants). This is a single independent comparison. There is no replication at the model-vendor level. The paper’s “3‑pilot” replication is within-apparatus, not within-family.

**3.3 No multiple-comparison correction across 41 findings**

- Even if the per-family analysis were pre-registered, the fact that 41 findings were examined means the probability of at least one finding achieving p<0.05 under global null is essentially 1. The authors acknowledge this but dismiss it with “replication across three pilots is our substitute.” However, the replication is on the same corpus, same apparatus, same operator, same prompt family—not independent at the level required to replace Bonferroni.

**3.4 V23 pre-registration is not yet executed**

- The paper relies on the promise of future replication to claim provisional validity. In mathematical form, this is an argument from “would be nice if true,” not evidence.

### 4. Verdict

**NO** — the paper does not provide statistical evidence for its central directional claims. The bootstrap CIs for 2 of 3 families include zero; the “three-pilot replication” is a pattern of point estimates without confidence; the selection rule is post-hoc; and the cross-family independence is limited to a single contrast. The codex_mini pattern is the only statistically supported result, but it is on a single family with small wrong-pool sizes. The paper’s conclusions are unsupported at the level of mathematical proof or standard statistical inference. It is an exploratory pattern, not a confirmed finding.
