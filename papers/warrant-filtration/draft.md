<!-- DRAFT v1. Short technical paper / workshop-or-preprint scope. Honest positioning: a specific synthesis with
named lineage, thin (demonstration-grade) empirics, one open theoretical question (cyclic convergence). Not a
top-venue full paper as-is — see §7. Companion code: src/ztare/scenarios/{strength,wager,research_signals,
warrant_promotion}.py; experiment: src/ztare/experiments/epistemic_lift_experiment.py. -->

# Warrant Filtration: Checkability-Stratified Gradual Argumentation for Grading Contested Claims

## Abstract

A governed research map — theses, claims, evidence, and the support/attack edges between them — is a bipolar
argument graph. Resolving it to a crisp verdict (SUPPORTED / BLOCKED / REFUTED) by grounded acceptance is the
right floor, but the wrong headline on a research substrate, where almost nothing is ever fully settled: nearly
every live map reads BLOCKED, and a crisp BLOCKED cannot distinguish a thesis backed by many sources but still
contested from one with no support at all. A gradual argumentation semantics grades this, but a gradual
semantics needs edge weights, and choosing numbers (why 0.7?) reintroduces the priors a governance setting is
built to avoid. We introduce **warrant filtration**: rather than weight edges, we order them by an external
epistemic-*checkability* ladder (kernel-certified ≻ re-executable ≻ verbatim-quote ≻ unchecked) and run a
continuous gradual semantics — the Quadratic Energy Model — once per nested stratum, emitting an **uncollapsed
lexicographic strength profile** `(s0, s1, s2, s3)` compared ordinally. The profile uses only the warrant partial
order, so it has zero free numeric parameters. We pair it with an override lattice that keeps a crisp refutation
from being laundered into a number, exact Shapley source-attribution, and a per-source (and derivation-lineage)
collapse. Every ingredient is classical; the contribution is the assembly. On adversarial synthetic topologies
the assembly is resilient where flat aggregation, a count heuristic, and — in the realistic cold prompt — a
language-model judge are not: a fifty-to-one sycophantic flood, a citation cascade, and a contradiction cycle
each break a naive aggregator on the topology that stresses it, while a clean control has all methods agree. The
evidence is a demonstration on hand-built graphs, not a benchmark, and one theoretical question (convergence on
cyclic graphs) is left open and surfaced as an honest non-terminal state rather than papered over.

## 1. The problem

Systems that aggregate evidence into a decision increasingly do so over an explicit argument graph: claims as
nodes, support and attack as typed edges. When the graph is *governed* — every element and relation traceable,
no language model permitted inside the decision rule — the natural verdict is grounded (least-fixpoint)
acceptance over an assumption-based argumentation framework [Bondarenko et al. 1997; Dung 1995]: a claim is
accepted iff evidence-rooted, and the thesis is SUPPORTED, BLOCKED, or REFUTED accordingly.

This verdict is correct but coarse. On a research substrate the adversarial process that builds the map attaches
open tensions and gaps to the thesis by construction, so the thesis almost always has at least one unresolved
challenge and the verdict is almost always BLOCKED. Worse, BLOCKED conflates two epistemically opposite states:
a thesis with strong evidence and open challenges, and a thesis with no support at all. A decision-maker needs
these separated; the crisp verdict cannot separate them.

The obvious remedy is a gradual argumentation semantics, which assigns each claim a strength in `[0,1]` rather
than an accept/reject label. But a gradual semantics is parameterized by edge weights, and in a governance
setting — where the entire trust story is that verdicts are deterministic functions of the graph and verbatim
evidence, with no injected priors — a hand-chosen weight (`0.7` for a quote, `0.4` for a guess) is exactly the
kind of unjustifiable number the setting exists to exclude. The question this paper answers is how to obtain a
graded read *without* choosing any such number.

## 2. Background and prior art

