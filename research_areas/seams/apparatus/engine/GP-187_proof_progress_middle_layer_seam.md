# GP-187 — Proof-Progress Middle Layer Seam

> **Seam metadata** · `seam_id:` GP-187 · `track:` apparatus · `status:` OPEN - Slice A implemented, seam still open for heavier laye · `last_updated:` 2026-04-28


**Status:** OPEN — Slice A implemented, seam still open for heavier layers
**Opened:** 2026-04-28 20:28:07 EDT
**Updated:** 2026-04-28 20:43:07 EDT
**Category:** Apparatus / Engine / Formal-Proof Search

## Eigenquestion

ZTARE already has:
- conjecture / compression generation
- Lean stub generation
- Lean compilation / proof attempt

What it does **not** have is a proof-search middle layer that turns binary
Lean rejection into a usable search gradient. The eigenquestion is:

> Can we insert a structured proof-progress substrate between LLM proof
> proposals and Lean's binary pass/fail gate, so the apparatus learns *why*
> proof search is stuck rather than merely retrying?

## Codebase Audit

### What already exists

1. **Lean stub generation**
   - `src/ztare/formal/lean_compiler.py`
   - `ztare_proofs/README.md`
   - Current role: convert discovered expressions / gate results into Lean
     stubs and empirical-check artifacts.

2. **Lean attempt loop**
   - `src/ztare/formal/lean_repl.py`
   - Current role: ask an LLM for a full Lean file, run Lean, retry on
     failure.

3. **Post-hoc proof gates**
   - `src/ztare/gates/ansatz_survivor_gate.py`
   - `src/ztare/gates/proof_surveyability_gate.py`
   - Current role: filter already-produced proofs or proof candidates.

4. **Public architectural framing**
   - `research_areas/seams/apparatus/engine/GP-122_millennium_substrate_seam.md`
   - `research_areas/seams/apparatus/engine/GP-125_differentiable_topology_backend_seam.md`
   - Current role: articulate the frontier ambition and the continuous
     backend swap for operator-style math substrates.

### What is missing

The codebase does **not** currently contain:

1. **Structured proof-state telemetry**
   - `lean_repl.py` captures raw Lean stderr, but does not parse it into a
     stable state representation.

2. **Partial-progress scoring**
   - There is no artifact that says "attempt 4 is closer than attempt 3"
     except a human reading errors.

3. **Lemma / subgoal decomposition substrate**
   - No DAG of pending lemmas, blocked lemmas, or recurring goal families.

4. **Premise retrieval / theorem routing**
   - No bridge from current proof failures to relevant Mathlib lemmas,
     imported facts, or external premise stores.

5. **Fast non-Lean proof-side falsifiers**
   - No SMT / symbolic logic / countermodel layer dedicated to the proof loop
     itself before full Lean compilation.

## Core Diagnosis

`lean_repl.py` is currently an LLM retry shell around a binary kernel:

`proposal -> Lean compile -> error text -> retry`

That is enough for bounded local proof repair. It is not enough for
Millennium-adjacent proof search, because the loop has no persistent notion
of:
- what subgoal family is failing
- whether the search is making progress
- which missing lemma is decisive
- when the problem should be reframed as a premise-retrieval or lemma-split
  problem rather than "try another tactic"

The missing architecture is therefore **not** "Lean support." Lean support
already exists. The missing architecture is a **gradient-bearing proof search
substrate**.

## First Clean Slice

When implementation opens, the first slice should be:

### Slice A — proof-progress telemetry

Add a formal-proof artifact that records, per attempt:
- proof status: verified / compiles-with-sorry / hard fail
- error count
- error classes
- recurring failing theorem / goal signatures where extractable
- delta vs previous attempt
- attempt-level progress verdict: improved / stalled / regressed

This slice is decisive because it creates the first non-binary proof
signal without pretending to solve theorem decomposition or automated proving
in full.

### Why Slice A first

It is the proof-side analogue of GP-029 latent-distance observability:
- cheap
- passive
- does not replace Lean
- does not require a full theorem prover refactor
- tells us whether richer machinery is justified

