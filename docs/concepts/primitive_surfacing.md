---
description: "Reusable capabilities: how to STRUCTURE one (the engine/consumer invariant) and how to SURFACE it to the research-director precheck (the pipeline + SOP + staleness map). Counters primitive-amnesia (re-building tools that already exist) and frankenstein duplication. Verified against the live tree 2026-06-04."
---

## Reusable capabilities — structure (invariant) + surfacing (SOP)

This is the canonical reference for two coupled questions: how to STRUCTURE a reusable capability so there's exactly one of it (§0), and how to SURFACE it to a cold Research-Director (RD) session before it free-recalls or reinvents tools (§1–4). Every path is verified against the live tree (2026-06-04).

### 0. The engine/consumer invariant (structure before surfacing)

The canonical shape for any reusable capability — the rule that decides *what* gets surfaced:

1. **ONE canonical ENGINE per capability = the interface and the surfaced PRIMITIVE.** Examples: `ztare.fit.mdl.MDLLibrary` / `bic` / `bic_from_loglik`; `ztare.common.constraint_isomorphism.IsomorphismLoop`.
2. **A DOMAIN/CONSUMER is a Strategy PLUG, specialized by CONFIG/COMPOSITION** — pass a function/dataclass (a `size_fn`, an `oracle_fn`, a `failure_state`, a `forbidden_domain`), or at most subclass the GENERAL domain. **NEVER fork a parallel per-subject class/file.**
3. **A consumer/domain is NOT a primitive — do not register/surface it.** Surface only the engine + its general entry point. The precheck must return the ENGINE, not a per-subject wrapper.
4. **The SUBJECT (a substrate, a research seam, leanmill) is config/INPUT to the general domain, not its own domain.**

Worked unifications:
- The curve-fit BIC was inlined 3× → de-duped to `mdl.bic` (proven byte-identical), and `bic_from_loglik` is the general likelihood form with `bic` as the Gaussian special case.
- `fit/analogy.py` (ANALOGY: match any field) and `fit/cold_llm_erdos_seed.py` (DEANCHOR: forbid home + adjacent → the orthogonal jump) are two settings of `IsomorphismLoop`'s `forbidden_domain` knob (None vs set), **not two systems**.

Lived error (do not repeat): `LeanMillArchitectureDomain` was built as a parallel class AND surfaced as a primitive — wrong on both counts. Deleted; leanmill is now config (`failure_state` + future `oracle_fn`) to the general RD `ResearchDomain` / `surface_for_research_ceiling`. Corollary: the constraint-isomorphism "strange loop" is an **RD/architecture** tool that takes a SYSTEM ceiling as input — it does NOT run inside the solver per-proof (that was an overreach; a stuck proof needs a lemma/tactic, and the per-proof invent-mode was already reverted as non-probative).

### 1. System map

The pipeline has ONE source-of-truth catalog (`architecture_index.jsonl`), ONE semantic index built from it (`primitive_atlas_embeddings.json`), ONE ranking engine (`primitive_amnesia.precheck`), and ONE proactive briefing surface (`primitive_tick_surface`). Two human-facing artifacts (`capabilities.md`, `orchestration_menu.yaml`) sit alongside, hand-authored.

