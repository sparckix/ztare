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

| ID | Track | Status | Workstream | Summary | So What | Seam File | Spec File | Next Action | Verifier |
|---|---|---|---|---|---|---|---|---|---|
| GP-005 | `kernel` | `verify` | Workflow / Suite Coherence | Baseline thesis / suite timestamp mismatch is warned, but not fully enforced | Stale test suites can silently validate outdated code | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Decide whether incoherent baseline should regenerate, fail closed, or parse from thesis | `src/ztare/validator/autoresearch_loop.py` |
| GP-006 | `kernel` | `closed` | Kernel Hardening | Bounded-discriminator mode verified in production across multiple projects | Forces the AI to show its reasoning, not just assert conclusions | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | One more adversarial bounded-discriminator verifier | `projects/eu_union_stability/debate_log_iter_1775688359.md` |
| GP-008 | `kernel` | `closed` | Kernel Hardening / Loop Control | UNDERIDENTIFIED exit verified in production (EU failure-probability run) | Loop stops itself when it cannot distinguish between competing explanations | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Confirm bounded-discriminator catastrophic streak exits cleanly | `projects/<project>/workspace/underidentification_verdict.json` |
| GP-010 | `kernel` | `verify` | Kernel Hardening / Prompt Contract | Bounded-discriminator style guide should survive stagnation pivots; GP-023 pre-kickoff audit additionally surfaced that the style guide is tuned for causal/historical theses and creates friction for quantitative curve-fit tasks — pivot selector and style-guide selector are currently package-dealed via `falsification_mode` and cannot be decoupled at the rubric layer | Style guide built for essays breaks when the task is curve-fitting; needs decoupling | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Confirm stagnation still preserves discriminator-mode contract; separately, decide whether to decouple pivot-profile selection from style-guide selection if a second curve-fit project hits the same friction | `src/ztare/validator/autoresearch_loop.py`, `src/ztare/validator/pivot_heuristics.py` |
| GP-011 | `kernel` | `closed` | Evidence RAM / Compiler | Typed derived-constraints lane verified in EU failure-probability project across multiple runs | Lessons from past runs carry forward automatically instead of being lost | `research_areas/seams/GP-011_derived_constraints_lane_seam.md` | `research_areas/specs/active/GP-011_derived_constraints_lane_spec.md` | Let the active `%` forecast project finish, then confirm recurring constraints promote into `derived_constraints.json` across distinct runs | `projects/eu_union_failure_probability_2035/workspace/derived_constraints.json` |
| GP-012 | `kernel` | `verify` | Scoring Contract | Quarantine laundering hardening exists, but should be cross-judge validated | Prevents the AI from inflating its score by burying bad results | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Run same thesis under Gemini and Claude and compare caps | `src/ztare/validator/test_thesis.py` |
| GP-013 | `kernel` | `verify` | Scoring Contract / Regime | Score-regime fingerprinting shipped, but one more live rebaseline test would close it cleanly | Detects when scoring standards shift so old scores stay comparable | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Rebaseline an older project after a regime bump | `src/ztare/validator/autoresearch_loop.py` |
| GP-014 | `kernel` | `verify` | Scoring Contract | Deferred-confirmation laundering hardening shipped and should be closed with one more forecast-leaning verifier | Stops "I'll prove it later" from counting as a perfect score today | `legacy_combined:research_areas/HARDENING_BOARD.md` | `legacy_combined:research_areas/HARDENING_BOARD.md` | Confirm future-observable theses cannot drift back toward `100` | `src/ztare/validator/test_thesis.py` |
| GP-017 | `kernel` | `closed` | Evidence RAM / Compiler | Typed evidence loop verified; EU ceiling bounded by comparator objection confirms loop honesty | System honestly caps its confidence when evidence runs out | `legacy_combined:research_areas/private/kernel/evidence_feedback_loop.md` | `legacy_combined:research_areas/private/kernel/evidence_feedback_loop.md` | One final comparator-focused EU pass, then decide whether the loop is verified and EU is honestly bounded | `projects/eu_union_load_bearing_pillars/workspace/latest_evidence_gaps.json` |
| GP-021 | `kernel` | `closed` | Kernel Hardening | Pivot heuristic profiles verified in production; profile selection works in V4 and non-V4 | When the AI gets stuck, it picks from typed recovery strategies instead of flailing | `research_areas/seams/GP-021_topological_pivot_heuristics_seam.md` | `research_areas/specs/active/GP-021_topological_pivot_heuristics_spec.md` | Run a live stagnation case and confirm profile selection behaves correctly in non-V4 and V4 | `src/ztare/validator/pivot_heuristics.py` |
| GP-022 | `kernel` | `closed` | Project Typing / Forecast Contract | Forecast typing and directional-project % cap verified in production | A forecast project cannot score 100 just by being internally consistent; it must be testable | `research_areas/seams/GP-022_forecast_project_typing_seam.md` | `research_areas/specs/active/GP-022_forecast_project_typing_spec.md` | Force a directional project to emit a naked percentage and confirm the new cap fires in a real run | `src/ztare/validator/test_thesis.py` |
| GP-026 | `kernel` | `verify` | Runner Hardening / Mutation Admission | Long Gemini hardening run on a private project exposed that no-suite mutations are still admitted as scored `0`s via sentinel fallback instead of being rejected pre-eval | Proposals without test suites were sneaking through as scored zeros instead of being rejected outright | `research_areas/seams/GP-026_runner_no_suite_rejection_seam.md` | `research_areas/specs/active/GP-026_runner_no_suite_rejection_spec.md` | Confirm missing-suite and sentinel-suite candidates now die as Runner R1 rejections and do not overwrite latest scored artifacts | `src/ztare/validator/mutation_suite_guard.py` |

