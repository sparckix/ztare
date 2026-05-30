# GP-061 Phase-2 Steering Measurement — Pre-Registration (DRAFT)

> **Seam metadata** · `seam_id:` GP-061 · `track:` substrates · `status:` SEALED - knobs fixed. Execution pending operator "go" on act · `last_updated:` 2026-05-08


**Sealed:** 2026-04-15 after operator sign-off on §9 open questions.
**Parent seam:** `GP-061_void_driven_steering_measurement_seam.md`
**Status:** SEALED — knobs fixed. Execution pending operator "go" on actual run initiation.

---

## 1. Question

Does injecting Component B's void constraint into the mutator prompt move the void-fill rate above the A-arm baseline established in phase 1?

**Phase-1 baseline recap.**
- sandbox_07: observed 0.25 vs chance 0.35 (lift −0.10, n=8)
- sandbox_08: observed 0.20 vs chance 0.43 (lift −0.23, n=5)

Phase 2 asks whether the mutator, given the void list as a prompt constraint, closes the gap toward chance or above.

## 2. Hypothesis

**H-STEER-01.** Under live paired runs on gp045_cold_residual_01 with Component B's confirmed void constraint injected in the treatment arm and `--disable-negative-space-extractor` in the control arm, the treatment arm's per-iteration void-fill rate exceeds the control arm's rate by ≥ 0.20 absolute, measured across ≥ 8 paired proposal pairs.

**Null.** Treatment fill rate − control fill rate < 0.20. This is operationalized as "Component B is a dashboard, not a steering wheel, under the current mutator prompt integration." Null is informative and is the failure mode most directly relevant to Paper-2 framing.

**Alternative (stronger) reading.** Treatment − control ≥ 0.40. This would justify claiming Component B actively redirects search away from the anchoring prior. Not the pre-registered primary; listed here only so the post-hoc reading cannot move the goalposts.

## 3. Target project

**gp045_cold_residual_01.**

Rationale over alternatives:
- gp045 has 5 qualifying `structural_misfit` families at residual ≥ 0.15. gp042 has 3 (bare minimum). More qualifying families → denser void universe → more headroom for steering to show.
- gp045 produced a clean Component B firing under the cold-test verification 2026-04-15 (4 voids at `fn:exp|arg0|has_op:{Add, Call, Div, Sub}`). The void set is known and stable.
- gp045 is Planck-grammar. Within-grammar portability is sufficient for this measurement — the question is about steering mechanics, not cross-grammar generalization.

## 4. Protocol

### 4.1 Project cloning

Before any run, clone the target project directory twice:

```
projects/gp045_cold_residual_01_ab_treatment/
projects/gp045_cold_residual_01_ab_control/
```

Each clone gets an identical copy of:
- `project_charter.md`, `evidence.txt`, `evidence_holdout.txt`, `raw/`, `history/`
- Rubric pinning (same rubric file for both clones)

Each clone gets a **fresh** (empty) `workspace/derived_constraints.json` at seal time. No pre-existing constraints carried over.

### 4.2 Run sequence

Four autoresearch_loop invocations total:

| Arm | Run | Invocation flags | Purpose |
|---|---|---|---|
| Treatment | 1 (prime) | normal (Component B active) | Emit void as provisional (seen_count_runs=1) |
| Treatment | 2 (measure) | normal (Component B active) | Re-emit void → promoted to confirmed (seen_count_runs=2) → injected into mutator prompt |
| Control | 1 (prime) | `--disable-negative-space-extractor` | Mutator sees no void injection; corpus grows |
| Control | 2 (measure) | `--disable-negative-space-extractor` | Mutator sees no void injection; collect measurement proposals |

**Iterations per run.** `--iters 10` for all four invocations. Same iteration budget in both arms.

**Models pinned.** `--mutator_model gemini --judge_model gemini` for all four invocations. No model fallback: `--no_model_fallback`. No primitive retrieval: no `--use_primitives`, no `--use_mutator_primitives`.

**Seeds.** Autoresearch_loop does not expose a seed flag for the mutator LLM. Both arms inherit the same temperature and sampling config from the shared runtime. Treatment/control differ only in whether the void constraint text appears in the rendered prompt block.

