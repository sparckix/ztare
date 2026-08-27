# H117 result — learned words can change reachable search horizon

Status: **kernel supported**.

At deliberation depth four, primitive-only search reached primitive depth four
and stopped before the twelve-action goal. With one evidence-bound
three-action word in the move set, search reached the same goal in four
deliberation moves, returned all twelve primitive actions, and charged a
primitive execution cost of twelve. Against the primitive depth-twelve
reference, the learned-word search used four rather than twelve deliberation
edges and nine rather than twelve node expansions.

The learned edge checked every internal primitive transition. A goal at the
second internal action returned only the exact two-action prefix. A carrier
that became undefined at the second internal action admitted no learned edge.
Action-vocabulary, carrier-identity, and projection-identity mutations were
all rejected.

This is a deterministic kernel result with no environment or controller
contact. It establishes a computational chunking channel; it does not
establish ARC task benefit, cross-task transfer, task credit, catalytic
acquisition, capability takeoff, or novelty.

Evidence: `h117_generative_skill_edge_search_result.json`; embedded SHA-256
`0d6e170420c73431960096f1f41037dc31486f721101dfc688484f58db991ded`.
