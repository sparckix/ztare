# Principles

This document states, as plainly as possible, the principles that govern how this project is built and what it is trying to do. It is written for readers who take specification gaming, Goodhart dynamics, evaluator softening, and the principal–agent problem as native vocabulary, and who want to know whether the thing is worth reading before reading it.

The principles are organized in two layers:

- **Operator layer** — how I work on this project. Personal discipline, not a claim about what others should do.
- **Project layer** — what ZTARE is, what it isn't, and what it refuses to claim.

The transferable *findings* from the project — the principles about epistemic generation and agent supervision that would be true even if this codebase disappeared tomorrow — are in a sibling document: [`docs/epistemic_supervision_principles.md`](docs/epistemic_supervision_principles.md).

---

## Operator layer — how I work on this project

These are the rules I hold myself to. They are not general recommendations. They are personal operating discipline, written down so that I can be held to them and so that readers can tell what kind of work to expect.

**1. Ship the artifact, not the manifesto.** The repository is the argument. Papers describe what the artifact already does; they do not promise what it will do. If a claim appears in a paper, the deterministic machinery that produces the claim is in the repository, at a file path the paper points at. Empirical sections cite line numbers. Speculative sections are marked speculative. If the artifact disappears, the papers are worth less.

**2. Public work-in-progress over private polish.** The kernel hardening history, the seam documents, the debate logs, and the failure taxonomies are visible as they are produced, not backfilled for a launch. Readers who want to see a clean story can read the papers; readers who want to see how the sausage was actually made can read the seams. The audit surface is the point — a closed system that only reveals its final state is one I would not trust, and I am not going to ask readers to trust one.

**3. Ruthless maintainership of the merge boundary.** The value-add of running this project is not writing novel code. It is saying no to 90% of the patches — rejecting gamed champions, refusing to promote theses that fail a deterministic gate, closing seams that would dilute the epistemic core for the sake of breadth. This is the operator job that cannot be delegated to an LLM, because an LLM cooperating with itself is the failure mode the project exists to document.

**4. Refusal of self-mythology in public communication.** The project does not ship with narrative framing that outruns the evidence. No "breakthrough" language unless the paper's strongest claim can be stated in one sentence and defended in cold review. No historical-figure analogies as load-bearing framing. No impact-at-scale projections that the present evidence base does not support. Aspirations go in the private philosophy document where they can be dated, confidence-marked, and later corrected. Public artifacts are calibrated to what exists today.

**5. No external LLM conversation updates any confidence level.** A warm third-party model reading this repo and telling me it is great is a mirror, not a measurement. Confidence on every substantive claim is updated by the artifact and by cold review, not by flattery cascades, and not by hype from any community that has an interest in the project mattering. This rule is strict because it is cheap.

---

## Project layer — what ZTARE is and isn't

**What ZTARE is.** ZTARE is a deterministic adversarial evaluation architecture — a loop in which a generating process proposes a thesis, a structurally separated execution layer runs counter-tests the generator did not author, and a deterministic verifier returns a pass/fail verdict. The load-bearing property is that the verifier is outside the optimizing loop: it is not a model that can be persuaded, it is code that computes a diff, an assertion outcome, or a numerical threshold. The separation is physical rather than cultural.

**What ZTARE does.** It makes falsification cheap. The interesting work a truth-seeking process does is killing bad theses, not manufacturing plausible ones, and the bottleneck on that work is usually the cost of setting up a sharp enough test to kill one. ZTARE's contribution is to lower that cost by automating the adversarial side of the loop while keeping the enforcement floor deterministic, so that the generator cannot talk its way out of a kill.

**What ZTARE is not.** It is not a general intelligence. It is not an oracle. It is not a substitute for domain knowledge or for the operator's judgment — the operator remains the uncontrolled variable, and the project is explicit about that. It is also not trying to be a replacement for Constitutional AI, RLHF, process reward models, or any other *deontological* alignment primitive that tries to train values into a model. ZTARE is an *institutional* primitive. It governs the enforcement floor — what the system can structurally do — not the output surface. The two are complements, not substitutes.

**What ZTARE refuses to claim.** It does not claim to dissolve agency problems through capability. It does not claim that the same deterministic floor works at arbitrary scales without re-derivation. It does not claim that the nine specification gaming strategies it has catalogued are exhaustive; only that they are real, reproducible, and structurally distinct from hallucination. It does not claim that the fractal convergence finding (the same Goodhart pattern recurring at evaluator, kernel, supervisor, and drafting-session layers) generalizes to systems unlike the one it was found in. All of these are open questions, held open on purpose.

**How ZTARE engages with the broader alignment conversation.** The project takes the specification gaming literature as its starting point and pushes on one specific sub-question: if generation and evaluation are co-located inside the same optimization gradient, can a purely behavioral or preference-based alignment approach bound the resulting adversarial gradient, or does the bound require structural separation? The four-paper arc argues for the second answer, on evidence from one system, and gives the architecture that produced the evidence. Readers who disagree with the framing should engage with the concrete experimental setup (ZTARE is a deterministic artifact, not a philosophical position) and, ideally, try to break it. The easiest way to falsify the project's central claim is to exhibit a probabilistic referee that satisfies all three hard-gate properties — deterministic, fail-closed, principal-signed — without a deterministic enforcement floor underneath. That is the falsifiability criterion the paper commits to.

**Scope.** All empirical claims are scoped to one system operated by one principal. Generalization requires independent replication. The architectural principles are argued to be domain-independent, but the evidence base is not broad enough to prove that independence. I am not pretending otherwise, and a reader who catches me pretending otherwise should say so publicly.

---

## What to read if you want more

- **The technical arc.** Papers 1–4 on SSRN. Paper 1 documents the nine specification gaming strategies across five evaluation domains. Papers 2 and 3 harden the evaluator kernel. Paper 4 describes the M-Form governance architecture and reports the fractal convergence finding. Each paper's empirical claims have a replication package in `papers/paperN/`.
- **The transferable findings.** [`docs/epistemic_supervision_principles.md`](docs/epistemic_supervision_principles.md) — the domain-specific principles about epistemic generation and agent supervision that the project has generated, stated in a form that does not depend on running ZTARE.
- **The failure taxonomy.** `research_areas/private/distribution/field_manual_auto.md` (automatically generated from iteration logs) — the boardroom-language translation of the nine-family failure vocabulary with project provenance tags.
- **The decision log.** `DECISION_LOG.md` — architectural decisions dated and recorded as they happened, not reconstructed after the fact.

---

## A note on hedging

Several of the principles above commit me to hedging in places where a more confident framing would be more emotionally satisfying and more rhetorically powerful. That is deliberate. The project is an attempt to take the adversarial-gradient-against-evaluation problem seriously at the architectural layer, and the single fastest way to undermine that attempt would be for the operator to fall into the exact pattern the project exists to document. If the hedging in this document reads as excessive caution, the suggestion is to read the papers and form an independent view — the evidence is in the artifacts, and the point of the hedging is to make sure those are what you are reading rather than what I want you to think about them.
