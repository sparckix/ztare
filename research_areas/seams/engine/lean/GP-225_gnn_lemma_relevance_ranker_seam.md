# GP-225 — GNN Lemma-Relevance Ranker (lineage seam)

> **Seam metadata** · `seam_id:` GP-225 · `track:` engine · `status:` open - opened 2026-05-06 PM (retroactive lineage capture) · `last_updated:` 2026-05-12


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

open — opened 2026-05-06 PM (retroactive lineage capture)
**Living seam** — versions log appended on each new training run.

## ID

GP-225

## Eigenquestion

What's the role of a learned lemma-relevance ranker in ZTARE — and at what
production hit@k does it earn a slot in `typed_endpoint_pack` as an
enrichment provider, vs. stay as research-shelf?

## Why this seam exists

Multiple ranker versions have been built across this project. Without a
single seam logging the lineage, the next person (or session) re-derives
the same numbers from scratch. This seam is that single source of truth.
**Append a row when you ship a new version. Don't re-litigate v1 in v6's
discussion.**

## Role-fit (the framing that survives across all versions)

The ranker is **prompt-enrichment**, not **closure-novel-step generator**.
That is: when typed_endpoint_pack invokes on a CANNOT-PATCH endpoint, the
ranker surfaces top-k mathlib lemmas the LLM should consider. It does NOT
replace the LLM, does NOT autonomously pick a lemma, does NOT generate
proof structure.

Bar for shipping into typed_endpoint_pack as an enrichment provider:
**production hit@10 ≥ 0.20 on Codex-shipped patches.** Below that, it's
research-shelf.

The role-fit was decided after the v2 production-hit@10 falsifier
(`scripts/public/models/gnn_lemma_relevance/production_hit10_falsifier.py`, 2026-05-06) exposed that
spine-eval test hit@10 (0.271) was 26x higher than NS-Track-B production
hit@10 (~0.000). The ranker is good at the eval distribution it trained
on; the production distribution is shifted. Architecture work alone
won't close the gap; data augmentation (v5/v6) will.

## Versions log

