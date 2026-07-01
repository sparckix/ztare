---
description: "Read-only architecture-metrics + connascence report for the LeanMill subsystem (src/ztare/leanmill). Generated artifact, not a design doc."
---

# LeanMill Architecture Metrics Report

> Read-only analysis. Tools: `radon cc/mi`, `cohesion`, `lizard`, plus a custom intra-package
> import-graph pass. Scope: `src/ztare/leanmill/` (105 modules, ~44,900 LOC, 1,333 analyzed blocks).
> Cross-reference `docs/concepts/leanmill_architecture.md` for the *intentional* single-door design
> (which is why several "hotspots" below are flagged as DO-NOT-SPLIT).

## Summary

- **Overall health: B-average, with a fat right tail.** Mean cyclomatic complexity is B (7.31) and 79%
  of blocks are rank A/B. But the tail is severe: **18 rank-F and 14 rank-E** functions, and complexity is
  hyper-concentrated in the solver lane — `solver_core.py` (5,058 LOC), `governed_dag_search.py`,
  `autoformalize.py`/`autoformalize_notes.py`, and `isomorphism_decompose.py` account for essentially all
  of the extreme scores. Six files are so large radon MI floors them at **0.00**.
- **One genuinely pathological function.** `solver_core._build_dag_move_runner.move_runner`
  (`solver/solver_core.py:2333`) is **222 CCN / 4,928 tokens / 642 lines** — 2.5× the next worst. This is
  the single highest-yield target and is *not* one of the intentional single-door chokepoints.
- **The top 3 refactor targets** (detail in the plan): (1) **`move_runner`** — decompose the per-move
  dispatch into a move-handler table; (2) **the `solve` / `solve_adhoc` param + result-dict contract**
  (`solve_adhoc` = 139 CCN, 11 params; `solve` = 92 CCN; both key off a stringly-typed result dict shared
  by 40+ sites) — introduce a typed config/result object; (3) **`autoformalize_and_solve`**
  (`solver/autoformalize.py:2003`) — **19 positional-ish params**, 72 CCN — the worst parameter list in the
  package.
- **Coupling is a hub-and-spoke, mostly by design.** `solver_core` is the fan-out hub (Ce=33, instability
  0.87) and `lean_source` (Ca=17) + `statement_integrity` (Ca=16) are the stable fan-in gates (instability
  ≤0.06). All **5 import cycles are deferred (function-local) imports** — the codebase's deliberate
  cycle-break idiom, not import-time deadlocks — so they are low-risk. The two multi-module SCCs are the
  known solver core-set.
- **Connascence: the dangerous seam is the stringly-typed solver result dict**, a cross-module Connascence
  of Meaning + Name spanning ~15+ modules (`res["shelf"]`, `res["deep_closures"]`, `res["iso_route"]`, …).
  The 202-flag `ZTARE_*` env surface is a second Connascence-of-Meaning surface, but it is already partly
  policed by the existing `flag_audit` split-brain guard.

---

## Metrics tables

### 1. Cyclomatic complexity — worst functions (radon `cc`, top 18 by CCN)

