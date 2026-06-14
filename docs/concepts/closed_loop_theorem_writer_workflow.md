---
description: "The four-stage closed loop turning LLM-nominated Lean theorems into verified proofs."
---
# Workflow: Closed-Loop Theorem-Writer Pipeline

> **Up:** [Documentation map](../README.md)

**Status:** shipped 2026-05-05; minimum viable form (Stages 1-4 of the full theorem-writer roadmap Codex articulated). Operates as a complement to hand-written proofs, not a replacement.
**Companion doc:** [`graph_diagnostic_belief_update_pattern.md`](graph_diagnostic_belief_update_pattern.md), the underlying pattern this pipeline operationalizes.

---

## What this pipeline is

A four-stage closed loop that takes LLM-nominated Lean theorems, filters / verifies / revises them, and emits two artifacts:

- **VERIFIED:** lake-build-accepted theorems (still need Codex review for triviality / mathematical meaning).
- **UNVERIFIABLE:** failed nominations + their revision history, used as training data for prompt calibration.

The pipeline does *not* generate proofs from scratch. It mechanizes the Codex-articulated insight: **"For graph+LLM to become a theorem writer, it needs a compiler-checked loop: graph nominates a typed theorem, Lean proves or refutes it, and the graph records the proof/falsifier outcome."**

---

## When to use

Use when:
- Spine is mostly built; specific open obligations need new lemmas.
- You want a verified-or-falsified inventory rather than hand-checking each LLM nomination.
- You're prepared to discard trivially-VERIFIED outputs (the loop accepts `theorem trivial : 0 ≤ 1` too).

Don't use when:
- Writing the spine from scratch (no graph yet).
- Doing exploratory math (loop only verifies, doesn't explore).
- Obligation needs orientation surgery the LLM can't see (e.g. Codex's `cross*` → `positivePart cross*` correction class, those are domain-expert calls).

---

## Cadence

- **Per closure-attempt:** 2-3 runs over a multi-day closure attempt; complement to Codex's hand-written work.
- **NOT per-iter:** this is RD / Codex tooling, not a ZTARE-loop component.
- **Cap:** 5-10 nominations per run. Each takes ~3 minutes (3 lake builds × ~60s). Larger batches scale linearly.

---

## Preconditions

```bash
# 1. Constraint graph fresh
python scripts/public/projects/ns/ns_graphs.py all

# 2. Decl index fresh (1724 declarations across 169 files at last build)
python scripts/public/lean/lean_decl_index.py --build

# 3. Lake build clean on current spine
cd ztare_proofs && lake build && cd ..
```

---

## Pipeline stages

| Stage | Purpose | Cost | Owner |
|---|---|---|---|
| 1 | Typed nomination filter | Zero compute (regex over decl index) | Apparatus |
| 2 | Orientation synthesizer (separate script) | Seconds (regex over Lean source) | Apparatus |
| 3 | lake build verification | ~60s per attempt | Apparatus |
| 4 | Learning summary | Trivial aggregation | Apparatus → Codex review |

### Stage 1, Typed nomination filter

`scripts/public/lean/lean_decl_index.py` builds a regex-extracted index of all theorems / lemmas / defs / structures / classes / instances in `ztare_proofs/ZtareProofs/`. Each LLM nomination is scanned for identifiers; any not in the index is flagged.

**Output:** valid / invalid + list of unresolved identifiers.

**Why it matters:** catches the `cross*` vs `positivePart cross*` error class deterministically *before* burning lake build time. The regex-based check is approximate (qualified-name edge cases can produce false positives) but in practice catches the majority of LLM-fabricated identifier names.

### Stage 2, Orientation synthesizer

`scripts/public/projects/ns/orientation_synthesizer.py`, separate entry point, produces typed-search candidates from transitivity chains in the constraint-basin graph. For each `(a → b → c)` triple where `a → c` is missing, it looks up the source theorems for `a → b` and `b → c` and extracts their hypothesis chains via regex.

Default output is not a Lean nomination. Graph quantity names are often not Lean terms, so the closed-loop theorem writer ignores rows marked `candidate_status: "search_candidate_only"`. Use `--emit-lean-skeletons` only when you explicitly want a `by exact le_trans (?lemma_a) (?lemma_b)` scaffold sent into the verifier/failure-learning loop.

**Output:** `projects/ns_millennium_hunt/workspace/queries/orientation_synthesized_candidates.jsonl`.

### Stage 3, lake build verification (the closed loop)

