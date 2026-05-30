# GP-222 — Operator-Memory ↔ Apparatus Bridge (PROPOSAL ONLY)

> **Seam metadata** · `seam_id:` GP-222 · `track:` apparatus · `status:` OPEN - opened 2026-05-06. · `last_updated:` 2026-05-08


**Status:** open *(inferred 2026-05-08 — needs operator review)*

## Status

OPEN — opened 2026-05-06.
**Decision required from principal before any implementation work.**
This seam describes an opportunity AND its privacy/scope risks. Do
not ship code from this seam without explicit operator review of the
specific data-flow proposed below.

## ID

GP-222

## Eigenquestion

The session-side memory at
`/projects/<this-project>/memory/` accumulates
operator feedback, project context, and agent-mistake corrections
across sessions. Currently it's read by Claude on cold-start and
shapes per-session behaviour. The apparatus itself can't see it.

When the operator types "stop overindexing on axioms" in a session,
that becomes a feedback memory entry. The next session, Claude
reads it. But the autoresearch_loop running in the background has
no idea that correction happened. It will keep weighting axiom-delta
as a quality signal until a separate apparatus-side correction is
made.

The eigenquestion: should the apparatus consume operator-side memory
as a damage-signal source — and if so, how to do it without
creating privacy/scope failure modes?

## Problem Statement

GP-102's reflexive primitive discovery rests on observing operator
frustration → primitive inception. The frustration signal is captured
TODAY in `feedback_*.md` memory entries. The pattern is:

  user: "no, that's wrong; do X instead"
  → Claude writes feedback_X.md
  → next session, Claude reads feedback_X.md
  → behavior changes per-session
  → apparatus stays unchanged (autoresearch_loop, judges, gates)

The bridge would close the loop by feeding new feedback memory
entries into the reflexive_audit (Component 1: gather telemetry)
as a structured input — not as Claude's internal state, but as a
cross-session damage signal of kind `feedback_received`.

## What this would buy

1. **Mechanizes operator inception.** Today, Claude infers from
   feedback that "operator is frustrated with X." Next session
   Claude doesn't carry the urgency forward; only the rule.
   Apparatus-side, the urgency NEVER propagates. Bridging would
   make "operator corrected this 3 times in a week" a first-class
   signal alongside `dag_stagnation` or `noether_gaming_streak`.

2. **Provides telemetry for GP-102 Component 4.** When the audit
   asks "what's stuck?" — the operator's recent corrections are
   the highest-quality answer. Today the audit can't see them.

3. **Closes a known under-feedback loop.** The reflexive primitive
   `Operator-Replay Mechanization` was built to extract operator
   behaviour patterns and mechanize them. Operator-feedback-text
   is a higher-signal source than operator-action-replay.

## Why this is risky

1. **Privacy/scope.** The memory directory contains operator-side
   context including personal preferences, role context, and
   sometimes things the operator wouldn't want compiled into a
   per-project artifact. Default-share is wrong; default-private
   plus explicit opt-in per entry is the floor.

2. **Cross-project leakage.** Memory entries can reference
   project-specific learnings that shouldn't influence other
   substrates. A feedback entry like "for paper 5, use cautious
   language about Claim B" should NOT propagate to a Track-B NS
   substrate's mutator briefing.

3. **Feedback-as-charter contamination.** Per
   `feedback_charter_contamination.md` (existing memory entry),
   the apparatus already has a known failure mode where injected
   text leaks ground-truth-like signals into the mutator. Operator
   feedback could be MORE contaminating than charter text — it's
   exactly the kind of corrective ("use X form", "don't do Y") that
   the apparatus is supposed to discover, not inherit.

4. **Auto-summarization is unsafe.** "LLM reads memory, summarizes,
   feeds into briefing" — the LLM might paraphrase a private
   feedback entry into something that looks like a substrate-domain
   instruction. We've seen this class of leak before
   (`feedback_principle_vs_instantiation.md`).

## Proposed mechanism (subject to operator review BEFORE any code)

A 3-layer architecture, each layer requiring explicit principal
authorization:

### Layer 1 — passive opt-in marking on memory entries

Memory entries gain an optional `apparatus_visible: true` frontmatter
field. Default false. Only entries with explicit opt-in flow.

