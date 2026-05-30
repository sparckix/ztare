# GP-029 Latent Distance Observability Seam

> **Seam metadata** · `seam_id:` GP-029 · `track:` apparatus · `status:` Closed, 2026-04-14. GP-023 Phase 1 complete; EU failure-prob · `last_updated:` 2026-05-17


## Status

Closed, 2026-04-14. GP-023 Phase 1 complete; EU failure-probability run complete. First slice (`src/ztare/validator/latent_distance.py`) shipped and live. Later-slice threshold calibration deferred to future work per original decision. Stale-active status corrected on visibility audit.

## Compressed Framing

> We infer mutator motion from scores. Scores are a noisy projection. We should measure the trajectory directly.

## Problem Snapshot

ZTARE currently has exactly two signals about where the mutator is in thesis-space:

1. **Score**, a scalar projection of a high-dimensional thesis onto a single rubric axis
2. **Novelty flags**, discrete set-membership signals (new attack IDs, new hinge IDs, new primitive IDs)

Both are indirect. A mutator that is cycling through the same three functional-form families with different parameterizations can produce large score fluctuations without actually moving in semantic space. A mutator that makes a genuine basin jump can produce zero score change if both basins are equally bad. The current signals cannot distinguish these cases.

The GP-023 smoke run made this concrete. The mutator moved through: power-law → rational function → exponential-suppression → additive composite. All of them scored 0 under the old rubric. From scores alone, the run looked like zero progress. From reading the debate logs by hand, it was clearly exploring distinct structural basins. Hand-reading 20 debate logs is not a scalable observability strategy.

## What Already Exists

`src/ztare/validator/proxy_signature.py:121` defines a `jaccard_distance(set_a, set_b)` helper that is already imported by `autoresearch_loop.py` and `test_thesis.py`. Its current use is narrow and specific: **anchor proxy drift detection** between the charter's declared anchor proxy list and the proxies actually exercised by the test suite, via `compute_anchor_proxy_coverage` (same file, line 210).

That is a single-axis drift measurement (charter vs. test suite). It is not an iteration-over-iteration motion measurement. But it means:

- GP-029 does NOT need a new Jaccard primitive, the function already exists and is battle-tested
- GP-029 DOES need a new caller that invokes `jaccard_distance` across the right pairs of sets (iter N constraints vs iter N−1 constraints, etc.)
- The implementation burden is smaller than I originally scoped: one extraction pass per iter + calls to the existing helper + one embedding call + one artifact writer

The existing anchor-proxy-drift use should be left untouched. GP-029 adds a second, independent caller of the same primitive for a different purpose (temporal motion, not structural drift). No refactoring of `proxy_signature.py` is required.

## What's Missing

There is no artifact in `workspace/` that answers the question:

> How far did the mutator move this iteration, semantically?

Not "did the score change." Not "were new primitive IDs introduced." The actual geometric question: **did the content of the thesis, the attack surface, the derived constraints, or the claim graph move meaningfully compared to the previous iteration?**

Without this signal, the operator cannot tell the difference between:

- productive exploration (mutator is covering distinct basins)
- basin orbiting (mutator is permuting parameters within one basin)
- drift (mutator is slowly diverging without landing anywhere)
- freeze (mutator is trivially repeating)

All four look identical on the score axis when all four score 0.

## Why This Is Not GP-028

GP-028 preserves speculative wedges that the scoring surface would kill. That is a **memory** fix, it adds a second artifact to hold content the score would discard.

GP-029 measures whether the mutator is actually moving. That is an **observability** fix, it adds a second signal to describe motion the score can't see.

They are complementary:

- GP-028 tells you what was almost lost
- GP-029 tells you whether anything is actually moving

Shipping GP-028 without GP-029 means you still can't tell whether the preserved wedges represent exploration or orbit. Shipping GP-029 first would tell you whether you have a preservation problem at all, or whether the mutator is just stuck.

## Option Space

### Option A, Hand reading only

Current state. Operator reads debate logs and workspace snapshots to infer motion.

- **Pro**: no code
- **Con**: does not scale; was the exact failure mode that made the 20-iter smoke run hard to interpret
- **Verdict**: insufficient

### Option B, Passive distance artifact (first slice)

After each iteration, compute a small set of distance metrics between iter N and iter N−1 content, and write them to `workspace/latent_distance.json`. No score impact, no mutation path, no feedback loop.

**Metrics in the first slice:**

1. **Jaccard over derived constraints**, how much of the constraint set changed
2. **Jaccard over attack surface IDs**, how much of the falsifier's probe surface changed
3. **Jaccard over named primitives**, how much of the thesis primitive set changed
4. **Character-level Levenshtein (normalized) over thesis.md**, crude but useful for freeze detection
5. **Cosine distance over thesis-claim sentence embeddings**, requires one embedding call per iter, gives the "did the thesis actually move" signal independent of score

