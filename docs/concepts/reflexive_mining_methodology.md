---
description: "Weekly procedure for checking whether ZTARE produced reusable research structure, not just more files."
---

# Reflexive mining and taste-rating methodology

> Up: [Documentation map](../README.md)

*Status:* authoritative. Read this before running the weekly mining cycle or
any taste-rating. The command path below supersedes scattered docstrings and
ledger-only guidance.

---

## 1. What this practice checks

The weekly cycle has one job:

> Did the system produce more useful research structure this week, or only more
> files?

It re-mines authored files, rates a contextualized sample, rebuilds the
dashboard, and compares movement inside one rater series. File count rises
automatically. The useful question is whether the new files changed what the
system can do next: a better check, a cleaner route, a reusable primitive, a
stronger falsifier, or a demoted claim.

The mining cycle is a measurement surface. It can surface dead instruments,
coverage gaps, candidate primitives, and dashboard deltas. It does not grant
public-claim authority by itself. Public claims still need the evidence atlas,
claim register, review artifacts, or the relevant subsystem gate.

### Measurement contract

Treat the mining cycle as an instrument that reads the system. A valid
cycle must preserve four boundaries:

| Boundary | Rule |
|---|---|
| Rater identity | Compare only rows from the same `rater_id` series. Cold, contextualized, and cross-family scores are different instruments. |
| Sample scope | A weekly sample can reveal a signal or a gap. It cannot certify the whole repository. |
| Authority | Mining can recommend a primitive, repair, demotion, or audit. It cannot promote a public claim without the owning evidence surface. |
| Action | A dashboard movement should name the next inspection or repair for an agent to carry out. |

The strongest outcome of the cycle is not a higher score. It is a named
follow-up that a later agent can execute from files alone.

### Quick command choices

| Need | Command | Use this when |
|---|---|---|
| Free coverage and split check | `python3 scripts/public/mining/run_reflexive_mine.py --index-only` | You need to know what authored files exist and how much work was in-loop vs out-of-loop. |
| Full weekly cycle | `python3 scripts/public/mining/run_reflexive_mine.py` | You have the required rating setup and want the dashboard refreshed. |
| Resume after ratings | `python3 scripts/public/mining/run_reflexive_mine.py --resume-after-rating` | Sampling/rating already happened and you need gate, aggregate, and dashboard. |
| Skip dashboard build | `python3 scripts/public/mining/run_reflexive_mine.py --skip-dashboard` | You want the mined outputs without rebuilding the frontend bundle. |

The canonical rater is `cold_subagent_contextualized`. Cold and cross-family
ratings are controls. They are never pooled into the primary curve.

## 2. Canonical procedure

The normal command is the orchestrator:

```bash
python3 scripts/public/mining/run_reflexive_mine.py
```

Use the table below when debugging a phase or reviewing the contract. All
scripts live in `scripts/public/mining/`. The orchestrator is the product path.

| # | Step | Command | Output |
|---|------|---------|--------|
| 1 | Snapshot prior archive | `cp analytics/public/ledgers/trajectory/trajectory_archive*.jsonl mine_baseline_<date>/` | baseline for the delta |
| 2 | Stage-1 extract | `python3 scripts/public/mining/mine_trajectories.py` | `analytics/public/ledgers/trajectory/trajectory_archive.jsonl` |
| 3 | Stage-1 enrich | `python3 scripts/public/mining/mine_trajectories_enrich.py` | `…/trajectory_archive_enriched.jsonl` |
| 4 | Trajectory curves | `python3 scripts/public/mining/mine_trajectory_curves.py` | `queries/trajectory/trajectory_curves.json` |
| 5 | Inflections | `python3 scripts/public/mining/detect_inflections.py` | `queries/trajectory/inflection_candidates.json` |
| 6 | Reference graph | `python3 scripts/public/mining/mine_reference_graph.py` then sync to `queries/graphs/` | `queries/reference_graph.json` |
| 7 | Consequential artifacts | `python3 scripts/public/mining/build_consequential_artifacts.py` | `queries/trajectory/consequential_artifacts_by_week.json` |
| 8 | Context primer | `python3 scripts/public/mining/build_context_primer.py` | `queries/taste/_taste_context_primer.md` |
| 9 | Recursive-gain candidates | `python3 scripts/public/mining/mine_recursive_gain_candidates.py` | `queries/trajectory/recursive_gain_candidates.json` |
| 10 | Sample for taste | `python3 scripts/public/mining/sample_artifacts_for_taste.py` | `queries/taste/_taste_sample.md` + `_taste_metadata.json` |
| 11 | Rate: primary contextualized/warm series | warm agent reads primer + sample → ratings | `queries/taste/_taste_ratings_contextualized.md` |
| 12 | Rate: controls only | cold (no primer) + cross-family (codex) | `_taste_ratings.md`, `_taste_ratings_crossfamily.md` |
| 13 | Aggregate (segregated) | `python3 scripts/public/mining/aggregate_taste.py --rater-id cold_subagent_contextualized` | `queries/taste/taste_weighted_insight.json` |
| 14 | Dashboard | `cd analytics/public/dashboard && bash scripts/refresh-data.sh && npm run build` | `dist/index.html` |
| 15 | Delta | compare step-13 output **within the same `rater_id` series** vs prior week | the recursive-gain read |

