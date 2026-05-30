---
id: PATTERN-024
name: scientific_amnesia_precheck
version: 1
status: active
discovered: 2026-05-14
triggers:
  lexical: [been_here_before, repeat_branch, prior_arc, deja_vu, overlap, history_audit]
  structural:
    - branch_choice_before_querying_prior_evidence
    - operator_flags_prior_work_after_agent_has_selected_next_move
    - proof_frontier_terms_overlap_prior_EF_rows_or_code_declarations
    - new_artifact_claim_without_nearest_prior_basin_pointers
  problem_classes: [hard_mathematical_residual, apparatus_self_audit, too_complex_direct_attack]
spawn:
  mode: agentic_pre_tick   # the AGENT vs the graph; the script is one weak prior, not a gate
  primary: agent_reasoning_against_artifact_graph
  weak_signal_only:
    module: src.ztare.research_director.scientific_amnesia
    cli:
      generic: scripts/public/control/scientific_amnesia_precheck.py
      ns_defaults: scripts/public/projects/ns/ns_scientific_amnesia_precheck.py
    role: "lexical/embedding overlap = WEAK PRIOR. Never branch on the score. False != novel; True-generic != safe."
  output_schema: scientific_amnesia_report_v1
  storage_path: analytics/public/queries/scientific_amnesia/<substrate>_latest.json
chain_position: pre
related_patterns:
  - PATTERN-012  # prediction_ledger: forecasts should know if the branch repeats a prior basin
  - PATTERN-017  # frontier_state_ledger: persistent state is complemented by evidence-row search
  - PATTERN-023  # anti_rename_charter_gate: literature collision outside; amnesia precheck inside
  - ANTI-PATTERN-011  # scientific_amnesia
references:
  - src/ztare/research_director/scientific_amnesia.py
  - scripts/public/control/scientific_amnesia_precheck.py
  - scripts/public/projects/ns/ns_scientific_amnesia_precheck.py
  - research_areas/EXPERIMENT_TRACK_RECORD.md
  - analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md
