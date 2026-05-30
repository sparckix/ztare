# GP-235 — Proof-Route Fingerprint Primitive Validation

> **Seam metadata** · `seam_id:` GP-235 · `track:` reflexive · `status:` ACTIVE - primitive-validation seam, narrowed scope per exter · `last_updated:` 2026-05-15


**Status:** ACTIVE — primitive-validation seam, narrowed scope per external review 2026-05-15
**Cabinet:** `reflexive/` (decisive primitive for proof-route deduplication; NOT theorem-novelty certification)
**Authored:** 2026-05-15 (un-dropped + revised same day)

> **REVISION HISTORY:**
>
> **v0 (initial draft):** "DAG Fingerprint Primitive Validation" — over-broad claim (theorem novelty).
> **v0.5 (post-operator Vulnerabilities A/B/C):** added train/test split, sorry-sparsity fix concept, type-signature enrichment.
> **v0.6 (post-Meta-Darwin v2 over-kill):** briefly DROPPED based on Meta-Darwin v2 criterion 10 ("wrong primitive — discriminator, not generator").
> **v1 (post external-reviewer un-drop, current):** UN-DROPPED. External reviewer correctly identified that Meta-Darwin v2 #10 was a false-negative-on-the-primitive — the primitive itself is right; its CLAIMED SCOPE was too broad. Primitive renamed from "DAG Fingerprint" to **"Proof-Route Fingerprint"** to prevent theorem-novelty overclaim. Four specific edits applied: (1) rename primitive, (2) split statement-novelty from proof-route-novelty into separate metrics, (3) add cheap-baseline ablation dominance test, (4) fix §4.4 to fingerprint compiled closures not goal statements.

> **What this primitive IS designed to do (narrowed claim, 2026-05-15):**
>
> - Proof-route deduplication: distinguish proofs that follow the SAME structural route from proofs that follow DIFFERENT routes.
> - Proof-diversity scoring: quantify how distinct a candidate proof is from existing Mathlib proofs of related lemmas.
> - Paraphrase-laundering audit support: when an LLM proposes a closure, this primitive can flag "your proof has the same DAG fingerprint as <existing Mathlib proof>".
> - Route C closure audit (post-hoc only): part of a multi-component audit pipeline, NOT the decisive piece.
>
> **What this primitive is NOT designed to do:**
>
> - Theorem-novelty certification — that requires a STATEMENT-similarity primitive (separate, not in this seam).
> - Solver architecture foundation by itself.
> - Proof search policy.
> - Replace LLM-mediated generation (Route C still needs a generation primitive; this seam is orthogonal).
>
> **Why the rename matters:** two unrelated lemmas can have identical proof routes (`by nlinarith` closes both `2+3=5` and `17*19=323`). Without statement-similarity, "same proof DAG" does NOT mean "same theorem." The previous "DAG fingerprint as novelty detector" framing collapsed these.

The original §2-§7 below is REVISED per the 4 specific edits (see §0 below for change log, §4.5 for new ablation requirement).

---

## 0. Change log (v0 → v1)

