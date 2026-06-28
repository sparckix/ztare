# Two cultures of mathematical writing: a corpus study of research-move vocabularies

# Introduction

To verify a claim is to ask whether it is adequately supported. But
before any claim exists, a research process has to pick its next move:
reformulate the problem, try a special case, draw an analogy, look for a
falsifier, introduce an auxiliary object, decompose, mark an evidence
boundary, or stop a branch.

Two curated mathematical styles turn out to favor different research-move
vocabularies, and the difference survives cross-corpus scoring against a
same-culture negative control. Gowers's theory-builder/problem-solver
distinction thus gets an empirical, operational form, without forcing all
of mathematics into two types.

We then widen the binary into a structural vocabulary of research moves.
Theory-building and problem-solving mark a real but incomplete split:
they stress different bands inside a larger space of reformulation,
abstraction, decomposition, local-to-global assembly, invariance,
translation, approximation, and constraint propagation.

This vocabulary earns its keep at one specific point in a research
system. Passive labels and long menus do little on their own, typed
evidence fields, residual-to-check edges, rejected nearest confusers, and
executable action schemas do the work. Research-move language turns
operational only when it changes what the system checks, blocks, turns
into an artifact, or executes next.

Generation, then, is a sequence of research moves, judged by whether the
system picked, checked, and executed the right one. A generic evaluation
vocabulary can miss domain-specific reasoning that typed intermediate
representations recover.

# Evidence base, reproducibility, and method

Our unit of analysis is the research move: a bounded step that changes a
problem representation, admissible object, proof strategy, evidence
standard, decomposition, validation frame, or next action. A vocabulary
covers a move when a frozen operation fits it mechanistically under our
scoring rubric.

Coverage is only a diagnostic. High coverage can index transfer, but it
can just as easily signal force-fitting, so we optimize nothing against
it directly. Every coverage number travels with cross-corpus scoring,
negative controls, adversarial raters, decoys, wrong-card controls,
source-cluster blocking, and downstream consequence checks. Raw fit to a
vocabulary is weak evidence, fit that survives the wrong-card, decoy,
source-only, and downstream-consequence checks is what carries weight.

The argument draws on several tiers of evidence, each with a different role. Saved-output corpus results carry the main quantitative claims: the two-cultures split, the negative control, structural-vocabulary coverage, and out-of-distribution transfer. Cross-family and multi-rater audits supply the reliability checks, especially for the PDE correction and the catalog-confusion analysis. Replay and synthetic-workflow experiments give the mechanism evidence for evidence carriers, residual-to-check edges, boundary cards, and action schemas. Human and production-trace validation is the next layer, for expert use and prospective deployment.

Durable records back the core percentages: stored move lists, frozen
vocabularies, scoring files, JSON verdicts, and reproducer scripts. Later
workflow experiments serve as mechanism evidence, showing which carrier
changes downstream behavior under controlled conditions. The
reproducibility packet bundles the saved-output verifiers for the
headline corpus claims, the PDE joint-vocabulary scoring artifacts, the
meta-language score files, and the compact workflow replay scorers. Each
main quantitative claim rests on a recomputable artifact, so the record
stands on its own without the underlying model transcripts.

# A corpus-level two-cultures result

Theory-building arcs make up our first corpus: Wiles, Grothendieck,
Lurie, Scholze, Riemann, Newton, Einstein, and Polya/Hadamard. The
theory-builder vocabulary we mine from them includes foundational object
redefinition, cross-domain unification, parameter-space internalization,
vocabulary lifting, strategic specialization, diagonal self-application,
and concept revision .

We collect problem-solving arcs in a sister corpus: Erdos discrepancy,
Green–Tao, Hales–Jewett Polymath, Szemeredi regularity, Roth, Behrend,
Furstenberg, and Ramsey/Erdos–Szekeres. Its problem-solver vocabulary
emphasizes partitioning, governed iterative refinement, theorem-use
transfer, rank induction, and estimate chaining.

