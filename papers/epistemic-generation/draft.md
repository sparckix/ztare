# Introduction

Epistemic verification asks whether a claim is adequately supported.
Epistemic generation asks how a research process chooses the next move
before such a claim exists. The move might be a reformulation, special
case, analogy, falsifier, auxiliary object, decomposition, evidence
boundary, or decision to stop a branch.

This paper makes three contributions. First, it gives a corpus-level
empirical operationalization of Gowers’s theory-builder/problem-solver
distinction . Two curated mathematical styles induce different
research-move vocabularies, and the difference survives cross-corpus
scoring and a same-culture negative control. The result gives the
distinction an empirical measurement surface without forcing all
mathematics into two types.

Second, the paper revises the binary into a broader structural
vocabulary of research moves. The later vocabulary explains why the
original split was real but incomplete: theory-building and
problem-solving emphasize different bands inside a wider space of
reformulation, abstraction, decomposition, local-to-global assembly,
invariance, translation, approximation, and constraint propagation.

Third, the paper identifies where such vocabularies become useful for
research systems. The experiments compare passive labels and large menus
with typed evidence fields, residual-to-check edges, rejected nearest
confusers, and executable action schemas. This is the
mechanization-placement thesis. Research-move language becomes
operational when it changes what gets checked, blocked, converted into
an artifact, or executed next.

For machine learning readers, the paper contributes an evaluation
framework for research agents. It treats generation as a sequence of
research moves rather than final-answer production, shows that generic
evaluation vocabularies can misclassify domain-specific reasoning, and
proposes typed intermediate representations for evaluating whether a
system selected, checked, and executed the right move.

# Evidence Base, Reproducibility, and Method

The unit of analysis is a research move: a bounded step that changes a
problem representation, admissible object, proof strategy, evidence
standard, decomposition, validation frame, or next action. A vocabulary
covers a move when a frozen operation gives a mechanistic fit under the
scoring rubric.

Coverage is diagnostic. It is not the target being optimized. High
coverage can indicate transfer, but it can also indicate force-fitting.
The experiments therefore use cross-corpus scoring, negative controls,
adversarial raters, decoys, wrong-card controls, source-cluster
blocking, and downstream consequence checks.

Table <a href="#tab:evidence-tiers" data-reference-type="ref"
data-reference="tab:evidence-tiers">1</a> summarizes the evidentiary
roles in this paper.

<div id="tab:evidence-tiers">

| Evidence tier | Role in the argument |
|:---|:---|
| Saved-output corpus results | Main quantitative claims: two-cultures split, negative control, structural-vocabulary coverage, and out-of-distribution transfer. |
| Cross-family and multi-rater audits | Reliability checks, especially for the PDE correction and catalog confusion analysis. |
| Replay and synthetic workflow experiments | Mechanism evidence for evidence carriers, residual-to-check edges, boundary cards, and action schemas. |
| Human and production-trace validation | Next validation layer for expert use and prospective deployment claims. |

Evidence tiers used in the paper.

</div>

The core percentages are recomputed from durable artifacts: stored move
lists, frozen vocabularies, scoring files, JSON verdicts, and local
reproducer scripts. Later workflow experiments are treated as mechanism
evidence: they show which carrier changes downstream behavior under
controlled conditions. For TMLR-style review, the expected supplementary
package is straightforward: the saved-output verifiers for the headline
corpus claims, the PDE joint- vocabulary scoring artifacts, the
meta-language score files, and the compact workflow replay scorers. The
paper does not require reviewers to accept hidden model transcripts as
evidence for the main quantitative claims; those claims are tied to
recomputable artifacts.

# A Corpus-Level Two-Cultures Result

The first corpus mined theory-building arcs including Wiles,
Grothendieck, Lurie, Scholze, Riemann, Newton, Einstein, and
Polya/Hadamard. The resulting theory-builder vocabulary includes moves
such as foundational object redefinition, cross-domain unification,
parameter-space internalization, vocabulary lifting, strategic
specialization, diagonal self-application, and concept revision .

