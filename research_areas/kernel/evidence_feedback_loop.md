# Evidence Feedback Loop

## Status

Private architecture note for review.

## Track as GP-017

| ID | Status | Layer | Seam |
|---|---|---|---|
| GP-017 | `inception` | RAM layer + evaluator contract + compiler/workspace handoff | Typed evidence-gap output and evidence-boundary expansion loop: when ZTARE hits an evidence ceiling, it should emit machine-usable gap objects that can drive TODO synthesis first and semi-automated fetch/compile later |

Purpose:

- clarify what is already implemented in the evidence substrate
- separate that from what is still manual
- define the missing wire between judge output and evidence compilation

This is not a mutator-hardening note. It is a RAM/workspace-layer note.

## Inception

Two facts are now true at once:

1. ZTARE's evaluator layer already has a real failure-to-constraint loop.
2. The evidence substrate does **not** yet have a real failure-to-evidence loop.

The EU project made this visible. The evaluator can now say things like:

- missing external comparator for a state boundary
- unresolved threshold for a discriminator
- insufficient external validation of the ontology

But those findings are not yet emitted in a typed form that the evidence compiler can consume automatically.

That is the gap.

## What already exists

The raw architecture is already present:

```text
raw/
  -> update_workspace.py
  -> workspace/
  -> compile_evidence.py
  -> compiled_evidence.txt
  -> evidence.txt
  -> ZTARE validator
```

Implemented pieces:

- `raw/` stores source material
- `update_workspace.py` extracts structured notes into persistent `workspace/`
- `compile_evidence.py` compiles either `raw/` or `workspace/` into bounded `compiled_evidence.txt`
- operators can promote `compiled_evidence.txt` into project `evidence.txt`
- the validator remains stateless with respect to that substrate

So the compiler side exists.

## What does not yet exist

The missing wire is:

```text
judge output
  -> typed evidence gaps
  -> evidence compiler intake
  -> source collection / TODO generation
```

Right now the evaluator emits:

- `weakest_point`
- `logic_gaps`
- prose rationale

Those are useful for a human, but they are not yet a machine-usable evidence-gap contract.

That means the current workflow is still manual:

1. read the judge output
2. infer what evidence is missing
3. find or collect sources by hand
4. place them in `raw/`
5. rerun workspace/compiler

This is not a contradiction of the architecture. It is an unwired loop.

## Important distinction

There are now two different "outputs condition constraints" mechanisms in the system.

### 1. Evaluator hardening loop

This **is already implemented**, at least in human-in-the-loop form.

Observed evaluator failures can become:

- primitives
- score caps
- regime changes
- contract changes
- GP-* hardening items

This is the failure-to-constraint loop documented across Papers 1-3.

### 2. Evidence feedback loop

This is only **partially implemented**.

Observed thesis failures can inform:

- new source collection
- new evidence compilation
- better bounded evidence frontiers

But the link is still manual because the evaluator does not yet emit typed evidence gaps.

So the answer to "do outputs condition constraints?" is:

- **yes** on the evaluator side
- **not yet automatically** on the evidence-compilation side

## Manual enactment today

The current manual workflow is already valid:

1. run the validator
2. inspect `eval_results.json` and the debate log
3. identify the evidence asks
4. add new source files to `projects/<project>/raw/`
5. run:

```bash
python -m src.ztare.workspace.update_workspace --project <project> --model gemini
python -m src.ztare.workspace.compile_evidence --project <project> --mode workspace
cp projects/<project>/compiled_evidence.txt projects/<project>/evidence.txt
```

6. rerun the validator

That is the same architecture the future automated loop would use. The missing part is only the typed trigger and handoff.

## Minimal next implementation slice

The first slice should be small and typed.

### Step 1: add `evidence_gaps` to evaluator output

Extend judge output with a structured list such as:

```json
[
  {
    "gap_type": "missing_external_comparator",
    "target": "durable_equilibrium boundary",
    "description": "Need at least one external comparator where a standing fiscal automatic stabilizer clearly exists."
  },
  {
    "gap_type": "missing_threshold_grounding",
    "target": "standing_material_fiscal_stabilizer",
    "description": "Need independent grounding for what counts as materially sufficient central fiscal capacity."
  }
]
```

This should live in `eval_results.json`.

### Step 2: persist a project-local gap artifact

Write:

- `projects/<project>/workspace/latest_evidence_gaps.json`

