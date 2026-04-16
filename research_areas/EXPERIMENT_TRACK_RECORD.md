# ZTARE Track Record — Public Mirror

## Status

Active — 2026-04-13 16:29:32 EDT (sanitized public mirror of the private experiment / hypothesis ledger)

## Why This Exists

This file is the public-facing track record for ZTARE's experiments and promoted knowledge claims.

It is intentionally lightweight:

- short enough to scan
- specific enough to audit
- stable enough to cite

The canonical full-detail ledger lives in `research_areas/private/EXPERIMENT_TRACK_RECORD.md` and includes unpublished experiments, active private findings, and methodology-sensitive rows omitted here under the visibility rule.

## Public-Safe Completed Experiments

| ID | Recorded | Window | Result | What changed | So What | Source |
|---|---|---|---|---|---|---|
| E-GP011-01 | `2026-04-13` | Derived-constraints lane verifier | `positive` | Typed derived constraints were verified in production across multiple EU runs. | Lessons learned by the system now persist and carry forward to future runs | `research_areas/seams/GP-011_derived_constraints_lane_seam.md` |
| E-GP021-01 | `2026-04-13` | Topological pivot heuristics verifier | `positive` | Pivot-profile selection was verified in production for both V4 and non-V4 contexts. | When stuck, the system now picks a typed recovery strategy instead of retrying blindly | `research_areas/seams/GP-021_topological_pivot_heuristics_seam.md` |
| E-GP022-01 | `2026-04-13` | Forecast project typing verifier | `positive` | Forecast typing and directional-project percentage caps were verified in production. | Forecasts cannot score perfectly unless they are actually testable | `research_areas/seams/GP-022_forecast_project_typing_seam.md` |
| E-GP027-01 | `2026-04-13` | Evidence compile reuse observation | `note` | A public-safe ergonomics finding was captured: recompilation still repays for unchanged inputs, motivating a reuse/cache lane. | Same evidence gets re-processed for no new insight; wastes cost | `research_areas/seams/GP-027_evidence_compile_reuse_seam.md` |

## Public-Safe Knowledge Claims

| ID | Claim | Current status | So What | Source |
|---|---|---|---|---|
| F-GP011-01 | Derived constraints belong as typed evidence-RAM artifacts rather than ad hoc prose residue. | `verified` | Structure your lessons learned or they get lost between runs | `research_areas/seams/GP-011_derived_constraints_lane_seam.md` |
| F-GP021-01 | Stagnation pivots can be selected by typed heuristic profile rather than one monolithic fallback. | `verified` | Different kinds of "stuck" need different recovery moves | `research_areas/seams/GP-021_topological_pivot_heuristics_seam.md` |
| F-GP022-01 | Forecast claims require project-typed scoring discipline; a naked `%` is not universally comparable. | `verified` | "60% likely" means nothing without a testable commitment | `research_areas/seams/GP-022_forecast_project_typing_seam.md` |

## Omitted From Public Mirror

Additional rows exist in the private canonical ledger and the private board mirror. They are omitted here when they would:

- expose runtime-discovered exploit patterns
- disclose unimplemented methodology primitives
- reveal first-mover research or product surfaces before shipment

The omission is structural, not a status downgrade.
