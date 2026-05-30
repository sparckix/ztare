# Claude review — LeanMill C-supply for benchmark-vs-APN comparison

**Date:** 2026-05-25
**Scope:** Fresh-eyes audit of the LeanMill 4-arm evaluation harness, the
C-discriminating slice generation pipeline (`leanmill_c_supply_batch.py` and
relatives), the seam (`research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md`),
the spec (`research_areas/specs/active/engine/lean/GP-225_leanmill_vnext_station_factory_spec.md`),
the kernel-resident code under `src/ztare/leanmill/`, and the live dashboard
state under `analytics/public/leanmill/dashboard_data/`.
Performed manually, no subagents.

**Reference for the external comparator:** *Advancing Mathematics Research with
AI-Driven Formal Proof Search* (Tsoukalos et al., Google DeepMind,
arXiv:2605.22763, "AlphaProof Nexus" / APN).

---

## 1. Headline verdict

The benchmark is not stuck on a bug. It is stuck on a **scope mismatch
between what the 4-arm harness measures and what APN measures**, layered on
top of a **C-supply pipeline whose live gate state is honest about being
short of rows**. The pipeline is correctly refusing to fire an
underpowered C-discriminating run. Fixing the comparison-to-APN question
is not the same task as unblocking the gate, and conflating the two has
been the time sink.

Concretely as of the latest `c_supply_batch_status` (`run_id:
c_supply_batch_1779636972`):

- selection status: `blocked_insufficient_c_discriminating_rows`
- eligible_count: **13**
- spec readiness gate requires **≥20** target-context-ready rows
- blockers by reason: `static_tool_positive: 51`, `static_result_unknown: 35`
- raw supply candidate hits: 1084 → unique rows: 15 (1069 duplicates)
- ex-post cleaner: 6325 raw checkpoint records → 99 clean (6226 duplicates)
- 4 rows have intra-arm exit conflicts (`raw_closure_candidate` AND
  `tested_no_positive_signal` for the same `public_tool_static` arm)

So the system is short by ~7 eligible rows on the spec's stated threshold,
not catastrophically short.

---

## 2. What APN measures vs what LeanMill measures — the apples-to-apples gap

This is the central issue and it is **not** something a bug-fix can fix.

| Dimension | APN (Tsoukalos 2026) | LeanMill 4-arm Evaluation Harness |
|---|---|---|
| Corpus | 353 formal Erdős problems (Formal Conjectures repo, ~Feb 2026 snapshot) + 492 autoformalized OEIS conjectures | Mathlib-derived rows curated via family-spec probes; family/row IDs internal to apparatus |
| Primary task | End-to-end formal proof generation (close all `sorry` placeholders) | Governed closure OR exact-gap candidate OR valid falsifier at equal budget |
| Primary metric | Solve rate (problems with complete `sorry`-free proofs) | Lift of governed-adaptive-residual-curriculum (C arm) over `public_tool_static` baseline on the C-discriminating slice |
| Baseline | Agent A: LLM + Lean compiler feedback loop, no evolution, no tools | `public_tool_static`: fixed-order tactic suggestion (`exact?`, `apply?`, `simp_all`, …); **no LLM** |
| Strongest arm | Agent D: LLM + AlphaProof tool + evolutionary search | `governed_adaptive_residual_curriculum`: residual-compiler memory + governance gate + adaptive execution on the same public tool substrate |
| Headline | 9/353 Erdős (2.5%) + 44/492 OEIS (8.9%) | Not yet fired (gate blocked) |
| Open artifact | `github.com/google-deepmind/alphaproof-nexus-results` (all Lean proofs published) | `analytics/public/leanmill/dashboard_data/` (internal artifacts) |

**Three independent mismatches:**

1. **Corpus.** APN tests on public open-conjecture corpora. LeanMill tests on
   apparatus-internal rows derived from mathlib. **Even if LeanMill C closes
   100% of its discriminating slice, that number is not comparable to APN's
   9/353 because the rows are different rows.**
2. **Baseline.** APN's Agent A is an LLM-plus-Lean loop. LeanMill's
   `public_tool_static` is automated tactic suggestion with NO LLM in the
   baseline. APN's Agent A is much stronger than LeanMill's "static baseline."
   This will make the LeanMill C-vs-baseline lift look much larger than the
   APN C-vs-baseline lift, but for the wrong reason.