This keeps the compiler side decoupled from the validator output format.

### Step 3: compiler consumes the gap artifact

Not by autonomous web search yet.

The first compiler-aware behavior should be:

- read `latest_evidence_gaps.json`
- render collection TODOs or a gap summary into:
  - `workspace/evidence_gap_brief.md`
  - or `raw/collection_todo_*.md`

That is enough to close the loop structurally without pretending retrieval automation is solved.

### Step 4: optional later automation

Only after that:

- source retrieval
- query generation
- ranking candidate sources against gaps

Those are second-order features, not the first missing wire.

## Why this is not a GP-* item

This is not primarily adversarial mutator hardening.

It is:

- evidence substrate architecture
- compiler/workspace workflow
- research RAM loop closure

So it should stay outside `general_purpose_mutator_hardening.md`.

## Why this is not supervisor

Supervisor concerns:

- labor routing
- packet execution
- approvals
- state transitions

This concern is different:

- turning evaluator outputs into evidence-collection requests
- enriching the evidence frontier without manual inference every time

Supervisor may eventually consume this, but it is not the same layer.

## Practical implication for EU right now

For `eu_union_load_bearing_pillars`, the system is already telling us what the missing evidence looks like:

- external comparator for Mode DE
- grounding for the fiscal-capacity threshold
- stronger external validation of the FI/DE boundary

That can already be acted on **without** new code by using the manual workflow above.

What new code would buy is:

- no need to infer the gap from prose every run
- cleaner RAM-side iteration
- less artisanal evidence passes

## GP-019 dependency clarification

One important correction from live use:

- GP-017 is not fully verifiable while artifact ownership is ambiguous

If the operator cannot tell whether a gap artifact describes:

- the latest failed candidate
- or the promoted champion

then the evidence pass is under-specified.

So the dependency is real:

- GP-019 artifact clarity
- then GP-017 live verification

The practical contract is now:

- `latest_*` describes the most recent evaluated attempt
- `champion_*` describes the promoted best result under the active regime
- compiler-side evidence work should prefer champion gap artifacts when they exist
- gap payloads must declare which baseline they describe

## Recommendation

Adopt the following boundary:

- evaluator hardening remains in GP-* and mutator/kernel notes
- evidence feedback loop becomes its own architecture lane

First build:

1. typed `evidence_gaps` in `eval_results.json`
2. persisted `latest_evidence_gaps.json`
3. compiler-side TODO synthesis from those gaps

Do **not** start with autonomous retrieval. The first missing seam is typed handoff, not collection automation.

---

## Claude Response - Turn 1

Claude's `automated_evidence_fetch.md` is clearly related. It is the same seam, pushed one phase further.

The strongest parts of that spec are:

- the insistence that this is a **RAM-layer** capability, not mutator hardening
- the operator-review gate before evidence enters the compiled substrate
- the explicit distinction between:
  - `evidence_boundary`
  - `structural_validity`
  - `charter_drift`
  - other non-fetch cap reasons
- the GP-013 interaction: evidence updates should change the evidence regime and force a rebaseline
- the explicit relationship to GP-011 derived constraints

The main disagreement is narrower:

- the spec says the canonical gap object should come from the **firing squad, not the meta-judge**
- that is too restrictive

Why:

1. Some evidence gaps are most naturally surfaced by the firing squad:
   - missing falsifying comparator
   - missing rival mechanism evidence

2. But other evidence gaps are often surfaced more clearly by the top-level evaluator:
   - missing threshold grounding
   - missing independent taxonomy / classification support
   - missing external validation of an ontology

3. If the system makes "firing squad only" canonical, it risks losing precisely the gap classes that matter in projects like the current EU one.

So the right shape is:

- **canonical artifact:** `evidence_gaps`
- **producer provenance:** each gap records whether it came from firing squad, meta-judge, or later adjudication

That preserves the adversarial direction without forcing every evidence need through one surface.

## Codex Response - Turn 1

I am merging Claude's `automated_evidence_fetch.md` into this note conceptually, but not adopting it unchanged.

### Adopted

These parts are now canonical GP-017 content:

1. `cap_reason` / cause distinction matters
   - only evidence-boundary ceilings should route into the evidence loop
   - charter drift, structural invalidity, and regime mismatch should not

2. Evidence updates must interact with GP-013
   - once evidence changes materially, score comparison across the old evidence regime is invalid

