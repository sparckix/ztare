# ZTARE Architecture

ZTARE keeps four things separate that most AI workflows collapse together:

1. **Collecting sources**: gathering raw material (documents, data, reports)
2. **Compiling evidence**: extracting the testable facts from those sources
3. **Adversarial validation**: having AIs argue over whether a claim holds up against the evidence
4. **Reporting**: turning the tested conclusions into audience-appropriate artifacts

The whole point of the architecture is that the AI proposing an answer never gets to grade itself, and the judge never gets to override hard numeric checks. If these separations break, the system degrades to "AI writing convincing essays about itself."

For a plain-English glossary of all terms, see [../concepts/glossary.md](../concepts/glossary.md).

## 0. Who This Document Is For

This repo now has two distinct audiences, and this document is heavier on the second one:

1. **General-purpose engine users**: you want to pressure-test a thesis on a domain (startup diligence, activist target, strategy question, research claim). You probably do not need most of this document. You need:
   - the system thesis in §1 (why state is not the enemy, but unearned trust is)
   - the four-layer boundary in §2
   - the workspace / compiler / validator / synthesis sections at a conceptual level
   - and then `docs/guides/workflow.md` §0b, §1-§5 for the actual loop
   You can ignore the V4 kernel hardening, primitive library internals, supervisor control plane, and program-birth chain sections. They are implementation concerns, not usage concerns.

2. **Developers / researchers playing with the engine**: you are modifying the validator, the workspace compiler, the V4 kernel, the primitive library, or the supervisor control plane. This document is written for you. Read it in order, and pair it with `supervisor/USER_MANUAL.md` for the control plane, `research_areas/HARDENING_BOARD.md` for the active seam list, and `docs/guides/workflow.md` §15 for the program hardening workflow.

If you are not sure which audience you are, start as a general-purpose user. The hardening machinery is orthogonal to using the engine on a domain project.

---

## 1. System Thesis

ZTARE is a **stateless adversarial validator**. It runs claims through an adversarial loop without remembering previous runs.

It sits between two layers that DO remember things:

1. A **workspace** upstream that accumulates source material over time
2. A **synthesis layer** downstream that turns results into reports

The key rule:

**Memory is fine. Unearned trust is the enemy.**

The workspace can grow and remember. But the validator never trusts previous conclusions just because they exist. Every run starts fresh from a bounded evidence snapshot. This prevents "the AI said it was right last time, so it must still be right."

---

## 1a. System Diagrams

Four diagrams: the full pipeline, the validator internals, cross-cutting services, and the separation invariants that hold the whole thing together.

### Figure 1: Full System Pipeline

```text
                    ╔═══════════════════════════════════════════╗
                    ║            OPERATOR  (human)               ║
                    ║                                            ║
                    ║  decides: what sources to ingest            ║
                    ║           what question to test             ║
                    ║           what rubric and model pairing     ║
                    ║           what iteration budget             ║
                    ║                                            ║
                    ║  gates:   evidence promotion (L2 → L3)     ║
                    ║           synthesis audience (L4)           ║
                    ║           program D-gate (control plane)    ║
                    ╚═════════════════════╤═════════════════════╝
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              v                           v                           v
    ┌──────────────────┐     ┌──────────────────┐      ┌──────────────────┐
    │    raw/ sources   │     │  project_charter  │      │   rubric JSON    │
    │                   │     │                   │      │                  │
    │  .md .txt .json   │     │  core question    │      │  scoring rules   │
    │  .csv .yaml .html │     │  forecast type    │      │  gate config     │
    │  .py .js .ts      │     │  anchor proxies   │      │  fit primitive   │
    │                   │     │  determ. gates ────│──┐   │  flags           │
    └────────┬─────────┘     └────────┬──────────┘  │   └────────┬─────────┘
             │                        │              │            │
    ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─
    L1: KNOWLEDGE WORKSPACE            │              │            │
    (Karpathy LLM Wiki adaptation)     │              │            │
                                       │              │            │
    update_workspace.py                │              │            │
      per-source extraction            │              │            │
      + cross-source merge             │              │            │
                                       │              │            │
    ──> workspace/                     │              │            │
        source_notes/*.json            │              │            │
        workspace_snapshot.json        │              │            │
        facts.md                       │              │            │
        contradictions.md              │              │            │
        open_questions.md              │              │            │
        candidate_claims.md            │              │            │
             │                         │              │            │
    ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─
    L2: EVIDENCE COMPILER              │              │            │
                                       │              │            │
    compile_evidence.py                │              │            │
    (mode: raw | workspace | auto)     │              │            │
                                       │              │            │
    ──> compiled_evidence.txt          │              │            │
    ──> compiled_evidence_packet.json  │              │            │
    ──> provenance.json                │              │            │
                                       │              │            │
    fail-closed on error               │              │            │
             │                         │              │            │
    ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─
             │                         │              │            │
    [operator promotes]                │              │            │
             │                         │              │            │
             v                         │              │            │
    ┌──────────────────┐               │              │            │
    │   evidence.txt   │◄── score      │              │            │
    │ (bounded snapshot)│   regime      │              │            │
    │                  │   fingerprints│              │            │
    └────────┬─────────┘               │              │            │
             │                         │              │            │
    ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─
    L3: ADVERSARIAL VALIDATOR          │              │            │
    (autoresearch_loop.py)             │              │            │
                                       │              │            │
    ┌────────┐  ┌───────────┐  ┌───────┴──┐  ┌───────┴────────────┴──┐
    │MUTATOR │─>│  SOLVER   │─>│  FRAMER  │─>│   CAGE ORCHESTRATOR    │
    │        │  │ fit_prim. │  │ canonical│  │   (GP-157 v5.0)        │
    │proposes│  │ 1D / N-D  │  │ (h_in,   │  │                        │
    │thesis +│  │ scipy     │  │  h_out)  │  │  16 gates, dispatched  │
    │code    │  │ multi-    │  │  match,  │  │  by substrate.meta     │
    │ + fit  │  │ start     │  │  raw-MDL │  │  ['class']; observe or │
    │ decl   │  │ [Kepler]  │  │ [GP-152] │  │  authoritative mode    │
    └──▲─────┘  └─────┬─────┘  └─────┬────┘  └──────────┬─────────────┘
       │              │              │                  │
       │              v              │                  v
       │       ┌──────────────┐      │        ┌────────────────────┐
       │       │ FIRING SQUAD │      │        │  META JUDGE        │
       │       │ 3 AIs attack │      │        │  scores exec       │
       │       │ weakest      │      │        │  output (Newton-   │
       │       │ assumptions  │      │        │  mode for          │
       │       └──────────────┘      │        │  generative yield) │
       │                             │        └─────────┬──────────┘
       │                             │                  │
       │                             v                  v
       │              ┌─────────────────────────────────────────┐
       │              │  HARD GATES (deterministic, fail-closed) │
       │              │  GP-030 charter gates + project harness  │
       │              │  + Cage POST_FIT gates                   │
       │              └──────────────────┬──────────────────────┘
       │                                  │
       │                                  v
       │              ┌─────────────────────────────────────────┐
       │              │  POST-CHAMPION STACK (on promotion)     │
       │              │  GP-119 Inverter (≥50)                  │
       │              │  G-CIRC + G-FALSIFY (mode=gate|both)    │
       │              │  GP-122 Lean REPL (≥70 + enable flag)   │
       │              │  GP-143 dynamical-lattice validation     │
       │              └──────────────────┬──────────────────────┘
       │                                  │
       │  ┌──────────────────────────────────┐
       │  │ STAGNATION ENGINE                 │
       │  │  stag >= 3: pivot profile inject  │
       │  │  stag >= 4: axiom purge           │
       │  │  V4 projects: bounded override    │
       │  └──────────────────────────────────┘
       │                                  v
       │  ┌──────────────────────────────────────────────────┐
       │  │ score improved?  ─ yes ─> promote to champion    │
       └──│ continue?        ─ yes ─> next iteration         │
          │ budget exhausted? ─ yes ─> exit loop              │
          └──────────────────────────────────────────────────┘

    OUTPUTS:                          FEEDBACK ──> workspace:
    thesis.md (updated)                latest_evidence_gaps.json
    debate_log_iter_*.md               champion_evidence_gaps.json
    history/*.md                       latest_constraint_proposals.json
    latest_eval_results.json           derived_constraints.json
    champion_eval_results.json         iteration_telemetry.jsonl
    fit_result*.json                   framing_report.json (GP-152)
    latest_* vs champion_*             cage_engagement.jsonl (GP-157)
                                       structural_blocker_gates_latest.json
                                         (G-CIRC + G-FALSIFY)
             │
    ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
    L4: SYNTHESIS PIPELINE
    (synthesize.py)

    sniff ──> history ──> ledger ──> brief ──> render ──> QA

    ┌────────────┐  ┌────────────┐  ┌─────────────────┐  ┌──────────┐
    │ledger.json │─>│ brief.json │─>│Report.candidate  │─>│ qa.json  │
    │ (canonical)│  │ (audience) │  │    .md (draft)   │  │ (gate)   │
    └────────────┘  └────────────┘  └─────────────────┘  └──────────┘
                                                                │
                                            QA passes? ─ yes ─> Report.md
                                                    no ─> inspect candidate

    Renderers:
      founder_memo | decision_brief | architectural_memo
      research_note | quantitative_appendix | field_manual
```

