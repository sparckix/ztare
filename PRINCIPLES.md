# Principles

Use this page to decide what kind of project ZTARE is and what discipline its
maintainer is committing to.

The rule is simple: a model-produced result is not a claim. A serious claim
needs local sources, a check that can fail, a deterministic floor where one is
available, and a clear statement of what the evidence does not prove.

The principles are organized in two layers:

- **Maintainer layer**, how I work on this project. Personal discipline, not a
  claim about what others should do.
- **Project layer**, what ZTARE is, what it is not, and what it refuses to
  claim.

The transferable findings from the project live in
[`docs/concepts/epistemic_principles.md`](docs/concepts/epistemic_principles.md):
principles about epistemic generation and agent supervision that should remain
useful even outside this codebase.

---

## Maintainer layer, how I work on this project

These are the rules I hold myself to. They are personal operating discipline,
written down so readers can tell what kind of work to expect.

**1. Ship the artifact, not the manifesto.** The repository is the argument.
Papers describe what the artifact already does; they do not promise what it
will do. If a claim appears in a paper, the machinery that supports it should
exist in the repository at a path the paper can name. Empirical sections cite
artifacts. Speculative sections are marked speculative.

**2. Public work-in-progress over private polish.** The hardening history,
design notes, debate logs, and failure taxonomies are visible as they are
produced, not backfilled for a launch. Readers who want the cleanest story can
read the papers; readers who want the operating record can inspect the
artifacts. The audit surface is the point: I would not trust a system that only
reveals its final state, and I am not going to ask readers to trust one.

**3. Maintain the merge boundary.** The maintainer job is deciding what does not
enter: gamed champions, overbroad theses, unsupported claims, and patches that
add breadth while weakening the claim discipline. This cannot be delegated to
the same model loop being supervised.

**4. Refusal of self-mythology in public communication.** The project does not
ship narrative framing that outruns the evidence. No "breakthrough" language
unless the strongest public claim can be stated in one sentence and defended
from artifacts. No historical-figure analogies as central framing. No
impact-at-scale projections that the present evidence base does not support.
Public artifacts are calibrated to what exists today.

**5. No external LLM conversation updates any confidence level.** A warm
third-party model reading this repo and praising it is a mirror, not a
measurement. Confidence on every substantive claim is updated by artifacts,
runnable checks, and cold review, not by approval from a model or community
that has an interest in the project mattering. This rule is strict because it
is cheap.

---

## Foundation layer, three working rules

Three rules underlie the project. Each came from a failure where the opposite
rule looked attractive and then broke.

**1. Compress first.** The better explanation is the one that survives outside
the window it was fit in with fewer assumptions. Discovery is usually limited
by the available vocabulary of structural forms, not by raw search effort. More
compute over the wrong vocabulary produces more attempts, not more structure.
A small declared primitive set can be stronger than a large loose language when
the system can compose inside it and reject vocabulary escapes.

**2. Invert before building.** Ask how the system would fail before asking how
it would succeed. Most checks in this repository exist because a plausible
failure was named first: missing evidence, stale artifacts, self-grading,
cosmetic novelty, or a report that cites a result it no longer holds.

**3. Design the environment.** Model capability matters, but the environment
decides what the model can get away with. Constraints, feedback, separated
roles, review records, and fail-closed checks often improve output more
reliably than swapping one frontier model for another.

These rules are not ZTARE-specific. They apply to any system where an AI works
under optimization pressure and a human needs to trust the output: compress the
claim, invert the failure, and design the environment that forces better work.

---

## Project layer, scope and refusals

**What ZTARE is.** ZTARE is a local workbench for checking claims. A generator
can propose a thesis, but the claim has to pass through source binding,
counter-tests, review records, and deterministic checks where those checks
exist. The important rule is separation: the checker is not the same process
that is trying to win the check.

**What ZTARE does.** It makes bad claims cheaper to catch. A useful system
should make it easy to reject a weak thesis, narrow an overbroad claim, or name
the next source that would change the verdict. The goal is not more fluent
answers. The goal is a claim state that can be inspected later.

**What ZTARE does not replace.** It is not a general intelligence, an oracle, a
substitute for domain knowledge, or a substitute for accountable review. It
does not replace model-alignment work that tries to improve the model itself.
ZTARE works on the surrounding process: what may be proposed, what must be
checked, what gets recorded, and what cannot be promoted without evidence.

**What ZTARE refuses to claim.** It does not claim to dissolve agency problems
through capability. It does not claim that the same deterministic floor works
at arbitrary scales without re-derivation. It does not claim that the nine
specification-gaming strategies it has catalogued are exhaustive; only that
they are real, reproducible, and structurally distinct from hallucination. It
does not claim that the same Goodhart pattern recurring at evaluator, kernel,
supervision, and drafting layers generalizes to systems unlike the one it was
found in. Those remain open questions.

**How ZTARE engages with the broader alignment conversation.** The project
starts from specification gaming: if generation and evaluation sit inside the
same pressure, a system can learn to satisfy the score without answering the
question. ZTARE tests one response to that problem: separate the proposal,
check, record, and promotion steps. Readers who disagree should engage with the
concrete artifacts, not the framing. A strong falsifier would be a probabilistic
referee that is deterministic at the enforcement boundary, fail-closed on
missing evidence, and accountable without relying on a separate deterministic
floor underneath.

**Scope.** All empirical claims are scoped to one maintained system and its
public artifacts. Generalization requires independent replication. The
architectural principles may transfer, but the evidence base is not broad
enough to prove broad transfer. A reader should treat every general statement
as a hypothesis until another implementation reproduces the result.

---

## What to read if you want more

- **The technical arc.** The papers read as a stack (full list and SSRN links in
  [README](README.md#published-papers)): *Cognitive Camouflage* documents the
  specification-gaming strategies LLMs use across evaluation domains;
  *Adversarial Precedent Memory* and *Contract-Governed Hardening* harden the
  evaluator through mined failure constraints and typed promotion contracts;
  *Cognitive Firm* describes role and gate separation for AI work; *Epistemic
  Verification* decomposes judgment into repeatable operations plus a bounded
  residual. Each promoted paper carries a replication package in
  `papers/<name>/`.
- **The transferable findings.** [`docs/concepts/epistemic_principles.md`](docs/concepts/epistemic_principles.md), the domain-specific principles about epistemic generation and agent supervision that the project has generated, stated in a form that does not depend on running ZTARE.
- **The failure taxonomy.** [Anti-pattern catalog](docs/concepts/anti_pattern_catalog.md)
  and [gaming behavior catalog](docs/gaming_behavior_catalog.md), the public
  field guides for recurring failure modes and the checks that catch them.
- **The decision log.** `DECISION_LOG.md`, architectural decisions dated and
  recorded as they happened, not reconstructed after the fact.

---

## A note on hedging

Several of the principles above force caution where a more confident framing
would be easier to sell. That is deliberate. The project studies how systems
learn to satisfy evaluation without answering the underlying question; the
public writing should not repeat that mistake. If the hedging here reads as
excessive caution, read the artifacts and form an independent view.
