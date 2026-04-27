# GP-119 — The Missing Third Role: Mechanizing the Inverter

**Status:** OPEN
**Opened:** 2026-04-22
**Category:** Apparatus / Engine / Architecture

## Eigenquestion

The GP-116 session produced 6 insights (INS-036 through INS-041).
The operator's honest assessment revealed that the human contributed
ROUTING, not INVERSION. The inversions came from Gemini Pro. The
measurements came from Claude. The human was a message bus.

Can the Inverter role be mechanized as a third agent in the
autoresearch loop, eliminating the human routing bottleneck?

## The Three-Role M-Form (Discovered Organically)

The current autoresearch_loop has two roles:
- **Mutator:** proposes hypotheses (LLM, creative)
- **Judge:** evaluates hypotheses (LLM, critical)

GP-116 revealed a third role that emerged in the conversation:
- **Inverter:** receives findings, generates counter-hypotheses,
  proposes falsification experiments, identifies measurement artifacts

In the GP-116 session, this role was played by Gemini Pro via the
operator. The operator's contribution was copy-pasting between
Claude and Gemini. This is mechanizable.

## What the Inverter Did (GP-116 Session Log)

| Finding | Inverter's Response | Result |
|---------|-------------------|--------|
| "Rank 1.8 bottleneck" | "What about BOS contamination?" | BOS artifact confirmed |
| "99.1% management fee" | "You're mixing granularities" | ROC corrected to 55% |
| "72% cancellation = waste" | "Run the null model" | Cancellation is architectural |
| "N^(-0.6) scaling law" | "That's Von Neumann's elephant" | Confound with depth identified |
| "The bottleneck is compressible" | "That's the residual stream, not computation" | Panel caught 5 flaws |
| "Mamba also has 62% cancellation" | "Is that less because of SSM or training?" | Null model showed training reduces it |

Every major correction in the session came from the Inverter, not
the Executor or the Judge. The existing loop (mutator + judge) would
have published "rank 1.8 bottleneck" and "99.1% management fee"
as findings. The Inverter killed them.

## Architecture Proposal

```
                    ┌─────────────┐
                    │  Principal   │
                    │  (human)     │
                    └──────┬──────┘
                           │ signs contracts, resolves gates
                    ┌──────┴──────┐
                    │  OS Layer    │
                    │  (deterministic) │
                    └──────┬──────┘
              ┌────────────┼────────────┐
              │            │            │
       ┌──────┴──────┐ ┌──┴───┐ ┌──────┴──────┐
       │  Mutator     │ │Judge │ │  Inverter    │
       │  (proposes)  │ │(evals)│ │  (falsifies) │
       │  Model A     │ │Mdl B │ │  Model C     │
       └──────────────┘ └──────┘ └──────────────┘
```

The Inverter agent:
1. Receives each finding (champion thesis, compression result, 
   measurement output)
2. Generates counter-hypotheses ("what if this is an artifact of X?")
3. Proposes specific falsification tests ("run the null model",
   "check BOS norms", "test on a different architecture")
4. The OS Layer routes the proposed tests to the Executor
5. Results feed back to the Inverter for further inversion

### Key Design Constraints

- The Inverter MUST be a different model from the Mutator and Judge
  (cross-model diversity prevents shared blind spots)
- The Inverter MUST NOT have access to the ground truth or the
  rubric (it operates on findings, not on the evaluation framework)
- The Inverter's output is PROPOSALS, not ACTIONS (the OS Layer
  decides whether to execute them)
- The Inverter should be prompted with Munger-style inversion:
  "What would make this finding wrong? What artifact could produce
  this result? What is the cheapest test that would kill it?"

### Existing Infrastructure That Maps

| Component | Current | Inverter Extension |
|-----------|---------|-------------------|
| GP-113 failure feedback | Injects diagnosis into mutator | Extend: inject into Inverter |
| GP-112 margin-of-safety | Post-compression stress test | The Inverter IS the pre-publication stress test |
| Bounded critique agent (memory) | Read-only Explore agent on artifacts | The Inverter is the persistent version |
| Panel debates | Ad-hoc Agent spawns | The Inverter replaces ad-hoc panels |
| GP-072 Division A/B | Information isolation between roles | Inverter is Division C |

### The bounded_critique_agent memory already describes this:

> "Before finalizing seam/spec fixes, spin a read-only Explore agent
> with only the artifact + problem statement; no run history; catches
> overfitting and frustration-anchored diagnosis"

The Inverter is the PERSISTENT, AUTOMATED version of this. Instead
of the operator remembering to spawn a critique agent, the OS Layer
spawns one after every finding.

