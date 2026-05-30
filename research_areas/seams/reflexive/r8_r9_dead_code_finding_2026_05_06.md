---
seam_id: r8-r9-dead-code-2026-05-06
status: closed
discovered: 2026-05-06
closed: 2026-05-06
owner: PM-of-ZTARE
relates_to: [#172, GP-220 reflexive ROI audit, v5.0 phase 3a]
resolution: option-A-wire-with-opt-in
---

# R8 / R9 Reflexive Primitives — Dead Code from v5.0 Phase 3a (RESOLVED)

> **Seam metadata** · `seam_id:` r8_r9_dead_code_finding_2026_05_06 · `track:` reflexive · `status:` closed · `last_updated:` 2026-05-09


## Resolution (2026-05-06 PM)

**Option A applied**: both gates wired as Cage-routed primitives with
opt-in default. New module
`src/ztare/gates/r8_r9_substrate_validators.py` provides `Gate` adapters
that route the existing `check_feature_coverage_adequacy` (R8) and
`check_target_convention_homogeneity` (R9) functions through the
Cage's engagement matrix. Registered via `register_r8_r9_gates()`
called from `build_cage_runtime` in
`src/ztare/orchestrator/state.py:160-170`.

Both gates default to opt-in to eliminate regression risk on the 156
historical projects:
  - R8 engages when `rubric.enable_r8_feature_coverage = True`
  - R9 engages when `rubric.enable_r9_target_convention_homogeneity = True`

GP-220 audit registry updated to include the new flags. Both gates
will show `insufficient_data` until a project opts in (correct verdict
for "wired but unused").

Smoke tested end-to-end: 35 gates in topology with cage_observe_mode,
R8 at position 14, R9 at position 15. R8 correctly fails on
candidates referencing missing-coverage features (25% < 30% threshold);
R9 correctly fails on heterogeneous substrates whose forms lack
`features['fit_convention']` references.

## Original finding



## Finding

`check_feature_coverage_adequacy` (R8, `src/ztare/gates/cage.py:155`)
and `check_target_convention_homogeneity` (R9,
`src/ztare/gates/cage.py:205`) are defined as functions but never
invoked anywhere in the running apparatus.

Cross-audit dashboard 2026-05-06 PM flagged R8/R9 as engagement_rate=0%
across 1,825 cage events. Initial theory was "infrastructure-bypass":
that R8/R9 ran as pre-flight validators that don't emit to the gate
engagement matrix. **That theory was wrong.**

The actual situation:

  1. `registry.py:_build_gates()` explicitly excludes cage.py functions
     ("cage.py + substrate_evaluation.py are infrastructure, not
     registered as gates"). So R8 and R9 are NOT in the Cage topology.

  2. `Cage.dispatch` calls `validate_substrate_meta()` but that
     function only checks META-SCHEMA validity (does the rubric.cage_meta
     dict have correct keys/types?). It does NOT call R8 or R9.

  3. No other code path invokes the R8/R9 functions. `grep -rn
     "check_feature_coverage_adequacy\|check_target_convention_homogeneity"
     --include="*.py" src/` returns ONLY:
       - the definitions themselves
       - the test file (`test_cage.py`)

R8 and R9 were authored as part of v5.0 Phase 3a (per the gp154 Class K
reference at `cage.py:210`) but the actual wiring step never landed.

## How the cross-audit caught this

This is a 5-month-old wiring gap that the cross-audit dashboard
surfaced today via two-source convergence:

  - `primitive_roi`: R8/R9 verdict=dead, engagement_rate=0%
  - `gate_telemetry`: R8/R9 expected names absent from cage_engagement.jsonl

Without two-source convergence the finding could have been dismissed
("audit registry has wrong gate name"). With both signals
independently reporting the absence, the engineering question forces
itself: *why is this primitive expected but missing from logs?*

## Decision space

Three options for the operator:

  **A. Wire R8 and R9** as Cage-registered gates (PRE_FIT phase) so
  they actually run and produce engagement events. Requires:
    - Author can_handle predicates (probably "always handle" for
      pre-flight validators)
    - Author Gate(name=..., phase="PRE_FIT", ...) wrappers in some
      module (likely `src/ztare/gates/r8_r9_substrate_validators.py`)
    - Register in `registry.py::_build_gates()`
    - Add to `scripts/public/analytics_shared/reflexive_primitive_roi_audit.py` registry with
      correct `cage_engagement_keys`
    - Smoke on at least one project with substrate.meta declaring
      heterogeneous target_convention_homogeneity to verify R9 fires

  **B. Retire R8 and R9** from the catalog. If they were authored but
  never wired because the operator decided the scope was wrong,
  formalize that:
    - Add RETIRE entry to `DECISION_LOG.md` with rationale
    - Delete `check_feature_coverage_adequacy` and
      `check_target_convention_homogeneity` from cage.py (and their
      tests)
    - Remove R8/R9 from
      `scripts/public/analytics_shared/reflexive_primitive_roi_audit.py` registry +
      `scripts/public/analytics_shared/diagnose_gate_telemetry.py` EXPECTED set
    - Update r_prefix_naming_convention.md catalog table

  **C. Defer** until the broader #172 can_handle investigation runs.
  The other 6 primitives in #172 (R10/R11/R15/R16/R22/R23) are similar
  questions: "primitive is in the pipeline but never engages — wire it
  better, or retire it?" Bundle R8/R9 with that investigation.

Recommendation: **Option C.** R8/R9's unwired-ness IS the same engineering
question as the others' narrow `can_handle` predicates. Treat the seven
primitives as one investigation.

## Telemetry

Today's diagnostic output snapshots:

  - `analytics/public/queries/audits/gate_telemetry_diagnosis.json` (all 14 expected
    names, 9 absent from logs, 5 present with R-prefix)
  - `analytics/public/queries/reflexive/reflexive_primitive_roi.json` (18 primitives,
    9 verdict=dead, 5 insufficient_data, 2 decorative_candidate, 2 engagement_high)
  - `analytics/public/queries/audits/cross_audit_dashboard.json` (9 convergent
    signals across 76 flagged entities)

Re-run all three after any R8/R9 fix so the audit reflects the new state.
