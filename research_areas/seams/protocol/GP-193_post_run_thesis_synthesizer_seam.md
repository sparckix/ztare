# GP-193 — Post-Run Thesis Synthesizer Seam

> **Seam metadata** · `seam_id:` GP-193 · `track:` protocol · `status:` Spec finalized; in-seam 4-perspective debate concluded with · `last_updated:` 2026-05-08


**Status:** Private. Opened 2026-05-02 evening. Triggered by operator
flag: "lower-score iters often yield insights that, when recombined
with adjacent iters, produce a thesis stronger than any single iter
— this should be mechanized per AGENTS.md guide instead of done by
hand at debrief time."

**Trigger event:** I (the agent) hand-synthesized iter-2 + iter-4 +
iter-5 of gp169 v3 into a combined thesis at debrief time. The
synthesis was substantive — none of the three iters individually
held the decisive protocol; the combination did. This pattern
recurred at gp168 v3 run-2 debrief (F1-F4 findings emerged from
recombining iters 1-6, not from the single highest-scored iter).
Both events were handled manually. AGENTS.md §mechanization-guide
requires that recurring valuable hand-procedures become deterministic
primitives.

**Companion seams:** GP-168 (org topology unfalsifiability),
GP-169 (consciousness decision protocol). Both seams' hero results
were cross-iter syntheses, not single-iter champions.

## Problem statement

The current `make synth` target produces a polished writeup
(`Report.md`) at REPORT stage from the run history. It is invoked
manually and frames the existing champion. It does NOT:

1. Identify recombineable iter clusters (clusters of iters whose
   decisive components are complementary, not competing).
2. Produce a candidate *combined thesis* as a substantive synthesis
   of those components.
3. Score the combined thesis against the rubric to test whether the
   synthesis beats the per-iter champion.
4. Run automatically post-loop without manual invocation.
5. Distinguish "the apparatus's score-ranked best" from "the
   substantive decisive best when components are recombined."

The gap is between Report-stage synthesis (what we have) and
Thesis-stage synthesis (what we need). Score-ranked champions miss
the multi-iter alpha when the score doesn't reward all components
of the eventual best thesis.

## Why this is hidden alpha

Three observations from gp168 v3 + gp169 v3:

1. **The score function is per-iter, not cross-iter.** A judge
   evaluates each thesis in isolation. It cannot reward a thesis
   for content present only in a different iter. So a decisive
   primitive that surfaces in iter-2 and a complementary primitive
   that surfaces in iter-4 each get partial credit; their *combination*
   gets no credit — there's no scoring slot for "this iter's content
   would beat its own score if combined with iter-N's content."

2. **Cross-iter recombination is exactly what an experienced reviewer
   does.** When I read all the gp169 iters at debrief time, I noted:
   iter-2 had calibration-veto; iter-4 had ERP; iter-5 had Trigger
   Table; combined they form a complete protocol that iter-2 alone
   only gestures at. A human reviewer routinely does this synthesis;
   the apparatus currently does not.

3. **The rubric's *anti-trivial* gates surface this gap.** Under
   v3.1 harshening, iter-2's calibration-veto WITHOUT explicit ERP
   wiring would score lower (Anti-Calibration-Closure-Drift gate
   hits). But iter-2's content paired with iter-4's ERP would pass
   that gate. The rubric is *correctly* penalizing the missing
   component; the synthesizer would *correctly* surface that the
   missing component IS present elsewhere in the run.

## In-seam debate (4 perspectives)

Following the GP-168 seam's Panel A / Panel B pattern, four
perspectives debated the spec internally before the implementation
section.

### Perspective 1 — Methodologist

The substantive question: when is two iters' content "complementary"
vs "competing"? A naive concatenation would produce nonsense. The
synthesizer needs a decisive-component extractor that can:

- Identify each iter's decisive primitives (name + role +
  contribution to which rubric dimension).
- Detect complementarity (component A from iter-N closes a
  weakness flagged in iter-M's judge critique, AND component A
  doesn't contradict iter-M's decisive primitives).
