# Harness changes, 2026-07-19 — mechanizing the meta-lessons (no game teaching)

Companion to `AGENTS.md` §8a. Both changes are substrate-general; no ls20 semantics (portal, key, coordinates, level structure) appear anywhere leaf-visible. The lessons are harness-design rules; the answers stay the leaf's job.

## Change 1 — `plan_witness_gap` (planner.py): evidence-support acquisition

**Defect class (lesson 8a-1):** novelty is scored over the model's *predicted* successors. Where the model is wrong, its prediction looks like an already-visited state → zero novelty → the planner never fires that transition. The engine therefore starves itself of exactly the counterexamples it needs. "Actions are falsifiers" was in the thesis, not the objective.

**Fix:** new terminal acquisition fallback. When goal/coverage/novelty all saturate, best-first search to the nearest reachable `(alpha(state), action)` pair with **no witnessed transition in the evidence bank**, and fire it. Witness support is computed from observed transitions (model-independent by construction), seeded from `evidence_transitions` at pursuit entry and updated as live observations land. Steering only — the sealed terminal verifier still owns success, so a wrong steer costs efficiency, never correctness. Receipt policy: `witness_gap_acquisition` / `unwitnessed_transition_pair`.

Self-check: toy-world test (finds nearest unwitnessed pair; returns None on saturated bank). All 43 planner regression tests pass.

## Change 2 — acquisition under unresolved identification (arc3_play_loop.py)

**Defect class (lesson 8a-2):** the `residual_frontier` gate path never sets `best_model`, so when governed identification ends without an executable candidate (typed control exits), `play_model is None` → "existing evidence is preserved without spending environment actions." The loop's own stated invariant — "always PLAY the deepest-playing model ever found" — silently died in that branch. Result: a carrier exact on 14,707/14,707 rows was barred from the environment because it has one known residual; model-completeness gated environment contact. Measured consequence: 2/2 cycles `identification_unresolved`, zero live steps.

**Fix:** in that branch, lower the incumbent root carrier via `carrier_loader.load_carrier_path` (steering-only, explicitly no promotion authority) and proceed to the play/acquisition leg; cycle status `acquisition_with_unresolved_identification`. Abstain only if the incumbent fails to lower. Bootstrap-exploration path preserved for the empty-log cold start.

## Change 3 — support-ranked residual digest (evidence_digest.py, 2026-07-20)

**Defect class (lesson 8a-6, "position is meaning"):** `_residual_clusters` quotients the residual correctly by diff-signature, but sorted the classes by `repr(signature)` — **alphabetical**. The digest is budget-truncated and `emit()` breaks when the budget fills, so a high-support class that sorts late lexically is dropped from the leaf's prompt entirely. Measured consequence: the 495-row energy-refill class (83% of the residual; file 12) sat mid-list alphabetically and was truncated out of the leaf's view — so for a week the leaf was never asked to close the dominant residual, wrote local patches on whatever small class it saw, and failed `visible_replay_exact`.

**Fix (one line):** `clusters.sort(key=lambda c: (-len(c["indices"]), min(c["indices"])))` — rank by rows-covered descending, tie-break by first index. Substrate-general: the key is class support, never a substrate noun; applies identically to residual classes and per-mechanic exemplars. 24/24 evidence_digest tests pass; unit-checked that the dominant class now leads.

**Why it's the highest-leverage of the three:** changes 1-2 bank the right transitions; change 3 makes the leaf actually *see* the dominant residual they reveal. Without it, better evidence still gets buried under the budget cut.

## Change 4 — observed-tier row-bitmap dominance at the promotion door (pre_judge_gate.py + champion_materialization.py, 2026-07-20)

**Defect class (gate-achievability at the promotion door):** `visible_replay_exact` was an absolute observed-tier must-pass. That was sound only under the invariant "the incumbent is visible-perfect" — then no-regression + strict-improvement degenerates to exactness. Once acquisition grows the bank after promotion, the incumbent itself fails rows (measured: 617 wrong of 16,506), and absolutism blocks every strict improver forever: a candidate fixing 500 of 617 wrong rows was hard-blocked. Determinism beyond the soundness boundary (promotion only selects the *steering* incumbent; the sealed terminal verifier still owns success) — a Goldilocks violation by the repo's own doctrine. Consequence measured live: the leaf induced the correct dominant-mechanic law ("exhaustion-restore") and could never get it promoted.

**Fix:** `_observed_row_dominance_witness` — both carriers scored by the ONE shared evaluator (`build_row_bitmap`, content-addressed) over the same episode bytes; witness refused unless episode_hash + evaluator_sha match (no harness-local row spaces trusted). A failing row-scored observed gate is tolerated iff candidate wrong-rows are a **strict subset** of the incumbent's (zero regressions, strictly fewer). Threaded through the single chokepoint `_dominance_promotion_ok` (both consumers: pre-judge decision + champion materialization; the materializer's redundant absolutist pre-filter folded into `_dominance_check`). Env kill-switch `ZTARE_OBSERVED_ROW_DOMINANCE=0`; fail-closed on any missing datum (falls back to absolutism); non-row substrates unaffected (no `wrong_rows` diagnostics → no witness → unchanged).

