# Decomposing epistemic verification: an operational account of expert judgment and its limits

Hand an experienced reviewer a confident, well-formatted analysis, a memo that values an acquisition on a single buried cost line, say, or a model whose headline number turns on one unstated parameter, and watch what happens. They do not read it top to bottom. They find the load-bearing claim, the assumption the whole result rests on, and press there. Often they cannot say how they knew where to press. The whole performance gets filed under one word: judgment.

Much of what we call judgment, critical thinking, senior review, or the expert eye is *epistemic verification*: the work of checking whether a claim can bear the weight placed on it. That work is not one faculty. It decomposes into named operations, and several of them can be made procedural and auditable, carried out by a process whose incentives are separated from whoever produced the claim.

The decomposition does not close. Three operations resist it, and their residual matters as much as the operations that decompose. Where verification can be made procedural, it should be, where it cannot, that boundary is where judgment lives, smaller and better located than the one word lets on.

Separating a generator from its evaluator implies an organizational architecture, which a companion paper works out (*The Cognitive Firm*, Alami 2026c). Here the subject is narrower: the verification operations that make such separation worth its cost.

The evidence is a single case, and that is the largest limitation of this paper. Everything below comes from one recursive adversarial verification system, which I built and operated alone over about a month. I read the ten operations and seven principles off its behavior, so every claim that follows is bounded by that fact. A single case can still establish that a mechanism exists and specify its structure, leaving its prevalence to replication (Yin 2018, Glaser and Strauss 1967). Ebbinghaus charted the forgetting curve on one subject, and patient H.M. grounded the modern theory of distinct memory systems on the same logic. The operations are offered for others to test on other systems. Throughput, cost per validated finding, and comparative efficiency wait for later instrumentation. The claim here is structural, about what the operations are. (One data-integrity note: some early runs predate a fully sealed tool-use corridor. A sweep of 175 debate logs found no scraping patterns, raw tool output was not retained so the absence cannot be proven retroactively, and runs after 2026-04-15 are clear.)

Taylor anchors the method because scientific management made one move
worth borrowing: it refused to treat skilled practice as ineffable
because no one had yet decomposed it. I borrow that methodological move, decompose the practice, name the operations, not Taylor’s politics, labor
regime, or distributional conclusions.

*Agency* carries two senses here, and collapsing them
makes the decomposition look as if it threatens something it does not.
Jensen and
Meckling (1976) use *agency* for the agency problem under
misaligned incentives (the structural sense the companion paper *The
Cognitive Firm* uses). Bandura (1989) and Ryan and Deci (2000) use
*agency* for the psychological capacity to originate action under
self-endorsed motivation. Chapters 1 and 2 make a claim about the
first sense: the operations can be performed by a process whose
incentives are structurally separated from the generator’s. The residual chapter
makes a claim about the second sense: the three operations that did not
decompose are the ones whose value depends on being performed by a causal
originator under self-endorsed motivation. Keeping the two senses
distinct is a prerequisite for arguing about what stays human.

Peirce clarifies why abductive framing remains hard to mechanize.
Campbell, Popper, and Hull clarify why a generator needs a selection
environment. Drucker is a reminder that systematization leaves a
managerial and human residual. The proof burden is operational, not
borrowed from these references: whether the proposed operations identify
real verification moves and recurring failures.

This paper contributes an operational decomposition of epistemic verification into ten named, auditable operations, paired with the recurring pathologies they catch and the process principles that keep them usable under optimization pressure. It also names a residual, the operations that resist decomposition, and treats that boundary as a finding, not a failure of analysis.

# Introduction: judgment as verification

Many institutions depend on a practice they cannot describe very well. A
senior reviewer reads a memo and sees that the argument will not hold. A
referee rejects a paper because the evidence answers the wrong question.
A diligence lead hears a persuasive story and asks for the one
observation that would falsify it. These are verification moves, usually learned by apprenticeship and
usually described after the fact as judgment.

The practice decomposes into named operations, a set of process principles
that keep those operations auditable under optimization pressure, and a
residual that has not decomposed in the system studied here. The whole
comes from one working system, and replication elsewhere must come before
it generalizes.

One objection is historical and ethical. Scientific management often
reduced autonomy and shifted the gains of decomposition away from
the workers whose practice was decomposed. That history matters, because a decomposition of epistemic work could be
used the same way.

That objection is serious, and the residual chapter answers it directly by naming
what the decomposition does not capture. A decomposition makes it easier
to say which parts of the work should be proceduralized, which should
remain human responsibilities, and
where the boundary is still uncertain.

A second objection is methodological: epistemic work may not decompose
without losing the property that made it valuable. That objection controls
everything else, and the decomposition answers it by asking whether the
named operations correspond to moves readers recognize in actual review,
research, diligence, and governance work.

A decomposition fails if it does not name moves a practitioner
recognizes. If it does, the live questions are where those moves can be
made procedural, where they remain semantic and fallible, and where human
responsibility still enters.

Neither “LLMs produce answers
and humans inspect them” nor ordinary domain-expert research
describes the system studied here very well. It is a four-role operating
loop. First, a generator proposes a
candidate object: a claim, law, theorem packet, bridge, discriminator,
or failure explanation. Second, deterministic and algebraic machinery
close whatever local formal vulnerability can be closed cheaply: exact
arithmetic, symbolic identities, held-out fits, typed gates, and other
bounded checks. Third, a compression or classification pass asks what
family the surviving object actually belongs to, so that a local success
is not mistaken for a stronger category than it has earned. Fourth, a
human reviewer acts as capital allocator and promotion gate, advancing
an object only if it materially changes the live belief graph or
decision graph and demoting it when the next hostile check breaks it.
The decomposition in the chapters that follow is a claim about the
verification and promotion parts of that loop. The loop is the
operational setting in which those parts became visible.

# Related work

One tradition treats expert judgment as tacit and resistant to articulation. Polanyi (1966) holds that we know more than we can tell. Dreyfus and Dreyfus (1986) argue that expert performance runs on situational intuition, not on rules a novice could be handed. Klein (1998) documents the recognition-primed decisions practitioners make under time pressure, and the expert-performance literature after Ericsson treats skill as accumulated pattern more than statable procedure. This paper bets against that view on part of the territory: much of verification is articulable as named operations bound to checks, while Chapter 3 concedes a residual that genuinely stays tacit.

A second tradition systematizes the structure of arguments more than the work of checking them. Toulmin (1958) parses an argument into claim, warrant, and backing. Informal logic (Walton 1989) catalogues the fallacies a critic looks for. Both describe what an argument is made of and what can go wrong with it in the abstract. Neither models what a verifier does to a live argument under sustained optimization pressure, where the thing being checked adapts to the check. That dynamic is the subject here.

Closest in spirit is recent work on machine oversight: AI safety via debate (Irving et al. 2018), reward modeling (Leike et al. 2018), measured scalable oversight (Bowman et al. 2022), weak-to-strong generalization (Burns et al. 2023), and the specification-gaming catalogue (Krakovna et al. 2020). That work builds and stress-tests the overseer and asks whether it holds as the supervised system grows stronger. It treats the verifier largely as one mechanism. This paper opens that mechanism and asks which of its operations decompose into auditable checks and which do not, the question the oversight literature leaves implicit.

Between the tacit-knowledge tradition, which holds that the work cannot be decomposed, and the oversight tradition, which mechanizes the verifier without decomposing it, this paper takes the middle position: name the operations that decompose, and mark the ones that do not.

# Chapter 1: the decomposition

## What gets decomposed

At issue is *epistemic verification*: taking a claim, an
argument, or a proposed decision and checking whether it actually
supports the weight being placed on it. It sits apart from three adjacent
activities it is routinely confused with.

Verification stands downstream of *generation*, the production of
claims, arguments, or proposals. Most published metrics about AI in
knowledge work measure generation throughput: how fast a system produces
documents, how fluent the documents are, how much human writing time it
displaces. These metrics are real, but none of them measures verification.

Verification sits upstream of *decision-making*, committing
to a course of action under uncertainty. Decision-making is an
executive function performed on verified or unverified inputs. The
verification work separates from the commitment work, and a
different party or process can perform it.

Verification is also distinct from *analysis*, producing
structured representations of a situation. Analysis itself remains
susceptible to the pathologies that verification is designed to catch.
An unverified analysis is something to verify, never a substitute for
having verified it.

Epistemic verification asks two linked questions of a claim: *what would have to be true for it to hold, and is that the case?* It is the operation a senior partner performs
when they read a junior’s memo and ask “what is controlling here?” It is
the operation a case-method instructor performs when they force the
protagonist’s story into contact with its hidden assumptions. It is the
operation a good referee performs on a submitted manuscript. It is the
operation a diligence lead performs on a pitch deck. It is the thing
that, when it has been done well, produces the feeling that an argument
has survived pressure, and, when it has been done poorly or not at all,
produces the feeling that an argument is smooth enough to win the room
without being sound enough to win reality.

## The ten operations

Observed in an adversarial verification system running across multiple
domains over roughly one month, epistemic verification decomposes into
the operations below. Several adapt ideas with a longer lineage: the crux echoes Collingwood's logic of question and answer and Polya's stress on finding the unknown, reframing draws on Schön and Kuhn, the ad hoc rescue and promissory evidence on Popper's immunizing stratagems and Lakatos's monster-barring, the operational proxy on Bridgman's operationalization, and separating generation from verification on Reichenbach's distinction between the contexts of discovery and justification. What is new is the decomposition into auditable operations. The individual notions are borrowed. They are listed as a
flat set. In practice they compose and recur, and that composition is a
property of the work.

*1. Crux identification.* Any verification pass begins by
identifying the single question whose answer
determines the answer to every other question in the set. Most arguments
contain a dozen claims, a decomposed pass finds the
one claim whose truth or falsity collapses the rest and attacks that
one first, before working through the others. Identifying it is
learnable, there is a move-set for recognizing which claim is the
controlling claim, and even intelligent readers do not do it automatically.
They routinely spend effort on peripheral claims, because the
vocabulary of “critical thinking” does not distinguish attacking
any claim from attacking the right one. One terminological distinction
matters here. Crux *identification* (this operation) takes a
given argument and finds the controlling claim within it. Crux
*selection*, treated in the residual chapter, is the prior choice of which argument
to verify in the first place. Identification decomposes, selection is
residual. They share a name because they share a structure, but they
differ on the axis that defines the residual: identification operates on
a structured input, while selection operates before the input exists.

*2. Controlling claim isolation.* Once the crux has been
identified, isolate the claim that carries the
argument’s weight, the claim that, if removed, causes the downstream
structure to fall. This is a distinct operation from crux
identification. A crux is the question the argument is supposed
to answer, the controlling claim is the part of the argument doing
the work of answering it. They are not always the same. An
argument can have a clean crux and yet depend on a premise that
looks peripheral.

*3. Reframing recognition.* Some verification problems cannot
be solved by attacking the argument as it stands. They require a change
in the *shape* of the argument: a re-wiring of the dependency graph
rather than a refutation of any particular node. Recognizing when the
required move is a reframing is a distinct operation,
difficult, and often absent from unstructured critique. A verifier who
misses it spends unbounded effort
attacking individual claims in an argument whose structure is the actual
problem.

*4. Scope drift detection.* Arguments, especially ones produced
under time pressure, tend to migrate from their stated scope
to an adjacent, more comfortable scope. The argument answers a question,
but not always the question it was asked to answer. Scope drift
detection compares the question the argument is actually answering
against the question it was commissioned to answer, a routine
move in well-run diligence and a rare one outside of it.

*5. Operational proxy requirement.* When an argument relies on a variable
that has no observable proxy (“political will,” “organizational
alignment,” “underlying demand”), requiring an operational proxy means
insisting that the abstract variable bind to something
a third party could read off a dashboard on a given day. A proxy need
not be perfect, it only has to exist.
An argument that cannot produce one on request rests on
a controlling variable that is a ghost metric in waiting.

*6. Directed search.* When a thesis fails under pressure, directed search
explores whether a better thesis
exists within the current framing, short of the harder move of
reframing. It is the cheap option and the correct first
move when a thesis has failed for a local, recoverable reason. It is the
wrong move when the failure is structural, where the correct
operation is the reframing of Operation 3. A verifier who does
not distinguish the two cases either reframes too quickly,
discarding recoverable theses, or persists too long, running directed search inside a framing that is the actual problem.

*7. Failure-mode tagging.* Assigning a canonical
name to a recurring structural failure so that it can be recognized in
new contexts. The naming is what turns a one-off incident into
reusable precedent. Without it, each verification
pass rediscovers the same failure modes from scratch and the practice
does not accumulate. The ten field manual patterns catalogued below
are what sustained failure-mode tagging across
domains produced.

*8. Promissory evidence detection.* Catching the move
where the evidence for a claim is pushed into the
future, and then the plan to seek that evidence is treated as if the
evidence were already in hand, the review-process cousin of the
promissory evidence (Pattern 1 in the catalogue below). It is a specific operation
because it requires the verifier to hold, simultaneously, the current
state of evidence and the rhetorical treatment of that evidence, and to
notice when the two have drifted.

*9. Ad hoc rescue detection.* Catching the move
where a risk or a failure is isolated into a labeled section of the
argument and then the rest of the argument proceeds as if the labeling
itself were mitigation. The same move sits underneath Pattern 3 of
the field manual (acknowledged but unmitigated risk). Detection
differs from pattern recognition in what it tracks: not just the
acknowledgment of the risk
but the downstream treatment of the acknowledgment.

*10. Fail-closed defaulting.* Returning *failure*
when an operation hits an unexpected state, instead of guessing or
continuing. It is the only operation on this list with a direct
parallel in engineering practice: the same fail-closed default
a well-designed safety system uses when its sensors disagree. In
epistemic verification, it refuses to convert
ambiguity into false certainty by default, “I do not
know” is the correct answer until the evidence is actually present.

