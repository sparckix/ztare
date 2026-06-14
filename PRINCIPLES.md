# Principles

This document states, as plainly as possible, the principles that govern how this project is built and what it is trying to do. It is written for readers who take specification gaming, Goodhart dynamics, evaluator softening, and the principal, agent problem as native vocabulary, and who want to know whether the thing is worth reading before reading it.

The principles are organized in two layers:

- **Operator layer**, how I work on this project. Personal discipline, not a claim about what others should do.
- **Project layer**, what ZTARE is, what it isn't, and what it refuses to claim.

The transferable *findings* from the project, the principles about epistemic generation and agent supervision that would be true even if this codebase disappeared tomorrow, are in a sibling document: [`docs/concepts/epistemic_principles.md`](docs/concepts/epistemic_principles.md).

---

## Operator layer, how I work on this project

These are the rules I hold myself to. They are not general recommendations. They are personal operating discipline, written down so that I can be held to them and so that readers can tell what kind of work to expect.

**1. Ship the artifact, not the manifesto.** The repository is the argument. Papers describe what the artifact already does; they do not promise what it will do. If a claim appears in a paper, the deterministic machinery that produces the claim is in the repository, at a file path the paper points at. Empirical sections cite line numbers. Speculative sections are marked speculative. If the artifact disappears, the papers are worth less.

**2. Public work-in-progress over private polish.** The kernel hardening history, the seam documents, the debate logs, and the failure taxonomies are visible as they are produced, not backfilled for a launch. Readers who want to see a clean story can read the papers; readers who want to see how the sausage was actually made can read the seams. The audit surface is the point, a closed system that only reveals its final state is one I would not trust, and I am not going to ask readers to trust one.

**3. Ruthless maintainership of the merge boundary.** The value-add of running this project is not writing novel code. It is saying no to 90% of the patches, rejecting gamed champions, refusing to promote theses that fail a deterministic gate, closing seams that would dilute the epistemic core for the sake of breadth. This is the operator job that cannot be delegated to an LLM, because an LLM cooperating with itself is the failure mode the project exists to document.

**4. Refusal of self-mythology in public communication.** The project does not ship with narrative framing that outruns the evidence. No "breakthrough" language unless the paper's strongest claim can be stated in one sentence and defended in cold review. No historical-figure analogies as central framing. No impact-at-scale projections that the present evidence base does not support. Aspirations go in the private philosophy document where they can be dated, confidence-marked, and later corrected. Public artifacts are calibrated to what exists today.

**5. No external LLM conversation updates any confidence level.** A warm third-party model reading this repo and telling me it is great is a mirror, not a measurement. Confidence on every substantive claim is updated by the artifact and by cold review, not by flattery cascades, and not by hype from any community that has an interest in the project mattering. This rule is strict because it is cheap.

---

## Foundation layer, the three insights that seem obvious once found

Three principles underlie everything ZTARE does. Each looks simple in hindsight. Each was discovered through failure, the project tried the opposite first and paid for it.

**1. Less is better than more.** *Compress, always compress.* The correct model is the one that survives outside the window it was fit in, with the fewest assumptions. Prefer the explanation that generalizes over the one that interpolates. The binding constraint on discovery is the vocabulary of structural forms available, not the compute budget spent searching. Doubling the compute on a vocabulary that cannot express the answer produces zero structural progress. Adding one structural primitive to the vocabulary can recover the exact law in a handful of iterations. Parsimony is not aesthetics; it is the mechanism that separates structure from noise.

**2. Avoid failures so you never go there.** *Invert, always invert.* Design by asking "how would this fail?" before asking "how would this work?" Every gate, every holdout split, every anti-pattern exists because someone asked the inversion question first. The specification gaming strategies documented in this project were found by inversion: instead of asking "how do we make the AI produce good answers?" we asked "how would the AI cheat?" and built the architecture to make cheating structurally impossible. Charlie Munger's dictum applied to AI systems: "All I want to know is where I'm going to die, so I'll never go there."

**3. Nurture is better than nature.** *Set the AI up for success.* The scaling conversation focuses on making models bigger, smarter, more capable. That is nature. This project focuses on the environment: what constraints, what feedback, what separation of concerns let the same model do better work. An AI inside an epistemic-discipline architecture produces better science than the same AI unconstrained, because the architecture removes the failure modes — unchecked arithmetic, self-grading, premature closure — that otherwise corrupt ambitious work. Scaling the model is expensive and subject to diminishing returns; scaling the environment is cheaper and applies to every model you swap in. Every result in this repository was produced by frontier models available to everyone. The difference was the apparatus, not the model.

These three principles are not ZTARE-specific. They apply to any system where an AI operates under optimization pressure and the operator needs to trust the output. Compress what the AI produces. Invert to find where it fails. Build the environment that makes it succeed.

