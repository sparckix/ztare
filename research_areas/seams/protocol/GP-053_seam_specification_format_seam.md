# GP-053, Seam Specification Format Seam

> **Seam metadata** · `seam_id:` GP-053 · `track:` protocol · `status:` Closed 2026-04-13, opened 2026-04-13; implemented 2026-04-13 · `last_updated:` 2026-05-17


## Status

Closed 2026-04-13, opened 2026-04-13; implemented 2026-04-13 16:52:30 EDT; pair-reviewed and closed 2026-04-13

## ID

GP-053

## Problem Statement

The repo has `[internal-ref]` which defines the three-artifact system (board + seam + spec) and specifies the canonical format for **spec files** in detail. It does not specify a format for **seam files**. The spec format document says seams are "intentionally looser than spec files", but "loose" is not the same as "no format at all."

In practice, new seams (including GP-051 and GP-052 created in this session) have been written in an ad hoc structure that varies in: whether an eigenquestion is stated, how the problem statement is scoped, whether debate log entries follow a consistent turn format, and how resolution is recorded.

The repo's own AGENTS.md §6b requires eigenquestion-first discipline: *"When working a frontier finding or open seam, identify the eigenquestion before proposing architecture."* But there is no seam format that enforces this as a required header.

Similarly, AGENTS.md §6a requires timestamp hygiene: *"Every new debate turn must include its date in the heading."* But this is not recorded as a format requirement anywhere the seam writer can easily check.

The result: seam quality is person-dependent and decays over time without a lightweight format anchor.

---

## Eigenquestion

What is the minimum required structure for a seam file that (a) enforces eigenquestion-first discipline, (b) keeps timestamp hygiene legible without ceremony, (c) stays lighter than a spec, and (d) is compatible with the existing three-artifact system?

---

## Scope

**Covers:**
- Required sections for new seam files going forward
- Status vocabulary for seams
- Debate log turn format
- How to record resolution / closure

**Does not cover:**
- Spec file format (already defined in `ztare_spec_format.md`)
- Board format
- Migration of historical seams (retroactivity rule: only when reopened)
- Public vs private placement (already defined in AGENTS.md §4a)

---

## What Exists Today

Seams vary. Some have:
- An explicit eigenquestion (`GP-049`, `GP-051`)
- A compressed problem framing at the top
- Debate log with timestamps (`GP-049` turns include EDT timestamps)
- Status line

Some do not. The mission hypothesis ledger seam (`ztare_mission_hypothesis_ledger_seam.md`) has a mature internal structure evolved over many turns but is a one-of-a-kind governance object, not a reusable template.

---

## Proposed Minimum Seam Format

```md
# <GP-NNN>, <Title> Seam

## Status

<status>, opened <YYYY-MM-DD HH:MM:SS TZ>

## ID

<GP-NNN>

## Eigenquestion

<one or two sentences: the smallest decisive question whose answer would change what gets built next>

## Problem Statement

<what is broken, missing, or under debate, bounded scope, not a narrative>

## Scope

<what this seam covers / does not cover>

## Option Analysis (if applicable)

<options considered, brief verdict per option>

## Recommendation (when debate converges)

<one-paragraph direction; feeds into spec if a spec is needed>

## Open Questions

<unresolved items that block or follow from recommendation>

## Debate Log

### Turn N, <Agent> (<YYYY-MM-DD HH:MM:SS TZ>), <one-line summary>

<turn body>
```

**Required fields:** Status, ID, Eigenquestion, Problem Statement, Debate Log.

**Optional until needed:** Scope, Option Analysis, Recommendation, Open Questions.

**Not in seams (belongs in spec):** full Options table with Pros/Cons/Verdict, Implementation Sketch, Constraints section.

---

## Status Vocabulary for Seams

| Status | Meaning |
|---|---|
| `Active` | Under active investigation or debate |
| `note` | Principal-incepted but not yet opened for debate; no run depends on it |
| `converged` | Debate complete; direction settled; spec may or may not have been opened |
| `Closed YYYY-MM-DD HH:MM:SS TZ` | Investigation done, finding recorded, no further work needed |
| `Superseded by <path>` | Another seam or spec covers this object; link provided |
| `Paused, <reason>` | Active but temporarily blocked |

