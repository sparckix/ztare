# GP-157 Phase 4g — status note (2026-05-06)

> **Seam metadata** · `seam_id:` GP-157 · `track:` apparatus · `status:` active · `last_updated:` 2026-05-09


**Status:** active *(inferred 2026-05-08 — needs operator review)*

**Update 2026-05-06 PM**: four atomic extractions shipped this session
(see "Extractions shipped 2026-05-06 PM" below).
autoresearch_loop.py is now **8,618 lines (down from 8,963, –345 net)**.
Original status note follows; the supplemental section captures
the extractions completed.

This is a stocktake. The prior status memory was over-optimistic
about Phase 4g being a 90-min job — empirical measurement showed
the real iter-body to be ~4,800 lines. The session-PM extractions
target the lower-risk helper layer; the iter-body wrap remains
deferred.

## Summary

**Phases 4a–4f are shipped** (IterContext, telemetry, state, prompt,
parallel_mutator stub, contract_adherence + 50+ orchestrator modules).
The validator namespace carve-up shipped 2026-05-06 (commit 6dca8aa5).

**Phase 4g is materially harder than the previous status memo
described.** The original spec called Phase 4g a 90-minute extraction
of `main.py`, `dispatch.py`, `r1_retry.py`. Empirical measurement:

| Claim (prior memo) | Reality (2026-05-06) |
|---|---|
| autoresearch_loop.py "should shrink to a 50-line shim" | currently 8,963 lines |
| iter-loop body extractable in ~90 min | iter-body spans line 4141 → 8963 = ~4,800 lines |
| 3 atomic commits, each 60–90 min | each module would still be ~1,600 lines |
| r1_retry is a contained extractable block | R1 logic is ALREADY largely extracted via `format_r1_retry_skeleton` (line 75), `validate_and_retry_fit_declaration` (line 116), `drain_failed_retry_tracker` (line 22). Only ~200 lines of session-counter + persist-r1-debug + SyntaxError handlers remain inline |
| dispatch can be pulled into one `dispatch_phase()` | The orchestrator already has `pre_iter1_dispatch`, `pre_fit_dispatch`, `post_fit_dispatch`, `post_harness_dispatch`, `gp180_dispatch`, `blitz_dispatch` — six phase-specific dispatchers shipped. The autoresearch_loop body calls them conditionally, but the conditionals themselves are substrate-flag-aware, not trivially collapsible |

## Why the prior estimate was wrong

