# Token-Optimized Self-Modeling

**Status:** public / central — methodological primitive
**Philosophical parent:** the compression leg of [The Three Legs of ZTARE](three_legs_of_ztare.md), applied reflexively
**Operational counterpart:** the autoresearch-loop architectural map (private working artifact, `docs/internal/architectural_maps/`) — first instance
**Provenance:** principal inception during a [GP-100](../seams/engine/mutator/GP-100_epistemic_decoupling_seam.md) session, after an agent made a partial-view mistake on a 4,100-line file because it read snippets and missed the pipeline ordering. The fix was inverted: the instruction became "compress your own understanding into a reusable artifact optimized for your consumption, not mine."

## The primitive

An AI agent editing a codebase it cannot hold in context is a scientist observing a system through a narrow instrument window. Reading snippets gives it partial views, and a partial view produces edits that look correct locally while violating global invariants the agent never read.

Documentation is the standard fix, and it fails here because documentation is optimized for human readers: it explains why things exist, uses narrative structure, buries ordering contracts inside prose, and assumes a reader who can hold the whole document in working memory.

Token-optimized self-modeling has the agent build a compressed representation of its own operational substrate, shaped by its own consumption characteristics:

1. Structured. Dependency graphs, precondition and postcondition contracts, lookup tables. The agent has no use for a pipeline's origin story; it needs to know what breaks if it changes step 3 without updating step 5.
2. Traversable. An agent map is an index to be queried: "I want to change X" resolves to "read lines Y–Z and preserve invariant K."
3. Assertion-shaped. An invariant stated as a checkable assertion (`python_code != None` before the `fit_parameters()` call) beats a paragraph explaining why the pipeline has this order.
4. Line-anchored, drift-tolerant. Line numbers are approximate pointers. A map entry reads "lines ~2900–3053" so the agent greps to confirm before trusting a possibly stale address.

## When to apply

Build one after a mistake caused by under-reading: a locally correct edit that violated a global invariant. A file qualifies for a self-model when it

- exceeds roughly 2,000 lines, beyond a comfortable single read;
- has ordering contracts between sections, where step A's output feeds step B's input;
- gets edited by agents that rotate between sessions with no persistent memory of prior reads;
- branches on configuration flags, each one a code path the agent might never explore.

A self-model is a pre-computed structural cache that substitutes for runtime exploration. Where documentation answers "what does this do?", a self-model answers "what breaks if I touch this?"

## Derivation from the compression leg

Token-optimized self-modeling falls out of applying compression reflexively, three times over:

1. Compress the evidence. ZTARE compresses data into claims that must survive outside their fit window.
2. Compress the search. The grammar's composition modes collapse a topology search into a small set of admissible moves over existing primitives.
3. Compress the agent's cognition. The agent's relationship to its own codebase gets the same treatment as the data it works on.

Step 3 is the reflexive one. An agent, too, is a system with a limited observation window (context size), costly exploration (reading burns tokens and attention), and failure modes caused by partial information, so the compression discipline applies to it as much as to any substrate.

Leg 1's inversion test applies here as well: what would make a self-model harmful? A stale map trusted over the actual code would. So the format carries its own defense: approximate line numbers, an explicit drift warning, and a standing instruction to grep-verify before acting on any specific reference.

## Open question: the optimal format

Live debate on the agent-native format sits in the [GP-101](../seams/apparatus/instrumentation/GP-101_agent_native_self_model_format_seam.md) seam. Our first map was still too human-readable, roughly 70% of the way to its own standard. One question decides the format: which representation minimizes agent error rate per token of self-model consumed? Candidates include dependency graphs in YAML, precondition/postcondition contracts, edit-intent lookup tables, assertion-based invariant lists, and hybrids.