### Figure 2: Feedback Loops

```text
    The system has three feedback loops. All are human-gated.

    ┌───────────────┐                      ┌───────────────┐
    │   VALIDATOR    │  evidence_gaps.json  │   WORKSPACE   │
    │   (L3)        │─────────────────────>│   (L1)        │
    │               │  constraint_         │               │
    │               │  proposals.json      │  operator     │
    │               │─────────────────────>│  decides what │
    │               │                      │  enters raw/  │
    │               │  derived_            │  and what gets│
    │               │  constraints.json    │  promoted     │
    │               │─────────────────────>│               │
    └───────────────┘                      └───────┬───────┘
                                                   │
                                          [compile + promote]
                                                   │
                                                   v
                                           ┌───────────────┐
                                           │ evidence.txt   │
                                           │ (next run)     │
                                           └───────────────┘

    ┌───────────────┐                      ┌───────────────┐
    │   VALIDATOR    │  debate logs,        │   GLOBAL      │
    │   (L3)        │  history files        │  PRIMITIVES   │
    │               │─────────────────────>│               │
    │               │  extract_incidents    │  incidents/   │
    │               │                      │  ──> review/  │
    │               │  approved primitives  │  ──> approved/│
    │               │<─────────────────────│               │
    │               │  (attacker/judge side)│  [human gate] │
    └───────────────┘                      └───────────────┘
```

### Figure 3: Cross-Cutting Services

```text
    ┌───────────────────────────────────────────────────────────────────┐
    │ PROVIDER RUNTIME  (src/ztare/common/llm_runtime.py)               │
    │                                                                   │
    │  model-family ──> model-id resolution                             │
    │  retry + transient-error handling                                 │
    │  cross-provider failover on persistent outages                    │
    │  token-usage extraction (Gemini / Anthropic / OpenAI)             │
    │  pricing normalization via supervisor/model_pricing.json          │
    │                                                                   │
    │  Consumed by: L1 workspace | L2 compiler | L3 validator |         │
    │               L4 synthesis | supervisor wrappers                  │
    └───────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────┐
    │ GLOBAL PRIMITIVES  (global_primitives/)                           │
    │ Cross-project adversarial precedent memory                        │
    │                                                                   │
    │  debate logs ──> extract_incidents ──> incidents/*.jsonl           │
    │  ──> draft_primitives ──> review/                                 │
    │  ──> [human promotes/rejects] ──> approved/                       │
    │                                                                   │
    │  Validator flags:                                                 │
    │    --use_primitives            attacker/judge side (safe default)  │
    │    --use_transfer_hypotheses   + mutator side (opt-in, stronger)   │
    │                                                                   │
    │  Never injected as evidence.  Never treated as axioms.            │
    └───────────────────────────────────────────────────────────────────┘
```

### Figure 4: Control Plane (Orthogonal to Data Pipeline)

```text
    ┌───────────────────────────────────────────────────────────────────┐
    │ SUPERVISOR  (supervisor/)                                         │
    │                                                                   │
    │  Decides: what work exists, who does it, what's in scope          │
    │  Does NOT decide: epistemic truth                                 │
    │                                                                   │
    │  seeds/                                                           │
    │  (active | deferred | legacy)                                     │
    │       │                                                           │
    │       v                                                           │
    │  seed_registry.json                                               │
    │       │                                                           │
    │  [human accepts] ──> program_genesis/ (immutable birth contracts) │
    │                           │                                       │
    │                           v                                       │
    │                      program_registry.json                        │
    │                           │                                       │
    │                           v                                       │
    │       ┌────────────────────────────────────────────────┐           │
    │       │  SUPERVISOR LOOP                               │           │
    │       │                                                │           │
    │       │   A1 ───> A2 ───> B ───> C ───> [D]          │           │
    │       │  (debate) (spec) (build) (verify) (human gate) │           │
    │       │                                                │           │
    │       │   optional: A2 ──> A1 refinement (≤ 2 rounds) │           │
    │       └───────────────────────────────────────────────┘           │
    │                                                                   │
    │  agent_wrappers.json     model_pricing.json                       │
    └───────────────────────────────────────────────────────────────────┘
```

### Figure 5: Separation Invariants

