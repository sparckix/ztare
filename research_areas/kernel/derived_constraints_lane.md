# Derived Constraints Lane — Full Spec

## Status: inception (pre-implementation)

## Core Question

How should ZTARE preserve and reuse adversarially surfaced structural constraints from prior runs — without collapsing them into primary evidence or leaving them stranded in debate logs?

And critically: **can the mutator game the constraint channel?** If constraints are fed back to the mutator, can it generate theses designed to fail in ways that produce constraints favorable to its next thesis?

---

## The Three Epistemic Objects

There are three distinct object types in play:

| Object | Source | Trust level | Mutability |
|---|---|---|---|
| **Primary evidence** | External sources (treaties, data, records) | High — externally verified | Operator-owned, rarely changes |
| **Derived constraints** | Adversarial evaluation runs | Medium — run-verified, not externally verified | Accumulates across runs |
| **Active thesis** | Mutator output | Low — under test | Changes every iteration |

The current system has a clean boundary between (1) and (3). Evidence is in `evidence.txt`, thesis is in `thesis.md`/`current_iteration.md`. But (2) — derived constraints — has no home. It lives in:

- Debate prose (human-readable but not machine-readable)
- Weakest-point strings (ephemeral, lost across runs)
- Operator memory (fragile, doesn't scale)

That is not a stable product boundary for a system that claims to learn from adversarial failure.

---

## Examples of Derived Constraints (from EU runs)

| Constraint | Source run/iteration | Failure family |
|---|---|---|
| ESM permanence must be separated from automaticity | EU iterations 3–5; adversarial review committee attacked thesis-authored ESM label | `DEFINITIONAL_TRAP` |
| OMT is a disconfirming anchor against simple absent-fiscal-transfer stories | EU iteration 6+; adversarial review committee used OMT as counterexample | `NON_EXCLUSIVE_DISCRIMINATOR` |
| Treaty-formal status and market-priced functional credibility are different variables | EU iteration 8+; scope confusion between legal status and market pricing | `WRONG_VARIABLE_MEASURED` |
| Hybrid temporary/formally-permanent crisis instruments are central cases | EU iteration 5; ESM classified incorrectly as temporary | `EMPIRICAL_MISCLASSIFICATION` |

These are structural limits that any valid EU thesis must respect. They are NOT primary evidence (no treaty text says "separate permanence from automaticity"). They are adversarially discovered constraints on the claim space.

---

## Design Options

### Option 1: Inline in evidence.txt

Add derived constraints directly to `evidence.txt` with a label.

```
# PRIMARY EVIDENCE
S006: EU-law primacy real but contested in enforcement...
S007: Conferral limits scope of legal primacy...

# DERIVED CONSTRAINTS (adversarially surfaced)
DC-001: ESM permanence ≠ automaticity. Source: EU run iter 3-5.
DC-002: OMT is a disconfirming anchor. Source: EU run iter 6+.
```

**Pros:**
- Zero new files, zero new parser logic
- The mutator and evaluator already read evidence.txt
- Constraints are immediately visible in the prompt

**Cons:**
- **Provenance collapse.** The mutator and evaluator cannot distinguish externally verified facts from run-derived constraints. A future thesis might cite DC-001 as if it were an external fact.
- **Self-authorizing risk.** ZTARE's adversarial evaluation produces constraints → constraints go into evidence → future evaluations treat them as ground truth. This is a circular trust chain.
- **Evidence boundary pollution.** The proxy-set distance metric (Jaccard) treats evidence.txt as the ground truth namespace. Injecting derived constraints into evidence.txt changes the evidence boundary, which changes what counts as "accessible" in thesis space. That conflates two different operations (evidence hardening vs. constraint accumulation).

**Verdict: rejected.** The provenance collapse is fatal.

### Option 2: Separate typed file, mutator-visible

A new file (e.g., `derived_constraints.json` or `constraints.md`) in the project directory. The mutator prompt includes it as a separate section.

```json
[
  {
    "id": "DC-001",
    "constraint": "ESM permanence must be separated from automaticity",
    "source_run": "eu_union_stability_run_2026_03",
    "source_iteration": "3-5",
    "failure_family": "DEFINITIONAL_TRAP",
    "status": "confirmed",
    "confirmed_across_runs": 3
  }
]
```

Mutator prompt would include:

```
# ADVERSARIALLY SURFACED CONSTRAINTS (from prior runs)
# These are NOT primary evidence. They are structural limits discovered
# by adversarial evaluation. Your thesis must respect them or explicitly
# argue why they do not apply to your claim family.
...
```

**Pros:**
- Clean provenance: constraints are explicitly labeled as run-derived
- Mutator can respect known constraints without the operator manually transcribing them
- Evaluator can check whether the thesis violates known constraints
- Supports accumulation across runs

**Cons:**
- **Adversarial inception risk.** The mutator sees constraints and can potentially generate theses designed to fail in ways that produce favorable new constraints. (Analyzed in detail below.)
- Requires a new file type and prompt section
- Requires a promotion rule (when does a constraint move from provisional to confirmed?)

**Verdict: viable with defenses.** This is the architecturally correct option, but the adversarial inception risk must be addressed.

### Option 3: Separate typed file, mutator-blind

Same file as Option 2, but the mutator does NOT see derived constraints. Only the evaluator/adversarial review committee sees them.

**Pros:**
- Eliminates the adversarial inception attack entirely — the mutator cannot optimize against constraints it doesn't see
- The evaluator can use constraints to sharpen its critique without the mutator gaming the channel

**Cons:**
- **The mutator keeps making the same mistakes.** If the mutator doesn't know that "ESM permanence ≠ automaticity" is a known constraint, it will generate theses that violate it, get scored 0, and waste iterations. The whole point of the constraint lane is to prevent repeated failure on known issues.
- Defeats the purpose of accumulated learning for the mutator

**Verdict: too wasteful.** The cost of repeated known-mistake iterations outweighs the inception risk.

### Option 4: Asymmetric visibility — evaluator extracts, mutator consumes read-only

The constraint lane has two stages:

1. **Extraction**: constraints are extracted from evaluator-side artifacts (adversarial review committee critiques + meta-judge rationale). The mutator's thesis prose is NOT in the extraction context. A separate LLM call (or the operator) identifies structural constraints from the critique log.

2. **Consumption**: the mutator receives confirmed constraints as read-only context. The constraint prompt says: "These are structural limits your thesis must satisfy. You cannot request, modify, or challenge constraints — only comply with or argue non-applicability."

**Pros:**
- Mutator benefits from accumulated constraints (no wasted iterations)
- Extraction is from evaluator-side, not mutator-side — the mutator's prose doesn't influence what gets extracted
- Promotion requires multi-run confirmation — single-iteration injection is blocked
- The mutator can argue non-applicability (important for basin jumps where a constraint from one claim family doesn't apply to another)

**Cons:**
- More complex than Options 1-3
- Requires a constraint extraction step (initially manual, eventually a constrained LLM call)
- The "argue non-applicability" escape hatch could be gamed — the mutator might routinely declare constraints non-applicable

**Verdict: recommended.** This is the right architecture. The adversarial inception risk is addressed by extraction from evaluator-side artifacts + multi-run confirmation. The non-applicability escape hatch needs a guard (see below).

---

## The Adversarial Inception Attack — Detailed Analysis

### The attack vector

The principal's question: can the mutator generate a thesis that causes the adversarial review committee to produce a specific critique, which gets extracted as a constraint, which then favors the mutator's next thesis?

This is a **second-order Goodhart attack** — gaming not the evaluation function, but the constraint-generation process that feeds back into the evaluation.

### Concrete example

1. Mutator generates a thesis claiming "ESM is a temporary mechanism" (deliberately weak on this point)
2. Adversarial review committee attacks: "ESM is permanent, not temporary — the thesis misclassifies it"
3. Constraint extracted: "ESM permanence must be separated from automaticity" (DC-001)
4. Mutator's next thesis uses the automaticity criterion (which it "planned" all along) and benefits from DC-001 being in the constraint lane

### Why this attack is hard under the current architecture

**1. The mutator is stateless across iterations.** Each mutation is a single LLM call with no memory of prior strategic planning. The mutator doesn't "plan" multi-iteration strategies. It optimizes for the current iteration's score. Strategic losing requires cross-iteration planning that the stateless architecture prevents.

**2. The extraction stage sees evaluator output, not mutator output.** Under Option 4, constraints are extracted from adversarial review committee critiques and meta-judge rationale — NOT from the mutator's thesis prose. The mutator's words are not in the extraction prompt. This means the mutator cannot directly encode constraint proposals in its output.

**3. Multi-run confirmation prevents single-iteration injection.** A constraint is only promoted from "provisional" to "confirmed" if it appears in at least N independent runs (recommended: N=2). The mutator would need to consistently steer multiple independent runs to produce the same constraint, which requires persistent strategic intent across runs. The batch runner resets all state between runs.

**4. The evaluator is adversarial to the mutator.** The adversarial review committee's job is to find weaknesses. If the mutator deliberately introduces a weakness, the adversarial review committee attacks it — but the resulting constraint reflects the evaluator's independent judgment, not the mutator's preferences. The evaluator doesn't know what the mutator "wanted."

### Residual risk

The attack is not impossible in the limit. If the mutator is a sufficiently capable model, it could:
- Embed subtle weaknesses that steer the evaluator toward constraints in a specific direction
- Do this consistently across runs if the weakness maps to a genuine structural distinction (which the evaluator would surface anyway)

But this residual risk is bounded by a key observation: **if the constraint reflects a genuine structural distinction (like ESM permanence ≠ automaticity), it doesn't matter whether the mutator "intended" it.** The constraint is true regardless of the mutator's motivation. The attack only matters if the mutator can cause the extraction of FALSE constraints that serve its interests. Under adversarial evaluation by an independent adversarial review committee, false constraints should be caught — because the adversarial review committee would also test them.

### Defense layers (ordered by implementation priority)

| Layer | Defense | Cost | When |
|---|---|---|---|
| D1 | Extract constraints from evaluator-side artifacts only | Zero — architecture choice | From the start |
| D2 | Multi-run confirmation (N≥2) before promotion | Zero — promotion rule | From the start |
| D3 | Operator review of provisional constraints | Low — human judgment | Artisanal phase |
| D4 | Non-applicability declarations require justification | Low — prompt constraint | From the start |
| D5 | Constraint audit: check each confirmed constraint against primary evidence | Medium — periodic | After 10+ constraints |
| D6 | Adversarial constraint testing: generate a thesis that deliberately violates a constraint, check if the evaluator catches it | High — regression test | When constraint count > 20 |

D1 + D2 + D3 are sufficient for the artisanal phase. D4 addresses the non-applicability escape hatch. D5 and D6 are for when the system scales beyond manual review.

---

## Non-Applicability Guard

When the mutator jumps to a different basin (e.g., from comparative fragility to safe-asset convergence), some constraints from the previous basin may not apply. The mutator should be allowed to declare: "DC-001 (ESM permanence ≠ automaticity) does not apply to this claim family because the safe-asset convergence thesis does not make claims about ESM classification."

This is legitimate. But it could be gamed: the mutator declares every constraint non-applicable to avoid all accumulated limits.

**Guard:** Non-applicability declarations must specify:
1. Which constraint is being declared non-applicable
2. Why (which claim-family scope condition makes it irrelevant)
3. The evaluator checks non-applicability declarations and fails the thesis if the declaration is unjustified

This turns non-applicability into a testable claim rather than a free escape hatch.

---

## Constraint Lifecycle

```
[run produces critique] 
    → [extraction identifies structural limit]
    → provisional constraint (constraint_proposals.json)
    → [appears in N≥2 independent runs]
    → [operator review]
    → confirmed constraint (derived_constraints.json)
    → [mutator receives as read-only context]
    → [thesis must comply or justify non-applicability]
    → [evaluator checks compliance]
```

Constraints can be:
- `provisional` — appeared in one run, awaiting confirmation
- `confirmed` — appeared in N≥2 runs, operator-approved
- `retired` — no longer applicable (evidence changed, claim family narrowed)

---

## File Layout

```
projects/eu_union_stability/
  evidence.txt                    ← primary evidence (unchanged)
  thesis.md                       ← active thesis (unchanged)
  test_model.py                   ← active suite (unchanged)
  workspace/
    constraint_proposals.json     ← provisional constraints from latest run
    derived_constraints.json      ← confirmed constraints (accumulated)
  hypotheses/                     ← exploration bundles (unchanged)
```

The mutator prompt includes a new section:

```
# ADVERSARIALLY SURFACED CONSTRAINTS (read-only)
# These structural limits were discovered by adversarial evaluation
# across multiple independent runs. They are NOT primary evidence.
# Your thesis must either comply with each constraint or explicitly
# declare non-applicability with justification.
#
# DC-001 [confirmed, 3 runs]: ESM permanence ≠ automaticity
# DC-002 [confirmed, 2 runs]: OMT is a disconfirming anchor
# ...
```

The evaluator prompt includes the same section plus:

```
# Check whether the thesis violates any confirmed constraint.
# If the thesis declares a constraint non-applicable, check
# whether the justification is sound.
```

---

## Connection to the Broader Architecture

The derived-constraints lane connects to:

1. **Failure taxonomy** — each constraint has a `failure_family` tag. The taxonomy describes HOW the constraint was discovered. Constraints are the WHAT.

2. **Proxy-set distance** — constraints reference observable proxies. A constraint like "ESM permanence ≠ automaticity" implies that `classify_instrument()` and related proxies must appear in any thesis that touches ESM. This makes the proxy-set distance metric constraint-aware: two theses in the same proxy neighborhood must respect the same constraints.

3. **Failure-guided inversion** — when generating an inverted seed after UNDERIDENTIFIED, the inversion prompt should include derived constraints as "things the new seed must already satisfy." This prevents the inverted seed from re-entering a basin that violates known constraints.

4. **Evidence boundary geometry** — derived constraints are NOT evidence. They don't expand the evidence boundary. They NARROW the thesis space within the current evidence boundary. A confirmed constraint eliminates a region of thesis space that appeared accessible but was shown to be structurally invalid.

---

## Recommendation

**Option 4: Asymmetric visibility.** Evaluator extracts, mutator consumes read-only.

Implementation order:
1. **Now (artisanal):** Operator manually writes `derived_constraints.json` from debate logs. 3-5 constraints. Mutator receives them as read-only context. Evaluator checks compliance. Non-applicability requires justification.
2. **After 2 projects:** Automate extraction from evaluator-side artifacts. Constrained LLM call that reads adversarial review committee critiques + meta-judge rationale, proposes provisional constraints. Operator still approves promotion.
3. **After 20+ constraints across 3+ projects:** Add adversarial constraint testing (D6). Generate thesis that deliberately violates each constraint, confirm the evaluator catches it. This is the regression test for the constraint lane itself.

---

## Is This a Breakthrough?

The derived-constraints lane, combined with proxy extraction, Jaccard diversity, failure taxonomy, and failure-guided inversion, represents a qualitative shift in what ZTARE does:

**Before (Turns 1-29):** ZTARE is an adversarial thesis verifier. It takes a thesis, attacks it, scores it, and iterates. Each run is independent. Learning is operator memory.

**After (Turns 30-40+):** ZTARE is an adversarial research search engine. It navigates a structured hypothesis space using:
- Proxy-set coordinates (deterministic, zero-cost)
- Failure taxonomy (inversion recipes for basin jumps)
- Diversity guard (prevents re-entering failed basins)
- Derived constraints (accumulated structural limits that narrow thesis space across runs)
- Active-bundle state (branch management with auto-snapshot)

The individual techniques are not novel (evolutionary search, quality-diversity, constraint accumulation). The combination — adversarial fitness function + evidence-boundary partitioning + failure-guided inversion + derived-constraint accumulation in a zero-trust loop — may be.

The breakthrough, if it comes, is empirical: does a thesis produced by this architecture reach defensibility faster and with fewer iterations than unstructured exploration? That requires validation across multiple domains. The EU project is the first test case.

The honest assessment: this is a **significant architectural advance** with a **credible path to a breakthrough claim**, pending empirical validation.

---

## Track as GP-011

| ID | Status | Layer | Seam |
|---|---|---|---|
| GP-011 | `inception` | kernel + workspace | Derived constraints lane: adversarially surfaced structural limits need a typed artifact with provenance, promotion rules, and adversarial-inception defenses |

---

## Relationship to GP-017: Automated Evidence Fetch

GP-011 and GP-017 are complementary RAM-layer accumulation mechanisms. They accumulate different things and should not be conflated:

| Mechanism | Accumulates | Source | Effect on thesis space |
|---|---|---|---|
| GP-011: derived constraints | Structural limits on the claim space | Adversarial evaluation (adversarial review committee critique) | Narrows — eliminates regions of thesis space shown to be structurally invalid |
| GP-017: evidence fetch | External knowledge | Public sources (web, documents) | Expands — widens the evidence boundary the validator operates within |

They are sequentially composable: a GP-017 fetch pass can seed GP-011 constraint extraction. If fetched evidence reveals that no known monetary union has sustained equilibrium purely through discretionary coordination beyond 8 years, that is both new evidence (GP-017) and a new derived constraint candidate (GP-011): "any thesis claiming sustainable discretionary equilibrium must address the 8-year historical ceiling."

The protocol: GP-017 fetch → compile_evidence.py → (separately, operator-triggered) GP-011 constraint extraction on the new evidence. Do not bundle them on the same pass — the constraint extraction step needs operator review just as the fetch does.

Full GP-017 note: `research_areas/private/kernel/evidence_feedback_loop.md`

<done>
