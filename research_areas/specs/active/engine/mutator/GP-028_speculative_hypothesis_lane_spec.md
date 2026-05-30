# GP-028 Speculative Hypothesis Lane Spec

## Status

Draft

## Scope

- preserve candidate wedges that appear during mutation before scoring can kill them
- keep the first slice passive and non-influential
- prevent GP-012 / GP-014 laundering regressions

Does not cover:

- mutator read access to staged wedges
- evaluator score credit for staged wedges
- thesis rendering from staged wedges
- a fourth bounded-discriminator observable state
- GP-023 pre-registration changes

## Decision

Implement Option B only:

- a passive extraction artifact lane for candidate wedges
- written after mutation generation
- before evaluation
- with no score impact and no feedback path

## Problem

V4 hardening correctly suppresses unsupported claims, but it also suppresses speculative candidate wedges that may be worth later investigation.

ZTARE currently forces a false binary:

- scored thesis truth
- or discarded noise

There is no typed place for:

- speculative hypotheses
- counterarguments
- governance/legal wedges
- hostile objections
- budget/mechanism wedges

that are not yet earned but should not disappear immediately.

## Why It Matters

If this is left unchanged:

- v1-style wedges continue to disappear in v4 runs
- operator patching remains the de facto workaround
- the system loses exploratory sharpness without preserving why

If fixed narrowly:

- candidate wedges are preserved for inspection
- GP-028 becomes empirically testable on live runs
- GP-012 / GP-014 stay intact because the lane remains passive

## Constraints

- extraction must happen from mutator output before evaluation
- staged wedges must receive no score credit
- staged wedges must not render into `thesis.md` / `current_iteration.md`
- staged wedges must not be readable by the mutator in this first slice
- post-failure relabeling is forbidden
- staged wedges must expire by run or phase

## Options

### Option A — External Discipline Only

**Description**

Operators keep wedges manually in notes or chat context.

**Pros**

- no code changes
- no laundering risk inside ZTARE artifacts

**Cons**

- does not solve the preservation problem inside the system
- does not generate auditable wedge traces
- keeps operator patching as the workaround

**Verdict**

Insufficient.

### Option B — Passive Extraction Artifact

**Description**

After the mutator produces a candidate, run a lightweight extractor on the mutator output and write candidate wedges into a dedicated workspace artifact.

**Pros**

- narrowest useful slice
- no score-path changes
- no mutator contamination
- auditable live traces

**Cons**

- preserved wedges still require later manual or architectural promotion
- extraction quality will need live validation

**Verdict**

Recommended.

### Option C — Active Staging

**Description**

Allow the mutator to read preserved wedges in future iterations.

**Pros**

- stronger preservation loop
- may help wedges survive long enough to find anchors

**Cons**

- introduces indirect score-path contamination risk
- much closer to a laundering reopening if not heavily guarded

**Verdict**

Later possibility, not first slice.

## Recommendation

Implement Option B now.

### Artifact

Persist under `projects/<project>/workspace/`:

- `candidate_wedges.json`
- `candidate_wedges_brief.md`

Optional later:

- `latest_candidate_wedges.json`

### Extraction timing

Extraction must run:

1. after the mutator produces its raw candidate output
2. before evaluator scoring
3. before any score-based rejection or operator rescue

This preserves forward-committed timing and blocks post-hoc laundering.

### Schema

Each wedge entry should include:

- `wedge_id`
- `created_on`
- `generation_iter`
- `score_regime_fingerprint`
- `candidate_source`
  - e.g. mutation attempt id or current iteration id
- `wedge_type`
  - `hypothesis`
  - `counterargument`
  - `governance`
  - `legal`
  - `mechanism`
  - `other`
- `status`
  - `staged`
  - `expired`
  - `promoted`
  - `discarded`
- `raw_excerpt`
- `extractor_rationale`
- `anchor_targets`
  - list of what would count as anchor evidence
- `expires_after_run`

### Contract

- staged wedges are not evidence
- staged wedges are not derived constraints
- staged wedges are not thesis claims
- staged wedges are not visible to the evaluator as support
- staged wedges are not visible to the mutator in this first slice

### Expiry

Default expiry should be:

- after `N` distinct runs
- or at explicit phase reset

Expired wedges remain in the artifact with:

- `status: expired`

They should not silently disappear.

### Promotion

This first slice does not implement automated promotion.

But the schema must leave room for explicit promotion events later:

- `status: promoted`
- `promotion_event_id`
- `promotion_reason`

## Implementation Sketch

### Step 1 — Add extractor helper

- new helper module for wedge extraction
- input: raw mutator candidate text
- output: zero or more staged wedge objects

### Step 2 — Persist wedge artifacts

- `workspace/candidate_wedges.json`
- `workspace/candidate_wedges_brief.md`

### Step 3 — Wire into mutation path

- call extractor after mutation generation
- before evaluation
- write staged wedge artifacts

### Step 4 — Add strict guardrails

- no read path from wedge artifact into mutator/evaluator
- no thesis rendering path
- no score impact

### Step 5 — Add regression

- candidate containing a novel wedge gets extracted
- same candidate after score failure cannot be newly re-labeled post-hoc
- expired wedges are marked expired after threshold
- wedge artifact does not alter scoring artifacts

## Open Questions

- what exact extractor heuristic is sufficient for the first slice?
- should operator-authored wedges ever be allowed into the same lane, or only model-generated ones?
- should the artifact be append-only, or should expired/discarded entries be compacted later?