## Architectural Placement: Inside GP-070, Not Alongside It

GP-070 (Meta-Supervisor Goal Orchestrator) is the Chandlerian
"general office" that routes between runners. GP-071 (Executive
Inbox) is how the human resolves gates. The Inverter is NOT a
new top-level component. It is a POST-CHAMPION HOOK inside the
science_sandbox module of GP-070.

```
GP-070 Goal Orchestrator
  └── science_sandbox module
        ├── autoresearch_loop (mutator + judge)
        ├── compress_champion (deterministic gates)
        ├── margin_of_safety (GP-112, post-compression)
        ├── diagnosis_feedback (GP-113, constraint injection)
        └── ★ INVERTER (GP-119, post-champion)
              ├── auto-battery: null model, confound check
              ├── if kill → inject constraint, continue loop
              ├── if confirm → log to insights ledger
              └── if ambiguous → escalate to GP-071 Inbox
```

The Inverter sits AFTER champion promotion, not during the thesis
loop. It fires when a new champion is crowned and runs a battery
of falsification tests. This is the exact insertion point where
the GP-116 session's manual routing happened.

### Applies to BOTH tracks

- **Science track** (GP-116): "is this compression an artifact?"
  Battery: null model comparison, cross-architecture replication,
  confound identification
- **General-purpose thesis track** (gp088, domain projects):
  "is this causal claim confounded?" Battery: rival hypothesis
  generation, evidence gap identification, overclaim detection

The Inverter prompt template is track-agnostic. The battery of
automated tests differs by track (science gets null model +
cross-arch; thesis gets rival + confound).

## Implementation Path

### Phase 1: Manual routing (current state, GP-116 pattern)
- Operator copies findings to a different model
- Different model generates inversions
- Operator copies inversions back
- THIS IS WHAT WE DID IN GP-116

### Phase 2: Post-champion hook in autoresearch_loop
- After champion promotion, auto-spawn Inverter agent
  (different model from mutator/judge)
- Inverter receives: champion thesis, compression result,
  evidence summary, current constraint ledger
- Inverter outputs: list of falsification proposals
- Each proposal tagged: {auto_testable, needs_human, needs_data}
- auto_testable proposals execute immediately (null model, etc.)
- needs_human proposals → GP-071 Executive Inbox
- Cost: one LLM call per champion promotion (~$0.03)
- Insert at: autoresearch_loop.py, after champion_eval_results
  is written and before the next iteration begins

### Phase 3: Standard diagnostic library
- A registry of auto-testable falsification tests:
  - null_model: instantiate architecture with random weights,
    compute same metric, compare
  - cross_architecture: if other model checkpoints available,
    run same diagnostic
  - granularity_check: recompute metric at different aggregation
    levels (per-token vs mean-pooled)
  - ablation: skip components and measure degradation
- The Inverter selects which tests to propose from this registry
- The OS Layer executes them deterministically

### Phase 4: Full three-role loop within GP-070
- GP-070 orchestrates: Mutator proposes → Judge evaluates →
  Champion promoted → Inverter falsifies → auto-tests run →
  results feed back to constraint ledger → next iteration
- Human's role: sign contracts, choose targets, resolve
  GP-071 inbox gates that require domain judgment
- The human is no longer the message bus between LLMs

## The GP-117 Connection

GP-117 asked "why does the pipeline kill but never discover?"
The answer is now clear: the pipeline kills because it has a Judge.
It doesn't discover because it lacks an Inverter. The Judge says
"this thesis is bad." The Inverter says "what if the measurement
is wrong?" The Judge operates within the current evidence. The
Inverter questions the evidence itself.

## The GP-118 Connection

The persona ablation experiment (GP-118) tests whether the Judge's
persona affects gaming behavior. The Inverter adds a new question:
does the INVERTER's persona affect the QUALITY of falsification?
A skeptical Inverter might catch more artifacts. An enthusiastic
Inverter might miss them. This is a second-order test.

## Checklist

- [ ] Design the Inverter prompt template (Munger-style inversion)
- [ ] Wire into autoresearch_loop as post-champion hook
- [ ] Test with GP-116 findings as historical replay
- [ ] Measure: does the Inverter catch the BOS artifact? The
      granularity mismatch? The scaling confound?
- [ ] If yes: mechanize the GP-116 session as a standard diagnostic
- [ ] If no: identify what the Inverter misses that requires human

---

*The operator's most important contribution to GP-116 was admitting
that the operator's most important contribution was routing.*
