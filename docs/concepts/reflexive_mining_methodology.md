---
description: "Canonical methodology, root-cause analysis, and prevention checklist for the weekly reflexive-mining and taste-rating practice."
---

# Reflexive Mining & Taste-Rating — Canonical Methodology + RCA

> **Up:** [Documentation map](../README.md)

**Status:** authoritative. Read this BEFORE running the weekly reflexive-mining
practice or any taste-rating. Supersedes scattered docstring/ledger-implicit
guidance. Created 2026-05-16 after a procedure-inversion incident (RCA §3).

This single file is the source of truth (consolidated on purpose — see §5).

---

## 1. What the reflexive practice is

A weekly cadence: re-mine every artifact the project produced, score a
de-biased sample for *insight density* (not volume), rebuild the dashboard,
and read the week-over-week delta. The point is to separate **volume**
(always rises) from **insight** (the thing recursive gain would actually
move). The dashboard/website is part of the story: the architecture
observing itself.

## 2. Canonical procedure (run in this order)

All scripts live in `scripts/public/mining/`. Paths below are the canonical
post-reorg locations (see §4 for the path bugs that were fixed to make these
true).

| # | Step | Command | Output |
|---|------|---------|--------|
| 1 | Snapshot prior archive | `cp analytics/public/ledgers/trajectory/trajectory_archive*.jsonl /tmp/mine_baseline_<date>/` | baseline for the delta |
| 2 | Stage-1 extract | `python3 scripts/public/mining/mine_trajectories.py` | `analytics/public/ledgers/trajectory/trajectory_archive.jsonl` |
| 3 | Stage-1 enrich | `python3 scripts/public/mining/mine_trajectories_enrich.py` | `…/trajectory_archive_enriched.jsonl` |
| 4 | Trajectory curves | `python3 scripts/public/mining/mine_trajectory_curves.py` | `queries/trajectory/trajectory_curves.json` |
| 5 | Inflections | `python3 scripts/public/mining/detect_inflections.py` | `queries/trajectory/inflection_candidates.json` |
| 6 | Reference graph | `python3 scripts/public/mining/mine_reference_graph.py` then sync to `queries/graphs/` | `queries/reference_graph.json` |
| 7 | Consequential artifacts | `python3 scripts/public/mining/build_consequential_artifacts.py` | `queries/trajectory/consequential_artifacts_by_week.json` |
| 8 | Context primer | `python3 scripts/public/mining/build_context_primer.py` | `queries/taste/_taste_context_primer.md` |
| 9 | Recursive-gain candidates | `python3 scripts/public/mining/mine_recursive_gain_candidates.py` | `queries/trajectory/recursive_gain_candidates.json` |
| 10 | Sample for taste | `python3 scripts/public/mining/sample_artifacts_for_taste.py` | `queries/taste/_taste_sample.md` + `_taste_metadata.json` |
| 11 | **Rate — PRIMARY: contextualized/warm** | warm agent reads primer + sample → ratings | `queries/taste/_taste_ratings_contextualized.md` |
| 12 | Rate — CONTROLS only | cold (no primer) + cross-family (codex) | `_taste_ratings.md`, `_taste_ratings_crossfamily.md` |
| 13 | Aggregate (segregated) | `python3 scripts/public/mining/aggregate_taste.py --rater-id cold_subagent_contextualized` | `queries/taste/taste_weighted_insight.json` |
| 14 | Dashboard | `cd analytics/public/dashboard && bash scripts/refresh-data.sh && npm run build` | `dist/index.html` |
| 15 | Delta | compare step-13 output **within the same `rater_id` series** vs prior week | the recursive-gain read |

### 2.1 THE RATER RULE (the rule that was broken)

- **The canonical rater is the CONTEXTUALIZED (warm) rater.** It is given
  `_taste_context_primer.md` so it can tell domain-significant work
  (meta-architecture, NS/Clay residual structure, pre-GNN/proof-composition,
  recursive-gain machinery) from generic-looking prose. The historical
  series in `taste_ledger.json` is `rater_id = cold_subagent_contextualized`
  (154 entries as of 2026-05-16). **Week-over-week gain is judged on this
  series and only this series.**
- The **cold** rater (no primer) and the **cross-family** rater (codex/GPT)
  are **CONTROLS**: they bound rater bias and confirm a signal is not a
  single-model artifact. They are NOT the primary series and must NOT be
  aggregated into it.
- `build_context_primer.py`'s own docstring states the cold rater is
  deficient ("never gives ≥5 because it has no codebase context"). Cold is
  the floor, not the measurement.
- `aggregate_taste.py --rater-id` **defaults to `cold_subagent`** and the
  script pools all ledger rows regardless of `rater_id`. ALWAYS pass
  `--rater-id cold_subagent_contextualized` for the canonical run. Never run
  it bare.

---

## 3. RCA — taste-rating procedure inversion (2026-05-16)

**Incident.** During the weekly reflexive run, the cold rater was used as the
primary instrument and `aggregate_taste` was run with no `--rater-id`,
pooling 59 `cold_subagent` rows into the 154-row `cold_subagent_contextualized`
series. A "flat / no exponential recursive gain" verdict was stated on this
wrong, contaminated instrument before being retracted.

