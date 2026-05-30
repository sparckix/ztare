# GP-213 — Operator-Role Mechanization Frontier (Seam)

> **Seam metadata** · `seam_id:` GP-213 · `track:` engine · `status:` active draft 2026-05-04; pre-spec debate. · `last_updated:` 2026-05-09


**Status:** active draft 2026-05-04; pre-spec debate.
**Owner:** automated-R&D frontier
**Depends on:** GP-148 / GP-149 (mining), GP-151 (cross-LLM constraint), GP-167 (persistent-agent channel + role offices), GP-212 (gate-package recommender), GP-104 (rubric authoring), GP-167 org-runtime architecture
**Triggered by:** 2026-05-04 operator question — "how close are we to automated R&D discovery, and are there any obvious bridges we can already cross?"
**Visibility:** private

---

## 1. The actual question

ZTARE today is a kernel that mechanizes the *iteration-level* discipline of adversarial verification. The operator + research director still own most of the *substrate-level* and *program-level* decisions. The question is which of those higher-level decisions are mechanizable given current infrastructure, and which are not.

This seam catalogs the bridges, separating:
- **Already mechanized** — built, deployed, working
- **Partially mechanized** — building blocks exist; full flow does not
- **Mandate-only** — entirely human-driven today
- **Structurally not mechanizable** — operator judgment is decisive for principled reasons

The output is a candidate list of bridges to cross + the discipline for doing it without hitting the failure modes GP-149 and GP-151 already identified (LLM-aesthetic capture, cross-LLM disagreement, false-positive routing).

---

## 2. The map of operator-role functions

### 2.1 Already mechanized (don't touch — they work)

| Function | Surface | Status |
|---|---|---|
| Iteration loop (mutator → judge → score) | `autoresearch_loop.py` | Production |
| Rubric authoring discipline | `rubric_authoring_map.md` + validators | Production |
| Charter pre-registration enforcement | `_evaluate_post_eval_loop_control` + Cage v5 | Production |
| Falsification gate stack | `src/ztare/gates/` | Production |
| Weakest-link runtime classification | `weakest_link_classifier.py` | Production (regex, observability-only per GP-151) |
| Anti-pattern catalog injection | `inject_antipattern_catalog` flag + `anti_pattern_catalog.md` | Production (hardkill mode) |
| Substrate-class dispatch | `cage_meta.substrate_class` (e.g., `lean_proof`) | Production |
| Stagnation detection + pivot triggering | autoresearch GP-103 | Production |
| F-row + insights-ledger recording | `EXPERIMENT_TRACK_RECORD.md` + `insights_ledger.md` | Production (manual operator-curated) |
| Cross-LLM consistency check | `mine_cross_provider_classifier_agreement.py` | Production (audit; PATH_C_ONLY) |
| Persistent-agent role offices | GP-167 `org/channels/` | Production |
| Lean-proof substrate harness | GP-211 `lean_proof_gate` | Production |
| Mining infrastructure | GP-148 `scripts/public/mining/` | Production |

### 2.2 Partially mechanized (building blocks exist; full flow does not)

| Function | Existing pieces | What's missing |
|---|---|---|
| Charter-from-brief generation | `make generate-gp` produces template + LLM-drafted rubric | Operator still writes the BRIEF. No "research director recommends next substrate based on EXPERIMENT_TRACK_RECORD + insights_ledger." |
| Gate-package recommendation | GP-212 (scaffolded today; Phase A) | Mining hit-rate population (Phase B) + classifier body (Phase C) + wiring (Phase D) |
| Paper drafting from substrate output | `config/renderers/` produces structured renders | Cross-substrate paper composition; section-from-debate-log; reference assembly |
| Cross-substrate finding synthesis | `insights_ledger.md` indexes findings | No automated cross-finding compositor — when two findings overlap, no system flags it |
| Cold-shot family selection | `cold_shot_policy.json` per project | Operator picks family per substrate; no recommender based on substrate class + stagnation state |
| Substrate retirement detection | Stagnation count + cost-per-finding telemetry | No "retire this substrate" auto-recommender; operator decides |
| Operator-override telemetry | `insights_ledger.md` is hand-written | No structured override log feeding back to recommenders (GP-212 introduces one) |

### 2.3 Mandate-only (research director / operator owns; not mechanized)