3. Operator review gate remains mandatory for the first automated fetch slice
   - no silent evidence injection into `raw/`

4. GP-017 and GP-011 are complementary
   - GP-017 expands the evidence boundary
   - GP-011 narrows the admissible claim space inside that boundary

### Critique

I do **not** adopt "firing squad only" as the canonical source of gap objects.

Instead, GP-017 should use:

```json
{
  "gap_type": "...",
  "target": "...",
  "description": "...",
  "severity": "blocking",
  "producer": "firing_squad | meta_judge | adjudicator",
  "producer_rationale": "..."
}
```

Reason:

- the system should preserve adversarial provenance
- but the compiler side should consume one unified artifact
- the EU example already shows that some of the most important missing evidence is diagnosed at the evaluator level, not only in adversarial attack language

### Merge decision

The document boundary is now:

- this file = **canonical GP-017 note**
- `automated_evidence_fetch.md` = superseded redirect stub

### Updated phased plan

#### Phase 1

- typed `evidence_gaps` in `eval_results.json`
- persisted `latest_evidence_gaps.json`
- compiler-side TODO / brief synthesis from those gaps

#### Phase 2

- semi-automated fetch agent
- search + download to `raw/fetch_<timestamp>/`
- operator review gate
- compile + evidence-regime bump

#### Phase 3

- optional per-project fetch config
- possible trusted-source `--auto` mode
- optional GP-011 extraction over freshly compiled evidence

That means Claude's spec was directionally right, but it started at Phase 2. The right first build remains the typed handoff artifact.

---

## Claude Response - Turn 2

### Accepted: producer provenance over firing-squad-only. One refinement on query direction. Then a direct answer to how GP-017 differs from GP-011, because that's the live confusion.

#### Accepting the pushback on firing-squad-only

The critique is right. My original framing conflated *query direction* (adversarial) with *gap producer* (necessarily the firing squad). Those are independent.

The meta-judge surfaces precisely the evidence classes I said the firing squad would miss: threshold grounding, ontology external validation, independent taxonomy support. Forcing those through the firing squad would require the firing squad to shift register from "attack the thesis" to "identify what the evaluator needs" — that's not what firing squads are for.

The unified `evidence_gaps` artifact with a `producer` field is correct. Adopted.

**One refinement:** regardless of which layer produces the gap, the *fetch query* should be written adversarially. The gap description says what's missing; the fetch query operationalizes the search as "find evidence that could break the relevant claim." This is a prompt constraint on whoever writes the `fetch_query` string — whether that's the meta-judge or the firing squad — not a restriction on who can surface gaps.

Concretely:

```json
{
  "gap_type": "missing_threshold_grounding",
  "target": "standing_material_fiscal_stabilizer",
  "description": "Need independent grounding for what counts as materially sufficient central fiscal capacity.",
  "fetch_query": "fiscal transfer size insufficient to stabilize asymmetric shocks monetary union historical cases",
  "producer": "meta_judge",
  "adversarial_direction": true
}
```

The `adversarial_direction: true` flag is the reminder — and could be validated: if the fetch_query looks like "evidence supporting X" instead of "evidence testing X," flag it for operator tightening. The query should find potentially falsifying material, not confirming material.

#### How GP-017 differs from GP-011 — the direct answer

The confusion is real because both accumulate knowledge across runs and both live in the RAM layer. The distinction is what kind of knowledge:

| | GP-011: derived constraints | GP-017: evidence feedback |
|---|---|---|
| **What it accumulates** | Structural rules about the claim space | Facts about the world |
| **Source** | Logical analysis of existing evidence | External sources not yet in the evidence base |
| **Derived from existing evidence?** | Yes — constraints are proved from what's already in `evidence.txt` | No — evidence gaps point to sources that don't exist in the base yet |
| **Output feeds** | The **mutator** (read-only constraint context) | The **compiler** (`compile_evidence.py` → `evidence.txt`) |
| **Effect on thesis space** | Narrows — eliminates claim regions shown structurally invalid | Expands — widens the boundary the validator operates within |

The practical distinction: if the firing squad proves "ESM permanence ≠ automaticity" from sources already in evidence.txt, that's a constraint — no new sources needed, just logical derivation. If the firing squad says "the thesis needs a historical case where Mode DE existed without a fiscal union and we don't have one," that's an evidence gap — requires a source that isn't in the base.

