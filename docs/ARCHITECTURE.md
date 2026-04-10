# ZTARE Architecture

ZTARE separates four things that are often collapsed in ordinary LLM workflows:

- source accumulation
- bounded evidence compilation
- stateless adversarial validation
- downstream synthesis / reporting

The architecture is only worth its complexity if those separations stay explicit under adversarial pressure.

## 1. System Thesis

ZTARE is a **stateless adversarial validator** for claims, theses, and strategic logic.

It is surrounded by two external layers:

1. a **stateful knowledge workspace** that accumulates sources and compresses them into a bounded evidence snapshot
2. a **synthesis layer** that turns adversarial outputs into audience-facing artifacts

The important rule is:

**State is not the enemy. Unearned trust is the enemy.**

That is why:

- the workspace is allowed to be stateful
- the validator is not allowed to inherit that state as authority
- every validation run still starts from a bounded input snapshot

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

### Purpose

This is the adversarial engine itself.

### Entry Point

`src/ztare/validator/autoresearch_loop.py`

### Core Inputs

- `evidence.txt`
- `thesis.md`
- rubric JSON
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
  -> firing squad attacks weakest assumptions
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