| Edit | Section | Change |
|---|---|---|
| 1 — Rename primitive | Throughout | "DAG fingerprint" → "proof-route fingerprint" |
| 2 — Split novelty axes | §2, §4, new §4.5 | Two separate metrics: `statement_similarity` (independent, not built here) + `proof_route_similarity` (built here). Verdict labels expanded from {NOVEL, TRIVIAL} to {STATEMENT_DUPLICATE, PROOF_ROUTE_DUPLICATE, BOTH_DUPLICATE, PROOF_STYLE_ONLY, STATEMENT_NEAR_BUT_ROUTE_DIFFERENT, NOVEL_STATEMENT_AND_ROUTE, UNCLOSED}. |
| 3 — Ablation dominance | New §4.5 | Pre-register: full fingerprint must beat each cheap baseline by F1 ≥ 0.03 on held-out test set. Baselines: statement-only / constants-only / tactic-only / namespace+head / normalization-only / skeleton-only. |
| 4 — Fix §4.4 sorry-sparsity | §4.4 | Fingerprint only COMPILED candidate closures, never bare sorry stubs. UNCLOSED is its own verdict for non-compiling candidates. N raised from 10 to 30 (10 natural Mathlib + 10 PR-stub + 10 generated escape-route). |
| (also) Schema rank | §2 | Split into `surface_fingerprint` (tactic-script AST) and `kernel_fingerprint` (elaborated proof term constants + typeclass instances). Combined only after ablation validates each adds distinct signal. |
**Trigger:** GP-233 §7 was killed by external Meta-Darwin (ARCHITECTURE-IS-FACADE verdict) + ablation data (Mode D = Mode A, zero distinct signal). The failure-mode analysis identified `primitive_before_architecture_gate` violation: §7 architected on top of Layer 2b (gap retrieval) which was admittedly "crude first pass / research thread." Before any further Route C architecture is written, the decisive primitive (DAG fingerprint) must be **independently validated** with pre-registered pass-gates.

## 1. What this seam is and is NOT

**IS:** a primitive-validation seam. It defines a single, concrete, measurable thing — DAG fingerprint of a Lean proof — and validates whether that thing is actually a useful discriminator. The deliverable is a NUMBER (or set of numbers) measured against pre-registered pass-gates.

**IS NOT:** an architecture seam. There is no "Layer 1 / Layer 2 / Layer 3" structure here. No claim about Route C, no claim about gap reports, no claim about LLM dispatch. If the primitive validates, a SEPARATE seam (GP-236, not written yet) will propose how to use it architecturally. If the primitive fails validation, the DAG-fingerprint approach is dropped and no follow-up seam is written.

This separation is enforced by the `primitive_before_architecture_gate` pattern (proposed addition to `org/patterns/`).

## 2. Proof-route fingerprint — concrete schema (REVISED v1: surface vs kernel split)

The fingerprint is split into two representations that capture different aspects. Combined-fingerprint usage requires ablation-passing (§4.5) — until then, they are reported separately.

### 2A. Surface fingerprint (tactic-script AST view)

For a Lean proof term `t : T` extracted from source syntax, the surface fingerprint is a 4-tuple:

```
fingerprint(t) := (
  tactic_family_sequence:    [list of tactic-family tags, in order]
  cited_constants:           [sorted multiset of constant names used in t]
  skeleton_kind:             one of {direct, calc, induction, refine, term, sorry}
  normalization_path:        [list of normalization tactics used, in order]
)
```

Where:
- **tactic_family_sequence**: each tactic in `t` is mapped to its family (e.g. `linarith` / `nlinarith` / `polyrith` → "linear_arith"; `simp` / `simp_all` / `simpa` → "simp"; `rw` / `rewrite` → "rewrite"; etc.). Sequence preserved.
- **cited_constants**: every named constant `c` such that `c` appears explicitly in `t`'s tactic arguments (e.g. `simp [foo, bar]` cites `{foo, bar}`). Multiset (with multiplicities), sorted lexicographically.
- **skeleton_kind**: pattern-matched on the top-level structure of `t`. `by exact e` → "direct"; `by calc ...` → "calc"; `by induction n with | ... => ...` → "induction"; `by refine ⟨?_, ?_⟩; ...` → "refine"; closed term `t := ...` → "term"; contains `sorry` → "sorry".
- **normalization_path**: subset of tactic_family_sequence restricted to normalization tactics (`ring` / `ring_nf` / `norm_num` / `field_simp` / `push_cast`). Preserved order.

### 2B. Kernel fingerprint (elaborated proof term view, NEW v1)

Extracted from Lean's elaborated proof term (not source syntax):

```
kernel_fingerprint(t) := (
  constants_used:       sorted multiset of fully-qualified constant names in t's expansion
  typeclass_instances:  sorted multiset of instances resolved during elaboration
  dependency_set:       sorted set of theorem names cited transitively (depth ≤ 2)
  target_type_head:     head symbol of T (the theorem's conclusion type, e.g. Eq / LE.le / Continuous)
)
```