```
  CODE PRIMITIVES                          CURATED REGISTRATION
  ───────────────                          ────────────────────
  Auto-scanned dirs                        primitive_amnesia.py
  (PRIMITIVE_DIRS):                          PRIMITIVE_MODULES  (curated, incl.
   src/ztare/research_director                  common/constraint_isomorphism.py)
   src/ztare/validator/core                   WHEN_TO_USE        (effect-vocab aliases)
   src/ztare/motion                                │
   src/ztare/fit                                   │ populate_catalog()  (AST extract → append rows;
   src/ztare/leanmill/solver                       │   --repopulate = drop signature-bearing rows + re-add)
        │ (swept on populate)                       │
        └───────────────┬───────────────────────────┘
                        ▼
        ┌──────────────────────────────────────────────┐
        │  analytics/public/index/                       │   ◄── SOURCE OF TRUTH
        │  architecture_index.jsonl  (JSONL, append-only)│       id/path/kind/description/
        │  semi-auto: curated + populate_catalog appended│       applicability/impact_factor_expost/…
        └───────┬──────────────────────┬────────────────┘
                │                       │
   --build-atlas│                       │ render_architecture_index.py
   (embed as    ▼                       ▼
   RETRIEVAL_  ┌──────────────────────┐ ┌──────────────────────────────┐
   DOCUMENT)   │ primitive_atlas_     │ │ src/ztare/architecture_index/│
               │ embeddings.json      │ │   INDEX.md  (auto, lexical    │
               │ (768-dim, gemini-code)│ │   human view; CAN GO STALE)  │
               └──────────┬───────────┘ │   graph.yaml (MANUAL append) │
                          │             └──────────────────────────────┘
                          ▼
        ┌─────────────────────────────────────────────┐
        │ primitive_amnesia.precheck(query)            │  semantic-PRIMARY ranker
        │   query embedded as CODE_RETRIEVAL_QUERY     │  (asymmetric query/doc embedding)
        │   ASYMMETRIC vs doc embeddings = the lift     │  → lexical fallback if embedder dead
        └──────────────────────┬───────────────────────┘
                               │ imported as the ranking engine
                               ▼
        ┌─────────────────────────────────────────────┐
        │ primitive_tick_surface.build/write           │  proactive cold-RD briefing
        │   reads architecture_index.jsonl rows        │  (CONSUMER — does NOT scan src/)
        │   ranks via precheck() (sem dominates)        │
        └──────────────────────┬───────────────────────┘
                               ▼
        analytics/public/queries/rd_tick_primitive_surface.json   ◄── what a cold RD reads

  HUMAN/RD-FACING (hand-authored, parallel):
   docs/concepts/capabilities.md        ── narrative catalog of named primitives
   org/menu/orchestration_menu.yaml     ── RD pattern routing (problem_classes)
        ▲ fed by org/runtime/pattern_catalog.yaml (auto: pattern_catalog_indexer.py ← org/patterns/*.md)
```

Key wiring facts (verified in source):
- `primitive_tick_surface.py` is a READER/CONSUMER of `architecture_index.jsonl` (it imports `precheck` from `primitive_amnesia` and ranks by the semantic score; it does NOT scan `src/ztare/`). The try/except SILENTLY falls back to lexical if the embedder fails.
- The actual catalog BUILDER is `primitive_amnesia.populate_catalog()` — AST-extracts public defs/classes from `PRIMITIVE_MODULES` (explicit list) + `PRIMITIVE_DIRS` (5 swept dirs) and appends rows.
- `src/ztare/common/` is NOT in `PRIMITIVE_DIRS` — common-dir primitives are invisible to the sweep unless explicitly listed in `PRIMITIVE_MODULES` (this is why `constraint_isomorphism.py` is listed there by hand).

### 2. Canonical SOP to wire a NEW primitive

Decide the case:
- **Case (a):** primitive lives in an auto-scanned dir (`research_director`, `validator/core`, `motion`, `fit`, `leanmill/solver`) and is a public def/class.
- **Case (b):** primitive lives anywhere else (notably `src/ztare/common/`, `framer/`, `product_exports/`, top-level `experiment_stats.py`). NOT swept → must be named in `PRIMITIVE_MODULES`.

The noise filter (`_is_quality_primitive`) drops utility-named functions (`_*`, `*test*`, `parse`, `load`, `save`, `read`, `write`, `get_`, `set_`, `hash`, …) UNLESS the name is a key in `WHEN_TO_USE`. A high-value primitive with a generic name MUST get a `WHEN_TO_USE` entry to survive the sweep.

#### Case (a) — gate/miner/op in an auto-scanned dir
```bash
cd .
# 1. (recommended) add a WHEN_TO_USE effect-alias so a TASK-phrased query finds it.
# 2. register into the catalog:
python -m ztare.research_director.primitive_amnesia --repopulate
# 3. re-embed the atlas (semantic ranking, not just lexical):
python -m ztare.research_director.primitive_amnesia --build-atlas --embedder gemini-code
```

#### Case (b) — curated primitive in a NON-scanned dir (e.g. `src/ztare/common/`)
```bash
# 1. add "src/ztare/common/your_module.py" to primitive_amnesia.PRIMITIVE_MODULES.
# 2. add a WHEN_TO_USE alias (also sets impact_factor_expost=3 → ranks above swept=1).
# 3. clean re-register + 4. re-embed:
python -m ztare.research_director.primitive_amnesia --repopulate
python -m ztare.research_director.primitive_amnesia --build-atlas --embedder gemini-code
```