Distribution over 1,333 blocks: A=782, B=277, C=200, D=42, **E=14, F=18**. Average B (7.31).
(CCN below from `lizard`, which agrees with radon's rank ordering.)

| CCN | file:line | function | note |
|----:|---|---|---|
| **222** | `solver/solver_core.py:2333` | `_build_dag_move_runner.move_runner` | **outlier**; per-move dispatch god-closure |
| 139 | `solver/solver_core.py:4058` | `solve_adhoc` | the one governed entry (§4.3.0) — *partly intentional* |
| 127 | `solver/governed_dag_search.py:1706` | `_selftest` | test harness, low priority |
| 115 | `solver/autoformalize_notes.py:158` | `autoformalize_from_notes` | the CAMPAIGN entry — *partly intentional* |
| 92 | `solver/solver_core.py:2993` | `solve` | the worker pipeline |
| 82 | `solver/isomorphism_decompose.py:1218` | `_selftest` | test harness |
| 78 | `solver/governed_dag_search.py:1319` | `run_governed_dag_search` | DAG search driver |
| 74 | `solver/solver_core.py:1555` | `_agentic_leaf_warm_solve` | warm-session solve |
| 72 | `solver/autoformalize.py:2003` | `autoformalize_and_solve` | **19 params** |
| 57 | `solver/autoformalize_notes.py:1442` | `main` | CLI |
| 56 | `solver/autoformalize_notes.py:814` | `write_refined_notes` | blueprint write-back |
| 56 | `solver/move_calibration.py:909` | `_self_test` | test harness |
| 46 | `work_queue.py:1385` | `main` | CLI (328 NLOC) |
| 44 | `solver/witness_transport.py:471` | `_selftest` | test harness |
| 43 | `solver/governed_dag_search.py:916` | `_strategist_move` | move selection |
| 42 | `solver/isomorphism_decompose.py:740` | `solve_decomposition` | 8 params |
| 40 | `run_diagnostics.py:110` | `summarize_run` | reporter |
| 37 | `solver/solver_core.py:419` | `_build_solver_context` | context builder |

*Signal:* strip `_selftest`/`_self_test`/`main` (test+CLI, deliberately linear-but-long) and the real
production hotspots are `move_runner`, `solve_adhoc`, `solve`, `run_governed_dag_search`,
`_agentic_leaf_warm_solve`, `autoformalize_and_solve`, `autoformalize_from_notes`.

### 2. Maintainability index — lowest files (radon `mi`)

Rank distribution: A=91, B=6, **C=8**. (Radon floors MI at 0.00 for the largest/most-complex files; treat
the six 0.00 files as "off the scale," ordered here by LOC.)

| MI | rank | file | LOC |
|----:|:--:|---|----:|
| 0.00 | C | `solver/solver_core.py` | 5,058 |
| 0.00 | C | `solver/governed_dag_search.py` | 2,604 |
| 0.00 | C | `solver/autoformalize.py` | 2,598 |
| 0.00 | C | `work_queue.py` | 1,735 |
| 0.00 | C | `solver/autoformalize_notes.py` | 1,726 |
| 0.00 | C | `solver/isomorphism_decompose.py` | 1,588 |
| 2.49 | C | `solver/abduction.py` | — |
| 7.37 | C | `solver/move_calibration.py` | 1,311 |
| 9.15 | B | `solver/agentic_leaf.py` | — |
| 12.60 | B | `semantic_premise_shelf.py` | — |
| 12.60 | B | `solver/conjecture.py` | — |
| 16.94 | B | `solver/family_lemma_library.py` | — |
| 17.30 | B | `workbench_actions.py` | — |
| 18.56 | B | `typed_exit.py` | — |

*Flag (MI < 20 = hard to maintain):* the six 0.00 files + `abduction`, `move_calibration`, `agentic_leaf`,
`semantic_premise_shelf`, `conjecture`, `family_lemma_library`, `workbench_actions`, `typed_exit`.

### 3. Cohesion — lowest LCOM-style classes (cohesion `-d`, methods ≥ 3 only)

Median class cohesion is 25%. **The many 0.0% classes with < 3 methods are dataclasses / enums / Protocols
(`WorkItem`, `LeafResult`, `Verdict`, `SolverConfig`, …) — a cohesion-tool false positive** (no shared
instance state to bind methods). Filtered to classes with real behavior:

| coh% | #fn | file:line | class | note |
|----:|--:|---|---|---|
| 0.0 | 7 | `workbench_actions.py:30` | `ActionStorage` | ABC / interface — expected 0 |
| 0.0 | 8 | `workbench_target.py:26` | `TargetStorage` | ABC / interface — expected 0 |
| 12.5 | 4 | `solver/leanmill_hardener.py:40` | `LeanmillHardener` | real split candidate |
| 22.2 | 9 | `workbench_target.py:46` | `FileTargetStorage` | storage grab-bag |
| 25.0 | 8 | `workbench_actions.py:48` | `FileActionStorage` | storage grab-bag |
| 27.1 | 12 | `solver/faithfulness_store.py:47` | `FaithfulnessStore` | 12 methods, low binding |
| 33.3 | 9 | `solver/outcome_link.py:118` | `OutcomeLinkStore` | store grab-bag |
| 37.0 | 9 | `solver/no_good_store.py:86` | `NoGoodStore` | store grab-bag |
| 40.0 | 5 | `solver/isomorphism_decompose.py:45` | `_DecomposeDomain` | — |

*Signal:* the low-cohesion real classes are all **`*Store` / `*Storage` persistence classes** — a normal
pattern (each method touches a different persisted field), low refactor value. The one worth a look is
`FaithfulnessStore` (12 methods, 27% — candidate to split read-path vs write-path). Abstract base classes
(`ActionStorage`, `TargetStorage`, `Provider`) correctly score 0 and should be ignored.

### 4. Coupling — import graph (custom intra-package pass)

**Highest fan-in (Ca — stable, widely-depended-on; keep stable):**

| Ca | module | I | role |
|---:|---|--:|---|
| 17 | `lean_source` | 0.00 | canonical Lean parsers — the single-door parser (intentional hub) |
| 16 | `solver.statement_integrity` | 0.06 | the faithfulness gate (intentional hub) |
| 12 | `solver.agentic_leaf` | 0.29 | the leaf + `LeafResult` contract |
| 9 | `solver.prompts` | 0.00 | prompt text store |
| 8 | `solver.proof_cache` | 0.20 | — |
| 8 | `solver.agent_output` | 0.00 | `fenced_block` parser (canonical) |
| 8 | `solver.conjecture` | 0.38 | — |

**Highest fan-out (Ce — unstable, orchestration; where complexity concentrates):**

| Ce | module | I | role |
|---:|---|--:|---|
| **33** | `solver.solver_core` | 0.87 | the fan-out hub / orchestrator |
| 17 | `solver.autoformalize_notes` | 0.89 | campaign driver |
| 12 | `solver.autoformalize` | 0.80 | firewall + solve driver |
| 11 | `solver.isomorphism_decompose` | 0.85 | decomposition driver |
| 6 | `solver.reflection` | — | — |
| 6 | `solver.forecast_router` | 0.75 | — |

**Import cycles (all DEFERRED / function-local — low risk):**

| cycle | kind |
|---|---|
| `isomorphism_decompose` ↔ `solver_core` | function-local imports both directions |
| `proposer_pool` ↔ `solver_core` | function-local |
| `autoformalize_notes` ↔ `autoformalize` | function-local |
| `cross_voting` ↔ `autoformalize` | function-local |
| `api_agentic_leaf` ↔ `agentic_leaf` | function-local |

Two multi-module SCCs (formed only through those deferred edges): an 11-module core set
(`solver_core`↔`governed_dag_search`↔`agentic_leaf`↔`conjecture`↔`abduction`↔`sledgehammer`↔… ) and the
3-module `{isomorphism_decompose, proposer_pool, solver_core}`. **No top-level circular imports exist** — the
package deliberately breaks every cycle with deferred imports. This is acceptable but hides the true
dependency shape from static tools.

### 5. Long parameter lists / token bloat (lizard `-w`)

| params | CCN | NLOC | file:line | function |
|---:|---:|---:|---|---|
| **19** | 72 | 181 | `solver/autoformalize.py:2003` | `autoformalize_and_solve` |
| 14 | 33 | 108 | `solver/agentic_leaf.py:888` | `solve_leaf` |
| 12 | 78 | 255 | `solver/governed_dag_search.py:1319` | `run_governed_dag_search` |
| 11 | 139 | 364 | `solver/solver_core.py:4058` | `solve_adhoc` |
| 11 | 34 | 122 | `solver/solver_core.py:1221` | `_validate_against_contract` |
| 11 | 28 | 84 | `solver/autoformalize.py:433` | `faithfulness_gate` |
| 11 | 16 | 111 | `semantic_premise_shelf.py:376` | `build_semantic_premise_shelf` |
| 10 | 24 | 40 | `solver/proposer_pool.py:291` | `attack_node` |
| 10 | 19 | 45 | `solver/solver_core.py:354` | `_record_attempt` |
| 9 | 36 | 59 | `solver/conjecture.py:167` | `decomposition_dag_audit` |

Biggest single blocks by NLOC (production, excluding tests/CLI): `move_runner` (432 NLOC / 642 lines),
`solve` (365), `solve_adhoc` (364), `autoformalize_from_notes` (274), `run_governed_dag_search` (255).

---

## Connascence findings (cross-module seams, ranked by strength × degree × locality)

Ranking rule applied: dynamic + cross-module Connascence of Meaning/Algorithm/Position is worst; static,
local Connascence of Name is fine. Only cross-module (the dangerous locality) seams are listed.

| # | Seam | Connascence class | strength×degree×locality | file:line | why risky |
|---|---|---|---|---|---|
| **C1** | Solver **result dict** stringly-typed keys (`res["shelf"]`, `res["deep_closures"]`, `res["iso_route"]`, `res["library_growth"]`, `res["outcome"]`, …) produced by `solve`/`solve_adhoc`, consumed by ~15+ modules | **Connascence of Meaning + Name** (dynamic, cross-module) | **highest** — 40+ keyed sites, high degree, cross-module | `solver/solver_core.py:2993`, `:4058` (producer) | a renamed/typo'd key fails silently (KeyError or `.get` default), no compile-time check; a consumer reading `res["shelf"]` must *know* the untyped shape the producer emits |
| **C2** | `ZTARE_*` env-flag surface — **202 distinct flags**, ~10 read in ≥3 files (e.g. `ZTARE_LEANMILL_ISO_ROUTE` in 6, `ZTARE_CONJECTURE_DECOMPOSE`, `ZTARE_LEANMILL_PROPOSER_POOL` in 3) | **Connascence of Meaning + Value** (dynamic, cross-module) | high — high count, but *partly guarded* | across package (see `grep ZTARE_`) | a flag's on/off semantics + default must agree across every reader; the split-brain-default face already bit `proposer_pool` — **mitigated** by the existing `flag_audit` guard (§4.3a) |
| **C3** | `LeafResult` dataclass field contract (`closed`, `reason`, `gap`, `statement_false`, `statement_false_confirmed`, `recovered_from_drift`, …) | **Connascence of Name + Type** (static, cross-module) | medium — Ca=12, but a *dataclass* (typed, static) | `solver/agentic_leaf.py:476` | far safer than C1 because it is a typed dataclass, not a dict; still, 12 importers bind to field names — a rename ripples. This is the *right* shape; C1 should converge to this |
| **C4** | The `(target_name, source, goal, *, substrate, mode, timeout_s)` producer→`solve_adhoc` interface + the 19-param `autoformalize_and_solve` | **Connascence of Position** (dynamic, cross-module) | medium-high — many producers, positional-ish long lists | `solver/solver_core.py:4058`, `solver/autoformalize.py:2003` | §4.3.0 mandates every target-producer call this exact interface; the long param list means a positional mismatch or a new required arg silently breaks producers. Keyword-only helps but 11–19 args is beyond human tracking |
| **C5** | `_move_prior` imported function-locally by `move_runner` from `governed_dag_search`; move-name strings shared between the move corpus, `move_runner`, and `_strategist_move` | **Connascence of Algorithm + Meaning** (dynamic, cross-module) | medium | `solver/solver_core.py:2333` (calls `governed_dag_search._move_prior`) | the per-move dispatch logic and the move-name vocabulary are duplicated/coordinated across `move_runner`, `move_policy`, `_strategist_move`; a new move must be wired consistently in each — the "forgotten move surface" class the architecture already fought (§4.3a move corpus) |
| **C6** | Deferred-import cycles (5) — each side reaches into the other's module-level functions at call time | **Connascence of Name** (dynamic via late binding, cross-module) | low-medium | listed in §4 | low risk (function-local, no import-time hazard), but they encode a real bidirectional dependency that hides the layering from tools and makes extraction harder |

---

## Prioritized refactor plan

### P0 — `move_runner` god-closure (`solver/solver_core.py:2333`)
- **Target:** `_build_dag_move_runner.move_runner` (the nested `def move_runner(node, move, budget)`).
- **Evidence:** 222 CCN, 4,928 tokens, 642 lines, 432 NLOC — **2.5× the next-worst production function**;
  the dominant contributor to `solver_core.py`'s MI=0.00. Connascence **C5** (per-move algorithm + move-name
  meaning coordinated across `move_runner`/`move_policy`/`_strategist_move`).
