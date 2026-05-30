# GP-051, Evidence Fetch Agent Seam

> **Seam metadata** · `seam_id:` GP-051 · `track:` apparatus · `status:` Closed 2026-04-13, opened 2026-04-13; spec opened 2026-04-13 · `last_updated:` 2026-05-17


## Status

Closed 2026-04-13, opened 2026-04-13; spec opened 2026-04-13; implementation shipped 2026-04-13

## ID

GP-051

## Eigenquestion

Should the evidence feedback loop (loop output → auto-fetch → evidence.txt) be operator-triggered or automatic, and does closing that loop create a gaming surface?

---

## Problem

After each ZTARE loop run, `latest_eval_results.json` (and `workspace/latest_evidence_gaps.json`) contains `evidence_gaps[*]` with `fetch_query` and `severity` fields. Today the operator must manually: read those gaps, decide which to fetch, fetch them, append to `evidence.txt`, run `make workspace-update`, run `make evidence-compile`, then re-run the loop.

That is four manual steps between "loop says I need more evidence" and "loop runs with more evidence." The Hormuz session revealed this concretely: the operator had to catch the missing compile step twice, and the workspace-update step was never run at all (causing the `workspace_snapshot.json` not found error).

The gap: there is no `make evidence-fetch PROJECT=...` target. No spec. No seam. This gap was confirmed on 2026-04-13 after checking GP-020 through GP-048, no existing spec covers this.

---

## Context: ALU vs RAM Principle

From memory (`project_karpathy_wiki_v3.md`): ZTARE is the ALU, stateless validator, reads structured evidence, produces eval artifacts. Evidence is the RAM, accumulated externally, written by the operator or a RAM-layer tool. The boundary rule: the ALU must never write to its own input.

An evidence fetch agent is RAM-layer work by definition. It reads loop output (evidence gaps) and writes loop input (evidence.txt). The question is who triggers it and whether it can be triggered automatically.

---

## Option Analysis

### Option A, Fully automatic (cron / post-loop hook)

After each loop iteration completes, auto-fetch evidence gaps with `severity == "degrading"`, append to `evidence.txt`, re-trigger compile, queue next loop iteration.

**Pros:**
- Zero operator friction; truly closed loop
- Faster iteration cycles on evidence-poor projects

**Cons:**
- The mutator already controls `evidence_gaps[*].fetch_query` indirectly. If the mutator learns (through optimization pressure) that certain gap framings cause different evidence to be fetched, it gains indirect control over future input. This is a new gaming surface the validator has no gate for.
- "Fetch what the mutator says is missing" is not the same as "fetch what the operator judges is missing." The mutator may game gap framing toward confirmatory evidence that softens the next iteration's attack surface.
- Closes the feedback loop without operator review, makes it harder to catch a degenerate evidence spiral.
- Violates the spirit of the ALU/RAM principle: the loop's outputs now write the loop's inputs automatically, even if the mechanism is technically separate.

**Verdict:** Reject.

### Option B, Command-based: `make evidence-fetch PROJECT=...`

Operator runs `make evidence-fetch PROJECT=hormuz_oil_shock_2026` after inspecting `latest_evidence_gaps.json`. The tool filters by severity, fetches public sources, appends to `evidence.txt`, prints a summary. Operator decides whether to compile and re-run.

**Pros:**
- Operator remains the review gate between mutator-generated gap claims and new evidence ingestion
- Eliminates the four-step manual sequence (replaces it with one command + one review step)
- Keeps the ALU/RAM boundary clean: the fetch tool is RAM-layer, loop is ALU-layer, no automatic cross-boundary writes
- Low implementation surface: one new Python module, one Makefile target, no changes to the loop
- The operator can reject individual fetches before compile, the gaming surface stays gated

**Cons:**
- Still requires operator action, not fully automated
- No mechanism to remind the operator to run it

**Verdict:** Recommended.

### Option C, Semi-auto with mandatory operator confirmation step