Why separate from 2A: surface tactic-script (`simp [foo, bar]`) and kernel proof term (which actually used `foo` to rewrite which subterm) are different signals. A `simp [foo, bar]` that fires only `bar` looks identical at surface but different at kernel.

### 2C. Distance metric — separate per representation, NOT combined until §4.5 passes

**Distance metric** between two fingerprints `f, g` (per representation):

```
d(f, g) := w1 · LevDist(tactic_family_seq_f, tactic_family_seq_g)
        + w2 · JaccardDistance(cited_constants_f, cited_constants_g)
        + w3 · (0 if skeleton_kind_f == skeleton_kind_g else 1)
        + w4 · LevDist(normalization_path_f, normalization_path_g)
```

With initial weights `w1=0.4, w2=0.3, w3=0.2, w4=0.1`. Weights are themselves subject to validation (see §4).

## 3. How to build the Mathlib index (one-time engineering task)

For each lemma `L` in the v4.29.0 Mathlib + LeanHammer sandbox:
1. Extract `L`'s proof term (the body after `:= by`).
2. Parse the proof term into a tactic-script AST (Lean 4 `Lean.Syntax` parser, available in the sandbox).
3. Compute `fingerprint(L)` per §2.
4. Store `(L_name, L_namespace, fingerprint)` in a JSON index.

**Estimated cost:** ~30 min on the sandbox. Mathlib has ~150K named lemmas; per-lemma fingerprint ~5ms with parsed AST → ~12 min compute + I/O overhead. Index file ~50 MB.

**Implementation file:** `scripts/public/control/build_mathlib_dag_fingerprint_index.py` (to be written; ~200 LoC estimated).

## 4. Validation experiments (pre-registered pass-gates)

> **Methodological discipline added 2026-05-15 after operator-surfaced vulnerabilities (A/B/C below):**
>
> **Vulnerability A — Weight-tuning trap (data leakage).** Earlier draft of §4.1/§4.2 said "tune weights or revise schema" using the same pairs that validate the pass-gate. That's classic train-on-test leakage — overfitting to the held set, not validating the metric. Fix: split data into TRAIN (weight-tuning) and TEST (pass-gate validation), labeled and locked separately.
>
> **Vulnerability B — Sorry sparsity (§4.4).** A `sorry` stub has empty fingerprint by construction (no proof DAG). Comparing it to dense Mathlib proofs gives artificially large distance — false NOVEL verdict. Fix: §4.4 fingerprints LLM-CANDIDATE-CLOSURES of sorries, never the sorry stub itself.
>
> **Vulnerability C — Syntactic aliasing.** Two mathematically-distinct theorems (e.g. Real vs Complex versions of same syntactic proof) can have identical fingerprints because cited_constants captures tactic-argument names only. Fix: cited_constants must include TYPE SIGNATURES / NAMESPACES of the carriers, not just argument names.

### 4.0 Schema revision (per Vulnerability C)

The `cited_constants` field in §2 is REVISED to:

```
cited_constants: sorted multiset of (constant_name, fully_qualified_namespace, top_level_type)
```

Where:
- `constant_name`: as before
- `fully_qualified_namespace`: e.g. `Real.add_comm` → `Real`, `MeasureTheory.lintegral_mul_le_Lp_mul_Lq` → `MeasureTheory`
- `top_level_type`: the head symbol of the lemma's conclusion type — e.g. `Eq`, `LE.le`, `Continuous`, `Measurable`. Extracted from Lean's elaborated AST, not surface syntax.

This makes the metric distinguish `Real.foo` from `Complex.foo` even if both are cited under identical tactic chains.

### 4.1 Intra-cluster distance — split TRAIN / TEST (per Vulnerability A)

**Hypothesis:** known near-duplicate lemmas in Mathlib have close DAG fingerprints.

**Protocol:**