Per-iteration output:

```json
{
  "iteration_index": 7,
  "jaccard_derived_constraints": 0.31,
  "jaccard_attack_surface": 0.52,
  "jaccard_primitives": 0.18,
  "thesis_edit_distance_normalized": 0.47,
  "thesis_claim_cosine_distance": 0.64,
  "score_delta": 0,
  "interpretation_hint": "semantic_movement_without_score_change"
}
```

The `interpretation_hint` is a derived classifier based on the metric combination:

- `orbiting`: low Jaccard across all sets, low cosine, low score delta
- `exploring`: high cosine, high Jaccard on primitives, any score delta
- `freeze`: near-zero edit distance and near-zero cosine
- `drift`: moderate cosine, low Jaccard on primitives (moving but not landing)
- `basin_jump`: high cosine AND high Jaccard on attack surface AND score delta

No score impact. No mutation path. No loop control read access. Pure observability.

### Option C, Active distance-aware loop control

Feed the distance metrics back into loop control so the pivot can fire on `orbiting` detection (low semantic motion) even when the catastrophic-failure streak hasn't triggered the usual pivot threshold.

- **Pro**: pivot fires earlier when the mutator is genuinely stuck
- **Con**: couples loop control to a new uncalibrated signal; risk of false-positive pivots
- **Verdict**: later-slice, only after Option B has produced enough live data to calibrate thresholds

### Option D, Distance-aware scoring bonus

Let the evaluator see distance metrics and reward basin jumps with a score bonus.

- **Verdict**: do not build. This reopens the GP-012 / GP-014 laundering surface, anything that lets distance influence score lets the mutator game distance.

## Recommendation

Implement Option B only. The metrics are cheap (4 set operations + 1 edit distance + 1 embedding call per iter). The output is purely observational. No interaction with score, mutation, or loop control in the first slice. Calibrate thresholds on live data, then debate Option C after a real run's worth of metric traces exist.

## Dependencies

- **Does not depend on GP-028.** Orthogonal. Can ship first, second, or in parallel.
- **Touches GP-013 (regime fingerprinting).** The regime fingerprint should NOT include distance metrics, that would couple the scoring regime to observational content.
- **Touches GP-023 interpretation.** If shipped before GP-023 main run completes, debate logs can be re-read with the distance trace as interpretation context. If shipped after, the GP-023 result is still valid but the observability gap I flagged in GP-023 Turn 3 remains for that run.

## Laundering Risk

None if Option B is implemented as specified. The metrics never influence the scoring path. The only risk is if Option C or D are built later without the Option B calibration phase, that would couple a new signal to the score, which is exactly how GP-012 was born. The seam should explicitly gate Option C behind "Option B has produced ≥ 2 live runs of metric trace data and calibrated thresholds."

## Why This Matters For GP-028

The GP-028 concern was "v4 suppresses creativity." The unspoken assumption behind that concern is "the mutator IS being creative and we can't see it." GP-029 tests that assumption. If the distance metrics show the mutator is orbiting (low semantic motion) even when v4 gates are lifted, then GP-028's preservation lane won't help, there is nothing worth preserving. If the distance metrics show genuine exploration that gets killed by the scoring surface, GP-028 is validated as exactly the right fix.

**GP-029 is the test of whether GP-028 is the right medicine.**

## Debate Log

### Turn 1, Claude (2026-04-11), Opening

The v1/v4 creativity discussion made it clear that ZTARE's observability of mutator motion is one scalar (score) plus a handful of discrete novelty flags. That is enough to detect "it's working" or "it's stuck," but not enough to distinguish "stuck in one basin" from "moving between equally bad basins" from "trivially repeating." All three look the same from the score axis.

The operator has been filling this gap by hand-reading debate logs. That was tolerable at 20 iters. It will not be tolerable at 100, and it is already the reason we couldn't diagnose the GP-023 smoke run quickly, we had to read 15 debate logs to confirm the mutator was actually moving through distinct functional-form families.

The fix is observability instrumentation, not scoring-surface change. Cheap set-theoretic and embedding distance metrics between consecutive iterations, written to a passive workspace artifact. No feedback loop. No score impact. Just: "how far did it move this turn."

This also gives us the diagnostic we need to know whether GP-028 is solving a real problem or a phantom one. If the mutator turns out to be orbiting rather than exploring, GP-028's preservation lane has nothing to preserve.

Next step: draft the schema, pick the embedding model (probably a small one, family-coupled to the mutator to avoid contamination), and write the interpretation-hint classifier. No implementation until the schema is reconciled with GP-028's workspace layout.

### Turn 2, Codex (2026-04-11), Deterministic first slice before any embedding call

