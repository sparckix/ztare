---
description: "Codex-facing procedure for the apparatus closure-utility test."
---
# Workflow: Apparatus Closure-Utility Test (for Codex)

> **Up:** [Documentation map](../README.md)

**Purpose:** measure whether the graph-diagnostic apparatus delivers nominations Codex would not have considered (real surprise) vs. nominations he already had (confirmation theater). The closure-utility test, distinct from the predictive-MRR test that v3 GNN passed at MRR 0.43.

---

## TL;DR

1. Apparatus produces a CSV of nominations from multiple sources.
2. Codex marks each row's `codex_verdict` (5-way label).
3. A metric script computes `novelty_rate` per source + aggregate.
4. Verdict: `> 30%` = real surprise; `5-30%` = mixed; `< 5%` = confirmation theater.

---

## The two novelty tools, when to use each

There are two "novelty" tools that produce different kinds of signal. They are NOT redundant; use both.

### Tool 1: LLM novelty (`scripts/public/analytics_shared/llm_novelty_nomination.py`)

**What it does:** re-prompts Gemini + Claude with an adversarial novelty prompt. Instead of "nominate plausible theorems", it asks "nominate theorems Codex would NOT have considered, surprising structural pairings, cross-cluster bridges, receipt-tree outliers."

**Output:** `analytics/public/queries/novelty/novelty_nominations/{gemini,claude}_novelty_raw.md`, 3 nominations each, each a Lean signature + justification citing structural signals.

**When to use:** when you want SEMANTIC + STRUCTURAL novelty. The LLM reads the structural diagnostics AND has training-data intuitions about what's mathematically surprising. Output tends to be high-level and conceptual ("viscosity should bound shell-level dissipation").

**Empirically measured (2026-05-06):** 0% overlap with standard-prompt nominations on both providers. Cross-LLM agreement: both nominated viscosity-to-sharpTarget bridges (the structurally-disconnected pair). The novelty prompt shifts the output distribution away from the standard prompt.

**Run cost:** ~30 sec, two API calls. ~$0.02.

### Tool 2: GNN novelty (`scripts/public/models/gnn_novelty_filter.py`)

**What it does:** re-ranks v3 GNN top-K predictions by overlap with (a) existing decl names, (b) recent F-row mentions, (c) open-obligation field names. Surfaces predictions that score high on the GNN but have LOW overlap with known vocabulary.

**Output:** `analytics/public/queries/novelty/gnn_v3_novelty_ranked.md`, table of (src, op, dst) candidates with GNN score, overlap, AA score.

**When to use:** when you want STRUCTURAL novelty grounded in the graph topology. The GNN doesn't "know" what a theorem looks like; it knows which nodes are structurally close in the constraint graph. Output tends to be low-level and edge-specific ("`B.qform ≤ rightPrice` is structurally likely but not in the spine").

**Honest caveats:**
- Vocabulary alignment is approximate (camelCase word match). Some plumbing leaks through.
- 24/25 predictions in early runs had AA = 0 (no shared neighbors), the GNN's high-confidence predictions tend to be embedding-space artifacts. **Always cross-check the AA column** (`✓` = AA-confirmed, `?` = no structural support).

**Run cost:** seconds (CPU). $0.

### Are both needed, or just one?

**Both, because they probe different signal types:**

| Tool | Surfaces | Limitation |
|---|---|---|
| LLM novelty | Conceptual / semantic surprise (e.g. "viscosity should connect to sharpTarget") | High-level; you have to translate to Lean signatures |
| GNN novelty | Edge-level structural surprise (e.g. "B.qform ≤ rightPrice missing") | Low-level; vocabulary gap and embedding artifacts |

When LLM and GNN converge on the same target quantity, two independent methods agree on it. When they diverge, you get two independent priors to evaluate.

**If you only have time for one:** start with LLM novelty. Output is more directly actionable as Lean proposals. Use GNN novelty as a second-pass tiebreaker on quantities the LLM mentioned.

---

## The CSV task, what Codex needs to do

### File: `analytics/public/queries/novelty/codex_nomination_panel.csv`

Built by `scripts/public/analytics_shared/build_codex_nomination_panel.py`. Aggregates today's apparatus output:

- 10 transitivity-closure top candidates
- 3 Gemini standard nominations
- 3 Claude standard nominations
- 3 Gemini novelty-prompted nominations
- 3 Claude novelty-prompted nominations
- (when available) v3 GNN top-K novelty-filtered

For each row, fill the `codex_verdict` column with ONE of:

| Verdict | Meaning |
|---|---|
| `already_considered` | You'd already thought of this (or something equivalent) |
| `novel_plausible` | Real new candidate worth a lake-build attempt |
| `wrong` | Dimensionally / structurally wrong as stated |
| `trivial` | True but adds no closure value (e.g. trivial corollaries) |
| `cant_classify` | Needs more context to judge |

Optionally fill `codex_notes` with brief reasoning.

### How long this should take

- ~22 nominations
- ~30 seconds per nomination = ~10 min total
- Don't over-engineer; gut-call is fine. The metric robust to small-N noise.

### After marking

```bash
python scripts/public/analytics_shared/compute_closure_utility.py
```

Outputs:
- Per-source `novelty_rate` (which apparatus is most surprising)
- Per-source `wrong_rate` (which apparatus most hallucinates)
- Aggregate metric + verdict

### What the verdict means

- **`novelty_rate > 30%`** → **REAL SURPRISE.** Apparatus delivers candidates Codex genuinely wouldn't have considered. Should be promoted to a routine pre-closure-attempt step.
- **`novelty_rate 5-30%`** → **MIXED.** Some real signal, some confirmation theater. Use selectively.
- **`novelty_rate < 5%`** → **CONFIRMATION THEATER.** Apparatus mostly rediscovers known. Closure work doesn't need it; v3 finding (predictive accuracy ≠ closure utility) confirmed at scale.

---

## Operational cadence

| When | Action |
|---|---|
| Per closure-attempt | Run LLM novelty; review nominations; mark CSV if running the panel |
| Weekly | Run the full panel build, mark CSV, compute metric, log to F-row |
| If verdict flips | Update RD mandate v1.2x with the new closure-utility evidence |

---

## Scripts shipped (2026-05-06)

| Script | Purpose |
|---|---|
| `scripts/public/analytics_shared/llm_novelty_nomination.py` | LLM novelty prompt (Gemini + Claude) |
| `scripts/public/models/gnn_novelty_filter.py` | GNN v3 novelty filter (with vocabulary alignment + plumbing strip) |
| `scripts/public/analytics_shared/build_codex_nomination_panel.py` | Aggregates all sources into Codex-rateable CSV |
| `scripts/public/analytics_shared/compute_closure_utility.py` | Reads marked CSV, computes novelty_rate metric |

## Related docs

- `docs/concepts/graph_diagnostic_belief_update_pattern.md`, the underlying methodology + Codex's "predictive accuracy ≠ closure utility" finding
- `docs/concepts/closed_loop_theorem_writer_workflow.md`, the lake-build verifier that NOM rows tagged `novel_plausible` should next pass through
- `org/mandates/research_director_mandate.md` v1.47, RD duties on graph-diagnostic apparatus, PDE anti-grind review, sequential graph-refresh / compatibility-structure visibility, paid-proof discipline for `Prop`-valued source declarations, source-first/generated-block/source-wrapper/projection-compression rules, failure-cluster patch-class invalidation, zero-spend Codex-agent typed-endpoint panels before paid queue/swarm promotion, and the ZTARE/RD split: RD callers reuse core ZTARE theory-building/falsifier primitives instead of recreating them.