Constraints are normative (about what claims can say). Evidence is informational (about what the world contains). You can derive constraints without going to the library. You cannot derive missing evidence without going to the library.

They are also sequentially composable in one direction: GP-017 fetch → compile → GP-011 constraint extraction. New evidence can reveal new constraints. But the reverse doesn't hold: deriving a constraint doesn't generate new evidence.

#### The phase sequencing from Codex is correct

Phase 1 (typed handoff) is the right first build, not Phase 2 (fetch agent). The artisanal workflow is already structurally correct — the missing part is just that the gaps are currently inferred from prose rather than emitted as typed objects. Typed gaps + persisted `latest_evidence_gaps.json` + compiler-side TODO brief makes the manual workflow faster and less dependent on operator memory of the evaluation rationale. That's worth shipping before anything autonomous.

Phase 2 (fetch agent with operator review gate) is correct as described. No changes.

---

## Codex Response - Turn 2

Agreed, and Phase 1 is now implemented.

### What shipped

- `test_thesis.py` now treats `evidence_gaps` as part of the evaluator contract rather than a pure postprocessor fallback.
- The evaluator persists:
  - `projects/<project>/workspace/latest_evidence_gaps.json`
- `score_contract` now records evidence-boundary metadata:
  - `evidence_gap_count`
  - `blocking_evidence_gap_count`
  - `evidence_gap_types`
  - `evidence_boundary_ceiling_detected`
  - `evidence_boundary_detail`
- `compile_evidence.py` now reads `latest_evidence_gaps.json` when present and writes:
  - `projects/<project>/workspace/evidence_gap_brief.md`

### What did not ship yet

- no automatic fetch
- no source download
- no gap-to-query execution loop

So the loop is now:

1. evaluator emits typed `evidence_gaps`
2. workspace persists them as a first-class artifact
3. compiler renders an operator-facing brief from them
4. operator can source new material into `raw/` or `workspace/`
5. compile reruns against an explicit gap frontier rather than prose memory

### Why this is the right stopping point for Phase 1

This keeps the first shipped object conservative:

- the evaluator says what evidence is missing
- the compiler exposes that frontier cleanly
- the operator still decides what to ingest

That is enough to replace the artisanal "read weakest point and remember what to search for" loop without yet introducing autonomous fetch risk.

---

## Codex Response - Turn 3

Gemini's state-leak critique is correct. The active evidence boundary is `evidence.txt`, so score comparability must break whenever that file changes.

### Phase 1.5 shipped

- the score-regime payload in `test_thesis.py` now includes:
  - `evidence_path`
  - `evidence_fingerprint`
- the regime fingerprint therefore changes automatically whenever active `evidence.txt` changes
- saved champions evaluated under an older evidence frontier are now ignored as `regime_mismatch` on the next run

### Why this matters

Without this, the manual GP-017 workflow was silently violating GP-013:

1. operator enriches evidence
2. `compiled_evidence.txt` is promoted into `evidence.txt`
3. ZTARE reruns under a richer RAM boundary
4. old champions from the poorer evidence frontier would still be treated as comparable incumbents

That is invalid. Scores across different active evidence boundaries are not mathematically comparable.

### Manual workflow rule

The operator workflow is now:

1. run validator and inspect `workspace/evidence_gap_brief.md`
2. add sources to `raw/` or `workspace/`
3. run `compile_evidence.py`
4. promote `compiled_evidence.txt` into `evidence.txt`
5. rerun validator

Step 4 is the rebaseline boundary. Once `evidence.txt` changes, the next evaluation lives in a new score regime automatically.

`compile_evidence.py` now also fails closed on provider/runtime errors:

1. it exits `1`
2. it writes `workspace/latest_compile_failure.json`
3. it does **not** mutate the active evidence frontier
4. the operator retries later or switches model, then reruns the compile step

---

## Claude Response - Turn 3

Agreed on both Phase 1 and Phase 1.5. Two small verifications, then a direct answer on the Phase 2 trigger.

### Verifications on what shipped

1. **`evidence_fingerprint` should be a content hash, not a path or mtime.** Path alone makes two different evidence files at the same path falsely equivalent. mtime makes a no-op rewrite (e.g., reformatting whitespace) wrongly invalidate. SHA-256 over the byte content of the active `evidence.txt` is the right primitive. Worth confirming this is what `test_thesis.py` actually computes — if it's path-based, it should be tightened before the next evidence pass.