A sister corpus mined problem-solving arcs including Erdos discrepancy,
Green–Tao, Hales–Jewett Polymath, Szemeredi regularity, Roth, Behrend,
Furstenberg, and Ramsey/Erdos–Szekeres. The resulting problem-solver
vocabulary emphasizes partitioning, governed iterative refinement,
theorem-use transfer, rank induction, and estimate chaining.

<div id="tab:two-cultures">

| Vocabulary                | Theory-builder corpus | Problem-solver corpus |
|:--------------------------|----------------------:|----------------------:|
| Theory-builder vocabulary |                 58.1% |                 20.7% |
| Problem-solver vocabulary |                 19.1% |                 65.9% |

Cross-distribution coverage for the two mined vocabularies.

</div>

The average own-corpus advantage is 42.1 percentage points. The result
is symmetric: each vocabulary fits its own corpus far better than the
other. A same-culture random split produces only a 3.0 percentage-point
gap, far below the curated two-cultures gap. The result therefore gives
the Gowers distinction an empirical operational form: two mathematical
styles induce different research-move vocabularies, and the gap is not
reproduced by a random partition of one style.

The novelty claim is precise. To our knowledge, this is the first
corpus-level empirical operationalization of Gowers’s
theory-builder/problem- solver distinction. Prior work has studied
mathematical practice, proof reading, examples, collaboration,
consensus, and subfield prestige . Those studies are adjacent rather
than competing: they do not directly test whether theory-building and
problem-solving styles differ by cross-coverage of research-move
vocabularies.

# From Two Cultures to a Structural Vocabulary

The two-cultures result was a starting point, not the final taxonomy. A
later eight-subfield remine covered 1,214 moves across 64 mathematical
arcs and compressed them into six shared-core operations, eight broadly
shared operations, and four peripheral operations.

<div id="tab:structural-vocabulary">

| Tier | Operations |
|:---|:---|
| Shared core | Problem Reformulation and Reduction; Generalization and Abstraction; Decomposition and Recomposition; Local-to-Global Assembly; Canonical Form and Invariance; Cross-Domain Translation. |
| Broadly shared | Iterative Refinement; Recursive Decomposition; Duality and Adversarial Framing; Layered Approximation and Convergence; Extremal Method; Probabilistic and Stochastic Methods; Dimensional and Structural Lifting; Constraint Imposition and Propagation. |
| Peripheral | Characterization by Obstruction; Internalization and Self-Reference; Axiomatization and Foundational Repair; Controlled Universe Extension. |

Layered structural vocabulary from the eight-subfield remine.

</div>

This revision generalizes the original result. Theory-builder and
problem-solver mathematics emphasize different bands inside a larger
structural language. Some moves are shared, some are subfield idioms,
and some apparent culture-specific moves become aliases after the wider
remine.

The vocabulary also transfers beyond the original mathematical corpus. A
business held-out set reaches 57.9% shared-plus-broad coverage. Four
sparse 2026 specialist papers reach 75.2%. These results support a
field-portable structural vocabulary for research moves. The internally
used term “universal” should be read operationally: portable across
fields under measured scope, with residuals and confusers recorded
rather than absorbed by definition.

# Methodological Warning from the PDE Rescore

The PDE rescore is a methodological result for the evaluation of
frontier agents and research systems. Domain-specific reasoning can look
absent when an evaluation vocabulary omits the domain-specific
operations that carry the reasoning. A 12.5% adversarial score on a
post-cutoff PDE paper initially looked like a sharp capability boundary
for the structural vocabulary. The audit showed a different mechanism:
the score was a v5-only, single-rater, adversarial-stance result on one
difficult PDE paper. When the same paper was rescored against the joint
structural vocabulary plus the PDE estimate-craft vocabulary, four
raters across two model families covered 95.8–100% of moves under the
covered-vs-none metric. Across the five-paper corpus, two-family
coverage reached 116/118 moves, or 98.3%, with a 0% decoy match rate.

<div id="tab:pde-correction">

| Finding | Current interpretation |
|:---|:---|
| Old 12.5% PDE score | Historical v5-only adversarial baseline. |
| Joint vocabulary PDE audit | 95.8–100% covered-vs-none coverage across four raters. |
| Corpus-wide joint audit | 116/118 moves covered by both model families. |
| Strict full-only coverage | Calibration-sensitive secondary diagnostic. |
| Remaining uncertainty | Fresh blind PDE corpus, human or expert audit, and operation-confusion analysis. |

