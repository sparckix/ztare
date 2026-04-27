# GP-120 — Should ZTARE Add a Bridger Agent?

**Status:** ANSWERED — Don't add. Enrich constraint ledger instead.
**Opened:** 2026-04-22
**Category:** Apparatus / Governance / Integration
**Origin:** Emily Tedards (HBS) suggestion: "What if you also added agents
that had 2+ specialist domains — bridgers at the intersection?"

*All panelist names are fictitious personas used as adversarial reasoning
lenses, not real individuals or endorsements.*

## Eigenquestion

The M-Form has specialists (Mutator, Judge) and an auditor (Inverter).
Should it also have a bridger — a T-shaped or Pi-shaped agent at the
intersection of generation and evaluation that facilitates integration?

## Panel (Lawrence / Wenger / Tushman / Munger / Karpathy)

### Lawrence (Differentiation & Integration)

The constraint ledger is a sophisticated "paper integrator" — a typed,
deduplicated, severity-graded, source-traced artifact with promotion
and demotion protocols. It exceeds what most human organizations achieve
for integration. The question is whether the system has hit the limits
of artifact-based integration. No evidence of that yet.

The interpretation gap IS real: the mutator receives a constraint like
"ESM permanence must be separated from automaticity" and must figure
out for itself what that means. A bridger could specify the
interpretation. But who audits the bridger's interpretation? (Munger's
rebuttal — see below.)

**Verdict: DON'T ADD.** Enrich the constraint ledger's expressiveness.

### Wenger (Communities of Practice)

The constraint ledger is a well-designed BOUNDARY OBJECT — an artifact
that sits at the intersection of practices, interpreted differently by
each community but maintaining enough shared structure to enable
coordination. The mutator reads it as "rules I must satisfy," the judge
reads it as "patterns I have confirmed." Same artifact, different
frames, productive coordination.