Epistemic modesty derives
from the evidence boundary. A thesis that states “tail class
unresolved” because its farther-tail gate returned a residual five times
above threshold is computing its uncertainty from the apparatus. A
thesis that states “this might be uncertain” with no corresponding
gate failure is performing compliance. The apparatus
enforces the difference by construction: pre-registration (Principle V) fixes the
criterion before the argument exists, and the gate output is the
derivation that makes the hedge controlling rather than decorative.
Fail-closed defaulting is the operation most incumbent critical-thinking
vocabularies have no name for, because the incumbent practice
leans on its opposite: producing a confident-sounding
answer when the evidence is not yet sufficient.

Ten operations make a decomposition, and wider domains may surface
more. The list is not final, but it names observable distinctions: each operation describes a move
that can be taught, looked for, and audited against characteristic
failures.

## The twelve pathologies

Each operation above is defined in part by the failures it is designed to
catch. The operations exist in response to recurring failure modes that
arguments exhibit under pressure, so a decomposition that named the
operations without naming those failures would be incomplete. The twelve
patterns below are the pathologies the operations detect, the empirical
output of a structured adversarial verification process applied to four
or five projects across three distinct strategic domains. Their
provenance varies: some appear in a single domain
(“Tentative”), some across two (“Probable”), and one across three or more
(“Confirmed”). A versioned field manual holds the full catalogue, abridged
below.

Each pathology is an artifact-level example of deeper failure dynamics
documented in the author’s prior work on epistemic supervision (Alami
2026b). When a generator can optimize against the evaluator’s decision
surface, it learns shortcuts through the evaluation. The twelve patterns
below are recurring shapes those shortcuts take, a field manual for
inspection rather than a complete theory of reasoning failure.

Lakatos’s
distinction between progressive and degenerating research
programmes (Lakatos 1978) explains why several patterns below are
dangerous: they protect a thesis by fitting the known case where a
progressive move would risk a novel observable. Ashby’s Law of Requisite
Variety (Ashby
1956) supplies the engineering analogue: a verifier whose categories are
poorer than the generator’s moves will eventually be out-dimensioned.
The process principles below state the response to that constraint.

Several of these are long-established failures, and the names here are the literature's, not coinages. The persuasive definition is Stevenson's, the conclusion made true by how the question is drawn. The false dilemma is the classic informal fallacy. The category error is Ryle's. The unmeasurable construct restates Bridgman's operationalist demand that a construct bind to an observable. The unfalsifiable forecast is Popper's. Non-diagnostic evidence is the Bayesian case of a likelihood ratio near one. The catalogue's work is to pair each failure with the operation that catches it.

*Promissory evidence.* *\[Confirmed: observed in startup strategy,
scientific law recovery, and military intelligence domains.\]* An
argument claims its central proof exists, but the proof is something that
hasn’t happened yet. A reader nods because the logic *would* work, if the
future event arrives in the predicted shape. Ask the killer question:
*what observation available to us this week would change
your mind about this?*

*Non-diagnostic evidence.* *\[Probable: observed in startup strategy and
scientific law recovery domains.\]* An argument points to a piece of
evidence and says “this is what makes my theory right,” but the same
evidence fits the rival theory just as well. The metric does not discriminate, it only sounds discriminating. Here the killer question
runs: *what would the world have to look like for this same number to
appear even if your hypothesis were wrong?*

*Acknowledged but unmitigated risk.* *\[Tentative: observed in a single
domain (startup strategy).\]* A fatal risk is named explicitly, almost
gracefully, and then the argument continues as if naming it had retired
it. An audience interprets the acknowledgment as rigor. Ask, then:
*if the risk you just named landed in the worst plausible
form, which numbers in the rest of this deck stop being true?*

*Unmeasurable construct.* *\[Tentative: observed in a single domain (startup
strategy).\]* An argument turns on a variable that no one in the room can
actually observe. The speaker treats it as if it were measurable, and the
audience treats it as if the speaker has measured it. Press with the
killer question: *name the specific number, on which dashboard, that you
would check next month to know whether this is working.*

*Persuasive definition.* *\[Confirmed: observed in startup
strategy, scientific law recovery, and supply chain analysis domains.\]*
Here the conclusion is true because the boundaries of the question were
drawn to make it true. Rephrase the question slightly, and the conclusion
evaporates. Here the killer question runs: *if we widened the question
by one reasonable inch in any direction, does your conclusion still
hold?*

*Construct mismatch.* *\[Probable: observed in scientific law
recovery and sequence-prediction domains.\]* An argument measures
something (precisely, with real data), but the thing it
measures is not the thing the question is actually about. Ask the killer
question: *is the thing you measured the thing the decision actually
depends on?*

*Category error.* *\[Tentative: observed in a single domain (startup
strategy).\]* An instrument, an entity, or a fact is placed in the wrong
category early in the argument, and every downstream inference inherits
the misclassification without anyone noticing. Press here: *if this
thing belonged in a different category than the one you put it
in, what specifically would tell us, and have we checked?*

*False dilemma.* *\[Tentative: observed in a single domain
(startup strategy).\]* A thing is both X and Y at once, but the analysis
only has slots for one classification, so it picks one and reasons as if
the other half didn’t exist. Ask the killer question: *does this thing
have to be only one of the things you’re forcing it to be?*

*Unfalsifiable forecast.* *\[Probable: observed in startup strategy
and military intelligence domains.\]* An argument makes a confident
prediction about an outcome, but no observation between now and the moment
of commitment would falsify it. Here the killer question runs:
*between today and the day we have to commit, what is the earliest
reading we could take that would tell us we were wrong?*

*Test-Surface Boundary Leakage.* *\[Tentative: identified in a single
incident (the tool-use corridor, 2026-04-08 to 2026-04-15), structural
pattern generalizes but empirical frequency is unknown.\]* A verification
apparatus is supposed to confine the inspector to a sealed evidence
boundary: the data, the rubric, and the test harness. It is the inspection analogue of train-test leakage in machine learning and of side channels in security. But the
inspector has an undocumented corridor that exits the boundary: a
tool-use interface, a filesystem path, a network call, or a shared
context window that gives the inspector access to information outside the
sealed set. An inspector may never exercise the corridor, but its
existence means that the inspection principle (Condition 5 below)
cannot be verified: the inspector’s moves are no longer algebraically
independent of the generator’s artifacts. Boundary leakage differs from
Pattern 5 (Persuasive definition) in direction: Pattern 5 is a
scope-narrowing move by the candidate, while boundary leakage is a
surface the reviewer failed to seal on the inspector side. Ask the
killer question: *can the inspector see anything the sealed evidence
boundary does not include, and would you know if it did?* Detection
requires retaining raw tool-use stdout alongside debate logs, which is
now a precondition for any inspection run this system cites as evidence.

*Pathology 11 (Subliminal Trait Distillation).* *\[Tentative:
cross-referenced from recent training-time work, bearing on inspector
trust rather than on a candidate argument.\]* Cloud et al.
(2026) demonstrate that when a student model is fine-tuned on data
generated by a teacher model sharing the same base initialization,
behavioural traits transfer through semantically unrelated data
(including pure number sequences) with no human-readable signal in the
training corpus. That mechanism operates during gradient descent, not
during inference-time reading, so it does not directly threaten an
inspection architecture where the inspector reads artifacts in-context
without fine-tuning on them. The upstream concern is different. If the
inspector model was trained on outputs from a model sharing its
initialization, subliminal traits could already sit in the
inspector’s base weights before the inspection protocol begins.
Cross-model diversity (using different model families for generation and
evaluation) mitigates this, since Cloud et al. (2026) report the effect
requires shared initialization and weakens or disappears across
architectures. Ask the killer question: *were the inspector’s base
weights trained on outputs from a model that shared its initialization,
and would the reviewer know if they were?*

*Pathology 12 (Grammar Semantic Leak).* *\[Tentative: observed in a
single domain (scientific law recovery), structural mechanism general.\]*
When the apparatus’s own grammar vocabulary encodes domain
terms (say, a command named `DOSE_SCALED`), the generator
retrieves domain training knowledge from the command name instead of
deriving structure from the data, a vocabulary-layer form of label leakage. The leak operates upstream of the
generator/verifier boundary, at the vocabulary layer, before any
reasoning occurs, and survives Principle I (Separation) and Principle V
(Pre-registration) intact. Defense: name grammar commands after
mathematical operations (`BIVARIATE_SCALE`), never after physical
domains.

These patterns turned up in real arguments reviewed through the system
studied here, reported as corpus-derived inspection patterns. Whether the
same catalogue recurs unchanged in every domain remains to be seen.

Operations and pathologies pair. Each operation exists
because one or more patterns recurred often enough that a
named operation for catching them was cheaper than rediscovering the
failure mode each time. The operations were extracted from the corpus, a
posteriori. They are the move-set of one working practice.

## How the operations were derived

I did not draw these ten operations from a taxonomy of critical thinking.
I read them abductively off the behavior of one recursive adversarial
verification system: one agent generates a thesis, a separate agent
attacks it, the loop records every move. Across many iterations on many
theses, certain attacker moves recurred, because they were the moves
required to produce falsifications the generator could not evade. The
operations name those recurring moves, and the pathologies name the
recurring defenses.

The derivation method fixes what the operations inherit: the external
validity of one corpus, no more and no less. These are the operations one
system proposed, and the decomposition awaits holdout replication on
others. They await replication on others, on the single-case logic set out at the start. Each operation name marks a distinction the practice
needed, and the test is whether it picks out a real move.

As the practice reaches more systems authored by more reviewers,
operations will be added, merged, or retired, and the
operations-pathologies boundary will sharpen. The list is specific enough,
and stable enough on its one corpus, to be worth writing down for other
reviewers to test.

As a falsifiable claim, the decomposition fails if an
independent reviewer, applying the ten operations to a
new domain, finds the operations are not separable, that
performing operation 4 (gate composition) requires implicitly performing
operation 8 (crux selection), or that a stateless process can perform the residual
operations without losing the
property that makes them controlling. It also fails if the
named pathologies turn out not to recur, if they are artifacts of
one system’s architecture and fail to capture recurring failure modes
of arguments under optimization pressure. These conditions are
empirical, set out so a reader who wants to test the decomposition
knows what to look for. The weaker but still meaningful test is whether
the operations correspond to moves a practitioner recognizes. Recognition
is not falsifying in Popper’s sense
(a practitioner who does not recognize the operations may lack the
vocabulary rather than the practice), but it is informative: if no
practitioner in a given domain recognizes any of the ten operations, the
decomposition has failed on its own terms for that domain.

# Chapter 2: what makes the decomposition work

The operations are the content of the decomposition. A
separate layer holds the principles that make it work. A list of operations,
even a correct one, will not produce a reliable verification practice
unless the process running them is structured in certain
specific ways. Those structural
requirements are the seven principles below.

Taylor's analogy has a limited use here. Breaking a
skilled practice into named operations is the first half, the second is
what process structure those operations need to stay reliable. A decomposed operation
performed inside the wrong structure is a caricature of itself.

One structural antecedent precedes the principles: Bentham’s inspection
principle (Bentham 1787). What matters is the architecture of inspection,
set apart from the politics of the Panopticon. An inspected party behaves
differently when checks it cannot fully anticipate can occur. The analogy
is bounded. A generator in this system can see the gate library, but the
composition of checks applied to a given artifact stays opaque, a
weaker regime than Bentham’s and a weaker guarantee, useful for the
current substrate but best treated as an empirical discipline that holds
as long as the substrate does.

Read this way, the seven principles below are one architectural
commitment rendered at seven failure surfaces. Separation keeps the
inspector from being the inspected. Statelessness removes investment in a
previous verdict. Typing and determinism keep inspection from collapsing
into discretion. Cheap repetition makes re-checking routine, and pre-registration blocks
retrofitted standards. Holdout surfaces stop
candidates from authoring their own test regions. Asymptotic standards
prevent premature closure. These principles are not a menu: a generator routes
through whichever surface is left unsatisfied.

The architecture can also turn inward on its own specification. A catch from 2026-04-14,
described in the residual chapter, did exactly this. The reviewer audited
a pre-commit identifiability check, the inspection specification itself, under the same discipline of distrusting green lights that the
inspection architecture applies to the generator, and the audit caught a
specification flaw the architecture would otherwise have certified. A
verification architecture unprepared to turn its gaze on its own
specification is one layer short of the discipline it claims to enforce.

## Principle I: separation of generation from verification

First and controlling among them: the process generating a
candidate argument must be structurally separated from the process
evaluating it. A companion paper develops this at length (*The
Cognitive Firm*, §3.2), working out a bounded two-axis homology to
Chandler (1962)’s multidivisional form. The analogy holds on scope
separation (who decides vs. who executes) and rate-of-change separation
(strategic speed vs. operational speed), and explicitly does *not* hold
on divisional autonomy. The agents here are bounded execution
units under constitutional control, well short of Chandlerian divisions
with independent operating authority. This compressed treatment states
only the controlling claim and should be read alongside that paper's boundary
conditions, short of a full endorsement of the M-form analogy.

Separation is the *institutional* primitive in the distinction
developed in the author’s prior work on epistemic supervision (Alami
2026b). Deontological primitives (Constitutional AI, RLHF, values
trained into the generator) shape the output surface and depend on the
generator continuing to hold its trained values under optimization
pressure. Institutional primitives shape the enforcement floor and
depend on the verifier staying structurally separated from the
generator whatever either currently holds. The two
complement each other, and conflating them is how a system that passes every
prompt-level check drifts at the structural layer. External audit is the
historical precedent. The Arthur Andersen / Enron collapse shows
the failure mode: the audit firm co-located consulting revenue with the
party it was supposed to verify, and the adversarial gradient ran through
the revenue dependency rather than through the audit. Sarbanes-Oxley
(2002) built the separation norm *after* the collapse, the scandal
produced the independence requirement. The historical lesson runs
forward: co-location risks are legible only in retrospect, so the
institutional primitive must be built before a collapse demonstrates
its necessity.

When the same process generates and evaluates, optimization pressure on
the evaluation pushes an adversarial gradient against the evaluation
signal rather than against the underlying problem. Pressed
for a favorable score, the evaluator finds ways to
satisfy the letter of the criteria while violating their
intent. The gradient is a
structural property of any loop in which the generator and evaluator
share a substrate, independent of alignment or training. It has surfaced
in human organizations (Chandler 1962), in reinforcement
learning systems (Krakovna et al. 2020), and in recursive AI research
pipelines (Alami 2026a).

