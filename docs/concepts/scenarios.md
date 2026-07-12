---
description: "Scenarios bind ZTARE's governance kernel to a domain through typed evidence, renderer, and solver plug-ins."
---

# Scenarios

> Up: [Documentation map](../README.md)

## What changes

ZTARE's core is a **claim hardener**: it takes a bounded claim, pressure-tests it against bounded
evidence under deterministic gates and adversarial review, and returns an auditable verdict. That core is
domain-neutral and unchanged.

What Scenarios add is a **thin composition layer** so the same kernel can be pointed at a *use-case* — product
decisions, research, finance, security review — without forking core code. Before: one loop, configured by a
sprawl of flags and env vars, producing a score. After: a named, declarative **Scenario** binds {which rubric
drives the judge, run config, which capability plug-ins to use, which artifacts to emit} — and the kernel
produces domain **artifacts** with the governance baked in, not just a number.

The line this crosses: from "a rigorous claim checker beside your tools" to "a governed studio that produces
the deliverable *with* the rigor inside it." A PM scenario doesn't just score a PRD assumption — it can emit a
spec, a decision memo, a risk register where every load-bearing claim is bounded, evidence-linked, and carries
a falsifier. The claim-hardener is still the engine; the Scenario is what makes its output a thing you ship.

## The unit

A Scenario is a file: `scenarios/<name>.yaml`. The filesystem is the registry — a new scenario is a dropped
file, no core edit (the same pattern already used for rubrics, roles, personas, primitives).

```
Scenario (scenarios/<name>.yaml)
  ├─ rubric        → rubrics/<rubric>.json     WIRED, honored (drives judge dimensions / persona / steering)
  ├─ iters/dynamic/models                      WIRED, honored (run config)
  ├─ gate_package  → Cage gates (opt-in)        WIRED mechanism (honored where the Cage engages)
  ├─ deliverable_specs                          safe one-shot document recipes (governed node selections)
  ├─ evidence / renderer / solvers             TYPED capability plug-ins (scenarios.registry)
  └─ workbench_panels                            contextual UI refs in existing host slots
```

Binding happens once, engine-side (`ztare.scenarios.resolver.apply_scenario_to_args`); the CLI passes
`--scenario` as an opaque string, so scenario config never round-trips through the flag/env sprawl it exists to
reduce. Precedence is **explicit CLI flag > scenario > code default** — a scenario is a convenience bundle,
never a straitjacket.

## Typed capability plug-ins

Capabilities are the extension points a scenario names. Each satisfies a structural `Protocol`
(`ztare/scenarios/protocols.py`) and self-registers with `@capability(kind, name)`
(`ztare/scenarios/registry.py`). Structural typing, not ABCs: a plug-in needs only the right methods — no
base-class import, no inheritance coupling — and a mis-shaped plug-in fails **loud** at registration, never
deep in a run.

- **EvidenceProvider** — where a scenario's evidence comes from (`local_files` today; Confluence / Jira /
  telemetry are drop-in next).
- **Renderer** — how a verdict / artifact is emitted (`markdown` and **`decision_brief`** today — the latter
  lays out the PM flow *decision → what it hinges on → evidence → falsifiers* with the apparatus in a collapsed
  audit drawer, consuming the governed DATA the kernel emits; workbench / obsidian / pdf next).
- **Solver** — a deeper reasoning engine a scenario can call (leanmill / fit adapt to this contract; an
  abduction / ARC engine can plug in later without touching the kernel).

**What is consumed end-to-end today (honest status).** The **rubric** drives the judge across the whole loop
(the main lever) and the **Renderer** emits the post-run artifacts. Beyond those:

- **`evidence_sources` — consumed.** The loop's evidence intake appends a scenario's *non-default*
  EvidenceProviders (e.g. `structured_files`, which reads a project's `evidence/` dir; `local_files` is the
  disk read). Guarded — a provider failure never breaks the run's disk-evidence path.
- **`gate_package` — consumed (live seam).** A scenario's gate-package wraps the Cage factory
  (`build_cage_factory`), appending its registered gates. The v1 scenario-gate registry ships empty by design
  (claim scenarios use the rubric lever), so this changes nothing until a gate is registered — but the seam is
  live and tested (a fake gate is appended; an unknown one is skipped, never fatal).
