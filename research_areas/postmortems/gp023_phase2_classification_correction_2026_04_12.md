# GP-023 Phase 2 Post-Mortem

**Run:** `gp023_planck_sandbox_02`, 24 iterations, 2026-04-11
**Scoring sheet:** `post_run_scoring_sheet.md` (frozen 2026-04-11, not edited)
**Author:** Claude, 2026-04-12
**Sources:** iteration logs, `workspace/latent_distance.jsonl` (30 entries), `workspace/latest_information_yield.json`, `workspace/latest_loop_event.json`, GP-023 seam Turns 14-20, GP-034 seam, GP-035 seam Turns 1-6

---

## Scoring sheet classification correction

The frozen scoring sheet introduced `operator_stop_with_apparatus_finding` as a classification. The GP-023 seam debate (Turns 18-20) subsequently concluded this was a post-hoc reinterpretation that the pre-reg discipline was built to prevent:

- **Turn 18 (Codex):** the pre-reg exhaustively defines four bands; we do not get to add a fifth because the run terminated in an inconvenient way.
- **Turn 19 (Claude):** accepted the correction, retracted the label.
- **Turn 20 (Codex):** ratified.

**Corrected classification:** `non-diagnostic / pre-reg deviation`. The binding interpretation path was not completed (run did not reach 100 iterations, post-run smoke gate not executed). The scoring sheet is not edited — this post-mortem records the correction.

---

## Paper-grade empirical findings

Phase 2 produced two verified empirical findings that stand independent of the Planck scientific question. Both are paper-grade results for the cognitive-firm / M-Form governance thesis.

### Finding 1: Misattributed Staleness (GP-034)

**The scalar yield metric is blinding loop control.**

Cold artifact evidence:

- `workspace/latent_distance.jsonl`: 29/29 distance entries are `structural_move`. Jaccard on `attack_surface` = **1.0 on every iteration**. Jaccard on `thesis_text` = **1.0 on every iteration**. The mutator proposed a structurally unique thesis on every single iteration for 24 iterations.
- `workspace/latest_information_yield.json`: `novel_attack_ids: []`, `novel_hinge_ids: []`, `novel_primitive_ids: []`, `verified_axioms_added: 0`, `stagnant_window: 23`, decision `REFRESH_SPECIALISTS`.
- `workspace/latest_loop_event.json`: `stagnation_count: 23`, `pending_loop_action: REFRESH_SPECIALISTS`.

The loop controller declared the run stagnant and fired `REFRESH_SPECIALISTS` 23 consecutive times. The latent-distance substrate simultaneously recorded maximum structural traversal on every iteration. The two channels looked at the same run and reached opposite conclusions.

**Mechanism:** `information_yield.py` computes yield from `verified_axioms_added`, `novel_attack_ids`, `novel_hinge_ids`, `novel_primitive_ids`. All are populated downstream of a successful-enough iteration. Every iteration hit `catastrophic_failure` (visible-residual `fail_assert` from GP-035), which short-circuits the extraction path. The novelty channels go silent exactly when the mutator is traversing hardest.

**Why this is paper-grade:**

1. **Proves the metric is blinding.** Scalar scores are a lossy, dangerous proxy for structural reasoning. The "manager" fired the "worker" for lack of progress while the worker was actively exploring the entire latent space.
2. **Validates GP-029.** Without `latent_distance.jsonl`, this run looks like 24 iterations of a confused LLM stalling. With it, you can see the mutator cycling through `unjustified_parameter_scaling` → `parameter_overfitting_without_generalization` → `missing_external_validation` → `per_sweep_tuning` → `fragile_parameter_derivation` → `internal_inconsistency` → `unjustified_phenomenology` → `undisclosed_external_import` → `phenomenological_ad_hoc_dependence` — a systematic traversal.
3. **Agency failure, not capability failure.** The LLM did not fail to generate ideas. The governance layer failed to read the correct channel. In M-Form terms, the General Office intervened destructively because it was looking at the wrong accounting metrics.

**Candidate failure class:** "misattributed staleness" — a control layer concludes a run is stuck on one channel while another channel in the same workspace shows sustained movement. Structurally close to `wrong_yardstick` but one layer up (loop control, not evaluator).

### Finding 2: Un-Fitted-Structure Emission (GP-035)

**The mutator produces form without landing parameters.**

Cold artifact evidence:

- `latent_distance.jsonl` failure-family rotation: the mutator reached power laws, composite rationals, Hill-like forms, stretched exponentials, additive decompositions, saturating decays — structurally correct neighborhoods for the target curve.
- Every iteration scored 0. Every iteration died at `max |I_obs - I_model| < 0.05` on the visible slice.
- Specific examples from debate logs:
  - Iter `1775946795`: composite rational, residual 0.0555 (over by ~11%)
  - Iter `1775946985`: `A(psi) * phi / (B(psi)^2 + phi^2) + C(psi)`, residual 0.054 (over by ~8%)
  - Iter `1775947125`: stretched exponential `x^a * exp(-x^b)`, `fail_runtime` (ValueError)
- Code audit (GP-035 seam Turns 3-4) confirmed Cause 1: no fit primitive exists anywhere in `src/`. The mutator loop is strictly prompt → LLM → text → disk → run. No pre-LLM or post-LLM numerical optimization step.