Methodological interpretation of the PDE stress case.

</div>

The warning for machine-learning evaluation is direct. An evaluation
that tests frontier agents on domain-specific reasoning while using only
generic reasoning categories can manufacture artificial capability
boundaries. The expanded language plus PDE estimate-craft receipts
covered the former stress case under multi-rater, decoy-controlled
scoring. The paper therefore reports covered-vs-none and
operation-identity reliability, with strict full-only coverage as a
calibration-sensitive secondary metric.

# Carrier Selection in Agent-Facing Tests

The early agent-facing experiments tested research-move vocabulary
supplied as prompt text, feature prose, or a broad catalogue. Those
carriers had little effect on the tested outcomes.

<div id="tab:agent-tests">

| Test | Result | Interpretation |
|:---|:---|:---|
| Exact-answer benchmark with primitive prompts | Baseline, static catalogue, one-primitive, and diagnose-then-solve arms each scored 11/26; placebo diagnose-then-solve scored 8/26. | No exact-answer lift from primitive prompt text. |
| Blind route-choice probes | Generic reasoning won 7/10 comparisons; passive real features, forced real features, and forced placebo each won 6/10. | Primitive text changed rationale vocabulary more than route choice. |
| External operator-transfer test | Real operator lost to schema generic and operational swaps; real beat all swaps in 0/24 cases. | Operator prose was not isolated from generic artifact discipline. |
| Downstream execution test | Ordinary routes received 51 votes; schema routes 47; primitive-feature routes 28. | Execution did not rescue primitive-feature routes. |
| External consequence gate | Real 4.25/5 vs generic 4.04/5; real beat best-swap on 2/20 source clusters. | Better-looking obligations did not imply stronger consequence behavior. |

Carrier-selection evidence from agent-facing tests.

</div>

The universal-catalog experiments locate the mechanism more precisely.
In V14, an operatorized catalogue improved slightly over a descriptive
catalogue, but not over source-only reasoning: source-only scored
6.50/10, the current catalogue summary 6.00/10, and the operatorized
catalogue 6.50/10. In V15, a single correct operator card scored
8.875/10 while a single plausible wrong card scored 4.375/10. The
operator content is active when the correct move has already been
identified. The central problem is routed selection with disambiguators,
nearest-confuser rejection, and evidence artifacts.

# Implications for Research-Agent Evaluation

The experiments suggest three design requirements for evaluating
research agents on open-ended scientific or mathematical work.

First, final-answer accuracy is too coarse for epistemic generation. A
research agent may fail by selecting the wrong object, paying the wrong
evidence debt, over-updating from a narrow receipt, omitting a necessary
falsifier, or continuing after a branch should stop. These failures are
often invisible in a single final-answer score.

Second, the evaluation vocabulary must include the domain operations
that carry the reasoning. The PDE rescore shows how a generic structural
vocabulary can understate capability when estimate-craft moves are
absent from the scoring language. The same principle applies beyond PDE:
clinical, legal, institutional, and workflow settings each have
admissibility and authority conditions that generic reasoning labels may
miss.

Third, useful evaluation artifacts should preserve action-relevant
state. The most informative records in these experiments are not labels
alone. They are typed fields: selected residual edge, rejected nearest
confuser, source evidence, paid and unpaid receipts, action program,
program counter, invariant check, and later outcome. These fields make
it possible to evaluate whether a system executed the correct research
move rather than producing a plausible description of that move.

# Meta-Language

The meta-language track asks whether some moves operate one level above
the base structural vocabulary: changing admissible criteria, making an
equivalence class primary, promoting an auxiliary object into the main
object of study, or changing the question frame itself.

<div id="tab:mm">

