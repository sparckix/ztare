# GP-221 — Seam Health Telemetry

> **Seam metadata** · `seam_id:` GP-221 · `track:` apparatus · `status:` open - opened 2026-05-06 · `last_updated:` 2026-05-09


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-05-06

## ID

GP-221

## Eigenquestion

The seam corpus (`research_areas/private/seams/`) has accumulated
~200 seam files across 12+ months. Some are decisive references
in current work; some are forgotten; some are orphans (seam shipped
but spec never written; spec written but implementation never wired;
seam open but contradicted by later work). Which seams are actually
alive — and how does an operator detect when one has rotted?

## Problem Statement

Reflexive engineering applied to the seam corpus itself. ZTARE has
`reflexive_audit.py` (GP-102) for telemetry-shaped failures, and
the proposed GP-220 for primitive ROI. There's no analogous audit for
**the seam corpus's own health**.

Failure modes in seam corpus:

1. **Stale seam, current code:** seam was written 8 months ago,
   referenced rubric/path that no longer exists. Reading the seam
   misleads about current state.
2. **Orphan seam:** seam scoped a problem, no spec or code followed.
   Either the problem went away, or the principal forgot, or the
   seam was wrong.
3. **Implemented-but-unmarked:** seam status is "open" but the work
   shipped under a different GP-XXX number. Index drift.
4. **Re-seamed:** the same problem got seamed twice 6 months apart
   with different vocabulary. Drift in operator memory.
5. **Contradicted seam:** seam X proposes mechanism A; later seam Y
   refutes A but doesn't update X's status. Reader of X gets a stale
   answer.

This isn't theoretical. The recent GP-128b status confusion
(subagent claimed not-shipped; actually shipped weeks ago) is
exactly failure mode #3. The reflexive_audit_report.json staleness
(3 weeks unrun until today) is failure mode #1 in the audit itself.

## Proposed Architecture

A periodic scan over `research_areas/private/seams/` that produces
a health report. Output:

```
analytics/public/queries/audits/seam_health_report.json:
{
  "scan_utc": "2026-05-06T16:30:00Z",
  "lookback_window_days": 60,
  "total_seams": 198,
  "by_status": {
    "open": 47, "shipped": 102, "deferred": 23, "no_status_field": 26
  },
  "stale_candidates": [
    {
      "seam_id": "GP-XXX",
      "path": "research_areas/private/seams/.../GP-XXX_*.md",
      "reason": "no F-row mention in 90+ days; status: open; references
                  paths that no longer exist (path1, path2)"
    }
  ],
  "orphan_candidates": [
    {
      "seam_id": "GP-YYY",
      "reason": "seam exists; no spec under research_areas/private/specs/{active,archived}/;
                  no code reference in src/ matching the seam's named primitive"
    }
  ],
  "implemented_unmarked": [
    {
      "seam_id": "GP-ZZZ",
      "reason": "status: open; but src/ contains the named primitive;
                  test for it exists; promote status to shipped?"
    }
  ],
  "potential_re_seam": [
    {
      "seam_a": "GP-AAA", "seam_b": "GP-BBB",
      "shared_keywords": ["X", "Y", "Z"],
      "reason": "8-month gap; >70% keyword overlap in eigenquestions"
    }
  ]
}
```

### Per-seam metrics

| Metric | How computed | Failure mode it catches |
|---|---|---|
| `last_referenced_utc` | most recent grep match in `research_areas/EXPERIMENT_TRACK_RECORD.md`, advisor channels, F-rows | stale (no recent reference) |
| `mention_frequency` | count of grep matches across recent 60d of F-rows | low engagement |
| `referenced_paths_exist` | for each `path/to/x` mentioned in seam body, does it exist? | path drift |
| `status_consistency` | declared status (open/shipped/deferred) vs implementation evidence | implemented_unmarked / orphan |
| `re_seam_candidates` | text-similarity (Jaccard on noun-phrase bigrams) against other seams older than 30d | duplication / drift |

### Verdict bands