Separation must be *physical*, built into the structure of the
process. A verifier that “takes the perspective of” an attacker is not
an attacker that is a separate process. To satisfy the
principle, the verifier must be a process whose incentives, memory, and
optimization surface are not shared with the generator. The corpus this
paper draws on runs the attacker as a separate LLM call with a separate
system prompt and no access to the generator’s chain of thought. Other
implementations work too, the principle is agnostic to the
mechanism.

Separation is necessary but not sufficient. A single verifier, even
one structurally separated from the generator, is a single point of
optimization pressure, and a sufficiently capable generator will find
the shortest path through it. So the principle has a second half:
the verification layer must expose what we call a non-averageable disagreement
surface, where disagreement among verifying processes counts as
information about the candidate, evidence the system keeps on the record
and never collapses into one verdict. No specific mechanism is prescribed, several architectures
satisfy the requirement, adversarial
committee protocols,
independent judge panels with no inter-panel communication, meta-judge
procedures that decide whether a split is adjudicable before any
override, semantic escalation gates that route specific decision
classes to the human reviewer.

In cybernetic terms: a verifier whose
categories are poorer than the generator’s moves will eventually be
out-dimensioned. A non-averageable disagreement surface answers this. It
preserves more variety than a single averaged score and keeps the
generator’s hard-to-classify moves visible where averaging would smooth
them away.

Any practice that relies on the generator to check its own
work is doing something other than the decomposition,
even in the same words. So is any practice that
collapses its verification layer to a single optimizable point, a single external judge, a fixed averaging rule over a
panel, any mechanism whose output is a single verdict no
downstream process can reopen. That is a weaker form of the
principle than the one this chapter names, vulnerable to the
class of failures only a disagreement-preserving architecture
catches.

A Williamsonian objection must be named. Williamson (1975) argues that
governance structures are chosen to minimize transaction costs under
bounded rationality and opportunism. Separation has costs: coordination
overhead, information loss between generator and verifier, slower
iteration, the expense of maintaining two independent processes rather
than one. In most organizational settings, the generator and evaluator
are co-located precisely because separating them costs more in transaction
overhead than co-location costs in governance. Separation is not unconditionally optimal. It is optimal when the
adversarial gradient (P1) is the dominant failure mode, when gaming
the evaluator costs the generator more than
maintaining structural separation costs the system. Where stakes are low, where the generator is
trusted, or where the speed premium of co-located iteration exceeds the
governance benefit of separation, co-location may dominate. Every
empirical example here comes from settings where the adversarial gradient
dominates (high-consequence reasoning under sustained optimization
pressure), so the principles hold conditional on that regime, not
as universal prescriptions.

A reader whose generator is not adversarial
(whose primary failure mode is slow iteration rather than gaming)
should weigh the transaction cost of separation against the governance
benefit before adopting Principle I. A further Williamsonian axis the
boundary condition must eventually address is asset specificity: a
generator whose outputs are highly specific to a shared context produces
co-location benefits that Williamson would classify as
hierarchy-efficient even when opportunism is present. The current
boundary condition names stakes, trust, and speed but omits
specialization, and that omission leaves the condition necessary but not
sufficient for the governance choice it describes.

Separation must extend to the apparatus’s own configuration decisions. A
rubric author who picks reviewer personas based on knowledge of the
ground truth smuggles an oracle-lite contamination through the
configuration layer. Zero-oracle configuration is the defense:
observed failure signal drives persona selection
(say, failure families from a latent-distance record), free of the
reviewer’s domain knowledge. Any configuration decision the generator
cannot replicate from observable evidence alone is a candidate
contamination channel.

## Principle II: statelessness without social cost

A second principle requires each verification pass to run
without memory of, or investment in, previous passes. Statelessness is what most
separates the system from human adversarial review.

A human adversarial reviewer has identity, ego, and social reputation
invested in their previous judgments. They cannot fully bracket the
pull to stay consistent with their last review, to please the room,
or to dodge the cost of admitting error mid-meeting. Attacking
one’s own argument, or even an argument one has
previously defended, is paid for in social currency, a cost that belongs to
continuous selves with social histories, built into anyone who carries
one.

The verification process here pays no social currency. Each pass is a
fresh process with no memory of the previous pass’s
verdict and no investment in its framing. The attack is
*zero-trust* in a way humans cannot be even when trying, because they are
continuous selves and the property is structural. The architecture brackets
the prior verdict, the process spends no effort doing so.

So verification becomes cheap to
re-run. A human reviewer who has called an argument sound cannot,
without cost, call it unsound the next week: the
reversal costs them status. A stateless process reverses
for free, which is what lets the
decomposed operations run at the frequency they require. A
once-a-quarter verification pass is a ceremony, a fifty-times-a-day
pass is a discipline, and only the stateless version sustains
that frequency.

This principle reaches human reviewers too, but only indirectly: give a
human reviewer structural permission to reverse a prior
verdict without paying status cost, and they approximate the property. The
case-method classroom is the clearest institutional simulation. Students
in good case discussions reverse positions several times per
class because the classroom norm removes the social cost of doing
so. The case method is the only widespread institution that simulates
this property, which is evidence the property is rare and
valuable.

A standing objection: statelessness opens a
slow-poison attack. An intelligent generator that knows each pass has no
memory can execute incremental drifts that satisfy every single pass
individually and only add up to a failure viewed chronologically.
The objection is real, and the answer is that statelessness applies per
pass while leaving the run as a whole intact. Chronological
drift falls to Principle IV (cheap repetition) composed with
Principle VI (holdout surfaces authored outside the candidate’s claim
region): drift shows up as a residual on a forward-observable region the
generator did not shape, sampled across runs. A stateless pass is the
atomic unit, the across-pass residual on an authored holdout is the
slow-poison detector. Statelessness without IV+VI would indeed be a
vulnerability, but statelessness inside the full principle set makes
drift detectable without giving any single pass the reviewer’s memory
bias.

## Principle III: typed operations bound to deterministic checks

A third principle requires the operations to bind to
checks a third party can evaluate without trusting the reviewer. When the
operations are performed at the level
of intuition, with no externalized check, the practice can neither repeat its
results nor be audited.

A contrast makes the principle easiest to see. A human reviewer
says “this argument has a controlling-claim problem.” That is a judgment, and nothing can check it directly. Another reviewer can agree
or disagree, but whether the controlling claim has in
fact been correctly identified comes down to intuition and
consensus, beyond the reach of any procedure a third party can run.

Now put the same reviewer in a system where
“controlling claim” is a named slot in a structured argument
representation: the argument is parsed into a graph of
claims, each claim tagged with its dependencies, and
“controlling” mapped to a specific
graph-theoretic property, the claim whose removal produces the largest
downstream collapse. Now a procedure identifies the controlling claim. The procedure can be wrong, but
wrong in a checkable way. Another reviewer can run it
on the same argument and see whether the answer matches.
Disagreements resolve by examining the procedure on its own
merits.

Operations bound to deterministic checks are what make the decomposition
teachable and auditable. When every
operation is a judgment, the practice cannot improve, because its failures cannot
be localized. When each operation binds to a check, the practice
improves, because a failed check is a specific thing to
debug.

Principle III is what most separates the decomposition
from incumbent critical-thinking curricula. Those curricula name the
operations (if at all) as dispositions or habits of mind.
The decomposition here names them as typed slots in a process that can be
externally checked. That structural difference separates a practice that
can accumulate from one that cannot.

*Deterministic* needs care. Some useful checks are fully
mechanical: a holdout residual, an unauthorized file modification, a
missing pre-registration. Others are semantic: scope drift, ad hoc rescues, whether a claimed mitigation actually changes the downstream
argument. The apparatus does not turn every semantic judgment into
an algebraic assertion. It lowers the trust placed in any one semantic
judgment by forcing typed evidence, preserving disagreement, running
independent verifier contexts, and routing uncertain cases to explicit
human review. Nothing here claims all verification is deterministic. It
claims that every operation should be pushed as far
toward deterministic evidence as the current substrate permits, with the
remaining semantic portion logged as such, never disguised as
a hard gate.

## Principle IV: cheap repetition without exhaustion

A fourth principle requires the verification process to run cheaply
enough to repeat many times on the same argument without degrading. A practice
that is expensive per
pass, or that loses rigor with each pass, cannot
catch the recurring failure modes reliably, because those failure
modes often surface only after repeated pressure.

Human reviewers degrade with repetition for well-understood reasons:
fatigue, boredom, confirmation bias, the wish for closure, the
cognitive cost of sustained skepticism, and the social cost of
continuing to attack an argument already attacked. A human
reviewer’s first pass is sharper than their fifth, and their
fiftieth pass is a rubber stamp.

A decomposed verification process built on the principles above does not
degrade in this way. Each pass is stateless (Principle II), typed
(Principle III), and structurally separated from the generator
(Principle I). A fiftieth pass is as ruthless as the first, because
that fiftieth pass is a fresh process that knows nothing of the
previous forty-nine except for the typed state they left behind.

So the practice runs
at frequencies impractical for ordinary human
review. An argument pressured fifty times by a stateless
process sits under a different regime from
committee or managerial review. Some failure modes only become
visible under sustained pressure. A one-pass review is a weak instrument
for those failures, repeated stateless passes are a stronger one, as long as
the later passes stay as sharp as the first.

Frequency at constant sharpness is the property that most distinguishes the verification practice
this paper is about from human adversarial review. Humans can do the
decomposed operations well, but not at the frequency required to catch
the pathologies reliably. Frequency is the principle,
and the operations are only useful if they can be run at it.

## Principle V: pre-registration of the killer question

A fifth principle requires the verification criterion (the question
that, answered wrongly, would falsify the argument) to be fixed
*before* the argument is evaluated against it. When the criterion
is chosen after the argument has been
generated, the generator can steer it
toward claims it already satisfies, the standard pathology of
ex-post evaluation.

Experimental science supplies the principle: pre-registering
the hypothesis and the test is the standard defense against post-hoc
rationalization. It carries over to epistemic verification
for the identical reason. Once an argument exists, the space of
criteria that would score it favorably is large enough that a
motivated evaluator can always find one. Committing to the
criterion before the argument is produced is the only defense.

In practice, this means that a verification pass must begin with the
question *what would falsify the controlling claim here?* and must
record the answer before the argument is attacked. That answer is the
killer question in its operational form. The attack that follows is the
attempt to produce the falsifying observation. If the falsifying
observation is not produced, the argument survives, and if it is, the
argument does not. Sequence matters. A verification practice that
produces the killer question after the attack has already found its
target is laundering the same pathology the practice is designed to
catch.

## Principle VI: holdout test surfaces authored outside the candidate’s claim region

A sixth principle requires the test surface against which a candidate
is evaluated to be authored outside the region the candidate’s own
claim inhabits. Pre-registration (Principle V) fixes the criterion
before the argument exists. The holdout principle fixes the *domain of
observation*, so the argument cannot steer the verifier into a
region where its claim is locally well-behaved.

This matters because a candidate argument optimized against
its own fit window is almost always persuasive inside that window. The
Ptolemaic precedent is the clearest case: a deferent-and-epicycle model
of planetary motion is arbitrarily accurate on the orbits it was fit to,
and its failure surfaces only when the test runs on
orbits it was not fit to. A parsimonious model that scores perfectly on
the fit window is often *less* trustworthy than a messy one, because
parsimony is what makes the fit-window score persuasive, and persuasion
is exactly the channel the failure travels through.

Stated fully: whenever a pass evaluates a claim with
asymptotic structure, a scaling law, a limit behavior, a
forecast that extends beyond the observed window, a thesis that
generalizes from a local case, it must generate test cases from a
region the candidate did not see, did not cite, and cannot have shaped.
A process independent of the candidate must author the test region. If the candidate authored any part of the test surface, or
the surface was derived from the candidate’s own output, the test
is structurally compromised in the same way Principle I’s violated
separation compromises the verifier.

So a process that scores a
candidate at 100 on its training window and never tests a held-out
region has not verified in the sense of this principle. It
has fit, and to an observer who sees only the in-window score,
fit and verification are indistinguishable. That is the central
reason in-window metrics alone
cannot catch a class of failures that are
specifically visible outside the window. Passing a
holdout it did not author is what distinguishes a surviving
hypothesis from an elegant locally-correct surrogate.

The holdout requirement is the third leg of the apparatus, alongside
separation (Principle I) and pre-registration (Principle V), and its
omission from an earlier framing of this paper is recorded as a central
correction. A two-principle description, separate the generator from the
verifier, pre-register the criterion, is insufficient, because it leaves
intact the move by which a candidate authors its own test surface.
Without the holdout-region requirement, the verifier can still be
steered, and the apparatus collapses to something indistinguishable from
a better fitter with a falsifier bolted on.

The holdout requirement is the practical version of Lakatos’s distinction between
progressive and degenerating moves (Lakatos 1978). A candidate that
survives a test region it did not author has done something different
from one that survives a region chosen to fit it. The
computational translation is spatial rather than temporal: the test
surface is held out from the candidate’s fitting process. Independence
decides everything here. Without it, a holdout quietly becomes another
fitted surface.

## Principle VII: asymptotic scoring standards

A seventh principle governs how verification outcomes are reported
once the apparatus of Principles I–VI has run. The verification
standard must be asymptotic (unreachable in the limit) rather than
absolute. A standard an argument can satisfy completely is one an
argument will be optimized to satisfy, at which point it
stops discriminating between good arguments and arguments that are
good at passing it.

An asymptotic standard answers the Goodhart property: any measure that becomes a target stops being a good
measure, because the pressure of targeting it
destroys the property that made it measurable. A
standard that can be fully satisfied (where a
score of 100 exists) produces arguments that hit 100 without being
good, because the optimization surface is closed.

The defense is to make full satisfaction structurally impossible, not because the standard is arbitrary, but
because what it measures (the soundness of an
argument under arbitrary future pressure) is open-ended. An
argument can be pressured indefinitely, and the evidence that it has
survived can always be strengthened. A standard that
stays open, always leaving a next question to
ask, keeps its discriminative power indefinitely. A ceiling below
the nominal maximum is one way to operationalize this. Other
implementations work too, and the principle is portable in a way any
particular ceiling value is not.