**Why it is not overfit:** with a visible-perfect incumbent the witness cannot dominate, so the rule *reduces exactly to the old absolutism* — the current rule is the special case of the general one. No substrate noun anywhere; the witness is row-set inclusion under one evaluator identity.

Verified: 6/6 semantic self-checks (witness rescues only row-scored gates, dominance required, strict-improvement still required, all-pass unchanged); materialization suite 6/6. (Two pre-existing test failures in the operator's uncommitted pre_judge WIP noted, unrelated: `load_current_repair_frontier` removal.)

## Change 5 — the `pattern_write` operator family: System-1 learns restoration laws (2026-07-20)

**Defect class (grammar gap in the deterministic Kepler):** every miner family in `spec_abduction` (`translate/consume/accumulate/recolor/com`) describes movement or recoloring of existing matter. None can express "a region rewrites to remembered content" — the RESTORATION class (refills, respawns, display resets). Measured: an 80-row ls20 slice dense with refill witnesses yielded **zero rules**; the system had proposed the missing operator to itself 15 times (all rejected/open; 106 proposals, 0 adoptions ever).

**Built (through the governed path — planted-synthetic acceptance + non-regression):**
- `spec_catalog`: `pattern_write {rect, pattern}` executor; generic guards compose; honest DL = pattern length.
- `spec_abduction`: `_abduce_pattern_write` — 4-connected diff clustering (NOT `_cluster_rects`, which shatters adjacent cells), bounded rect-expansion to the s_next-connected extent of restored content (capped at 4×cluster+8 so background values can't flood), min-area 2.
- `_effect_present` pattern branch (region ARRIVED at pattern: post matches, pre didn't).
- **Memorizer containment (the hard-won part):** pattern_write is the family of last resort with exactly ONE door — a conditional-always post-selection pass that runs AFTER compact assembly, overlap/phase variants, AND physics-closure region mining; admits a guarded pattern only on a STRICT cut of the CELL metric (`_wrong_cell_count` — compound restorations land one cluster at a time; a transition metric would reject every partial fix); support-ranked (occurrences × cells, 8a-6); greedy-chained; kill-switch `ZTARE_PATTERN_WRITE=0`. Patterns are excluded from the always-intersection and the per-action windows entirely — measured: every softer containment (ordering-last, pre-loop variants, cross-op pair search) flipped planted recoveries to extensionally-equivalent memorized forms.

**Verified:** 3/3 planted acceptance (miner/guards/end-to-end 40/40); 234/234 worldmodel suite; ls20 bench: same slice went 0 rules → `region_event` + **`pattern_write [61,13,62,54] len 84`** — the energy bar's refill law mined from data with a learned count guard, the first autonomous catalog-vocabulary extension in the project's history (proposals 106 → first adoption-equivalent, via miner rather than card).

**The catalog-promotion funnel note:** this change routes AROUND the dead card pipeline by giving System 1 the family directly; the 15 cards' diagnosis is thereby confirmed correct. The card pipeline itself (0% conversion) remains the open governance item.

## Why these five compose

Change 2 gets the loop back into the environment when identification stalls; Change 1 points the environment budget at the transitions no one has ever witnessed — which is where the unexpressed law lives. Together they mechanize: *when you can't explain, go touch what you've never tried.* The leaf then sees the resulting counterexamples through the ordinary evidence path and must induce the law itself.

## Session receipts

- `AGENTS.md` §8a — six meta-lessons (general form, RCA-derived).
- Out-of-loop quarantined contact session (2026-07-19, `workspace/win_attempt_l3_trace.jsonl`, `admissible_to_synthesis=false`): confirmed the portal law live twice, refuted the dead-end-exit hypothesis by contact, discovered mode-conditional dynamics (see file 10). Direction-buying only; the governed collector must reacquire.
- First post-change grind runs (receipts own ongoing status; first-fire recorded here per wiring discipline):
  - Change 2 first fire: cycle status `acquisition_with_unresolved_identification`; 250 live steps, +75 banked transitions, 2 boundary classifications — first environment contact after a week of zero-step cycles.
  - Change 1 required a follow-up (missed-sibling, caught by receipts): the fallback only triggered on empty plans, but a saturated sweep still emits non-empty known-uninformative coverage plans. Fixed by overriding the coverage plan at the saturation verdict itself.
  - Change 1 first fire (grind 3): `acquisition_routing.jsonl` → `witness_gap_acquisition | unwitnessed_transition_pair | depth 2 (6 nodes)`; plan executed live, +18 transitions. Saturation → witness-gap → environment contact chain verified end-to-end.
