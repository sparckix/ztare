# Option transport across predictive refinement result

Date: 2026-07-26

Status: confirmed

Adding the reservoir coordinate refined prior source nodes into context
children. Digest-only option initiation lookup consequently marked all six
learned programs unsupported.

Boundary reachability now accepts an explicit source-lineage morphism. Each
current child retains its own digest and the digest of its pre-refinement
parent. Option reindexing pulls the prior initiation set back over that
morphism, executes each child only on its witnessed edges, and records failed
children rather than borrowing sibling transitions.

The two-child fixture yields two context variants when both child paths exist
and partial support when one child edge is absent, with unchanged option
identity. On the current ARC graph:

- three repeated-operation options are context-gated with three variants and
  both prior initiation lineages resolved;
- three mixed-operation options are partially supported because one prior
  lineage or refined child lacks the second operation;
- no option remains unsupported through `initiation_source_absent`.

The result preserves learned program identity across predictive refinement while
keeping missing child images explicit. It does not infer any unobserved option
edge.