3. **Metric.** APN measures absolute solve rate on a fixed problem set.
   LeanMill measures relative lift on a curated discriminating slice (rows
   the baseline can't solve are the only rows that count). Reporting the
   lift number directly against APN's solve rate would be **category-error
   apples-to-oranges**.

**This means:** the current C-discriminating pipeline, even if unblocked
today, does not produce a number that can be honestly placed next to APN's
9/353. To produce an APN-comparable number you would need to run the
governed-adaptive-residual-curriculum arm on **APN's actual corpus** (the
353 Erdős + 492 OEIS rows) with the **same metric** (sorry-free closure at
a comparable budget), not the discriminating slice.

This is the real reason the bug-fixing has felt fruitless. The pipeline is
optimized for a different question than the one being asked.

---

## 3. Why the C-discriminating gate is short-by-7 right now

Even setting aside the APN comparison, the internal gate is short. Reading
`leanmill_c_discriminating_slice_prep.py` line by line, the eligibility
rule is:

```
structural_eligible = (
    static["status"] == "failed_or_no_positive_signal"
    AND bool(matched_families)
    AND target_ok
)
probe_terminal_block = (
    structural_eligible
    AND not probe_verified_families
    AND not probe_pending_families
    AND probe_terminal_nonuseful_families
)
eligible = structural_eligible AND not probe_terminal_block
```

To be eligible, a row needs ALL of:

- Both static arms (`public_tool_static` + `governed_public_tool_static`)
  must have run and **both** must have returned strict no-signal
  (`tested_no_positive_signal`), not `raw_closure_candidate`, not
  `harness_*_failure`, not unknown.
- The row must have at least one family with BOTH a positive template AND
  a matched negative-control template.
- Family-spec probes must not have all terminated with no-useful exits.

The 96 corpus rows distribute as:
- 51 with `static_tool_positive` — public tools already solve them
- 35 with `static_result_unknown` — baseline arms have not completed
- 13 eligible (the current count)
- 4 with intra-arm static exit conflicts

**The 35 `static_result_unknown` rows are the cheapest fix.** These are rows
where either `public_tool_static` or `governed_public_tool_static` has not
run to completion. Running them through both static arms would resolve
them into either "positive" (which still blocks) or "failed_or_no_signal"
(which might unblock). If half of the 35 land on the failed side, you get
~17 more eligible rows, comfortably above the spec's ≥20 threshold.

**The 51 `static_tool_positive` rows are not fixable — they are
structurally not C-discriminating.** A row that the public-tool baseline
already closes cannot be used to demonstrate lift of the adaptive arm
over the baseline. Stop trying to recover them.

**The 4 intra-arm static exit conflicts** (where the same `public_tool_static`
arm produced both `raw_closure_candidate` AND `tested_no_positive_signal`
for the same row) are a non-determinism source. The current safety rule
("public-tool positive dominates conflicting static no-signal records for
C-slice safety") is the right rule, but the existence of the conflict
itself means the static arm is non-deterministic in some configuration —
probably timeout-vs-budget variance. Worth tracking but not blocking.

---

## 4. The 6226-of-6325 duplicate problem

This is a separate pathology and it is wasting compute and obscuring
signal.

From `c_supply_batch_expost_cleaner.md`:
- raw checkpoint records: 6325
- cleaned checkpoint records: 99
- duplicate checkpoint records: 6226 (98.4% duplication)
- raw corpus rows: 86460
- unique corpus rows: 101
- duplicate corpus rows: 86359 (99.9% duplication)

The cleaner is doing its job — it dedupes correctly. But the ratio means
**the upstream pipeline is producing the same probe over and over.**
Scanning the per-corpus reports in `c_supply_batch_status.md`, the
`cusp_function_qparam_periodic_planner` corpus alone appears in five
separate timestamped runs (`1779635367`, `1779633454`, `1779633264`,
`1779632978`, `1779630031`) and each one reports `new_rows=0 supply=0
counts={'static_positive': 6}`. That is the same 6 already-positive rows
being re-tested across five runs spanning ~1.5 hours.

The 2026-05-22 adversarial review identified this pattern as **the
recovery loop is re-firing identically**:

> "The recovery `work_id`s in `leanmill_observability.md` lines 32–36
> are recursively nested (`recovery_source_bind_auto_..._recovery_source_bind_auto_...`
> ×5) — a retry loop that re-fails identically each pass."

This is almost certainly the same underlying loop. A row whose static arm
returned `tested_no_positive_signal` or `static_positive` should not be
re-probed; the cached result is the canonical answer. The work_queue's
`source_query` contract should make a queued WorkItem idempotent on
`(family, row_id, arm)`. It is worth verifying that idempotency is
enforced at the queue insertion point (in `src/ztare/leanmill/work_queue.py`)
rather than only at the result-aggregation point (in the slice prep).

---

## 5. Code-level observations

### `src/ztare/leanmill/work_queue.py` (1177 lines)

- Module owns SQLite WorkItem queue + append-only JSONL event ledger.
  This is the right architectural shape for a durable bus.
- I did not read the full 1177 lines line-by-line; the spot checks are:
  - claims side-effect-free at import time per `__init__.py` invariant —
    verified by `__init__.py`'s `__all__ = ["common"]` (Phase A migration
    is incremental and `work_queue` is staged but the module itself does
    not run on import).
  - the `self-test` CLI subcommand exists per the README invariant.
