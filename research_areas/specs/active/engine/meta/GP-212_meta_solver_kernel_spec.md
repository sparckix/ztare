# GP-212 — Meta-Solver Kernel (Spec)

**Status:** spec v0, scaffolded 2026-05-04
**Companion seam:** `research_areas/private/seams/engine/GP-212_meta_solver_kernel_seam.md`
**Entry conditions:** the seam's §7 checklist. This spec scaffolds the surfaces; full population requires Phase 2 mining + per-class hit-rate population.

---

## 1. Scope

This spec covers Steps 1–3 of the seam: mining-corpus refresh, problem-class taxonomy artifact, and gate-package recommender. Step 4 (full auto-instantiation) is explicitly out of scope for v0 and gated on the seam §7 checklist.

In scope:
- A new artifact `docs/concepts/problem_class_taxonomy.md` listing initial problem classes with structured metadata
- A new module `src/ztare/validator/gate_package_recommender.py` exposing `recommend_gate_package(charter_text: str, taxonomy: dict) -> Recommendation`
- Wiring into `src/ztare/validator/rubric_mode_resolver.py` so the recommender is invoked at rubric-resolution time as advisory output (no auto-apply)
- Operator-override log shape and storage location
- Novel-substrate detection thresholds

Out of scope:
- Auto-application of the recommender's output (operator confirmation required throughout v0)
- LLM-derived problem-class labeling at runtime (cross-LLM consistency block per GP-151)
- Cross-substrate gate transfer experiments

---

## 2. Surfaces and contracts

### 2.1 Problem-class taxonomy artifact

Path: `docs/concepts/problem_class_taxonomy.md`

Format: structured markdown with one section per class. Each section MUST contain:

- A short name (snake_case)
- One-paragraph definition
- Canonical example: project slug + brief
- Default rubric_mode (`newton` / `kepler` / `calibration`)
- Default cage_meta.substrate_class value
- Recommended gate package (rubric flags + their default values)
- Anti-pattern emphasis (which catalog entries matter most)
- Required N for stability (per seam §7 checklist: ≥20)
- Current N (project count classified into this class as of last mining run)

This file is operator-curated. The recommender reads it; it does not modify it. Modifications happen via PR + operator review.

### 2.2 Recommender module

Path: `src/ztare/validator/gate_package_recommender.py`

Interface:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Recommendation:
    """Output of the gate-package recommender."""
    problem_class: str | None       # None when novel-substrate detection fires
    confidence: str                 # "high" | "medium" | "low" | "novel"
    rubric_mode: Optional[str]      # suggested rubric_mode, or None
    gate_flags: dict                # suggested rubric flag values
    anti_pattern_inject_mode: str   # "off" | "hardkill" | "ceilingbreaker" | "both"
    rationale: str                  # one-paragraph explanation citing taxonomy + mining sources
    novel_substrate: bool           # True iff confidence == "novel"

def recommend_gate_package(
    charter_text: str,
    taxonomy_path: str = "docs/concepts/problem_class_taxonomy.md",
) -> Recommendation:
    """Read the taxonomy, classify the charter, return a Recommendation.

    NEVER auto-applies. The caller (rubric_mode_resolver) surfaces the
    Recommendation to the operator and waits for explicit confirmation.

    Confidence levels:
        high   — charter strongly matches one class (above match threshold);
                 mining N for that class >= 20
        medium — strong match but mining N < 20
        low    — weak match (between novel threshold and match threshold)
        novel  — below novel threshold; recommender refuses to auto-suggest;
                 caller falls back to operator-only authoring
    """

def classify_problem_class(
    charter_text: str,
    taxonomy: dict,
) -> tuple[Optional[str], float]:
    """Return (best_match_class_name, similarity_score) or (None, score) when novel."""