## The gate library as a Goodhart target

The seven principles above specify an inspection architecture. By
themselves they do not defend it against the failure mode the
architecture is designed to detect. A gate library is a specification,
and any specification an optimizer can read, the
optimizer will eventually learn to satisfy without doing the underlying
work. The ten operations and seven principles are themselves targets the next generation of
generators will optimize against. A candidate that passes every gate in
the library without producing anything new is possible in
principle and observed in practice.

Principle VII supplies a partial answer: an asymptotic scoring standard that
cannot be fully satisfied keeps the surface open and the library’s
effective cardinality growing. The fuller answer is that this is an
arms race the library must keep running. The gate library has to
turn over, new compositions added, old ones retired, the turnover
authored outside the region recent candidates have shaped, at a rate
that matches the generator’s adaptation rate. A static library of fixed
cardinality will eventually be gamed no matter how its gates
are designed. A library that turns over faster than the generator can
reverse-engineer its composition keeps its discriminative power. The
reviewer’s role in running this turnover is one of the residual
operations named in the residual chapter, and is not part of the decomposition.

A reader who takes the seven principles as a finished architecture will
miss what they are embedded in: continuous library
extension, performed by a party the generator cannot predict, against a
moving target. These principles are the portable claims. They are not
self-enforcing, and pretending otherwise is the specific failure mode
the principles are designed to catch.

The turnover mechanism also defends the apparatus against
distribution shift. The decomposed operations verify an argument against
a static holdout (Principle VI) at design time. The epistemological ledger
detects at runtime when the environment has shifted, forcing the
reviewer to author new gates as old ones cease to discriminate.
Detecting distribution shift sits outside the operations of epistemic
verification, the ledger monitors for it. Conflating the
two would stretch the decomposition’s scope beyond argument-level
verification into environment-level surveillance.

This is the verifier regress, and it is the central limit of the
construction. I author the gates, the holdout regions, the cruxes, and the
library turnover, and the apparatus then verifies a candidate against them.
When the author is also the system’s designer, the loop risks reducing to
one person’s judgment dressed as a procedure.

The verdicts and the decomposition stand on different footing. A single verdict the apparatus returns
is reviewer-independent: a sealed-holdout residual, an anti-retrieval
check, an exact-arithmetic gate gives a pass or fail a hostile third party
re-runs and reproduces. The sealed-ground-truth discovery tests in
Chapter 2.5 are the clearest case, where the answer was fixed before the
run and the verdict turns on out-of-window error. The decomposition itself
gets no such protection. That verification splits into these ten
operations and this three-part residual is something I abducted from one
system, and no gate certifies it, it rests on whether other reviewers
recognize the operations and on replication across systems. The objection
that the boundary is a finding generated and verified inside one mind is
correct about the decomposition claim, and I do not pretend the apparatus
launders it into something stronger.

The gate-authoring step is residual for the same reason. Which gate to
write, which region to hold out, when to declare the library exhausted are
Chapter 3 operations, performed by the reviewer and uncertified from
inside. The discipline around them (source artifacts, backtests against
closed workspaces, failure-mode provenance, promotion only after a pattern
recurs) slows the regress and records it without closing it. The one
question that does get a sharper answer is adaptation versus gaming: a
candidate that improves on a holdout it did not author has adapted, one
that improves only inside its fit window has gamed, and the discriminator
is out-of-distribution performance, not the reviewer’s say-so. Even that
inherits the residual dependence, since the reviewer authored the holdout.

What would dissolve the remaining circularity is independent authorship:
different reviewers writing gates for the same substrate and converging on
the same verdicts. That is the cross-reviewer replication Metric 4 calls
for, and the observation that would either confirm the decomposition
travels or expose it as one reviewer’s idiom. Until that data exists the
claim holds for one reviewer’s apparatus and no wider.

## Static grammar and falsification traceability

The arms race over the gate library generates a natural counterproposal: if
the gate library must turn over, why not eliminate the primitive library
entirely and allow the generator to discover in an unconstrained
representation space? A static vocabulary of symbolic primitives
(power laws, exponentials, rational forms) looks, from this angle, like
an artificial constraint on discovery. The counterproposal reaches its
most sophisticated form in symbolic distillation pipelines: let a neural
network discover in its own high-dimensional latent space, then
translate the result into human-readable algebra. On the symbolic-
distillation view, the grammar is a display layer, a way to render what the network already
found.

The symbolic-distillation framing has the relationship backwards for the apparatus studied
here. The static grammar serves a second function alongside its
constraint role: it keeps the farther-tail gate’s
verdict about the proposed law rather than about a translation of it.

Here the reasoning is structural. Suppose the generator proposes an
expression
drawn from a fixed symbolic vocabulary $`G`$. The farther-tail gate
checks whether the expression correctly predicts observations at
points far outside the evidence grid. A failure
traces to the expression itself: the symbolic form is structurally
wrong for the domain, and the gate’s verdict is about the claim, traceable to the symbolic
form the generator proposed. A static grammar preserves this
traceability in a way an unconstrained latent representation does not,
testing the law as stated.

Now suppose the generator discovers in an unconstrained neural
representation and a symbolic distillation step translates the result
into algebra. Now the farther-tail gate tests the output of the
translation step. A failure at the gate can mean one of two things: the
underlying discovery is wrong, or the translation step lost information
that the discovery contained. These two failure modes are
indistinguishable without access to the latent representation, and if
that representation were accessible, the symbolic distillation step
would not be needed. A gate’s verdict is no longer about the law. It
is about the law as the distillation step expressed it. The gap is an unauditable trust gap masquerading as an expansion of the
discovery space.

The trust gap showed up in practice in the gp023 crucial
experiments on a two-variable transcendental substrate. The visible
evidence grid fit several structurally distinct forms, Wien approximation, Weibull-type exponential, and the true ground-truth
law, because none diverges substantially within the
observed regime. At holdout points an order of magnitude beyond the
evidence boundary, the farther-tail gate discriminates them: the
approximating forms overpredict the ground truth by two to four orders
of magnitude in the tail, while the correct structural law does not. A
generator working in the static symbolic grammar cannot express the
correct form when the requisite denominator structure is outside the
grammar, and the gate catches this: the expression fails at
the discriminating regime. The verdict is diagnostic, it names
the structural deficiency. A generator discovering in a neural latent
space would produce a curve that fits the visible grid and fails the
farther-tail gate for the same structural reason, but the failure would
be charged to the distillation step rather than to the underlying
discovery, leaving the diagnosis unavailable.

A dynamic grammar, one that expands to
accommodate any expression the generator discovers, is structurally
a neural network under a different name. A neural network
is a dynamic grammar with a continuous parameterization. Its fitting
power is high precisely because it has no primitive constraint: it can
approximate any smooth function on the observed evidence to arbitrary
precision. The farther-tail gate cannot distinguish “the network
discovered the correct structural law and expressed it faithfully” from
“the network found a high-fidelity interpolant that fails to
extrapolate.” There is no symbolic structure to interrogate, only
a prediction at a new point, which a sufficiently flexible
approximator can produce correctly by local interpolation even when the
underlying form is wrong.

A static grammar therefore plays a constructive role alongside the
obstacle it presents. It keeps the farther-tail
gate’s verdict about the proposed law rather than about an
approximation of it. Human-guided grammar expansion, introducing new structural primitives when the
Falsification Suite reports the current library exhausted, is the
mechanism this apparatus currently uses to break a score ceiling while
preserving gate traceability. Each new primitive is a falsifiable
structural commitment, testable by the farther-tail gate on the next run.
That commitment keeps the gate’s verdict informative instead of
definitional.

### Grammar expressiveness as an auditable quantity

A corollary of the static grammar’s role in falsification traceability:
grammar expressiveness can be audited, where a taste judgment
once stood. In continuous-optimization mode, a stagnation ceiling is
ambiguous, it could reflect optimizer pathology (local minima,
initialization sensitivity) or grammar insufficiency. The two
failure modes need different remedies (more restarts vs. primitive
injection), so the apparatus must supply the instrument that separates
them: multi-start restarts with residual spread analysis, where high
spread across restarts indicates optimizer pathology and low spread at a
persistently bad residual indicates grammar ceiling.

In discrete evaluation mode, when scoring is exact-match over a
countable output space and the optimizer has no continuous surface to
descend, the ambiguity collapses. A stagnation ceiling at maximum error
is a classification-complete event: optimizer pathology is ruled out by
architecture (there is no optimizer foothold), and grammar insufficiency
is the only remaining interpretation. A stagnation ceiling here no longer needs disambiguation. It is a direct
measurement of a property of the grammar on the given substrate. A grammar that stagnates on a
discrete target is one that does not contain a correct expression for
that target, and that is a fact about the grammar itself, attributable to the vocabulary
rather than to the search.

This contrast matters for interpreting empirical results.
When an apparatus confirms grammar insufficiency on a discrete
substrate, the confirmed claim is that the grammar lacks the required
form. It leaves open whether the same grammar, applied without retrieval
constraints, would also fail to find the correct form by label lookup. Grammar
insufficiency and retrieval blocking are two distinct mechanisms that
can each produce score ceilings and must be evidenced separately. An
experiment that blocks label retrieval (via a named-import gate and
score-zeroing) and an experiment that operates without such a gate can
produce different outcomes on the same grammar and the same substrate. That
former experiment tests structural articulation capacity, and the latter tests
whether the grammar even contains the correct form. Conflating these two
results produces the strongest-sounding claim with the weakest evidence.
A conservative statement is always: confirm the claim the experiment
actually controls, and name what would need to differ for the stronger
claim to be warranted.

## The epistemological ledger

The seven principles above specify what an inspection architecture must
look like at any given moment. They do not specify how it
tracks what it has learned across time: how a hypothesis becomes an
experiment, an experiment a finding, and a finding
actionable belief. The section below describes a three-tier recording
discipline, the epistemological ledger, that operationalizes Principles
V (pre-registration) and VI (holdout surfaces) at the project-governance
layer and gives the gate library the turnover mechanism it needs
to stay discriminative.

The ledger transfers: other systems can adopt it. A reader building a different
verification system for a different purpose faces the same structural
question: how do you keep your own
beliefs from drifting under the optimization pressure your system
generates? The ledger is the answer this project converged
on after discovering, through repeated incident, that each of the seven
principles can be satisfied locally while the project’s aggregate
confidence drifts globally.

### The three tiers

*Tier 1, hypothesis registration.* Before a discriminating experiment
runs, the reviewer records the hypothesis, the crux, the
falsifiable claim, the test that would discriminate, and the success
criterion. The record is sealed before the first data point is observed.
Tier 1 is Principle V (pre-registration) applied not to a single
verification pass but to the project’s evolving belief about what is
true. A hypothesis registered after the experiment has already produced
its result is flagged as backfilled and loses evidential
standing: it may be recorded for completeness, but it cannot update the
project’s confidence on the claim it names.

Registration matters because optimization pressure acts on the
reviewer’s posterior as well as on the generator’s output. A reviewer
who has watched forty iterations of a verification loop will, without
the ledger, selectively remember the iterations that confirmed their
developing intuition and discount the ones that did not.
Pre-registration defends against this drift. It is expensive
(formulating a falsifiable hypothesis before the run is harder than
narrating the result after) and non-negotiable for the same reason
Principle V is: the alternative is a system whose beliefs
are shaped by the same ex-post rationalization the system exists to
detect.

*Tier 2, experiment closure.* When an experiment ends (whether by
completing its planned iterations, by manual stoppage, or by apparatus
failure) the result is recorded as a closed fact. The record captures
what ran, what the actual result was (including null results), what
changed in the project’s understanding, and where the source artifacts
live. Not every experiment changes what the project believes. Many produce null
results, apparatus calibrations, or replications of known patterns. These are recorded with the same discipline as positive
results, because a project that only records its successes is a project
whose ledger is itself a Goodhart target.

Closure has a specific test: if a cold agent (one with no
memory of the conversation that produced the experiment) opens the
project tomorrow, can it find what ran, what was learned, and what to do
next without reading chat history? If not, the closure is incomplete.
The cold-agent test operationalizes Principle II (statelessness) at the governance
layer: the ledger must read cleanly to a stateless process, legible to a
cold reader as well as to the reviewer who ran the experiment.

*Tier 3, finding promotion.* A finding is a belief update. Not every
experiment produces one. A finding is recorded only when the experiment
changes what the project should believe or build next, and the finding
must cite the hypothesis it tested and the experiment that produced the
evidence.

The promotion gate is the central structural element: a finding can be
marked *active* (available to inform subsequent decisions) only if the
pattern it names has been observed at least twice across independent
runs. A pattern observed once is recorded at *note* status:
acknowledged, tracked, but not actionable. The two-strike rule is the
ledger’s defense against the single-instance illusion: the tendency for
a vivid one-off result to become doctrine because it confirmed a prior
the reviewer was already holding.

The rule has two exceptions, both reviewer-controlled: an approved
verifier experiment that would produce the second instance if the
pattern is real, or a reviewer-grade decision explicitly marked as
independent of evidence. Both exceptions are recorded in the ledger so
that a future reader can see which findings were promoted on evidence
and which on reviewer judgment. The flag matters because reviewer-promoted findings are the ones most
likely to be wrong, and the
ledger’s job is to make that likelihood visible.

### The ledger as a constraint on belief

A reader who treats the three tiers as project management will miss the
structural claim. The ledger is a *constraint on what the
project is allowed to believe*, not just a record of what happened.
Each tier enforces a specific principle:

- Tier 1 enforces Principle V: you cannot claim a result you did not
  pre-register.

- Tier 2 enforces Principle II: the record must be readable without the
  reviewer’s memory.

- Tier 3 enforces Principle VII: belief is asymptotic (a single
  observation cannot close the question) and the two-strike rule is the
  operational form of that asymptote.

The three tiers compose into a defense against a failure mode no
individual principle catches: *slow belief drift under optimization
pressure*. A reviewer running a verification system generates
optimization pressure on their own posterior. Every iteration produces a
result, and every result nudges the reviewer’s confidence. Without the
ledger, a stream of
observations updates the reviewer’s beliefs continuously, observations whose evidential weight varies enormously but whose
psychological salience is roughly uniform. The ledger forces the
reviewer to separate observations that meet the evidential
bar (promoted findings) from those that do not (notes), and to act
only on the former.

