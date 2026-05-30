---
seam_id: GP-227
status: open
opened: 2026-05-06
cabinet: reflexive
owner: PM-of-ZTARE
proposed_by: operator (2026-05-06 PM)
---

# GP-227 — Apparatus Sophistication vs. Insight Curve (Trajectory Mining)

> **Seam metadata** · `seam_id:` GP-227 · `track:` reflexive · `status:` open · `last_updated:` 2026-05-09


## Trigger

Operator question 2026-05-06 PM: "an interesting experiment would be to
check timestamps since I started this project ~40-50 days ago and draw
a curve on the sophistication of ZTARE and the org primitives and all
of that and correlated against the level of insights somehow (with
annotated curve of the key inflection points). It seems that yesterday
with the language, the NS-related scripts / graph stuff, and today
self-recursive primitives we are accelerating."

The question has the shape of: **is the apparatus accelerating, can we
measure that empirically over the project lifetime, and which specific
moves were the decisive inflection points?**

## Eigenquestion

> Can we operationalize "apparatus sophistication" and "insight quality"
> robustly enough that a 40-day trajectory plot is informative rather
> than just confirmatory of whatever narrative we already believe?

## Why this needs a panel before any plot is drawn

This kind of self-measurement is a known failure mode in three ways:
(a) Goodhart on whatever metric we pick, (b) survival bias because the
narrator is inside the trajectory, (c) confirmation bias because the
operator already has the "we're accelerating" hypothesis. Building the
plot without a methodological argument up-front is the same anti-pattern
as our own `project_rubric_as_eval.md` finding: any optimizer (or
narrator) chases satisfiability, not the underlying truth.

Run the panel BEFORE building so we either ship a real instrument or
explicitly reject the exercise as not-yet-doable.

## Panel debate (4 perspectives, 2 rounds each)

### Round 1 — opening positions

#### Methodologist (skeptical)

> "What you're proposing is a self-narrated longitudinal study with N=1
> (the apparatus), no control group, and a narrator who has the outcome
> already in mind. The sample size for any inferential claim is exactly
> zero — there's only one trajectory. Whatever curve you plot will be
> dominated by the metric choice, not by underlying signal. I would not
> let you publish this. The minimum bar before drawing any line: pick
> the metric BEFORE looking at the data; commit to the inflection points
> BEFORE annotating; produce a sham-arm (a non-apparatus directory)
> showing the curve looks DIFFERENT. Otherwise it's a Rorschach test."

#### Measurement theorist

> "Sophistication is a construct, not an observable. You need
> construct validity before instrument validity. Three candidate
> definitions, each with different implications:
>
>   1. **Capability sophistication** — what the apparatus can do that
>      it couldn't 40 days ago. Operationalize via the cage gate
>      catalog, the v5-op vocabulary, the substrate type list. Counts
>      the kit, not the depth.
>   2. **Recursive depth** — how many layers of self-improvement loop
>      currently exist. Today: Layer 1 (constraint injection from
>      telemetry), Layer 2 (primitive ROI), Layer 3 (closure-pattern
>      mining), and now Layer 4 (structural-analogy mining proposed in
>      GP-215 seventh pass). On day 1 it was Layer 0.
>   3. **Operator labor displaced** — what the operator USED to do by
>      hand that the apparatus now does automatically. The GP-226
>      charter critic, today's R8/R9 wiring, the structural-analogy
>      miner — each represents a specific operator-task displaced.
>
> These three are NOT the same curve. Recursive depth might step-jump
> while capability is flat; operator-labor-displaced might track
> capability tightly. Pick which one you actually care about and
> say so."

#### Builder (utility-pragmatic)

> "I disagree with the methodologist's bar. Even imperfect measurement
> informs decisions. If we plot any of the three sophistication metrics
> the measurement theorist named and they all show the same shape, the
> measurement uncertainty doesn't matter for the decision: keep
> pressing or rest. The plot is for ops, not for publication. My
> proposal: pick the cheapest one to compute (capability count: number
> of cage gates registered + number of seams with status=closed +
> number of mandates), plot it weekly, annotate when an inflection is
> visible, ship. Total cost: a 100-line script, no LLM, runs in 30
> seconds. The methodologist is solving a publication problem; we have
> an internal-decision problem."