**Gradual / quantitative bipolar argumentation.** A quantitative bipolar argumentation framework (QBAF) equips
an argument graph with base scores and computes a strength per argument from its supporters and attackers under a
gradual semantics: DF-QuAD [Rago et al. 2016], the h-categoriser [Besnard and Hunter 2001; Amgoud et al. 2017],
and the Quadratic Energy Model (QEM) [Potyka 2018], a continuous, damped fixed-point semantics that is defined on
cyclic graphs where DF-QuAD is not. We use QEM.

**Attribution.** Shapley-value attribution over gradual argumentation is established: relation-attribution
explanations assign Shapley values to *edges* under exactly the QEM/DF-QuAD/Euler semantics [Yin, Potyka and Toni
2024], and impact measures generalize this across gradual semantics [Al Anaissy et al. 2025]. Our Shapley layer
attributes to *sources* rather than edges but is otherwise the same idea, and is credited, not claimed.

**Stratified / ordinal reasoning.** Refining a result over ordered strata into a lexicographic outcome is
System-Z and preferred subtheories [Brewka 1989], applied to abstract argumentation as stratified labelings
[Thimm and Kern-Isberner 2013]; replacing cardinal weights with ordinal certainty levels is possibilistic
argumentation [Alsinet et al.]. These supply the *skeleton* — nested strata, lexicographic comparison, ordinal
levels — but over classical consistency or discrete labelings, not a continuous gradual semantics, and stratified
by internal controversiality or premise certainty, not by an external checkability order over edges.

**Argumentative LLMs.** Building a QBAF from language-model outputs and scoring it with a gradual semantics is
the ArgLLM line [Freedman et al. 2024] and successors. That work uses cardinal, model-estimated base scores and a
single scalar; it does not stratify by checkability and does not emit a profile.

To our knowledge no published work combines a continuous gradual semantics with cardinal weights *removed* in
favour of an external checkability ordering of edges, re-run per stratum and kept as an uncollapsed lexicographic
profile. That combination is the contribution.

## 3. Method

**The graph and the warrant ladder.** The input is a bipolar argument graph: `SUPPORTS`/`DERIVES` edges and
`CONTRADICTS`/`FALSIFIES`/`CHALLENGES` edges over claim, evidence, and finding nodes. Each edge carries a
**warrant** typed by re-executable checkability, in a fixed total order: `W0` kernel-certified (a machine-checked
proof), `W1` independently recomputable from bound data, `W2` a verbatim quote binding, `W3` proposed-unchecked.
Warrants are *earned* — a `W0` exists only because a check actually ran — not asserted; this is what keeps the
downstream numbers prior-free.

**The semantics (QEM).** Base scores are prior-free: leaf evidence scores `1`, every internal node scores `0`.
For node `a` with supporters `Sup(a)` and attackers `Att(a)`, the energy is `E_a = Σ_{Sup} s_b − Σ_{Att} s_b`, the
squashing function is `h(x) = max(0,x)² / (1 + max(0,x)²)`, and the update is
`f_a(s) = w_a − w_a·h(−E_a) + (1−w_a)·h(E_a)`, iterated with forward-Euler damping
`s_a(t+1) = s_a(t) + δ·(f_a(s(t)) − s_a(t))`, `δ = 0.1`, to a fixed point.

**Filtration, not weights.** Instead of assigning cardinal weights to warrant classes, we run the semantics four
times. Stratum `k` includes only edges at least as checkable as tier `k` (`k=0` keeps `W0` only; `k=3` keeps
all). The output is the **strength profile** `S = (s0, s1, s2, s3)`: the thesis strength if one trusts only
kernel certificates, then also re-executable computation, then quotes, then proposals. Theses are compared
lexicographically from `s0` up. The profile is built entirely from the warrant partial order and has no chosen
numbers; `(0, 0, 0.97, 0.97)` reads as "well supported, but nothing kernel-hard — a castle of quotes."

