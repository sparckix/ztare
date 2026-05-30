# GP-033 Multi-Project Synthesis Generalization Seam

> **Seam metadata** · `seam_id:` GP-033 · `track:` apparatus · `status:` `implemented` (kernel track) - opened 2026-04-11 16:19:55, s · `last_updated:` 2026-05-08


**Status:** closed *(inferred 2026-05-08 — needs operator review)*

## Status

`implemented` (kernel track) — opened 2026-04-11 16:19:55, spec'd 2026-04-11 16:19:55, implemented 2026-04-11 16:19:55, hardened 2026-04-11 17:20:31, live-verified 2026-04-11 17:27:05.

## Problem Snapshot

`src/ztare/synthesis/synthesize.py` already had one multi-project lane, but it was hardcoded to `field_manual`. That meant the synthesis layer could aggregate several projects only for the failure-family distribution artifact, while report-grade renderers like `research_note` and `decision_brief` remained single-project only.

That was now the wrong boundary. The renderer and QA layers were already capable of consuming an `aggregated_corpus`; the bottleneck was the router and the lack of a generic combined ledger/brief path. The immediate use case is the EU portfolio: combine `eu_union_load_bearing_pillars` with `eu_union_failure_probability_2035` into one report without inventing an EU-only workflow.

## Chosen Slice

Generalize multi-project synthesis for explicit renderer types by adding:

1. a generic multi-project aggregation path
2. a combined multi-project ledger extraction step
3. fully scoped outputs so anchor-project single-project artifacts are never clobbered

Keep the specialized `field_manual` path intact, because it has its own provenance discipline and distribution output contract.

## Why This Slice

- It solves the real operator problem without forcing merged synthetic projects.
- It reuses the existing synthesis architecture instead of creating a parallel report system.
- It keeps the first implementation bounded: explicit `--renderer-type`, no `--pack` support, no new UI layer.

## Implementation Note

Shipped in:

- `src/ztare/synthesis/synthesize.py`
- `config/prompts/extract_ledger_multi_project.md`
- `src/ztare/synthesis/synthesize_multi_project_fixture_regression.py`

## Turn 1 — Codex (2026-04-11 16:19:55) — Generalize the router, not the product taxonomy

The right fix is not an EU-specific synthesis hack and not a new renderer family. The existing renderer layer is already generic enough. The actual missing primitive was a multi-project router plus a combined ledger path.

So the first slice should do exactly three things:

1. allow `--projects ... --renderer-type <non-field_manual>` in `synthesize.py`
2. create a generic aggregated corpus and a combined ledger for renderers like `research_note` and `decision_brief`
3. scope all multi-project outputs so the first project acts only as an anchor directory, not as a clobbered source of truth

Anything beyond that — auto-packs, UI work, merged project objects, or a public workflow claim that all renderers are equally good in multi-project mode — is second-slice work.

## Turn 2 — Codex (2026-04-11 17:20:31) — Add quantitative carry-forward and fix stale-history reuse

The first shipped slice proved the router generalization was real, but the first live EU report exposed a second seam: generic multi-project synthesis could now combine projects, yet it still had no typed way to preserve bounded working priors or forecast-status distinctions. The result was a report that correctly refused to invent a fully earned top-line percentage, but incorrectly dropped the only decision-relevant ranges the underlying project had already bounded.

That is not EU-specific overfitting. It is a synthesis-contract bug. The repair belongs at the generic layer:

1. add typed `forecast_status`, `quantitative_anchors`, and `working_priors` fields to the ledger prompts
2. teach the `research_note` renderer to surface a compact Working Ranges section when those fields exist
3. force multi-project report synthesis onto focused-history defaults unless the operator explicitly requests `full`
4. stop reusing stale history summaries or malformed cached ledgers when the prompt hash or history mode changes

This keeps the combined renderer honest in both directions: it still cannot overclaim an earned forecast, but it also cannot hide bounded working ranges merely because the top-line object remains unresolved.

## Turn 3 — Codex (2026-04-11 17:27:05) — Live verifier passed on the EU pair

The live EU combined render now verifies the second slice:

- final artifact written: `projects/eu_union_load_bearing_pillars/Report.multi_project.research_note.44feeb1afe.md`
- QA passed at `98`
- the written note preserves:
  - explicit `component_only` / not-fully-earned forecast language
  - bounded working ranges for the EU failure object
  - a distinct dependency chain section

That means the generic multi-project renderer is no longer just structurally generalized; it is now materially usable for mixed structural + bounded-forecast synthesis. The remaining limitations are quality-oriented rather than architectural.