- **Refactor (extract to a dispatch table):** the function is a giant `if move == "…": … elif move == "…":`
  ladder over move names. Extract each branch into a named handler `_move_<name>(node, budget, ctx)` and
  drive them from a `{move_name: handler}` table built once. The shared closure state (`_boost`, forecast
  recording, `_cap`) becomes an explicit `ctx` object passed to each handler.
- **Expected improvement:** `move_runner` drops from 222 CCN to a thin dispatcher (~15 CCN); each handler
  lands in rank A/B (≤15 CCN). `solver_core.py` MI lifts off the 0.00 floor. **Caveat:** the dispatch table
  is the correct single-surface for moves — it must *replace*, not sit beside, the existing branches, or it
  reintroduces the "fifth move surface" the architecture forbids (§4.3a). Keep it in `solver_core` (do not
  scatter handlers across files) to preserve the single-door property.

### P1 — Typed solver result object (kills connascence C1)
- **Target:** the dict returned by `solve` (`solver/solver_core.py:2993`) and `solve_adhoc`
  (`:4058`), consumed by 15+ modules via `res["…"]`.
- **Evidence:** Connascence **C1** (highest-ranked seam: dynamic, cross-module, ~40 keyed sites). No
  compile-time protection today; a mistyped key degrades silently to a `.get` default — exactly the
  silent-degrade class the memory notes warn about repeatedly.
