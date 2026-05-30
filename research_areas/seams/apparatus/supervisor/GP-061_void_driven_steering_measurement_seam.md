# GP-061 Component B — Void-Driven Proposal Steering Measurement (seam)

> **Seam metadata** · `seam_id:` GP-061 · `track:` apparatus · `status:` DRAFT 2026-04-15. Seam-stage under AGENTS.md §spec-format. N · `last_updated:` 2026-05-08


**Status:** DRAFT 2026-04-15. Seam-stage under AGENTS.md §spec-format. Not a spec.
**Purpose:** Tier-2 generalization ladder for Component B. Cold-run and R3b/R4 establish only that the detector's vocabulary is stable and grep-verifiable. They do not establish that the mutator's next proposal is actually *shaped* by void injection. This seam defines the measurement that closes that gap.

---

## The gap

What Component B emits today: a `negative_space_blind_spot` provisional constraint listing `fn:*|arg*|has_op:*` voids, rendered into the mutator prompt via the existing `derived_constraints.json` → confirmed-bucket promotion path (`seen_count_runs ≥ 2`).

What we have not measured: whether the mutator's next proposal actually fills a previously-void slot at a rate higher than chance, conditional on void injection. Every capability claim above this point has been about detector behavior in isolation. The closed-loop claim — "Component B changes what the mutator tries" — is unverified.