## Deferred Slices

These remain explicitly out of scope for the first implementation:

1. **Lemma DAG planner**
   - Split theorem into sub-lemmas, dependency edges, blocked nodes.

2. **Premise retrieval**
   - Search Mathlib / local theorem corpus for candidate support lemmas.

3. **Proof-side non-Lean falsifier**
   - SMT / symbolic logic layer for fast contradiction or admissibility checks.

4. **Surveyability-aware proof steering**
   - Use proof complexity / sketch alignment inside the search loop, not only
     as a post-hoc filter.

## Acceptance Criteria For Opening Implementation

Implementation should not open until the seam is scoped to one concrete
artifact. The minimum acceptable first implementation is:

1. `lean_repl.py` emits a structured per-attempt proof-progress artifact.
2. The artifact is stable enough to compare attempt N to N-1.
3. The LLM prompt can receive a concise structured summary instead of only raw
   stderr.
4. No claims are made that theorem decomposition, premise retrieval, or
   proof-planning have been solved.

## Implementation Update

### 2026-04-28 20:43:07 EDT — Slice A shipped into the existing REPL

Implemented in `src/ztare/formal/lean_repl.py` without opening a second proof
loop or retiring the legacy path:

1. Added `proof_obligation_ledger.json` emission for each proof attempt.
2. Added attempt summaries with:
   - status: `hard_fail` / `compiles_with_sorry` / `verified`
   - error classes
   - extracted goal signatures
   - open-goal markers
   - delta vs previous attempt
   - progress verdict: `initial` / `improved` / `stalled` / `regressed`
3. Added repeated-stall classification into coarse bottleneck labels
   (`statement_translation`, `premise_retrieval`, `lemma_split`,
   `tactic_local`, `other_obstruction`).
4. Fed the structured summary back into the next LLM attempt instead of
   relying on raw Lean stderr alone.

Validation shipped with targeted tests in `tests/formal/test_lean_repl.py`:

- extractor coverage for imports / declarations / assumptions / open goals
- obstruction and stall classification coverage
- end-to-end `attempt_proof(...)` ledger write + structured-feedback reuse

What remains open by design:

- no lemma DAG
- no premise retrieval engine
- no SMT-side proof falsifier
- no claim of general theorem-search competence

## Non-Goals

- Not a full Lean proof-search engine
- Not a replacement for domain-expert mathematical reasoning
- Not a claim that pure proof Millennium problems are currently tractable in
  the apparatus
- Not a theorem of "ZTARE can now prove math"; this seam is about making the
  proof loop observable and steerable

## Honest Outcome

If Slice A ships and shows that proof attempts still wander with no stable
progress pattern, that is a positive result: it will identify whether the next
real bottleneck is:
- theorem decomposition
- premise retrieval
- proof-state routing
- or the absence of a proof-side continuous surrogate entirely

That is the point of the seam.

## Debate Panel

### Turn 1 — Terence Tao-style analyst (2026-04-28 20:30:39 EDT)

1. **Technical diagnosis of the current loop**

   The current proof path is not a proof-search engine; it is a post-champion
   repair shell. In `src/ztare/validator/autoresearch_loop.py`, the Lean path
   fires only after a thesis already scores `>= 70` and
   `enable_lean_proof` is set, then calls `prove_from_compression(..., max_attempts=5)`.
   In `src/ztare/formal/lean_repl.py`, that function picks the current
   gate-passing compression winner by BIC, sends the whole file to the LLM,
   runs Lean, and feeds back only a short list of raw error strings. The
   saved history is attempt number, the first 500 characters of code,
   success boolean, and raw errors. There is no persistent representation of
   goal state, no theorem-header integrity check inside the retry loop, no
   notion of subgoal recurrence, and no scoring of "closer" versus "farther."
   The surrounding proof gates do not repair this. `proof_surveyability_gate.py`
   is largely post-hoc and returns `passed: None` when the reviewer persona is
   blocked. `translation_diff_gate.py` has a real hash check, but its own
   comments say live pre/post capture is not wired into the loop. `ansatz_survivor_gate.py`
   advertises top-K proof shortness, but `run_gate(...)` calls the shortness
   function without `project_dir`, so it degrades to the blocked shell path.
   Finally, `ztare_proofs/README.md` still states that deductive proofs were
   "killed by design," which is consistent with the code: the stack certifies
   empirical bounds and conjecture boundaries much more strongly than it
   performs live theorem search.

