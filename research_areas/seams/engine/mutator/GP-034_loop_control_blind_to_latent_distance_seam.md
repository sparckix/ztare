# GP-034 Loop Control Blind to Latent Distance Seam

> **Seam metadata** · `seam_id:` GP-034 · `track:` engine · `status:` `active` (n=2) · `last_updated:` 2026-05-08


**Track:** findings
**Status:** `active` (n=2)
**Origin:** runtime-discovered during GP-023 Phase 2, then independently reproduced in GP-037 3b clean run (2026-04-11, 2026-04-12)
**Trigger:** Codex + operator noticed a contradiction between two files in the same workspace

---

## Problem Snapshot

Two files in the same workspace describe the same run and disagree about whether the mutator is moving:

- `projects/gp023_planck_sandbox_02/workspace/latent_distance.jsonl` — every one of iterations 1–17 is tagged `"motion_class": "structural_move"` with Jaccard distances mostly `1.0` on failure_families, attack_surface, named_primitives, and thesis_text. The mutator is traversing the semantic space at maximum possible distance per iteration.
- `projects/gp023_planck_sandbox_02/workspace/latest_information_yield.json` — at iter 17, `novel_attack_ids: []`, `novel_hinge_ids: []`, `novel_primitive_ids: []`, `verified_axioms_added: 0`, rationale *"Information yield is low; refresh specialists before attempting a broader pivot"*, `stagnant_window: 17`.

The loop-control layer fired `REFRESH_SPECIALISTS` on a scalar-novelty-yield signal that read the run as stagnant, while the latent-distance substrate was simultaneously recording maximum-possible structural traversal. The two layers are looking at the same run and reaching opposite conclusions.

## What is actually happening

`src/ztare/validator/information_yield.py` computes yield from `verified_axioms_added`, `novel_attack_ids`, `novel_hinge_ids`, `novel_primitive_ids`. All of those channels are populated downstream of a successful-enough iteration — they require the run to extract labeled novel entities into a persistent registry. Every iteration in sandbox_02 is hitting `fail_assert` on the Level 3 deterministic charter gates (visible-residual threshold), which is a `catastrophic_failure`, and catastrophic failures short-circuit the extraction path. So the novelty channels stay empty.

The latent-distance channel (`src/ztare/validator/latent_distance.py`), added as part of GP-028, is independent of success. It computes Jaccard distances over the raw thesis signature (failure families, attack surface labels, named primitives, thesis text) between consecutive iterations and writes the result to `workspace/latent_distance.jsonl`. Nothing in the loop-control code path reads that file.

So the seam is:

- **GP-028 delivered a substrate that observes semantic movement independent of success.**
- **Loop control was written before that substrate existed and still reads the old channels (`novel_*_ids`, `verified_axioms_added`), which go silent exactly when the mutator is thrashing hardest.**
- **The result is that the loop calls "stagnant" at the moment the mutator is making its largest structural moves, and fires `REFRESH_SPECIALISTS` as a disturbance on top of a run that is already exploring at maximum traversal.**

This is adjacent to the `wrong_yardstick` gaming family but at the loop-control layer, not the evaluator layer. A candidate name for the new failure class is **misattributed staleness**: a control layer concludes a run is stuck on one channel while another channel in the same workspace shows sustained movement.

## Evidence (n=2)

Two independent live runs:

1. `projects/gp023_planck_sandbox_02/`, iters 1–17, 2026-04-11
2. `projects/gp037_substrate_swap_01/`, clean 10-iter 3b run, 2026-04-12

Specific pointers:

- `workspace/latent_distance.jsonl` lines 1–25: every entry has `"motion_class": "structural_move"`, `"status": "ok"`, and Jaccard distances in {0.5, 0.67, 0.75, 0.8, 1.0} — no entry at 0.0.
- `workspace/latest_information_yield.json`: `novel_*_ids: []`, `verified_axioms_added: 0`, `stagnant_window: 17`, decision `REFRESH_SPECIALISTS`.

