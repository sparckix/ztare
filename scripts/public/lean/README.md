# scripts/public/lean/

> **Up:** [scripts/](../../README.md) · **Siblings:** [models/](../models/README.md) · [control/](../control/README.md) · [validators/](../validators/README.md)

Lean proof-search support for the NS / GP-216 / GP-223-224 lines. These
drive prover runs, type and route the gaps, mine what the prover cannot
do, and gate the result. The typed-endpoint group is the architecture
that replaced "let the LLM invent any theorem" with "bind the LLM to a
named endpoint shape", which moved closure from 0/22 to a measurable
rate.

## Provers and candidate generation

| Script | What it does |
|---|---|
| `auto_prover_harness.py` | GP-216f scale-8 auto-prover: wraps any Lean-aware neural prover (DeepSeek-Prover-V2, LeanCopilot, LLM-as-prover) over closure obligations. |
| `llm_lean_prover.py` | Option D, long-context LLM-as-prover with Lean verification (instead of LoRA-fine-tuning DSP-V2). |
| `batched_candidate_generator.py` | K candidates in parallel, accept any that pass, instead of serial generate-fail-revise-retry. |
| `decomposition_candidate_enumerator.py` | Lightweight Lean source probe: enumerate candidates that may decompose a structure field (not a full elaborator). |
| `lean_tactic_hammer.py` | Try `exact?` / `aesop` / `polyrith` / `linarith` / `omega` before spending an LLM call (Lean already has trained tactic search). |

## Typed-endpoint architecture (Codex 10x)

| Script | What it does |
|---|---|
| `typed_endpoint_pack.py` | Typed endpoint-bound context pack: supersedes `typed_patch_proposer.py` by binding the LLM to a fixed Lean shape. |
| `typed_patch_proposer.py` | Earlier typed-first proposer (the refuted "LLM proposes any novel theorem" approach; kept as the lineage baseline). |
| `typed_endpoint_queue.py` | GP-224 Option B scaffold-only opt-in work queue; not the default execution path. |
| `typed_endpoint_agent_panel.py` | Builds zero-spend Codex read-only audit panels from a structure-instantiation workmap (scheduling artifact, not an LLM caller). |
| `typed_endpoint_agent_panel_harvest.py` | Companion that records / harvests the results of those zero-spend panels. |
| `structure_instantiation_workmap.py` | CLI wrapper for the NS Track B structure-instantiation workmap (implementation lives with the NS workspace). |
| `gap_typed_prompter.py` | CLI wrapper for gap typing + Mathlib shelf dispatch; reusable taxonomy/classifier lives in `src/ztare/research_director/gap_typing.py`. |
| `patch_class_selector.py` | Meta-prompt that picks the patch class, removing operator judgment from the typed-endpoint loop. |

## Indexing and retrieval

| Script | What it does |
|---|---|
| `lean_decl_index.py` | Stage-1 typed nomination filter: index every declaration in `ztare_proofs/` for the closed loop. |
| `mathlib_lemma_scout.py` | Index `Mathlib.Analysis.*` and friends by type shape (pre-curated lemma library matching). |
| `extract_mathlib_graph.py` | Extract the mathlib4 dependency graph for v4 GNN pre-training. |
| `mine_mathlib_pairs.py` | Mine (theorem, used-lemmas) pairs from mathlib4 itself (about 50x more training data than the spine). |
| `build_mathlib_atlas_embeddings.py` | Gemini-embedding-001 atlas over the full Mathlib lemma index (~46K entries). Resumable (checkpoint every 1000) with 429 retry-on-quota. Output consumed by the kernel primitive `src/ztare/research_director/mathlib_semantic.py`. Use `--untagged-only`, `--analysis-only`, or `--subdir` for narrower selections. |
| `calibrate_mathlib_atlas.py` | Internal retrieval-quality calibration for the built atlas: family-cohesion (same-subdir top-10) and cross-family separation against analysis-classic anchors. Run after each atlas rebuild. |

## Gates, compile, diagnostics

| Script | What it does |
|---|---|
| `verify_lean_stub.py` | GP-135 P4 Lean stub verifier with an axiom allowlist (a `lake build` success is not a proof if it rides an axiom). |
| `proof_closure_candidate_gate.py` | Deterministic, domain-light gate for proof-closure strategy candidates emitted as one fenced JSON object. |
| `endpoint_type_compression_audit.py` | GP-223 Layer-3 post-hoc audit: deterministic compression check over recent typed_endpoint failures and verified patches. |
| `lean_fast_compile.py` | Faster compile via `lake env lean <file>` instead of full `lake build <module>` per call. |
| `cannot_patch_harvester.py` | Mines LLM `# CANNOT PATCH` refusals: the diagnosis paragraph names a missing primitive, which feeds the primitive backlog. |

## Related

- Learned rankers that consume this output: [models/](../models/README.md)
- Pinned Lean sandboxes (gitignored, must not be purged): `analytics/public/leanmill/external_benchmarks/` (v4.29.0 Carleson)
- Concept: [the cognitive gym](../../../docs/concepts/cognitive_gym.md)
