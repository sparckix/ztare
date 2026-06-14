---
description: "Command-line entry points for the apparatus: demo, smoke, gates, loop, and the public model-free surfaces."
---

# The `ztare` CLI

> **Up:** [`docs/README.md`](../README.md)

A single command entry point for the adversarial-reasoning engine's
human-facing surface. Replaces `cd repo && python scripts/public/control/<name>.py …`
with `ztare <subcommand> …`.

The CLI is deliberately a thin wrapper — it dispatches to the existing
control scripts and does not own business logic.

## Scope

This CLI is the **ZTARE engine's** human-facing surface only. The
governance / org side (roles, mandates, role daemons, closure
daemons, OKR-tree polling) belongs to the sibling
[`cognitive-firm`](https://github.com/sparckix/cognitive-firm) package
and is deliberately not exposed here. Reviewers who want to compose
ZTARE with a governed organisation install both: `pip install ztare`
plus `pip install cognitive-firm`. The user's own *tenant overlay*
lives in `org/` and uses cognitive-firm primitives.

## Subcommands

| Command | What it does | Underlying script |
|---|---|---|
| `ztare forecast <verb> …` | Forecast-pool, calibration DB, and experiment execution operations | `scripts/public/control/forecast/` plus selected experiment runners |
| `ztare leanmill <verb> …` | LeanMill orchestration ([GP-225](../../research_areas/seams/engine/lean/GP-225_gnn_lemma_relevance_ranker_seam.md)) | `scripts/public/control/leanmill_*.py` |
| `ztare bundle <verb> …` | Sealed-bundle run / verify | `bundle_run.py`, `bundle_verify.py` |
| `ztare charter …` | Project-charter commit | `charter_commit.py` |
| `ztare routine-review …` | RD routine reviews | `rd_routine_review.py` |
| `ztare action-intel …` | Action intelligence read surface ([GP-243](../../research_areas/seams/protocol/GP-243_action_intelligence_loop_seam.md)) | `action_intelligence.py` |
| `ztare autoresearch …` | In-loop autoresearch run and read-only projection surfaces | `Makefile` targets |
| `ztare eigenquestion …` | Advisory eigenquestion proposal + explored-class evidence lint | `eigenquestion_generator.py` |
| `ztare primitive …` | Primitive catalog / amnesia health checks | `Makefile` + `primitive_amnesia` |

`ztare leanmill` verbs: `schedule` (station scheduler), `run` (24/7
runner), `andon` (andon cord), `triage` (post-probe triage),
`backlog` (backlog replenisher).

`ztare bundle` verbs: `run`, `verify`.

## Pass-through `--help`

For any subcommand, `--help` flows through to the underlying control
script's argument parser or verb router. So `ztare forecast --help`
shows the user-facing forecast verb list; `ztare bundle run --help`
shows the `bundle_run.py` flags; and so on. The CLI's own help
(`ztare --help`) is short by design.

`ztare forecast` is intentionally not a menu of every [GP-245](../../research_areas/seams/apparatus/instrumentation/GP-245_forecaster_skill_calibration_seam.md) research
script. It keeps forecast-pool operations, calibration DB surfaces, and
experiment execution/scoring commands that a user could reasonably run:
`pool`, `resolve`, `calibration-stats`, `calibration-db`, `score`,
`ingest-smoke`, `cutoff-panel-run`, `cutoff-panel-ingest`,
`cutoff-panel-score`, `anti-bias-run`, `anti-bias-score`,
`nurture-run`, `nurture-ingest`, `nurture-score`, `elo-refresh`,
`brier-elo`, and `resolve-open-metaculus`. Research-planning,
paper-readiness, packet-generation, and sibling-analysis scripts stay
project-local under `projects/.../tools/`.

## Repository root discovery

The CLI runs the control scripts via subprocess and needs to know
where the repository root is. It tries, in order:

1. `$ZTARE_REPO` environment variable.
2. Walk up from the installed `ztare.cli` module's location.
3. Current working directory if it contains `scripts/public/control/`.

For a `pip install -e .` checkout this resolves automatically. For a
plain `pip install ztare` from PyPI, the control scripts live inside
the installed package data — set `$ZTARE_REPO` to the repository
checkout where ledgers and `org/` state actually live.

## Adding a subcommand

Each new subcommand is one entry in the `_SUBCOMMANDS` table in
[`src/ztare/cli.py`](../../src/ztare/cli.py): a help line plus a
callable that takes the remaining argv and returns an exit code.
Most callables are one-liners that delegate via `_delegate(script,
rest)`. Multi-verb subcommands (LeanMill, bundle) define a small
verb-router function alongside.

Subcommand names should be nouns or noun-verb pairs (e.g.
`routine-review`), match the underlying script's capability rather
than its implementation file, and stay short.

## Examples

```bash
# Forecast pool and calibration surfaces
ztare forecast pool smoke
ztare forecast calibration-stats --help
ztare forecast calibration-db --help

# Forecasting experiment execution surfaces
ztare forecast cutoff-panel-run --mode preview --max-calls 6
ztare forecast nurture-score --pilot-id n3_high_worry_action_policy_v1 --queue projects/llm_forecasting_calibration_program/nurture_intervention_v1/workspace/n3_high_worry_action_policy_dispatch_queue.jsonl

# LeanMill: one-shot station-scheduler plan, then start the 24/7 worker
ztare leanmill schedule --contract analytics/public/leanmill/_legacy_lemma_relevance/...
ztare leanmill run --max-rows 100

# Bundle: run a sealed candidate, then verify
ztare bundle run --substrate gp096_kww_sandbox_17 --rubric kww
ztare bundle verify --bundle path/to/bundle.json

# Project charter commit
ztare charter --substrate ns_l3a --hypothesis-class S

# Action intelligence read
ztare action-intel materialize --no-write
ztare action-intel record-agentic-route --route-json /tmp/autoresearch_route.json --decision-id decision_gp_example_route

# Autoresearch: route RD work, run in-loop, then inspect the read-only projection
ztare autoresearch route --task "test bounded claim X" --project gp_example --rubric gp_example > /tmp/autoresearch_route.json
ztare autoresearch route --task "test bounded claim X" --project gp_example --rubric gp_example --record-decision-id decision_gp_example_route
ztare autoresearch run --project gp_example --rubric gp_example --iters 10
ztare autoresearch run --project gp_example --rubric gp_example --agent-mutator --agent-runtime codex
ztare autoresearch run --project gp_example --rubric gp_example --agent-mutator --agent-judge --agent-committee --agent-inverter --agent-runtime codex
ztare autoresearch substrate-recommend --prompt-only
ztare autoresearch substrate-recommend --agent-recommender --agent-runtime codex
ztare autoresearch projection --project gp_example --out /tmp/gp_example_projection.json
ztare autoresearch hillclimb-audit --project gp_example
ztare autoresearch hillclimb-audit --json --limit 20
ztare autoresearch consequence-audit --project gp_example --json
ztare autoresearch consequence-audit --json
ztare autoresearch rubric-mode-audit --json
ztare autoresearch rubric-mode-audit --rubric rubrics/gp_example.json
ztare autoresearch rubric-mode-audit --freshness-days 14
ztare autoresearch rubric-mode-audit --strict
ztare autoresearch health
ztare autoresearch health --json --strict
ztare autoresearch control-demo --json
ztare autoresearch parent-utility --json
ztare autoresearch operations-intelligence --json --no-markdown --out /tmp/ztare_intel.json
ztare autoresearch dispatch-audit --json
ztare autoresearch dispatch-canary --contract mutator --runtime codex --live --json
ztare autoresearch dispatch-canary --contract judge --call-site judge --runtime codex --live --json
ztare autoresearch dispatch-canary --contract committee --call-site committee --runtime codex --live --json
ztare autoresearch dispatch-canary --contract inverter --call-site inverter_review --runtime codex --live --json
ztare autoresearch subscription-outcomes --json
ztare autoresearch dispatch-parity --json
ztare autoresearch dispatch-parity --contracts text,mutator,judge,committee,inverter --runtime codex --live --json

# Advisory eigenquestion rotation
ztare eigenquestion propose --project gp_example
ztare eigenquestion status --project gp_example
ztare eigenquestion validate --project gp_example

# Primitive catalog and semantic atlas health
ztare primitive health
ztare primitive health --semantic-live --eval
```

`dispatch-parity` replays fixed typed contracts through the API and
subscription paths. The JSON report includes contract parity, per-contract
`quality_score`, and a latency/call-count `cost_proxy`; `--live` only promotes
the subscription leg.

`subscription-outcomes` reads run history only. Fresh rows can carry
prompt-free worker-dispatch receipts, and the report separates completed
subscription receipt counts from aggregate transport rows.

`consequence-audit` is a read-only check for whether the listed kernel
mechanisms do something observable. It classifies each mechanism by consequence
type, names the consumer, samples the current evidence paths, and flags
mechanisms that are unobserved in the selected project or workspace.

`rubric-mode-audit` scans the rubric corpus for Newton/Kepler/calibration
coherence. It uses the same mode contract as launch validation and flags
invalid modes, Newton rubrics with missing projects, missing charters, or
missing secondary-observable sections, and Kepler rubrics that still carry
Generative Yield. Historical unset modes stay summarized; unset modes with
recent run telemetry become attention rows. Use `--strict` when this should
fail the command while attention rows remain.

`health` aggregates the cheap kernel checks into one first page: dispatch
coverage, primitive-catalog freshness, mechanism consequences, in-loop fixture
status, rubric-mode attention, and hill-climb control evidence. Each component
includes a `next_command` pointing to the narrow audit that owns the details;
when health is scoped to a project, rubric, or workspace, those commands carry
the same scope. `evidence_gap` rows are non-blocking by default: they name
mechanisms or transport comparisons that are wired but not yet outcome-evidenced
in the selected scope.

`fixtures` runs the cheap in-loop mechanism matrix. The text and JSON reports
name each mechanism's status, proof boundary, command to try next, and focused
test reference, so dormant mechanisms can be inspected without reading the loop
source first.

`control-demo` materializes a local replay project whose optional in-loop
controls are visible to the normal consequence audit. It is useful for checking
that parallel blitz, primitive-class rotation, and eigenquestion preflight
produce project-scoped artifacts. It is not a live research-quality or transport
lift result.

`operations-intelligence` writes the fuller read-only RD operations packet. Use
it when health points at route-logging, source-health, or workbench-bypass
questions and you need the underlying action-intelligence packet rather than
the compact first-page summary.