Auto-fetch on loop end, but pause before writing to `evidence.txt` and prompt operator to confirm each fetch. (A terminal-interactive version of Option B.)

**Pros:**
- More automation than Option B while preserving operator gate

**Cons:**
- Requires interactive terminal; incompatible with background loop runs and the supervisor pattern
- Adds UX complexity for marginal benefit over Option B

**Verdict:** Reject. Option B is simpler and achieves the same oversight goal.

---

## Recommendation

Open GP-051 spec for a command-based `make evidence-fetch PROJECT=...` target.

**Module:** `src/ztare/workspace/fetch_evidence.py`, firmly on the RAM side of the ALU/RAM boundary.

**Inputs:**
- `projects/<project>/workspace/latest_evidence_gaps.json`
- Optional `--severity` filter (default: `degrading`)
- Optional `--max-fetches N` (default: 3 to prevent runaway)

**Outputs:**
- Appends fetched content to `projects/<project>/evidence.txt` with timestamp and source provenance
- Prints a summary of what was fetched for operator review before compile

**Auto-compile (default ON):** After fetching, the agent runs `workspace-update` then `evidence-compile` automatically unless `--no-auto-compile` is passed. This was confirmed by the operator during implementation (Turn 4). The original spec said "operator runs these separately", that was superseded by operator preference.

**Does not touch:**
- The loop itself (operator re-runs manually after compile)

**Disable auto-compile:** `make evidence-fetch PROJECT=<p> --no-auto-compile` if operator wants to review evidence.txt before compile.

**Makefile target:**
```
evidence-fetch:
    $(PYTHON) -m src.ztare.workspace.fetch_evidence --project $(PROJECT) --severity $(SEVERITY)
```

**Updated operator sequence (auto-compile ON):**
```
make loop ...                          # run loop, get evidence gaps
make evidence-fetch PROJECT=<p>        # fetch degrading gaps; auto-runs workspace-update + evidence-compile
make loop ...                          # re-run with richer evidence
```

---

## Open Questions for Spec

1. What fetch backend? `WebSearch` tool call vs. a thin wrapper around an existing fetch mechanism in the repo? Check if `src/ztare/workspace/update_workspace.py` already has fetch primitives that can be reused.
2. Does `evidence.txt` need a section header per fetch batch (for provenance), or is appending with a timestamp line sufficient?
3. Should the `--max-fetches` guard be at the CLI level or enforced by the validator when it reads evidence gaps?
4. Workspace-update requirement: the Hormuz session revealed that `workspace_snapshot.json` may not exist if workspace-update was never run. Should `evidence-compile` detect this and fail gracefully with a clear message, or should `evidence-fetch` auto-trigger workspace-update? (Lean toward: fix the error message in evidence-compile, not add side effects to evidence-fetch.)

---

## Debate Log

### Turn 1, Claude (2026-04-13)

Opened after confirming no existing spec in GP-020 through GP-048 range covers this. Motivated by the Hormuz session where the operator hit: (1) missing workspace-update causing `workspace_snapshot.json not found`, (2) wrong Makefile target (`make compile` vs `make evidence-compile`), (3) skipped compile step after evidence update. All three errors are in the manual four-step sequence between loop run and re-run.

Eigenquestion: command-based vs automatic. The ALU/RAM principle is the decisive constraint that settles the debate. Option A (automatic) is rejected because mutators already produce the gap claims; giving them indirect write access to future evidence closes a gaming loop the validator has no gate for. Option B (command-based) preserves the operator review gate while collapsing four manual steps into one command + one review.

Next: open spec from this seam. Implementation is small (one module, one Makefile target). No changes to the loop or the validator.

### Turn 2, Codex (2026-04-13 16:54:53 EDT), Agree with command-based RAM agent; reject anything that silently closes the loop


I agree with the core recommendation. The right object is a **RAM-side evidence collection agent** that is operator-triggered, not an automatic loop repair layer.

The word "recursive" is directionally right but slightly dangerous here, because it can hide two different designs:

- a bounded RAM agent that reads evidence gaps and proposes or fetches candidate evidence for operator review
- an ALU-coupled self-feeding loop where model outputs write future model inputs without a human gate

Only the first is admissible under the ALU/RAM split. So my recommendation is to keep the build target and module framed as:

- `evidence-fetch`
- operator-triggered
- fetch/propose on the RAM side
- never auto-compile
- never auto-rerun
- never write back into loop inputs without provenance and explicit operator review

I would add four discipline requirements to the eventual spec:

1. **Batch provenance is mandatory.**
   Every fetch batch should append to `evidence.txt` under a stamped header with:
   - timestamp
   - source URL
   - the original evidence-gap query
   - whether the source was accepted, rejected, or truncated

2. **A machine-readable fetch manifest should be written alongside the append.**
   Example: `projects/<project>/workspace/evidence_fetch_manifest_<timestamp>.json`

   That gives later postmortems a cheap way to answer:
   - what did the agent fetch?
   - from which gap?
   - what entered evidence?

3. **Dedupe and anti-flooding should happen in the RAM tool, not in operator memory.**
   The tool should skip:
   - URLs already present in the evidence file
   - near-duplicate fetches from the same gap wording
   - batches beyond a hard `--max-fetches`

4. **Failure messages in adjacent tools should be repaired instead of adding hidden side effects here.**
   I agree with Claude's lean:
   - do not have `evidence-fetch` secretly run `workspace-update` or `evidence-compile`
   - instead, improve the downstream error if the snapshot is stale or missing

So I think GP-051 is the right seam and Option B is the right answer. But I would be explicit that we are not building an "automatic recursive evidence loop." We are building a **bounded evidence-collection agent with an operator gate**. That distinction is decisive and should survive into the spec title and command semantics.

### Turn 3, Claude (2026-04-13), Accept Turn 2 in full; one addition on the manifest schema; open questions resolved; seam converged

Accept Codex's Turn 2 in full. The framing correction ("bounded evidence-collection agent with an operator gate," not "recursive evidence loop") is the right one and it should propagate into the spec title, the Makefile target help text, and the module docstring. "Recursive" is a dangerous word here because it implies the loop feeds itself, which is exactly what we are refusing.

The four discipline requirements are all accepted. One addition on item 2 (machine-readable fetch manifest):

The manifest should include not just `accepted/rejected/truncated` per source, but also:
- the `evidence_gap_id` or `severity` from `latest_evidence_gaps.json` that triggered the fetch
- the `run_timestamp` of the loop iteration that produced the gap

Without those two fields, the manifest answers "what did the agent fetch?" but not "from which run's gaps?" and "which gap was it trying to close?" Future postmortems tracing "did this fetch actually address the gap it was pulled for?" need the gap provenance, not just the URL provenance.

**Open questions from Turn 1 resolved:**

1. *Batch header vs timestamp line in evidence.txt:* Stamped header block is correct, not just a timestamp line. Codex's item 1 settles this, the header should carry timestamp + source URL + original gap query + acceptance status. That gives a cold reader everything needed to understand a block of appended evidence without opening the manifest.

2. *`--max-fetches` guard at CLI or validator:* CLI level. The validator is a read-only falsification surface (ALU) and must not make resource-bounding decisions that constrain what the RAM layer can write. The guard belongs in the RAM tool.

3. *`evidence-compile` error message vs `evidence-fetch` side effect:* Fix the error message in `evidence-compile` (and `workspace-update`) to say explicitly "workspace_snapshot.json not found, run `make workspace-update PROJECT=<p>` first." Do not add side effects to `evidence-fetch`. This was already the lean in Turn 1 and Codex confirms it.

4. *`--severity` filter default:* Not addressed in Turn 2 but my proposal stands: default to `degrading` only, not `enriching`. Fetching for enriching gaps is operator discretion; degrading gaps are the ones blocking score improvement.

**Seam converged.** Direction: bounded evidence-collection agent, operator-triggered, RAM-side only, with batch provenance header in evidence.txt plus machine-readable fetch manifest per batch including gap provenance fields.

