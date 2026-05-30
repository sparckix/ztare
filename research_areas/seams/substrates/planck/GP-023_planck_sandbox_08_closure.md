# GP-023 Planck Sandbox 08 — Closure Note

> **Seam metadata** · `seam_id:` GP-023 · `track:` substrates · `status:` unrecorded · `last_updated:` 2026-05-08


Status: closed 2026-04-14
Primary outcome: **D (score=0 across 14 iterations) + GP-061/GP-062 cold-run evidence**
Pre-reg: `GP-023_planck_sandbox_08_pre_registration.md`
Run: 14 iters logged in `iteration_telemetry.jsonl`, 12 fits recorded, 13 derived_constraints provisional entries. Stopped at iter 13 per decision 2026-04-14.

Per AGENTS.md §7: sealed artifacts never edited in place. This is the post-mortem.

---

## Primary verdict

**Outcome D — score starvation.** Every one of the 14 logged iterations scored 0 against the gate battery. `champion_eval_results.json` shows `score=0`, unchanged from the iter-0 seed. `latest_eval_results.json` weakest-point: *"Level 3 falsification suite disproved the thesis by assertion (`fail_assert`). The thesis is directly falsified by its own output."*

Same structural verdict as sandbox_07: gemini-pro did not recover the Planck GT form under the eml-only grammar within the iteration budget. Sandbox_08 differed from sandbox_07 in having the hardcoded `_STRUCTURAL_MISFIT_HINT_TEMPLATE` injected into the mutator prompt (the workaround later subsumed by GP-061). It did not change the outcome.

---

## GP-061 live wiring — worked as designed

GP-061's `run_structural_extractor` hook was wired live into `autoresearch_loop._refresh_derived_constraints_from_eval` for this run. Expected behavior under the overfitting-defense audit: fire every iteration, write into the provisional bucket, never promote to confirmed because a single-run `run_id` keeps `seen_count_runs=1`, and therefore never appear in the mutator prompt.

**Observed in `derived_constraints.json`:** `confirmed=0`, `provisional=13`. All 13 provisional entries have `producer=meta_judge`. **Zero** entries have `producer=structural_extractor`.

The absence is not the single-run provisional gate — it is the extractor's own confidence threshold firing. Of the 12 families in `structural_memory.json`, 8 are `structural_misfit` and 4 are `outlier_dominated`. The feature-bag intersection across the 8 structural_misfit families collapsed below `min_operator_nodes=4`, because sandbox_08's families were genuinely more varied at the outer skeleton than sandbox_07's (some had `X0 ** P3 + X1 ** P4` compound inner arguments, others had `X0 / X1` ratios, others dropped `X1` entirely). The extractor correctly refused to emit a constraint it could not support with ≥4 invariant features.

This is a **good** conservatism signature. GP-061 did not false-fire on a project where the mutator actually varied the skeleton, it just failed to score. The overfitting-defense story in the GP-061 seam holds in the code and in the data.

---

## GP-062 cold-run test — de facto blind test passed

Sandbox_08 was closed *after* GP-062 was implemented. Running the detector cold:

```
python -m src.ztare.validator.trajectory_thrash_detector --project gp023_planck_sandbox_08

fired: True
iterations_covered: [4, 5, 6, 10]
semantic_means:    [1.0,  1.0,  0.938, 0.875]
structural_deltas: [0.0,  0.0,  0.0,   0.0]
preserved_features: [
  'eml_arg:compound_X0_X1',
  'eml_arg:ratio_X0_X1',
  'has_eml_term',
  'var_power:X0',
]
```

Compare to sandbox_07 (the feature set was chosen while staring at sandbox_07 artifacts):

| project    | iters covered           | # preserved feats | preserved set delta vs sandbox_07              |
|------------|-------------------------|-------------------|------------------------------------------------|
| sandbox_07 | [2..10] (9 iters)       | 6                 | —                                              |
| sandbox_08 | [4, 5, 6, 10] (4 iters) | 4                 | dropped `has_outer_additive_const`, `var_power:X1` |

Interpretation:

