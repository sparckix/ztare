# GP-105b — Ex-Post Goal Orchestration (SUPERSEDED)

> **SUPERSEDED 2026-04-23 by GP-131.** This seam was never implemented (0 LOC). The cross-run apparatus-improvement-scan scope is absorbed into GP-131's discovery-source model as the "apparatus-improvement-scan" source (9th of 8 planned sources in `research_areas/private/seams/mission/GP-131_work_discovery_loop_seam.md`). First-release GP-131 ships with TODO-scan + damage-scan only; apparatus-improvement-scan is queued for a later release. Do not implement from this seam. For design decisions see the GP-131 spec at `research_areas/private/specs/active/mission/GP-131_work_discovery_loop_spec.md` § Reconstruction Audit.
>
> Preserved verbatim below for reasoning-trail continuity.

---

Status: SUPERSEDED (was: opening)
Opened: 2026-04-20
Superseded: 2026-04-23
Parent: GP-105 (M-Form Alignment Audit — in-loop tactical layer)
Successor: GP-131 (Work-Discovery Loop)
Layer: ex-post strategic (cron-triggered, cross-run, apparatus-modifying)

## Eigenquestion

> When the apparatus detects a systematic failure pattern across completed runs,
> can it generate a Supervisor Goal that modifies its own structure — and does
> this self-modification produce measurably better outcomes on subsequent runs?

## Relationship to GP-105

GP-105 has two complementary layers:

| Layer | GP-105 (in-loop) | GP-105b (ex-post) |
|-------|-------------------|---------------------|
| Trigger | Stochastic, per-iteration | Cron/batch, cross-run |
| Scope | Single run, single rubric | All completed runs, all domains |
| Action | Append adversarial criterion to rubric | Create Supervisor Goal → modify apparatus code/config |
| Speed | Same-run (next iteration) | Next-run (or next operator session) |
| Risk | Low (rubric weight rebalance) | High (structural code change) |
| Feedback signal | Score improvement in same run | Score/yield improvement across runs |

GP-105 catches Goodhart within a run. GP-105b catches structural weaknesses across runs.

## Problem Statement

The in-loop tactical layer (GP-105) detects specification-level Goodhart: the rubric
drops charter requirements, the mutator optimizes a narrow proxy. But it cannot:

