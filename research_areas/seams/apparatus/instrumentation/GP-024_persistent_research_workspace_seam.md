# GP-024 Persistent Research Workspace / Librarian Seam

> **Seam metadata** · `seam_id:` GP-024 · `track:` apparatus · `status:` closed · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Problem Snapshot

ZTARE now has several durable research objects, but they are still split across partially connected lanes:

- `raw/` source notes
- `evidence.txt`
- `workspace/latest_evidence_gaps.json`
- `workspace/derived_constraints.json`
- project-local reports and debate logs

That is enough for an artisanal operator workflow, but not yet enough for a future librarian-style agent that can:

- read the accumulated workspace state
- propose or fetch the next best sources
- maintain a persistent, compounding research layer between raw sources and live reasoning

The current system has the pieces of that workspace, but not the unified project type or artifact contract.

## Current State

Important recent progress:

- GP-017 created typed evidence gaps
- GP-011 created typed derived constraints
- project charters now type forecast objects
- champion/latest artifacts now separate stable baselines from fresh candidates

So the seam is no longer “should ZTARE preserve intermediate research state?”

It is:

- how should these intermediate objects be unified into a persistent research workspace?
- which objects are source-of-truth versus compiled synthesis?
- what should a future librarian agent read, write, and never mutate?

## Debate Log

### Turn 1 — Operator need

The operator surfaced the real downstream need:

- constraints should eventually inform upstream research
- a future agent should be able to use those constraints to search for missing sources
- this feels close to the “persistent wiki / compiled knowledge base” pattern rather than one-shot RAG

### Turn 2 — Independent synthesis

The right framing is not generic “RAG improvement.”

It is a layered persistent research workspace:

- raw sources
- compiled evidence
- derived constraints
- evidence gaps
- project schema / charter

That is structurally similar to Karpathy’s “LLM Wiki” pattern, but narrower and more falsification-oriented.

### Turn 3 — Boundary clarification

The key distinction is:

- GP-011 is **not** the librarian
- GP-011 is the typed intermediate layer the librarian would later consume

Likewise:

- evidence gaps are not raw sources
- derived constraints are not evidence
- reports are not source-of-truth memory

The librarian seam exists to unify these into a project workspace contract.

### Turn 4 — Why this matters now

The current `%` forecasting project already shows the need.

The evaluator can now emit:

- missing evidence classes
- repeated structural constraints

but there is still no agentic layer that says:

- here is the next source to ingest
- here is which page in the workspace should be revised
- here is which unresolved claim is now likely stale or contradicted

That is exactly the transition from artisanal research memory to persistent compiled workspace.

### Turn 5 — Current conclusion

This should become a real seam on the roadmap, but not the very next kernel build.

The enabling pieces are being assembled now:

- evidence gaps
- derived constraints
- project typing
- artifact clarity

The librarian/workspace project type is the next natural synthesis of those pieces, not a replacement for them.