### 2.1 Rater rule

- The primary series is `rater_id = cold_subagent_contextualized`.
- The contextualized rater reads `_taste_context_primer.md` before rating.
- Cold and cross-family raters are controls. They bound rater bias and do not
  enter the primary curve.
- Never compare a cold series to a contextualized series as if they were the
  same instrument.
- When calling `aggregate_taste.py` directly, pass
  `--rater-id cold_subagent_contextualized`. Do not run it bare.

### 2.2 Decision boundary

The weekly output can justify four kinds of follow-up:

| Output | Valid follow-up |
|---|---|
| Dead instrument or stale ledger | repair the instrument or demote the metric |
| Repeated residual or catch category | open a primitive/card/contract promotion review |
| Coverage gap | add a miner, sampler, or review artifact only if the missing region affects decisions |
| Rising or falling taste series | inspect the underlying sample before making a roadmap claim |

Avoid two shortcuts: treating a dashboard curve as public proof, and treating a
single rater score as a product decision. The mining cycle points to work. It
does not replace review.

### 2.3 What the cycle must emit

A useful run leaves a compact trail:

- coverage: what authored regions entered the index and what was excluded.
- ratings: which rater series was used and what sample it rated.
- deltas: what changed versus the prior comparable cycle.
- candidates: repeated residuals, candidate primitives, dead instruments, or
  source gaps worth inspecting.
- decision boundary: which findings are only measurements and which have an
  owning gate, evidence atlas entry, or roadmap item.

If a run cannot name at least one of "no material change", "repair this
instrument", "inspect this residual", or "promote/demote this claim through its
owner", the result is not decision-useful yet.

---

## 3. Incident: Taste-Rating Procedure Inversion (2026-05-16)

*Incident.* During the weekly reflexive run, the cold rater was used as the
primary instrument and `aggregate_taste` was run with no `--rater-id`,
pooling 59 `cold_subagent` rows into the 154-row `cold_subagent_contextualized`
series. A "flat / no exponential recursive gain" verdict was stated on this
wrong, contaminated instrument before being retracted.

*Impact.*
1. Recursive-gain verdict made on the floor instrument (cold) where the
   canonical contextualized instrument was required.
2. `taste_weighted_insight.json` for this cycle is contaminated
   (two rater methodologies pooled). Week-over-week comparability broken
   until re-aggregated segregated by `rater_id`.
3. No data loss (append-only ledger intact). Remediation is re-aggregation,
   not ledger rewrite.

*Why it happened.* The wrong path was more discoverable than the right one.
`rate_artifacts_for_taste.py --mode cold-agent` looked like the obvious
procedure, while the canonical contextualized series was implicit in prior
artifacts and ledger history. The aggregate command also allowed mixed rater
series.

*Root cause.* The method was not encoded as one authoritative runbook, and
the tooling did not force the rater boundary.

*Prevention.* The orchestrator and this document now own the path. The cold
path serves as a control, with the contextualized series as the primary instrument.

## 4. Code and documentation gaps found in that audit

