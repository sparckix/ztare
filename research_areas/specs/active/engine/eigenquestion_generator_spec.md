# `eigenquestion_generator` — frontier-eigenquestion advisor — spec v0

**Parent seam:** `GP-213_operator_role_mechanization_seam.md` (director-mechanization).
**Companion seam:** `GP-228_substrate_portfolio_v05_v3_seam.md` (anti-anchoring composition).
**Status:** v0 spec written 2026-05-07; module shipped at `src/ztare/research_director/eigenquestion_generator.py`.

## 1. What this builds

A kernel module + Make target that drafts an advisory replacement eigenquestion for a substrate, structurally orthogonal to the substrate's prior-run primitive classes and anchored on its current mining-output snapshots.

- **Module:** `src/ztare/research_director/eigenquestion_generator.py`
- **Programmatic API:** `generate_eigenquestion(project_slug, model_id=None, out_path=None) -> Path`
- **Make target:** `make eigenquestion-propose PROJECT=<slug> [MODEL=<id>]`
- **Daemon hook:** `discover_substrate_portfolio_opportunities()` proposes `rotate-eigenquestion` candidates for substrates whose ledger shows ≥3 runs in one class

## 2. Why now

Family-attractor failure mode in `ztare_on_ztare_v2_expanded_scope` runs 1-5 (one primitive family across 5 runs). Score-cap rotation §22 + lane asymmetry §23 + adversarial-judge §24 + cross-substrate exclusion §25 attack the symptom (the mutator anchors on what scores well); this advisor attacks the root (the eigenquestion is fixed, so the mutator's basin is fixed).

Operator-confirmed advisory; never auto-modifies `project_charter.md`.

## 3. Inputs

The advisor reads (and only reads):
- `projects/<slug>/raw/*.json|md` — current mining-output snapshots
- `projects/<slug>/workspace/explored_primitive_classes.jsonl` — substrate's prior class history
- `projects/<slug>/project_charter.md` — extracts current Eigenquestion section

No write access to apparatus state. Only writes to `projects/<slug>/proposed_eigenquestion_<ts>.md`.

## 4. Output

A single markdown file at `projects/<slug>/proposed_eigenquestion_<ts>.md` containing:
- Proposed eigenquestion (one paragraph)
- Why it's orthogonal to explored families
- Anchored evidence (1-2 named snapshot files + JSONPath fragments)
- Expected candidate form (admissible mechanism types)
- Newton-mode secondary observable
- Falsifier (what next-week mining would refute candidates under this eigenquestion)

Operator decides whether to merge into `project_charter.md::Eigenquestion`.

## 5. Cost contract

Single LLM call. Default model picked by `pick_default_model_id_for_scripts()` (cheap-tier per provider). ~$0.005-0.01 per invocation. ~2K input tokens, ~2K output tokens. No timeout configured at spec level; `LLMRuntime` defaults apply.

## 6. Code references

| File | Function |
|---|---|
| `src/ztare/research_director/eigenquestion_generator.py` | `generate_eigenquestion`, `_build_prompt`, `_summarize_*` |
| `src/ztare/common/llm_runtime.py` | `LLMRuntime`, `pick_default_model_id_for_scripts` |
| `src/ztare/orchestration/work_discovery.py` | `discover_substrate_portfolio_opportunities` (rotate-eigenquestion) |

## 7. Dependencies

- GP-213 (director mechanization) — parent seam
- GP-228 (substrate-portfolio + anti-anchoring composition seam) — the WHY
- rubric_specification.md §27 — the architectural context (multi-charter portfolio + v3 meta-recursive)
