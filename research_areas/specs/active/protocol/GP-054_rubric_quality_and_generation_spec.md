# GP-054 — Rubric Quality and Generation Spec

Canonical file-format note: this spec records the GP-054 review/generation
slice. The current rubric JSON schema, mode contract, submission-contract
fields such as `require_i_model_in_submission`, and run-time flag list are
maintained in `docs/concepts/rubric_specification.md`. Do not duplicate new
rubric keys here; reference that document from implementation work.

## Status

Active — opened 2026-04-13 17:58:45 EDT; implemented 2026-04-13 18:21:21 EDT; fixture-verified 2026-04-13 18:21:21 EDT; live-verified 2026-04-13 (GLP-1 run); pre-run gaps emission implemented 2026-04-13 19:27:58 EDT; fixture-verified 2026-04-13 19:27:58 EDT

## Seam

`research_areas/private/seams/GP-054_rubric_quality_and_generation_seam.md`

## Scope

- defines the first implementation slice for GP-054
- adds a pre-run rubric-review command with a hard scenario-validity admissibility gate
- writes durable review and patch-proposal artifacts for operator auditability
- distinguishes rubric-structure failures from thin-evidence-surface failures for evidence-dependent checks
- emits pre-run evidence gaps when the evidence surface is thin so `rubric-review` can bootstrap `evidence-fetch` before any loop run exists

Does not cover:

- in-run scenario-transition sentinel
- lower-threshold `--auto-evolve` changes
- rubric retrospective inheritance across projects
- changes to the rubric JSON schema
- judge-model selection

## Decision

Implement the smallest structural repair that would have prevented the Hormuz dead-frame failure: a pre-run admissibility gate plus broader rubric review. Defer in-run scenario sentinels, richer rubric evolution, and retrospective inheritance to later slices.

## Problem

Rubrics currently have no hard pre-run check for whether the project is modeling a still-operative scenario. That lets the system start runs on invalid objects and only discover the mismatch indirectly, if at all.

## Why It Matters

This is a first-order admissibility failure, not a refinement problem. If the frame is already dead, the run should not start. Better scoring or later rubric evolution does not solve that.

## Constraints

- scenario validity must be treated primarily as a gate, not as a score
- the pre-run check must read the project charter, compiled workspace summary, and rubric
- operator review remains the final control point before patching a rubric
- no hidden side effects that silently rewrite project framing
- artifacts must be versioned and auditable
- first slice remains a standalone pre-run command, not hidden loop behavior
- if integrated with the loop, it must be explicit preflight enforcement, not silent implicit review
- evidence-dependent failures must be tagged when the current evidence surface is too thin to interpret them as pure rubric-design failures
- if the evidence surface is thin, the review layer should emit pre-run evidence gaps in the same schema family that `evidence-fetch` already consumes

## Options

### Option A — Scored scenario-validity criterion inside the rubric

**Pros**

- easy to express in the existing rubric surface
- may catch scenario drift in ordinary scoring

**Cons**

- acts too late; the run has already started
- spends iterations on an invalid frame
- turns an admissibility failure into a scoring event

**Verdict**

Reject as the primary fix.

### Option B — Pre-run gate plus rubric review

**Pros**

- stops dead-frame runs before iteration 1
- matches the actual failure class
- keeps scoring separate from admissibility

**Cons**

- requires a new command and prompt surface
- still depends on a well-structured project charter and workspace summary

**Verdict**

Recommended.

### Option C — Skip gating, improve only `--auto-evolve`

**Pros**

- reuses existing infrastructure
- may improve rubric quality over time

**Cons**

- does not solve the first-run dead-frame problem
- still acts after invalid iterations have already run

**Verdict**

Insufficient.

### Option D — Embed rubric review directly inside `autoresearch_loop.py`

**Pros**

- lower operator friction once the review surface is stable
- could eventually prevent runs from starting without a recent review artifact

**Cons**

- blurs project-setup admissibility with execution behavior too early
- risks hidden side effects at run start
- makes the first verifier harder to interpret because review quality and loop behavior change at once

**Verdict**

Defer. Revisit only after the standalone review command is live-verified on multiple projects.

### Option E — When the evidence surface is thin, have `rubric-review` emit pre-run evidence gaps for `evidence-fetch`

**Pros**

- closes the pre-run bootstrap gap without requiring a loop iteration first
- lets `rubric-review -> evidence-fetch -> evidence-compile -> rubric-review` become a self-contained front-door sequence
- reuses the existing GP-051 fetch machinery instead of inventing a second evidence-acquisition path

**Cons**

- extends GP-054 beyond pure critique into structured gap generation
- needs a stable minimal gap schema and an explicit handoff contract to GP-051
- risks mixing rubric debt and evidence debt if the emitted gaps are too loose

**Verdict**

Accepted and implemented.

## Recommendation

Adopt Option B as one pre-run front door:

1. **`make rubric-review`**
   - front-door command before the first run
   - performs a hard scenario-validity admissibility check
   - if admissible, performs five broader rubric critique checks
   - writes a review artifact and optional patch proposal
   - remains intentionally separate from `autoresearch_loop.py` in the first slice
   - if `evidence_surface_ready` is `false`, emits a pre-run evidence gaps artifact for GP-051 consumption