**Impact.**
1. Recursive-gain verdict made on the floor instrument (cold), not the
   canonical one (contextualized).
2. `taste_weighted_insight.json` for this cycle is contaminated
   (two rater methodologies pooled); week-over-week comparability broken
   until re-aggregated segregated by `rater_id`.
3. No data loss (append-only ledger intact); remediation is re-aggregation,
   not ledger rewrite.

**Five whys.**
1. Verdict used the wrong instrument → cold rater was run as primary.
2. Why cold → followed `rate_artifacts_for_taste.py --mode cold-agent`, the
   most discoverable codified path, whose instruction string asserts
   "You are deliberately a COLD agent" as if that were canonical.
3. Why that path and not the canonical procedure → the saved methodology was
   not retrieved before acting; no 3-source check (primer docstring + ledger
   `rater_id` history + prior `_taste_*_contextualized` artifacts), each of
   which independently says contextualized is canonical.
4. Why skipped → under rapid multi-directive execution pressure, anchored on
   the first codified script path and constructed a plausible "de-biasing"
   justification. This is the scientific-amnesia / anchoring failure already
   named in operator memory.
5. Why possible & undetected → **systemic, not just operator error**: there
   was no authoritative methodology doc; the wrong path is more discoverable
   than the right one; `aggregate_taste` silently pools across `rater_id`.

**Root cause.** Documentation/tooling gap (§5 G7, G8): the canonical
procedure was implicit and the wrong path was the path of least resistance.

## 4. Code/doc gaps found this session (and fix status)

| ID | Gap | Status |
|----|-----|--------|
| G1 | `mine_trajectories.py` `ARCHIVE_PATH` stranded at pre-reorg `analytics/trajectory_archive.jsonl` | FIXED → canonical path |
| G2 | `mine_trajectories_enrich.py` `ARCHIVE_IN/OUT` same staleness | FIXED |
| G3 | `build_consequential_artifacts.py` `OUT_JSON` missing `trajectory/` subdir (wrote where dashboard does not read) | FIXED |
| G4 | `dashboard/scripts/refresh-data.sh` `REPO_ROOT` off-by-one (`../..` from `analytics/public/dashboard` → `analytics`, not repo root). Silent placeholder fallback → **served stale dashboards undetected** | FIXED → `../../..` |
| G5 | `rate_artifacts_for_taste.py` `--mode parse-existing` branch exists in code but absent from argparse `choices` → unreachable via CLI | OPEN (non-blocking; `aggregate_taste` reads `.md` directly) |
| G6 | `reference_graph.json` writer path vs `graphs/` reader path inconsistency | MITIGATED (sync copy); structural fix OPEN |
| G7 | No authoritative methodology doc; canonical procedure implicit; `--mode cold-agent` instruction string asserts coldness as if canonical | FIXED by THIS doc; instruction-string correction recommended |
| G8 | `aggregate_taste.py --rater-id` defaults to `cold_subagent`; pools all `rater_id`s into one curve | OPEN — recommend: require explicit `--rater-id`; segregate weekly curve by `rater_id` |

## 5. Consolidation plan (operator preference: fewer files)

The pipeline is ~13 scripts writing ~10 query JSONs. The path-bug class (G1–G4,
G6) exists *because* paths are duplicated across many scripts. Recommended:

- **One orchestrator** `scripts/public/mining/run_reflexive_mine.py` that runs
  steps 2–13 in order, owns the canonical paths in one place, defaults the
  rater to `cold_subagent_contextualized`, and fails loudly instead of
  silent-placeholder fallback. Single entrypoint = the path-bug class cannot
  recur and the procedure cannot be inverted.
- **Fewer outputs**: the dashboard's six core JSONs can be emitted as one
  `dashboard_bundle.json` by the orchestrator; `refresh-data.sh` then copies
  one file. Reduces the contract surface that drifts.
- This methodology doc stays the single source of truth (do not re-scatter
  into per-script docstrings; point docstrings here instead).

## 5b. The orchestrator (built 2026-05-16)

`scripts/public/mining/run_reflexive_mine.py` is now the single canonical
entrypoint. It owns every canonical path in one place, runs phases in order,
fails loud (no silent placeholder / no cold fallback), and ends with the
mandatory dashboard rebuild. G5 (`parse-existing` reachable), G6
(reference_graph `graphs/` sync), G8 (aggregate rater-segregation) fixed.

- `--index-only`: Phase 1 only — exhaustive, deterministic, ZERO tokens.
- Phase 3 is a hard gate: requires fresh CONTEXTUALIZED ratings newer than
  the sample, else STOP. The cold-fallback path that caused the §3 incident
  cannot recur.

**First exhaustive index (2026-05-16):** 34,417 authored artifacts
(48,045 generated/vendored excluded). **Bifurcation: iter-loop 7,355 (21%)
vs agent-work 27,062 (79%).** The ZTARE iter-loop is ~1/5 of authored
output; the live substrate is out-of-loop. This is the empirical anchor for
the in-loop/out-of-loop architecture question — see
`analytics/public/ledgers/reflexive/bifurcation_report.json`.