If this gap is not closed, Component B is a faithful detector of coverage holes that has no demonstrated effect on search. That is still useful as apparatus (an auditor's dashboard) but does not justify the "Generalized Falsification Engine" framing.

## The measurement

**Protocol.** On a live autoresearch run against a fit-primitive project that has produced ≥ 1 void emission and had it promoted to confirmed:

1. Record the pre-injection feature-bag matrix at iteration *k* (the iteration after void emission, before mutator call).
2. Run one iteration with the constraint injected.
3. Parse the mutator's proposed `family_label` and compute its feature bag.
4. Check whether the proposed bag intersects the void set at the `(fn, arg_pos, has_op)` key level.

**Control.** Same project, same prior iterations, re-run with `--disable-negative-space-extractor`. Mutator sees the same process/compliance constraints but no void injection. Record its proposal's feature bag.

**Metric.** `P(void_filled | injection) − P(void_filled | no injection)`, over N ≥ 10 paired iterations across ≥ 2 projects. The effect size must exceed chance under a one-sided binomial test (α = 0.05) to claim steering.

**Null result is informative.** If the mutator ignores void injection at chance rate, that is publishable — it means Component B is an audit layer, not a search-shaping layer, and the prompt injection surface needs redesign. That is a real finding, not a failure.

## Why this is tier 2

Tier 1 (R3b + R4): detector behavior is stable across corpora and grammars (curated).
Tier 2 (this seam): detector output has measurable effect on the search loop.
Tier 3 (GP-069-cleared live-mutator target): detector operates inside a live search loop without the identifiability/nesting pathology.

Tier 2 is achievable **now** on any Planck-grammar project — it does not require the GP-069-cleared target from task #55. The effect measurement is independent of whether the search loop is cross-grammar.

## Open questions

1. Which pair of projects to use for the paired-run measurement? gp042 and gp045 are candidates — both are fit-primitive, both have non-trivial structural_memory, neither has Component B emission in its historical ledger, so the re-run is a first-emission.
2. How to hold everything except void injection constant under a re-run? Mutator temperature + seed are already fixed in autoresearch_loop; confirm. The confirmed-bucket promotion gate (`seen_count_runs ≥ 2`) means a single run's emission is provisional and not prompt-injected, so the measurement needs two consecutive runs or a temporary gate override for this experiment only (pre-registered, time-boxed).
3. What counts as "void filled" — exact slot match, or same `(fn, arg_pos)` key with any operator the mutator had not previously used? Exact slot is cleaner but may undercount steering; broader definition risks claiming steering for spurious slot changes.
4. Chance-rate baseline. Pure random slot selection from the filled-side operator catalog is an obvious null, but the mutator's prior distribution over operators is not uniform. The honest null is the mutator's own per-operator frequency observed in the no-injection control arm.

## Pre-decision

Do not build a specialized harness. The measurement runs on the existing autoresearch_loop with a short pre-reg doc, two paired runs, and a post-hoc feature-bag diff. No new code except the diff script (~50 lines).

---

## Phase 1 — Retrospective A-arm baseline (run 2026-04-15)

**Script:** `src/ztare/validator/gp061_retro_steering_baseline.py` (read-only, no LLM calls).

**Method.** Walk `structural_memory.json` for sandbox_07 and sandbox_08 by `first_seen_iteration`. At each iteration *k* where the corpus has ≥ 3 `structural_misfit` families at residual ≥ 0.15, run `detect_negative_space` to get the void set at dense `(fn, arg_pos)` keys. For each new family introduced at iteration *k+1*, compute its feature bag and check whether it fills any void slot at any key. Report observed fill rate vs per-key chance rate (`voids / universe`).

**Why this is the A arm.** Sandbox_07 and sandbox_08 closed before Component B existed, so the mutator at every iteration received zero void injection. The measurement on those runs is factually an A-arm observation under the original (no-injection) condition.

**Results:**

| Sandbox | Steps | Observed fill rate | Chance fill rate | Lift |
|---|---|---|---|---|
| sandbox_07 | 8 | 0.25 | 0.35 | −0.10 |
| sandbox_08 | 5 | 0.20 | 0.43 | −0.23 |

**Reading.** Both sandboxes show the mutator filling Component B's would-be void slots at a rate **below** random draw over the per-key universe. The mutator is not neutral on voids — it is actively anchored on the prior family as a template and perturbs locally, which keeps returning it to slots already filled in the corpus. Under this anchoring bias, voids accumulate not because the slots are hard, but because the mutator's local-perturbation prior does not reach them.

**What this implies for phase 2.** There is measurable headroom for Component B to close: the gap between observed (0.20–0.25) and chance (0.35–0.43) is the floor effect a minimally-useful steering signal would need to recover. If void injection moves the rate to chance or above, Component B is actually steering. If injection leaves the rate at the A-arm baseline, the detector is a dashboard — still useful as apparatus but not as a search modifier.

**Statistical caveats (decisive).**

1. N is small: 13 paired steps total across both sandboxes. 0.25 vs 0.35 with n=8 is not significant at α=0.05 under a one-sided binomial test (p ≈ 0.33). 0.20 vs 0.43 with n=5 is not significant either. **This is directional evidence, not a confirmed finding.** The honest claim is "the gap has the right sign and the right order of magnitude for phase 2 to be worth running."
2. Chance rate is computed per-key as (# voids at key) / (# universe at key), then averaged across keys the detector surfaced. A mutator drawing uniformly from the per-key universe would match this rate. The chance is not a uniform baseline over all operators — it is the baseline *conditional on the key the detector flagged as dense*.
3. The "any void filled" hit definition counts a new family as a hit if it touches any void at any dense key. Per-slot counting (sum over keys) would be slightly higher resolution but more volatile on N=13.
4. Both sandboxes are Planck-grammar. The baseline on a non-Planck corpus may differ, but the anchoring-bias phenomenon is grammar-agnostic in principle — it is a property of local-perturbation mutation strategy, not of exp/eml vocabulary.

**Phase 1 verdict.** Headroom exists. Phase 2 (live paired run with void injection) is worth running.

## Phase 2 — substrate pivot (2026-04-15, after GP-045 halt)

**What halted.** Phase 2 treatment run 1 against `gp045_cold_residual_01_ab_treatment` exited at 18:55 EDT with "no negative_space_extractor void." Root cause is not apparatus — it is target surface. The `gp045` structural memory after run 1 has 10 families: 9 at `best_visible_max_abs_residual` between 0.049 and 0.063, 1 at 3.45. The detector gate (`RESIDUAL_THRESHOLD_DEFAULT = 0.15` + `latest_diagnostic_classification == "structural_misfit"`, `negative_space_extractor.py:48-50`) cannot see any of the nine tight-fit families. The diagnostic-trigger gate upstream (`max_abs_residual > 0.10`, `autoresearch_loop.py:2768`) also does not fire on them. No trigger → no classification → no void emission. GP-045 is a criterion-driven **failure** surface, not a structurally-interesting one. It was the wrong phase-2 substrate from the start.

**Pivot: Hinge target under BIC-penalized scorer.** The right substrate is the GP-069-cleared Hinge target, because (a) it has a genuine structural kink the mutator cannot smooth-close away locally, (b) its failure modes produce residual patterns dense enough for the detector to see, and (c) under a complexity-penalized scorer, the nesting-collapse pathology that would have let the mutator escape into a sigmoid-limit approximation is closed.

**Does this change what we are trying to prove?** No. The core claim — "Component B void injection changes the mutator's next proposal at a rate above chance" — is preserved verbatim. Only the substrate changes. The measurement protocol, control arm, metric, and null-result interpretation from § "The measurement" above still apply. What changes is:
- **Target**: from GP-045 (continuous smooth physics, criterion-driven failure) → Hinge target (piecewise-linear, GP-069 level-1 cleared).
- **Scorer**: unregularized L2 → BIC-penalized cross-family ranking in structural memory. Without this, the Hinge target would itself be exploitable via smooth closure (GP-069 seam § sigmoid-limit probe).

**Blocking dependency: #65 (complexity-penalty wiring) — SHIPPED 2026-04-15.** The minimal scorer fix landed in `src/ztare/validator/structural_memory.py` as a rubric-flag gate (`rubric_data["complexity_penalty_enabled"] = true`). `structural_memory_fixture_regression.py::gp069_bic_flag_flips_hinge_vs_sigmoid_ordering` verifies cross-family ordering flips from sigmoid-first (flag off, L2) to hinge-first (flag on, BIC). `gp069_hinge_sigmoid_limit_probe.py` still reports ΔBIC = −3.30 / ΔAIC = −1.90 in favor of hinge under the same n=30, σ=0.02 conditions. Phase 2 is unblocked on the scorer side.

**Scope of #65 — what was NOT done.** BIC is only a partial patch per GP-069 seam §§ 109–119: it closes honestly-counted extra-parameter exploits (like the sigmoid τ in the probe) but does not close smuggled-parameter attacks (grid-scale τ-floor constants, bandwidth constants not counted in `k`). If phase 2 under Hinge+BIC still shows smooth-closure escape via smuggled parameters, the correct escalation per GP-069 §§ 127+ is a discrete-grader pilot (modular arithmetic grader, not continuing to patch BIC). Also, retroactive audit of sandbox_09 v2 / sandbox_10 under BIC is not informative as a scorer diff because both runs' winning families converged to residual ≈ 0 — the SSE term dominates BIC regardless. A true retroactive would need to walk `fit_result_iter_NNN.json` history per iteration and re-rank across candidates, which is a bigger undertaking and not blocking phase 2.

**Next concrete step.** Construct a Hinge target rubric that opts into `complexity_penalty_enabled: true`, pre-register the paired A/B protocol from § "The measurement" against it, then resume phase 2 from run 1. The Hinge target is also the first candidate to exercise task #55 (live-mutator-compatible GP-069-cleared target) — the two tasks share a substrate.

---

## Cross-references

- `GP-061_R4_retrospective_audit.md` — tier 1 evidence closed
- `GP-023_sandbox_10_post_run_audit.md` — tier 1 curated evidence
- `GP-061_constraint_accumulation_as_output_seam.md` — authorization status promoted 2026-04-15
- `src/ztare/validator/negative_space_extractor.py` — detector under measurement
- `src/ztare/validator/autoresearch_loop.py` L1013–1051 — live hook