| Function | Why not yet mechanized |
|---|---|
| Substrate selection (which problem to ZTARE next) | Requires reading the field, selecting a question that has the right shape for ZTARE's discipline |
| Problem decomposition (vague question → substrate-able formulation) | Requires substantive domain knowledge + creative reformulation |
| Cross-domain calibration (pace, novelty positioning) | Requires market awareness; cannot be derived from in-repo signals alone |
| Promotion decisions (ship paper / retire thesis / freeze branch) | Stakes-sensitive; multi-axis judgment |
| Cross-substrate synthesis at paper level | Requires holding entire research program in working memory |
| Funder / external-stakeholder communication | Out of scope; not a research function |

### 2.4 Structurally not mechanizable (decisive judgment, principled)

These three are where operator judgment is structurally decisive because the recommender would itself be subject to the same failure modes ZTARE catches:

1. **Selecting the eigenquestion** — what counts as the central question of a substrate. Currently the operator's residual per paper 5 §3. Mechanization here would risk substrate-level Goodhart.
2. **Recognizing when to reframe rather than attack** — Munger inversion at the substrate level. Same risk.
3. **The social dynamics of live pressure-testing** — calls outside the kernel; not a research function.

These are paper 5's "three residual commitments." They are deliberately preserved as human.

---

## 3. The bridges hiding in plain sight

Five bridges that the existing infrastructure makes feasible AND that have not been crossed:

### 3.1 BRIDGE-1: Substrate-recommender (next-best-substrate-from-track-record)

**Premise:** the operator currently picks the next substrate. ZTARE has accumulated 128 projects, 2608 iteration records, an experiment track record + insights ledger. An LLM with read access to those artifacts can propose the top-3 candidate next substrates, with a rationale citing existing findings.

**Mechanization:** new module `src/ztare/director/substrate_recommender.py`. Reads `EXPERIMENT_TRACK_RECORD.md`, `insights_ledger.md`, `analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl`, the seam library. Outputs three candidates with charter sketches.

**Anti-tautology guard:** must cite specific findings; must not reuse existing substrate names; must surface "what would change if this substrate succeeds" up front. Operator-confirmable.

**Why this is feasible now:** GP-148 (mining infrastructure) gives us the data layer. GP-167 (org channels) gives us the inbox to deposit recommendations.

**Why it's worth crossing:** the operator's bottleneck is no longer iteration speed — it is substrate selection. Mechanizing this lets the operator focus on substrate-level judgment, which is the decisive residual.

### 3.2 BRIDGE-2: Substrate-retirement detector

**Premise:** substrates stagnate before they are retired. Currently the operator decides retirement; some substrates ride too long, some get retired too early.

**Mechanization:** new module `src/ztare/director/retirement_detector.py`. Reads stagnation count, score trajectory, cost-per-finding, last-N-iters score variance from the trajectory archive. Outputs a retirement recommendation with confidence + rationale.

**Decision rule (proposed):** retire when `stagnation_count >= 5` AND `last_5_iter_score_variance < 5` AND `cost_per_finding_30d > median_cost_per_finding_all_time * 2`.

**Anti-tautology guard:** must distinguish "substrate genuinely exhausted" from "substrate hitting a productive plateau before a climb." Mining shows the second pattern is real (GP-149 §2.2 — pivots work after stagnation in some classes).

**Why this is feasible now:** all the telemetry exists. Just needs aggregation + decision rule + operator-confirm flow.

### 3.3 BRIDGE-3: Cross-finding synthesizer

**Premise:** when two completed substrates produce findings that touch the same structural question, the operator manually composes the cross-finding. Examples: gp149 mining + GP-151 cross-LLM both touch reliability of LLM judgments. Paper 7's cross-domain methodology synthesis is the manual version of this.

**Mechanization:** new module `src/ztare/director/cross_finding_synthesizer.py`. Reads `insights_ledger.md` entries, computes pairwise embedding similarity between findings, surfaces clusters where ≥3 findings share structural language. Outputs draft synthesis text + citation graph.

**Anti-tautology guard:** must NOT collapse findings that share surface vocabulary but differ structurally. Cross-LLM consistency check on cluster labels (per GP-151 PATH_C_ONLY discipline). Operator-confirmable; never auto-publishes.