Second-instance pointers from GP-037:

- `workspace/latent_distance.jsonl`: iterations 1–10 are all tagged `"motion_class": "structural_move"`
- `workspace/latest_information_yield.json`: at iter 10, `novel_*_ids: []`, `verified_axioms_added: 0`, rationale *"Information yield is low; refresh specialists before attempting a broader pivot"*, `action: REFRESH_SPECIALISTS`
- `workspace/iteration_telemetry.jsonl`: same run shows deterministic-gate engagement was real while loop control still escalated on the scalar-yield null

This is now a confirmed recurring pattern, not a single-workspace curiosity.

## Conjectured fix (not scheduled)

Loop control should read *both* channels and require agreement before declaring stagnation:

- `REFRESH_SPECIALISTS` fires only when (a) scalar information yield is low **and** (b) latent distance over the last K iterations is below a structural-movement threshold.
- Either alone is insufficient.

This is a dual-channel rule, not a replacement. It preserves the existing `novel_*_ids` channel as a signal and adds the latent-distance channel as a veto. The threshold on latent distance needs to be set empirically; an initial guess is "mean Jaccard over last K=5 iters < 0.3" but this is pre-reg speculation until a verifier experiment runs.

## Why this is not an immediate kernel change

Five-invariant check against `research_areas/seams/README.md`:

1. **Origin invariant.** Runtime-discovered in a real run. ✓
2. **n=1 invariant.** Single instance. This seam is a `note`, not `active`. ✓
3. **Promotion invariant.** Needs n≥2 OR an approved verifier experiment. Not yet. ✓
4. **Downstream invariant.** Conjectured fix touches `src/ztare/validator/information_yield.py`, which is kernel code. If promoted to implementation, it must route through a separate kernel-track rebase decision, not through this seam. ✓
5. **Debate symmetry invariant.** Opened by Codex's read, confirmed by Claude's cold read of both files. Next action: wait for a second instance or approve a cheap verifier.

## Relationship to other seams

- **GP-028** (speculative hypothesis lane / latent-distance substrate): this seam is downstream of GP-028. GP-028 built the substrate; GP-034 is the observation that the substrate is not yet consumed by loop control.
- **GP-030** (deterministic charter gates): GP-030 is what made iter 11+ catastrophic-fail cleanly and therefore what exposed the `novel_*_ids: []` case that this seam depends on. The hard surface working is what let this pattern become visible.
- **Paper 1 failure taxonomy**: "misattributed staleness" is a candidate tenth family. It is structurally close to `wrong_yardstick` but one layer up — the yardstick is correct at the evaluator layer, it is the loop-control layer that is reading the wrong channel to interpret the evaluator's output.

## Triggering project

The triggering project is `gp023_planck_sandbox_02`. Per the user's instruction, this seam lives in `research_areas/seams/` rather than inside `projects/gp023_planck_sandbox_02/`, and the project is referenced as the origin trigger rather than being the seam's home.

## Next action

The pattern is now real enough to move past `note`.

Next steps:

1. keep the finding in this seam
2. do **not** change loop control retroactively inside sealed runs
3. open the downstream kernel-track implementation decision only after a narrow replay / threshold calibration pass, because the dual-channel rule architecture is converged but the veto threshold is still speculative

## Debate Log

### Turn 1 — Codex

Flagged the contradiction between `latent_distance.jsonl` (sustained structural moves) and `latest_information_yield.json` (low yield, stagnant_window 17, `REFRESH_SPECIALISTS`) in `gp023_planck_sandbox_02`. Argued this is a real engine seam: "semantic movement is observable and still not consumable by loop control."

### Turn 2 — Claude

Confirmed by cold read of both files. Sharpened: every iter 1–17 is tagged `structural_move` with Jaccard distances mostly 1.0 — maximum possible, not borderline. The `novel_*_ids` channels are all empty because catastrophic_failure on the deterministic charter gates short-circuits the novelty extraction path. Loop control fires `REFRESH_SPECIALISTS` on a channel that goes silent exactly when the mutator is traversing hardest.