1. **TRAIN set (N=30):** hand-curate 30 pairs of known-near-duplicate Mathlib lemmas (e.g. `Nat.add_comm` vs `Nat.add_comm'`; `Real.add_comm` vs same lemma in different namespace presentation). Sample pairs from `Algebra/`, `Analysis/`, `MeasureTheory/`, `Topology/` — 7-8 per namespace.
2. **Tune `(w1, w2, w3, w4)` on TRAIN** via grid search to minimize mean intra-cluster distance. Lock the weights. Commit them to git with timestamp.
3. **TEST set (N=50):** hand-curate 50 DIFFERENT pairs, sampled by the same protocol but using lemma pairs NOT in TRAIN. Operator + external review labels the test set independently to remove author bias.
4. **Pass gate (pre-registered, on TEST only):** ≥80% of TEST pairs have distance < 0.30.

**If TRAIN tuning cannot achieve mean intra-distance < 0.30 even with optimized weights:** schema is too coarse — primitive fails.
**If TRAIN passes but TEST does not:** overfitting confirmed — primitive fails.

### 4.2 Inter-cluster distance — TEST-set only (per Vulnerability A)

**Hypothesis:** structurally distinct Mathlib lemmas have large fingerprint distances.

**Protocol:** with weights locked from §4.1 TRAIN, compute distances on 50 cross-namespace lemma pairs in the §4.1 TEST set (or a separate held set).

**Pass gate:** ≥80% of pairs have distance > 0.60.

**If FAIL:** metric collapses topologically — primitive fails.

### 4.3 ε threshold determination

**Hypothesis:** there exists an ε such that fingerprint distance < ε correlates with "these are paraphrases or near-duplicates" with ≥80% precision and ≥60% recall.

**Test:** hand-label 100 lemma pairs as {paraphrase, related, unrelated}. Compute fingerprint distance for each. Find ε that maximizes F1.

**Pass gate:** F1 at optimal ε ≥ 0.70. If max F1 < 0.70, the distance metric is not discriminating well enough for the discriminator role.

**If FAIL:** primitive's discriminator value is insufficient. Either revise schema or drop the approach.

### 4.4 Compiled-closure proof-route coverage (REVISED v1 — fixes sorry-sparsity)

> **Vulnerability B fix (sorry sparsity):** earlier draft fingerprinted bare sorry stubs. A sorry stub has empty proof DAG by construction; comparing to dense Mathlib proofs gives artificially large distance → false NOVEL verdict. **Fix:** fingerprint only COMPILED candidate closures. The bare sorry stub gets verdict UNCLOSED, not NOVEL.

**Hypothesis:** for candidate sorries with at least one compiling proof attempt, the proof-route fingerprint distinguishes proofs whose route is duplicated in Mathlib from proofs whose route is structurally distinct.

**Protocol (REVISED — N raised from 10 to 30):**

For each of 30 candidate sorries:
- 10 natural Mathlib-style rows (from `V30Rows/Row_v30_*.lean`)
- 10 PR/stub rows (from `/tmp/open_sorries_v31_candidates.json` Tier 1+2)
- 10 generated escape-route rows (Carleson sandbox open stubs, Lorentz seminorm helpers)

1. Attempt closure with baseline tactic-cascade (B0+: linarith / nlinarith / ring / ring_nf / simp / aesop / norm_num / polyrith / field_simp / positivity / decide / gcongr / measurability / fun_prop). Per-tactic budget 60s.
2. If any tactic closes: compute `surface_fingerprint` AND `kernel_fingerprint` of the closure.
3. Compute `statement_similarity` independently (using a SEPARATE statement-similarity metric — see §4.6 below).
4. Issue one of these verdicts (NOT just NOVEL/TRIVIAL):
   - **STATEMENT_DUPLICATE** — statement_similarity to some Mathlib lemma > ε_stmt
   - **PROOF_ROUTE_DUPLICATE** — proof_route_similarity to some Mathlib proof > ε_route
   - **BOTH_DUPLICATE** — both above
   - **PROOF_STYLE_ONLY** — proof route matches a Mathlib proof but statement does not (e.g. both `by nlinarith` but different theorems)
   - **STATEMENT_NEAR_BUT_ROUTE_DIFFERENT** — statement near a Mathlib lemma but proof route is distinct
   - **NOVEL_STATEMENT_AND_ROUTE** — both metrics show distinct
   - **UNCLOSED** — no tactic closed; no proof DAG to fingerprint