#### Confound-finder

> "Three confounds will dominate any acceleration story:
>
>   - **Operator-hours-per-week** rising. The recent 'acceleration' may
>     just be the operator working more, not the apparatus working
>     harder. Plot operator hours alongside.
>   - **LLM model upgrades** between Sonnet → Opus 4.7, model swaps in
>     mutator/judge. Capability changes that aren't apparatus-driven
>     will look like apparatus acceleration.
>   - **External events**: paper deadlines, conference cycles, the
>     2026-05 Erdős paper, all create activity-volume confounds.
>
> If any of these three correlate with the apparent inflection points
> better than the apparatus changes themselves do, the apparatus story
> is confounded. The plot needs THREE companion curves: operator-hours,
> model-version-trajectory, and external-event timeline. Without those,
> the apparatus curve is uninterpretable."

### Round 2 — synthesis attempts and pushback

#### Methodologist (round 2)

> "The builder's pragmatist framing is fine PROVIDED we don't dress up
> the result as anything more than internal navigation. The risk is
> that the plot gets cited later — in a paper, in a postmortem, in a
> pitch — as evidence of acceleration when it was constructed
> precisely to confirm that hypothesis. Lock down the framing: this
> is an OPS DASHBOARD, not a research finding. Any time someone wants
> to use it as a finding, regenerate with the methodologist bar
> (sham-arm, pre-registration, etc.).
>
> The confound-finder's three companion curves are non-negotiable.
> Without them the plot is misleading whether or not we admit it."

#### Measurement theorist (round 2)

> "I'll tighten my position: build all THREE sophistication curves, not
> one. They're not redundant — they probe different aspects of the
> apparatus. If they tell the same story, the signal is robust. If
> they diverge, we've learned something specific about what KIND of
> sophistication is changing.
>
> For the insight axis, I'd push back on 'peak score per project'
> because it's confounded with substrate difficulty. Better: F-row
> closure rate per week (closures / opens, on a rolling basis) AND
> 'novel-finding density' (operator-tagged 'novel' annotations per
> week). Two independent measures, look for convergence."

#### Builder (round 2)

> "I accept the companion-curves requirement. Adding operator-hours is
> hard without time-tracking infrastructure — best proxy is git
> commit-author-timestamp density (we DON'T have git history reliably
> per the operator earlier today, so we use file mtimes for active
> directories). Model-version is in the per-run telemetry. External
> events are operator-curated; small effort.
>
> Concrete build proposal:
>
>   1. `scripts/public/mining/mine_trajectory_curves.py` — produces 6 curves:
>      Sophistication-A (capability count), Sophistication-B (recursive
>      depth, hand-curated layer count), Sophistication-C (operator-
>      labor-displaced, hand-curated), Insight-A (F-row closure rate),
>      Insight-B (novel-finding density), Confound-A (file-mtime
>      density across `src/ztare/`).
>   2. Operator-curated artifacts: `org/runtime/inflection_points.yaml`
>      (predicted inflection dates BEFORE looking at curves) and
>      `org/runtime/external_events.yaml` (deadlines, paper releases,
>      etc).
>   3. Pre-registration discipline: write the inflection-point
>      predictions BEFORE running the miner. Compare to actual
>      curves AFTER. The delta is the calibration data."

#### Confound-finder (round 2)

> "One more confound the others missed: **the seam itself is the
> apparatus's output**. Counting seams as a sophistication signal is
> circular if seams are the artifact OF insight, not the cause of it.
> Same for mandates, KRs, etc. — these are EXPRESSIONS of operator
> understanding, not separate from it.
>
> Cleaner sophistication metric: count things the apparatus EXECUTES
> automatically without operator intervention per run. Number of cage
> gates that engage, number of telemetry-derived constraint injections
> per iter, number of times a miner self-fires (when KR recurrence
> hits). These are all instrumented behaviors, not narrative artifacts.
> Recommend Sophistication-D: 'autonomous apparatus actions per
> project run' as a fourth, more honest curve."

### Synthesis

