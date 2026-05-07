# ZTARE Documentation Map

This is the canonical public map for the docs tree. The root `README.md` is
the entry point; this file explains which layer each document belongs to and
which documents are canonical versus supporting context.

## Layer Map

| Layer | Canonical docs | Maturity | Purpose |
|---|---|---:|---|
| ZTARE kernel | `docs/concepts/architecture.md`, `docs/guides/workflow.md`, `docs/guides/quickstart.md` | usable / evolving | Evidence snapshots, adversarial validation, deterministic gates, synthesis, and the project workflow. |
| Cognitive gym / recursive primitives | `docs/concepts/cognitive_gym.md`, `docs/concepts/epistemic_principles.md`, `docs/concepts/reflexive_engineering.md` | conceptual / partially mechanized | The constraint stack and epistemic operations that make the validator more than a chat loop. |
| Agentic engineering patterns | `docs/concepts/agentic_engineering_patterns.md`, `docs/guides/reflexive_audit_workflow.md` | public / reusable | General LLM-pipeline engineering patterns extracted from building ZTARE. |
| Agentic Organization Runtime | `org/README.md`, `docs/concepts/organizational_primitives.md`, `docs/guides/org_runtime_quickstart.md` | working prototype | Reusable organization primitives: persistent roles, mandates, tasks, gates, preferences, transition logs, damage signals, Orbit, Telegram, and role-bound execution. |
| ZTARE Research Co | `docs/concepts/ztare_research_company_architecture.md`, `research_areas/ZTARE_BOARD.md`, `research_areas/EXPERIMENT_TRACK_RECORD.md` | dogfood / active | The repo operating as its own research company: the org runtime instantiated around ZTARE research programs and closure discipline. |
| Operator surfaces | `docs/guides/operator_console.md`, `docs/guides/runtime_smoke_test.md`, `docs/guides/org_runtime_docker_deploy.md` | working / local-first | How a principal operates the repo locally or through daemonized roles. |
| Scientific case studies and papers | `papers/README.md`, `research_areas/EXPERIMENT_TRACK_RECORD.md`, `research_areas/ZTARE_BOARD.md` | mixed; status-labeled | Public manuscripts and durable experiment/findings records for gravity, neural scaling, Navier-Stokes, transformer-successor, and other bounded campaigns. |
| Formal proofs | `ztare_proofs/README.md`, `ztare_proofs/ZtareProofs.lean`, `ztare_proofs/ZtareProofs/` | experimental / public source | Lean proof sources and formalization experiments. Generated `.lake/` build state is not source. |
| Internal architecture maps | `docs/internal/` | internal / audit support | Detailed maps, audits, and implementation notes for maintainers. Not the first-read path. |
| Demos | `docs/demos/` | prototype UI artifacts | Static visual demos for governance and org-runtime concepts. |

## Recommended Paths

### New Reader

1. `README.md`
2. `docs/guides/quickstart.md`
3. `docs/guides/workflow.md`
4. `docs/concepts/architecture.md`

### Researcher Evaluating Claims

1. `README.md`
2. `papers/README.md`
3. `research_areas/EXPERIMENT_TRACK_RECORD.md`
4. Relevant project artifacts under `projects/` when intentionally public

### Builder Integrating The Kernel

1. `docs/concepts/architecture.md`
2. `docs/guides/workflow.md`
3. `docs/concepts/cognitive_gym.md`
4. `supervisor/USER_MANUAL.md`

### Builder Interested In Agentic Organization Runtime

1. `org/README.md`
2. `docs/concepts/organizational_primitives.md`
3. `docs/concepts/ztare_research_company_architecture.md`
4. `docs/guides/org_runtime_quickstart.md`

### Builder Interested In LLM Engineering Patterns

1. `docs/concepts/agentic_engineering_patterns.md`
2. `docs/concepts/reflexive_engineering.md`
3. `docs/guides/reflexive_audit_workflow.md`

## Status Vocabulary

- `usable`: expected to work for the documented path.
- `working prototype`: dogfooded locally, but not enterprise-hardened.
- `experimental`: useful research track, not a product promise.
- `conceptual`: explains the architecture or philosophy; not necessarily a runnable component.
- `internal`: maintainer-facing audit map or implementation note.
- `historical`: preserved for provenance; not canonical.

## Non-Goals For The Public Entry Point

- Do not read every file in `docs/internal/` first.
- Do not treat every project under `projects/` as a polished public case study.
- Do not infer that a high-scoring experiment is a scientific discovery unless
  the experiment ledger and paper layer say so.
- Do not treat private mirror paths as public source material.
