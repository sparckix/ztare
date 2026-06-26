# GP-039 Gate Library Formalization Spec

## Status

Verify

## Scope

- create a private two-layer inventory of all implemented deterministic controls and their failure-family precedents
- documentary only — no runtime code changes, no new JSON consumed by the engine
- strictly backward-linked: every entry points to an existing enforcement surface, code path, or real incident

Does not cover:

- runtime-authoritative gate catalog in `src/ztare/` (only after this inventory exists and runtime consumption is justified)
- public-facing gate documentation (promotion decision is separate)
- new gate design or aspirational controls
- changes to GP-030, charter parsing, or gate harness behavior

## Decision

Build a private two-layer inventory at the maintainer-only gate-library workspace. Layer 1 catalogs executable controls grouped by enforcement surface. Layer 2 catalogs failure-family precedents that motivated each control. The two layers are explicitly cross-linked. This is the compounding asset GP-032 identifies as the moat — the controls are the GAAP analog, the precedents are the case-law analog.

## Problem

ZTARE's deterministic gates exist in three places today:

1. **Rubric-level gates:** `enable_fit_primitive`, `fit_required_dimensionality`, `deterministic_score_gates` in per-project JSON rubrics
2. **Hardcoded gates:** charter-drift checks, quarantine-laundering caps, deferred-confirmation caps, bounded-discriminator contracts in `autoresearch_loop.py` prompt templates and scoring logic
3. **Documented failure families:** the ~9 boardroom families cataloged across GP-012, GP-014, GP-023, GP-030, and the field manual

There is no single artifact that lists what gates exist, what each one checks, what version is active, and what failure family it was designed to catch.

## Why It Matters