- **alive**: referenced in last 30d AND status_consistency OK
- **stale**: not referenced in 60+d AND status: open
- **orphan**: status: open AND no spec AND no code reference matching seam's named primitive
- **implemented_unmarked**: status: open BUT code/test reference exists for the named primitive
- **path_drift**: referenced_paths_exist < 80%
- **re_seam_candidate**: shares >70% noun-phrase bigrams with another seam from >30d ago

## Implementation

`scripts/public/audits/seam_health_audit.py`:

```python
def main():
    seams = list_all_seams(REPO / "research_areas/private/seams/")
    f_rows = read_f_rows(REPO / "research_areas/EXPERIMENT_TRACK_RECORD.md", days=60)
    code_index = build_code_index(REPO / "src/")
    spec_index = list_specs(REPO / "research_areas/private/specs/")
    
    health = []
    for seam in seams:
        m = compute_metrics(seam, f_rows, code_index, spec_index)
        health.append(m)
    
    # Re-seam detection: pairwise on seams older than 30d
    re_seam_pairs = detect_re_seams(seams, threshold=0.7)
    
    write_report(REPO / "analytics/public/queries/audits/seam_health_report.json", health, re_seam_pairs)
```

## Cadence

Author as KR `kr_seam_health_periodic` with P30D recurrence (slower
than the per-substrate audit cycle; seam corpus changes more slowly
than per-iter telemetry). Owner: `role.research_director` (RD has
the M-form authority over seam authoring).

## Scope

**Covers:**
- File-level health metrics across the seam corpus
- Status-consistency check (declared vs implemented)
- Re-seam pair detection (likely-duplicate seams)
- Path-drift detection (broken file references)
- Output: `analytics/public/queries/audits/seam_health_report.json`

**Does not cover:**
- Auto-archival of stale seams (creative judgment required)
- Auto-merging of re-seam pairs (human disposition)
- Seam-quality assessment (does the seam ask the right question? out
  of scope; that's the operator's domain)
- Forward-looking work (which new seams should exist?) — that's
  GP-102's domain

## Why this is a real seam

1. **It applies the apparatus's anti-staleness discipline to the
   apparatus's own seam corpus.** The same hygiene that flags stale
   reflexive_audit_report.json applies to the very seams that
   describe the audits.

2. **The re-seam detection is non-trivial.** Without it, the
   apparatus naturally drifts toward duplicate seams as the operator
   forgets prior work. GP-220 + GP-221 + GP-128b inbound (and the
   stale GP-128 outbound) is likely such a cluster — three telegram
   seams over six months with overlapping vocabulary.

3. **It's cheap.** No LLM calls; pure file-system + grep + simple
   string similarity. Could run nightly without budget concerns.

## Connection to other seams

- `GP-102` reflexive_primitive_discovery_seam.md — the parent
  pattern: periodic audit over apparatus telemetry. GP-221 applies
  the same logic to seam corpus telemetry.
- `GP-220` reflexive_primitive_roi_telemetry_seam.md — sibling.
  GP-220 audits primitive ROI; GP-221 audits seam-corpus health.
  Both flow into the operator's periodic-review surface.
- `MIRROR.md` — public/private mirror map. GP-221 should also
  cross-reference: when a seam's public derivative drifts, surface
  it.

## Honest failure modes

- **Re-seam detection is fuzzy.** Bigram Jaccard is a starting
  heuristic; will produce false positives (seams that share
  vocabulary but address genuinely different problems).
  Mitigation: report is suggestive only; the principal disposes.
- **Path-drift over-counts.** Seams reference example paths that
  intentionally don't exist (`path/to/foo` as an illustration).
  Mitigation: only count paths that match `src/`, `scripts/public/`,
  `org/`, `analytics/public/queries/`, `projects/` prefixes.
- **Status field absent on older seams.** 26 seams (per quick scan)
  have no `status:` frontmatter field. Audit either skips them or
  treats absent as `open`; report should distinguish "no status
  field" from "status: open".

## Relevant prior art / inspiration

The "documentation rot" problem is well-studied in industrial
software engineering (e.g., Treude+Robillard's work on stale API
docs). What's distinctive here: a seam IS a planning artifact,
not just documentation, and the rot detection has to consider
whether the planned work happened (status_consistency) — not just
whether the prose is current.