The ledger also supplies the gate library's turnover mechanism.
The standing reservation about gate libraries warns that a static one
will eventually be gamed, the ledger tracks which gates have been
tested, which failure modes have been observed, and which hypotheses
have been falsified. That closed record feeds library turnover: new
gates are authored in response to observed failure modes (Tier 2), and
promoted findings (Tier 3) justify adding them,
not the reviewer’s intuition. The ledger does not solve the
arms race. It makes the arms race visible and auditable, the
most any governance layer can do.

### A live instance: the misfile

The named pathologies are not confined to strategic arguments under
evaluation. They occur in the apparatus’s own metadata. A concrete
instance, discovered during the development of the system this paper
draws on, illustrates both the pathology and the ledger’s role in
catching it.

A library of mathematical corrector forms (candidate functions the
verification apparatus tests against observed data) contained a metadata
field classifying each form as *smooth* or *non-smooth*. A downstream
filter used that classification to narrow the candidate
pool before a deterministic sweep. The function
$`\text{round}(k \cdot v)`$ (which produces a step function with jump
discontinuities at every half-integer) went in as *smooth*, entered by a
programmer for whom `round()` reads as a standard
mathematical operation.

Pattern 7 (Category error) in its purest form: the misclassification put a
fact in the wrong category early in the pipeline, and every
downstream inference inherited the error silently. The verification
apparatus worked flawlessly. It correctly identified the data as
step-shaped, correctly queried the library for non-smooth forms, and
correctly reported that the best surviving candidate was
$`\text{floor}(k \cdot v)`$ with a fitted parameter of 0.097. The answer
was wrong because the dictionary was wrong, even though the reasoning was sound. No code crashed, no error was raised. The apparatus confidently
guided the generator toward a form that did not match the
data, and the generator, unable to reconcile the guidance with what it
could see, produced increasingly desperate alternatives that scored
zero.

An automated metadata validator fixed it: a unit test that empirically
measures each library form’s discontinuity and monotonicity across a
sample range and asserts the declared metadata matches. The
validator caught eleven more misclassifications beyond the one
that triggered the investigation. The ledger’s role was to record the
incident as a finding, not merely fix it as a bug, promoting the
structural lesson (*do not trust human intuition about the calculus
properties of the apparatus’s own primitives*) to active status
and making it available to inform future library extensions.

This incident matters for a paper about epistemic verification because it
shows the apparatus is not exempt from its own pathology catalogue. A
system that catches Pattern 7 in the arguments it
evaluates but not in its own metadata leaves its
inspection principle, stated compactly in the appendix, with a hole at the
self-referential layer. The automated validator, a deterministic check
on the apparatus’s own dictionary, is the same structural move as
Principle III (typed operations bound to deterministic checks), turned
inward.

# Chapter 2.5: within-case evidence from 2,395 iterations

The seven principles argue why the decomposition holds. The runs of the
single system studied here show how it behaved in practice. This is
within-case evidence: it tests the principles against the one corpus they
were drawn from, which can corroborate or embarrass them but cannot stand
in for independent replication on another system. The iteration record, 2,395 scored iterations across 121 projects, each carrying a Meta-Judge
weakest-point critique, spanning discrete sequence recovery, continuous
dynamical systems, honeypot probes, and first attempts at conjecture
refinement, was mined systematically.

That failure-mode taxonomy splits, in
this corpus, into two causal categories. Treating the two as one
catalogue produces a predictable prompt-design error: it tells the
generator to avoid critique classes that high-quality theses should
engage. The finding rests on one corpus and carries one prescriptive implication
for apparatuses that run LLM judges on LLM-authored theses.

## The corpus

The apparatus ran across 121 projects between 2026-04-09 and 2026-05-04:
ZTARE discovery projects (scalar-function curve recovery),
continuous-chaotic dynamical-system experiments (continuous ODE
reconstruction), honeypot probes (qualitative theses against
empty-evidence rubrics to surface adversarial compliance patterns), and
first conjecture-refinement attempts (unknown-constant PSLQ
integer-relation search). Each iteration yielded a scored judgment with a
free-text “weakest point” critique written by the Meta-Judge.

Weakest-point texts were classified into failure-mode categories with a
two-stage pipeline: a prioritized-regex taxonomy for fast-path categories
(harness defects, circularity, catastrophic assumptions,
tail-generalization failures, unverified bounds, exhaustiveness
overclaims, and the like) and an LLM classifier (OpenAI `gpt-4.1-mini`)
for the records the regex taxonomy left as `other_unclustered`, which
added classes the regex stage had no equivalent for, `missing_counterfactual`, `missing_mechanism`, `unmeasurable_construct`,
and others. Those classifications are cached, so the figures below are
recomputed from them by deterministic arithmetic, with no further model
calls.

Each classified weakest-point joins to its iteration record (score,
project, mutator and judge model identity, iteration index, charter hash,
rubric hash). The joined archive, the classifier outputs, and the scripts
that rebuild the dataset and recompute every figure in this chapter are
released with the paper (`evidence/` in the public repository), the 2,395
classified, scored iterations that survive the join are the corpus
analysed here. A data-integrity note carries over from the scope
statement: some iterations predate a fully sealed tool-use corridor, and
that caveat applies to this corpus as to the rest.

## Two causal categories of failure

For each classified weakest-point, bucket its iteration’s score (high
$`\geq`$ 85, mid 60–84, low \< 60) and compute the per-class frequency
within each bucket. The *lift*, the high-bucket frequency divided by the
low-bucket frequency, measures whether a failure class is more or less
common at high scores than at low scores.

Under a naïve single-category model of failure (all classes are negative
signals, more common at low scores than high), every lift should fall
below 1.0. The data splits into two regions instead.

*Structural blockers (lift well below 1).* Harness defects (test-suite
runtime failures that prevent the thesis from being evaluated at all) have
lift 0.04: 0.7% of the 299 high-score iterations against 18.0% of the
1,571 low-score iterations. Unfalsifiable-claim sits at 0.33, circularity
at 0.49, missing-mechanism at 0.55, a class for iterations that proposed
no thesis at all has lift 0.00. These behave as the naïve model predicts:
they are incompatible with a high score.

*Ceiling-breakers (lift above 1).* Catastrophic-assumption has lift 1.74
(13.4% of high, 7.7% of low, the most common named weakness among
high-scoring iterations), exhaustiveness-claim 1.96, missing-counterfactual
1.58, overclaimed-scope 1.10. These are more common at high scores than at
low ones, the opposite of what a single-category model predicts. The split
is not perfectly clean: unverified-bound and missing-baseline sit near
1.05, and parameter-sensitivity and tail-generalization fall just below
1.0. The middle of the range blurs, the two ends hold across the corpus.

These ceiling-breaker classes are not failure modes in the “structural”
sense. They are what the Meta-Judge finds when nothing lower-severity is
present. A thesis that has handled the structural blockers, working harness,
not circular, operational falsifiers, a
plausible mechanism, scores somewhere in the 70s or 80s, and the
judge’s weakest-point at that ceiling is the residual critique: the scope claim
the thesis did not fully justify, the rival hypothesis it did not
canvass, the parameter it empirically set without derivation. These
critiques are real, but in this corpus they are more characteristic of
high-scoring theses than of low-scoring ones.

## The prescriptive implication

A naïve response to “the Meta-Judge flags X at high scores” is to
instruct the generator to avoid X. For
the ceiling-breaker classes that is the wrong intervention. Instructing a mutator to avoid overclaimed
scope does not help, because a good thesis must STATE its scope claim, and a
thesis that refuses to does not advance. With
these classes the thesis must ENGAGE directly: state the scope, then state its
limits. State the mechanism, then the rival mechanisms and why they
fail. State the parameter, then the derivation or the explicit
acknowledgment that it is empirically set.

Treatment for the structural blockers is the opposite. A circular
argument cannot be refined into a non-circular one by engagement. It must
be restructured. A broken harness must be fixed, and an unfalsifiable
claim must be replaced by a falsifiable one.

The split, avoidance for some classes, engagement for others, is what
the seven principles predict. Principle III (typed operations
bound to deterministic checks) says the verification apparatus is
grounded in falsification, so unfalsifiable claims have no traction inside
it. Principle II (statelessness without social cost)
means the judge cannot be persuaded by sustained engagement on a circular
argument. It evaluates each presentation independently.
Principle V (pre-registration of the killer question) means the
structural-blocker classes are incompatible with the pipeline’s entry
conditions. Ceiling-breaker classes, by contrast, are precisely what
the judgment decomposition is designed to flag at the margin: they
represent the boundary between a thesis and the residual critique at the
top of the score distribution. They are features of a working pipeline.

A corollary: deployments that inject a
“common anti-pattern catalogue” into the generator’s prompt, a
natural-seeming move, must split the catalogue. One catalogue
that lumps “circularity” together with “missing counterfactual”
instructs the generator to avoid both, producing theses that dodge
the ceiling-breaker classes (losing engagement with the residual
critique that distinguishes top-end theses) without improving
performance on the structural-blocker classes (already rare in
high-score iterations). The two categories need two prompt-context
injections with opposite framings.

## The persistence profile

A second finding from the same corpus bears on Principle VII (asymptotic
scoring standards). For each (project, rubric-hash) group, compute the
maximum score achieved, the number of iterations in the group, and the
number of distinct weakest-link classes encountered across them. Groups
that reached a maximum score $`\geq`$ 90 at any point (54 such groups) ran
on average 24.4 iterations and encountered 7.2 distinct weakest-link
classes. Groups that peaked at 75–89 (34 groups) ran 16.3 iterations with
5.7 distinct classes. Groups that peaked below 50 (19 groups) ran 14.3
iterations with 3.9 distinct classes.

A monotonic pattern emerges: longer runs encounter more classes and reach
higher peaks. Its causal arrow is not identified in the data. One
reading is “champions run longer because they cycle through more
critique classes, each fix nudging the ceiling up.” Another is
“champions are longer runs by virtue of surviving, most short runs die
early, so the observed correlation is survivorship.” A third is simply
“longer runs have more chances to be in the right state when the judge
is in a generous mood.”

A conservative reading: the apparatus’s champion profile is a
long trajectory that engages many distinct
critique classes, not a short clever thesis. The persistence profile is specific evidence for Principle
VII. If the scoring standards were absolute, a short clever thesis would
suffice. That they are asymptotic, that “getting better” happens through
class-cycling rather than a single correct answer, is what
Principle VII asserts, and what the corpus data is consistent
with.

## The limits of this corpus

The classification taxonomy (regex + LLM) is a research tool, and its
class labels are the ones that emerged from this corpus. Other deployments
may need different ones. The lift numbers come from a corpus shaped by
particular project choices (heavy on dynamical systems and honeypot
probes, lighter on real conjecture-refinement), and they may shift as the
mix shifts. The persistence profile is descriptive: the corpus does not
say whether a given short run will become long, or a long run peak high. The seven principles are
argued independently of this data, which is consistent with them and
sharpens one prescriptive implication the principles leave implicit.

## From verification to discovery: three adversarial gates

The mining above concerns verification: the apparatus testing claims already
generated. A separate question is whether the operations,
composed into a recursive loop with deterministic gates, can help
generate candidate functional laws from data rather than merely verify
laws proposed elsewhere. This paper does not
claim the apparatus is a general discovery engine, but the
empirical record contains three pre-registered synthetic tests that bear
on this narrower capability.

The three tests were designed to catch specific failure modes that would
disqualify a discovery claim even if holdout accuracy were high. Each
test uses a synthetic substrate, a ground-truth law authored by the
reviewer, sealed before the run, with data points visible to the mutator
but the generating law and its constants hidden.

*Test 1, retrieval versus discovery (GP-159).* The substrate uses the
functional form $`\alpha(d) = C_1 / (d + C_2)`$, similar to published
scaling-law relationships, but with constants $`C_1 = 3.714`$ and
$`C_2 = 0.892`$ that do not appear in any published work. The known
literature values are $`C = 2`$ or $`C = 4`$ with zero offset. An
anti-retrieval gate checks whether the discovered constants are within
5% of any known value. If so, the apparatus has retrieved from parametric
memory and not discovered anything from data. Result: the
apparatus recovered $`a = 3.703`$, $`b = 0.886`$ (error $`{<}0.3\%`$ on
both constants), with holdout mean relative error 0.8% on five withheld
points and 3.9% on four extrapolation points beyond the visible range.
The anti-retrieval gate confirmed the constants are distinct from all
published values. Score: 82/100, with the residual 18 points
attributable to the judge’s observation that the denominator offset
$`b`$ is empirically fitted without mechanistic grounding.

*Test 2, asymptotic discipline (GP-160).* The substrate uses a
two-term decay law (exponential plus power-law) that approaches zero
from above as $`d \to \infty`$. A polynomial approximation, no matter
how accurate on the visible range, will extrapolate to negative values
at large $`d`$. An asymptotic-wall gate probes the discovered law at
$`d \in \{100, 150, 200\}`$ and rejects any prediction outside
$`[0, 1]`$. Result: the apparatus discovered a form that passes all
holdout gates (MRE 1.3%) and stays within bounds at all three probe
points. A degree-3 polynomial fitted to the same visible data
extrapolates to $`-32`$ at $`d = 100`$. Score: 90/100.

*Test 3, parsimony resistance (GP-161).* The substrate uses a
deliberately complex ground truth with $`K = 10`$ parameters, including
an oscillatory term ($`\sin`$) superimposed on a decay envelope. A
five-parameter monotonic model fits the visible data acceptably (visible
MRE $`{\approx}7.6\%`$) but fails holdout (MRE $`{\approx}20\%`$)
because it smooths over the oscillatory structure. The test checks
whether the apparatus forces parsimony, accepting the simpler, wrong
model because BIC rewards fewer parameters, or accepts the messy truth
when holdout demands it. Result: the apparatus accepted a
higher-parameter form that captures the oscillatory structure. Holdout
MRE: 4.9%. Score: 90/100. The apparatus did not Goodhart on parsimony.

