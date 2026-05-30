---
seam_id: r-prefix-naming-convention
status: closed
discovered: 2026-05-06
owner: PM-of-ZTARE
---

# Reflexive Primitive Naming Convention — R-Prefix Catalog ID

> **Seam metadata** · `seam_id:` r_prefix_naming_convention · `track:` reflexive · `status:` closed · `last_updated:` 2026-05-09


## Decision (2026-05-06)

Reflexive primitives keep their **R-number catalog ID** as a stable
permanent identifier. User-facing reports always pair the R-number with
a descriptive name in the form **`R<N> (descriptive_name)`** so that
readers don't need to memorize what each R-number means.

## Why this convention

The 2026-05-06 PM "what is R8/R9/R10/R11/R12/R13/R14/R16" conversation
surfaced a real readability problem: bare R-numbers in chat / audit
output are opaque to a reader who hasn't internalized the catalog. The
remedies considered:

1. **Strip R-prefix entirely** (rename gate-emit strings) — rejected.
   58 references in src/, plus dependency edges (R11 depends on R10),
   plus 156 projects × cage_engagement.jsonl logging history. High
   regression risk for low aesthetic gain.

2. **Pair R-number with descriptive name in user-facing output** —
   adopted. The descriptive part of every gate name is already present
   (e.g. `R10_cross_class_extrapolation`). Audit reports just need to
   parse it out and display side-by-side.

## Where the convention applies

User-facing audit outputs that show primitive identity:

| Audit | Fixed 2026-05-06? |
|---|---|
| `analytics/public/queries/reflexive/reflexive_primitive_roi.md` | yes — `R13 (substrate_critic)` |
| `analytics/public/queries/audits/gate_telemetry_diagnosis.md` | yes — emits already descriptive (`R10_cross_class_extrapolation`) |
| `analytics/public/queries/audits/cross_audit_dashboard.md` | yes — `_label()` helper added |
| Seam writeups (research_areas/private/seams/reflexive/*.md) | yes — manual discipline going forward |
| Chat / Slack / commit messages | yes — manual discipline going forward |

## What stays as-is

- Gate(name=...) constructor strings — still `R<N>_descriptive_name`
- Gate dependency edges — still keyed on `R<N>_descriptive_name`
- Persisted JSONL telemetry — still logs `R<N>_descriptive_name`
- Internal error messages emitted from gate code — still `R<N>` is fine
  (reader has the source for context)

## When to revisit

If the R-numbering becomes ambiguous (collisions, holes, misleading
ordering) revisit. As of 2026-05-06 the catalog is:

| R# | Descriptive name | Source file |
|---:|---|---|
| R8 | feature_coverage_adequacy | src/ztare/gates/cage.py (not in active topology — see #172) |
| R9 | target_convention_homogeneity | src/ztare/gates/cage.py (not in active topology — see #172) |
| R10 | cross_class_extrapolation | src/ztare/gates/cross_class_extrapolation_gate.py |
| R11 | per_class_mre_ceiling | src/ztare/gates/cross_class_extrapolation_gate.py |
| R13 | substrate_critic | (preflight + post_fit pair) |
| R14 | noise_profile | (preflight + post_fit pair) |
| R15 | analogy | src/ztare/fit/analogy.py |
| R16 | framer_1d | (framer_pre_fit) |
| R20 | withheld_value_leakage | src/ztare/gates/structural_anti_pattern_gates.py |
| R21 | effective_parameter_count | src/ztare/gates/structural_anti_pattern_gates.py |
| R22 | apparatus_meta_runner | src/ztare/gates/structural_anti_pattern_gates.py |
| R23 | sparse_cell_exclusion | src/ztare/gates/structural_anti_pattern_gates.py |
| R24 | feature_bump_pattern | src/ztare/gates/structural_anti_pattern_gates.py |
| R170 | symbolic_logic_cage | src/ztare/gates/symbolic_logic_cage.py — number mismatch (catalog used R12) |

Notable: R12 / R17 / R18 / R19 are unallocated. R170 is a
number-mismatch (catalog says R12). Reconcile via #172.

## Outcome

Task #171 closed as "scoped down to label-pairing only." Heavier
rename work is rejected as not worth the regression risk. Cross-audit
dashboard label fix shipped. R-prefix convention documented here for
future reference.