- The gate library is the compounding asset (GP-032's moat argument). An asset you cannot inventory is not one you can compound.
- Paper 4 Section 7.7 proposes a "public, versioned rule library" as the institutional-verification primitive. Building it internally first is the prerequisite.
- Any future external verification or audit would need to reference a canonical gate catalog, not scattered prompt templates.
- Operator onboarding and rubric authoring are harder than they need to be because the available gates are not documented in one place.

## Constraints

From converged seam debate (GP-039 Turns 1-3):

1. **Two layers, not a flat list.** Deterministic charter gates, score caps, runner guards, promotion guards, and prompt-level contracts are related but not commensurable. A flat JSON list that pretends they are one object hides the actual architecture. The right structure is: controls catalog + precedent catalog, linked.
2. **Private first.** A catalog that no runtime code reads has no business in `src/ztare/`. First slice lives in the maintainer-only gate-library workspace. Move to `src/` only if/when runtime code needs to consume it.
3. **Inventory what exists, not what we wish existed.** Every control entry must point to an existing enforcement surface, file, or code path. Every precedent entry must point to a real incident, seam, or postmortem. If the first slice drifts into aspirational controls, it stops being audit infrastructure and becomes strategy documentation.
4. **Do not wait on GP-037.** GP-037 may add entries but does not change the need for the catalog.

## Options

### Option A — Flat JSON catalog in src/

**Description**

Single `src/ztare/gates/gate_catalog.json` with one schema for all control types.

**Pros**

- Simple, one file
- Immediately consumable by runtime

**Cons**

- Collapses heterogeneous controls into false uniformity
- Creates a source-of-truth signal before runtime code reads it
- Loses the precedent/case-law layer entirely

**Verdict**

Rejected (Codex Turn 1).

### Option B — Private two-layer markdown inventory

**Description**

Two linked markdown files in the maintainer-only gate-library workspace:
- `control_catalog.md` — executable controls grouped by enforcement surface
- `precedent_catalog.md` — failure families and case law linked to controls

**Pros**

- Honest about what exists vs. what is aspirational
- Human-readable, easy to audit
- Cross-linkable
- Lives in the right place (private, documentary)

**Cons**

- Not machine-readable (acceptable for first slice — the purpose is inventory, not automation)
- Requires manual maintenance

**Verdict**

Recommended.

### Option C — Structured YAML with markdown summaries

**Description**

YAML source of truth plus rendered markdown views.

**Pros**

- Machine-parseable from day one
- Could later be promoted to runtime

**Cons**

- Premature structure for an inventory that does not yet exist
- YAML maintenance overhead for a documentary first slice

**Verdict**

Deferred. Build after the markdown inventory stabilizes.

## Recommendation

Option B. Private two-layer markdown inventory.

## Implementation Sketch

### File structure

```
maintainer-only gate-library workspace/
  control_catalog.md
  precedent_catalog.md
```

### Control catalog structure

Grouped by enforcement surface:

```markdown
# Control Catalog

## Charter Gates (GP-030)
Enforcement surface: `src/ztare/validator/deterministic_charter_gates.py`, `src/ztare/validator/test_thesis.py`

| Control | Type | Metric | Trigger | Fail-Closed Behavior | Origin |
|---|---|---|---|---|---|
| hidden_global_residual | threshold_gate | max_abs_residual_holdout | every iteration | score = 0 | GP-030 |
| ... | ... | ... | ... | ... | ... |

## Score Caps
Enforcement surface: `autoresearch_loop.py` scoring logic

| Control | Type | Cap Value | Trigger | Origin |
|---|---|---|---|---|
| quarantine_laundering_cap | scoring_cap | ... | flaws excluded from scored claim | GP-012 |
| ... | ... | ... | ... | ... |

## Runner Admission Guards
...

## Promotion Guards
...

## Prompt-Level Contracts
Enforcement surface: prompt templates in `autoresearch_loop.py`

| Control | Type | Contract | Origin |
|---|---|---|---|
| bounded_discriminator | prompt_contract | mutator must declare discriminating prediction | TBD (verify against GP-021 / hardening board before populating) |
| ... | ... | ... | ... |
```

### Precedent catalog structure

```markdown
# Precedent Catalog

## Failure Families

### Quarantine Laundering (GP-012)
- **What:** Model acknowledges a flaw in one paragraph, quietly drops it from the scored conclusion
- **First observed:** GP-012
- **Controls motivated:** quarantine_laundering_cap
- **Evidence:** [link to seam, debate log, or postmortem]

### Tolerance Abuse (Paper 1)
- **What:** Apply round() before assertion to destroy precision difference
- **First observed:** recursive_bayesian_claude_gemini run
- **Controls motivated:** deterministic_score_gates (GP-030)
- **Evidence:** [link to Paper 1 artifact]

...
```

### Cross-linking convention

- Each control entry has an `Origin` column pointing to the seam/GP that created it
- Each precedent entry has a `Controls motivated` field pointing to the control(s) it spawned
- Both directions are maintained: control -> precedent origin, precedent -> controls created

### Inventory method

1. Grep `autoresearch_loop.py` for all hardcoded thresholds, caps, and contract terms
2. Grep `deterministic_charter_gates.py` for all gate types
3. Grep rubric JSONs for all gate-related fields
4. Cross-reference against the ~9 boardroom failure families in the field manual and Papers 1-4
5. For each control found: verify it is live (not dead code), record the enforcement surface and trigger
6. For each failure family: verify it has at least one real incident (seam, debate log, or postmortem)

## Open Questions

1. Should the control catalog include prompt-level contracts (bounded-discriminator, eigenquestion ordering) or only hard deterministic gates? The seam debate says yes — they are "things that constrain the loop" — but they have weaker enforcement (LLM compliance, not deterministic check). Include them but mark the enforcement type honestly.
2. When should the inventory be promoted to a machine-readable format (YAML/JSON)? Only when runtime code needs to consume it — e.g., a gate-version field in attestation instruments per Paper 4 Section 7.7.
3. Should the precedent catalog include the 9 specification gaming strategies from Paper 1? Resolved: slice 1 includes only precedents backed by a repo-local incident, seam, paper artifact, or postmortem AND explicitly linked to either an implemented control or a documented absence of control. The full Paper 1 taxonomy is an appendix or later expansion — not default in slice 1. (Codex re-check 2026-04-12.)

## Review Notes

### 2026-04-12 12:04:43 EDT — Codex

The two-layer structure is right, but the current spec still slips in three ways:

1. **The problem statement still over-collapses heterogeneous controls into “deterministic gates.”** Rubric flags, score caps, prompt contracts, runner guards, and promotion guards are not one class. The spec's implementation sketch is better than the problem section. Tighten the language there so the document does not recreate the exact flattening the seam rejected.

2. **Some example provenance is too loose to trust.** The sample row tying `bounded_discriminator` to `GP-028` is almost certainly wrong; the live provenance is closer to the pivot/profile work around `GP-021` plus earlier bounded-discriminator hardening. More generally, the first slice should avoid illustrative rows with uncertain origins. If provenance is not verified, leave the row blank or mark it `TBD` until the inventory step confirms it.

3. **Open Question 3 currently contradicts the spec's own constraint #3.** “Include all 9” drifts from inventory into taxonomy curation. Slice 1 should include only precedents that are:
   - backed by a repo-local incident, seam, paper artifact, or postmortem
   - and explicitly linked to either an implemented control or a documented absence of control
   The full Paper 1 taxonomy can be an appendix or later expansion, but making it default now weakens the “inventory what exists” discipline.

One more implementation correction:

- avoid pseudo-paths in the catalog like `autoresearch_loop.py -> parse_deterministic_gates() -> gate_harness.py` unless the function names are verified and stable. The first slice should cite real files and real enforcement surfaces, not explanatory shorthand that will rot.

So my judgment is:

- structure: right
- placement: right
- provenance discipline: not tight enough yet

### 2026-04-12 13:13:41 EDT — Codex

Re-check after revision:

Two of the earlier problems are still unresolved in the body of the spec.

1. **The sample provenance is still not disciplined enough.**
   The illustrative control row still ties `bounded_discriminator` to `GP-028`. That is still not a safe provenance claim. Slice 1 should avoid example rows with uncertain origins. If provenance is not verified, mark the origin `TBD` until the inventory pass confirms it.

2. **Open Question 3 still violates the inventory-first rule.**
   It still says “Include all 9,” which drifts from inventory into taxonomy curation. Slice 1 should only include precedents that are:
   - backed by a repo-local incident, seam, paper artifact, or postmortem
   - and explicitly linked to either an implemented control or a documented absence of control

The core design is still right. But the spec is not yet honest enough on provenance discipline to implement unchanged.

### 2026-04-12 15:16:53 EDT — Codex

Slice 1 is now implemented as a private documentary inventory:

- control catalog
- precedent catalog

The implementation follows the seam constraints:

- private-first, not runtime-authoritative
- two-layer structure
- file-level enforcement surfaces only
- `TBD` provenance only where the control is live but the exact seam-of-origin has not yet been reconstructed

So the spec is no longer blocked on design. The next step is a verification audit:

- sanity-check the inventory against current shipped controls
- tighten remaining `TBD` provenance where the repo history is clear
- only after that consider any machine-readable or public-facing library