<div id="tab:two-cultures">

| Vocabulary                | Theory-builder corpus | Problem-solver corpus |
|:--------------------------|----------------------:|----------------------:|
| Theory-builder vocabulary |                 58.1% |                 20.7% |
| Problem-solver vocabulary |                 19.1% |                 65.9% |

Cross-distribution coverage for the two mined vocabularies.

</div>

Each vocabulary fits its own corpus far better than the other, by 42.1
percentage points on average, and the advantage runs symmetrically in
both directions. Split one culture at random and the gap drops to 3.0
points, far below the curated two-cultures gap. So two mathematical
styles favor different research-move vocabularies that a random partition
of one style cannot reproduce, and the Gowers distinction picks up an
empirical, operational form. This operationalizes the axis descriptively,
it does not pin it down causally against every corpus-construction factor,
since subfield, era, and selection effects may all feed the gap. The
narrower claim is the one we make: the curated contrast yields a
measurable research-move difference that a same-style random split does
not.

Studies of mathematical practice, proof reading, examples,
collaboration, consensus, subfield prestige, stop short of a
corpus-level operationalization of Gowers's theory-builder/problem-solver
distinction. None of that adjacent work tests directly whether the two
styles differ by cross-coverage of research-move vocabularies, and that
is the test the result above supplies.

# From two cultures to a structural vocabulary

The two-cultures result is only a starting point. A follow-up
eight-subfield analysis covered 1,214 moves across 64 mathematical arcs
and compressed them into six shared-core operations, eight broadly shared
operations, and four peripheral operations, a taxonomy already wider than
the binary.

<div id="tab:structural-vocabulary">

| Tier | Operations |
|:---|:---|
| Shared core | Problem Reformulation and Reduction, Generalization and Abstraction, Decomposition and Recomposition, Local-to-Global Assembly, Canonical Form and Invariance, Cross-Domain Translation. |
| Broadly shared | Iterative Refinement, Recursive Decomposition, Duality and Adversarial Framing, Layered Approximation and Convergence, Extremal Method, Probabilistic and Stochastic Methods, Dimensional and Structural Lifting, Constraint Imposition and Propagation. |
| Peripheral | Characterization by Obstruction, Internalization and Self-Reference, Axiomatization and Foundational Repair, Controlled Universe Extension. |

Layered structural vocabulary from the eight-subfield remine.

</div>

This revision generalizes the original result: theory-builder and
problem-solver mathematics stress different bands inside a larger
structural language. Some moves are shared, others are subfield idioms,
and several seemingly culture-specific moves turn out to be aliases once
the remine widens.

Transfer also reaches past the original mathematical corpus. A business
held-out set reaches 57.9% shared-plus-broad coverage, and four sparse
2026 specialist papers reach 75.2%. We record scope, residuals, and
confusers to bound this portability as measured, keeping the coverage well
short of any claim to universality.

# Methodological warning from the PDE rescore

The PDE rescore carries a methodological lesson for evaluating frontier
agents and research systems: domain-specific reasoning can look absent
whenever an evaluation vocabulary omits the operations that carry it. A
12.5% adversarial score on a post-cutoff PDE paper first looked like a
sharp capability boundary for the structural vocabulary. Auditing it
exposed a different mechanism, the score came from a single vocabulary, a
single adversarial rater, and one hard PDE paper. Rescore against the
joint structural vocabulary plus the PDE estimate-craft vocabulary, and
the same paper draws 95.8–100% coverage of its moves from four raters
across two model families under the covered-vs-none metric. Across the
five-paper corpus, two-family coverage reached 116/118 moves, or 98.3%,
with a 0% decoy match rate. The old 12.5% figure was a single-vocabulary adversarial baseline, what stays open is a fresh blind PDE corpus and an expert audit.

Test frontier agents on domain-specific reasoning using only generic
reasoning categories, and you can manufacture artificial capability
boundaries. The expanded language plus PDE estimate-craft receipts covered
this former stress case under multi-rater, decoy-controlled scoring.
Throughout, we report covered-vs-none coverage and operation-identity
reliability, and keep strict full-only coverage as a calibration-sensitive
secondary metric.

