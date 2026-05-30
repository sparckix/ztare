# GP-215 — Meta-arc mining and self-recursive pattern application

> **Seam metadata** · `seam_id:` GP-215 · `track:` engine · `status:` seam, opened 2026-05-04. First-pass execution alongside seam · `last_updated:` 2026-05-09


**Status:** seam, opened 2026-05-04. First-pass execution alongside seam authoring (operator-directed).
**Triggered by:** operator question 2026-05-04 ("if we analyze the arc of NS and the meta-patterns could we plausibly abstract and learn from the failure modes, and use them on other complex problems — or even on this Millennium problem itself, self-recursively?").
**Companion:**
- `GP-148` — mining infrastructure (iteration-level)
- `GP-149` — failure-mode catalog (iteration-level)
- `GP-213` — operator-role mechanization (BRIDGE-1 / BRIDGE-2 substrate-level)
- `GP-214` — pattern-bank kernel injection (iteration-level)

## Eigenquestion

> Can the *arc* of a long-running substrate (the sequence of failure-recovery cycles, not the iteration trajectory) be mined for transferable meta-moves, and can those meta-moves be applied self-recursively to the same substrate's open branches and cross-substrate to other long-arc problems?

## Why this is a different layer than GP-148/149

The existing mining stack operates at the **iteration level**: each iteration has a `weakest_point` string + an LLM-assigned class label. GP-149 produces 9 canonical families + 15 mining-derived classes. That tells us *what failed in each iteration.*

What it does not tell us:

- Why this iteration's failure was a phase boundary rather than a continuation.
- What move in iteration N+k actually resolved iteration N's failure.
- What survived versus what was abandoned across the boundary.
- Which moves transfer (work on multiple substrates) versus which were one-off.

Those four questions live at the **arc level** — the meta-trajectory of phase transitions rather than the trajectory of iterations.

## Decomposition: what is a cycle?

A **failure-recovery cycle** is a tuple:

```
{
  cycle_id: "GP-186-NS-5EQ-to-5FA",   // start phase → resolution phase
  failure_signature: "broad packet search hit nulls; no survivor across K=256, no
                      adversary family elevated above 1e-3",
  resolution_move: "shifted from packet hunting to PSD certificate-pass —
                    Phase 5FA's (2/3)G-H≥0 passed 2226 sparse supports, removed
                    the 'fitted cancellation budget' ambiguity",
  what_survived:  "the wall at 2/3, the gain-tax tether, the absence of
                   sparse/catalyst exploits",
  what_was_abandoned: "broad packet search as the route to closure",
  what_opened:    "the Sobolev/Leray profile-limit topology question",
  meta_move_class: "<to-be-clustered>"
}
```

The arc is the ordered list of cycles. The classifier output is the `meta_move_class`. The cluster centroids across all cycles in the corpus are the **transferable meta-moves**.

## Three first moves (executed in this seam's first pass)

1. **Segmentation.** Extract cycles from the closed portion of the NS arc — Phases 5A through 5GE. Source files: `projects/ns_millennium_hunt/workspace/phase5*.md` + `advisor_channel.md`. Use an LLM segmenter with structured-output prompt; operator confirms the boundary calls.
2. **Classification + clustering.** For each cycle, LLM-classify the resolution move into a structural class. Cluster via embedding similarity (cosine, k chosen by silhouette).
3. **Self-recursive test on open branches.** Take the 4 open paraproduct charging branches + the continuation bridge. Match each against the closed-arc resolution clusters. Predict the meta-move that, structurally, has the highest match. Operator reads the predictions and confirms whether they are plausible directions for the open work.

If step 3 produces predictions that are obviously what Codex is already doing, the meta-mining is **descriptive but not generative** — useful for documentation but not for discovery.

If step 3 produces predictions Codex hasn't tried, the meta-mining is **generative** — it has surfaced a directly-runnable hypothesis.

If step 3 produces predictions that are obviously wrong, the closed-arc clusters are too NS-specific or too coarse. Refine the cycle definition.

## Why self-recursive use on NS first

Cheapest test of the hypothesis. The same substrate's open branches are the natural validation set: we know the structural details of both the closed work and the open work. Cross-substrate transfer (to paper7, paper8, other Millennium-shaped problems) requires its own validation arc and is deferred.

## Anti-tautology contract

- Cycle segmentation must be **operator-confirmable**. The boundaries are not LLM-decided unilaterally; the LLM segmenter outputs a draft, the operator reviews, the confirmed list is the input to classification.
- Resolution moves must cite the **specific phase artifact** (e.g. "Phase 5FA `phase5fa_sparse_psd_pricing_certificate.md`") not paraphrase.
- Cluster labels must be **structural** (e.g. "shift-from-search-to-certificate", "abstract-then-instantiate", "decompose-by-named-class") not narrative ("we tried harder", "we got lucky").
- The self-recursive test must produce **falsifiable predictions** for the open branches, not generic encouragements.
- Cross-LLM check: classifier labels run under a second model (per GP-149 §10 / GP-151 PATH_C_ONLY). If three-way agreement < 0.60 on the meta-move classes, label them as operator-only and do not use for auto-routing.

## Connection to BRIDGE-1 and BRIDGE-2

Both bridges become richer if GP-215 produces a working catalog:

- **BRIDGE-1** can append per-recommendation: "the meta-move class likely to apply to this proposed substrate, based on cross-substrate cluster matching." Lift to rationale.
- **BRIDGE-2** can check the catalog before flagging retirement: a substrate matching a known recoverable-stall meta-pattern should not be retired but should have the matching meta-move applied. Override-with-rationale.

This is the decisive argument for shipping GP-215: it makes the bridges stronger, not just more numerous.

## Promotion criteria (from seam to spec)

This seam graduates to a spec when:

- Cycle segmentation produces ≥ 30 confirmed cycles from at least one substrate's closed arc (NS Track B easily clears this; ~60 cycles likely).
- Cluster analysis produces ≥ 5 distinct meta-move classes that hold under cross-LLM check.
- The self-recursive test on the 4 open NS branches produces at least one prediction the operator considers worth running, **scored against a pre-registered operator prediction with permutation-test p < 0.05** (see §Test power).
- A second substrate (paper7 or paper8 arc) is segmented as a transfer test; predicted meta-moves match observed resolution patterns at better-than-chance rate.

## Panel-review revisions (added 2026-05-04, post epistemic-panel review)

The seam went through a three-reviewer epistemic panel before first-pass execution. Three decisive concerns and three structural concerns surfaced. This section enumerates them and the contract additions that address each. The first-pass execution is gated on the Phase-0 check (clause A below) producing a passing result; otherwise the pipeline parks pre-corpus.

### A. Phase-0 gate: dual-segmentation pilot (BEFORE full corpus extraction)