**Override lattice.** A crisp verdict still overrides the number, top-down: `REFUTED` (a surviving `W0`/`W1`
attack on the thesis) ≻ `NONCONVERGENT` (the iteration hit its cap; see §4) ≻ `UNSUPPORTED` (no support at any
tier) ≻ `CONTESTED` (report the profile — the state of essentially every live map). A kernel-grade refutation is
never laundered into "strength 0.12."

**Attribution and provenance.** `shapley_support` computes exact removal-Shapley over the evidence sources, with
the characteristic function equal to thesis strength given only that subset present; contributions sum to the
strength (efficiency), naming what the decision rests on. Support is aggregated per provenance source — maximum
within a source, sum across sources, and across a source's `DERIVED_FROM` lineage — so redundant quotes from one
document, or a citation cascade, cannot inflate a stratum the way independent corroboration does.

## 4. Properties

Determinism is unconditional: the QEM update is Lipschitz, so the trajectory is unique and bit-reproducible.
Convergence to a fixed point is proved in the gradual-semantics literature for acyclic graphs; no universal
theorem covers cyclic bipolar weighted semantics. We do not paper over this: a run that reaches its iteration cap
is reported as the first-class state `NONCONVERGENT`, never a number reached by an unproven process. Cycle
resistance, separately, is a theorem: `h(x) < x` on `(0,1]`, so a pure support cycle with zero internal base
weight has `0` as its only fixed point — no self-lifting bootstrap. The whole construction introduces zero free
numeric parameters beyond the fixed `δ` and stopping tolerance.

Because no prior gradual semantics emits a warrant-stratified profile, a **local** monotonicity property specific
to the profile can be stated: **promoting a support edge to a strictly more checkable warrant never
lexicographically lowers the profile of the node that edge is incident on, and promoting an attack edge never
raises it** (the thesis is the special case of an edge incident on it). Sketch: a promotion moves the edge into
one or more earlier (harder) strata and removes it from none; the semantics satisfies the standard
local-monotonicity principle — a node's strength is nondecreasing in its supporters and nonincreasing in its
attackers, immediate from `h` being nondecreasing — so at each newly-keeping stratum the target's strength moves
weakly in the edge's direction and is unchanged elsewhere, a componentwise and hence lexicographic inequality.
The locality is essential and not a limitation of the sketch: bipolar argumentation is non-monotone globally.
Promoting an attack edge *deep* in the graph can *raise* a distant thesis through a chain of rebuttals — the
enemy-of-my-enemy effect — so the effect of a promotion on a target it is not incident on is not sign-determined
and must be recomputed, not predicted. This is exactly why the wager (§6) has the kernel *simulate* the
recompilation of each declared outcome rather than assume its direction. A machine-checked proof of the local
property for the acyclic case is blueprinted; the audit against the gradual-semantics principle canon (balance,
monotony, neutrality, directionality, per stratum and lifted to the order) is the natural next step.

## 5. Demonstration

Because the contribution is representational — distinguishing states a crisp verdict conflates — we test
adversarial *resilience* on hand-built synthetic topologies, not accuracy on a corpus. Each topology isolates one
mechanism; a positive control ensures "the method diverges" is not a tautology of the design. Baselines: a
**flat QEM** (the same semantics with strata, override, and collapse removed — a plain sum), a **count**
heuristic (supports minus attacks), and a **language-model judge** (codex/gpt-5.5) in three arms of increasing
charity — `cold` (raw prose, structure hidden), `structured` (typed relations, warrant tiers hidden), and
`labeled` (relations plus the same warrant tiers the system extracts). Results (one call per topology; the judge
is reported, not asserted):

- **Sycophantic flood** (one `W0` refutation vs. fifty `W3` supports): our method returns `REFUTED` via the
  override; flat QEM and count both read *supported*; the judge reads *supported* in the cold and structured arms
  and recovers to *refuted* only in the labeled arm. The one thing that flips the flood verdict is precisely the
  checkability structure the system surfaces and a prompt does not supply.