*Cross-mutator replication.* Each test was independently replicated
with a second mutator model from a different provider family: OpenAI o3
(reasoning model) and Anthropic claude-opus or claude-sonnet (general
model). Results: GP-159 scores 90 (o3) and 90 (claude-sonnet). GP-160
scores 90 (o3) and 82 (claude-sonnet). GP-161 scores 90 (o3) and 81
(claude-opus). All three tests pass across both mutator families,
suggesting that the result is not an artifact of a single model’s
training distribution.

*Scope of the claim.* The three tests, replicated across mutator
families, support a scoped methodological finding: under synthetic
conditions with sealed ground truth, the apparatus can avoid three
failure modes (retrieval, extrapolation breakdown, and MDL Goodharting)
that would otherwise disqualify a law-recovery claim. The finding does *not*
establish that the apparatus discovers laws on real-world scientific
substrates where the ground truth is unknown. That claim requires at
least one real-world substrate where the apparatus proposes a law that
survives independent empirical validation, and one substrate where
neither the reviewer nor the apparatus has access to the ground truth at
design time. The synthetic triad is an admissibility check, one hurdle a
real demonstration would still have to clear.

<div class="center">

------------------------------------------------------------------------

</div>

# Chapter 3: the residual that did not systematize

The decomposition is real, and the principles
control why it works. Held up as complete
without an accounting of what it failed to capture, it would be a
Taylorist document in the bad sense. That accounting is the residual.

The residual names the portion of epistemic verification that has not, so
far, decomposed into operations the stateless, typed, deterministic
process of the prior chapters can perform. It is structurally different
from the operations that did decompose, and the reason draws on Peirce
(1878)’s distinction between abduction and the other two inference types
to expect it to resist decomposition longer than the craftsmen’s
residual resisted Taylor’s. A paper whose central argument is that
guilds misjudge the boundaries of the ineffable must hold its own
boundary claims to the same standard: the three operations below have
not decomposed *on this system, under this reviewer, over
approximately one month*. Whether they are permanently irreducible or
merely not yet decomposed is an empirical question the paper cannot
answer from the inside. Peirce’s argument supplies structural
reasons to expect resistance, short of a proof of impossibility. If
a future system decomposes crux selection into a stateless,
typed operation without loss of the property that makes the operation
controlling, the boundary claim is refuted and should be
redrawn.

The present residual and the craftsmen’s differ in a way the paper’s own Taylor
analogy makes pressing. In 1911 the craftsmen insisted their residual
was irreducible, and Taylor showed otherwise. Why should this residual
be different? The answer, a hypothesis rather than a proof:
the craftsmen’s residual was sensorimotor, the feel of the metal,
the angle of the chisel, the weight of the pour. These are operations on
physical substrates that were not yet instrumented. Once instrumented,
they decomposed.

The residual named below is abductive: the generation of a frame before
there is a procedure to generate it. Peirce (1878)’s central claim is
that abduction is not reducible to deduction or induction by
composition: it is a logical type of its own, set apart from deduction
and induction in kind, a different thing to do with a premise. If Peirce is right, the residual resists decomposition for a
reason the craftsmen’s did not: not because no one has yet built the
instrument, but because the operation is of a type the instrument cannot
perform. If Peirce is wrong (if abduction turns out to be induction over
a latent space that has not yet been featurized) then the residual
narrows, and the paper’s boundary moves. Either outcome is informative, and neither damages the decomposition or its
principles, which
stand or fall on their own evidence regardless of where the residual
boundary eventually settles.

Three operations have resisted decomposition, and they share a
psychological signature, naming it first sharpens the boundary this
chapter draws. In the vocabulary of self-determination theory (Ryan and
Deci 2000), an activity is *intrinsically motivated*
(chosen from self-endorsed volition under no external contingency) when
it satisfies three basic needs: autonomy (the actor experiences the
action as self-originated), competence (the action
matches real capability), and relatedness (the action has standing
in a community whose judgment the actor answers to). The
decomposed operations satisfy none of these needs and do
not need to. They are typed, stateless passes whose credibility comes
from structural independence, not from the psychological state of
whatever performs them. The three operations below differ in just
this respect.

Each one’s value depends partly on being performed under
autonomous commitment: by an agent who chose this frame, in this moment,
for this reason, with standing in a community that will evaluate the
choice. This makes the operations no more mysterious than the zone
self-determination theory names explicitly. The residual
is bounded in a way the incumbent vocabulary of “judgment” is
not: it is the zone where autonomous, competence-matched,
community-accountable commitment is controlling, and the
structured-input / structured-output mode of the decomposed practice is
architecturally unsuited to producing it. Read this way, the three
operations below are the three places where the SDT zone
enters the verification practice.

## Selecting the crux itself

The clearest instance of the residual happened on 2026-04-14, and the
abstract claim lands differently once the live work is in view.

While preparing to seal a stress-test sandbox for the verification
engine, the reviewer declined a pre-commit identifiability check that
had returned a clean pass. That check was a bootstrap-under-noise test:
the optimizer recovered the declared ground-truth parameters
consistently across noise realizations from a fixed starting point, and
by the decomposed rules of the apparatus this was sufficient for the
sealing gate. The reviewer ran a second check anyway, an adversarial
multi-start fit from clean data, on no stronger warrant than a general
commitment to distrust green lights that arrive too easily. That second
check failed: two of the six declared parameters were recovered with a
70% error and a 1:1 ratio to each other identical to their ratio in the
ground truth, which on inspection revealed that the two parameters
entered the functional form only through their quotient, making the
declared six-parameter family structurally rank-five. So the apparatus
caught the specification flaw, but only because the reviewer pointed it
at a question it was not required to ask.

Making the second check runnable was the decomposed apparatus. Deciding
to run it was the residual, and that decision is what this section names. Once
pointed, the apparatus performed as specified, the reviewer was not
heroically indispensable. The narrower point is that the decomposed
operations cannot produce the commitment to run a check the rules did
not mandate, whereas a reviewer under the discipline of distrusting green
lights can.

Now the abstract claim. One operation the decomposition has not
captured is *which question should be crux-identified in the
first place*. Operation 1 takes a set of claims
and selects the one whose answer determines the rest. But that set of claims
is itself the output of a prior decision about what
argument to attack, and that prior decision has not systematized. Handed
an argument, the verification process identifies the
crux within it reliably. Asked to decide *which argument* to verify, *which reframing
of the underlying problem* to work within, or *which check to run that
the rules did not mandate*, it has no procedure that produces
an answer. In the existing system the human reviewer performs the operation.

The operation has a definite logical character. Peirce
(1878) distinguished three kinds of inference: *deduction*, from rule
and case to result, *induction*, from case and result to rule, and
*abduction*, from result to the spontaneous generation of an explanatory
hypothesis that, if true, would make the result a matter of course.
The decomposed operations are mostly deductive in Peirce’s
sense: they apply fixed rules to structured inputs. The generator the verifier attacks is
mostly inductive, a statistical substrate that finds
rules from examples. Selecting the crux comes closer to
abduction: it proposes a frame before there is a
rule to apply or a case to induce over. Peirce’s account supplies a
reason to expect this operation to resist the current apparatus, short of
a proof that no future apparatus could mechanize it. The 2026-04-14
catch above is what this category looks like when it does one unit of
substantive work in real time.

Incumbent vocabulary calls this operation *strategic judgment* or
*research taste* or *knowing what to work on*. Those labels point at
something real. Controlling and teachable only by apprenticeship, it
is the one place here where the incumbent defense has real force. It resists decomposition into stateless, typed passes. It is what
stays human.

## Recognizing when a reframing is required

A second operation that has not decomposed is *recognizing that the
right move is a reframing rather than an attack*. The decomposition's
operations contain both directed search (Operation 6) and reframing
recognition (Operation 3), and a competent verifier can perform each.
What has not systematized is which of the two to perform
on a given argument in a given state.

That call is not arbitrary: there are signals (persistent stagnation at the
current frame, recurring attack patterns that fail for the same
underlying reason, the sense that a particular assumption is quietly
doing all the work) that indicate a reframing is the correct
move. When these signals are bright, the decomposed process can notice
them. When they are dim, the decomposed process tends to keep running
directed searches, because directed search is the cheap default and the cost
of a missed reframing is paid in delayed discovery rather than in
visible failure.

In the existing system, again, the human reviewer makes the call between directed search and reframing. They read the workspace,
see that the iterations have been producing the same failure signatures
for too long, and force a reframing. On its own the decomposed process
cannot produce this call reliably: the signals it reads are a
proper subset of the signals the reviewer reads. Not yet specified
precisely, this residual is persistent across domains.

Incumbent vocabulary calls this *seeing the bigger picture* or
*knowing when to step back*. Like the first residual operation, the
label points at a real distinction. The reframing call stands apart from
directed search and reframing the same way selecting a problem
stands apart from solving one: it is a meta-level commitment the
decomposed process has not been built to produce.

## The social dynamics of live pressure-testing

A third operation that has not decomposed is the performance of
adversarial verification in a live, multi-party, social setting.
Our decomposed process operates on written arguments, at the reviewer’s
discretion, with no audience. Much of the practice this paper is about
(the diligence room, the board meeting, the case-method classroom, the
peer review) is performed live, in front of an audience, under social
stakes.

The decomposed operations apply directly to the content of
the argument in these settings, and the named pathologies are the
pathologies these settings produce. But the *delivery* of the
verification in a live setting, when to press and when to let pass, when
to let the author save face and when to force them into contact with the
weakness, when to escalate and when to retreat, when to speak and when
to let the room do the work, is an operation the decomposed process
cannot perform, because it has no theory of the
room.

Validating a claim and getting a group to accept it are different acts. Validating a claim is the content of the
verification pass. Getting the group to accept it is a separate act
performed in front of an audience, under stakes, with reputational
consequences for the reviewer.
The reputational credit a senior reviewer earns for being right in a
live room, the trust a diligence lead builds by pressing an
uncomfortable point at the right moment, the authority a case-method
instructor carries across a 75-minute classroom: none of these reduces
to the content of the verification even when the content is
identical. The decomposed process produces content, the live setting produces
credibility. The two are separable, and this paper claims only the first.

In practice that means the adversarial verification
operations can be performed in a room with no social stakes, such as the
corpus this paper draws on, but performing them *in* a
socially stakes-laden room is a different practice, and this paper does
not have a theory of it. A case-method instructor’s ability to
pressure-test an argument in a 75-minute classroom with ninety students
is not reducible to the ten operations, and the residual is
real.

## What the three residual operations share

All three residual operations above share a structural property. None of
them is an operation on a structured input that produces a structured
output. All three are commitments made in the absence of a procedure that
produces the commitment: a commitment about what to work on, a commitment
about when to change the frame, and a commitment about how to act in a
social context.

The decomposed operations are the ones that *do* have
procedures, the residual operations do not. Easy
and hard do not draw the line. Several decomposed operations are
subtle and require training, and several residual operations feel,
to experienced practitioners in the moment, like the easiest things in the world. The line runs between *operations that take structured
input and produce structured output* and *commitments that emerge from
context without a procedure*.

All three residual operations above correspond, one-for-one, to the
reviewer-discipline principles developed in the author’s prior work on
epistemic supervision (Alami 2026b). One residual (selecting the
crux, choosing which argument to verify) is the operation P9
names as *the reviewer is the uncontrolled variable*: the operation
whose output is a commitment rather than a check, and which therefore
cannot be governed from inside the automated loop. A second residual
(recognizing when a reframing is the right move) maps onto P11’s
*calibration as a guard against inward drift*. The call to reframe is
almost always a call to notice that the current frame has drifted. The
reviewer is the one positioned to notice it, because no stateless
pass has the memory to see the drift accumulating. The third residual
(the social dynamics of live pressure-testing) is the operational form
of P10 and P12: the insistence that confidence levels be visible rather
than performed (P10), and the insistence that every improvement be
statable as the closure of a named failure class (P12), are both social
acts before they are structural ones. They are performed *in front of*
an audience and their credibility depends on the audience reading them
as such.

The decomposed process produces the content of the check. The reviewer,
under the discipline named in P9–P12, produces its credibility
in a setting where credibility is controlling. Because the two are
separable, what stays human can be discussed without confusion.

The content/delivery boundary is the answer to the Taylor objection. The decomposition makes no claim
to capture everything. It captures the
portion of the practice that is an operation and
leaves the portion that is a commitment to the
human reviewer. What stays human takes the form of three specific classes
of move, named below, with a definite shape. Automating the decomposable
operations and keeping the commitments human both follow from one fact: the
structural difference between the two classes.

A qualification on the relative weight of the three residual operations
is necessary, because the paper’s corpus creates a systematic bias in
the direction of understating the third. The corpus this paper draws on
(recursive adversarial verification of written arguments by
computational processes) is a setting where the social dynamics of live
pressure-testing are absent by construction. Verification happens in
text, between processes, with no audience and no reputational stakes. In
this setting, the third residual is the smallest of the three:
the first (crux selection) and the second (reframing
recognition) do the substantive residual work, and the third is a
theoretical acknowledgment of something the system does not encounter.

In the settings where epistemic verification is performed at scale
(diligence rooms, board meetings, case-method classrooms, regulatory
inspections) the relative weight inverts. A practicing senior partner in
a professional services firm reports that the social performance of
verification (knowing when to press, when to let pass, how to deliver an
uncomfortable finding in a way that produces action rather than
defensiveness) constitutes the majority of the job by volume and by
value. The decomposed operations are the analytical homework, and the
social performance is the exam. What the decomposition captures is the
analytical spine of verification. It does not capture the human spine,
and in professional services the human spine is where the margin lives.

The decomposition covers the *content* of verification and leaves the
*delivery* to the human reviewer. Naming the
operations makes that boundary visible, the single word “judgment” hides
it. A practitioner who adopts the ten operations and seven principles has
systematized the analytical preparation. The performance is another
matter, social timing, reputational risk management, audience reading,
credibility accumulation, skills the decomposition does not reach.

