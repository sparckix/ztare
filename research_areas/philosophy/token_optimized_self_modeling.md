# Token-Optimized Self-Modeling

**Status:** public / central — methodological primitive
**Date:** 2026-04-19
**Philosophical parent:** Compress, always compress (Leg 2)
**Operational counterpart:** `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md` — first instance
**Provenance:** Principal inception during [GP-100](../seams/engine/mutator/GP-100_epistemic_decoupling_seam.md) session. The agent made a partial-view mistake on a 4100-line file because it read snippets instead of understanding the pipeline ordering. The principal inverted the fix: instead of "read more code," the instruction was "compress your own understanding into a reusable artifact optimized for your consumption, not mine."

---

## The Primitive

An AI agent editing a codebase it cannot hold in context is analogous to a scientist observing a system through a narrow instrument window. The agent reads snippets. Snippets create partial views. Partial views cause mistakes that look correct locally but violate global invariants the agent never read.

The standard fix is documentation — but documentation is optimized for human readers. Human documentation explains *why* things exist, uses narrative structure, buries ordering contracts inside prose, and assumes the reader can hold the whole document in working memory and cross-reference.

**Token-optimized self-modeling** is the agent building a compressed representation of its own operational substrate, optimized for its own consumption characteristics:

1. **Structured over narrative.** Dependency graphs, precondition/postcondition contracts, lookup tables — not explanatory prose. The agent doesn't need to understand *why* a pipeline exists; it needs to know what breaks if it changes step 3 without updating step 5.

2. **Traversable over readable.** The map should be queryable: "I want to change X" → "you must read lines Y-Z and preserve invariant K." Human docs are read linearly. Agent maps are indexed.

3. **Assertion-shaped over explanation-shaped.** Invariants stated as checkable assertions (`python_code != None BEFORE fit_parameters() call`) are more useful than paragraphs explaining why the pipeline has this order.

4. **Line-anchored with drift tolerance.** Line numbers are approximate pointers, not stable addresses. The map acknowledges drift ("lines ~2900-3053") so the agent greps to confirm rather than blindly trusting a stale number.

---

## When to Apply

Trigger: an agent made a mistake because it didn't read enough of a file. If the mistake class is "locally correct edit that violates a global invariant," the file needs a self-model.

Criteria for a file to qualify:
- Exceeds ~2000 lines (beyond comfortable single-read)
- Has ordering contracts between sections (step A's output feeds step B's input)
- Gets edited by agents who rotate between sessions (no persistent memory of prior reads)
- Has multiple code paths gated by configuration flags (each flag creates a branch the agent might not explore)

The self-model is NOT documentation. It is a *pre-computed structural cache* that substitutes for runtime exploration. The distinction matters: documentation answers "what does this do?" The self-model answers "what breaks if I touch this?"

---

## The Mungerian Derivation

This primitive follows from compress-always-compress applied reflexively:

1. **Compress the data** — ZTARE compresses evidence into asymptotic survival tests (Leg 2)
2. **Compress the search** — Component D compresses topology search via AST composition
3. **Compress the agent's cognition** — Token-optimized self-modeling compresses the agent's relationship to its own codebase

Step 3 is the reflexive application. The agent is itself a system with limited observation windows (context size), costly exploration (reading files burns tokens and attention), and failure modes caused by partial information. Compress-always-compress says: don't just compress the data the agent works on; compress the agent's own cognitive substrate.

The inversion test (Leg 1): what would make this self-model harmful? If it becomes stale and the agent trusts it over the actual code. Defense: the map states line numbers as approximate, includes a "drift over time" warning, and the agent is instructed to grep-verify before acting on any specific line reference.

---

## What the Optimal Format Looks Like

See [GP-101](../seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md) seam for the open debate on agent-native format. The v1 map was 70% optimized — still too much prose, too human-readable. The eigenquestion: what representation minimizes agent error rate per token of self-model consumed?

Candidates under debate: dependency graphs (YAML), precondition/postcondition contracts, edit-intent lookup tables, assertion-based invariant lists, hybrid formats.
