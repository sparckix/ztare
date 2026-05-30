# GP-062 Trajectory-Level Thrash Detection — Seam

> **Seam metadata** · `seam_id:` GP-062 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: open
Opened: 2026-04-14
Hypothesis family: H-ARCH-03 (cross-artifact reader over trajectory signal)
Parent: GP-061 (Constraint Accumulation as Scientific Output)

---

## Problem Statement

sandbox_07 contains a second hidden-in-plain-sight artifact next to `structural_memory.json`: `latent_distance.jsonl`. Across iterations 2..10, every per-iteration row reports `jaccard_failure_families=1.0`, `jaccard_attack_surface=1.0`, `jaccard_named_primitives=1.0`, `thesis_text_distance=1.0`, `motion_class="structural_move"`. The mutator is rewriting the thesis *completely* at the semantic surface each iteration. In parallel, `structural_memory.json` shows that the outer algebraic skeleton (`P0 * X0**P1 * X1**P2 [mul-or-div] eml(...) + P_const`) is preserved across all 12 families.

**Semantic orthogonality ≫ structural change = thrash.** The apparatus is burning iterations on candidates that look new to the prompt-level signature but have not moved at the structural level the score contract measures. `latent_distance.jsonl` is read once in `latent_distance.py` for a pivot heuristic prior; nothing reads it against `structural_memory.json` to compare the two distance axes. Same shape as GP-061: populated artifact, no cross-artifact consumer for the relevant signal axis.

---

## Retroactive Test Result (Premise Check Before Design)

Manual check against sandbox_07 closed artifacts:

| iter | jaccard(failure_fam, attack, primitives, thesis) | structural feature-bag delta |
|---|---|---|
| 2 | 1.0 / 1.0 / 1.0 / 1.0 | feature-bag identical on outer skeleton features (`var_power:X0`, `var_power:X1`, `has_eml_term`, `has_outer_additive_const`) |
| 3 | 1.0 / 1.0 / 1.0 / 1.0 | identical |
| 4 | 1.0 / 1.0 / 1.0 / 1.0 | identical |
| 5 | 1.0 / 1.0 / 1.0 / 1.0 | identical |
| ... | ... | identical |

Every iteration 2..10 satisfies `semantic_mean ≥ 0.8 AND structural_feature_bag_distance ≤ ε`. A trajectory-thrash detector would have fired on iteration 3 and emitted a constraint naming the specific preserved features. The existing `topological_pivot_profile_injected` loop event fired on pivot heuristics but did not name the preserved structural features — that naming is the decisive new signal.

Premise holds. Proceed to design.

---

## Peer Review of the "Veto-and-Retry" Proposal

A prior proposal (external, Gemini Pro) framed this as:

1. Detect thrash **before fit** by parsing the mutator output for structural features.
2. **Veto** the candidate if it looks structurally orthogonal to prior champions.
3. **Retry**: re-prompt the mutator in a tight inner loop with "VETO: you rewrote the thesis but kept the skeleton" until a structurally novel candidate is produced.

Four problems with that shape, stated harshly:

**1. Veto-before-fit inverts the signal flow.** The reliable structural features in sandbox_07 live in `structural_memory.json`, which is populated *by the fit pass*. Pre-fit, we would have to parse raw mutator text through a second fragile parser that duplicates the fit-primitive symbolic extraction. The fit is cheap (~seconds), the parser would be new code, and the detection quality would be strictly worse than reading the existing canonical artifact. **Rule from §6d: don't build a new signal injector when the signal is already in a workspace artifact.**

