---
seam_id: cross-audit-convergent-2026-05-06
status: open
discovered: 2026-05-06
owner: PM-of-ZTARE
---

# Cross-Audit Convergent Signals — 2026-05-06

> **Seam metadata** · `seam_id:` cross_audit_convergent_signals_2026_05_06 · `track:` reflexive · `status:` open · `last_updated:` 2026-05-09


## What

The cross-audit synthesis dashboard (scripts/public/analytics_shared/synthesize_audit_dashboard.py) joins
9 independent scorecards by entity. After patching the entity-alias map so that
`primitive/R<N>` and `gate_name/<descriptive>` resolve to the same entity, it
surfaces **8 convergent signals** (entities flagged by ≥2 independent scorecards).

## Findings

### 1. CAN_HANDLE-NARROW class — gate is in the pipeline but always refuses

Both `primitive_roi` (engagement_rate=0%) and `gate_telemetry` (rename detected
in cage_engagement.jsonl) confirm:

| Primitive | Descriptive name | Refused | Engaged |
|---|---|---:|---:|
| R10 | cross_class_extrapolation | 433 | 0 |
| R11 | per_class_mre_ceiling | 294 | 0 |
| R15 | analogy | 325 | 0 |
| R16 | framer_1d | 280 | 0 |
| R22 | apparatus_meta_runner | 433 | 0 |
| R23 | sparse_cell_exclusion | 433 | 0 |
| R24 | feature_bump_pattern | 424 | 0 (insufficient_data — opt-in) |

**R8 / R9 catalog gap:** both are coded in `src/ztare/gates/cage.py`
(R8 `check_feature_coverage_adequacy` line 155, R9
`check_target_convention_homogeneity` line 205) but appear in zero
cage_engagement.jsonl events across 1,825+ iters. Likely not
registered in the active Cage topology. Worth a focused trace.

**R12 ↔ R170 number mismatch:** catalog calls symbolic_logic_cage
"R12"; code and logs call it "R170". Reconcile.

**R20-R23 newly registered:** five gates that emit 424 events each
were absent from the GP-220 audit registry until today's
cross-audit dashboard surfaced them via gate_telemetry alias matching.

Each engages exactly zero times across 1,825+ cage events. The gates ARE
firing — `can_handle` returns False every time.

**Reading**: the eligibility predicates are too narrow OR they sit at the
wrong pipeline stage (R24 says "no parametric form on candidate" but it's
gated after the form is built — likely a wiring bug). R15 is opt-in via
`enable_analogy` rubric flag; that's expected — segment the audit.

### 2. DECORATIVE-CANDIDATE class — engages often, finds little

| Primitive | Engagement | Findings |
|---|---:|---:|
| R13 substrate_critic | 38.66% | 1 |
| R14 noise_profile | 38.66% | 1 |

Both engage 663 times across the corpus and emit 1 finding each. Either
the finding-emit thresholds are too strict (true missing detection) or
the gates are decoration (true low ROI). Audit the threshold logic
before deciding.

### 3. R24 is unregistered

`R24_feature_bump_pattern` appears 424 times in cage_engagement.jsonl
but was absent from the GP-220 ROI audit registry until today's
cross-audit dashboard found it via gate_telemetry alias matching. Add
to scripts/public/analytics_shared/reflexive_primitive_roi_audit.py registry.

### 4. Track B target with two-axis evidence

`target/TrackBProfileDecompositionObligation` is flagged by both
`endpoint_compression` (GP-223 Layer 3 candidate, X_of_Y projection
shape on `threshold_defect_of_family_no_arbitrage`) AND `triangulation`
(compounding_score=4, 1 cannot_patch event in source_provenance_bridge
class). GP-223 protocol: check whether `threshold_defect` already
exists as a field accessor on a `family_no_arbitrage`-qualified
receipt; if yes, close by projection rather than fresh patch.

## Why this matters

Single-source flags are noisy. The R8-R16 fiasco earlier today (audit
reported 0% engagement for working primitives because of a logging-name
mismatch in the audit's own registry) showed that any one scorecard can
silently lie. **Convergent signals** — same entity flagged by two
independent scorecards looking at different axes — survive that class
of failure. The 8 convergent signals here are the dashboard's first
real-world output, and 7 of them point to coherent engineering work
(narrow can_handle predicates, decorative-candidate verdicts, an
unregistered primitive).

## Action items

Captured as task #172 (can_handle/hit-rate investigation) and #171
(R-number → descriptive-name rename). Don't pick up while v6 GPU
training is mutating analytics.