**Pass gate (revised):**
- At least **5 of 30** candidates marked NOVEL_STATEMENT_AND_ROUTE
- At least **5 of 30** marked PROOF_ROUTE_DUPLICATE or PROOF_STYLE_ONLY (= primitive is doing work, not just emitting NOVEL everywhere)
- Manual operator audit confirms ≥70% of NOVEL_STATEMENT_AND_ROUTE verdicts are GENUINELY mathematically novel (not metric artifacts)

**If FAIL:** primitive is producing either (a) all-NOVEL (useless), (b) all-DUPLICATE (over-killing), or (c) verdicts that don't survive manual audit.

### 4.5 Cheap-baseline ablation dominance test (NEW v1 — Edit 3)

> Per external-reviewer point: GP-225 history shows fancy structures repeatedly collapse into cheap deterministic signals (BM25 / signature matching / WHNF / dependency-set Jaccard). The proof-route fingerprint MUST beat cheap baselines or it's redundant.

**Hypothesis:** the full proof-route fingerprint adds signal that cheap baselines do not capture.

**Test:** on the §4.3 held-out test set, compute distance and F1 for each of these representations:
- **B0** target_type_head + namespace only (1-2 tokens)
- **B1** constants_used multiset Jaccard
- **B2** tactic_family_sequence only (surface)
- **B3** skeleton_kind indicator
- **B4** normalization_path only
- **B5** statement token cosine similarity
- **B6** dependency_set Jaccard (kernel)
- **B7** full surface_fingerprint
- **B8** full kernel_fingerprint
- **B9** combined surface + kernel fingerprint

**Pass gate (pre-registered):** B9 (combined) must beat the best single-feature baseline (B0-B6) by F1 ≥ 0.03 on the held-out test set.

**If FAIL:**
- If B1 (constants only) matches/beats B9 → primitive is mostly a dependency-set heuristic; demote to "cheap-feature bundle" not "DAG fingerprint primitive."
- If B5 (statement similarity) matches B9 → you don't need proof fingerprints for the task; abandon proof-route axis.
- If B2 (tactic family) matches B9 → metric is too shallow; primitive fails.

### 4.6 Statement-similarity primitive (PUNTED — separate seam needed)

This seam validates ONLY proof-route fingerprint. Statement-similarity (e.g., embedding-based or AST-based) is required to issue STATEMENT_DUPLICATE / NOVEL_STATEMENT verdicts in §4.4. That primitive is its own seam (GP-237? to be written if needed). For §4.4 in this seam, statement similarity is approximated by `theorem_name_grep + namespace_match + type_head_match` (cheap heuristic, not the decisive piece). The verdict-quality manual-audit step in §4.4 catches errors from this approximation.

### 4.7 Hard falsifier — proof-route same, statement different (NEW v1)

When `proof_route_similarity > ε_route` BUT `statement_similarity < ε_stmt`:
- Verdict is **PROOF_STYLE_ONLY**, NOT TRIVIAL.
- This catches the `by nlinarith / by simp / by ring` collision case.
- Without this distinction, the primitive over-kills automation-heavy rows.

**Example:** `example : 2 + 3 = 5 := by norm_num` and `example : 17 * 19 = 323 := by norm_num` have identical proof routes but neither trivializes the other as a theorem.

## 5. Decision flow after this seam runs