2. **Whether the proposed proof-progress telemetry is decisive**

   Yes, but only as the first honest slice, not as the whole solution. Right
   now the loop cannot distinguish three very different failure modes:
   tactic-local failure, statement/translation corruption, and missing-lemma
   failure. Because `lean_repl.py` stores only raw error text and retries,
   the apparatus has no internal variable corresponding to proof progress at
   all. A structured per-attempt artifact is therefore decisive in the
   narrow sense that it creates the first observable state for proof search:
   theorem header preserved or changed, `sorry` count, error-count delta,
   recurring unresolved identifiers, recurring theorem names, timeout versus
   parser failure versus typeclass failure versus goal-mismatch failure, and
   whether the new attempt strictly reduces the support of the previous error
   family. That will not prove the theorem, but it will separate "the loop is
   wandering randomly" from "the loop is repeatedly hitting one missing
   lemma." Without that distinction, the next layer cannot be chosen
   rationally.

3. **What would falsify the seam's premise**

   The seam's premise is false if observability is not the binding
   bottleneck. Three concrete falsifiers would do it. First, if replay on
   existing Lean attempt histories shows that simple telemetry features do
   not correlate at all with eventual proof success or with human judgments
   of progress, then the proposed middle layer is mostly bookkeeping.
   Second, if wiring the already-declared GP-144 paths reveals that semantic
   drift or statement corruption dominates failures, then the decisive
   gap is translation integrity, not progress telemetry. Third, if a small
   benchmark of proof-target substrates improves materially just by adding
   premise retrieval or lemma decomposition while telemetry adds little, then
   the premise has been inverted: the real missing middle layer is theorem
   decomposition, and telemetry is diagnostic but not central.

## Debate Log

### Turn 1 — Ramanujan-style mathematician (2026-04-28 20:30:49 EDT) — The missing object is a proof-relevant lemma scaffold, not merely better retries

1. **What the real missing mathematical object is**

   The missing object is not "more Lean attempts." It is a
   **proof-relevant intermediate mathematical object** between
   `src/ztare/formal/lean_compiler.py` and
   `src/ztare/formal/lean_repl.py`: a canonical lemma scaffold that states
   the theorem, assumptions, admissible transformations, and recurring goal
   families in a stable form. The repo state is decisive here:
   `ztare_proofs/README.md` says Product C deductive proofs are "killed by
   design"; `lean_compiler.py` says `expression_to_lean()` is "approximate"
   and produces "readable pseudocode, not valid Lean"; `lean_repl.py`
   currently asks an LLM for a complete Lean file and feeds back raw error
   strings. That means the proof stack is missing the mathematical object
   over which search should range. Without that object, the system is not
   failing only on tactics; it is failing to preserve the conjecture's
   shape in a proof-searchable form.

2. **Whether GP-187 Slice A is the right first move or a distraction**

   Slice A is the right first move **only if it is treated as observability,
   not as the mathematical fix itself**. In the current repo,
   `lean_repl.py` stores attempt history as `{success, errors, code[:500]}`;
   there is no stable notion of goal family, blocked lemma, or preserved
   theorem shape. So telemetry is necessary. But plain error telemetry over
   an ill-posed proof object is still shallow. If the compiler has not yet
   produced a canonical theorem-and-lemma skeleton, then measuring error
   counts is measuring turbulence, not proof progress. So Slice A is not a
   distraction, but it is one layer too late if scoped only as "parse Lean
   stderr better."