The panel converges on five claims:

  1. **The exercise is doable but only as an OPS DASHBOARD**, not a
     research finding. The methodologist's pre-registration / sham-arm
     bar is too high for the use case (internal navigation), but the
     finding must not be cited later as evidence of acceleration
     without re-generation under that bar.
  2. **Multiple sophistication metrics, not one.** Capability count
     (A), recursive depth (B), operator-labor-displaced (C), and
     autonomous apparatus actions per run (D — confound-finder's
     correction). If they agree, signal is robust; if they diverge,
     the divergence itself is informative.
  3. **Two insight metrics**: F-row closure rate (objective) and
     operator-tagged novel-finding density (subjective). Convergence
     check.
  4. **Three companion confound curves**: operator-activity proxy
     (file-mtime density on apparatus dirs), LLM model-version
     trajectory, external-event timeline.
  5. **Pre-registered inflection points**. Operator commits to expected
     inflection dates BEFORE running the miner. Calibration delta is
     the actual finding.

## Concrete proposal (what to ship) — REVISED 2026-05-06 PM

Operator pushback (2026-05-06 PM): "I don't actually have a clear
sense of the inflection points — that's what I want to learn. Can we
do this without pre-registration? Just be wary of overfitting to a
plausible story." Original Phase 0 required operator-authored
inflection_points.yaml; this revision drops that requirement and
substitutes three weaker-but-mechanical disciplines that protect
against the same overfitting failure mode without requiring
operator-authored predictions.