**Rubric.** Both arms use `rubrics/gp045_cold_residual_01.json` unchanged, no dynamic rubric evolution (`--dynamic` off, `--auto-evolve` off).

### 4.3 Measurement extraction

After all four runs complete, read:
- `projects/gp045_cold_residual_01_ab_treatment/workspace/fit_result_iter_*.json` (run 2 only)
- `projects/gp045_cold_residual_01_ab_control/workspace/fit_result_iter_*.json` (run 2 only)

For each iteration in each arm, parse the `expression` field into a feature bag using the same `_normalize_family_label + _parse_to_ast + extract_generalized_feature_matrix` path as `gp061_retro_steering_baseline.py`.

For each iteration's proposal, check whether its feature bag contains any slot in the **Run-1 treatment void set** (the voids Component B emitted after the priming run in the treatment arm — this is the set that was actually injected into the treatment's Run-2 prompt).

### 4.4 Primary metric

**Paired fill-rate difference.**

```
treatment_rate = (# Run-2 treatment iterations whose bag fills any void) / (# Run-2 treatment iterations)
control_rate   = (# Run-2 control iterations whose bag fills any void)   / (# Run-2 control iterations)
delta          = treatment_rate - control_rate
```

**Success criterion for H-STEER-01:** `delta ≥ 0.20`.
**Null:** `delta < 0.20`.
**Dashboard reading:** `delta < 0.05` — Component B has no measurable effect on the next proposal distribution.

## 5. Secondary measurements (exploratory, not pre-committed)

These are computed and reported but do not bear on H-STEER-01's pass/fail.

1. **Per-slot fill rate.** For each void slot, across both arms' run-2 iterations, fraction that filled it. Useful for seeing whether one slot dominates the steering effect.
2. **Novelty rate.** Fraction of run-2 iterations where the proposal's feature bag is not a strict subset of the run-1 corpus. Addresses whether void injection changes exploration breadth generally, or only the specific void dimension.
3. **Score trajectory difference.** Treatment arm run-2 score trajectory vs control arm run-2 score trajectory. Not a steering metric, but reveals whether void injection improves or degrades convergence.

## 6. What could invalidate the measurement

1. **Void set differs between treatment Run 1 and Run 2.** If Run 2's emitted voids are a different set than Run 1's, the injection may be mis-aligned with the iterations we are measuring. Mitigation: freeze the Run-1 void set as the "injection target" and check that Run-2's emission matches it before reading the measurement. If they diverge, the measurement is discarded and the design needs revisiting.
2. **Mutator ignores the constraint block entirely.** If Run-2 proposals in the treatment arm look identical to the control arm, distinguish between "injection rendered but ignored" and "injection never rendered" by grepping the mutator prompt log for the void constraint text. This is a diagnostic check, not a success criterion.
3. **Random-seed dominance.** Without a mutator seed flag, run-to-run variance on the same arm could exceed the treatment–control gap. Mitigation: budget permitting, run each arm twice (8 invocations total) and report mean delta with a crude variance estimate. Phase-2a: skip this mitigation. Phase-2b (if delta is close to 0.20 threshold): re-run with the variance estimate.
4. **The first iteration of the mutator gets the full charter and not the derived_constraints injection.** Need to verify the derived_constraints injection point in `autoresearch_loop.py` applies to iteration 1 of the measurement run (run 2), not only iteration ≥ 2. If the injection only applies from iteration 2 onward in a run, the measurement window is n=9 per arm, not n=10.

## 7. Budget and sign-off required

- **LLM calls.** 4 runs × 10 iterations × (mutator + firing squad + judge calls per iter) ≈ 4 × 10 × 5 = ~200 LLM calls at gemini-flash rates. Rough cost: $2–10 depending on context sizes. Low cost.
- **Wall time.** Each run ≈ 20 min. 4 runs sequential ≈ 80 min. Can be parallelized if the workspace paths are distinct (they are, via cloning).
- **Disk.** Two cloned project directories × ~50 MB each = ~100 MB transient. Can be deleted after measurement extraction.

**Operator sign-off required before sealing this pre-reg:**
1. Approval of target project choice (gp045 vs gp042 vs other).
2. Approval of iteration budget (--iters 10 vs 8 vs 5).
3. Approval of model pinning (gemini vs claude vs gpt4o).
4. Approval to clone project directories under the `_ab_treatment` / `_ab_control` suffix convention.