- **Recommend reading the WorkItem-deduplication path before next run.**
  The 99% duplication ratio suggests this is where the leak is.

### `scripts/public/control/leanmill/c_discriminating_slice_prep.py`

- The gate logic is correct (see §3 above).
- The status reason set is well-named and the blocker
  accounting is honest. The doc-string explicitly says: "if the pool has
  no such rows, it reports the supply gap instead of letting an aggregate
  benchmark be misread as a Path-C test." This discipline is doing its
  job.
- `_record_rank` ranking has a safety rule: a row with even one
  public-tool positive cannot enter the slice. This is the right rule;
  do not relax it for the benchmark.

### `scripts/public/control/leanmill/c_supply_batch.py`

- The orchestrator wires miner → slice prep → optional freezer. The flow
  is sound.
- `DEFAULT_CORPUS_GLOBS` points at `queued_learning_work/probe_corpus_family_spec_*.json`.
  These corpora are the input. The 96-row corpus_count comes from union
  across these family-specific corpora.
- **The cheapest unblock:** add more family-specific corpora, or expand
  the rows-per-corpus, to widen the pool of candidates with
  `static_result_unknown`. Then run the static arms on them.

### `scripts/public/control/leanmill/c_supply_expost_cleaner.py`

- The cleaner is well-written. The static-conflict accounting (lines
  recording rows where the same arm produced different exits) is the
  right place to surface non-determinism.
- It does not delete raw artifacts. Good.

---

## 6. The bigger structural finding — what the 2026-05-22 review already said

The adversarial review at
`analytics/public/leanmill/dashboard_data/claude_adversarial_leanmill_review.md`
(2026-05-22) already said the headline:

> "the factory currently has no functioning path from a learning unit to
> a governed proof exit, and two of its three teeth signals are dead, not
> quiet."

Specifically:

- `ratified_closure_count: 0` in the live window
- `exact_gap_candidate_count: 0`
- `negative_control_unexpected_pass_count: 0`
- 8/8 probe exits = `tested_no_positive_signal`
- 19/19 source-families allocator-frozen (`do_not_spend_until_new_evidence`)
- Zero `validated_family` status anywhere (promotion requires ≥1 heldout-
  independence receipt; lifetime `heldout_receipt_events: 0`)
- 24× SLA breach on `source_qualification` (2903s vs 120s)

The C-supply blocker is downstream of this. The gate cannot select C-
discriminating rows because the family-spec probes that would qualify
them are either not producing useful exits or not running fast enough.

This is a **governance + schema** failure, per the May 22 review's
classification, "wearing a candidate-quality costume."

---

## 7. What I would do next, ranked

### A) If the goal is "unblock the gate so the harness can fire at all"

1. **Run the static arms on the 35 `static_result_unknown` rows.** Cheapest
   fix. Even a 50% failure rate yields ~17 newly-eligible rows.
2. **Fix the duplicate probe re-firing.** Verify that
   `src/ztare/leanmill/work_queue.py` deduplicates `(family, row_id, arm)`
   at insertion. If it does not, this is the leak.
3. **Expand the family-spec corpus** to introduce more candidate rows where
   the static baseline genuinely fails. Hard to do quickly — requires
   discovering new families. Probably the right move long-term.

### B) If the goal is "compare LeanMill against APN apples-to-apples"

This is a different and bigger undertaking.