### Findings track

Findings items are runtime-discovered observations, not planned construction. The `n` column is the evidence count — the number of distinct runtime occurrences of the pattern. Items at `active` with `n=1` violate the promotion invariant unless a verifier experiment has been explicitly approved as an n=2 generator (shown in the Verifier column).

| ID | Track | n | Status | Workstream | Summary | So What | Seam File | Spec File | Next Action | Verifier |
|---|---|---|---|---|---|---|---|---|---|---|
| GP-027 | `findings` | n=1 | `note` | Evidence RAM / Compiler | Raw evidence compilation still re-pays for unchanged inputs; add an exact-input reuse/cache lane so frugal operators are not forced into needless recompilation. n=1 observation from operator frugality complaint. Promotion requires either a second occurrence or an operator decision to implement for ergonomics independent of evidence | Re-running with same inputs wastes money for no new information | `research_areas/seams/GP-027_evidence_compile_reuse_seam.md` | `research_areas/specs/active/GP-027_evidence_compile_reuse_spec.md` | Hold at note. If a second project hits the same waste, promote to active. Otherwise decide out-of-band whether to implement for ergonomics | `src/ztare/workspace/compile_evidence.py` |
| GP-029 | `findings` | n=2 | `closed` | Kernel Frontier / Observability | Verified. `latent_distance.jsonl` observability confirmed across GP-023 and EU failure-probability runs; structural motion visible independent of score | Can now see that the AI is exploring structurally different ideas even when the score does not move | `research_areas/private/seams/GP-029_latent_distance_observability_seam.md` | (none — first slice shipped directly from seam debate) | Closed | `projects/eu_union_failure_probability_2035/workspace/latent_distance.jsonl` |
| GP-030 | `findings` | n=1 | `closed` | Scoring Contract / Charter Enforcement | Verified. Deterministic charter-gate evaluation shipped; EU run confirmed scope discipline, GP-037 substrate-swap run exercises active gates | Hard numeric checks now enforce the project charter; the AI judge cannot override them | `research_areas/private/seams/GP-030_deterministic_charter_gate_seam.md` | (none — first slice shipped directly from seam debate) | Closed | `projects/gp037_substrate_swap_01/gate_harness.py` |
| GP-035 | `findings` | n=2 | `closed` | Mutator / Fit Primitive | Implemented: `src/ztare/validator/fit_primitive.py`. Post-LLM `scipy.optimize.curve_fit` step, opt-in via rubric `enable_fit_primitive`. Verified on GP-037 substrate-swap: fitter engaged successfully and produced real residual diagnostics. Next binding constraint is mutator structural diversity, not parameter fitting | Computer now fits the numbers after the AI proposes the equation shape; bottleneck moved upstream to shape selection | `research_areas/private/seams/GP-035_mutator_missing_fit_primitive_seam.md` | `research_areas/private/specs/active/GP-035_mutator_fit_primitive_spec.md` | Closed | `src/ztare/validator/fit_primitive.py` |
| GP-037 | `findings` | n=2 | `closed` | Kernel Frontier / Substrate-Swap Verifier | Clean 10-iter run: gates engaged, semantic traversal real, score remained `0`, no viable basin emerged. GP-035 verified as non-binding; structural diversity / form-family escape is the next bottleneck | Fitting equations works; the AI proposing the right equation shape is now the binding problem | `research_areas/private/seams/GP-037_substrate_swap_3b_seam.md` | (no spec — sandbox files are the artifact) | Closed | `projects/gp037_substrate_swap_01/gate_harness.py` |

