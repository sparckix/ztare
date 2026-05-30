# Closure-Pattern Distribution

_Generated 2026-05-09T23:23:48.587237+00:00_  
_Rows analyzed:_ 446  _Verified:_ 9  _Falsified+finding:_ 1  _In-progress:_ 434

## Closure status distribution

| Status | Count |
|---|---:|
| `in_progress` | 434 |
| `verified` | 9 |
| `falsified_null` | 2 |
| `falsified_with_finding` | 1 |

## v5-op closure rate (verified + falsified_with_finding)

| v5 op | Verified | Falsified+finding | Total closures |
|---|---:|---:|---:|
| `subfield_pde_estimate_craft` | 98 | 0 | 98 |
| `subfield_residual_chasing` | 13 | 0 | 13 |
| `core_05_canonical_invariance` | 5 | 0 | 5 |
| `core_03_decomposition` | 2 | 0 | 2 |
| `subfield_basin_hopping` | 1 | 0 | 1 |
| `broad_inversion` | 1 | 0 | 1 |

## Primitive candidates + load-bearing-confirmed

| v5 op | Verdict | Closures | Classes | Existing gates |
|---|---|---:|---:|---|
| `subfield_pde_estimate_craft` | `covered_load_bearing` | 98 | 2 | noise_profile |
| `subfield_residual_chasing` | `covered_load_bearing` | 13 | 5 | per_class_farther_tail |
| `core_05_canonical_invariance` | `covered_load_bearing` | 5 | 4 | feature_coverage_adequacy, target_convention_homogeneity, symbolic_logic_cage, substrate_critic, framer_1d, endpoint_type_compression_gate |

### Detailed rationale

- **`subfield_pde_estimate_craft`** — Recurs in 98 closing rows (1 F-row + 97 axiom); existing gates ['noise_profile'] already cover. Load-bearing — do not retire.
- **`subfield_residual_chasing`** — Recurs in 13 closing rows (3 F-row + 10 axiom); existing gates ['per_class_farther_tail'] already cover. Load-bearing — do not retire.
- **`core_05_canonical_invariance`** — Recurs in 5 closing rows (0 F-row + 5 axiom); existing gates ['feature_coverage_adequacy', 'target_convention_homogeneity', 'symbolic_logic_cage', 'substrate_critic', 'framer_1d', 'endpoint_type_compression_gate'] already cover. Load-bearing — do not retire.

## Honest caveats

- v5-op detection is keyword-based — false positives expected on multi-meaning words (e.g. 'compress' may match prose about compression but not the structural move).
- closure_status classifier is also keyword-based; F-row prose uses varied vocabulary across vintages.
- EXISTING_CAGE_GATES table is hand-curated — a new gate that covers an op but isn't in this table will look like a missing primitive when it isn't.
- v0.1 surfaces candidates — operator/PM disposes whether to ship.

