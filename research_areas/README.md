# Research Areas

`research_areas/` holds all the human-authored research content for this repo: seeds, debates, specs, drafts, plans, cross-cutting seam trackers, and (gitignored) private principal notes. It is a **peer folder** to `supervisor/`, not nested inside it.

The split is:

- **prose a human reads or writes → `research_areas/`**
- **JSON the supervisor reads or writes → `supervisor/`**

Nothing supervisor-owned lives inside `research_areas/`, and nothing human-authored lives inside `supervisor/`. They cross-reference by filename, not by nesting.

---

## What lives where

| Subfolder | What it holds | Who writes it |
|---|---|---|
| `seeds/{active,deferred,legacy}/` | Seed specs — strategic starting contracts for potential programs | Human, manually |
| `seed_registry.json` | Authoritative seed lifecycle status (`active` / `deferred` / `closed` / `superseded`) | Human, manually |
| `debates/{kernel,papers,planning,supervisor,product-strategy}/` | Bounded A1/A2 debate logs, one file per program | A1/A2 spec agents, turn-by-turn |
| `specs/{active,archive}/` | Locked deterministic contracts (canonical `ProseSpec` etc.) | A2 spec agent, locked after debate |
| `drafts/` | Generated manuscript fragments and assembly manifests | B writer/builder |
| `program_plans/` | Human-readable *rendering* of active program manifests | Rendered from `supervisor/program_manifests/*.json` |
| `proposal_plans/` | Human-readable rendering of pre-registry proposals | Rendered from `supervisor_proposal` outputs |
| `seams/` | Cross-project hardening seam writeups (GP-0* generics) | Human, standalone from programs |
| `catch_grammar/` | Paper-4 evidence log, rule-auditor specs, corpus notes | Human, ad hoc |
| `HARDENING_BOARD.md` | Public historical hardening tracker as of 2026-05-20 | Human |
| `ZTARE_BOARD.md` | Historical cross-cutting seam tracker; current priorities live in `priority_roadmap.md` and the experiment record | Human |
| `EXPERIMENT_TRACK_RECORD.md` | Public sanitized track record of experiments and promoted knowledge claims | Human, manually |
| `private/` (gitignored) | Principal-facing notes, planning, private product thinking | Human, private |
| `archive/` | Frozen artifacts from closed programs kept for provenance | One-time archival moves |

`program_plans/` and `proposal_plans/` are **views** rendered from supervisor JSON. Treat them as read-only outputs, not sources of truth. If a `program_plans/foo.md` and `supervisor/program_manifests/foo.json` disagree, the JSON wins.

The experiment / hypothesis reporting split is:

- `research_areas/EXPERIMENT_TRACK_RECORD.md` — public sanitized mirror
- `[internal-ref]` — canonical private ledger

These are not replacements for seams. They are the compressed cross-program
track record. The hardening board is public historical provenance as of
2026-05-20; do not use it as the current roadmap.

---

## Seed lifecycle (authoritative)

Seed status is tracked in `seed_registry.json`. Folder location is a convention, not the final source of truth — some older seed files remain in place for path stability even after their registry status flips to `closed`.

Current seed statuses (check `seed_registry.json` for authoritative state):

- `seeds/active/stage2_derivation_seam.md` — registry `closed`, retained for provenance after the derivation-seam program completed
- `seeds/active/paper4_managerial_capitalism.md` — registry `closed`, retained while the live manuscript continues at `research_areas/drafts/paper4_full_working.md` and `papers/paper4/main.tex`
- `seeds/active/paper4_manuscript.md` — registry `closed`, retained while supervisor-era packet artifacts remain archived under `research_areas/_archive/paper4_supervisor/`
- `seeds/deferred/systems_to_algorithms.md` — deferred future avenue
- `seeds/deferred/vnext_semantic_gate_stabilization.md` — deferred kernel hardening seed
- `seeds/deferred/ztare_open_source.md` — deferred future avenue
- `seeds/legacy/v3_interface.md` — closed legacy seed, superseded by the V4-era contract and supervisor stack

Seed specs are **strategic inputs**. They must not be mutated by the tactical debate loop.

---

## How a program touches both folders

A single program touches `research_areas/` and `supervisor/` by design. Each artifact has exactly one home. The flow:

```
research_areas/seeds/active/foo.md            (you write the seed)
  ↓ human acceptance
supervisor/program_genesis/foo.json           (immutable genesis contract)
supervisor/program_registry.json              (entry added to portfolio)
supervisor/program_manifests/foo.json         (live mutable manifest)
  ↓ rendered for humans
research_areas/program_plans/foo.md           (readable view — not source of truth)
  ↓ supervisor routes A1/A2/B/C
research_areas/debates/kernel/foo.md          (debate turns, append-only)
research_areas/specs/active/foo.md            (locked ProseSpec after debate, if public)
[internal-ref]    (locked ProseSpec after debate, if private)
research_areas/drafts/foo_fragment.md         (generated output from B)
  ↓ run state
supervisor/active_runs/<run_id>/status.json   (machine state, gitignored)
```

See `supervisor/USER_MANUAL.md` for the supervisor side of this flow and the A1 / A2 / B / C / D state machine.

---

## Canonical debate groups

- `debates/papers/` — paper drafting debates
- `debates/kernel/` — V4 kernel hardening debates
- `debates/planning/` — roadshow, strategy, non-implementation planning
- `debates/supervisor/` — supervisor meta-loop debates (the supervisor improving itself)
- `debates/product-strategy/` — product and go-to-market thinking

Debate logs are append-only. Do not rewrite history.

---

## Archival

Opportunistic, not scheduled. When a program closes in `supervisor/program_registry.json`, its stale `active/` artifacts get moved to archive folders — seed → `seeds/legacy/`, spec → `specs/archive/`, drafts → `research_areas/_archive/<program>/drafts/`, program_plan → `research_areas/_archive/<program>/program_plan.md`.

Debate logs stay in place (provenance). `supervisor/program_genesis/*.json` and `supervisor/program_manifests/*.json` never move (immutable / registry-indexed). Registries themselves are never archived.

Full move table and the principal rule ("archival is opportunistic, not a scheduled sweep") live in `[internal-ref]` §1b.

---

## Rule of thumb

If you are not sure where to put something, ask:

1. Is it prose a human reads or writes? → `research_areas/`
2. Is it JSON the supervisor reads or writes? → `supervisor/`
3. Is it a rendered *view* of supervisor state for human reading? → `research_areas/program_plans/` or `research_areas/proposal_plans/`
4. Is it confidential / still-cooking / principal-facing? → `[internal-ref]` (gitignored)
5. Is it from a closed program? → archive it per PRINCIPAL_MANUAL §1b, don't leave it in `active/`