2. **Explicit loop preflight enforcement**
   - `autoresearch_loop.py` may invoke the same review path only when the operator passes `--rubric_review_before_run`
   - on any non-zero review result, the loop aborts before iteration 1
   - this enforcement reuses the standalone artifact-writing path; it does not duplicate review logic

## Implementation Sketch

### 1. `make rubric-review`

Add:

- module: `src/ztare/rubrics/review_rubric.py`
- Makefile target:

```make
rubric-review:
	$(PYTHON) -m src.ztare.rubrics.review_rubric --project $(PROJECT) --rubric $(RUBRIC)
```

Inputs:

- `projects/<project>/project_charter.md`
- compiled workspace summary:
  - `projects/<project>/workspace/facts.md`
  - `projects/<project>/workspace/candidate_claims.md`
  - fallback: first 3KB of `projects/<project>/evidence.txt` if no workspace summary exists
- `rubrics/<rubric>.json`

Checks:

1. **Scenario-validity admissibility gate**
   - asks whether the operative scenario defined in the charter has already been superseded by current evidence
   - output: `pass` / `fail`

2. **Gaming-surface coverage**
   - asks whether the rubric is missing criteria that would catch known failure classes relevant to the project type
   - failure means the review names a concrete blind spot and proposed criterion-level repair

3. **Evidence-anchor requirement**
   - asks whether the rubric allows internally coherent claims to score well without requiring observable support from the provided evidence
   - failure means at least one criterion can be satisfied without evidence-grounded support

4. **Score-ceiling reachability without evidence**
   - asks whether the current rubric could award a high score to a thesis that cites evidence not present in the actual project materials
   - failure means the review identifies a path to an unjustified high score

5. **Criterion independence**
   - asks whether satisfying one criterion would automatically satisfy another, collapsing the rubric into redundant checks
   - failure means the review identifies at least one overlapping or non-independent criterion pair

6. **Persona blind-spot coverage**
   - asks whether the rubric persona is hostile to the actual known failure modes for this project class or whether it is likely to be charmed by polished but weak claims
   - failure means the review identifies a concrete persona weakness and a proposed tightening

Artifacts:

- `projects/<project>/workspace/rubric_review_<timestamp>.json`
- optional patch proposal:
  - `projects/<project>/workspace/rubric_patch_<timestamp>.json`

Additional review metadata:

- `evidence_surface_ready: true|false`
- if `evidence_surface_ready` is `false`, the two evidence-dependent checks
  - `evidence_anchor_requirement`
  - `score_ceiling_reachability_without_evidence`
  should carry `cause: "evidence_surface_empty"` when they fail because the current surface is too thin to cleanly separate rubric debt from evidence-prep debt
- `evidence_gaps_proposed: true|false`
- optional `evidence_gaps` array in the review artifact

Artifacts emitted when `evidence_surface_ready` is `false` and gaps are proposed:

- `projects/<project>/workspace/evidence_gaps_<timestamp>.json`
- `projects/<project>/workspace/latest_evidence_gaps.json`

Gap source logic:

- synthesize pre-run gaps from:
  - charter evidence requirements
  - rubric criteria that explicitly name missing anchors or external evidence dependencies
- keep the output in the same schema family that `evidence-fetch` already understands so the handoff is mechanical rather than bespoke

Minimum patch proposal schema:

```json
{
  "rubric_file": "rubrics/<rubric>.json",
  "scenario_validity": {
    "status": "pass|fail",
    "evidence_ref": ["..."],
    "suggested_revision": "..."
  },
  "checks_failed": [
    {
      "check_name": "criterion_independence",
      "issue": "...",
      "proposed_fix": "..."
    }
  ]
}
```

Failure behavior:

- if scenario-validity gate fails:
  - command exits non-zero
  - no run should start until charter/rubric is revised
- if `evidence_surface_ready` is `false`, the review should still run, but it should warn the operator to compile/refresh evidence before acting on evidence-anchor failures as pure rubric fixes
- if `evidence_surface_ready` is `false` and gaps are proposed, the review also emits a pre-run gaps file so the operator can run `make evidence-fetch` before any loop iteration exists

Deferred enforcement path:

- later work may let `autoresearch_loop.py` require a recent passing `rubric_review_<timestamp>.json` before iteration 1 without rerunning review
- any future stronger integration should still enforce the presence/result of a review artifact rather than silently bury review logic inside the loop

## Open Questions

1. Should the review artifact also preserve the raw LLM critique text, or only the structured fields?
2. Do we want a small project-type selector now, or should the prompt infer domain style from charter + workspace summary alone?
3. After live verification, should the loop support a stronger `--require-rubric-review` mode that checks for a recent passing artifact instead of rerunning review at start?
4. Should pre-run gap emission remain limited to thin-surface cases, or should `rubric-review` be allowed to propose fetch gaps even when the surface is substantive but incomplete?
