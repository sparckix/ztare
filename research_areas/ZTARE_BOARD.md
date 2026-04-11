# ZTARE Board

This is the canonical board for in-flight ZTARE work.

Use it when the question is:

- what is currently open?
- what should be worked next?
- where is the investigation?
- where is the clean blueprint?

This board is intentionally broader than the old hardening board.
It covers active ZTARE work across:

- kernel hardening
- workflow / operator UX
- evidence RAM / compiler
- project typing
- distribution artifacts
- product/workbench planning

## Visibility

This board is the **public** view. Items whose seams describe runtime-discovered exploit patterns, unimplemented product surfaces, or unimplemented methodology primitives whose value depends on being first are tracked in the private mirror at `research_areas/private/ZTARE_BOARD.md` (gitignored). The full visibility rule lives in `research_areas/seams/README.md` and `AGENTS.md`. When a private seam ships or is subsumed, its row promotes to this public board and its file moves out of `research_areas/private/seams/` at the same moment.

## Two tracks

ZTARE work splits into two tracks with different origins and closure rules. The distinction is load-bearing — see `research_areas/seams/README.md` for the full category definition and the five invariants.

- **`kernel`** — planned V4 hardening. Construction project. Modifies the core. Closure = implemented + verified. Examples: wrappers, write-scope guard, manifest, derived-constraints lane, bridge freeze.
- **`findings`** — runtime-discovered frontier observation. Ledger entry. Strictly downstream of core. Closure = implemented, subsumed, promoted, or dormant.

**Findings invariant (load-bearing):** a findings item at `active` must have either n ≥ 2 (pattern observed at least twice) OR an approved verifier experiment that would produce n=2 if the pattern is real. A findings item at n=1 is a `note`, not `active`.

## Status Legend

**Kernel track:**
- `active`: currently open and shaping near-term engineering decisions
- `verify`: implemented enough to need a live verifier before closure
- `blocked`: known seam, but sequenced behind another item
- `legacy_combined`: still tracked through one mixed note until migrated

**Findings track:**
- `note`: n=1 observation captured, conjectured fix named, not implementable, not scheduled (the default for a new findings seam)
- `dormant`: evidence captured, no further turns expected until a triggering condition fires
- `active`: n ≥ 2 OR a verifier experiment is approved — implementation may begin
- `converged`: debate has converged on a downstream artifact (design brief, recommendation, decision) that does not require kernel implementation — the artifact itself is the closure
- `verify`: shipped, awaiting live confirmation
- `closed`: verified and retired
- `subsumed`: absorbed into another seam or a kernel-track item

## File Ontology

- `Seam File`
  - the investigation / debate / failure analysis
- `Spec File`
  - the implementation blueprint
- if an older item is not split yet, both columns should use:
  - `legacy_combined:<path>`

## Current In-Flight Work

### Kernel track