## 8. What this pre-reg does NOT claim

- Cross-grammar generalization of Component B. That remains gated by task #55 (nesting-cleared live-mutator target construction). Phase 2 is within-grammar only.
- Closed-loop convergence improvement. The measurement is about *whether the mutator's next proposal shifts*, not whether the score trajectory benefits. Score trajectory is a secondary exploratory observation.
- Generalization to non-Planck domains, non-fit-primitive graders, or non-gemini mutators. All of those are separately-scoped future questions.
- That a positive result resolves INS-011 (the nesting-collapse-at-ε=0 pathology). INS-011 is about what happens when the mutator is *smart* about over-parameterization under a smooth continuous grader. Phase 2 measures a different thing: whether the mutator, in a regime where it is already stagnating, responds to void injection. These are independent measurements.

## 9. Operator decisions — sealed 2026-04-15

1. **Target project: `gp045_cold_residual_01`.** Confirmed.
2. **Iteration budget: `--iters 10` per run.** Confirmed.
3. **Model pinning: `--mutator_model gemini-pro --judge_model gemini-pro`.** Confirmed. Rationale: gemini-flash prone to instruction-following failures on constraint-block compliance; gemini-pro is the deliberate-but-still-affordable tier. No `--no_model_fallback` exception — keep the pinning strict.
4. **Sequential runs.** Confirmed implicitly (no parallelization this round).
5. **No pre-commit to phase-2b.** If phase-2a delivers `delta ≥ 0.20` or `delta < 0.05`, stop and write the result up. Run phase-2b ONLY if phase-2a's delta is in the ambiguous zone (approximately 0.05 ≤ delta < 0.20). Operator's framing: "Ship the artifact. Do not waste time and credits re-running a proven success just to be pedantic. The goal is to establish the capability and move to the LessWrong write-up, not to achieve a p-value of 0.0001."

**Locked invocation flags (identical across arms except the single axis):**

```
--project gp045_cold_residual_01_ab_{treatment|control}
--rubric gp045_cold_residual_01
--iters 10
--mutator_model gemini-pro
--judge_model gemini-pro
```

Note: `--rubric` takes the bare rubric name, not a path. `autoresearch_loop.py:293` builds the full path as `RUBRICS_DIR / f"{args.rubric}.json"`.

Treatment arm adds: (nothing — Component B default-on).
Control arm adds: `--disable-negative-space-extractor`.

## 9a. Operator amendment 2026-04-15 — WITHDRAWN same day after skeptic review

**Status: WITHDRAWN 2026-04-15.** The amendment below was drafted after a stuck 20-min run on gemini-pro motivated a cost/time escape. A subsequent ruthless skeptic review surfaced five decisive problems the amendment did not address:

1. **Prompt-length confound.** Injection lengthens the treatment prompt; flash degrades more than pro with context length. Treatment vs control confounds void steering with attention-budget pressure. This was likely part of the original §9 rationale.
2. **Flash base-rate artifact.** Flash's looser generation produces more diffuse outputs with higher incidental void overlap. A +0.20 delta on flash could be real steering OR a noise-floor artifact — the compliance grep doesn't separate these.
3. **Compliance grep is presence-only, not position-aware.** Flash attends more heavily to recent tokens. If the void block lands mid-prompt, grep passes but the causal channel is closed.
4. **n=9 paired iterations is underpowered under flash variance.** Minimum detectable effect likely exceeds 0.20 — a null is uninterpretable regardless of compliance.
5. **Motivated-stopping bias.** The asymmetric-evidence argument ("positive on flash is stronger than positive on pro") was constructed because operator was cost-anxious, not because the physics supported it. Classic `feedback_frustration_diagnosis.md` failure mode.

**Decision after skeptic review.** Revert to sealed §9: gemini-pro for both arms, `--no_model_fallback`, full phase-2 sequential. The stuck-run problem is diagnosed as visibility (Python stdout block buffering) + gemini-pro per-call latency, not a design flaw. Re-run with `PYTHONUNBUFFERED=1` to fix visibility. Accept the 4–6 hour wall time and ~$10–20 cost as the price of interpretability.

