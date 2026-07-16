---
description: "The five-category decision-support decomposition and its governed argument-graph consumers."
---

# Decision-support primitives — the complete grid

ZTARE's decision-support kernel is not an open-ended pile of features. It is a **closed decomposition**: five
categories, each with one owner, that together cover the whole job of hardening a claim into a decision. This
document is the answer to "won't we keep inventing new primitives?" — **no.** A genuinely new idea is admissible
as a new *module* only if it (i) adds a warrant-minting capability (an ADMIT plugin) or (ii) fills a new cell —
**and the grid is full.** Everything else you will think of (pre-mortem, risk register, assurance case) is a
**view** (a cheap read over the graph, in the report layer) or a **consumer** (a scenario plugin). Views and
consumers are unlimited and carry no kernel weight; primitives are fixed.

The frame is standard: the **decision-analysis cycle** (Howard) crossed with **truth-maintenance** (de Kleer's
ATMS; Reiter) and **assumption-based planning** (Dewar, RAND). We did not invent the categories; we implement
them deterministically over a governed argument graph, with a warrant (checkability) tier on every piece of
backing.

## The five categories

| # | Category | The question it answers | ZTARE owns | Literature origin |
|---|----------|-------------------------|------------|-------------------|
| 1 | **ADMIT** | What may enter the graph, at what backing tier? | warrant tiers (unchecked / cited / reproducible / proven), quote-binding, the recheck door (the only minter of the *reproducible* tier), the governed-overlay write-back doors | Toulmin, *The Uses of Argument* (1958) — warrants; Gordon & Walton, **Carneades** proof standards (our tiers are a checkability analogue) |
| 2 | **EVALUATE** | What does the argument conclude, and how firmly? | the crisp grounded `verdict`; the graded `strength_profile` (strength recomputed at each backing cutoff) + the override lattice | Dung (1995) abstract argumentation & **ABA** grounded semantics; **gradual/quantitative** semantics — Potyka (KR 2018, QEM); Baroni, Rago, Toni |
| 3 | **ATTRIBUTE** | What does the conclusion rest on? ("What would you have to believe?") | `minimal_cores` (the decision-critical assumption sets), `dominators` (conditions on every support path), `shapley_support`, `warrant_ceiling`. **The "beliefs" view is a rendering of this cell — not a separate primitive.** | de Kleer **ATMS** minimal environments; flow-graph dominators; Shapley attribution (Yin, Potyka, Toni, IJCAI 2024); **"what would have to be true"** — Martin & Lafley, *Playing to Win*; Rivkin's classroom form; Dewar **assumption-based planning** (critical + vulnerable assumptions) |
| 4 | **AGENDA** | What is the cheapest thing that would change my mind? | the unified wager-typed ranking: `identification_bits` (value of information), maximin `severity`, cost, `flips_alone`; loop-proposed experiments enter through the same door | **Value of Information** — Howard (1966); prior-free variant = **query-by-committee** (Seung, Opper, Sompolinsky 1992); **severity** — Mayo, *Error and the Growth of Experimental Knowledge*; **pre-mortem / red-team** — Klein (generative side) |
| 5 | **MAINTAIN** | Does the conclusion still hold over time? | `recompile` (stale-decision diff), `warrant_recheck` (earn / demote / expire), the wager lifecycle (deadline = option expiry) | TMS label update (Doyle; de Kleer); **signposts** — Dewar; living-evidence half-life; **real options** (a deadline is an option to keep alive by paying) |

A **consumer** layer sits on top and is deliberately *outside* the kernel: e.g. Governed RICE reads category-2
strength into a PM verb (Confidence is *read*, never typed). Consumers are scenario plugins.

## The AGENDA cell — one door, but dissent is kept

Category 4 is the crowded one; several rankers legitimately answer "what to test next" through different lenses
(information yield, severity, cost, single-toggle flip). The rule is **one door, one read-time recompute** (so
they cannot silently disagree and drift) — but the ranking is **not** collapsed into one lossy scalar. Each item
keeps its multiple lens-scores, and where the lenses *disagree* that tradeoff is surfaced as signal (a
multi-criteria / Pareto view: "highest info-yield but low severity" vs "highest severity but costly"). The
dissent is informative; it is presented coherently, not hidden.

## The loop ↔ kernel contract — "the loop proposes; the kernel disposes"

The LLM-driven autoresearch loop may **author** nodes/edges (admitted at the *unchecked* tier, and marked) and
may **propose** experiments. It may never mint a backing tier above *unchecked* — only the deterministic doors
do that (the recheck driver, quote-binding, kernel certificates). Every ranking or number shown to a human is
**recomputed at read time** from the frozen graph; no LLM-produced scalar survives past the admission door.
The anti-drift invariant is mechanical: (1) one proposal schema — everything in AGENDA is a wager payload,
whoever authored it; (2) read-time recompute — no persisted rankings; (3) one tier vocabulary, in one module.

## Named gaps and deliberate non-goals

- **Node-level provenance (real gap):** edges default to the *unchecked* tier honestly, but a node minted from
  an LLM-produced carrier carries no tier at all — the determinism starts *after* an LLM-shaped carrier, and
  nothing marks that. This is the design's principal weak spot; it is tracked, not hidden.
- **Evidence independence** beyond shared-source lineage: designed (`_lineage_sources`) but the carrier does not
  emit `DERIVED_FROM` yet.
- **Alternatives / framing:** ZTARE hardens one thesis; only a portfolio compares. A beachhead non-goal for now.
- **Preferences / utilities (deliberately empty):** ZTARE declares dollars/odds, never computes them. Filling
  this cell would turn decision-*support* into decision-*making* — which is exactly where claim discipline fails. This
  cell is left empty on purpose.

The worldmodel substrate (`src/ztare/worldmodel/`) independently instantiates the same five categories and the same warrant-tier ladder over interactive-game evidence. The ATTRIBUTE cell's minimal-core math and AGENDA's `identification_bits` (in `src/ztare/common/information_yield_pricing.py`) are, or are becoming, shared modules under the common/ boundary. The hitting-set core used for minimal environments also lives in `src/ztare/common/hitting_sets.py`. That the grid recurs across two independently-built substrates — one over a governed argument graph, one over episode-log transitions — is evidence the decomposition carves the problem at its joints rather than at a design convenience.

---
*Provenance: this decomposition was stress-tested in an external strategic ("Fable") eigenreview, 2026-07. The
categories are the standard decision-analysis / truth-maintenance / assumption-based-planning canon; ZTARE's
contribution is the deterministic, warrant-tiered implementation over a governed argument graph.*