- The detector fires on a **second project** — not trivially dead.
- It fires on **fewer iterations** (4 vs 9) and finds **fewer preserved features** (4 vs 6) — not overfit-universal.
- The preserved-feature set is a **subset** of sandbox_07's, not a superset or a disjoint set. The detector is reading "what the mutator kept preserving" and getting different answers on different projects, in a direction consistent with sandbox_08 having a more varied outer skeleton.
- The four iterations GP-062 flags (4, 5, 6, 10) line up with `loop_events.jsonl`, which records `topological_pivot_profile_injected` at iter 4 followed by `topological_pivot_emergency` every iteration 5 through 13. The existing pivot heuristic saw the same thrash GP-062 saw, but via a write-only event stream no reader consumed to emit a constraint. GP-062 is the missing reader.

**Verdict on GP-062 rollout gate:** sandbox_08 is not a fully independent blind test (it is still a `gp023_planck_*` variant), but it is the closest blind test available now. The detector's behavior on sandbox_08 is healthy: selective firing, smaller feature set, consistent with existing pivot heuristic events. I am willing to promote GP-062 from "implement + retroactive-test only" to "wire live on the next fit-primitive run, kept provisional-only under the normal 2-run gate."

---

## Ablation at iter 10

Per user note: an ablation was performed at iter 10. The run continued through iter 13 after the ablation and the score-starvation pattern persisted unchanged. The 3 post-ablation iterations are confirmatory, not new data. (Ablation details to be captured inline here if the user wants them logged; otherwise this paragraph is the placeholder.)

---

## Cross-reference to sandbox_07

Sandbox_07 and sandbox_08 are now a matched pair:

|                                        | sandbox_07         | sandbox_08         |
|----------------------------------------|--------------------|--------------------|
| Mutator / judge                        | gemini-pro / gemini-flash | same       |
| Iteration budget                       | 10                 | 14 (stopped iter 13) |
| Champion score trajectory              | 0 throughout       | 0 throughout       |
| `_STRUCTURAL_MISFIT_HINT_TEMPLATE`     | not injected       | **injected**       |
| GP-061 structural_extractor (cold)     | fires (6 invariant features) | does NOT fire (feature intersection below threshold) |
| GP-062 trajectory_thrash (cold)        | fires on 9 iters   | fires on 4 iters   |
| Outer skeleton variation               | low (ratio-coupled dominant) | higher (multiple compound forms) |

**Surprising read:** the hardcoded structural-misfit hint in sandbox_08 appears to have *moved the mutator toward more structural variation*, not less. GP-061 refused to emit because the variation defeated its intersection threshold; GP-062 fired fewer times because some iterations broke the skeleton enough to cross the structural-delta epsilon. Neither extractor got a free "fire everywhere on a gp023 variant" result — both gave meaningfully different outputs per project. This is the opposite of the overfitting failure mode the defense audit named.

---

## What changed in the repo during this run

- `src/ztare/validator/structural_constraint_extractor.py` — GP-061 Component A, wired into autoresearch_loop post-eval hook. Live on sandbox_08 (fired every iter, emitted nothing due to conservative threshold — correct behavior).
- `src/ztare/validator/trajectory_thrash_detector.py` — GP-062, implemented, retroactive-tested. Not wired live during sandbox_08.
- `src/ztare/validator/derived_constraints.py` — added `trajectory_extractor` to `CONSTRAINT_PRODUCERS`; added `downgrade_constraints_on_stagnation` retraction mechanism narrow to `DOWNGRADABLE_PRODUCERS={structural_extractor, trajectory_extractor}`.
- Seams: `GP-061_constraint_accumulation_as_output_seam.md` gained an Overfitting Defense Audit section; `GP-062_trajectory_thrash_detection_seam.md` was opened with retroactive test + rollout discipline + feature-bias analysis.
- AGENTS.md §6d — Working Harvester Masking + Attention Debt rules added.
- Postmortem: `research_areas/private/postmortems/gp061_cross_artifact_signal_missed_2026_04_14.md`.

---

## Next steps (suggested, not yet committed)

