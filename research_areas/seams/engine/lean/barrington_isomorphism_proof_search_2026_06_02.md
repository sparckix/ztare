# Barrington isomorphism → leanmill proof-search (reasoning-by-isomorphism, 2026-06-02)

> **Seam metadata** · `seam_id:` barrington_isomorphism_proof_search_2026_06_02 · `track:` engine/lean · `status:` hypothesis · `last_updated:` 2026-06-02
> **Cross-links (superset / consumes):** relates Barrington-style bounded-width non-commutative composition to leanmill proof-search move algebra and mm_x structural reframes.

**Operator prompt:** Barrington used non-commutativity for an elegant constant-width solution to
NC¹ — can the same concept transport to what ZTARE/leanmill does?

## Barrington (the structural fact, not the surface)
Width-5 permutation branching programs of poly length = NC¹. `AND` is encoded as a commutator
`[g,h]=ghg⁻¹h⁻¹` in **S₅**, which is **non-solvable** — its commutator series never collapses to
identity, so iterated commutators stay expressive. A solvable/abelian group collapses and cannot
encode deep formulas. ⇒ **At bounded resource (constant width), power comes from the
NON-COMMUTATIVITY of the composition, not from the width.**

## Transport to leanmill (structural)
- width ↔ beam-width / budget / working-set (the bounded resource)
- program-step composition ↔ proof-move composition
- COMMUTATIVE / "solvable" moves ↔ tactic-spraying (decide/simp/aesop, order-insensitive, add no
  structure) — collapse, weak.
- NON-COMMUTATIVE / "commutator" moves ↔ STRUCTURAL moves: lemma INVENTION (MOVE_CONJECTURE),
  structure-introducing decomposition, and the mm_x reframes (mm_01 ACR / mm_02 SSP / mm_03
  Ontological Promotion). They change the structure and don't commute with the linear flow.

## Prediction + this session's (unplanned) evidence
Barrington predicts: at bounded resource the WIDTH is not the lever; the non-commutative
composition is. Observed this session, kernel-arbitrated:
- one-shot battery + research-ops vocabulary (commutative spraying) = 1/12; the vocabulary added
  ZERO lift over a plain battery.
- MORE budget / best-of-N / wider beam did NOT crack the frontier (P1_d2 was a budget artifact;
  P2-unimodal stayed open under 1800s).
- what CLOSED leaves was the agentic leaf INVENTING a helper lemma (`totalDeg=0→m=0`, the explicit
  divisor enumeration for d=2) — a "commutator"/structural move — and the P2 frontier only moved
  under an ACR reframe (target theorem → missing reusable lemma).
⇒ power sat in the structural/invention moves, not the resource — the Barrington-predicted shape.

## The ablation is ALREADY in the data — and it confirms the prediction (kernel-arbitrated)
The clean controlled ablation Barrington implies (fix budget, toggle the non-commutative
structural/invention moves) was effectively run on the P1 bucket, comparable budget:
- **commutative spraying** (deterministic battery + obligation-router vocabulary, NO invention):
  **0/4** — the A/B run showed every P1 component open under the battery, and more budget /
  best-of-N / wider beam did not change it.
- **non-commutative / invention** (agentic leaf inventing helper lemmas — `totalDeg=0→m=0`, the
  explicit degree-2 divisor enumeration — the "commutators"): **4/4** (d0/d1/d2/d3 kernel-clean).
Opposite outcomes at the same budget regime ⇒ power is in the non-commutative composition, not the
width — Barrington's exact shape, on this corpus. (Directional confirmation, scoped to one corpus;
a dedicated same-harness toggle would firm it, but the existing kernel-arbitrated data already
separates the two regimes cleanly.)

## Falsifiable forward claim (test, do not launder)
A solver with SMALL bounded budget + a rich algebra of non-commutative structural moves
(conjecture/decompose/reframe) out-closes a WIDE/high-budget solver restricted to commutative
tactic-spraying. FALSIFIER: if closure rate scales with width/budget as much as with
structural-move richness, the isomorphism is poetry. Clean ablation: fix budget, toggle the
structural-invention moves on/off; Barrington predicts a large gap. (Partial confirmation already:
width/budget flat; structural moves did the closing.)

## Why it matters for ZTARE
Gives the nurture thesis a rigorous backbone: the lever is the COMPOSITION STRUCTURE
(non-commutative, bounded resource), not model/resource scale (nature). Sharpens the architecture
axis: not "bigger model / wider beam" but "ensure the move-algebra's non-commutative core
(invention + reframe) is first-class at bounded resource."

## Honest caveat (not a theorem)
Barrington EVALUATES a known formula; proof SEARCH must DISCOVER structure. So this is a structural
/ heuristic transport + a falsifiable hypothesis, not a reduction. Mapped to the vocabulary: this
is itself an mm_02-SSP move (reinterpret "what gives proof-search power" via the
solvable/non-solvable invariant of the move-composition) + a Characterization-by-Obstruction
(commutative-spraying is the solvable, collapsing, weak regime).