### The three substitute disciplines (replaces pre-registration)

  1. **Candidate inflections come from independent timestamp records,
     not from narrator memory.** Walk creation dates of: papers/* draft
     files, research_areas/private/seams/* files, src/ztare/gates/*
     module landings, org/mandates/* files, scripts/public/mining/* shipments.
     Each date appears because the artifact exists, not because anyone
     felt it was an inflection. The candidate pool is then ~50-100
     dates over the 40-day window.

  2. **Multi-metric convergence test prunes candidates.** A date counts
     as a "real" inflection only when ≥3 of the 9 trajectory metrics
     (4 sophistication + 2 insight + 3 confound) show a coincident
     step-change or rate-change at that date. Single-metric inflections
     are dismissed as metric noise. The narrator never gets to pick
     dates; the convergence count does.

  3. **Sham-arm comparison.** Run the same pipeline on a directory
     that's clearly NOT decisive for apparatus sophistication
     (e.g., `papers/paper2/`, an old completed project). If the
     apparent acceleration shows up there too, the apparatus story
     is confounded by general activity volume.

### Phase 0 (operator, 10 min — drastically shrunk)

  - Author ONLY `org/runtime/external_events.yaml` with paper deadlines,
    GPU runs, conferences, model upgrades, etc. — these are external
    confounds the timestamp record cannot reconstruct from inside the
    apparatus.
  - **NO inflection_points.yaml required.** The pipeline generates
    candidates from the artifact-creation record and the convergence
    test prunes them.

### Cost-discipline addendum (2026-05-06 PM) — content-hash ledger

Operator pushback: weekly re-runs would re-rate the entire corpus
each time, which is wasteful. Architecture added:

  - `analytics/public/queries/taste/taste_ledger.json` — content-hash keyed cache
    of all ratings ever produced
  - **Cache key**: `sha1(content[:1400])[:16]` — the rated content
    itself, not path or filename. If content changes, sha changes,
    and the artifact gets re-rated. Path renames don't trigger
    re-rates.
  - **Sampler** computes sha for every candidate, looks up in
    ledger; cached entries pass their score forward via metadata
    without ever appearing in the rater-visible sample.md.
  - **Aggregator** joins ledger-cached scores + fresh ratings;
    after aggregation, writes new ratings back to the ledger so the
    next run sees them as cached.
  - **Generalizes** to other LLM-assisted miners (the v5-op tagging
    script already uses the same `{project}::{sha8}` pattern).

Cost profile: first run rates ~150 samples; subsequent runs rate only
new/changed files (5-30/week). ~90% reduction after run 1.

Optional future discipline: quarterly drift-check by force-re-rating
random 5% of ledger; deviations >2 points flag for operator review.

### Phase 1 (auto, ~3 scripts) — REVISED

  - `scripts/public/mining/mine_trajectory_curves.py` — walks
    `src/ztare/gates/`, `scripts/public/mining/`, `research_areas/private/seams/`,
    `org/`. For each artifact: extract creation timestamp from
    frontmatter (or fall back to mtime). Bin by week. Emit:
      - **Sophistication-A** (capability count): cumulative gate count,
        seam count, mandate count, KR count
      - **Sophistication-D** (autonomous actions per run): pulls from
        per-project `cage_engagement.jsonl` event counts; aggregate by
        week
      - **Insight-A** (F-row closure rate): walks
        `research_areas/EXPERIMENT_TRACK_RECORD.md` for status changes
        per week
      - **Confound-A** (operator-activity proxy): file-mtime density
        across `src/ztare/`, `scripts/public/`, `research_areas/`

  - Sophistication-B (recursive depth) and Sophistication-C
    (operator-labor-displaced) are HAND-CURATED; written into the
    inflection_points.yaml as a "depth_at_date" field per inflection.

### Phase 2 (~50-line script)

  - `scripts/public/mining/render_trajectory_dashboard.py` — produces a single
    plot with the 4 sophistication curves + 1 insight curve + 3
    confound curves stacked, with operator-pre-registered inflection
    points annotated as vertical lines. Outputs to
    `analytics/public/queries/trajectory_dashboard.{html,json}`.

### Phase 3 (operator, post-curves)

  - Read the actual curves vs. predicted inflection points.
  - Write a **calibration note** in this seam: which predictions
    matched, which didn't, what the delta tells us about which moves
    were really decisive.

## Failure modes to declare up-front

  1. **The plot looks like acceleration regardless of metric** — this
     is consistent with the operator's hypothesis BUT also consistent
     with operator-hours-per-week rising. The companion curves
     adjudicate; if Sophistication-A rises at the same rate as
     Confound-A (operator activity), the apparatus story is
     confounded.

  2. **The plot is flat** — also informative; means the recent
     "acceleration" feeling is intuition without instrument support.
     Worth knowing.

  3. **Curves diverge** — Sophistication-A rises but D is flat means
     the apparatus is accreting catalog without growing autonomous
     behavior. That would be a SURPRISE and would force a different
     read of "sophistication."

  4. **Inflection-point predictions all match** — suspicious. Suggests
     the operator has hindsight-confirmed the curve in their head. The
     calibration value comes from MIS-predictions; if all 6-10
     predictions land, the exercise didn't generate signal.

## Promotion criteria (seam → spec)

This seam graduates to a spec when:

  - Phase 0 is complete (operator-curated YAMLs).
  - At least one panel member's concern has been mechanically
    addressed in the proposed Phase 1 design (the four sophistication
    curves are the explicit response to the measurement theorist).
  - Operator commits to NOT citing the dashboard as a research finding.

This seam stays in the SEAM state (no spec) if:

  - Operator is unwilling to pre-register inflection points
  - Operator is unwilling to author the external_events YAML
  - Panel concerns about narrator-inside-trajectory dominate

## Decision

**Recommendation: BUILD with the panel-corrected design.** Specifically:

  - 4 sophistication curves (A, B, C, D), not 1
  - 2 insight curves (closure rate, novel-finding density)
  - 3 confound curves
  - Operator-pre-registered inflection points before any plot is drawn
  - Plot is OPS dashboard only, not a research finding

The expensive thing is operator labor in Phase 0 (the YAMLs). Don't
build Phase 1 until those exist — otherwise the phase-1 output
calibrates against operator intuition AFTER seeing the curve, and the
calibration loses value.

## Forward links

  - **Pending operator artifacts:**
    - `org/runtime/inflection_points.yaml` (Phase 0)
    - `org/runtime/external_events.yaml` (Phase 0)
  - **Spec to author after Phase 0:**
    `specs/active/reflexive/GP-227_trajectory_dashboard_spec.md`
  - **Connection to GP-215 seventh pass:** structural-analogy mining
    is one of the recursive depth (Sophistication-B) layers. A
    successful trajectory plot would show Layer 4 emerging today
    (2026-05-06) as a step.
  - **Connection to GP-226:** the charter critic shipping today is the
    largest single operator-labor-displaced increment. Sophistication-C
    should reflect it.

## Memory entry pending at promotion-to-spec

`feedback_apparatus_self_measurement.md` — once Phase 1 ships and
results land, capture: did pre-registered inflection points match? did
sophistication-A vs D agree or diverge? was the dashboard useful for
ops decisions or was it just confirmatory?
