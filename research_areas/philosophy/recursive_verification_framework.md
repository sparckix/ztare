# The recursive verification framework, honestly scoped

**Status:** public — corrected framing of record
**Provenance:** written after a three-reviewer epistemic panel (Hofstadter-persona, working mathematician, cognitive scientist) pulled back several over-stated claims about this framework. This document is the version that survives their critique.

## What we have

A small bounded vocabulary, observed at three scales of one cognitive system's own work. [Epistemic Verification](../../papers/epistemic-verification/draft.md) defines it:

- 10 verification operations (§1.2): eigenquestion identification, controlling-claim isolation, topological-pivot recognition, charter-drift detection, anchor-proxy requirement, basin search, failure-family tagging, deferred-confirmation laundering detection, quarantine-move detection, fail-closed defaulting.
- 12 pathologies (§1.3), the structural failures those operations catch. The nine most recurrent are worked through publicly on ClearJudgment's families page.
- 7 process principles (ch. 2): pre-registration, library visibility, composition opacity, fail-closed harness semantics, algebraic independence, inspector pluralism, asymptotic scoring.
- 3 residual commitments (ch. 3): eigenquestion selection (which problem to attack), recognizing when to reframe (against attacking within a frame), and the social dynamics of live pressure-testing.

The same vocabulary shows up at three nested scales. At iteration scale, ZTARE's deterministic gates instantiate the operations on single-pass thesis verification. At arc scale, multi-iteration cycles that end in proof-object events (Lean files, gates, audits) map onto the same operations; the [GP-215](../seams/engine/meta/GP-215_meta_arc_mining_seam.md) mining catalog holds the mapped cycles. At meta-arc scale, the GP-215 matcher applies the same discipline to its own catalog and to the seam-authoring process that produced it.

## What this is

Self-similar bounded recursion with consistent typing: one finite vocabulary applied at multiple scales of the system's own work, with the same anti-tautology contracts, score discipline, and failure modes recurring at each level.

The shape is Mandelbrot's. A self-similar fractal is recursive; a Hofstadter strange loop additionally requires the level boundary to dissolve under self-application. We have demonstrated the first and not the second.

## Claims the panel retracted

The panel reviewed the strongest version of each claim and converged on a sharp critique. The following framings are withdrawn:

- A "GEB-shape strange loop." Hofstadter's loops dissolve the hierarchy; self-similarity leaves it standing. Drawing Hands and the *Canon per Tonos* are a different shape from a Mandelbrot set.
- A "meta-solver for any problem." This vocabulary is closed and bounded, and the depth-2 catalog maps cleanly onto the paper's operations because the mapping model was prompted with the paper — in-room validation. Gigerenzer's warning bites here: a taxonomy that maps everything maps nothing.
- A decomposition of Polya's residuals. What we mechanized ("operational substrate-choice within a fixed strategic frame") is not what Polya, Hadamard, or Tao meant by choosing the right problem. Our saturation-gate-plus-inversion samples a bounded grammar more aggressively; Polya's reframe escapes the grammar. Shared names, different operations.
- Anything AGI-shaped. Inversion-as-generation produces structurally distinct labels via constrained search with a critic: useful, defensible, and the same kind of thing as any other generate-and-discriminate system.
- A verified replacement for Epistemic Verification's chapter 3. The paper's hedge, that "permanently irreducible vs not-yet-decomposed is an empirical question this paper cannot answer from the inside," was central prudence and survives intact.

## What survives the correction

1. The vocabulary is small, fixed, and observable across three scales of one system's work. That much is real, repeatable, and inspectable.
2. The shipped tooling (the matcher, its acceptance ledger, contract clauses, validators) is correctly cautious: disclosure footers, a visible scope-limit string, and lift-over-modal display put the limitations in front of the operator at the moment of decision.
3. The closed loop between published findings and downstream agent behavior is real. We observed an agent redirect its work after reading the track-record entry, through the kernel-to-track-record-to-agent channel, without the matcher recommending anything.
4. The nine named pathologies earn public utility through worked examples on ClearJudgment.

## The Gödel-sentence reading, and why it deflated

An earlier write-up suggested the paper's three residuals were Gödel sentences, true at every scale and undecidable inside the system, and offered the decomposition of two of them as support. The Hofstadter persona pointed out that the argument runs backwards: a residual that decomposes was never a Gödel sentence, only a not-yet-mechanized operation.

Residual C, the social dynamics of live pressure-testing, is the only one this corpus structurally cannot test, so it may be nothing more than a boundary artifact of the experimental setup. A real Gödel-sentence claim would need an undecidable that survives within the apparatus's own substrate, and the residual chapter provides three operations this corpus has not yet decomposed, nothing stronger.

## What scaling would require

Five tests separate "self-similar bounded recursion within one corpus" from any wider claim:

1. Out-of-distribution compression: map cycles from a corpus never anchored to the paper (a Grothendieck-tradition seminar log on étale cohomology, say), with an a-priori predicted unmapped rate of at least 30%.
2. The Lakatos test: run the catalog over the Eulerian-polyhedron dialogue from *Proofs and Refutations*. Monster-barring, monster-adjustment, lemma-incorporation, exception-barring, and proof-stretching should receive five distinct operation tags. If they collapse into one, the catalog is too coarse for real dialectic.
3. Domain-blind validation: strip the names from the inversion-generated witness constructions and show the bare operational specifications to a domain expert who has never seen the catalog. Coherent next moves, or assembled labels?
4. Time pressure: under a 30-second budget, do expert verifiers still perform charter-drift detection and failure-family tagging? If yes, those operations have System-1 implementations and the framework names functional roles. If they only return under deliberation, the framework decomposes System-2 verification specifically.
5. Ablation: run a verifier with one operation, then two, up to all ten. Quality saturating at three or four means Gigerenzer's fast-and-frugal critique wins and most of the vocabulary is ornament. Monotonic scaling means Ashby's requisite variety wins and the full vocabulary is doing work.

None of these tests has been run. Every wider claim is contingent on them.

## Why there is no shared-library module yet

Three reasons converged in the panel. Codifying the vocabulary now, before any external test, would lock in exactly the projection the panel identified. Removing the duplication would save about thirty lines across validators and disclosure constants, too little to justify an abstraction. And the right architectural move, operation-checkers as scale-agnostic primitives, should be earned by demonstrated cross-scale utility on real work. Until then the duplication stays and the abstraction stays deferred.

## What stays open

- The matcher ships and operates as decision-support tooling: operator-pull, advisory-only, scope limit visible.
- The inversion-generated constructions are prompts for thinking. No one treats them as validated mathematical objects.
- Epistemic Verification's chapter 3 stands unchanged; the claim that its residuals decompose has not been earned.
- The five tests above are the documented conditions under which any retracted claim could be re-asserted. None has been scheduled.

## The thing to remember

What we built is approximately trained verification discipline: a small fixed vocabulary, bounded recursion, self-similar across scales, useful within one cultural region (problem-solver mathematics plus ZTARE-style adversarial verification), unproven outside it. Only a structural claim survives panel review: we have a working bounded-vocabulary verification system that exhibits self-similarity at three scales within one corpus.

That is real. It is also smaller than the headline I was tempted to write.