1. **Promote GP-062 to live wiring.** The sandbox_08 cold-run pattern is healthy enough to justify moving GP-062 from "implement-only" to a second try/except block in `_refresh_derived_constraints_from_eval`, parallel to the GP-061 hook. Stays provisional-only until the 2-distinct-run gate fires. Task #24 stays deferred behavior-wise, but the code path can be added now.

2. **Run a non-Planck fit-primitive project next.** Both sandbox_07 and sandbox_08 are `gp023_planck_*` variants. GP-061 and GP-062 have only been tested against Planck-family failures. A non-Planck fit-primitive run is the real blind test for both — especially for GP-062's hand-picked `SKELETON_FEATURE_PREFIXES`. If no such project exists, the next-best test is running the extractors against an older closed fit-primitive sandbox that the feature set was not designed around.

3. **Investigate why gemini-pro never scored.** Both sandboxes closed with score=0 across 10–14 iterations. The weakest-point string *"The thesis is directly falsified by its own output"* suggests the mutator's `fit_declaration` block is producing expressions that fail their own assertion. This is upstream of GP-061/GP-062 and is a separate bug to chase. Candidate diagnoses: (a) mutator hallucinating parameter bounds that numerically explode in the fit, (b) the eml-only grammar constraint forcing expressions that cannot satisfy the Level-3 assertion, (c) some `fail_assert` rule that is itself mis-specified. Worth one focused debugging session before running another full sandbox.

4. **Retire `_STRUCTURAL_MISFIT_HINT_TEMPLATE`.** Sandbox_08 showed it does not rescue the run. GP-061's general-purpose reader subsumes the intent (even when GP-061 itself refuses to emit on thin data, the hardcoded template is no better). Cleanup task: remove the template, delete the injection site, let GP-061 own this signal end-to-end.

5. **Log cross-artifact gap B (loop_events.jsonl).** Sandbox_08 made the gap concrete — `topological_pivot_emergency` fired on 9 consecutive iterations and no component read those events to emit a constraint or halt the loop. GP-062 read the underlying latent_distance signal and got there anyway, but the loop_events artifact itself is still write-only. Not blocking; worth a seam note.

6. **Consider pausing further full-run sandbox experiments until #3 is diagnosed.** Two consecutive runs scoring 0 across all iterations is cheap information for #3 but expensive if the goal is to test mutator improvements. A shorter diagnostic run (3–5 iters, different mutator or different grammar) would isolate the score-starvation cause before the next full investment.

---

## Score-starvation root cause — end-to-end debug 2026-04-14

Ran the debug myself against the live sandbox_08 harness. Findings:

**A. Harness is healthy.** Plugged the GT into `test_model.py` (EML form: `A * phi**p / eml((gamma*phi/psi)**q, math.e) + offset`, params `(0.95, 2.30, 0.72, 1.30, 0.06)`):

- `python gate_harness.py --run-visible-assertions` → `✅ visible-slice assertions passed`
- `python gate_harness.py --emit-deterministic-gates` → all 9 gates pass. Max residual on holdout ≈ 4.8e-6, on farther tail ≈ 4.0e-6, all peak-location errors = 0.0, terminal-value errors < 3e-14.

So the score=0 outcome is **not** a harness bug, not a fail_assert-rule misspec, and not a grammar-unreachability issue. The GT is expressible in the eml grammar, the harness passes it trivially, and the `< 0.05` residual threshold is easily clearable by anything within shouting distance of GT. Candidate (c) from next-step #3 is eliminated.

**B. Every candidate fails visible assertions at the fit stage.** Iterated through `workspace/fit_result_iter_{001..012}.json`:

| iter | rmse    | max_abs_residual |
|------|---------|------------------|
| 1    | 0.0715  | 0.337            |
| 2    | 0.227   | 0.545            |
| 3    | 0.082   | 0.381            |
| 4    | 0.230   | 0.705            |
| 5    | 0.146   | 0.532            |
| 6    | 0.093   | 0.401            |
| 7    | 0.681   | 2.045            |
| 8    | 0.084   | 0.293            |
| 9    | 0.227   | 0.704            |
| 10   | 0.441   | 2.138            |
| 11   | 1.020   | 2.480            |
| 12   | 0.244   | 0.558            |