```text
    The system's integrity depends on these separations never collapsing.

    ┌──────────┐          ┌──────────┐          ┌──────────┐
    │ PROPOSER │    ≠     │  JUDGE   │    ≠     │   GATE   │
    │ (mutator)│          │(meta-    │          │ (GP-030) │
    │          │          │ judge)   │          │          │
    │ generates│          │ scores   │          │ enforces │
    │ thesis + │          │ exec     │          │ numeric  │
    │ code     │          │ output   │          │ pass/fail│
    │          │          │ only     │          │          │
    │ NEVER    │          │ NEVER    │          │ CANNOT   │
    │ grades   │          │ reads    │          │ be over- │
    │ itself   │          │ prose    │          │ ridden   │
    └──────────┘          └──────────┘          └──────────┘

    ┌──────────┐          ┌──────────┐
    │WORKSPACE │    ≠     │VALIDATOR │
    │ (L1)     │          │ (L3)     │
    │          │          │          │
    │ remembers│          │ attacks  │
    │accumulates│         │ forgets  │
    │ compounds│          │ re-proves│
    └──────────┘          └──────────┘

    ┌──────────┐          ┌──────────┐
    │ CONTROL  │    ≠     │EPISTEMIC │
    │  PLANE   │          │  ENGINE  │
    │(supervisor)│        │(validator)│
    │          │          │          │
    │ routes   │          │ decides  │
    │ work     │          │ truth    │
    └──────────┘          └──────────┘
```

---

## 2. Architectural Boundary

ZTARE now has four layers:

```text
raw sources
  -> workspace updater
  -> workspace snapshot
  -> evidence compiler
  -> ZTARE validator
  -> synthesis pipeline
  -> audience artifact
```

More explicitly:

```text
raw/ -> src/ztare/workspace/update_workspace.py -> workspace/
workspace/ -> src/ztare/workspace/compile_evidence.py -> compiled_evidence.txt
compiled_evidence.txt -> evidence.txt -> src/ztare/validator/autoresearch_loop.py
thesis/history/debates -> src/ztare/synthesis/synthesize.py -> Report.md / Appendix...
```

The validator never reads `workspace/` directly.

The validator may, however, emit typed evidence-boundary diagnostics back into `workspace/`:

- `workspace/latest_evidence_gaps.json`
- `workspace/champion_evidence_gaps.json`
- `workspace/latest_constraint_proposals.json`
- `workspace/derived_constraints.json`
- `workspace/derived_constraints_brief.md`
- `workspace/evidence_gap_brief.md` (written by the compiler when gap artifacts exist)
- `workspace/latest_compile_failure.json` (written by the compiler only when a compile step fails closed)

This is a human-gated feedback loop, not autonomous retrieval. The operator still decides what enters `raw/` and what gets promoted into active `evidence.txt`.

Derived constraints are intentionally separate from primary evidence:

- `evidence.txt`
  - externally sourced facts and compiled evidence boundary
- `derived_constraints.json`
  - adversarially surfaced structural limits confirmed across multiple runs

The first expands the evidence boundary. The second narrows the allowable thesis space inside that boundary.

The validator/output layer also distinguishes between:

- `latest_*`
  - the newest evaluated candidate
- `champion_*`
  - the promoted best candidate for the active regime

This separation is load-bearing because the most recent evaluated attempt may fail while the promoted champion remains valid.

### Provider Runtime

Provider-specific API plumbing is now centralized in:

- `src/ztare/common/llm_runtime.py`

That layer owns:

- model-family alias resolution
- provider client initialization
- timeout / retry / transient-error policy
- cross-provider failover policy for persistent transient outages
- usage extraction into a common token/cost shape
- pricing-name normalization before cost estimation

The point is to stop landing the same provider fix independently in validator, compiler, synthesis, and workspace flows.

### Control Plane

The repo now has a separate control plane for program-level hardening work:

- `research_areas/seeds/**/*.md`
  - human-authored seed specs grouped by lifecycle (`active`, `deferred`, `legacy`)
- `research_areas/seed_registry.json`
  - seed lifecycle
- `supervisor/program_genesis/`
  - immutable birth contracts for accepted programs
- `supervisor/program_registry.json`
  - curated routable portfolio
- `supervisor/agent_wrappers.json`
  - thin launch-wrapper configuration for agent CLI invocation and verifier automation

This layer decides:

- which programs exist
- why they exist
- what they are not allowed to reopen
- whose turn it is inside a routed hardening loop

It does **not** decide truth.

The current routing contract is still explicit and bounded:

- default flow: `A1 -> A2 -> B -> C`
- optional bounded refinement: `A2 -> A1`, capped at 2 rounds
- optional budget-aware refinement: disabled by default until pricing + telemetry are configured
- supervisor remains the only component allowed to commit state

### Two Orthogonal Systems

The easiest way to stay oriented is to separate:

1. the **kernel**
2. the **control plane**

The kernel is the epistemic engine itself:

- derivation
- hinge extraction
- bridge / runner
- stage contracts

The control plane is the work-governance layer around bounded improvement programs:

- seed
- proposal
- genesis
- manifest
- supervisor loop

These are orthogonal.

The control plane does not decide epistemic truth.
It decides:

- what packet is next
- who is allowed to work on it
- what files are in scope
- whether the result can be committed

So:

- kernel hardening improves evaluator logic
- supervisor hardening improves execution discipline

One does not replace the other.

### Fractal Layer Map

The same separation pattern recurs across layers, but the names should stay distinct.

1. **Evidence substrate**
   - `raw/`, `workspace/`, compiled evidence
2. **Project charter**
   - `project_charter.md`, consumed as scope anchor, forecast-type contract, and deterministic drift surface
3. **ZTARE validator**
   - the adversarial domain-validation loop over bounded evidence
4. **V4 kernel**
   - the evaluator being hardened
5. **Meta-runner**
   - the kernel-local deterministic promotion runner for V4 stage advancement
6. **Supervisor**
   - the multi-program control plane for bounded work packets
7. **Publication layer**
   - paper bundles and reader-facing artifacts

These layers are fractal in structure because each introduces some separation between generation and evaluation. They are **not** interchangeable in responsibility:

- `meta-runner` is a kernel term
- `supervisor` is a control-plane term
- the supervisor does not decide epistemic truth
- the papers do not define runtime control

### Operational Contract

For repository structure and execution, the contract is:

- implementation lives under `src/ztare/`
- operational assets live under `config/`
- commands are run from repo root with `python -m src.ztare.<area>.<module>`
- `rubrics/` stays top-level because it is a first-class validator input, not an internal implementation detail

---

## 3. Design Invariants

These are load-bearing.