```
Run §4 experiments → measure pass-gate outcomes:

  ALL FOUR PASS (4.1, 4.2, 4.3, 4.4):
    DAG fingerprint primitive is validated.
    → Write GP-236 (separate seam) proposing Route C v32 architecture
      USING this primitive as its decisive discriminator.
    → Pre-register Route C v32's falsifier in GP-230 forecast pool.
    → Run v31 ablation with the new architecture.

  ANY ONE OR MORE FAIL:
    Primitive doesn't validate.
    → No GP-236.
    → Document the failure mode in this seam's §6.
    → Update v31 handover to "DAG fingerprint approach killed; harness
      pivots to (TBD next architectural direction or to gap-report-only
      deliverable on PR drafts via manual review)."
```

## 6. Honest limitations of this seam (pre-Meta-Darwin)

Things I expect Meta-Darwin to attack:

1. **Fingerprint schema is hand-designed.** No learned representation. May be brittle to the specific tactic-family categorization choices in §2.
2. **Distance weights `w1=0.4 / w2=0.3 / w3=0.2 / w4=0.1` are guessed.** Their tuning under §4.1/4.2 should be part of validation, not assumed.
3. **Mathlib's `~150K lemmas` count is approximate.** Actual v4.29.0 sandbox count may differ. Index construction needs the real count.
4. **§4.3 needs hand-labeled paraphrase pairs.** That's 100 lemma pairs to label. Time cost ~1 hour by a human. If the labeling is done by claude_rd alone, it's biased toward whatever the classifier already agrees with — labeling should be operator + external review.
5. **§4.4's "10 sorry-miner candidates" is the sorry-miner output from this same session.** That's a small N. If 2-3 of them happen to be NOVEL by luck, §4.4 passes but the result is non-robust.
6. **The primitive's value depends on Lean compile being available** to verify NOVEL candidates after Layer 3 lets them through. This seam doesn't address the compile step.
7. **DAG fingerprint may be invariant to mathematically-significant differences.** E.g., `2 + 3 = 5` and `3 + 2 = 5` could have identical fingerprints (both `direct` skeleton, both cite `Nat.add_comm`, etc.) even though one is symbol-permuted. This could either be a feature (truly equivalent statements should be near-duplicate) or a bug (some symbol permutations are mathematically nontrivial).

## 7. Pre-registered falsifier for the primitive itself

**The DAG fingerprint primitive is killed if:**
- §4.1 fails (intra-cluster distance not small enough)
- OR §4.2 fails (inter-cluster distance not large enough)
- OR §4.3's optimal F1 < 0.70
- OR §4.4 yields <3 NOVEL out of 10 sorry-miner candidates

ANY ONE of these failing kills the primitive. The current author (claude_rd) commits to documenting the failure mode and NOT proposing a GP-236 follow-on if the primitive fails.

## 8. Pattern provenance

This seam is structured per the proposed `primitive_before_architecture_gate` pattern (see `org/patterns/primitive_before_architecture_gate.md`, to be written). The rule:

> Don't write a multi-layer architecture if any layer is "TBD" or "first pass is crude" or "research thread." Each layer must be (a) implemented, (b) measured, (c) within pass-gate range, BEFORE it's named in an architecture spec.

GP-233 §7 violated this rule by architecting on top of Layer 2b which was admittedly "crude first pass" and "its own research thread." This seam (GP-235) demonstrates the corrective: validate the primitive in its own seam with pre-registered pass-gates BEFORE any architectural seam is written.

## 9. Related

- [[GP-233 4-catalog meta solver framework seam]] §7 (DEMOTED) — the architectural failure that motivates this primitive-first redesign
- [[feedback_be_meta_darwin_to_self_2026_05_14]] — in-artifact discipline rule that GP-233 §7 violated
- [[project_gp225_v28_v29_breakthrough_15_moat_grade_closures_2026_05_15]] (PARTIALLY RETRACTED) — earlier work in the v22-v30 chain
- [[feedback_gp225_4_catalog_meta_solver_framework_2026_05_15]] — operator memory of the 4-catalog reframe
- `analytics/public/leanmill/results/v30_ablation_10rows_report.md` — empirical data confirming Mode D = Mode A