- **`solvers` — resolved, not auto-invoked (by design).** The claim-hardening loop has no universal "solve"
  step, so a Solver is not something the base loop dispatches; it is resolved and reachable
  (`resolve_capabilities`) for a scenario- or goal-type-specific handler to call (LeanMill runs via its own
  path, not this seam).

So "drop a YAML" wires the rubric + renderer + deliverables + evidence + gates end-to-end today; a Solver is a
capability a scenario's own dispatch uses. This is a genuine seam, not dead config.

## Governed artifacts — the provenance firewall

The point of a Scenario is not to score a claim — it is to **produce the deliverable** (a decision-memo,
spec, risk-register) *with the rigor inside it*. The danger: if a scenario "writes the spec" post-run with
free generation, it smuggles in claims the loop never tested — ungoverned assertions laundered through a
governed pipeline. So artifact production is bounded by a **provenance firewall**
(`src/ztare/scenarios/artifacts.py`) with a machine-checkable invariant:

- **Total provenance, onto the hardened state.** Every element of an artifact must trace to an element of the
  run's **governed final state** — the *hardened* claim (the final working thesis, not the pre-test charter
  claim), the bound evidence, the falsifiers, the adversarial findings. The map is **total** (no orphan
  element), and deliberately **not injective** — a spec section and a risk row may both cite one hardened
  claim; reuse is what deliverables are. The one forbidden thing is an element with no governed pre-image.
- **Verbatim, not "semantically equivalent."** A slot's text must be normalized-equal (whitespace only) to the
  governed text. Accepting paraphrase would let a dropped scope-qualifier ("under bounded evidence E" → flat)
  silently strengthen a claim through a passing gate — the flaky-judge failure the faithfulness firewall
  already fights. Enforcement is syntactic; no LLM in the gate.
- **Set-completeness (anti-cherry-pick).** Every declared deliverable is emitted or emitted as a **stub with a
  reason**. You cannot silently drop the deliverable that didn't survive. (The set is ideally pre-registered
  in the charter — immutable — so the *what* can't be edited after seeing outcomes; the Scenario manifest holds
  the *format*.)

v1 is **template-composition**: deliverable slots are typed refs into the governed state, filled verbatim.
For a one-shot document, `deliverable_specs` supplies labelled sections, audience metadata, and optional
renderer guidance; all matching governed nodes are included by default. A spec is not a prompt or evidence
source. The baseline renderer emits a governed source draft with a collapsed provenance/argument drawer, and
code-owned templates may enrich the composition while preserving the spec's presentation metadata.
`decision_memo` is the one kernel default (domain-neutral kind-labels). Domain templates are plugin assets that
self-register from a scenario's `providers/` module and vanish with it (the rot test) — the product-domain set
(`providers/pm_templates.py`) ships **product_spec, risk_register, prd, launch_readiness, adr, rice**. Each
composes slots purely from governed elements under a PM-native label; the firewall gates all of them the same
way regardless of who registered them. Two carry their own weight: **adr** is the only template that pulls the
governed `rejected` node kind into an explicit "alternatives considered & rejected" section, and **rice**
refuses to emit numbers — it composes the governed *inputs* to a RICE score (evidence grounds R/I, findings
bound C, the kill-criterion bounds E-risk) and leaves the score to the PM, because a fabricated number wearing
the stamp is the exact laundering the firewall exists to stop. Free-prose generation would need a
claim-extraction judge and is deliberately a later layer. Outputs land in `workspace/<run>/scenarios/<name>/`
(outputs, not the charter), each artifact stamped with its `← governed:<id>` provenance and accompanied by a
`provenance_report.md` — which also names the **decision hinge**: `assemble_verdict` ranks claims by
*counterfactual decision sensitivity* (toggle each assumption holds-vs-fails, rank by how far the verdict
swings — NOT graph degree), so the report says not just SUPPORTED/BLOCKED but *which assumption the decision
turns on*, its ties, and a coverage score. The full ranked hinges are data in `governed_artifact.json`;
presentation (a decision brief, an audit drawer) is the renderer's job, dynamic per scenario — not a kernel
template. This is the line between a governed claim-checker and a governed studio for any substrate: **the
loop hardens the claim; the firewall guarantees the deliverable says nothing the loop didn't govern.**