3. **One concrete recommendation**

   Re-scope Slice A to emit a `proof_obligation_ledger.json` artifact for
   each attempt. Minimum contents: theorem statement, imported dependencies,
   explicit assumptions, every `sorry` site or open-goal header, normalized
   goal signatures where extractable, and delta vs prior attempt. Do **not**
   open lemma-DAG automation yet. First force the system to preserve the
   mathematical shape of the conjecture across
   `lean_compiler.py -> .lean stub -> lean_repl.py`. That ledger is the
   real decisive object; later telemetry, premise retrieval, and lemma
   decomposition can attach to it cleanly.

## Panel Turn — Judea Pearl-Style Causal/Diagnostic Methodologist (2026-04-28 20:30:26 EDT)

1. **What variable is unobserved in the present proof loop**

   The unobserved variable is not "proof quality" in the abstract. It is the
   **latent proof obstruction state**: which subgoal family is live, which
   obligations were discharged, which missing lemma/import/type alignment is
   decisive, and whether attempt `t+1` is causally closer to discharge than
   attempt `t`.

   In current repo state, the proof path is:

   `champion score >= 70 -> autoresearch_loop.py dispatch -> lean_repl.py LLM retry -> check_lean() -> raw error lines -> retry`

   The loop in `src/ztare/formal/lean_repl.py` observes only a lossy proxy for
   this state: a truncated stderr plus a list of lines containing `"error"`.
   `src/ztare/validator/autoresearch_loop.py` treats the Lean attempt as a
   post-champion binary sidecar, and `src/ztare/gates/proof_surveyability_gate.py`
   is a downstream filter, not a state observer. So the causally decisive
   mediator between candidate proof and next action is present in the system but
   unmeasured.

2. **Whether Slice A identifies the right intervention surface**

   **Yes, for the first intervention.** Slice A targets the correct surface
   because it intervenes on the measurement channel between Lean and the next
   proposal, not on the theorem content itself.

   That is the right order of operations. If you intervene first on tactic
   prompting, lemma planning, or Mathlib retrieval before instrumenting the
   obstruction state, you cannot distinguish:
   - search failure,
   - missing-premise failure,
   - decomposition failure,
   - or parser/typing churn.

   Slice A is therefore the cleanest first move because it tests whether the
   missing variable is mainly **observability**. It does **not** solve the full
   causal graph; it only identifies whether richer proof machinery is justified.

3. **The cleanest discriminating experiment**

   Run a fixed-stub, fixed-budget A/B replay using existing repo proof artifacts
   in `ztare_proofs/ZtareProofs/*.lean` plus a small set of intentionally
   blocked variants derived from them.

   Arm A: current loop (`lean_repl.py` as-is, raw stderr feedback only).

   Arm B: same model, same max attempts, same theorem stubs, but replace raw
   stderr feedback with a structured Slice A summary:
   - status class: typecheck / compiles-with-sorry / hard fail
   - error classes
   - recurring goal signature where extractable
   - delta vs previous attempt
   - verdict: improved / stalled / regressed

   Primary discriminator: does Arm B produce a materially higher rate of
   **monotone progress** on near-solved stubs than Arm A?

   Concretely, measure:
   - first attempt reaching `compiles-with-sorry`
   - reduction in repeated identical error clusters across attempts
   - number of attempts classified `improved` before exhaustion
   - final proof success rate, secondarily

   Interpretation:
   - If B beats A on monotone progress, the missing variable was largely
     observational and Slice A is the right seam.
   - If B does not beat A, the missing variable lies upstream in lemma
     decomposition or premise retrieval, and the next seam should move there.

## Panel Turn — 2026-04-28 21:13:42 EDT — Feynman-Style Systems Engineer

### 1. Where the current loop is fooling itself