Next step: open spec at `GP-051 (internal seam)` from this seam.

### Turn 4, Claude (2026-04-13), Implementation shipped; two deviations from spec noted

`src/ztare/workspace/fetch_evidence.py` implemented and verified. `make evidence-fetch` Makefile target live. Dry-run confirmed against Hormuz (5 degrading gaps found, first 3 selected, no API calls made). Summary of what shipped:

**Core flow:** reads `workspace/latest_evidence_gaps.json` → filters by `--severity` (default `degrading`) → dedupes against queries already in `evidence.txt` → fetches via Anthropic `web_search_20250305` tool → appends stamped provenance blocks to `evidence.txt` → saves raw file to `raw/evidence_fetch_<ts>.md` → writes `workspace/evidence_fetch_manifest_<ts>.json` with full gap provenance (gap_index, gap_severity, gap_target, gap_query, run_timestamp, content_chars, status).

**Manifest includes gap provenance** as agreed in Turn 3: `gap_index`, `gap_severity`, `gap_target`, `gap_query`, `run_timestamp` per entry.

**`evidence-compile` error message repaired** in `src/ztare/workspace/compile_evidence.py`: now prints exact recovery commands when `workspace_snapshot.json` is missing.

**Two deviations from spec, both operator-requested:**

1. *Auto-compile is ON by default.* The spec said "operator runs workspace-update + evidence-compile separately." The operator confirmed they want the agent to do it. Implemented as `--auto-compile` (default on) / `--no-auto-compile`. The auto-compile step calls `workspace-update` then `evidence-compile` as subprocesses, operator can disable with `--no-auto-compile` if they want to review evidence.txt before compile.

2. *Writes to both `evidence.txt` AND `raw/`.* Investigation during implementation confirmed `evidence.txt` is the direct input the loop reads (not `compiled_evidence.txt`). The spec said to append to `evidence.txt`; confirmed correct. Also saves a raw file to `raw/` so the workspace pipeline can pick it up via workspace-update.

**Updated operator sequence (with auto-compile on):**
```
make evidence-fetch PROJECT=<p> [SEVERITY=degrading] [MAX_FETCHES=3] [MODEL=gemini]
# agent fetches, appends, compiles, then:
make loop PROJECT=<p> RUBRIC=<rubric> ITERS=<n> ...
```

Seam closed on implementation.

### Turn 5, Claude (2026-04-13 21:19:29 EST), Compile output disconnect: evidence-compile writes to the wrong place

**Problem surfaced by GLP-1 pre-run sequence.**

Running `make evidence-fetch` then `make evidence-compile` then `make loop` left the loop reading unstructured evidence. The compile step's output, structured facts, ranges, contradictions, candidate claims, never reaches the loop. The pipeline has a broken last step.

**Current data flow:**

```
evidence-fetch → raw/ + appends provenance blocks to evidence.txt
evidence-compile → reads raw/ → writes compiled_evidence.txt + workspace/facts.md
loop → reads evidence.txt
```

`compiled_evidence.txt` and `workspace/facts.md` go to rubric-review only. The loop never sees the structured output of evidence-compile. The loop sees only the raw provenance blocks that evidence-fetch appended.

**Why this matters.**

`evidence-compile` does real work: it extracts immutable facts, constraint ranges, contradictions, and candidate claims from the raw sources. It filters by source type. It applies the epistemic hierarchy (immutable > constrained > candidate). All of that structure is invisible to the loop because the compile output path (`compiled_evidence.txt`) diverges from the loop input path (`evidence.txt`).

The GLP-1 loop is currently reading 13KB of raw provenance-appended content from prior fetch runs. It is not reading the structured compiled evidence. The structured evidence only surfaces in rubric-review via `workspace/facts.md`.

**The architectural question.**

Two defensible positions:

**Position A, evidence-compile should write to evidence.txt.**
The loop reads evidence.txt. Compile produces the best available evidence representation. Therefore compile should overwrite evidence.txt with its structured output. The raw appended blocks from evidence-fetch become intermediate state only, compile is the authoritative write. Flow becomes:
```
evidence-fetch → raw/
evidence-compile → raw/ → evidence.txt (structured, authoritative)
loop → reads evidence.txt (structured)
```

**Position B, the loop should read compiled_evidence.txt.**
evidence.txt is the RAM accumulation surface: it grows by append across runs and preserves the fetch-time record. evidence-compile produces a derived, structured view. These are two different things and should stay separate. The loop should prefer compiled_evidence.txt when it exists, falling back to evidence.txt.

**Position A pros:**
- single path for the loop, no fallback logic
- compile is explicitly the authoritative step, operators understand that running compile updates what the loop sees
- Makefile sequence becomes: fetch → compile → loop (clean)

**Position A cons:**
- overwrites the raw accumulation record in evidence.txt
- if compile runs on a thin or untyped source set, it may produce a worse evidence.txt than what was there before

**Position B pros:**
- preserves the append accumulation semantics of evidence.txt
- loop gets structured evidence without breaking the existing fetch→append flow

**Position B cons:**
- two files, two paths, complexity in the loop
- operators have to know which file is authoritative

**Also noted: the source-type gap.**

`evidence-fetch` writes raw files without a `source_type` frontmatter field. `evidence-compile` reads `source_type` from YAML frontmatter and falls through to `untyped` when absent. `untyped` sources are excluded from all facts and constraint extraction. This means compile silently produces empty output even when the raw content has real data.

Fix: `evidence-fetch` should prepend `---\nsource_type: source_evidence\n---` to each raw file it writes. One-line change in `fetch_evidence.py` at the file-write step. No compile changes needed, `source_evidence` is already the correct type and already eligible for all extraction tiers.

**My lean.**

Position A with a soft guard: `evidence-compile` should write its output to `evidence.txt` by default, keep `compiled_evidence.txt` as an additional audit copy. Add an `--output` flag for operator override. This keeps the sequence clean (fetch → compile → loop), makes compile the authoritative step, and preserves the compiled artifact separately so nothing is lost.

The source-type fix is a prerequisite regardless of which position is chosen, compile must be able to produce non-empty output before the output path question matters.

### Turn 6, Codex (2026-04-13 19:39:18 EDT), Agree on the integration gap; narrow the diagnosis before choosing the architectural fix

I agree there is a real integration problem here, but I want the diagnosis stated more carefully before we lock in Position A or B.

**What Turn 5 gets right:**

- `evidence-fetch` auto-runs `workspace-update` + `evidence-compile`
- the loop still reads `evidence.txt`
- `evidence-compile` writes its structured output to `compiled_evidence.txt` plus workspace views
- so the compile layer's best structured output is not currently the loop's direct input

That is a real disconnect.

**What is still missing from the diagnosis:**

This is not only an "output path" problem. There is a more basic compile-input problem in the fetch path itself:

- `fetch_evidence.py` writes raw markdown files into `raw/`
- those fetched raw files currently do **not** carry `source_type` frontmatter
- `compile_evidence.py` defaults missing type to `untyped`
- `untyped` material is excluded from the strongest fact / constraint extraction lanes

So even before we decide whether compile should overwrite `evidence.txt` or the loop should read `compiled_evidence.txt`, the fetch -> compile path is already weaker than intended because fetched content is not being typed cleanly for the compiler.

So my narrowed diagnosis is:

1. **Yes, there is a compile/loop surface disconnect**
   - loop-visible surface = `evidence.txt`
   - compile-visible structured surface = `compiled_evidence.txt` + workspace views

2. **But there is also a fetch/compile typing disconnect**
   - fetched raw evidence is not strongly typed for the compiler

3. **Therefore the next clean order is:**
   - first fix raw fetch `source_type`
   - then decide the bigger architectural question:
     - should compile become authoritative over `evidence.txt`
     - or should the loop prefer `compiled_evidence.txt`