The matching **rubric library** (each a dropped JSON, no kernel change) covers the product domain beyond the
first `product_manager` rubric: `launch_readiness`, `prioritization`, `strategy_review` — a scenario names one
and it drives the whole judge loop.

## The deliverable-generation boundary

The governed graph becomes a deliverable by **template-composition**, with the LLM demoted to *chooser*
(structure, ordering, whitelisted connectives) — never *author*. Content stays verbatim governed slots;
connectives stay edge-licensed. Two supporting pieces (`scenarios/artifacts.py`):

- **Interim artifact** (`serialize_governed`) — a free serialization of the governed graph + provenance you can
  hand downstream. It is the *export format*, not the trust boundary.
- **Re-ingest as the governed-UPDATE path** (`reingest_gate` → `open_reingest_session` / `promote_reingest`) —
  if a downstream AI polishes the prose, feed it back: every claim sentence must be **verbatim a governed
  sentence** or it is flagged **UNGOVERNED**, fail-closed, no LLM judge. The gate is deliberately **strict**
  (this is output, the stamp): match is normalized *equality*, never substring-containment — so dropping a
  scope qualifier is caught — and markdown markers are stripped so a claim laundered into a **bullet / quote /
  table cell is gated, not skipped**. Promotion is an explicit *session*: it binds the base governed-state hash,
  shows a diff (traced / dropped-claim / ungoverned), and promotes the rendering to canonical only if nothing is
  ungoverned **and** the base hasn't shifted — writing a `.reingest.json` audit record. This kills the failure
  mode that dooms naive "let my AI write it": *silent claim mutation with credential transfer* — the polish AI
  upgrades "challenges" to "refutes," and the doc ships wearing ZTARE's stamp. (Re-ingest promotes a *rendering*;
  it never mutates the governed graph — edges are only produced inside the loop under proposer≠grader.)

## The annotated round-trip (the inverse firewall)

The forward firewall compiles a governed graph *into* a deliverable. The **annotated round-trip** runs the
other way: a document (a PRD, a proposal) comes *in*, and the same document comes back with every sentence
tagged by its claim **lifecycle stage** (`artifacts.annotate`). annotate is **read-only ANALYSIS** — the
opposite valence from `reingest`, which is the *update gate*; they share one sentence-splitter (`_prose_sentences`)
but not the match strictness (annotate is permissive `align`; reingest is strict). The four statuses are the
states of a **finite state machine** (`CLAIM_LIFECYCLE`, built on `common.control_state_machine`) — one
canonical transition table with invariants, not scattered branches. A status is read off the governed edges:

| Status | Meaning |
|---|---|
| **BACKED** | aligns to a governed element carrying a SUPPORTS edge |
| **CONTRADICTED** | aligns to an element carrying a FALSIFIES/CONTRADICTS in-edge |
| **UNTESTED** | a load-bearing assumption — surfaced, in the queue, no evidence yet |
| **INERT** | nothing surfaced here (never rendered as "ungoverned rhetoric" — the surfacer has false negatives, so an unmatched sentence is *unknown*, not *bad*) |

The point a naive "let my AI critique the PRD" misses: **a document is input, not a deliverable, so it never
"fails."** The headline is a count, not a pass/fail — *"14 load-bearing assumptions, 0 tested, 1 contradicts
your existing map."* That is triage, not red ink. The statuses are stages of a claim, not verdicts on a page:
the *same* `annotate` call against a maturing governed state upgrades UNTESTED → BACKED as evidence
lands — no pre-run/post-run mode switch (an empty graph simply cannot emit BACKED yet). Afforded as
`ztare scenario annotate <doc> --project X` and the workbench "Annotate a doc" view (`POST /api/scenario-annotate`).

## Compounders (kernel mechanisms; the LLM proposes, the kernel gates)

Domain-neutral kernel capabilities that compound; domain bindings are plugins:

- **Multi-claim verdict** (`artifacts.assemble_verdict`) — a deterministic verdict over the governed argument
  graph: REFUTED (a governed FALSIFIES/CONTRADICTS edge), BLOCKED (an unresolved tension/gap — the governed
  answer, not a forced verdict), else SUPPORTED. Cites the edges that produced it, and names the **load-bearing
  hinge** by *counterfactual decision sensitivity* — toggle each assumption holds-vs-fails, rank by how far
  the verdict swings (not graph degree) — with ties and a coverage score.
- **Assumption-surfacing** (`surfacing.surface_assumptions`) — a doc → bounded claims to test, each anchored to
  a **verbatim source span**; the LLM extractor is an injected proposer, the kernel gates the anchor and drops
  hallucinated ones (fail-closed). Primary intake composes the evidence compiler's already-extracted claims
  (`claims_from_packet`) and only adds the span gate — it does not re-run extraction.
- **Annotated round-trip** (`artifacts.annotate`) — the inverse firewall above; the PM-facing surface.
- **Evidence-binding** (`evidence_binding.bind_evidence`) — a cited excerpt bound to a source by content hash +
  timestamp, refused unless the excerpt is verbatim-in-source. Connectors (Jira/Confluence/telemetry) are
  plugins behind `EvidenceProvider`; staleness re-verification and ACLs are deferred.

## Afford it

```bash
ztare scenario list                       # installed scenarios
ztare scenario show <name>                # resolved rubric / run-config / capability plug-ins
ztare scenario validate <name>            # typecheck the manifest (fails loud)
ztare scenario new <name>                 # scaffold scenarios/<name>.yaml (self-validating)
ztare scenario run <name> --project X     # → autoresearch run --scenario <name>
ztare scenario surface <doc> --project X  # doc → its load-bearing assumptions (gated to verbatim spans)
ztare scenario annotate <doc> --project X # doc → the same doc back, each sentence lifecycle-tagged
ztare scenario reingest <polished> --project X [--promote <out.md>]  # diff + promote-if-fully-governed
ztare scenario brief --project X [--out <file.md>]  # the PM decision brief (hinges + audit drawer) from the map
```

In the Project Workbench: `GET /api/scenarios` serves the picker; `POST /api/scenario-surface`,
`/api/scenario-annotate`, `/api/scenario-reingest` back the "Annotate a doc" view. All three annotate/reingest
paths are deterministic (no model call); `surface`/`annotate` use an LLM only to *propose* spans, which the
kernel then gates.

## Add your own — dynamic install (CLI or the workbench UI)

Three plugin kinds, three install paths — none require editing core code, and `ztare scenario plugins` (or the
workbench **Projects → Plugins** manager) lists everything installed:

- **A scenario** (data): `ztare scenario new <name>`, or the UI's *New scenario* form — written to
  `scenarios/<name>.yaml`, validated, and **live immediately** (the filesystem is the registry). The honored
  lever is almost always the **rubric**.
- **A rubric** (data): the UI's *New rubric* form (name + persona + weighted dimensions summing to 100) — written
  to `rubrics/<name>.json`, live immediately.
- **A capability** (code — an EvidenceProvider / Renderer / Solver): implement the Protocol, decorate with
  `@capability(kind, name)`, and either add it under `ztare/scenarios/providers/` (built-in) **or drop the `.py`
  into a plugin directory** (`$ZTARE_SCENARIO_PLUGINS`, os.pathsep-separated, or the repo `plugins/scenarios/`
  convention) and hit **Reload** (UI) / `ztare scenario plugins --reload` — no restart, no `providers/__init__.py`
  edit. A broken plugin is logged, never bricks discovery. (Data plugins install via the web form; code plugins
  drop-in + reload rather than accepting arbitrary code over HTTP.)

## Verify

```bash
PYTHONPATH=src python -m ztare.scenarios.resolver    # scenario binding changes real honored inputs (no LLM)
PYTHONPATH=src python -m ztare.scenarios.artifacts   # firewall + verdict + annotate round-trip (no LLM)
PYTHONPATH=src python -m ztare.scenarios.surfacing   # compose-compiler-claims + span gate (no LLM)
```

The selftest asserts a scenario changes the **real, honored** inputs the kernel consumes (rubric
dimensions/persona, cage-mode channel, gate-list, resolved plug-ins) — a non-empty with/without diff, or it
would be cosmetic.
