# Track B: The Bethlehem Steel Test — ZTARE Live Pilot Design

Status: draft
Date: 2026-04-20
Source: Taylor/Paper 5 panel debate verdict

## The Thesis

Paper 5 is an operational doctrine awaiting its absorbing institution. The Taylor
comparison is aspirational but structurally grounded. The panel's prescription:
stop asking whether it's Taylor-level; find one firm willing to implement the
seven principles on one real decision pipeline and measure the before/after.

## What a Pilot Looks Like

### Target: One Decision Pipeline

Pick a knowledge-work decision pipeline where:
1. The decision has a measurable outcome (deal closed/failed, forecast accuracy, analysis accepted/rejected by client)
2. The current process involves human generation + human self-verification (the guild premium)
3. The decision volume is high enough to measure error rates (at least 20 decisions/month)
4. The stakes are high enough that errors matter ($100K+ per wrong decision)

**Candidate pipelines** (in order of feasibility):
- Investment due diligence memo generation (PE/VC)
- Market research report production (consulting)
- Regulatory compliance review (legal/fintech)
- Product requirement specification (tech PM)
- Credit underwriting analysis (banking)

### The Seven Principles Applied to the Pilot

| Principle | Current State (typical) | ZTARE Pilot State |
|-----------|------------------------|-------------------|
| I. Separation | Same person writes and grades the memo | Separate generation (AI+analyst) from verification (AI+reviewer) |
| II. Statelessness | Reviewer reads prior memos, anchored | Reviewer sees only the current memo + rubric, no history |
| III. Pre-registration | No upfront criteria; "good enough" is subjective | Rubric with pass/fail gates written before generation |
| IV. Deterministic gates | All evaluation is subjective | At least 3 binary pass/fail checks (completeness, consistency, source verification) |
| V. Pre-registered holdout | No holdout | 20% of source material withheld; memo must not contradict withheld facts |
| VI. Structural memory | Previous errors are informal "lessons learned" | Kill list: named failure patterns from prior memos that current memo must avoid |
| VII. Adversarial disagreement | Single reviewer | Two independent reviewers + meta-reviewer on disagreement |

### Measurement Protocol

**Before (30-day baseline)**:
- Error rate: % of decisions that were later identified as wrong (6-month lookback)
- Time to decision: calendar days from request to final memo
- Cost per decision: analyst hours + reviewer hours + partner review time
- Rework rate: % of memos sent back for revision

**After (90-day pilot)**:
- Same metrics, measured identically
- Additional: gate pass/fail rates, structural memory size, adversarial disagreement frequency

**Success criteria** (pre-registered):
- Error rate reduction ≥ 30% (Taylor achieved 200-300% throughput; we need at least directional)
- Time to decision reduction ≥ 20% OR error rate reduction ≥ 50% (trade time for quality is acceptable)
- Analyst satisfaction ≥ 3/5 (the guild must not mutiny)
- Cost per decision stable or decreasing (gates add friction; net must be positive)

### The Organizational Friction Map

From the panel debate, the adoption barriers are political, not computational:

| Barrier | Who Resists | Why | Mitigation |
|---------|------------|-----|------------|
| Separation (Principle I) | Senior analysts | "I know my work is good" | Frame as "protecting your reputation — the gates catch errors before the client does" |
| Pre-registration (Principle V) | Partners/MDs | "We need flexibility to pivot" | Start with the rubric as a checklist, not a cage — make it advisory for month 1, mandatory for month 2 |
| Adversarial disagreement (Principle VII) | Reviewers | "I don't need a second opinion" | Frame as "disagreement is signal, not criticism" — the meta-reviewer decides, not the egos |
| Structural memory (Principle VI) | Everyone | "We don't make the same mistake twice" — (they do) | Show the kill list growing; make it a team artifact, not a blame log |

### The Economic Case

From Coase (panel): the pilot works when the cost of NOT adopting exceeds the cost of adopting.

**Cost of adoption**:
- Setup: 2-4 weeks to build rubric, gate harness, and workflow
- Per-decision overhead: ~30 min additional for gates + dual review
- Training: 1 day workshop on the seven principles

**Cost of non-adoption** (the invisible cost):
- One wrong due diligence memo → $500K-$5M bad investment
- One compliance miss → $100K-$1M regulatory fine
- One flawed market sizing → product built on hallucinated premise

The pilot pays for itself if it catches ONE error that would have been a six-figure loss.

## The Deliverable

A one-page executive summary for a firm's decision-maker:
1. What ZTARE is (the one-paragraph version from goodhart_at_every_layer.md)
2. What the pilot measures (error rate, time, cost, satisfaction)
3. What it costs (4 weeks setup, 30 min/decision overhead)
4. What it replaces (nothing — it augments existing workflow with gates)
5. What the exit criterion is (90 days, pre-registered success criteria)

## Next Steps

- [ ] Identify one candidate firm/pipeline (personal network, advisory, or open call)
- [ ] Build the rubric + gate harness for the selected pipeline
- [ ] Run the 30-day baseline measurement
- [ ] Deploy the seven principles for 90 days
- [ ] Publish the case study (the Bethlehem Steel moment)