> **Additional findings-track items omitted from public listing.** Several active and noted findings-track items describe runtime-discovered exploit patterns or unimplemented methodology primitives. They are tracked in the private mirror at `research_areas/private/ZTARE_BOARD.md` per the visibility rule in `research_areas/seams/README.md`. The omission is structural, not a status change.

### Other

| ID | Track | Status | Workstream | Summary | So What | Seam File | Spec File | Next Action | Verifier |
|---|---|---|---|---|---|---|---|---|---|
| GP-070 | `kernel` | `active` | Workflow / Meta-Supervisor | Goal orchestrator — three-layer architecture (OS / Config / App) for typed goal lifecycles with hard gates, stage guidance, dispatch adapters, and AGENTS.md auto-maintenance | Agent programs now have a state machine that tracks where they are and what gate they need to pass next | `research_areas/private/seams/GP-070_meta_supervisor_seam.md` | `research_areas/private/specs/active/GP-070_meta_supervisor_spec.md` | Slice B remaining: agent-driven gate resolution, `kernel_hardening.yaml` and `public_writeup.yaml` configs | `src/ztare/orchestration/cli.py` |
| GP-071 | `kernel` | `verify` | Workflow / Operator UX | Executive inbox — advisory-mode surface for gate queue, active goals, and structured status | Operator sees all pending decisions in one place instead of hunting through files | `research_areas/private/seams/GP-071_executive_inbox_seam.md` | (shipped directly) | Verify on next gate-heavy goal lifecycle; Flask rewrite if Streamlit design quality is unacceptable | `src/ztare/supervisor/inbox_streamlit.py` |
| WB-001 | `kernel` | `active` | Product / Workbench | Local workbench service layer — all four blocking trust seams now closed. Ready for implementation scoping | The user-facing product can now be built; all trust prerequisites are met | `legacy_combined:research_areas/private/product-strategy/local_workbench_productization.md` | `legacy_combined:research_areas/private/product-strategy/local_workbench_productization.md` | Scope v1 implementation against D4 design brief | `research_areas/private/product-strategy/local_workbench_productization.md` |

## Migration Rule

- this board is canonical for active work
- `research_areas/HARDENING_BOARD.md` becomes a legacy hardening archive / provenance source
- old combined notes are allowed temporarily, but should be marked `legacy_combined`
- new serious work should get separate seam/spec files
