# GP-233 — 4-Catalog META Solver/Harness Framework

> **Seam metadata** · `seam_id:` GP-233 · `track:` reflexive · `status:` demoted / superseded · `last_updated:` 2026-05-25


**Status:** demoted / superseded as a solver architecture; retained for failure-mode provenance and reusable subcomponents
**Cabinet:** `reflexive/` (meta-architecture for any substrate-specific solver)
**Authored:** 2026-05-15
**Trigger:** v22 → v30 chain of 6+ consecutive negative-claim collapses under fair Meta-Darwin discipline on the GP-225 Lean proof-composition benchmark. Operator reframe (this session): the decisive artifact is NOT the moat-grade row count (structurally bounded at 0-1 per session-day) but the **4-catalog meta-policy** that classifies goals + picks tactics + flags anti-patterns + logs traces.

**2026-05-25 status correction:** this seam is not an active LeanMill solver contract. Its own §7 demotion and the follow-on GP-235/pattern-action-contract work supersede the original 4-catalog Route-C architecture. Surviving pieces are reusable primitives only: anti-pattern guards, semantic masking intuition, bounded safe Lean execution, DAG-fingerprint discrimination, and typed pattern/action contracts. Do not cite this seam as evidence that a 4-catalog solver is implemented or value-additive in the current 24x7 LeanMill factory. Current LeanMill work should consume the surviving principles through `src/ztare/research_director/pattern_action_contract.py`, `research_areas/seams/reflexive/GP-235_dag_fingerprint_primitive_validation_seam.md`, and GP-225 LeanMill factory seams/specs.

## 1. The empirical observation

Across 8 consecutive v22→v30 chains, every claimed "moat-grade Lean closure" was killed under fair audit by one of:

- `gold_name_verbatim` (the closure cites the gold lemma by name)
- `paraphrase_of_named_gold_lemma_via_rewrite` (simp-set ≈ gold lemma's defining simp set)
- `fun_prop_indirect_leakage` (@[fun_prop] global set contains gold lemma)
- `simp_set_indirect_leakage` (@[simp] global set contains gold lemma)
- `gcongr_floor_satisfiable` (Mathlib's generic k-fold monotonicity tactic kills the row at the floor)
- `missing_import_Hammer_bug` (B1 screen mis-classified rows as hammer-OPEN due to missing import)

**Honest harvest rate on natural Mathlib-style goals: 0-1 moat-grade closures per session-day under fair audit.** This is structural, not skill — the goal class is exactly the intersection (truth ∩ tactic-resistant ∩ Mathlib-resistant ∩ paraphrase-resistant), which is empty for "natural" rows.

## 2. The reframe

The solver/harness is NOT "close N rows per session." It is a **4-catalog meta-policy** where each layer is independent, has its own consumer, and composes cleanly:

| Layer | Catalog | Role | Consumer |
|---|---|---|---|
| **L1 — Research process** | `org/runtime/pattern_catalog.yaml` (generated from `org/patterns/*.md`) | Orchestration patterns: when to dispatch agents, debates, cold-shots, Meta-Darwin audits | Dispatcher / orchestrator |
| **L2 — Mathematical content** | `workingpapers/epistemic-generation/evidence/structural_language_catalog_20260514.json` | Structural ops of a goal (Reformulation, Auxiliary Comparison, Limit-Passage, Sharpness, Failure-Witness, PDE estimate craft, etc.) | Goal-shape classifier |
| **L3 — Failure modes** | `org/anti-patterns/*.md` (12 existing + 5 new from v30) | Pre-screen for anti-pattern risk on a proposed closure | Closure auditor / Meta-Darwin |
| **L4 — Lean tactic archetypes** | `analytics/public/leanmill/results/v30_layer4_unified_catalog.json` (this seam, NEW) | 24 archetypes from 50-proof corpus + 40 curated exemplars across ARCH-001..008 (reviewer-spec) | Tactic-pack selector / `archetype_classifier.py` |

The solver pipeline becomes:

```
goal → classify(L4 archetype) + classify(L2 op) + flag(L3 anti-patterns)
     → recommend tactic chain (from L4 catalog)
     → execute via safe Lean runner
     → repair on compiler feedback (APRIL-style)
     → log trace + DAG fingerprint
     → if 0/N close: emit gap report with named missing lemma
```

## 3. Mitigations shipped this session

### 5 new L3 anti-patterns

Minted from the v22-v30 collapse chain:

1. **`gcongr_floor_satisfiable`** — bare `gcongr` closes the goal at the floor; k-fold monotonicity is never "moat-grade by construction"
2. **`missing_import_Hammer_bug`** — `by hammer` without `import Hammer` mis-classified as hammer-OPEN
3. **`paraphrase_of_named_gold_lemma_via_rewrite`** — `simp [X, Y]` rewrites are paraphrase laundering when `X, Y` is the gold lemma's defining simp set
4. **`fun_prop_indirect_leakage`** — `fun_prop`'s @[fun_prop] global set contains the gold lemma
5. **`simp_set_indirect_leakage`** — same as #4, but for @[simp]

### L4 unified catalog

`analytics/public/leanmill/results/v30_layer4_unified_catalog.json`:
- 24 archetypes (20 corpus-mined + 4 new reviewer-spec: ARCH-004 constructor/refine, ARCH-007 Hölder/CS, ARCH-008 measurability/fun_prop, plus ARCH-001..006 mapping into existing v1 keys)
- 50 sample Mathlib proofs (v1 distribution)
- 40 curated exemplars from v3 pattern-mining (5 per ARCH-001..008)
- Cross-maps: L4 → L2 (structural op) + L4 → L3 (anti-pattern flags) + L4 → recommended tactic sequence

### `archetype_classifier.py`

`scripts/public/control/archetype_classifier.py`:
- Heuristic shape-based classifier on Lean goal text
- Input: goal signature + local context
- Output: predicted_L4_archetype, predicted_L2_structural_ops, predicted_L3_anti_pattern_flags, recommended_tactic_sequence
- Smoke-tested on H02/H07/H08 — all classified correctly with appropriate anti-pattern flags

### `route_c_archetype_runner.py` with wired Mode D

`scripts/public/control/route_c_archetype_runner.py`:
- 5 ablation modes: A baseline / B Route C / C structural-only / D archetype-only / Full
- Mode D wired in this session — executes the archetype classifier's argument-free recommended tactics (linarith/nlinarith/gcongr/ring/ring_nf/norm_num/field_simp;ring/measurability/fun_prop)
- Indirect tactics (`exact ?lemma`, `apply ?lemma`, `calc ...`, `induction ...`) are flagged but skipped — those need Route C / LLM wiring
- 3-row sanity (A05/D02/A01): A=1, D=1, B=C=Full=0 — Mode D correctly routed to nlinarith on A05 via ARCH-002 prediction
- 10-row ablation running at time of seam-write (Tasks #39); results land in `v30_ablation_10rows_2026_05_15.json`

### `safe_lean_runner.py`

`scripts/public/control/safe_lean_runner.py`:
- Resource-bounded Lean runner per operator CPU/memory-safety mandate
- max_workers=2, nice +10, process-group kill on timeout, load-aware throttling at N_CORES * 1.5

## 4. Why the bound is structural (Munger compression test)

Every claim that survives this seam must pass: *"What would still be true if an adversary reran this with current LeanHammer, no oracle proof lines, fixed budgets, structural proof deduplication, and replay from scratch?"*

For natural Mathlib-style goals, the moat-grade intersection (goal true ∩ B0+ fails ∩ B1 fails ∩ no Mathlib direct ∩ no Mathlib paraphrase ∩ proof DAG-distinct ∩ 0 manual edits) is **empirically bounded at 0-1 per session-day**, because Mathlib + reasonable tactics cover that goal class. The escape routes are:

- (a) external-library `unverified stub`s / PR drafts (research-grade, multi-session)
- (b) NS Track B genuine open math (deep)
- (c) Cross-formalization imports
- (d) k-fold compositions external library hasn't packaged AND `gcongr` doesn't handle (vanishingly small set)

The META infrastructure built this session passes the Munger compression test. The 6 originally-claimed v30 moat-grade closures DID NOT — Meta-Darwin killed 4, weakened 1, left 1 partial-survivor (H07 only if `gcongr` is excluded from baseline; killed if included).

## 5. Consumer feedback contract

| Consumer | What it pulls | What it returns |
|---|---|---|
| `gp230_solve.py` harness CLI | L1 dispatch rule + L2 op classifier + L4 archetype + L3 anti-pattern guard | Per-row trace + closure verdict + gap report |
| External Meta-Darwin agent | L3 anti-pattern catalog + DAG fingerprint of claimed closure | Kill / weaken / survive verdict |
| `archetype_classifier.py` | L4 unified catalog + L2 op map + L3 flag map | (archetype, ops, flags, tactic_sequence) tuple |
| `route_c_archetype_runner.py` | archetype_classifier output | 5-mode ablation trace per row |
| v31+ session start | This seam + v31 handover doc | "where we are, what's next, what's binding" |

## 6. What this seam is NOT

- It is NOT a claim that the harness closes more rows than the bare baseline. The 10-row ablation results (pending at time-of-write) will determine that empirically.
- It is NOT a substitute for Mathlib / LeanPremise / LeanHammer. It is a routing / discipline layer that sits ABOVE the substrate.
- It is NOT specific to Lean. The 4-catalog structure transfers to any substrate where: (a) goals can be classified by shape, (b) substrate has primitive operations, (c) closures can be audited DAG-fingerprint-style.

## 7. Route C exploration notes — DEMOTED 2026-05-15

> **DEMOTION NOTICE (2026-05-15, post-Meta-Darwin kill + ablation data + operator false-negative review):**
>
> §7 was originally written as "architecture" but was killed by external Meta-Darwin idea-killer dispatch (kill_report_v1, 2026-05-15) with overall verdict ARCHITECTURE-IS-FACADE. The 10-row ablation completed concurrently produced consistent data: Mode D archetype routing contributed 0 distinct closures over Mode A baseline (3/10 in both, SAME tactics on all 3).
>
> **False-negative review of the Meta-Darwin kill** identified 2 partial false negatives:
> - **#4 Layer 2c "positive framing"**: Meta-Darwin didn't engage with the operator-framed *semantic masking* refinement that removes names from prompts entirely. That's a real architectural mitigation Meta-Darwin missed. Severity reduced 8→5-6.
> - **#7 "paraphrase-free claim"**: Meta-Darwin used cosine similarity (noisy — conflates topic and statement). The right test is **DAG fingerprint match**, not cosine. Severity reduced 10→6-7.
>
> **Surviving kills (severity ≥7):** #1 Layer 1 non-disjoint, #2 Layer 2a self-falsification (25% accuracy in same seam), #3 Layer 2b crude grep = white-bear-relabeled, #10 unfalsifiability move (no pre-registered falsifier).
>
> **What's salvageable** (carried forward to GP-235 DAG fingerprint primitive seam):
> - Semantic masking (operator's framing) — Layer 2c-style prompt with no names
> - Deterministic termination guard (max-2-rounds, fingerprint-diff exit)
> - Layer 5 gap-report concept — WEAK survivor, only useful if DAG fingerprint primitive ships first
> - 5 new L3 anti-patterns — observations, orthogonal to architecture
> - L4 unified catalog — infrastructure (with honest 25% top-1 caveat)
>
> **What's dead:**
> - Layer 2a operation-type taxonomy pick (25% accuracy)
> - Layer 2b content-axis gap retrieval (degenerate crude version is white-bear-relabeled)
> - "Route C runs ONLY on escape-route targets" framing (unfalsifiability move)
> - "PR drafts are paraphrase-free" claim (Meta-Darwin #7 partially survives — DAG fingerprint test still pending)
> - Mode D heuristic archetype routing as proposed (ablation: 0 distinct signal)
>
> **Replaced by:** [[GP-235_dag_fingerprint_primitive_seam]] (TBW) — DAG fingerprint becomes the decisive discriminator, replacing operation-type taxonomy.
>
> The below §§7.1-7.7 are retained as **exploration notes** documenting the failure modes that led to the revised architecture. Do not cite §§7.3-7.4 as architecture in v31+ work.

---

### 7. Route C exploration notes (original text, retained for failure-mode provenance) (5-layer, target-class-aware)

### 7.1 The misread to reject

The naive read of "Route C must wire LLM-generative tactics" is *"prompt the LLM for tactics that close the goal without triggering L3 guards."* This is **laundering by definition** — anything that bypasses the guards is what the guards exist to catch. The guards are correct; they are not the obstacle.

### 7.2 The structural diagnosis

For "natural Mathlib-style" goals, the moat-grade intersection (truth ∩ B0+ fails ∩ B1 fails ∩ no Mathlib direct ∩ no Mathlib paraphrase ∩ DAG-distinct ∩ 0 manual edits) is **empirically empty** (0-1/session bound, GP-233 §4). Route C cannot close this intersection because *the room itself is empty*. The L3 guards correctly enforce the emptiness.

The intersection is NOT empty for these escape-route target classes:

| Class | Why intersection is non-empty | v31 target source |
|---|---|---|
| (a) external-library PR drafts / `unverified stub`s | Closure doesn't exist yet → no paraphrase exists | `PR_1b_minkowski_rate` (Lieb-Loss Theorem 2.4 stub, ~120 LoC); Carleson sandbox's own open stubs |
| (c) Cross-formalization imports | Lemma exists in Isabelle / Coq / Metamath but NOT in Mathlib | Isabelle's `Real_Analysis.Holder` theorems not yet ported (long-horizon) |
| (d) k-fold compositions Mathlib hasn't packaged AND `gcongr` can't handle | Vanishingly small but guard-clean | Specific weighted estimate aggregations |
| (e) NS Track B genuine open math | No Mathlib reference exists | Specific Liouvillian-Σ pressure-AP residuals |

**Route C runs ONLY on these target classes. The v30 / 10-row ablation rows are the WRONG target class for measuring Route C's value.** Including them is a target-class mismatch, not a Route C failure.

### 7.3 The 5-layer Route C architecture

```
Layer 1 — TARGET FILTER (pre-LLM)
  Pre-classify each row by escape route. If row is "natural Mathlib"
  (no escape route applies), emit a "Mathlib coverage" report and SKIP
  Route C. Do not waste LLM calls on guard-empty rooms.

Layer 2 — INTERMEDIATE-LEMMA PROPOSAL (LLM dispatch)
  LLM is asked to propose a NOVEL intermediate lemma L whose statement
  is NOT a paraphrase of any Mathlib named lemma in the relevant
  namespaces. Prompt is a NEGATIVE DICTIONARY: "do not propose L
  whose statement matches any of {grep'd lemma index for goal's
  namespace}". See §7.4 for the prompt template.

Layer 3 — RECURSIVE L3 GUARDS (per-have-step)
  Apply L3 anti-pattern classifier at EVERY `have h : T := by P` step,
  not just the final closing tactic. If T's predicted archetype is
  ARCH-001_direct_library_chain AND grep-check shows T matches an
  existing Mathlib lemma statement (modulo alpha-renaming), REJECT and
  re-prompt LLM with the matched-lemma name added to the negative
  dictionary.

Layer 4 — DAG FINGERPRINT DEDUPLICATION
  Compute the proof DAG fingerprint (tactic-family sequence + cited
  constants + skeleton kind + normalization path) of the candidate
  proof. Cross-reference against fingerprints of Mathlib proofs of
  structurally-related lemmas (indexed offline). If fingerprint
  matches → REJECT.

Layer 5 — GAP-REPORT FALLBACK
  If all candidates rejected after N=3 re-prompt rounds, emit a
  STRUCTURED REPORT: "to close goal G, the missing lemma is L with
  statement S, predicted archetype A, estimated novelty score N."
  THIS REPORT IS THE DELIVERABLE for Mathlib-contribution targets —
  not the closure. The closure happens in a follow-up session where
  L is added to Mathlib by human-LLM collaboration.
```

### 7.4 The Layer 2 problem — neither negative-dictionary nor pure forward-generative works

**The trap (operator-surfaced 2026-05-15):** the naive Layer 2 prompt "do not propose any of these {N lemmas}" hits the *"do not think of a white bear"* problem. LLM attention weights the negative tokens, *increasing* the likelihood of paraphrase. Also Mathlib has ~150K named lemmas; can't fit the relevant subset in context.

**The competing trap:** pure forward-generative + Layer 3 discriminator also fails. The LLM's prior IS Mathlib. Its "forward mathematical state" generation defaults to regenerating Mathlib content. Layer 3 rejects → re-prompt → LLM regenerates the same content (prior hasn't moved) → generate-reject-regenerate loop without convergence.

**The architectural fix (semantic masking + DAG-fingerprint termination):**

This is the operator's "black box" framing (2026-05-15) augmented with a deterministic termination guard against syntactic-variant oscillation. The earlier decompositional draft (Layer 2b "retrieve gap") is retired — its content-axis extraction step was the architecture's hardest and most-fragile step, and semantic masking eliminates it entirely.

```
Layer 2a — DECOMPOSE (cheap LLM call OR heuristic)
  Prompt: "What mathematical OPERATION TYPE does goal G need?"
  Output: forced pick from L2 structural-content catalog
  (broad_01_estimate_chain / core_03_decomposition / ...).
  → LLM operates in a small fixed taxonomy, not lemma space.
  → No "white bear" because no negative content in prompt.

Layer 2c — SEMANTIC MASKING (LLM call, operator-framed)
  Prompt: show the LLM ONLY:
    - The local hypotheses (axioms)
    - The required ending state (goal G)
    - The operation type from 2a
  Ask: "Generate the single intermediate mathematical state (lemma L)
  that represents the hardest logical leap between the hypotheses and
  the goal. Output ONLY the formal Lean statement of L."
  → LLM is purely forward-generating. No negative dictionary, no
    "covered" set, no named-lemma list, no anchors of any kind.
  → The LLM's prior cannot be biased by negative tokens because there
    are no negative tokens.

Layer 3 — DISCRIMINATOR (deterministic, internal-only)
  Grep L's statement against Mathlib lemma index (alpha-rename-tolerant).
  Compute the proof DAG fingerprint of L's stated proof (or of L's
  closest Mathlib analog if grep hits).
  Internal verdicts (NEVER returned to LLM):
    - NOVEL: L's statement doesn't match any named Mathlib lemma AND
      L's DAG fingerprint isn't in the Mathlib proof DAG library.
    - TRIVIAL: L matches a named Mathlib lemma X modulo alpha-rename, OR
      L's DAG fingerprint matches an existing proof DAG.
    - PARTIAL: L is novel but adjacent to a Mathlib lemma's neighborhood.
  X's name (when TRIVIAL) is logged but NEVER appears in any subsequent
  LLM prompt.

Layer 3.5 — POSITIVE-FRAMED FEEDBACK (max 2 re-prompts)
  If TRIVIAL: re-prompt LLM with operator-framed positive signal:
    "Your proposal closes the gap via a state that's already discharged
     by a single library application from the listed hypotheses.
     Propose an intermediate state that requires a different structural
     pathway — one that cannot be closed by a single named lemma."
  → No white bear (no name mentioned, no "do not propose").
  → Positive direction ("different pathway") rather than negative
    constraint ("not paraphrase of X").

Layer 3.5 TERMINATION GUARD (deterministic, prevents oscillation)
  After 2 consecutive TRIVIAL verdicts:
    - Compare the 2 candidates' DAG fingerprints.
    - SAME fingerprint twice → LLM is oscillating on syntactic variants
      → exit IMMEDIATELY to Layer 5 gap report.
    - DIFFERENT fingerprints but both TRIVIAL → LLM is exploring the
      Mathlib-adjacent neighborhood, not the genuinely-open space →
      exit to Layer 5 with the union of both fingerprints as
      "candidate paths via existing Mathlib" (those are the audit-grade
      evidence that the target is in Mathlib's reach).
  → Convergence is now FORMAL: at most 3 LLM calls per target (1 initial
    + 2 feedback), guaranteed termination.

Layer 5 — GAP REPORT (default deliverable)
  Structured output:
    {
      target_goal: G,
      operation_type: T (from 2a),
      candidate_pathways: [DAG fingerprints from 2c attempts],
      verdict: NOVEL_FOUND | TRIVIAL_VIA_MATHLIB | PARTIAL_NEEDS_REVIEW,
      named_missing_lemma_if_novel: L (if Layer 3 returned NOVEL),
      audit_evidence: {trivial_matches: [X, Y, ...], fingerprints: [...]}
    }
```

**Why semantic masking + termination guard handles everything:**

| Failure mode | Mitigation |
|---|---|
| "White bear" attention bias | No negative content anywhere in any LLM prompt. The LLM never sees names of existing lemmas, never sees a "covered" set, never sees a "do not" list. |
| Generate-reject-regenerate non-convergence | Termination guard exits after 2 consecutive TRIVIAL verdicts. At most 3 LLM calls per target — formal bound, not informal monotonicity argument. |
| LLM prior = Mathlib | Layer 2c gives the LLM ONLY hypotheses + goal + operation type — the prompt is structurally orthogonal to "name a Mathlib lemma" because no names are anywhere. |
| Syntactic variant oscillation (semantic masking's own weakness) | Termination guard's "SAME fingerprint twice" condition catches this directly. |
| Hallucinated near-matches that pass string comparison but fail spirit | Layer 3 uses alpha-rename-tolerant grep + DAG fingerprint, not raw string match. |

**Honest limitations remaining:**

1. **Layer 2a operation-type accuracy.** Current heuristic classifier is 25% top-1 / 42.5% top-3 on v3 ground truth. If 2a picks the wrong operation, 2c forward-generates under wrong structural prior. Mitigation: 2a uses top-K and 2c is asked for K parallel proposals, one per top-K operation.
2. **Layer 3 DAG fingerprint library is not yet built.** For v31 first pass, Layer 3 uses only grep against Mathlib's lemma-name index (catches gross paraphrases) without DAG fingerprint. DAG library construction is its own work item.
3. **"Different structural pathway" framing in 3.5 is still subjective from the LLM's side.** The LLM might respond with a syntactic variant of the same content. The deterministic termination guard catches this, but it means many targets will exit to Layer 5 gap report — not be closed.
4. **Cost.** ≤3 LLM calls per target × 30 targets = 90 cheap-tier calls @ ~$0.01 = ~$0.90 per ablation pass. Tractable.
5. **The semantic-masking convergence is termination-bounded, not success-bounded.** The architecture guarantees the loop ends; it does NOT guarantee the LLM ever produces a NOVEL output. For natural Mathlib rows, the expected outcome is TRIVIAL → Layer 5 gap report (which is correct — those rows ARE in Mathlib's reach). For escape-route rows, the empirical question is whether the LLM can produce NOVEL output at all.

**What's NOT being claimed (Munger compression):**

- This architecture does NOT guarantee any closures. It guarantees termination + audit-grade evidence.
- The "different structural pathway" 3.5 framing is a heuristic, not a proof of LLM behavior.
- Layer 2a's wrong-operation-type failure can cascade — top-K mitigation is partial.
- Cost estimates assume LLM doesn't recursively dispatch other LLMs (which the harness will not do).

**Why this handles both failure modes:**

| Failure mode | Mitigation |
|---|---|
| "White bear" attention bias | Negative content never appears in any LLM prompt. Layer 2c sees only POSITIVE content descriptors ("covered" and "needed"). |
| Generate-reject-regenerate non-convergence | Layer 3.5's feedback is reframed as POSITIVE coverage growth, not "do not propose X". Monotone shrinking of uncovered space guarantees termination. |
| LLM prior = Mathlib | Layer 2a forces a fixed taxonomy choice, not free-form lemma proposal. Layer 2b deterministically extracts the gap. Layer 2c's prompt structure orthogonalizes from the prior. |
| Best-of-1 unreliability | Layer 2d K=5..10 amortizes single-call variance. |

**Honest limitations (open in v31):**

1. **Layer 2b's gap-extraction quality is the hardest step.** Decomposing lemma content into orthogonal "covered/uncovered" axes requires a real content-axis taxonomy that doesn't yet exist. First pass for v31: crude grep on type signatures + named-constant frequency in conclusion. Refining 2b is its own research thread.
2. **Layer 2c may still paraphrase** if the LLM's prior is overwhelmingly anchored on an existing Mathlib lemma even given the forward framing. For genuinely-open targets (PR drafts, NS Track B) the lemma doesn't exist yet so the LLM has to construct. For natural Mathlib rows Layer 1 should have routed away from Route C entirely.
3. **Convergence proof is informal.** Layer 3.5 monotonicity argument assumes Layer 2b's gap-extraction shrinks deterministically with each added covered_content item. If 2b's decomposition is non-monotone (e.g., adding a covered item REVEALS a new uncovered axis), 3.5 can loop. Real convergence depends on 2b's quality.
4. **Cost.** ~3-4 LLM calls per target × K=5 best-of-N = 15-20 cheap-tier calls per target. At ~$0.01/call → ~$0.20/target. 30-target benchmark = $6. Tractable for occasional runs, expensive for daily.

**What gets built for v31 (concrete, cheap):**

- Layer 2a + 2c only (skip 2b sophistication; use simple "list of Mathlib lemma NAMES in goal's namespace" as the covered set; let LLM infer the gap from name semantics).
- K=3 best-of-N (cheap probe; raise if rejection rate >70%).
- Layer 3.5 with max 2 feedback rounds; early exit if post-feedback rejection rate doesn't drop.
- **Honest Layer 5 gap report as default deliverable.** Closures are bonus, not pass-gate. The harness ships value via gap reports on natural Mathlib rows AND via closures on escape-route rows.

**What's NOT being claimed:**

- This is not a solved Layer 2. Layer 2b's content-axis decomposition is the open research question.
- The convergence argument is informal, not proved.
- Cost may scale poorly with target complexity.
- For v31, success criterion is "Layer 5 gap reports are high-quality and substantively useful for Mathlib-PR-draft work" — NOT "Mode B / Full closes ≥10 escape-route rows."

### 7.5 Pass-gate for v31 ablation row selection

The v31 ablation row set MUST include AT LEAST:
- **5 escape-route rows** (Class (a)/(c)/(d)/(e) per §7.2) — Route C target class
- **5 natural Mathlib rows** (the 10-row set already running) — control set, Route C expected to skip these via Layer 1

Mode B / Mode Full closure rates are then measured **per target class**, not aggregated. If Route C closes ≥1 escape-route row honestly (full L1..L4 guards pass) and skips all natural Mathlib rows via Layer 1, the harness has shipped the cure.

### 7.6 Open questions for v31

1. **Mode A vs Mode D** on natural Mathlib rows — pending the 10-row ablation. (Will likely show structural ceiling per §7.2.)
2. **Mode B / Mode Full on escape-route rows** — requires Layer 1 row classifier, Layer 2 negative-dictionary prompt, Layer 3 recursive guards. Operator authorization needed for `codex_rd` invocation outside prediction markets.
3. **Mathlib lemma-statement grep index** for Layer 3's "matches existing Mathlib lemma" check — needs offline construction (one-time ~30 min on the v4.29.0 sandbox).
4. **DAG fingerprint library** for Layer 4 — extend `v30_dag_fingerprinter.py` to index Mathlib proofs (not just the harness's own outputs).
5. **Top-K classifier accuracy** on v3 ground truth — current heuristic: top-1 25%, top-3 42.5%, far below the ≥80% pass-gate. Either (a) refine rules with v3 exemplars as training signal, or (b) replace heuristic with learned classifier. Tracked separately; not blocking Route C.

### 7.7 What this seam now claims (after §7 addition)

- The framework correctly identifies WHY natural Mathlib rows are guard-empty.
- The 5-layer Route C architecture (§7.3) ships the cure for non-empty target classes.
- The negative-dictionary prompt (§7.4) is the concrete operator-pending wiring.
- The v31 ablation row set (§7.5) must change to include escape-route rows.
- The framework no longer "guards an empty room" — it routes empty-room targets to a gap-report path (Layer 5) and non-empty-room targets to the full 5-layer pipeline.

## 8. Related

- [[feedback_gp225_4_catalog_meta_solver_framework_2026_05_15]] — operator memory of the META reframe (decisive rule)
- [[feedback_gp225_munger_inversion_premortem_2026_05_15]] — GPT-5.5-mediated premortem that anticipated this collapse
- [[feedback_be_meta_darwin_to_self_2026_05_14]] — in-artifact audit mandate (necessary but insufficient; external dispatch + fair baseline are the corrective)
- [[GP-225_lean_premise_selection_carleson_substrate]] — the substrate where the META was crystallized
- [[GP-234_closure_claim_discipline_linter_seam]] — Tier-1 + Tier-2 linters that operationalize parts of L3
- `epistemic_hygiene_bundle` (one-shot 2026-05-15 ship; substrate-agnostic export of L1 (filtered) + L3 (filtered) + meta rules for cross-domain transfer, CONOP / military planning use case) — packaged as `epistemic_hygiene_bundle.zip`, shipped externally and removed from the tree; regenerate from native `org/` catalogs if needed for another recipient

## 9. 2026-05-17 substrate + benchmark-validity correction (persistent REPL; leak-tight extraction)

Three decisive corrections, externally validated (cold xhigh GPT-5.5 epd-41227f9ea30e, epd-242f7c0e78c5):

1. **Substrate was the bottleneck, not the idea.** The probe substrate re-ran `import Mathlib` (~40s) per probe (~the entire cost of a ~3h run). Fixed by a persistent leanprover-community/repl process (vendored `vendor/lean_repl`, pinned v4.29.0): import paid once, ~0.07s/probe (~300–4000×). `lean_persistent.py` (proof-state stepping) + hardened `lean_repl.check_lean` (fixed-path race) are the shared in-loop primitives autoresearch also inherits. See [[pointfix-treadmill-on-wrong-primitive]].

2. **`#print axioms` does NOT catch corpus leakage.** Leak audit measured **50% of 30 prior "certified-genuine" proofs contaminated** (single-lemma rename / axiom-smuggle / self-reference) under bare `import Mathlib`. Pre-2026-05-17 closure tallies are validity-SUSPECT. The v30 "decisive" experiment was non-probative (one-shot arithmetic, the regime predicted to give proof-state search zero edge). See [[print-axioms-does-not-catch-corpus-leakage]].

3. **Correct benchmark = Lean-elaborator file-prefix replay with in-place proof-hole.** Per module: load only F's direct imports, replay command-by-command via Lean's real frontend, checkpoint full `Command.State` before each candidate, pose by restoring + opening the original declaration body as a proof hole (T not yet registered), audit proof-term constants ⊆ {transitive imports of F} ∪ {same-file pre-target decls}. Leak boundary = direct-imports + same-file-prefix (full-Mathlib+forbid-descendants is strictly weaker). Reuse path confirmed: the vendored repl's File mode (`{"path":...,"allTactics":true}`) + `sorries[].proofState` + `usedConstants` already implement this without LeanDojo or a hand-rolled tracer. Builds `mcb` benchmark; unblocks the genuinely-probative stateful-vs-baseline decisive experiment. Closes §7.6-open-Q3/Q4 (Mathlib lemma index / DAG fingerprint) via the constant-audit instead.

Status: persistent substrate shipped + validated; leak audit done; extractor being rebuilt to the §9.3 algorithm (regex variant retired); decisive experiment pending the leak-tight corpus.