1. **Mirror APN's corpus.** Ingest the 353 Erdős statements from the Formal
   Conjectures repo (snapshot ~Feb 2026 per APN's note) and the 492 OEIS
   conjectures from APN's open-source results repo at
   `github.com/google-deepmind/alphaproof-nexus-results`. These rows are
   the comparator.
2. **Build a metric that matches.** End-to-end Lean closure (`sorry`-free
   proof) at a fixed per-row budget, not "governed closure or exact-gap or
   falsifier at equal budget." The latter is a richer signal, but APN does
   not measure it.
3. **Honest baseline.** APN's Agent A includes the LLM. The closest
   LeanMill arm is `governed_adaptive_execution` (LLM + governance, no
   residual memory). Calling `public_tool_static` the "baseline" against
   APN would inflate the apparent lift dishonestly.
4. **Pre-register the comparison.** Before running, register the row set,
   the per-row budget, the metric, the closure verifier, and the
   contamination-control discipline (Mathlib commit hash, Lean version).
   This is exactly the apparatus's existing discipline applied to an
   external benchmark.
5. **Expect a smaller absolute number.** APN ran multiple agents at
   "hundreds of dollars per problem." A LeanMill single-pass result will
   look smaller. The honest framing is not "LeanMill beats APN" — it is
   "LeanMill on the same corpus, with this much budget, closed N." The
   structural contributions (governance, residual memory, 4-arm
   ablation) are then a separate methodology claim that does NOT depend
   on outperforming.

### C) If the goal is "publish something soon and the APN comparison can wait"

Honest path: publish the 4-arm methodology paper without an APN
comparison. The 4-arm harness IS a genuine methodology contribution
(governance + residual curriculum as a controlled ablation on top of
public tools). It does not need to beat APN to be publishable. The
honest non-claim "no head-to-head comparison against APN yet; the
corpora and metrics differ, an apples-to-apples run is owed" is the
right framing.

---

## 8. The one thing I am most confident about

**The pipeline is not lying to itself.** The `blocked_insufficient_c_discriminating_rows`
status, the explicit per-reason blocker accounting, the static-conflict
surfacing, and the ex-post cleaner reporting 98.4% duplication are all
the apparatus doing exactly what it is supposed to do: refuse to fire
an under-powered benchmark, name the specific blocker, and surface the
non-determinism instead of hiding it.

The bug-fixing frustration is not because the code is broken. It is
because **the question the pipeline was built to answer is not quite
the question being asked of it.** The 4-arm harness measures
governed-adaptive lift over a no-LLM tactic-suggestion baseline on a
mathlib-derived discriminating slice. APN measures end-to-end Lean
closure on public open-conjecture corpora with an LLM-plus-Lean
baseline. They are not the same benchmark.

The shortest path to a clean publishable result is **either**:

- decouple from the APN comparison and publish the methodology (the
  4-arm ablation IS publishable as is, once the gate clears the
  ≥20-row threshold), **or**
- accept that comparison-vs-APN is a second project: clone APN's
  corpus, match the metric, run the adaptive-residual-curriculum arm
  on it, and report the resulting number honestly.

Doing both at once through the current C-supply pipeline is the source
of the stuckness.

---

## 9. Honest non-claims of this review

- I did not read all 1177 lines of `work_queue.py`. The duplicate-probe
  diagnosis is based on the ex-post cleaner output (6226 dupes out of
  6325) and the 2026-05-22 adversarial review's note about recursively
  nested recovery work_ids; both consistent but neither line-by-line.
- I did not run anything. All findings come from reading code + JSON +
  markdown artifacts.
- I have not verified that the APN paper's `github.com/google-deepmind/alphaproof-nexus-results`
  repo actually contains the rows in a Lean-ingestible form. The WebFetch
  summary said it does; this should be checked before committing to the
  apples-to-apples comparison path.
- The estimate "running static arms on the 35 unknown rows would yield
  ~17 newly-eligible rows" assumes a 50% failure rate at the public-tool
  baseline. The actual rate on this corpus might be lower (it skews
  toward families where public tools work, since those are easier to
  build family-specs for); if so, this fix alone may not be enough.
- The May 22 adversarial review I am citing is well-aligned with what I
  see today, but the operating world has moved (this review is dated
  2026-05-25). It is possible some of those issues are partially
  remediated; I did not audit the delta.

---

*Review written manually, no subagents. Cross-references: GP-225 seam,
GP-225 vNext spec, `claude_adversarial_leanmill_review.md` (2026-05-22),
arXiv:2605.22763 (Tsoukalos et al., AlphaProof Nexus).*
