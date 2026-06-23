---
description: "How to fork ZTARE while keeping the reusable kernel, project policy, and private state separate."
---
# Forking ZTARE

> **Up:** [Documentation map](../README.md)

*Last updated: 2026-06-19.*

This guide is for someone who wants to fork ZTARE for their own research,
evaluation, or project-governance work. The practical goal is simple: keep the
reusable kernel intact, add your own project surfaces deliberately, and avoid
publishing local/private state by accident.

## 1. What You Are Forking

ZTARE is a public research and project-governance workbench. A fork contains
three kinds of material:

| Layer | Examples | Forking guidance |
|---|---|---|
| Reusable kernel | `src/ztare/`, `schemas/`, `scripts/public/`, public validators, CLI surfaces | Treat as shared infrastructure. Patch when you are improving the common machinery. |
| ZTARE policy and examples | `priority_roadmap.md`, `docs/`, `examples/`, public rubrics and selected projects | Use as reference material. Replace or adapt only when you mean to publish your own stance. |
| Local/private state | credentials, live workspaces, tenant overlays, unpublished project data | Keep out of git unless you intentionally promote a sanitized artifact. |

If you are only trying ZTARE, start with the public first-run path. If you are
building a durable fork, create a new branch and keep your own project policy
separate from kernel edits.

## 2. Verify a Fresh Checkout

From a new clone:

```bash
make hello
make first-run
ztare --help
ztare project --help
```

`make hello` is the shortest offline value demo. `make first-run` runs the
offline public review path, including the adversarial smoke checks that keep
the README, CLI help, and public examples aligned.

If you are preparing a pull request or a public push, run the publish gate used
by this repo:

```bash
make gates
```

## 3. Add Your First Project Surface

For external use, the safest entry point is project intake. It describes what
should be evaluated, which evidence exists, what is explicitly out of scope,
and the next falsifier. It prepares a project/data surface; it does not run the
research loop by itself. `ztare project packet` is the legacy spelling for the
same JSON boundary; prefer `ztare project intake` in new docs and scripts.

Create and validate an intake file:

```bash
ztare project intake create --path my_project_intake.json \
  --project my_project \
  --rubric my_project \
  --task "test one bounded claim" \
  --bounded-claim "bounded claim X holds on fixture Y" \
  --source-ref paper.md \
  --evidence-ref projects/my_project/workspace/min_repro.json \
  --non-claim "not a full replication" \
  --next-falsifier "run the setup from a clean checkout" \
  --expected-command "ztare autoresearch route --task 'test one bounded claim' --project my_project --rubric my_project"

ztare project intake validate --path my_project_intake.json
```

See [`examples/project_packets/`](../../examples/project_packets/) for a
ready intake file and an intentionally malformed one.

When intake validates and you want to place it in the local intake ledger:

```bash
ztare project intake enqueue --path my_project_intake.json
```

The intake queue is a readiness ledger, not an agent scheduler. Autoresearch
execution remains a separate in-loop decision.

## 4. Keep Kernel Edits and Project Policy Separate

Use this rule of thumb when deciding where a change belongs:

| If you are changing... | Put it in... |
|---|---|
| A reusable validator, gate, CLI command, parser, or schema | `src/ztare/`, `scripts/public/`, `schemas/`, tests |
| A public guide, example, claim register, or roadmap | `docs/`, `examples/`, `priority_roadmap.md` |
| A project-specific rubric or fixture intended for publication | a sanitized project/example path with evidence references |
| Private project data, unpublished notes, local credentials, live run state | a private workspace outside the public commit set |

Avoid cleaning a fork by deleting broad tracked directories. Start from a fresh
clone or branch, inspect `git status`, and promote only the files you mean to
publish.

## 5. Public and Private Boundary

The repo is designed so public artifacts are inspectable and private state can
stay outside the public tree.

| Path | Public fork default |
|---|---|
| `src/ztare/` | yes, reusable kernel |
| `scripts/public/` | yes, public tooling and gates |
| `schemas/` | yes, shared contracts |
| `docs/` | yes, public documentation unless under an explicitly internal path |
| `examples/` | yes, small reviewable fixtures and packets |
| `priority_roadmap.md` | yes, public roadmap |
| `org/` | public policy where intentionally tracked; live/private org state should stay out |
| `projects/` | publish only sanitized, intentional project artifacts |
| `papers/` | publish only work you mean to release |
| `ztare_workspace/` | local runtime state; do not publish casually |

Before any public push, `make gates` is the practical boundary check. It catches
private references, stale documentation indexes, and public-entry drift.

## 6. Optional Org Runtime Work

If you want the org-runtime surface, read these after the first-run path works:

- [`org_runtime_quickstart.md`](org_runtime_quickstart.md)
- [`runtime_smoke_test.md`](runtime_smoke_test.md)
- [`workflow.md`](workflow.md)

Treat org runtime configuration as advanced. The first public fork milestone is
a reproducible checkout plus one small project-intake file or demo that another
person can validate offline.

## 7. Useful Next Steps

- Run [`quickstart.md`](quickstart.md) end to end.
- Read the public capability map in [`../concepts/capabilities.md`](../concepts/capabilities.md).
- Add one bounded project-intake file and one matching rubric.
- Run `make first-run` after every public-facing change.
- Run `make gates` before committing or pushing.
