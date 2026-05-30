---
description: "First 30 minutes for a new ZTARE reader or agent."
---
# First 30 Minutes

> **Up:** [Documentation map](../README.md)

This path is for a new reader or agent opening ZTARE for the first time. It
checks the runnable substrate, names the durable records, and points to the
right next document for each kind of work.

The goal of the first half hour is not to understand every subsystem. It is to
learn the map, verify the public runnable path, and choose the right workflow
without confusing validator work, research-operations work, and org-runtime
work.

The current roadmap is organized around four priorities: hard-problem
campaigns, the discovery kernel, recursive self-improvement, and
organizational learning. Keep that frame in mind while reading; many older
files are useful historical provenance, not the current priority stack.

## 0-5: Open the Vault Map

ZTARE is Obsidian-compatible by default. Open the repository root as the vault,
then start from:

1. `README.md`
2. `docs/README.md`
3. `docs/public_claim_register.md`
4. `docs/concepts/system_position_and_module_map.md`

The core rule: chat is not the system of record. Durable artifacts live under
`projects/`, `research_areas/`, `org/`, `ztare_workspace/`, `analytics/`, and
the public ledgers.

Boundary to keep straight: ZTARE is the applied research stack and tenant
overlay. The reusable organization kernel lives in
[`cognitive-firm`](https://github.com/sparckix/cognitive-firm). Read `org/`
here as the ZTARE deployment of that kernel, not as a second canonical upstream.

Use this mental model while reading:

```text
hard problem or operating question -> route choice
-> validator / proof / script / panel / human-agent work
-> durable artifact -> ledger or outcome -> next routing decision
```

## 5-15: Run The Public Demo And Smoke

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
make demo
make smoke-public
```

The public demo runs three small evaluation-failure reproducers. It is not a
demo of the current frontier engine; it is a quick way to see the core
discipline: a check can pass while the real structural question fails.

The public smoke target exercises:

- org runtime structure and transition-log replay;
- forecast-pool contract, forecast, aggregate, resolve, score, calibrate flow;
- action-intelligence read-model checks.

It does not invoke live model calls. Maintainer-only publish checks and Docker
checks live in the Makefile reference; they are not part of the first-reader
path.

## 15-25: Pick the Right Track

| Goal | Start |
|---|---|
| Understand the whole stack | `docs/concepts/architecture.md` |
| Evaluate public claims and non-claims | `docs/public_claim_register.md` |
| Understand proof execution / governance gate / residual compiler | `docs/concepts/closure_claim_governance.md` |
| Understand current priorities | `priority_roadmap.md` |
| Run a bounded claim or data-substrate test | `docs/guides/workflow.md` |
| Do frontier work before a bounded evidence packet exists | `docs/guides/workflow.md` section 0 |
| Inspect the org runtime | `docs/guides/org_runtime_quickstart.md` |
| Inspect forecast-market work | `research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md` |
| Inspect action intelligence | `research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md` |
| Review the current research-company architecture | `docs/concepts/ztare_research_company_architecture.md` |
| Learn the repo with an agent | `docs/guides/agent-prompts.md` |

If you are using an agent, do not start with a broad "summarize this repo"
request. Use the route-choice prompt in `docs/guides/agent-prompts.md` and make
the agent name the durable artifact it expects to produce.

## 25-30: Agent Prompt

```text
You are helping me understand ZTARE. Read README.md, docs/README.md,
docs/guides/first-30-minutes.md, docs/concepts/architecture.md,
docs/guides/workflow.md, docs/guides/org_runtime_quickstart.md, and
docs/guides/agent-prompts.md. Then explain:

1. the durable system of record;
2. whether my task belongs in the substrate-prober workflow, workbench workflow,
   program hardening workflow, org runtime overlay, or a tiny manual note;
3. the safest next command or file to inspect;
4. what artifact should be written if the work should persist.

My task is: [describe task].
```