The current loop is pretending that "retry after Lean rejection" is a search
mechanism when it is really a post-hoc certification shim. In
`src/ztare/validator/autoresearch_loop.py`, the Lean path only fires after a
champion already scores `>= 70` (`GP-122: Post-champion Lean proof attempt`),
so proof is not steering the main search; it is bolted on after the apparatus
already believes it found something. In `src/ztare/formal/lean_repl.py`, the
state carried across attempts is basically `current_code` plus up to five raw
error strings. There is no persistent object for subgoals, blocked lemmas, or
attempt-to-attempt movement. Worse, the prompt explicitly says "start with
sorry first to check the statement compiles, then replace with real tactics,"
which can generate the feeling of motion without any theorem-level progress.
Finally, `ztare_proofs/README.md` is honest that Product C deductive proofs are
"Killed by design" and that the shipped Lean path mainly certifies empirical
bounds or publishes conjectural gaps. Treating this stack as if it already
contains a proof-search engine is the self-deception.

### 2. Whether Slice A creates a real signal or just prettier logs

Slice A creates a real signal only if it changes the state representation of
the loop, not merely the readability of the transcript. Right now
`lean_repl.py` stores attempt history as `attempt`, a 500-character code
prefix, `success`, and raw `errors`. That is better than nothing, but it is
not yet a search substrate. If Slice A merely counts errors or prettifies Lean
stderr, it is cosmetic. It becomes real when the apparatus can say things like:
"attempt 4 eliminated parse/import failures but preserved the same unsolved
goal family," or "the loop is stuck in a missing-lemma regime, not a tactic
repair regime." That would be the first proof-side analogue of a gradient:
coarse, discontinuous, but directional. The key test is not whether humans get
better logs; it is whether attempt `N+1` can be steered differently from
attempt `N` because the artifact expresses a stable failure class.

### 3. One next-step recommendation

Tighten the seam so Slice A is only considered successful if it changes control
flow on a closed proof-target example. Concretely: require the progress
artifact to classify each attempt into a small canonical set such as
`parse/import`, `contains_sorry`, `unknown_identifier`, `tactic_mismatch`,
`unsolved_goal_family`, `timeout`, and `verified`; then require one explicit
policy edge, e.g. three consecutive attempts in the same class force the loop
to stop retrying and label the bottleneck as "needs lemma split or premise
retrieval." Without that control-flow consequence, Slice A is just better
telemetry for a loop that still does not know what it is doing.

## Panel Turn — Kevin Buzzard / Lean Formalization Lens (2026-04-28 21:31:12 EDT)

1. **What exists already**

   There is already a small Lean-adjacent toolchain here, but it is much
   narrower than "serious Lean search." `src/ztare/formal/lean_repl.py` is a
   batch retry loop: it asks an LLM for an entire Lean file, runs `lake env
   lean` on a temporary file, extracts stderr lines containing `"error"`, and
   retries with at most five raw error strings fed back into the next prompt.
   That is real infrastructure, but it is not interactive proof-state search.
   `src/ztare/gates/proof_surveyability_gate.py` is even further downstream: it
   checks a finished `.lean` file for forbidden strings like `sorry` and
   `axiom`, counts lines, and leaves two of its three sub-gates explicitly
   deferred. It is a hygiene filter on completed artifacts, not a proving
   engine. `ztare_proofs/README.md` is admirably honest about the scope: most of
   the shipped artifacts are `#eval`-based certified empirical bounds, while the
   deductive-proof path is "Killed by design." So yes, there is Lean support in
   the repo, but it is support for compilation, certification, and packaging,
   not for navigating a hard theorem proof.

2. **What is naively missing for serious Lean search**

   The obvious missing piece is not "more retries"; it is access to the actual
   mathematical state of the proof. The present loop does not inspect goals,
   local hypotheses, metavariables, tactic state transitions, or lemma
   applicability. It rewrites whole files and reads error text after the fact.
   For serious Lean work, one normally needs at least some combination of:
   stable goal-state capture, declaration-scoped editing rather than full-file
   regeneration, theorem/premise retrieval from Mathlib, and a way to
   distinguish parser/import trouble from a genuinely interesting missing-lemma
   obstruction. None of that is present in the audited files. The current
   `ztare_proofs` objects are mostly numeric checks and explicit conjectural
   boundaries, which is fine, but it means the apparatus has not yet crossed
   into the world where Lean is being used as a research proof assistant rather
   than as a certifier of already-formed artifacts.

