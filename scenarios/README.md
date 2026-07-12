# Scenarios — the composable use-case layer

A **Scenario** binds ZTARE's reasoning kernel to a use-case. It is a declarative bundle
(`scenarios/<name>.yaml`) that COMPOSES capabilities the kernel already has — it never re-implements them. The
filesystem is the registry: a new scenario is a dropped YAML, no core edit (the same pattern the repo already
uses for rubrics/roles/personas/primitives).

```
Scenario (scenarios/<name>.yaml)
  ├─ rubric          → rubrics/<rubric>.json      # WIRED: drives judge dimensions / persona / steering
  ├─ iters / dynamic / models                     # WIRED: run config
  ├─ gate_package    → Cage gates (opt-in)        # WIRED mechanism (honored where the Cage engages)
  ├─ deliverables    → governed output templates  # composed post-run through the provenance firewall
  ├─ evidence_sources / renderer / solvers        # typed capability plug-ins (scenarios.registry)
  ├─ rechecks        → re-executable backing checks
  └─ workbench_panels → contextual UI refs such as results:governed-rice
```

## Run it

```bash
# full engine-side bind (rubric + config + gate-package + capabilities):
python -m src.ztare.validator.autoresearch_loop --scenario product-manager --project <slug>

# via the CLI (resolves rubric/iters/dynamic at the boundary into the existing pipeline):
ztare autoresearch run --scenario product-manager --project <slug>
```

Precedence is **explicit CLI flag > scenario > code default** — a scenario is a convenience bundle, never a
straitjacket.

## Add a scenario (drop a file)

Copy `product-manager.yaml`, change the fields, done. The honored lever is almost always the **rubric** (it
drives the whole judge/mutator loop); most scenarios need nothing more.

### Declare a one-shot handoff

Use `deliverable_specs` when a scenario needs a new audience-facing document without a Python template:

```yaml
deliverables:
  - decision_memo
  - tradeoff_register
deliverable_specs:
  - name: tradeoff_register
    label: Trade-off register
    audience: Decision team
    description: Tensions and constraints that could change the call.
    presentation_brief: Keep open trade-offs visible; do not turn gaps into commitments.
    sections:
      - label: Decision
        kinds: [thesis, claim]
      - label: Trade-offs
        kinds: [tension, constraint, gap]
      - label: Revisit if
        kinds: [falsifier]
```

The recipe selects exact governed nodes; it cannot invent facts or relations. Sections include all matching
nodes by default. `presentation_brief` is renderer guidance only, never an evidence prompt. The baseline output
is a readable governed **source draft** with a collapsed provenance/argument drawer. **Shape for audience** lets
the report model choose only the title, headings, grouping, and reading order; every governed slot must appear
exactly once and its wording is inserted verbatim. The result is still an editorial draft until it passes the
fingerprint-bound trace and explicit promotion step. The Workbench Plugins editor can create and edit these
designs without writing CSS or Python.

## Add a capability plug-in (implement a contract)

Capabilities are the typed extension points a scenario names. Each satisfies a `Protocol` in
`src/ztare/scenarios/protocols.py` and self-registers with `@capability(kind, name)`:

```python
# src/ztare/scenarios/providers/confluence.py
from ztare.scenarios.protocols import EvidenceItem
from ztare.scenarios.registry import capability

@capability("evidence", "confluence")
class ConfluenceEvidenceProvider:
    name = "confluence"
    def list_evidence(self, project): ...      # -> list[EvidenceItem]
    def fetch(self, ref): ...                   # -> EvidenceItem | None
```

Drop the file into `plugins/scenarios/` or a directory named by
`ZTARE_SCENARIO_PLUGINS`, then run `ztare scenario plugins --reload` (or use
Reload on the Workbench Plugins screen). No provider-package edit is required.
A mis-shaped plug-in is recorded as a load issue and cannot resolve into a
scenario. Name collisions are rejected instead of depending on filesystem
order. Kinds today are `evidence`, `renderer`, `solver`, and `recheck`.

## Add a Workbench panel

`workbench_panels` references frontend code; it is not a request for the core
UI to invent a domain screen. A plugin author creates
`forensic-workbench/src/scenario-panels/<id>.jsx` with a default component and
this metadata:

```jsx
export const scenarioPanel = {
  id: "my-panel",
  host: "results",
  label: "My panel",
  description: "What this panel lets the operator do.",
  contract: {
    schema: "plugin_contribution_contract_v1",
    carriers: ["decision_state", "test_agenda"],
    actions: [
      { id: "refresh", mode: "read" },
      { id: "open-test", mode: "navigate" },
    ],
  },
};
```

Then declare `results:my-panel` in the scenario. The Workbench discovers panel
modules during the Vite build. It renders them inside the existing Results
home only while that scenario is selected; panels never create sidebar items.
Panels without the contribution contract, a governed carrier declaration, or typed
`read` / `write` / `navigate` actions fail discovery and appear in Plugins health.
Use `ModalPortal` and `useModalBehavior` from
`forensic-workbench/src/modal-behavior.js` for panel dialogs.

## Gate-packages: honored, not cosmetic

A `gate_package` appends deterministic Cage gates for fit/analysis scenarios. The kernel's Cage runs gates in
observe/authoritative mode; a gate produces an **observable** difference (engagement telemetry always; a raised
verdict under authoritative mode). Claim-governance scenarios (like `product-manager`) ship an **empty**
package on purpose — their lever is the rubric, so the package is never dead config. To make a gate drive a
run, promote it to a real Cage gate first, prove a with/without behavioral diff, *then* name it in a package —
`build_cage_factory` in `scenarios/resolver.py` is the opt-in seam.

## Verify

```bash
PYTHONPATH=src python -m ztare.scenarios.resolver   # deterministic behavioral selftest (no LLM)
```

Asserts the scenario changes the real, honored inputs the kernel consumes (rubric dimensions/persona,
cage-mode channel, gate-list) — a **non-empty** with/without diff, or it would be cosmetic.