The rescore cuts both ways, and the sharper objection runs the other direction: if the wrong vocabulary drives a fixed artifact to 12.5% and the right one to nearly 100%, coverage is measuring the vocabulary, not the paper. On a single artifact that is true, which is why no claim here rests on one paper's coverage. The weight falls instead on three controls that vocabulary choice cannot satisfy at once. A same-culture negative control blocks easy inflation: a generous vocabulary applied to two papers from the same culture does not reproduce the cross-culture split. Held-out transfer blocks overfitting: coverage holds on papers the vocabulary was never tuned against, including business and 2026 specialist corpora. The 0% decoy-match rate blocks looseness: the vocabulary does not light up on planted moves it should miss. A vocabulary tuned to inflate one paper's score breaks at least one of these three, so the coverage numbers count only where all three hold.

# Carrier selection in agent-facing tests

Knowing the vocabulary is one thing, getting an agent to act on it is another. We supplied research-move vocabulary three ways, as prompt text, as feature prose, and as a broad catalogue, and none of them moved the tested outcomes much.

On an exact-answer benchmark, every prompt arm (baseline, static catalogue, one-primitive, diagnose-then-solve) scored the same 11/26, and a placebo 8/26: no lift from the prompt text. On blind route-choice probes, generic reasoning won 7 of 10 comparisons while each vocabulary-supplied arm won 6 of 10, so the vocabulary changed how the agent explained its choice more than the choice itself. A specialized card for a move beat its schema and swap controls in 0 of 24 cases, routing the choices to execution did not rescue the vocabulary-supplied routes (51 votes to ordinary routes, 47 to schema routes, 28 to vocabulary routes), and a consequence-ranking test gave the card only a 4.25/5 to 4.04/5 edge, ahead of the strongest control in just 2 of 20 source clusters. Supplied this way, the vocabulary is close to inert.

It begins to matter only once the correct move has already been chosen. An action-oriented catalogue merely matched source-only reasoning (6.50/10 each, against 6.00/10 for a descriptive summary), while a correct action card scored 8.875/10 against 4.375/10 for a plausible wrong one. So the open problem is not naming more moves, it is routed selection: picking the right move, rejecting the nearest confuser, and attaching the evidence that makes the choice executable.

# Implications for research-agent evaluation

The experiments point to three design requirements for evaluating
research agents on open-ended scientific or mathematical work.

Final-answer accuracy is too coarse for epistemic generation. A research
agent can fail by picking the wrong object, paying the wrong evidence
debt, over-updating from a narrow receipt, dropping a necessary
falsifier, or pressing on after a branch should have stopped. A single
final-answer score routinely hides such failures.

An evaluation vocabulary has to include the domain operations that carry
the reasoning. In the PDE rescore, a generic structural vocabulary
understated capability the moment estimate-craft moves fell out of the
scoring language. The same point reaches past PDE to clinical, legal,
institutional, and workflow settings, each of which carries admissibility
and authority conditions that generic reasoning labels can miss.

Useful evaluation artifacts preserve action-relevant state, so the most
informative records here are typed fields: selected residual edge,
rejected nearest confuser, source evidence, satisfied and unsatisfied
evidence obligations, action schema, step index, invariant check, and
later outcome. These fields show whether a system executed the right
research move where a plausible description of it would have passed an
accuracy score.

# Meta-language

In one track we ask whether some moves operate a level above the base
structural vocabulary: changing the admissible criteria, making an
equivalence class primary, promoting an auxiliary object into the main
object of study, or reframing the question itself.

Across these families one pattern holds: meta cards are separable from adjacent lower-tier forms, typed parsing identifies the family, and a target card sharpens an already-parsed artifact, lifting frozen typed-frame artifacts from 6.91/8 to 7.91/8. Easy cases reach ceiling without testing downstream use, and content matters more than packaging.