A BROKER (Wenger's term for the bridger) is necessary when boundary
objects fail — when the practices have become so differentiated that
the shared artifact cannot carry the translation load. No evidence of
that failure in the current system.

**Verdict: DON'T ADD.** Improve boundary objects before adding a broker.

### Tushman (Boundary Spanning)

Four boundary-spanning functions exist in organizations:
- Representative (carrying info): constraint ledger ✓
- Scout (monitoring environment): structural constraint extractor ✓
- Guard (controlling flow): OS Layer ✓
- Interpretive (translating): GP-113 feedback loop (partial) ✓

All four are covered. The bridger maps to interpretive spanning, which
is real and valuable. But effective boundary spanners need EARNED
CREDIBILITY in both practices through direct participation. An LLM
agent prompted into both vocabularies has prompted participation,
not earned participation — the McKinsey consultant failure mode.

**Verdict: DEFER.** Real function, wrong mechanism. Wait for evidence
of systematic miscommunication that artifact enrichment cannot fix.

### Munger (Inversion)

Three failure modes of the bridger:

1. **Consultant failure mode.** The bridger learns what language makes
   judges happy and what framing makes mutators productive. In the
   short run: integration. In the long run: Arthur Andersen. A
   consulting arm that teaches clients to satisfy auditors without
   changing substance.

2. **Narrative integration without testable claims.** The Inverter
   distinguishes Mode 1 (generate the doubt) from Mode 2 (convert to
   test). The bridger would be all Mode 1 — "the mutator meant X, the
   judge wanted Y, here is how to reconcile" — without any test for
   whether the reconciliation is substantive or cosmetic.

3. **Unauditable interpretation layer.** The constraint ledger's
   integration is deterministic and auditable. The bridger replaces
   an observable gap (did the mutator understand?) with an unobservable
   gap (did the bridger translate faithfully?).

"You have replaced a gap you can observe with a gap you cannot observe."

**Verdict: DON'T ADD.** The bridger collapses the generation-evaluation
boundary that Paper 4 says is load-bearing. It directly contradicts
the paper's central claim.

### Karpathy (Practical ML)

The bridger is adding another LLM call to the inner loop. Three costs:
latency, tokens, error surface. Five integration mechanisms already
exist. Before adding a sixth, show that all five are maxed out.

The useful parts of the bridger (constraint disambiguation, failure-family
matching) are all deterministic. The parts requiring an LLM (vocabulary
translation, shared mental model) are exactly the parts that create
co-location risk. Keep the useful parts deterministic, skip the rest.

Specific alternative: extend GP-113 to trigger on ALL gate failure types,
not just PERSIST_GRAMMAR_EXHAUSTED.

**Verdict: DON'T ADD.** Improve GP-113 and the constraint ledger instead.

## Joint Recommendation: DON'T ADD

Unanimous on the agent form; 4-to-1 on outright rejection (Tushman defers).

### Three points of agreement:

1. The integration gap Emily identified IS REAL. There is an unaudited
   interpretation step between judge constraints and mutator understanding.

2. The correct response is ARTIFACT ENRICHMENT, not AGENT ADDITION.
   Extend the constraint ledger to carry not just the constraint text
   but also the failure family, the triggering mechanism, and what a
   compliant vs non-compliant response looks like.

3. A probabilistic bridger inside the loop ERODES Paper 4's central claim.
   The paper argues structural separation is load-bearing. A co-located
   LLM that sees both proposals and evaluations is a U-Form seam in an
   M-Form architecture.

### Concrete alternative (Karpathy's three-step proposal):

**Step 1:** Extend GP-113 to fire on ALL gate failure types, not just
grammar exhaustion. Currently fires only on PERSIST_GRAMMAR_EXHAUSTED.

**Step 2:** Add a deterministic "constraint addressing" audit: for each
confirmed constraint, track whether the latest mutator proposal's text
contains the constraint's failure family vocabulary. Surface un-addressed
constraints as a structured prompt section.

**Step 3:** If Steps 1-2 are insufficient after 50+ iterations of evidence,
revisit with the specific iteration data showing where artifact-based
integration failed.

## Connection to Emily's T-Shaped / Pi-Shaped Framing

Emily's insight was correct but the solution is different from what she
proposed:

| Shape | ZTARE Implementation |
|-------|---------------------|
| I-shaped specialists | Mutator (generation), Judge (evaluation) |
| T-shaped (via artifacts) | Constraint ledger makes each specialist read the other's output |
| Pi-shaped auditor | Inverter (GP-119) — deep in both + inversion |
| Bridger | NOT a new agent — the constraint ledger IS the bridger |

The T-shaping happens through shared artifacts, not through agent
capability. This is a structural solution: rather than requiring each
specialist to develop cross-functional expertise (which would erode
differentiation), the architecture makes each specialist's output
legible to the other through typed, deterministic channels.

## What to Implement

1. **Extend GP-113 trigger scope** — fire on all gate failure types,
   not just PERSIST_GRAMMAR_EXHAUSTED. Medium priority.
   Location: `src/ztare/fit/diagnosis_feedback.py`

2. **Add "constraint addressing" audit** — deterministic check: does
   the latest thesis mention each confirmed constraint's failure family?
   Surface un-addressed constraints prominently in the mutator prompt.
   Medium priority.
   Location: `src/ztare/validator/autoresearch_loop.py` (prompt builder)

3. **Do NOT add a probabilistic bridger agent.** The integration gap
   is real but the fix is artifact enrichment, consistent with the
   M-Form's deterministic governance principle.

## Checklist

- [x] Multi-panel debate (Lawrence/Wenger/Tushman/Munger/Karpathy)
- [x] Verdict: DON'T ADD the bridger agent
- [x] Alternative: three-step constraint ledger enrichment
- [ ] Implement Step 1: extend GP-113 trigger scope
- [ ] Implement Step 2: constraint addressing audit
- [ ] Log in Paper 4 §7.3 (T-shaped/Pi-shaped framing — DONE)

---

*Fictitious personas used as adversarial reasoning lenses.
No claim of endorsement by any real person.*
