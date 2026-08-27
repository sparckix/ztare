# Compression & scale — the Sutskever pass (2026-07-20)

Frame: compression IS the engine. The champion is the compressed history; the catalog is the compressed mechanic-space; the digest is compressed evidence. Anywhere the system re-pays for information it has already compressed, it gets slower as it learns — the anti-scaling law. This pass measured the biggest leak and closed it, and maps the rest.

## Measured: 80.4% of the bank is redundant to score

Live ls20 bank: 16,506 rows → **3,242 distinct (s,a,t)** — and full-row distinct is also 3,242 (deterministic environment: zero contradictions among duplicates). Every full-bank replay (gate, diagnostics, bitmap, candidate scoring) was paying 5× for content the bank already contains.

## Shipped: content-quotient replay (`_memoized_predictor`, gates.py)

Carriers are **pure functions of (s,a,t) by contract** — so memoizing predictions is verdict-identical *by purity*, not by sampling. No equivalence proof debt: identical inputs, identical outputs, per-call memo (no cross-call staleness), typed-failure side channel carried through hits. Wired at the three chokepoints: `replay_consistency_gate`, `replay_diagnostics`, `build_row_bitmap`. Abduction already class-quotients via `_ScoreContext` (verified — its scoring consults `classes_for`). 257/257 tests pass.

This composes with acquisition: witness-gap steering deliberately AVOIDS re-witnessing known (state, action) pairs, so the marginal row is increasingly likely to be novel — acquisition maximizes information per environment step while the quotient eliminates paying twice for the rest. Both sides of the same coin: **spend only on surprise.**

## The scale map (what breaks at 10× evidence / 10× games, in order)

1. ~~`env_frame_indices`~~ — CORRECTED: already content-memoized (`_ENV_FRAME_CACHE` on `log.content_hash()`); the measured 14.8s was a cold first call per bank state, warm calls are dict hits. The remaining cold cost (~14s of `_color_counts` over 2×16.5k grids, once per append) is acceptable; fold into the append lineage only if per-append cadence rises.
2. ~~The nogood ledger is quadratic~~ — SHIPPED (2026-07-20): measured 21MB / 837 rows / 365 distinct signatures (2.3× write bloat, ~25KB of duplicate grids per row, full re-parse per `blocks()` consult). Fixed at both chokepoints in `spec_nogood.py`: stat-keyed parse cache (consult cost ∝ distinct clauses, not history) + decline-to-append for already-indexed signatures (growth bounded to distinct clauses; ledger stays append-only — never rewritten, only declined). 8/8 nogood tests + worldmodel suite green. Historical 21MB left in place (append-only doctrine; compaction would need operator sign-off).
3. **The authority gate re-replays the full bank after small appends** (the docs' own "weakest computational seam"): the append-lineage + bitmap machinery exists; the missing piece is suffix-validation reuse of the prior full-gate receipt. This is the true residual-scaling fix — gate cost ∝ new rows, not total rows.
4. **The LLM lane is the token wall**: ~4min × 3 iterations of codex per cycle vs ~seconds of System 1. The scale strategy is exactly what Change 5 did: keep moving law families INTO the deterministic miner so the LLM is reserved for genuine grammar ceilings. Every family migrated is a permanent compute dividend (Sutskever's point: the compressor that generalizes is the one you can afford to run everywhere).
5. **Cross-game scale (tu93, beyond)**: the catalog is the advice string — its value is amortized across games. The blockers are known (coordinate-action interface; adapter-width `variables` rung has no candidate organ since causal_compiler was deleted). Per-game cost should FALL as the catalog grows; measure with the already-defined `V_G`/`R_O` metrics once a second game runs.

## Source-code compression pass (same day, operator-directed)

Codex hill-climbed for weeks; a fresh import-graph scan (src+scripts+tests) with dynamic-reference verification (rubrics, Makefile, project scripts — the `*_gt` substrate modules are rubric-driven dynamic loads and were correctly spared) found and removed **~3,930 LOC of verifiably dead code**:

- **Codex-orphaned worldmodel organs** (were live a week ago; their roles were absorbed by refactors): `challenger_portfolio` (disagreement-producer role moved into `version_space.py`), `evaluation_protocol`, `level_transfer_repair` (superseded by `level_boundary_seed`), `closure_audit` (superseded by `operator_proposals` — the reflex imports the latter).
- **Dead common modules** (zero references anywhere incl. non-Python): `llm_runtime_fixture_regression` (393), `runtime_execution_identity` (545), `pricing_calibration`, `turn_profile_adapter`, `theory_substrate_adapter`.
- **Dead functions**: `frontier_codec.batch_novelty_multi` (verified zero refs; `_subprocess_gate` and `plan_to_hole`/`coverage_planner` had already been removed by the operator's own passes).
- 9 orphaned test functions/files pruned with their subjects.

Verification discipline: every deletion preceded by a reference scan over src/scripts/tests plus rubric/Makefile/project greps (the "orphans are hypotheses" rule — the scan's first cut wrongly listed 27 rubric-loaded substrate modules as dead). Suites after: **318/318**.

Method note for repeat runs: the scan script is 30 lines (import-regex over the tree + per-module classification); rerun it after any multi-week LLM hill-climbing burst — codex leaves superseded twins behind when it moves a role, and twins are where the next split-brain bug breeds.

## Overnight run findings (2026-07-20 late) — the next two builds, precisely

1. **Routing deadlock (escaped, needs the real fix):** the system1 residual-frontier preemption assumes the patch compiler's language covers the frontier; when it doesn't (restoration law) and the mutator is down (codex wedged >60min past its own timeout ceiling, rc=124 with stdout 0 all night), the only wider-language producer (sprint full abduction) never runs. Env escape shipped: `ZTARE_FORCE_SPRINT_REABDUCTION=1` at the `_system1_status` chokepoint. Daylight fix: stagnation-based escalation — same frontier sha with zero gate-passing patches across N runs demotes the preemption automatically.
2. **The memorizer door never runs at scale (the decisive one):** with the escape on, round-1 full re-abduction on 16,506 rows ran 43.5 min to a `budget_exit` with residual 441 (down from 617 — partial progress) — but the pipeline was cut BEFORE the conditional-always door (it sits last, after physics closure), so `pattern_write` never entered the spec. Full-bank abduction cannot be the restoration family's carrier at scale. **The right integration is the patch path**: teach `deterministic_candidate_producers._catalog_operation_patch_compiler` to compose guarded `pattern_write` deltas over the incumbent (PATCH_BASE + delta), mined from the residual-frontier task's counterexample rows — residual-scoped cost, exactly the architecture's own prescription (cost ∝ residual), and it rides the promotion door's row-dominance change end-to-end. This is the single highest-leverage build remaining.
3. Codex-lane operational note: `ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS=90` did not bound a wedged codex CLI call (ran 66+ min); the timeout enforcement path deserves an audit when the lane is next used.

## Discipline notes

- Fast paths here required **zero** authority weakening: purity-quotient is exact; everything else stays screening-vs-authority per the repo's own rule.
- The memo is per-call by design — a cross-call cache would need the full identity convention (carrier sha × episode bytes × evaluator), which the bitmap cache already implements; don't build a second one.
