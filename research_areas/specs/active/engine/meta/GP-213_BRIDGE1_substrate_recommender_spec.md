# BRIDGE-1 — Substrate-recommender — spec v0

**Parent seam:** `GP-213_operator_role_mechanization_seam.md` §3.1.
**Companion findings:** `GP-149_phase2_refresh_2026-05-04.md` §10 (cross-LLM audit).
**Dependency completed:** GP-148 mining infrastructure; GP-149 phase 2 refresh; cross-LLM audit (failed at 0.42, scopes this spec to operator-confirmed mode).
**Status:** spec-stage entry conditions for BRIDGE-1 were met; v0 spec written 2026-05-04.

## 1. What this builds

A new module `src/ztare/director/substrate_recommender.py` and a CLI entrypoint `python -m ztare.director.recommend_substrate`. The module reads the existing track record, insights ledger, mining archive, and seam library; outputs top-3 candidate next-substrates with rationale + charter sketches; deposits the output into `ztare_workspace/inbox/substrate_recommendations/` for operator review.

The recommender is **operator-confirmed only in v0.** The kernel does not auto-launch substrates from these recommendations. Operator copies a recommendation into a charter, edits, then runs the substrate as today.

## 2. Why now

Operator's bottleneck has shifted from iteration speed to substrate selection. The mining archive (1825 records, 128 projects) gives the data layer needed to recommend grounded next-substrates. The cross-LLM audit found classifier labels are unreliable for *auto-routing*, but **operator-supplied class labels remain valid** as recommendation inputs.

## 3. Inputs

The recommender reads (and only reads):

- `EXPERIMENT_TRACK_RECORD.md` — substrate names, end states, F-row findings
- `research_areas/private/insights/insights_ledger.md` — cross-substrate findings
- `analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl` — per-iteration metadata
- `research_areas/private/seams/engine/*.md` — operator's stated bridges and tensions
- `docs/concepts/problem_class_taxonomy.md` — the 6 problem classes with mining N counts
- *Optional:* operator-supplied class label (`--class catastrophic_fit_failure` etc.)
- *Optional:* operator-supplied substrate-class hint (`--substrate-class continuous_chaotic`)

No write access. No network calls except for the LLM API call.

## 4. Output

A markdown file dropped into `ztare_workspace/inbox/substrate_recommendations/{timestamp}_{slug}.md`:

```markdown
# Substrate recommendation — {timestamp}

## Top 3 candidates

### Candidate 1: {substrate_name}

**Predicted class:** {class_name}
**Confidence:** {high|medium|low}
**Mining basis:** {N records cited from {project_count} projects}

**Why this is a candidate:**
{1-paragraph rationale citing specific F-row findings + insight ledger entries by exact line/file}

**Charter sketch:**
{300-word charter sketch with target, falsification criterion, gate package}

**What would change if this substrate succeeds:**
{1-paragraph description of the structural question it would answer}

**Anti-tautology check:**
- Does NOT reuse existing substrate name: {YES|NO + match}
- Cites specific findings (not vocabulary): {list of citations}
- Substrate-class hint matches operator override (if any): {YES|NO}

### Candidate 2: ... [same shape]
### Candidate 3: ... [same shape]

---
**Recommender metadata:**
- Run timestamp: ...
- Inputs read: ...
- LLM model: ...
- Cross-LLM agreement on class labels (from May 4 audit): 42% three-way; recommendations gated on operator confirmation.
```

## 5. Anti-tautology guards

Hard-coded validators on the LLM output before write:

1. **No name-reuse.** `recommended_name not in existing_substrate_names` — read from `EXPERIMENT_TRACK_RECORD.md`. Reject and re-prompt if violated.
2. **Citation discipline.** Every rationale must cite at least 2 specific findings by `EXPERIMENT_TRACK_RECORD.md:Lxxx` line ref or `insights_ledger.md:section` heading. Reject if citations are vocabulary-level (e.g. "uses inversion" without a line ref).
3. **Surface what changes.** "What would change if this substrate succeeds" must be present and ≥ 100 chars. Reject if missing or boilerplate.
4. **No claim of LLM consensus on class label.** The recommender writes the class label as "predicted class" with an explicit confidence band; never asserts consensus across providers.
5. **Cross-LLM disclosure.** The output must include the cross-LLM audit verdict at the bottom (see template above) so the operator does not over-trust the predicted class.

