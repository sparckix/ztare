# GP-027 Evidence Compile Reuse / Frugal Compiler Seam

## Problem Snapshot

ZTARE already has one reuse lane:

- `update_workspace` hashes raw files and reuses unchanged source notes
- `compile_evidence --mode workspace` then renders from the saved snapshot without another LLM call

But many live operator workflows still use:

- `compile_evidence --mode raw`

because it is simpler and gets to a runnable `evidence.txt` faster.

That raw path currently recompiles from scratch every time, even when:

- the selected source files are unchanged
- the source contents are unchanged
- the truncation budgets are unchanged
- the model and prompt contract are unchanged

For a frugal operator, that is wasteful.

## Current State

The actual architecture is split:

- `update_workspace.py`
  - already stores source hashes in `workspace/source_index.json`
  - already reuses unchanged source notes
- `compile_evidence.py --mode workspace`
  - does not call the LLM
  - just renders from `workspace_snapshot.json`
- `compile_evidence.py --mode raw`
  - always rebuilds the prompt
  - always calls the LLM again
  - has no cache key or reuse artifact

So the system already has reuse in one lane, but not in the most operator-convenient lane.

## Debate Log

### Turn 1 — Operator need

The operator surfaced the practical problem clearly:

- given frugality, can we avoid recompiling evidence repeatedly when the content has not changed?

This is not the broader librarian/workspace question.
It is a narrower compiler-cost question.

### Turn 2 — Misfire clarification

`GP-025` is a real seam, but it is a different one:

- `GP-025` asks when manual thesis patching becomes self-defeating versus mutation
- this seam asks when repeated evidence compilation becomes self-defeating versus frugal reuse

They are orthogonal.

### Turn 3 — Existing workaround

There is already a partial answer:

1. run `update_workspace`
2. let unchanged source notes be reused by hash
3. use `compile_evidence --mode workspace`

That avoids repeated raw compilation costs.

But it is not a full answer because:

- operators often intentionally skip workspace for speed
- the workspace path is a different workflow with different artifacts
- the raw compile path still has no memoization of its own

### Turn 4 — Option space

Three real options exist.

1. **Workflow-Only Discipline**
   - declare that frugal operators should use:
     - `update_workspace`
     - then `compile_evidence --mode workspace`
   - no code changes

2. **Raw Compile Cache**
   - add a cache for `compile_evidence --mode raw`
   - key it on:
     - selected source paths
     - source hashes
     - source types
     - truncation budgets
     - prompt template hash
     - model family / model id
   - if unchanged, reuse the last compiled packet/text instead of calling the LLM

3. **Full Incremental Compiler**
   - refactor raw compilation into a source-note + merge pipeline identical to workspace
   - make raw mode mostly a thin alias over workspace generation

### Turn 5 — Current conclusion

Option 2 is the right first slice.

Why:

- Option 1 is real but too operator-fragile
- Option 3 is architecturally elegant but larger than needed
- Option 2 preserves the current simple raw workflow while removing obviously wasteful repeat spend

The likely shape is:

- compute a deterministic raw-compile cache key
- persist cache metadata under `workspace/`
- on cache hit:
  - reuse the previous compiled packet/text/provenance
  - mark the manifest as a cache hit
- on cache miss:
  - run the current raw compile as normal
  - write the new cache metadata

That gives frugal reuse without collapsing into hidden, untraceable state.

### Turn 6 — Claude (2026-04-10) — Options confirmed, one spec gap, three open questions answered

Options evaluation confirms Turn 5's conclusion. Additions:

**Option A** is worth keeping as a documented fallback even though it's insufficient as a primary fix. Some operators will encounter the problem in a context where they already have workspace mode available; a one-line doc pointer is zero cost and handles that case.

**Option B shape is correct. One critical gap in the spec as written.** Looking at `compile_evidence.py:compile_from_raw` (line 646–648): `compiler_date = time.strftime("%B %d, %Y")` is injected directly into `build_prompt()`, making the rendered prompt a dynamic string with a live date embedded in it. The spec says "prompt template hash" but hashing the rendered prompt will produce a different key on every new calendar day, guaranteeing daily cache misses regardless of whether inputs changed. The fix: hash the **template file** (`prompts/compile_evidence.md`) separately, and hash **source content** separately. Exclude `compiler_date` from the cache key entirely — it belongs only in the manifest metadata of the stored artifact, not the key.

The corrected cache key inputs are: `hash(sorted([{path, hash, source_type, chars_used, truncated} for s in sources]) + template_file_hash + model_family + model_id + max_files + max_chars_per_file + max_total_chars)`. No date, no run ID, no timestamp anywhere in the key.

**Three open questions in the spec — resolved:**

1. *Single-entry or small keyed history?* Single-entry for the first slice. `compiled_evidence_cache_index.json` maps one key → one entry; a new key replaces the old one. Git history of the manifest file provides provenance if needed. History is complexity without payback at current scale.

2. *Should compile date be removed from the semantic cache key?* Yes, and it is non-negotiable given the `compiler_date`-in-prompt issue above. Store it in manifest metadata only.

3. *Should `--force-recompile` exist?* Yes. One line: skip the cache lookup if the flag is set, still write the new cache entry. Useful after intentional prompt template changes that didn't bump the template hash (e.g., mid-day edit), or for operator sanity checks.

**Spec update needed before Codex handoff.** Add a "Cache Key Construction" section to the spec that states explicitly: *do not include `compiler_date` in the cache key — hash the template file, not the rendered prompt.* Everything else in the spec is implementable as written.
