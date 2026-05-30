# GP-220 — Reflexive Primitive ROI Telemetry

> **Seam metadata** · `seam_id:` GP-220 · `track:` apparatus · `status:` open - opened 2026-05-06 · `last_updated:` 2026-05-09


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-05-06

## ID

GP-220

## Eigenquestion

Each reflexive primitive (R10-R16, GP-076, GP-156 hardening, GP-180
DAG steering, etc.) shipped with a hypothesis about what failure mode
it catches and what behaviour it changes. After 3+ weeks live, do they
actually fire? Do they actually catch real issues? Or are they
decorative — adding apparatus complexity without buying signal?

## Problem Statement

The apparatus has a registry leak in REVERSE. Reflexive primitives
got added based on operator inception (the GP-102 pattern: principal
observes failure → proposes primitive → ships) but **no primitive has
ever been retired** based on observed ROI. The discipline that
applies to substrates ("kill ones with no progress") doesn't apply to
the primitives that were supposed to help substrates.

This isn't theoretical. The apparatus_level2_review claim
`claim_failure_log_compounds` (Stage 4 typed_endpoint_failure_log
accumulator) explicitly tests whether one such primitive does
compound vs. is a write-only log. That same logic should apply
across the entire reflexive primitive catalog, not just the typed
endpoint pack.

The cost of decorative primitives:
- Apparatus complexity grows without bounded benefit
- Mutator briefing surface grows; signal-to-noise on briefings degrades
- New operator/agent has more to read on cold start (bootstrap_manifest)
- Bug surface grows
- Each primitive's "did it fire" flag hides in a different jsonl

## Proposed Architecture

A periodic ROI scan over per-primitive telemetry that produces a
scorecard:

```
analytics/public/queries/reflexive/reflexive_primitive_roi.json:
{
  "scan_utc": "2026-05-06T16:00:00Z",
  "lookback_window_days": 28,
  "primitives": [
    {
      "primitive_id": "R10",
      "primitive_name": "cross_class_extrapolation_gate",
      "engagement_rate": 0.38,
      "hit_rate": 0.21,
      "action_rate": 0.05,
      "score_lift": -0.02,
      "verdict": "noisy_detector",
      "data_points": 124
    },
    {
      "primitive_id": "GP-076",
      "primitive_name": "predictive_divergence_sweep",
      "engagement_rate": 0.04,
      "hit_rate": 0.92,
      "action_rate": 0.86,
      "score_lift": +6.4,
      "verdict": "load_bearing",
      "data_points": 11
    }
    ...
  ],
  "retire_candidates": [
    {"primitive_id": "RXX", "reason": "engagement_rate < 0.05 AND data_points >= 50"}
  ],
  "decorative_candidates": [
    {"primitive_id": "RYY", "reason": "engagement_rate >= 0.30 AND action_rate < 0.05"}
  ]
}
```

### Metrics (per primitive, computed per substrate-class then aggregated)

| Metric | Definition | Failure mode it catches |
|---|---|---|
| **engagement_rate** | (iters where `can_handle` returned True) / (total iters where rubric flag was on) | Primitive declared but never engages — `can_handle` predicate too narrow |
| **hit_rate** | (iters where engagement produced a non-empty finding) / (engaged iters) | Primitive engages but never finds anything — implementation broken |
| **action_rate** | (iters where finding influenced next-iter mutator briefing) / (hit iters) | Primitive finds but the apparatus doesn't act on it — wiring gap |
| **score_lift** | mean Δ-score on iters where action took effect vs control | Primitive acts but doesn't help — decorative |
| **time_to_promotion** | mean iters between `can_handle=True` and observable score improvement | Primitive helps but slowly — calibrate cadence |

### Verdict bands