## 6. CLI

```
python -m ztare.director.recommend_substrate \
    [--class CLASS_LABEL] \
    [--substrate-class SUBSTRATE_CLASS] \
    [--n_candidates 3] \
    [--model MODEL_ID]
```

Defaults: `n_candidates=3`, `model=gemini-2.5-flash` (not lite — recommendation is reasoning-heavy).

The `--class` flag is the *operator-supplied* class label; the recommender treats it as ground truth and finds substrates that would address it. Without `--class`, the recommender reads the class distribution from the mining archive (top-3 most-N classes) and hedges across them.

## 7. Failure modes

- **LLM fabricates substrate names that don't fit the existing taxonomy.** Caught by anti-tautology check 1.
- **LLM cites findings that don't exist.** Caught by check 2 (validator opens the cited file and confirms the line/section exists).
- **LLM proposes a substrate that is functionally identical to an existing one with a renamed wrapper.** Hardest to catch automatically; v0 relies on operator review. v1 candidate: embedding-based similarity check against existing substrates.
- **Recommendation drifts toward the LLM's training-distribution comfort zone (Lollapalooza camouflage).** Mitigation: cross-LLM check on top-3 outputs from two providers; if they agree on > 1 of 3 candidates, that candidate is flagged as "may be aesthetic-aligned, double-check."

## 8. Verified pre-build (do these before merging the module)

- [ ] Read `EXPERIMENT_TRACK_RECORD.md` and confirm the F-row schema is stable.
- [ ] Read 5 random recent F-rows and write a sample LLM prompt by hand. Confirm the model can produce a citation-disciplined output before automating.
- [ ] Confirm the `inbox/substrate_recommendations/` path conforms to GP-167 inbox conventions (directory exists, slug format matches).
- [ ] Confirm the operator-override log shape matches `analytics/public/operator_overrides.jsonl` so we can later evaluate recommendation acceptance rate.

## 9. Out of scope (v0)

- Auto-launching the recommended substrate. Always operator-confirmed.
- Multi-class recommendations. v0 recommends within one class (operator-supplied or top-N inferred).
- Cross-substrate synthesis. That is BRIDGE-3, separate spec.
- Pattern-bank class injection from I-5. Recommender outputs the class label; the I-5 manual mode (see GP-214) is what *uses* the label at substrate runtime. The two stay decoupled in v0.

## 10. Acceptance criteria

The spec is shipped when:

- Module compiles, the CLI runs end-to-end on the current archive, and an operator-readable markdown drops into the inbox.
- Anti-tautology checks 1–5 fire on test inputs (3 unit tests, one per check, with crafted bad outputs).
- One real recommendation is generated, the operator reads it, and the operator confirms the rationale citations are real (not hallucinated).
- F-row entry added to `EXPERIMENT_TRACK_RECORD.md`: "BRIDGE-1 v0 shipped, first recommendation accepted/rejected by operator."

## 11. Risks called out by GP-213 §6

GP-213 surfaces three risks of mechanizing this layer; this spec addresses each:

1. **Reading-bottleneck.** Recommender output is capped at 3 candidates per run. Operator review time is bounded.
2. **Coupling-debt with BRIDGE-3.** v0 outputs do not feed BRIDGE-3; the two specs stay decoupled until BRIDGE-3 ships.
3. **LLM-aesthetic capture.** The cross-LLM disclosure in §6 + the cross-provider double-check in §7 mitigate this. The full mitigation is to run the recommender with two model families and only accept candidates where they disagree on ≥ 1 of 3 (forcing aesthetic diversity).

---

*v0 spec written 2026-05-04 in auto mode. Refresh after first 5 real recommendations and operator-acceptance data.*
