# GP-022 Forecast Project Typing Spec

## Status

Active

## Scope

- define the difference between bounded directional forecast projects and probabilistic point-forecast projects
- define how that distinction should live in the charter and scorer contract
- keep the EU load-bearing project valid on its own terms

Does not cover:

- implementing a full calibrated probability engine
- retrofitting every historical forecast-adjacent project immediately
- public go-to-market framing

## Decision

ZTARE should explicitly type forecast projects as either `directional_forecast` or `probabilistic_forecast`. Directional projects may emit bounded tilt claims but not `%` claims. Probabilistic projects may emit `%` claims only when the target event, horizon, and model basis are explicit. Unsupported `%` claims in a directional project should be scorer-capped, not merely discouraged by prompt text.

## Problem

ZTARE already had forecast-adjacent machinery:

- probability DAGs
- a Bayesian updater
- forecast language in some theses

But it lacked an explicit type boundary saying when a point-probability claim was actually valid. That made the system look internally inconsistent.

## Why It Matters

Without explicit forecast typing, the system invites false precision.

If a project that is really about current-state classification or pillar ranking can silently mutate into a `%` forecast project, ZTARE starts recreating the very symbolic theater it was designed to punish.

## Constraints

- preserve bounded directional forecasts as valid outputs
- do not let a probability DAG alone authorize a `%` claim
- should reuse existing charter/scorer machinery where possible
- should not require immediate repo-wide migration

## Options

### Option A — Keep The Distinction Informal

**Description**

Rely on README prose and operator judgment.

**Pros**

- no new code
- low friction

**Cons**

- confusion repeats
- `%` overclaim remains a prompt-level vulnerability

**Verdict**

Not enough.

### Option B — Charter Typing Only

**Description**

Add forecast type to the charter and prompts, but not the scorer.

**Pros**

- simple
- clarifies intent

**Cons**

- repeats the pre-GP-014 mistake
- prompt-only rules can erode under optimization pressure

**Verdict**

Incomplete.

### Option C — Charter Typing Plus Scorer Gate

**Description**

Add forecast typing to the charter, scaffold, prompts, and scorer contract.

**Pros**

- resolves the ambiguity cleanly
- blocks unsupported `%` claims deterministically
- preserves directional forecasts without pretending they are probability models

**Cons**

- still needs live verification
- full probabilistic project support remains a later layer

**Verdict**

Recommended.

## Recommendation

Adopt Option C.

Current first two slices are shipped:

- `Forecast Type` in `project_charter.md`
- scaffold/manual support
- mutator/judge prompt awareness
- scorer gate via:
  - `unsupported_point_probability_claim`
  - `forecast_overclaim_rationale`

The EU load-bearing project remains a `directional_forecast`.

## Implementation Sketch

Phase 1:

- charter field
- parser support
- scaffold/manual support
- prompt awareness

Phase 2:

- judge schema fields for unsupported `%` claims
- scorer cap at `50` for unsupported point-probability claims in directional projects

Phase 3:

- live verifier
- then, only if needed, open a separate probabilistic EU forecast project

## Open Questions

- should unsupported `%` claims eventually become a hard fail instead of a cap?
- should project type live only in the charter, or also in the rubric?
- does a future probabilistic project need extra calibration metadata beyond the current DAG shape?
