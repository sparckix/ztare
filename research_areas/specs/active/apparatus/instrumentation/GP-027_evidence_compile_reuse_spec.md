# GP-027 Evidence Compile Reuse Spec

## Status

Draft

## Scope

- avoid repeated `compile_evidence --mode raw` LLM calls when the effective input has not changed
- preserve auditable provenance for cache hits and cache misses
- keep the first slice narrow and deterministic

Does not cover:

- replacing the workspace pipeline
- cross-project compile caching
- semantic equivalence detection beyond exact input identity
- caching partial runs after provider failures

## Decision

Add a deterministic cache layer to `compile_evidence --mode raw`.

If the effective raw compile input is unchanged, reuse the last compiled packet/text instead of calling the LLM again.

## Problem

`compile_evidence --mode raw` currently always recompiles.

That is wasteful when:

- the same selected files are used
- the same file contents are used
- the same compile budgets are used
- the same prompt contract is used
- the same model family is used

The frugal operator should not have to choose between:

- paying again for unchanged work
- or switching into a heavier workspace workflow just to get reuse

## Why It Matters

If this is left unchanged:

- repeated thesis experiments keep re-paying for unchanged evidence compile work
- operators are pushed into manual reuse habits instead of explicit system support
- the simple raw path remains economically worse than it needs to be

If fixed:

- repeated compile costs drop for unchanged source packs
- provenance remains explicit
- the simple raw workflow becomes safer for iterative project work

## Constraints

- cache hits must be exact-input reuse, not fuzzy reuse
- cache state must be inspectable on disk
- cache hits must not silently hide changed inputs
- first slice should avoid broad architectural refactors

## Options

### Option A — Document Workspace-Only Reuse

**Description**

Tell operators to use `update_workspace` plus `compile_evidence --mode workspace` whenever they want reuse.

**Pros**

- no code changes
- uses existing hash-based source-note reuse

**Cons**

- does not fix the raw path
- changes operator workflow
- still requires a heavier pipeline than some users want

**Verdict**

Insufficient by itself.

### Option B — Exact Raw Compile Cache

**Description**

Persist a cache record for raw compile inputs and outputs. On exact-key match, reuse the prior compiled packet/text/provenance.

**Pros**

- directly solves the operator problem
- preserves current workflow
- small, auditable first slice

**Cons**

- adds another artifact family
- requires careful cache-key definition

**Verdict**

Recommended.

### Option C — Collapse Raw Mode Into Workspace Pipeline

**Description**

Refactor raw compile to internally build or reuse workspace notes/snapshots, making raw mode mostly an alias.

**Pros**

- architectural unification
- one reuse story

**Cons**

- much larger change
- changes semantics of the current raw path

**Verdict**

Later possibility, not first slice.

## Recommendation

Implement Option B now.

### Cache key inputs

The raw-compile cache key should include:

- mode: `raw`
- project path or project name
- model family and resolved model id
- prompt template hash for `compile_evidence.md`
- `max_files`
- `max_chars_per_file`
- `max_total_chars`
- ordered selected source list, with for each source:
  - relative path
  - source type
  - full source hash
  - `chars_used`
  - `truncated`

This makes the cache key reflect the actual effective input to the LLM call.

### Cache artifacts

Persist under `workspace/`:

- `compiled_evidence_cache_index.json`
- `latest_compile_cache_hit.json` on hit

The cache index should map cache keys to:

- compiled packet path
- compiled text path
- provenance/manifest path
- generated timestamp
- model family / model id

### Cache behavior

On raw compile:

1. collect sources exactly as today
2. compute cache key
3. if key exists and artifacts still exist:
   - reuse them
   - write new latest outputs from cached payload
   - mark manifest with:
     - `cache_hit: true`
     - `cache_key`
     - `reused_from`
4. otherwise:
   - call the LLM
   - write outputs as today
   - register the cache entry

## Implementation Sketch

### Step 1 — Add raw compile cache key helper

- new helper module or internal functions in `compile_evidence.py`
- deterministic hash over effective inputs

### Step 2 — Add workspace cache artifacts

- `workspace/compiled_evidence_cache_index.json`
- `workspace/latest_compile_cache_hit.json`

### Step 3 — Wire cache lookup into `compile_from_raw`

- lookup before LLM call
- on hit, skip `LLMClient.call()`
- on miss, run existing path

### Step 4 — Surface reuse in terminal and manifest

- print whether compile was a cache hit
- include cache metadata in manifest/provenance

### Step 5 — Add regression coverage

- same inputs twice -> second run is cache hit
- change one source -> cache miss
- change budget -> cache miss
- change model family -> cache miss
- delete cached artifact -> fail closed to miss and rebuild

## Open Questions

- should cache entries be single-entry latest-only, or a small keyed history?
- should the compile date be removed from the semantic cache key and only live in metadata?
- should `--force-recompile` exist as an explicit bypass flag?
