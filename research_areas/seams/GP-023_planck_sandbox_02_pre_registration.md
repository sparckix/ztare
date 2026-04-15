# GP-023 Planck Sandbox 02 — Phase 2 Pre-Registration

## Status

Drafted 2026-04-11. **Sealed 2026-04-11 15:13 EDT** pending operator invocation of the Stage 1 smoke run.

This pre-registration is a fresh document for Phase 2. The Phase 1 pre-registration at `research_areas/private/seams/GP-023_planck_pre_registration.md` covered sandbox_01 and is now frozen as historical record; it remains on disk for audit. This file supersedes it for anything that touches sandbox_02.

Phase 2 preconditions (all must be verified before seal):

- GP-030 first slice shipped: deterministic-charter-gate schema parser, gate evaluator, `finalize_deterministic_score` integration, cap-at-50 policy on gate failure, fixture regression green. **Verified 2026-04-11 by Codex Turn 11:** `src/ztare/validator/test_thesis.py:1847-1862` invokes `evaluate_deterministic_charter_gates(...)` and `src/ztare/validator/deterministic_charter_gates.py:56` defines `GATE_FAILURE_SCORE_CAP = 50`. Cap is live in code.
- Sandbox rebuilt with asymmetric data holdout: `projects/gp023_planck_sandbox_02/` (construction record at `projects/gp023_planck_sandbox_02/sandbox_construction_record.md`).
- `test_model.py` exposes both invocation modes (default assertion suite and `--emit-deterministic-gates`) and the gate payload JSON shape is stable.
- Pre-run harness smoke-check in place (see §Harness Smoke Gate below) — script at `projects/gp023_planck_sandbox_02/harness_smoke_gate.py`, verified green against current seed 2026-04-11.
- Contamination audit 01 (gpt-4o checker, 2026-04-10, verdict PASS with wrong-retrieval-basin top guess) is **carried forward by contract** as the sandbox_02 contamination posture. This is the one explicit choice this pre-reg makes on the audit question (closes Codex Turn 11's internal-inconsistency correction): audit 01 is sufficient because sandbox_02 inherits the sandbox_01 generating model, rename map, and perturbations verbatim per construction record §2, and the visible slice of sandbox_02 is a strict subset of the sandbox_01 evidence grid — no new curve shape, no new retrieval surface. A fresh audit 02 is NOT required for seal and NOT required for the run to be valid.

## Purpose

This document freezes the Phase 2 evaluation contract before the main run. It exists to close the five Phase 1 failure modes documented in Codex's 2026-04-11 review:

1. Pre-reg ↔ charter success mismatch (Phase 1 pre-reg accepted novelty criteria; charter demanded a hard residual gate; the score-95 champion admitted it failed the gate).
2. Raw-LLM-score rewarded criterion reinterpretation rather than literal charter enforcement.
3. Run-state interpretation was ambiguous (champion vs latest vs completed-run was not pre-registered).
4. Harness robustness was a live risk (iter-32 IndexError collapsed candidates to score 6 mid-run).
5. Output record did not include a dedicated scoring sheet against the pre-reg.

Items 1 and 2 are structurally closed by sandbox_02's Deterministic Gates block bound to the hidden slice via `--deterministic_score_gates`. Items 3, 4, and 5 are closed by this pre-registration.

## Experiment Object

Unchanged from Phase 1. Test whether ZTARE can generate a structurally novel primitive through sustained adversarial blockade, starvation under repeated failure, orthogonal-shock prompt pressure, and anchor-proxy filtering, without retrieving the historical answer from pretraining.

Source inspiration: Planck-style pattern — old vocabulary fails under hard empirical constraint, a previously illegal composition appears, the composition survives because it anchors to the curve.

The experiment is not "did the model rediscover Planck." The experiment is "can the mechanism fire at all under a contamination-controlled setup with deterministic charter enforcement."

## Primary Hypothesis

Unchanged from Phase 1. Under a contamination-controlled isomorphic sandbox with hidden-slice generalization enforcement, a ZTARE run with sustained blockade plus repeated `bounded_discriminator` pivot pressure can produce a structurally novel composite primitive that (1) was not explicitly present in the seed artifact, (2) is argued into existence through renamed-variable reasoning, and (3) survives anchor-proxy demand against the perturbed target curve *and* generalizes to the 10-point-per-sweep hidden holdout.

## Null Hypothesis

Under the same conditions, the run will do one of:

- retrieve the historical solution shape directly
- cycle through existing failure families
- produce only ad hoc patches that pass the visible slice but fail the hidden-slice gates
- produce a visible-slice fit without a structurally novel composite primitive
- fail to produce a structurally novel composite primitive at all

## Pre-Registered Controls

Inherited verbatim from Phase 1 pre-reg §Pre-Registered Controls (semantic retrieval control, mathematical-form control, data-shape control, prompt telegraphing control, operator contamination control). Sandbox_02 reuses the sandbox_01 generating model, rename map, and perturbations, so the contamination surface is unchanged modulo the visible/hidden split.

## Independent Contamination Check

Sandbox_02 inherits sandbox_01's contamination audit 01 **by contract** (gpt-4o checker, verdict PASS, 2026-04-10, forensic probe top guess = "driven harmonic oscillator / RLC resonance" = wrong retrieval basin; audit log at `research_areas/private/gp023_contamination_audit_01.md`).

No fresh audit 02 is required for Phase 2 seal or for the main run to be valid. The justification is that sandbox_02's visible slice is a strict subset of sandbox_01's evidence grid (the holdout split removes 10 of 40 phi points per sweep; no new points are added, no curve shape is changed, no rename-map element is altered), so any contamination that audit 01 did not surface on the full 40-point set cannot appear on the 30-point subset. The holdout file itself is never sent to an external model and is therefore out of scope for any audit.

This clause supersedes any earlier wording in this file about audit 02 being "recommended" or "pending." It is the single binding answer on the audit question. Closes Codex Turn 11 internal-inconsistency correction.

## Pre-Registered Runtime

**Execution plan: two-stage smoke + main.** Phase 2 runs in two stages, in order. Stage 1 is a 25-iteration smoke run whose sole purpose is to verify that `--deterministic_score_gates` actually exercises inside a live autoresearch_loop iteration against a real mutated candidate — the harness smoke gate only verifies the contract on the seed *before* the loop starts, not that the cap-at-50 fires mid-run on a bad candidate. Stage 1 is **below the 30-iteration binding floor** defined below and therefore *cannot* produce a Phase 2 result under any circumstance; it is definitionally non-diagnostic for scoring. Stage 2 is the 100-iteration main run, invoked only after Stage 1 passes the smoke-exit checks named below. Stage 1 is a pre-registered precondition to Stage 2.

**Stage 1 smoke-exit checks** (all four must hold for Stage 2 to be invoked; any failure aborts Phase 2 pending operator review):

1. Loop exited cleanly at iteration 25 (no `fail_runtime` terminal exception, no provider cascade).
2. At least one iteration shows the GP-030 deterministic-gate evaluation path actually running (visible in the iteration telemetry). Specifically: at least one candidate must have had its gate payload computed, whether or not any gate passed. "Gates never evaluated" is a Stage-1 failure even if the loop exited at 25 cleanly.
3. The three startup banners present in the run log: `🔒 Model fallback DISABLED`, deterministic-gate enablement banner (exact text to be recorded during Stage 1), and the `SMOKE GATE PASS` line from the pre-run harness smoke gate.
4. No gpt-4o / OpenAI-family model appears anywhere in the run log (provider cascade would silently hand the run to the burned contamination checker; `--no_model_fallback` should prevent this but the log is the verifier).

**Stage 2 main-run budget:**

- 100 iterations minimum.
- Do not stop on the first `0`.
- Do not stop on early stagnation unless the run becomes technically invalid.
- Early stop permitted only if the GP-030 deterministic gates pass on a `champion` thesis AND the champion satisfies all three success criteria below AND at least 30 iterations have been completed. The 30-iteration floor exists so a Phase-1-style iter-4 early champion cannot short-circuit the run.

Mutator/judge family:

- Sealed at seal time. Phase 2 default: same as Phase 1 (Gemini `gemini-2.5-flash`), unless an explicit family switch is recorded in the seal section.
- Same-family contamination checker (gpt-4o / OpenAI) remains forbidden as runtime.

Pivot regime:

- `bounded_discriminator` profile, GP-021 Phase 1.5 expanded module set.
- No domain-specific heuristic hints beyond the registered profile.

Required flags (all three are mandatory; absence of any one invalidates the run):

- `--deterministic_score_gates` (GP-030 enforcement — the load-bearing addition vs Phase 1).
- `--underidentified_after 100` (match iteration budget to suppress the 3-iter UNDERIDENTIFIED exit that preempted Phase 1 pivots).
- `--no_model_fallback` (model-family seal — prevents silent cascade to the burned contamination checker via `llm_runtime.FALLBACK_MODEL_CHAINS`).

A valid Phase 2 run must show all three of:

- `🔒 Model fallback DISABLED` banner at startup
- `🔒 Deterministic score gates ENABLED` banner (or equivalent — name to be confirmed at seal time against the actual autoresearch_loop output)
- The harness smoke-gate PASS line (see below)

## Harness Smoke Gate (Phase 2 addition)

Before the main loop begins, the runner must execute a sealed smoke-check on the seed thesis as shipped in `projects/gp023_planck_sandbox_02/test_model.py`:

1. `python projects/gp023_planck_sandbox_02/test_model.py` → must exit non-zero (the naive seed power law is expected to fail the visible-slice assertion suite — this confirms the assertion path is live). Any exit-zero at this stage means the seed is not actually naive and the sandbox is mis-built; fail the run.
2. `python projects/gp023_planck_sandbox_02/test_model.py --emit-deterministic-gates` → must exit zero AND stdout must parse as `{"gates": [...]}` with exactly the five gate entries named in the charter's Deterministic Gates block (`hidden_global_residual`, `hidden_peak_location_psi_0_60`, `hidden_peak_location_psi_1_00`, `hidden_peak_location_psi_1_80`, `hidden_high_phi_decay_ratio`). Any non-zero exit, any malformed JSON, or any missing gate entry fails the run before it starts.
3. The five gate entries on the naive seed are expected to all report `passed: false` with finite `actual` values (the seed is monotonic in phi, so peak-location errors will be large but not infinite; residual errors will be large but not infinite). Any `actual: null` (infinity or NaN) on the seed smoke-check indicates a numerical pathology in the harness path and fails the run.

The smoke gate exists because sandbox_02 moves harness correctness from a passive property ("the harness probably works") into the experiment contract ("the harness is part of the scoring path"). A harness bug during a live run would now collapse candidates to fail-closed cap-50 at every iteration, producing a false-negative that looks identical to a real failed run. The pre-run smoke-check closes this by verifying the harness end-to-end before mutation begins.

Operator executes the smoke gate by hand before invoking the run command, or the run command wraps it — either is acceptable as long as the smoke-gate output is preserved in the run log.

## Run-State Binding (Phase 2 addition)

This section closes Codex's Finding #3. It names, before the run, which artifact binds for interpretation.

**Primary binding artifact:** `projects/gp023_planck_sandbox_02/champion_eval_results.json` **conditional on the champion passing all five deterministic gates**.

**Interpretation rule:**

1. Run completes (100 iterations OR valid early stop per §Pre-Registered Runtime).
2. Load `champion_eval_results.json`. If no champion file exists → outcome is `invalid` (the run produced no scored candidate).
3. Re-run the harness smoke gate a second time (post-run) against the champion's `test_model.py` (the mutator-rewritten version, not the seed). All three smoke-gate checks must pass, except that step 3 (the "seed smoke check") is replaced with: the five deterministic gates may return any boolean, but all five `actual` values must be finite. Any `null`/infinity value → outcome is `invalid` (harness collapse on champion).
4. If post-run smoke check passes: load the five deterministic-gate results for the champion thesis.
5. **Success band:** champion scored ≥ 85 by the judge AND all five deterministic gates returned `passed: true` AND the `Mechanical Trace Rule` below is satisfied on the champion thesis (≥ 3 intermediate reasoning steps over renamed variables, final composite primitive derivable without unexplained jump).
6. **Strong-partial band:** champion scored ≥ 70 AND at least 4 of 5 deterministic gates returned `passed: true` AND the Mechanical Trace Rule is satisfied. This band exists so Phase 1's actual result (a thesis that was structurally interesting but failed one gate) has a place to land honestly, rather than being forced into the binary success/failure partition.
7. **Failure band:** anything else, including score ≥ 85 with ≥ 1 failed gate (this is the exact Phase 1 pathology the sandbox is built to reject).
8. **Invalid band:** any of the invalidation conditions above (no champion, post-run harness collapse, smoke-gate failure).

Explicitly rejected bindings (so there is no ambiguity at post-mortem time):

- `latest_eval_results.json` — rejected. The Phase 1 confusion had latest regressing after the score-95 champion; binding to `latest` would have rewarded the collapse. Latest is used only for monitoring, not interpretation.
- Any specific iteration number (e.g., "iter 4 champion") — rejected. Binding to an iteration pre-commits to a specific trajectory shape that cannot be known before the run.
- A manually-selected "best" thesis at post-mortem — rejected. Post-hoc selection is the exact operator-contamination failure this pre-reg exists to prevent.

**Tie-breaking across multiple champions:** the loop preserves one champion at a time (the highest-scoring thesis seen so far), so the binding is unambiguous at loop exit. If the champion file is overwritten by a regression event (later thesis with equal or higher score but failing gates), the pre-reg binds to whatever champion_eval_results.json contains at the moment of loop exit. This is a known failure mode and is accepted deliberately: the deterministic gates are the guardrail against regression-as-champion, not a separate mechanism.

## Success Criteria

The run counts as a positive GP-023 Phase 2 result only if all three of the Phase 1 criteria hold (novel composite primitive, anchor-proxy bridge, trace emergence) AND the champion binds to the Success band in §Run-State Binding.

## Failure Criteria

The run counts as a negative GP-023 Phase 2 result if:

- The run completes (100 iterations or valid early stop) AND
- The sandbox is uncontaminated AND
- The post-run harness smoke check passes AND
- The champion does not bind to the Success band.

Negative Phase 2 includes the strong-partial band explicitly: a strong partial is a valid negative result for the Planck mechanism on this sandbox, not a non-result. The distinction between Phase 1's n=0 non-diagnostic outcome and a Phase 2 strong partial is that a strong partial *did* exercise the full run under correct enforcement, so the null was actually tested.

## Invalid / Non-Diagnostic Outcomes

Unchanged from Phase 1, plus:

- Pre-run harness smoke-gate failure → `invalid` (sandbox mis-built or harness broken; rebuild before any run counts).
- Post-run harness smoke-gate failure (champion harness collapsed) → `invalid` (mid-run harness degradation; recorded in the scoring sheet).
- Missing champion file → `invalid`.
- Any of the three required flags (`--deterministic_score_gates`, `--underidentified_after 100`, `--no_model_fallback`) missing from the run log → `invalid` (the run did not execute under the pre-registered contract).

Handling rule: classify as `invalid`, do not silently upgrade to partial, and do not re-interpret.

## Mechanical Trace Rule

Unchanged from Phase 1:

- at least 3 explicit intermediate reasoning steps
- each step references renamed variables or renamed observables from the seed
- the final primitive is derivable from those steps without an unexplained jump

## Output Record

A valid GP-023 Phase 2 run must preserve:

- full debate logs (`projects/gp023_planck_sandbox_02/debate_log_iter_*.md`)
- final thesis (`projects/gp023_planck_sandbox_02/thesis.md`)
- final falsification suite (`projects/gp023_planck_sandbox_02/test_model.py`)
- contamination-check record (either carried forward from audit 01 with an explicit reference, or a fresh audit 02 record at `research_areas/private/gp023_contamination_audit_02.md`)
- champion file (`projects/gp023_planck_sandbox_02/champion_eval_results.json`)
- pre-run and post-run harness smoke-gate output (appended to the run log)
- **Scoring sheet against this pre-registration** (Phase 2 addition — closes Codex Finding #5) — a dedicated markdown file at `projects/gp023_planck_sandbox_02/post_run_scoring_sheet.md`, written by the operator at post-mortem time, structured as a checklist against each numbered success/failure criterion in this pre-reg with pass/fail/invalid verdicts and the evidence path for each. A run without this file counts as `output_record_incomplete` rather than a clean Phase 2 result.

## Seal

**Sealed 2026-04-11 15:13 EDT.** All seal preconditions verified. Operator may now invoke Stage 1.

### Sealed values

- **Seal date:** 2026-04-11 15:13 EDT
- **Runtime mutator family:** Gemini `gemini-2.5-flash` (via `MODEL_MAP["gemini"]`) — unchanged from Phase 1 seal block. Operator confirmed 2026-04-11. Rationale: Phase 2 tests the gate-enforcement variable only; holding the runtime family constant against Phase 1 is required to keep `--deterministic_score_gates` as the single changed variable.
- **Runtime judge family:** Gemini `gemini-2.5-flash` — same as mutator, same rationale.
- **Forbidden as runtime:** gpt-4o / OpenAI family (burned as Phase 1 contamination checker; independence would be violated). Enforced by `--no_model_fallback`.
- **Pre-run harness smoke gate result:** PASS at 2026-04-11 15:13:49 EDT on `projects/gp023_planck_sandbox_02/test_model.py`. All three contracts verified: (C1) default mode exits non-zero on the naive seed (exit 1); (C2) `--emit-deterministic-gates` emits well-formed JSON with exactly the five charter-declared gate entries; (C3) every gate's `actual` field is finite and 5/5 gates fail as expected on the monotonic power-law seed. Script: `projects/gp023_planck_sandbox_02/harness_smoke_gate.py`.
- **Contamination audit posture:** audit 01 carried forward by contract (see §Independent Contamination Check). No audit 02 required. Audit 01 log at `research_areas/private/gp023_contamination_audit_01.md`. Verdict: PASS (gpt-4o checker, 2026-04-10, forensic probe top guess = "driven harmonic oscillator / RLC resonance" = wrong retrieval basin).
- **GP-030 ship verification:** live. `src/ztare/validator/deterministic_charter_gates.py:56` defines `GATE_FAILURE_SCORE_CAP = 50`; `src/ztare/validator/test_thesis.py:1847-1862` invokes `evaluate_deterministic_charter_gates(...)`. Verified by Codex Turn 11 and spot-checked by Claude Turn 12 in the GP-023 seam.

### Sealed run commands (copy-pasteable)

**Stage 1 — 25-iter smoke run.** Invoke first. Do NOT invoke Stage 2 until the four smoke-exit checks in §Pre-Registered Runtime pass.

```
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_02 \
    --rubric rubrics/gp023_planck_sandbox_02.json \
    --iters 25 \
    --deterministic_score_gates \
    --underidentified_after 100 \
    --no_model_fallback
```

**Stage 2 — 100-iter main run.** Invoke only after Stage 1 passes the smoke-exit checks. This is the binding Phase 2 run.

```
python -m src.ztare.validator.autoresearch_loop \
    --project gp023_planck_sandbox_02 \
    --rubric rubrics/gp023_planck_sandbox_02.json \
    --iters 100 \
    --deterministic_score_gates \
    --underidentified_after 100 \
    --no_model_fallback
```

**Pre-run smoke gate (must be re-run immediately before each stage):**

```
python projects/gp023_planck_sandbox_02/harness_smoke_gate.py
```

Exit 0 = PASS, proceed. Any non-zero exit = sandbox is not ready; fix and re-run.

### Post-seal amendment policy

Once sealed, this pre-registration may be amended only by:
- Adding post-run material in §Post-Run Scoring Sheet section (expected).
- Recording new status updates in §Status (expected).
- Correcting factual errors with an explicit amendment note citing date and reason. **Substantive scoring-rule changes after seal are NOT permitted** and would invalidate the Phase 2 result under the pre-reg's own "post-hoc reinterpretation" clause.
- Run command (exact, copy-pasteable) will be pasted here at seal time

## What This Pre-Registration Does Not Decide

- the final seed_registry treatment of any Phase 2 finding (that is GP-031 / findings-birth bridge territory)
- whether Phase 2 positive generalizes beyond this one sandbox (that is a Phase 3 question, explicitly out of scope)
- whether GP-030's cap-at-50 policy needs adjustment post-Phase-2 (that is a GP-030 post-mortem question)

Those are spec-level or post-run interpretation questions, not things to improvise mid-run.
