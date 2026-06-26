---
description: "One-page pilot brief: using ZTARE to audit AI-assisted decision work."
---
# ZTARE Pilot Brief

> Up: [Documentation map](../README.md)

## The problem

AI-generated analysis is fast and cheap, and it produces confident errors at a
rate human review does not reliably catch under time pressure. As generation
cost falls, output volume grows faster than manual verification capacity. An
organization that generates faster than it verifies accumulates unsupported
claims, missing sources, weak comparisons, and stale assumptions in its decision
record.

## What ZTARE is

ZTARE is a zero-trust workbench for generating, stress-testing, and auditing
claims from agents. It separates proposal, critique, deterministic gates,
ledgers, review packets, and explicit non-claims so a reviewer can inspect what
survived, what was demoted, and what should be tested next.

ZTARE is not a model and not a replacement for domain review. It is a control
layer around models and human workflows.

Run the smallest public demo with:

```bash
make hello
```

The demo feeds an overbroad claim through the claim-discipline surface and
returns bounded wording, missing evidence, and a next falsifier.

## What the pilot measures

Pick one bounded decision pipeline, such as a due diligence memo, market
research report, compliance review, source-gathering workflow, or research
agent evaluation. The pilot measures whether ZTARE makes unsupported claims
visible earlier and leaves a better audit trail.

For organizational diagnosis, start with one repeated question over existing
operations data: "why did this metric degrade?", "which workflow step creates
the delay?", or "what root-cause claim would change the next management
action?" ZTARE should not be pointed at the whole organization at once. It is
best used to turn one agentic diagnosis into a bounded claim with declared
data, explicit non-claims, adversarial challenges, deterministic or
evidence-backed checks, and a ledgered status. The surrounding workflow can
live in a tenant or the reusable cognitive-firm runtime. ZTARE supplies the
verification discipline for claims that should not be accepted on narrative
plausibility alone.

| Metric | Baseline | Pilot signal |
|---|---|---|
| Unsupported claims | Claims later found to lack source, baseline, or scope support | Fewer unsupported claims reach final review |
| Time to first useful critique | Time from draft to first actionable objection | Earlier missing-evidence or weak-comparison findings |
| Rework quality | Revision cycles caused by unclear evidence, missing sources, or overclaiming | Rework points to named gates or falsifiers |
| Auditability | Can a reviewer trace the claim to sources, checks, non-claims, and next tests? | More decisions have inspectable review packets |

Success criteria should be pre-registered before the pilot starts. A pilot can
be useful even if it returns a negative result: the point is to learn whether
the workbench catches consequential failure modes in that pipeline.

## What it requires

- A bounded work object: memo, claim, reproduction task, proof obligation, or
  agent output.
- A project-intake file or equivalent intake record: task, bounded claim, sources,
  evidence refs, non-claims, expected command, and next falsifier.
- A small rubric or contract that says what counts as support.
- One or more deterministic checks, plus a human or independent-agent review
  path for cases the checks cannot decide.
- A baseline record of how the current workflow catches or misses these
  failures.

## What it does not replace

Analysts still write memos. Reviewers still review. Domain experts still own
domain judgments. ZTARE adds claim boundaries, gate checks, evidence trails,
and explicit non-claims before a result is promoted.

## Operating principles

1. The proposer does not grade itself.
2. Pass/fail criteria are written before the result is inspected.
3. Deterministic checks catch what can be made mechanical.
4. Source, baseline, and scope failures are recorded as first-class results.
5. Repeated failure modes become reusable checks only after evidence justifies
   promotion.
6. Every promoted claim carries non-claims and a next falsifier.

## Public evidence to inspect first

- `make hello`: smallest claim-demotion demo.
- `make first-run`: offline public review path.
- [LLM Gaming Behavior Catalog](../gaming_behavior_catalog.md): observed
  self-certification and specification-gaming behaviors, with catch patterns
  and evidence tiers.
- [Evidence atlas](../evidence_atlas/README.md): claim-by-claim evidence
  crosswalk, non-claims, commands, and caveats.
- [Evaluator-hardening packet](../evidence_atlas/packets/evaluator_hardening.md):
  bounded public proof point with a frozen three-arm suite and an explicit
  ordinary-review blocker before any four-arm upgrade.

## The ask

One bounded decision or research pipeline. Pre-register the failure modes and
success criteria. Run the current workflow and the ZTARE-assisted workflow on a
small sample. Compare whether unsupported claims are caught earlier and whether
the review trail is easier to inspect.

## Contact

Commercial licensing contact: see `README.md` §License.