For each nomination passing Stage 1:
1. `lean_proof_gate.write_lean_target()` writes to `ztare_proofs/ZtareProofs/closed_loop_<name>_iter.lean`
2. `lean_proof_gate.compile_lean()` runs `lake build`
3. If compiled → VERIFIED, exit loop
4. If failed → capture stderr, ask Gemini to revise with the error as falsifier feedback
5. Repeat up to `--max-revisions` times (default 3)

### Stage 4, Learning summary

After each run, aggregate the closed-loop log:
- `verification_rate` (verified / total)
- `top_unresolved_idents`, most common Stage-1 rejections across nominations
- `top_lake_errors`, most common Stage-3 error categories

**Output:** `analytics/public/queries/closed_loop/closed_loop_log.learning.json`.

This is descriptive only, no closed feedback to Gemini's prompt yet. Future work: condition the next iteration's nomination prompt on the aggregated learning signal.

---

## Entry points

```bash
# Default: runs llm_graph_analyst.py to gather nominations from Gemini
./venv/bin/python scripts/public/analytics_shared/llm_theorem_closed_loop.py --max-revisions 3

# Use a hand-curated nominations file with real Lean blocks
./venv/bin/python scripts/public/analytics_shared/llm_theorem_closed_loop.py \
    --nominations-file projects/ns_millennium_hunt/workspace/queries/llm_graph_analyst_output.md \
    --max-revisions 3

# To use orientation_synthesizer as closed-loop input, opt into Lean skeletons
./venv/bin/python scripts/public/projects/ns/orientation_synthesizer.py --top 10 --emit-lean-skeletons
./venv/bin/python scripts/public/analytics_shared/llm_theorem_closed_loop.py \
    --nominations-file projects/ns_millennium_hunt/workspace/queries/orientation_synthesized_candidates.jsonl \
    --max-revisions 0

# Smoke test without invoking lake (verify pipeline wiring)
./venv/bin/python scripts/public/analytics_shared/llm_theorem_closed_loop.py --dry-run
```

---

## Codex intervention points

### After VERIFIED nominations

Just because lake-build accepts doesn't mean the theorem is mathematically meaningful, `theorem trivial : 0 ≤ 1 := by linarith` would also be VERIFIED. Codex decides which verified-but-trivial nominations to discard vs. which to add to the spine permanently.

### After UNVERIFIABLE nominations

The revision history is the falsifier log. For each:
- If the same identifier keeps appearing as unresolved across many nominations → **vocabulary calibration finding** (apparatus is using outdated names).
- If lake errors cluster around the same type-mismatch class → **domain ground-truth finding** (LLM is missing a structural invariant Codex has internalized).

Either type of finding feeds back into the next iteration's nomination prompt (manually for now; Stage 4 closed feedback is future work).

---

## Caveats and limitations

- **Stage 1 is regex-based**, not Lean elaboration; misses qualified-name resolution edge cases (false-positive unresolved idents possible).
- **Stage 2 produces scaffolds**, not finished proofs. Codex must resolve `?lemma_name` placeholders to actual term-mode references.
- **Stage 3 trusts lake build as ground truth.** If the spine has unsoundness elsewhere, this propagates.
- **Stage 4 is descriptive only**; no closed feedback to Gemini's prompt yet. Each run starts cold.
- **Pipeline does not catch "trivially true but useless" theorems**; Codex's review remains central for filtering meaningful additions.
- **Decl index is regex-extracted**, not Lake-elaborated; rebuild via `--build` if the spine has been edited recently.

---

## Files / call-sites

- Entry: `scripts/public/analytics_shared/llm_theorem_closed_loop.py`
- Stage 1 dependency: `scripts/public/lean/lean_decl_index.py` + `analytics/public/queries/lean/lean_decl_index.json`
- Stage 2 (separate script): `scripts/public/projects/ns/orientation_synthesizer.py` + `projects/ns_millennium_hunt/workspace/queries/orientation_synthesized_candidates.jsonl`
- Stage 3 backend: `src/ztare/gates/lean_proof_gate.py` (`write_lean_target` + `compile_lean`)
- Output log: `analytics/public/queries/closed_loop/closed_loop_log.jsonl`
- Learning signal: `analytics/public/queries/closed_loop/closed_loop_log.learning.json`
- Companion analyst: `scripts/public/projects/ns/llm_graph_analyst.py` (Gemini 3 Pro)
- Underlying pattern: `docs/concepts/graph_diagnostic_belief_update_pattern.md`
- Director duty: `org/mandates/research_director_mandate.md` §Per-closure-attempt review
