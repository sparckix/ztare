# Review — gates/evaluation authority core

Cluster: `gates.py`, `batch_gate.py`, `evidence_consolidation.py`, `harness.py`, `evaluation_protocol.py`, `episode_log.py` (+655 uncommitted), `p0_metrics.py`.
Scope: 3,188 LOC across the 7 targets (read fully) + ~2,000 supporting (`transition_identity.py`, `carrier_loader.py`, `patch_base_carrier.py`, `gate_harness.py`, `observation_chart.py`, call sites) ≈ 5,200 total.
Verification: ran the real gate harness end-to-end (32s, score 0.6667, champion currently failing visible replay at t=13); evidence_consolidation self-check (pass); p0_metrics on live workspace; 3 targeted probes.

## 1. Correctness findings

**C1 — `within_epoch_view` infers a stale epoch and silently drops 93% of evidence. VERIFIED EMPIRICALLY.**
`episode_log.py:388-425`. No-arg inference takes the *last* non-boundary identity row's `source_epoch` as "active". On the live bank, epochs interleave (last row index per epoch: {2: 15269, 4: 15360, 6: 15375, 8: 14801}) so the inferred active chart is epoch **6** while max progress is epoch **8**; the view collapses 15,376 rows → **109**, dropping all 14,246 identity-less legacy rows (unknown-epoch treated as other-epoch). Consumers: `arc3_play_loop.py:1273` (`_role_state` → role induction → planning abstraction) and `:1360` (goal scoping). Planner induces roles/goals from a tiny stale-epoch slice. Related: `arc3_play_loop.py:177` passes an adapter epoch explicitly — if rows carry no identity (legacy adapter) the explicit branch returns an EMPTY log (probe: 2 rows → 0), zeroing `evidence_states`.

**C2 — Two sidecar validators with different strictness. VERIFIED BY PROBE.**
`episode_log.py:594-673` (`read_jsonl_indices`) re-implements sidecar validation weaker than `_apply_identity_sidecar` (:118-280): duplicate `row_index` bindings silently last-wins (:642-646) where the full reader raises (:153-154); non-dict bindings skipped instead of raising; raw ValueError possible. Probe: a sidecar with duplicated bindings — full read rejects, indexed read **accepts and applies the identity**. Weak-path consumers: `leaf_workbench.py:4035,4184,4223,4495,4816`, `compiled_fiber_planning.py:213`. A sidecar the authority path rejects still feeds identity into repair/spot-check flows.

**C3 — Cap-trip receipt erased by cache housekeeping; gate reports clean. VERIFIED BY PROBE.**
`gates.py:455-468`. `_ENV_FRAME_CAP_TRIPS[key]` written at :460, wiped by the >64 `clear()` at :464-466 when the clear fires on the same call, key re-cached at :468 without the trip. Probe: filled cache to 65, ran a cap-tripping log → detail "replay consistent over 10 transitions", trip record None. Verdict unaffected, but silently violates the file's own "exclusions are NEVER silent" contract — third patch on this exact seam (F3a 2026-07-09, F3b 2026-07-09, this rewrite).

**C4 — Asymmetric trust: bare boundary labels excluded uncapped, bare dynamics labels distrusted.**
`transition_identity.py:162-181` + `gates.py:376-378,455,467`. `authoritative_dynamics` requires `evidence_refs`; `authoritative_boundary` requires none; `explicit_boundary` bypasses `ENV_FRAME_CAP` entirely (cap applies to `inferred` only). Live: episode_001 carries **11 reset_boundary rows with empty evidence_refs** — excluded from replay scoring with no evidence and no cap. Boundary exclusion is the candidate-favorable direction; the identical "unattested collector label" argument was applied to dynamics but not boundaries.

**C5 — `rollout_depth` doesn't reseed at identity-attested boundaries (latent).**
`gates.py:622-650`. Segment reseed triggers only on `tr.t <= prev_t`. An adapter-attested boundary row with advancing t in a holdout is neither reseeded nor excluded → depth caps at that row for every candidate including the true law — the same unpassable-by-construction class fixed for t-based segments (docstring :632-640). Latent today (episode_002 has no identity rows/sidecar); live the moment holdouts are collected by the new identity-writing adapter.

**C6 — Bitmap cache persists poisoned results under a valid key; key under-specifies identity.**
`evidence_consolidation.py:181-185, 187-244`. Cache-hit returns persisted JSON without checking `load_error`; a transient load failure writes an all-rows-wrong bitmap returned forever for that (carrier, episode, evaluator) key. Key omits rubric `dynamics_assumption`, which changes lowering semantics (`patch_base_carrier.py:135-147`, `carrier_loader.py:307-314`) without changing any digest. (Positive: PATCH_BASE chains are sha-pinned in carrier source, so base bytes ARE transitively covered by `carrier_sha`.)