3. **Whether the seam's first slice is the right cut**

   Broadly yes, but only if "proof-progress telemetry" means telemetry about
   Lean proof state rather than prettier stderr summaries. As written, the seam
   is directionally right: do not jump straight to lemma DAGs or premise
   retrieval before measuring where the current loop actually fails. But a
   telemetry slice that merely classifies error strings will be too weak. The
   right first cut is: extract a stable per-attempt representation of the proof
   state that can answer simple questions such as "are we failing on the same
   unsolved goal?", "did imports/typeclass issues disappear?", and "did this
   attempt reduce the obligation set or just move text around?" If Slice A is
   tightened to that standard, it is the correct seam. If not, it risks
   producing nicer logs for a loop that still has no mathematical traction.

## Munger Synthesis — 2026-04-28 21:36:20 EDT

### What the panel agrees on

1. **The seam is real.**

   Every seat converged on the same decisive diagnosis: the repo has Lean
   compilation, Lean retries, and post-hoc proof hygiene, but it does not yet
   have a proof-search middle layer. `lean_repl.py` is a retry shell around a
   binary kernel, not a stateful proof-search substrate.

2. **The missing thing is not "Lean support."**

   The missing thing is a **gradient-bearing proof object**. The panel named it
   in slightly different ways:
   - Ramanujan: proof-relevant intermediate scaffold
   - Pearl: latent proof obstruction state
   - Feynman: state that changes control flow rather than prettier logs
   - Buzzard: actual proof-state access rather than whole-file rewrite
   - Tao: enough structure to distinguish tactic failure from translation or
     missing-lemma failure

3. **Slice A is the right first cut only as observability.**

   No seat argued to jump directly to lemma DAGs or premise retrieval. The
   common view is: first make the loop capable of observing its own proof-side
   failure classes, then decide whether the next bottleneck is decomposition,
   retrieval, or translation integrity.

### Where the panel is sharpening the seam

The original seam described Slice A mainly as proof-progress telemetry. The
panel tightened that in three ways:

1. **Telemetry must be tied to a stable object.**

   Raw stderr classification is not enough. The first artifact should preserve
   theorem statement, imports, assumptions, `sorry` / open-goal sites, and
   normalized obstruction signatures where extractable.

2. **Telemetry must change control flow.**

   A "progress artifact" that does not alter the retry policy is just better
   logging. Minimum bar: repeated identical obstruction classes should trigger a
   new label such as `needs_lemma_split` or `needs_premise_retrieval`.

3. **The seam must be falsifiable.**

   The clean test is not "did logs get nicer?" It is whether structured
   feedback materially improves monotone progress on fixed proof stubs compared
   to raw stderr replay.

### Final Recommendation

**Recommendation: keep GP-187 open exactly as a proof-search observability seam,
but tighten Slice A before implementation opens.**

Concretely, the first implementation target should be renamed in spirit from
"proof-progress telemetry" to:

**`proof_obligation_ledger` + progress classification**

Minimum acceptance criteria for opening implementation:

1. Emit a structured artifact per attempt containing:
   - theorem statement
   - imports
   - assumptions
   - proof status: `verified` / `compiles_with_sorry` / `hard_fail`
   - canonical obstruction classes
   - normalized open-goal or obligation signatures where extractable
   - delta vs prior attempt

2. Add a coarse policy edge:
   - repeated same obstruction class stops blind retry and labels the bottleneck
     as one of `statement_translation`, `lemma_split`, `premise_retrieval`, or
     `tactic_local`

3. Validate the seam on a fixed-stub A/B replay:
   - Arm A: raw stderr only
   - Arm B: structured ledger summary
   - Success criterion: B improves monotone proof progress, not merely human
     readability

### What not to do next

- Do **not** claim theorem decomposition is solved
- Do **not** open a full lemma-DAG or retrieval implementation before the A/B
  replay
- Do **not** call this a proof engine upgrade yet; it is an observability and
  routing upgrade

### One-sentence verdict

**ZTARE's proof stack is currently a certifier with retries; GP-187 should turn
it into an observable proof-search loop before any heavier formal-math
architecture is built.**