1. ZTARE remains stateless across validation runs.
2. The validator never trusts prior accepted conclusions just because they already exist in a workspace.
3. Every run must be reproducible from a bounded evidence snapshot.
4. Contradictions must be preserved upstream, not smoothed into fake consensus.
5. Audience artifacts are downstream views, not canonical truth stores.
6. The canonical machine-readable artifact for synthesis is `ledger.json`.
7. The knowledge workspace is external infrastructure, not part of the validator proof.
8. Broad projects should declare a `project_charter.md`; drift control is not left to prose judgment alone.
9. Forecast projects must distinguish bounded directional forecasts from probabilistic `%` forecasts at the charter level.
10. Score comparability breaks when active `evidence.txt` changes; the score regime now fingerprints the evidence boundary.
11. Operator-facing artifacts must distinguish the promoted champion from the latest failed or exploratory candidate.
12. Stagnation pivots should be selected as reusable heuristic profiles, not left as one monolithic prompt or a binary on/off switch.

---

## 4. Layer 1: Knowledge Workspace

### Purpose

The workspace is the persistent memory layer for source accumulation, but constrained for ZTARE's zero-trust needs.

### Design Inspiration

The workspace layer is an adaptation of [Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): raw sources accumulate, an LLM extracts structured per-source notes, and the system maintains cross-referenced knowledge that compounds over time. The key adaptation is that ZTARE intentionally stops short of a full autonomous wiki. The workspace accumulates and compiles, but the validator never trusts accumulated knowledge as authority. The boundary is: workspace remembers, validator attacks a snapshot. See [DECISION_LOG.md §14](../DECISION_LOG.md) for the full architectural reasoning.

Its job is to:

- ingest and retain source material over time
- maintain structured per-source notes
- preserve contradictions and unresolved questions
- emit a workspace snapshot that can be compiled into a bounded evidence file

Its job is **not** to certify truth.

### Entry Point

`src/ztare/workspace/update_workspace.py`

### Inputs

- `projects/<project>/raw/`

Supported source types today are text-like files:

- `.md`
- `.txt`
- `.json`
- `.csv`
- `.yaml` / `.yml`
- `.html`
- code/text files such as `.py`, `.js`, `.ts`

Non-text assets such as PDFs and images currently need conversion before ingest.

### Outputs

`projects/<project>/workspace/`

Key files:

- `source_notes/*.json`
- `source_index.json`
- `workspace_snapshot.json`
- `workspace_meta.json`
- `facts.md`
- `ranges.md`
- `contradictions.md`
- `open_questions.md`
- `candidate_claims.md`

### Internal Flow

```text
raw/ 
  -> per-source extraction (`config/prompts/extract_source_note.md`)
  -> source_notes/Sxxx.json
  -> cross-source merge (`config/prompts/merge_workspace.md`)
  -> workspace_snapshot.json
  -> human-readable workspace views
```

### Source-Note Contract

Each source note captures:

- source summary
- immutable ground truth
- numerical ranges and constraints
- potentially conflicting assertions
- epistemic voids
- candidate claims to test

### Workspace Rules

- unchanged sources are reused via content hash
- deleted raw files remove stale source notes
- contradictions are preserved until explicitly resolved
- candidate claims remain hypotheses, not accepted conclusions

---

## 5. Layer 2: Evidence Compiler

### Purpose

The compiler converts either:

- raw sources directly, or
- the richer workspace snapshot

into a bounded evidence artifact for ZTARE.

### Entry Point

`src/ztare/workspace/compile_evidence.py`

### Modes

- `--mode raw`
- `--mode workspace`
- `--mode auto`

`auto` prefers `workspace/workspace_snapshot.json` when present and falls back to `raw/` otherwise.

### Default Outputs

- `compiled_evidence.txt`
- `compiled_evidence_packet.json`
- `compiled_evidence_provenance.json`

These defaults are intentionally non-destructive. They do not overwrite `evidence.txt` unless explicitly told to.

### Evidence Schema

The compiler emits the same six-part structure in both markdown and JSON form:

1. Immutable Ground Truth
2. Numerical Ranges And Constraints
3. Identified Contradictions
4. Epistemic Voids
5. Provenance
6. Candidate Claims To Test

### Why This Exists

The current ZTARE core consumes `evidence.txt` as raw text. It does not parse JSON schemas. Therefore the compiler has to preserve the legacy textual affordances that current rubrics and prompts already rely on:

- load-bearing variables
- open problems / unknowns
- explicit ranges and constraints

This is why the compiler renders headings like:

- `NUMERICAL RANGES & CONSTRAINTS (LOAD-BEARING VARIABLES / CONSTRAINTS)`
- `EPISTEMIC VOIDS (OPEN PROBLEMS / UNKNOWNS)`

### Current Interface Gap

ZTARE still reads:

- `projects/<project>/evidence.txt`

So to use compiled evidence in the existing loop, one of these must happen:

1. compile directly to `evidence.txt`, or
2. promote `compiled_evidence.txt` to `evidence.txt`

This is a current implementation detail, not a conceptual limitation.

---

## 6. Layer 3: ZTARE Core Validator

**Companion doc:** [docs/concepts/cognitive_gym.md](cognitive_gym.md) — the constraint architecture that enforces epistemic discipline on the LLM. This section describes the components; the cognitive gym doc explains WHY the cage works and how it maps to Paper 5's decomposition of epistemic verification.

### Purpose

This is the adversarial engine itself.

### Entry Point

`src/ztare/validator/autoresearch_loop.py`

### Core Inputs

- `evidence.txt`
- `thesis.md`
- rubric JSON (including optional flags: `enable_fit_primitive`,
  `enable_fit_primitive_features`, `fit_primitive_features_k_max`,
  `enable_framer`, `framer_live_mode`, `cage_observe_mode`,
  `cage_authoritative_mode`, `cage_meta`, `rubric_mode` (e.g.
  `'newton'` for Newton-step Generative Yield scoring),
  `enable_lean_proof`, `structural_blocker_enforcement`)
- `verified_axioms.json`

### Core Outputs

- updated `thesis.md`
- `current_iteration.md`
- `history/*.md`
- `debate_log_iter_*.md`
- optional test artifacts such as `test_model.py`

### Validator Loop

```text
evidence.txt + thesis.md + rubric
  -> mutator proposes revised thesis + falsification suite
  -> verification panel evaluates weakest assumptions
  -> meta-judge scores thesis using executable evidence
  -> best surviving iteration is retained
  -> stagnation triggers pivots / escalations
```

The pivot policy is deliberately asymmetric:

- non-V4 projects can enter a generic topological-pivot prompt once `stagnation_count >= 3`
- V4-family projects suppress that generic pivot and substitute a bounded mutation override tied to the active kernel stage
- once a non-V4 run reaches `stagnation_count >= 4`, the loop can also purge visible axiom context to force a stronger blank-slate reset

### Invariants Inside The Core

- the generator cannot certify itself
- the judge relies on executable evidence, not rhetoric
- adversarial pressure is continuous
- axioms survive only by withstanding attack

### What The Core Is Not

- not a wiki
- not a research notebook
- not a persistent memory system
- not a general-purpose RAG engine

It is a validator.

---

## 6a. Fit Primitives — Sibling-Block Architecture

### Purpose

ZTARE ships TWO scipy-based fit primitives sized for different substrate
shapes. They are SIBLING blocks within Layer 3, NOT nested:

| Primitive | Path | Substrate shape | Engages when |
|---|---|---|---|
| `fit_primitive` (1D) | `src/ztare/fit/fit_primitive.py` | paired `(x, y)` evidence rows | rubric `enable_fit_primitive=true` AND thesis declares `FIT_DECLARATION` block |
| `fit_primitive_features` (N-D) | `src/ztare/fit/fit_primitive_features.py` | feature dict `(features_dict, y_observed)` rows | rubric `enable_fit_primitive_features=true` AND test_model.py declares `PARAMETRIC_FORM` + `PARAMETER_NAMES` + `MODEL_PARAMS = {}` |

Both engines run scipy.optimize.minimize multi-start (3 default; 5 at
stagnation_count≥3) and return per-fit telemetry. The N-D engine
additionally exposes `BIC = N·log(σ̂²) + K·log(N)` per GP-152 framer
spec v2.0.

### Why sibling, not nested

Bug #11 (2026-04-25) discovered the N-D wire-in had been silently
nested inside the 1D engine's `if rubric.enable_fit_primitive` branch
in autoresearch_loop.py. Substrates that opted only for the N-D
primitive (gp154, gp155 with `enable_fit_primitive=false`) skipped the
entire 1D branch, taking the N-D wire-in with it. 30+ iters ran with
zero N-D engagement despite the apparatus being shipped.

**Invariant:** future fit primitives must be SIBLING blocks at the
iter-body scope, gated only by their own rubric flag. NOT nested
under another primitive's flag.

### Engagement contract — feature-vector primitive

When `enable_fit_primitive_features=true`:

1. Mutator submits `test_model.py` with three module-level names:
   - `PARAMETRIC_FORM = "<expression as Python string with `features['key']` and `params['name']` subscripts>"`
   - `PARAMETER_NAMES = ['a', 'b', ...]` (the free parameters)
   - `MODEL_PARAMS = {}` (apparatus fills with fitted values)

2. Apparatus reads the declaration via `extract_form_declaration`,
   loads visible rows via `load_visible_from_substrate(project_dir)`
   (sorted by id for determinism, R8 spec mitigation), and runs
   `fit_features` with scipy.optimize multi-start.

3. On success, `substitute_fitted_model_params` rewrites the
   `MODEL_PARAMS = {}` line in test_model.py source with the fitted
   dict literal. The harness then imports the now-substituted
   test_model.py and calls `I_model(features, params=MODEL_PARAMS)`
   with the apparatus-fitted constants.

### AST whitelist (eval-injection defense)

PARAMETRIC_FORM is parsed via `ast.parse(form, mode='eval')` with a
whitelist of allowed AST nodes:

- Arithmetic: `+ - * / ** % //`
- Functions (bare or `math.X` / `np.X` attribute): `sigmoid, exp, log,
  log10, sin, cos, tan, tanh, sqrt, abs, max, min, float, int, bool`
- Subscript: ONLY on `features` or `params` (e.g. `features['key']`,
  `params['a']`)
- Conditionals: ternary `a if cond else b`, comparisons, boolean ops,
  tuple/list literals (for `in (...)` patterns)

Statement blocks (e.g. `if/elif`, `=` assignments) are rejected
with an actionable diagnostic pointing to the ternary alternative.

### K_law budget — BIC-justified, not flat-capped

Hard ceiling at K=8 (rubric-overridable via `fit_primitive_features_k_max`).
Within the ceiling, BIC is the real budget: `BIC = N·log(σ̂²) + K·log(N)`.
The mutator and judge see BIC alongside fitted_params; lower BIC = better-
justified parameter count. See `research_areas/private/specs/active/GP-156_apparatus_hardening_proposal.md`
for the K=5→K=8 transition rationale.

### Force-opt-in

When the rubric sets `enable_fit_primitive_features=true`, R1 rejects
any submission that does NOT declare `PARAMETRIC_FORM` + `PARAMETER_NAMES`.
Substrates running with this flag were designed for apparatus-fit
constants; opting out by writing hardcoded constants is gaming, not a
valid escape from the K_law budget.

### Kepler vs Newton (terminology, not separate components)

Two observables are judged at the gate-and-judge layer over the same
fit output:

- **Kepler step** — does the proposed form fit the data? Owned by the
  solver layer (the fit primitives above) plus the holdout / farther-tail
  gate. A pass means the form is empirically adequate.
- **Newton step** — does the form predict secondary observables NOT
  used in the fit? Owned by the Newton-mode rubric flag
  (`rubric_mode='newton'`), the Generative Yield rubric dimension, and
  optionally the Framer's canonical-form match (§6b). A pass means the
  form has predictive content beyond curve-fitting.

These are not separate code modules. They are vocabulary for talking
about which observable a given gate or rubric dimension is checking.

---

## 6b. Framer Architecture (GP-152 v2.0)

### Purpose

The Framer is a post-fit canonical-form mapper sitting between the
solver and the post-fit gate stack. Given a fitted `(form, params)`,
it asks: does this law belong to a known canonical family expressible
under an axis-separable monotone-invertible transform pair
`(h_in, h_out)`?

A successful frame yields an MDL gain (in raw coordinates, no Jacobian
correction) over the identity-identity baseline. A failed frame
auto-disables and reports `disabled_reason`.

### Code path

- `src/ztare/framer/active_framer.py` — entry point `frame(x, y, meta, rubric_data)`
- `src/ztare/framer/{symmetry,enumerate,search,collapse,report,primitives,units}.py`
  — components A–F per spec §4
- `src/ztare/framer/solver_wrapper.py` — `fit_with_framer()`
- `src/ztare/framer_gates/` — three runtime gates plus canary:
  - `library_coverage_gate.py` (G-LIB-COVER, MDL-gain ≥ 100 bits)
  - `filter_independence_gate.py` (G-FILTER-INDEP, |corr| < 0.3)
  - `symmetry_false_negative_gate.py` (G-SYM-FN, detection ≥ 0.95)
  - `framer_helped_canary.py` (auto-disable on pathological transforms)
- Spec: `research_areas/private/specs/active/GP-152_framer_architecture_spec_v2.md`

### MDL formula (raw coords)

```
σ̂²_raw   :=  (1/N) · Σ_i ( y_i − h_out⁻¹( f̂( h_in(x_i) ) ) )²
K_total  :=  K_law + K_h_in + K_h_out
MDL_v2   =  N · log( σ̂²_raw ) + K_total · log(N)
```

Frame-invariance is constructive in v2.0 (raw-coord evaluation), not
patched (the v1.x Jacobian-correction cycle is obsolete; backtest at
`scripts/backtest_framer_mdl_v2_vs_v1.py`).

### Wire-in mode