The 90-min estimate appears to have been generated against the GP-157
spec's Phase 4g description without measuring the actual file. The
spec was written when autoresearch_loop was 7,654 lines (per spec
estimate). It has grown 23% since (reasons: GP-216 vocabulary
narration, GP-219 PDE estimate-craft tagging, R10–R16 reflexive
primitives backports, GP-180/181 rubric-mode resolution, GP-219+v5
joint vocabulary instrumentation, evidence-gap enrichment hooks). Each
addition was small in isolation; in aggregate they pushed the iter-body
back into 4,800-line territory after the orchestrator/* extractions
shrunk it earlier.

## What's actually extractable today (honest scope)

Three extraction targets remain plausible. Effort estimates revised
against the 8,963-line reality:

### Target 1 — `orchestrator/main.py::run_main_loop(args, rubric_data)`
Wrap lines 4141–8963 in a single function. Leaves a thin
`if __name__ == "__main__":` shim that calls it.

**Honest effort**: 6–10 hours of careful work + a real substrate
smoke-test. Not doable in the same session as other work.

**Required preconditions**:
- A reproducible substrate smoke test (gp155 fixture or similar) that
  runs in <5 min and exercises pre_fit + post_fit + post_harness +
  pivot + best-state persistence. Currently `tests/validator/
  test_autoresearch_loop_static_guards.py` is static-only; the
  closest live-run smoke is `scripts/public/control/runtime_smoke_test.py` and
  `scripts/public/audits/gp156_integration_smoke_test.py` — verify these still work
  before refactoring.
- An IterState dataclass capturing all loop-body globals
  (best_state, iter_count, score_history, usage_ledger,
  stagnation_count, etc.). Probably 30+ fields based on quick scan.

### Target 2 — `orchestrator/r1_retry.py` (smaller, more contained)
Pull the ~200 inline lines: SyntaxError handlers (~lines 1926–1940),
`_persist_r1_debug` helper (~2244–2289), session-counter logic, and
the GP-156 R1 hardening section (~2044–2078) into a module.

**Honest effort**: 2–3 hours. Feasible as a single atomic commit.
Lower blast radius than Target 1 because the imported callers
(`format_r1_retry_skeleton`, `validate_and_retry_fit_declaration`)
already live outside.

### Target 3 — `orchestrator/dispatch.py::dispatch_phase(phase, ctx)`
Aggregate the 6 phase-specific dispatchers into one router. Replace
the ~150 lines of conditional `if rubric.enable_X: ... if
rubric.enable_Y: ...` with a single dispatch_phase call.

**Honest effort**: 4–6 hours. Many phase-conditionals are subtly
different (some require post-call state inspection, some are gated by
stagnation predicates, etc.). The aggregation needs careful spec'ing.

## Recommendation

Don't ship Phase 4g piecemeal in a session shared with other work.
The right approach:

1. **Dedicated session** with a working substrate smoke test as the
   first artifact. Use gp155 fixture or the most recently green
   integration test.
2. **Target 2 first** (r1_retry.py) — smallest, most isolated, lowest
   blast radius. Validates the smoke-test apparatus before touching
   the iter-body.
3. **Target 1 second** (main.py wrap) — only if Target 2 lands clean.
   This is the decisive extraction; do it slowly.
4. **Target 3 third** (dispatch.py) — only if Targets 1+2 land. Phase
   4g is "complete enough" without it; the existing 6 phase
   dispatchers already do the work, just with conditional inline
   calls instead of a single router.

## Status of Phase 4 overall (2026-05-06)

| Phase | Status |
|---|---|
| 4a IterContext | ✅ shipped 2026-04-25 |
| 4b telemetry.py | ✅ shipped (8 tests) |
| 4c state.py | ✅ shipped (13 tests) |
| 4d prompt.py | ✅ shipped (31 tests) |
| 4e parallel_mutator.py | ✅ stub shipped (18 tests); not wired (cost-gated) |
| 4f contract_adherence.py | ✅ shipped (18 tests) |
| 4g main.py | ⏸ deferred — see Target 1 above |
| 4g r1_retry.py | ⏸ deferred — see Target 2 above |
| 4g dispatch.py | ⏸ deferred — see Target 3 above |
| validator/ namespace carve-up | ✅ shipped 2026-05-06 (commit 6dca8aa5) |
| 4g — orchestrator/r1_retry.py | ✅ shipped 2026-05-06 PM |
| 4g — orchestrator/iteration_telemetry.py | ✅ shipped 2026-05-06 PM |
| 4g — orchestrator/best_state_persistence.py | ✅ shipped 2026-05-06 PM (read side only; write side deferred) |
| 4g — common/file_io.py | ✅ shipped 2026-05-06 PM |

## Extractions shipped 2026-05-06 PM

Four atomic extractions, all uncommitted (per operator instruction).
All file sizes post-extraction:

| File | Lines | Notes |
|---|---|---|
| `autoresearch_loop.py` | 8,618 | down from 8,963 (–345 net) |
| `orchestrator/r1_retry.py` | 122 | log_r1_attempt + R1ExhaustionTracker |
| `orchestrator/iteration_telemetry.py` | 433 | 10 helpers (utc_now_iso, usage_*, gate metrics, normalize_eval_payload, append_run_boundary_telemetry, append_iteration_telemetry) |
| `orchestrator/best_state_persistence.py` | 252 | read side: stem/score/meta/regime accessors + comparison anchor (write side `_persist_best_candidate` still inline) |
| `common/file_io.py` | 91 | read_file/write_file/read_json/write_json/append_jsonl |

Each extraction follows the same pattern:
1. Function bodies move to a dedicated module with explicit args
   replacing module-globals.
2. Path-dependent helpers are wrapped in autoresearch_loop with
   thin alias-functions that fill in the globals (`THESIS_PATH`,
   `HISTORY_DIR`, `BEST_ITERATION_RE`, `RUN_ID`, etc.).
3. Existing call sites use the same private-name (`_log_r1_attempt`,
   `_append_iteration_telemetry`, etc.), so no call-site changes
   were needed.
4. Behaviour is preserved verbatim — pre-extraction git history is
   the reference; the doc-strings call out any deferred-decisions.

Verification (no live substrate run; per-module smoke tests instead):
- `tests/validator/test_autoresearch_loop_static_guards.py`: 2/2 pass
- `runner_r1_fixture_regression`: 5/5 pass
- `runner_r1_suite_guard_fixture_regression`: 4/4 pass
- `scripts/public/control/runtime_smoke_test.py`: full pass
- per-module unit smokes (write a file, read it back, parse a payload, etc.): all pass

## What remains pending

Targets 1 (`main.py` iter-body wrap) and 3 (`dispatch.py` aggregator)
from the original Phase 4g list remain. The honest scope for those:

- **Target 1**: lines 4141–8618 (~4,500 lines) of iter-body need
  wrapping in `run_main_loop(args, rubric_data, …)`. Module-globals
  used by the body must move into an IterState dataclass or be
  passed as args. Realistic effort: 6–10 hours of careful work + a
  live substrate smoke test.
- **Target 3**: 6 phase-specific dispatchers
  (`pre_iter1_dispatch`, `pre_fit_dispatch`, `post_fit_dispatch`,
  `post_harness_dispatch`, `gp180_dispatch`, `blitz_dispatch`)
  could be consolidated behind a single `dispatch_phase(phase, ctx)`
  router. The existing dispatchers already share IterContext so
  the consolidation is mostly call-site rewriting. Effort: 4–6 hours.

Other extractable clusters identified but not shipped this session:
- Champion artifact synchronization (3 functions: reconstruct, sync
  check, promote latest). Heavy coupling to `args` namespace +
  MUTATOR_MODEL_ID/JUDGE_MODEL_ID; defer until those are
  parameterized.
- Cluster B project-state snapshot (3 truly-pure helpers:
  capture_project_state, restore_project_state, latest_debate_log_text).
  Small (~30 lines); low priority.
- Startup helpers (`_load_v4_stage_index`, `_startup_axiom_restore_*`).
  Pure but invoked exactly once at run-start; extraction yields
  organisational rather than testability gains.
- GP-156 R1 hardening block (~lines 2044-2078). Already invokes
  imported helpers; small remaining inline logic.

The validator carve-up was the highest-leverage architectural cleanup
of the past sprint (split flat namespace into core / utilities /
committees / tests). Phase 4g is cosmetically remaining but not
decisive for ZTARE engine quality — the orchestrator/* modules
that DO ship are the ones that matter for testability and modularity.
The 4,800-line iter-body is loud but doesn't gate any engine
capability. Defer to dedicated session.

## Pointers for the next session

- `src/ztare/validator/autoresearch_loop.py:4141` — main entry, where
  Target 1 extraction begins
- `src/ztare/orchestrator/__init__.py` — what's already exported
- `src/ztare/orchestrator/state.py` — Phase 4c state primitives
- `src/ztare/orchestrator/iter_context.py` — Phase 4a context dataclass
- `scripts/public/control/runtime_smoke_test.py` — closest live-run smoke today
- Architectural map verifier:
  `scripts/public/validators/validate_autoresearch_arch_map.py ex-post`
- Commit pattern: per Linus atomic-commit discipline, each extraction
  lands in its own commit; arch-map verifier must stay green per-commit