- **Refactor (introduce a seam):** define a `@dataclass SolveResult` (or a `TypedDict`) with the ~20 stable
  keys already in use (`row_id`, `target`, `shelf`, `lemmas`, `deep_closures`, `outcome`, `iso_route`,
  `library_growth`, `source_cue_check_status`, `fp`, `plan_action`, …). Producers return it; keep
  `__getitem__`/`.get` (or `dataclasses.asdict`) as a shim so consumers migrate incrementally. Model it on
  the *already-good* `LeafResult` (C3) — the codebase clearly prefers typed results, so this is convergence,
  not a new pattern.
- **Expected improvement:** turns a dynamic cross-module Connascence of Meaning into a static Connascence of
  Name+Type (safest class); typos/renames become type errors; the result shape becomes self-documenting.
  **Do incrementally** — a big-bang rename across 40 sites is its own risk.

### P1 — Parameter-list reduction on the two worst signatures
- **Target:** `autoformalize_and_solve` (`solver/autoformalize.py:2003`, **19 params**) and
  `solve_adhoc` (`solver/solver_core.py:4058`, 11 params); secondarily `solve_leaf` (14),
  `run_governed_dag_search` (12).
- **Evidence:** Connascence **C4** (Position, cross-module, many producers); 19 params is unmaintainable and
  a magnet for positional bugs when a producer is added.
