---
id: PATTERN-004
name: vocabulary_quarantine
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [project-2150, future-vocabulary, paradigm-shift]
  structural: [agent_prompted_for_future_math, naming_sprint_starting]
  problem_classes: [pre_category_emergence]
spawn:
  mode: prompt_injection  # not a separate agent; injects guards into projector's prompt
  subagents: []
output_schema: prompt_template_v1
fallback: null
preconditions:
  - prompt_will_request_future_vocabulary: yes
chain_position: pre  # injects BEFORE the projector agent runs
related_patterns:
  - PATTERN-003 (reducer, post-output enforcement)
  - PATTERN-005 (falsifiable_asymmetry, output-time enforcement)
falsifiable_test: |
  Once wired into the future-vocabulary projector prompt chain, across N>=15
  future-vocab / paradigm-shift / naming-sprint dispatches that carry the
  quarantine prompt-injection, downstream PATTERN-003 reducer LAUNDERED-verdict rate
  on the resulting candidates must be at least 25 percentage points LOWER than the
  matched LAUNDERED rate for projector outputs generated without the injection (the
  pre-P11 baseline; the 2026-05-08 first-fire showed 3/3 launderings still caught
  but pre-constrained). If injected and non-injected outputs launder at rates
  within 25 points of each other, the quarantine prevents nothing and demotes.
  metric_source: pattern_deployment_ledger.jsonl (primary_pattern=PATTERN-004,
  vocabulary_quarantine_injected flag per projector dispatch) joined to downstream
  reducer_verdict_v1 LAUNDERED/GENUINE outcomes on the same dispatch_id chain.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 4, Vocabulary Quarantine (P11 from operator-directed mitigations)

## Problem

When asked to project "2150 vocabulary" or "alien math from the future,"
LLMs reach for elite nouns from adjacent advanced fields (∞-categories,
derived stacks, topos theory, sheaves, gerbes, Postnikov towers,
representation theory) without grounding them in operator-level mechanics.

The result is sophisticated-sounding candidates that fail the Reducer
test (P13) because they're tautological renamings of existing 2026
constraints.

The fix: prevent the laundering at PROMPT-INJECTION time.

## Pattern

When a prompt asks for future-vocabulary projection, INJECT this
constraint:

> "You must articulate the [future] meta-pattern using ONLY the
> foundational vocabulary of the 2026 problem itself. You may NOT
> import 'savior concepts' from adjacent advanced fields (e.g.,
> algebraic topology, representation theory, ∞-categories, derived
> stacks, sheaves, gerbes, Postnikov towers) UNLESS you can explicitly
> map the mechanical, operator-level bridge that justifies it."

Programmatically: this is a string append to the system / user prompt.

The constraint forces the agent to:
1. Describe the structural shape of what's missing
2. Use foundational vocabulary (Banach spaces, Fourier analysis,
   PDE-level operators, Bohr means, etc.)
3. Earn elite nouns by exhibiting a mechanical bridge

## Why it works

Prevents elite-noun hiding; forces structural-shape description.
Operates BEFORE the projector outputs, so no after-the-fact reduction
needed (though Reducer P13 still runs as backstop).

## When to deploy

- ANY prompt asking for "2150 vocabulary"
- ANY naming-sprint that wants paradigm-shift proposals
- ANY alien-math projection request

## Anti-pattern

**OVER-RESTRICTION**: forbidding ALL elite nouns kills genuine
categorical work. The constraint allows elite nouns IF the operator-
level bridge is supplied. Don't ban; demand the bridge.

**WORDY ENFORCEMENT**: appending a 2-page constitutional preamble to
every prompt drains the context budget. The injection is ONE PARAGRAPH.

## Concrete example

2026-05-08 ~09:30, operator directive added P11 to the Reducer
deployment chain. Applied to all future-vocab agent invocations:

```
USER PROMPT:
[original task]

CONSTRAINT (Vocabulary Quarantine P11): you must articulate the future
meta-pattern using ONLY the foundational vocabulary of the 2026 problem
itself. You may NOT import 'savior concepts' from adjacent advanced
fields ... UNLESS you can explicitly map the mechanical, operator-level
bridge that justifies it.
```

Effect: subsequent projector outputs were FORCED to either ground the
elite nouns mechanically OR drop them. When grounding failed, agents
produced foundational-vocabulary descriptions that were then
amenable to Reducer (P13) and Falsifiable Asymmetry (P12) audits.

Result: 3/3 follow-up reductions caught laundering (OCCT, FDOS, VBNS-PT)
because the prompts had already constrained the form, making strip-
and-compare easy.

## Cross-references

- `mitigations_11_12_13_2026_05_08.md`, full P11/P12/P13 set
- PATTERN-003 (reducer), backstop after this guardrail
- PATTERN-005 (falsifiable_asymmetry), additional guardrail
