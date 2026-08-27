# H117 — Generative skill edges in factored search

**Hypothesis ID:**
`H-GPSA-GENERATIVE-SKILL-EDGE-SEARCH-20260806-117`

**Eigenquestion:** does placing a carrier-lowerable remembered word inside the
factored search graph, rather than compressing a primitive plan afterward,
increase reachable planning horizon at fixed deliberation depth while
preserving primitive execution cost, environment time, and intermediate goal
checks?

**Candidate mechanism:** search over a mixed move set. A primitive move
contains one operation. A learned move contains an evidence-bound operation
word. Both consume one deliberation edge; the learned move rolls through the
accepted carrier one primitive at a time, advances the environment clock at
each step, and returns the flattened primitive program for external execution.
Primitive cost remains the number of operations. An undefined or inadmissible
intermediate state refuses the entire learned edge.

**Discriminating test:** on a deterministic chain whose goal lies beyond the
primitive-only decision-depth bound, compare the unchanged primitive search
with a mixed search containing one three-operation learned move. Require the
mixed search to find the goal, return the exact primitive action sequence, and
report fewer deliberation edges without reducing primitive execution cost.
Separate fixtures place a goal inside the learned word and make its carrier
undefined mid-word.

**Success criterion:** primitive-only search remains depth-bounded; mixed
search reaches the same externally executable goal within the frozen
deliberation bound; intermediate goals stop at the exact primitive prefix;
undefined learned edges do not enter the frontier; existing factored-search
tests remain unchanged.

**Kill conditions:** a learned move receives free primitive execution cost,
skips an intermediate goal or feasibility check, changes the returned action
vocabulary, treats a predictive rollout as external task settlement, or
changes primitive-only behavior.

**Claim boundary:** this tests computational chunking in the search kernel.
It does not establish ARC task benefit, transfer to another task, autonomous
skill generation, external task credit, catalytic acquisition, or novelty.

