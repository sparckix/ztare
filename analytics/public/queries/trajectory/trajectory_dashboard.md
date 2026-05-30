# ZTARE Apparatus Trajectory Dashboard

_Generated 2026-05-06T20:38:49.390254+00:00_

_Weeks observed:_ 7  
_Real inflections (≥3 metrics):_ 1  
_Candidate inflections (≥2 metrics):_ 0

## Sparklines per metric

```
  Weeks:                                    03-23 03-30 04-06 04-13 04-20 04-27 05-04

  Soph-A capability cumulative ▁▁▁▂▄▅█  (last: 869)
  Soph-D autonomous actions    ▁▁▁▁▂█▁  (last: 288)
  Insight-A F-row creates      ▁▁▁▂▂█▇  (last: 162)
  Insight-B F-row closures     ▁▁▁▆▁█▃  (last: 1)
  Insight-C paper-line growth  ▁▁▁▁▁▃█  (last: 8830)
  Insight-D project artifacts  ▁▅▂▃█▆▂  (last: 1272)
  Insight-E verified axioms    ▁█▁▁▁▁▁  (last: 11)
  Confound-A code activity     ▁▁▁▅█▃▇  (last: 206)
  Confound-B total creates     ▁▁▂▅▇▃█  (last: 650)

  --- TASTE-WEIGHTED INSIGHT (cold-rater scores 0-5, N=10/week) ---
  Taste mean (0-5)              █▆▃▁▄▆▃  (last: 2.2)
  Taste max (0-5)               ▁▁▁▁▁▁▁  (last: 4.0)
  Taste high-quality count (≥4) ▁▃▅▃█▆▅  (last: 4.0)
```

## Detailed weekly table

| Week | Inflection | Soph-A cum | Soph-D auto | Ins-A creates | Ins-B closures | Conf-A activity | Conf-B all creates | External events |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2026-03-23 |  |  | 0 | 0 | 0 | 0 | 0 | ZTARE project began (~40-50 days before  |
| 2026-03-30 |  |  | 0 | 0 | 0 | 0 | 9 | — |
| 2026-04-06 |  | 9 | 0 | 0 | 0 | 0 | 128 | — |
| 2026-04-13 |  | 161 | 0 | 32 | 2 | 140 | 360 | Pace anxiety surfaced — Erdős + Odrzywoł; GPT-4.1 added as default fallback (Gemin |
| 2026-04-20 |  | 434 | 444 | 28 | 0 | 252 | 601 | Mungerian thinking codified into core ph |
| 2026-04-27 | **★ REAL** | 538 | 4715 | 187 | 3 | 90 | 182 | — |
| 2026-05-04 |  | 869 | 288 | 162 | 1 | 206 | 650 | Sonnet 4.6 → Opus 4.7 (1M context) for t; GPU link-prediction prep (Adamic-Adar ba; Lemma-relevance ranker v1/v2/v4/v5/v |

## Auto-detected real inflections (≥3 of 6 metrics step-change)

| Week | Convergence | Metrics with step-change | External events that week |
|---|---:|---|---|
| 2026-04-27 | 3/6 | sophistication d autonomous ac, insight a f row creates , insight b f row closures  | — |

## Candidate inflections (2 metrics — weaker signal)

(none)

## Volume vs taste — cross-cutting finding

Volume metrics (Soph-D, Ins-A, Ins-C, Ins-D) and taste metrics (mean / max / high-quality count) tell different stories on the same trajectory. Read the sparklines above looking for:

  - Weeks where volume rose AND taste rose → real apparatus acceleration
  - Weeks where volume rose BUT taste fell → busywork / consolidation, not breakthrough
  - Weeks where volume was flat BUT taste rose → quiet but deep work; under-attributed by volume-only metrics
  - Weeks where both rose then taste plateaued → diminishing returns on the current track


## Operator interpretation prompt

The data has chosen the inflection candidates from the trajectory record, not from your memory. Read the table above and the real inflections list, then write a calibration note in this file (or a follow-up seam) answering:

  1. **Did the auto-detected inflection week(s) match your intuition?** If the operator's pre-Compaction sense was 'we're accelerating today (2026-05-06)' but the detector says the real inflection was a week or two earlier, that's calibration data.

  2. **What architectural moves landed in the inflection week(s)?** Look at git log / file mtimes for the days inside the inflection week. Name the load-bearing change(s).

  3. **Are there inflections you expected to see that DIDN'T appear?** Those are evidence that your intuition was attributing more to a particular move than the data supports.

  4. **Sham-arm question:** is Confound-A (general code activity) or Confound-B (total artifact creation) ALSO inflected at the real-inflection week? If yes, the apparatus story is at least partly confounded by general activity volume.


## Caveats and known limitations

  - **N=6 weeks** is too short for proper change-point detection. All findings here are exploratory, not inferential. Re-run weekly to grow N.
  - **File-mtime as creation date** is approximate. Files edited today get bumped to today's mtime even if they were authored a month ago.
  - **Soph-B (recursive depth) and Soph-C (operator-labor-displaced)** are NOT in this dashboard — both require operator curation.
  - **Ops dashboard, not research finding.** Per GP-227 panel: do not cite this as evidence of acceleration without re-generation under stricter discipline.