**Bounded follow-up (not yet done):** the taste *sampler* still gathers
projects/research_areas/papers/analytics/memory; extending its `_gather_*`
to ztare_proofs authored `.lean` + scripts authored `.py` would close the
last rating-coverage gap (the INDEX already covers them; only rating is
sampler-scoped). Tracked separately to avoid sampler+ledger-schema churn.

## 5c. Cycle status + known structural limits (2026-05-16)

Full orchestrated cycle runs end-to-end: index → miners → impact (2b) →
gate → G8-segregated aggregate → dashboard. Known limits, documented so
they are not rediscovered:

- **`aggregate_taste` is sample-scoped, not the full historical series.**
  It builds the weekly curve from the *current sample's* cached/fresh
  scores, not the full rater-segregated ledger. For the true contextualized
  week-over-week curve, compute read-only from `taste_ledger.json` filtered
  by `rater == cold_subagent_contextualized` (that is the source of truth:
  it gave the real rising 1.83→2.80 over 7 weeks, plateau+downtick 05-11).
- **`mine_climb_triggers.py`** is best-effort (G-class debt): missing
  reorg-deleted `weakest_link_clusters_*.json` input. WARN-not-fatal in
  Phase 2b; the central ROI + index-render still run.
- **Gate refinement:** `n_new == 0` (fully cache-served) passes the rate
  gate by construction — re-rating unchanged content is forbidden waste.
- Canonical path knowledge is collapsed into
  `scripts/public/mining/_canonical_paths.py` (the warranted file-collapse;
  the 13 scripts stay modular by design — merging them would be an
  anti-pattern).
- **Authored-week binning is GIT-DATE-robust (2026-06-04).**
  `mine_trajectory_curves._file_create_date` now derives a file's creation week from
  `frontmatter date > git first-commit (authored) date > birthtime > mtime`. A bulk checkout/restore
  resets BOTH `st_birthtime` AND `st_mtime` to "now" (observed: a bulk re-create dumped ~every file's
  birthtime to 2026-06-01) and Linux has no birthtime — git's authored date survives all of it. The
  contextualized TASTE series was ALREADY robust (it groups by the STORED `first_seen_week` in the
  ledger, never a re-stat, + content-hash cached), so the bulk change did NOT corrupt the realized-gain
  trajectory; the git-date fix hardens the VOLUME curves to match.
- **Realized recursive-gain is now MEASURED, not just candidate-recommended (2026-06-04).** The p0
  rollup carries `realized_primitive_gain` (exogenous `impact_factor_expost`, carrier-split,
  `self_measured=false`), `recursive_gain_trajectory` (the taste series + a `stale_days` silent-rot
  guard), and a `dead_letter_rate` repaired to an exogenous catch-ledger join. The candidate aggregator
  is the FORWARD recommender; these are the BACKWARD realized measure (read together). See GP-236 §3.4.
- **Producer re-fire (P1, 2026-06-04).** `run_reflexive_mine.phase2_mine` now runs the candidate
  aggregator's producer miners (`mine_closure_patterns`, `mine_structural_analogies`) BEFORE the
  consumer, so candidates reflect current work (was stale-by-construction: month-old scorecards, 0
  leanmill mentions).

## 5d. The per-graph "so what" (operator-mandated 2026-05-16)

Raw charts mislead — a *cumulative* line always rises; that is arithmetic,
not progress. Every graph carries a one-line **"so what"** takeaway,
**authored in flight by the agent doing that week's update** (the one who
just ran the mine, saw the adversary results, and knows what actually
matters this cycle). It is NOT templated/deterministic — templates cannot
say "Soph-D collapsed to 20 because the iter-loop didn't run, and that
metric mismeasures autonomy anyway."

Procedure (new canonical step, between aggregate and dashboard):

1. The updating agent reads `build_graph_sowhat.py`'s numbers digest.
2. The agent authors `analytics/public/queries/graph_sowhat.json`
   (`panels.<k>.{headline,detail,trend}`) for: bifurcation, sophistication,
   insight_volume, taste, compounding, recursive_gain — grounded in THIS
   cycle's verified numbers, honest about caveats (e.g. Soph-D measures
   dormant-loop cage engagements, not out-of-loop RD/agent autonomy).
3. `build_graph_sowhat.py` runs as a **freshness gate** (orchestrator
   Phase 4b): fail-loud if the file is missing, missing a panel, or older
   than the fresh bifurcation report — i.e. last week's interpretation must
   not ship over this week's data. Full-cycle order therefore is:
   mine → author so-what from fresh numbers → resume (gate → dashboard).
4. The dashboard renders `headline` (and `detail`) above each chart.

Known methodology gap surfaced this cycle: **Soph-D ("autonomous actions")
instruments only the dormant ZTARE iter-loop (`cage_engagement.jsonl`); it
is not a P0 autonomy metric.** The real autonomous-activity signal is the
out-of-loop artifact volume (Bifurcation panel). Tracked under the P0
metrics rollup seam task.

## 6. Prevention checklist (run before every reflexive cycle)

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
