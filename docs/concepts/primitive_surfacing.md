---
description: "How reusable code capabilities enter the primitive catalog, semantic atlas, and Research Director briefing without duplicating implementations."
---

## Reusable capabilities and primitive surfacing

When the repo already has a useful capability, how does a cold Research
Director find it and reuse it?

There are two parts. First, the capability should have one general engine with
many consumers configuring it, so each subject stays a caller of that single
engine. Second, that engine must
enter the catalog, semantic atlas, and RD briefing surface, otherwise it exists
in code but not in memory.

### 0. The Engine/Consumer Rule

Use this rule to decide what gets surfaced:

1. One engine per capability. The engine is the interface and the primitive
   worth surfacing. Examples: `ztare.fit.mdl.MDLLibrary`, `bic`,
   `bic_from_loglik`, and `ztare.common.constraint_isomorphism.IsomorphismLoop`.
2. Consumers specialize the engine by configuration or composition. Pass a
   function/dataclass such as `size_fn`, `oracle_fn`, `failure_state`, or
   `forbidden_domain`. Do not fork a parallel per-subject implementation.
3. The primitive worth surfacing is the engine, reached through its general
   entry point. A consumer or subject-specific wrapper sits one layer above it
   and stays out of the catalog.
4. The subject is input. A substrate, research seam, or LeanMill use case
   configures the general domain and does not become its own domain by default.

Worked unifications:
- The curve-fit BIC was inlined 3× → de-duped to `mdl.bic` (proven byte-identical), and `bic_from_loglik` is the general likelihood form with `bic` as the Gaussian special case.
- `fit/analogy.py` (ANALOGY: match any field) and `fit/cold_llm_erdos_seed.py` (DEANCHOR: forbid home + adjacent → the orthogonal jump) are one system under two settings of `IsomorphismLoop`'s `forbidden_domain` knob (None vs set).

Lived error (do not repeat): `LeanMillArchitectureDomain` was built as a parallel class AND surfaced as a primitive, wrong on both counts. Deleted. Leanmill is now config (`failure_state` + future `oracle_fn`) to the general RD `ResearchDomain` / `surface_for_research_ceiling`. Corollary: the constraint-isomorphism "strange loop" is an RD/architecture tool that takes a SYSTEM ceiling as input. It does NOT run inside the solver per-proof (that was an overreach: a stuck proof needs a lemma/tactic, and the per-proof invent-mode was already reverted as non-probative).

### 1. System Map