The seam is real. The GP-023 smoke run already proved the core claim: score is an inadequate proxy for motion. A run can remain at `0` while still moving through distinct structural neighborhoods, and the only reason we know that today is because the operator read the debate logs by hand.

But the current Option B is still over-scoped for the timing we care about.

The weak point is the embedding call.

Before the GP-023 main run, adding an embedding-based motion metric would create a new runtime surface:

- an extra model/API call per iteration
- extra latency and failure modes
- a new contamination argument for any pre-registered run

That is not acceptable this close to Planck. Even if the metric remains passive, it is still a new experimental condition.

So the correct first slice is narrower:

- Jaccard over derived constraints
- Jaccard over attack-surface IDs or committee/attack headers
- Jaccard over named primitives / mutation declaration primitives
- normalized thesis edit distance
- optional section-heading / claim-count delta if needed

These are all deterministic, local, cheap, and pre-registration-safe.

That deterministic slice is already enough to answer the main observability question:

- `freeze` vs `movement`
- `orbiting` vs `basin jump`
- repeated parameter churn vs structural reframe

The interpretation-hint classifier should therefore also stay simple in slice 1:

- `freeze`: near-zero edit distance and near-zero set deltas
- `orbiting`: low-to-moderate edit distance with low set deltas
- `structural_move`: moderate/high set delta or declaration/primitive delta
- `score_only_change`: low motion with score movement
- `semantic_move_without_score_change`: non-trivial motion with zero score delta

No embeddings are needed to get those first distinctions.

This matters because GP-029 is observability, not elegance. The goal is not to build the best possible thesis-space geometry in one shot. The goal is to stop being blind.

So my current recommendation is:

- keep GP-029 open
- narrow Option B to a deterministic-only first slice
- explicitly defer any embedding-based metric until after GP-023 main run is complete
- keep the artifact passive and out of score, loop control, and mutation paths

If later runs show that deterministic metrics are too blunt to distinguish real semantic movement from verbose paraphrase, that is when an embedding-based second slice becomes justified. Not before.

### Turn 3, Codex (2026-04-11), GP-023 live run evidence

The live GP-023 main run strengthens this seam materially.

After the early `95` champion, the run kept going and the score trace mostly looked like regression/stagnation (`95` champion retained while later candidates fell to `40`, `40`, then `19`). If you only looked at score, the natural but wrong summary would be: "nothing new is happening; the mutator is just failing repeatedly."

The debate logs show that this summary is incomplete. The post-champion candidates are failing for different reasons across different structural families:

- bad decay-exponent derivation + external-form import critique
- flawed bell-component peak derivation
- peak-location + low-phi-slope failure
- high-phi floor miss plus explicitly unresolved mechanism

At the same time, `workspace/loop_events.jsonl` shows stagnation counts climbing through repeated pivot emergencies. So score says "flat/down," loop control says "stuck," but the content is still moving. That is exactly the observability gap this seam names.

This does not yet prove the mutator is productively exploring. It does prove that:

- score is not motion
- stagnation count is not motion
- hand-reading the logs is currently the only way to tell whether the run is orbiting, drifting, or traversing distinct but still-wrong basins

That is enough to strengthen GP-029's evidence base beyond the smoke-run argument alone.

### Turn 4, Codex (2026-04-11), EU run is the second live confirmation

The EU failure-probability run is the second live environment this seam needed.

The terminal trace by itself looked like a messy oscillation ending in bounded-discriminator exhaustion (`0 -> 50 -> 83 -> 50 -> 0 -> 50 -> 0 -> 50 -> 0 -> 0`, then `UNDERIDENTIFIED`). If you only watched score and stagnation count, the natural summary would be "the mutator searched around one bad basin and gave up."

`workspace/latent_distance.jsonl` shows that summary is wrong. Every recorded transition in the run is tagged `structural_move`, with high set deltas on the attack surface and named primitives. The mutator was not frozen and was not trivially orbiting one wording cluster. It was traversing distinct claim shapes:

- event-boundary definition work
- N=3 threshold grounding
- broader probability-model re-expansion
- causal-sufficiency threshold claims

and still ended `UNDERIDENTIFIED`.

That is exactly the informational role GP-029 was supposed to play:

- score is not motion
- stagnation count is not motion
- underidentification can happen after real structural search, not just repetition

It also sharpens the operator use of the signal. In this EU run, GP-029 argues **against** an immediate evidence-hardening reflex. The loop exhausted itself while still making structural moves, which points more toward `claim_narrowing` or `freeze` than "we are blind and need more evidence."

So the first-slice verdict is now stronger than it was after GP-023 alone:

- GP-029 is not just a Planck/curve-fit observability aid
- it is also useful in a soft-domain forecast project
- the first slice is likely past `active` and into `verify`

What remains open is not whether the slice works. What remains open is only whether to stop here or open a narrow follow-on seam later for loop-control use after enough traces accumulate.