**C7 — `evaluator_implementation_identity` hashes disk, stamps in-memory judgments.**
`gates.py:52-73`. Digest recomputed from source files per call. Editing any of the 14 refs mid-run (this project's normal operating mode) makes subsequent bitmaps carry the NEW evaluator sha while computed by OLD loaded code — the inversion of the staleness guarantee the key exists for.

**C8 — `_count_interventions` narrowed to fields no producer writes.**
`p0_metrics.py:394-400`. Requires `record_type == "conductor_intervention"` or `operator_intervention is True`; no producer exists (only `search_control_repair.py`'s differently-shaped `operator_interventions`). Live returns 0; "no interventions" and "counter disconnected" indistinguishable. Observer-only, but a metric silently fixed to a constant.

**C9 — Corrupt MANIFEST silently flips episode roles (holdout-leak vector).**
`evidence_consolidation.py:92-116`. Unreadable MANIFEST.json → `except Exception: pass` → rubric → sorted-glob convention (first file visible, second holdout). A truncated MANIFEST write silently reassigns roles by filename sort → candidates fit on the sealed holdout. `raw/episodes/` also now contains `fleet_*.jsonl` (currently sorting after episode_002; any future earlier-sorting file shifts roles silently).

## 2. Symptom-patch vs root-cause assessment

The 4 days converge on **one underlying defect: cached/derived judgments keyed on incomplete identity**; most fixes hit real chokepoints:
- env-frame cache: id-tuple → `content_hash()` (root-cause; kills GC-aliasing + sampled-cell collisions at the one key site)
- carrier loading: 3 divergent copies (batch_gate, evidence_consolidation, gate_harness) collapsed into `carrier_loader.py` (genuine consolidation, best change in the set)
- bitmap key: + `evaluator_sha256` (right idea; C6/C7 residue)
- transfer receipts: + carrier/evidence binding in p0_metrics (fail-closed, verified live: `historical_or_unbound`)

But the same defect class survives in ≥4 places: C6 (load-success + rubric not in key), C7 (disk-vs-memory identity), C2 (second privately-reconstructed sidecar validator — precisely what the `evaluator_implementation_identity` docstring forbids), and `arc3_play_loop.py:2206-2218` where the evidence-admission dedup key (`context_hash`+`observation_hash`) excludes `identity` — a re-observation carrying a NEW authoritative identity is dropped as duplicate, so identity upgrades to already-banked rows can never enter. **Verdict: ~70% root-cause, 30% same defect re-patched per-consumer.**

## 3. Silent-failure paths

- `evidence_consolidation.py:102,115` — MANIFEST/rubric parse failure silently flips role authority (C9).
- `batch_gate.py:119-158` — `_subprocess_gate` now **dead** (no caller); docstring :14-23,47 still promises subprocess fallback for un-isolatable EXTENSIONS_SRC conflicts — safety path gone, conflicts run in-process silently. `harness_path` (:194) unused. Docstring :8-12 claims an equivalence "proof in the module's main block" that isn't there (pre-existing).
- `evaluation_protocol.py:107-148` — `record_attempt` never checks the lineage budget; only registrations are budget-gated → anti-adaptive-testing budget is advisory (pre-existing).
- `evaluation_protocol.py:186-193` — `_unresolved_probe_targets` swallows `load_targets` exceptions → broken module silently shrinks `required_interventions` → `validate_slice` passes slices avoiding disputed contexts (pre-existing).
- `p0_metrics.py:45-46,54` — broad catches map any binding-code bug to "historical_or_unbound"/empty; fail-closed but masks defects.
- `gates.py:120-127` (`as_predictor`) — TypeError inside a 3-arg candidate retried as 2-arg then fail-closed; verdict-safe but misattributes the candidate's own bug (pre-existing).

## 4. Complexity / iatrogenics

- `episode_log.py:443-467` — `write_jsonl` validates the sidecar twice (full `_apply_identity_sidecar` pre-write, full `rebind_identity_sidecar` post-write incl. transport-certificate recertification). One suffices.
- `gates.py:275-302` — `_holdout_witness` duplicates `rollout_depth`'s segment-reseed loop; any boundary-rule change (C5) must be applied twice in lockstep.
- `gates.py:590-619` — `replay_gate_and_diagnostics` puts full-bank diagnostics (mismatch signatures over 15k rows) on the binary gate path; observed 32s/candidate where the old gate early-exited at first mismatch. Deliberate trade; now the authority path's hot cost.
- `episode_log.py:513-521` — `(size, mtime_ns)` stat check redundant with the sha check and can false-refuse a legal append (same bytes, touched mtime).
- Dead: `batch_gate._subprocess_gate`.

## Overall assessment of the authority path

**Sound on verdicts.** The deterministic chain (gate_harness → carrier_loader → gates replay/rollout over EpisodeLog with fail-closed sidecar binding) is exact-match, fail-closed at every prediction, content-hash keyed; new sidecar/append machinery fails closed on every tampering scenario constructed. No holdout leakage into visible scoring found (the one leak vector is C9's role-flip default). Dangerous residue is not in the gates but in (a) trust rules for adapter-authored identity (C4 uncapped bare-boundary exclusion), (b) secondary readers privately reconstructing identity/validation (C2), (c) cache keys still missing part of their input identity (C6, C7). The one empirically misbehaving new function is `within_epoch_view` (C1) — planning-path, not gate authority, but live and wrong today.

## Top 3 structural remediations

1. **One sidecar validator.** `read_jsonl_indices` calls the same `_apply_identity_sidecar` core (validate once, project wanted rows); delete the private re-implementation. Kills C2 and future divergence.
2. **Complete the cache identity at the bitmap chokepoint.** On cache-hit refuse payloads with `load_error`; add rubric `dynamics_assumption` digest to the key; compute `evaluator_implementation_identity` once at module import so judgments are stamped with the code that actually ran. Fixes C6+C7 in one function.
3. **One lifecycle-boundary door.** Epoch selection from adapter/boundary receipts (max authoritative boundary `target_epoch`, or a required explicit argument), never last-row order; define the mixed-bank policy for identity-less rows explicitly; `rollout_depth`/`_holdout_witness` consult the same boundary definition (fixes C1, C5, pre-empts the identity-holdout failure). Quick win: `resolve_episode_paths` raises on unreadable MANIFEST (C9, one line).