falsifiable_test: |
  Once wired as a pre-tick step, over N>=20 branch queries with known historical
  overlap, the precheck must (a) surface >=1 exact prior E/F row or code
  declaration above threshold AND (b) cause the RD to record a non-no_close_prior
  classification (repeat/reuse/adjacent_but_distinct) in >=80% of those cases; AND
  the rate of basin re-visits later caught by the operator ("have we been here
  before?") must drop to <=0.5x the pre-wiring re-visit rate. If overlap-bearing
  queries yield a prior-pointer-backed reclassification in <80% of cases, or
  operator-caught re-visits do not halve, the precheck does not displace operator
  memory and demotes.
  metric_source: scientific_amnesia_report_v1 outputs in
  analytics/public/queries/scientific_amnesia/ joined to branch-note
  classifications; operator-caught re-visit events from catch_ledger.jsonl
  (amnesia-category catches).
last_reviewed: 2026-05-22
review_due: 2026-06-21
review_cadence: per_campaign_summary
---

# PATTERN-024 — Scientific Amnesia Precheck

## Problem

Research programs can revisit a basin under new vocabulary and fail to
notice until the operator asks, "have we been here before?" The failure
is not only human memory. It is an orchestration gap: the branch-choice
step did not query prior evidence rows, GP-233 decisions, and code
declarations before acting.

This matters most in high-dimensional proof work. Two branches can look
different at the wrapper level while sharing the same mathematical
frontier. Conversely, an old branch may be reusable but insufficient for
the current goal. The precheck forces that distinction before spending a
tick.

## Pattern (AGENTIC — general-purpose, substrate-agnostic)

The central mechanism is **the agent reasoning against the
artifact graph**, not a deterministic matcher. Six+ recurrences of
the same basin under drifting vocabulary proved the lexical script
cannot be the gate (it returned "generic overlap" every time; what
actually caught the amnesia was the agent grepping mechanism names
and reading file cores). These are the agentic prompt-rules:

1. **Score is a weak prior, never a gate.** Run the script (step 0)
   but do NOT branch on `overlap_detected`. `False` ≠ novel;
   `True`-generic ≠ safe. It is one input among the rules below.
2. **Search by MECHANISM, not vocabulary.** Vocabulary drifts; the
   underlying cited theorem/tool names are stable. Grep the codebase
   for the *mechanism* names the work uses (e.g. the specific
   theorems, operators, constructions), not the tick's framing
   words. Disjoint-vocabulary isomorphisms only surface this way.
3. **Consult the domain's structural anchor regardless of score.**
   If the domain has a known fixed residual structure (a canonical
   "closure ⟺ discharge one of {…}" node), name explicitly *which*
   canonical node/axiom the new work targets. A "new reduction"
   that cannot name its target is amnesia, not progress.
4. **Read the CORES of matched files, not filenames/grep lines.**
   The amnesia hides in theorem bodies and structures, not titles.
5. **Structural-equivalence test, not lexical.** Ask: "has this
   reduction / mechanism been done before under different words?"
   If the work "reduces X to a new open thing", that thing is
   probably an existing node re-vocabularied — find which BEFORE
   building.
6. **Formalize negatives.** A machine-checked impossibility
   (Lean non-implication) is the strongest anti-amnesia: it
   prevents re-litigation under all future vocabulary drift,
   because the negative is in the proof, not in prose.
7. **Output**: one of `repeat | reuse | adjacent_but_distinct |
   no_close_prior`, WITH the named target node + the mechanism-grep
   evidence + which file-cores were read. Not the score.

If `repeat`/`reuse`, change the branch plan before dispatch.

The deterministic script is offline token/Jaccard overlap — a
cheap prior that emits exact pointers. It is NOT a semantic oracle
and NOT the pattern; rules 2–6 are the pattern. (NS-specific
overfit, e.g. the FINAL_THEOREM 5-axiom structural anchor injected
unconditionally by the NS CLI, is a correct instance of rule 3 —
the *method* here is general; substrates supply their own anchor.)

## Residual-manifest primitive — the Residual Manifest (O(1), general)

The decisive generalization: a substrate that has a **fixed
canonical residual structure** (closure ⟺ discharge one of a small
named set) must maintain a **Residual Manifest** — a tiny curated
artifact listing (a) the canonical open nodes (≤~10, vocabulary-
independent, each tied to its cited mechanism), and (b) an **alias
table** recording every known re-vocabularization of each node.

This converts amnesia-check from O(corpus) fragile lexical search
into **O(1) canonical+alias matching**: a tick names which manifest
node it targets; if its framing hits an alias, it is that node, not
new. Discovering a new re-vocabularization = appending one alias
line (cheap, append-only — this *is* the maintenance the operator
called "force an md update"). The lexical script and the artifact
graph / E-F ledger are the *feed* that surfaces candidate aliases;
the manifest is the *decision surface*. Formalized negatives
against a node go in the manifest as re-litigation blockers.

General contract (any substrate):
- `<substrate>_residual_manifest.md` next to that substrate's
  closure source-of-truth; canonical nodes + alias table + status +
  formalized-negative pointers.
- Hard rule: every reduction tick names its target node from the
  manifest; "cannot name one" ⇒ new canonical node (rare, justify
  vs source-of-truth) OR amnesia (find the aliased node).
- The substrate CLI surfaces the manifest unconditionally for
  in-domain queries (rule 3 instance).

NS instance: `projects/ns_millennium_hunt/workspace/
ns_residual_manifest.md` (5 Clay-equivalent + C6 anti-twist +
Galerkin + Aubin–Lions; alias table = the ≥6 vocabulary drifts all
mapping to C5 Constantin–Fefferman ≡ perennial atom; formalized
negatives tick578-580). Source of truth: `ns_trackb_FINAL_THEOREM`.

## Output Schema

```json
{
  "generated_at": "ISO-8601",
  "substrate": "NS",
  "query": "pressure hessian tail window ...",
  "query_tokens": ["pressure", "riesz", "..."],
  "overlap_detected": true,
  "threshold": 0.22,
  "sources_scanned": {
    "experiment_rows": 1399,
    "gp233_rows": 65,
    "code_declarations": 6174
  },
  "top_hits": [
    {
      "source": "experiment_rows",
      "identifier": "F-GP225-...",
      "path": "research_areas/EXPERIMENT_TRACK_RECORD.md",
      "line": 1710,
      "score": 0.6417,
      "jaccard": 0.1234,
      "query_coverage": 0.6667,
      "matched_terms": ["pressure", "riesz", "..."],
      "text": "| F-GP225-... | ..."
    }
  ]
}
```

## NS First-Fire

On 2026-05-14, the operator asked whether the pressure/Riesz angular
branch had been visited before. The precheck on:

```text
pressure hessian tail window recovered Riesz angular carrier
identification same-scale sheath cancellation projected Riesz angular moment
```

returned `overlap_detected=true` and surfaced:

- `F-GP225-NS-RIESZ-ANGULAR-BOTTLENECK-IS-NOW-A-FIXED-KERNEL-FORMULA-20260514-319`
- `F-GP225-NS-PRESSURE-VISIBILITY-NOW-REDUCES-TO-ANGULAR-NONNULLNESS-20260513-314`
- `Route1PressureAngularCarrierIdentification.ofTailProjectionAndRieszAngular`
- GP-233 row for the angular-carrier split

This is the desired behavior. The precheck would have shown the overlap
without relying on chat memory. The resulting classification is `reuse`:
older recovered-Riesz/local-CZ pressure work is relevant, but it is not
enough to prove the current lower-bound pressure-visibility formula.

## Falsifiable Test

The pattern is working iff a branch query with known historical overlap
returns at least one exact prior E/F row or declaration above threshold
and the RD changes the branch note to one of `repeat`, `reuse`,
`adjacent_but_distinct`, or `no_close_prior`.

It is not working if the RD still relies on operator memory to identify
prior basins, or if the report contains only vague summaries without
artifact pointers.

## When to Deploy

- Before proof-frontier edits.
- Before a swarm or No-Go dispatch.
- Before GP-230 pricing when historical overlap changes the event class.
- Before claiming that a branch is new, newly compressed, or 10x faster.

## Limits

- Lexical overlap misses deep isomorphisms with disjoint vocabulary.
- High overlap can be a legitimate reuse, not a reason to stop.
- It complements literature search; it only searches local project
  artifacts unless the caller adds external sources.