**Why this is feasible now:** insights_ledger is structured. Embedding-based clustering is cheap. Operator role is to confirm + author the actual synthesis paragraph.

### 3.4 BRIDGE-4: Cold-shot recommender

**Premise:** cold shots are cross-LLM seeds for de-anchoring. The operator currently picks the family per substrate from `cold_shot_policy.json`. Mining shows certain cold-shot families work better on certain substrate classes (gp164 ANALOGY work, gp210 consciousness Erdős seed pattern).

**Mechanization:** extend `src/ztare/validator/cold_shot_runner.py` (or sibling) with a `recommend_cold_shot_family(charter_text, substrate_class, current_stagnation_state)` function. Reads the trajectory archive for prior cold-shot-effectiveness by substrate class.

**Anti-tautology guard:** must respect the cross-LLM block — cold-shot family must come from a different model family than the current mutator/judge. Recommender enforces this.

**Why this is feasible now:** existing cold-shot infrastructure is robust. Just adds a recommender layer.

### 3.5 BRIDGE-5: Paper-section drafter from substrate output

**Premise:** when a substrate produces a champion thesis (e.g., gp210 score-97), the operator drafts the paper section. The renderer system (`config/renderers/`) handles per-substrate notes; cross-substrate paper composition is manual.

**Mechanization:** new renderer `config/renderers/paper_section.md` that takes (champion thesis + debate logs + substrate context) → paper-section markdown. Plus a cross-substrate composer that assembles multiple sections + reference list.

**Anti-tautology guard:** the section drafter must NOT introduce claims not supported by the debate logs. Verification step: cross-check every claim in drafted section against the source iteration log.

**Why this is feasible now:** renderer system is mature. Cross-substrate composition is a new but bounded artifact.

---

## 4. The order in which to cross them

Three considerations: cost, value, and dependency.

| Bridge | Cost (effort) | Value (operator-time saved) | Depends on | Recommended order |
|---|---|---|---|---|
| BRIDGE-1 substrate-recommender | M | H | GP-148 (built) | 1st |
| BRIDGE-2 retirement detector | S | M | trajectory archive (built) | 2nd |
| BRIDGE-3 cross-finding synthesizer | M | H | insights_ledger structured | 3rd |
| BRIDGE-4 cold-shot recommender | S | M | cold_shot infrastructure (built) | 4th |
| BRIDGE-5 paper-section drafter | M | H | renderer system + champion-promotion telemetry | 5th |

Cross BRIDGE-1 first because it removes the operator's biggest bottleneck (substrate selection). BRIDGE-2 is cheap and complementary. BRIDGE-3 produces the cross-substrate synthesis the operator currently does in paper-writing — high time-saved per output. BRIDGE-4 and BRIDGE-5 are quality multipliers, not bottleneck removers; do them after the bigger items.

---

## 5. The honest answer to "how close are we to automated R&D discovery"

**Calibrated:** at the iteration-level (within a substrate), ZTARE is automated. The mutator generates, the judge attacks, the loop iterates without human intervention until it stagnates or scores high. That is automated discovery within a fixed problem.

**At the substrate-level (which problem to ZTARE)**: not automated. BRIDGE-1 brings it to "operator-confirmable LLM recommendation" rather than "operator-only authoring." That is a meaningful step but not full automation.

**At the program-level (which research direction is worth pursuing)**: not automated and structurally should not be. This is paper 5's residual + Munger circle-of-competence + the operator's accumulated taste. Mechanizing this would risk substrate-level Goodhart on the operator's own taste (which is what the corpus-gradient pluralism failure mode in gp169 was).

