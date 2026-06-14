---
description: "One-page pilot brief: the cost of confidently-wrong AI analysis."
---
# ZTARE Epistemic Verification, Pilot Brief

> **Up:** [Documentation map](../README.md)

## The Problem

AI-generated analysis is fast and cheap, and it produces confident errors at a
rate human review does not reliably catch under time pressure. As generation cost
falls, output volume grows faster than manual verification capacity. An
organization that generates faster than it verifies accumulates undetected errors
in its decision record.

## What ZTARE Is

ZTARE is a verification engine for AI-augmented knowledge work. It runs a
structured loop: an AI generates a thesis, a second AI and a battery of
deterministic gates verify it, failures are recorded as constraints, and the
next iteration must respect every prior failure. The output is a thesis that
passed the gates under pre-registered criteria, or a declaration that the
evidence is insufficient.

ZTARE is not a model. It is a control layer applied to models.

## What the Pilot Measures

We instrument one decision pipeline (e.g., due diligence memo, market research
report, compliance review) and measure four metrics for 30 days before and 90
days during:

| Metric | Before (baseline) | After (pilot) |
|--------|-------------------|---------------|
| **Error rate** | % of decisions later identified as wrong | Target: 30%+ reduction |
| **Time to decision** | Calendar days, request to final memo | Target: 20%+ reduction OR 50%+ error reduction |
| **Cost per decision** | Analyst + reviewer hours | Target: stable or decreasing |
| **Rework rate** | % of memos sent back for revision | Tracked as secondary signal |

Success criteria are pre-registered before the pilot starts.

## What It Costs

- **Setup**: 2-4 weeks to build the rubric, gate harness, and workflow integration
- **Per-decision overhead**: ~30 minutes additional for gate checks + dual review
- **Training**: 1-day workshop on the seven verification principles
- **Infrastructure**: Cloud compute for LLM calls (~$1-5 per verified decision)

## What It Replaces

Nothing. ZTARE augments existing workflow. Analysts still write memos. Reviewers
still review. The difference: before review, the memo passes through a gate
battery that catches structural errors (missing counterfactual, unsupported
causal claim, contradicted by withheld data) that human review routinely misses
under time pressure.

## The Seven Principles (from Epistemic Verification)

1. **Separation**: The person who writes the thesis does not grade it
2. **Statelessness**: The reviewer sees only the current memo and rubric, no anchoring to prior work
3. **Pre-registration**: Pass/fail criteria are written before generation, not after
4. **Deterministic gates**: At least 3 binary checks (completeness, consistency, source verification)
5. **Pre-registered holdout**: 20% of source material withheld; memo must not contradict it
6. **Structural memory**: Named failure patterns from prior memos become constraints on future ones
7. **Adversarial disagreement**: Two independent reviewers; a meta-reviewer resolves disagreement

## The Evidence

ZTARE has been tested on 15+ pre-registered scientific discovery sandboxes:
- Recovered a 6-parameter transcendental physics law from raw data under sealed gates
- Recovered fractional-exponent decay laws at machine precision
- Produced a 453-entry labeled taxonomy of how AI optimizers game scored rubrics
- Detected specification-layer Goodhart's Law (the rubric itself was wrong) in qualitative analysis
- All results published with full iteration logs, debate transcripts, and gate harness code

## The Ask

One decision pipeline. 90 days. Pre-registered success criteria. We measure
before and after. If it works, you have the case study. If it doesn't, you have
a well-documented negative result and we stop.

## Contact

Commercial licensing contact: see `README.md` §License.