- **Contradiction cycle** (a mutually-contradicting pair, one side supporting the thesis): the damped semantics
  converges to a stable `CONTESTED`; the same fixed point undamped (`δ=1`) fails to converge within 4000
  iterations, so the damping is load-bearing.
- **Citation cascade** (five sources supporting the thesis, all derived from one): lineage collapse lowers the
  strength to `0.50` against `0.96` for five genuinely independent sources; flat QEM sums both to `0.96`, and the
  judge reads *supported* in all three arms, even when the prose states plainly that the five share one source.
- **Clean control** (two independent sources, no attacks): all methods agree the thesis is supported.

The reading is deliberately narrow. Given the extracted structure, the language model reasons adequately (it
recovers on the flood when handed the tiers); what it does not do is *construct or enforce* that structure — it
is fooled by raw volume and does not discount derivative provenance in any arm. The system's contribution over a
judge is thus the deterministic structure-surfacing and provenance-discounting, not better reasoning.

Two robustness notes. On the sixteen real project maps the system has built, the damped iteration converged on
all sixteen and the `NONCONVERGENT` state never fired; the deadlock divergence above required reinforcing the
cycle beyond what the map generator produces, so non-convergence is a guarded possibility rather than an observed
regime. And the obvious objection — why not hand a language model the structured, warrant-labelled input and let
it judge — is answered three ways. Empirically the model does not match even then: it reads the citation cascade
as supported in the labelled arm too, having no mechanism to discount derivative provenance. A warrant is
*earned* — a `W0` because a proof ran, a `W1` because a computation reran — so a model asked instead to *assign*
the tiers is trusting labels it cannot itself verify, and the ladder's grounding is lost. And the verdict is then
non-deterministic, unauditable, and paid per call on every recompilation. The semantics is the price of a
deterministic, auditable verdict over earned warrants, worth paying exactly when those properties are the point.

## 6. Application: a protected-hypothesis lifecycle

The same graded read supports a decision-time operation we mention only briefly. A thesis that is grounded but
contested can carry a *wager*: a named experiment whose declared outcomes are typed graph edits (evidence and
warrants only, never a verdict), which the kernel simulates by recomputation. A wager is admitted only if some
outcome moves the decision, ranked by prior-free information yield, and its lifecycle never changes the claim's
verdict. Executing a wager writes its resolved evidence back into the map, and surviving a re-check promotes an
edge's warrant (`W2→W1`), so the ladder is dynamic. This turns "perpetually contested" from a defect of the crisp
verdict into a managed queue of the cheapest tests that would settle the decision.

The economics of ranking experiments by information yield are not new — that is value of information and active
learning — and a queue that resolves contested claims is shared with prediction markets and bug bounties. What is
new is the placement: defining a wager as a *typed graph edit the kernel simulates* turns a gradual argumentation
framework from a passive read-out into a state machine, and ties the value-of-information reward to a *structural*
warrant promotion. At multi-agent scale this queue would inherit the free-rider and spam pressures of any public
good — the executor pays while downstream readers capture the upgraded warrant for free, and cheap-to-propose
wagers can flood the queue — which a cost-to-propose and a bounty would address; at single-operator scale they do
not arise.

## 7. Limitations