| ID | Gap | Status |
|----|-----|--------|
| G1 | `mine_trajectories.py` `ARCHIVE_PATH` stranded at pre-reorg `analytics/trajectory_archive.jsonl` | FIXED → canonical path |
| G2 | `mine_trajectories_enrich.py` `ARCHIVE_IN/OUT` same staleness | FIXED |
| G3 | `build_consequential_artifacts.py` `OUT_JSON` missing `trajectory/` subdir (wrote where dashboard does not read) | FIXED |
| G4 | `dashboard/scripts/refresh-data.sh` `REPO_ROOT` off-by-one (`../..` from `analytics/public/dashboard` → `analytics`, not repo root). Silent placeholder fallback → **served stale dashboards undetected** | FIXED → `../../..` |
| G5 | `rate_artifacts_for_taste.py` `--mode parse-existing` branch exists in code but absent from argparse `choices` → unreachable via CLI | OPEN (non-blocking, `aggregate_taste` reads `.md` directly) |
| G6 | `reference_graph.json` writer path vs `graphs/` reader path inconsistency | MITIGATED (sync copy). Structural fix OPEN |
| G7 | No authoritative methodology doc, canonical procedure implicit, `--mode cold-agent` instruction string asserts coldness as if canonical | FIXED by this doc. Instruction-string correction recommended |
| G8 | `aggregate_taste.py --rater-id` defaults to `cold_subagent`, pooling all `rater_id`s into one curve | OPEN. Recommend: require explicit `--rater-id`, segregate weekly curve by `rater_id` |

## 5. Consolidation plan

The pipeline has many scripts and output contracts. The path-bug class (G1-G4,
G6) came from duplicated path knowledge. Keep the run path consolidated:

- One orchestrator `scripts/public/mining/run_reflexive_mine.py` that runs
  steps 2–13 in order, owns the canonical paths in one place, defaults the
  rater to `cold_subagent_contextualized`, and fails loudly on a missing or
  stale input. Single entrypoint = the path-bug class cannot
  recur and the procedure cannot be inverted.
- *Fewer outputs*: the dashboard's six core JSONs can be emitted as one
  `dashboard_bundle.json` by the orchestrator. `refresh-data.sh` then copies
  one file, reducing the contract surface that drifts.
- This methodology doc stays the single source of truth. Per-script docstrings
  should point here for the procedure.

## 5b. The orchestrator (built 2026-05-16)

`scripts/public/mining/run_reflexive_mine.py` is now the single canonical
entrypoint. It owns every canonical path in one place, runs phases in order,
fails loud (no silent placeholder / no cold fallback), and ends with the
mandatory dashboard rebuild. G5 (`parse-existing` reachable), G6
(reference_graph `graphs/` sync), G8 (aggregate rater-segregation) fixed.

- `--index-only`: Phase 1 only (exhaustive, deterministic, ZERO tokens).
- Phase 3 is a hard gate: requires fresh CONTEXTUALIZED ratings newer than
  the sample, else STOP. The cold-fallback path that caused the §3 incident
  cannot recur.

*First exhaustive index (2026-05-16):* 34,417 authored artifacts
(48,045 generated/vendored excluded). **Bifurcation: iter-loop 7,355 (21%)
vs agent-work 27,062 (79%).** The ZTARE iter-loop is ~1/5 of authored
output. The live substrate is out-of-loop. This is the empirical anchor for
the in-loop/out-of-loop architecture question. See
`analytics/public/ledgers/reflexive/bifurcation_report.json`.

*Bounded follow-up (not yet done):* the taste *sampler* still gathers
projects/research_areas/papers/analytics/memory. Extending its `_gather_*`
to ztare_proofs authored `.lean` + scripts authored `.py` would close the
last rating-coverage gap (the INDEX already covers them, but only rating is
sampler-scoped). Tracked separately to avoid sampler+ledger-schema churn.

## 5c. Cycle status + known structural limits (2026-05-16)

Full orchestrated cycle runs end-to-end: index → miners → impact (2b) →
gate → G8-segregated aggregate → dashboard. Known limits, documented so
they are not rediscovered:

- `aggregate_taste` is sample-scoped: it builds the weekly curve from the
  *current sample's* cached/fresh scores, covering that sample alone. For
  the full historical rater-segregated series and the true contextualized
  week-over-week curve, compute read-only from `taste_ledger.json` filtered
  by `rater == cold_subagent_contextualized` (that is the source of truth:
  it gave the real rising 1.83→2.80 over 7 weeks, plateau+downtick 05-11).
- `mine_climb_triggers.py` is best-effort (G-class debt): missing
  reorg-deleted `weakest_link_clusters_*.json` input. WARN-not-fatal in
  Phase 2b. The central ROI + index-render still run.