1. Detect apparatus-level failures that recur across projects (e.g., "committee rotation
   always suppresses stagnation in qualitative mode" — the bug we just fixed)
2. Generate code changes, grammar changes, or gate modifications
3. Prioritize which structural fixes have the highest expected improvement
4. Close the PDCA loop: verify that a structural change actually improved outcomes

These require an **ex-post scanner** that reads completed-run artifacts, identifies
systematic patterns, and creates actionable Supervisor Goals.

## Input Artifacts (what the scanner reads)

- `goodhart_log.jsonl` — GP-105 findings across runs (cross-run persistent)
- `iteration_telemetry.jsonl` — per-iteration scores, stagnation, actions
- `latent_distance.jsonl` — structural motion records
- `eval_history.jsonl` — judge scores and eval details
- `workspace/latest_information_yield.json` — yield decisions and rationale
- `research_areas/EXPERIMENT_TRACK_RECORD.md` — E/F row outcomes
- Seam postmortems (F-rows) — failure analysis from completed experiments

## Output Artifacts (what the scanner produces)

- **Supervisor Goal** (via existing supervisor loop infrastructure):
  - `goal_type: "apparatus_improvement"`
  - `source: "gp105b_expost_scanner"`
  - `priority: <computed from recurrence and severity>`
  - `evidence: <references to specific runs/iterations>`
  - `proposed_action: <seam to open / spec to write / code to change>`

- **Cross-run pattern log** (`rubrics/apparatus_patterns.jsonl`):
  - Systematic failures detected
  - Which runs exhibited them
  - Whether a prior fix resolved them (PDCA closure)

## Architecture Sketch

```
┌─────────────────────────────────────────────────┐
│  Trigger: cron / operator / post-run hook        │
│  (NOT in the autoresearch_loop — separate entry) │
└───────────────┬─────────────────────────────────┘
                │
    ┌───────────▼───────────────┐
    │  1. Artifact Collector     │
    │  Read telemetry, logs,     │
    │  experiment track record   │
    │  from ALL completed runs   │
    └───────────┬───────────────┘
                │
    ┌───────────▼───────────────┐
    │  2. Pattern Detector       │
    │  (LLM + heuristic)        │
    │                            │
    │  Heuristic triggers:       │
    │  - stagnation=0 for N+     │
    │    non-improving iters     │
    │  - pivot never fires       │
    │  - score oscillation w/o   │
    │    convergence             │
    │  - same weakest_point      │
    │    across runs             │
    │  - goodhart_log.jsonl has  │
    │    >2 entries same domain  │
    │                            │
    │  LLM synthesis:            │
    │  "What structural weakness │
    │   explains this pattern?"  │
    └───────────┬───────────────┘
                │
    ┌───────────▼───────────────┐
    │  3. Goal Generator         │
    │  Maps pattern → action:    │
    │  - Open seam               │
    │  - Modify gate config      │
    │  - Adjust yield thresholds │
    │  - Add new fixture test    │
    │  - Flag for operator       │
    └───────────┬───────────────┘
                │
    ┌───────────▼───────────────┐
    │  4. Supervisor Goal Emit   │
    │  Uses existing supervisor  │
    │  loop: backlog → proposal  │
    │  → manifest → execution   │
    └───────────────────────────┘
```

## Constraints

1. **Read-only on completed runs**: scanner never modifies artifacts of completed runs.
2. **Operator approval gate**: generated Goals are proposals, not auto-executed. The
   operator reviews before the supervisor loop picks them up.
3. **PDCA closure**: every Goal emitted must be tracked. When the next run completes
   in the same domain, the scanner checks whether the structural change improved the
   target metric. If not, the Goal is marked `ineffective` and the pattern is flagged
   for manual review.
4. **Cross-family model**: the pattern detector LLM must be a different family from
   the mutator/judge used in the runs it's analyzing (same M-Form separation as GP-105).
5. **No recursive depth > 1**: the scanner can propose changes to the apparatus, but
   it cannot propose changes to itself. Self-modification of the scanner requires
   operator intervention. (Prevents recursive Goodhart on the Goodhart detector.)

## Existing Infrastructure to Reuse

- **Supervisor loop** (`src/ztare/supervisor/`): Goal creation, backlog, proposal,
  manifest, staging, execution — all already built (Turn 55, closed).
- **goodhart_log.jsonl**: GP-105 already writes cross-run findings here.
- **EXPERIMENT_TRACK_RECORD.md**: F-rows already contain failure analysis.
- **reflexive_audit.py**: `AuditVerdict` enum already includes `GOODHARTED_SPECIFICATION`.

## What's New (must be built)

1. **`src/ztare/validator/expost_scanner.py`** — the artifact collector + pattern detector
2. **Heuristic triggers** — pattern-matching rules on telemetry (stagnation stuck,
   pivot never fires, score oscillation, etc.)
3. **Goal emission bridge** — adapter that converts scanner findings into supervisor
   Goal format
4. **Makefile target** — `make expost-scan PROJECT=<project>` or cron-triggered
5. **PDCA tracker** — `apparatus_patterns.jsonl` with status tracking

## Debate Log

_No debate yet. Seam opened for sketching. Debate to be scheduled after the in-loop
GP-105 and stagnation bug fix stabilize._

## Next Actions

- [ ] Sketch heuristic triggers (which telemetry patterns → which structural hypotheses)
- [ ] Design Goal format for `apparatus_improvement` type
- [ ] Debate: should the scanner run automatically after every `make loop`, or only on operator request?
- [ ] Prototype: run scanner on seattle_tech_housing telemetry to validate that it would have detected the `verified_axioms_added` stagnation bug