Compact meta-level semantics improve already-parsed evidence artifacts
and tell frame-changing moves apart from adjacent lower-tier ones. Wrong
meta cards can mis-shape downstream artifacts, which gives the meta layer
causal content. The evidence supports three candidate meta families and
argues against expanding to a fourth before the data warrant it.

# From vocabulary to action schemas

The strongest later evidence arrives when the vocabulary is compiled into
an action schema the agent executes, with the label form held back as a
control.

Boundary-card experiments show the pattern. Agents act correctly from a
fully specified boundary card that states the satisfied evidence
obligation, unsatisfied evidence obligation, permitted update, blocked
update, next-action rule, and false-reading confuser. Letting the model
extract that card raw is unreliable, model-only validation improves but
still waves through unsafe cards, rule-backed source-cue validation plus
action-schema fields recover correct behavior on the tested packets.

Process-control experiments show the same architecture. A compiled action
schema, selected residual edge, rejected nearest confuser, source
evidence, step index, required next action, reached 1.0 action accuracy
on the held-out two-step packet. Label-only controls failed, and so did
free-form automatic compilation. Typed class selection helped but stayed
unsafe until we added source-cue checks and deterministic lowering.
Open-set refusal kept outside cases from being forced into known classes.

The resulting architecture is a research-agent contract:
``` math
\begin{aligned}
\text{source facts} &\rightarrow \text{residual/evidence carrier}
\rightarrow \text{nearest confuser} \\
&\rightarrow \text{action program}
\rightarrow \text{deterministic check}
\rightarrow \text{outcome trace}.
\end{aligned}
```
This sits next to algorithm selection, metareasoning, selective
prediction, mixture-of-experts routing, prompt-programming systems, and
workflow-agent evaluation . As a runtime contract for research agents, it
binds local source facts to the next inspectable action.

# Mechanization placement

Across the math corpus, structural vocabulary, agent-prompt tests,
meta-language probes, and action-schema experiments, one result recurs:
placement. A single research move can sit in several different roles.

<div id="tab:placement">

| Placement | Appropriate use | Failure mode |
|:---|:---|:---|
| Recognition language | Naming and comparing research moves. | Mistaken for a recipe. |
| Human review aid | Helping reviewers remember obligations and confusers. | Measured by self-reported usefulness instead of blinded decisions. |
| Evidence contract | Forcing an output into inspectable fields. | Shape is imitated without source alignment. |
| Deterministic check | Enforcing a crisp pass/fail condition. | Check overreaches beyond its contract. |
| Policy feature | Supplying state to a decision rule. | Retrospective labels mistaken for prospective policy quality. |
| Action schema | Binding source facts to next actions and stop rules. | Unsafe if parsed free-form or without refusal. |
| Judgment | Handling semantic frontier choices. | Hidden behind premature automation. |

Placement roles for research-move vocabulary.

</div>

Place each move at the strongest level its evidence supports. Structural
vocabulary is the recognition layer, typed receipts and nearest-confuser
fields form the evidence-contract layer, deterministic gates earn their
place once the contract is crisp. Human judgment stays necessary wherever
a move is semantic, frontier-dependent, or mathematically substantive.

# Future validation

Five bounded claims now stand on the evidence: the two-cultures
operationalization holds under its negative control, the structural
vocabulary ports across fields, the PDE audit corrects the earlier
boundary, the meta-language artifact result is scoped to typed
conditions, and carrier selection accounts for where mechanization pays
off. Further experiments would strengthen external validity and
prospective-use claims.

Four follow-ons carry the most value: (i) a blinded human or expert audit
of structural-vocabulary assignments and checklist usefulness,
(ii) production or historical-trace replay testing whether compiled
contract fields reduce downstream cost, missed obligations, false stops,
or wrong actions relative to strong context baselines, (iii) a clean
meta-language downstream-consequence test with generic headroom, and
(iv) a fresh blind PDE or broader scientific corpus audit using
covered-vs-none coverage, operation-identity reliability, decoys, and
human review.