**Calibrated answer:** we are 0.5 → 0.7 of the way to "operator-confirmable automated R&D" if all 5 bridges are crossed, with the residual 0.3 deliberately preserved as human (paper 5's three residual commitments). Full automation of R&D discovery is structurally out of reach; operator-confirmable recommendation across all decision layers is reachable.

This is the right framing for external description. "We automated R&D" is overclaim. "We mechanized 70% of operator workflow under explicit operator-confirmation" is accurate.

---

## 6. Three uncomfortable truths

### 6.1 Bridges crossed too fast become the new bottleneck

If BRIDGE-1 ships and the recommender starts auto-suggesting substrates, the operator must read every recommendation. If the recommender produces 5 suggestions per day, the operator's review time becomes the bottleneck. Mechanization shifts where the bottleneck sits; it does not remove it.

Mitigation: rate-limit recommender output. One substrate suggestion per N completed substrates, not continuous.

### 6.2 The bridges interact

BRIDGE-1 (substrate-recommender) reads the insights_ledger. BRIDGE-3 (cross-finding synthesizer) reads the same artifact. If BRIDGE-3 starts auto-composing findings, BRIDGE-1's input distribution shifts. The recommender starts recommending based on auto-composed findings rather than human-authored ones.

Mitigation: maintain provenance. Each bridge tags its outputs as machine-derived; subsequent bridges weight machine-derived inputs lower than human-authored ones.

### 6.3 The bridges may compound the cross-LLM aesthetic-capture risk

GP-151 found fine-grained LLM labels disagree across providers (48% three-way). If BRIDGE-1, BRIDGE-3, and BRIDGE-5 all use LLM judgment for their recommendations, and they all happen to be operating against the same LLM family, they jointly entrench that family's aesthetic.

Mitigation: cross-LLM consistency check on every bridge's output, same discipline as GP-151. Below 75% three-way → PATH_C_ONLY (advisory, not auto-applied).

---

## 7. Decision

**Decided here (subject to operator confirmation):**

- BRIDGE-1 (substrate-recommender) is the highest-value next step. Scaffold it after GP-212 Phase B (mining hit-rate population) completes, since the recommender's input data depends on the same mining refresh.
- BRIDGE-2 (retirement detector) can ship in parallel with BRIDGE-1 since its inputs (trajectory archive, telemetry) are already populated.
- BRIDGE-3, 4, 5 ship in order after BRIDGE-1+2 are validated.
- All bridges follow the same operator-confirmable discipline as GP-212: never auto-applies, always surfaces reasoning, override log feeds back into mining.

**Pre-spec deliverables:**

1. Phase 2 mining LLM classifier completion (DONE 2026-05-04)
2. Phase 2 mining findings refresh report (in flight; this seam triggered while it was being written)
3. GP-212 Phase B (per-class hit-rate population) before BRIDGE-1 spec is written

**Spec stage entry conditions:** items 1–3 above must complete before BRIDGE-1 spec is written.

---

## 8. Cross-references

- `research_areas/private/seams/engine/GP-148_void_mining_seam.md` — mining infrastructure
- `research_areas/private/seams/engine/GP-149_mining_findings_and_interventions_seam.md` — first-pass findings
- `research_areas/private/seams/engine/GP-151_classifier_telemetry_downgrade_seam.md` — cross-LLM PATH_C constraint
- `research_areas/private/seams/engine/GP-212_meta_solver_kernel_seam.md` — gate-package recommender (BRIDGE-related)
- `research_areas/private/seams/mission/GP-167_multi_agent_interface_form_factor_seam.md` — persistent-agent channel + role offices
- `papers/paper5/draft.md` — *Principles of Epistemic Verification*; the three residual commitments that should NOT be mechanized
- `docs/concepts/organizational_primitives.md` — org-runtime primitive list (BRIDGE-1, 3 may register new primitives)
- `docs/concepts/ztare_research_company_architecture.md` — research-director role definition

---

## Task list (added 2026-05-04)

- [ ] Wait for GP-212 Phase B (mining hit-rate population)
- [ ] Write BRIDGE-1 substrate-recommender spec (after GP-212 Phase B)
- [ ] Implement BRIDGE-1 module + operator-confirm flow
- [ ] Write BRIDGE-2 retirement-detector spec (parallel with BRIDGE-1)
- [ ] Implement BRIDGE-2 + dashboard surface
- [ ] Validate BRIDGE-1+2 against current operator's intuition before broader rollout
- [ ] Write BRIDGE-3 cross-finding synthesizer spec
- [ ] Implement BRIDGE-3 + cross-LLM consistency check
- [ ] BRIDGE-4 cold-shot recommender (lower priority)
- [ ] BRIDGE-5 paper-section drafter (after BRIDGE-3 ships)

---

*Seam v0 written 2026-05-04 in auto mode. Refresh after BRIDGE-1+2 ship and the operator's overrides surface gaps in the recommender's reasoning.*