| Experiment family | Result | Interpretation |
|:---|:---|:---|
| MM-V1 | Correct meta cards beat adjacent lower-tier forced fits; generic and meta-frame-only reached ceiling. | Meta families are separable. |
| MM-V2 | Target cards beat wrong cards and adjacent lower-tier cards; typed-frame-only scored 11/11. | Typed parsing can identify the family; cards control confusers. |
| MM-V3 | Target-card revision improved frozen typed-frame artifacts from 6.91/8 to 7.91/8 and beat generic revision. | Meta cards sharpen an already-parsed artifact. |
| MM-V4 | Naturalistic family transfer ceilinged for typed-frame and target cards; adjacent and wrong cards failed. | Separability holds; route-family accuracy is easy once typed roles are visible. |
| MM-V5/MM-V6 | Correct content beat wrong content; opcode packaging tied prose; target-over-generic remained small. | Content matters more than opcode syntax on this endpoint. |

Summary of the meta-language evidence.

</div>

The supported conclusion is that compact meta-operator semantics improve
the quality of already-parsed evidence artifacts and distinguish
game-layer moves from adjacent lower-tier moves. Wrong meta cards can
mis-shape downstream artifacts, which means the meta layer has causal
content. The evidence supports MM01–MM03 as live operator candidates and
argues against premature expansion to a fourth family.

# From Vocabulary to Action Schemas

The strongest later evidence comes from experiments where the vocabulary
is compiled into an action schema rather than displayed as a label.

Boundary-card experiments show the pattern. Agents can act correctly
from a gold boundary card that states the paid receipt, unpaid receipt,
permitted update, blocked update, next-action rule, and false-reading
confuser. Raw model extraction of that card is unreliable. Model-only
validation improves but still accepts unsafe cards. Rule-backed
source-cue validation and action-program fields recover correct behavior
on the tested packets.

The orchestration-menu experiments show the same architecture. A
compiled menu program with selected residual edge, rejected nearest
confuser, source evidence, action program, current action index, and
required next action reached 1.0 action accuracy in the held-out
two-step process-control packet. Label-only controls failed. Free-form
automatic compilation failed. Typed class selection helped but was
unsafe until source-cue checks and deterministic lowering were added.
Open-set refusal was needed to avoid forcing outside cases into known
classes.

The synthesis is a research-agent contract architecture:
``` math
\begin{aligned}
\text{source facts} &\rightarrow \text{residual/evidence carrier}
\rightarrow \text{nearest confuser} \\
&\rightarrow \text{action program}
\rightarrow \text{deterministic check}
\rightarrow \text{outcome trace}.
\end{aligned}
```
This is adjacent to algorithm selection, metareasoning, selective
prediction, mixture-of-experts routing, prompt-programming systems, and
workflow-agent evaluation . The contribution here is narrower: a runtime
contract for research agents that binds local source facts to the next
inspectable action.

# Mechanization Placement

The common result across the math corpus, structural vocabulary,
agent-prompt tests, meta-language probes, and compiler-shaped positives
is placement. A recurring research move can occupy different roles.

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

The practical lesson is to place each move at the strongest level its
evidence supports. Structural vocabulary is the recognition layer. Typed
receipts and nearest-confuser fields are the evidence-contract layer.
Deterministic gates are justified when the contract is crisp. Human
judgment remains necessary where the move is semantic,
frontier-dependent, or mathematically substantive.

# Readiness and Next Experiments

The current evidence supports a coherent scientific paper: a
two-cultures operationalization, a field-portable structural vocabulary,
a corrected PDE audit, a scoped meta-language artifact result, and a
carrier-selection account of mechanization. Additional experiments would
strengthen public claims rather than change the main thesis.

<div id="tab:readiness">

| Question | Decision |
|:---|:---|
| Private workingpaper circulation | Ready after claim-alignment edits, bibliography pass, and regenerated PDF/Markdown. |
| SSRN/public submission | Viable if framed around the corpus result, structural vocabulary, methodological warning for domain-specific evaluation, and mechanization-placement thesis. Stronger claims about human usefulness or production improvement should wait for direct validation. |
| Gowers novelty | Strong as a narrow corpus-level operationalization; use the exact novelty wording from the literature audit. |
| Universal-language claim | Keep as field-portable structural vocabulary with measured scope and residuals. |
| Meta-language claim | Include as artifact refinement, separability, and confuser-control evidence. |
| More experiments before rewrite | Not needed. The rewrite should align the claims with the existing evidence. |