- **load_bearing**: action_rate ≥ 0.30 AND score_lift ≥ +1.0 over 4-week window
- **useful**: action_rate ≥ 0.10 AND score_lift ≥ 0
- **noisy_detector**: hit_rate ≥ 0.20 BUT score_lift ≤ 0 (catches things; acting on them doesn't help)
- **decorative**: engagement_rate ≥ 0.30 AND action_rate < 0.05 (engages but apparatus ignores findings)
- **dead**: engagement_rate < 0.05 AND data_points ≥ 50 (predicate too narrow OR rubric flag never on)

## Scope

**Covers:**
- Per-primitive telemetry aggregation across all projects' workspace/*.jsonl
- ROI scorecard with explicit verdict bands
- Retire / decorative / dead candidate flagging (NOT auto-retirement —
  principal disposes)
- Output: `analytics/public/queries/reflexive/reflexive_primitive_roi.json`

**Does not cover:**
- Auto-retirement of primitives (creative judgment required;
  the report is input to a principal-time review, not an autonomous
  decision)
- Re-engineering of low-ROI primitives (the report says "low ROI";
  the redesign is a separate task)
- Confounding analysis (a primitive might have low ROI because the
  substrate distribution shifted, not because the primitive is bad)

## Telemetry Sources

Per-primitive activity surfaces (sampled — full list discoverable
by scanning workspace/ for jsonl with primitive markers):

| Primitive | Source jsonl | Engagement marker |
|---|---|---|
| R8 feature-coverage adequacy | `cage_engagement.jsonl` | `engagements["feature_coverage_adequacy"].ok=True` |
| R9 target-convention homogeneity | `cage_engagement.jsonl` | `engagements["target_convention_homogeneity"].ok=True` |
| R10 cross-class extrapolation | `cage_engagement.jsonl` | `engagements["cross_class_extrapolation"]` |
| R11 per-class farther-tail | `cage_engagement.jsonl` | `engagements["per_class_farther_tail"]` |
| R12 symbolic logic cage | `cage_engagement.jsonl` | `engagements["symbolic_logic_cage"]` |
| R13 substrate_critic | `substrate_critique.json` + `substrate_critique_post_fit_iter_*.json` | file presence + non-empty epistemic_voids |
| R14 noise_profile | `noise_profile.json` + `noise_profile_post_fit_iter_*.json` | file presence + classification != "unknown" |
| R15 ANALOGY | `analogy_log.jsonl` | append events |
| R16 framer 1D | `framing_report.json` | file presence |
| GP-076 predictive divergence | `divergence_sweep_*.json` | file presence |
| GP-156 R1 visible-MRE attestation | `iteration_telemetry.jsonl` `escalation_flags` | flag-set events |
| GP-180 DAG steering | `dag_steering_log.jsonl` | append events |
| typed_endpoint_pack | `typed_endpoint_failure_log.jsonl` | append events; cap_kind |
| contract_adherence | `contract_violations.jsonl` | append events |

For "did the finding influence next-iter briefing": cross-reference
the per-primitive output against the next iter's mutator-briefing
log (`mutator_briefing_*.json`) for the corresponding line/section.

For "score_lift": diff `iteration_telemetry.jsonl` `score` between
iters where primitive acted vs comparable iters where it didn't.

## Implementation

`scripts/public/analytics_shared/reflexive_primitive_roi_audit.py`:

```python
def main():
    """Walk projects/, aggregate per-primitive telemetry, compute
    ROI metrics, write the scorecard."""
    primitives = build_primitive_catalog()  # static list w/ source-jsonl mapping
    for project in projects_dir.iterdir():
        if not project.is_dir(): continue
        for primitive in primitives:
            primitive.absorb_project(project)
    scorecard = {
        "scan_utc": utc_now_iso(),
        "lookback_window_days": 28,
        "primitives": [p.summarize() for p in primitives],
        "retire_candidates": [...],
        "decorative_candidates": [...],
    }
    write_json(REPO / "analytics/public/queries/reflexive/reflexive_primitive_roi.json", scorecard)
```

Cadence: P28D as a KR (`kr_reflexive_primitive_roi_periodic`),
following the same pattern as `kr_reflexive_audit_periodic`.

## Why this is non-trivial / why it's a real seam

1. **It applies the apparatus's own discipline reflexively.** ZTARE
   says "kill substrates with no progress." This applies the same
   to the primitives that were supposed to help.

2. **It distinguishes "primitive doesn't catch real failures"
   (`hit_rate` low) from "primitive catches failures but apparatus
   doesn't act" (`action_rate` low) from "primitive acts but
   doesn't help" (`score_lift` flat).** Three distinct failure
   modes with three distinct fixes. Lumping them into one ROI
   number would lose this resolution.

3. **It surfaces where the registry leak vs the action leak is.**
   The R10-R16 backport debt (GP-157 §8.6) is a registry leak; the
   proposed audit is the consumer that would notice if the
   directly-wired gates aren't being hit by Cage routing. Pairs
   well with that backport.

## Connection to other seams

- `GP-102` reflexive_primitive_discovery_seam.md — proposes the
  cron-style reflexive audit for failure-class detection. GP-220
  is the analogue for primitive ROI tracking (input → output).
- `GP-157` cage_v5_implementation_spec.md §8.6 — R10-R16 backport
  debt. GP-220 would notice if the backport doesn't ship.
- `apparatus_level2_review.py::claim_failure_log_compounds` —
  one specific instance of this scoring pattern (per-cap-kind
  failure log). GP-220 generalizes it across the catalog.

## Honest failure modes / ways this could mislead

- **Action_rate underestimates value.** Some primitives are
  diagnostic-only (R13/R14 noise_profile). Their "action" is to
  surface in mutator briefing; whether the mutator USED the surfaced
  signal is harder to measure. Mitigation: `score_lift` is the
  ultimate metric; if score lifts when primitive engages, action
  happened somewhere.
- **Score_lift is confounded by substrate difficulty.** A primitive
  that only fires on hard substrates will appear to have lower lift
  than a primitive that fires on easy ones. Mitigation: per-substrate-class
  aggregation; report distribution, not just mean.
- **28-day lookback may be too short for slow-engaging primitives.**
  GP-076 predictive divergence sweep fires only on Component-C
  exhaustion — could be 1-2 events per month. data_points < 10 →
  verdict is "insufficient data", not a band assignment.

## Future Work

If the ROI audit consistently flags certain primitive classes as
decorative, a meta-pattern emerges: under what conditions does the
apparatus over-build? GP-216 vocabulary v5 might predict the
op-classes most prone to decorative implementation. Predicted
op-classes: `core_07 Generalization` (over-abstraction is a known
risk) > `core_03 Decomposition` (over-splitting). Test this against
the empirical ROI bands once enough data is collected.