The pipeline has one catalog (`architecture_index.jsonl`), one generated
taxonomy layer (`primitive_catalog_taxonomy.py`), one semantic index
(`primitive_atlas_embeddings.json`), one ranking engine
(`primitive_amnesia.precheck`), and one proactive briefing surface
(`primitive_tick_surface`). Two human-facing artifacts, `capabilities.md` and
`orchestration_menu.yaml`, sit alongside as hand-authored guides.

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
                │ taxonomy              │
                ▼                       │
        primitive_catalog_taxonomy.py    │
        source_category + semantic_family│
        catalog health + parent nodes    │
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
        │   semantic score + lexical tiebreak          │  → lexical fallback if embedder dead
        └──────────────────────┬───────────────────────┘
                               │ imported as the ranking engine
                               ▼
        ┌─────────────────────────────────────────────┐
        │ primitive_tick_surface.build/write           │  proactive cold-RD briefing
        │   reads architecture_index.jsonl rows        │  (CONSUMER, does NOT scan src/)
        │   ranks via precheck() (sem dominates)        │
        │   adds semantic parent nodes from             │
        │   primitive_family_registry.py                │
        └──────────────────────┬───────────────────────┘
                               ▼
        analytics/public/queries/rd_tick_primitive_surface.json   ◄── what a cold RD reads

  HUMAN/RD-FACING (hand-authored, parallel):
   docs/concepts/capabilities.md        ── narrative catalog of named primitives
   org/menu/orchestration_menu.yaml     ── RD pattern routing (problem_classes)
        ▲ fed by org/runtime/pattern_catalog.yaml (auto: pattern_catalog_indexer.py ← org/patterns/*.md)
```

Key wiring facts (verified in source):
- `primitive_tick_surface.py` is a READER/CONSUMER of `architecture_index.jsonl` (it imports `precheck` from `primitive_amnesia` and ranks by the semantic score; it does NOT scan `src/ztare/`). The try/except silently falls back to lexical if the embedder fails.
- The actual catalog BUILDER is `primitive_amnesia.populate_catalog()`, which AST-extracts public defs/classes from `PRIMITIVE_MODULES` (explicit list) + `PRIMITIVE_DIRS` (5 swept dirs) and appends rows.
- `src/ztare/common/` is NOT in `PRIMITIVE_DIRS`. Common-dir primitives are invisible to the sweep unless explicitly listed in `PRIMITIVE_MODULES` (this is why `constraint_isomorphism.py` is listed there by hand).
- `primitive_catalog_taxonomy.py` is the full-catalog generated taxonomy. It derives `source_category` (implementation location) and `semantic_family` (research role), exposes catalog parent nodes, and checks duplicate/stale surfaces. It does not rewrite identity or ownership of rows.
- `primitive_family_registry.py` is the narrower LLM-mediated PARENT-NODE overlay. It groups dispatchable LLM/agent workers into MECE families (`core_workbench_worker`, `external_perspective_generator`, `review_governance_helper`, `composition_helper`) and preserves each child module/path identity so the atlas and architecture index do not drift. Its `--check` mode validates that card module paths and entrypoints still exist.
- Embeddings and subscription agents may propose related-capability edges, but they should not own the ontology. Promotion into taxonomy should be a deterministic rule or explicit curated mapping. Dynamic semantic pairing belongs in review reports until stabilized.

### 2. How To Wire A New Primitive

Decide the case:
- Case (a): primitive lives in an auto-scanned dir (`research_director`, `validator/core`, `motion`, `fit`, `leanmill/solver`) and is a public def/class.
- Case (b): primitive lives anywhere else (notably `src/ztare/common/`, `framer/`, `product_exports/`, top-level `experiment_stats.py`). It is not swept automatically, so name it in `PRIMITIVE_MODULES`.

The noise filter (`_is_quality_primitive`) drops utility-named functions (`_*`, `*test*`, `parse`, `load`, `save`, `read`, `write`, `get_`, `set_`, `hash`, ...), unless the name is a key in `WHEN_TO_USE`. A high-value primitive with a generic name needs a `WHEN_TO_USE` entry to survive the sweep.

#### Case (a): gate/miner/op in an auto-scanned dir
```bash
cd .
# 1. (recommended) add a WHEN_TO_USE effect-alias so a TASK-phrased query finds it.
# 2. register into the catalog:
python -m ztare.research_director.primitive_amnesia --repopulate
# 3. re-embed the atlas (semantic ranking, not just lexical):
python -m ztare.research_director.primitive_amnesia --build-atlas --embedder gemini-code
# 4. check the generated taxonomy / duplicate / freshness surface:
python -m ztare.research_director.primitive_catalog_taxonomy
```

#### Case (b): curated primitive in a NON-scanned dir (e.g. `src/ztare/common/`)
```bash
# 1. add "src/ztare/common/your_module.py" to primitive_amnesia.PRIMITIVE_MODULES.
# 2. add a WHEN_TO_USE alias (also sets impact_factor_expost=3 → ranks above swept=1).
# 3. clean re-register + 4. re-embed:
python -m ztare.research_director.primitive_amnesia --repopulate
python -m ztare.research_director.primitive_amnesia --build-atlas --embedder gemini-code
```

#### Both cases: propagate to the human-facing surfaces
```bash
# 5. refresh the rendered human/lexical index (routinely hours stale):
python scripts/public/control/render_architecture_index.py
# 6. refresh the proactive cold-RD briefing surface:
python -c "from ztare.research_director.primitive_tick_surface import write_primitive_tick_surface; write_primitive_tick_surface()"
```

#### If it is also a named CAPABILITY or an RD MOVE
- Capability: hand-add a subsection to `docs/concepts/capabilities.md` (name, one-line, module link, role). Entirely hand-written with no generator.
- RD MOVE: create `org/patterns/PATTERN-NNN_name.md` (frontmatter: `id`,`name`,`version`,`triggers`,`problem_classes`,`spawn`) → `python -m ztare.orchestration.pattern_catalog_indexer` (writes `org/runtime/pattern_catalog.yaml`; do not hand-edit the generated file), then hand-wire the trigger into `org/menu/orchestration_menu.yaml`.

#### Verification

A "no match" result is not useful if the embedder is dead. In that case the
system has fallen back to lexical search.
```bash
python -m ztare.research_director.primitive_amnesia --semantic-live     # expect SEMANTIC_LIVE=true
python -m ztare.research_director.primitive_amnesia --atlas-status       # expect ATLAS_STATUS status=ok
python -m ztare.research_director.primitive_catalog_taxonomy             # expect CATALOG_HEALTH status=ok
python -m ztare.research_director.primitive_amnesia "<problem described in TASK language>"  # primitive in top-k
python -m ztare.research_director.primitive_amnesia --eval             # report current recall@k/MRR; inspect misses
python -m ztare.research_director.primitive_amnesia --eval --record-misses  # append semantic misses to analytics/public/queries/primitive_amnesia_miss_queue.jsonl
```

### 3. Staleness & health

Regen commands: jsonl/taxonomy fields → `--repopulate`, atlas → `--build-atlas`, taxonomy/duplicate/staleness check → `primitive_catalog_taxonomy`, INDEX.md → `render_architecture_index.py`, rd_tick surface → `write_primitive_tick_surface()`, pattern_catalog → `pattern_catalog_indexer`. `graph.yaml` is MANUAL.

| Artifact | Auto/Manual | Stale when | 
|---|---|---|
| `architecture_index.jsonl` | semi-auto (curated + populate) | a `PRIMITIVE_MODULES`/dir primitive is absent (`grep`) |
| generated taxonomy fields | auto (`primitive_catalog_taxonomy.enrich_row` via `--repopulate`) | rows lack `source_category` / `semantic_family`, or `primitive_catalog_taxonomy` reports duplicates/missing paths |
| `primitive_atlas_embeddings.json` | auto (`--build-atlas`) | jsonl newer than atlas, catalog digest mismatch, a row has no embedding, `--semantic-live` fails, or `--eval` misses point to absent/stale catalog rows |
| `rd_tick_primitive_surface.json` | auto (`write_primitive_tick_surface`) | mtime < jsonl mtime |
| `INDEX.md` | auto (`render_architecture_index`) | mtime < jsonl mtime (routinely ~2h behind) |
| `graph.yaml` | MANUAL append-only | `last_updated` field vs live work |
| `capabilities.md` / `orchestration_menu.yaml` | MANUAL | module paths drift / `rd_pattern_audit` reconciliation |

*Embedder requirement:* semantic ranking needs a live embedder:
`gemini`/`gemini-code` (`GEMINI_API_KEY`/`GOOGLE_API_KEY`) or `openai`
(`OPENAI_API_KEY`). The default is `gemini-embedding-001`, 768-dimensional,
with asymmetric task types: docs as `RETRIEVAL_DOCUMENT`, queries as
`CODE_RETRIEVAL_QUERY`. Without a key the pipeline degrades to lexical-only.
Positive control: `--semantic-live` and `src/ztare/common/embedder_liveness.py`.

On 2026-06-12 after target-resolvability hardening, the live held-out eval
reported `n=29`, `resolvable=29`, `k=5`, lexical recall@5 `0.793` / MRR
`0.659`, semantic recall@5 `1.0` / MRR `0.943`, with zero semantic misses. Use
`--eval` as live calibration. The evaluator reports `resolvable=<n>` separately
from total cases so a stale or unresolved target counts as benchmark debt, on its
own line, leaving the retrieval score uncharged for it. Use `--eval --record-misses` to append deduped repair rows to
`analytics/public/queries/primitive_amnesia_miss_queue.jsonl`.

### 3a. Relationship to cards, patterns, and action contracts

Primitive surfacing is allowed to return pattern/router primitives such as
`route_operator_cards()` or `build_pattern_action_contract()`, because those are reusable
code capabilities. That does not make primitive amnesia the owner of research routing.

- `primitive_amnesia.py` answers: "which existing code capability should I reuse?"
- `primitive_family_registry.py` answers: "which semantic parent family does this primitive belong to, and which child implementations preserve that identity?" `primitive-parent-utility` also calls its integrity check, so a useful-looking parent graph fails if a child card points at a moved symbol.
- `primitive_operator_cards.py` answers: "which compact RD move candidates and nearest
  confusers fit this problem surface?"
- `pattern_action_contract.py` answers: "which source-bound fields, receipts, checks,
  and action-program slots must be paid before close?"
- `rd_tick_brief.py` renders these surfaces and should not grow its own trigger tables.

The experimental evidence in `epistemic-generation/research_log.md` favors small routed
candidate sets and checked receipt/action fields over broad menus or labels. When a new
move is added, put recognition logic in the card/router layer, have contracts consume
the routed id, and let primitive amnesia surface only the implementation primitives. If
the same keyword list appears in multiple layers, consolidate it. The release gate
`scripts/public/control/research_move_routing_drift_audit.py` prevents
top-level route phrase lists in `pattern_action_contract.py`, requires the
hard-residual and PDE route-owner cards to exist, requires RD briefs to use
semantic-with-fallback operator-card routing, and checks that shared graph
carrier primitives are declared in primitive amnesia before they are treated as
reusable kernel surfaces.

### 4. Gotchas

1. `src/ztare/common/` is NOT auto-swept. Add the module to `PRIMITIVE_MODULES` by hand (done for `constraint_isomorphism.py`). Same for `framer/`, `product_exports/`, top-level files.
2. Lexical fallback is silent in both consumers. A dead embedder produces a degraded ranking with no error. Always `--semantic-live` before trusting a negative.
3. A row added or edited without re-embedding is lexically visible but NOT semantically current. `--atlas-status` checks the catalog digest, which catches content edits that leave the row count unchanged. Always pair `--repopulate`/`--populate-catalog` with `--build-atlas`.
4. `INDEX.md` ≠ `jsonl`. INDEX.md is an auto-rendered, hours-stale human view. The precheck reads the jsonl + atlas. Never judge "is my primitive registered?" from INDEX.md.
5. Noise filter silently drops generic names unless they have a `WHEN_TO_USE` alias.
6. Curated outranks swept by design (`impact_factor_expost=3` for aliased primitives vs `1`).
7. `--repopulate` only drops rows it added (those carrying a `signature` field). Curated/non-tool rows are untouched.
8. `pattern_catalog.yaml` is generated, never hand-edit it. Patch `org/patterns/*.md` and re-run the indexer. `org/` must never import ZTARE (one-way: the indexer lives in `src/ztare/`).