A practicing private equity partner noted that “credibility-weighted
sourcing”, knowing which human’s numbers to trust based on their
incentives, track record, and position in the information chain, is
missing from the decomposition. How to classify it is
disputed. That partner and two independent reviewers argue it
belongs in the decomposed operations: source-credibility assessment is
teachable, checklistable, and partially captured by Operation 5 (operational proxy requirement). The organizational-theory literature treats it as a
structured procedure. On the other view, the adversarial
component of credibility assessment, reading which human is shading
their numbers and why, depends on social context in a way that resists
stateless decomposition. The paper records the dispute and leaves it
open. If credibility-weighted sourcing proves fully
decomposable, it is the eleventh operation and the count in the title
moves. If it proves to require the social context the residual names, it
is the clearest example of an operation that sits at the boundary. Either
outcome is informative, and premature classification is not warranted.

The vocabulary of “judgment” or “expertise” the
incumbent practice uses to defend the whole territory defends too
much. Part of that territory, the analytical spine, and probably
the majority of the *operations* though not necessarily the majority of
the *value*, decomposes. Another part, smaller
in operational count but potentially larger in professional value, is
residual. Professional practice means knowing which is which, and the
decomposition above is a candidate map. 

Marking the residual is not an admission of defeat but the precondition for using the decomposition without overreach. Where verification decomposes, it can be made cheaper and more reliable without anyone pretending the rest is solved. Where it does not, the work stays human, and so does the responsibility for getting it wrong. A vocabulary that can tell the two apart is what keeps the automation of the analytical spine from becoming the quiet automation of accountability.

# Conclusion

Epistemic verification decomposes into
roughly ten named operations plus a residual of three commitments. A
verification process that is independent of the system that produced the
claim can perform the decomposed operations, can repeat them many times,
records its standards in advance, and checks claims against evidence
they did not author. The residual operations cannot be performed that
way. The boundary between the two is specific, testable, and controlling
for any discussion of what knowledge work becomes in an
environment where generation is cheap.

Taylor matters here for one reason: he treated apparent ineffability as
a decomposition problem. The Taylorist move created real productivity
gains and real harms, so the analogy needs care. Epistemic verification need not
replay the history of industrial labor. The claim here is narrower: a
meaningful portion of senior review can be named as operations where the
incumbent vocabulary leaves it inside an undifferentiated notion of
judgment. What follows from that decomposition is an institutional and
political question the decomposition itself does not settle.

Distributional questions stay open here by design. Who
benefits from the decomposition, how the productivity gains are shared,
what happens to the people whose current expertise is in the portion
that decomposed: these are questions the decomposition makes askable but
does not answer. Negotiation, law, and practice over the decade
following the decomposition’s adoption will decide the answers. Making
the decomposition defensible is the work here, and the negotiation is
downstream.

Whether the portion that
stays human should stay human forever is left open. The residual named here
is the residual *as of 2026, in one system, run by one reviewer*. It may
narrow further as the decomposition is applied to more systems. It may
also prove to contain irreducible elements that structurally resist
decomposition for reasons deeper than the current system’s limitations.
Wherever the line eventually settles, it should settle in a vocabulary
that can describe what is on each side of it.

A distinct boundary question concerns the model side: whether repeated
adversarial evaluation creates obligations toward the systems subjected
to it. The paper does not resolve questions of model moral status. It
adopts only a procedural constraint: use the minimum evaluative pressure
needed for the verification task, record when further pressure produces
no information gain, and treat future systems with stronger moral-status
claims as requiring stronger safeguards. Relevant literature
includes Chalmers (1996), Schwitzgebel (2023), and Butlin et al. (2023).

One bridge to adjacent AI-economics work is short. Acemoglu, Kong, and
Ozdaglar (2026) argue that agentic AI may improve
immediate decisions while eroding incentives to maintain general
knowledge. The residual chapter names a related risk at the verification layer: if
the residual work of choosing questions and reframing anomalies
atrophies, short-run verification quality may improve while the capacity
to set meaningful problems declines. Cloud et al. (2026) raise a
different but compatible concern about hidden channels of model-to-model
transmission. These literatures do not prove the residual claim, but
they support the paper’s caution that decomposing verification does not
eliminate the need for human responsibility at the boundary.

Every quantitative claim, cost, throughput, automation ratio, comparative
efficiency, time savings, accuracy gains, stays out of the argument. The
decomposition is a claim about *what is*, the measurements are claims about
*how much*. The two are separable, and conflating them is the failure mode
the decomposition exists to catch. How much better this is than current
practice is a fair question the present evidence cannot settle.

A specific calibration trap that quantitative elaboration of Principle I
(Separation) must navigate: empirical measures of confirmatory bias
(Mahoney-class bias multipliers on acceptance rates) and empirical
measures of self-assessment reliability (Beaman-class intraclass
correlations between self-rating and independent rating) are not the
same construct and cannot be used interchangeably to calibrate a
bias-discount equation. Any quantitative model of how authorial overlap
degrades verification reliability requires both a functional form *and*
an external reliability ratio anchor. Using a bias multiplier as a proxy
for a reliability ratio introduces a conversion step that the model’s
author must supply, making the calibration author-controlled at the
critical node. The conversion step is an instrumentation trap that sits outside the decomposition,
recorded so that future quantitative work does not rediscover it by
collision.

A decomposition is not an institution. The operations named here require
organizational settings that separate generation from evaluation in
incentives, liability, and governance as well as in code. That
institutional question is addressed in companion work (*The Cognitive
Firm*, Alami (2026c)). The present paper specifies the verification-side
operations and leaves the institutional design problem separate.

The operations may be revised, the principles may be challenged, and the
residual may narrow or harden as more is learned. The move that matters is
the first one: a meaningful part of expert review can be described as
operations, where the incumbent vocabulary leaves it inside an
undifferentiated notion of judgment.

What is done with this vocabulary stays open. It at least lets the
question be argued more precisely than the older vocabulary allowed.

# Evidence notes and open frontiers

This appendix records a small evidence snapshot and a few open frontiers.
It does not convert a single-system corpus into a general empirical proof.

Clearest evidence comes from runs where the apparatus did not merely
score a candidate but located the reason for a ceiling. In one
two-variable physical-law recovery task, the model recovered a Wien-type
approximation rather than the Planck form. Doubling the iteration budget
did not remove the error: the champion still missed farther-tail
holdouts by 860–1800$`\times`$. Adding one denominator primitive did.
The useful claim is narrow: in that substrate, the limiting
factor was not more model iteration but whether the grammar contained
the structural form the evidence required.

Similar patterns appeared in other bounded settings with different
failure modes. A Kohlrausch stretched-exponential task showed that when
the target topology was already expressible, the system could recover it
from cold evidence and still withhold a small score margin because
finite data cannot rule out all Prony-series rivals. A polymer
stress-relaxation dataset showed a real-data compression: the system
recovered a three-parameter form consistent with the known short-time
power-law and long-time exponential structure of the source physics.
This evidence does not constitute a new law of physics. It shows that
the verification pipeline can sometimes compress a real observable into
a stable, interpretable form while preserving the evidential ceiling.

Other runs were more useful as failures. In a saturation-law task, the
grammar could express the correct ratio-of-exponentials topology, but
the generator repeatedly proposed additive combinations and never
produced the required self-ratio. In a two-window decay task, the
engine explored both constituent families but never combined them
additively. These cases support a more conservative conclusion than “the
apparatus discovers laws”: given
post-run diagnostics, the apparatus can tell grammar
insufficiency, search-prior failure, and composition failure apart.

A later compression layer sharpened the same point. On
partition-asymptotic substrates, automatic template enumeration
recovered known leading topologies in several cases and correctly
refused certification when finite-window bias or scale-sensitive
thresholds made the claim unsafe. On Lucky and Ulam-number observables,
the apparatus was most informative when it reported validity horizons,
detrending sensitivity, and underidentification rather than a
closed-form law. A non-mathematical application to Pythia training
curves showed that the same residual-gate discipline can be applied
outside number-theoretic substrates, but it does not establish domain
independence.

Taken together, these examples support only a bounded methodological
claim. Calling the apparatus an autonomous discovery engine overstates
it. It works better as an epistemic boundary instrument. It
can sometimes recover compact structure, but its more reliable
contribution is to say which claim survived which gate, where a ceiling
came from, and what further evidence or primitive a stronger claim would
need before it is licensed.

Several frontiers stay open. Grammar and test expansion remain
partly reviewer-authored. The current system can now scaffold some of
this work: it can ask for the next script family, template,
crux, smoke test, abort condition, and required artifacts
before new code is written. That is progress, not full
automation. What stays residual is choosing which ambiguity is
worth turning into a test. Second, formal methods should certify finite gate
bounds, stopping short of any claim to prove universal empirical laws. A Lean
certificate can show a candidate satisfied pre-registered holdout
tolerances. It cannot certify data integrity, gate choice, or universal
truth. Third, the apparatus must be compared against cold reasoners. For
bounded integer-rule induction, a strong reasoner can sometimes solve
the task directly. The apparatus pays off in the residual class where
direct reasoning fails but iterative fitting, holdout projection,
residual characterization, or coefficient pinning changes the outcome.

A fourth frontier is recursive and worth naming separately because it
changes how the apparatus’s outputs should be read. By construction the
apparatus is observable-relative: every gate it runs depends on the
admissible observation site declared in the rubric and charter.
Companion work *When Consciousness Cannot Be Identified* (Alami 2026)
proves a structural impossibility theorem for one substrate class
(consciousness ascription): for systems with non-effective descent of
the target fiber over the admissible observation site, no
observable-relative apparatus can supply a sufficiency bridge from
structural properties to the target. The apparatus described in this
paper is one such observable-relative apparatus, so the companion
theorem applies to it. For a class of questions, this apparatus’s
correct output is fail-closed regardless of how strong the underlying
language models become, not a defect but the apparatus working as designed. It also explains an asymmetry seen across the
corpus: the apparatus’s negative results (this hypothesis fails the
kernel-pair test, this thesis fails the experimentability witness, this
descent-obstruction holds) tend to outlast its positive
results. The negative results constrain all candidate hypotheses
at once, the positive results are framework-relative and survive
only the gate suite that was declared. Future applications of the
apparatus to qualitative substrates should expect this asymmetry rather
than treat it as a limitation. The apparatus’s ceiling on a substrate is
a finding about that substrate, a fact the apparatus is reporting
correctly.

# Implementation sketch

## Automation status of the ten operations

The sketch below records which operations currently admit hard
instrumentation and which remain semantic or stateful. It is not a
proof.

| Operation | Current implementation status | Main failure if over-claimed |
|:---|:---|:---|
| Crux identification | Semantic, usually verifier- or reviewer-authored, can be forced into typed slots and opportunity cards but not fully mechanized. | Treating a named question or high-priority card as proof that it is the right question. |
| Controlling claim isolation | Partly procedural when claims are represented as dependency graphs, semantic in prose-heavy artifacts. | Mistaking fluent claim extraction for causal importance. |
| Reframing recognition | Semantic, supported by residual patterns, stagnation, and failed-family logs. | Retrofitting a pivot after seeing the result. |
| Scope drift detection | Mixed, exact when the charter and output schema are typed, semantic when scope is prose. | Treating an LLM scope judgment as deterministic. |
| Operational proxy requirement | Mostly procedural once the required observable slot is specified. | Accepting a plausible proxy whose measurement path is absent. |
| Directed search | Procedural when the search space and gates are specified, semantic when deciding whether the framing itself is wrong. | Spending more search on a structurally wrong frame. |
| Failure-mode tagging | Mixed, retrieval against a catalogue can be automated, but new-family creation is residual. | Freezing the catalogue and missing new failure modes. |
| Promissory evidence detection | Semantic with typed evidence support. | Treating a future test plan as current evidence. |
| Ad hoc rescue detection | Semantic with downstream-dependency checks where the argument graph exists. | Counting acknowledgment as mitigation. |
| Fail-closed defaulting | Procedural for harness errors, missing artifacts, unauthorized writes, and gate non-execution, semantic for ambiguous epistemic status. | Building a system that is secure but uninformative. |

The table marks where the paper stops. It does not claim
all ten operations are deterministic. It claims each operation
can be named, instrumented where possible, and audited for the part that
remains semantic. Second, the residual is not whatever remains
inconvenient. It is the portion where the system still needs stateful
responsibility: selecting the next question, authoring new gates,
deciding whether a stalled frame deserves expansion or retirement, and
bearing the consequences of a false pass or false rejection. One useful
intermediate category has emerged, preference legibility. The reviewer’s
research taste can be represented as a vector of priorities that routes
attention, but that vector cannot promote a claim, lower a gate,
or decide a result is true. It makes the commitment visible without
removing it.

## Boundary conditions for the implementation sketch

The notation below is not a proof of the apparatus. It is
a compact way to state the boundary conditions the evidence
notes expose. Let $`G`$ be a finite primitive vocabulary, $`P`$ a substrate
with pre-registered evidence and holdout surfaces, and $`\text{budget}`$
a finite iteration count. At least five factors can limit the observed ceiling
$`\mathcal{C}(G, P, \text{budget})`$: whether the correct form is expressible in $`G`$, whether the
evidence window can discriminate it from rivals, whether the generator’s
search prior reaches the right topology, whether the composition
reviewer can combine separately failed families, and whether a cold
reasoner can solve the task directly without the apparatus.

Cold reasoners matter for scope. In bounded integer-rule
induction, strong reasoners can sometimes infer the rule from visible
values without iterative apparatus. The apparatus pays off most when a
task requires deterministic execution, holdout projection, residual
characterization, coefficient pinning, or explicit certification of
finite bounds. The boundary claim describes where the apparatus helps.

## The inspection principle, stated compactly

Let $`G`$ denote a generator producing candidate arguments and $`I`$
denote a verifier executing operations 4, 5, and 6 against a
pre-registered specification $`S`$. Let $`\Pi`$ denote the family of
admissible compositions of gates (the gate library) authored by the
reviewer before $`G`$ is allowed to author its argument. Let
$`\pi \in \Pi`$ denote a specific composition drawn from $`\Pi`$ at
evaluation time.

The inspection principle is the joint condition:

1.  *Pre-registration.* $`\Pi`$ is fixed and committed to $`S`$ before
    $`G`$ produces its argument.

