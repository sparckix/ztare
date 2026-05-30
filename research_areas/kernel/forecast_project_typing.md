# Forecast Project Typing

Legacy combined note:

- seam now lives at `research_areas/seams/GP-022_forecast_project_typing_seam.md`
- spec now lives at `research_areas/specs/active/GP-022_forecast_project_typing_spec.md`

## Status

Active

## Scope

- define the distinction between bounded directional forecast projects and calibrated probabilistic forecast projects
- decide how ZTARE should type, enforce, and route them
- clarify what the current EU central project did and did not achieve

Does not cover:

- implementation of a full new probabilistic forecasting engine
- retrofitting older projects immediately
- public-facing product messaging

## Decision

ZTARE should explicitly split forecast work into two project types: a `directional_forecast` type and a `probabilistic_forecast` type. The current EU central project should remain a successful `directional_forecast` project and should not be forced to emit a point probability. If the operator wants `% intact` / `% break`, that should be a new `probabilistic_forecast` project with extra contract requirements, not a reinterpretation of the current charter.

## Problem

ZTARE currently has enough machinery to make the distinction visible, but not enough typing discipline to make it explicit. The EU central project includes a forecast subquestion and a probability DAG, but its charter, README, and score behavior all treat the forecast as a bounded directional tilt rather than a calibrated point probability.

That creates operator confusion. The system appears to be "doing forecasting," so it is natural to ask for `% stays / breaks`. But the current project object is not actually a point-probability project. It is a central-pillar project with a secondary forward-looking tilt.

Without an explicit project-type distinction, three things get conflated:

- directional forecasts
- probabilistic forecasts
- posterior-updating tools like the Bayesian engine

## Why It Matters

This is a trust seam.

If ZTARE emits a `%` from a project that was never structured to justify one, it reintroduces the exact false-precision problem the engine is meant to block.

At the same time, if the system has a Bayesian engine and probability DAGs but cannot explain when those are sufficient for a real point forecast, it looks internally inconsistent.

The goal is not to suppress forecasting. The goal is to separate:

- honest directional forecast claims
- honest point-probability claims

and make the contract difference explicit.

## Constraints

- must preserve the usefulness of bounded directional forecasts
- must not allow a probability DAG alone to license false-precision output
- should reuse existing charter and score-regime machinery where possible
- should not require immediate migration of all historical projects
- should keep EU centrals valid on its own terms

## Options

### Option A — Keep The Distinction Informal

**Description**

Keep handling this through README language, charter prose, and operator judgment.

**Pros**

- zero implementation cost
- no migration burden

**Cons**

- repeats the same confusion on future projects
- leaves a real product/architecture boundary undocumented
- makes the Bayesian engine look more general than it is

**Verdict**

Not enough. The ambiguity is already costly.

### Option B — Add Forecast Project Typing

**Description**

Add an explicit project type distinction:

- `directional_forecast`
- `probabilistic_forecast`

and define what each one is allowed to claim.

**Pros**

- resolves the current confusion cleanly
- preserves bounded forecasts without pretending they are probability models
- gives the Bayesian engine a proper home
- fits naturally with existing charter/project typing work

**Cons**

- adds one more contract surface to explain
- may require new verifier rules later

**Verdict**

Best next move.

### Option C — Force All Forecast Projects Into Point Probabilities

**Description**

Treat every forecast-capable project as if it should eventually emit a `%`.

**Pros**

- superficially simple
- gives operators the number they want

**Cons**

- collapses bounded mechanism projects into fake precision
- breaks current EU charter intent
- overstates what the Bayesian engine currently justifies

**Verdict**

Wrong direction.

## Recommendation

Choose Option B.

Concretely:

- keep `eu_union_load_bearing_pillars` as a `directional_forecast` success
- do not force `% stays / breaks` out of this project
- if a point probability is wanted, fork a new `probabilistic_forecast` project seeded by the current EU thesis, evidence, and DAG

What is not being recommended:

- closing forecasting as a category
- treating the current Bayesian engine as irrelevant
- pretending the current EU project failed because it did not emit a number

## Implementation Sketch

Phase 1:

- add a charter/manual distinction between:
  - `directional_forecast`
  - `probabilistic_forecast`
- define minimal contract requirements for each

Phase 2:

- update project scaffolding so a new forecast project can be initialized in one of the two modes
- directional mode:
  - allow bounded tilt language
  - forbid fake point-probability claims
- probabilistic mode:
  - require explicit event ontology
  - require target outcome definition
  - require prior/calibration note
  - require probability DAG semantics aligned to the forecast target

Phase 3:

- decide whether score gates should treat unsupported `%` claims as a typed failure mode
- decide whether the Bayesian updater needs a companion “initial probability calibration” artifact rather than only posterior updates

Verifier:

- re-open EU only as a type-check example:
  - current project should cleanly classify as directional, not probabilistic
- create one small probabilistic pilot project only after the type boundary is documented

## Open Questions

- should project type live in `project_charter.md`, the rubric, or both?
- should unsupported point-probability claims become a hard fail or a soft cap?
- is the current Bayesian DAG format sufficient for probabilistic forecast projects, or does it need typed outcome/calibration metadata?

## Debate Log

### Turn 1 — Codex

Opened this seam after the EU central project stabilized at `67` with a bounded 2035 forecast tilt, while the operator still wanted `% stays / breaks`. The core issue is not "can ZTARE forecast?" but "what type of forecast project is this?" The elegant move is to type forecast projects explicitly rather than stretching a directional project until it pretends to be a calibrated probability model.

### Turn 2 — Codex

Implemented the first slice of GP-022:

- `project_charter.md` now supports `## Forecast Type`
- the charter scaffold emits the section
- the operator manual documents the distinction
- the EU central charter is explicitly marked `directional_forecast`
- mutator and judge prompts now read and enforce the distinction at the prompt-contract level

What remains is the harder question: whether unsupported `%` claims in a `directional_forecast` project should become a typed score-bearing failure rather than just a prompt-level rule.

### Turn 3 — Codex

Implemented Phase 2 of GP-022 using the same pattern as GP-014:

- added `unsupported_point_probability_claim` to the judge contract
- added `forecast_overclaim_rationale`
- directional projects now get a scorer-level cap at `50` if a `%` forecast is smuggled in without the project being typed as probabilistic

This closes the specific soft-surface gap Claude identified: forecast typing is no longer prompt-only.
