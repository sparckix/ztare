# GP-022 Forecast Project Typing Seam

## Problem Snapshot

The EU load-bearing project stabilized as a successful bounded 2035 forecast at `67`, but the operator still reasonably wanted `% stays / breaks`.

That exposed a missing type boundary:

- bounded directional forecast projects
- probabilistic point-forecast projects

ZTARE already had probability DAGs and a Bayesian updater, but no explicit contract saying when a `%` claim was actually in-bounds.

## Current State

Two slices have shipped:

1. Forecast typing exists in `project_charter.md`
2. Unsupported `%` claims in a `directional_forecast` project now trigger a scorer cap

What remains is live verification and eventual migration of other projects into the clearer type system.

## Debate Log

### Turn 1 — Codex

Opened the seam after the EU load-bearing project stabilized at `67` with a bounded 2035 forecast tilt, while the operator still wanted `% stays / breaks`. The key question became: what type of forecast project is this?

### Turn 2 — Codex

Recommendation stabilized:

- keep the EU project as a successful `directional_forecast`
- do not force `%` output from it
- if a point probability is wanted, open a separate `probabilistic_forecast` project

### Turn 3 — Codex

Implemented the first slice:

- `project_charter.md` can declare `Forecast Type`
- scaffold/manual support exists
- mutator and judge prompts read the contract
- EU is explicitly typed as `directional_forecast`

### Turn 4 — Claude / Gemini / Codex Synthesis

Prompt-only typing was not enough. The system had already learned this lesson in GP-014: prompt rules erode under optimization pressure if they are not backed by scorer logic.

### Turn 5 — Codex

Implemented Phase 2:

- judge contract now includes `unsupported_point_probability_claim`
- scorer hard-caps a directional project at `50` when it sneaks in an unsupported `%` claim

### Turn 6 — Codex

The seam is now narrower:

- the contract exists
- the scorer gate exists
- what remains is a live verifier proving the cap fires in a real run rather than only in a unit-style smoke test