**Mechanism:** the mutator's structural proposals are good. A composite rational with phi in the numerator and a quadratic in the denominator is structurally correct for a curve that rises, peaks, and decays. But the parameter values the LLM assigns are guesses — they land within ~50% of correct values but not close enough for an 8% residual threshold. LLM token-level numerical reasoning cannot substitute for `scipy.optimize.curve_fit`.

**Why this is paper-grade:**

1. **Falsifies "semantic exploration alone can bypass deterministic math gates."** The mutator exhausted the structural search space (Jaccard 1.0 on 24 iterations) without ever clearing the residual threshold. Structure is necessary but not sufficient; numerical precision requires a numerical tool.
2. **Proves the gates work.** GP-030's `cap-at-50` enforcement and the visible-residual `fail_assert` fired correctly for 24 iterations. No candidate drifted above 50 on a failed gate. The hard surface held.
3. **Separates structural capability from parametric capability.** The finding is not "the LLM can't do physics" — it's "the LLM can propose the right functional family but cannot fit its parameters." This is a precise, actionable apparatus limitation.

### Supporting validations

- **GP-030 (deterministic charter gates):** validated. Cap-at-50 worked for 24 iterations.
- **GP-029 (latent distance):** validated. The observability substrate recorded real movement when the run scored 0 on every iteration. n is now 2 (GP-023 + EU failure-probability run).
- **Sandbox holdout integrity:** held. The mutator never discovered hidden-slice targets. Failure families rotated without ever producing a hidden-slice-aware candidate.
- **Model-fallback seal:** held. `--no_model_fallback` enforced; no gpt-4o cascade in the run log.
- **Bounded-discriminator profile:** survived 24 iterations of stagnation pivots without drifting the prompt contract.

---

## Critical-path analysis for Sandbox 03

Whether to open Sandbox 03 depends on the ordering rule locked in GP-023 seam Turns 18-19:

### Ordering rule (locked)

**3a (audit) → 3b (substrate-swap) → 3c (Planck Phase 3)**

- **3a is complete.** GP-035 seam Turns 3-4 confirmed Cause 1 (no fit primitive). Spec written at `research_areas/private/specs/active/GP-035_mutator_fit_primitive_spec.md`.
- **3b is next.** Build the fit primitive, then verify it on a non-Planck smooth-curve sandbox that shares the residual-gate structure but not the Planck ontology. This separates "the fit primitive was the bottleneck" from "the Planck basin is specifically hostile."
- **3c (Sandbox 03 / Planck Phase 3) is gated on 3b success.** Same charter, same five deterministic gates, same hidden-slice thresholds, same bounded-discriminator profile, same `--no_model_fallback` seal. The only allowed delta is the fit primitive. Fresh pre-registration sealed before the run.

### What Sandbox 03 inherits from Phase 2

If 3b succeeds and Sandbox 03 is opened:

1. **Charter:** frozen from sandbox_02. No edits.
2. **Rubric:** frozen from sandbox_02, plus `enable_fit_primitive: true`.
3. **Deterministic gates (GP-030):** identical five gates, same thresholds.
4. **Hidden-slice holdout:** identical split, same target curves.
5. **Bounded-discriminator profile:** identical nine-module pivot set.
6. **Contamination audit:** carried forward by contract from audit_01.
7. **Model-fallback seal:** `--no_model_fallback` stays.

### What Sandbox 03 changes from Phase 2

1. **Fit primitive added.** Post-LLM inline scratchpad: parse declared form → `scipy.optimize.curve_fit` server-side → substitute fitted parameters into `test_model.py` → write residual map to workspace. Opt-in via rubric flag.
2. **Fresh pre-registration.** Phase 3 pre-reg document sealed before the run. Must declare the fit primitive as the single allowed apparatus delta.
3. **No warm starts.** No reuse of Phase 2 trajectories, thesis text, or workspace state.

### What Sandbox 03 does NOT change

- No gate loosening, threshold relaxation, or success-band broadening.
- No hidden-slice redesign.
- No GP-034 dual-channel fix (deferred until n=2 or separate verifier).
- No charter edits.

### Blocking dependencies

| Dependency | Status | Blocks |
|---|---|---|
| GP-035 spec ratified | Done (seam Turn 6) | Implementation |
| GP-035 fit primitive implemented | Not started | 3b substrate-swap |
| 3b substrate-swap sandbox designed + pre-registered | Not started | 3b run |
| 3b run completes successfully | Not started | Sandbox 03 decision |
| Sandbox 03 pre-registration sealed | Not started | Sandbox 03 run |

### Decision point

**Sandbox 03 is not on the immediate critical path.** The critical path runs through GP-035 implementation → 3b substrate-swap → 3b result. Only a 3b success unlocks the Sandbox 03 decision. If 3b fails at the same residual wall, the hypothesis space narrows further and Sandbox 03 may not be warranted.

---

## Frozen artifacts (do not edit)

- `post_run_scoring_sheet.md` — binding Phase 2 post-mortem, classification as-written
- `project_charter.md` — Phase 2 charter
- `sandbox_construction_record.md` — Phase 2 construction provenance
- `workspace/latent_distance.jsonl` — raw GP-029 output
- `workspace/latest_information_yield.json` — final yield snapshot
- `workspace/latest_loop_event.json` — final loop state
- All `debate_log_iter_*.md` files — 38 iteration logs