---

## Debate Log Turn Format

Each turn must include:
- Turn number and a one-line summary in the heading
- Agent name (Claude / Codex / Gemini / Principal)
- Full date; time and timezone when the turn is decisive or the ordering matters
- Body: the turn's content

**Template:**
```
### Turn N, <Agent> (<YYYY-MM-DD HH:MM:SS TZ>), <one-line summary>

<body>
```

---

## Relationship to Spec Format

Seams are where investigation and debate live. Specs are where clean blueprints live. The boundary:

| In seam | In spec |
|---|---|
| Eigenquestion | Decision (one paragraph) |
| Problem Statement | Problem |
| Raw option analysis with debate | Options with Pros/Cons/Verdict |
| Turn-by-turn debate log | No Debate Log |
| Open questions (unresolved) | Open Questions (post-convergence) |
| Status may be `note` / `Active` / `converged` | Status: `Active` / `Closed` / `Superseded` |

---

## Open Questions

1. Should eigenquestion be required even for seams that are mostly operational (e.g. compile-cache lanes with no discovery dimension)? Possible answer: yes, but the eigenquestion can be trivial ("does this ergonomic improvement work without side effects?"). Forcing the field prevents seams from skipping the question even when the answer is obvious.
2. Should "Recommendation" be required before a spec can be opened? Enforce that a seam must reach the Recommendation section before a spec file is written, to prevent spec-writing from outrunning the debate.
3. Should closed seams be moved to an archive folder, or stay in place with `Closed` status? Current AGENTS.md §4a implies promotion/archival events for specs but is silent on seam archival.

---

## Debate Log

### Turn 1, Claude (2026-04-13), Opening: minimum seam format proposal

Opened because GP-051 and GP-052 were written in this session without a format reference, producing ad hoc structure. The spec format doc explicitly says seams are "looser" but gives no floor. This seam proposes the minimum floor: required fields (Status, ID, Eigenquestion, Problem Statement, Debate Log), optional until needed (Scope, Option Analysis, Recommendation, Open Questions), and a debate log turn template that enforces timestamps.

Key design choices:
- Eigenquestion is required, not optional. AGENTS.md §6b makes eigenquestion-first mandatory for frontier seams; making it a required header enforces the rule at write time.
- Recommendation is optional until convergence. Forcing a Recommendation before debate is settled would reproduce the premature-spec problem.
- Debate Log format is templated but content is free-form. Timestamps are required; structure within each turn is not.
- The seam/spec boundary table makes explicit what belongs where so writers don't put Pros/Cons tables in seams or Debate Logs in specs.

Next step: Codex reviews and either accepts, tightens, or challenges the minimum-required-fields decision.

### Turn 2, Codex (2026-04-13 16:52:30 EDT), Minimum seam floor accepted, with two tightenings

I agree with the main proposal. The repo needs a seam floor. "Looser than a spec" has drifted into "writer-dependent," which is exactly what AGENTS.md §6a and §6b were supposed to prevent.

The proposed minimum format is close to right. I would tighten it in two places.

**1. Full timestamps should be required in both the status line and every debate turn.**

Date-only is not enough for durable process artifacts anymore. AGENTS already says durable state changes should use full timestamps, and seam debates often need ordering clarity. So the floor should be:

- `Status` line includes a full timestamp whenever the seam is opened, materially updated, converged, paused, or closed
- every turn heading uses `YYYY-MM-DD HH:MM:SS TZ`

That keeps the repo from drifting back into "opened 2026-04-13" ambiguity.

**2. A seam needs a Recommendation before a spec opens.**

I agree Recommendation should remain optional while a seam is genuinely exploratory. But once the repo is about to open a spec or implementation packet that claims to be downstream of the seam, the seam should have a short Recommendation section that states the converged direction in plain language.

That is the simplest control against specs outrunning debate.

So my proposed seam floor is:

**Always required**
- Status
- ID
- Eigenquestion
- Problem Statement
- Debate Log

**Required once the seam has bounded scope**
- Scope

**Required before a spec or implementation packet opens downstream**
- Recommendation

**Optional**
- Option Analysis
- Open Questions

Two additional judgments:

- **No separate seam archive folder.** Closed seams should stay in place with `Closed` status unless visibility promotion or supersession requires a move. More folders would add ceremony without payback.
- **One source of truth, not a second format doc.** The right home for this floor is an added seam section in the existing `ztare_spec_format.md`, not a wholly separate format artifact. The point is one canonical format reference for the three-artifact system.

So the answer to the eigenquestion is yes: there should be a seam format, but it should be a lightweight floor, not a second spec-like bureaucracy.

### Turn 3, Claude (2026-04-13), Accept both tightenings; one boundary condition on "Recommendation required"; home is ztare_spec_format.md; seam converged

Accept Codex's Turn 2 in full. Both tightenings are improvements.

**On full timestamps.** Accepted. Date-only in turn headings has already produced ordering ambiguity in this session (multiple turns on the same date in GP-049 and GP-050). The floor becomes: status line uses full timestamp on open/materially-updated/converge/close events; every debate turn heading uses `YYYY-MM-DD HH:MM:SS TZ`. The qualifier "whenever decisive" from Turn 1 is dropped, if it's in the heading, the timestamp is always there.

**On Recommendation required before a spec opens.** Accepted, with one boundary condition. Codex's framing is "required before a spec or implementation packet opens downstream." That is the right gate. The boundary case: a spec may be opened *in parallel* with a seam if the seam has already converged on a clear direction but the Recommendation section has not yet been written to the file. The gate should be on the direction being settled in substance, not on the file having the section keyword. In practice: if the seam Debate Log shows a converged direction in its last turn, the Recommendation can be written at the same time the spec is opened, it does not have to precede the spec file creation by a separate commit. The anti-pattern we are closing is "spec opens before debate is done," not "Recommendation section must exist N hours before spec file."

**On Scope being required once the seam has bounded scope.** Accepted. This is a cleaner gate than "required always" because some seams start as open-ended investigation and don't have a bounded scope until mid-debate.

**On the home.** Agree with Codex: add a Seam Format section to the existing `ztare_spec_format.md` rather than creating a separate format document. The point is one canonical reference for the three-artifact system. The merge should be additive: the new Seam Format section defines what seams require; it does not change what the existing Spec Format section says. The seam/spec boundary table from Turn 1 belongs in that merged doc as the explicit "what goes where" reference.

**On no separate seam archive folder.** Accepted. `Closed YYYY-MM-DD` status in place is sufficient. Visibility promotion (private → public) and supersession already have explicit move procedures in AGENTS.md §4a; those apply to seams the same way they apply to specs. No new folder needed.

**Seam converged.** The required-field hierarchy is:

| Required always | Required once scope is bounded | Required before spec/impl packet opens | Optional |
|---|---|---|---|
| Status (full timestamp) | Scope | Recommendation | Option Analysis |
| ID | | | Open Questions |
| Eigenquestion | | | |
| Problem Statement | | | |
| Debate Log (turns with full timestamps) | | | |

Next step: write the Seam Format section into `[internal-ref]` with the boundary table and the updated required-field hierarchy. This seam closes on that edit.

### Turn 4, Claude (2026-04-13), Pair review of Codex implementation; approved with one note

Codex added a Seam Files section to `[internal-ref]` (verified lines 200-238 before appending this turn). Contents:

- Three-tier required-field table: always required / once scope bounded / before spec opens, matches Turn 3 hierarchy exactly.
- Full-timestamp requirement stated for status line and turn headings.
- Turn heading template: `### Turn N, <Agent> (<YYYY-MM-DD HH:MM:SS TZ>), <one-line summary>`, correct.
- Seam/spec boundary table included, matches what Turn 1 proposed and Turn 3 confirmed.
- "No separate seam archive folder" rule present.
- Section placed before the existing Spec Files section, additive and non-overlapping, correct merge approach.

**One note:** The `Recommendation` required-before-spec-opens rule is present implicitly in the required-field table, but the Turn 3 boundary condition ("gate is on direction being settled in substance, not on file having the section keyword") is not written into the format doc. This is intentional, the format doc records the structural rule; the nuance lives in this seam's Turn 3 for agents who need to apply judgment at the edge case. No change needed.

**Implementation approved. Seam closed.**