Activated per-rubric via `enable_framer: true`. Currently runs in
**OBSERVE mode** in `autoresearch_loop.py:4817`: `frame()` is called
on the parsed `(xdata, ydata)` BEFORE the fit and `framing_report.json`
is written to `workspace/`, but the fit itself still consumes raw
coords. Live mode (replacing fit input with framed data) is gated by
`framer_live_mode` and unset until validation §7 steps 6–10 complete.

### Scope and auto-disable

In scope: numerical fits with `fit_score_mode in {continuous_l2,
continuous_rmse}`, `N ≥ 80`, axis-separable monotone-invertible
transforms at composition depth ≤ 2 from `Σ = {identity, shift, scale,
power_k, log, exp, reciprocal}`. Auto-disable on heteroscedasticity in
the chosen frame, effective precision < 8 bits, non-invertible
composites, discrete/dynamical/FOM substrates, or bivariate/mixing
transforms (Lorentz-class).

### Newton-mode interaction

When the Framer engages and identifies a canonical family, the result
feeds the Newton-step verdict (§6a Kepler vs Newton): rediscovery of a
canonical family ≠ a new law. The judge sees the framing report and
the Generative Yield dimension is scored against secondary observables
the canonical family predicts.

---

## 6c. Cage Orchestrator (GP-157 v5.0)

### Purpose

The Cage is a substrate-agnostic dispatcher that replaces the
rubric-flag-plus-if-block dispatch pattern that has accumulated inside
`autoresearch_loop.py`. Each gate declares a `can_handle(substrate,
candidate)` predicate keyed off `substrate.meta['class']`. The Cage
inspects the submission shape, queries every registered gate's
predicate, builds a dependency-ordered DAG of qualified gates, and
runs them, emitting a per-iter engagement matrix.

### Code path

- `src/ztare/gates/cage.py` — `Cage` class, `Gate` dataclass,
  substrate-meta validation, topological dispatch
- `src/ztare/gates/registry.py` — `get_default_cage()` builds the
  default registry of 16 `Gate(...)` entries (universal +
  per-substrate-class)
- `src/ztare/orchestrator/state.py` — `CageRuntime` state object,
  `resolve_cage_mode()` (off / observe / authoritative)
- `src/ztare/orchestrator/{telemetry,prompt,dispatch,iter_context}.py`
  — engagement-record formatting, observe-summary printer, per-iter
  context builders
- Wire-in: `autoresearch_loop.py:3447` (init) and `:4106` (per-iter
  dispatch)
- Seam: `research_areas/private/seams/GP-157_cage_orchestrator_substrate_agnostic_dispatch.md`
- Spec: `research_areas/private/specs/active/GP-157_cage_v5_implementation_spec.md`

### Substrate-class taxonomy

The orchestrator infers (or reads from `cage_meta`) one of:

- `1d` — paired (x, y) data
- `nd_features` — features.py + `I_model(features)`
- `time_series` / `time_series_chaotic` — Lyapunov / Wasserstein-class
- `proof_target` — Lean-formalizable claim
- `closed_form_constant` — PSLQ integer-relation discovery
- `audit` — meta-audit / red-team substrates
- `literature` — text-based research review

Each registered gate declares which classes it targets; the Cage
filters by intersection. Universal gates run on every substrate.

### Modes

- `off` — Cage import unused, dispatch is legacy (default).
- `observe` — Cage runs alongside the existing dispatch and writes
  `workspace/cage_engagement.jsonl`. Does NOT influence scoring.
- `authoritative` — Cage owns dispatch; the legacy if-blocks defer.
  Migration is per-substrate-class per spec §4 Phase 3.

Resolution: `cage_authoritative_mode: true` wins over
`cage_observe_mode: true`; both default false.

### Universal Gate Contract

Every gate registered in the Cage exposes:

```python
class Gate:
    name: str
    phase: str            # "POST_FIT" | "POST_JUDGE" | "PRE_JUDGE"
    can_handle: Callable  # (substrate, candidate) -> (bool, reason)
    run: Callable         # (substrate, candidate) -> GateResult
    dependencies: tuple[str, ...]
```

The 16 currently-registered gates (per `gates/registry.py`):

- **Universal:** `semantic_gate_stabilization`, `circularity` (G-CIRC),
  `falsifiability` (G-FALSIFY), `derived_constraints`
- **1d / nd_features:** `coordinate_invariance`,
  `asymptotic_claim_discipline`, `deterministic_charter_gates`
- **nd_features-only:** `domain_match`, `ensemble_ambiguity`
- **time_series / time_series_chaotic:** `continuum_limit`,
  `wasserstein_persistence`
- **proof_target:** `ansatz_survivor`, `proof_surveyability` (depends
  on ansatz_survivor), `translation_diff`
- **closed_form_constant:** `pslq_falsity_audit`
- **audit:** `prompt_leak_audit`

Note: `bridge_scope_contract` and `residual_norm` are present in
`src/ztare/gates/` but currently RETIRED / classified as utility per
panel synthesis 2026-04-25. See `DECISION_LOG.md` for retire rationale.

---

## 6d. Post-Champion Gate Stack

After a candidate is promoted to champion (`res["score"]` improves),
four post-hoc gates run in series and can demote the champion back
into the loop. These execute in `autoresearch_loop.py` around line
3738 (full-promotion path) and line 5911 (in-loop promotion path).