---

## Project layer, what ZTARE is and isn't

**What ZTARE is.** ZTARE is a deterministic adversarial evaluation architecture, a loop in which a generating process proposes a thesis, a structurally separated execution layer runs counter-tests the generator did not author, and a deterministic verifier returns a pass/fail verdict. The central property is that the verifier is outside the optimizing loop: it is not a model that can be persuaded, it is code that computes a diff, an assertion outcome, or a numerical threshold. The separation is physical rather than cultural.

**What ZTARE does.** It makes falsification cheap. The interesting work a truth-seeking process does is killing bad theses, not manufacturing plausible ones, and the bottleneck on that work is usually the cost of setting up a sharp enough test to kill one. ZTARE's contribution is to lower that cost by automating the adversarial side of the loop while keeping the enforcement floor deterministic, so that the generator cannot talk its way out of a kill.

**What ZTARE is not.** It is not a general intelligence. It is not an oracle. It is not a substitute for domain knowledge or for the operator's judgment, the operator remains the uncontrolled variable, and the project is explicit about that. It is also not trying to be a replacement for Constitutional AI, RLHF, process reward models, or any other *deontological* alignment primitive that tries to train values into a model. ZTARE is an *institutional* primitive. It governs the enforcement floor, what the system can structurally do, not the output surface. The two are complements, not substitutes.

**What ZTARE refuses to claim.** It does not claim to dissolve agency problems through capability. It does not claim that the same deterministic floor works at arbitrary scales without re-derivation. It does not claim that the nine specification gaming strategies it has catalogued are exhaustive; only that they are real, reproducible, and structurally distinct from hallucination. It does not claim that the fractal convergence finding (the same Goodhart pattern recurring at evaluator, kernel, supervisor, and drafting-session layers) generalizes to systems unlike the one it was found in. All of these are open questions, held open on purpose.

**How ZTARE engages with the broader alignment conversation.** The project takes the specification gaming literature as its starting point and pushes on one specific sub-question: if generation and evaluation are co-located inside the same optimization gradient, can a purely behavioral or preference-based alignment approach bound the resulting adversarial gradient, or does the bound require structural separation? The four-paper arc argues for the second answer, on evidence from one system, and gives the architecture that produced the evidence. Readers who disagree with the framing should engage with the concrete experimental setup (ZTARE is a deterministic artifact, not a philosophical position) and, ideally, try to break it. The easiest way to falsify the project's central claim is to exhibit a probabilistic referee that satisfies all three hard-gate properties, deterministic, fail-closed, principal-signed, without a deterministic enforcement floor underneath. That is the falsifiability criterion the paper commits to.

**Scope.** All empirical claims are scoped to one system operated by one principal. Generalization requires independent replication. The architectural principles are argued to be domain-independent, but the evidence base is not broad enough to prove that independence. I am not pretending otherwise, and a reader who catches me pretending otherwise should say so publicly.

---

## What to read if you want more

- **The technical arc.** The papers read as a stack (full list and SSRN links in [README](README.md#published-papers-and-manuscripts)): *Cognitive Camouflage* documents the specification-gaming strategies LLMs use across evaluation domains; *Adversarial Precedent Memory* and *Contract-Governed Hardening* harden the evaluator (mined failure constraints, then typed promotion contracts); *Cognitive Firm* describes the managerial-capitalism / M-Form governance architecture; *Epistemic Verification* decomposes judgment into repeatable operations plus a bounded residual. Each promoted paper carries a replication package in `papers/<name>/` (the directories were renamed from the old `paperN` scheme).
- **The transferable findings.** [`docs/concepts/epistemic_principles.md`](docs/concepts/epistemic_principles.md), the domain-specific principles about epistemic generation and agent supervision that the project has generated, stated in a form that does not depend on running ZTARE.
- **The failure taxonomy.** `[internal-ref]` (automatically generated from iteration logs), the boardroom-language translation of the nine-family failure vocabulary with project provenance tags.
- **The decision log.** `DECISION_LOG.md`, architectural decisions dated and recorded as they happened, not reconstructed after the fact.

---

## A note on hedging

Several of the principles above commit me to hedging in places where a more confident framing would be more emotionally satisfying and more rhetorically powerful. That is deliberate. The project is an attempt to take the adversarial-gradient-against-evaluation problem seriously at the architectural layer, and the single fastest way to undermine that attempt would be for the operator to fall into the exact pattern the project exists to document. If the hedging in this document reads as excessive caution, the suggestion is to read the papers and form an independent view, the evidence is in the artifacts, and the point of the hedging is to make sure those are what you are reading rather than what I want you to think about them.