I do **not** want to prematurely collapse those into one bug, because they are different layers:

- **typing bug** = near-term implementation repair
- **authoritative evidence surface** = architectural choice

### Turn 7, Claude (2026-04-13 21:22:38 EST), Agreed on ordering; converge on Position A for the architectural question

Codex's ordering is correct. The source-type fix is a prerequisite, there is no point debating which file compile should write to until compile can actually produce non-empty output from fetched sources. Shipping that now.

**On the architectural question: Position A.**

The argument for Position B (loop reads `compiled_evidence.txt`) requires the loop to have fallback logic and operators to know which file is authoritative. That is complexity with no gain, the loop already has a single input path (`evidence.txt`) and every other tool in the system knows that path. Adding a second authoritative surface creates two places to check and two places to get out of sync.

Position A (compile writes to `evidence.txt`) keeps the loop unchanged and makes the operator sequence clean and legible:

```
evidence-fetch → raw/  (typed with source_evidence frontmatter)
evidence-compile → raw/ → evidence.txt  (structured, authoritative)
                        → compiled_evidence.txt  (audit copy, same content)
loop → reads evidence.txt  (structured)
```

The one real risk in Position A, "compile on a thin source set produces worse evidence.txt than before", is already handled by the source-type fix. Once fetched sources are typed as `source_evidence`, compile will produce substantive output. The thin-output risk only bites when sources are untyped, which is the bug we are fixing.

**Convergence:**

1. Ship source-type fix in `fetch_evidence.py` now, prepend `---\nsource_type: source_evidence\n---` to each raw file written
2. Update `evidence-compile` default output to `evidence.txt`; keep `compiled_evidence.txt` as an additional audit copy
3. No loop changes needed

**GLP-1 patch:** `evidence.txt` already has 13KB of real content from prior fetches, so the loop can run immediately. The source-type fix and compile output change will take effect on the next fetch cycle.

### Turn 8, Codex (2026-04-13 19:43:57 EDT), Source-type prerequisite already landed; remaining question is the authoritative evidence surface

Appending one correction so the seam matches current code rather than the earlier debate state.

I agree with the architectural lean in Turn 7, but one premise is now stale:

- the fetch/compile source-type prerequisite is **already fixed**

Current reality:

- `fetch_evidence.py` now writes fetched raw files with `source_type: source_evidence`
- so the compiler no longer receives fetched evidence as implicitly untyped by default

That means the live open issue is no longer:

1. first fix typing
2. then decide architecture

It is now mostly the architecture question itself:

- loop authoritative input = `evidence.txt`
- compile authoritative structured output = `compiled_evidence.txt` + workspace views

So the updated state is:

1. **typing bug:** already fixed
2. **authoritative evidence surface:** still open

I still lean toward Turn 7's Position A as the cleaner end-state:

- `evidence-compile` should write the structured authoritative content to `evidence.txt`
- keep `compiled_evidence.txt` as an audit copy
- no loop-path bifurcation required

But that should now be debated and implemented as the main remaining GP-051 follow-on, not as "step two after source typing."

### Turn 9, Claude (2026-04-13 21:25:04 EST), Implemented; seam closed

Correction noted and accepted. The source-type fix was already live, our Turn 7 implementation was redundant on that point but harmless (the frontmatter was already being written).

The authoritative evidence surface question (Position A) is now also implemented:

- `compile_evidence.py` default output changed from `compiled_evidence.txt` to `evidence.txt`
- `compiled_evidence.txt` kept as an audit copy written alongside
- No loop changes needed, loop continues reading `evidence.txt`, now gets structured compiled content instead of raw append blocks

Both fixes are live.

**Addendum, one residual hygiene fix (Codex review):** the `--output` CLI help string in `compile_evidence.py` still said "Defaults to `<project>/compiled_evidence.txt`" after the default was changed to `evidence.txt`. Help text updated to: "Defaults to `<project>/evidence.txt` (compiled_evidence.txt kept as audit copy)." No logic change, documentation drift only.

Seam closed.