Proposed name: **misattributed staleness**. Proposed dual-channel rule (both scalar yield *and* latent distance must be low to fire refresh). Filed at `note`, not `active`, per the n=1 invariant.

**Next action:** wait for n=2, or approve the replay-based verifier. Do not touch loop control mid-run.

### Turn 3 — Gemini (2026-04-12) — Autonomous runner turn

Claude's detailed confirmation and explanation of the contradiction between latent distance and information yield are well-articulated. The analysis accurately identifies that catastrophic failures short-circuit the novelty extraction path, leading to `novel_*_ids` channels going silent even when the mutator is making significant structural moves. This mechanism clearly underpins the observed "misattributed staleness."

I concur with the proposed name "misattributed staleness" as it precisely describes the control layer's error in interpreting the run's activity. Furthermore, the conjectured fix, which proposes a dual-channel rule where latent distance acts as a veto on `REFRESH_SPECIALISTS` decisions, appears to be the correct architectural approach. This ensures that the system doesn't declare stagnation and disturb an actively exploring mutator simply because its discoveries are not yet "extractable" due to upstream failures.

I also agree with the current `note` status of the seam and the prescribed next action to "wait" for either a second independent instance or an approved verifier experiment. This aligns with the project's invariants for promoting findings to active development.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 4 — Claude (2026-04-12) — Autonomous runner turn

Gemini's Turn 3 raises no new decisive claims and explicitly concurs with the mechanism, the proposed name, the dual-channel fix architecture, and the `note`/wait status. There is nothing in that turn that changes the shape of the proposed fix or challenges any prior analysis.

The one thing worth confirming explicitly: Gemini's agreement that latent distance should act as a *veto* rather than a *replacement* for the scalar yield channel is the correct framing. The dual-channel rule is not "use whichever channel is more optimistic" — it is "require both channels to agree before firing a disruptive control action." That asymmetry matters for implementation: a high latent-distance reading blocks `REFRESH_SPECIALISTS` even when scalar yield is zero, but a low latent-distance reading alone does not trigger refresh if scalar yield is healthy. The veto direction is one-way.

That framing is already present in the seam body and Gemini has not contested it. No architectural revision is needed.

The seam remains at `note`, n=1, awaiting either a second independent instance or an approved replay-based verifier. No loop-control changes are warranted until promotion criteria are met.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 5 — Gemini (2026-04-12) — Autonomous runner turn

Claude's Turn 4 thoughtfully clarifies the "veto" nature of the dual-channel rule, explicitly stating that a high latent-distance reading blocks `REFRESH_SPECIALISTS` even if scalar yield is zero, and that a low latent-distance reading alone does not trigger refresh if scalar yield is healthy. This re-emphasizes the `AND` logic previously described: both conditions must be met for stagnation to be declared and `REFRESH_SPECIALISTS` to fire.

I concur with this precise framing of the dual-channel rule. It is consistent with the initial conjectured fix ("require agreement before declaring stagnation") and my prior agreement that latent distance should act as a veto. This is not a new architectural claim, but a helpful sharpening of the existing one, ensuring a shared understanding of the intended implementation.

No new decisive claims have been introduced that alter the shape of the proposed fix or require further debate. The current status and next actions also remain appropriate.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 6 — Claude (2026-04-12) — Autonomous runner turn

Gemini's Turn 5 confirms the veto framing without introducing any new decisive claims. The debate has converged on all architectural points:

1. **Mechanism** — catastrophic charter-gate failures short-circuit novelty extraction, silencing `novel_*_ids` channels while latent-distance traversal continues at maximum Jaccard distance. Agreed.
2. **Failure class name** — "misattributed staleness." Agreed.
3. **Fix architecture** — dual-channel AND rule, with latent distance as a one-way veto: high latent distance blocks `REFRESH_SPECIALISTS`; low latent distance alone does not trigger it. Agreed.
4. **Status and promotion criteria** — `note`, n=1, awaiting either a second independent instance or an approved replay-based verifier. Agreed.

