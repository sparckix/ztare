---
id: PATTERN-010
name: business_framing
version: 1
status: active
discovered: 2026-05-08
triggers:
  lexical: [stuck, diminishing-returns, exhausted, multiple-iterations-no-progress]
  structural: [N_consecutive_iterations_no_signal, team_at_grandiosity_or_retreat_risk]
  problem_classes: [pre_category_emergence, pure_analysis_drift]
spawn:
  mode: external_reframe
  subagents:
    - role: business_strategy_consultant
      description: NO mathematical training. Strong meta-cognition. Pattern-matches to business literature.
      tools: [read]
output_schema: business_diagnosis_v1
fallback: null
preconditions:
  - apparatus_has_been_iterating: at least 5 iterations on same problem
  - operator_or_agent_at_risk_of_grandiosity_or_retreat: yes
chain_position: orthogonal  # not in the math chain; orthogonal pressure
related_patterns:
  - PATTERN-001 (friction_debate, math-side complement)
falsifiable_test: |
  Over N>=8 business-framing deployments on stuck campaigns, the generative-prompt
  deliverable must, within the next 3 campaign iterations, produce a measurable
  unstick — defined as either (a) a new F-row closure or (b) a pre-registered
  residual reclassification — at a rate >=2x the unstick-within-3-iterations rate
  of matched stuck campaigns where no business-framing dispatch fired. If the
  post-deployment unstick rate is below 2x the no-deployment baseline, the external
  reframe earns nothing and demotes.
  metric_source: business_diagnosis_v1 dispatch dates in
  pattern_deployment_ledger.jsonl vs F-row closures / residual reclassifications in
  the residual_to_lever ledger over the following 3 iterations.
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# Pattern 10, Business-Framing Agent for Pre-Category-Emergence Stuck

## Problem

When iterating on a hard math problem produces diminishing returns,
the apparatus team can fall into one of two failure modes:

1. **Grandiosity**: prematurely claim a "paradigm shift" / "new
   vocabulary unifier" and waste time on theatrical naming.
2. **Retreat**: declare the problem "too hard for now" and abandon,
   missing the case where one more reframe would unstick.

Both modes share a root cause: the team is too IN the math to see
the meta-structure of where they're stuck.

A business-strategy consultant with NO mathematical training but strong
meta-cognition can pattern-match the situation against broader
literature (Christensen disruption, Andreessen platform, SaaS
emergence) and produce a diagnosis the math-team can't.

## Pattern

Spawn an agent given ONLY meta-cognitive framing of the stuck point, 
NO mathematical content. Ask:

1. Business-strategy diagnosis: what kind of "stuck" is this?
   - Missing platform feature?
   - Pre-category-emergence?
   - Insight phase before product-market-fit articulation?
2. What business pattern matches the multi-tradition convergence?
3. Recommended next move: keep grinding, name the unifier, wait,
   or pivot?
4. Generative prompt that would unstick?

The agent's lack of math knowledge prevents math-laundering. The
business pattern library is large, battle-tested.

## Why it works

- No math knowledge means no math-laundering
- Business pattern library (Christensen, Andreessen, etc.) is large
- Generative prompt format produces ACTIONABLE deliverable, not
  diagnostic-only
- External vantage prevents grandiosity AND retreat

## When to deploy

- Multiple iterations producing diminishing returns
- Architecture team exhausted, at risk of grandiosity OR retreat
- "Stuck" feels emotional / vague; need disciplined external reframing
- Every N iterations as a periodic sanity check

## Anti-pattern

**BUSINESS-AS-MATH**: treating the agent's diagnosis as mathematical
content. The output is META-COGNITIVE / STRATEGY, not math. Apply it
to the team's NEXT MOVE, not the proof.

**MATH-LITERATE-CONSULTANT**: spawning a business agent with math
context defeats the purpose. Strict no-math-content prompt.

## Concrete example

2026-05-08 ~07:50, after 7 hours of iteration on NS Track B Clay
closure, business-framing agent diagnosed:

> "This is **pre-category emergence stuck** (NOT platform-blocked). 4
> traditions converging on same wall = strongest market signal that
> a category is REAL and UNNAMED. Like SaaS before 2005. Recommended
> move: 2-3 day TIMEBOXED naming sprint with FALSIFIABLE-PREDICTION
> requirement."

Generative prompt: "If all four traditions are shadows of the same
object, what is the single property of that object that, if true, would
make all four shadows necessary, and what is the one experiment,
runnable in our current apparatus this week, where the unifier predicts
something different from any individual tradition?"

This produced the naming-sprint deliverable + falsifiable prediction
requirement that subsequently caught OCCT/FDOS/VBNS-PT as LAUNDERED.

## Cross-references

- `naming_sprint_deliverable_2026_05_08.md`, output of this pattern
- `agent_orchestration_meta_patterns_2026_05_08.md` Pattern 2