The `run_visible_assertions` contract is `abs(i_obs - pred) < 0.05` for every visible point. The **best** candidate across 12 iterations (iter 8) has max_abs 0.293 — ~6× over threshold. None are close. This is candidate (a)/(b) from next-step #3: the mutator is producing expressions that cannot fit the visible slice well enough to satisfy Level-3.

**C. The structural gap — concrete diagnosis.** Reading the 12 candidate expressions against GT:

- GT: `A * phi**p / (exp((gamma*phi/psi)**q) - 1) + offset` — i.e. `eml((gamma*phi/psi)**q, math.e)` in the denominator. The **exp argument is `(gamma*phi/psi)**q`** — a *power-nested* inner term. That `**q` with q=1.30 is what bends the Planck curve's high-phi decay.
- All 12 candidates use `eml(gamma*phi/psi, ...)`, `eml(gamma*phi, ...)`, `eml(gamma*(phi/psi), ...)`, or `eml(gamma*phi*(psi**delta), ...)` as the first argument. **Not one of them puts a power operator inside the first argument of eml** — i.e. not one produces `exp(something**q)`. The mutator is exploring linear-argument eml calls exclusively.
- Consequence: every candidate produces a denominator with `exp(linear_in_phi) - <second_arg>`. That family of shapes has the wrong high-phi decay rate no matter how the outer `(psi**q)*(phi**p)` coefficients are tuned. Max-abs ~0.3 is the floor for linear-inner-arg fits against this GT.
- This is a **single-operator structural blind spot** in the mutator's search. The eml grammar *permits* `eml((gamma*phi/psi)**q, math.e)`; gemini-pro just never tries it. Every iteration mutates outer coefficients, outer skeletons (`phi**p * psi**q` vs `(phi/psi)**p`), and eml second arguments (phi/psi, gamma*phi/psi, (phi/psi)**p, phi*(psi**delta), …) — but the first argument of eml stays linear in phi and psi across all 12 iterations.

**D. What GP-061 saw vs. what the debugger sees.** GP-061's conservative refusal on sandbox_08 (reported in the main body above) refused to fire because the feature-bag intersection across families collapsed below `min_operator_nodes=4`. But the feature bag it's intersecting is the **outer skeleton** — `var_power:X0`, `has_eml_term`, `eml_arg:*`. It is not tracking "is there a power operator inside the first argument of eml." The structural invariant GP-061 missed — "mutator never nests a power inside the exp argument" — is not in `SKELETON_FEATURE_PREFIXES`. The diagnostic the mutator needed ("put a `**q` inside your eml first argument") was not something the current feature set could have emitted even if the intersection threshold had been met. This is a **feature-bag completeness gap**, distinct from the overfitting risk the GP-061 audit covered.

**E. Implications for next steps.**

- Next-step #3 upgrades from "a separate bug to chase" to "diagnosed: mutator has a single-operator structural blind spot in eml first-argument nesting." The fix is on the mutator-prompt side, not the harness or judge side.
- A minimal unblock that does not require a new full run: add a one-liner to the mutator system prompt explicitly instructing that the eml grammar permits (and frequently requires) power-operator nesting inside the first argument. Probe with a short 3–5 iter run.
- A second-order fix: extend GP-061's feature-bag vocabulary to include "power-nested inside eml first arg" (`eml_arg0_has_power`). Would have let the extractor emit the missing structural constraint after ~3 failed iterations instead of conservatively refusing.
- Next-step #6 (pause full runs) still stands: the short diagnostic probe is the next experiment, not another full sandbox.

**Preservation note.** Full debug was reproducible from in-repo artifacts alone: 12 fit_result_iter_NNN.json files + gate_harness.py + the pre-registration leak audit gave me GT form + params + every candidate expression + every candidate residual. No mutator re-run was required. This retroactively justifies the fit_result_iter archival pattern — the user's fear ("not sure we keep interim python test models") was unfounded for this class of diagnosis. Per-iter test_model.py source is not preserved, but expression + fitted_params + residual_map is, and that is the reconstructable minimum.
