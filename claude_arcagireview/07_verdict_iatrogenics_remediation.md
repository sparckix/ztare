# Verdict — the ARC-AGI apparatus, harness iatrogenics, and the road to a general-purpose skill-acquisition engine

Consolidates: 00 (campaign forensics) + 01–06 (six full-code cluster reviews, ~50k LOC read, findings verified against live receipts and runnable probes). Date: 2026-07-15/16.

---

## 1. The one-paragraph verdict

The authority core is sound and the science it produced is real: exact replay over 14,707 rows, 16/16 withheld rollout, two in-loop operation acquisitions without a conductor-authored law, zero false ratifications since day one. But the system around that core has crossed into iatrogenic territory: ~181k LOC of apparatus for a 64×64 grid game, a 10:1 machinery-to-environment time ratio, ~4,300 LOC of governance that provably cannot change any behavior, ~2,500 LOC of cold science modules, a weakness-receipt stream that re-describes the same ~150 defects without converging, and — the deepest cut — the single autonomy lever the whole meta-layer exists to provide (grammar promotion without the conductor) switched off at its only call site: 106 proposals, 0 promotions. The 4 days of harness fixes were mostly good fixes (~70% root-cause), but they were spent paying interest on a surface that generates defects faster than one operator can fix them. The cure is not another organ; it is a deletion pass, one identity convention, one validator per boundary, and turning on the two loops that are built and dark.

## 2. Is it harness iatrogenics? Yes — with a precise boundary

**The inner ring pays its way.** Replay/holdout gates, carrier digest chains, refuted-experiment blocks, the strategy-card lifecycle, stale-surface currentness, capability scoping — all verified decision-bearing, all fail-closed under every tampering scenario the reviewers constructed. These receipts enabled real RCAs (gate achievability, the 261-row executor re-emission loop, close-laundering). Zero false ratifications held in live fire. Do not weaken this ring.

**The outer ring is the disease.** Evidence:

- **The apparatus injures its own evidence more than the environment resists.** The campaign's costliest failures were all self-inflicted signal corruption: `EpisodeLog.append` mis-stamping `t` (made step-dependent laws unrecoverable from their own evidence); the holdout gate unpassable-by-construction for a week (every candidate scored exactly 4 or 0); the feedback chain with three dead links; the workbench cache returning stale singleton receipts; 2,843 rows of "level-2" evidence that were all level-1 (`adapter.reset()`); and — live today — `within_epoch_view` silently dropping 93% of the bank (05/C1) and the candidate pool silently dropping the very carriers it exists to hold (03/F1). The environment (a deterministic grid game) never fought back; the harness did.
- **The failure-response loop is additive, and addition is the vector.** Every harness bug was answered with a new organ: a receipt family, an auditor check, an identity declaration, a briefing provider. Each organ adds surface that itself can be buggy, unwired, or stale — and measurably is: the trace auditor (2,093 LOC, 21 checks) has no consumer of its findings; the k-line prior (1,100 LOC) is unreachable by three independent proofs; the weakness ledger has no emission dedup and three receipt classes with no executor. The system now contains governance whose main occupation is auditing other governance's dead outputs, and a test (`test_no_dead_letter_receipts.py`) that freezes 12 dead ledgers as permanent debt rather than deleting them.
- **The doctrine predicted this and was not followed.** aci.md names the ratchet ("each out-of-loop fix makes the in-loop agent more dependent"), names the migration criterion ("net deletion"), and the architecture doc's own adoption discipline is "built ≠ wired ≠ fired." The working tree is +50k/−9k insertions-to-deletions; the wired-and-fired auditor is itself unwired. The constitution is right; the state doesn't obey it.
- **The counterfactual test.** Of the ~20 highest-severity findings across the six reviews, roughly three are about the environment being hard; the rest are the apparatus mis-keying its own caches, forking its own validators, latching its own stale receipts, or steering its own probes with holdout-derived constants (06/F1 — the repo's own "master discriminator" violation). The 4-day bug marathon was not bad luck; it is the expected maintenance bill of this surface area at this test coverage (~7 worldmodel test files for 40k LOC).

**Precise diagnosis:** iatrogenics of the *scaffolding*, not the *epistemology*. The determinism floor at the soundness boundary (the repo's Goldilocks rule) is correct and working. The injury comes from determinism sprayed everywhere else — telemetry, priors, auditors, parallel validators, per-consumer caches — where each new mechanism is another thing whose identity, wiring, and staleness must themselves be governed. That regress is the iatrogenic engine.

## 3. View on the docs

**aci.md** is the strongest document in the repo — the receipt-as-unit-of-interaction, the scaffolding ratchet, rejection hysteresis, position-is-meaning, and "every deterministic validator should be exposed as a read-only precheck" are genuinely good interface science, most of it purchased with named failures. Two criticisms: (1) it is a constitution the code does not keep — the single-door rule is violated by two sidecar validators, three `dynamics_assumption` resolution sites, a private carrier lowering in candidate_pool, and duplicated policy prose in three renderers; the net-deletion criterion is violated by the working tree itself; (2) several clauses have no enforcement mechanism, so they decay into aspiration — the doc should mark each clause as ENFORCED (by what) or ASPIRATIONAL, or the distinction between constitution and wish-list keeps blurring.

**arc_agi_3_system.md** is honest in a way most architecture docs are not — it names its own violations (the residual-scaling seam, observer_only status, the unowned tool-synthesis pipeline, cold modules). Keep that register. Problems: it is 1,580 lines and violates its own "position is meaning" rule — controlling contracts (proposal taxonomy, adoption discipline) sit past line 1,500 while case-study narrative occupies the middle; and despite its own rule that run status belongs in receipts, epoch-specific numbers keep accreting (already stale against the code in at least one place — the `(alpha(state), phase)` pruning claim at line ~292 no longer matches the diff). Restructure: contracts first, case studies out to the seam, hard cap on length.

## 4. Consolidated remediation (prioritized)

### P0 — live-path correctness (do before the next science run)
| # | Fix | Source |
|---|---|---|
| 1 | Holdout-blind experiment selection: delete episode_002-derived probe constants from `distinguishing_play.py`; probe targets arrive as provenance-carrying data, admissibility-checked against holdout refs | 06/F1 |
| 2 | `within_epoch_view`: epoch from boundary receipts (max authoritative `target_epoch`) or required explicit arg — never last-row inference; explicit mixed-bank policy for identity-less rows | 05/C1 |
| 3 | Route `candidate_pool._load_member` through `carrier_loader.lower_carrier_namespace` (restores PATCH_BASE/PROGRAM to the committee; un-no-ops disagreement probing) | 03/F1 |
| 4 | Split interned/visited in `StateInterner`; delete `_ensure_interners_synced` (positional set-cursor) | 04/H1,H2 |
| 5 | `resolve_episode_paths` raises on unreadable MANIFEST (one line); hard "holdout ref is never bridgeable" guard in the workbench contrast bridge | 05/C9, 01/F2 |
| 6 | `engine_router._unreachable_targets` honors `reopened` (reuse `distinguishing_play._resolved_target_ids`) | 02 |
| 7 | Stamp `spec_sha256`/epoch into Lean invariant certs at absorb; filter stale rows in `_invariants` before reachability pruning | 03/F3 |
| 8 | Per-program (or save/restore) DSL extension registry — kill global `EXTENSIONS.clear()` | 03/F2 |

### P1 — one convention, enforced at chokepoints
9. **One identity rule for every cache/ledger key**: content digests of (candidate bytes, evidence bytes, evaluator identity captured once at import). Apply to: bitmap cache load_error+rubric gap (05/C6,C7), `version_space_fp_cache` (06/F3), `_WARM_VERIFY_MEMO` (06/F5), both `id()` memos (06/F4), evidence-admission dedup key missing `identity` (05 §2), frontier scope missing epoch (04/M5). One helper; every cache routes through it. This is the same defect fixed in 8+ places this week — fix the convention, not the instance.
10. **One validator per boundary**: single sidecar validator (05/C2); single segment-reseed loop shared by `rollout_depth`/`_holdout_witness` (05/C5); `dynamics_assumption` resolved once and threaded (01/F3); one source for the duplicated policy prose (01).
11. Weakness-receipt emission dedup on (task_id, evidence epoch) + a convergence counter; classes without a `recommended_capability_id` route to an explicit human queue instead of infinite re-emission (02).

### P2 — the deletion pass (the actual iatrogenics cure)
12. Delete or wire ~6,800 LOC now provably inert: k-line routing-prior lane, `adapter_width` (or wire it — see P3), `arc3_run_observability`, `machinery_adoption`, `_emit_rider`, trace_auditor shrunk to acted-on checks with an actuator (an active `halt_required` should fence closure claims), `fiber_lift`, `scene_grammar`, `batch_transition`, `coverage_planner` (or fix 04/H3 first if keeping), `lean_equivalence`→CI or delete, dead `_AUTHORITY_DERIVED_ACTIONS` entries, `batch_gate._subprocess_gate`. Stop editing `effect_compiler.py` while it has no caller — decide: register it as a producer or delete it.
13. Move the two mega-functions (~1,300 LOC) out of `leaf_workbench.py` into a `worldmodel/residual_event_analysis.py` (01).
14. Convert the review probes that verified bugs empirically (05/C1,C2,C3; 04/H1) into regression tests — the authority path deserves more than 7 test files.

### P3 — the generality program (what "done" looks like)
15. **Turn on the grammar loop**: `budget>=1`, drop the `governed_carrier` short-circuit at its single call site; one end-to-end proposal→adoption→first-fire validates 2,000+ LOC of card machinery currently converting at 0% (02).
16. **Coordinate-action interface** (`closure_audit` UNCLOSED item) — the admitted blocker for tu93 and any non-arrow-key game (06).
17. **Adapter-width ladder, one field at a time**: `variables` first (causal_compiler candidate exists; needs a typed validator + an active consumer), then `success_signal`, then `reset_semantics` (reset-invariance tests are still untested). Each graduation is a receipt; width 7/7 → 6/7 is the first real generality claim.
18. **One learning-transaction digest** joining task/epoch/abstraction/carrier/intervention/consequence — the docs' own stated migration; make p0_metrics consumable by a registered allocator (currently `observer_only`, 0 consumers).
19. **Separate harness-debug from science runs** (the CEGIS membrane already defines HARNESS_DEBUG): no apparatus edits inside a live science campaign — 05/C7 (disk-vs-memory evaluator hash) is a symptom of editing the evaluator mid-run being normal practice.

## 5. What remains to achieve the general-purpose skill-acquisition engine

Measured against the system's own definition (adapter-width deletion + earned advice string + substrate-portable contracts):

1. **Width: 7/7 → nothing graduated.** Every abduction outsourced to humans is still outsourced: variables, actions, success signal, reset semantics, time structure, observability, verification oracle. One candidate organ exists (causal_compiler for `variables`) and lacks its validator and consumer. This is the honest scoreboard, and it says the engine is currently a *governed program-synthesis harness for one game family*, not a general skill acquirer.
2. **The advice string doesn't grow.** Operator vocabulary = 2; catalog velocity/reuse not computable (no denominators); the wake-sleep grammar-growth loop — the external panel's #1 condition from 2026-07-02 — is built, gated, and off. Until proposals convert, the P/poly-advice thesis is untested by the system itself.
3. **Transfer is one qualified data point.** tu93 completed a level while its transition model was still wrong (`terminal_verifier_model_mismatch: true`) — a win by navigation, not by understanding. The declared architectural test (same operator identities and induction path, no source-game coordinates) is blocked on the coordinate-action interface.
4. **The learning transaction has no single identity.** Stages are individually receipted but no shared digest joins them; by the repo's own criterion, organ presence and local receipts must not be reported as autonomous learning — and currently that is exactly what a status report would have to lean on.
5. **Allocation never became causal.** The K-line/matched-ablation lane is unreachable code; the router works but routes on a buggy latch. "Ways of working" transfer — the second half of the memory story — has never fired.
6. **Two substrates in the code, one in reality.** `factored_search`/`observation_chart`/`task_discharge` are mechanically neutral but every ontology choice in them is ls20-shaped, and each has exactly one lowering. Substrate-generality claims stay speculative until a genuinely different adapter (text, graph, or the proof substrate) lowers end-to-end.

The gap is not more architecture — the contracts are written, mostly well. The gap is: **turn on what is built (15, 16), delete what is dead (12), enforce the two conventions the constitution already states (9, 10), and then attack the seven givens one receipt at a time (17)**. On current evidence the fastest path to the general engine runs through less harness, not more.
