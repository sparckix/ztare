# GP-051 — Bounded Evidence-Collection Agent Spec

## Status

Active — 2026-04-13

## Scope

**Covers:**
- A new `make evidence-fetch PROJECT=...` Makefile target
- A new RAM-layer module `src/ztare/workspace/fetch_evidence.py`
- Stamped provenance headers appended to `evidence.txt` per fetch batch
- A machine-readable fetch manifest written per batch to `workspace/`
- Dedupe and flood-protection logic in the tool itself
- Error message improvements in `evidence-compile` for the missing-snapshot failure

**Does not cover:**
- Changes to the loop (`autoresearch_loop.py`) or the validator
- Changes to `workspace-update` or `evidence-compile` logic beyond error messaging
- Any automatic or scheduled fetch triggering
- The `workspace-update` step (still operator-run before `evidence-compile`)

## Decision

Build a command-based RAM-layer evidence-collection agent: `make evidence-fetch PROJECT=<p>`. It reads `workspace/latest_evidence_gaps.json`, filters by severity, fetches external sources, appends stamped provenance blocks to `evidence.txt`, and writes a machine-readable fetch manifest. It never triggers compile, never triggers workspace-update, never re-runs the loop. The operator reviews the appended evidence and decides whether to compile and re-run. This preserves the ALU/RAM boundary: the ALU (loop/validator) remains stateless; all writes to loop inputs (evidence.txt) are RAM-layer and operator-gated.

---

## Problem

After each loop run, `workspace/latest_evidence_gaps.json` contains evidence gaps with `fetch_query` and `severity` fields. Closing those gaps today requires four manual steps: read the gap file, decide which to fetch, fetch and append to `evidence.txt`, then compile. All four are error-prone:
- The Hormuz session produced `workspace_snapshot.json not found` (workspace-update never run), wrong Makefile target (`make compile` vs `make evidence-compile`), and a skipped compile step after appending evidence.
- There is no single tool that reads the gap file and fetches — the operator improvises each time.

## Why It Matters

Evidence quality is the primary lever on score improvement once the mutation loop has saturated a basin. The gap between "loop flags a missing evidence target" and "that evidence enters the next run" is currently four manual steps with no provenance trail. A bounded agent collapses this to one operator command plus one review step, while keeping the operator as the gate between mutator-generated gap claims and new evidence ingestion. Automating the gate would give the mutator indirect control over future evidence, opening a gaming surface the validator has no defense against.

## Constraints

- **ALU/RAM boundary is inviolable.** The fetch agent must never write to loop inputs automatically. Every write to `evidence.txt` is operator-initiated via the Makefile target.
- **No side effects on adjacent tools.** `evidence-fetch` must not silently run `workspace-update` or `evidence-compile`. Those remain separate operator steps.
- **Provenance is mandatory.** Every fetched block appended to `evidence.txt` must carry: timestamp, source URL, originating gap query, acceptance status (accepted / rejected / truncated). No provenance = no append.
- **Gap provenance is mandatory in the manifest.** The machine-readable manifest must record which evidence gap (by ID and severity) and which run (by run timestamp) generated each fetch, so postmortems can answer "did this fetch close the gap it was pulled for?"
- **Dedupe and flood-protection live in the tool.** The operator must not be responsible for remembering what was already fetched. The tool skips URLs already present in `evidence.txt` and near-duplicate fetches from the same gap wording, and enforces a hard `--max-fetches` ceiling.
- **Default filter is `degrading` only.** Fetching for `enriching` gaps is operator discretion and must be explicitly requested via `--severity enriching`. The default targets only the gaps that are currently blocking score improvement.

## Options

### Option A — Automatic post-loop fetch (cron / hook)

After each loop iteration, auto-fetch gaps with `severity == degrading`, append, re-trigger compile, queue next iteration.

**Verdict:** Rejected. Mutators generate the gap claims. Auto-fetch gives them indirect write access to future evidence — a gaming surface the validator has no gate for. Violates the ALU/RAM boundary in spirit even if the mechanism is technically separate.

### Option B — Command-based: `make evidence-fetch PROJECT=...` *(selected)*

Operator runs the command after inspecting `latest_evidence_gaps.json`. Tool fetches, appends with provenance, writes manifest. Operator reviews, then decides whether to compile and re-run.

