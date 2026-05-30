# scripts/

> **Up:** [repository root](../README.md) · **Concepts:** [architecture](../docs/concepts/architecture.md) · [reflexive engineering](../docs/concepts/reflexive_engineering.md)

Operational tooling for the apparatus. Hand-authored map (not
auto-generated). Every subdirectory below has its own README that names
each script and says in one line what it does, so an agent (or a human
reading in Obsidian) can navigate without opening the source. Every
subdirectory was inspected for what it does and whether anything
depends on it.

## Script vs `src/ztare` Boundary

The promotion test for moving a script (or part of one) into the in-loop
kernel. ZTARE's reflexive primitives say *the apparatus applies the same
discipline to itself*; the promotion rule below is that discipline applied
to its own code surface.

### Three tests, applied in order

A promotion requires *all three*. If any fails, the script stays in
`scripts/` (possibly with a refactor next to it).

1. **Falsifier-survival.** Has the script's central hypothesis survived
   its own pre-committed falsifier across at least two of: a distinct
   substrate, a distinct mutator family, or a distinct evidence corpus?
   A primitive only earns kernel residency when it has passed the same
   discipline the rest of the apparatus passes.
2. **Cross-caller.** Is the script's *logic* — not its CLI wrapper, not
   its argv parsing, not its ledger writes — imported by at least one of:
   `autoresearch_loop`, a gate, an RD brief, a daemon, or another
   packaged service in `src/ztare/`? If no, either write that caller and
   prove it is actually wanted, or stay in `scripts/`.
3. **Stable contract.** Does it have explicit typed inputs, structured
   outputs, and no silent writes to official state? If no, refactor the
   contract *before* promoting. A promotion introduces coupling that is
   hard to undo.

### Refactor-during-promotion

When a script passes the three tests, split it on the way in:

- Pure logic (classifier, ranker, gate predicate, transition function)
  → `src/ztare/<module>/<name>.py`.
- CLI wrapper, argv parsing, local paths, artifact writes, SSH, rsync,
  approval-bound operations → stay in `scripts/public/control/` (or
  the right sub-bucket).
- The CLI imports the promoted primitive. The kernel never imports the
  CLI.

Worked example: `gap_typed_prompter.py` is the right shape today. The
CLI wrapper and Mathlib shelf dispatcher remain in `scripts/`; the
reusable gap taxonomy/classifier lives at
`src/ztare/research_director/gap_typing.py` so in-loop code can consume
it without importing public scripts.

### Bi-directional flow — the strange-loop rule

Promotion is one-way only in apparatus diagrams; in reality residency is
a moving claim, not a fixed status. The bi-directional rule:

- **Out → In (promotion).** An out-of-loop (RD / agentic) tool that
  survives its falsifier across multiple substrates is *pulled into*
  `src/ztare/` so the in-loop validator can consume it. The
  reflexive-mining pipeline plus the catch ledger record the promotion
  as an INS entry next to the original RD experiment.
- **In → Out (demotion).** An in-loop primitive that *fails* its
  falsifier is moved back the other way. Options: out to `scripts/` as
  a labelled experiment, into `scripts/public/_archive/<dated-subdir>/`
  as a sealed retired artifact, or marked retired in the capability-ROI
  audit. A demotion is the same kind of artifact as a promotion — both
  pass through the catch ledger.

The capability-ROI audit is the periodic mechanism. A primitive's
residency is reviewed against its current cross-caller count, recent
falsifier outcomes, and contract stability. Promotions and demotions
are dated and reversible.

### Coupling rule

`src/ztare/` does not depend on `scripts/`. Scripts may import
`src/ztare/`. If a transition needs the reverse temporarily, it goes
behind a named, dated adapter — never an ambient import — and the
adapter is recorded as technical debt with a removal target.

### Authority-narrowing on promotion

For security and anti-gaming, every kernel promotion must *narrow* the
script's authority surface. A promoted primitive takes explicit inputs
and returns structured outputs; it does not silently write official
state, call SSH, or mutate production ledgers unless it is itself a
named gate or daemon interface. Anything the script could previously do
by virtue of "being in scripts/" must be re-justified at the kernel
boundary, not inherited.

## Map (each row links to a per-script README)

| Subdir | Files | What it is |
|---|---:|---|
| [`public/mining/`](public/mining/README.md) | ~46 | The reflexive-mining pipeline: trajectory/taste/reference-graph miners, `_canonical_paths.py` (single source of truth for mining paths), `aggregate_taste.py`, `build_consequential_artifacts.py`, `render_sprint_progression.py`. Run weekly; feeds the dashboard + P0 ledgers. |
| [`public/control/`](public/control/README.md) | ~256 | The largest and most heterogeneous tree. Agent daemon/channel, forecast-pool control, route-C / GP-225 experiment drivers, ablation analysis, and the LeanMill 24/7 worker stack (~64 `leanmill_*` + ~26 `leansearch_*` scripts) that grew the bucket roughly 2.5× since the prior pass. Several files are recent GP-225 work-in-progress. |
| [`public/models/`](public/models/README.md) | ~26 | GFlowNet / GNN training + data extraction for the GP-225 lemma-relevance line (`gflownet_train.py`, `gnn_inductive_holdout.py`, …). |
| [`public/lean/`](public/lean/README.md) | ~23 | Lean prover runners: auto-prover, batched candidate generation, CANNOT-PATCH refusal harvesting. NS / GP-216 proof-search support. |
| [`public/validators/`](public/validators/README.md) | ~15 | Schema + discipline validators (architecture-index, autoresearch arch-map drift, catch-ledger, rubric, prediction-ledger). Wired into the pipeline and `make` targets. |
| [`public/analytics_shared/`](public/analytics_shared/README.md) | ~19 | Apparatus-on-apparatus meta-review, forecast-pool externalities audit, Codex nomination panels. |
| [`public/audits/`](public/audits/README.md) | ~9 | Gate coverage / effectiveness / engagement audits, the backend behind `make gates`. |
| [`public/utilities/`](public/utilities/README.md) | ~15 | One-shot linters, bulk migrations, catalog generators. |
| `public/projects/` | - | Project-scoped tooling (e.g. the NS graph stack). |
| `public/archive/` | - | Already-retired scripts, kept for provenance. |
| `private/` | 6 | Operator-internal, **gitignored**: `publish_mask.py` (private-ref masker), `gen_folder_index.py` (index generator), `validate_docs_index.py`, `validate_prose_style.py`, the two gate tests, and `git-hooks/`. Run locally via `make gates`; deliberately not public. |

## Archive rule

A file moves to `public/archive/<dated-subdir>/` only when all three hold:
no references in the source corpus, no recent mtime, and a superseding
replacement exists. Name-grep alone is not sufficient; recent in-flight
research tooling routinely lacks named references and must not be
archived on a name-grep miss.