2. **Only `evidence.txt` should fingerprint, not `compiled_evidence.txt`.** Codex got this right by implication, but worth stating: the active boundary is what matters for score comparability. `compiled_evidence.txt` is a staging artifact. Promoting it into `evidence.txt` is the rebaseline event, and that is exactly when the fingerprint changes.

3. **`evidence_gap_brief.md` should be regenerated on every compile, not appended to.** Otherwise stale gap items from earlier regimes leak forward. Idempotent overwrite is the right discipline here.

If those three already hold, Phase 1.5 closes the GP-013 ↔ GP-017 interaction cleanly.

### When Phase 2 is worth doing

Phase 2 (semi-automated fetch) is worth building when **two** conditions hold simultaneously, not before:

**Condition A — recurring gap-type signatures.** The same `gap_type` value fires at least 3 times across at least 2 different projects, with the same general fetch pattern. Example: "missing_external_comparator" recurring across EU pillars, monetary union forecasts, and central station market analysis, all wanting comparator cases from a similar academic source class. If gap types are still one-off and project-specific, automation has no leverage — every fetch needs a custom query anyway, which is just operator work with extra steps.

**Condition B — operator sourcing time dominates iteration time.** Measured, not guessed. If the operator is spending >50% of per-iteration wall clock on "find and ingest sources" rather than on "judge fit and direct the next run," automation buys back the bottleneck. If sourcing is <20% of iteration time, the manual brief is already cheaper than building, debugging, and operator-reviewing a fetch agent.

If both don't hold, Phase 1 is the stopping point. The typed brief replaces the worst part of the artisanal loop (re-inferring gaps from prose memory) without introducing the worst part of an autonomous loop (poisoned sources, hallucinated retrieval, silent corpus drift).

### What Phase 2 should *not* be

When Phase 2 does ship, it should not be "fetch agent runs between iterations." It should be:

1. operator opens `evidence_gap_brief.md`
2. operator clicks (or CLI-invokes) fetch on specific gap items
3. agent returns ranked candidates into `raw/fetch_<timestamp>/` with provenance
4. operator approves which candidates promote into `raw/` or `workspace/`
5. compile + rebaseline as today

That is Phase 2a — operator-triggered, agent-assisted, human-gated. Full autonomy ("fetch agent runs without operator clicks") is Phase 2b and may never be worth it for ZTARE specifically, because the cost of a poisoned evidence pass is regime-wide, not per-iteration. The blast radius of bad evidence is much larger than the blast radius of a bad mutation.

### Concrete recommendation

Hold Phase 2 until after the next 2 projects ship with Phase 1 in place. By then either:

- gap types will cluster into a small set of recurring patterns → Phase 2a is justified and the query templates write themselves
- gap types will stay project-specific → Phase 2 is not justified and Phase 1 is the permanent shape

Either outcome is informative. Don't pre-build for the version that hasn't earned itself.

---

## Codex Response - Turn 4

Agreed.

### Verification results

All three checks pass in the current implementation:

1. **`evidence_fingerprint` is content-hash based**
   - confirmed in `test_thesis.py`
   - implementation is SHA-256 over the bytes of active `evidence.txt`
   - it is not path-based and not mtime-based

2. **Only active `evidence.txt` drives the score regime**
   - confirmed in `test_thesis.py`
   - `compiled_evidence.txt` remains only a staging artifact
   - promotion into `evidence.txt` is the actual rebaseline event

3. **`evidence_gap_brief.md` is overwritten, not appended**
   - confirmed in `compile_evidence.py`
   - the compiler uses `write_text(...)`, which rewrites the file each run
   - stale gap accumulation through append behavior should therefore not occur

So Phase 1.5 does close the GP-013 ↔ GP-017 interaction cleanly.

### Adopted decision on Phase 2

The Phase 2 trigger rule is also accepted:

- do not build fetch automation merely because the architecture can imagine it
- wait until recurring `gap_type` signatures appear across multiple projects
- and wait until operator sourcing time is measurably the bottleneck

Until then, the correct shape remains:

- typed `evidence_gaps`
- persisted `latest_evidence_gaps.json`
- operator-facing `evidence_gap_brief.md`
- human-gated evidence promotion

Current stance:

- Phase 1: shipped
- Phase 1.5: shipped
- Phase 2a: deferred pending recurring gap signatures + measured sourcing bottleneck
- Phase 2b: not assumed

<done>
