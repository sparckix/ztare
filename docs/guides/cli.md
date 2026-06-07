---
description: "Command-line entry points for the apparatus: demo, smoke, gates, loop, and the public model-free surfaces."
---

# The `ztare` CLI

> **Up:** [`docs/README.md`](../README.md)

A single command entry point for the adversarial-reasoning engine's
operator surface. Replaces `cd repo && python scripts/public/control/<name>.py …`
with `ztare <subcommand> …`.

The CLI is deliberately a thin wrapper — it dispatches to the existing
control scripts and does not own business logic.

## Scope

This CLI is the **ZTARE engine's** operator surface only. The
governance / org side (roles, mandates, role daemons, closure
daemons, OKR-tree polling) belongs to the sibling
[`cognitive-firm`](https://github.com/sparckix/cognitive-firm) package
and is deliberately not exposed here. Operators who want to compose
ZTARE with a governed organisation install both: `pip install ztare`
plus `pip install cognitive-firm`. The user's own *tenant overlay*
lives in `org/` and uses cognitive-firm primitives.

## Subcommands

| Command | What it does | Underlying script |
|---|---|---|
| `ztare forecast <verb> …` | Forecast-pool, calibration DB, and experiment execution operations | `scripts/public/control/forecast/` plus selected experiment runners |
| `ztare leanmill <verb> …` | LeanMill orchestration (GP-225) | `scripts/public/control/leanmill_*.py` |
| `ztare bundle <verb> …` | Sealed-bundle run / verify | `bundle_run.py`, `bundle_verify.py` |
| `ztare charter …` | Project-charter commit | `charter_commit.py` |
| `ztare routine-review …` | RD routine reviews | `rd_routine_review.py` |
| `ztare action-intel …` | Action intelligence read surface (GP-243) | `action_intelligence.py` |

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

`ztare forecast` is intentionally not a menu of every GP-245 research
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
ztare action-intel --since 7d
```
