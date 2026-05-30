# ZTARE Spec Format

## Status

Active — updated 2026-05-18 (added the required seam header block: `seam_id` / `track` / `status` / `last_updated`, and the one-time backfill rule)

## Scope

- defines the canonical work-item tracking ontology for ZTARE
- defines the difference between board entries, seam files, and spec files
- defines the required format for spec files going forward

Does not cover:

- seed/program registry policy
- public product documentation
- retroactive migration of every historical combined note

## Decision

ZTARE should use a three-artifact system for active work: a single canonical board, a messy seam file for investigation/debate, and a clean spec file for the implementation blueprint. New work items should follow this separation by default. Older combined notes do not need immediate migration, but when a legacy item is reopened the board must mark it as `legacy_combined` until it is split or retired.

## Problem

ZTARE's current tracking is conflated.

Some work items live only in the hardening board. Some live only in a kernel note with embedded debate. Some have a clean recommendation mixed with a turn-by-turn log in the same file. Some product/distribution items never appear in the board at all.

That creates three recurring failures:

- it is hard to tell what is actually in flight
- it is hard to tell whether a file is an investigation or a blueprint
- naming and placement drift over time, so even correct work becomes hard to retrieve

## Why It Matters

This is not just a documentation hygiene problem.

ZTARE is now running multiple parallel workstreams:

- kernel hardening
- workflow / operator UX
- evidence RAM / compiler
- distribution artifacts
- product/workbench planning

Without a consistent tracking ontology, the system starts losing its own state. That slows implementation, creates duplicated debates, and makes it too easy for a soft narrative about what is happening to drift away from the actual implementation boundary.

## Constraints

- must keep one canonical board for in-flight work
- must separate investigation from blueprint
- should preserve path stability where practical
- should not require a full repo migration in one shot
- must make legacy combined files visible rather than pretending they are already cleanly split

## Options

### Option A — Keep The Current Mixed System

**Description**

Keep the hardening board, roadmap, and mixed kernel notes as-is.

**Pros**

- zero migration effort
- no path churn

**Cons**

- the conflation problem remains
- active work stays hard to scan
- new files will continue to drift in naming and placement

**Verdict**

Not acceptable.

### Option B — Single File Per Work Item

**Description**

Force each work item into one file that contains both debate and spec.

**Pros**

- simpler file counting
- no need to maintain seam/spec links

**Cons**

- recreates the conflation problem immediately
- investigation mess keeps colliding with implementation blueprint
- board links become less meaningful

**Verdict**

Too coarse.

### Option C — Board + Seam + Spec

**Description**

Use:

- one canonical board for all in-flight work
- one seam file for investigation/debate
- one spec file for the clean blueprint

with explicit legacy handling for older combined notes.

**Pros**

- clean separation of concerns
- easier retrieval and scanning
- works well for a research-heavy engine where debate is part of the process
- keeps implementation docs crisp without losing the debate trail

**Cons**

- requires two links per serious work item
- requires migration discipline

**Verdict**

Recommended.

## Recommendation

Adopt Option C.

Canonical structure:

- board:
  - `research_areas/ZTARE_BOARD.md`
- seam files:
  - `research_areas/seams/<ID>_<slug>_seam.md`
- spec files:
  - `research_areas/specs/active/<ID>_<slug>_spec.md`
  - `research_areas/specs/_archive/`

Legacy rule:

- older combined files may remain where they are
- the board must mark them as `legacy_combined`
- if a legacy work item is reopened for real implementation work, split it or explicitly retire it

Not recommended:

- keeping `HARDENING_BOARD.md` as the active canonical board
- treating a combined note as “good enough” for new work

## Implementation Sketch

### Canonical Board

Use one board:

- `research_areas/ZTARE_BOARD.md`

Board columns:

- `ID`
- `Status`
- `Workstream`
- `Summary`
- `Seam File`
- `Spec File`
- `Next Action`
- `Verifier`

Board rules:

- only in-flight items belong on the canonical board
- `done` items move to legacy/archive views rather than cluttering the active board
- if an item has not been split yet, both columns should say `legacy_combined:<path>`

### Seam Files

Seam files live under:

- `research_areas/seams/`

Naming:

- `<ID>_<slug>_seam.md`

Purpose:

- raw failure logs
- hypothesis formation
- debate with Codex / Claude / Gemini
- option exploration