**Verdict:** Correct. Operator remains the review gate. One command replaces four error-prone manual steps. ALU/RAM boundary stays clean.

### Option C — Interactive confirmation (terminal prompt per fetch)

Auto-fetch but pause before writing, prompting operator to confirm each source.

**Verdict:** Rejected. Incompatible with background loop runs and the supervisor pattern. Option B achieves the same gate without interactive overhead.

## Recommendation

Implement Option B. The spec title and module name should use "bounded evidence-collection agent" not "recursive evidence fetch" — "recursive" implies the loop feeds itself, which this design explicitly refuses.

## Implementation Sketch

### Module

`src/ztare/workspace/fetch_evidence.py`

```
fetch_evidence.py
├── load_evidence_gaps(project)           # reads workspace/latest_evidence_gaps.json
├── filter_by_severity(gaps, severity)    # default: "degrading"
├── dedupe(gaps, evidence_txt_path)       # skip URLs already present
├── fetch_sources(filtered_gaps, max_n)   # fetch up to --max-fetches sources
├── build_provenance_header(gap, result)  # timestamp + URL + query + status
├── append_to_evidence(project, blocks)   # write stamped blocks to evidence.txt
└── write_manifest(project, manifest)     # write fetch_manifest_<timestamp>.json
```

### Makefile target

```makefile
evidence-fetch:
    $(PYTHON) -m src.ztare.workspace.fetch_evidence \
        --project $(PROJECT) \
        --severity $(SEVERITY) \
        --max-fetches $(MAX_FETCHES)
```

Default variable values (in Makefile):
```makefile
SEVERITY ?= degrading
MAX_FETCHES ?= 3
```

### Evidence.txt provenance block format

```
## Evidence Batch — 2026-04-13T17:00:00Z
Source: https://example.com/article
Gap query: "IEA coordinated release historical precedents"
Gap ID: gap_2 | Severity: degrading | Run: 1776111512
Status: accepted

<fetched content here>

---
```

### Fetch manifest schema

`projects/<project>/workspace/evidence_fetch_manifest_<timestamp>.json`

```json
{
  "fetched_at": "<ISO timestamp>",
  "project": "<project>",
  "severity_filter": "degrading",
  "run_timestamp": "<timestamp of loop run that produced the gaps>",
  "fetches": [
    {
      "gap_id": "gap_2",
      "gap_severity": "degrading",
      "gap_query": "IEA coordinated release historical precedents",
      "source_url": "https://example.com/article",
      "status": "accepted",
      "evidence_block_start_line": 412
    }
  ],
  "skipped_duplicates": 1,
  "total_attempted": 3,
  "total_accepted": 2
}
```

### Adjacent tool error message repair

In `src/ztare/workspace/compile_evidence.py` (or wherever the snapshot is read), replace the current bare exception with:

```
WorkspaceSnapshot not found at {path}.
Run: make workspace-update PROJECT={project} [MODEL=gemini]
Then retry: make evidence-compile PROJECT={project} [MODEL=gemini]
```

Same repair in `workspace-update` if it has a similar bare failure on missing preconditions.

### Updated operator sequence

```
make loop ...                                        # run loop, get evidence gaps
# inspect workspace/latest_evidence_gaps.json
make evidence-fetch PROJECT=<p>                      # fetch degrading gaps, review summary
# review appended blocks in evidence.txt and manifest
make workspace-update PROJECT=<p> MODEL=gemini       # rebuild snapshot
make evidence-compile PROJECT=<p> MODEL=gemini       # compile into structured evidence
make loop ...                                        # re-run with richer evidence
```

## Open Questions

1. **Fetch backend.** Does `src/ztare/workspace/update_workspace.py` expose fetch primitives reusable here, or does `fetch_evidence.py` need its own web fetch layer? Check before implementing to avoid duplicating fetch logic.
2. **`evidence_gap_id` field.** Does `latest_evidence_gaps.json` already have stable gap IDs, or does the manifest need to use a positional index? Check the schema before writing the manifest serializer.
3. **Public/private placement of this spec.** Currently private (active + first-mover IP). Promote to public once the target ships and is closed, under the three-test visibility rule.