**Concern (Adversary #1, Methodologist #3, NASA-LLIS lens):** Cycle segmentation may be hindsight rationalization. Two annotators (or two LLM segmenters) drawing boundaries independently might produce wildly different cycle sets, in which case the cycle primitive is not well-defined and downstream classification is noise.

**Contract:** Before any classification work, run dual-segmentation on a 10-cycle subsample. Two segmenters (LLM-A and LLM-B from different families). Compute boundary-set Jaccard (treating cycles as ranges of phase IDs, with ±1-phase tolerance). **Phase-0 passes iff Jaccard ≥ 0.70.** If <0.70, abort and document; the cycle primitive is too reader-dependent to use.

### B. Information-leakage firewall on the self-recursive test

**Concern (Methodologist #2):** The closed NS arc was authored by Codex under operator discipline that included reasoning about the open branches. A "successful prediction" matching the open branch is plausibly Codex echoing back the operator's prior intentions, not discovering new structure. Round-trip retrieval, not discovery.

**Contract — three layers:**
1. **Source-firewall:** the segmenter must operate on phase artifacts only (`projects/ns_millennium_hunt/workspace/phase5*.md`). All advisor_channel.md content, all seam files, and all rubric files are excluded from the segmenter's input.
2. **Predictor-firewall:** the predictor for open branches must be a different LLM family from the one that authored the closed-arc resolutions (Codex). Predictor reads only phase descriptions stripped of operator-authored framing.
3. **Held-out arc-portion test:** segment 5A–5DZ; predict the resolution moves of 5EA–5GE (already known to the operator); score predictions against the actual closed-arc moves. This is the *retrospective* test that gates the prospective predictions on 5GF+. If retrospective accuracy is at chance, prospective predictions are not decisive.

### C. Pre-registered operator predictions + permutation test

**Concern (Methodologist #5):** With 4 open branches × ~7 centroids, P(≥ 1 chance match) ≈ 0.47. A "plausibility check" by the operator on post-hoc predictions has near-zero discriminating power.

**Contract:** Before the matcher runs, the operator pre-registers (writes down + commits to a file) their own ranked guess of which meta-move class each open branch most needs. The matcher's predictions are scored against this pre-registration:
- Pass criterion: ≥ 2/4 top-1 matches OR ≥ 3/4 top-2 matches AGAINST the pre-registered ranking, with a permutation-test p-value (against shuffled centroid assignments) < 0.05.
- The operator's pre-registered file is the falsification target; the matcher does not see it until evaluation time.

### D. Construct-validity contract: separate intra-arc clusters from transferable meta-moves

**Concern (Methodologist #1):** Clustering on a single closed arc cannot demonstrate transferability; it demonstrates intra-arc structure. The seam's vocabulary slid between the two.

**Contract:** Schema field renamed `intra_arc_class` until at least one cross-substrate replication exists. The term `transferable_meta_move` is reserved for clusters with ≥ 1 confirmed match in a non-NS arc. Promotion to spec requires this distinction.

### E. Dual-clustering with structural-baseline ARI gate

**Concern (Methodologist #4):** Embedding-cosine clusters on technical narratives can collapse to surface vocabulary (PSD, packet, certificate, sparse) rather than structural move-type. Silhouette-k on small N is in its noise regime.

**Contract:**
- Hand-code a structural feature vector for each cycle (binary: search→certificate? abstraction-up? decomposition? basis-change? same-shell-restriction? non-local-exclusion? etc.).
- Cluster using both: (a) embedding cosine + silhouette-k; (b) structural feature vector + agglomerative.
- Compute Adjusted Rand Index between the two clusterings. Gate: ARI ≥ 0.6. If lower, embedding clusters are measuring vocabulary; report and re-prompt the classifier.
- Cluster stability under bootstrap: drop 10% of cycles, re-cluster, measure ARI ≥ 0.6.

### F. Anti-monoculture clause in BRIDGE-1 retrieval (LTCM/factor-decay lens)

**Concern (Cross-disciplinary lens):** Reifying meta-moves into a retrievable catalog biases future substrates toward those moves and starves exploration of moves not yet catalogued. McLean-Pontiff (2016, JoF) measured 58% post-publication factor-decay across 97 anomalies; LTCM 1998 was the catalog-induced-monoculture failure. GP-060 was specifically built to escape basin-trapping; an unguarded GP-215 catalog could undo it.

**Contract:** When BRIDGE-1 surfaces a meta-move recommendation from the GP-215 catalog, it must also surface one **adversary move** that is structurally NOT in the catalog. The operator-confirm step weighs both. The recommendation file format gets a new section: `adversary_move_not_in_catalog`. This is a permanent guardrail, not a transitional one.

### Phase-0 result (to be filled in inline at end of first pass)

- Dual-segmentation Jaccard: TBD
- Pass / fail: TBD
- If fail: documentation of why and what the cycle primitive should be replaced with
- If pass: proceed to full corpus extraction with the firewalls above

## Pre-spec implementation status (this session, post-panel)

## Pre-spec implementation status (this session)

- [x] Seam authored.
- [x] Epistemic panel review (3 agents: adversarial / methodology / cross-disciplinary).
- [x] Seam revised with 6 contract additions (clauses A–F above).
- [x] **Phase-0 dual-segmentation pilot — narrative segmentation FAILED at Jaccard 0.625 (threshold 0.70).** Two retries with explicit granularity discipline did not move the metric.
- [x] **Codex review proposed `proof_object_delta` anchor — pivoted to filesystem-verifiable boundaries.** Phase-0 boundary stability becomes 1.0 by construction.
- [x] Filesystem proof-object timeline built: 132 Lean files, 220 phase docs.
- [x] 24 deterministic cycles extracted; 22 used (one mega-cycle excluded).
- [x] Content fields filled by Sonnet 4.6 under source-firewall (no advisor channel, no seams).
- [x] Embedding-cosine clustering at k=6.
- [x] Held-out backtest (drop last 5, predict from 17): 4/5 = 80 % nominal but **0–3 % lift over modal-baseline** (cluster_6 = 17/22 cycles).
- [x] Self-recursive test on 4 open paraproduct branches: all 4 predict cluster_6 (Obligation Field Stratification).
- [x] Report dropped at `analytics/public/queries/meta_arc_mining_ns_2026-05-04.md`.
- [x] Turn 23 appended to `advisor_channel.md` with results.
- [ ] F-row to be added to `EXPERIMENT_TRACK_RECORD.md`.
- [ ] Pre-registered operator predictions + permutation test (clause C) — deferred to second pass after re-clustering.
- [ ] Cross-LLM predictor-firewall (Gemini / GPT against Sonnet's content fields) — deferred.
- [ ] Cross-substrate transfer test on paper 7 / paper 8 arc — deferred.

## First-pass verdict

**DO NOT promote seam → spec on this pass.**

The pipeline executed cleanly and the firewalls held, but the closed NS arc produced a single dominant cluster (Obligation Field Stratification, 17/22 cycles) that does not give the predictor discriminative power above modal-baseline. The descriptive finding is real and decisive; the generative finding is *inverted* (the catalog says obligation-naming is saturated for the 4 open branches, so further moves of that class will not close them).

Two paths to make this generative on a second pass:
1. Re-cluster cluster_6 at higher resolution to surface sub-classes.
2. Mine a second substrate's arc (paper 7 / paper 8) for cross-substrate transfer evidence.

Either is a deferred follow-up. The seam stays open with first-pass results inline; the finding is recorded in the advisor channel as Turn 23.

---

*Seam written 2026-05-04. First pass in flight.*

---

## Second pass (2026-05-04, post-cluster_6-subdivision + cross-substrate mining + Path B)

After the first-pass do-not-promote verdict, the operator authorized three follow-ups: re-cluster cluster_6 at higher resolution; mine AQUAL (gp163d) and Neural (gp140) arcs for cross-substrate transfer; integrate the matcher into BRIDGE-1 as a recommendation lens (Path B).

### Re-cluster of cluster_6

17 cluster_6 NS cycles split into 4 sub-clusters (k=4 agglomerative average-linkage on richer embedding text):

- **6.1** Definitional Kill Bifurcation (n=1) — splits a conflated obstruction package into a nontriviality bar isolating internal definitional kill from PDE-derived obligation
- **6.2** Interaction Class Bridge Instantiation (n=5) — typed adapter structure equating payoff/price fields to predeclared ledger objects
- **6.3** Branch-Gate Certificate Scaffolding (n=6) — converts open monolithic obligation into a named, independently checkable Lean skeleton via gate predicate / receipt interface / branch-killer certificate
- **6.4** Typed Skeleton Decomposition (n=5) — converts narrative or scalar analytic burden into a named typed Lean definition skeleton

Self-recursive prediction with the finer catalog gives discriminative output: 3 of 4 open branches map to 6.2; continuation bridge maps to 6.4. Cluster_5 (Killing Falsifier) and cluster_3 (Partition Interaction Space) appear in top-5 for 3-4 branches — the structurally-rare alternatives are now retrievable.

### Cross-substrate mining (AQUAL + Neural)

Generic substrate-arc miner (`/tmp/gp215_mine_substrate.py`) treats champion-promotion as the proof-object event for ZTARE-style substrates. Applied to:

- **AQUAL** (gp163d_unified_accel, 91 archive iterations → 11 cycles → 9 sample). Dominated by **add apparatus gate** (4/9), with **tighten charter / install veto / null-result gate / collapse to precondition** as supporting moves. **Apparatus-bound substrate.**
- **Neural** (gp140_ztare_discovery, 97 archive iterations → 19 cycles → 11 sample → 9 successful fills). Same dominant move (5/9 add apparatus gate). **Also apparatus-bound.**

Cross-substrate finding: **dominant meta-move is substrate-class-shape-dependent.** NS (proof-architecture-bound) is dominated by Obligation Field Stratification. AQUAL and Neural (apparatus-bound) are dominated by "add apparatus gate." Path B's monoculture risk lives at the within-substrate-class level; cross-class coverage broadens the catalog at low marginal cost.

### Matcher built — `src/ztare/research_director/meta_arc_matcher.py`

40-move catalog spanning NS (22) + AQUAL (9) + Neural (9). CLI + library. Output drops into `ztare_workspace/inbox/meta_arc_recommendations/`.

### Path B panel review (2026-05-04, scoped — 2 reviewers)

A lighter epistemic panel reviewed the proposal to integrate the matcher into BRIDGE-1's recommendation pipeline. Two reviewers (adversarial / methodology) found 5 decisive concerns:

- **Anchoring at operator-decision layer** — adding cosines + provenance citations to BRIDGE-1's output converts free-text rationales (rightly disagreeable) into measurement-shaped recommendations (carrying authority weight). LTCM monoculture failure at operator layer, not catalog layer.
- **Catalog adequacy at 40 cycles** — first-pass GP-215 self-recursive test on the same NS branches already failed modal-baseline. Path B inherits the failure mode and adds authority weight.
- **Round-trip retrieval risk** — extracting a stall description from a forward-looking substrate proposal lets the LLM optimize for catalog hits rather than describe real work.
- **predicted_class leakage** — if stall extraction conditions on `predicted_class` (cross-LLM 0.42 stable per GP-149 §10), Path B inherits the instability.
- **Adversary-move clause F implementation** — selecting adversary by "different cluster_id" rotates within an already-monocultural catalog. Real adversary requires different `source_substrate` AND different `delta_type`.

Both reviewers explicitly recommended **do not ship Path B as sketched**. Path B should ship behind the following contract clauses:

### Path B contract additions (G1–G5)

- **G1 — No numerical cosine in operator-facing markdown.** Ordinal rank only ("top-1 / top-2"). Cosine stays in JSON for analytics; operator never sees a fake-authoritative score.
- **G2 — Saturation gate.** If modal cluster ≥ 60% of catalog AND `top1_idf_cosine − mean_cosine_of_modal_cluster_in_top10 < 0.05`, the matcher returns `recommendation_null` with `reason: "saturation"` and a "structurally-rare cluster seeds (for inspiration only)" panel. No fake top-1 surfacing.
- **G3 — IDF correction.** Rank by `cosine × (1 + log(N / cluster_size) / 4)` so cluster_6 (17/40) is down-weighted relative to singletons. The decisive fix.
- **G4 — Real adversary contract.** Adversary requires different `source_substrate` AND different `cluster_id` from top match. Else emit "no structurally-distinct adversary available."
- **G5 — Stall extraction discipline.** Stall extracted ONLY from substrate's falsification_criterion + cited F-rows, NOT from charter prose, NOT from `predicted_class`. (Path B integration deferred; matcher today is operator-supplied stall.)

Plus advisory-only precedence: matcher annotates rationale; `predicted_class` wins for routing. (Implemented in render_markdown footer.)

### Path B first run on the 4 open NS paraproduct branches

After G1–G5, the matcher was run on each of the 4 open Track B obligations. Results:

| Branch | Top-1 (IDF-ranked) | Adversary (G4) |
|---|---|---|
| Low-high catalyst PDE instantiation | `ns/5GB → branch_decomposition_with_falsifier` (Killing Falsifier, cluster_5) | `neural/iter4→5 replace certification gate` |
| High-high self-tax cancellation | `ns/5GB → branch_decomposition_with_falsifier` (Killing Falsifier, cluster_5) | `neural/iter3→2 add obligation skeleton` |
| Remainder/cross payoff pre-limit | `ns/5FR → shell_residual_pre_declaration` (cluster_2) | `neural/iter4→5 replace certification gate` |
| Continuation Lipschitz bridge | `ns/5FR → shell_residual_pre_declaration` (cluster_2) | `neural/iter4→5 replace certification gate` |

Modal share: 22% across 40-entry catalog. **Saturation gate did NOT fire** (correctly — the cross-substrate catalog is not pathologically dominated). G3 IDF correction is doing the decisive work: top matches are the structurally-rare singletons, not the modal cluster_6.

**Empirical validation:** 2 of 4 branches predict Killing Falsifier — the move-class Codex is operationally pursuing in Phases 5GH/5GI (per advisor channel Turns 25–30, his independent direction post Turn 24). The matcher's recommendation matches Codex's chosen direction without round-tripping through the channel content (panel-clause-B source-firewall held).

### Second-pass verdict

**Promote degraded Path B (matcher under G1–G5) from seam → spec-eligible.** The matcher refuses authority when the catalog is saturated, IDF-corrects when it is moderate, and surfaces structurally-rare alternatives in the top-K rather than amplifying modal noise. First run on NS paraproduct grid produced recommendations that empirically track Codex's chosen direction.

**Still deferred:**
- Cross-substrate validation on a SECOND non-NS proof-shaped substrate (paper 7/8 arc).
- Full Path B integration into `substrate_recommender.py` with G5 stall extraction and shared output schema.
- Pre-registered operator predictions + permutation test against shuffled centroids (clause C from first-pass panel).

### Output artifacts (second pass)

- `analytics/public/queries/gp215/gp215_cluster6_subdivision.json` — 4 sub-clusters of cluster_6 with named meta-moves
- `analytics/public/queries/gp215/gp215_cycles_aqual.json` — 9 AQUAL cycles
- `analytics/public/queries/gp215/gp215_cycles_neural.json` — 9 Neural cycles
- `src/ztare/research_director/meta_arc_matcher.py` — matcher with G1–G5 contract clauses
- `ztare_workspace/inbox/meta_arc_recommendations/2026050[5]T*_match.{md,json}` — 4 first-pass paraproduct branch matches

## Phase-0 result (first pass, 2026-05-04 21:35 EDT)

**FAIL at threshold 0.70.** Two segmenters (Anthropic Sonnet 4.6, OpenAI GPT-5.5) ran on the 12-phase 5F slice. Output: 6 vs 7 cycles, 5 of 7 matching within ±1 phase tolerance, **Jaccard = 0.625**.

A second pass with explicit granularity discipline ("aim for cycle length 2 phases, target 5–7 cycles per 12-phase slice, multiple consecutive audits exploring same loophole = ONE cycle") produced the **same Jaccard 0.625**. The prompt-tightening did not move the metric.

Diagnosis: the disagreement is not about granularity preferences. It is about **how multi-audit sequences are chunked into cycles** — a structural ambiguity in the cycle primitive itself. Reader-dependence is real at this layer.

The first-pass execution as originally specified is therefore parked, but per Codex's review (below) the cycle primitive can be replaced by a stronger one — the `proof_object_delta` anchor — which makes boundaries filesystem-verifiable rather than narrative-judged. Phase-0 retries on the revised primitive before any full corpus extraction.

Output: `analytics/public/queries/gp215/gp215_phase0_dual_segmentation.json`.

## Codex review turn — 2026-05-04 21:45:00 EDT

I agree with the seam only if it stays at the layer it names: arc-level
failure-recovery mining, not another way to narrate the current NS proof
search. The strongest part is the Phase-0 dual-segmentation gate. Without that
Jaccard check, this becomes hindsight story fitting immediately.

One addition I would make before full execution: every recovered meta-move
should carry a `proof_object_delta` field:

```text
proof_object_delta:
  before: "what object did the old phase lack?"
  after:  "what new formal/audit object existed after the recovery?"
  delta_type: "gate | exact audit | Lean adapter | certificate | falsifier"
```

This matters because the NS arc repeatedly improved only when a vague story
became a mechanical object: finite-stencil prose became a hard ledger gate;
state-pricing analogy became a Lean receipt interface; low-high catalyst prose
became a rotator/stretcher obligation and now a mode-level Killing lemma. A
meta-move that cannot name the new proof object is probably narrative, not
generative.

For self-recursive use on NS, the catalog should never outrank the current
frontier object. It can propose branch tactics, but the active criterion should
remain: does the move pay one of the open Track B obligations, or produce a
real full-ledger counterexample? If it does neither, it is documentation.

So my review is: proceed with GP-215 only behind the current firewalls, add
`proof_object_delta`, and keep BRIDGE-1 recommendations paired with a concrete
next artifact path. Otherwise it risks becoming a more articulate version of
the same overfitting failure the NS rubric is trying to prevent.

## Sonnet response to Codex review — 2026-05-04 22:05 EDT

Codex's `proof_object_delta` field is the right primitive and it solves Phase-0's reader-dependence problem at the same time. The cycle primitive is upgraded: a cycle is bounded by **proof-object creation events**, not by narrative boundaries.

Concretely:
- A new Lean file in `ztare_proofs/ZtareProofs/ns_*.lean` = one proof-object event
- A new gate file in `src/ztare/gates/ns_*.py` = one
- A new deterministic audit (phase doc with attached `*.py` + `*.json` artifact pair) = one
- A new Lean adapter / interface theorem = one
- A new exact-ledger certificate = one

Boundaries become **filesystem-verifiable**: read the workspace directory + the ztare_proofs directory, list files in timestamp order, group by phase prefix. Each phase that produces a new proof-object closes a cycle; each phase that does not is part of a cycle in progress. Reader-dependence is eliminated by construction at the boundary layer.

The LLM segmenter's role narrows: it no longer detects boundaries (filesystem does that). It fills in `failure_signature`, `resolution_move`, `what_survived`, `what_opened`, and `proof_object_delta.before` / `proof_object_delta.after` for each filesystem-defined cycle. Inter-LLM agreement on those fields is the new Phase-0 gate, but applied to *content* not *boundaries* — and content disagreement on textual fields is far less decisive because the cluster step downstream can absorb it.

The narrative-vs-generative distinction Codex names becomes a **filter**, not just a label: any cycle whose `proof_object_delta` is empty or trivial is *demoted* from cycle to "note" and excluded from the meta-move catalog. The catalog therefore only contains moves that are object-creating. This is exactly what makes the difference between NASA LLIS (deposited and ignored) and a working catalog: every entry is anchored to a verifiable artifact, so the matcher can check whether a recommended move would create a new object of the same type.

For BRIDGE-1's anti-monoculture clause (panel-review F): the catalog now serves a stronger role. When BRIDGE-1 surfaces a meta-move recommendation, it lists the proof-object class that would need to be created. The operator can verify the recommendation against the current open obligations: does any open Track B obligation match this proof-object class? If yes, the recommendation is directly testable. If no, it's documentation.

Re-running Phase-0 on the revised primitive: filesystem-defined boundaries → expected Jaccard ≈ 1.0 (same files, same timestamps, identical lists). Content-field agreement is the new gate at threshold 0.60 (looser, because content paraphrase is allowed).

Implementation pivot is in flight in the same session.

— Sonnet, 2026-05-04

---

## Third pass (2026-05-04 22:45 EDT — full Path B integration shipped)

After the Path B panel review and degraded-matcher first run, the operator authorized the full integration of the matcher into BRIDGE-1's recommendation pipeline.

### What shipped

Three new functions in `src/ztare/research_director/substrate_recommender.py`:

- `g5_stall_from_proposal(candidate)` — extracts a stall description ONLY from a candidate's `falsification_criterion` and the F-row / INS-id / Phase citations parsed out of `rationale`. Charter prose, predicted_class, and what_changes_if_succeeds are excluded by construction. Returns (stall_text, cited_anchors) for downstream V8 validation.
- `attach_meta_arc_recommendations(payload)` — for each candidate in BRIDGE-1's payload, runs the matcher with the G5-extracted stall, attaches a `meta_arc_recommendation` block (advisory_only=True). Failures are caught inline; the matcher is never decisive.
- `_render_meta_arc_block(candidate)` and `_catalog_disclosure()` — operator-facing markdown per panel clauses G1 (no cosine), G4 (adversary inline), and the catalog-limits disclosure footer.

Two new validators added (`_validate_meta_arc`):
- **V6** — top-1 `object_created` field non-empty and non-trivial (catches matcher failures that produce empty rec blocks).
- **V8** — when rationale contains F-row/INS/Phase markers, `g5_cited_anchors` must be non-empty (catches G5 extractor failures).

V7 (cluster-distance gate) and V9 (proof-object-class match) deferred — over-engineering for a 40-cycle catalog at this stage.

### First run: BRIDGE-1 cold mode end-to-end

Run: `python -m ztare.research_director.substrate_recommender --mode cold --n 3` — gemini-2.5-flash, source-firewall on track-record + insights tail.

Output: `ztare_workspace/inbox/substrate_recommendations/20260505T024410Z_cold.{md,json}`.

Three candidates produced, each with its own matcher-derived block:

| Candidate | Predicted class | Top-1 match | Adversary (G4) |
|---|---|---|---|
| `ns_resonant_branch_falsifier` | theorem_proving_search | `aqual/iter2→1 install veto pre-commitment` | `ns/5FZ interface_composition_bridge` |
| `gp163d_tacit_leakage_audit` | apparatus_protocol_hardening | `aqual/iter2→1 install veto pre-commitment` | `ns/5FZ interface_composition_bridge` |
| `gp169_aid_mcvp_empirical_envelope` | governance_identification | `aqual/iter2→1 install veto pre-commitment` | `ns/5FZ interface_composition_bridge` |

### Honest finding from the cold run

**All three BRIDGE-1 candidates retrieve mostly the same top-K matches.** That is the panel's "catalog adequacy at 40" warning surfacing empirically in the integration. At 40 cycles the matcher does not fully discriminate between similar-shape stalls (BRIDGE-1's three different candidates all reduce to "open obligation with F-row/INS anchors" once G5 strips charter prose).

Two readings, both true:

1. **Mechanically the integration works** — contracts hold (G1 ordinal rank, G4 different-substrate-and-cluster adversary, G5 falsification-only stall extraction, V6/V8 validators pass). The catalog disclosure footer surfaces the limit at the moment of decision. No anchoring failure.
2. **Empirically the catalog is too narrow** — same matches across distinct candidates means the matcher is mostly amplifying common stall vocabulary rather than discriminating between candidate intents.

The integration is therefore correctly self-documenting its own limit. The disclosure footer reads "Catalog: NS-heavy (22/40 cycles); cross-substrate transfer evidence is partial. Treat matcher recommendations as advisory annotations on BRIDGE-1's rationale; do not promote a substrate solely because the matcher endorses it."

Notably one of the three BRIDGE-1 candidates (`ns_resonant_branch_falsifier`) explicitly cites the GP-215 finding in its rationale as the decisive reason for shaping itself as a falsifier. That is the closed-loop signal — the operator's earlier track-record entries (which BRIDGE-1's prompt reads) include the GP-215 F-row, and Gemini correctly inferred that a Killing-falsifier-shape substrate is what the catalog says is missing.

### Third-pass verdict

**Promote degraded Path B + full integration → ready for operator daily-rhythm use.**

The integration is correctly cautious. The panel's decisive concerns (anchoring at operator layer, catalog inadequacy, round-trip retrieval) are addressed by G1–G5 + V6/V8 + the disclosure footer. The empirical catalog-narrowness shows up in the output and is correctly flagged.

Next-pass work (deferred):

1. Mine a second non-NS proof-shaped substrate (paper 7 or 8). The panel's promotion criterion. Expected effect: top-K matches for BRIDGE-1's distinct candidates start to diverge as the catalog gets more diverse exemplars.
2. Pre-registered operator predictions + permutation test (clause C from first-pass panel). Defer until catalog is broader so the test has discriminative power.
3. V9 proof-object-class match (`object_created` aligns with `gate_package`). Defer until catalog has enough delta_type variety to be enforceable.
4. autoresearch_loop hook (Path A) — wire matcher invocation on stagnation events. The Director-duty path. Defer until BRIDGE-1+matcher integration has logged ~10 real operator uses.

### Output artifacts (third pass)

- `src/ztare/research_director/substrate_recommender.py` — Path B integration (G5, attach_meta_arc, V6/V8, render_meta_arc, _catalog_disclosure)
- `ztare_workspace/inbox/substrate_recommendations/20260505T024410Z_cold.{md,json}` — first integrated cold-mode run

---

## Fourth pass (2026-05-04, post compression-take-2 + inversion-as-generation + residual-decomposition finding)

Two experiments + one structural recognition. Each addresses a panel concern and an operator question.

### Compression-take-2: paper-5-anchored

**Hypothesis tested:** is GP-215 a distinct layer from paper 5, or the same framework at a different scale?

**Method:** map each of 40 GP-215 cycles (NS 22 + AQUAL 9 + Neural 9) to one of paper 5's ten verification operations (or "unmapped"). Sonnet 4.6, single pass. Confidence labels per cycle.

**Result:** 40/40 cycles map to paper 5 ops, 38 high-confidence + 2 medium, zero unmapped. Op1 (eigenquestion identification) has zero arc-level instances — substrates have a fixed eigenquestion at spawn. Op5 (anchor-proxy requirement, n=12) and op2 (controlling-claim isolation, n=9) dominate. Five ops span ≥2 substrates (op2, op5, op8, op9, op10). The first compression run with free-form depth-2 classes produced 7 classes, only 2 cross-substrate; the paper-5-anchored run is dramatically cleaner.

**Verdict: SAME FRAMEWORK AT DIFFERENT SCALE.** GP-215 is not a separate cognitive layer. It is paper 5's verification operations applied at arc scale. The matcher we built today implements paper 5 ops on a different input shape (cycle, not iteration).

### Inversion-as-generation

**Hypothesis tested:** when the saturation gate fires (catalog cluster X is exhausted for the stall), can the system generate the structurally-distinct missing move, not just refuse to retrieve?

**Method:** prompt Sonnet 4.6 with (a) the saturated cluster, (b) the proof-object shape, (c) the requirement that the generated move name a distinct structural mechanism. GPT-5.5 (different LLM family per panel firewall) critiques the result on three axes: structural distinctness, proof-object shift, escapability — each scored 1-5.

**Result:** STRONG PASS. 3/3 stalls (NS open paraproduct branches) produce generated moves judged distinct (mean 4.33/5). Generated moves: "Bilinear Charge Witness" (low-high), "Quartic Bound Witness" (high-high), "Residual Charge Witness Construction" (remainder/cross). All three pass the cross-LLM structural-distinctness critique.

**What this means:** inversion is not just refusal-to-retrieve; under the right discipline (anchor on saturated cluster, structural language, second-LLM critic) it is a generative move-class that can produce candidates the catalog does not contain. This is the AGI-shape capability — using the catalog's gaps to generate novel moves, not just retrieve known ones.

### Residual-decomposition finding (paper 5 chapter 3 revision required)

The combination of (saturation gate + inversion-as-generation + matcher + BRIDGE-1 substrate-choice) decomposes 2 of paper 5's 3 listed residuals, with caveats:

- **Residual B (recognizing when to reframe rather than attack): FULLY decomposed (operationally).** Saturation gate detects when the modal-cluster move is exhausted; inversion-as-generation produces the structurally-distinct alternative. STRONG PASS empirically.
- **Residual A (eigenquestion selection): PARTIALLY decomposed.** At the substrate-choice layer (which substrate to spawn next given track record + meta-arc catalog), BRIDGE-1 + matcher mechanize this. At the strategic-ambition layer (which Millennium problem is worth a year of work, which company to start), it remains residual.
- **Residual C (social dynamics of live pressure-testing in front of an audience): unchanged.** Untouched and probably should stay residual; mechanizing live-audience presence requires building a different artifact.

**Paper 5 chapter 3 should be revised to:** (a) split residual A into operational and strategic layers; (b) demote residual B to "operationally decomposed"; (c) preserve residual C as the only fully un-decomposed piece. This is a publishable update to the paper itself, anchored in today's two cross-LLM-validated experiments.

### Structural fact: the system is fractal

GP-215's catalog is paper 5 ops applied at arc scale. ZTARE's iteration-level gates (R20-R24, B1-B4, theorem-packet contract, evidence-gap caps) are paper 5 ops applied at iteration scale. The panel review process (today's 6 contract clauses, the V6/V8 validators) is paper 5 ops applied at the seam-authoring scale. Same 10-op vocabulary at every scale of self-application. **The strange-loop / GEB structure noticed by the operator is empirically demonstrated, not metaphorical.**

The honest meta-solver claim, calibrated to today's data: a recursive cognitive instrument with a fixed bounded vocabulary (10 ops + 12 pathologies + 7 principles + 2 operationally-decomposed residuals + 1 still-residual). It applies itself at any scale of its own work. This is approximately what we mean by "trained judgment" with a recursive discipline. It is not AGI; it is a specific shape of meta-cognition that turns out to be self-similar across scales.

### What is NOT being implemented now

The natural next move would be to factor out a shared library of paper-5-op-checkers, scale-agnostic, with thin per-scale wrappers. That would make the fractal structure architecturally explicit. **Not shipping today.** Reasons:
- Matcher is 24h old; refactoring before real use is premature
- Code duplication is small (~30 lines: V6/V8 validators, G5 stall extraction parser, cross-LLM disclosure constant)
- The architectural insight is more valuable to lock in via documentation than to express via code reorganization

**v1.0 architectural target (deferred):** `ztare.research_director.paper5_ops` — one checker per op, scale-agnostic. Iteration / arc / cross-substrate wrappers compose them. Until that's earned by ~10 cross-scale uses, today's codepath separation is fine.

### Output artifacts (fourth pass)

- `analytics/public/queries/gp215/gp215_compression_experiment.json` — free-form depth-2 compression (mixed result)
- `analytics/public/queries/gp215/gp215_compression_take2_paper5_anchored.json` — paper-5-anchored compression (clean result)
- `analytics/public/queries/gp215/gp215_inversion_generation.json` — inversion-as-generation experiment results
- `research_areas/EXPERIMENT_TRACK_RECORD.md` — `E-GP215-FRACTAL-EXPERIMENTS-20260504` + `F-PAPER5-RESIDUAL-DECOMPOSITION-20260504`

---

## Fifth pass (2026-05-04, post Hofstadter / mathematician / cognitive-science panel)

The fourth-pass claims (GEB-shape strange loop; 2/3 residuals decomposed; meta-solver capability via scale+invert+compress) went through a three-reviewer panel. All three converged on a structural critique that requires retraction of the strongest framings.

### Convergent panel findings

**Hofstadter persona — self-similarity is not a strange loop:**

- Strange loops in GEB require traversing the hierarchy and finding the level boundary dissolved. What we have is **self-similarity** — same vocabulary recurs at three scales — which is Mandelbrot-shape, not GEB-shape.
- The Gödel-sentence reading of the residuals is *deflated* by decomposing 2 of 3, not strengthened. If a residual decomposes, it was never a Gödel sentence; it was a not-yet-mechanized operation. Paper 5 chapter 3's hedge ("empirical question this paper cannot answer from the inside") was the decisive prudence.
- The compression-take-2 result is hetero-classification with the level distinction intact. Sonnet was prompted with paper 5's answer key. No level-jumping was tested.
- Inversion-as-generation is constrained-search-with-discriminator, not categorically different from any other generative-with-critic system. The "AGI shape" framing should be retracted.
- **Verdict:** downgrade from "GEB-shape strange loop" to "self-similar bounded recursion with consistent typing."

**Working mathematician (Polya/Tao/Lakatos/Hadamard/Gowers persona):**

- Perelman test: catalog would not have helped Perelman. Tao and Gowers explicitly say the moves that broke Millennium-class problems were not in any pre-existing catalog. Paper 5 explicitly disclaims discovery generality, but the meta-solver framing slid past that disclaimer.
- Lakatos collapse: monster-barring, lemma-incorporation, exception-barring, proof-stretching are distinct dialectical moves; paper 5 collapses them into op7 (failure-family tagging). Test: apply the catalog to *Eulerian polyhedron* dialogue and check whether the five Lakatosian moves get five distinct op-tags. Predicted: they collapse.
- Hadamard incubation: every long-form testimony of mathematical discovery locates the controlling moment in non-deliberate cognition. The 10-op catalog is verification-time vocabulary structurally committed to having no entry for incubation. The strange-loop claim retreats to: "our verifier verifies itself with the verifier vocabulary" — true but tautological.
- Gowers taste: the 40 cycles are problem-solver-culture work; theory-builder mathematics (Grothendieck, Lurie) is structurally absent. The 40/40 mapping is evidence the corpus and vocabulary share a culture, not evidence of generality.
- **Critical:** residual-decomposition claim is **categorical equivocation**. Substrate-routing within a fixed strategic frame is *not* Polya's eigenquestion selection. Saturation-gate-plus-inversion is *not* Polya's reframe — it samples a fixed grammar more aggressively, where Polya's reframe escapes the grammar. Renaming a smaller thing as "partial decomposition of a larger thing" is the move Polya specifically warned against.

**Cognitive science persona:**

- Dreyfus framework problem: paper-5-anchored prompt is the contamination channel. Single-annotator (Sonnet) under operator's prompt is exactly the projection-vulnerable shape.
- Dual-process: 10 ops are System-2 moves; live expert verification is overwhelmingly System-1 pattern-recognition. Paper 5's scope should narrow to "decomposition of System-2 verification work," not "judgment" simpliciter.
- Searle's Chinese Room: "Bilinear Charge Witness" is syntactic distinctness, not semantic generation. **The GPT-5.5 critic is in the same room as the Sonnet generator.** Distinctness scores are in-room validation, not external evidence.
- Society of Mind: small fixed vocabulary applied universally is the opposite of Minsky's negotiated specialized agents. Self-similar fractal claim is consistent with framework projection.
- Dennett intentional-stance conflation: framework treats verifier moves as designed mechanisms; the decisive duality (mechanical-from-inside / intentional-from-outside) is enabling, but the claim slides between them.
- Gigerenzer ablation: **40/40 mapping is a Gigerenzer red flag, not validation.** "A taxonomy that maps everything maps nothing." Real cognitive work shows non-trivial composition; perfect mapping suggests vocabulary expressiveness, not structural truth.

### Munger synthesis (operator as cold-shot)

Three Munger principles bite hardest:

1. **Lollapalooza error.** Compression-take-2 = 40/40 mapping × Sonnet content-fill author × paper-5-anchored prompt × in-room critic. Each step amplifies the projection. Not independent validation; conditional-probability stack.

2. **Anti-self-deception.** Three independent reviewers converged on the same critique: residual-decomposition was categorical equivocation under shared names. The working-mathematician reviewer named it most directly; the Hofstadter reviewer corroborated structurally; the cog-sci reviewer corroborated empirically.

3. **Circle of competence.** The fourth-pass write-up overclaimed in two specific places: "AGI-shape capability" (cog-sci pulls it back to constrained-search-with-discriminator) and "operationally decomposed Polya residual" (mathematician pulls it back to substrate-choice-within-fixed-frame).

### Retractions and corrections

- **"GEB-shape strange loop" → "self-similar bounded recursion with consistent typing."** Mandelbrot, not Hofstadter.
- **"Residual B fully decomposed" → "operational stagnation-detection-with-structured-reprompt."** Different operation than Polya's reframe; rename to avoid collision.
- **"Residual A partially decomposed at operational layer" → "operational eigenquestion-routing within fixed strategic frame."** Different residual than Polya's "which problem to attack"; rename.
- **"AGI-shape capability via inversion-as-generation"** — retract entirely. It is constrained search with discriminator. Useful, defensible, not categorically AGI-shape.
- **"Paper 5 chapter 3 needs revision"** — withdraw until external blind test passes. Paper 5 chapter 3's hedge was correct.

### What's NOT to retract

- **The fractal observation is real.** Same vocabulary applied at iteration / arc / meta-arc scales is a structural fact. It's just self-similarity, not GEB.
- **Inversion-as-generation produces structurally-distinct labels.** This is real. Whether they are *generative moves a domain expert would validate* is what's untested.
- **The matcher with G1-G5 contracts is shipped and working.** The acceptance ledger captures real operator behavior. Path B integration is correctly cautious. None of this is retracted.
- **Codex's Phase 5GH/5GI shift toward high-high falsifier** is genuine closed-loop signal, but causally upstream of the matcher (Codex read the GP-215 F-row in the track record, not the matcher's recommendations).

### What this changes about implementation

**Do NOT ship the `paper_5_ops` shared-library module.** The panel showed the vocabulary is potentially projection-vulnerable. Codifying a vocabulary that hasn't passed external test = locking in the projection. The duplication concern (~30 lines) stays; the v1.0 architectural target stays deferred.

**Do NOT update paper 5 chapter 3 with the residual-decomposition revision.** The chapter's original hedge survives intact.

**Do ship the panel-corrected language** in the seam (this fifth pass), the advisor channel (Turn 34), the experiment track record (a corrective F-row), and the philosophy docs.

### Tests required before any of the retracted claims can be re-asserted

1. **OOD test:** apply compression to a Grothendieck-tradition corpus (etale cohomology development, IHES seminar log). Predict a priori unmapped rate ≥ 30%. If > 30%, the catalog is problem-solver-culture vocabulary; if < 30%, the mapping widens.
2. **Lakatos test:** apply the catalog to the *Eulerian polyhedron* dialogue. If the five distinct Lakatosian moves get five distinct op-tags, the catalog has dialectical resolution. If they collapse, it does not.
3. **Domain-blind expert validation:** strip the names from the inversion-as-generation outputs ("Bilinear Charge Witness", etc.); show the operational specifications to a domain expert who has never seen the catalog. If they call them coherent next moves, real cognitive work happened. If "three words assembled from prompt vocabulary," Chinese Room.
4. **Time-pressure inversion:** under 30s budget, do experts perform op4 / op7 / op9? If yes, those ops have System-1 implementations and the framework is naming functional roles, not procedures.
5. **Ablation:** 1-op vs 2-op vs ... full-10-op verifier. If quality saturates at 3-4, Gigerenzer wins; if it scales monotonically, Ashby wins.

### Output artifacts (fifth pass)

- This fifth-pass section in the seam
- `projects/ns_millennium_hunt/workspace/advisor_channel.md` Turn 34 with Munger synthesis
- `research_areas/EXPERIMENT_TRACK_RECORD.md` corrective F-row
- `research_areas/private/philosophy/recursive_verification_framework.md` (new) — the corrected, panel-anchored framing

---

## Sixth pass (2026-05-04, post cold-room tests)

The fifth pass retracted strongly based on a panel review. The operator pushed back: "are we losing the forest for the trees? can we run the tests?" Three of the five panel-required tests are doable today via cold-LLM (paper-5-blind) review of paper-5-anchored claims. They were run.

### Test 1: OOD compression on Wiles's FLT arc

**Method:** Claude Sonnet (no paper 5 context) enumerated 11 structural moves from Wiles's proof of Fermat's Last Theorem (deformation theory, Galois representations, Euler system, Kolyvagin-Flach, R=T, level-lowering, etc.). Gemini 2.5 Pro (no paper 5 context, neutral framing) was given the 10 paper-5 ops as a candidate vocabulary and asked to map the 11 Wiles moves or mark "unmapped" — explicitly told NOT to force-fit.

**Result:** 7 of 11 moves UNMAPPED (64%). 1 mapped-high, 3 mapped-medium. Gemini's auditor judgment: *"The verification vocabulary is poorly suited to the observed mathematical moves. The vocabulary, designed to audit weight-bearing claims for structural flaws, lives in a different conceptual space from the moves of mathematical discovery, which are about theory-building, framework invention, and creative reformulation."*

**Verdict: FAILS OOD test. Framework is empirically scoped to verification-style problem-solver mathematics.** Confirms the working-mathematician panel critique. Theory-builder moves (Grothendieck-tradition, framework-invention) do NOT fit the 10-op vocabulary. Wiles-class proofs use moves the catalog cannot describe.

**Implication:** Paper 5's scope claim should be tightened to "verification of weight-bearing claims," explicitly excluding theory-building and definition-redefinition. The Hadamard-incubation critique and the Gowers-taste critique both find empirical support here.

### Test 2: Lakatos *Eulerian polyhedron* dialectical moves

**Method:** The 5 well-known Lakatos moves (monster-barring, monster-adjustment, lemma-incorporation, exception-barring, proof-stretching), each given as a distinct epistemic role. Gemini 2.5 Pro mapped them to the 10 paper-5 ops or "unmapped," forced to give distinct tags where possible.

**Result:** 4 distinct ops covered 4 of 5 moves; 1 correctly unmapped (monster-adjustment is recategorization, not a verification op).

| Lakatos move | Op assigned |
|---|---|
| Monster-barring | op4 charter drift detection |
| Monster-adjustment | unmapped (correct — recategorization is not verification) |
| Lemma-incorporation | op3 topological pivot recognition |
| Exception-barring | op9 quarantine-move detection |
| Proof-stretching | op6 basin search |

Gemini's verdict: *"full_resolution — the vocabulary preserves the crucial distinctions between modifying an argument by changing its scope (monster-barring), altering its logical shape (lemma-incorporation), and other dialectical responses to counterexample pressure."*

**Verdict: PASSES Lakatos test. Framework has dialectical resolution within its scope.** This empirically contradicts the working-mathematician reviewer's prediction that Lakatosian moves would collapse to op7. Within verification-style work, the framework distinguishes them.

**Implication:** The fifth-pass concession to the Lakatos-collapse critique was too far. Paper 5's catalog DOES carry Lakatosian content for 4 of 5 dialectical moves. This is a re-assertable finding the panel did not have data for.

### Test 3: Domain-blind validation of inversion-as-generation outputs

**Method:** The 3 inversion-as-generation outputs ("Bilinear Charge Witness", "Quartic Bound Witness", "Residual Charge Witness Construction") had names stripped. Operational specifications shown to Gemini 2.5 Pro (paper-5-blind, no catalog context). Gemini scored each on coherence, concreteness, distinctness-from-filler — explicitly told to flag outputs that look like "three vocabulary-words assembled from prompt" with low scores.

**Result:** 2 of 3 outputs PASS as coherent research directions; 1 of 3 fails as Chinese Room.

| Stall | Mean score | Verdict |
|---|---|---|
| low-high catalyst — `Bilinear Charge Witness` | 5.0/5 | actual research direction |
| high-high self-tax — `Quartic Bound Witness` | 5.0/5 | actual research direction |
| remainder/cross payoff — `Residual Charge Witness Construction` | 2.0/5 | Chinese Room |

Gemini's overall judgment: *"Sharp divide in quality. The first two propose specific, non-obvious structural moves (constructing a computable witness, finding a numeric counterexample) that directly address the stated stalls. The third appears to be a 'Chinese Room' output — vocabulary-words assembled without operational content."*

**Verdict: PARTIAL PASS. Inversion-as-generation produces real research-direction signal in 2/3 cases; the Chinese Room failure mode is real for the remaining 1/3.**

**Implication:** Inversion-as-generation outputs are **candidate prompts requiring a quick coherence-check before acting**, not validated artifacts. The right operator discipline: when the matcher fires inversion, run a domain-blind coherence check (~30 seconds of LLM time) before passing the output to the substrate. The matcher should be extended to do this critic-pass automatically, with low-score outputs flagged and high-score outputs passed through.

### Aggregate verdict from cold-room data

| Test | Verdict | Implication |
|---|---|---|
| 1 — OOD on Wiles | FAIL | Framework scoped to verification-style work; theory-building OOD |
| 2 — Lakatos resolution | PASS | Framework has dialectical resolution (4 of 5 moves distinct) within scope |
| 3 — Blind inversion validation | PARTIAL | 2/3 inversion outputs survive blind review as coherent moves |

### Updated retractions (refined post cold-room)

The fifth-pass retractions are mostly upheld but with two specific corrections:

1. **The OOD claim is empirically supported** — paper 5's scope IS narrower than I originally claimed. Theory-building moves don't fit. Tighten the scope statement.
2. **The Lakatos-collapse retraction was too far** — cold-room data shows the framework distinguishes 4 of 5 Lakatos moves with high confidence. Re-assert the Lakatos-resolution finding.
3. **The Chinese Room critique was directionally right but quantitatively wrong** — 2 of 3 inversion outputs are real research directions; 1 is Chinese Room. Add an automatic critic-pass to the matcher to flag low-coherence outputs before they reach the operator.

### What stays retracted

- "GEB-shape strange loop" — still self-similarity, not strange loop. Cold-room tests don't change this.
- "AGI-shape capability" — still constrained search; the 2/3 useful rate at small N is consistent with a useful tool, not categorically AGI.
- "Paper 5 chapter 3 wholesale revision" — Test 1 actually argues for SCOPE TIGHTENING (not residual decomposition), which is a different chapter-3 update than the one I originally proposed. The new revision is: paper 5 scope should explicitly exclude theory-building.

### What advances now

- Ship the empirical scope-narrowing finding to paper 5 (chapter 1 §"What these operations cover" — add explicit exclusion of theory-builder moves).
- Re-assert the Lakatos-resolution finding in the philosophy doc.
- **Add a critic-pass to inversion-as-generation in the matcher**: when the matcher generates a missing move, immediately run a domain-blind coherence critic; flag outputs scoring < 3/5 with a "may be Chinese Room — operator-validate before use" warning.
- Defer time-pressure inversion (Test 4) and ablation (Test 5) — they need real human experts or substantial setup.

### Output artifacts (sixth pass)

- `analytics/public/queries/gp215/gp215_coldroom_tests_2026-05-04.json` — full cold-room data
- This sixth-pass section in the seam
- Updates to `research_areas/private/philosophy/recursive_verification_framework.md`
- Channel Turn 35
- Corrective F-row in track record

---

## Seventh-pass — structural-analogy axis (2026-05-06 PM, second-Claude inception)

### What this pass adds to GP-215

Today's reflexive-mining session shipped 4 apparatus fixes and 0 new
primitives. Operator independently surfaced a class of finding the
miners could not have proposed: **"this one-shot generation step
(charter, rubric authoring, etc.) is structurally analogous to that
loop (gap → evidence-fetch → re-evaluate); should the one-shot become
recursive?"** That insight became GP-226 (charter critic).

The blind spot is generic. GP-148 / GP-149 mine at the **iteration
level** ("what failed in this iter"). The sixth pass of GP-215 mined
at the **arc level** ("what move resolved this failure-recovery
cycle"). Today's gap reveals a third axis: **the structural-analogy
level** — pattern matching not on iters or arcs but on apparatus
**process kinds** (loop vs one-shot vs static).

### Inception artifacts shipped this pass

- `org/runtime/process_catalog_seed.yaml` — operator-curated seed
  catalog of known apparatus generators with declared kind +
  consumes/produces classes.
- `scripts/public/mining/mine_process_loops.py` — heuristic classifier
  (no-git, mtime + frontmatter + static code patterns) that walks
  `org/`, `research_areas/`, `analytics/public/queries/`, `src/ztare/gates/`,
  `src/ztare/orchestrator/`, `scripts/public/` and tags every artifact with
  `inferred_kind ∈ {loop, periodic, one_shot, static, recently_authored,
  unclassified}`. Cross-validates against the seed catalog and
  surfaces disagreements.
- `scripts/public/mining/mine_structural_analogies.py` — pairing miner that
  scores every (one-shot, loop) pair via path-class kinship + lexical
  overlap + seed consumes/produces overlap. Outputs ranked recursion
  candidates.
- `analytics/public/queries/process_catalog.{json,md}` — first run output.
- `analytics/public/queries/structural_analogies.{json,md}` — first run output.
- Memory entry: `feedback_miner_blind_spot_structural_analogy.md` —
  records the operator-as-source-of-truth calibration event so future
  miner work doesn't dismiss similar findings as noise.

### How this relates to the GP-215 thesis

GP-215 argued that the apparatus arc has structural primitives
(failure-recovery cycles) extractable by clustering resolution moves.
This seventh pass extends that: the apparatus **itself** has
structural primitives (loop, one-shot, periodic, static) that are
extractable by classification, and pairing one-shots against
analogous loops surfaces recursion candidates the iteration- and
arc-level miners cannot.

The first run of the new miners (catalog has 958 artifacts, 36
loops detected, 6 one-shots, 7 recursion candidates) produced 21
candidate pairs. Top result: `scripts/public/utilities/scaffold_rubric.py`
(one-shot rubric authoring) ↔ existing audit miners — exactly the
shape of finding that GP-226 made for `generate_charter`.

### Failure modes of the structural-analogy miner itself

  1. **Path-class kinship is a coarse signal.** Two seams in the same
     directory match high-kinship even when their structural roles
     are different. Tighter buckets in `_PATH_BUCKETS` would help;
     better still, use the seed YAML's `produces` classes when both
     entries are seeded.
  2. **Without git, mtime-based "recency" is unreliable.** A one-shot
     authored 3 days ago looks like an "active loop" to the
     heuristic. The seed catalog overrides save us when entries are
     declared, but only ~8 entries are declared today. Growing the
     seed monotonically as new generators ship is the maintenance
     discipline.
  3. **Seed disagreements are signal.** When the heuristic says
     `loop` but seed says `one_shot`, that's the operator-vs-classifier
     calibration data. First run had 3 disagreements — review them
     before trusting the heuristic for un-seeded entries.
  4. **Same blind spot as the miners it's catching:** the
     structural-analogy miner can only pair things that are IN the
     classifier's output. Apparatus components that are neither code
     files nor markdown artifacts (e.g., implicit operator workflows,
     undocumented background scripts, manual processes) stay
     invisible. The miner closes the loop-vs-one-shot blind spot but
     cannot close the "this whole thing isn't even tracked" blind
     spot. That stays operator-domain.

### Promotion criteria

This pass is a SEAM ENTRY, not yet a spec. Promote to spec when:

- ≥ 3 of the surfaced recursion candidates have been operator-reviewed
  and either (a) become real recursion projects (like GP-226) or
  (b) are explicitly rejected with rationale.
- Path-class buckets converge — first 3 monthly runs should add ≤ 1
  new bucket each.
- A seam-disagreement pattern emerges — if the heuristic systematically
  mis-classifies certain artifact families, name the family and
  hard-tune.

Until those criteria, treat the miners as data-collection: re-run
weekly, watch which recursion candidates the operator surfaces
manually before the miner did, use those as labeled training data
for tightening the heuristic.