Seam files are intentionally looser than spec files, but they still have a minimum required floor.

**Required header block** (the first content line after the `# <title>` H1 and any `> **Up:**` breadcrumb; machine-checkable; the single source for `seam_id` / `track` / `last_updated`):

```md
> **Seam metadata** · `seam_id:` GP-NNN · `track:` <apparatus|engine|governance|protocol|mission|substrates|...> · `status:` <status or `unrecorded`> · `last_updated:` YYYY-MM-DD
```

`last_updated` is the date the seam file last changed in fact, not a freshness signal hand-entered by the author. While the repo is uncommitted it is the filesystem modification date; once committed it is the last-commit date. `status` mirrors the seam's `## Status` section and is never inferred when absent (use `unrecorded`). `seam_id` and `track` are derived from the filename and folder. The one-time stamp of historical seams is recorded under Migration Rule below.

**Required sections in every seam**

- `## Status`
- `## ID`
- `## Eigenquestion`
- `## Problem Statement`
- `## Debate Log`

**Required once the seam has bounded scope**

- `## Scope`

**Required before a downstream spec or implementation packet opens**

- `## Recommendation`

**Optional until needed**

- `## Option Analysis`
- `## Open Questions`

Seam status lines should use full timestamps whenever the seam is opened, materially updated, converged, paused, or closed.

Debate turns must use this heading format:

```md
### Turn N — <Agent> (<YYYY-MM-DD HH:MM:SS EST>) — <one-line summary>
```

Timestamp rules:

- Always use EST as the timezone label, regardless of daylight saving
- Claude-authored turns must run `date '+%Y-%m-%d %H:%M:%S'` to get the actual system time rather than fabricating a timestamp — fabricated timestamps will not match other turns in the same session

Closed seams stay in place with `Closed <timestamp>` status unless visibility-promotion or supersession rules require a move.

Seam/spec boundary:

| In seam | In spec |
|---|---|
| Eigenquestion | Decision (one paragraph) |
| Problem Statement | Problem |
| Raw option analysis and debate | Options with Pros/Cons/Verdict |
| Turn-by-turn debate log | No Debate Log |
| Open questions during investigation | Open Questions after convergence |
| Recommendation that states the converged direction | Implementation Sketch / execution blueprint |

### Spec Files

Spec files live under:

- `research_areas/specs/active/`
- `research_areas/specs/_archive/`

Naming:

- `<ID>_<slug>_spec.md`

Spec files are clean blueprints, not debate dumps.

Required top block:

```md
# <Spec Title>

## Status

<status>

## Seam

<path to the seam file that preceded and motivated this spec>

## Scope

- ...

## Decision

<one-paragraph decision>
```

Required sections after the top block:

```md
## Problem
## Why It Matters
## Constraints
## Options
## Recommendation
## Implementation Sketch
## Open Questions
```

Unlike the previous combined format, **spec files no longer carry a Debate Log**. That belongs in the seam file.

### Status Vocabulary

Use one of:

- `Active`
- `Closed YYYY-MM-DD`
- `Superseded by <path>`
- `Paused — <reason>`

If status is not `Active`, add:

- `## Closure`

with:

- What shipped
- Where it lives
- What was archived
- What was deferred

### Migration Rule

This is a forward standard.

- new work should use board + seam + spec
- old combined files do not need immediate migration
- if a legacy item is reopened, the board must explicitly show whether it is still `legacy_combined`
- the header block is retroactive: historical seams already carry it. `last_updated` is the date the file last changed and is preserved across re-stamping (it advances only on a real edit). Section-level floors (Eigenquestion / Problem Statement / Debate Log) stay forward-only / on-reopen.

## Open Questions

- should older kernel combined notes be split only when reopened, or should high-value active ones be migrated proactively?
- should the canonical board eventually gain an `Owner` column?
- should distribution-track items use the same ID space or a parallel prefix?

## Debate Log

This document is itself a legacy combined governance note because it defines the transition.

### Turn 1 — Codex

The repo had drifted into a mixed state where some seams lived only in the board, some only in private notes, and some in combined spec-plus-debate files. The fix is to separate index, investigation, and blueprint.

### Turn 2 — Codex

Recommendation stabilized on a three-artifact ontology:

- `ZTARE_BOARD.md` as the index
- seam files for messy investigation
- spec files for clean blueprints

Legacy combined notes remain tolerable only as an explicitly marked migration state.