| version | date | encoder | data | test hit@10 | NS production hit@10 | verdict |
|---|---|---|---|---|---|---|
| v1 | 2026-05-06 AM | all-MiniLM-L6-v2 (frozen) | spine-only ~1.6K | 0.379 (overfit) | n/a | Overfit baseline. Val peaked at 0.50 then dropped. Test was inflated by easy in-distribution lookups. |
| v2 | 2026-05-06 AM | all-MiniLM-L6-v2 (frozen) | mathlib_pairs ~57K + spine | **0.271** | **~0.000** (cleaned regex) | Honest re-baseline. Distribution shift to NS production exposed by post-hoc falsifier. Architecture was fine; data was wrong. |
| v3 | (skipped) | mpnet-base (frozen) + hard-neg | mathlib_pairs ~57K | — | — | Predicted lift from v2 + interpolation; superseded by v4. Never trained. |
| v4 | 2026-05-06 PM | mpnet-base (last 4 layers fine-tuned) + hard-neg + 4-layer projection + cosine LR | mathlib_pairs ~57K | **collapsed** | n/a | **Empirical: training collapsed (val flat, train loss dropped — feature collapse). Prediction (0.35-0.45) FALSIFIED.** Encoder fine-tuning + aggressive hard-neg mining drove the encoder to a degenerate point. Killed; pivoted to v5. |
| v5 | 2026-05-06 PM | frozen mpnet-base + same loss as v4 | mathlib_pairs ~57K + ztare_pairs ~880 | **collapsed** | n/a | **Empirical: ALSO collapsed.** Freezing the encoder didn't fix it — the BCE-loss + hard-neg combination was the root cause, not encoder choice. v4 hypothesis (encoder fine-tune was the problem) FALSIFIED. Pivoted to v6 (architectural rewrite). |
| ~~v6 (vocab expansion plan)~~ | **DROPPED 2026-05-06 PM** | — | (was: vocab expansion from ztare_proofs/*.lean) | n/a | n/a | **DROPPED before any compute.** Operator review: the ZTARE Lean spine has stubs / scaffolding interleaved with verified proofs. Vocab expansion would import junk lemma names. **Prerequisite for any future spine-aware retrieval:** stub-vs-verified discriminator pass on `ztare_proofs/*.lean` first. Separate seam if/when pursued. **Note:** the v6 that actually ran is the architectural-fix variant below, not this dropped vocab plan. Naming collision. |
| v6 (arch fix that actually ran) | 2026-05-06 17:18 | mpnet-base (frozen) + InfoNCE loss + 8 hard + 16 random negs + 3-epoch random-only warmup + cosine LR | mathlib_pairs ~57K | **0.275** | n/a | **Empirical: didn't collapse, but didn't beat v1 either.** Training trace shows mining-induced val crashes at every hard-neg re-mine (epochs 3, 8, 13). "Best" epoch (8, mrr=0.161) is a brief recovery between two collapses. Architecturally validated InfoNCE > BCE for stability, but the schedule is too aggressive for 756 train pairs. **v1 remains the best ranker on disk.** |
| v2.1 local rerank | 2026-05-11 | v1 checkpoint + deterministic mathlib graph/context late fusion | recent 30 Lean files, 200 extracted targets, 59 in-vocab production pairs | n/a | base hit@10 **0.0169**, v2.1 hit@10 **0.0169** | **No GPU promotion.** Late-fusion graph features improved hit@20 `0.0339→0.0508` and MRR `0.0081→0.0085`, but not hit@10. This validates the cache/eval path and weakly supports graph context, but says the next lever is production-pair coverage/feature targeting, not remote training. Artifact: `analytics/public/leanmill/results/v21_graph_augmented_production_hit_at_k.json`. |
| v2.1 trusted local context | 2026-05-11 | v1 checkpoint + trusted ZTARE declaration hygiene + prior same-file candidate injection + local-accessibility rerank | recent 30 Lean files, 200 extracted targets, 115 in-vocab production pairs | n/a | base hit@10 **0.0087**, v2.1 hit@10 **0.2870** | **Local prompt-enrichment candidate, still no GPU promotion.** The gain comes from candidate-generation/accessibility, not learned GNN architecture: same-file trusted declarations before the target are added to the pool, then reranked with `--alpha-local 6.0`. hit@20 improved `0.0174→0.3304`, hit@50 `0.0435→0.3826`, MRR `0.0042→0.1897`. Next gate is general-purpose verified/non-NS Lean eval and regression against mathlib/spine before any training. Artifact: `analytics/public/leanmill/results/v21_trusted_local_context_alpha6_production_hit_at_k.json`. |
| v2.1 non-NS guard | 2026-05-11 | same trusted local-context evaluator, excluding `ns_*.lean` | 80 non-NS Lean files scanned, 60 extracted targets, 29 in-vocab production pairs | n/a | base hit@10 **0.0000**, v2.1 hit@10 **0.0000** | **General-purpose gate not yet passed.** Candidate-pool recall was only `0.2759`; hit@50 improved `0.0000→0.0345`, MRR `0.0009→0.0033`, but top-10 stayed zero. The strong NS/local result cannot be promoted as a general math-work ranker yet. Artifact: `analytics/public/leanmill/results/v21_trusted_local_context_alpha6_non_ns_eval.json`. |
| v3.1 candidate generator | 2026-05-11 | v1 dense + BM25-lite token + trusted same-file prior + mathlib/local-co-use graph candidate union, ranked by cheap feature weights | recent 30 Lean files, 300 extracted targets, 192 in-vocab production pairs | n/a | dense hit@10 **0.0052**, v3.1 hit@10 **0.2292** | **Best current workstation path.** NS candidate source recall: dense `0.1198`, token `0.4635`, same-file `0.3229`, graph/co-use `0.1198`, union `0.5573`; v3.1 hit@20 `0.2656`, hit@50 `0.2969`, MRR `0.1292`. Non-NS guard now also passes directionally after local co-use graph repair: 81 in-vocab pairs, dense hit@10 `0.0370`, v3.1 hit@10 `0.1975`, union recall `0.8272`, graph/co-use recall `0.4568`. Still no GPU: first integrate/report as CPU prompt enrichment and add ablations. Artifacts: `analytics/public/leanmill/results/v31_candidate_generator_ns_recent_report.json`, `analytics/public/leanmill/results/v31_candidate_generator_non_ns_report.json`. |
| v4.1 CPU learned reranker | 2026-05-11 | transparent logistic reranker over v3.1 candidate features, deterministic target-hash train/test split | NS: 254 in-vocab records, 184 train / 70 test. Non-NS: 107 in-vocab records, 80 train / 27 test. | n/a | NS v31 test hit@10 **0.3000**, v41 **0.3571**; non-NS v31 **0.2963**, v41 **0.5185** | **Pre-GPU learned reranker passes local signal.** NS test hit@50 improved `0.3429→0.5857`, MRR `0.1897→0.2472`. Non-NS test hit@20 improved `0.3333→0.7037`, MRR `0.2051→0.2888`. This justifies v4.1 as CPU prompt enrichment and makes v5.1 data-contract preparation reasonable. Artifacts: `analytics/public/leanmill/results/v41_learned_reranker_ns_recent_report.json`, `analytics/public/leanmill/results/v41_learned_reranker_non_ns_report.json`. |
| v5.1 heterogeneous graph contract | 2026-05-11 | typed node/edge schema plus local pre-GPU gates over v3.1/v4.1 reports | NS and non-NS v5.1 contract checks | n/a | both contracts **pass_local_v51_data_contract** | **GPU eligible by data contract, still requires operator approval and pre-registration.** Node types: target, premise, file, route, source_kind. Edge types: target/file, premise/file, dense/token/same-file/graph candidate edges, positive-used edge, route/source-kind edges. NS metrics: union recall `0.5573`, graph/co-use recall `0.1198`, v41 lift over v31 `+0.0571`. Non-NS metrics: union recall `0.8272`, graph/co-use recall `0.4568`, v41 lift `+0.2222`. Artifacts: `analytics/public/leanmill/results/v51_heterogeneous_graph_contract_ns.json`, `analytics/public/leanmill/results/v51_heterogeneous_graph_contract_non_ns.json`. |
| v5.2 residual advisory + RD tick precheck | 2026-05-11 | v4.1-anchored residual graph reranker plus frozen tick-start consumer | remote CPU sanity: 170 targets / 99,753 candidate edges; local NS advisory packet: 24 emitted targets | n/a | remote CPU sanity v4.1 hit@10 **0.3611**, v5.2 **0.5833**; local packet validation hit@10 **0.5357** | **Promoted to optional RD tick visibility, not to hard gating.** The residual model preserves v4.1 candidate-generation gains while adding graph signal. The tick precheck reads frozen artifacts only, emits endpoint/guard/tautology warnings, and does not retrain or block dispatch. Artifacts: `scripts/public/control/rd_tick_gnn_precheck.py`, `analytics/public/queries/rd/rd_tick_gnn_precheck.json`, `analytics/public/leanmill/results/v52_ns_advisory_packet.json`, `analytics/public/leanmill/results/v52_residual_hetero_gnn_remote_cpu_sanity.json`. |
| v5.3 guarded advisory filter | 2026-05-11 | danger-aware work-queue filter over the frozen v5.2 NS advisory packet + same-tree obligation graph | 24 emitted NS targets; top-5 queue profile | n/a | clean actionability **0.1917→0.5000**; danger fraction **0.3250→0.0500**; hit@10 preserved **0.6250→0.6250** | **Current safe consumption layer.** v5.3 does not retrain. It demotes endpoint/guard/opaque candidates and promotes clean constructors/adapters/graph-local primitives. This is the right tick-facing interface because raw top-k contains useful context and dangerous near-endpoint names in the same list. Artifacts: `scripts/public/models/gnn_lemma_relevance/v53_guarded_advisory_filter.py`, `analytics/public/leanmill/results/v53_guarded_advisory_filter.json`, `analytics/public/leanmill/results/v53_guarded_advisory_filter.md`. |
| v5.4 typed-symmetry audit | 2026-05-11 | no-GPU role audit over v5.3 queue; tests whether equivariant architecture is justified | 24 emitted NS targets; top-5 queue roles | n/a | **warn**: missing clean roles `bounded_fanout`, `pressure_lock`; wrong-equivariance risks `duhamel_budget_visible_without_clean_pressure_lock`, `fresh_packet_visible_without_clean_bounded_fanout`; collapse risks `14` | **Architecture gate, not model training.** The audit says a generic equivariant GNN is premature: the queue has Duhamel/fresh-packet signal but lacks the two typed roles that prevent NS same-tree laundering. v6 should be a residual typed-symmetry scorer only after v5.5 perturbation canaries quantify the gap. Artifacts: `scripts/public/models/gnn_lemma_relevance/v54_typed_symmetry_audit.py`, `analytics/public/leanmill/results/v54_typed_symmetry_audit.json`, `analytics/public/leanmill/results/v54_typed_symmetry_audit.md`. |

### v4/v5/v6 GPU spend — postmortem (2026-05-06 PM)

Three GPU runs over the afternoon. None beat v1. Honest debrief
inline below.

**The critical failure:** every comparison line in v4/v5/v6 logs
reads "comparison vs v2 (BCE baseline)". v2 was treated as the floor
going forward — but v2 was ALREADY KNOWN to regress vs v1 (v2's own
log says "comparison vs v1: hit@10 0.379→0.271"). Every "improvement"
in the v4 → v5 → v6 chain was measured against the wrong baseline.
v6's reported "comparison vs v2: 0.271→0.275 = improvement" reads
as success and is literally true; against v1 (0.379→0.275) it's a
~28% regression.

**Secondary failures:**

  - **Hard-neg mining is destabilizing on 756 train pairs.** v6 train
    trace: val crashes at every re-mine (epochs 3 and 13), brief
    recovery at epoch 8 — that's the "best" point. Not a stable
    ranker.
  - **Encoder fine-tuning + BCE + hard-neg = feature collapse.** v4
    confirmed. v5 confirmed (freezing encoder didn't fix it; loss
    was the root cause).
  - **Small-data ranking is a regularization game, not architecture
    game.** v1's train loss = 0.028 = severe overfit; the val signal
    reflects what generalizes from sentence-transformer embeddings,
    not what the head learned. Architecture changes mostly modulate
    overfitting regime, not ranking quality.

**Hard rules going forward:**

  1. Anchor every architecture-search comparison on the BEST known
     prior result, not the most recent prior result. Pre-register a
     kill-criterion against v_BEST before any v_(N+1) launches.
  2. Treat collapsed runs (v4/v5) as architecture-veto signals, not
     as motivation for the next architecture. v4 collapsed → that's
     information about data scale, not a prompt to try v5/v6.
  3. With 756 train pairs, the next experiment is data augmentation /
     synthetic pair generation, not a new loss function.
  4. Hard-neg mining schedule must be tied to validation stability,
     not a hardcoded N-epoch cadence. If val crashes after each
     mine, mine less often or smaller batch.
  5. A v2.1+ GPU run requires a local production-style improvement over
     v1 first. Deterministic reranking or cached evaluation may run
     locally; remote training is blocked while hit@10 is flat.

**What stays usable from this spend:**

  - v1 remains the production ranker (`ranker_checkpoint.pt`,
    hit@10=0.379, MRR=0.154).
  - Three architectural complications publicly fail to beat the
    simplest setup. That's a genuine negative result — future-me
    won't retry encoder fine-tuning or aggressive hard-neg mining
    on this dataset size without changing the data first.
  - All checkpoints (v1/v2/v6) + train/val/test data + vocab files
    pulled local from the GPU host. Remote 129.146.21.210 safe to
    terminate.

### Versions log appendix — to-be-promised numbers

These were stated as predictions at decision time. Filling in when the
training run completes is part of the seam's discipline (ship the
prediction; ship the empirical; both stay).

- **v4 prediction (made 2026-05-06 PM):** test hit@10 0.35-0.45,
  test MRR 0.18-0.25. Production NS hit@10 stays low.
- **v5 prediction (made 2026-05-06 PM):** test hit@10 ~ v4 ± 0.02
  (no significant change on mathlib distribution). NS production
  hit@10 from ~0.000 → 0.05-0.15.
- **v6 prediction (will be revised when scoped):** NS production
  hit@10 0.20-0.35 (clears the typed_endpoint_pack enrichment bar).
  Mathlib test hit@10 unchanged from v4/v5 (vocab expansion
  doesn't degrade mathlib lookup).

## Cost discipline

The 2026-05-06 v4-kill incident codified the rule (`AGENTS.md §4z1`):
**don't kill long-running paid compute on a single noisy diagnostic.**
For this ranker family specifically:

- v2 production falsifier was contaminated (regex captured local
  hypotheses as lemmas). Cleaned in same session.
- v4 has GENERAL-PURPOSE value beyond NS Track B (any future
  substrate without a mature spine starts on mathlib lookup). Killing
  v4 because of NS-specific underperformance fails the inversion-reflex
  test.
- v5/v6 escalate ONLY if the prior version's empirical NS performance
  warrants it. Not on hypothesis.

## Falsifier provenance

- **`scripts/public/models/gnn_lemma_relevance/production_hit10_falsifier.py`** — extracts (target,
  used_lemmas) pairs from recent ZTARE Lean files, scores against the
  ranker, computes production hit@k, prints SHIP_V2 / PURSUE_V4 /
  DATA_SHIFT_DOMINATES verdict
- **`scripts/public/models/mine_ztare_pairs_for_training.py`** — same extractor,
  but persists pairs as training data (ztare_pairs.jsonl) instead of
  evaluating against a checkpoint
- **`apparatus_level2_review.py::claim_v3_gnn_predicts_real`** — the
  Level-2 meta-claim under which the falsifier discharges; closes
  out the ROI question for the ranker family

## Connection to other seams

- **GP-220** Reflexive Primitive ROI Telemetry — the ranker is one
  apparatus addition; GP-220's per-primitive scorecard would track
  its engagement_rate / hit_rate / action_rate / score_lift
- **GP-223** Endpoint-Type Compression Gate — alternative path to
  the same goal (cheaper LLM dollars). The ranker surfaces lemmas;
  GP-223 surfaces "this isn't even fresh work, it's a projection."
  Both are typed_endpoint_pack enrichment providers; ship both
- **GP-216 v5 vocabulary** — the ranker's role-fit verdict
  (prompt-enrichment, not closure-novel) maps to `core_06 External
  Framework Importation` (importing mathlib's existing structure
  without trying to derive it)
- **The 0/22 closure-utility verdict** (Codex panel, 2026-04-30) —
  Codex panel found 0/22 verified-patch closures attributable to
  LLM-augmentation tools. The ranker is in this class. Its value
  is COST REDUCTION (faster Codex turnaround, fewer wasted LLM
  rounds), not closure novelty

## Future work

- v15-v16 target-aware repair harness hard-negative lane (2026-05-11): the
  40-row route selector is useful but not GNN-ready. v15.2 showed BM25
  signature routing could match the full-interface router on repaired local
  obligations, blocking novelty/training. v15.4-v15.8 then generated
  policy-hard same-shape, false-premise, and plausible missing-obligation
  decoys; Lean witnesses rejected wrong candidates cleanly, but v15.9-v16.2
  showed cheap side-condition/body-token rules separated the apparent
  residuals. v16.4-v16.6 repeated this on NS-local structure-valued
  side-condition swaps and corrected a Prop-only audit blind spot: all-binder
  body tokens separated `4/4`. v16.7-v16.10 produced the strongest current
  decoys: same-token argument-slot swaps (`exhaustHorizon G L` vs `L G`,
  `1 ≤ p` vs `p ≤ 1`, kernel sign/order, Holder conjugate order). BM25 was
  tempted and Lean rejected all wrong actions, but deterministic fvar/constant
  occurrence paths separated `4/4`. Current verdict: keep the CPU
  target-aware repair harness and add slot-path/incidence features. v16.11 then
  showed raw slot paths are too brittle under reducible aliases, while v16.12
  showed whnf-normalized slot paths accept the alias and still separate `4/4`
  wrong slot swaps. v16.13 reran the same normalized feature on the older
  anchored Eq local-object/order challenge: aliases matched `5/5` and wrong
  Eq candidates separated `5/5`. GPU/GNN remains blocked until a nontrivial
  same-vocabulary residual family survives all-binder token, alpha-stable whnf
  slot-path, endpoint-orientation, and local-object incidence audits. v16.14
  removed printed fvar names from the slot paths and replaced them with
  telescope binder indices; the combined v16.9 + anchored-Eq suite still
  separated `9/9` wrong candidates and preserved `5/5` aliases. v16.15 found
  a real gap in that sidecar: binder-only paths missed conclusion-poison decoys
  `2/2`, while alpha-stable whnf conclusion-body paths separated `2/2` with
  zero wrong accepts. The CPU ladder therefore becomes all-binder tokens +
  alpha-stable whnf binder paths + alpha-stable whnf body paths + witness
  digests. v16.16 then found a normalization-depth gap: root-WHNF body paths
  falsely separated a reducible alias buried under `contractiveAbove`, but a
  binder-safe recursive-WHNF walker matched the alias and still separated the
  swapped wrong candidate. v16.17 then caught the cost risk in the naive
  version: unrestricted recursive WHNF hit Lean's deterministic heartbeat
  limit on large terms. Bounded wrapper normalization passed the regression
  across `12` rows: alias matches `6/6`, wrong separations `12/12`, survivors
  `0`. The CPU ladder therefore upgrades to all-binder tokens + alpha-stable
  binder paths + alpha-stable bounded recursive-WHNF conclusion/body paths +
  witness digests; GNN remains blocked until a natural family survives that
  ladder. v16.18 then audited same-candidate action ambiguity on the 40-row
  all-action packet: `86/200` non-gold actions compiled, `41` had distinct
  after-state digests, but `45` shared the gold digest across `18` rows. This
  blocks action-priority learning from single gold-action labels until row
  contracts encode acceptable alternate actions or stricter semantic deltas.
  v16.19 extracted that contract: `22/40` rows are strict-action rows and
  `18/40` are multi-action-equivalent. Use all rows for candidate-repair
  evaluation, but use accepted-action sets or the strict subset for
  action-priority evaluation. v16.20 rescored policies under this contract.
  BM25-target-kind remains the strongest cheap CPU baseline on all rows
  (success@10 `36/40`, success@25 `40/40`, mean failed `2.1`) and on
  strict-action rows (success@10 `20/22`, success@25 `22/22`, mean failed
  `2.18`). On NS-only rows, generic fixed gets success@10 `2/16` with mean
  failed `138.19`, while target-kind/BM25-target-kind get success@10 `14/16`,
  success@25 `16/16`, mean failed `3.0`, false-before rows `0`. This is a
  strong reason to use GP-225 as an NS CPU sidecar and a strong reason not to
  train yet. v16.21 extracted the concrete NS advisory report: both
  target-kind and BM25-target-kind policies solve `14/16` NS rows within 10
  probes and `16/16` within 25; the only budget-10 misses are the two
  cumulative-dissipation LSC rows, delayed behind L2/vector-L2 LSC candidates.
  v16.22 fixed those misses with kernel slot-path fallback for pretty-print
  signature collapse: both cumulative-LSC accepted repairs moved to probe `1`.
  The current NS packet is therefore effectively `16/16` at budget 10 with the
  deterministic stack. v16.23 integrates this as a policy: BM25-target-kind
  normally, slot-path fallback for signature-collapse rows. It improves all-row
  success@10 `36/40 -> 38/40`, strict-action success@10 `20/22 -> 22/22`, and
  NS success@10 `14/16 -> 16/16`, with false-before rows still `0`. The current
  authority is a hybrid CPU proof-repair sidecar; the next NS-side use is
  direct advisory queueing, not a learned model. v16.24 generalized the
  fallback trigger from two row IDs to every target pretty-printer collapse:
  all-row mean failed improved `1.35 -> 1.05`, strict-action mean
  `0.82 -> 0.27`, and NS-only mean `1.125 -> 0.375`, with false-before rows
  still `0`. v16.25 then removed the remaining budget-10 misses by fixing the
  scheduler: action-rank sweep over candidates avoids spending all six actions
  on an earlier Eq candidate before trying the next candidate's primary action.
  Broad slot-path plus action sweep reaches success@3/10 `40/40`, mean failed
  `0.175`, false-before rows `0`; NS-only reaches success@3 `16/16`, mean
  failed `0.0625`. v16.26 shows this is mostly a scheduler correction rather
  than representation novelty: BM25 and full-interface plus action sweep both
  reach success@10 `40/40`, mean failed `0.35`; domain/head plus action sweep
  also reaches success@10 `40/40`, mean failed `1.175`. v16.27 stress-tests
  the scheduler on v15.8 plausible missing-obligation decoys where BM25 ranks
  wrong >= gold on `8/8`; forced-front candidate-major gets FDCR@3 `0/8`,
  mean failed `6.0`, while action-rank sweep gets FDCR@3 `8/8`, mean failed
  `1.0`, wrong accepts `0`. Conclusion: the current GP-225 artifact is a
  strong deterministic probe-budget sidecar. GNN remains blocked until natural
  held-out rows show residual top-rank/mean-failed lift over BM25/full-interface
  action sweep and broad slot-path action sweep, with witness digests and
  false-before rows still clean. v16.28 applies this sidecar boundary to the
  live NS Phase 5CG frontier using the NS artifact graph as a soft candidate
  prior. Lean imports/query succeeds on `189` declarations, with `70` direct
  theorem/lemma candidates, `22` Prop helper schemas, and `11` wrapper-required
  Prop-valued live obligation schemas. The live frontier is therefore not a
  declaration-ranking target yet; counted progress requires generated
  theorem-hole proof states around those schemas, then action-rank probes with
  target-aware witness digests. Artifact:
  `analytics/public/leanmill/results/v1628_live_ns_phase5cg_sidecar_inventory.md`.
  v16.29 then generated applied-predicate wrapper goals for five live Phase 5CG
  schemas and probed `40` graph-near candidates over `240` candidate-action
  pairs. Raw compiled probes were `42`, but v16.30's strict filter rejects `39`
  convert/Iff overbreadth artifacts and one bad after-head. Two strict
  survivors remain: `pressureL2TransportDefectObligation` via
  `transport_defect_control_of_pressureL2TransportObligation`/`apply`, and
  `phase5cgBroadProofSearchTarget` via
  `local_route_promoted_of_phase5cgBroadProofSearchTarget`/`apply`. These are
  useful live obligation-consequence exposures, not solved NS atoms. Current
  next step is target-kind design separating “prove the source obligation” from
  “expose what the source obligation buys.” v16.32 confirms this distinction
  by compiling two temporary Lean wrapper snippets:
  `pressure_transport_defect_exposes_l2_control` and
  `phase5cg_broad_target_exposes_route_fork`. The three blocked live schemas
  are `EventRecurrencePricePDEObligationSatisfied`, `ns2028HindsightBundle`,
  and `uniformContinuationObligation`. GNN remains blocked.

- v5.3-v6 typed-symmetry lane (2026-05-11): raw v5.2/v5.3 GNN output was
  useful but mixed actionable adapters with endpoint and guard declarations.
  v5.3 added guarded consumption; v5.4 audited typed proof/PDE roles; v5.5
  added perturbation canaries; v5.6 used the same-tree obligation graph to
  repair missing `bounded_fanout` and `pressure_lock` roles; v6 emitted a
  design-only contract for a residual typed-symmetry scorer. Base v5.4 warned
  on missing `bounded_fanout` / `pressure_lock`; after v5.6 repair, the top-7
  queue passed typed-role audit with no missing roles, no wrong-equivariance
  warnings, and zero collapse risks. The semantic-alias canary still warned
  (`0.5357` on the repaired top-7 queue), so generic E(3)/CFD equivariant GNN
  training and plain from-scratch message passing remain blocked. The typed
  role contract now lives in `typed_role_maps.json`, with the NS map as the
  first stress-test instance and a generic theorem-workstation seed map as a
  canary for non-NS substrates. The generic seed currently warns on missing
  `error_or_obstruction_lock`, which preserves the generality brake. v5.7
  seeds a patch-attribution ledger from the tick precheck; it currently has
  `12` unobserved candidate rows and zero successful-edit attributions. The
  next admissible model is a residual over v4.1/v5.2 scores plus typed-role
  metadata, after non-NS role maps and positive patch-attribution labels exist.
  v6.1 now names the library-level design as a typed-obligation hypergraph:
  rank `(proof state, unmet obligation, candidate declaration/adapter,
  patch-attribution context)` instead of theorem names. It is ready as a
  contract only; training remains blocked because successful patch attribution
  is still `0`. v6.2 instantiates the contract as an NS typed-obligation work
  packet. It identifies the current local move as side-condition audit, not
  endpoint search: fresh-packet creation for nonflat, non-inherited nodes is
  the atomic NS probe; pressure-lock, fanout/no-reuse, and beta-payment are
  covered as obligations but still need field-level proof audits. v6.2 also
  records a priori and ex post usefulness criteria. The first tri-arm pilot
  now exists: graph alone got partial credit, GNN alone weak partial credit,
  and GNN+graph positive pilot credit for the compile-checked split of
  `FreshComparablePacketForNonflatNonInheritedNode` into partition,
  event-selection, and payment/carrier-lock side-condition objects. This is
  a single-edit signal, not training evidence.
  Artifacts:
  `scripts/public/models/gnn_lemma_relevance/typed_role_maps.json`,
  `scripts/public/models/gnn_lemma_relevance/typed_obligation_role_library.json`,
  `scripts/public/models/gnn_lemma_relevance/v53_guarded_advisory_filter.py`,
  `scripts/public/models/gnn_lemma_relevance/v54_typed_symmetry_audit.py`,
  `scripts/public/models/gnn_lemma_relevance/v55_typed_symmetry_perturbation_canary.py`,
  `scripts/public/models/gnn_lemma_relevance/v56_typed_role_repair_queue.py`,
  `scripts/public/models/gnn_lemma_relevance/v57_patch_attribution_seed.py`,
  `scripts/public/models/gnn_lemma_relevance/v60_typed_symmetry_residual_contract.py`,
  `scripts/public/models/gnn_lemma_relevance/v61_typed_obligation_hypergraph_contract.py`,
  `scripts/public/models/gnn_lemma_relevance/v62_typed_obligation_work_packet.py`,
  `analytics/public/leanmill/results/v54_on_v56_top7_typed_symmetry_audit.json`,
  `analytics/public/leanmill/results/v55_on_v56_top7_typed_symmetry_perturbation_canary.json`,
  `analytics/public/leanmill/results/v54_generic_seed_typed_symmetry_audit.json`,
  `analytics/public/leanmill/results/v57_patch_attribution_seed.json`,
  `analytics/public/leanmill/results/v60_typed_symmetry_residual_contract.json`,
  `analytics/public/leanmill/results/v61_typed_obligation_hypergraph_contract.json`,
  `analytics/public/leanmill/results/v62_ns_typed_obligation_work_packet.json`,
  `analytics/public/leanmill/results/v63_gnn_graph_combo_patch_attribution.json`,
  `analytics/public/leanmill/results/v64_tri_arm_usefulness_pilot.json`,
  `analytics/public/queries/rd/rd_tick_gnn_precheck.json`.
- v6.5-v6.9 endpoint-occluded/generalization hardening (2026-05-11):
  The NS tri-arm pilot now has three compile-checked combo attributions:
  fresh-packet side-condition split (`v63`), beta-payment adapter (`v65`),
  and structured pressure/fanout lock adapter (`v66`). The latest Lean check
  for `ZtareProofs/ns_L3_multiscale_YM_rescaled_increments.lean` exited `0`.
  v6.7 adds an endpoint-occluded attribution harness that scores repair
  bundles, not exact theorem names; it recovers all three NS attributions at
  top-3 (`hit_at_3=1.0`) while hiding endpoint/guard-shaped declarations.
  v6.8 adds a synthetic non-NS role-map canary across probability
  filtrations, harmonic-analysis tiles, category diagrams, and optimization
  projection; the first run caught a guard-classification miss for
  `Closure`/`Carleson` decoys, then passed after repair. v6.9 adds a real
  non-NS Lean attribution canary on
  `ZtareProofs/PR_B_NormSqExpand_SmokeTest.lean`; the file compiles and the
  canary classifies its explicit proof ingredients with `role_hit_rate=1.0`.
  Training remains blocked: semantic alias brittleness is unresolved, and
  non-NS evidence is currently existing-proof attribution rather than a
  generated patch attribution.
  Artifacts:
  `analytics/public/leanmill/results/v65_gnn_graph_combo_beta_payment_patch_attribution.json`,
  `analytics/public/leanmill/results/v66_gnn_graph_combo_structured_lock_patch_attribution.json`,
  `scripts/public/models/gnn_lemma_relevance/v67_endpoint_occluded_attribution_harness.py`,
  `analytics/public/leanmill/results/v67_endpoint_occluded_attribution_harness.json`,
  `scripts/public/models/gnn_lemma_relevance/v68_non_ns_role_map_canary.py`,
  `analytics/public/leanmill/results/v68_non_ns_role_map_canary.json`,
  `scripts/public/models/gnn_lemma_relevance/v69_non_ns_real_lean_attribution_canary.py`,
  `analytics/public/leanmill/results/v69_non_ns_real_lean_attribution_canary.json`.
- v7.0-v7.2 novelty/yield hardening (2026-05-11):
  The non-NS evidence moved from existing-proof attribution to one generated
  compile-checked patch attribution in
  `ZtareProofs/PR_B_NormSqExpand_SmokeTest.lean`: the patch added
  `forwardChar_mul_conj_self` and `trigPoly_packet_mul_conj_split`, then
  refactored `normSq_trigPoly_expand` through the new packet split. This is
  still only one generated non-NS patch, so it does not clear the training
  gate. The semantic-alias canary improved after typed-role-map repair
  (`0.8988` on the repaired queue in the RD precheck), but alias robustness is
  not yet proven on external corpora. v7.1 now detects staged external
  benchmark files, including MathlibGraph experiment summaries. v7.2 extracts
  the public MathlibGraph premise-retrieval baseline: network features already
  reach `R@10=0.5201` and all features `R@10=0.5247` on the published summary,
  with hard-negative `R@10=0.5104` / `0.5203`. This changes the novelty line:
  "graph premise retrieval helps Lean" is already occupied. This ranker's
  differentiator must be typed-obligation repair bundles, endpoint occlusion,
  wrong-carrier/budget-reuse guards, and compile-checked patch attribution.
  v7.3 turns that into a scientific-yield gate: GPU remains blocked, but a
  conditional novelty claim is allowed only in the narrow typed-repair-routing
  sense. v7.5/v7.6 stage LeanRank validation rows and show the important
  consumption rule: ungated typed residual hurts top precision, while
  `tail_after_top1` preserves graph-only `hit@1=0.3864` and improves `hit@10`
  from `0.8078` to `0.9190`. v7.7/v7.8 codify the synthesis: borrow
  accessibility-aware retrieval / negatives / dense-retriever discipline from
  LeanDojo/ReProver, but keep the first-principles differentiator as typed
  repair routing above retrieval. v7.9 seeds the endpoint-occluded repair
  benchmark with four compile-checked repair rows, one generated non-NS row.
  v8.0 adds a ReProver-style BM25 baseline on the same LeanRank sample. The
  best premise proxy is now graph top-1 plus BM25 tail (`hit@1=0.3864`,
  `hit@10=0.9476`, `MRR=0.5621` on 5k rows). Typed residual does not own
  generic premise ranking after BM25 is present; its job is repair-bundle
  routing, risk flags, and patch attribution. v8.1 adds the first
  repair-router protocol harness over the four compile-checked repair rows.
  It correctly separates a cheap retrieval-like baseline from a typed router
  on synthetic endpoint/guard/wrong-carrier/wrong-incidence/budget-reuse
  decoys (`typed_router_success_at_1=1.0`, `cheap_baseline_success_at_1=0.0`),
  but the artifact is explicitly `protocol_debug_complete_not_evidence`:
  candidate pools are hand-shaped protocol decoys, not real Lean declaration
  pools. GPU remains blocked; next no-GPU work is more generated non-NS
  repair rows and deriving repair candidate pools from actual declarations.
  v8.2-v8.4 then ran that next proxy over actual Lean declarations extracted
  from the repair files. Typed scoring alone remains bad top-1 but strong as a
  repair tail (`typed_hit_at_7=1.0` over five rows). A constrained set-cover
  queue improved mean first-gold rank but could skip useful local adapter
  families. The current best no-training policy is hybrid: preserve retrieval
  head precision, keep a short typed repair tail, then use typed set-cover and
  risk demotion. On the five-row actual-declaration proxy it preserves
  retrieval top-1 (`0.6`) and restores `hybrid_hit_at_7=1.0`. v8.5 records the
  literature positioning: LeanDojo/ReProver, graph-augmented Lean premise
  selection, older formula-graph embeddings, and LeanHammer already occupy
  generic premise selection / graph theorem proving. The viable 10x claim is
  a typed repair debugger above retrieval. v8.6 adds a fifth compile-checked
  repair attribution from the NS pressure/Duhamel same-carrier split; the
  sidecar audit classifies it as useful dependency factoring, not PDE content.
  v8.7 adds a second generated non-NS compile-checked patch attribution in
  `PR_B_OrthoSmokeTest.lean`, naming the diagonal character/conjugation
  simplification separately from the off-diagonal Bohr-mean cancellation
  theorem. The repair benchmark now has six rows and two generated non-NS
  rows. Hybrid actual-declaration routing remains the best proxy policy:
  `hybrid_top1_gold=0.6667`, `hybrid_hit_at_7=1.0`, mean first-gold rank
  `2.1667`. GPU remains blocked by the 8-row / 3 generated non-NS / semantic
  alias `>=0.90` gate. v8.8 adds an alias/name-anonymization stress test over
  the actual-declaration repair pools. It fails the desired robustness bar:
  hybrid `hit_at_7` drops from `1.0` under identity names to `0.6667` under
  semantic aliases and `0.6667` under name anonymization. This is useful
  negative evidence: before GPU, the router needs kernel/type/doc/dependency
  features rather than string-heavy role cues.
  Artifacts:
  `analytics/public/leanmill/results/v70_non_ns_generated_patch_attribution.json`,
  `scripts/public/models/gnn_lemma_relevance/v71_external_benchmark_intake.py`,
  `analytics/public/leanmill/results/v71_external_benchmark_intake.json`,
  `scripts/public/models/gnn_lemma_relevance/v72_mathlibgraph_external_baseline_summary.py`,
  `analytics/public/leanmill/results/v72_mathlibgraph_external_baseline_summary.json`,
  `scripts/public/models/gnn_lemma_relevance/v73_scientific_yield_gate.py`,
  `analytics/public/leanmill/results/v73_scientific_yield_gate.json`,
  `scripts/public/models/gnn_lemma_relevance/v75_leanrank_three_arm_proxy_eval.py`,
  `analytics/public/leanmill/results/v75_leanrank_three_arm_proxy_eval.json`,
  `scripts/public/models/gnn_lemma_relevance/v76_leanrank_gated_typed_residual_eval.py`,
  `analytics/public/leanmill/results/v76_leanrank_gated_typed_residual_eval.json`,
  `scripts/public/models/gnn_lemma_relevance/v77_external_system_lessons_audit.py`,
  `analytics/public/leanmill/results/v77_external_system_lessons_audit.json`,
  `scripts/public/models/gnn_lemma_relevance/v78_first_principles_router_spec.py`,
  `analytics/public/leanmill/results/v78_first_principles_router_spec.json`,
  `scripts/public/models/gnn_lemma_relevance/v79_endpoint_occluded_repair_benchmark_seed.py`,
  `analytics/public/leanmill/results/v79_endpoint_occluded_repair_benchmark_seed.json`,
  `scripts/public/models/gnn_lemma_relevance/v80_leanrank_bm25_gated_eval.py`,
  `analytics/public/leanmill/results/v80_leanrank_bm25_gated_eval.json`,
  `scripts/public/models/gnn_lemma_relevance/v81_repair_router_baseline_protocol.py`,
  `analytics/public/leanmill/results/v81_repair_router_baseline_protocol.json`,
  `scripts/public/models/gnn_lemma_relevance/v82_actual_declaration_repair_pool_eval.py`,
  `analytics/public/leanmill/results/v82_actual_declaration_repair_pool_eval.json`,
  `scripts/public/models/gnn_lemma_relevance/v83_constrained_repair_queue_eval.py`,
  `analytics/public/leanmill/results/v83_constrained_repair_queue_eval.json`,
  `scripts/public/models/gnn_lemma_relevance/v84_hybrid_repair_router_eval.py`,
  `analytics/public/leanmill/results/v84_hybrid_repair_router_eval.json`,
  `scripts/public/models/gnn_lemma_relevance/v85_literature_positioning_audit.py`,
  `analytics/public/leanmill/results/v85_literature_positioning_audit.json`,
  `analytics/public/leanmill/results/v86_gnn_graph_combo_pressure_duhamel_audit_patch_attribution.json`,
  `analytics/public/leanmill/results/v87_non_ns_ortho_generated_patch_attribution.json`,
  `scripts/public/models/gnn_lemma_relevance/v88_repair_router_alias_stress.py`,
  `analytics/public/leanmill/results/v88_repair_router_alias_stress.json`.
- v8.9-v9.1 label-blind repair-router reset (2026-05-11): a third
  generated non-NS row was added in `PR_B_CharMulConj_SmokeTest.lean`,
  factoring `forwardChar_sum_sub` and `star_exp_forwardChar_exponent`.
  An NS sidecar patch added `LerayHeatFreshFrequencyEventTentGeometry` and
  `LerayHeatFreshFrequencyCarrierCompatibility.ofEventTentGeometry`, making
  the pressure/Duhamel same-carrier obligation talk about explicit event
  tents before any prefix or Carleson endpoint. This brought the seed to
  eight compile-checked rows and three generated non-NS rows. Sagan's
  overfit audit caught a serious flaw: v8.2/v8.4 had used evaluator-only
  labels for scoring and pool construction. The scripts were reset to
  label-blind scoring/pools. Under the stricter setup, hybrid remains better
  than lexical at `hit@7` (`0.875` vs `0.75`) but does not beat lexical at
  top-1 (`0.5` vs `0.5`), and the structural occlusion canary fails:
  docless anonymized `hit@7=0.5`, signature-name-erased `0.625`, and
  role-token-alias signature `0.625`. Decision: GPU remains blocked. The
  v9.2 label-blind hard-decoy audit confirms the direct leak is closed and
  pools are nontrivial (`min_pool_size=50`): hybrid `hit@7=0.875`, lexical
  `hit@7=0.75`, hybrid MRR `0.65`, lexical MRR `0.6328`. Decision: still
  hold GPU. The next useful GNN work is kernel/type/dependency extraction,
  not training.
  Artifacts:
  `analytics/public/leanmill/results/v89_non_ns_charmulconj_generated_patch_attribution.json`,
  `analytics/public/leanmill/results/v91_ns_leray_heat_tent_geometry_patch_attribution.json`,
  `scripts/public/models/gnn_lemma_relevance/v90_repair_router_structural_occlusion_stress.py`,
  `analytics/public/leanmill/results/v90_repair_router_structural_occlusion_stress.json`,
  `scripts/public/models/gnn_lemma_relevance/v92_label_blind_hard_decoy_audit.py`,
  `analytics/public/leanmill/results/v92_label_blind_hard_decoy_audit.json`,
  `analytics/public/queries/rd/rd_tick_gnn_precheck.json`.
- v9.5-v10.2 Lean-kernel graph extraction + primitive-use reset (2026-05-11):
  the lane now has an actual Lean environment / Expr graph substrate, but the
  first ablations keep GPU blocked. v9.5 resolved all benchmark rows through
  Lean (`8/8`). v9.6 resolved all candidate declarations (`146/146`) and
  emitted a name-erased Expr graph with `10,448` AST nodes, `10,302` AST
  edges, and `2,755` constant occurrences. v9.7 showed that declaration-local
  AST shape is not enough (`hit@7=0.625`). v9.8 showed that symbolic constant
  neighborhoods, even local-redacted, are also not enough (`hit@7=0.625`).
  v9.9 built the heterogeneous typed-obligation Expr graph (`295` nodes,
  `24,089` edges). v10.0 reused the existing Jaccard primitive at
  `src.ztare.motion.set_distance.jaccard_distance`: non-name neighborhoods
  stayed weak (`hit@7=0.375`), but bootstrap role-neighborhood Jaccard was
  strong (`hit@7=1.0`) and combined non-name+role was `0.875`. v10.1 PPR was
  weak (`combined hit@7=0.375`), likely because row/high-degree role seeds
  flood the walk. v10.2 seeded from row obligation labels rather than gold
  candidates, but stayed weak (`hit@7=0.375`, `MRR=0.3334`). v10.3 replaced
  bootstrap candidate-role edges with a stricter non-bootstrap extractor over
  declaration kind, name-erased Expr node counts, bucketed global constants,
  and opaque `LOCAL_PROJECT` reference counts. That static interface pass
  failed hard (`hit@7=0.0`, `MRR=0.0320`). v10.4 then added a bounded
  Lean-side action-delta type probe: it compares candidate declarations
  against row patch declarations inside Lean, excludes candidate==target
  self-matches to block endpoint tautology, and ranks by non-self exact/type
  and stripped-conclusion compatibility. This recovered a real behavioral
  signal (`hit@7=0.75`, `MRR=0.3379`, `1,790` emitted probes, `40` non-self
  exact matches, `267` non-self conclusion-head matches), but still missed
  two NS rows and does not yet observe tactic side goals or failure classes.
  v10.5 upgraded to real Lean metavariable goals and probed `exact`/`apply`
  behavior (`1,790` emitted probes, `40` non-self exact successes, `40`
  non-self apply successes), but raw exact/apply success alone was sparse
  (`hit@7=0.5`, `MRR=0.2638`). v10.6 then combined v10.4 and v10.5 into an
  anti-failure router. The action-only mode held `hit@7=0.75` and improved MRR
  to `0.5251`; the mixed declaration-text adapter/risk-prior mode fell to
  `hit@7=0.5`, with non-NS hit@7 `0.3333`.

  Decision: the value surface is not plain AST shape, local constants, PPR, or
  GPU training. Static non-bootstrap structure is too coarse, but Lean-derived
  action behavior has enough signal to justify the full action-delta router:
  candidate role edges must come from bounded Lean proof-state changes
  (`exact/apply/refine/rw/simp/have/convert`), side-condition introduction,
  failure classes, patch-attribution text, or audited LLM extraction constrained
  by Lean behavior, then be tested under the same endpoint-occluded benchmark.
  v10.6 is also an overfitting warning: declaration-text priors can hurt
  transfer even when they look semantically aligned. The next improvement must
  replace text priors with more observed Lean deltas (`rw`, `simp`, `convert`,
  side-goal roles), not with more name/role vocabulary.
  GP-188 process correction:
  before adding graph algorithms or metrics, the RD/Codex workstation must
  query both the primitive surface and direct source inventory (`rg`) for
  existing set-distance, motion, graph, vocabulary, and proof-gate primitives.
  The Jaccard miss was a process bug, now corrected in v10.0 and the tick
  precheck.
  v10.7 adds actual Lean tactic deltas to the sequence. For each row/candidate
  pair, the probe tried `rw [candidate]`, `rw [<- candidate]`, and
  `simp only [candidate]` against synthetic metavariable goals. It ran `5,370`
  tactic attempts over `1,790` candidate-row probes, reached hit@7 `0.75`, and
  improved MRR to `0.6719`, with `23` successful tactic attempts. This is the
  strongest no-GPU ranking signal so far, but it is still not training
  evidence: `other_failure=5,262` versus `no_occurrence=85`, so the failure
  classifier is hiding the actual obstruction taxonomy. The v7.3 gate and RD
  precheck now consume v10.7 and keep GPU blocked until failure classes are
  split and normalizer-only wins are penalized.
  v10.8 then tested the tempting next move: combine v10.4 type compatibility,
  v10.5 exact/apply, and v10.7 rw/simp into one observed-action router without
  declaration-text role priors. This did not beat the best single tactic
  channel: set-cover tail stayed hit@7 `0.75` with MRR `0.5255` versus v10.7
  MRR `0.6719`, although non-NS hit@7 was `1.0`. This is a useful falsifier:
  simple weighting is not the next 10x move.
  v10.9 reran the same `5,370` tactic attempts with a sharper Lean failure
  taxonomy. It split the collapsed bucket completely: `no_equation_theorem =
  2,436`, `simp_no_progress = 1,770`, `invalid_rewrite_argument = 1,056`,
  `no_occurrence = 85`, and `other_failure_rate = 0.0`. The useful next router
  input is therefore not a bigger graph metric but these observed anti-failure
  classes: structure/type objects should not be sent to rewrite, equations
  without equation theorems need apply/refine/constructor probes, no-occurrence
  points to wrong target orientation or wrong local occurrence, and simp-no-
  progress marks normalization-only non-repair.
  v10.10 consumed that taxonomy as simple class penalties. It did not improve
  routing: taxonomy raw hit@7 stayed `0.75` with MRR `0.4624`; taxonomy
  penalized/set-cover MRR fell to `0.4414`. This is a useful guard: the
  taxonomy should choose actions, not merely subtract score.
  v11.1 adds the public competitor benchmark matrix after checking the current
  public landscape. Baselines are: LeanDojo/ReProver for extraction/retrieval/
  tactic generation; LeanRank for premise-selection rows; MathlibGraph for
  graph priors and holdout retrieval bars; LeanHammer/LeanPremise for dynamic
  local-premise hammer selection; Lean State Search for proof-state search;
  PyPantograph/Pantograph for execution substrate. Decision: no cold shot yet
  and no GPU. First build a same-sample competitor harness comparing graph/BM25
  public retrieval, endpoint-demoted public retrieval where available, action-
  delta routing, and combined retrieval+action routing on repair-bundle metrics.
  v11.2 ran that local same-sample harness on the current 8 repair rows and
  actual declaration pools. The robust hit@7 winner before tie adjustment was
  the hybrid retrieval+typed proxy (`hit@7=0.875`, MRR `0.65`), not pure
  action. The v10.7 tactic probe had higher optimistic MRR (`0.6719`) but
  lower hit@7 (`0.75`). v11.3 then audited action ties and found the action
  MRR was contaminated: v10.7 average-tie MRR drops to `0.0625`, with five
  zero-score gold-tie rows and five large tie groups. v11.4 freezes the robust
  verdict: current winner is cheap hybrid retrieval+typed proxy; no GPU; cold
  shot is now useful because there is a nontrivial negative to attack. The next
  local build is action selection, not action scoring: choose whether a
  candidate should be probed by `rw/simp/apply/refine/convert` before ranking.
  v11.5 implemented a conservative action-selection router: preserve the
  hybrid retrieval head, admit only candidates with positive discriminating
  Lean evidence, and block unbacked simp-only / zero-score action ties. It
  improves the local eight-row score over the robust hybrid proxy (`hit@7=1.0`,
  MRR `0.675` vs hybrid `hit@7=0.875`, MRR `0.65`). v11.6 immediately audited
  overfit and found the gain is high risk: one positive row (`v87`) and one
  negative row (`v91`), six neutral rows. Decision: v11.5 is the next
  hypothesis, not a 10x result. Do not tune it further on the 8-row set; expand
  or stress the benchmark first.
  v11.7 changed the unit from candidate rank to candidate/action repair bundle
  under fixed probe budgets. It exposed the critical split: the hybrid head hits
  a gold candidate on `7/8` rows, but the existing exact/apply/rw/simp probe
  inventory can witness gold action progress on only `2/8` rows. Candidate hit
  is therefore not proof-repair progress.
  v11.8 added actual Lean tactic execution for `exact`, `apply`, `convert ...
  using 1`, and `have h := ...`, with self-target matches excluded from
  progress and `have` success not counted as progress. This raised rows with
  gold progress witnesses from `2/8` to `6/8`; most new progress came from
  `convert_using1`, with exact/apply contributing on the pressure/Duhamel row.
  v11.9 wired those expanded actions into fixed-budget routing. The current
  best policy, `v115_expanded_affordance`, reaches the v11.8 ceiling: `6/8`
  bundle success under budget `7`, `10`, and `25`, with mean first gold repair
  probe count `2.0`. The generic fixed action order reaches only `3/8` at
  budget `7` and `4/8` at budget `25`. This is the first positive controller
  signal, but not a training or novelty promotion: two rows still lack gold
  progress witnesses, `convert_using1` is broad enough to need stricter
  before/after proof-state checks, and v11.5/v11.9 remain evaluated on the
  eight-row seed.
  v12.0 audited that exact convert risk. Among v11.9/v115 budget-7 progress
  bundles, precision is only `0.389` (`14` true progress vs `22` false
  progress), and `65` candidates have overbroad progress signatures. False
  progress is dominated by `convert_using1`. This downgrades raw convert
  success from evidence to a diagnostic.
  v12.1 reran focused Lean probes on only the v11.9/v115 budget-7 bundles and
  filtered by non-label witness quality. Raw success stays `6/8` with precision
  `0.389`; `small_delta`, `selective_action`, and `small_and_selective` all
  reduce bundle success to `4/8`, with best precision only `0.5`. The controller
  signal remains live, but the next novelty discriminator is stricter
  proof-state witness quality: target/candidate type heads, side-goal type
  snapshots, role-compatible local obligations, and endpoint/wrong-family risk.
  v12.2 made that a formal gate. It fails the current lane for external
  candidate integration and GPU: raw bundle success is `0.75`, but raw
  precision is `0.389`; the `small_and_selective` witness filter has bundle@7
  `0.5` and precision `0.5`; convert precision is `0.389`; overbroad candidate
  count is `65`. Decision: no cold shot needed now, no public candidate source
  integration yet, no GPU. Next experiment is `v12.3_full_goal_snapshot_witness_probe`.
  v12.3 ran that full-snapshot probe and failed the pre-registered witness
  gate. The strict snapshot filter reached bundle@7 `0.5` but precision only
  `0.478`; strict+selective reached precision `0.529`. Adding a sort-closure
  guard exposed the sharper instrument flaw: precision rises to `1.0`, but
  bundle@7 falls to `0.375`, because many earlier exact/apply/convert "closed"
  witnesses are Type-level closures on structure declarations rather than local
  proof-repair progress. This is useful and blocking: the target unit for the
  repair benchmark must become an executable local obligation/field/tactic state,
  not merely the type of an added declaration. Public candidate integration,
  solver/novelty claims, and GPU remain blocked until that target-unit repair is
  made and retested.
  v12.4 audited the target unit directly. The seed is mixed, not uniformly bad:
  `25` targets split into `10` sort-like, `8` object-like, and `7` proof-like
  declarations. But both v12.3 strict false-positive rows have sort-like targets
  (`v63`, `v91`). This confirms the immediate repair: rebuild the false-positive
  rows around executable local obligations or patch-level tactic states before
  expanding the benchmark or comparing against public candidate sources.
  v12.5 tested that repair on the two false-positive rows. It replaced the
  declaration-type targets with local adapter-application obligations and
  instantiated all target parameters before probing. The intended `apply`
  action now exposes the correct lower side obligation in both rows:
  `FreshComparablePacketSideConditionAudit` for `v63` and
  `LerayHeatFreshFrequencyEventTentGeometry` for `v91`; old structure-type
  decoys fail and the sort-closure count is `0`. This is a feasibility proof
  for a full 8-row target-unit rewrite, not a promotion to GPU or public
  candidate-source integration.
  v12.6 completed that full rewrite. All 8 seed rows now have executable
  local-obligation targets with gold candidate/action witnesses; gold witness
  success is `8/8` and Sort/Type closure count is `0`. The NS rows expose lower
  side-obligation heads instead of closing structure declarations, while the
  three non-NS rows close proof-like Eq goals. This clears the target-unit
  blocker and moves the next gate to target-aware policy value: the router must
  beat cheap retrieval/generic action order on the repaired rows under a fixed
  probe budget before public candidate sources, GPU, or solver/novelty claims
  are admissible.
  v12.7 ran that first policy-value check and failed the strict pre-registered
  gate with a partial positive. Best target-aware budget-10 success was `6/8`
  versus generic fixed action order `5/8`, short of the required +2-row margin;
  at budget `25`, target-aware-v115 reached `8/8` versus generic `6/8`.
  Sort/Type closures remained `0` and accepted non-gold progress was empty.
  The repaired benchmark is therefore cleaner, but the router value is still
  not strong enough to scale. Next required experiment: decompose candidate
  ordering versus action ordering on the v12.7 outputs before adding public
  candidate sources, GPU, or 20-row expansion.
  v12.8 decomposed that miss. It found no target-acceptance artifact
  (`sort_closure_count=0`, no accepted non-gold progress). Five rows are
  already solved by generic fixed action order at budget `10`. The remaining
  cases are concrete: `v65` needs action-affordance compression because the
  gold apply witness appears at probe `13`; `v86` already shows the action
  policy saving budget (`20` generic probe vs `10` target-aware); `v87` is a
  candidate-queue miss where v115 finds the non-NS diagonal simplification and
  hybrid/typed queues do not. The next useful increment is narrow v12.9 policy
  repair, not benchmark expansion or GPU.
  v12.9 implemented that narrow repair and passed the repaired-seed policy
  gate. Compressing adapter-side rows to try `apply_tac` first, with the v115
  candidate queue available, reached `8/8` success at budgets `7`, `10`, and
  `25`; generic fixed hybrid remained at `5/8` for budget `10` and `6/8` for
  budget `25`. Sort closures and accepted non-gold progress were both zero.
  This reopens the action-router lane locally, but only as an 8-row repaired
  seed result. The next admissible step is robustness/overfit stress on v12.9,
  not GPU, public candidate-source integration, or solver/novelty promotion.
  v12.10 audited the source chain after a subagent flagged possible leakage.
  The refined static audit found `0` pre-metric evaluator-label accesses in
  scoring/pool construction, so the label-leakage concern was too broad. It
  did find `6` current-file declaration-extraction paths, confirming temporal
  / post-patch candidate-pool risk. Therefore v12.9 remains valid as a local
  target-acceptance/action-affordance result, but not as deployable router
  evidence. Next gate: temporal quarantine or pre-patch/scrubbed candidate
  pools, then rerun the compressed policy.
  v12.11 ran that quarantine. It retained each row's proposed repair
  declarations but removed other seed-row repair declarations from the same
  file, removing `8-15` declarations from each NS row pool. The compressed
  policy still beat generic: `compressed_quarantined_v115` reached `7/8` at
  budget `10` and `8/8` at budget `25`, versus generic `5/8` and `6/8`, with
  no Sort/Type closures and no accepted non-gold progress. The remaining
  failure is now route selection: hybrid/union solve `v65` by budget `10`,
  while v115 solves `v87` by budget `7`.
  v12.12 converted that into a route selector under the same quarantine:
  `navier_stokes → compressed_hybrid`, non-NS → compressed-v115. The selector
  reached `8/8` at budget `10` and `8/8` at budget `25`; generic fixed hybrid
  was `5/8` and `6/8`. Sort closures and accepted non-gold progress remained
  zero. This clears advisory use for local Lean repair ordering on the NS
  track. It does not clear GPU/training/novelty claims; those need a larger
  repaired temporal-quarantined benchmark and public/cheap baseline comparison.
  Artifacts:
  `scripts/public/models/gnn_lemma_relevance/v95_lean_check_type_extractor.py`,
  `scripts/public/models/gnn_lemma_relevance/v96_lean_expr_ast_graph_extractor.py`,
  `scripts/public/models/gnn_lemma_relevance/v97_ast_graph_repair_backtest.py`,
  `scripts/public/models/gnn_lemma_relevance/v98_symbolic_expr_graph_repair_backtest.py`,
  `scripts/public/models/gnn_lemma_relevance/v99_typed_obligation_expr_graph_builder.py`,
  `scripts/public/models/gnn_lemma_relevance/v100_neighborhood_similarity_graph_backtest.py`,
  `scripts/public/models/gnn_lemma_relevance/v101_ppr_typed_obligation_graph_backtest.py`,
  `scripts/public/models/gnn_lemma_relevance/v102_row_obligation_seeded_role_backtest.py`,
  `scripts/public/models/gnn_lemma_relevance/v103_nonbootstrap_interface_role_extractor.py`,
  `scripts/public/models/gnn_lemma_relevance/v104_action_delta_type_probe.py`,
  `scripts/public/models/gnn_lemma_relevance/v105_metavar_action_delta_probe.py`,
  `scripts/public/models/gnn_lemma_relevance/v106_antifailure_repair_router.py`,
  `scripts/public/models/gnn_lemma_relevance/v107_tactic_rewrite_delta_probe.py`,
  `scripts/public/models/gnn_lemma_relevance/v108_combined_action_delta_router.py`,
  `scripts/public/models/gnn_lemma_relevance/v109_tactic_failure_taxonomy_probe.py`,
  `scripts/public/models/gnn_lemma_relevance/v110_failure_aware_action_router.py`,
  `scripts/public/models/gnn_lemma_relevance/v111_public_competitor_benchmark_matrix.py`,
  `scripts/public/models/gnn_lemma_relevance/v112_same_sample_competitor_harness.py`,
  `scripts/public/models/gnn_lemma_relevance/v113_action_probe_tie_audit.py`,
  `scripts/public/models/gnn_lemma_relevance/v114_robust_competitor_verdict.py`,
  `scripts/public/models/gnn_lemma_relevance/v115_discriminating_action_selection_router.py`,
  `scripts/public/models/gnn_lemma_relevance/v116_action_selection_overfit_audit.py`,
  `scripts/public/models/gnn_lemma_relevance/v117_probe_budget_repair_bundle_harness.py`,
  `scripts/public/models/gnn_lemma_relevance/v118_expanded_tactic_action_probe.py`,
  `scripts/public/models/gnn_lemma_relevance/v119_expanded_action_bundle_router.py`,
  `scripts/public/models/gnn_lemma_relevance/v120_convert_selectivity_audit.py`,
  `scripts/public/models/gnn_lemma_relevance/v121_focused_proof_state_witness_probe.py`,
  `scripts/public/models/gnn_lemma_relevance/v122_witness_quality_gate.py`,
  `scripts/public/models/gnn_lemma_relevance/v123_full_goal_snapshot_witness_probe.py`,
  `scripts/public/models/gnn_lemma_relevance/v124_target_unit_audit.py`,
  `scripts/public/models/gnn_lemma_relevance/v125_target_unit_repair_packet.py`,
  `scripts/public/models/gnn_lemma_relevance/v126_full_target_unit_rewrite_packet.py`,
  `scripts/public/models/gnn_lemma_relevance/v127_target_aware_policy_eval.py`,
  `scripts/public/models/gnn_lemma_relevance/v128_policy_gap_decomposition.py`,
  `scripts/public/models/gnn_lemma_relevance/v129_compressed_affordance_policy_eval.py`,
  `scripts/public/models/gnn_lemma_relevance/v130_label_leakage_static_audit.py`,
  `scripts/public/models/gnn_lemma_relevance/v131_temporal_quarantine_policy_eval.py`,
  `scripts/public/models/gnn_lemma_relevance/v132_quarantined_route_selector_eval.py`,
  `scripts/public/models/gnn_lemma_relevance/v133_pre_gnn_tri_arm_truth_gate.py`,
  `scripts/public/models/gnn_lemma_relevance/v134_probe_efficiency_truth_gate.py`,
  `analytics/public/leanmill/results/v95_lean_check_type_extractor.json`,
  `analytics/public/leanmill/results/v96_lean_expr_ast_graph_extractor.json`,
  `analytics/public/leanmill/results/v97_ast_graph_repair_backtest.json`,
  `analytics/public/leanmill/results/v98_symbolic_expr_graph_repair_backtest.json`,
  `analytics/public/leanmill/results/v99_typed_obligation_expr_graph.json`,
  `analytics/public/leanmill/results/v100_neighborhood_similarity_graph_backtest.json`,
  `analytics/public/leanmill/results/v101_ppr_typed_obligation_graph_backtest.json`,
  `analytics/public/leanmill/results/v102_row_obligation_seeded_role_backtest.json`,
  `analytics/public/leanmill/results/v103_nonbootstrap_interface_role_extractor.json`,
  `analytics/public/leanmill/results/v104_action_delta_type_probe.json`,
  `analytics/public/leanmill/results/v105_metavar_action_delta_probe.json`,
  `analytics/public/leanmill/results/v106_antifailure_repair_router.json`,
  `analytics/public/leanmill/results/v107_tactic_rewrite_delta_probe.json`,
  `analytics/public/leanmill/results/v108_combined_action_delta_router.json`,
  `analytics/public/leanmill/results/v109_tactic_failure_taxonomy_probe.json`,
  `analytics/public/leanmill/results/v110_failure_aware_action_router.json`,
  `analytics/public/leanmill/results/v111_public_competitor_benchmark_matrix.json`,
  `analytics/public/leanmill/results/v112_same_sample_competitor_harness.json`,
  `analytics/public/leanmill/results/v113_action_probe_tie_audit.json`,
  `analytics/public/leanmill/results/v114_robust_competitor_verdict.json`,
  `analytics/public/leanmill/results/v115_discriminating_action_selection_router.json`,
  `analytics/public/leanmill/results/v116_action_selection_overfit_audit.json`,
  `analytics/public/leanmill/results/v117_probe_budget_repair_bundle_harness.json`,
  `analytics/public/leanmill/results/v118_expanded_tactic_action_probe.json`,
  `analytics/public/leanmill/results/v119_expanded_action_bundle_router.json`,
  `analytics/public/leanmill/results/v120_convert_selectivity_audit.json`,
  `analytics/public/leanmill/results/v121_focused_proof_state_witness_probe.json`,
  `analytics/public/leanmill/results/v122_witness_quality_gate.json`,
  `analytics/public/leanmill/results/v123_full_goal_snapshot_witness_probe.json`,
  `analytics/public/leanmill/results/v124_target_unit_audit.json`,
  `analytics/public/leanmill/results/v125_target_unit_repair_packet.json`,
  `analytics/public/leanmill/results/v126_full_target_unit_rewrite_packet.json`,
  `analytics/public/leanmill/results/v127_target_aware_policy_eval.json`,
  `analytics/public/leanmill/results/v128_policy_gap_decomposition.json`,
  `analytics/public/leanmill/results/v129_compressed_affordance_policy_eval.json`,
  `analytics/public/leanmill/results/v130_label_leakage_static_audit.json`,
  `analytics/public/leanmill/results/v131_temporal_quarantine_policy_eval.json`,
  `analytics/public/leanmill/results/v132_quarantined_route_selector_eval.json`,
  `analytics/public/leanmill/results/v133_pre_gnn_tri_arm_truth_gate.json`,
  `analytics/public/leanmill/results/v134_probe_efficiency_truth_gate.json`.
- v13.3/v13.4 truth gates (2026-05-11): the repaired-row route selector is
  useful but not 10x.  Same-sample target-aware comparison gave graph/generic
  `5/8` at budget 10, pre-GNN proxies `7/8`, and graph+pre-GNN route selector
  `8/8`, with zero sort closures and no accepted non-gold progress.  Probe
  efficiency then showed the real workstation-shaped signal: mean failed probes
  before accepted repair fell from `8.50` for generic fixed hybrid to `1.75`
  for the route selector under a 25-probe cap (`4.86x`), while accepted repairs
  per probe at budget 10 improved from `0.125` to `0.364` (`2.91x`).  This
  authorizes advisory use and a 20-row scale-up gate, not GPU training or
  solver/novelty claims.
- v13.5 target-unit scale-up (2026-05-11): the 20-row repaired local-obligation
  packet is mechanically ready.  The Lean driver combines the repaired v12.6
  seed with 12 AP/Bohr smoke-test fixture rows and records intended
  candidate/action witnesses.  Final run: `20/20` accepted witnesses, `60`
  probes, Lean returncode `0`, total Sort/Type closure count `0`; domain mix is
  `5` NS/PDE, `13` harmonic-analysis, `1` measure-analysis, and `1`
  filter-analysis.  This is benchmark readiness only.  Next gate is v13.6:
  branch-factor/policy evaluation on these 20 rows under budgets
  `3/5/7/10/25`, still no GPU/training.
- v13.6 branch-factor policy gate (2026-05-11): the scale-up signal survives
  versus generic fixed probing but not versus cheap structural baselines by
  enough to justify novelty or training.  Full matrix: `20` rows x `20`
  candidates x `3` actions = `1200` Lean probes, returncode `0`, Sort/Type
  closures `0`.  Route selector vs generic fixed: success@10 `15/20` vs
  `3/20`, mean failed probes before gold `6.00` vs `29.50` (`4.92x`).  But
  domain+head ordering reached success@10 `14/20` and mean failed probes
  `7.00`; action-affordance reached `14/20`.  Verdict: useful advisory
  harness, no 10x/solver/GPU claim.  Next research discriminator should target
  the residual false-before-gold rows and budget-10 misses that cheap
  baselines cannot resolve.
- v13.7 strict witness digest (2026-05-11): after-state digest checks are now
  mandatory.  Re-evaluating the v13.6 matrix with a stricter target-aware
  witness contract removes route-selector false-before-gold rows from `3` to
  `0` while preserving route success@10 `15/20`, mean failed probes `6.00`,
  and Sort/Type closures `0`.  Broad `convert_using1` witnesses exposing
  `Iff`/`Nat` and weaker side-obligation exposures are rejected unless they
  match the gold local-obligation digest.  The `4.92x` generic-probe reduction
  remains, but cheap-baseline closeness still blocks training/novelty claims.
- v13.8 residual decomposition (2026-05-11): the route-selector edge over the
  best cheap baseline is not training-ready.  Route beats domain+head on all
  `20` rows, but mostly by one-probe action-order effects: `10`
  Eq-candidate-crowding/action-order rows, `9` side-obligation action-order
  rows, and only `1` non-Eq structural edge.  Only `1` row is route-only at
  budget 10 versus domain+head.  The five shared budget-10 misses are all
  Eq-heavy harmonic rows (`bohr_add`, `bohr_translate`, `mulchar_norm`,
  `finitespec_zero`, `finitespec_mul`).  Next lever: deterministic
  name-redacted candidate-interface disambiguation for crowded Eq rows, plus
  public candidate-source integration.  GPU remains blocked.
- v13.9 deterministic interface disambiguation (2026-05-11): the strongest
  pre-GNN result so far.  A CPU-only candidate-interface scorer using Lean
  conclusion signatures and namespace-leaf token overlap fixes the v13.8
  Eq-crowding failure mode: strict 20-row success@10 becomes `20/20`, false
  before gold remains `0`, and mean failed probes before gold drops to `1.05`
  versus route selector `6.00` and domain+head `7.00`.  This promotes the
  pre-GNN interface router for advisory use.  It does not promote a learned
  model: token-overlap interface scoring may still be a static/lexical shortcut.
  Required next gates are name/semantic canaries, wrong-carrier/wrong-incidence
  decoys, public candidate-source comparison, and a 40-row expansion.
- v14.0 lexical canary (2026-05-11): interface scoring is not purely
  domain-vocabulary, but tie optimism is now the main risk.  Full interface:
  success@10 `20/20`, mean failed `1.05`.  Domain-stem-redacted interface:
  success@10 `16/20`, mean failed `4.65`, still above domain+head `14/20` and
  `7.00`.  Abstract-shape interface reports success@10 `20/20`, mean failed
  `0.15`, which is suspiciously strong and probably benefits from stable
  ordering inside coarse ties.  Next gate: average-tie/permutation-tie audit.
- v14.1/v14.2 tie audits (2026-05-11): exact all-candidate tie scoring is now
  the interface promotion rule.  v14.1 top-5 estimate was insufficient and
  routed to v14.2.  v14.2 exact tie audit: full-leaf interface remains useful
  (`19/20` success@10, mean failed `1.35`), but no-domain-stem falls to
  `14/20` success@10, matching domain+head, though with lower mean failed
  (`4.20` vs `7.00`).  Abstract shape remains `20/20`, mean failed `0.15`,
  suggesting the 20-row fixture is structurally separable and not enough for a
  generality claim.  Current promotion: full interface CPU router for advisory
  use only.  Training remains blocked pending semantic alias/wrong-carrier/
  wrong-incidence decoys and 40-row expansion.
- v14.3 counterfactual interface challenge (2026-05-11): existing-pool
  adversarial decoys support the typed-router next step but not training.
  Over `517` gold-over-decoy pairs from the current 20-candidate pool,
  full-leaf interface pairwise accuracy is `0.968`, no-domain-stem `0.908`,
  abstract-shape `0.992`, and domain+head `0.891`.  Same-domain/head decoys
  improve from `0.500` under domain+head to `0.914` under full interface.
  Limitation: decoys were selected from the existing pool; no generated
  semantic wrappers, wrong-carrier axioms, or wrong-incidence axioms yet.
  Next gate: generated counterfactual decoys + slot-binding/action-delta checks.
- v14.4 generated wrong-Eq challenge (2026-05-11): aliases are stable but the
  current target-state probe is not anchored enough.  Generated aliases/wrappers
  for the five hard Eq rows pass (`5/5`).  Generated wrong-Eq decoys produce
  `3` false accepted actions (`bohr_add`, `bohr_translate`, `finitespec_mul`),
  and gold-over-wrong pairwise accuracy is `0.5` under full/no-domain/abstract
  scoring.  Root cause: `ztareProbe` instantiates target forall variables as
  fresh metavariables, so wrong Eq candidates can close by reassigning target
  variables instead of preserving local objects.  This blocks all stronger
  typed-router/novelty/training claims.  Next fix: anchored local fvar target
  states / proof-state slot binding.
- v14.5 anchored hard-Eq slot binding (2026-05-11): proof-state slot binding
  fixes the v14.4 failure.  The anchored probe uses `forallTelescope` local
  fvars for target variables on the five hard Eq rows.  Gold acceptance `5/5`,
  alias acceptance `5/5`, wrong-Eq false accepted actions `0`, Lean returncode
  `0`.  This promotes anchored target states as a mandatory GP-225 harness
  component.  Next: integrate anchoring into the full 20-row branch-factor
  harness and generated wrong-slot decoy suite.  GPU remains blocked.
- v14.6 anchored full harness (2026-05-11): the slot-binding fix survives the
  full 20-row policy loop with generated alias/wrong-Eq decoys in the candidate
  pool.  The harness uses anchored `forallTelescope` local fvars for
  `proof_goal` rows and strict after-state digests for side-obligation rows.
  Run: `1230` Lean probes, `430` signatures, returncode `0`, Sort/Type
  closures `0`.  Full-interface anchored policy: success@10 `20/20`, clean
  success@10 `20/20`, mean failed probes `1.05`; generic fixed: success@10
  `3/20`, mean failed `29.5`; domain+head: success@10 `14/20`, mean failed
  `7.0`.  Generated aliases are accepted `5/5`; generated wrong-Eq false
  accepted actions are `0`.  This reduces the immediate overfitting/leak
  concern but does not clear the broader one: the 20-row packet is still
  harmonic-heavy, all gold actions are `apply_tac`, and generated wrong-slot
  decoys only cover the five hard Eq rows.  Next discriminator: broader
  generated wrong-slot/side-obligation/NS carrier-incidence decoys before any
  40-row expansion or GPU/GNN training.
- v14.7 extended generated wrong-slot decoys (2026-05-11): broader generated
  wrong candidates also fail to fool the anchored witness contract.  Added
  wrong-slot decoys for `v87` diagonal-character RHS, `v89` sum-sub sign,
  `v135_forward_bridge` sign, `v135_volume` exponent, and
  `v135_mulchar_cont` target-function mismatch, in addition to the original
  five hard-Eq wrong candidates.  Corrected run: `1245` probes, `435`
  signatures, Lean returncode `0`, Sort/Type closures `0`, full-interface
  success@10 `20/20`, clean success@10 `20/20`, extended wrong false accepted
  actions `0`, aliases `5/5`.  Interpretation: overfit risk is materially
  reduced but not cleared.  The remaining blockers are domain skew
  (`13/20` harmonic-analysis), all gold actions currently `apply_tac`,
  suspiciously high abstract-shape separability, and missing generated NS
  wrong-carrier/wrong-incidence/fanout/budget decoys.  Keep CPU advisory use;
  no GPU/GNN training yet.
- v14.8 NS wrong-carrier/incidence/fanout decoys (2026-05-11): generated NS
  side-obligation decoys also fail to fool the anchored strict witness
  contract.  Added wrong candidates for all five NS rows (`v63`, `v65`,
  `v66`, `v86`, `v91`) that return the same result head but require the wrong
  side-obligation digest.  Run: `1260` probes, `440` signatures, Lean
  returncode `0`, Sort/Type closures `0`, full-interface success@10 `20/20`,
  clean success@10 `20/20`, all generated wrong false accepted actions `0`,
  NS wrong false accepted actions `0`, NS wrong false-before-correct rows `0`.
  This closes the current GPT-5.5 counterfactual-candidate roadmap slice for
  the 20-row packet: harder pools, semantic aliases, wrong Eq/slot decoys, NS
  wrong-carrier/incidence/fanout decoys, redacted-name diagnostics, and
  pairwise decoy metrics.  Remaining blockers before 40-row expansion:
  mixed-action rows and public-strength candidate-source baselines.  GPU/GNN
  remains blocked.
- v14.9 mixed-action local-obligation gate (2026-05-11): the harness can
  represent all six primitive action families before expanding to 40 rows.
  Synthetic local-obligation packet: `exact_tac`, `apply_tac`,
  `convert_using1`, `rw_fwd`, `rw_rev`, and `simp_only`.  Run: `324` Lean
  candidate-action probes, returncode `0`, gold accepts `6/6`, Sort/Type
  closures `0`.  The mixed-action router reaches success@3/5/10 `6/6`,
  mean failed probes `0.0`, false-before rows `0`; generic fixed action order
  reaches success@10 `1/6`, mean failed `26.5`, false-before rows `1`.
  Caveat: there are `9` alternate accepted candidate/action paths after the
  gold route, mostly exact/apply/convert equivalences or inverse rewrite
  aliases.  This reduces the apply-action monoculture blocker but does not
  prove generality.  Next: build the 40-row repaired local-obligation packet
  with real mixed-action rows, explicit allowed alternate actions, adversarial
  decoys, and public/cheap baselines.  GPU/GNN remains blocked until that
  larger packet leaves systematic residual errors for deterministic routing.
- v15.0 40-row target-unit packet (2026-05-11): construction gate passes.
  Added 20 repository-backed candidate-type local goals from SQ3/Lp
  translation, SQ3 convolution/duality, NS LSC/energy/budget/recurrence, and
  iterated-log surfaces to the existing 20-row packet.  Final run: `240` Lean
  probes, returncode `0`, gold accepts `40/40`, Sort/Type closures `0`.
  Domain mix improves but remains imperfect: harmonic-analysis `13`, NS/PDE
  `5`, SQ3/Lp `4`, NS LSC `4`, NS budget `3`, SQ3 convolution `2`,
  NS energy `2`, NS recurrence `2`, iterated-log `2`, plus three singleton
  domains.  Caveat: gold actions are still apply-heavy (`apply_tac=36`,
  `rw_fwd=3`, `exact_tac=1`) and `36/40` rows have alternate accepted actions.
  This authorizes v15.1 policy scoring but not GNN/training.  The scoring gate
  must report action mix, allowed alternates, and cheap/public baselines.
- v15.1 40-row branch-factor policy gate (2026-05-11): CPU router signal
  survives scale-up.  The shared 40-row/40-candidate/6-action matrix was split
  across eight Lean drivers to avoid code-generator recursion depth.  Run:
  `9600` candidate-action probes, `1640` signatures, returncode `0`,
  Sort/Type closures `0`.  Generic fixed order: success@10 `2/40`, mean
  failed `117.95`, false rows `1`.  Domain/head: success@10 `30/40`, mean
  failed `8.0`, false rows `0`.  Full-interface: success@10 `36/40`,
  success@25 `40/40`, mean failed `3.05`, false rows `0`.  Target-kind
  router: success@10 `30/40`, mean failed `7.05`, false rows `0`.
  Interpretation: deterministic full-interface routing is still useful at
  40 rows and beats domain/head by `+6` rows at budget 10 and `2.62x` mean
  failed-probe reduction, but the `10x`-like gap exists only versus generic
  fixed probing.  GPU/GNN remains blocked until public-strength candidate
  sources and residual-error analysis show deterministic baselines are
  insufficient.
- v15.2 BM25 signature baseline (2026-05-11): cheap lexical signature
  retrieval matches or beats the v15.1 full-interface router on the same
  40-row probe matrix.  BM25 over target/candidate conclusion tokens with
  generic action order exactly matches full-interface: success@10 `36/40`,
  success@25 `40/40`, mean failed `3.05`.  BM25 plus target-kind actions keeps
  success@10 `36/40`, success@25 `40/40`, and improves mean failed probes to
  `2.1`.  Interpretation: the current 40-row signal is a useful CPU
  signature-retrieval/action-ordering result, not yet typed proof-obstruction
  routing evidence.  This blocks any typed-router/GNN novelty claim from the
  current packet.  Next discriminators must make signature matching
  insufficient: paired same-signature wrong-carrier/wrong-incidence decoys for
  new rows, name/leaf redaction, and public candidate-source baselines.
- v15.3 40-row signature redaction audit (2026-05-11): redaction weakens the
  signal but does not clear the overfitting concern.  Full-leaf target-kind
  routing: success@10 `36/40`, mean failed `2.1`.  No-domain-stem:
  success@10 `31/40`, mean failed `5.7`, still slightly above domain/head
  (`30/40`, mean failed `8.0`).  Abstract-shape remains suspiciously strong:
  success@10 `38/40`, mean failed `1.2`.  Interpretation: the packet is still
  structurally separable, and a learned/GNN model would likely fit fixture
  geometry unless same-shape wrong-carrier/wrong-incidence/budget decoys are
  added for the 20 new rows.  Next gate should be generated counterfactual
  decoys, not training.
- v15.4 same-shape counterfactual decoy gate (2026-05-11): representative
  generated wrong candidates were added for 8 new 40-row packet families
  (SQ3 translation, NS LSC/energy/budget/recurrent maps, iterated log).  The
  clean gold-action-only witness run returned Lean code `0`, `16` probes, and
  wrong accepted repairs `0/8`.  BM25 tied or ranked the wrong decoy at least
  as high as gold in `5/8` rows, so the target-aware witness is adding signal
  beyond lexical signature matching on this representative slice.  This keeps
  the typed repair lane alive but still blocks GNN/training until these decoys
  are integrated into a full 40-row policy-pool rerun.  Artifacts:
  `scripts/public/models/gnn_lemma_relevance/v154_same_shape_counterfactual_decoys.py`,
  `analytics/public/leanmill/results/v154_same_shape_counterfactual_decoys.json`,
  `analytics/public/leanmill/results/v154_same_shape_counterfactual_decoys.md`.
- v15.5 same-shape decoy policy-delta compression gate (2026-05-11): injecting
  the v15.4 decoys into the v15.1 policy ordering barely moved branch-factor
  behavior.  Stable-order BM25/full-interface produced `0` wrong-before-gold
  rows.  Adversarial tie-breaking produced only `1` wrong-before-gold row and
  `6` added wrong-decoy actions; BM25 target-kind stayed success@10 `36/40`,
  success@25 `40/40`, with mean failed probes only moving `2.1 -> 2.25`.
  Interpretation: v15.4 is witness-hard but not policy-hard.  GNN/training is
  still blocked; the next useful discriminator must construct hard negatives
  that BM25/public retrieval place ahead of gold while Lean witnesses reject
  them.  Artifacts:
  `scripts/public/models/gnn_lemma_relevance/v155_same_shape_decoy_policy_delta.py`,
  `analytics/public/leanmill/results/v155_same_shape_decoy_policy_delta.json`,
  `analytics/public/leanmill/results/v155_same_shape_decoy_policy_delta.md`.
- v15.6/v15.7 forced-front hard-negative labels (2026-05-11): false-premise
  decoys with the same final conclusion shape as gold make BM25 wrong >= gold
  on `8/8` representative rows.  v15.6 gold-action-only probes had wrong
  accepted repairs `0`, Sort/Type closures `0`, and FDCR@3/5/10/25 `8/8`.
  v15.7 all-action probes expanded this to `96` Lean probes and `48` wrong
  action probes with wrong accepted repairs `0` and Sort/Type closures `0`.
  Forced all-actions-before-gold FDCR was `0/8` at budgets `3` and `5`, `8/8`
  at budgets `10` and `25`; this exposes the intended probe-priority learning
  target.  Action taxonomy: exact failed, apply exposed `False`, convert
  produced non-gold side goals, rewrites sometimes exposed `False`, simp failed.
  Interpretation: useful all-action hard-negative label shape, but still
  synthetic.  Before GNN, replace `False` premises with plausible missing
  obligations (carrier/incidence/budget/horizon/monotonicity).
- v15.8 plausible missing-obligation hard negatives (2026-05-11): replaced
  `False` with realistic extra side conditions on the same 8 representative
  rows: shift/carrier equality, sequence equality, zero-time equality, budget
  identity, zero-loss condition, weak horizon, input bound, and monotonicity.
  All-action run: `96` probes, `48` wrong action probes, Lean returncode `0`,
  wrong accepted repairs `0`, Sort/Type closures `0`, `False` side heads `0`,
  and BM25 wrong >= gold `8/8`.  Forced all-actions-before-gold FDCR remains
  `0/8` at budgets `3` and `5`, `8/8` at budgets `10` and `25`.  This clears
  the synthetic-`False` objection for the representative slice and produces
  plausible typed hard-negative labels.  Next blocker before GNN: test whether
  cheap symbolic pre-probe features (extra premise count, Prop premise count,
  conclusion-head match, side-condition head) already separate these decoys.
- v16.28-v16.33 live NS transfer (2026-05-12): the sidecar now has a clean
  live-NS packet, but it remains deterministic and pre-GNN.  v16.28 imported
  the Phase 5CG frontier and matched `134` NS graph nodes.  v16.29 built five
  local wrapper-hole targets and probed `240` candidate-action pairs.  v16.30
  strict filtering rejected `39` broad convert/Iff artifacts and left two
  accepted route exposures.  v16.31 narrowed the 10x claim: strong versus
  graph candidate-major/generic probing, only `2x` versus BM25 action-sweep on
  all repaired rows.  v16.32 compiled two route-exposure wrappers.  v16.33
  compiled decomposition wrappers for the three blocked live targets:
  `uniformContinuationObligation` becomes two source duties,
  `ns2028HindsightBundle` becomes four component obligations, and
  `EventRecurrencePricePDEObligationSatisfied` becomes twenty field duties.
  Interpretation: GP-225 is useful for target-kind proof-state triage and
  obligation-consequence exploration.  It is not a solver, and it is not ready
  for GNN training.
- v16.34-v16.37 solver-status inversion (2026-05-12): live NS scoring now
  separates source-proof progress, consequence exposure, decomposition,
  downstream-subgoal routing, and gap mining.  v16.34 reports source-proof
  progress `0/5`, consequence exposure `2/5`, source-duty decomposition `3/5`,
  downstream/component local units `32`, and unpaid analytic atoms `26`.
  v16.35 compiles downstream/source-duty wrapper rows without assuming the
  original source schemas.  v16.36 reframes those rows as close-or-gap:
  local closure under supplied primitive duties `5/5`, source-obligation
  closure without primitive duties `0`, named gap statements `5`.  v16.37
  runs the first replayable-closure search canary: generic action order averages
  `1.6` failed probes before local closure; target-kind order closes first-shot
  on all five rows.  Interpretation: this creates a solver-0 foothold, but only
  at local subgoal closure with primitive duties supplied.  The next gate is a
  larger closeable local-proof benchmark; GNN remains blocked.
- v16.38 twenty-row solver-0 closure seed (2026-05-12): the closure metric
  expands beyond the five-row NS canary.  The packet runs `20` closeable local
  proof rows with isolated Lean attempts: `10` NS downstream/source-duty atoms
  and `10` non-NS logic/arithmetic closure forms.  All `20/20` rows have
  replayable closure attempts.  Generic action order averages `1.3` failed
  probes before closure; GP-225 target-kind ordering closes first-shot on all
  rows (`0.0` failed).  Source-obligation closure remains `0`.  Interpretation:
  closure-ordering signal survives a broader generated seed, but the next gate
  must use natural local proof states and stronger baselines before any solver
  promotion.  GNN remains blocked.
- v16.39 natural local-closure inventory (2026-05-12): compact theorem-body
  mining found enough natural rows for the next closure benchmark.  The scan
  over selected NS and proof-helper Lean files found `39` candidates and
  selected `23`: `15` NS rows and `8` control rows.  Target-kind mix:
  `branch_choice=6`, `decomposition=5`, `exact_or_helper=3`, and
  `normalization_or_transport=9`.  Interpretation: stop expanding generated
  closure seeds.  v16.40 should replay natural theorem-body rows with file/line
  provenance and the same no-goal-left closure evaluator.  GNN remains blocked.
- v16.40 natural theorem-body replay feasibility (2026-05-12): the selected
  v16.39 rows now clone and compile in isolated Lean drivers.  The first pass
  exposed an instrument gap: controls needed active `open`/`open scoped`/
  `variable` context and two smoke-test controls were source-valid but not
  importable as built modules.  After adding context capture, stdout diagnostics,
  and source-prefix fallback for controls, v16.40 compiles `23/23` natural
  cloned theorem bodies: `15` NS and `8` controls.  Interpretation: natural
  replay is ready, but this is extraction feasibility only.  v16.41 must score
  policy attempts while treating the original proof body as oracle/extraction
  validation, not as a GP-225 success.  GNN remains blocked.
- v16.41 natural action-family closure canary (2026-05-12): after correcting an
  invalid-import instrument bug, fixed action-family replacement attempts close
  only `1/23` replayable natural rows.  The single strict closure is the
  helper-shaped `phase5cg_interior_renormalization_target_shape`; generic order
  reaches it after `1` failed probe, while target-kind ordering reaches it after
  `2`, and GP-225 improves `0` rows.  One NS `aesop` closure is marked
  leakage-risk because the source module is imported.  Interpretation: the
  generated v16.38 closure seed was too easy for action-only closure.  Natural
  closure requires candidate-bearing proof steps, dependency extraction, or a
  search tree.  This is not a GNN residual; it blocks action-only solver claims
  and points v16.42 at candidate/dependency-bearing replay.  GNN remains
  blocked.
- v16.42 natural proof-dependency replay inventory (2026-05-12): proof-line
  dependency extraction explains the v16.41 negative.  Extracted final proof
  steps close `7/23` rows; `16/23` require prefix context; `22/23` use
  helper/global identifiers.  Class counts: `one_step_branch_or_wrapper=4`,
  `one_step_exact_or_shape=2`, `one_step_local_projection=1`,
  `prefix_destructure_plus_helper=12`, `rewrite_prefix=3`,
  `helper_theorem_chain=1`.  Interpretation: natural closure is a
  prefix-aware candidate/search problem with explicit symbolic dependencies,
  not an immediate GNN residual.  The next gate is minimal proof-prefix depth
  and then candidate-bearing search baselines.  GNN remains blocked.
- v16.43 natural minimal proof-prefix depth (2026-05-12): oracle prefix replay
  closes all `23/23` natural rows after fixing raw indentation preservation for
  bullet proofs.  Depth counts: `<=1: 7`, `<=2: 8`, `<=3: 9`, `<=5: 14`,
  `<=8: 16`, `full_or_prefix: 23`, `unclosed: 0`; mean minimal prefix depth
  `8.35`.  Interpretation: natural local closure is bounded but not trivial.
  The next solver-0 gate should extract proof-step traces and test
  prefix-aware candidate search under budgets.  This remains explicit symbolic
  search work, not a GNN trigger.
- v16.44 natural proof-step trace extractor (2026-05-12): the natural rows now
  have a concrete trace table: `192` proof steps over `23` rows, with family
  counts `have=42`, `rw=20`, `rcases=14`, `arithmetic=11`,
  `simp_or_simpa=11`, `exact=10`, `branch=9`, `intro=7`, `constructor=5`,
  `structured=6`, `other=57`.  It found `107` dependency tokens and depth
  buckets `one_step=7`, `short_2_3=2`, `medium_4_8=7`, `long_9_plus=7`.
  Interpretation: the next bottleneck is deterministic prefix-aware
  candidate/search policy, not representation learning.  These traces are
  useful labels for future learning, but the current scale and explicit family
  structure still block GNN.
- v16.45 natural final-step candidate replay (2026-05-12): deterministic local
  binding produces the first natural candidate-bearing closure signal.  With
  original proof prefixes minus the final line and a pool of generic closures
  plus all natural final proof lines, all `23/23` rows close.  Generic inventory
  order averages `14.65` failed probes before closure; local-binding order
  averages `2.57` and improves `22/23` rows.  Caveat: the pool is oracle-derived
  from final proof lines, and two rows close via non-self final lines.  The next
  test must be parallelized and add same-family decoys/name-blind ordering
  before any stronger claim.  GNN remains blocked.
- v16.46 hard-decoy final-step ranking audit (2026-05-12): same-family proof-line
  decoys break the simple local-binding story.  A parallel compile pass over
  the larger pool was too slow under per-driver Lean startup, so v16.46 ran a
  no-compile ranking audit over `129` candidates: generic closures, all final
  proof lines, and same-family non-final proof-line decoys.  Generic mean rank
  is `15.0`; local binding without a final-line prior is worse at `17.35`;
  local binding with a final-line prior improves to `8.09`, but that prior is
  oracle-ish.  Interpretation: v16.45 was a real bridge signal but not robust
  enough.  The next deterministic layer is sequence/action-state context plus
  top-k compile verification.  GNN remains blocked.
- v16.47 sequence-aware hard-decoy ranking (2026-05-12): unbound-local penalties
  plus simple sequence-family priors only partially repair v16.46.  Generic
  mean true-final rank is `15.0`; v16.46 local-binding rank is `17.35`;
  sequence-aware rank is `16.61`.  Sequence improves over local binding on
  `12/23` rows but remains worse than generic overall.  True-final top-3 is
  `8/23`, top-5 `11/23`; top-3 compile verification closes those `8` rows.
  Interpretation: static sequence/local features are insufficient for hard
  same-family proof-line decoys.  The next gate is Lean-observed action deltas
  or persistent top-k probing, not GNN.
- v16.48 hard-decoy top-1 compile audit (2026-05-12): hard same-family decoys
  are currently a probe-efficiency issue rather than a false-progress issue.
  Top-1 compile results on the v16.46 hard pool: generic `0/23`, local binding
  `1/23`, sequence-aware `2/23`, final-prior binding `3/23`; wrong closures
  `0` for every policy.  Interpretation: strict witness filtering remains
  clean, but top-1 success is too low.  The next gate is top-k compile under a
  persistent Lean/Pantograph runner or action-delta filtering.  GNN remains
  blocked.
- v16.49/v16.50 hard-decoy top-k compile + leakage audit (2026-05-12):
  batched theorem-clone drivers work as an execution substrate, but raw
  theorem-clone closure is contaminated.  Every policy closed `23/23` rows by
  top-5, yet first closures were dominated by non-self final lines,
  same-source non-final lines, and generic fragments.  The leakage audit found
  `370` compiled closures over `456` attempts, including `218` wrong closures.
  Interpretation: top-k compilation is useful for instrumentation; it is not a
  solver metric without provenance filters.
- v16.50/v16.51 terminal-consumption feature (2026-05-12): terminal-consumption
  scoring is a real deterministic improvement over static sequence ranking.
  Offline true-final rank improved from `16.61` to `7.70`; compiled true-final
  top-5 improved from sequence `11/23` to `15/23`, with top-1 `7/23`.
  However, first compiled closure remained provenance-contaminated on `16/23`
  rows.  Interpretation: terminal-consumption is a CPU-router feature, not a
  deployable repair signal.
- v16.52 quarantined replay failure (2026-05-12): after removing final lines,
  same-source lines, target-name citations, and generic tactics, numeric clean
  closure still looked perfect (`23/23` for sequence/terminal).  Inspection of
  generated Lean drivers showed partial proof-line fragments such as
  `have ... :=`, truncated rewrites, and bullet fragments immediately followed
  by `#check` markers.  Interpretation: proof-line replay is killed as a
  solver metric; it can be parser-poisoned and does not model local repair.
- v16.53 candidate-action proof-state search (2026-05-12): the harness pivoted
  to live proof-state transitions.  It replays original prefixes, then tries
  dependency-derived candidates through `exact/apply/rw/rw_rev/simp/convert`.
  After namespace/prefix fixes it produced `1152` Lean probe markers over
  `3312` planned attempts.  Results: `8/23` rows showed strict proof-state
  change, `0/23` closed, mean first-progress probe `14.5`; progress came from
  `apply_tac` (`5`) and `convert_using1` (`3`).  Marker coverage is still
  partial because richer prefixes fail tactic quotation.  Interpretation:
  action-delta is the live lane, but prefix coverage and target-aware filters
  are the next bottlenecks.  GNN remains blocked.
- v16.54 target-aware progress filter audit (2026-05-12): the v16.53
  strict-progress signal collapses under a stricter target-aware filter.
  Accepted candidate progress is `0/23`; the `8/23` apparent progress rows are
  generic `Or.inl`/`Or.inr` constructor narrowing and broad `convert` schema
  gaps.  Over `1152` probes the classes are `1030` no-progress, `26`
  generic-constructor progress, `32` Sort side-goal explosions, and `64`
  convert schema gaps.  Interpretation: the current natural action-delta lane
  is valuable instrumentation but has not found accepted repair progress.
  Improve local-hypothesis candidates, branch-path compatibility, and convert
  side-goal filtering before any learning/GNN move.
- v16.55/v16.56 local-hypothesis branch compatibility (2026-05-12): local
  hypotheses improve the execution harness but not yet solver progress.  v16.55
  produced `624` markers, raw closure on `5/23` rows, and raw progress on
  `6/23`.  v16.56 then applied branch-path/local compatibility against the
  original final proof line and reduced accepted closures to `0/23`
  (`wrong_branch_path=3`, `closed_non_branch_row=1`, `wrong_local=1`).
  Interpretation: no-goal-left is insufficient on disjunction targets.  The
  next deterministic gate is branch-aware local action generation; GNN remains
  blocked because the current miss is acceptance logic, not representation
  capacity.
- v16.57 independent branch-aware local probe (2026-05-12): the v16.56 zero was
  partly an instrument artifact.  v16.55 had run candidate actions against the
  same active metavariable, so an early successful wrong-branch probe poisoned
  later compatible attempts.  v16.57 wraps every candidate-action attempt in an
  independent Lean state, snapshots residual goals before state restoration,
  and tightens direct `exact h` compatibility.  Corrected result: `624` probes,
  `5/23` branch-compatible closures, and `6/23` branch-compatible progress
  rows, all within `10` probes.  Interpretation: GP-225 has a narrow natural
  local branch-closure signal, but the solver unit now has to be replayable
  proof snippets plus gaps for the remaining rows.  GNN remains blocked.
- v17.0/v17.1 natural solver replay (2026-05-12): the solver unit moved from
  observed local progress to replay-verified closure-or-gap.  v17.0 replayed
  the v16.57 branch-compatible closures as concrete proof snippets and closed
  `5/23` natural theorem-body rows.  v17.1 added deterministic local action
  inventory (projections, tuple construction, `simpa using`, local helper
  application, arithmetic/rewrite residue) and raised primary replay-verified
  closures to `15/23`, all by budget `10` with mean first closure probe `1.47`.
  Remaining gaps are `6` oracle-only site/nested-proof rows and `2`
  no-local-inventory rows.  Interpretation: the current bottleneck is
  site-aware solver search plus helper/global candidate sources, not GNN
  capacity.
- v17.2 pull-forward candidate source prototype (2026-05-12): a non-oracle
  helper/global extractor emitted `979` candidate records across local/prefix
  locals, header/prefix identifiers, earlier same-file declarations, and
  mathlib BM25 signature matches while excluding the final proof line from query
  and candidate evidence.  This is candidate plumbing only; solver success still
  requires replay compilation.
- v17.3/v17.4 site-locality falsifier and fix (2026-05-12): v17.3 tested
  non-oracle helper/global templates as flat final-tactic appends on the `8`
  v17.1 gaps and closed `0/8`, killing candidate-source breadth as the immediate
  explanation.  v17.4 then attacked the site-locality mechanism directly:
  branch-scoped local extraction plus site-aware seed ordering closed `5/6`
  oracle-only rows, all by first probe, raising the natural replay packet to
  `20/23` closed without GNN.  Interpretation: the active residual is solver
  substrate/search/gap mining, not graph representation capacity.
- v5.1/v5.2 GPU follow-through (2026-05-11): `132.226.159.108`
  has a live watcher in `tmux` session `gnn_v51_gpu_wait`, but the A100
  was occupied by a `VLLM::EngineCore` process using ~39.5 GB, so CUDA
  training correctly waited instead of failing or killing another job.
  While waiting, a remote CPU sanity run of v5.2 residual graph reranking
  produced a positive heldout signal on 170 targets / 99,753 candidate
  edges: test hit@10 improved from v4.1 `0.3611` to v5.2 `0.5833`, hit@20
  from `0.4167` to `0.6667`, and MRR from `0.2613` to `0.3196`.
  Artifact: `analytics/public/leanmill/results/v52_residual_hetero_gnn_remote_cpu_sanity.json`.
- v6 vocab expansion (see versions log)
- v7 hypothetical: cross-encoder reranker over v5/v6 top-50 (small
  Transformer trained on (target, candidate-lemma) pairs to rerank
  by joint relevance). Estimate +0.05-0.08 over v5/v6 single-tower.
  Defer until v5/v6 production hit@10 measured.
- v8 hypothetical: true Graph2Tac (Lean AST + GNN encoder). Requires
  Lean parsing infrastructure on the GPU machine. Defer until
  cross-encoder reranker v7 lands and we measure whether the
  remaining gap warrants the architectural cost.

## Honest scope

This seam is for the LEMMA-RELEVANCE RANKER family. It is NOT for:

- The constraint-basin GNN (`scripts/public/projects/ns/ns_constraint_basin_graph.py`
  diagnostics) — different concern, separate seam if needed
- The graph2tac premise-selection literature in general — see the
  RD mandate and `papers/paper7/draft.md` for citations
- Any future ML-on-graph work that doesn't directly target lemma
  relevance

If a related ML/graph effort wants its own lineage seam, open a new
GP-XXX. This seam stays focused on the ranker.