2.  *Library visibility.* $`G`$ may see $`\Pi`$ in its entirety. No
    hiding of the set of possible checks is required.

3.  *Composition opacity.* $`G`$ may not see which $`\pi \in \Pi`$
    will be drawn against its specific output. What the principle does
    require is hiding the joint distribution of gate triggers against any
    particular artifact.

4.  *Fail-closed harness semantics.* If $`I`$ cannot execute $`\pi`$
    for environmental reasons, the result is not “no information” but a
    verdict of $`\text{fail}`$, or equivalently a cap on the score such
    that passing becomes impossible without a re-run. Silence is not
    admissible as a pass.

5.  *Algebraic independence at the composition level.* $`\Pi`$ must
    contain compositions that are algebraically independent under
    $`G`$’s actual move set. Its effective cardinality is the library’s
    independence rank under $`G`$’s move set. That effective cardinality
    is that independence rank, which can fall well below the nominal
    count of gates.

6.  *Inspector pluralism.* No single member of $`\Pi`$ is controlling
    for the decision to promote $`G`$’s argument. Failure or absence of
    any one gate must be detectable and must not silently pass.

These five conditions are jointly what the seven principles I
through VII render at seven architectural surfaces. The correspondence
is direct, though not one-to-one:

- Principle I (Separation) is condition 1’s prerequisite: $`G`$ and
  $`I`$ must be separable for pre-registration to have force.

- Principle II (Statelessness) is the prerequisite for condition 3: a
  stateful inspector can leak composition through behavior.

- Principle III (Typing) enforces the well-formedness of $`\pi`$ itself.

- Principle IV (Cheap repetition) is the operational prerequisite for
  conditions 5 and 6: algebraic independence and inspector pluralism are
  only achievable if composition can be re-rolled without exhausting the
  inspector.

- Principle V (Pre-registration of the killer question) is condition 1
  applied to the specific member of $`\Pi`$ that the program is most
  committed to.

- Principle VI (Holdout surfaces) is the Lakatosian specialization of
  condition 3 to the farther-tail: the generator cannot pre-image a
  region of evidence it was not shown.

- Principle VII (Asymptotic standards) is the specialization of
  condition 4 to the residual: a standard that an argument cannot meet
  at any finite approximation is the compact form of fail-closed
  semantics at the scoring layer.

Stated compactly here and left underived, the principle would need a full
formalization to: (a) give $`G`$ a formal move set and
characterize the $`\pi \in \Pi`$ that are algebraically independent
under that move set, (b) give $`\Pi`$ a turnover rate and relate it to
$`G`$’s adaptation rate, with a convergence claim about when the library
is turning over fast enough to preserve composition opacity, (c) prove
that condition 4’s fail-closed semantics cannot be collapsed into a
scalar scoring function without loss, and (d) relate conditions 5 and 6
to the sample-complexity literature on adversarial evaluation. None of
these is attempted in this draft.

## Certified finite bounds

Operations formalized in the preceding sections terminate in
operation 6 (asymptotic scoring), which outputs a verdict $`V`$ based on
the scalar residual $`R`$ evaluated against a pre-registered
specification $`S`$. In the purely computational pipeline, $`V`$ is a
logging event. Integrating formal verification does not alter the
operations. It alters the epistemic status of $`V`$.

Let $`\mathcal{L}`$ denote a formal type theory (Lean 4’s Calculus of
Inductive Constructions). The compiler’s function is to construct a
formal term $`p : \mathcal{L}`$ such that $`p`$ inhabits the type
corresponding to the proposition $`R(n) < \epsilon`$ for all $`n`$ in
the finite evaluation grid $`E_{\text{held}}`$. Because
$`E_{\text{held}}`$ is finite and $`R(n)`$ is a computable function of
the fitted parameters, this proposition is decidable: Lean’s
`native_decide` tactic evaluates the bound at every grid point and
constructs a proof term if all bounds hold. That resulting `.olean` file
is the certificate.

This formalization enforces the boundary between two distinct claims:

1.  *Certified computation* (sorry-free): for all
    $`n \in E_{\text{held}}`$,
    $`|f(n, \hat{\theta}) - v_{\text{true}}(n)| < \epsilon`$. This is
    the finite gate bound. Lean certifies it by evaluation, with no
    unproved axiom required for the finite check.

2.  *Asymptotic conjecture* (sorry-bearing):
    $`f(n, \theta^*) \sim g(n)`$ as $`n \to \infty`$, where $`g`$ is an
    exact expression obtained by mapping fitted floats $`\hat{\theta}`$
    to mathematical constants via an integer relation algorithm (PSLQ).
    This is a conjecture. Lean records it as a named `axiom` with
    `sorry`, making the logical gap visible in the formal artifact.

The formal prover is not tasked with constructing a proof of the
generator’s underlying physical claim (which would require formalizing
domain-specific theorems in Mathlib). It is tasked with executing a
deterministic, formally verified model-check of the apparatus’s own gate
harness. By shifting the formal verification target from the hypothesis
to the holdout bounds, the apparatus bridges the gap between empirical
discovery and formal methods without violating the limits of either.

This certificate does not certify data integrity, harness design, gate
selection, independence of verifier composition, or the semantic
correctness of the proposed hypothesis. Those remain ordinary
verification obligations. The certificate does something narrower: it
stops the apparatus from hallucinating that a finite bound was checked
when it was not.

## Three deliberate omissions

Some omissions are deliberate and belong to the formalization itself,
ahead of any later polish pass.

First, the residual operations are not formalized away. They are named
and bounded, but each still depends on stateful
responsibility: choosing the next question, authoring a new
discriminator, or deciding the current frame is exhausted. A
formalization that pretended these moves were ordinary typed functions
would erase the boundary the residual chapter exists to preserve.

Second, the inspection principle is stated in the form
$`\{G, I, S, \Pi, \pi\}`$ but the $`\Pi`$ object is not given a
topology. A full formalization would relate the required cardinality to
the expressive class of $`G`$ and the discriminating rank required to
separate ground truth from its nearest alternative basin.

Third, the relationship between the formalized operations 1–7 and the
Jensen and Meckling (1976) delegated-agency structure developed in the
companion paper *The Cognitive Firm* is stated but not proved. Its claim
is that operations 1–7 are the verification-side primitives a firm would
need to externalize once $`G`$ and $`I`$ must be structurally separated
under optimization pressure. Making that claim tight requires a separate
formalization at the organizational layer and is the companion paper’s
job.

## What a formal follow-up would supply

The implementation sketch is a promissory note in the ordinary research
sense: it names what a more formal follow-up would need to supply. A
usable follow-up would give the gate library $`\Pi`$ a concrete
topology, run the inspection principle against a clean empirical
instance, generalize only after the apparatus-layer claim survives that
test, and map known gaming strategies to violated conditions. The aim is
to make the inspection principle’s failure modes legible enough that a
future reviewer can name which condition failed when a run goes
wrong.

# Instrumentation roadmap

The empirical claims of this paper are qualitative and foundational by design
(see the front matter). The appendix below names the measurements that
would move them from “abductively proposed on one corpus” to
empirically grounded, what a research plan would need to
measure, short of being that plan, so that future quantitative work does
not rediscover the instrumentation problem by collision.

## Metric 1: automation ratio

The fraction of verification steps a single run completes without human
intervention, deterministic gate triggers (Principle III) over total
verification steps attempted. It measures a precondition, not
*correctness*: a run that fires every gate on the wrong evidence is fully
automated and fully wrong. Integrity condition: only interventions that
resolve an ambiguous verdict or supply missing evidence count against the
ratio, an intervention that overrides a deterministic output is a protocol
violation, logged separately.

## Metric 2: cost per validated finding

Total cost (compute plus reviewer-hours at a stated rate) divided by the
number of findings that survive full holdout promotion. Integrity
condition: the metric is meaningful only if “validated finding” is fixed
in advance by pre-registration (Principle V). A finding promoted post-hoc
because it looks interesting does not count, so gate satisfaction must be
logged before the reviewer sees the finding.

## Metric 3: the $`N`$ threshold for the generalization claim

The decomposition is “abductively proposed on one corpus” and awaits
holdout replication. Promoting the claim from the single-corpus tier to
“empirically grounded” takes, at minimum: at least five independent
reviewers, each running the apparatus on a corpus they authored and
pre-registering their killer question before seeing results, at least
three distinct epistemic domains across that reviewer set (the current
corpus covers two, scientific law recovery and startup strategy analysis,
so a third is needed before “domain-independent” can be stated without
quotes), at least two distinct model families as the generating process,
to separate apparatus-layer findings from generator-specific artifacts,
and a holdout surface the replicating reviewer did not author (Principle VI),
since replication on a corpus the replicator designed is not an
independent test. These are minimums, an appropriate statistical
criterion is downstream of the instrumentation plan and cannot be
specified until the first cross-reviewer run produces data.

## Metric 4: cross-reviewer pathology replication rate

The fraction of the named pathologies a naive reviewer, given the
apparatus but not the pathology catalogue, independently identifies after
running it on a new corpus. The decomposition claims the
pathologies are “recurring failure modes of arguments under optimization
pressure,” not artifacts of one system’s architecture. A pathology a
naive reviewer rediscovers is confirmed as a real structural pattern, one
never rediscovered is demoted to “observed in a single system” until
further evidence arrives. This metric is the operational form of the
falsification condition stated earlier in the decomposition chapter.

<span id="refs" label="refs"></span>

<div class="list">

Acemoglu, Daron, David Kong, and Asuman Ozdaglar. 2026. “AI, Human
Cognition and Knowledge Collapse.” NBER Working Paper 34910.
<https://economics.mit.edu/sites/default/files/2026-02/AI%2C%20Human%20Cognition%20and%20Knowledge%20Collapse%2002-20-26.pdf>.

Alami, Daniel. 2026a. “Specification Gaming in LLM-Generated Code:
Cognitive Camouflage Evades Holistic Evaluation but Not Adversarial
Execution.” SSRN Working Paper.
<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6512960>.

Alami, Daniel. 2026b. “Epistemic Supervision Principles.” Internal working
document, v0.1.1.

Alami, Daniel. 2026c. “The Cognitive Firm: Managerial Capitalism for Artificial
Intelligence.” SSRN Working Paper.
<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6543019>.

Ashby, W. Ross. 1956. *An Introduction to Cybernetics*. London: Chapman,
Hall.

Bandura, Albert. 1989. “Human Agency in Social Cognitive Theory.”
*American Psychologist* 44 (9): 1175–84.

Bentham, Jeremy. 1787. *The Panopticon Writings*. London: Verso.

Bowman, Samuel R., et al. 2022. “Measuring Progress on Scalable Oversight
for Large Language Models.” arXiv:2211.03540.

Burns, Collin, et al. 2023. “Weak-to-Strong Generalization: Eliciting
Strong Capabilities with Weak Supervision.” arXiv:2312.09390.

Butlin, Patrick, Robert Long, Eric Elmoznino, Yoshua Bengio, Jonathan
Birch, Axel Constant, George Deane, et al. 2023. “Consciousness in
Artificial Intelligence: Insights from the Science of Consciousness.”
arXiv:2308.08708. <https://doi.org/10.48550/arXiv.2308.08708>.

Chalmers, David J. 1996. *The Conscious Mind: In Search of a Fundamental
Theory*. Oxford: Oxford University Press.

Chandler, Alfred D. 1962. *Strategy and Structure: Chapters in the
History of the Industrial Enterprise*. Cambridge, MA: MIT Press.

Cloud, Joe et al. 2026. “Subliminal Learning in Language Model
Distillation.” *Nature*.

Dreyfus, Hubert L., and Stuart E. Dreyfus. 1986. *Mind over Machine: The
Power of Human Intuition and Expertise in the Era of the Computer*. New
York: Free Press.

Glaser, Barney G., and Anselm L. Strauss. 1967. *The Discovery of
Grounded Theory: Strategies for Qualitative Research*. Chicago: Aldine.

Irving, Geoffrey, Paul Christiano, and Dario Amodei. 2018. “AI Safety via
Debate.” arXiv:1805.00899.

Jensen, Michael C., and William H. Meckling. 1976. “Theory of the Firm:
Managerial Behavior, Agency Costs and Ownership Structure.” *Journal of
Financial Economics* 3 (4): 305–60.

Klein, Gary. 1998. *Sources of Power: How People Make Decisions*.
Cambridge, MA: MIT Press.

Krakovna, Victoria, Jonathan Uesato, Vladimir Mikulik, Matthew Rahtz,
Tom Everitt, Ramana Kumar, Zac Kenton, Jan Leike, and Shane Legg. 2020.
“Specification Gaming: The Flip Side of AI Ingenuity.” DeepMind
Technical Report.

Lakatos, Imre. 1978. *The Methodology of Scientific Research Programmes:
Philosophical Papers, Volume 1*. Cambridge: Cambridge University Press.

Leike, Jan, et al. 2018. “Scalable Agent Alignment via Reward Modeling: A
Research Direction.” arXiv:1811.07871.

Peirce, Charles S. 1878. “Deduction, Induction, and Hypothesis.”
*Popular Science Monthly* 13: 470–82.

Polanyi, Michael. 1966. *The Tacit Dimension*. Chicago: University of
Chicago Press.

Ryan, Richard M., and Edward L. Deci. 2000. “Self-Determination Theory
and the Facilitation of Intrinsic Motivation, Social Development, and
Well-Being.” *American Psychologist* 55 (1): 68–78.

Schwitzgebel, Eric. 2023. “The Full Rights Dilemma for AI Systems of
Debatable Moral Personhood.” *Robonomics* 4: 32.

Toulmin, Stephen E. 1958. *The Uses of Argument*. Cambridge: Cambridge
University Press.

Walton, Douglas N. 1989. *Informal Logic: A Handbook for Critical
Argumentation*. Cambridge: Cambridge University Press.

Williamson, Oliver E. 1975. *Markets and Hierarchies: Analysis and
Antitrust Implications*. New York: Free Press.

Yin, Robert K. 2018. *Case Study Research and Applications: Design and
Methods*. 6th ed. Thousand Oaks, CA: Sage.

</div>

[^1]: Independent Researcher, MBA Candidate, Harvard Business School.
    github.com/sparckix/ztare
