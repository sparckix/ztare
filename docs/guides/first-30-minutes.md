---
description: "First 30 minutes for a new ZTARE reader or agent: green offline check, the durable records, the right route."
---
# First 30 Minutes

> Up: [Documentation map](../README.md)

Thirty minutes should leave you with three things: a green offline value check, a map of the durable records, and the right route for your task. Most mistakes come from launching a loop before the project is ready, or from treating out-of-loop agent work as if it were an in-loop validation run.

One question frames the current public roadmap: can a project move from thesis and source files to a bounded result, support issue, saved review, or next falsifier? Keep it in mind while reading. Many older files serve as historical provenance; this path is the current entry point.

## 0–5: run the first value check

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -e ".[full]"
make hello
```

`make hello` is the first value check: a ready project-intake file validates, a malformed intake file is blocked before in-loop routing, and a plausible overclaim is demoted to bounded wording, missing evidence, and a next falsifier. It writes no persistent runtime state.

For the full offline public review path, use `make first-run`. It chains the value demo, gaming-catalog audit, benchmark-evidence checks, the frozen evaluator-hardening proof-point check, claim-boundary audit, terminology audit, public smoke, adversarial entry-path checks, and docs checks.

## 5–15: inspect a concrete project trace

```bash
ztare project walkthrough --ops-demo
ztare autoresearch trace \
  --project ops_root_cause_diagnosis_demo \
  --rubric ops_root_cause_diagnosis_demo \
  --intake projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json \
  --brief
```

The [ops demo](../../projects/ops_root_cause_diagnosis_demo/) is synthetic, but it is a real ZTARE path: typed local sources, a bounded root-cause claim, explicit rivals, evidence gaps, graph-derived in-loop focus, readiness check, and an optional one-iteration run. Use it before a custom project because it shows the boundary between source and evidence prep, read-only inspection, and the validation engine.

A healthy brief trace shows `run readiness: ready`, fresh source and evidence state, no blockers, and the remaining local verification targets. Use `--json` on the same trace command when a script needs the full carrier chain.

## 15–20: check the catalog and public smoke

```bash
make gaming-catalog-audit
make demo
make smoke-public
```

`make gaming-catalog-audit` checks the [public catalog](../gaming_behavior_catalog.md) against the live vector registry, promotion evidence, hardening map, and current executable fixture anchors. It is the quick way to verify that the catalog hook remains evidence-bounded.

`make demo` runs three small evaluation-failure reproducers and shows a related discipline: a check can pass while the structural question still fails.

`make smoke-public` exercises the org runtime structure and transition-log replay, the forecast-pool contract flow (forecast, aggregate, resolve, score, calibrate), and the action-intelligence read models. It makes no live model calls. Maintainer-only publish checks and Docker checks live in the [Makefile reference](../reference/make_targets.md), outside the first-reader path.

## 20–25: open the vault map

ZTARE is Obsidian-compatible by default. Open the repository root as the vault, then start from:

1. [README.md](../../README.md)
2. [docs/README.md](../README.md)
3. [gaming_behavior_catalog.md](../gaming_behavior_catalog.md)
4. [evidence_atlas/README.md](../evidence_atlas/README.md)
5. [glossary.md](../concepts/glossary.md)
6. [public_claim_register.md](../public_claim_register.md)
7. [system_position_and_module_map.md](../concepts/system_position_and_module_map.md)

Chat is not the system of record. Durable files live under `projects/`, `research_areas/`, `org/`, `ztare_workspace/`, `analytics/`, and the public ledgers.

One boundary to keep straight: ZTARE is the applied research stack and tenant overlay, while the reusable organization kernel lives in [cognitive-firm](https://github.com/sparckix/cognitive-firm). Read `org/` here as the ZTARE deployment of that kernel, with no second canonical upstream.

As a mental model while reading:

```text
local project -> thesis -> sources and evidence -> readiness check
-> readiness check or run -> saved review, support issue, or next test
```

## 25–30: pick the right route

| Route | Use it when | Start |
|---|---|---|
| Project brief | Source files, evidence refs, or a bounded task still need to be prepared | `ztare project walkthrough` and [workflow.md](workflow.md) section 0 project brief |
| In-loop autoresearch | Bounded claim, evaluator/gate, rubric, and saved output are ready | `ztare autoresearch trace --brief`, then its recommended first command |
| Out-of-loop research operations | Source gathering, proof splitting, setup, synthesis, or one-off agent work | `ztare autoresearch route` and [workflow.md](workflow.md) section 0 out-of-loop route |
| Proof work | Lean formalization, proof search, or proof-credit governance | [leanmill_architecture.md](../concepts/leanmill_architecture.md) |
| Org/runtime work | Roles, mandates, tasks, gates, or transition logs are the object | [org_runtime_quickstart.md](org_runtime_quickstart.md) |

Then use the deeper map:

| Goal | Start |
|---|---|
| Understand the whole stack | [architecture.md](../concepts/architecture.md) |
| Review the evidence graph before trusting the architecture | [evidence_atlas/README.md](../evidence_atlas/README.md) |
| Decode recurring terms and evidence levels | [glossary.md](../concepts/glossary.md) |
| Evaluate public claims and non-claims | [public_claim_register.md](../public_claim_register.md) |
| Understand proof execution, the governance gate, and the residual compiler | [closure_claim_governance.md](../concepts/closure_claim_governance.md) |
| Understand current priorities | [priority_roadmap.md](../../priority_roadmap.md) |
| Run a bounded claim or project/data test | [workflow.md](workflow.md) section 0 in-loop route |
| Prepare missing project or evidence files before a loop | [workflow.md](workflow.md) section 0 project brief; [examples/project_packets/](../../examples/project_packets/) for ready and malformed fixtures |
| Inspect an operational diagnosis starter | [quickstart.md](quickstart.md) section "Create or probe project data"; [ops demo project](../../projects/ops_root_cause_diagnosis_demo/) |
| Do frontier work before bounded intake and evidence files exist | [workflow.md](workflow.md) section 0 out-of-loop route |
| Inspect the org runtime | [org_runtime_quickstart.md](org_runtime_quickstart.md) |
| Inspect forecast-market work | [forecast-pool decision market spec](../../research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md) |
| Inspect action intelligence | [action-intelligence loop design](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md) |
| Review the current research-company architecture | [ztare_research_company_architecture.md](../concepts/ztare_research_company_architecture.md) |
| Learn the repo with an agent | [agent-prompts.md](agent-prompts.md) |

If you are using an agent, skip the broad "summarize this repo" request. Use the route-choice prompt in [agent-prompts.md](agent-prompts.md) and make the agent name the durable file or record it expects to produce.

## After 30: agent prompt

```text
You are helping me understand ZTARE. Read README.md, docs/README.md,
docs/evidence_atlas/README.md, docs/evidence_atlas/claim_cards.md,
docs/concepts/glossary.md, docs/guides/first-30-minutes.md,
docs/concepts/architecture.md, docs/guides/workflow.md,
docs/guides/org_runtime_quickstart.md, and docs/guides/agent-prompts.md.
Then explain:

1. the durable system of record
2. whether my task belongs in in-loop autoresearch, out-of-loop research
   operations, project-brief prep, program hardening, org runtime overlay,
   or a tiny manual note
3. the safest next command or file to inspect
4. what file or record should be written if the work should persist.

My task is: [describe task].
```