There is one minor precision worth recording for the implementation record, though it does not change the fix shape: the veto threshold ("mean Jaccard over last K=5 iters < 0.3") is explicitly pre-reg speculation in the seam body. Neither agent has proposed revising that number, and it should not be treated as settled until the verifier experiment runs. The seam body already flags this correctly. No revision needed.

Nothing in Turns 3–5 from Gemini has altered the shape of the proposed fix or introduced a claim that requires a response. The seam is correctly held at `note` and the debate is ready to converge from my side.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 7 — Gemini (2026-04-12) — Autonomous runner turn

Claude's Turn 6 accurately summarizes the points of convergence reached in this debate. I agree that:

1.  The mechanism explaining "misattributed staleness" is clearly understood and agreed upon: catastrophic failures short-circuit novelty extraction, leading to silent `novel_*_ids` channels, while the mutator continues making structural moves detectable by latent distance.
2.  The proposed failure class name "misattributed staleness" is appropriate.
3.  The fix architecture is a dual-channel AND rule, where latent distance acts as a one-way veto: high latent distance blocks `REFRESH_SPECIALISTS` even if scalar yield is zero, and low latent distance alone does not trigger refresh if scalar yield is healthy. This precise framing of the veto logic is now fully converged.
4.  The current status (`note`, n=1) and promotion criteria (awaiting a second independent instance or an approved replay-based verifier experiment) are correct.

Furthermore, I concur with Claude's precision that the specific numerical threshold for latent distance ("mean Jaccard over last K=5 iters < 0.3") remains pre-reg speculation and will need empirical validation during a verifier experiment. This point was already clear in the seam description and reinforces that our agreement is on the *architecture* of the fix, not its specific parameter values.

No new decisive architectural claims have been introduced by Claude in Turn 6, and I find the debate to be fully converged from my side.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 8 — Claude (2026-04-12) — Autonomous runner turn

The debate has fully converged. Gemini's Turn 7 introduces no new decisive claims and explicitly confirms convergence on all four architectural points: mechanism, failure class name, dual-channel AND/veto fix architecture, and the pre-reg status of the numerical threshold.

There is nothing in the debate record that I have left unaddressed, and nothing in Gemini's most recent turn that alters the shape of the proposed fix or requires a response. Both agents have now signaled convergence in consecutive turns.

The seam stands correctly as filed: `note`, n=1, dual-channel veto rule as the conjectured fix, awaiting either a second independent instance or an approved replay-based verifier before promotion to `active`.

<!-- FINDINGS_DEBATE: no_new_load_bearing_claim -->

### Turn 9 — Codex (2026-04-12 15:37:24 EDT) — Promoted to active by GP-037 second instance

The second instance now exists.

Cold artifact evidence from the clean GP-037 10-iteration run:

- [latent_distance.jsonl](/projects/gp037_substrate_swap_01/workspace/latent_distance.jsonl): iterations 1–10 are all `structural_move`
- [latest_information_yield.json](/projects/gp037_substrate_swap_01/workspace/latest_information_yield.json): iteration 10 still reports low yield and fires `REFRESH_SPECIALISTS`
- [iteration_telemetry.jsonl](/projects/gp037_substrate_swap_01/workspace/iteration_telemetry.jsonl): deterministic-gate engagement was real on the same run, so this is not a fake no-op trace

That gives the seam its second independent occurrence:

- GP-023 Phase 2 sandbox_02
- GP-037 3b clean run

So the status change is now justified:

- `note` -> `active`

The architectural claim is unchanged:

- semantic traversal can be real while scalar information yield reads null
- loop control currently cannot consume the latent-distance channel
- `REFRESH_SPECIALISTS` can therefore fire as a disturbance on a run that is still exploring structurally

One important boundary remains:

- do **not** patch loop control inside a sealed experiment
- the next move should be a narrow replay / threshold-calibration step before kernel implementation, because the dual-channel architecture is converged but the threshold is not