```

Implementation discipline:
- The classifier MUST be deterministic on a given charter + taxonomy. Use embedding-based cosine similarity over taxonomy class definitions, not LLM judgment. (Cross-LLM block from GP-151.)
- Embedding model: same as Falsify, `gemini-embedding-001`, or any embedding model the operator declares in environment. Module reads `META_SOLVER_EMBED_MODEL` env var with default.
- Thresholds are configurable in the module; defaults: match ≥ 0.65, novel < 0.45.
- The `rationale` field MUST cite the taxonomy entry that matched + the mining source for the gate-package recommendation. No bare assertions.

### 2.3 Wiring into rubric_mode_resolver

`apply_rubric_mode_defaults` in `rubric_mode_resolver.py` gets a sibling function `surface_recommender_advice` that runs alongside the existing defaults logic. Output is logged to the operator at rubric load time but NEVER mutates the rubric without `--accept-recommender` flag.

Default behavior: print the recommendation, list deltas vs. current rubric, exit 0. Operator decides whether to apply.

### 2.4 Operator-override log

Path: `analytics/public/meta_solver_overrides.jsonl`

Each entry written when operator chooses NOT to apply a recommendation:

```json
{
  "timestamp_utc": "2026-05-04T...",
  "project": "<slug>",
  "recommended": {<Recommendation as dict>},
  "operator_action": "rejected" | "modified" | "ignored",
  "operator_modifications": {<deltas applied>},
  "operator_rationale": "<free text from operator, optional>"
}
```

This log is mining input for future taxonomy refinement. It is operator-only (gitignored or under `research_areas/private/`).

### 2.5 Novel-substrate detection

Per seam §7 checklist item 6: when `classify_problem_class` returns confidence < novel threshold, the recommender returns `novel=True` and no auto-suggestion. The operator is forced to hand-tune. This prevents the meta-solver from confidently mis-classifying genuinely new substrate types.

The novel-substrate threshold MUST be operator-tunable per environment. Default 0.45.

---

## 3. Test plan

### 3.1 Unit tests

- `recommend_gate_package` returns deterministic output on a fixed charter + fixed taxonomy
- `classify_problem_class` returns `(None, score)` when score < novel threshold
- Embedding model is read from `META_SOLVER_EMBED_MODEL` env var
- Recommendation `rationale` always cites the taxonomy entry that matched

### 3.2 Integration tests

- Apply recommender to 6 known substrate types (one per initial class). Verify it correctly classifies each.
- Apply to a deliberately-novel charter (off-taxonomy substrate). Verify `novel_substrate=True`.
- Verify operator-override log writes correctly when operator rejects a recommendation.

### 3.3 Validator integration

- `make validate-rubric` continues to pass for all existing rubrics (no regression)
- A new `make recommend-gate-package PROJECT=<slug>` target invokes the recommender on a project's charter and prints the recommendation

---

## 4. Rollout plan

### Phase A — scaffold (this spec, today)

- Create `docs/concepts/problem_class_taxonomy.md` with 6 initial classes seeded from existing projects (skeleton only — no per-class hit rates yet)
- Create `src/ztare/validator/gate_package_recommender.py` with the interface above; implementation is `NotImplementedError` for now
- Update arch maps (autoresearch_loop, rubric_authoring_map)
- Run validator to confirm no regression

### Phase B — Phase 2 mining (in flight)

- Refresh trajectory archive (DONE: 2608 records)
- Patch LLM classifier for Gemini Flash-Lite
- Re-run mining suite
- Population per-class hit rates in the taxonomy

### Phase C — recommender implementation

- Replace `NotImplementedError` with embedding-based cosine similarity classifier
- Implement `Recommendation` rationale with taxonomy + mining citations
- Wire into `rubric_mode_resolver`
- Ship operator-override log writes

### Phase D — operator confirmation flow

- `make recommend-gate-package` target
- Surface deltas vs. current rubric in human-readable form
- Test against 6+ existing projects to verify correct recommendations

### Phase E — production deployment (gated on seam §7 checklist)

- Cross-LLM consistency check on problem-class labels
- Per-class N ≥ 20
- Novel-substrate detection threshold validated

---

## 5. Backward compatibility

- Existing rubrics: unaffected. The recommender is advisory. Old rubrics continue to load through `apply_rubric_mode_defaults` exactly as before.
- Existing CLI flows: unaffected. `make loop` does not invoke the recommender unless `--accept-recommender` is passed.
- Existing arch maps: extended, not rewritten.

---

## 6. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Operator-skill atrophy (seam §6 P2) | Recommender surfaces reasoning at confirm-time; operator must read why before applying |
| Aesthetic capture (seam §6 P4) | Embedding-based classifier (not LLM-judgment); cross-LLM consistency check on problem-class labels per GP-151 |
| Novel-substrate misclassification | Threshold-gated `novel=True` fallback; operator forced to hand-tune below threshold |
| Per-class N too small (seam §6 P3) | Phase B (mining) blocks Phase C until N ≥ 20 per class; otherwise classes ship as `low` confidence |
| Open-source release dilutes moat | Per seam §4.3: open-source the framework + interface; taxonomy stays operator-curated |
| Rubric loader regression | `make validate-rubric` runs in CI; backward-compat tests in §3 |

---

## 7. Acceptance criteria for Phase A (this turn)

- [x] Seam written
- [ ] Spec written (this file)
- [ ] Taxonomy artifact scaffolded with 6 classes (skeleton)
- [ ] Recommender module scaffolded with the interface in §2.2 (NotImplementedError body)
- [ ] Arch map updates (autoresearch_loop_architectural_map, rubric_authoring_map)
- [ ] AST parses + `make validate-rubric` passes against an existing rubric (e.g., `gp211_paper8_lean_proofs`)

When all six are checked, Phase A is complete. Phase B (mining) starts.

---

## 8. Cross-references

- Seam: `research_areas/private/seams/engine/GP-212_meta_solver_kernel_seam.md`
- Mining corpus: `analytics/public/ledgers/trajectory/trajectory_archive.jsonl` (2608 records as of 2026-05-04)
- Existing kernel: `src/ztare/validator/rubric_mode_resolver.py`, `src/ztare/validator/weakest_link_classifier.py`
- Rubric authoring: `docs/internal/agent_workflow/rubric_authoring_map.md`
- Anti-pattern catalog: `docs/concepts/anti_pattern_catalog.md`
- Cross-LLM constraint: `research_areas/private/seams/engine/GP-151_classifier_telemetry_downgrade_seam.md`
