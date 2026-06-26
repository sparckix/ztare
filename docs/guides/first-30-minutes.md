---
description: "First 30 minutes for a new ZTARE reader or agent."
---
# First 30 Minutes

> Up: [Documentation map](../README.md)

This path is for a new reader or agent opening ZTARE for the first time. It
checks the runnable path, names the durable records, and points to the
right next document for each kind of work.

The first half hour should leave you with three things: a green offline value
check, a map of the durable records, and the right route for your task. Most
mistakes come from launching a loop before the project surface is ready, or from
treating out-of-loop agent work as if it were an in-loop validation run.

The current public roadmap is organized around one first-reader question:
can a claim be traced from proposal, through evidence and gates, to a bounded
verdict or next falsifier? Keep that frame in mind while reading. Many older
files serve as historical provenance, and this path is the current entry point.

## 0-5: Run The First Value Check

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
make hello
```

`make hello` is the first value check: a ready project-intake file validates, a
malformed intake file is blocked before in-loop routing, and a plausible overclaim
is demoted to bounded wording, missing evidence, and a next falsifier. It
writes no persistent runtime state.

For the full offline public review path, use `make first-run`. It chains the
value demo, gaming-catalog audit, benchmark-evidence checks, the frozen
evaluator-hardening proof-point check, claim-boundary audit, terminology audit,
public smoke, adversarial entry-path checks, and docs checks.

## 5-15: Inspect A Concrete Project Trace

```bash
ztare project walkthrough --ops-demo
ztare autoresearch trace \
  --project ops_root_cause_diagnosis_demo \
  --rubric ops_root_cause_diagnosis_demo \
  --intake projects/ops_root_cause_diagnosis_demo/ops_root_cause_diagnosis_demo_intake.json \
  --brief
```

The ops demo is synthetic, but it is a real ZTARE path: typed local sources,
a bounded root-cause claim, explicit rivals, evidence gaps, graph-derived
in-loop focus, preflight, and an optional one-iteration run. Use this before a
custom project because it shows the boundary between source/evidence prep,
read-only inspection, and the validation engine.

The brief trace should show `run readiness: ready`, fresh source/evidence
surfaces, no blockers, and the remaining local verification targets. Use
`--json` on the same trace command when a script needs the full carrier chain.

## 15-20: Check The Catalog And Public Smoke

```bash
make gaming-catalog-audit
make demo
make smoke-public
```

`make gaming-catalog-audit` checks the public catalog against the live vector
registry, promotion evidence, hardening map, and current executable fixture
anchors. It is the quick way to verify that the catalog hook remains
evidence-bounded.

The public demo runs three small evaluation-failure reproducers. It is a quick
way to see a related discipline: a check can pass while the structural question
still fails.

The public smoke target exercises:

- org runtime structure and transition-log replay
- forecast-pool contract, forecast, aggregate, resolve, score, calibrate flow
- action-intelligence read-model checks

It does not invoke live model calls. Maintainer-only publish checks and Docker
checks live in the Makefile reference and are outside the first-reader path.

## 20-25: Open the Vault Map

ZTARE is Obsidian-compatible by default. Open the repository root as the vault,
then start from:

1. `README.md`
2. `docs/README.md`
3. `docs/gaming_behavior_catalog.md`
4. `docs/evidence_atlas/README.md`
5. `docs/concepts/glossary.md`
6. `docs/public_claim_register.md`
7. `docs/concepts/system_position_and_module_map.md`

The core rule: chat is not the system of record. Durable artifacts live under
`projects/`, `research_areas/`, `org/`, `ztare_workspace/`, `analytics/`, and
the public ledgers.

Boundary to keep straight: ZTARE is the applied research stack and tenant
overlay. The reusable organization kernel lives in
[`cognitive-firm`](https://github.com/sparckix/cognitive-firm). Read `org/`
here as the ZTARE deployment of that kernel, with no second canonical upstream.

Use this mental model while reading:

```text
hard problem or operating question -> route choice
-> validator / proof / script / panel / human-agent work
-> durable artifact -> ledger or outcome -> next routing decision
```

## 25-30: Pick The Right Route

| Route | Use it when | Start |
|---|---|---|
| Project intake | Source files, evidence refs, or a bounded task still need to be prepared | `ztare project walkthrough` and `docs/guides/workflow.md` section 0 project intake |
| In-loop autoresearch | Bounded claim, evaluator/gate, rubric, and artifact output are ready | `ztare autoresearch trace --brief`, then its recommended first command |
| Out-of-loop research operations | The work is source gathering, proof splitting, setup, synthesis, or one-off agent work | `ztare autoresearch route` and `docs/guides/workflow.md` section 0 out-of-loop route |
| Proof work | The task is Lean formalization, proof search, or proof-credit governance | `docs/concepts/leanmill_architecture.md` |
| Org/runtime work | Roles, mandates, tasks, gates, or transition logs are the object | `docs/guides/org_runtime_quickstart.md` |

Then use the deeper map below.

| Goal | Start |
|---|---|
| Understand the whole stack | `docs/concepts/architecture.md` |
| Review the evidence graph before trusting the architecture | `docs/evidence_atlas/README.md` |
| Decode recurring terms and evidence levels | `docs/concepts/glossary.md` |
| Evaluate public claims and non-claims | `docs/public_claim_register.md` |
| Understand proof execution / governance gate / residual compiler | `docs/concepts/closure_claim_governance.md` |
| Understand current priorities | `priority_roadmap.md` |
| Run a bounded claim or project/data test | `docs/guides/workflow.md` section 0 in-loop route |
| Prepare missing project/evidence surfaces before a loop | `docs/guides/workflow.md` section 0 project intake; [examples/project_packets/](../../examples/project_packets/) for ready and malformed fixtures |
| Inspect an operational diagnosis starter | `docs/guides/quickstart.md` section "Create or probe a project/data surface"; `projects/ops_root_cause_diagnosis_demo/` |
| Do frontier work before bounded intake and evidence surfaces exist | `docs/guides/workflow.md` section 0 out-of-loop route |
| Inspect the org runtime | `docs/guides/org_runtime_quickstart.md` |
| Inspect forecast-market work | [Forecast-pool decision market spec](../../research_areas/specs/active/protocol/GP-230_forecast_pool_decision_market_spec.md) |
| Inspect action intelligence | [Action-intelligence loop seam](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md) |
| Review the current research-company architecture | `docs/concepts/ztare_research_company_architecture.md` |
| Learn the repo with an agent | `docs/guides/agent-prompts.md` |

If you are using an agent, do not start with a broad "summarize this repo"
request. Use the route-choice prompt in `docs/guides/agent-prompts.md` and make
the agent name the durable artifact it expects to produce.

## After 30: Agent Prompt

```text
You are helping me understand ZTARE. Read README.md, docs/README.md,
docs/evidence_atlas/README.md, docs/evidence_atlas/claim_cards.md,
docs/concepts/glossary.md, docs/guides/first-30-minutes.md,
docs/concepts/architecture.md, docs/guides/workflow.md,
docs/guides/org_runtime_quickstart.md, and docs/guides/agent-prompts.md.
Then explain:

1. the durable system of record
2. whether my task belongs in in-loop autoresearch, out-of-loop research
   operations, project intake, program hardening, org runtime overlay,
   or a tiny manual note
3. the safest next command or file to inspect
4. what artifact should be written if the work should persist.

My task is: [describe task].
```