- **Refactor (reduce params via a config object):** group the cohesive clusters — the campaign/blueprint
  context, the budget/timeout knobs, the flag overrides — into 2–3 small frozen dataclasses
  (e.g. `CampaignCtx`, `SolveBudget`). Pass those instead of loose args. Do **not** touch the *soundness*
  interface `(target_name, source, goal, *, substrate, mode, timeout_s)` that §4.3.0 pins — only bundle the
  optional/advisory tail.
- **Expected improvement:** `autoformalize_and_solve` 19→~6 params; `solve_adhoc` 11→~5. Lowers the
  positional-connascence degree and makes the §4.3.0 producer contract enforceable by type.

### P2 — `FaithfulnessStore` cohesion split (optional, low yield)
- **Target:** `solver/faithfulness_store.py:47` `FaithfulnessStore` (12 methods, 27% cohesion).
- **Evidence:** lowest-cohesion *real* class with meaningful method count.
- **Refactor:** if the 12 methods partition into read-path vs write-path (or per-record-kind), split into two
  classes sharing a small backing handle. **Verify first** — most `*Store` classes are legitimately low-cohesion
  (each method touches one persisted field) and splitting adds indirection for no gain. Skip unless the read/write
  partition is clean.

### P2 — Document the deferred-import layering (no code change)
- **Target:** the 5 deferred-import cycles / 2 SCCs (§4).
- **Refactor:** these are safe as-is (function-local, no import hazard). The lazy fix is *not* to break them
  (that would force a shared-types module and more churn) but to add a one-line comment at each deferred import
  naming the cycle it breaks, so the layering intent is visible. Only extract a shared module if a *third*
  party starts needing the same round-trip.