# Broader impact

Measuring intermediate research moves, evidence payments, confuser
rejection, and action schemas sharpens evaluation discipline for research
agents. A reviewer can then see where a final-answer score or a broad
reasoning label would have papered over a domain-specific limitation, and
the claims one can make about agent capability tighten accordingly.

A structural label can also be misused as an authority signal, dressing
up a weak research step to look more systematic than it is. Placement
already supplies the mitigation: a label stays advisory until it ties to
source evidence, falsifiers, deterministic checks, or downstream
outcomes. Domain-specific evaluation should report its residuals and
confusers, leaving every move that resists the nearest available category
visibly uncategorized.

# Limitations

We cover one research system and curated corpora, which gives us a
measured vocabulary and a mechanization account for research moves.

Most of our coverage judgments are model-mediated, so we shore up several
claims with cross-family and multi-rater audits. Independent human and
expert audits are the natural next validation layer, here, human audit
remains a future external-validity test whose evidentiary value is still
to be collected.

Several agent-facing experiments are small-N mechanism tests. Their point
estimates diagnose mechanism, so reading them as population estimates
would overreach, and small differences should not carry inferential
weight. The main weight falls on large contrasts, negative controls,
decoys, wrong-card tests, and cases where a carrier change alters the
downstream artifact.

Coverage measures structural recognition, so generative competence,
frontier selection, and mathematical correctness need separate tests.

The evidence supports a compact core vocabulary plus field-specific
receipts and confuser guards, while also surfacing overlap, low-use
operations, and calibration-sensitive full/partial distinctions in some
catalog versions.

For meta-language, the evidence supports separability and artifact
refinement under typed conditions, with incremental routing and
downstream consequence tests as the next extension.

Action-schema positives are strongest in replay, synthetic, and
rule-checked settings, with production-trace tests as the next
external-validity step.

# Conclusion

A Gowers-style question opened the inquiry: do theory-building and
problem-solving arcs favor different research-move vocabularies? In this
corpus, they do. The binary sits inside a structural vocabulary whose
usefulness depends on placement.

Passive labels have little causal force, a correct compact schema can
help once the move is selected, meta-language sharpens typed artifacts,
checked action schemas change downstream behavior. So the discipline is
to name recurring research moves, test their boundaries, and mechanize
the parts whose contracts can be made inspectable.

# Evidence map

<div id="tab:evidence-map">

| Claim family | Saved artifact or source |
|:---|:---|
| Two-cultures cross-coverage | `evidence/gp216_queries/gp216_cross_distribution_full.json` |
| Headline verifier | `evidence/reproducers/verify_gp216_claims.py` |
| Same-culture negative control | `evidence/gp216_queries/gp216_negative_control.json` |
| Four-operation compression | `evidence/gp216_queries/gp216_4op_compression.json` |
| Eight-subfield structural vocabulary | `evidence/gp216_queries/gp216_pathA_8sf_cluster.json` |
| Business held-out transfer | `evidence/gp216_queries/gp216_business_held_out_OOD.json` |
| Sparse 2026 specialist transfer | `evidence/gp216_queries/gp216_sparse_coverage_OOD.json` |
| PDE correction | `experiments/joint_vocab_corpus_ood_vC01_20260521/` |
| Catalog reliability stress test | `experiments/v128b_catalog_stats_20260521/` |
| Catalogue surface tests | `experiments/source_packet_catalog_surface_v14/` and follow-up catalogue/card tests in `research_log.md` |
| Meta-language tests | Meta-card, typed-frame, and packaging-ablation tests in `research_log.md` |
| Boundary-card and action-schema tests | Boundary-card and process-control tests in `research_log.md` |
| Pattern/action contract tests | Pattern/action contract synthesis in `research_log.md` and `research_roadmap.md` |
| Literature audit | `literature_audit.md` |
| Claim guardrail | `claim_evidence_matrix.md` |

Local artifacts that back each claim family.

</div>