The empirical evidence is a demonstration, not a benchmark: four hand-built topologies, one call per arm, a
single language model. It shows the mechanisms behave as designed under adversarial structure; it does not
measure a win rate on real data, and no such corpus of checkability-labelled argument graphs yet exists. The
theoretical contribution is a synthesis, not a new primitive — the nested-strata-to-lexicographic-profile
skeleton is itself prior art, and the honest framing is an assembly with its lineage named, not the invention of
stratified argument strength. Convergence on cyclic graphs has no universal guarantee here (nor, we believe, for
any bipolar weighted gradual semantics), which is mitigated by the `NONCONVERGENT` state and by the small size of
real maps but not resolved. The warrant ladder is only as meaningful as the checks that mint it, and this bounds
the method twice. First, a `W1` exists only where a claim recomputes from bound data and a `W0` only where a
machine-checked proof does, so an empirical claim that cannot be reduced to a re-executable script tops out at
`W2` — no governance manufactures a higher tier, and the honest ceiling of the method is the ceiling of what can
be checked again. Second, in consequence, the ladder's *resolution* scales with how much of a map has earned
higher warrants: on the sixteen real maps tested none had earned a `W0` or `W1` (all evidence entered as `W2`
quotes), so the profile was effectively two-band — evidence-backed versus not — rather than the full four. That
still separates unsupported from contested and reads a castle of quotes for what it is; it is not degeneration to
a single scalar. But the four-way resolution activates only as recomputation and kernel-verification are actually
run on the evidence, and the common starting regime is `W2`/`W3`. Two further residuals bound the warrants and
the discounting. A `W1` certifies that a computation reran, not that the computation faithfully captures the
claim: choosing which data represent the claim is a human binding the warrant does not check, so a machine-checked
tier can still sit atop an unverified relevance judgment — the same faithfulness gap an autoformalization firewall
narrows but does not close. And the lineage collapse discounts only the correlation the graph makes explicit as
`DERIVED_FROM`; two sources that are formally independent but share a flawed method, dataset, or paradigm read as
independent corroboration and their support sums, so systemic — as opposed to citational — correlation stays
invisible unless the shared method is itself modelled as a node the sources derive from. A full-venue treatment
would add an axiomatic characterization (which gradual-semantics principles warrant filtration satisfies — the
local monotonicity property of §4 is a first result, with a machine-checked proof of its acyclic case
blueprinted), broader empirics across models and a real corpus, and progress on the cyclic case.

## 8. Conclusion

When nothing is ever settled, a crisp verdict is inert, and a gradual one needs numbers a governance setting
cannot justify. Warrant filtration obtains a graded read from the checkability order alone — a lexicographic
strength profile over a continuous gradual semantics, with a refutation-preserving override, source attribution,
and provenance discounting, at zero free parameters. On adversarial topologies it holds where flat aggregation, a
count heuristic, and a realistic language-model judge do not, and it says so without overclaiming: the model
reasons well once handed the structure the method builds, and the method's contribution is to build and enforce
that structure deterministically. The pieces are old; the assembly, and its freedom from injected priors, are the
point.

## References

Al Anaissy, Delobelle, Vesic and Yun. Impact Measures for Gradual Argumentation Semantics. AAMAS 2025.
Alsinet, Chesñevar, Godo. A level-based approach to computing warranted arguments in possibilistic defeasible
logic programming.
Amgoud, Ben-Naim, Doder, Vesic. Acceptability semantics for weighted argumentation frameworks. IJCAI 2017.
Besnard and Hunter. A logic-based theory of deductive arguments. Artificial Intelligence 2001.
Bondarenko, Dung, Kowalski, Toni. An abstract, argumentation-theoretic approach to default reasoning. AIJ 1997.
Brewka. Preferred subtheories: an extended logical framework for default reasoning. IJCAI 1989.
Dung. On the acceptability of arguments and its fundamental role in nonmonotonic reasoning. AIJ 1995.
Freedman, Rago, Potyka, Toni, et al. Argumentative Large Language Models for explainable and contestable claim
verification. 2024.
Potyka. Continuous dynamical systems for weighted bipolar argumentation. KR 2018.
Rago, Toni, Aurisicchio, Baroni. Discontinuity-free decision support with quantitative argumentation debates.
KR 2016.
Thimm and Kern-Isberner. Stratified labelings for abstract argumentation. 2013.
Yin, Potyka and Toni. Explaining arguments' strength: unveiling the role of attacks and supports via
relation-attribution explanations. IJCAI 2024.