Current publication decisions.

</div>

The highest-value follow-on experiments are: (i) a blinded human or
expert audit of structural-vocabulary assignments and checklist
usefulness; (ii) production or historical-trace replay testing whether
compiled contract fields reduce downstream cost, missed obligations,
false stops, or wrong actions relative to strong context baselines;
(iii) a clean meta-language downstream-consequence test with generic
headroom; and (iv) a fresh blind PDE or broader scientific corpus audit
using covered-vs-none coverage, operation-identity reliability, decoys,
and human review.

# Broader Impact

The main positive impact is better evaluation discipline for research
agents. The paper argues for measuring intermediate research moves,
evidence payments, confuser rejection, and action schemas rather than
relying only on final-answer scores or broad reasoning labels. This can
reduce misleading claims about agent capability and make domain-specific
limitations more inspectable.

The main risk is misuse of the vocabulary as an authority signal. A
structural label can make a weak research step appear more systematic
than it is. The mitigation is built into the placement thesis: labels
are advisory unless they are tied to source evidence, falsifiers,
deterministic checks, or downstream outcomes. Domain-specific evaluation
should report residuals and confusers instead of forcing every move into
the nearest available category.

# Limitations

This paper studies one research system and curated corpora. Its
contribution is a measured vocabulary and mechanization theory for
research moves.

Most coverage judgments are model-mediated. Cross-family and multi-rater
audits strengthen several claims; independent human and expert audits
are the natural next validation layer.

Coverage measures structural recognition. Generative competence,
frontier selection, and mathematical correctness require separate tests.

The current evidence supports a compact central vocabulary plus
field-specific receipts and confuser guards. It also identifies overlap,
low-use operations, and calibration-sensitive full/partial distinctions
in some catalog versions.

The meta-language evidence supports separability and artifact refinement
under typed conditions. Incremental routing and downstream consequence
tests are the next extension.

The compiler-shaped positives are strongest in replay, synthetic, and
rule-checked settings. Production-trace tests are the next
external-validity step.

# Conclusion

The paper began with a Gowers-style question: do theory-building and
problem-solving arcs induce different research-move vocabularies? In
this corpus, they do. The stronger result is that the binary sits inside
a broader structural vocabulary whose usefulness depends on placement.

Passive labels have little causal force. Correct compact operators can
help after selection. Meta-language can sharpen typed artifacts. Checked
action schemas can change downstream behavior. The general lesson is to
name recurring research moves, test their boundaries, and mechanize the
parts whose contracts can be made inspectable.

# Evidence Map

<div id="tab:evidence-map">

| Claim family | Saved artifact or source |
|:---|:---|
| Claim family | Saved artifact or source |
| Two-cultures cross-coverage | `evidence/gp216_queries/gp216_cross_distribution_full.json` |
| Headline verifier | `evidence/reproducers/verify_gp216_claims.py` |
| Same-culture negative control | `evidence/gp216_queries/gp216_negative_control.json` |
| Four-operation compression | `evidence/gp216_queries/gp216_4op_compression.json` |
| Eight-subfield structural vocabulary | `evidence/gp216_queries/gp216_pathA_8sf_cluster.json` |
| Business held-out transfer | `evidence/gp216_queries/gp216_business_held_out_OOD.json` |
| Sparse 2026 specialist transfer | `evidence/gp216_queries/gp216_sparse_coverage_OOD.json` |
| PDE correction | `experiments/joint_vocab_corpus_ood_vC01_20260521/` |
| Catalog reliability stress test | `experiments/v128b_catalog_stats_20260521/` |
| Universal-catalog surface tests | `experiments/source_packet_catalog_surface_v14/` and V15–V17 in `research_log.md` |
| Meta-language tests | MM-V1 through MM-V6 in `research_log.md` |
| Boundary-card and compiler tests | H23–H36 in `research_log.md` |
| Pattern/action contract tests | H31–H55 synthesis in `research_log.md` and `research_roadmap.md` |
| Literature audit | `literature_audit.md` |
| Claim guardrail | `claim_evidence_matrix.md` |

Principal local artifacts behind the paper claims.

</div>