- Gate refinement: `n_new == 0` (fully cache-served) passes the rate
  gate by construction (re-rating unchanged content is forbidden waste).
- Canonical path knowledge is collapsed into
  `scripts/public/mining/_canonical_paths.py` (the warranted file-collapse;
  the 13 scripts remain modular by design, and merging them would be an
  anti-pattern).
- Authored-week binning is GIT-DATE-robust (2026-06-04).
  `mine_trajectory_curves._file_create_date` now derives a file's creation week from
  `frontmatter date > git first-commit (authored) date > birthtime > mtime`. A bulk checkout/restore
  resets BOTH `st_birthtime` AND `st_mtime` to "now" (observed: a bulk re-create dumped ~every file's
  birthtime to 2026-06-01) and Linux has no birthtime. Git's authored date survives all of it. The
  contextualized TASTE series was ALREADY robust (it groups by the STORED `first_seen_week` in the
  ledger, never a re-stat, + content-hash cached), so the bulk change did NOT corrupt the realized-gain
  trajectory. The git-date fix hardens the VOLUME curves to match.
- Realized recursive-gain is now MEASURED, an advance on the earlier candidate-recommended state (2026-06-04). The p0
  rollup carries `realized_primitive_gain` (exogenous `impact_factor_expost`, carrier-split,
  `self_measured=false`), `recursive_gain_trajectory` (the taste series + a `stale_days` silent-rot
  guard), and a `dead_letter_rate` repaired to an exogenous catch-ledger join. The candidate aggregator
  is the FORWARD recommender. These are the BACKWARD realized measure (read together). See GP-236 §3.4.
- Producer re-fire (P1, 2026-06-04). `run_reflexive_mine.phase2_mine` now runs the candidate
  aggregator's producer miners (`mine_closure_patterns`, `mine_structural_analogies`) BEFORE the
  consumer, so candidates reflect current work (was stale-by-construction: month-old scorecards, 0
  leanmill mentions).

## 5d. The per-graph "so what" (review-mandated 2026-05-16)

Raw charts mislead. A *cumulative* line always rises; that is arithmetic,
not progress. Every graph carries a one-line "so what" takeaway,
authored in flight by the agent doing that week's update (the one who
just ran the mine, saw the adversary results, and knows what actually
matters this cycle). It is NOT templated/deterministic. Templates cannot
say "Soph-D collapsed to 20 because the iter-loop didn't run, and that
metric mismeasures autonomy anyway."

Procedure (new canonical step, between aggregate and dashboard):

1. The updating agent reads `build_graph_sowhat.py`'s numbers digest.
2. The agent authors `analytics/public/queries/graph_sowhat.json`
   (`panels.<k>.{headline,detail,trend}`) for: bifurcation, sophistication,
   insight_volume, taste, compounding, recursive_gain, grounded in THIS
   cycle's verified numbers, honest about caveats (e.g. Soph-D measures
   dormant-loop cage engagements only, leaving out-of-loop RD/agent autonomy
   uncovered).
3. `build_graph_sowhat.py` runs as a freshness gate (orchestrator
   Phase 4b): fail-loud if the file is missing, missing a panel, or older
   than the fresh bifurcation report, i.e. last week's interpretation must
   not ship over this week's data. Full-cycle order therefore is:
   mine → author so-what from fresh numbers → resume (gate → dashboard).
4. The dashboard renders `headline` (and `detail`) above each chart.

Known methodology gap surfaced this cycle: **Soph-D ("autonomous actions")
instruments only the dormant ZTARE iter-loop (`cage_engagement.jsonl`) and
is not a P0 autonomy metric.** The real autonomous-activity signal is the
out-of-loop artifact volume (Bifurcation panel). Tracked under the P0
metrics rollup seam task.

## 6. Pre-cycle checklist

1. Read this file.
2. 3-source check that the rater is `cold_subagent_contextualized`
   (primer docstring + ledger `rater_id` history + prior contextualized
   artifacts).
3. `aggregate_taste.py` is invoked WITH `--rater-id cold_subagent_contextualized`.
4. Cold + cross-family are run as controls, kept in separate files, never
   aggregated into the primary series.
5. Verify dashboard `src/data/*` timestamps are fresh AFTER `refresh-data.sh`
   (guards against the G4 silent-stale class).
6. Compare the delta within one `rater_id` series only.