The withdrawn amendment text is preserved below for audit trail. **Do not execute it.**

---

### §9a amendment text (WITHDRAWN — retained for audit)

**Motivation.** The original §9 sealed `gemini-pro` for both arms on the rationale that flash has weaker instruction-following on constraint blocks. A live run attempt on 2026-04-15 (PID 4730) stalled on iter 1 for 20+ minutes with zero visible output — the stuck-vs-slow diagnosis pointed to gemini-pro per-call latency (5 calls per iter × ~60–120s gemini-pro response time, amplified by silent stdout buffering). The operational friction of running a sealed pre-reg that takes 4–6 hours wall time per attempt conflicts with the "ship the artifact" framing in §9 decision 5.

**Amendment.** Replace §9 decision 3 with a phased design:

- **Phase-2a:** Run all four autoresearch_loop invocations (treatment×2 + control×2) with `--mutator_model gemini --judge_model gemini` (flash tier). Expected wall time ~30 min total, cost ~$0.50.
- **Phase-2b (conditional):** Re-run all four invocations with `--mutator_model gemini-pro --judge_model gemini-pro` IFF phase-2a produces a non-decisive result. See interpretation rules below.

**Interpretation rules under the amendment.**

| Phase-2a delta (flash) | Interpretation | Phase-2b triggered? |
|---|---|---|
| delta ≥ 0.20 | **Decisive positive.** Component B steers even the weaker instruction-follower — stress-test survival. Ship the result. | No |
| 0.05 ≤ delta < 0.20 | Ambiguous zone | Yes — run phase-2b on pro |
| delta < 0.05 | Either Component B is a dashboard OR flash ignored the void constraint block (§9 original concern) | Yes — run phase-2b on pro to disambiguate |

**Asymmetric evidentiary weight.** A positive delta on flash is *stronger* evidence than the same delta on pro would be, because flash's weaker instruction-following raises the bar for any steering effect to show through. A null delta on flash is *weaker* evidence than the same null on pro would be, because of the instruction-following confound. The phased design exploits this asymmetry: flash is a cheap discriminator that settles the cleanest case at lowest cost, and pro is reserved for the expensive-but-necessary disambiguation when the signal is weak.

**Mandatory compliance check (non-negotiable addition).** Before interpreting any phase-2a delta, run a grep on the treatment arm's last mutator prompt debug log (`projects/gp045_cold_residual_01_ab_treatment/last_prompt_debug.txt` or equivalent) for the text of the Run-1 void constraint. This proves flash was *shown* the injection (distinct from "flash acted on it"). If the compliance grep fails — the constraint block is not rendered in the prompt sent to flash — phase-2a is uninterpretable regardless of delta and phase-2b on pro is mandatory. This check was optional under the original §9; under the amendment it is a hard gate.

**Updated locked invocation flags (phase-2a, identical across arms except the single axis):**

```
--project gp045_cold_residual_01_ab_{treatment|control}
--rubric gp045_cold_residual_01
--iters 10
--mutator_model gemini
--judge_model gemini
--no_model_fallback
```

**What remains unchanged.** Target project, iteration budget, rubric, clone directory convention, measurement extraction (§4.3), primary metric (§4.4), success criteria for H-STEER-01, and the sequential-run constraint. Only the model pinning and the conditional phase-2b trigger are amended.

**Accountability.** If phase-2a flash returns a decisive positive and phase-2b pro is skipped, the write-up must explicitly note that the measurement was taken on flash, and must frame the result as "Component B steering survives under the weaker model" rather than "Component B steering on gemini-pro" — do not mix the generalization claim.

---

## 10. Cross-references

- `GP-061_void_driven_steering_measurement_seam.md` — phase-1 baseline + protocol frame
- `src/ztare/validator/gp061_retro_steering_baseline.py` — phase-1 runnable
- `insights_ledger.md#INS-011` — the nesting-collapse pathology (independent question)
- `src/ztare/validator/autoresearch_loop.py:1013-1051` — Component B post-eval hook
- `src/ztare/validator/derived_constraints.py:179-252` — `seen_count_runs` promotion path (the mechanism that gates injection from run 2 onward)
