---
description: "Criteria for what counts as a ZTARE primitive."
---
# Primitive Classification Criteria

> **Up:** [Documentation map](../README.md)

**Status:** public, canonical. Companion to `docs/concepts/reflexive_engineering.md` and `docs/concepts/agentic_engineering_patterns.md`.
**Audience:** anyone proposing to add a new entry to either catalog, OR anyone deciding whether a proposed move qualifies as one of these classes (or as neither, in which case it's just code, not a pattern).
**Why this exists:** without a deterministic checklist, the question "should X become Reflexive Primitive 9 / Agentic Pattern 11?" turns into argument by anecdote. This doc defines the inclusion criteria so the answer can be derived, not litigated.

---

## The two classes

### Reflexive Engineering Primitive (REP)

A specific application of one of ZTARE's three legs (Invert / Compress / Adversarial Disagreement) turned **inward on the apparatus itself**: the engine applies a principle it uses to evaluate substrates to its own infrastructure instead. The catalog lives in `docs/concepts/reflexive_engineering.md`.

A REP is a meta-move: it takes a principle used for evaluating substrates and applies that same principle to the apparatus that evaluates them. Each existing REP names the leg, names the apparatus surface it operates on, and explains why the leg-application is the right shape.

### Agentic Engineering Pattern (AEP)

A **standard software-engineering discipline** adapted for pipelines whose internals are LLM calls, pipelines that are non-deterministic at the call layer but deterministic at the orchestration layer. The catalog lives in `docs/concepts/agentic_engineering_patterns.md`.

An AEP is orchestration infrastructure, not a ZTARE-specific principle. It names a recurring bug class in LLM-mediated pipelines and a detector + fix + invariant assertion that closes it. Patterns are substrate-agnostic and adoptable à la carte without adopting any ZTARE-specific framing.

---

## Not strictly MECE: classify by layer

The catalogs are discriminating, but they are not mutually exclusive at the
mechanism level. The same mechanism can be an Agentic Engineering Pattern when
described as portable orchestration infrastructure for any LLM-mediated system,
and a Reflexive Engineering Primitive when turned inward on ZTARE's own
research and governance loop.

The catalogs should stay separate by primary claim:

- An AEP entry must stand alone for any agentic system. It names the detector,
  fix, invariant, and drift validator for the orchestration pattern.
- A REP entry must name the ZTARE leg applied inward, the apparatus surface it
  acts on, the failure class that produced it, the falsifier, and the evidence
  across contexts.

When both tests pass, document both entries and cross-link them instead of
forcing a false exclusive choice. [GP-230](../../research_areas/seams/mission/org/GP-230_cognitive_firm_absorption_seam.md) is the working example: Pattern 12
is the public sealed-forecast-pool infrastructure; Primitive 9 is the inward
reflexive market that uses scored forecasts to govern ZTARE's own actions.

---

## Inclusion criteria

A proposed entry qualifies as a Reflexive Engineering Primitive **only if all six** of the REP criteria below are satisfied. Likewise for Agentic Engineering Pattern. A proposal may pass both checklists at different abstraction layers; in that case, keep both entries with the AEP documenting the public reusable infrastructure and the REP documenting the inward self-application. A proposal that fails any criterion of both is **not a catalog entry**, it's just code (a specific gate, a one-off helper, a substrate-particular fix).

The "≥2" criteria below apply the same minimum-evidence-bar discipline this repo uses for damage-signal kinds (`org/signals/SIGNAL_KINDS.md`) and for novelty claims (paper 5b's claim-A / claim-B framing). One observation is a hypothesis; two independent observations earn promotion.

### REP-1 through REP-6 (Reflexive Engineering Primitive)

| # | Criterion | Test question |
|---|---|---|
| **REP-1** | The move is **inward** (apparatus → apparatus), not outward (apparatus → substrate). | "If I strip the substrate-domain words from this primitive's description, does it still describe a self-application of a ZTARE leg?" |
| **REP-2** | One of the three ZTARE legs (Invert / Compress / Adversarial Disagreement) is **explicitly identifiable** as the operating principle. | "Can I name the leg without hand-waving? Compress applied to what? Invert applied to what?" |
| **REP-3** | The primitive **abstracts over a class** of failure-driven engineering moves, it's a pattern, not a specific gate or one-off mechanism. | "Strip out the proper nouns (file paths, project names, function names). Does the description still make sense as a recurring meta-move? If it collapses, it's an instantiation, not a primitive." |
| **REP-4** | Discovery happened via **principal-inception**, not first-principles design, a failure occurred, was recognized as infrastructure (not science), and a leg was applied reflexively. | "Can I name the failure that motivated this? Or is this a primitive somebody dreamt up because it sounded clever?" |
| **REP-5** | The primitive is **testable against the failure class it addresses**. | "Can I describe a falsifying observation? An empirical signal that would say 'this primitive isn't actually working'?" |
| **REP-6** | The primitive has been observed **in ≥2 substrates / ≥2 contexts**. One observation is a hypothesis; two earn promotion. | "Has this move been useful on at least two distinct surfaces? Or is this a one-substrate observation generalizing prematurely?" |

### AEP-1 through AEP-6 (Agentic Engineering Pattern)

| # | Criterion | Test question |
|---|---|---|
| **AEP-1** | The technique is **substrate-agnostic**, works for any LLM-mediated pipeline, not specific to ZTARE. | "If I gave this pattern to someone building a RAG system / chatbot / multi-stage agent on a totally unrelated domain, would they recognize the value?" |
| **AEP-2** | It targets the **orchestration layer** (dispatch, contract enforcement, candidate selection, telemetry), not the LLM itself. | "Does this pattern care WHICH model is called? If yes, it's a model-tuning recipe, not a pattern." |
| **AEP-3** | It has a **clear three-part shape**: detector mechanism + fix mechanism + invariant assertion. | "Can I name what triggers the pattern, what the pattern does, and what I assert afterwards to verify it worked?" |
| **AEP-4** | Adoptable **à la carte**, without buying into ZTARE philosophy or any sister-pattern. | "Does this pattern stand alone, or does it implicitly depend on Inversion/Compression/Adversarial Disagreement to make sense?" |
| **AEP-5** | It closes a **specific non-determinism-class bug** that surfaces because LLM call output is non-deterministic but downstream dispatch is deterministic. | "Name the bug class. If I can't name it sharply, the pattern is too vague to be in the catalog." |
| **AEP-6** | It has a **paired drift validator**, something the operator runs to detect that the pattern's invariant has stopped holding (e.g., generation-shape drift, contract drift, regex-coverage drift). | "What test would catch the day this pattern silently stops working?" |

### Neither (just code)

If a proposed entry **fails ≥1 REP criterion AND ≥1 AEP criterion**, it's neither a primitive nor a pattern. It's a specific mechanism (a gate, a helper, a one-off audit). That's fine, most code IS code, not a pattern. Not everything needs to be in the catalog. Specific mechanisms belong in:

- `src/ztare/gates/`, for Cage gates
- `scripts/public/`, for standalone tools
- maintainer seam records, for architectural commitments awaiting empirical validation

---

## Worked examples, applying the checklist

### Example 1: Token-Optimized Self-Modeling (existing REP-1 in the catalog)

| Test | Verdict |
|---|---|
| REP-1 (inward?) | ✓, the agent models its own cognition; nothing about substrates here |
| REP-2 (leg?) | ✓, Compress applied to agent's tacit understanding of large codebases |
| REP-3 (abstracts over class?) | ✓, strip "autoresearch_loop architectural map" and the description is still about formal self-modeling for any large-codebase agent |
| REP-4 (failure-driven?) | ✓, principal observed agent making partial-view mistakes |
| REP-5 (testable?) | ✓, falsifier: agents with arch maps make fewer cross-reader debt errors than without |
| REP-6 (≥2 contexts?) | ✓, applied to autoresearch_loop, mini-ztare, others |

**Verdict: qualifies.** Catalog entry justified.

### Example 2: Stub-Replay Integration Testing (existing AEP-1 in the catalog)

| Test | Verdict |
|---|---|
| AEP-1 (substrate-agnostic?) | ✓, works for any LLM pipeline |
| AEP-2 (orchestration layer?) | ✓, stubs the LLM, tests dispatch logic |
| AEP-3 (three-part shape?) | ✓, detector (real-gen archive) + fix (canned replay) + invariant (record counts, candidate fate) |
| AEP-4 (à la carte?) | ✓, needs no ZTARE philosophy |
| AEP-5 (non-determinism class?) | ✓, closes regex / format-string / type-mismatch bugs that only surface on real generation shapes |
| AEP-6 (drift validator?) | ✓, re-mint stub fixtures from recent real outputs periodically; if the new fixtures break the test, the pipeline drifted |

**Verdict: qualifies.** Catalog entry justified.

### Example 3: Endpoint-Type Compression (proposed but rejected, 2026-05-06)

A specific gate for typed_endpoint_pack (NS Track B): before invoking the LLM to patch a CANNOT-PATCH endpoint, check whether the endpoint's type is a projection of a carried receipt. If yes, synthesize a projection constructor instead of buying fresh proof work. This was recorded under GP-223.

| Test | Verdict |
|---|---|
| REP-1 (inward?) | ✓, typed_endpoint_pack reflexively checks its own classification |
| REP-2 (leg?) | ✓, Compress (project to canonical form) + Invert (would the work be discharged by an existing object?) |
| REP-3 (abstracts over class?) | **✗**, the description doesn't survive proper-noun stripping. "Lean obligations with carried receipts and projection paths" IS the substrate. The general move ("compress before treating as new") might qualify under a different name, but Endpoint-Type Compression as written is the gate, not the abstraction. |
| REP-4 (failure-driven?) | ✓, operator-reframe in NS Track B Codex session |
| REP-5 (testable?) | ✓, `endpoint_double_invoice` damage signal post-hoc detector |
| REP-6 (≥2 contexts?) | **✗**, observed only in NS Track B today |

**Verdict: does NOT qualify** as a Reflexive Primitive (fails REP-3 and REP-6). It's a Cage gate / specific mechanism. Belongs in `src/ztare/gates/` once Layer 1+2 ship, with the seam `GP-223` as its architectural commitment.

If the same compression-before-classifying-as-new pattern surfaces in a non-Lean substrate (REP-6 satisfied) AND someone abstracts it under a substrate-agnostic name (REP-3 satisfied), then it could be promoted. Until then, it's specific code, not catalog material.

---

## How to use this doc

**Authoring a new catalog entry:**

1. Write a 3-paragraph proposal description.
2. Strip the substrate-domain proper nouns. Re-read.
3. Run the REP-1..6 checklist. If all six pass: REP entry.
4. Run the AEP-1..6 checklist. If all six pass: AEP entry.
5. If both: keep both only when they make different claims. The AEP entry must
   be reusable outside ZTARE; the REP entry must explain the inward ZTARE
   self-application.
6. If neither: don't add to the catalog. Find the right home (gate / script / seam) and ship it there.

**Reviewing someone else's proposed entry:**

Use the worked examples above as a calibration. The Endpoint-Type Compression worked example is the canonical "would-be primitive that doesn't quite qualify", keep it as a reference for the next borderline case.

**When the catalog grows:** every five new entries, audit the existing catalog against the criteria. If an entry no longer satisfies (e.g., turned out to be substrate-specific in retrospect), demote it to `gates/` or `scripts/public/`. The catalog earns its own retirement discipline; nothing is permanent.

---

## Anti-patterns

These are NOT REPs or AEPs, even if they sound like they could be:

- **A Cage gate.** Specific gates live in `src/ztare/gates/`. They're not primitives unless the GATE-AUTHORING-METHODOLOGY is the primitive (which is rarer and would itself need to satisfy REP-1..6).
- **A Lean tactic / lemma.** Domain mathematics, not engineering primitive.
- **A clever rubric.** Substrate-specific.
- **A new model fine-tune recipe.** Model-layer, not orchestration-layer (fails AEP-2).
- **An idea that "feels meta" but came from sitting down and trying to be clever.** Fails REP-4 (must be failure-driven).
- **A one-substrate observation generalizing prematurely.** Fails REP-6.

---

## See also

- `docs/concepts/reflexive_engineering.md`, the REP catalog
- `docs/concepts/agentic_engineering_patterns.md`, the AEP catalog
- `docs/guides/reflexive_audit_workflow.md`, the discovery mechanism that surfaces candidate REPs from telemetry
- GP-102, the periodic-audit primitive that proposes new REPs
- `org/signals/SIGNAL_KINDS.md`, the same minimum-evidence-bar discipline applied to damage-signal reservations