```yaml
---
name: read_data_first
description: When run fails, read telemetry before shipping more apparatus
type: feedback
apparatus_visible: true   # ← new optional field; default false
apparatus_scope: all      # ← optional; "all" / "ztare-loop" / "research-director" / "off"
---
```

The principal hand-marks each memory entry that should bridge.

### Layer 2 — out-of-loop read by reflexive_audit

`reflexive_audit.py` Component 1 (gather_telemetry) gains a new
input source: scans the memory directory for entries with
`apparatus_visible: true`, accumulates them as a separate field
on the audit report (`operator_feedback_window`). NOT fed into
mutator briefing. NOT fed into autoresearch_loop. Only visible
to the audit's Component 4 (LLM proposes new primitive).

### Layer 3 — never-shipped: in-loop influence

The hardest part: **even Layer 2 should NOT inject feedback text
into mutator briefing.** Component 4 of the audit is an
out-of-loop LLM call that reads the feedback as context for
proposing a NEW primitive. The principal disposes the proposal.
The proposal might be "add a new gate that detects pattern X" —
that's the artifact that flows into the apparatus, NOT the
feedback text itself.

## What this seam is NOT proposing

- Direct read of memory by autoresearch_loop. **Forbidden.** Memory
  is operator context, not loop state.
- Auto-extraction of feedback text into mutator briefings. **Forbidden.**
  Charter contamination class.
- Sharing feedback across projects without explicit `apparatus_scope`
  scoping. **Forbidden.**
- Any change to memory write semantics. Memory writes happen via
  Claude → file-system, unchanged.

## What success looks like

A periodic (P14D, joined to the reflexive_audit cadence) digest
that includes:

- Recent `apparatus_visible: true` feedback entries from the
  operator-memory side
- Cross-referenced against per-substrate gate failures and
  primitive engagement rates
- One LLM-mediated proposal per cycle MAX (per the
  `conversation_stagnation` reservation discipline: don't dilute
  the reframe move)

The principal reads the digest, decides whether the proposed
mechanism is worth seaming + implementing, and disposes.

## Honest assessment of feasibility

If shipping Layers 1+2 means the principal hand-marks 5-10 memory
entries with `apparatus_visible: true` and reads a bi-weekly digest,
that's a few minutes of operator overhead per cycle and surfaces
real signals.

If it means inventing a gating mechanism for "should this feedback
flow" and an LLM that summarizes feedback into briefing-grade text,
that's months of work with high contamination risk.

Layer 3 is explicitly out of scope until Layers 1+2 have run for a
full quarter and the principal has an empirical sense of whether
the bridged feedback is producing better proposals than the existing
inception cycle.

## Honest concerns the principal should weigh

1. **Does the bridge solve a problem we have, or import a problem?**
   Today, the operator inception cycle works (the catalog of 8
   reflexive primitives all came from it). The bridge is a
   "do faster what already works." But faster might also mean
   **more**, which might also mean more decorative primitives.
   The GP-220 ROI audit is a check on this — but GP-220 hasn't
   shipped yet.

2. **Is the operator's feedback text the right signal?** Or is the
   operator's BEHAVIOUR (what they accepted, rejected, modified) a
   higher-signal source? `Operator-Replay Mechanization` already
   bridges behaviour. The text might be redundant.

3. **What's the failure mode if this leaks?** Worst case: a
   feedback entry like "stop suggesting that approach for paper 5"
   leaks into a substrate's mutator briefing as "do not approach
   the problem this way" — which may be exactly wrong for the
   substrate. The contamination pathway is reasonably narrow but
   not zero.

## Decision gate

This seam stays OPEN until the principal:

1. Reads it
2. Decides yes / no / modify on Layer 1 + Layer 2 (Layer 3 is
   permanently deferred)
3. If yes: identifies which existing memory entries should be
   marked `apparatus_visible: true` for the first cycle (sample
   size: small, e.g., 3-5 entries)
4. Reviews the first reflexive_audit Component 4 proposal that
   uses this signal before any apparatus change

No implementation work happens in this seam without explicit
principal authorization. The seam is the artefact; the
implementation needs a separate spec under
`research_areas/private/specs/active/`.