| Gate | Code path | Fires when | What it enforces |
|---|---|---|---|
| **GP-119 Inverter** | `src/ztare/validator/inverter_agent.py` | `score >= 50` | Popper-style falsification: the agent proposes specific TESTS (not narrative doubts) against the champion thesis; results land in `derived_constraints.json` |
| **G-CIRC** (circularity) | `src/ztare/gates/circularity_gate.py` | `structural_blocker_enforcement in {gate, both}` | DAG cycle detection in `champion_probability_dag.json`; cycle ⇒ structural-blocker fail (SB-1) |
| **G-FALSIFY** (falsifiability) | `src/ztare/gates/falsifiability_gate.py` | `structural_blocker_enforcement in {gate, both}` | ≥ 1 numeric-threshold assertion in `test_model.py` (mandatory); plus optional watch-signal in DAG and rival/discriminator in thesis |
| **GP-122 Lean REPL** | `src/ztare/formal/lean_repl.py` | `score >= 70 AND enable_lean_proof` | Constrained Lean 4 REPL: LLM agent fills proof tactics; Lean verifies each step — the ultimate hard gate (typechecks or doesn't) |

Verdicts persist to `workspace/structural_blocker_gates_latest.json`
(G-CIRC + G-FALSIFY) and `workspace/inverter_review.json` (GP-119;
also appends to `derived_constraints.json`). The
GP-143 continuous-chaotic pipeline (`fit_score_mode:
"dynamical_lattice"`, score ≥ 70) also fires post-champion as
independent validation against the holdout trajectory — its
`certified_subset` JSONL feeds GP-122 if Lean is enabled.

The post-champion stack is NOT registered through the Cage — it runs
unconditionally on champion promotion. Migration to Cage's POST_JUDGE
phase is a Phase 4 candidate per the GP-157 spec.

---

## 7. Layer 4: Synthesis Pipeline

### Purpose

The synthesis system turns adversarially hardened project state into audience-facing artifacts without collapsing the canonical evidence trail.

### Entry Point

`src/ztare/synthesis/synthesize.py`

### Pipeline

```text
sniff_context
  -> summarize_history
  -> extract_ledger
  -> derive_brief
  -> render_artifact
  -> refine_artifact
  -> qa_artifact
```

### Canonical Artifact Hierarchy

1. `ledger.json`
   - canonical machine-readable synthesis state
2. `brief.<renderer>.json`
   - audience-specific planning layer
3. `Report.<renderer>.candidate.md`
   - rendered draft
4. `qa.<renderer>.json`
   - gate result
5. final report
   - only written if QA passes

### Key Design Principle

The synthesis layer separates:

- **what is true enough to keep** (`ledger`)
- **what matters to this audience** (`brief`)
- **how to say it** (`renderer`)
- **whether the result stayed faithful** (`QA`)

### Available Artifact Types

Current renderers include:

- `founder_memo`
- `decision_brief`
- `architectural_memo`
- `research_note`
- `quantitative_appendix`
- multi-project mode is available for `field_manual` and explicit report renderers via `--projects ... --renderer-type ...`; combined outputs are scoped so single-project synthesis artifacts are not overwritten

### History Control

The pipeline supports:

- `focused` history mode for audience-facing clarity
- `full` history mode for research/audit completeness

This avoids raw historical contamination in founder-facing artifacts while preserving traceability when needed.

---

## 8. End-to-End Data Flow

### A. Workspace Update

```text
raw/ -> src/ztare/workspace/update_workspace.py -> workspace/source_notes + workspace_snapshot
```

### B. Evidence Compilation

```text
workspace_snapshot -> src/ztare/workspace/compile_evidence.py -> compiled_evidence.txt
```

### C. Adversarial Validation

```text
evidence.txt -> src/ztare/validator/autoresearch_loop.py -> thesis/history/debates
```

### D. Audience Rendering

```text
thesis + evidence + history -> src/ztare/synthesis/synthesize.py -> memo / appendix / note
```

---

## 9. Directory Structure

```text
.
├── research_areas/
│   ├── v3_interface.md
│   └── systems_to_algorithms.md
├── src/
│   └── ztare/
│       ├── common/
│       ├── validator/
│       ├── workspace/
│       ├── primitives/
│       ├── synthesis/
│       └── experiments/
├── DECISION_LOG.md
├── ARCHITECTURE.md                   # redirect to docs/ARCHITECTURE.md
│
├── config/
│   ├── prompts/
│   │   ├── extract_source_note.md
│   │   ├── merge_workspace.md
│   │   ├── compile_evidence.md
│   │   ├── sniff_context.md
│   │   ├── summarize_history.md
│   │   ├── extract_ledger.md
│   │   ├── derive_brief_*.md
│   │   ├── refine_founder_memo.md
│   │   └── qa_artifact.md
│   └── renderers/
│       ├── founder_memo.md
│       ├── decision_brief.md
│       ├── architectural_memo.md
│       ├── research_note.md
│       └── quantitative_appendix.md
│
├── rubrics/
│   └── ...
│
└── projects/
    └── <project>/
        ├── raw/
        ├── workspace/
        ├── evidence.txt
        ├── compiled_evidence.txt
        ├── compiled_evidence_packet.json
        ├── compiled_evidence_provenance.json
        ├── thesis.md
        ├── current_iteration.md
        ├── verified_axioms.json
        ├── history/
        ├── debate_log_iter_*.md
        ├── synthesis/
        ├── Report.md
        └── Appendix.*.md
```

---

## 10. What This Architecture Is Optimizing For

This stack optimizes for:

- stronger evidence inputs
- explicit contradictions instead of smooth prose
- zero-trust validation of claims
- reproducible, bounded validation packets
- audience-ready artifacts without sacrificing canonical traceability

It is **not** optimizing for:

- fully autonomous long-running research agents
- end-to-end self-healing knowledge systems
- hidden state inside the validator

Those may come later. They are not assumed here.

---

## 11. Recommended Operating Pattern

For a real project:

1. ingest/update sources
```bash
python -m src.ztare.workspace.update_workspace --project <project> --model gemini
```

2. compile evidence snapshot
```bash
python -m src.ztare.workspace.compile_evidence --project <project> --mode workspace
```

3. promote snapshot if running current validator unchanged
```bash
cp projects/<project>/compiled_evidence.txt projects/<project>/evidence.txt
```

4. run ZTARE
```bash
python -m src.ztare.validator.autoresearch_loop --project <project> ...
```

5. synthesize outputs
```bash
python -m src.ztare.synthesis.synthesize --project <project> --pack founder
```

---

## 12. Future Work

Near-term:

- add an A/B harness for manual vs compiled evidence
- reduce friction around promoting `compiled_evidence.txt` into `evidence.txt`
- improve PDF/image ingestion into `raw/`

Later:

- external search-assisted workspace updates
- stronger provenance and reconciliation tooling
- packetized validator API around `claim_packet` / `validation_packet`

The key boundary should remain unchanged:

**workspace accumulates, validator attacks.**

---

## 13. Global Primitives (Curated Adversarial Precedents)

The repo now also has a second external memory layer:

```text
project workspace memory != global primitive memory
```

- `workspace/` stores project-local content:
  - facts
  - ranges
  - contradictions
  - open questions
- `global_primitives/` stores cross-project meta-patterns:
  - attack patterns
  - failure patterns
  - test templates
  - narrow causal motifs

This library is intentionally **not** a global axiom store.

### Why It Exists

ZTARE was strong but amnesiac. Good adversarial attacks discovered in one project tended to die with the run. The primitive library exists to preserve reusable adversarial leverage without smuggling prior conclusions into the next thesis as truth.

### Generation Pipeline

```text
project runs
  -> src/ztare/workspace/extract_incidents.py
  -> global_primitives/incidents/*.jsonl
  -> src/ztare/primitives/draft_primitives.py
  -> global_primitives/review/
  -> src/ztare/primitives/approve_primitive.py
  -> global_primitives/approved/
```

The promotion model is deliberately hybrid:

1. Python extracts concrete incidents from debate logs, history files, and tests.
2. An LLM drafts candidate primitive cards.
3. A human promotes or rejects.

### Engine Usage Boundary

Approved primitives may be used in the validator, but only under strict limits:

1. They are never injected as `evidence.txt`.
2. They are never treated as project-local axioms.
3. Retrieval is bounded (`top_k` small).
4. Default use is attacker/judge-side only.
5. Mutator-side use is explicit opt-in.

That means the safe default is:

```bash
python -m src.ztare.validator.autoresearch_loop --project <project> --rubric <rubric> --use_primitives
```

This arms the attacker generation, attacker prompts, and meta-judge with known failure precedents.

Mutator exposure is intentionally separate:

```bash
python -m src.ztare.validator.autoresearch_loop --project <project> --rubric <rubric> --use_primitives --use_transfer_hypotheses
```

When enabled, mutator-side primitives are framed only as **transfer hypotheses**, never as truths. They require explicit transfer justification and a domain-specific falsification test.

---

## 14. Program Birth And Routing

Program-level hardening work now follows this birth chain:

1. seed spec exists
2. seed is tracked in `research_areas/seed_registry.json`
3. human accepts opening a program
4. `supervisor/program_genesis/<program>.json` is written
5. program is added to `supervisor/program_registry.json`
6. supervisor routing begins

This prevents:

- stale seed specs from silently re-entering the active portfolio
- old closed programs from being reopened by drift
- chat-only concepts from becoming routable work without explicit provenance


## 15. The v2.1 Meta-Architecture: Measuring the Data's Epistemology

Earlier sections of this document describe an apparatus that fits forms to data. The v2.1 work, completed during the gp163d 2026-04-25 session, addressed a more basic question: what should the apparatus assume about the data itself?

The answer, working backward from a sequence of failure modes that surfaced under live multi-class astrophysics data, was that the apparatus had been assuming far too much. The original solver path assumed that residuals were independent, identically distributed, Gaussian, and confined to the dependent variable. The weighted-χ² fit primitive (GP-164) closed the "identically distributed" gap by accepting per-row σ from the substrate's feature dictionary. Three further assumptions remained — errors confined to y (an orthogonal-distance-regression gap), Gaussian residuals (a robust-loss gap), and independent residuals (a covariance / Mahalanobis gap) — and the apparatus had no way of knowing when any of them broke.

v2.1 closes this by measuring rather than assuming.

### The noise-profile diagnostic

`src/ztare/diagnostics/noise_profile.py` runs four statistical tests on a baseline-fit residual series before the first iteration begins. A Breusch-Pagan-style correlation between squared residuals and the primary predictor flags heteroscedasticity. Shapiro-Wilk (for n < 5000) or Jarque-Bera (otherwise), supplemented by skew and kurtosis thresholds, flags non-Gaussian residuals and heavy tails. Durbin-Watson on residuals ordered by predictor flags lag-1 autocorrelation. Explicit `sigma_x_*` keys in the feature dictionary flag errors in the independent variable; a spacing-coefficient-of-variation heuristic surfaces a soft hint for substrates with measured rather than controlled X but does not auto-route on that hint alone.

The verdict, a `NoiseProfile` dataclass with four boolean flags and the underlying test statistics, drives auto-routing of solver-related rubric flags the operator did not explicitly set. Heteroscedasticity routes to weighted χ². Non-Gaussian residuals route to robust loss (currently telemetry-only until the Huber path lands in the fit primitive). Autocorrelation routes to a covariance-aware solver (also telemetry-only). Explicit σ_x routes to ODR (also telemetry-only). The operator can override any auto-routed flag by setting it explicitly in the rubric — operator intent always wins.

The same four detectors run again per iteration on the fitted model's residuals via `classify_residuals`. This second pass distinguishes a good fit with clean noise (the solver was the right call) from a good fit with structured residuals (model misspecification, a missing feature, or genuine class-dependent physics that a single form cannot capture). The verdict feeds the mutator's briefing through `NoiseProfileBriefingProvider`, so each iter sees both the pre-flight verdict on the data and the per-iter verdict on the current form.

### Apparatus hardening

The same arc surfaced five places where the apparatus had silent failure modes that masked real findings as tooling failures. All five shipped under GP-166.

The fit primitive's pathology detector had been telemetry-only: it flagged catastrophic fitted parameters (those exceeding ten times the maximum |y| in visible data) but did not stop them from being substituted into MODEL_PARAMS. On gp163d, an underdetermined parameter `k_m` absorbed visible-class noise and reached -1.2 million, far outside its declared init-range of (-2, 2). That value then propagated to the gate harness, where `10^(-1.2M × Δ-mass)` underflowed to zero on cluster predictions and the form collapsed to y = x with farther-tail MRE near 0.85. Pathology *enforcement* now replaces flagged parameters with the midpoint of their declared init-range before substitution, so the gate harness receives bounded numbers and the mutator's briefing surfaces the substitution explicitly: "your form has unconstrainable parameters given visible-class data; restructure so each free parameter is bounded by the visible classes alone."

The harness-failure classifier had a related blind spot. When the mutator's own discriminator assertion failed on a fitted form — a real, scientifically meaningful self-falsification — the truncated or wrapped stderr sometimes did not contain a parseable Python exception name. The classifier returned `fail_other`, the apparatus labeled it "harness defect," and the score capped at 50 as a tooling failure. The fallback now matches `AssertionError` substrings and bare `assert` traceback frames, returning `fail_assert` (a real falsification, score-eligible per the rubric) in those cases.

The contamination-defense gate (`global_named_import_check`, which scans thesis prose against a project's `.denylist`) had been firing silently. The mutator's iter would hard-fail without any indication of which word triggered the gate. A new `ContaminationDefenseBriefingProvider` reads the most recent submission, scans it against the denylist with case-insensitive whole-word matching, and surfaces hits with line numbers and explicit guidance: do not name the canonical theory; restate the same structural argument from the anonymized features the substrate exposes. The contamination feedback loop is closed.

The R1 stdlib-only contract had an unintended interaction with N-D feature-dict substrates. The mutator's natural pattern was `from features import VISIBLE; for row in VISIBLE: ...`, which the stdlib-only rule blocked. Inlining the data instead triggered a separate R1 rule against module-level I_model calls, because inline-data evaluation was indistinguishable from import-time side effects. The mutator burned all retry budget bouncing between the two rules and produced no thesis prose. The fix now allows `from features import …` whenever the project directory contains a `features.py` — the rule was designed against apparatus-import bypass, not against project-local substrate adapters.

Finally, the framer's scope check had been gated on `enable_fit_primitive` (the 1D flag) without consulting `enable_fit_primitive_features` (the N-D flag). Every N-D substrate that set `enable_framer=true` saw the framer silently self-disable with reason `fit_primitive_disabled`. The check now accepts either flag.

### What this is, philosophically

The unifying move is the one Gemini named at the start of the session: the apparatus stops assuming the data's epistemology and starts measuring it. This is the mechanization of the physicist's reflex of looking at the error bars before choosing the math. v2.1 is the ZTARE 3.0 trajectory in miniature — from curve-fitter (which assumes the data is a clean array of floats) toward instrument-aware solver (which measures the error profile and routes accordingly). The five hardening patches are the same move applied at the apparatus's other silent boundaries: catch the catastrophic fit before it propagates, label the falsification as a finding, tell the mutator which word tripped the gate, give it the right contract for the substrate it is on, run the framer where it belongs.