---

## Caveats — where a "refactor" would REINTRODUCE a sibling (do NOT split)

The architecture (`docs/concepts/leanmill_architecture.md`) *intentionally* centralizes several functions into
ONE chokepoint precisely to prevent sibling-drift bugs (the dominant bug class in this repo's history). High
complexity there is the cost of the single-door property, not accidental sprawl. **Do not split these to chase
a CC number:**

- **`solve_adhoc` (139 CCN)** is "the ONE governed solve entry" (§4.3, principle 2). Every producer routes
  through it by design. Reducing its *params* (P1) is fine; **splitting its body into parallel solve paths is
  forbidden** — that is exactly the "parallel solve/governance path" the architecture bans.
- **`statement_integrity.check` (33 CCN, Ca=16)** and **`lean_source` (Ca=17)** are the deliberate single-door
  gate + parser. Their high fan-in is the *goal* (one door, no siblings). Do not fork them; a second parser is
  the canonical sibling-drift bug (memory: `reference_kernel_faithfulness_not_text_diff`,
  `feedback_anti_sibling_default_on_at_chokepoint`).
- **`autoformalize_from_notes` (115 CCN)** is the single CAMPAIGN entry (§4.3.0) — the write-back aggregate is
  intentionally campaign-only. Extract *helpers* from it, but keep it the one campaign door.
- **`move_runner` (P0) is the exception:** it is NOT a soundness single-door — it is a dispatch ladder. Extracting
  per-move handlers *behind a single dispatch table in the same module* preserves the single-surface property
  (§4.3a: one corpus, two consumers) while removing the complexity. The failure mode to avoid is scattering the
  handlers across files or adding a *second* dispatch surface.
- **`_selftest` / `_self_test` / `main` functions** dominate several F-ranks (governed_dag_search:1706 = 127 CCN,
  etc.). These are test batteries and CLIs — long but linear, low change-risk, low refactor value. Deprioritize.
- **The 202-flag `ZTARE_*` surface (C2)** is large but the dangerous face (split-brain defaults) is *already*
  guarded by `flag_audit`. Do not build a new flag registry; extend the existing guard if coverage gaps appear.

---

## Tool notes / caveats

- Radon MI **floors at 0.00** for the six largest files; ordering within that floor is by LOC, not a true MI
  gradient. Treat all six as "off the scale — too large," not as a precise ranking.
- The `cohesion` tool reports **0.0% for dataclasses, enums, Protocols, and ABCs** (no methods sharing instance
  state) — a systematic false positive. All such classes were filtered out of the §3 table.
- `pydeps --show-cycles` was not used for the final numbers; the intra-package import graph was computed with a
  custom pass (resolves relative imports, matches against known modules) to get per-module Ca/Ce and to
  distinguish top-level vs deferred imports (which `pydeps` does not surface). No tool errored on any file.
- CCN figures cross-checked between `radon cc` and `lizard`; they agree on the ordering of the top ~20.