| ID | Track | Status | Workstream | Summary | Seam File | Spec File | Next Action | Verifier |
|---|---|---|---|---|---|---|---|---|
| GP-005 | `kernel` | `verify` | Workflow / Suite Coherence | Baseline thesis / suite timestamp mismatch is warned, but not fully enforced | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Decide whether incoherent baseline should regenerate, fail closed, or parse from thesis | `src/ztare/validator/autoresearch_loop.py` |
| GP-006 | `kernel` | `verify` | Kernel Hardening | Bounded-discriminator mode is much healthier, but still needs one more live closeout | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | One more adversarial bounded-discriminator verifier | `projects/eu_union_stability/debate_log_iter_1775688359.md` |
| GP-008 | `kernel` | `verify` | Kernel Hardening / Loop Control | UNDERIDENTIFIED behavior exists but still needs a clean live verifier | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Confirm bounded-discriminator catastrophic streak exits cleanly | `projects/<project>/workspace/underidentification_verdict.json` |
| GP-010 | `kernel` | `verify` | Kernel Hardening / Prompt Contract | Bounded-discriminator style guide should survive stagnation pivots; a recent pre-kickoff audit additionally surfaced that the style guide is tuned for causal/historical theses and creates friction for quantitative curve-fit tasks that need the same 9-module pivot profile — pivot selector and style-guide selector are currently package-dealed via `falsification_mode` and cannot be decoupled at the rubric layer | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Confirm stagnation still preserves discriminator-mode contract; separately, decide whether to decouple pivot-profile selection from style-guide selection if a second curve-fit project hits the same friction | `src/ztare/validator/autoresearch_loop.py`, `src/ztare/validator/pivot_heuristics.py` |
| GP-011 | `kernel` | `verify` | Evidence RAM / Compiler | Typed derived-constraints lane is implemented; now needs a live project verifier to confirm cross-run promotion and prompt reuse behave correctly | `research_areas/seams/GP-011_derived_constraints_lane_seam.md` | `research_areas/specs/active/GP-011_derived_constraints_lane_spec.md` | Let the active `%` forecast project finish, then confirm recurring constraints promote into `derived_constraints.json` across distinct runs | `projects/eu_union_failure_probability_2035/workspace/derived_constraints.json` |
| GP-012 | `kernel` | `verify` | Scoring Contract | Quarantine laundering hardening exists, but should be cross-judge validated | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Run same thesis under Gemini and Claude and compare caps | `src/ztare/validator/test_thesis.py` |
| GP-013 | `kernel` | `verify` | Scoring Contract / Regime | Score-regime fingerprinting shipped, but one more live rebaseline test would close it cleanly | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Rebaseline an older project after a regime bump | `src/ztare/validator/autoresearch_loop.py` |
| GP-014 | `kernel` | `verify` | Scoring Contract | Deferred-confirmation laundering hardening shipped and should be closed with one more forecast-leaning verifier | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Confirm future-observable theses cannot drift back toward `100` | `src/ztare/validator/test_thesis.py` |
| GP-017 | `kernel` | `verify` | Evidence RAM / Compiler | Typed evidence loop is real; EU now sits at a cleaner `67` ceiling driven by the discretionary-equilibrium comparator objection | `legacy_combined:research_areas/private/kernel/evidence_feedback_loop.md` | `legacy_combined:research_areas/private/kernel/evidence_feedback_loop.md` | One final comparator-focused EU pass, then decide whether the loop is verified and EU is honestly bounded | `projects/eu_union_load_bearing_pillars/workspace/latest_evidence_gaps.json` |
| GP-021 | `kernel` | `verify` | Kernel Hardening | Legacy topological pivot has been factorized into reusable heuristic profiles, but needs live confirmation | `research_areas/seams/GP-021_topological_pivot_heuristics_seam.md` | `research_areas/specs/active/GP-021_topological_pivot_heuristics_spec.md` | Run a live stagnation case and confirm profile selection behaves correctly in non-V4 and V4 | `src/ztare/validator/pivot_heuristics.py` |
| GP-022 | `kernel` | `verify` | Project Typing / Forecast Contract | Forecast typing is now in the charter and unsupported `%` claims in directional projects are scorer-capped | `research_areas/seams/GP-022_forecast_project_typing_seam.md` | `research_areas/specs/active/GP-022_forecast_project_typing_spec.md` | Force a directional project to emit a naked percentage and confirm the new cap fires in a real run | `src/ztare/validator/test_thesis.py` |
| GP-026 | `kernel` | `verify` | Runner Hardening / Mutation Admission | Long Gemini hardening run on a private project exposed that no-suite mutations are still admitted as scored `0`s via sentinel fallback instead of being rejected pre-eval | `research_areas/seams/GP-026_runner_no_suite_rejection_seam.md` | `research_areas/specs/active/GP-026_runner_no_suite_rejection_spec.md` | Confirm missing-suite and sentinel-suite candidates now die as Runner R1 rejections and do not overwrite latest scored artifacts | `src/ztare/validator/mutation_suite_guard.py` |

### Findings track

Findings items are runtime-discovered observations, not planned construction. The `n` column is the evidence count — the number of distinct runtime occurrences of the pattern. Items at `active` with `n=1` violate the promotion invariant unless a verifier experiment has been explicitly approved as an n=2 generator (shown in the Verifier column).

| ID | Track | n | Status | Workstream | Summary | Seam File | Spec File | Next Action | Verifier |
|---|---|---|---|---|---|---|---|---|---|
| GP-027 | `findings` | n=1 | `note` | Evidence RAM / Compiler | Raw evidence compilation still re-pays for unchanged inputs; add an exact-input reuse/cache lane so frugal operators are not forced into needless recompilation. n=1 observation from operator frugality complaint. Promotion requires either a second occurrence or an operator decision to implement for ergonomics independent of evidence | `research_areas/seams/GP-027_evidence_compile_reuse_seam.md` | `research_areas/specs/active/GP-027_evidence_compile_reuse_spec.md` | Hold at note. If a second project hits the same waste, promote to active. Otherwise decide out-of-band whether to implement for ergonomics | `src/ztare/workspace/compile_evidence.py` |

> **Additional findings-track items omitted from public listing.** Several active and noted findings-track items describe runtime-discovered exploit patterns or unimplemented methodology primitives. They are tracked in the private mirror at `research_areas/private/ZTARE_BOARD.md` per the visibility rule in `research_areas/seams/README.md`. The omission is structural, not a status change.

### Other

| ID | Track | Status | Workstream | Summary | Seam File | Spec File | Next Action | Verifier |
|---|---|---|---|---|---|---|---|---|
| WB-001 | `kernel` | `blocked` | Product / Workbench | Local workbench service layer is likely the first real product surface, but still sequenced behind trust seams | `legacy_combined:research_areas/private/product-strategy/local_workbench_productization.md` | `legacy_combined:research_areas/private/product-strategy/local_workbench_productization.md` | Reopen after GP-017 / GP-021 / GP-022 / GP-011 | `research_areas/private/product-strategy/local_workbench_productization.md` |

## Migration Rule

- this board is canonical for active work
- `research_areas/HARDENING_BOARD.md` becomes a legacy hardening archive / provenance source
- old combined notes are allowed temporarily, but should be marked `legacy_combined`
- new serious work should get separate seam/spec files
