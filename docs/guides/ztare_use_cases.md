---
description: "Use cases for ZTARE across diligence, legal, scientific, policy, product, security, formal, and other source-backed reasoning work."
---

# ZTARE use cases

> Up: [`docs/guides/README.md`](README.md)

ZTARE is for work where a fluent answer is not enough. Use it when you need to
turn a messy project into something you can inspect, challenge, narrow, and
hand to someone else with the source files still attached.

The common object is not an industry, and it is not the UI. It is a reasoning
project with a thesis, sources, evidence, checks, a review trail, and a next
step.

```text
project -> thesis -> sources -> evidence -> checks -> review -> next step
```

A source is the raw material: a contract, paper, deck, dataset, log, note,
transcript, repo, or model output. Evidence is the part of that source that is
actually tied to the project thesis. ZTARE helps you keep that difference
inspectable.

The Project Workbench is one visualization and control surface over this state.
The repo also contains CLI paths, evidence compilers, run-readiness checks,
report-readiness checks, evaluator-hardening artifacts, LeanMill proof
governance, public evidence maps, and read models. The use cases below are for
ZTARE as the reasoning compiler; the workbench is how many users will operate
the local project path.

## Who should use it

Use ZTARE if you have local files or formal artifacts and need to know what you
can stand behind before you send a memo, investment view, report, proof note,
research summary, or decision recommendation.

Good fits:

- people doing diligence on a company, market, policy, product, incident, or
  scientific claim
- people reviewing AI-assisted work before it becomes a deliverable
- people inheriting a folder of sources and trying to recover the current
  thesis, missing support, and next useful check
- people running repeated project reviews who want failures and revisions to
  stay visible instead of disappearing into chat history

Weak fits:

- quick answers with no source files
- generic task management
- team chat or inbox workflows
- domains where the user cannot inspect or share the underlying material
- situations where professional judgment can be skipped

## Professions and jobs

### Private equity, venture, and investment diligence

Job: decide whether an investment thesis survives contact with the source pack.

Use ZTARE to:

- state the current investment thesis and the main ways it could be wrong
- bind the thesis to CIMs, data rooms, customer notes, market reports, product
  logs, expert-call notes, and model outputs
- separate source existence from evidence support
- save what changed after partner review
- keep the next diligence question visible

Example projects:

- "Is retention quality strong enough to support the revenue multiple?"
- "Does customer concentration change the downside case?"
- "Does the market-size claim survive the cited sources?"

### Law firms and legal teams

Job: review a matter file, argument, investigation, or compliance position
without losing the connection to source documents.

Use ZTARE to:

- summarize the working position and the documents it depends on
- mark which exhibits, contracts, policies, emails, or transcripts support each
  point
- surface missing or stale support before a memo leaves the team
- record reviewer decisions without treating model prose as authority

This is not a legal-advice engine. It is a source-backed reasoning system for
lawyers and legal teams who remain responsible for the judgment.

Example projects:

- "Which facts support the proposed argument?"
- "Which contract clauses support the risk memo?"
- "What is missing before the internal investigation summary is defensible?"

### Research scientists and labs

Job: harden a scientific or technical thesis against papers, data, failed runs,
and competing explanations.

Use ZTARE to:

- track the current thesis and alternatives
- bind claims to papers, datasets, notebooks, logs, and experiment outputs
- preserve negative results and failed branches
- ask what evidence would change the conclusion
- prepare a reviewable summary before writing a paper or proposal

Example projects:

- "Does this intervention improve the outcome, or did the control fail?"
- "Which prior papers actually support this mechanism?"
- "What would falsify the current interpretation of the run?"

### Consulting, strategy, and corporate development

Job: turn scattered sources into a recommendation that survives executive
review.

Use ZTARE to:

- keep the recommendation, assumptions, and source support in one project
- challenge market, cost, risk, and implementation claims
- save unresolved questions as next steps instead of burying them in a deck
- inspect what changed between drafts

Example projects:

- "Should we enter this segment now?"
- "Which acquisition risks are supported by evidence versus speculation?"
- "Which assumptions drive the recommendation?"

### Product, growth, and customer research

Job: decide what customers are saying, what is inferred, and what should be
tested next.

Use ZTARE to:

- bind a product thesis to interviews, tickets, analytics, experiments, and
  sales notes
- separate customer quotes from interpretation
- track which product claim still lacks support
- turn review into a concrete next experiment

Example projects:

- "Do customers want automation, or do they want review confidence?"
- "Which feature request is common enough to prioritize?"
- "What does the churn evidence actually support?"

### Policy, public-interest, and nonprofit research

Job: make a policy or program claim inspectable before it becomes public.

Use ZTARE to:

- connect a policy claim to statutes, reports, datasets, interviews, and field
  notes
- mark uncertainty and unsupported extrapolation
- keep the next evidence request explicit
- preserve the source path behind a public summary

Example projects:

- "Which evidence supports this proposed intervention?"
- "What is the strongest objection the current report does not answer?"
- "Which data source is stale or missing?"

### Security, risk, and incident review

Job: reconstruct what happened, what is known, and what should happen next.

Use ZTARE to:

- bind a working diagnosis to logs, alerts, tickets, timelines, and postmortem
  notes
- separate confirmed facts from plausible theories
- save the next action after review
- keep historical project folders recoverable

Example projects:

- "Which logs support the incident timeline?"
- "What evidence rules out the leading diagnosis?"
- "What follow-up would change the risk assessment?"

### Journalism, investigations, and expert research

Job: decide which statements are supported before publishing or briefing.

Use ZTARE to:

- attach claims to interviews, documents, datasets, public records, and notes
- identify unsupported leaps
- preserve the path from source to statement
- keep sensitive judgment separate from raw model prose

Example projects:

- "Which documents support this paragraph?"
- "Which claim needs one more source?"
- "What is the cleanest version of the story that the evidence supports?"

## LeanMill use cases

The project path handles source-backed reasoning. LeanMill handles the formal
side: work where a statement can be translated into a checkable proof or
rule-shaped artifact.

Today LeanMill is strongest for Lean and mathematical proof work. The same idea
matters outside pure math when a domain can express part of the work as a
formal specification, policy rule, protocol invariant, contract condition,
safety property, or compliance rule. In those domains, the useful split is:

- ZTARE manages the human project, source files, evidence, and review trail
- LeanMill checks the formal fragment when there is one
- the report should say what was checked formally, what remained judgment, and
  what evidence would change the conclusion

Examples:

- a research proof note where the informal idea and the Lean artifact must stay
  aligned
- a protocol review where an invariant can be checked, but the product risk
  still needs source-backed review
- a policy or compliance project where a rule can be represented formally, but
  interpretation and evidence still belong in the project file

Do not treat a formal check as the whole answer. It is one strong check inside a
larger project.

## How to choose the first project

Choose a project where the value of inspection is obvious:

- there is a clear thesis or recommendation
- at least three source files matter
- at least one support issue is plausible
- the next step would change the decision, memo, report, or experiment

Avoid starting with a giant corpus. A good first project is a folder you can
understand in one sitting, with one question you actually care about.

Related docs:

- [`README.md`](../../README.md)
- [`first-30-minutes.md`](first-30-minutes.md)
- [`workflow.md`](workflow.md)
- [`forensic_workbench_interface.md`](../concepts/forensic_workbench_interface.md)
- [`leanmill_architecture.md`](../concepts/leanmill_architecture.md)