**2. Retry loops add an inner control loop.** A tight mutator-retry loop triples iteration cost when the mutator paraphrases instead of restructuring (the exact failure mode we're trying to detect). It also creates a new class of bug: "what if the mutator keeps producing veto'd candidates indefinitely." The existing sequential loop already has a retry channel: **the next iteration**. The detector's job is to arm that next iteration with a sharper constraint, not to mid-iteration-interrupt the current one.

**3. "Structurally orthogonal" is vague.** The proposal uses "structural orthogonality" as a rejection criterion without naming features. A rejection criterion that cannot be decomposed into a feature set cannot be stated as a "have-to-believe" positive inversion, which means it cannot be stored in `derived_constraints.json` in the format GP-061 just established. The detector has to name features.

**4. Falls into the man-with-a-hammer trap.** sandbox_08 hardcoded `_STRUCTURAL_MISFIT_HINT_TEMPLATE` as a bespoke mid-iteration signal injector. GP-061 replaced it with a cross-artifact reader that feeds the existing constraint channel. Veto-and-retry is another bespoke mid-iteration signal injector. Same anti-pattern, different channel. The correct move is to keep using the constraint channel GP-061 established and add another reader to it.

**What the proposal gets right.** The core insight — high semantic distance co-occurring with zero structural distance = thrash — is correct and decisive. The architectural shape around it is wrong.

---

## Proposed Architecture

**Shape:** cross-artifact reader over `latent_distance.jsonl` + `structural_memory.json`. Emits one constraint per fire into `derived_constraints.json` via the existing `update_derived_constraints_ledger` channel, tagged `producer="trajectory_extractor"`. No veto, no retry, no mutator interrupt. Runs in the same post-eval hook as the GP-061 structural extractor.

**Module:** `src/ztare/validator/trajectory_thrash_detector.py`

**Signal sources (both read-only):**

1. `workspace/latent_distance.jsonl` — per-iteration rows with `distances.jaccard_failure_families`, `distances.jaccard_attack_surface`, `distances.jaccard_named_primitives`, `distances.thesis_text_distance`. Already produced by `latent_distance.py`.
2. `workspace/structural_memory.json` — family rows with `family_label`, `first_seen_iteration`, `last_seen_iteration`. Already produced by `structural_memory.py`.

**Structural distance computation:** reuse `_extract_feature_bag()` from `structural_constraint_extractor.py`. For each iteration `i`, collect the feature bag of every family with `first_seen_iteration == i`. Distance between iterations is `1 - jaccard(bag_i, bag_{i-1})` on the subset of features that matter for "did the skeleton change": `var_power:*`, `has_eml_term`, `has_outer_additive_const`, `eml_arg:compound_X0_X1`, `eml_arg:ratio_X0_X1`, `eml_arg:product_X0_X1`, `eml_first_arg_negated`. Literal coefficients and scalar exponents are excluded — they are fit noise, not skeleton structure.

**Thrash condition:**

```
semantic_mean(i) = mean(jaccard_failure_families, jaccard_attack_surface,
                        jaccard_named_primitives, thesis_text_distance)
structural_delta(i) = 1 - jaccard(skeleton_features_i, skeleton_features_{i-1})

thrash(i) := semantic_mean(i) >= 0.8 AND structural_delta(i) <= 0.1
```

**Fire condition:** `thrash(i)` holds for the current iteration AND at least one prior iteration within a rolling window of 3. This is the "≥2 consecutive thrash iterations" rule — avoids single-spike false positives. Tunable: `SEMANTIC_THRESHOLD=0.8`, `STRUCTURAL_EPSILON=0.1`, `WINDOW=3`, `MIN_THRASH_COUNT=2`.

**Emitted constraint shape (fed through `build_structural_constraint_proposal`-equivalent):**

```
constraint: "Across the last {N} iterations the mutator rewrote failure_families,
             attack_surface, named_primitives, and thesis text completely while
             preserving the structural features {preserved_features}. Any valid
             next candidate MUST remove at least one of: {preserved_features}."
applies_to: "mutator trajectory over {project}"
failure_family: "trajectory_thrash"
severity: "degrading"
producer: "trajectory_extractor"
rationale: "semantic_mean={x}, structural_delta={y} across iterations {i-N..i}"
non_applicability_condition: "Only non-applicable when the thesis intentionally
                              fixes the skeleton and varies only fit coefficients."
```

The preserved-features list is concrete (names like `var_power:X0`, `has_eml_term`) so the mutator constraint consumer can actually check its next candidate against it.

**Wiring:** add `"trajectory_extractor"` to `CONSTRAINT_PRODUCERS` in `derived_constraints.py`. Add a second try/except block in `autoresearch_loop._refresh_derived_constraints_from_eval` immediately after the GP-061 structural-extractor block, same shape (swallow all failures, log, carry on).

---

## Failure Modes and Guardrails

**FM1 — first-iteration false fire.** Iteration 1 has no prior. Skip if `i < 2`. If `MIN_THRASH_COUNT=2`, the detector can't fire until iteration 3 at the earliest anyway.

**FM2 — legitimate coefficient-tuning iterations look like thrash.** If the mutator is *intentionally* holding the skeleton and varying only coefficients (e.g., during a fit-refinement phase), structural_delta will be ~0 by design. But in that case the semantic surface should also be ~unchanged — thesis text, attack surface, failure families do not oscillate during pure coefficient tuning. The semantic-mean ≥ 0.8 conjunct guards this. The non-applicability clause states the boundary explicitly.

**FM3 — missing latent_distance row.** If `latent_distance.jsonl` is absent or truncated, the detector should skip silently, not raise. Same try/except discipline as GP-061.

**FM4 — feature-bag trivially identical across families because the project only ever tries one skeleton.** This is not a false positive — it is a *true* positive. If the mutator has only ever produced one skeleton class over 10 iterations, that is the thrash we are trying to surface. The test is not "did the feature-bag change" but "did the feature-bag change **given that the semantic surface changed completely**."

**FM5 — overfitting to sandbox_07.** The detector must not hard-code `X0`/`X1`, `eml`, `compound_X0_X1`, etc. It reads whatever features `_extract_feature_bag()` produces for the current project. Retroactive test is sandbox_07; live test will be whatever run fires next.

**FM6 — false applicability outside fit-primitive projects.** `structural_memory.json` is only populated for fit-primitive projects. Detector should early-exit if the file is missing. `latent_distance.jsonl` exists for most projects but the structural-delta side is fit-primitive-only.

---

## Discriminating Experiment (H-ARCH-03)

**Claim:** A trajectory-thrash reader over `latent_distance.jsonl` + `structural_memory.json` surfaces at least one named-feature constraint on sandbox_07 that is distinct from (not a re-statement of) the GP-061 structural-extractor output.

**Test:** Run both extractors against sandbox_07 closed workspace. Compare the two emitted constraint strings and their `failure_family` tags.

- **Pass:** GP-061 emits `failure_family=structural_misfit` naming the inner coupling (ratio/product/compound). GP-062 emits `failure_family=trajectory_thrash` naming the preserved *trajectory invariants* (which features survived N rewrites). The two constraints are complementary: GP-061 says "your skeleton is wrong in this specific way," GP-062 says "you keep writing the same skeleton even after rewriting everything else."
- **Fail:** GP-062 emits a constraint that is a paraphrase of the GP-061 constraint, or fails to fire. In that case the detector collapses into GP-061 and should not be built as a separate pass.

**Prediction before running:** pass. The two extractors read different axes (cross-family invariants vs cross-iteration invariants), so their outputs should differ in `failure_family` and in the set of named features.

---

## Relationship to Existing Apparatus

- **GP-034** (loop control blind to latent distance) — GP-034 introduced `latent_distance.jsonl` and wired it as a *pivot heuristic prior*, not as a trajectory signal for constraint emission. GP-062 is the missing second reader on the same artifact.
- **GP-061** (constraint accumulation) — GP-062 uses the exact same delivery channel (`derived_constraints.json` via `update_derived_constraints_ledger`), the same producer-whitelist pattern, the same try/except discipline in the post-eval hook. This is deliberate: one channel, multiple readers, zero mid-iteration interrupts.
- **Topological pivot events** (`loop_events.jsonl`) — these already fire on pivot heuristics but are write-only (Gap B from the cross-artifact gap scan). GP-062 does not read `loop_events.jsonl`; it reads the underlying signal `latent_distance.jsonl`. Gap B remains open.
- **§6d (AGENTS.md)** — GP-062 is a direct application of the "signal coverage, not consumer existence" rule. `latent_distance.jsonl` has a consumer (`latent_distance.py` itself), but the trajectory-invariants axis has no consumer. The rule says: every distinct kind of signal needs a named consumer.

---

## Out of Scope

- **No spec required.** This is a single module, one call site, one new producer tag, one new failure_family string. Written-once seam-and-implement lane.
- **No mutator-facing UI changes.** The constraint flows through the existing `render_confirmed_constraints_prompt_section` path once promoted from provisional.
- **No change to `latent_distance.py` or `structural_memory.py`.** Both remain pure producers.
- **No Component B (cross-run accumulation).** Same deferral as GP-061 — prove it on one project first.

---

## Retroactive Test Result (2026-04-14)

Detector run against sandbox_07 closed workspace via
`python -m src.ztare.validator.trajectory_thrash_detector --project gp023_planck_sandbox_07`:

```
fired: True
iterations_covered: [2, 3, 4, 5, 6, 7, 8, 9, 10]
semantic_means:    [0.938, 1.0, 1.0, 0.938, 1.0, 1.0, 1.0, 1.0, 1.0]
structural_deltas: [0.0,   0.0, 0.0, 0.0,   0.0, 0.0, 0.0, 0.0, 0.0]
preserved_features: [
  'eml_arg:compound_X0_X1',
  'eml_arg:ratio_X0_X1',
  'has_eml_term',
  'has_outer_additive_const',
  'var_power:X0',
  'var_power:X1',
]
```

**H-ARCH-03 outcome: pass.** GP-062's emission is distinct from GP-061's:

- GP-061 emitted `failure_family=structural_invariant_ratio_coupled_uniform_structured` — names the *inner coupling* and directs the mutator to break the ratio coupling.
- GP-062 emitted `failure_family=trajectory_thrash` — names the *six preserved features across nine rewrites* and directs the mutator to alter at least one of them.

The two constraints are complementary (different failure_family, different applies_to, different directional instruction) and read different axes of the same failure (cross-family invariant vs cross-iteration invariant). Detector fired on 9 consecutive iterations, well above `MIN_THRASH_COUNT=2`, giving a large margin before a tuning change would change the retroactive conclusion.

---

## Rollout Discipline (added 2026-04-14)

Decision: **implement + retroactive-test only. Do NOT wire into the live
autoresearch_loop until a second fit-primitive project closes and GP-062 is
re-run cold against it.**

Reason: GP-062 has a sharper overfitting vector than GP-061. See next section.

Status checklist:

- [x] Module implemented at `src/ztare/validator/trajectory_thrash_detector.py`.
- [x] `trajectory_extractor` added to `CONSTRAINT_PRODUCERS` whitelist in `derived_constraints.py`.
- [x] Retroactive test against sandbox_07 → fires cleanly on 9 iterations with 6 preserved features, `failure_family=trajectory_thrash` distinct from GP-061 emission.
- [x] Stagnation-downgrade mechanism added to the ledger for the `trajectory_extractor` producer (via `downgrade_constraints_on_stagnation`, narrow to `DOWNGRADABLE_PRODUCERS`).
- [ ] **NOT DONE (deliberately):** second try/except block in `_refresh_derived_constraints_from_eval` calling the detector.
- [ ] **Gate before live wiring:** a second fit-primitive project must close with the detector run cold against its workspace. If the feature set fires on sandbox_07-like patterns only, promote to live. If it fires on everything, the feature set is overfit and must be widened first.

---

## Feature-Set Bias (the real overfitting vector)

GP-061's extractor reads features that emerge from the data — whatever
`_extract_feature_bag()` observes in the family_labels actually tried by the
project. If the project tries different skeletons, the feature bag reflects
that. Bias-limited at the data layer.

GP-062 is different. The distinguishing ingredient is the human-chosen
`SKELETON_FEATURE_PREFIXES` list in `trajectory_thrash_detector.py`:

```python
SKELETON_FEATURE_PREFIXES = (
    "var_power:",
    "has_eml_term",
    "has_outer_additive_const",
    "eml_arg:",
    "eml_first_arg_negated",
)
```

That list was written while staring at sandbox_07. If it omits a feature that
matters in project X, the detector fires false positives (says "thrash" when
the mutator is actually varying something that matters). If it overweights a
feature that was incidental to sandbox_07, the detector under-fires on
projects where that feature happens to always be absent. This is
feature-selection overfitting at the classifier layer, not at the data
layer, and the existing provisional→confirmed gate does not defend against
it — both projects could confirm the same biased feature set and make it
confidently wrong.

**Prevention path:**

1. Treat the next live wiring as a blind test. Do not adjust
   `SKELETON_FEATURE_PREFIXES` in response to a specific next-project's
   structural_memory until after the cold run.
2. If GP-062 fires on a second project that is *not* structurally similar to
   sandbox_07, re-read the proposal string: does the preserved-features list
   name things a domain reader would agree are "the mutator is stuck"? If
   not, widen the feature set (add features) or tighten the prefix list
   (remove over-weighted features).
3. Never auto-confirm a GP-062 constraint. Confirmation should be gated on a
   human review of the first two firing instances. Document the decision in
   the project closure.

---

## Relationship to GP-061 Retraction Mechanism

`downgrade_constraints_on_stagnation` in `derived_constraints.py` covers both
`structural_extractor` and `trajectory_extractor` via `DOWNGRADABLE_PRODUCERS`.
If the loop ever stagnates under a trajectory-thrash prior that turns out to
be wrong (e.g., the mutator is correctly holding the skeleton because that
skeleton is the right answer), stagnation downgrade will demote the constraint
back to provisional and it will stop being injected. The mechanism is in code;
the trigger is intentionally not auto-wired and is owned by the loop-control
path.

---

## Sandbox_08 Blind-Test Result (2026-04-15)

Closed after the detector was implemented but before live wiring — effectively a blind test of the feature set, since `SKELETON_FEATURE_PREFIXES` was frozen while staring at sandbox_07 and not re-touched for sandbox_08.

Cold run on sandbox_08 closed workspace:

```
fired: True
iterations_covered: [4, 5, 6, 10]
semantic_means:    [1.0, 1.0, 0.938, 0.875]
structural_deltas: [0.0, 0.0, 0.0, 0.0]
preserved_features: [
  'eml_arg:compound_X0_X1',
  'eml_arg:ratio_X0_X1',
  'has_eml_term',
  'var_power:X0',
]
```

| project    | iters covered      | # preserved feats | preserved set delta vs sandbox_07                    |
|------------|--------------------|-------------------|------------------------------------------------------|
| sandbox_07 | [2..10] (9 iters)  | 6                 | —                                                    |
| sandbox_08 | [4,5,6,10]         | 4                 | dropped `has_outer_additive_const`, `var_power:X1`   |

**Readings of the table:**

- Fires on a second project (not trivially dead).
- Fewer iterations (4 vs 9), smaller preserved set (4 vs 6) — not overfit-universal.
- Preserved set is a **subset** of sandbox_07's. The detector is reading "what the mutator actually kept preserving" and getting different answers on different projects.
- The four flagged iterations line up with `loop_events.jsonl`: `topological_pivot_profile_injected` at iter 4 then `topological_pivot_emergency` through iter 13. The existing pivot heuristic saw the same thrash via a write-only event stream no reader consumed.

**Caveat on blind-test rigor.** Sandbox_08 is still a `gp023_planck_*` variant, not a fully independent domain. A non-Planck fit-primitive blind test remains wanted for full confidence in the feature set. Sandbox_08 is the strongest blind test available at the time of promotion, but it is imperfect.

**Promotion decision:** move GP-062 from "implement-only" to live wiring with provisional-only behavior. Confirmation still gated on the 2-distinct-run rule in `derived_constraints.update_derived_constraints_ledger`. Feature-set changes frozen until the next non-Planck project closes.

---

## Live Wiring (2026-04-15)

Checklist update:

- [x] Module implemented at `src/ztare/validator/trajectory_thrash_detector.py`.
- [x] `trajectory_extractor` added to `CONSTRAINT_PRODUCERS` whitelist.
- [x] Retroactive test against sandbox_07 → fires on 9 iters.
- [x] Sandbox_08 blind-test → fires on 4 iters with subset preserved features.
- [x] Stagnation-downgrade mechanism in the ledger for `trajectory_extractor` producer.
- [x] **Wired live** into `autoresearch_loop._refresh_derived_constraints_from_eval` as a second try/except block immediately after the GP-061 structural_extractor hook. Same provisional gate applies.
- [ ] Non-Planck fit-primitive blind test — still open, deferred to next non-Planck project closure. If that cold run fires on every iteration or produces a wildly different preserved set, revisit feature-set choice.