#### Both cases — propagate to the human-facing surfaces
```bash
# 5. refresh the rendered human/lexical index (routinely hours stale):
python scripts/public/control/render_architecture_index.py
# 6. refresh the proactive cold-RD briefing surface:
python -c "from src.ztare.research_director.primitive_tick_surface import write_primitive_tick_surface; write_primitive_tick_surface()"
```

#### If it is also a named CAPABILITY or an RD MOVE
- **Capability:** hand-add a subsection to `docs/concepts/capabilities.md` (name, one-line, module link, role). Entirely hand-written; no generator.
- **RD MOVE:** create `org/patterns/PATTERN-NNN_name.md` (frontmatter: `id`,`name`,`version`,`triggers`,`problem_classes`,`spawn`) → `python -m src.ztare.orchestration.pattern_catalog_indexer` (writes `org/runtime/pattern_catalog.yaml`, NEVER hand-edit it) → hand-wire the trigger into `org/menu/orchestration_menu.yaml`.

#### Verification (do not skip — a "no match" on a dead embedder is INADMISSIBLE)
```bash
python -m ztare.research_director.primitive_amnesia --semantic-live    # expect SEMANTIC_LIVE=true
python -m ztare.research_director.primitive_amnesia "<problem described in TASK language>"  # primitive in top-k
python -m ztare.research_director.primitive_amnesia --eval             # recall@5 target 1.0 (<0.9 = atlas drift)
```

### 3. Staleness & health

Regen commands: jsonl → `--repopulate`; atlas → `--build-atlas`; INDEX.md → `render_architecture_index.py`; rd_tick surface → `write_primitive_tick_surface()`; pattern_catalog → `pattern_catalog_indexer`; `graph.yaml` is MANUAL.

| Artifact | Auto/Manual | Stale when | 
|---|---|---|
| `architecture_index.jsonl` | semi-auto (curated + populate) | a `PRIMITIVE_MODULES`/dir primitive is absent (`grep`) |
| `primitive_atlas_embeddings.json` | auto (`--build-atlas`) | jsonl newer than atlas, or a row has no embedding (silently lexical); `--eval` < 1.0 |
| `rd_tick_primitive_surface.json` | auto (`write_primitive_tick_surface`) | mtime < jsonl mtime |
| `INDEX.md` | auto (`render_architecture_index`) | mtime < jsonl mtime (routinely ~2h behind) |
| `graph.yaml` | MANUAL append-only | `last_updated` field vs live work |
| `capabilities.md` / `orchestration_menu.yaml` | MANUAL | module paths drift / `rd_pattern_audit` reconciliation |

**Embedder requirement:** semantic ranking needs a live embedder — `gemini`/`gemini-code` (`GEMINI_API_KEY`/`GOOGLE_API_KEY`) or `openai` (`OPENAI_API_KEY`). Default `gemini-embedding-001`, 768-dim, ASYMMETRIC (docs as `RETRIEVAL_DOCUMENT`, queries as `CODE_RETRIEVAL_QUERY`). Without a key the whole pipeline degrades to lexical-only (recall ~0.67 vs semantic 1.0). Positive control: `--semantic-live` (and `src/ztare/common/embedder_liveness.py`).

### 4. Gotchas

1. **`src/ztare/common/` is NOT auto-swept** — add the module to `PRIMITIVE_MODULES` by hand (done for `constraint_isomorphism.py`). Same for `framer/`, `product_exports/`, top-level files.
2. **Lexical fallback is SILENT in both consumers.** A dead embedder produces a degraded ranking with no error — a "no primitive matched" under a dead embedder is INADMISSIBLE. Always `--semantic-live` before trusting a negative.
3. **A row added without re-embedding is lexically visible but NOT semantically ranked.** Always pair `--repopulate`/`--populate-catalog` with `--build-atlas`.
4. **`INDEX.md` ≠ `jsonl`.** INDEX.md is an auto-rendered, hours-stale human view; the precheck reads the jsonl + atlas. Never judge "is my primitive registered?" from INDEX.md.
5. **Noise filter silently drops generic names** unless they have a `WHEN_TO_USE` alias.
6. **Curated outranks swept by design** (`impact_factor_expost=3` for aliased primitives vs `1`).
7. **`--repopulate` only drops rows it added** (those carrying a `signature` field); curated/non-tool rows untouched.
8. **`pattern_catalog.yaml` is generated — never hand-edit;** patch `org/patterns/*.md` and re-run the indexer. `org/` must never import ZTARE (one-way: the indexer lives in `src/ztare/`).