- Detect competition (two iters propose primitives that occupy
  the same rubric-dimension slot with conflicting content) — these
  cannot be merged; pick one or neither.

The simplest extractor: parse each iter's `weakest_point` field
(judge's flagged failure) AND each iter's `verified_axioms` field
(judge's accepted decisive claims). A complementary pair is
one where iter-M's verified_axiom names a primitive that iter-N's
weakest_point identifies as missing. This is a well-defined,
deterministic test.

**Methodologist verdict:** the spec is well-defined IF we restrict
the synthesis to verified-axiom-based combination. Going beyond
verified axioms to weakest_point-only-mentioned content risks
hallucinating the original mutator's intent. Start narrow, expand
later.

### Perspective 2 — Implementer

Operationally cheap path:

```
post-loop hook (autoresearch_loop:end_of_run):
  1. read all iter history files (already on disk in projects/<slug>/history/)
  2. extract per-iter (verified_axioms, weakest_points, score, dim_scores)
  3. find complementary pairs/triples by:
     - iter-M verified_axiom V_a closes iter-N weakest_point W_b
     - V_a does not contradict iter-N verified_axioms
  4. compose candidate combined thesis:
     - copy iter-M's V_a section into iter-N's structure
     - flag the synthesis explicitly ("this section synthesized
       from iter-M; iter-N's original was X, judge flagged Y;
       iter-M's V_a addresses Y")
  5. submit candidate to JUDGE (one extra LLM call per synthesis)
  6. if synthesis_score > max(iter_scores):
     - promote to champion, write to thesis.md with synthesis trail
  7. else:
     - record in workspace/post_run_synthesis_attempts.jsonl
     - keep original champion
```

Token cost: ~1 extra judge call per synthesis attempt. With a cap
of 3 synthesis attempts per run, ~$0.03-0.10 per run. Cheap.

**Implementer verdict:** this is a 200-line module + a hook in
autoresearch_loop. Implementable in one session. The risk: the
extractor's parsing of verified_axioms and weakest_points relies
on the judge's JSON schema being stable. If the schema drifts,
extraction fails silently. Mitigation: schema-version the extractor;
fail loud.

### Perspective 3 — Skeptic

Three risks:

1. **Hallucinated complementarity.** The extractor might detect
   "V_a closes W_b" when the decisive semantics differ. E.g.,
   iter-M's "calibration veto" and iter-N's "predicate transfer"
   both reference "calibration" but mean different things. A naive
   string-match extractor would call them complementary; the
   substantive content is conflicting. Mitigation: require the
   judge to score the synthesis as a separate evaluation — if the
   synthesis is incoherent, the judge will catch it.

2. **Synthesis gaming.** The mutator could learn to "leave
   complementary holes" in iter-N intending the synthesizer to
   patch them with iter-M content. This is Goodhart on the
   post-run synthesizer. Mitigation: synthesis is OPT-IN to
   promotion — it must beat the original champion by a margin
   (not just match), and the synthesis trail is auditable so
   gaming is observable.

3. **Cross-iter contamination of the per-iter score signal.** If
   iters know synthesis is downstream, they may write differently
   ("this iter's role is to provide ERP for the next iter's
   calibration veto"). This corrupts the per-iter rubric scores
   as a noise-free measurement of single-iter quality.
   Mitigation: synthesis happens ONLY at end-of-run (mutator
   doesn't see it); per-iter scores stay clean.

**Skeptic verdict:** the design is defensible IF (a) synthesis is
opt-in to promotion via a margin threshold, (b) synthesis trail is
auditable, (c) synthesis is not visible to mid-run mutator. All
three are achievable with the implementer's design.

### Perspective 4 — Integrator (paper 7 lens)

Paper 7's methodological story gets stronger with this primitive.
gp168 v3 run-2 produced 4 implementation findings via cross-iter
recombination; gp169 v3 produced the operational protocol via
cross-iter recombination. **The recombination IS the apparatus's
finding generation, not a debrief artifact.** Mechanizing it makes
the recombination an apparatus output, not an observer output.

This also closes a paper 7 honesty gap: today, when I read the
seams, I am the cross-iter integrator — and that's hidden human-in-
the-loop work that the apparatus's reported scores don't credit. A
post-run synthesizer makes that work apparatus-output, with
auditable provenance from per-iter content to combined thesis.

**Integrator verdict:** ship it. Mechanizing this would let paper
7 §11.7+ claim "ZTARE produces multi-component findings via post-
run cross-iter synthesis, not just per-iter scoring," which is a
methodological upgrade to the existing claim. The seam should
record the existing manual examples (gp168 v3 run-2 F1-F4, gp169
v3 protocol synthesis) as the empirical motivation.

### Synthesis of the four perspectives

All four agree the primitive is buildable, valuable, and low-risk
under the design constraints (verified-axiom-only extraction,
opt-in promotion via margin threshold, end-of-run-only firing,
auditable trail). The dimensions of disagreement:

- **Methodologist** wants narrow start (verified-axiom only);
  Implementer agrees; Skeptic confirms safety; Integrator
  confirms paper-grade value.
- No perspective opposed shipping. No perspective demanded
  pre-conditions beyond what the spec already satisfies.

**Decision:** ship as-specified, narrow scope (verified-axiom
based), opt-in promotion, end-of-run firing, audit trail.

## Spec (canonical)

### Module: `src/ztare/synthesis/post_run_thesis_synthesizer.py`

**Inputs:**
- `project_dir` — projects/<slug>/
- `rubric_data` — already parsed
- `judge_invoker` — callable that takes a candidate thesis and
  returns the judge's evaluation (existing test_thesis.py helper)

**Procedure:**

1. **Read iter history.** Walk `projects/<slug>/history/` for files
   matching `*_iter*_score_*_<slug>.md` and `_meta.json`. Build
   `iter_records: list[IterRecord]` with fields `(iter_index,
   score, verified_axioms, weakest_point, dim_scores,
   thesis_md_path)`.

2. **Detect complementary clusters.** For each pair `(iter_M,
   iter_N)`:
   - Check whether any verified_axiom V_a from iter_M closes the
     specific weakness named in iter_N's `weakest_point`.
   - "Closes" defined operationally: V_a's text contains a
     phrase that *negates the failure* W_b describes (e.g.,
     W_b = "no ERP wiring"; V_a = "I-type classification is
     never permanent + Trigger Table forces re-evaluation" → match).
   - Heuristic: V_a closes W_b if V_a contains ≥3 content words
     that overlap with the structural complement of W_b
     (negation + key noun phrases). Fallback: ask the judge
     directly (one extra LLM call per pair).
   - Symmetric: also check N→M.
   - Build `clusters: list[set[iter_index]]` of complementary
     iters; each cluster is a synthesis candidate.

3. **Compose candidate combined theses.** For each cluster:
   - Pick the *highest-scored iter as base*.
   - For each other iter in the cluster, identify the section of
     the base thesis whose weakness that other iter's V_a addresses.
   - Insert V_a's content into the base thesis with an explicit
     synthesis marker:
     ```
     <!-- SYNTHESIS: from iter-N (score X), addresses base's
          weakest_point "W". Original base section retained for
          audit at thesis_synthesis_audit.md. -->
     ```
   - Write candidate to `workspace/synthesis_candidate_<cluster>.md`.

4. **Score the candidate.** Run the existing judge invoker on each
   candidate. Record `(cluster, candidate_score, base_score,
   margin = candidate_score - base_score)`.

5. **Promote if margin > threshold.** Default threshold = 5 points.
   If `margin >= threshold`:
   - Copy candidate to `thesis.md` (with audit trail).
   - Append `_iter_synthesis_score_<S>_<slug>.md` to history/.
   - Update `<!-- best_iteration: ... -->` marker in thesis.md to
     point to the synthesis (e.g., `synthesis_iters_2_4_5`).
   - Log to `transitions.jsonl` as `event: post_run_synthesis_promoted`.

6. **Always log.** Whether promoted or not, append to
   `workspace/post_run_synthesis_attempts.jsonl` for audit:
   `{cluster, attempted, candidate_score, base_score, margin,
   promoted, reason}`.

### Hook into autoresearch_loop

Add at end of `main()`, after the final iter completes and after
`make synth`-style report-stage hooks:

```python
if rubric_data.get("enable_post_run_thesis_synthesis", True):
    from src.ztare.synthesis.post_run_thesis_synthesizer import (
        run_post_run_synthesis,
    )
    try:
        run_post_run_synthesis(
            project_dir=Path(PROJECT_DIR),
            rubric_data=rubric_data,
            judge_invoker=_invoke_judge_for_synthesis,
            margin_threshold=int(rubric_data.get(
                "post_run_synthesis_margin_threshold", 5)),
            max_synthesis_attempts=int(rubric_data.get(
                "post_run_synthesis_max_attempts", 3)),
        )
    except Exception as exc:
        log.warning("post-run synthesis failed (non-fatal): %s", exc)
```

### Rubric flags (opt-in by default for qualitative substrates)

```yaml
enable_post_run_thesis_synthesis: true   # default true
post_run_synthesis_margin_threshold: 5   # min point gain to promote
post_run_synthesis_max_attempts: 3       # cap LLM cost
```

For numerical substrates, default `enable_post_run_thesis_synthesis:
false` — verified_axioms in numerical substrates name PARAMETRIC_FORMs
that don't compose by concatenation; synthesis would corrupt them.

### Anti-regression test

Smoke test: replay the gp169 v3 run-2 history through the
synthesizer. Expected outcome: the synthesizer detects iter-2 +
iter-4 + iter-5 as a complementary cluster, composes the same
combined thesis I wrote by hand, scores it via the judge, and
promotes it (the combined thesis I authored should beat iter-2's
score 91 by at least 5 points if the synthesizer is working).

### Updating the arch map

Add to `docs/internal/architectural_maps/autoresearch_loop_architectural_map.md`:

```
post_run_synthesis (NEW, GP-193):
  fires: end of main() loop, after final iter complete
  reads: projects/<slug>/history/* and meta.json
  writes: thesis.md (if promoted), workspace/post_run_synthesis_attempts.jsonl
  cost: 1-3 extra judge calls per run
  opt-out: rubric.enable_post_run_thesis_synthesis=false
  reference: research_areas/private/seams/protocol/GP-193_*.md
```

## Provenance

- **Trigger:** operator flag 2026-05-02 evening, post-debrief on
  gp169 v3 run.
- **Empirical motivation (existing manual examples):**
  - gp168 v3 run-2 (2026-05-02 17:48-17:52): F1-F4 findings emerged
    from cross-iter recombination of 6 iters, not from any single
    iter. Documented at GP-168 seam §"v3 RUN-2 RESULTS".
  - gp169 v3 (2026-05-02 18:17-18:21): operational decision
    protocol emerged from synthesis of iter-2 + iter-4 + iter-5,
    not from any single iter. Documented at GP-169 seam.
  - In both cases, the synthesis was performed by the agent at
    debrief time, not by the apparatus. The seams now record the
    synthesis but the apparatus produced no synthesis-output.
- **AGENTS.md mechanization rule reference:** "if I'm doing this
  by hand and it adds clear value, build it as a deterministic
  primitive." This seam is the rule-application record.

## Status

Spec finalized; in-seam 4-perspective debate concluded with
consensus to ship. Implementation pending. Arch map update pending.

## Perspective 5 — Architecture-Coherence (added 2026-05-02 evening, post-implementation flag)

**Trigger:** operator caught a real overlap risk after I shipped
v1: "synthesize.py already does some of this for report generation
purposes. Risk of duplicating logic. Maybe combine, maybe pre-step,
maybe refactor — important to debate."

**The overlap audit:**

| Concern | `synthesize.py` (existing) | `post_run_thesis_synthesizer.py` (new) |
|---|---|---|
| Reads history/ | yes (LLM-driven summarization step) | yes (deterministic record extraction) |
| Builds per-iter records | implicit, in `summarize_history` LLM call | explicit `IterRecord` dataclass |
| Cross-iter analysis | LLM does it inside `summarize_history` | deterministic complementary-pair detection |
| Updates thesis.md | NO | yes (when synthesis beats champion by margin) |
| Produces Report.md | yes (after multi-step LLM pipeline) | NO |
| Cost | ~5-10 LLM calls per `make synth` invocation | 1-3 judge calls per post-run firing |
| Stability | "synthesize sometimes fucks things up" — operator quote | new; not yet stress-tested |
| Invocation | manual `make synth` | automatic at end-of-loop |

**Three architecture options:**

**Option A — Independent modules with shared primitive.**
Extract `read_iter_records()` + `IterRecord` dataclass + complementary-
pair detection into a new `src/ztare/synthesis/iter_extraction.py`.
Both `post_run_thesis_synthesizer.py` and `synthesize.py` consume it.
synthesize.py's `summarize_history` step becomes "summarize a list of
already-extracted IterRecords" rather than "read history files +
summarize." Removes duplication; preserves separation.

**Option B — post_run as a pre-step inside synthesize.py.**
`make synth` first invokes post_run_thesis_synthesizer (if enabled
and no synthesis artifact exists), then runs the existing report-
generation pipeline against the (possibly newly-promoted) thesis.
Bundles the two flows; doesn't touch module boundaries.

**Option C — Full merge.** Collapse both into one module with
multiple entry points. High refactor cost; loses the clean
separation between "improve the thesis" (post_run) and "explain
the thesis" (synthesize).

**Architecture-Coherence verdict:** **Option A + B together.**

Rationale:
- **A** addresses the immediate duplication risk (reading history
  is now done in two places; if either drifts the other will need
  patching). Extracting `iter_extraction.py` makes the history-
  read contract single-source.
- **B** addresses the user's "10x potential" intuition. Today
  `make synth` reads raw history and asks an LLM to summarize.
  After A+B, `make synth` invokes post_run first, which deterministically
  surfaces complementary clusters AND verified-axiom matrices the
  LLM-summarization step can consume as STRUCTURE rather than raw
  content. This both reduces hallucination risk in synthesize.py
  ("synthesize sometimes fucks things up") and improves the report
  by giving the LLM a deterministic skeleton.
- **Option C** is overkill — the modules genuinely have different
  output objectives (Report.md vs thesis.md mutation).

**Skeptic check on A+B:** does this introduce circular dependency?
No: `iter_extraction.py` has no dependencies on either module;
both consume it. synthesize.py optionally calls post_run (one-way
dependency).

**Implementer check on A+B:** synthesize.py's `summarize_history`
step is LLM-driven and currently somewhat unstable. Refactoring it
to consume `IterRecord` lists is non-trivial — needs careful
testing because the existing prompt expects raw text. Decision:
ship A now (clean extraction); ship B as a follow-up (touch
synthesize.py only after the extraction has been stable for a
week).

**Net 5-perspective consensus:** ship Option A immediately
(extract `iter_extraction.py`, refactor `post_run_thesis_synthesizer`
to use it, leave synthesize.py untouched in v1 of GP-193). Ship
Option B as GP-193b after one week of stable post_run telemetry.

## Open questions (to revisit after first deployment)

1. Should the synthesizer try to compose ≥3-iter clusters (e.g.,
   iter-2 + iter-4 + iter-5 for gp169) or only 2-iter pairs in v1?
   Current spec allows clusters of any size detected by transitive
   complementarity; simpler 2-iter-only would be safer.
2. Should the synthesis attempt fall back to LLM-judge-arbitrated
   complementarity when the deterministic heuristic returns no
   clusters? Adds cost but may surface non-obvious recombinations.
3. Should this primitive ship with the gp168 / gp169 runs replayed
   as fixture-regression tests, so future apparatus changes can't
   break the synthesis pattern?
